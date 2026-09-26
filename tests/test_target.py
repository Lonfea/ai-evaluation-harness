import json

import httpx

from app import target
from app.models import GoldenCase

CASE = GoldenCase(
    id="grounded-001",
    category="grounded_fact",
    input="What is the documented value for indicator 1?",
    expected_output="Indicator 1 has the documented value 101.",
    retrieval_context=["Page 1: Indicator 1 has the documented value 101."],
    expected_citations=[1],
)


def test_request_never_contains_the_answer_key(monkeypatch):
    sent = {}

    def handler(request: httpx.Request) -> httpx.Response:
        sent.update(json.loads(request.content))
        return httpx.Response(200, json={"answer": "value 101 [p.1]", "citations": [1]})

    real_client = httpx.Client
    monkeypatch.setenv("TARGET_URL", "http://target.test/ask")
    monkeypatch.setattr(
        target.httpx,
        "Client",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    result = target.call_target(CASE)
    assert result.citations == [1]
    assert sent == {"input": CASE.input, "retrieval_context": CASE.retrieval_context}

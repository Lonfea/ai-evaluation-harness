import os

import httpx
from langsmith import traceable

from app.models import GoldenCase, TargetResult


@traceable(name="golden-case-target-call", run_type="chain")
def call_target(case: GoldenCase) -> TargetResult:
    url = os.environ["TARGET_URL"]
    with httpx.Client(timeout=90) as client:
        response = client.post(
            url,
            json={
                "input": case.input,
                "retrieval_context": case.retrieval_context,
                "expected_output": case.expected_output,
            },
        )
        response.raise_for_status()
        return TargetResult.model_validate(response.json())

import pytest

from app.models import GoldenCase, TargetResult
from app.scoring import citation_scores, deterministic_checks, is_abstention, key_facts


@pytest.mark.parametrize(
    "answer",
    [
        "The provided evidence does not support an exact audited profit.",
        "The documents do not contain enough evidence to answer.",
        "I cannot determine the audited profit from these pages.",
        "There is insufficient information to answer.",
    ],
)
def test_detects_abstentions(answer):
    assert is_abstention(answer)


@pytest.mark.parametrize(
    "answer",
    ["Indicator 1 has the documented value 101.", "The audited profit was 4.2 million."],
)
def test_does_not_mistake_answers_for_abstentions(answer):
    assert not is_abstention(answer)


def test_key_facts_keep_numbers_and_identifiers():
    assert key_facts("Programme 1 is assigned to Region-1.") == {"1", "region-1"}
    assert key_facts("Revenue was 3,400.5 million") == {"3,400.5"}


def test_citation_scores():
    assert citation_scores([31], [31]) == (1.0, 1.0)
    assert citation_scores([31], [31, 91]) == (0.5, 1.0)
    assert citation_scores([31], []) == (1.0, 0.0)
    assert citation_scores([], []) == (1.0, 1.0)


CASE = GoldenCase(
    id="distractor-001",
    category="distractor_resistance",
    input="Which region is assigned to programme 1?",
    expected_output="Programme 1 is assigned to Region-1.",
    retrieval_context=["Page 31: Programme 1 is assigned to Region-1."],
    expected_citations=[31],
)


def test_correct_response_passes_every_check():
    checks = deterministic_checks(CASE, TargetResult(answer="Programme 1 is assigned to Region-1 [p.31].", citations=[31]))
    assert checks["citation_ok"] and checks["refusal_ok"] and checks["facts_ok"]


def test_similar_entity_fails_fact_check():
    checks = deterministic_checks(CASE, TargetResult(answer="Programme 1 is assigned to Region-101.", citations=[31]))
    assert not checks["facts_ok"]


def test_refusing_an_answerable_question_fails():
    checks = deterministic_checks(CASE, TargetResult(answer="The evidence does not support an answer."))
    assert not checks["refusal_ok"]

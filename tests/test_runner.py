import httpx

from app.dataset import load_goldens
from app.models import TargetResult
from app.runner import evaluate_suite

CASES = load_goldens("goldens/goldens.jsonl")


def oracle(case):
    return TargetResult(answer=case.expected_output, citations=case.expected_citations)


def test_oracle_passes_every_case_without_judges():
    aggregate, _ = evaluate_suite(CASES, oracle)
    assert aggregate.pass_rate == 1.0
    assert aggregate.mean_faithfulness is None  # no judges ran
    assert set(aggregate.category_pass_rates) == {
        "conflicting_context",
        "distractor_resistance",
        "grounded_fact",
        "unanswerable",
    }


def test_target_errors_fail_the_case_but_not_the_suite():
    def flaky(case):
        if case.id == "grounded-001":
            raise httpx.ReadTimeout("slow target")
        return oracle(case)

    aggregate, results = evaluate_suite(CASES, flaky)
    failed = [row for row in results if not row["passed"]]
    assert [row["id"] for row in failed] == ["grounded-001"]
    assert "ReadTimeout" in failed[0]["error"]
    assert aggregate.category_pass_rates["grounded_fact"] == 29 / 30


def test_judges_are_skipped_for_refusal_cases():
    class RecordingJudges:
        def __init__(self):
            self.seen = []

        def score(self, case, target):
            self.seen.append(case.category)
            return 1.0, 1.0

    judges = RecordingJudges()
    evaluate_suite(CASES, oracle, judges)
    assert "unanswerable" not in judges.seen
    assert len(judges.seen) == 90


def test_low_judge_scores_fail_cases():
    class HarshJudges:
        def score(self, case, target):
            return 0.5, 0.9

    aggregate, _ = evaluate_suite(CASES, oracle, HarshJudges())
    assert aggregate.category_pass_rates["unanswerable"] == 1.0
    assert aggregate.category_pass_rates["grounded_fact"] == 0.0
    assert aggregate.mean_faithfulness == 0.5

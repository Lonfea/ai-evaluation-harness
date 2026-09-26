import argparse
import json
import os
from collections import defaultdict
from collections.abc import Callable
from pathlib import Path
from statistics import mean

import httpx

from app.dataset import load_goldens
from app.gate import GateConfig, regression_reasons
from app.models import AggregateResult, GoldenCase, TargetResult
from app.scoring import deterministic_checks

Target = Callable[[GoldenCase], TargetResult]
JUDGE_CHOICES = ("none", "deepeval", "ragas", "all")
CASE_MIN_FAITHFULNESS = 0.85
CASE_MIN_ANSWER_RELEVANCY = 0.80


class Judges:
    """LLM-judge metrics, created only when a run asks for them."""

    def __init__(self, kind: str, model: str | None):
        from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
        from deepeval.metrics.ragas import RAGASAnswerRelevancyMetric, RAGASFaithfulnessMetric

        self.faithfulness = []
        self.relevancy = []
        if kind in ("deepeval", "all"):
            self.faithfulness.append(FaithfulnessMetric(model=model))
            self.relevancy.append(AnswerRelevancyMetric(model=model))
        if kind in ("ragas", "all"):
            self.faithfulness.append(RAGASFaithfulnessMetric(model=model))
            self.relevancy.append(RAGASAnswerRelevancyMetric(model=model))

    def score(self, case: GoldenCase, target: TargetResult) -> tuple[float, float]:
        from deepeval.test_case import LLMTestCase

        test_case = LLMTestCase(
            input=case.input,
            actual_output=target.answer,
            expected_output=case.expected_output,
            retrieval_context=target.retrieval_context or case.retrieval_context,
        )

        def measure(metric) -> float:
            metric.measure(test_case)
            return float(metric.score or 0.0)

        return (
            mean(measure(metric) for metric in self.faithfulness),
            mean(measure(metric) for metric in self.relevancy),
        )


def evaluate_case(case: GoldenCase, target: Target, judges: Judges | None) -> dict:
    result: dict = {"id": case.id, "category": case.category}
    try:
        response = target(case)
    except (httpx.HTTPError, ValueError) as exc:
        # One failing call is a failed case, not a crashed suite.
        return {**result, "error": f"{type(exc).__name__}: {exc}", "passed": False}

    checks = deterministic_checks(case, response)
    passed = checks["citation_ok"] and checks["refusal_ok"] and checks["facts_ok"]
    result.update(checks)

    # Abstentions contain no claims to judge; refusal_ok already covers them.
    if judges and not case.should_refuse:
        faithfulness, relevancy = judges.score(case, response)
        result.update(faithfulness=faithfulness, answer_relevancy=relevancy)
        passed = (
            passed
            and faithfulness >= CASE_MIN_FAITHFULNESS
            and relevancy >= CASE_MIN_ANSWER_RELEVANCY
        )
    result["passed"] = passed
    return result


def aggregate(case_results: list[dict]) -> AggregateResult:
    def rate(key: str, rows: list[dict]) -> float:
        return mean(1.0 if row.get(key) else 0.0 for row in rows)

    def average(key: str) -> float | None:
        values = [row[key] for row in case_results if key in row]
        return mean(values) if values else None

    by_category: dict[str, list[dict]] = defaultdict(list)
    for row in case_results:
        by_category[row["category"]].append(row)

    return AggregateResult(
        cases=len(case_results),
        pass_rate=rate("passed", case_results),
        citation_accuracy=rate("citation_ok", case_results),
        refusal_accuracy=rate("refusal_ok", case_results),
        fact_accuracy=rate("facts_ok", case_results),
        mean_faithfulness=average("faithfulness"),
        mean_answer_relevancy=average("answer_relevancy"),
        category_pass_rates={
            category: rate("passed", rows) for category, rows in sorted(by_category.items())
        },
    )


def evaluate_suite(
    cases: list[GoldenCase], target: Target, judges: Judges | None = None
) -> tuple[AggregateResult, list[dict]]:
    if len(cases) < 100:
        raise RuntimeError("Production eval suite must contain at least 100 golden cases.")
    case_results = [evaluate_case(case, target, judges) for case in cases]
    return aggregate(case_results), case_results


def config_from_env() -> GateConfig:
    def env(name: str, default: float) -> float:
        return float(os.getenv(name, str(default)))

    defaults = GateConfig()
    return GateConfig(
        min_pass_rate=env("MIN_PASS_RATE", defaults.min_pass_rate),
        min_faithfulness=env("MIN_FAITHFULNESS", defaults.min_faithfulness),
        min_answer_relevancy=env("MIN_ANSWER_RELEVANCY", defaults.min_answer_relevancy),
        min_citation_accuracy=env("MIN_CITATION_ACCURACY", defaults.min_citation_accuracy),
        min_refusal_accuracy=env("MIN_REFUSAL_ACCURACY", defaults.min_refusal_accuracy),
        min_fact_accuracy=env("MIN_FACT_ACCURACY", defaults.min_fact_accuracy),
        min_category_pass_rate=env("MIN_CATEGORY_PASS_RATE", defaults.min_category_pass_rate),
        max_regression=env("MAX_REGRESSION", defaults.max_regression),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the golden suite and apply the release gate.")
    parser.add_argument("--goldens", default="goldens/goldens.jsonl")
    parser.add_argument("--report", default="reports/latest.json")
    parser.add_argument("--baseline", default="baseline/approved.json")
    parser.add_argument(
        "--judges",
        choices=JUDGE_CHOICES,
        default=os.getenv("EVAL_JUDGES", "all" if os.getenv("EVAL_MODEL") else "none"),
        help="LLM-judge metrics to run; 'none' runs deterministic checks only",
    )
    args = parser.parse_args()

    from app.target import call_target

    judges = None if args.judges == "none" else Judges(args.judges, os.getenv("EVAL_MODEL"))
    current, case_results = evaluate_suite(load_goldens(args.goldens), call_target, judges)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps({"aggregate": current.model_dump(), "cases": case_results}, indent=2),
        encoding="utf-8",
    )

    baseline_path = Path(args.baseline)
    baseline = (
        AggregateResult.model_validate_json(baseline_path.read_text(encoding="utf-8"))
        if baseline_path.exists()
        else None
    )
    print(json.dumps(current.model_dump(), indent=2))
    failures = regression_reasons(current, baseline, config_from_env())
    if failures:
        raise SystemExit("Evaluation gate failed:\n- " + "\n- ".join(failures))
    print("Evaluation gate passed.")


if __name__ == "__main__":
    main()

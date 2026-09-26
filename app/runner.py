import json
import os
from pathlib import Path
from statistics import mean

from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.metrics.ragas import RAGASAnswerRelevancyMetric, RAGASFaithfulnessMetric
from deepeval.test_case import LLMTestCase

from app.dataset import load_goldens
from app.gate import GateConfig, regression_reasons
from app.models import AggregateResult
from app.target import call_target


def _score(metric, test_case: LLMTestCase) -> float:
    metric.measure(test_case)
    return float(metric.score or 0.0)


def evaluate_suite(goldens_path: str, report_path: str) -> AggregateResult:
    cases = load_goldens(goldens_path)
    if len(cases) < 100:
        raise RuntimeError("Production eval suite must contain at least 100 golden cases.")

    native_faithfulness = FaithfulnessMetric(model=os.getenv("EVAL_MODEL"))
    native_relevancy = AnswerRelevancyMetric(model=os.getenv("EVAL_MODEL"))
    ragas_faithfulness = RAGASFaithfulnessMetric(model=os.getenv("EVAL_MODEL"))
    ragas_relevancy = RAGASAnswerRelevancyMetric(model=os.getenv("EVAL_MODEL"))

    case_results = []
    for case in cases:
        target = call_target(case)
        test_case = LLMTestCase(
            input=case.input,
            actual_output=target.answer,
            expected_output=case.expected_output,
            retrieval_context=target.retrieval_context or case.retrieval_context,
        )

        faithfulness_scores = [
            _score(native_faithfulness, test_case),
            _score(ragas_faithfulness, test_case),
        ]
        relevancy_scores = [
            _score(native_relevancy, test_case),
            _score(ragas_relevancy, test_case),
        ]

        expected = set(case.expected_citations)
        actual = set(target.citations)
        citation_ok = (not expected) or expected.issubset(actual)

        faithfulness = mean(faithfulness_scores)
        relevancy = mean(relevancy_scores)
        passed = faithfulness >= 0.85 and relevancy >= 0.80 and citation_ok

        case_results.append(
            {
                "id": case.id,
                "category": case.category,
                "faithfulness": faithfulness,
                "answer_relevancy": relevancy,
                "citation_ok": citation_ok,
                "passed": passed,
            }
        )

    aggregate = AggregateResult(
        cases=len(case_results),
        pass_rate=mean(1.0 if r["passed"] else 0.0 for r in case_results),
        mean_faithfulness=mean(r["faithfulness"] for r in case_results),
        mean_answer_relevancy=mean(r["answer_relevancy"] for r in case_results),
        citation_accuracy=mean(1.0 if r["citation_ok"] else 0.0 for r in case_results),
    )

    payload = {"aggregate": aggregate.model_dump(), "cases": case_results}
    Path(report_path).parent.mkdir(parents=True, exist_ok=True)
    Path(report_path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return aggregate


def main() -> None:
    current = evaluate_suite("goldens/goldens.jsonl", "reports/latest.json")

    baseline_path = Path("baseline/approved.json")
    baseline = None
    if baseline_path.exists():
        baseline = AggregateResult.model_validate_json(
            baseline_path.read_text(encoding="utf-8")
        )

    config = GateConfig(
        min_pass_rate=float(os.getenv("MIN_PASS_RATE", "0.90")),
        min_faithfulness=float(os.getenv("MIN_FAITHFULNESS", "0.85")),
        min_answer_relevancy=float(os.getenv("MIN_ANSWER_RELEVANCY", "0.80")),
        max_regression=float(os.getenv("MAX_REGRESSION", "0.03")),
    )
    failures = regression_reasons(current, baseline, config)
    if failures:
        raise SystemExit("Evaluation gate failed:\n- " + "\n- ".join(failures))


if __name__ == "__main__":
    main()

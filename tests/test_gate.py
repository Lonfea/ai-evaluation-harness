from app.gate import GateConfig, regression_reasons
from app.models import AggregateResult


def result(value: float, **overrides) -> AggregateResult:
    fields = {
        "cases": 120,
        "pass_rate": value,
        "mean_faithfulness": value,
        "mean_answer_relevancy": value,
        "citation_accuracy": value,
        "refusal_accuracy": value,
        "fact_accuracy": value,
    }
    return AggregateResult(**{**fields, **overrides})


def test_green_result_passes():
    assert regression_reasons(result(0.97), None, GateConfig()) == []


def test_threshold_failure_is_blocked():
    reasons = regression_reasons(result(0.50), None, GateConfig())
    assert reasons


def test_quality_regression_is_blocked():
    reasons = regression_reasons(result(0.90), result(0.97), GateConfig(max_regression=0.03))
    assert any("regressed" in reason for reason in reasons)


def test_metrics_not_computed_are_skipped():
    deterministic_only = result(0.97, mean_faithfulness=None, mean_answer_relevancy=None)
    assert regression_reasons(deterministic_only, result(0.97), GateConfig()) == []


def test_one_collapsed_category_blocks_despite_good_average():
    candidate = result(0.97, category_pass_rates={"grounded_fact": 1.0, "unanswerable": 0.6})
    reasons = regression_reasons(candidate, None, GateConfig())
    assert reasons == ["category unanswerable pass rate below threshold: 0.600 < 0.800"]


def test_category_regression_against_baseline_is_blocked():
    baseline = result(0.97, category_pass_rates={"unanswerable": 1.0})
    candidate = result(0.97, category_pass_rates={"unanswerable": 0.9})
    assert any("unanswerable regressed" in r for r in regression_reasons(candidate, baseline, GateConfig()))


def test_baselines_from_v0_1_still_load():
    old = AggregateResult.model_validate_json(
        '{"cases": 120, "pass_rate": 0.95, "mean_faithfulness": 0.9, '
        '"mean_answer_relevancy": 0.9, "citation_accuracy": 0.97}'
    )
    assert old.refusal_accuracy is None
    assert regression_reasons(result(0.97), old, GateConfig()) == []

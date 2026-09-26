from app.gate import GateConfig, regression_reasons
from app.models import AggregateResult


def result(value: float) -> AggregateResult:
    return AggregateResult(
        cases=120,
        pass_rate=value,
        mean_faithfulness=value,
        mean_answer_relevancy=value,
        citation_accuracy=value,
    )


def test_green_result_passes():
    assert regression_reasons(result(0.97), None, GateConfig()) == []


def test_threshold_failure_is_blocked():
    reasons = regression_reasons(result(0.50), None, GateConfig())
    assert reasons


def test_quality_regression_is_blocked():
    reasons = regression_reasons(result(0.90), result(0.97), GateConfig(max_regression=0.03))
    assert any("regressed" in reason for reason in reasons)

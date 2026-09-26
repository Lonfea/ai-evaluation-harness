from dataclasses import dataclass

from app.models import AggregateResult


@dataclass(frozen=True)
class GateConfig:
    min_pass_rate: float = 0.90
    min_faithfulness: float = 0.85
    min_answer_relevancy: float = 0.80
    min_citation_accuracy: float = 0.95
    max_regression: float = 0.03


def regression_reasons(
    current: AggregateResult,
    baseline: AggregateResult | None,
    config: GateConfig,
) -> list[str]:
    reasons: list[str] = []

    thresholds = {
        "pass_rate": (current.pass_rate, config.min_pass_rate),
        "faithfulness": (current.mean_faithfulness, config.min_faithfulness),
        "answer_relevancy": (
            current.mean_answer_relevancy,
            config.min_answer_relevancy,
        ),
        "citation_accuracy": (current.citation_accuracy, config.min_citation_accuracy),
    }
    for name, (value, minimum) in thresholds.items():
        if value < minimum:
            reasons.append(f"{name} below threshold: {value:.3f} < {minimum:.3f}")

    if baseline:
        comparisons = {
            "pass_rate": (current.pass_rate, baseline.pass_rate),
            "faithfulness": (
                current.mean_faithfulness,
                baseline.mean_faithfulness,
            ),
            "answer_relevancy": (
                current.mean_answer_relevancy,
                baseline.mean_answer_relevancy,
            ),
            "citation_accuracy": (
                current.citation_accuracy,
                baseline.citation_accuracy,
            ),
        }
        for name, (now, before) in comparisons.items():
            drop = before - now
            if drop > config.max_regression:
                reasons.append(
                    f"{name} regressed by {drop:.3f}, "
                    f"exceeding {config.max_regression:.3f}"
                )

    return reasons

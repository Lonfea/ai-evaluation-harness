from dataclasses import dataclass

from app.models import AggregateResult

TRACKED = {
    "pass_rate": "pass_rate",
    "faithfulness": "mean_faithfulness",
    "answer_relevancy": "mean_answer_relevancy",
    "citation_accuracy": "citation_accuracy",
    "refusal_accuracy": "refusal_accuracy",
    "fact_accuracy": "fact_accuracy",
}


@dataclass(frozen=True)
class GateConfig:
    min_pass_rate: float = 0.90
    min_faithfulness: float = 0.85
    min_answer_relevancy: float = 0.80
    min_citation_accuracy: float = 0.95
    min_refusal_accuracy: float = 0.95
    min_fact_accuracy: float = 0.95
    min_category_pass_rate: float = 0.80
    max_regression: float = 0.03

    def minimum(self, name: str) -> float:
        return getattr(self, f"min_{name}")


def regression_reasons(
    current: AggregateResult,
    baseline: AggregateResult | None,
    config: GateConfig,
) -> list[str]:
    """Return every reason the candidate must not ship; an empty list means pass.

    Metrics the run did not compute (None) are skipped rather than treated as zero,
    so a deterministic-only run is not failed for lacking judge scores.
    """
    reasons: list[str] = []

    for name, field in TRACKED.items():
        value = getattr(current, field)
        if value is not None and value < config.minimum(name):
            reasons.append(f"{name} below threshold: {value:.3f} < {config.minimum(name):.3f}")

    # A collapse in one failure mode must not hide inside a healthy average.
    for category, value in sorted(current.category_pass_rates.items()):
        if value < config.min_category_pass_rate:
            reasons.append(
                f"category {category} pass rate below threshold: "
                f"{value:.3f} < {config.min_category_pass_rate:.3f}"
            )

    if baseline:
        for name, field in TRACKED.items():
            now, before = getattr(current, field), getattr(baseline, field)
            if now is None or before is None:
                continue
            drop = before - now
            if drop > config.max_regression:
                reasons.append(
                    f"{name} regressed by {drop:.3f}, exceeding {config.max_regression:.3f}"
                )
        for category, before in sorted(baseline.category_pass_rates.items()):
            now = current.category_pass_rates.get(category)
            if now is not None and before - now > config.max_regression:
                reasons.append(
                    f"category {category} regressed by {before - now:.3f}, "
                    f"exceeding {config.max_regression:.3f}"
                )

    return reasons

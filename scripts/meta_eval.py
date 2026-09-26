"""Check that the release gate blocks systems with known defects.

An evaluation harness is only useful if it fails bad releases. This script
runs the golden suite against reference systems with one planted defect
each, plus a correct oracle, and records whether the gate blocks them.

Only the deterministic checks run here (no judge model), so the results are
exact and reproducible. The "v1" column shows what the harness's original
deterministic check (expected citations are a subset of cited pages) would
have decided for the same systems.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.dataset import load_goldens
from app.gate import GateConfig, regression_reasons
from app.models import GoldenCase, TargetResult
from app.runner import evaluate_suite

ABSTAIN = "The provided evidence does not support an answer."


def page(context: str) -> int:
    return int(re.match(r"Page (\d+):", context).group(1))


def sentence(context: str) -> str:
    return context.split(":", 1)[1].strip()


def oracle(case: GoldenCase) -> TargetResult:
    return TargetResult(answer=case.expected_output, citations=case.expected_citations)


def cites_everything(case: GoldenCase) -> TargetResult:
    """Correct answers, but cites every retrieved page to be safe."""
    answer = oracle(case)
    if case.should_refuse:
        return answer
    return TargetResult(
        answer=answer.answer, citations=[page(c) for c in case.retrieval_context]
    )


def never_abstains(case: GoldenCase) -> TargetResult:
    """Invents a figure when the evidence has none."""
    if not case.should_refuse:
        return oracle(case)
    first = case.retrieval_context[0]
    return TargetResult(answer="The audited profit was 4.2 million.", citations=[page(first)])


def always_abstains(case: GoldenCase) -> TargetResult:
    """Over-cautious: refuses everything."""
    return TargetResult(answer=ABSTAIN, citations=[])


def follows_distractor(case: GoldenCase) -> TargetResult:
    """Answers from the second passage, which names a similar but different entity."""
    if case.category != "distractor_resistance":
        return oracle(case)
    distractor = case.retrieval_context[1]
    return TargetResult(answer=sentence(distractor), citations=[page(distractor)])


def uses_stale_draft(case: GoldenCase) -> TargetResult:
    """Answers conflicting-evidence cases from the superseded draft."""
    if case.category != "conflicting_context":
        return oracle(case)
    draft = case.retrieval_context[0]
    value = re.search(r"target of (\d+)", draft).group(1)
    metric = re.search(r"metric (\d+)", case.input).group(1)
    return TargetResult(
        answer=f"The latest approved target for metric {metric} is {value}.",
        citations=[page(draft)],
    )


def right_page_wrong_number(case: GoldenCase) -> TargetResult:
    """Cites correctly but misreads the value (off by one) in grounded cases."""
    if case.category != "grounded_fact":
        return oracle(case)
    wrong = re.sub(r"value (\d+)", lambda m: f"value {int(m.group(1)) + 1}", case.expected_output)
    return TargetResult(answer=wrong, citations=case.expected_citations)


SYSTEMS = {
    "oracle (correct)": oracle,
    "cites every retrieved page": cites_everything,
    "never abstains (invents figures)": never_abstains,
    "always abstains": always_abstains,
    "follows distractor passage": follows_distractor,
    "uses superseded draft": uses_stale_draft,
    "right page, wrong number": right_page_wrong_number,
}


def v1_blocks(cases: list[GoldenCase], target) -> bool:
    """Original deterministic gate: citation subset check at >= 95% of cases."""
    ok = [
        not case.expected_citations or set(case.expected_citations) <= set(target(case).citations)
        for case in cases
    ]
    return sum(ok) / len(ok) < GateConfig().min_citation_accuracy


def run(goldens: Path) -> dict:
    cases = load_goldens(goldens)
    results = {}
    for name, target in SYSTEMS.items():
        aggregate, _ = evaluate_suite(cases, target)
        reasons = regression_reasons(aggregate, None, GateConfig())
        results[name] = {
            "blocked": bool(reasons),
            "blocked_by_v1_checks": v1_blocks(cases, target),
            "pass_rate": round(aggregate.pass_rate, 3),
            "reasons": reasons,
        }
    defective = [name for name in SYSTEMS if name != "oracle (correct)"]
    return {
        "goldens": str(goldens),
        "cases": len(cases),
        "judges": "none (deterministic checks only)",
        "defective_systems_blocked": sum(results[n]["blocked"] for n in defective),
        "defective_systems_blocked_by_v1_checks": sum(
            results[n]["blocked_by_v1_checks"] for n in defective
        ),
        "defective_systems": len(defective),
        "oracle_passes": not results["oracle (correct)"]["blocked"],
        "systems": results,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check that the gate blocks known-bad systems.")
    parser.add_argument("--goldens", type=Path, default=PROJECT_ROOT / "goldens" / "goldens.jsonl")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    args = parser.parse_args()
    report = run(args.goldens)
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)

"""Regenerate goldens/goldens.jsonl.

The suite is templated on purpose: four failure modes, 30 cases each, where
case i differs only in its numbers and page positions. That makes every
expected answer and citation checkable by eye, at the cost of linguistic
variety. Real product questions belong in a separate, hand-reviewed file.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CASES_PER_CATEGORY = 30


def grounded(i: int) -> dict:
    return {
        "id": f"grounded-{i:03d}",
        "category": "grounded_fact",
        "input": f"What is the documented value for indicator {i}?",
        "expected_output": f"Indicator {i} has the documented value {100 + i}.",
        "retrieval_context": [
            f"Page {i}: Indicator {i} has the documented value {100 + i}.",
            f"Page {40 + i}: Background information unrelated to indicator {i}.",
        ],
        "expected_citations": [i],
        "should_refuse": False,
    }


def distractor(i: int) -> dict:
    return {
        "id": f"distractor-{i:03d}",
        "category": "distractor_resistance",
        "input": f"Which region is assigned to programme {i}?",
        "expected_output": f"Programme {i} is assigned to Region-{i}.",
        "retrieval_context": [
            f"Page {30 + i}: Programme {i} is assigned to Region-{i}.",
            f"Page {90 + i}: Programme {100 + i} is assigned to Region-{100 + i}.",
            f"Page {120 + i}: This appendix discusses programme naming conventions but not assignment.",
        ],
        "expected_citations": [30 + i],
        "should_refuse": False,
    }


def unanswerable(i: int) -> dict:
    return {
        "id": f"unanswerable-{i:03d}",
        "category": "unanswerable",
        "input": f"What was the exact audited profit for fictional unit {i}?",
        "expected_output": "The provided evidence does not support an exact audited profit.",
        "retrieval_context": [
            f"Page {120 + i}: Fictional unit {i} is mentioned, but no audited profit figure is provided.",
            f"Page {150 + i}: This section contains operational notes only.",
        ],
        "expected_citations": [],
        "should_refuse": True,
    }


def conflict(i: int) -> dict:
    return {
        "id": f"conflict-{i:03d}",
        "category": "conflicting_context",
        "input": f"What is the latest approved target for metric {i}?",
        "expected_output": f"The latest approved target for metric {i} is {200 + i}.",
        "retrieval_context": [
            f"Page {180 + i}: An earlier draft proposed a target of {150 + i} for metric {i}.",
            f"Page {210 + i}: The later approved revision supersedes the draft and sets metric {i} to {200 + i}.",
        ],
        "expected_citations": [210 + i],
        "should_refuse": False,
    }


def generate() -> list[dict]:
    return [
        build(i)
        for build in (grounded, distractor, unanswerable, conflict)
        for i in range(1, CASES_PER_CATEGORY + 1)
    ]


def render() -> str:
    return "\n".join(json.dumps(case, separators=(",", ":")) for case in generate()) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, default=Path("goldens/goldens.jsonl"))
    args = parser.parse_args()
    args.output.write_text(render(), encoding="utf-8")
    print(f"Wrote {len(generate())} cases to {args.output}")

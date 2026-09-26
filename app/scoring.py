"""Deterministic checks that need no judge model.

They run on every commit and cover what LLM judges are weakest at: exact
citations, required abstention, and whether the answer contains the facts
the golden case expects.
"""

from __future__ import annotations

import re

from app.models import GoldenCase, TargetResult

_ABSTAIN = re.compile(
    r"does not (?:support|contain|provide|include|state|specify)"
    r"|do not (?:support|contain|provide|include|state|specify)"
    r"|(?:not|no) (?:enough|sufficient) (?:evidence|information)"
    r"|(?:cannot|can't|unable to) (?:be )?(?:determine|answer|find|confirm)"
    r"|insufficient (?:evidence|information)"
    r"|no (?:evidence|information) (?:is |was )?(?:provided|available)",
    re.IGNORECASE,
)
_FACT = re.compile(r"[A-Za-z]*-?\d+(?:[.,]\d+)*")


def is_abstention(answer: str) -> bool:
    return bool(_ABSTAIN.search(answer))


def key_facts(text: str) -> set[str]:
    """Tokens that carry the answer: numbers and identifiers containing digits."""
    return {token.lower().rstrip(".,") for token in _FACT.findall(text)}


def citation_scores(expected: list[int], actual: list[int]) -> tuple[float, float]:
    """Precision and recall of cited pages against the golden pages."""
    expected_set, actual_set = set(expected), set(actual)
    if not expected_set and not actual_set:
        return 1.0, 1.0
    true_positives = len(expected_set & actual_set)
    precision = true_positives / len(actual_set) if actual_set else 1.0
    recall = true_positives / len(expected_set) if expected_set else 1.0
    return precision, recall


def deterministic_checks(case: GoldenCase, target: TargetResult) -> dict:
    """Score one response without an LLM judge."""
    abstained = is_abstention(target.answer)
    precision, recall = citation_scores(case.expected_citations, target.citations)
    if case.should_refuse:
        facts_ok = True
    else:
        facts_ok = key_facts(case.expected_output) <= key_facts(target.answer)
    return {
        "abstained": abstained,
        "refusal_ok": abstained == case.should_refuse,
        "citation_precision": precision,
        "citation_recall": recall,
        "citation_ok": precision == 1.0 and recall == 1.0,
        "facts_ok": facts_ok,
    }

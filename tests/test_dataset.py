from app.dataset import load_goldens


def test_suite_has_at_least_100_goldens():
    cases = load_goldens("goldens/goldens.jsonl")
    assert len(cases) >= 100


def test_golden_ids_are_unique():
    cases = load_goldens("goldens/goldens.jsonl")
    ids = [case.id for case in cases]
    assert len(ids) == len(set(ids))


def test_suite_has_multiple_failure_modes():
    cases = load_goldens("goldens/goldens.jsonl")
    categories = {case.category for case in cases}
    assert {
        "grounded_fact",
        "distractor_resistance",
        "unanswerable",
        "conflicting_context",
    }.issubset(categories)

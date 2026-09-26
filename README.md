# Automated AI Evaluation Harness

A regression-testing system for AI applications with **120 committed golden cases**, DeepEval and RAGAS quality metrics, optional LangSmith tracing, and a quality gate that can fail deployment when model behavior degrades.

## Why this exists

Traditional unit tests catch deterministic software bugs. They do not answer whether an LLM response became less faithful, less relevant, or worse at citing evidence after a prompt, retrieval, model, or infrastructure change.

This harness treats AI quality as a release criterion.

## Evaluation layers

1. **Deterministic contract tests**
   - 100+ golden cases are present and valid.
   - IDs are unique.
   - expected failure modes are represented.
   - regression-gate math is unit tested.

2. **LLM quality evaluation**
   - DeepEval faithfulness
   - DeepEval answer relevancy
   - RAGAS faithfulness
   - RAGAS answer relevancy
   - citation accuracy

3. **Regression gate**
   - absolute minimum thresholds;
   - comparison with an approved baseline;
   - deployment blocked when the quality drop exceeds tolerance.

4. **Traceability**
   - target calls are decorated with LangSmith `traceable`;
   - set `LANGSMITH_TRACING=true` and credentials to record full runs.

## Golden suite

`goldens/goldens.jsonl` contains 120 synthetic, auditable cases across:

- grounded factual answers;
- distractor resistance;
- unanswerable questions;
- conflicting evidence.

These cases are test fixtures, **not claimed production measurements**.

## Target contract

Set `TARGET_URL` to an endpoint that accepts:

    {
      "input": "...",
      "retrieval_context": ["..."],
      "expected_output": "..."
    }

and returns:

    {
      "answer": "...",
      "retrieval_context": ["..."],
      "citations": [1, 2]
    }

This makes the harness usable against a local service, preview deployment, or production canary.

## Run deterministic CI

    pytest -q
    ruff check .

## Run full quality gate

    python -m app.runner

The full run requires an evaluator model and the configured target service. Results are written to `reports/latest.json`.

## Baselines

A baseline is only created from a **real completed run**. This repository intentionally does not ship fabricated quality scores.

To approve a real run:

    cp reports/latest.json <review-and-extract-aggregate-to-baseline>

## Release policy

Default thresholds:
- pass rate >= 0.90
- mean faithfulness >= 0.85
- mean answer relevancy >= 0.80
- citation accuracy >= 0.95
- no tracked metric may regress by more than 0.03 from the approved baseline

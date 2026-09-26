from pathlib import Path

from app.models import GoldenCase


def load_goldens(path: str | Path) -> list[GoldenCase]:
    rows = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                rows.append(GoldenCase.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"Invalid golden on line {line_number}") from exc
    return rows

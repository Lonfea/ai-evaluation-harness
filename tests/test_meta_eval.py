from pathlib import Path

import generate_goldens
import meta_eval


def test_committed_goldens_match_the_generator():
    assert Path("goldens/goldens.jsonl").read_text(encoding="utf-8") == generate_goldens.render()


def test_gate_blocks_every_planted_defect_and_passes_the_oracle():
    report = meta_eval.run(Path("goldens/goldens.jsonl"))
    assert report["oracle_passes"]
    assert report["defective_systems_blocked"] == report["defective_systems"]

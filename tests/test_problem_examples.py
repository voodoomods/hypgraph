"""The problem examples (examples/problems) run end to end with no model: each scripts an agent's lines, files them,
and asserts what the engine did with each one. A changed refusal code or a line that now goes in fails here."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from hypgraph import Graph

HERE = Path(__file__).resolve().parent.parent / "examples" / "problems"

CASES = [
    ("hallucinated_figures.py", "OK: 3 made-up figures refused", {"UNBOUND_NUMBER": 3}),
    ("hit_the_number.py", "OK: the 20% was refused",
     {"UNBOUND_NUMBER": 1, "TARGET_NOT_MET": 1, "SIGNIFICANCE_NOT_SHOWN": 1}),
    ("backtest_brag.py", "OK: an unlabelled in-sample return",
     {"BACKTEST_WITHOUT_COSTS": 1, "IN_SAMPLE_UNLABELLED": 1, "EDGE_CONTRADICTED": 2, "COMPARISON_REVERSED": 1}),
    ("optimal_trust_me.py", "OK: 'optimal' and 'best possible' were refused",
     {"OPTIMAL_CONTRADICTED": 2, "OBJECTIVE_WITHOUT_FEASIBILITY": 1}),
    ("cover_up.py", "OK: 1 attack blocked, 1 caught by the file's own check, 3 caught only by the published head.",
     None),
]


@pytest.mark.parametrize("script,expect,codes", CASES, ids=[c[0] for c in CASES])
def test_example_runs(script, expect, codes, tmp_path):
    if not (HERE / script).exists():
        pytest.skip("examples aren't shipped in the sdist")
    db = tmp_path / "record.hypgraph"
    r = subprocess.run([sys.executable, script, "--db", str(db)], cwd=HERE, env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-3000:])
    assert expect in r.stdout
    g = Graph(str(db))
    try:
        assert g.verify()["ok"]
        if codes is not None:                        # the refusals the story tells are the ones in the record's log
            got = g.refusal_report()["by_code"]
            assert {c: got.get(c) for c in codes} == codes, got
    finally:
        g.close()

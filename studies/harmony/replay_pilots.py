#!/usr/bin/env python3
"""Replay every refusal logged in the pilot records (runs/*/*/record.hypgraph) through the current checker and
aggregate: which refusals would now pass, which are refused for other reasons, which can't be replayed because the
log holds only the statement (pilots 1-3; bodies are logged from D-10 on).

    python studies/harmony/replay_pilots.py runs/pilot runs/pilot2 runs/pilot3
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from hypgraph import Graph  # noqa: E402
from hypgraph.refusals import replay_markdown  # noqa: E402


def main(roots: list[str]) -> int:
    total = {"replayed": 0, "verdicts": Counter(), "by_code": defaultdict(Counter), "rows": []}
    for root in roots:
        for rec in sorted(Path(root).glob("*/record.hypgraph")):
            r = Graph(str(rec)).replay_refusals()
            total["replayed"] += r["replayed"]
            total["verdicts"].update(r["verdicts"])
            for c, v in r["by_code"].items():
                total["by_code"][c].update(v)
            for x in r["rows"]:
                x["record"] = rec.parent.name
            total["rows"] += r["rows"]
    total["verdicts"] = dict(total["verdicts"])
    total["by_code"] = {k: dict(v) for k, v in total["by_code"].items()}
    print(replay_markdown(total))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["runs/pilot", "runs/pilot2", "runs/pilot3"]))

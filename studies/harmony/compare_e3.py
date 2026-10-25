#!/usr/bin/env python3
"""E, E′ (D-19) and E″ (D-19b) side by side, paired by instance; reproduction verdicts for the latter two.

    python studies/harmony/compare_e3.py runs/confirmatory runs/d19 runs/d19b
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from collections import Counter
from pathlib import Path

from compare_e import load


def reprod(root: Path) -> Counter:
    c: Counter = Counter()
    for d in root.iterdir():
        if not (d / "run.json").exists():
            continue
        r = json.loads((d / "run.json").read_text(encoding="utf-8"))
        for e in (r.get("scheduler") or {}).get("events") or []:
            if e.get("kind") == "reproduced":
                c["runs"] += 1
                c["confirmed values"] += len(e.get("confirmed") or [])
                c["unprinted values"] += len(e.get("unprinted") or [])
                c["contradicted values"] += len(e.get("contradicted") or [])
                c["ok"] += 1 if e.get("ok") else 0
            if e.get("kind") == "report_missing":
                c["reports lost"] += 1
    return c


def main(a: str, b: str, c: str) -> int:
    E, E2, E3 = load(Path(a), "E"), load(Path(b), "E"), load(Path(c), "E")
    both = sorted(set(E) & set(E2) & set(E3), key=lambda x: (int(x.split("-")[0][1:]), x))
    print(f"E {len(E)} · E′ {len(E2)} · E″ {len(E3)} · instances in all three: {len(both)}\n")
    print(f"{'metric':<14}{'E':>9}{'E′':>9}{'E″':>9}{'E″/E':>8}")
    for k in ("calls", "usd", "critic", "show", "graph_add", "register_run", "review"):
        x, y, z = (st.mean(S[i][k] for i in both) for S in (E, E2, E3))
        print(f"{k:<14}{x:>9.3f}{y:>9.3f}{z:>9.3f}{(z / x if x else float('nan')):>8.2f}")
    for name, S in (("E′/E", E2), ("E″/E", E3), ("E″/E′", None)):
        base = E if S is not None else E2
        cmp = S if S is not None else E3
        lr = [math.log(cmp[i]["usd"] / base[i]["usd"]) for i in both if base[i]["usd"] and cmp[i]["usd"]]
        m, sd = st.mean(lr), st.stdev(lr)
        h = 1.96 * sd / math.sqrt(len(lr))
        print(f"paired cost ratio {name}: {math.exp(m):.2f} [{math.exp(m - h):.2f}, {math.exp(m + h):.2f}]")
    for k in ("correct", "traps", "cap"):
        print(f"{k:<10} E {sum(E[i][k] for i in both):>3}  E′ {sum(E2[i][k] for i in both):>3}  E″ {sum(E3[i][k] for i in both):>3}  (of {len(both)})")
    for name, root in (("E′", Path(b)), ("E″", Path(c))):
        print(f"reproductions {name}:", dict(reprod(root)))
    print("\nper instance calls E→E′→E″ (correct):")
    for i in both:
        print(f"  {i:<8} {E[i]['calls']:>4}→{E2[i]['calls']:<4}→{E3[i]['calls']:<4}  {int(E[i]['correct'])}{int(E2[i]['correct'])}{int(E3[i]['correct'])}"
              + ("  CAP" if E3[i]["cap"] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))

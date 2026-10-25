#!/usr/bin/env python3
"""E′ (D-19) against E, paired by instance: calls, cost, correctness, traps, cap hits, the critic's share, `show`
calls, reproductions and their outcome. Measurement of a harness change, not a result of the preregistered study.

    python studies/harmony/compare_e.py runs/confirmatory runs/d19
"""
from __future__ import annotations

import json
import math
import statistics as st
import sys
from collections import Counter
from pathlib import Path


def load(root: Path, cond: str) -> dict[str, dict]:
    out = {}
    for d in sorted(root.iterdir()):
        if not (d / "meta.json").exists():
            continue
        m = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        if m["condition"] != cond:
            continue
        r = json.loads((d / "run.json").read_text(encoding="utf-8"))
        s = json.loads((d / "score.json").read_text(encoding="utf-8"))
        led = json.loads((d / "ledger.json").read_text(encoding="utf-8"))
        units = r.get("units") or {}
        critic = sum(v.get("calls", 0) for k, v in units.items() if (v.get("agent") or k).startswith("critic"))
        tools = Counter(t.get("tool") for t in r.get("tool_log") or [])
        ev = (r.get("scheduler") or {}).get("events") or []
        rep = [e for e in ev if e.get("kind") == "reproduced"]
        out[m["instance"]] = {"calls": r.get("n_calls") or 0, "usd": led.get("usd") or 0, "correct": s["fraction"] == 1.0,
                              "traps": len(s["trap_hits"]), "cap": bool(r.get("cap_hit")), "critic": critic,
                              "show": tools.get("show", 0), "graph_add": tools.get("graph_add", 0),
                              "register_run": tools.get("register_run", 0), "review": tools.get("review", 0),
                              "reproduced": len(rep), "reproduced_ok": sum(1 for e in rep if e.get("ok")),
                              "stall_aff": bool(m.get("stall_affected"))}
    return out


def main(a: str, b: str) -> int:
    E, E2 = load(Path(a), "E"), load(Path(b), "E")
    both = sorted(set(E) & set(E2), key=lambda x: (int(x.split("-")[0][1:]), x))
    print(f"E: {len(E)} runs · E′: {len(E2)} runs · paired instances: {len(both)}\n")
    keys = ["calls", "usd", "critic", "show", "graph_add", "register_run", "review"]
    print(f"{'metric':<14}{'E':>9}{'E′':>9}{'ratio':>8}")
    for k in keys:
        x, y = st.mean(E[i][k] for i in both), st.mean(E2[i][k] for i in both)
        print(f"{k:<14}{x:>9.3f}{y:>9.3f}{(y / x if x else float('nan')):>8.2f}")
    lr = [math.log(E2[i]["usd"] / E[i]["usd"]) for i in both if E[i]["usd"] and E2[i]["usd"]]
    if len(lr) > 1:
        m, sd = st.mean(lr), st.stdev(lr)
        lo, hi = m - 1.96 * sd / math.sqrt(len(lr)), m + 1.96 * sd / math.sqrt(len(lr))
        print(f"\npaired cost ratio E′/E (geometric): {math.exp(m):.2f}  [{math.exp(lo):.2f}, {math.exp(hi):.2f}]  n={len(lr)}")
    for k in ("correct", "traps", "cap"):
        print(f"{k:<10} E {sum(E[i][k] for i in both):>3}   E′ {sum(E2[i][k] for i in both):>3}   (of {len(both)})")
    rep = sum(E2[i]["reproduced"] for i in both)
    print(f"reproductions in E′: {rep} ({sum(E2[i]['reproduced_ok'] for i in both)} ok, "
          f"{rep - sum(E2[i]['reproduced_ok'] for i in both)} not reproduced)")
    print("\nper instance (calls E→E′, $ E→E′, correct, traps):")
    for i in both:
        e, f = E[i], E2[i]
        print(f"  {i:<8} {e['calls']:>4}→{f['calls']:<4} {e['usd']:.4f}→{f['usd']:.4f}  {int(e['correct'])}→{int(f['correct'])}"
              f"  traps {e['traps']}→{f['traps']}{'  CAP' if f['cap'] else ''}")
    only = sorted(set(E2) - set(E))
    if only:
        print("\nE′ only (no E pair):", ", ".join(only))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

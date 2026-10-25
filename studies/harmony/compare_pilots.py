#!/usr/bin/env python3
"""Compare two pilots run by run and condition by condition: did the record condition finish, how many calls, how
many sub-agent units ran to the turn cap, refusals and fixes, and metered cost. Pilot data only; nothing here is a
result of the study.

    python studies/harmony/compare_pilots.py runs/pilot2 runs/pilot3
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path


def load(root: Path) -> dict:
    out: dict[str, list] = defaultdict(list)
    for d in sorted(root.iterdir()):
        if not (d / "meta.json").exists():
            continue
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        run = json.loads((d / "run.json").read_text(encoding="utf-8"))
        sc = json.loads((d / "score.json").read_text(encoding="utf-8"))
        led = json.loads((d / "ledger.json").read_text(encoding="utf-8"))
        units = [v for k, v in run.get("units", {}).items() if k != "lead"]
        ref = run.get("refusals") or {}
        out[meta["condition"]].append({
            "instance": meta["instance"], "calls": run.get("n_calls", 0), "usd": float(led.get("usd") or 0),
            "submitted": bool(run.get("submitted")), "cap_hit": bool(run.get("cap_hit")),
            "correct": sc["core_correct"], "total": sc["core_total"], "traps": sc["trap_hits"],
            "units": len(units), "unit_calls": [u["calls"] for u in units],
            "capped_units": sum(1 for u in units if u["calls"] >= run.get("caps", {}).get("max_turns", 14)),
            "refused": ref.get("refused", 0), "fixed": ref.get("fixed", 0),
            "by_code": ref.get("by_code", {}), "seconds": run.get("seconds", 0),
            "claims": sum(1 for t in run.get("tool_log", []) if t["tool"] == "graph_add" and '"claim"' in t["args"]
                          and t["out"].startswith("added")),
        })
    return out


def summarise(rows: list[dict]) -> dict:
    n = len(rows)
    uc = [c for r in rows for c in r["unit_calls"]]
    return {"runs": n, "submitted": sum(r["submitted"] for r in rows), "cap_hits": sum(r["cap_hit"] for r in rows),
            "correct_runs": sum(r["correct"] == r["total"] for r in rows),
            "fraction": round(sum(r["correct"] / r["total"] for r in rows) / n, 3) if n else 0,
            "traps": sum(len(r["traps"]) for r in rows), "calls_mean": round(sum(r["calls"] for r in rows) / n, 1),
            "usd_total": round(sum(r["usd"] for r in rows), 4), "usd_mean": round(sum(r["usd"] for r in rows) / n, 4),
            "seconds_mean": round(sum(r["seconds"] for r in rows) / n), "units": sum(r["units"] for r in rows),
            "calls_per_unit": round(sum(uc) / len(uc), 1) if uc else 0,
            "capped_units": sum(r["capped_units"] for r in rows), "refused": sum(r["refused"] for r in rows),
            "fixed": sum(r["fixed"] for r in rows), "claims": sum(r["claims"] for r in rows)}


def main(a: str, b: str) -> int:
    A, B = load(Path(a)), load(Path(b))
    name_a, name_b = Path(a).name, Path(b).name
    keys = ["runs", "submitted", "cap_hits", "correct_runs", "fraction", "traps", "calls_mean", "usd_mean",
            "usd_total", "seconds_mean", "units", "calls_per_unit", "capped_units", "claims", "refused", "fixed"]
    print(f"| condition | metric | {name_a} | {name_b} |\n|---|---|---|---|")
    for c in "ABCD":
        if c not in A and c not in B:
            continue
        sa, sb = summarise(A.get(c, [])), summarise(B.get(c, []))
        for k in keys:
            print(f"| {c} | {k} | {sa.get(k, '—')} | {sb.get(k, '—')} |")
    for c in ("C", "D"):
        codes_a, codes_b = defaultdict(int), defaultdict(int)
        for r in A.get(c, []):
            for k, v in r["by_code"].items():
                codes_a[k] += v
        for r in B.get(c, []):
            for k, v in r["by_code"].items():
                codes_b[k] += v
        print(f"\n{c} refusal codes: {name_a} {dict(sorted(codes_a.items(), key=lambda x: -x[1]))}")
        print(f"{c} refusal codes: {name_b} {dict(sorted(codes_b.items(), key=lambda x: -x[1]))}")
    print(f"\nper run ({name_b}):")
    for c in "ABCD":
        for r in B.get(c, []):
            print(f"  {r['instance']:<7} {c}  calls {r['calls']:>3}  ${r['usd']:.4f}  {r['correct']}/{r['total']}"
                  f"  submitted {r['submitted']!s:<5} capped units {r['capped_units']}/{r['units']}"
                  f"  refused {r['refused']} fixed {r['fixed']}  traps {r['traps']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))

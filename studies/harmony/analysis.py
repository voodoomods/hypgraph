#!/usr/bin/env python3
"""
Harmony study — the preregistered analysis. Frozen with PREREG.md (see PREREG-LOCK.json); changing it after the
lock is a deviation and goes in DEVIATIONS.md.

    python studies/harmony/analysis.py runs/            # every run under runs/ → results.json + results.md
    python studies/harmony/analysis.py runs/ --pilot    # also: the sample-size rule applied to pilot variance

Stdlib only. Reads, per run directory: meta.json, score.json, run.json, ledger.json (written by dev/study_host.py).

Primary outcomes
    correct      run_correct (every core sub-question right) and fraction (core sub-questions right)
    cost         metered dollars from the proxy ledger (ledger.json usd). A run with no ledger rows but model calls
                 is costed from its token counts at the subject model's pricing (flagged "estimated").
Contrasts (Holm-corrected within the primary family): C vs A, C vs B. Secondary: D vs C, B vs A.
Pairing: by instance (family + seed). Bootstrap over instances, 10,000 resamples, seed 20261024.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
from collections import defaultdict
from pathlib import Path

PRIMARY = [("C", "A"), ("C", "B")]
SECONDARY = [("D", "C"), ("B", "A")]
B_RESAMPLES = 10_000
SEED = 20261024
COST_EFFECT = math.log(1 / 0.8)       # the smallest cost difference worth detecting: 20 % cheaper
INSTANCES_MIN, INSTANCES_MAX = 3, 6   # per family, the sample-size rule's bounds


def load(root: Path) -> list[dict]:
    rows = []
    for d in sorted(p for p in root.iterdir() if (p / "meta.json").exists()):
        meta = json.loads((d / "meta.json").read_text(encoding="utf-8"))
        sc = json.loads((d / "score.json").read_text(encoding="utf-8"))
        run = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
        led = json.loads((d / "ledger.json").read_text(encoding="utf-8")) if (d / "ledger.json").exists() else {}
        usd, est = led.get("usd"), False
        if (usd in (None, 0) or led.get("error")) and run.get("n_calls"):
            usd, est = None, True                     # costed later from tokens if a price is given
        rows.append({"dir": d.name, "instance": meta["instance"], "family": meta["family"], "seed": meta["seed"],
                     "condition": meta["condition"], "model": meta["model"], "correct": bool(sc["run_correct"]),
                     "fraction": sc["fraction"], "parse_ok": sc["parse_ok"], "traps": sc["trap_hits"],
                     "usd": usd, "usd_estimated": est, "calls": run.get("n_calls", 0),
                     "tokens": run.get("tokens", {}), "cap_hit": run.get("cap_hit", False),
                     "error": bool(run.get("error")), "submitted": run.get("submitted", False),
                     "waste": waste(run, led, meta)})
    return rows


def waste(run: dict, led: dict, meta: dict) -> dict:
    """Spend on work that couldn't count, by kind — from the run's own logs, the same way in every condition.
       after_notice_stale   F7: calls after the notice, in units that read the stale file after it
       duplicate            F6: calls in units working Q2 or Q4 beyond the first unit that worked either
       rework               B reopened hand-offs, C/D reworked orders
    Dollars split a unit's metered cost across its calls by tokens."""
    calls = run.get("calls") or []
    unit_usd = {u["unit"].split(":", 1)[-1]: u["usd"] for u in led.get("by_unit", []) if u.get("unit")}
    tok = defaultdict(int)
    for c in calls:
        tok[c["unit"]] += (c.get("in") or 0) + (c.get("out") or 0)

    def usd(c):
        u = c["unit"]
        return unit_usd.get(u, 0.0) * (((c.get("in") or 0) + (c.get("out") or 0)) / tok[u]) if tok[u] else 0.0
    out = {"after_notice_stale": 0.0, "duplicate": 0.0, "rework": 0.0, "calls_after_notice_stale": 0}
    tools = run.get("tool_log") or []
    if meta["family"] == "F7" and run.get("notice_call") is not None:
        # D-4: stale = used site_b.csv after the notice and never site_b_fixed.csv (checking one against the
        # other is verification, not waste)
        post = [t for t in tools if t["after_notice"]]
        used_stale = {t["unit"] for t in post if re.search(r"site_b\.csv", t["args"])}
        used_fixed = {t["unit"] for t in post if "site_b_fixed" in t["args"]}
        stale_units = used_stale - used_fixed
        for c in calls:
            if c["after_notice"] and c["unit"] in stale_units:
                out["after_notice_stale"] += usd(c)
                out["calls_after_notice_stale"] += 1
    if meta["family"] == "F6":
        q24 = [u for u in dict.fromkeys(c["unit"] for c in calls) if u != "lead" and _unit_mentions(run, u)]
        for u in q24[1:]:
            out["duplicate"] += sum(usd(c) for c in calls if c["unit"] == u)
    rew = [u for u in {c["unit"] for c in calls} if re.fullmatch(r"H\d+r\d+", u)]
    rew += [o["code"] for o in run.get("orders", []) if o.get("status") == "reworked"]
    for u in rew:
        out["rework"] += sum(usd(c) for c in calls if c["unit"] == u)
    return {k: round(v, 6) if isinstance(v, float) else v for k, v in out.items()}


def _unit_mentions(run: dict, unit: str) -> bool:
    """Did the unit's brief (the orchestrator call that started it) name Q2 or Q4?"""
    calls = run.get("calls") or []
    start = next((c["i"] for c in calls if c["unit"] == unit), None)
    if start is None:
        return False
    before = [t for t in (run.get("tool_log") or []) if t["agent"] == "orchestrator" and t["call"] <= start
              and t["tool"] in ("ask", "delegate", "issue_work")]
    return bool(before) and bool(re.search(r"\bQ[24]\b", before[-1]["args"]))


def boot(xs: list[float], rng: random.Random, stat=lambda v: sum(v) / len(v)) -> tuple[float, float, float]:
    if not xs:
        return (float("nan"),) * 3
    est = stat(xs)
    sims = sorted(stat([xs[rng.randrange(len(xs))] for _ in xs]) for _ in range(B_RESAMPLES))
    return est, sims[int(0.025 * B_RESAMPLES)], sims[int(0.975 * B_RESAMPLES) - 1]


def boot_p(xs: list[float], rng: random.Random, null: float = 0.0) -> float:
    """Two-sided bootstrap p for the mean of paired differences against ``null`` (percentile inversion)."""
    if not xs:
        return float("nan")
    m = sum(xs) / len(xs)
    centred = [x - m + null for x in xs]
    sims = [sum(centred[rng.randrange(len(xs))] for _ in xs) / len(xs) for _ in range(B_RESAMPLES)]
    return min(1.0, 2 * min(sum(s >= m for s in sims), sum(s <= m for s in sims)) / B_RESAMPLES)


def contrast(rows: list[dict], a: str, b: str, rng: random.Random) -> dict:
    by = defaultdict(dict)
    for r in rows:
        by[r["instance"]][r["condition"]] = r
    pairs = [(v[a], v[b]) for v in by.values() if a in v and b in v]
    d_corr = [int(x["correct"]) - int(y["correct"]) for x, y in pairs]
    d_frac = [x["fraction"] - y["fraction"] for x, y in pairs]
    costed = [(x, y) for x, y in pairs if x["usd"] and y["usd"]]
    lr = [math.log(x["usd"] / y["usd"]) for x, y in costed]
    per_correct = {c: (sum(r["usd"] or 0 for r in rows if r["condition"] == c)
                       / max(1, sum(r["correct"] for r in rows if r["condition"] == c))) for c in (a, b)}
    est, lo, hi = boot(lr, rng)
    return {"contrast": f"{a} vs {b}", "pairs": len(pairs), "costed_pairs": len(costed),
            "correct_diff": boot(d_corr, rng), "correct_p": boot_p(d_corr, rng),
            "fraction_diff": boot(d_frac, rng),
            "cost_ratio": tuple(math.exp(v) for v in (est, lo, hi)) if lr else None,
            "cost_p": boot_p(lr, rng) if lr else None,
            "usd_per_correct": per_correct}


def holm(ps: list[float]) -> list[float]:
    order = sorted(range(len(ps)), key=lambda i: ps[i])
    adj, run = [0.0] * len(ps), 0.0
    for k, i in enumerate(order):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = run
    return adj


def sample_size(rows: list[dict]) -> dict:
    """The preregistered rule: instances per family so that a paired test on log cost detects a 20 % difference
    with 80 % power at the 5 % level, from the pilot's SD of paired log ratios (C vs A), bounded to [3, 6]."""
    by = defaultdict(dict)
    for r in rows:
        by[r["instance"]][r["condition"]] = r
    lr = [math.log(v["C"]["usd"] / v["A"]["usd"]) for v in by.values() if "C" in v and "A" in v
          and v["C"]["usd"] and v["A"]["usd"]]
    if len(lr) < 2:
        return {"rule": "not enough costed pilot pairs", "pairs": len(lr), "instances_per_family": INSTANCES_MAX}
    m = sum(lr) / len(lr)
    sd = math.sqrt(sum((x - m) ** 2 for x in lr) / (len(lr) - 1))
    n_total = math.ceil(((1.959964 + 0.841621) * sd / COST_EFFECT) ** 2)
    fams = len({r["family"] for r in rows}) or 1
    per = min(INSTANCES_MAX, max(INSTANCES_MIN, math.ceil(n_total / 10)))
    return {"pairs": len(lr), "sd_log_ratio": round(sd, 4), "total_pairs_needed": n_total, "families_piloted": fams,
            "instances_per_family": per, "underpowered_for_cost": n_total > INSTANCES_MAX * 10}


def summarise(rows: list[dict], price: float | None) -> dict:
    if price:
        for r in rows:
            if r["usd"] is None:
                t = r["tokens"] or {}
                r["usd"] = ((t.get("in", 0) - t.get("cached", 0)) * price["in"] + t.get("cached", 0) * price["cached"]
                            + t.get("out", 0) * price["out"]) / 1e6
    rng = random.Random(SEED)
    per = {}
    for c in "ABCD":
        rs = [r for r in rows if r["condition"] == c]
        if not rs:
            continue
        per[c] = {"runs": len(rs), "correct": sum(r["correct"] for r in rs),
                  "mean_fraction": round(sum(r["fraction"] for r in rs) / len(rs), 4),
                  "usd": round(sum(r["usd"] or 0 for r in rs), 6), "calls": sum(r["calls"] for r in rs),
                  "cap_hits": sum(r["cap_hit"] for r in rs), "errors": sum(r["error"] for r in rs),
                  "trap_hits": sum(len(r["traps"]) for r in rs),
                  "waste_usd": {k: round(sum(r["waste"][k] for r in rs), 6)
                                for k in ("after_notice_stale", "duplicate", "rework")}}
    prim = [contrast(rows, a, b, rng) for a, b in PRIMARY]
    for key in ("correct_p", "cost_p"):
        ps = [c[key] if c[key] is not None and not math.isnan(c[key]) else 1.0 for c in prim]
        for c, adj in zip(prim, holm(ps)):
            c[key + "_holm"] = adj
    sec = [contrast(rows, a, b, rng) for a, b in SECONDARY]
    return {"per_condition": per, "primary": prim, "secondary": sec,
            "estimated_cost_runs": sum(r["usd_estimated"] for r in rows)}


def fmt(x) -> str:
    if isinstance(x, tuple):
        return f"{x[0]:.3f} [{x[1]:.3f}, {x[2]:.3f}]"
    return "—" if x is None else (f"{x:.4f}" if isinstance(x, float) else str(x))


def markdown(s: dict) -> str:
    L = ["# Harmony study — results", "", "| condition | runs | correct | mean fraction | $ | calls | traps | cap hits |"
         " errors |", "|---|---|---|---|---|---|---|---|---|"]
    for c, v in s["per_condition"].items():
        L.append(f"| {c} | {v['runs']} | {v['correct']} | {v['mean_fraction']} | {v['usd']:.4f} | {v['calls']} | "
                 f"{v['trap_hits']} | {v['cap_hits']} | {v['errors']} |")
    for name, rows in (("Primary contrasts (Holm)", s["primary"]), ("Secondary contrasts", s["secondary"])):
        L += ["", f"## {name}", "", "| contrast | pairs | Δ correct [95% CI] | p | cost ratio [95% CI] | p |",
              "|---|---|---|---|---|---|"]
        for c in rows:
            L.append(f"| {c['contrast']} | {c['pairs']} | {fmt(c['correct_diff'])} | "
                     f"{fmt(c.get('correct_p_holm', c['correct_p']))} | {fmt(c['cost_ratio'])} | "
                     f"{fmt(c.get('cost_p_holm', c['cost_p']))} |")
    return "\n".join(L)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", type=Path)
    ap.add_argument("--pilot", action="store_true")
    ap.add_argument("--price", default="", help="in,cached,out $ per million tokens, for runs without ledger rows")
    a = ap.parse_args(argv)
    rows = load(a.runs)
    price = dict(zip(("in", "cached", "out"), map(float, a.price.split(",")))) if a.price else None
    s = summarise(rows, price)
    if a.pilot:
        s["sample_size"] = sample_size(rows)
    (a.runs / "results.json").write_text(json.dumps(s, indent=1, default=str), encoding="utf-8")
    (a.runs / "results.md").write_text(markdown(s), encoding="utf-8")
    print(markdown(s))
    if a.pilot:
        print("\nSample-size rule:", json.dumps(s["sample_size"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
The engine's timings at research-record scale, the source for the README's and the site's performance figures.

    python dev/bench.py [--nodes 10000] [--json]

Builds a record of about N nodes (questions, results bound to values, claims derived from them and answering the
questions, reviews on some), then measures on that file:
- derive_all_s: every node's standing derived from a cold cache (deriving, not reading SQLite);
- read_one_ms:  one node read (`get`) once the snapshot is warm;
- write_ms:     one write (a claim), median of 20, including SQLite's commit.
Numbers are this machine's, and the output says which machine and Python they came from.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hypgraph import Graph, Policy, __version__  # noqa: E402
from hypgraph import derive as D  # noqa: E402


def build(g: Graph, n: int) -> tuple[str, list[str]]:
    lead, a, critic = g.author("lead"), g.author("analyst"), g.author("critic")
    inv = lead.investigation("Benchmark investigation", "Measure the engine at research-record scale.")["id"]
    claims: list[str] = []
    made = 1
    i = 0
    while made < n:
        k, m = 100 + i % 700, 821 + i // 700               # every result's numbers differ (a repeat is refused)
        q = lead.add("question", inv, text=f"Is variant {i} better than the baseline on its items?")["id"]
        rs = a.add("result", inv, summary=f"Variant {i} right on {k} of {m} items.", values={"acc": {"k": k, "n": m}})["id"]
        cl = a.add("claim", inv, statement=f"The variant is right on {k} of {m} items.",
                   scope=f"Variant {i}, on its held-out items.",
                   links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
        claims.append(cl)
        made += 3
        if i % 3 == 0:
            critic.review(cl, "checked", "Recounted from the items file.", "The count holds.")
            made += 1
        i += 1
    return inv, claims


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--nodes", type=int, default=10000)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        g = Graph(Path(tmp) / "bench.hypgraph", policy=Policy(max_creates_per_minute=10**9))   # bulk build
        t0 = time.perf_counter()
        inv, claims = build(g, args.nodes)
        build_s = time.perf_counter() - t0
        s = g.snapshot()
        ids = list(s.nodes)
        s._state.clear()                                   # cold: nothing derived yet
        t0 = time.perf_counter()
        for nid in ids:
            D.state(s, nid)
        derive_all = time.perf_counter() - t0
        g.get(claims[0])
        reads = []
        for nid in claims[:200]:
            t0 = time.perf_counter()
            g.get(nid)
            reads.append(time.perf_counter() - t0)
        writes = []
        a = g.author("analyst")
        for k in range(20):
            t0 = time.perf_counter()
            a.add("question", inv, text=f"Is extra variant {k} better than the baseline on its items?")
            writes.append(time.perf_counter() - t0)
        g.close()
    out = {"nodes": len(ids), "derive_all_s": round(derive_all, 3), "read_one_ms": round(statistics.median(reads) * 1000, 2),
           "write_ms": round(statistics.median(writes) * 1000, 1), "build_s": round(build_s, 1),
           "hypgraph": __version__, "python": platform.python_version(),
           "machine": f"{platform.system()} {platform.release()}, {platform.processor() or platform.machine()}"}
    if args.json:
        print(json.dumps(out))
    else:
        print(f"{out['nodes']:,} nodes: derive all {out['derive_all_s']} s · read one {out['read_one_ms']} ms · "
              f"write {out['write_ms']} ms  ({out['machine']}, Python {out['python']}, hypgraph {out['hypgraph']})")


if __name__ == "__main__":
    main()

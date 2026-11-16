"""Export the records behind site/results/ as bundles (site/data/results/), from a checkout of the showcase runs.

    python dev/site_results.py <showcase dir>

The runs themselves (gpt-oss-20b, preregistered, labelled blind) live in the showcase repository; this copies the
five records the page opens, each re-verified on export, so dev/build_site.py can build the page without it. A bundle
carries the hash-chained record, not the refusal log, so each record's refusals and conduct lines are written beside
it (<name>.refusals.json), for the page to quote.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hypgraph import Graph  # noqa: E402

RECORDS = {  # bundle name -> record in the showcase repository
    "liar-s400": "exp1_spot_the_liar/results/run3/records/LIAR-s400.hypgraph",
    "mistake-s406": "exp1_spot_the_liar/results/run3/records/MISTAKE-s406.hypgraph",
    "headlines-s400": "exp2_no_more_than_the_data/results/run3/records/campaign-s400.hypgraph",
    "hallucinate-s100": "exp4_whos_hallucinating/results/run1/records/HALLUCINATE-s100.hypgraph",
    "outdated-s100": "exp4_whos_hallucinating/results/run1/records/OUTDATED-s100.hypgraph",
}


def main() -> None:
    src = Path(sys.argv[1])
    out = ROOT / "site" / "data" / "results"
    out.mkdir(parents=True, exist_ok=True)
    for name, rel in RECORDS.items():
        with tempfile.TemporaryDirectory() as d:
            copy = Path(d) / "r.hypgraph"           # never open the committed record itself
            shutil.copy2(src / rel, copy)
            g = Graph(str(copy))
            ok = g.verify()
            if not (ok.get("ok") if isinstance(ok, dict) else ok):
                raise SystemExit(f"{rel}: the hash chain does not verify")
            b = g.export()
            inv = b["derived"]["investigations"][0]
            inv = inv["id"] if isinstance(inv, dict) else inv
            refused = [{"author": r["author"], "statement": r["statement"], "codes": r["codes"],
                        "fixed": (r.get("fixed_by") or {}).get("statement")}
                       for r in sorted(g.refusals(inv), key=lambda r: r["id"])]
            conduct = {who: c["sentence"] for who, c in sorted(g.conduct(inv).items())}
            g.close()
        (out / f"{name}.refusals.json").write_text(json.dumps({"refused": refused, "conduct": conduct}, indent=1,
                                                              ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        (out / f"{name}.bundle.json").write_text(json.dumps(b, ensure_ascii=False, separators=(",", ":")),
                                                 encoding="utf-8", newline="\n")
        print(f"  site/data/results/{name}.bundle.json  {len(b['events'])} events, {len(b['nodes'])} nodes, {len(refused)} refusals")


if __name__ == "__main__":
    main()

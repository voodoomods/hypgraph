"""Export one verifiable bundle per @2 profile for the UI's checks (the site's examples: dev/site_examples.py).

    python dev/ui_fixtures.py <record> …      e.g. HypSwarm's examples/0{1..5}-*/record.hypgraph

Each record's first investigation is exported (`hypgraph export`) to dev/ui-fixtures/<profile family>.bundle.json, with
the derived views the UI reads. The bundles verify on their own; nothing in them is trusted by the UI."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypgraph import Graph
from hypgraph.bundle import verify_bundle

OUT = Path(__file__).resolve().parent / "ui-fixtures"

for path in sys.argv[1:]:
    g = Graph(path)
    try:
        inv = g.investigations()[0]["id"]
        pid = str(g.get(inv)["body"].get("profile") or "none")
        b = g.export(inv)
    finally:
        g.close()
    assert verify_bundle(b)["ok"], path
    name = pid.split("@")[0]
    (OUT / f"{name}.bundle.json").write_text(json.dumps(b, separators=(",", ":")), encoding="utf-8")
    print(f"{name:13} {pid:16} {len(b['nodes'])} nodes, {len(b['events'])} events")

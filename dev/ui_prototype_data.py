"""Build dev/ui-prototype/data.js from real records — one investigation per @2 profile — for the UI prototype.

    python dev/ui_prototype_data.py RECORD [RECORD …]

Each record is read with the engine (standing, stages, board, completion, report, chain check are all derived here,
exactly as `hypgraph serve` would), and written as `window.HG_DATA = {...}` so the prototype opens from disk with
no server. Read-only on the records."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hypgraph import Graph
from hypgraph import profiles as P

OUT = Path(__file__).resolve().parent / "ui-prototype" / "data.js"


def profile_meta(pid: str) -> dict:
    p = P.get(pid)
    w = p.workflow
    return {"id": pid, "name": p.name, "about": p.about, "vocabulary": p.vocabulary,
            "report": w.report if w else "Facts from the record", "method": w.method if w else "",
            "stages": [{"name": s.name, "holds": s.holds, "gate": s.gate, "who": s.who, "optional": s.optional}
                       for s in (w.stages if w else ())]}


def one(path: str) -> dict:
    g = Graph(path)
    try:
        inv = g.investigations()[0]
        iid = inv["id"]
        node = g.get(iid)
        pid = str(node["body"].get("profile") or "")
        sub = g.subgraph(iid)
        nodes = []
        for n in sub["nodes"]:
            st = n.get("state") or {}
            nodes.append({"id": n["id"], "code": n.get("code"), "type": n["type"], "title": n.get("title") or "",
                          "by": n.get("by"), "at": n.get("at"), "kind": n.get("kind") or "",
                          "lifecycle": st.get("lifecycle"), "review": (st.get("review") or {}).get("state"),
                          "stale": st.get("stale"), "at_risk": st.get("at_risk"), "sentence": st.get("sentence")})
        edges = [{"src": e["src"], "dst": e["dst"], "rel": e["rel"]} for e in sub["edges"]]
        rep = g.report(iid)
        snap = g.snapshot()
        code_of = {i: (n.get("code") or i) for i, n in snap.nodes.items()}
        evs = []
        for e in snap.events:
            pl = e.get("payload") or {}
            ref = e.get("ref") or ""
            if ref != iid and snap.nodes.get(ref, {}).get("inv") not in (iid, None) and e["kind"] != "create":
                continue
            if e["kind"] == "create" and pl.get("inv") not in (iid, "") and ref != iid:
                continue
            evs.append({"seq": e["seq"], "at": e["at"], "actor": e["actor"], "kind": e["kind"],
                        "ref": code_of.get(ref, ref), "type": pl.get("type") or snap.nodes.get(ref, {}).get("type"),
                        "rel": pl.get("rel"), "dst": code_of.get(pl.get("dst"), pl.get("dst")),
                        "verdict": pl.get("verdict"), "reason": pl.get("reason") or pl.get("note"),
                        "task": code_of.get(pl.get("task"), pl.get("task")), "for": pl.get("for")})
        orders = [{k: o.get(k) for k in ("code", "status", "assignee", "role", "target", "issued", "objective",
                                          "returned_note", "done_when")} for o in g.orders(iid)]
        return {"inv": {"id": iid, "code": node["code"], "title": node["body"].get("title"),
                        "objective": node["body"].get("objective"), "profile": pid},
                "profile": profile_meta(pid), "stages": g.stages(iid), "board": g.question_board(iid),
                "completion": g.completion(iid), "nodes": nodes, "edges": edges,
                "report": rep["markdown"], "open": rep.get("open"), "spend": rep.get("spend"),
                "events": evs, "orders": orders,
                "verify": g.verify() if hasattr(g, "verify") else None}
    finally:
        g.close()


def main() -> None:
    data = [one(p) for p in sys.argv[1:]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("window.HG_DATA = " + json.dumps(data, default=str) + ";\n", encoding="utf-8")
    for d in data:
        print(f"{d['profile']['id']:16} {d['inv']['title'][:60]:60} nodes={len(d['nodes'])} stages={len(d['stages'])}")
    print(OUT)


if __name__ == "__main__":
    main()

"""
Bundles: a record you can hand to someone else, who can check it without trusting you.

``export()`` writes the whole graph; ``export(inv)`` one investigation. Every event is included as the **exact string
its hash was taken over**, and every version body and edge's data as the exact string stored, so verifying is just
SHA-256 over strings plus a few lookups — any language can do it (the site does it in the browser with WebCrypto).

    {"format": "hypgraph/1-bundle", "complete": true, "scope": {...}, "policy": {...},
     "events":   [{"seq", "hash", "body"}],                 # body = canonical JSON of {at, actor, kind, ref, payload, prev}
     "nodes":    [{"id", "type", "code", "inv", "created_at", "created_by"}],
     "versions": [{"node", "v", "at", "by", "reason", "body"}],   # body = the stored canonical string
     "edges":    [{"id", "src", "src_v", "rel", "dst", "dst_v", "data", "at", "by", "why"}],   # data likewise
     "withdrawals": [...], "retractions": [...], "leases": [...],
     "derived":  {...}}                                     # standing at export time, for viewers; never trusted

A scoped bundle (one investigation out of a shared graph) redacts the events outside it to {seq, hash, prev}: their
content can't be checked, so a change hidden among them (a withdrawal, say) would not show. ``verify_bundle`` says so
(``complete: false``). To publish a study, keep it in a graph of its own and export all of it.
"""

from __future__ import annotations

import hashlib
import json
from typing import TYPE_CHECKING, Any

from . import __version__
from .store import GENESIS, event_body, now

if TYPE_CHECKING:
    from .graph import Graph

BUNDLE_FORMAT = "hypgraph/1-bundle"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def export(g: "Graph", inv: str = "", *, derived: bool = True) -> dict:
    with g._snap_lock:
        con = g._connect()
        rows = lambda q, *a: [dict(zip([c[0] for c in cur.description], r))  # noqa: E731
                              for cur in [con.execute(q, a)] for r in cur.fetchall()]
        nodes = rows("SELECT id, type, code, inv, created_at, created_by FROM nodes ORDER BY rowid")
        if inv:
            if not any(n["id"] == inv and n["type"] == "investigation" for n in nodes):
                raise KeyError(inv)
            nodes = [n for n in nodes if n["id"] == inv or n["inv"] == inv]
        ids = {n["id"] for n in nodes}
        versions = [v for v in rows("SELECT node, v, at, by, reason, body FROM versions ORDER BY rowid")
                    if v["node"] in ids]
        edges = [e for e in rows("SELECT id, src, src_v, rel, dst, dst_v, data, at, by, why FROM edges ORDER BY id")
                 if e["src"] in ids and e["dst"] in ids]
        eids = {e["id"] for e in edges}
        withdrawals = [w for w in rows("SELECT node, at, by, why FROM withdrawals ORDER BY rowid") if w["node"] in ids]
        retractions = [r for r in rows("SELECT edge, at, by, why FROM retractions ORDER BY rowid") if r["edge"] in eids]
        leases = [x for x in rows("SELECT id, node, agent, task, kind, at, expires, note FROM leases ORDER BY id")
                  if x["node"] in ids]
        events, redacted = [], 0
        for r in rows("SELECT seq, at, actor, kind, ref, payload, prev, hash FROM events ORDER BY seq"):
            p = json.loads(r["payload"])
            mine = not inv or _event_in(r["kind"], r["ref"], p, ids, eids)
            if mine:
                events.append({"seq": r["seq"], "hash": r["hash"],
                               "body": event_body(r["at"], r["actor"], r["kind"], r["ref"], p, r["prev"])})
            else:
                redacted += 1
                events.append({"seq": r["seq"], "hash": r["hash"], "prev": r["prev"], "redacted": True})
    title = next((json.loads(v["body"]).get("title") for v in versions if v["node"] == inv), "") if inv else ""
    out: dict[str, Any] = {
        "format": BUNDLE_FORMAT, "generator": f"hypgraph {__version__}",
        "exported_at": now(),
        "complete": redacted == 0, "redacted_events": redacted,
        "scope": {"inv": inv, "title": title} if inv else {"inv": "", "title": "whole graph"},
        "policy": g.policy.to_dict(), "head": events[-1]["hash"] if events else GENESIS,
        "events": events, "nodes": nodes, "versions": versions, "edges": edges,
        "withdrawals": withdrawals, "retractions": retractions, "leases": leases,
    }
    if derived:
        out["derived"] = derive_views(g, [inv] if inv else [n["id"] for n in nodes if n["type"] == "investigation"])
    return out


def _event_in(kind: str, ref: str, p: dict, ids: set, eids: set) -> bool:
    if kind in ("link", "retract"):
        return int(p.get("edge", -1)) in eids or (kind == "link" and ref in ids and p.get("dst") in ids)
    return ref in ids


def derive_views(g: "Graph", invs: list[str]) -> dict:
    """What a viewer needs without running the engine: standing of every node and the per-investigation views."""
    views = {"investigations": [i for i in g.investigations() if i["id"] in invs], "stats": g.stats(), "by_inv": {}}
    from . import profiles
    for i in invs:
        pid = str((g.get(i).get("body") or {}).get("profile") or "")
        views["by_inv"][i] = {"subgraph": g.subgraph(i), "work": g.work_map(i), "next": g.next_experiments(i, 20),
                              "report": g.report(i),
                              # the workflow views (hypgraph 0.6): a viewer shows each question's stage and gates,
                              # the board, the work orders and the profile's own words without the engine
                              "profile": profiles.view(pid), "stages": g.stages(i), "completion": g.completion(i),
                              "board": g.question_board(i), "orders": g.orders(i)}
    views["verify"] = g.verify()
    return views


def verify_bundle(b: dict) -> dict:
    """Check a bundle string-for-string: the chain, then every row against the event that wrote it."""
    if not isinstance(b, dict) or b.get("format") != BUNDLE_FORMAT:
        return {"ok": False, "problem": f"not a {BUNDLE_FORMAT} bundle"}
    prev, checked, red = GENESIS, 0, 0
    creates, revs, reviews, links, withdraws, retracts = {}, {}, {}, {}, set(), set()
    for ev in sorted(b.get("events") or [], key=lambda e: e["seq"]):
        if ev.get("redacted"):
            if ev.get("prev") != prev:
                return {"ok": False, "broken_at": ev["seq"], "problem": "chain broken (redacted event)"}
            prev, red = ev["hash"], red + 1
            continue
        if _sha(ev["body"]) != ev["hash"]:
            return {"ok": False, "broken_at": ev["seq"], "problem": "event body does not match its hash"}
        body = json.loads(ev["body"])
        if body.get("prev") != prev:
            return {"ok": False, "broken_at": ev["seq"], "problem": "chain broken (prev does not match)"}
        prev, checked = ev["hash"], checked + 1
        k, ref, p = body["kind"], body["ref"], body["payload"]
        if k == "create":
            creates[ref] = p
            revs[(ref, int(p.get("v", 1)))] = p.get("body_sha")
        elif k == "revise":
            revs[(ref, int(p.get("v")))] = p.get("body_sha")
        elif k == "review":
            reviews[p["review"]] = p
            revs[(p["review"], 1)] = p.get("body_sha")
        elif k == "link":
            links[int(p["edge"])] = p
        elif k == "withdraw":
            withdraws.add(ref)
        elif k == "retract":
            retracts.add(int(p["edge"]))
    if b.get("head") and b["head"] != prev:
        return {"ok": False, "problem": "the chain does not end at the bundle's head"}
    for n in b.get("nodes") or []:
        c = creates.get(n["id"])
        if n["type"] == "review":
            if n["id"] not in reviews:
                return {"ok": False, "problem": f"review {n['id']} has no event"}
        elif not c or (c.get("type"), c.get("code"), c.get("inv")) != (n["type"], n["code"], n["inv"]):
            return {"ok": False, "problem": f"node {n['id']} differs from its create event"}
    for v in b.get("versions") or []:
        want = revs.get((v["node"], v["v"]))
        if want is None:
            return {"ok": False, "problem": f"version {v['node']} v{v['v']} has no event"}
        if _sha(v["body"]) != want:
            return {"ok": False, "problem": f"version {v['node']} v{v['v']} differs from its event"}
    for e in b.get("edges") or []:
        want = links.get(e["id"])
        if want is None:
            return {"ok": False, "problem": f"edge {e['id']} has no event"}
        if (want.get("rel"), want.get("dst"), want.get("dst_v")) != (e["rel"], e["dst"], e["dst_v"]) or \
                _sha(e["data"]) != want.get("data_sha"):
            return {"ok": False, "problem": f"edge {e['id']} differs from its event"}
    for w in b.get("withdrawals") or []:
        if w["node"] not in withdraws:
            return {"ok": False, "problem": f"withdrawal of {w['node']} has no event"}
    for r in b.get("retractions") or []:
        if int(r["edge"]) not in retracts:
            return {"ok": False, "problem": f"retraction of edge {r['edge']} has no event"}
    out = {"ok": True, "checked": checked, "head": prev, "complete": red == 0, "redacted": red,
           "nodes": len(b.get("nodes") or []), "edges": len(b.get("edges") or [])}
    if red:
        out["warning"] = (f"{red} event(s) outside this investigation are redacted: their content can't be checked, so "
                          "a change hidden among them (a withdrawal, say) would not show. The full record rules that "
                          "out.")
    return out


def load(g: "Graph", b: dict) -> None:
    """Replay a complete bundle into an empty graph, row for row — the result verifies exactly as the original."""
    v = verify_bundle(b)
    if not v["ok"]:
        raise ValueError(f"bundle does not verify: {v['problem']}")
    if not v["complete"]:
        raise ValueError("a scoped bundle has redacted events and can't be replayed; view it, or ask for the full one")
    with g._lock:
        con = g._connect()
        if con.execute("SELECT COUNT(*) FROM events").fetchone()[0]:
            raise ValueError("load a bundle into an empty graph")
        con.execute("BEGIN IMMEDIATE")
        try:
            for n in b["nodes"]:
                con.execute("INSERT INTO nodes (id, type, code, inv, created_at, created_by) VALUES (?,?,?,?,?,?)",
                            (n["id"], n["type"], n["code"], n["inv"], n["created_at"], n["created_by"]))
            for x in b["versions"]:
                con.execute("INSERT INTO versions (node, v, at, by, reason, body) VALUES (?,?,?,?,?,?)",
                            (x["node"], x["v"], x["at"], x["by"], x["reason"], x["body"]))
            for e in b["edges"]:
                con.execute("INSERT INTO edges (id, src, src_v, rel, dst, dst_v, data, at, by, why) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)", (e["id"], e["src"], e["src_v"], e["rel"], e["dst"],
                                                             e["dst_v"], e["data"], e["at"], e["by"], e["why"]))
            for w in b["withdrawals"]:
                con.execute("INSERT INTO withdrawals (node, at, by, why) VALUES (?,?,?,?)",
                            (w["node"], w["at"], w["by"], w["why"]))
            for r in b["retractions"]:
                con.execute("INSERT INTO retractions (edge, at, by, why) VALUES (?,?,?,?)",
                            (r["edge"], r["at"], r["by"], r["why"]))
            for x in b["leases"]:
                con.execute("INSERT INTO leases (id, node, agent, task, kind, at, expires, note) "
                            "VALUES (?,?,?,?,?,?,?,?)", (x["id"], x["node"], x["agent"], x["task"], x["kind"],
                                                         x["at"], x["expires"], x["note"]))
            for ev in b["events"]:
                body = json.loads(ev["body"])
                con.execute("INSERT INTO events (seq, at, actor, kind, ref, payload, prev, hash) "
                            "VALUES (?,?,?,?,?,?,?,?)", (ev["seq"], body["at"], body["actor"], body["kind"],
                                                         body["ref"], json.dumps(body["payload"], sort_keys=True,
                                                                                 ensure_ascii=False,
                                                                                 separators=(",", ":")),
                                                         body["prev"], ev["hash"]))
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    g._invalidate()

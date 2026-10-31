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
     "derived":  {...},                                     # views for viewers: facts checked against the rows,
                                                            # standing not (verify_bundle(..., standing=True) re-derives)
     "telemetry": {"source", "covered_by_chain": false, "events": [...]}}   # optional: a swarm's telemetry sidecar

A scoped bundle (one investigation out of a shared graph) redacts the events outside it to {seq, hash, prev}: their
content can't be checked, so a change hidden among them (a withdrawal, say) would not show. ``verify_bundle`` says so
(``complete: false``). To publish a study, keep it in a graph of its own and export all of it.

``export(..., telemetry=path)`` adds a swarm's telemetry sidecar (HypSwarm writes ``<record>.telemetry.jsonl``): its
model and tool calls, work orders and scheduler decisions, so a viewer can replay the run. Telemetry is observation:
it is not part of the hash chain, ``verify_bundle`` doesn't look at it, and nothing derived from the record rests on
it. It is off unless asked for — a sidecar names the models, seats and spend of a run.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import __version__
from .store import GENESIS, ROW_TABLES, check_rows, event_body, now

if TYPE_CHECKING:
    from .graph import Graph

BUNDLE_FORMAT = "hypgraph/1-bundle"


def _sha(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def read_sidecar(path: str | os.PathLike, invs: set[str] | None = None) -> list[dict]:
    """Every complete JSON line of a telemetry sidecar; with ``invs``, those investigations' events (and any without
    one). Lines that aren't JSON objects — a torn last line, say — are skipped."""
    out: list[dict] = []
    with open(path, "rb") as f:
        for line in f.read().splitlines():
            try:
                e = json.loads(line)
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
            if isinstance(e, dict) and (invs is None or e.get("inv") in (None, "") or e.get("inv") in invs):
                out.append(e)
    return out


def export(g: "Graph", inv: str = "", *, derived: bool = True,
           telemetry: str | os.PathLike | list | None = None) -> dict:
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
    invs = [inv] if inv else [n["id"] for n in nodes if n["type"] == "investigation"]
    if derived:
        out["derived"] = derive_views(g, invs)
    if telemetry is not None:
        if isinstance(telemetry, (str, os.PathLike)):
            src, tel = Path(telemetry).name, read_sidecar(telemetry, set(invs))
        else:
            src, tel = "", [e for e in telemetry if isinstance(e, dict) and e.get("inv") in (None, "", *invs)]
        out["telemetry"] = {"source": src, "covered_by_chain": False, "events": tel}
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
    views["at"] = g.clock()          # the time standing was derived at (leases expire): re-deriving uses it
    return views


def anchored(res: dict, head: str) -> dict:
    """A verification held against a head published elsewhere (a paper, a signed tag, a release asset, a timestamp).
    A chain only shows it is consistent with itself: whoever can write the record can rewrite it and recompute every
    hash, or cut it short. Matching a head its holder can't change since rules both out. ``head`` is the full hash or a
    prefix of at least 16 hex characters."""
    want = str(head or "").strip().lower()
    if not want or not res.get("ok"):
        return res
    if len(want) < 16 or any(c not in "0123456789abcdef" for c in want):
        return {**res, "ok": False, "problem": "the anchor must be the head's hash, or at least its first 16 hex characters"}
    got = str(res.get("head") or "")
    if not got.startswith(want):
        return {**res, "ok": False, "anchored": False,
                "problem": f"the chain ends at {got[:16]}…, not at the anchored head {want[:16]}…: this is not the "
                           "record that was published (rewritten, cut short, or another record)"}
    return {**res, "anchored": True}


def verify_bundle(b: dict, head: str = "", *, standing: bool = False) -> dict:
    """Check a bundle string-for-string: the chain; then the rows against the events, both ways (every row written by
    an event, every event's row present, every recorded field equal); then the derived views against those rows. With
    ``head``, also that the chain ends at that published head (see ``anchored``). With ``standing``, re-derive the
    standing from the verified rows and compare it with what the bundle carries (``rederive``)."""
    res = anchored(_verify_bundle(b), head)
    if standing and res.get("ok"):
        res = {**res, "standing": rederive(b)}
        if res["standing"].get("problem"):
            res = {**res, "ok": False, "problem": res["standing"]["problem"]}
    return res


STANDING_NOTE = ("standing (review state, support, at-risk, the sentence) is what the exporting engine derived: the "
                 "chain doesn't cover it. Re-derive it from the verified rows with `hypgraph verify --standing`.")


def _verify_bundle(b: dict) -> dict:
    if not isinstance(b, dict) or b.get("format") != BUNDLE_FORMAT:
        return {"ok": False, "problem": f"not a {BUNDLE_FORMAT} bundle"}
    prev, checked, red, seqs = GENESIS, 0, 0, set()
    events: list[dict] = []
    for ev in sorted(b.get("events") or [], key=lambda e: e["seq"]):
        if ev["seq"] in seqs:
            return {"ok": False, "broken_at": ev["seq"], "problem": "two events share a sequence number"}
        seqs.add(ev["seq"])
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
        events.append(body)
    if b.get("head") and b["head"] != prev:
        return {"ok": False, "problem": "the chain does not end at the bundle's head"}
    tables = {t: b.get(t) or [] for t in ROW_TABLES}
    rows = check_rows(events, tables, importer=str((b.get("policy") or {}).get("importer") or "importer"))
    if "problem" in rows:
        return {"ok": False, "problem": rows["problem"]}
    problem = _derived_problem(b, tables)
    if problem:
        return {"ok": False, "problem": f"the derived views contradict the verified record: {problem}"}
    out = {"ok": True, "checked": checked, "head": prev, "complete": red == 0, "redacted": red,
           "nodes": len(tables["nodes"]), "edges": len(tables["edges"]), "unchecked": rows["unchecked"],
           "standing": {"checked": False, "note": STANDING_NOTE}}
    if red:
        out["warning"] = (f"{red} event(s) outside this investigation are redacted: their content can't be checked, so "
                          "a change hidden among them (a withdrawal, say) would not show. The full record rules that "
                          "out.")
    return out


def _j(v: Any) -> str:
    """A value in a problem, written as the browser's verifier writes it (JSON.stringify)."""
    return json.dumps(v, ensure_ascii=False, separators=(",", ":"))


def _title(body: dict) -> str:
    """A node's title as the engine shows it (Graph.brief)."""
    t = (body.get("statement") or body.get("title") or body.get("text") or body.get("aim") or body.get("summary")
         or body.get("choice") or body.get("citation") or body.get("name") or body.get("path") or body.get("verdict")
         or "")
    return str(t)[:300]


def _derived_problem(b: dict, tables: dict) -> str:
    """The derived views are presentation, but a viewer shows them beside a verified chain: every fact in them that
    the rows fix — which nodes and live links each investigation has, each node's type, code, author, time, version,
    title and whether it is withdrawn — must agree with the verified rows. Standing can't be checked this way."""
    d = b.get("derived")
    if d is None:
        return ""
    if not isinstance(d, dict):
        return "derived is not an object"
    nodes = {n["id"]: n for n in tables["nodes"]}
    latest: dict[str, tuple[int, dict]] = {}
    for v in tables["versions"]:
        if v["v"] > latest.get(v["node"], (0, {}))[0]:
            latest[v["node"]] = (v["v"], json.loads(v["body"]))
    withdrawn = {w["node"] for w in tables["withdrawals"]}
    retracted = {int(r["edge"]) for r in tables["retractions"]}
    live = {int(e["id"]): e for e in tables["edges"] if int(e["id"]) not in retracted}
    scope = str((b.get("scope") or {}).get("inv") or "")
    invs = {scope} if scope else {i for i, n in nodes.items() if n["type"] == "investigation"}

    def facts(x: dict, where: str) -> str:
        n = nodes.get(x.get("id")) if isinstance(x, dict) else None
        if not n:
            return f"{where} shows {x.get('id') if isinstance(x, dict) else _j(x)}, which the record doesn't hold"
        v, body = latest.get(n["id"], (0, {}))
        want = {"type": n["type"], "code": n["code"], "inv": n["inv"], "by": n["created_by"], "at": n["created_at"],
                "v": v, "title": _title(body), "kind": body.get("kind") or body.get("verdict") or ""}
        for k, w in want.items():
            if k in x and x[k] != w:
                return f"{where} shows {n['code'] or n['id']} with {k} {_j(x[k])}; the record has {_j(w)}"
        life = (x.get("state") or {}).get("lifecycle")
        if life is not None and (life == "withdrawn") != (n["id"] in withdrawn):
            return (f"{where} shows {n['code'] or n['id']} as {life}; the record "
                    f"{'withdrew it' if n['id'] in withdrawn else 'has no withdrawal of it'}")
        return ""
    by_inv = d.get("by_inv") or {}
    if set(by_inv) != invs:
        return "the views don't cover the record's investigations"
    for x in d.get("investigations") or []:
        if x.get("id") not in invs:
            return f"the investigation list shows {x.get('id')}, which isn't in the bundle's scope"
        p = facts(x, "the investigation list")
        if p:
            return p
    for inv, v in by_inv.items():
        sg = (v or {}).get("subgraph") or {}
        shown = sg.get("nodes") or []
        for x in shown:
            p = facts(x, f"the graph of {nodes[inv]['code'] or inv}")
            if p:
                return p
        mine = {i for i, n in nodes.items() if n["inv"] == inv or i == inv}
        ids = [x["id"] for x in shown]
        if len(ids) != len(set(ids)) or (set(ids) != mine and not (len(mine) > len(ids) >= 5000)):
            return f"the graph of {nodes[inv]['code'] or inv} doesn't show the nodes the record holds"
        want = {i: e for i, e in live.items() if e["src"] in set(ids) and e["dst"] in set(ids)}
        got = sg.get("edges") or []
        if len(got) != len(want) or {int(e["id"]) for e in got} != set(want):
            return f"the graph of {nodes[inv]['code'] or inv} doesn't show the live links the record holds"
        for e in got:
            r = want[int(e["id"])]
            for k in ("src", "src_v", "rel", "dst", "dst_v", "at", "by", "why"):
                if k in e and e[k] != r[k]:
                    return f"the graph shows link {e['id']} with {k} {_j(e[k])}; the record has {_j(r[k])}"
            if "data" in e and e["data"] != json.loads(r["data"]):      # as values: 1.0 and 1 are one number
                return f"the graph shows link {e['id']} with other data than the record"
    return ""


def rederive(b: dict) -> dict:
    """Replay a complete bundle in memory and derive the standing again, at the time it was derived, with this
    engine: {"checked": True} when it matches what the bundle carries, a "problem" when it doesn't. Standing rules
    change between releases, so only a bundle exported by this version can be compared; others are reported as not
    checked."""
    from .graph import Graph
    from .policy import Policy
    d = b.get("derived")
    if not isinstance(d, dict):
        return {"checked": False, "note": "the bundle carries no derived views"}
    if b.get("generator") != f"hypgraph {__version__}":
        return {"checked": False, "note": f"exported by {b.get('generator') or 'an unknown version'}; standing rules "
                                          f"differ between releases, so re-derive it with that version"}
    if b.get("redacted_events") or any(e.get("redacted") for e in b.get("events") or []):
        return {"checked": False, "note": "a scoped bundle can't be replayed; re-derive from the full record"}
    at = str(d.get("at") or b.get("exported_at") or now())
    g = Graph(None, policy=Policy.from_dict(b.get("policy") or {}), clock=lambda: at)
    load(g, b)
    fresh = json.loads(json.dumps(derive_views(g, list(d.get("by_inv") or {})), sort_keys=True))
    old = json.loads(json.dumps(d, sort_keys=True))
    for k in ("investigations", "by_inv"):
        if fresh.get(k) != old.get(k):
            where = k
            if k == "by_inv":
                where = next((f"{i}/{view}" for i in old.get(k) or {} for view in (old[k][i] or {})
                              if (fresh[k].get(i) or {}).get(view) != old[k][i][view]), k)
            return {"checked": False, "problem": f"the standing the bundle carries differs from what its record "
                                                 f"derives ({where})"}
    return {"checked": True}


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

"""
Storage: one SQLite file, every table append-only (triggers refuse UPDATE and DELETE), every write an event in a
SHA-256 hash chain. ``verify()`` recomputes the chain and checks the rows against the events both ways
(``check_rows``): every row written by an event and equal to it field by field, every row an event wrote present. An
edit, insert or delete made to the file outside the library — even one that drops the triggers first — shows up.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS nodes (id TEXT PRIMARY KEY, type TEXT NOT NULL, code TEXT NOT NULL DEFAULT '',
        inv TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, created_by TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS versions (node TEXT NOT NULL, v INTEGER NOT NULL, at TEXT NOT NULL,
        by TEXT NOT NULL, reason TEXT NOT NULL DEFAULT '', body TEXT NOT NULL, PRIMARY KEY (node, v))""",
    """CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY AUTOINCREMENT, src TEXT NOT NULL, src_v INTEGER,
        rel TEXT NOT NULL, dst TEXT NOT NULL, dst_v INTEGER, data TEXT NOT NULL DEFAULT '{}', at TEXT NOT NULL,
        by TEXT NOT NULL, why TEXT NOT NULL DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS retractions (edge INTEGER PRIMARY KEY, at TEXT NOT NULL, by TEXT NOT NULL,
        why TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS withdrawals (node TEXT PRIMARY KEY, at TEXT NOT NULL, by TEXT NOT NULL,
        why TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS leases (id INTEGER PRIMARY KEY AUTOINCREMENT, node TEXT NOT NULL, agent TEXT NOT NULL,
        task TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL, at TEXT NOT NULL, expires TEXT NOT NULL DEFAULT '',
        note TEXT NOT NULL DEFAULT '')""",
    """CREATE TABLE IF NOT EXISTS events (seq INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL,
        kind TEXT NOT NULL, ref TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL DEFAULT '{}', prev TEXT NOT NULL,
        hash TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_nodes_inv ON nodes(inv)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_inv_type ON nodes(inv, type)",
    "CREATE INDEX IF NOT EXISTS idx_nodes_inv_code ON nodes(inv, code)",
    "CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor, kind, at)",
    "CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src)",
    "CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst)",
    "CREATE INDEX IF NOT EXISTS idx_leases_node ON leases(node, id)",
]
APPEND_ONLY = ("nodes", "versions", "edges", "retractions", "withdrawals", "leases", "events")
GENESIS = "0" * 64


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canon(obj: Any) -> str:
    """The canonical JSON every hash is taken over: sorted keys, no spaces, UTF-8 kept as is."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def event_body(at: str, actor: str, kind: str, ref: str, payload: dict, prev: str) -> str:
    """The exact string an event's hash is over."""
    return canon({"at": at, "actor": actor, "kind": kind, "ref": ref, "payload": payload, "prev": prev})


class Conn(sqlite3.Connection):
    """A connection kept open per thread (opening a file on a slow host mount costs ~0.2 s). close() is a no-op;
    really_close() closes it."""
    def close(self) -> None:  # noqa: D401
        pass

    def really_close(self) -> None:
        super().close()


def install(con: sqlite3.Connection, *, journal: str = "DELETE") -> None:
    """Create the tables and the append-only triggers. A rollback journal by default: WAL's shared-memory file isn't
    reliable on network and VM host mounts, where research data often lives."""
    try:
        con.execute(f"PRAGMA journal_mode={journal}")
    except sqlite3.OperationalError:
        pass
    for stmt in SCHEMA:
        con.execute(stmt)
    for t in APPEND_ONLY:
        for op in ("UPDATE", "DELETE"):
            con.execute(f"CREATE TRIGGER IF NOT EXISTS {t}_no_{op.lower()} BEFORE {op} ON {t} "
                        f"BEGIN SELECT RAISE(ABORT, '{t} is append-only'); END")


def append_event(con: sqlite3.Connection, actor: str, kind: str, ref: str, payload: dict, at: str) -> int:
    row = con.execute("SELECT hash FROM events ORDER BY seq DESC LIMIT 1").fetchone()
    prev = row[0] if row else GENESIS
    h = sha(event_body(at, actor, kind, ref, payload, prev))
    cur = con.execute("INSERT INTO events (at, actor, kind, ref, payload, prev, hash) VALUES (?,?,?,?,?,?,?)",
                      (at, actor, kind, ref, canon(payload), prev, h))
    return cur.lastrowid


ROW_TABLES = ("nodes", "versions", "edges", "withdrawals", "retractions", "leases")
COLUMNS = {
    "nodes": ("id", "type", "code", "inv", "created_at", "created_by"),
    "versions": ("node", "v", "at", "by", "reason", "body"),
    "edges": ("id", "src", "src_v", "rel", "dst", "dst_v", "data", "at", "by", "why"),
    "withdrawals": ("node", "at", "by", "why"),
    "retractions": ("edge", "at", "by", "why"),
    "leases": ("id", "node", "agent", "task", "kind", "at", "expires", "note"),
}


def _expect(events: list[dict], importer: str) -> tuple[dict, list, dict, str]:
    """What the tables must hold, read from the events alone: {table: {key: [(field, how, value)]}}, the leases in
    order, the fields no event recorded (rows written before this release), and the first problem in the events.

    ``how`` is "eq" (the row's value), "sha" (SHA-256 of the row's string), "head" (the row's string starts with the
    value: an event that kept the first 300 characters of a longer text) or "who" (an author, see below)."""
    want: dict[str, dict] = {t: {} for t in ROW_TABLES}
    leases: list = []
    unchecked: dict[str, int] = {}

    def put(table: str, key, checks: list) -> str:
        if key in want[table]:
            return f"two events write {_label(table, key)}"
        want[table][key] = checks
        return ""

    def who(actor: str, p: dict, strict: bool) -> tuple:
        # who a row is shown as by: the event's actor, unless the importer credits the original author ("as")
        if "as" in p:
            return ("eq", p["as"]) if actor == importer else ("bad", f"only the {importer} credits another author")
        if strict or actor != importer:
            return ("eq", actor)
        return ("any", "nodes.created_by")      # an importer's write from before "as" was recorded
    for ev in events:
        k, ref, p, at, actor = ev["kind"], ev["ref"], ev["payload"], ev["at"], ev["actor"]
        problem = ""
        if k == "create":
            strict = "reason_sha" in p
            problem = put("nodes", ref, [("type", "eq", p.get("type")), ("code", "eq", p.get("code")),
                                         ("inv", "eq", p.get("inv")), ("created_at", "eq", at),
                                         ("created_by",) + who(actor, p, strict)]) or \
                put("versions", (ref, int(p.get("v", 1))), [("at", "eq", at), ("by", "eq", actor),
                                                            ("body", "sha", p.get("body_sha")),
                                                            ("reason", "sha", p["reason_sha"]) if strict
                                                            else ("reason", "unchecked", "versions.reason")])
        elif k == "revise":
            problem = put("versions", (ref, int(p.get("v"))), [
                ("at", "eq", at), ("by", "eq", actor), ("body", "sha", p.get("body_sha")),
                ("reason", "sha", p["reason_sha"]) if "reason_sha" in p else ("reason", "head", str(p.get("reason", "")))])
        elif k == "review":
            strict = "code" in p
            problem = put("nodes", p["review"], [("type", "eq", "review"), ("created_at", "eq", at),
                                                 ("code", "eq", p["code"]) if strict
                                                 else ("code", "unchecked", "nodes.code"),
                                                 ("inv", "eq", p["inv"]) if strict else ("inv", "inv_of", ref),
                                                 ("created_by",) + who(actor, p, strict)]) or \
                put("versions", (p["review"], 1), [("at", "eq", at), ("by", "eq", actor), ("reason", "eq", ""),
                                                   ("body", "sha", p.get("body_sha"))])
        elif k == "link":
            checks = [("src", "eq", ref), ("rel", "eq", p.get("rel")), ("dst", "eq", p.get("dst")),
                      ("dst_v", "eq", p.get("dst_v")), ("data", "sha", p.get("data_sha")), ("at", "eq", at),
                      ("by", "eq", actor)]
            checks.append(("src_v", "eq", p["src_v"]) if "src_v" in p else ("src_v", "unchecked", "edges.src_v"))
            checks.append(("why", "sha", p["why_sha"]) if "why_sha" in p else ("why", "unchecked", "edges.why"))
            problem = put("edges", int(p["edge"]), checks)
        elif k == "withdraw":
            strict = "why_sha" in p
            problem = put("withdrawals", ref, [("at", "eq", at), ("by",) + who(actor, p, strict),
                                               ("why", "sha", p["why_sha"]) if strict
                                               else ("why", "head", str(p.get("why", "")))])
        elif k == "retract":
            problem = put("retractions", int(p["edge"]), [
                ("at", "eq", at), ("by", "eq", actor),
                ("why", "sha", p["why_sha"]) if "why_sha" in p else ("why", "unchecked", "retractions.why")])
        elif k in ("lease_take", "lease_release"):
            note = (("note", "sha", p["note_sha"]) if "note_sha" in p else
                    ("note", "eq", str(p["note"])[:300]) if "note" in p else ("note", "unchecked", "leases.note"))
            leases.append([("node", "eq", ref), ("agent", "eq", p.get("for") or actor), ("task", "eq", p.get("task")),
                           ("kind", "eq", k[6:]), ("at", "eq", at), ("expires", "eq", p.get("expires", "")), note])
        if problem:
            return want, leases, unchecked, problem
    return want, leases, unchecked, ""


def _mismatch(row: dict, checks: list, nodes: dict, unchecked: dict) -> str:
    for field, how, *val in checks:
        got = row.get(field)
        v = val[0] if val else None
        if how == "eq":
            ok = got == v
        elif how == "sha":
            ok = isinstance(got, str) and sha(got) == v
        elif how == "head":
            ok = isinstance(got, str) and got[:300] == v
        elif how == "inv_of":
            ok = got == (nodes.get(v) or {}).get("inv")
        elif how == "bad":
            return v
        else:                                     # "unchecked" / "any": no event recorded it
            if got not in (None, ""):
                unchecked[v] = unchecked.get(v, 0) + 1
            ok = True
        if not ok:
            return field
    return ""


def _label(table: str, key) -> str:
    """A row as a person names it: "version n1 v2", "link 7", "withdrawal of n1"."""
    if table == "versions":
        return f"version {key[0]} v{key[1]}"
    return {"nodes": "node {}", "edges": "link {}", "withdrawals": "withdrawal of {}",
            "retractions": "retraction of link {}"}[table].format(key)


def check_rows(events: list[dict], tables: dict[str, list[dict]], *, importer: str = "importer") -> dict:
    """Both directions, for every table: each row must be written by an event, each event's row must be there, once,
    and every field the event recorded must match. ``events`` are the checked events in order ({at, actor, kind, ref,
    payload}); in a scoped bundle, only the ones it shows — their rows are all in scope, so the check is complete for
    what the bundle shows. Returns {"problem"} or {"unchecked": {table.field: rows}}: fields of rows written before
    this release that no event recorded (a link's why, a retraction's why, a create's reason, a lease's note)."""
    want, leases, unchecked, problem = _expect(events, importer)
    if problem:
        return {"problem": problem}
    keys = {"nodes": lambda r: r["id"], "versions": lambda r: (r["node"], int(r["v"])), "edges": lambda r: int(r["id"]),
            "withdrawals": lambda r: r["node"], "retractions": lambda r: int(r["edge"])}
    have: dict[str, dict] = {}
    for t, key in keys.items():
        have[t] = {}
        for r in tables.get(t) or []:
            k = key(r)
            if k in have[t]:
                return {"problem": f"{_label(t, k)} appears twice"}
            have[t][k] = r
    # a review written before this release names its target, not its investigation: the target's, from its event
    expected_nodes = {k: {"inv": v[0]} for k, c in want["nodes"].items() for f, how, *v in c if f == "inv" and how == "eq"}
    for t in keys:
        for k, r in have[t].items():
            if k not in want[t]:
                return {"problem": f"{_label(t, k)} has no event"}
            bad = _mismatch(r, want[t][k], expected_nodes, unchecked)
            if bad:
                return {"problem": f"{_label(t, k)} differs from its event ({bad})"}
        missing = [k for k in want[t] if k not in have[t]]
        if missing:
            return {"problem": f"{_label(t, missing[0])} is missing: its event says it was written"}
    rows = sorted(tables.get("leases") or [], key=lambda r: int(r["id"]))
    if len({int(r["id"]) for r in rows}) != len(rows):
        return {"problem": "a lease id appears twice"}
    if len(rows) != len(leases):
        return {"problem": f"{len(rows)} lease rows for {len(leases)} lease events"}
    for r, checks in zip(rows, leases):
        bad = _mismatch(r, checks, expected_nodes, unchecked)
        if bad:
            return {"problem": f"lease {r['id']} differs from its event ({bad})"}
    return {"unchecked": unchecked}


def verify_connection(con: sqlite3.Connection, importer: str = "importer") -> dict:
    """Recompute every event hash, then check the tables against what the events recorded, both ways (check_rows):
    every row written by an event, every event's row present, every recorded field equal — so an edit made to the file
    outside the library, even one that drops the triggers first, shows up."""
    prev, n = GENESIS, 0
    events: list[dict] = []
    for r in con.execute("SELECT seq, at, actor, kind, ref, payload, prev, hash FROM events ORDER BY seq"):
        seq, at, actor, kind, ref, payload_s, prev_s, h = r
        payload = json.loads(payload_s)
        if prev_s != prev or sha(event_body(at, actor, kind, ref, payload, prev)) != h:
            return {"ok": False, "broken_at": seq, "checked": n, "problem": "event hash chain broken"}
        prev, n = h, n + 1
        events.append({"at": at, "actor": actor, "kind": kind, "ref": ref, "payload": payload})
    tables = {}
    for t in ROW_TABLES:
        cur = con.execute(f"SELECT {', '.join(COLUMNS[t])} FROM {t}")
        tables[t] = [dict(zip(COLUMNS[t], r)) for r in cur.fetchall()]
    res = check_rows(events, tables, importer=importer)
    if "problem" in res:
        return {"ok": False, "checked": n, "problem": res["problem"]}
    return {"ok": True, "checked": n, "head": prev, "unchecked": res["unchecked"]}


def verify_file(path: str, importer: str = "importer") -> dict:
    """Verify a graph file read-only (a backup, a copy someone sent you) without opening it for writing. ``importer``
    is the policy's importer name, the one author allowed to credit another (the default policy's)."""
    from pathlib import Path
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return verify_connection(con, importer)
    finally:
        con.close()

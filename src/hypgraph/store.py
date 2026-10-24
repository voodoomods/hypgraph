"""
Storage: one SQLite file, every table append-only (triggers refuse UPDATE and DELETE), every write an event in a
SHA-256 hash chain. ``verify()`` recomputes the chain and checks each stored version body and edge against the event
that wrote it, so an edit made to the file outside the library — even one that drops the triggers first — shows up.
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


def verify_connection(con: sqlite3.Connection) -> dict:
    """Recompute every event hash, then check stored content against what the events recorded: each version body
    against its create / revise / review event's body_sha, each edge against its link event, and that no row exists
    without its event."""
    prev, n = GENESIS, 0
    bodies: dict[tuple, str] = {}
    links: dict[int, dict] = {}
    for r in con.execute("SELECT seq, at, actor, kind, ref, payload, prev, hash FROM events ORDER BY seq"):
        seq, at, actor, kind, ref, payload_s, prev_s, h = r
        payload = json.loads(payload_s)
        if prev_s != prev or sha(event_body(at, actor, kind, ref, payload, prev)) != h:
            return {"ok": False, "broken_at": seq, "checked": n, "problem": "event hash chain broken"}
        prev, n = h, n + 1
        if kind in ("create", "revise"):
            bodies[(ref, int(payload.get("v", 1)))] = payload.get("body_sha", "")
        elif kind == "review":
            bodies[(payload["review"], 1)] = payload.get("body_sha", "")
        elif kind == "link":
            links[int(payload["edge"])] = payload
    for node, v, body in con.execute("SELECT node, v, body FROM versions"):
        want = bodies.get((node, v))
        if want is None:
            return {"ok": False, "checked": n, "problem": f"version {node} v{v} has no event"}
        if sha(body) != want:
            return {"ok": False, "checked": n, "problem": f"version {node} v{v} differs from its event"}
    for eid, rel, dst, dst_v, data in con.execute("SELECT id, rel, dst, dst_v, data FROM edges"):
        want = links.get(eid)
        if want is None:
            return {"ok": False, "checked": n, "problem": f"edge {eid} has no event"}
        if (want.get("rel"), want.get("dst"), want.get("dst_v")) != (rel, dst, dst_v) or \
                sha(data) != want.get("data_sha"):
            return {"ok": False, "checked": n, "problem": f"edge {eid} differs from its event"}
    return {"ok": True, "checked": n, "head": prev}


def verify_file(path: str) -> dict:
    """Verify a graph file read-only (a backup, a copy someone sent you) without opening it for writing."""
    from pathlib import Path
    con = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)
    try:
        return verify_connection(con)
    finally:
        con.close()

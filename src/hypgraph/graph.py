"""
The Graph: one research record in one SQLite file (or in memory).

    from hypgraph import Graph, Policy
    g = Graph("study.hypgraph", policy=Policy(reviewers={"ada"}))
    inv = g.create(author="me", type="investigation", fields={"title": "…", "objective": "…"})["id"]

Writes add rows and events and never change one; reads come from an in-memory snapshot that loads only rows newer
than the last read (every table is append-only), so a read after a write costs milliseconds. Status is derived on
every read (derive.py) and claims are checked on every write (checks.py).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import sqlite3
import sys
import threading
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from . import profiles
from . import derive as D
from . import refusals, store
from .checks import claim_issues
from .policy import Policy
from .schema import REPLICATION, RELS, SAME_TYPE, SYNONYMS, TYPES, VERDICTS
from .store import canon, now


class GraphError(ValueError):
    """A write the graph refuses — the message says what to fix. A refused claim also carries ``problems``: one dict
    per rule it broke, with a stable ``code``, the ``message``, a ``fix`` and the offending ``words``."""

    def __init__(self, message: str, problems: list | None = None):
        super().__init__(message)
        self.problems = problems or []


SpendFn = Callable[..., dict]


def clean_body(ntype: str, body: dict, *, partial_ok: bool = False) -> dict:
    """Validate and normalise a node's fields against its type (schema.TYPES)."""
    spec = TYPES[ntype]["fields"]
    if not isinstance(body, dict):
        raise GraphError("fields must be an object")
    unknown = sorted(set(body) - set(spec))
    if unknown:
        raise GraphError(f"{ntype} has no field(s) {unknown}; fields: {', '.join(spec)}")
    out = {}
    for k, (kind, n, req) in spec.items():
        v = body.get(k)
        if v in (None, "", [], {}):
            if req and not partial_ok:
                raise GraphError(f"{ntype} needs {k}")
            continue
        if kind in ("str", "text"):
            v = str(v).strip()
            if len(v) > n:
                raise GraphError(f"{k} is longer than {n} characters")
            if req and len(v) < (3 if kind == "str" else 10):
                raise GraphError(f"{k}: say it in a full sentence")
        elif kind.startswith("enum:"):
            v = SYNONYMS.get((ntype, k), {}).get(str(v).strip().lower().replace(" ", "_").replace("-", "_"), str(v).strip())
            if str(v) not in kind[5:].split("|"):
                raise GraphError(f"{k} must be one of {kind[5:].replace('|', ', ')}")
            v = str(v)
        elif kind == "list":
            if isinstance(v, str):
                v = [v]
            if not isinstance(v, list) or len(v) > n:
                raise GraphError(f"{k} must be a list of at most {n} items")
        elif kind == "dict":
            if not isinstance(v, dict) or len(canon(v)) > n:
                raise GraphError(f"{k} must be an object (at most {n} characters)")
        elif kind == "bool":
            v = bool(v)
        elif kind == "num":
            v = float(v)
            if not math.isfinite(v):
                raise GraphError(f"{k} must be a finite number")
        elif kind == "any":
            if len(canon(v)) > n:
                raise GraphError(f"{k} is too long")
        out[k] = v
    return out


class _Writer(threading.local):
    task = ""


class writing_for:
    """``with g.writing_for(task_id):`` — every event written inside carries ``task`` in its payload, so the work
    behind a node can be traced to the task (and its cost) that made it."""
    def __init__(self, graph: "Graph", task: str | None):
        self.graph = graph
        self.task = re.sub(r"[^A-Za-z0-9:_.\-]", "", str(task or ""))[:80]

    def __enter__(self):
        self.prev, self.graph._writer.task = self.graph._writer.task, self.task
        return self

    def __exit__(self, *exc):
        self.graph._writer.task = self.prev


class Graph:
    """A research record. ``path`` is a SQLite file (created if missing); None or ":memory:" keeps it in memory.

    ``policy`` says who reviews and who the trusted authors are (policy.Policy). ``spend`` is an optional hook
    ``spend(inv, tasks, since=None) -> {usd, calls, input_tokens, cached_tokens, output_tokens, by_task: [...],
    ...}`` that cost() uses to price the work behind an investigation; without it, cost() reports no money.
    ``clock`` returns the ISO time stamped on each write (default: now, UTC) — a host may inject its own; callers
    can't pass a time, except the importer bringing in a legacy record with its original dates."""

    def __init__(self, path: str | os.PathLike | None = None, *, policy: Policy | None = None,
                 spend: SpendFn | None = None, clock: Callable[[], str] | None = None):
        self.policy = policy or Policy()
        self.clock = clock or now
        self.spend = spend
        self.memory = path in (None, ":memory:", "")
        self.path = ":memory:" if self.memory else str(path)
        self._lock = threading.RLock()
        self._snap_lock = self._lock if self.memory else threading.Lock()
        self._local = threading.local()
        self._writer = _Writer()
        self._snap: Optional[D.Snap] = None
        self._verified: dict = {"sig": None, "result": None}
        self._mem: Optional[store.Conn] = None
        self._opened: list = []
        with self._lock:
            con = self._connect()
            store.install(con)
            refusals.install(con)

    # ── connections ─────────────────────────────────────────────────
    def _connect(self) -> sqlite3.Connection:
        if self.memory:
            if self._mem is None:
                self._mem = sqlite3.connect(":memory:", isolation_level=None, check_same_thread=False,
                                            factory=store.Conn)
            return self._mem
        con = getattr(self._local, "con", None)
        if con is not None:
            return con
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False,
                              factory=store.Conn)
        self._local.con = con
        self._opened.append(con)
        return con

    def close(self) -> None:
        """Close every connection this Graph opened (any thread)."""
        for c in self._opened:
            try:
                c.really_close()
            except sqlite3.Error:
                pass
        self._opened.clear()
        self._local = threading.local()
        if self._mem is not None:
            self._mem.really_close()
            self._mem = None
        self._snap = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def __repr__(self) -> str:
        return f"Graph({self.path!r})"

    def writing_for(self, task: str | None) -> writing_for:
        return writing_for(self, task)

    def author(self, name: str) -> "Author":
        """A handle that writes as ``name`` — convenient in notebooks and scripts."""
        return Author(self, name)

    # ── the event chain ─────────────────────────────────────────────
    def _event(self, con, actor: str, kind: str, ref: str, payload: dict, at: str) -> int:
        task = self._writer.task
        if task and "task" not in payload:
            payload = {**payload, "task": task}
        return store.append_event(con, actor, kind, ref, payload, at)

    def verify(self, path: str = "") -> dict:
        """Recompute the hash chain and check every stored body and edge against its event. ``path``: check another
        copy read-only (a backup) instead."""
        if path:
            return store.verify_file(path)
        with self._snap_lock:
            return store.verify_connection(self._connect())

    def verify_chain(self) -> dict:
        """verify(), cached until the record changes."""
        sig = self._sig()
        if self._verified["sig"] == sig and self._verified["result"] is not None:
            return self._verified["result"]
        res = self.verify()
        self._verified.update(sig=self._sig(), result=res)
        return res

    # ── the snapshot ────────────────────────────────────────────────
    def _sig(self) -> tuple:
        """What changes with every commit. For a file: size, mtime and SQLite's own change counter (header bytes
        24-27) — mtime alone can miss a commit on a coarse-clock filesystem — read without a SQLite query, which on
        a host mount costs lock traffic. In memory: the head of the event log (every write adds an event)."""
        if self.memory:
            with self._lock:
                r = self._connect().execute("SELECT MAX(seq) FROM events").fetchone()
            return ("mem", int(r[0] or 0))
        try:
            st = os.stat(self.path)
            with open(self.path, "rb") as f:
                f.seek(24)
                counter = f.read(4)
            return (st.st_size, st.st_mtime_ns, counter)
        except OSError:
            return (0, 0, b"")

    def snapshot(self) -> D.Snap:
        """The whole graph at its latest event. Reads never touch the database unless something was written since;
        then only the new rows are loaded (or, after a retraction, everything)."""
        sig = self._sig()
        s = self._snap
        if s is not None and s.sig == sig:
            t = self.clock()
            if any(v["expires"] <= t for v in s.leases.values()):          # leases expire without a write
                s.leases = {k: v for k, v in s.leases.items() if v["expires"] > t}
                s._state.clear()
            if t[:10] != (s.now or "")[:10]:                                # a day turned: freshness may have changed
                s._state.clear()
            s.now = t
            return s
        with self._snap_lock:
            if self._snap is not None and self._snap.sig == sig:
                self._snap.now = self.clock()
                return self._snap
            con = self._connect()
            snap = self._delta(con, self._snap) if self._snap is not None else None
            if snap is None:
                snap = self._rebuild(con)
            snap.sig = sig
            snap.now = self.clock()
            self._snap = snap
            return snap

    def _head_seq(self, con) -> int:
        r = con.execute("SELECT MAX(seq) FROM events").fetchone()
        return int(r[0] or 0)

    def _rebuild(self, con) -> D.Snap:
        s = D.Snap(0, self.policy)
        retracted = {r[0] for r in con.execute("SELECT edge FROM retractions")}
        self._load_rows(con, s, retracted)
        s.seq = max(self._head_seq(con), s.seq)
        return s

    def _load_rows(self, con, s: D.Snap, retracted: set, *, shared: bool = False) -> set:
        """Add every row newer than s.marks to s (all of it for a fresh Snap) and return the ids of the nodes those
        rows touched. ``shared``: s's per-node lists still belong to an older snapshot too, so a list is copied the
        first time this load appends to it (readers of the old snapshot never see it change) and appended to after."""
        touched: set = set()
        owned: set = set()

        def push(table: dict, key: str, item) -> None:
            if shared and (id(table), key) not in owned:
                table[key] = list(table.get(key, ())) + [item]
                owned.add((id(table), key))
            else:
                table[key].append(item)

        con.row_factory = sqlite3.Row
        try:
            m = s.marks
            for r in con.execute("SELECT rowid AS _r, * FROM nodes WHERE rowid > ? ORDER BY rowid", (m["nodes"],)):
                row = dict(r)
                m["nodes"] = max(m["nodes"], row.pop("_r"))
                s.nodes[row["id"]] = row | {"v": 0, "body": {}}
                touched.add(row["id"])
            for r in con.execute("SELECT rowid AS _r, node, v, at, by, reason, body FROM versions WHERE rowid > ? "
                                 "ORDER BY node, v", (m["versions"],)):
                row = dict(r)
                m["versions"] = max(m["versions"], row.pop("_r"))
                row["body"] = json.loads(row["body"])
                push(s.versions, row["node"], row)
                touched.add(row["node"])
                n = s.nodes.get(row["node"])
                if n and row["v"] >= n["v"]:
                    s.nodes[row["node"]] = n | {"v": row["v"], "body": row["body"], "revised_at": row["at"],
                                                "revised_by": row["by"]}
            s.events.extend(dict(r) | {"payload": json.loads(r["payload"])} for r in
                            con.execute("SELECT seq, at, actor, kind, ref, payload FROM events WHERE seq > ? "
                                        "ORDER BY seq", (s.seq,)))
            if s.events:
                s.seq = s.events[-1]["seq"]
            for r in con.execute("SELECT * FROM edges WHERE id > ? ORDER BY id", (m["edges"],)):
                e = dict(r) | {"data": json.loads(r["data"] or "{}")}
                m["edges"] = max(m["edges"], e["id"])
                if e["id"] in retracted or e["src"] not in s.nodes or e["dst"] not in s.nodes:
                    continue
                s.edges[e["id"]] = e
                push(s.out, e["src"], e)
                push(s.inn, e["dst"], e)
                touched.update((e["src"], e["dst"]))
            for r in con.execute("SELECT rowid AS _r, * FROM withdrawals WHERE rowid > ?", (m["withdrawals"],)):
                row = dict(r)
                m["withdrawals"] = max(m["withdrawals"], row.pop("_r"))
                s.withdrawn[row["node"]] = row
                touched.add(row["node"])
            t = self.clock()
            for r in con.execute("SELECT * FROM leases WHERE id > ? ORDER BY id", (m["leases"],)):
                m["leases"] = max(m["leases"], r["id"])
                touched.add(r["node"])
                if r["kind"] == "take":
                    s.leases[r["node"]] = dict(r)
                elif r["kind"] == "release" and s.leases.get(r["node"], {}).get("agent") == r["agent"]:
                    s.leases.pop(r["node"], None)
            s.leases = {k: v for k, v in s.leases.items() if v["expires"] > t}
        finally:
            con.row_factory = None
        return touched

    def _delta(self, con, old: D.Snap) -> Optional[D.Snap]:
        """The old snapshot plus what was written since. Readers holding the old one never see it change: the tables
        are shallow copies (C speed), and a per-node list is copied only when this load appends to it — a write
        costs what it touched, not the size of the graph. Derived standing carries over for every node the write
        can't have affected (derive.affected_by). None (rebuild instead) when an edge was retracted: retractions
        remove, they don't append."""
        if con.execute("SELECT 1 FROM events WHERE seq > ? AND kind = 'retract' LIMIT 1", (old.seq,)).fetchone():
            return None
        s = D.Snap(old.seq, self.policy)
        s.nodes = dict(old.nodes)
        s.edges = dict(old.edges)
        s.out = defaultdict(list, old.out)
        s.inn = defaultdict(list, old.inn)
        s.withdrawn = dict(old.withdrawn)
        s.leases = dict(old.leases)
        s.versions = defaultdict(list, old.versions)
        s.events = list(old.events)
        s.marks = dict(old.marks)
        s._sigs = old._sigs                       # keyed by body: still right for every node not revised
        touched = self._load_rows(con, s, set(), shared=True)
        if old._state and touched:
            stale = D.affected_by(s, touched)
            s._state = {k: v for k, v in old._state.items() if k not in stale}
        elif not touched:
            s._state = dict(old._state)
        return s

    def _invalidate(self) -> None:
        self._snap = None

    def _after_write(self) -> None:
        """From every write's finally: a failed write drops the snapshot (it may hold a staged node); a write that
        landed leaves it — the next read loads only the new rows."""
        if sys.exc_info()[0] is not None:
            self._invalidate()

    def state(self, nid: str) -> dict:
        return D.state(self.snapshot(), nid)

    # ── writes ──────────────────────────────────────────────────────
    def _rate(self, con, author: str) -> None:
        if author in self.policy.reserved:
            return
        since = (datetime.fromisoformat(self.clock()) - timedelta(minutes=1)).isoformat(timespec="seconds")
        n = con.execute("SELECT COUNT(*) FROM events WHERE actor=? AND kind='create' AND at>=?",
                        (author, since)).fetchone()[0]
        if n >= self.policy.max_creates_per_minute:
            raise GraphError(f"rate limit: {self.policy.max_creates_per_minute} new nodes a minute")

    @staticmethod
    def _code(con, ntype: str, inv: str) -> str:
        """The next free display code (H3, CL12 …) in an investigation — an indexed count and lookups, not a scan."""
        prefix = TYPES[ntype]["prefix"]
        k = con.execute("SELECT COUNT(*) FROM nodes WHERE inv=? AND type=?", (inv, ntype)).fetchone()[0] + 1
        while con.execute("SELECT 1 FROM nodes WHERE inv=? AND code=? LIMIT 1", (inv, f"{prefix}{k}")).fetchone():
            k += 1
        return f"{prefix}{k}"

    @staticmethod
    def _orient(s: D.Snap, src: str, rel: str, dst: str) -> tuple[str, str, str, bool]:
        """A link given backwards — a claim that 'supports' its result — is turned round when only the reverse is
        allowed (the relation's meaning fixes its direction, so there is one reading)."""
        if rel in RELS and src in s.nodes and dst in s.nodes and rel not in SAME_TYPE:
            st, dt = s.nodes[src]["type"], s.nodes[dst]["type"]
            srcs, dsts = RELS[rel]
            if not (st in srcs and dt in dsts) and (dt in srcs and st in dsts):
                return dst, rel, src, True
        return src, rel, dst, False

    @staticmethod
    def _check_link(s: D.Snap, src: str, rel: str, dst: str) -> None:
        if rel not in RELS:
            raise GraphError(f"unknown relation {rel!r}; relations: {', '.join(RELS)}")
        for x in (src, dst):
            if x not in s.nodes:
                raise GraphError(f"no node {x}")
        st, dt = s.nodes[src]["type"], s.nodes[dst]["type"]
        srcs, dsts = RELS[rel]
        if st not in srcs or dt not in dsts:
            joins = [r for r, (a, b) in RELS.items() if st in a and dt in b and r not in SAME_TYPE]
            back = [r for r, (a, b) in RELS.items() if dt in a and st in b and r not in SAME_TYPE and r not in joins]
            hint = (f" — a {st} joins a {dt} with {', '.join(joins)}" if joins else "") + \
                   (f"; the other way round, a {dt} joins a {st} with {', '.join(back)}" if back else "")
            raise GraphError(f"{rel} can't join {st} → {dt} (allowed: {', '.join(sorted(srcs))} → "
                             f"{', '.join(sorted(dsts))}){hint}")
        if rel in SAME_TYPE and st != dt:
            raise GraphError(f"{rel} joins two nodes of the same type")
        if src == dst:
            raise GraphError("a node can't link to itself")

    def _insert_edge(self, con, s: D.Snap, src: str, rel: str, dst: str, data: dict, why: str, author: str,
                     at: str) -> int:
        P = self.policy
        self._check_link(s, src, rel, dst)
        data = dict(data or {})
        why = str(why or "").strip()[:1500]
        trusted = author in P.reserved
        if rel in ("supports", "challenges") and len(why) < 10 and not trusted:
            raise GraphError(f"{rel}: say why (a sentence) — what in {src} bears on {dst}")
        if rel == "replicates" and data.get("differs") not in REPLICATION:
            raise GraphError(f"replicates needs data.differs: one of {', '.join(REPLICATION)}")
        if rel == "uses" and (data.get("role") or "data") not in ("data", "code", "model", "config"):
            raise GraphError("uses needs data.role: data | code | model | config")
        if rel == "tests" and not str(data.get("expected") or "").strip() and not trusted:
            raise GraphError(f"tests {dst}: give data.expected — what this experiment should show if that hypothesis "
                             "is true (that is what makes it a test)")
        if rel == "produced" and s.nodes[src]["created_by"] == P.instrument and \
                author not in {P.instrument} | P.curators:
            raise GraphError(f"only the {P.instrument} records what a {P.instrument} run produced")
        src_v, dst_v = s.nodes[src]["v"], s.nodes[dst]["v"]
        cur = con.execute("INSERT INTO edges (src, src_v, rel, dst, dst_v, data, at, by, why) VALUES (?,?,?,?,?,?,?,?,?)",
                          (src, src_v, rel, dst, dst_v, canon(data), at, author, why))
        eid = cur.lastrowid
        self._event(con, author, "link", src, {"edge": eid, "rel": rel, "dst": dst, "src_v": src_v, "dst_v": dst_v,
                                               "data_sha": store.sha(canon(data))}, at)
        return eid

    @staticmethod
    def _link_spec(nid: str, l: dict) -> tuple[str, str, str]:
        """A link given at creation: {"rel", "to"} goes from the new node; {"rel", "from"} comes into it."""
        rel = str(l.get("rel") or "")
        if l.get("from"):
            return str(l["from"]), rel, nid
        if l.get("to"):
            return nid, rel, str(l["to"])
        raise GraphError(f"link {l}: give 'to' (from this node) or 'from' (into it)")

    @staticmethod
    def _support_ids(s: D.Snap, nid: str, pending: list[tuple[str, str, str]]) -> list[str]:
        ids = [a for a, rel, b in pending if rel == "supports" and b == nid]
        ids += [b for a, rel, b in pending if rel == "derived_from" and a == nid]
        ids += [e["src"] for e in s.inn.get(nid, []) if e["rel"] == "supports"]
        ids += [e["dst"] for e in s.out.get(nid, []) if e["rel"] == "derived_from"]
        # a cited source is evidence too (knowledge profile: the source is what was read)
        ids += [b for a, rel, b in pending if rel == "cites" and a == nid and s.nodes.get(b, {}).get("type") == "source"]
        ids += [e["dst"] for e in s.out.get(nid, []) if e["rel"] == "cites" and s.nodes.get(e["dst"], {}).get("type") == "source"]
        return list(dict.fromkeys(ids))

    @staticmethod
    def _version_row(con, nid: str, v: int, at: str, author: str, reason: str, body: dict) -> str:
        c = canon(body)
        con.execute("INSERT INTO versions (node, v, at, by, reason, body) VALUES (?,?,?,?,?,?)",
                    (nid, v, at, author, str(reason)[:500], c))
        return store.sha(c)

    @staticmethod
    def _bind_measurements(s: D.Snap, body: dict, inv: str) -> dict:
        """A measurement may name its result by code (RS3): stored by id, so the binding can't drift."""
        meas = body.get("measurements")
        if not meas:
            return body
        out = []
        for m in meas:
            ref = str(m.get("result") or "") if isinstance(m, dict) else ""
            if ref and ref not in s.nodes:
                hits = [i for i, n in s.nodes.items() if n["code"].lower() == ref.lower() and n["inv"] == inv
                        and n["type"] == "result"]
                if len(hits) == 1:
                    m = {**m, "result": hits[0]}
            out.append(m)
        return {**body, "measurements": out}

    def _attribution(self, author: str, attribute_to: str) -> str:
        """Who a record is shown as by. Only the importer may attribute (to the original author of a legacy entry)."""
        if attribute_to and author == self.policy.importer:
            return str(attribute_to).strip()[:40] or author
        return author

    def _when(self, author: str, at: str) -> str:
        """The time a write is stamped with: the clock's. Only the importer brings a legacy entry in at its own date."""
        if at and author != self.policy.importer:
            raise GraphError(f"only the {self.policy.importer} sets a write's time; everyone else's is the clock's")
        return str(at) if at else self.clock()

    def _fixed_guard(self, s: D.Snap, author: str, nid: str) -> None:
        inv = s.nodes.get(s.nodes[nid]["inv"]) if nid in s.nodes else None
        if inv and author not in self.policy.reserved and (inv["body"].get("state") or "active") in ("archived",
                                                                                                      "published"):
            raise GraphError(f"{inv['body'].get('title', inv['id'])} is {inv['body'].get('state')} — its record is "
                             "fixed; build on it in a follow-up investigation (reviews and comments are still welcome)")

    def _transaction(self, fn):
        con = self._connect()
        con.execute("BEGIN IMMEDIATE")
        try:
            out = fn(con)
            con.execute("COMMIT")
            return out
        except BaseException:
            con.execute("ROLLBACK")
            raise

    def create(self, *, author: str, type: str, fields: dict, inv: str = "", links: list | None = None,
               code: str = "", node_id: str = "", reason: str = "", at: str = "", attribute_to: str = "") -> dict:
        """Add a node (version 1) with its links. ``links``: [{"rel", "to"} | {"rel", "from"}, "why", "data"].
        Claims are checked (checks.claim_issues) unless a curator writes them or the investigation is non-strict.
        Artifacts are content-addressed: the same bytes are one node."""
        P = self.policy
        author = str(author or "").strip()[:40]
        if not author:
            raise GraphError("author is required")
        if type not in TYPES:
            raise GraphError(f"unknown type {type!r}; types: {', '.join(TYPES)}")
        if type == "review":
            raise GraphError("use review() to record a review")
        body = clean_body(type, fields)
        links = [l for l in (links or []) if isinstance(l, dict)]
        with self._lock:
            try:
                s = self.snapshot()
                if type == "investigation":
                    inv = ""
                    if body.get("profile"):
                        try:
                            body["profile"] = profiles.validate_profile_id(body["profile"])   # unknown → refused
                        except KeyError as e:
                            raise GraphError(str(e).strip("'\"")) from None
                elif not inv:
                    raise GraphError("inv: which investigation this belongs to (search(type='investigation') lists "
                                     "them)")
                elif inv not in s.nodes or s.nodes[inv]["type"] != "investigation":
                    raise GraphError(f"no investigation {inv}")
                if type == "artifact":
                    node_id = "a-" + str(body["sha256"]).lower()[:16]
                    if node_id in s.nodes:
                        return self._absorb_artifact(s, node_id, body, links, author, at=at)
                nid = node_id or ("inv-" + secrets.token_hex(4) if type == "investigation"
                                  else "n" + secrets.token_hex(6))
                if nid in s.nodes:
                    raise GraphError(f"node {nid} already exists")
                at = self._when(author, at)
                if inv and author not in P.reserved and \
                        (s.nodes[inv]["body"].get("state") or "active") in ("archived", "published"):
                    raise GraphError(f"{s.nodes[inv]['body'].get('title', inv)} is "
                                     f"{s.nodes[inv]['body'].get('state')} — its record is fixed. Open a follow-up "
                                     "investigation and link to what you build on; reviews and comments on it are "
                                     "still welcome.")
                who = self._attribution(author, attribute_to)
                if type == "run" and body.get("kind") == "lab" and who != P.instrument:
                    raise GraphError(f"kind=lab is the {P.instrument}'s own record (filed by the instrument itself, "
                                     "with hashes); a run you report is kind=agent")
                staged = {"id": nid, "type": type, "code": "", "inv": inv, "created_at": at, "created_by": who,
                          "v": 1, "body": body}
                s.nodes[nid] = staged                     # staged for link checks; dropped if the write fails
                oriented = [self._orient(s, *self._link_spec(nid, l)) for l in links]
                pending = [(a, rel, b) for a, rel, b, _f in oriented]
                flipped = [f"{s.nodes[a].get('code') or a} -{rel}-> {s.nodes[b].get('code') or b}"
                           for a, rel, b, f in oriented if f]
                for a, rel, b in pending:
                    self._check_link(s, a, rel, b)
                auto_notes: list[str] = []
                if type == "claim":
                    body = self._bind_measurements(s, body, inv)
                    staged["body"] = body
                    # a measurement names the result its number comes from: that result supports the claim, so the
                    # standing counts it as a line of support without a separate link from the writer
                    for m in body.get("measurements") or []:
                        rid = m.get("result") if isinstance(m, dict) else None
                        if rid not in s.nodes:
                            rid = next((i for i, n in s.nodes.items() if n.get("code") == rid and n["inv"] == inv), None)
                        if rid and s.nodes[rid]["type"] == "result" and rid != nid and not any(
                                (a == rid and b == nid and rel == "supports") or (a == nid and b == rid and rel == "derived_from")
                                for a, rel, b in pending):
                            a, rel, b, _f = self._orient(s, rid, "supports", nid)
                            self._check_link(s, a, rel, b)
                            pending.append((a, rel, b))
                            links.append({"rel": "supports", "from": rid, "why": "a measurement of this claim is this result's"})
                if type == "claim" and author not in P.curators:
                    problems = claim_issues(s, body, self._support_ids(s, nid, pending), inv)
                    loose = [w for p in problems if p.code == "UNBOUND_NUMBER" for w in p.words]
                    if loose:                               # repair before refusing: bind what the record holds
                        body, extra, auto_notes = self._auto_bind(s, body, inv, who,
                                                                  self._support_ids(s, nid, pending), loose)
                        if auto_notes:
                            staged["body"] = body
                            for dst in extra:
                                a, rel, b, _f = self._orient(s, dst, "supports", nid)
                                self._check_link(s, a, rel, b)
                                pending.append((a, rel, b))
                                links.append({"rel": "supports", "from": dst,
                                              "why": "bound by the record: the claim's numbers are this result's"})
                            problems = claim_issues(s, body, self._support_ids(s, nid, pending), inv)
                    problems = list(problems) + profiles.claim_issues(s, inv, body, self._support_ids(s, nid, pending),
                                                                      pending)
                    if problems:
                        found = [p.to_dict() for p in problems]
                        refusals.record_refusal(self, author=author, op="create", inv=inv, node="", body=body,
                                                problems=found, support=self._support_ids(s, nid, pending))
                        raise GraphError("claim refused:\n- " + "\n- ".join(p.text() for p in problems), found)
                if type == "result" and author not in P.curators:
                    rp = profiles.result_issues(s, inv, body, pending, author=author)
                    if rp:
                        found = [p.to_dict() for p in rp]
                        refusals.record_refusal(self, author=author, op="create", inv=inv, node="", body=body,
                                                problems=found, support=[])
                        raise GraphError("result refused:\n- " + "\n- ".join(p.text() for p in rp), found)
                if type in ("artifact", "source", "decision") and author not in P.curators:
                    np_ = profiles.node_issues(s, inv, type, body, pending)       # the workflow's typed shapes
                    if np_:
                        found = [p.to_dict() for p in np_]
                        refusals.record_refusal(self, author=author, op="create", inv=inv, node="",
                                                body={"statement": str(body.get("choice") or body.get("citation")
                                                                       or body.get("path") or ""), "kind": type},
                                                problems=found)
                        raise GraphError(f"{type} refused:\n- " + "\n- ".join(p.text() for p in np_), found)
                if type == "result" and author not in P.reserved:
                    same = self._restated_by(s, body, inv, nid)
                    runs = [a for a, rel, b in pending if rel == "produced" and b == nid]
                    declared = any(e["rel"] == "replicates" for r in runs for e in s.out.get(r, []))
                    mine = [i for i in same if s.nodes[i]["created_by"] == who]
                    if mine and not declared:
                        c = s.nodes[mine[0]]["code"] or mine[0]
                        found = [{"code": "RESULT_RESTATES", "message": f"this result repeats the numbers of your own "
                                  f"{c}", "fix": f"bind claims to {c} instead", "words": []}]
                        refusals.record_refusal(self, author=author, op="create", inv=inv, node="",
                                                body={"statement": body.get("summary", ""), "kind": "result"},
                                                problems=found)
                        raise GraphError(f"result refused: it repeats the numbers of your own {c} — bind claims to "
                                         f"{c} instead of writing it again; a genuine rerun is a run that replicates "
                                         f"{c}'s run [RESULT_RESTATES]", found)

                def write(con):
                    self._rate(con, author)
                    c = str(code or "").strip()[:40] or self._code(con, type, inv)
                    staged["code"] = c
                    con.execute("INSERT INTO nodes (id, type, code, inv, created_at, created_by) VALUES (?,?,?,?,?,?)",
                                (nid, type, c, inv, at, who))
                    sha = self._version_row(con, nid, 1, at, author, reason, body)
                    self._event(con, author, "create", nid, {"type": type, "code": c, "inv": inv, "v": 1,
                                                             "body_sha": sha}, at)
                    for (a, rel, b), l in zip(pending, links):
                        self._insert_edge(con, s, a, rel, b, l.get("data") or {}, l.get("why") or "", author, at)
                self._transaction(write)
            finally:
                # the staged node lives in the cached snapshot: a failed write drops it; after a commit the next
                # read loads the committed rows over it
                self._after_write()
        out = self.get(nid)
        notes = [f"link turned round to the direction the relation allows: {x}" for x in flipped]
        if auto_notes:
            notes.append("bound by the record: " + ", ".join(auto_notes))
            out["auto_bound"] = auto_notes
        if notes:
            out["notes"] = notes
        if out["state"].get("restates"):
            out["restates"] = [self.get(r)["code"] for r in out["state"]["restates"]]
        self._with_orders(out, author, inv)
        if type == "claim" and author not in P.curators:
            fixed = refusals.match_fix(self, author=author, inv=inv, node=nid, statement=body.get("statement", ""),
                                       op="create")
            if fixed:
                out["fixes_refusals"] = fixed
        return out

    @staticmethod
    def _auto_bind(s: D.Snap, body: dict, inv: str, author: str, support: list[str], loose: list[str]) -> tuple:
        """Bind the statement's loose numbers to results the claim already links, then to the author's own results
        in this investigation (newest first). Small integers (≤ 12) bind only to counts (k, n) — or to a value whose
        field the sentence names ("0 trades" to `oos_trades`, "capacity is 7" to `capacity_total`) — never to an
        unnamed value, so a limit or a day of the month can't borrow a field by coincidence.
        Returns (body, results to link, notes)."""
        import re as _re
        from .checks import _arm, _matches, _nums, numbers

        def named(key: str, text: str) -> bool:
            words = [w for w in _re.split(r"[^a-z0-9]+", key.lower()) if len(w) >= 3]
            low = text.lower()
            return bool(words) and any(_re.search(r"\b" + _re.escape(w), low) for w in words)
        stmt = body.get("statement", "")
        linked = [x for x in support if (s.nodes.get(x) or {}).get("type") == "result"]
        mine = sorted((i for i, n in s.nodes.items() if n["type"] == "result" and n["inv"] == inv
                       and n["created_by"] == author and i not in linked and not D.fallen(s, i)),
                      key=lambda i: s.nodes[i]["created_at"], reverse=True)
        cands = []
        for rid in linked + mine:
            for key, rv in (s.nodes[rid]["body"].get("values") or {}).items():
                if isinstance(rv, (int, float)) and not isinstance(rv, bool):
                    rv = {"value": rv}
                if isinstance(rv, dict):
                    cands.append((rid, key, rv))
        meas = [m for m in body.get("measurements") or [] if isinstance(m, dict)]
        taken = {(m.get("result"), m.get("key")) for m in meas}
        added, notes = [], []
        for printed in numbers(stmt):
            if printed[3] not in loose:
                continue
            small = printed[1] == 0 and not printed[2] and printed[0] <= 12
            for rid, key, rv in cands:
                if (rid, key) in taken:
                    continue
                arm = _arm(rv)
                vals = ([float(arm[0]), float(arm[1])] if arm else []) if small else _nums(rv) + \
                    ([arm[0] / arm[1]] if arm else [])
                if small and not arm and isinstance(rv.get("value"), (int, float)) and not isinstance(rv.get("value"), bool) \
                        and named(key, stmt):
                    vals = [float(rv["value"])]
                if vals and _matches(printed, vals):
                    m = {"name": key, "result": rid, "key": key}
                    if arm:
                        m.update(k=arm[0], n=arm[1])
                    elif isinstance(rv.get("value"), (int, float)):
                        m["value"] = rv["value"]
                    added.append(m)
                    taken.add((rid, key))
                    notes.append(f"{printed[3]} → {s.nodes[rid]['code'] or rid}.{key}")
                    break
        if not added:
            return body, [], []
        extra = list(dict.fromkeys(m["result"] for m in added if m["result"] not in linked))
        return {**body, "measurements": meas + added}, extra, notes

    @staticmethod
    def _restated_by(s: D.Snap, body: dict, inv: str, exclude: str = "") -> list[str]:
        """Live results in the investigation whose numbers this body repeats, oldest first."""
        sig = D.result_signature(body)
        if not sig:
            return []
        hits = [i for i in D.repeating(s, sig, inv) if i != exclude]
        return sorted(hits, key=lambda i: s.nodes[i]["created_at"])

    def _with_orders(self, out: dict, author: str, inv: str) -> None:
        """The done signal: after a write, the author's open work orders with their predicates checked."""
        if not inv or author in self.policy.reserved:
            return
        from . import coord
        try:
            lines = coord.done_lines(self, author, inv)
        except Exception:  # noqa: BLE001 — advisory; never fails a write
            lines = []
        if lines:
            out["orders"] = lines

    def _absorb_artifact(self, s: D.Snap, nid: str, body: dict, links: list, author: str, *, at: str = "") -> dict:
        """The same bytes are one node. A second registration adds what the first lacked: the links given now
        (part_of a question, supersedes an older file) and, when the node was untyped, its kind / meta / path — a
        classification of the bytes, by anyone, as a new version (the bytes never change). Called inside create()'s
        lock; the caller's finally refreshes the snapshot."""
        n = s.nodes[nid]
        at = self._when(author, at)
        have = {(e["rel"], e["dst"]) for e in s.out.get(nid, [])} | {(e["rel"], e["src"]) for e in s.inn.get(nid, [])}
        oriented = [self._orient(s, *self._link_spec(nid, l)) for l in links]
        pending = [(a, rel, b, l) for (a, rel, b, _f), l in zip(oriented, links)
                   if (rel, b if a == nid else a) not in have]
        for a, rel, b, _l in pending:
            self._check_link(s, a, rel, b)
        merged = None
        if not n["body"].get("kind") and body.get("kind"):
            merged = clean_body("artifact", {**n["body"], **{k: v for k, v in body.items()
                                                             if k in ("kind", "meta", "path", "format", "size") and v}})
            if author not in self.policy.curators:
                np_ = profiles.node_issues(s, n["inv"], "artifact", merged, [(a, rel, b) for a, rel, b, _l in pending])
                if np_:
                    raise GraphError("artifact refused:\n- " + "\n- ".join(p.text() for p in np_), [p.to_dict() for p in np_])
        if not pending and merged is None:
            return self.get(nid)

        def write(con):
            if merged is not None:
                v = con.execute("SELECT MAX(v) FROM versions WHERE node=?", (nid,)).fetchone()[0] + 1
                sha = self._version_row(con, nid, v, at, author, f"typed as {merged.get('kind')}", merged)
                self._event(con, author, "revise", nid, {"v": v, "reason": f"typed as {merged.get('kind')}",
                                                         "body_sha": sha}, at)
            for a, rel, b, l in pending:
                self._insert_edge(con, s, a, rel, b, l.get("data") or {}, l.get("why") or "", author, at)
        self._transaction(write)
        self._after_write()
        out = self.get(nid)
        notes = ["the same bytes were already registered: one node"]
        if merged is not None:
            notes.append(f"typed as {merged.get('kind')} (v{out['v']})")
        if pending:
            notes.append("linked: " + ", ".join(f"{rel} {s.nodes[b if a == nid else a].get('code') or b}"
                                                for a, rel, b, _l in pending))
        out["notes"] = notes
        return out

    def _may_revise(self, s: D.Snap, author: str, n: dict) -> bool:
        return author in {n["created_by"]} | self.policy.curators or author in D.board(s, n["id"])

    def revise(self, *, author: str, node: str, fields: dict, reason: str) -> dict:
        """A new version: the given fields replace the old ones (others carry over). Reviews of the old version stay
        on record but no longer count as a check of this one. Only the author, a reviewer or a curator revises;
        anyone else challenges it, or writes a node that supersedes it."""
        P = self.policy
        if len(str(reason or "").strip()) < 10:
            raise GraphError("reason: why this changes (a sentence)")
        with self._lock:
            try:
                s = self.snapshot()
                n = s.nodes.get(node)
                if not n:
                    raise GraphError(f"no node {node}")
                if n["type"] in ("artifact", "review"):
                    raise GraphError(f"a {n['type']} can't be revised — add a new one")
                if n["created_by"] == P.instrument and author not in (P.instrument, P.operator):
                    raise GraphError(f"a {P.instrument}-recorded run is the {P.instrument}'s record; add a result or "
                                     "a review instead")
                self._fixed_guard(s, author, node)
                if not self._may_revise(s, author, n):
                    raise GraphError(f"only {n['created_by']} (its author), a reviewer or the {P.operator} revises "
                                     f"{n['code']}; challenge it, or propose a node that supersedes it")
                body = clean_body(n["type"], {**n["body"], **(fields or {})})
                extra: list[str] = []
                auto_notes: list[str] = []
                if n["type"] == "claim":
                    body = self._bind_measurements(s, body, n["inv"])
                if n["type"] == "run" and body.get("kind") != n["body"].get("kind") and author != P.operator:
                    raise GraphError("a run's kind (lab / agent / external) is where its record came from; it doesn't "
                                     "change")
                if n["type"] == "claim" and author not in P.curators:
                    problems = claim_issues(s, body, self._support_ids(s, node, []), n["inv"])
                    loose = [w for p in problems if p.code == "UNBOUND_NUMBER" for w in p.words]
                    if loose:
                        body, extra, auto_notes = self._auto_bind(s, body, n["inv"], n["created_by"],
                                                                  self._support_ids(s, node, []), loose)
                        if auto_notes:
                            pend = [(dst, "supports", node) for dst in extra]
                            for a, rel, b in pend:
                                self._check_link(s, a, rel, b)
                            problems = claim_issues(s, body, self._support_ids(s, node, pend), n["inv"])
                    if problems:
                        found = [p.to_dict() for p in problems]
                        refusals.record_refusal(self, author=author, op="revise", inv=n["inv"], node=node, body=body,
                                                problems=found, support=self._support_ids(s, node, []))
                        raise GraphError("revision refused:\n- " + "\n- ".join(p.text() for p in problems), found)
                at = self.clock()

                def write(con):
                    v = con.execute("SELECT MAX(v) FROM versions WHERE node=?", (node,)).fetchone()[0] + 1
                    sha = self._version_row(con, node, v, at, author, reason, body)
                    self._event(con, author, "revise", node, {"v": v, "reason": str(reason)[:300], "body_sha": sha}, at)
                    for dst in extra:
                        self._insert_edge(con, s, dst, "supports", node, {},
                                          "bound by the record: the claim's numbers are this result's", author, at)
                self._transaction(write)
            finally:
                self._after_write()
        out = self.get(node)
        if auto_notes:
            out["notes"] = ["bound by the record: " + ", ".join(auto_notes)]
            out["auto_bound"] = auto_notes
        self._with_orders(out, author, out["inv"])
        if out["type"] == "claim" and author not in P.curators:
            fixed = refusals.match_fix(self, author=author, inv=out["inv"], node=node,
                                       statement=out["body"].get("statement", ""), op="revise")
            if fixed:
                out["fixes_refusals"] = fixed
        return out

    def link(self, *, author: str, src: str, rel: str, dst: str, why: str = "", data: dict | None = None) -> dict:
        if rel == "reviews":
            raise GraphError("use review() — a review is its own node")
        with self._lock:
            try:
                s = self.snapshot()
                src, rel, dst, flipped = self._orient(s, src, rel, dst)
                if src in s.nodes:
                    self._fixed_guard(s, author, src)
                eid = self._transaction(lambda con: self._insert_edge(con, s, src, rel, dst, data or {}, why, author,
                                                                      self.clock()))
            finally:
                self._after_write()
        return {"edge": eid, "src": src, "rel": rel, "dst": dst, "flipped": flipped}

    def retract(self, *, author: str, edge: int, why: str) -> dict:
        if len(str(why or "").strip()) < 10:
            raise GraphError("why: say why this link no longer holds")
        with self._lock:
            try:
                s = self.snapshot()
                e = s.edges.get(int(edge))
                if not e:
                    raise GraphError(f"no live edge {edge}")
                if author not in (e["by"], self.policy.operator) and author not in D.board(s, e["src"]):
                    raise GraphError(f"only the link's author, a reviewer or the {self.policy.operator} retracts a link")
                at = self.clock()

                def write(con):
                    con.execute("INSERT INTO retractions (edge, at, by, why) VALUES (?,?,?,?)",
                                (int(edge), at, author, why[:1000]))
                    self._event(con, author, "retract", e["src"], {"edge": int(edge)}, at)
                self._transaction(write)
            finally:
                self._after_write()
        return {"retracted": int(edge)}

    def withdraw(self, *, author: str, node: str, why: str, at: str = "", attribute_to: str = "") -> dict:
        if len(str(why or "").strip()) < 10:
            raise GraphError("why: say why it is withdrawn")
        with self._lock:
            try:
                s = self.snapshot()
                n = s.nodes.get(node)
                if not n:
                    raise GraphError(f"no node {node}")
                if node in s.withdrawn:
                    raise GraphError(f"{node} is already withdrawn")
                if author not in (n["created_by"], self.policy.operator) and author not in D.board(s, node):
                    raise GraphError(f"only its author, a reviewer or the {self.policy.operator} withdraws a node")
                at = self._when(author, at)

                def write(con):
                    con.execute("INSERT INTO withdrawals (node, at, by, why) VALUES (?,?,?,?)",
                                (node, at, self._attribution(author, attribute_to), why[:1000]))
                    self._event(con, author, "withdraw", node, {"why": why[:300]}, at)
                self._transaction(write)
            finally:
                self._after_write()
        return self.get(node) | {"blast_radius": self.blast_radius(node)}

    def blast_radius(self, nid: str) -> dict:
        """What falls if this node falls: everything that rests on it, by type, with the claims and decisions named,
        and — when a spend meter is connected — what the work behind them cost. Returned by withdraw() and by a
        review that contests a node, so a correction always shows its consequences."""
        s = self.snapshot()
        if nid not in s.nodes:
            raise KeyError(nid)
        dep = D.dependents(s, nid)
        ids = [d for d, _r, _k in dep if d in s.nodes and s.nodes[d]["type"] not in ("review", "artifact")]
        by: dict[str, list] = defaultdict(list)
        for d in ids:
            by[s.nodes[d]["type"]].append(s.nodes[d]["code"] or d)
        out = {"node": nid, "code": s.nodes[nid]["code"], "count": len(ids), "by_type": {k: len(v) for k, v in by.items()},
               "claims": by.get("claim", [])[:50], "decisions": by.get("decision", [])[:50],
               "results": by.get("result", [])[:50], "hypotheses": by.get("hypothesis", [])[:50]}
        if self.spend is not None and ids and s.nodes[nid]["inv"]:
            try:
                idset = set(ids)
                tasks = {t for e in s.events if e["ref"] in idset for t in [(e["payload"] or {}).get("task")] if t}
                led = self.spend(s.nodes[nid]["inv"], tasks) if tasks else {"usd": 0.0}
                out["usd"] = round(float(led.get("usd") or 0), 2)
            except Exception:  # noqa: BLE001 - a spend problem never hides the consequences
                pass
        if not ids:
            out["sentence"] = f"nothing rests on {out['code'] or nid}"
        else:
            parts = [f"{len(v)} {k}{'s' if len(v) != 1 else ''} ({', '.join(v[:6])}{'…' if len(v) > 6 else ''})"
                     for k, v in sorted(by.items(), key=lambda x: (x[0] != "decision", x[0] != "claim", x[0]))]
            out["sentence"] = (f"{len(ids)} node{'s' if len(ids) != 1 else ''} rest on {out['code'] or nid}: "
                               + "; ".join(parts)
                               + (f" — ${out['usd']:,.2f} of work behind them" if out.get("usd") else ""))
        return out

    def review(self, *, author: str, target: str, verdict: str, method: str, notes: str, links: list | None = None,
               at: str = "", attribute_to: str = "") -> dict:
        """A review of a node's CURRENT version. Board members' verdicts count; anyone else's is recorded as a
        comment. Nobody reviews their own work officially."""
        P = self.policy
        with self._lock:
            try:
                s = self.snapshot()
                n = s.nodes.get(target)
                if not n:
                    raise GraphError(f"no node {target}")
                if n["type"] not in RELS["reviews"][1]:
                    raise GraphError(f"a {n['type']} isn't reviewed")
                official = author in D.board(s, target) and verdict != "comment"
                if official and author == n["created_by"] and author not in P.curators:
                    who = ", ".join(sorted(D.board(s, target) - P.curators - {author})[:6]) or "another reviewer"
                    raise GraphError(f"you can't review your own work — ask a reviewer ({who})")
                if official and author not in P.curators:
                    why = profiles.review_refusal(s, n["inv"], target, author)
                    if why:
                        raise GraphError(why)
                if verdict not in VERDICTS:
                    raise GraphError(f"verdict must be one of {', '.join(sorted(VERDICTS))}")
                body = clean_body("review", {"verdict": verdict if official or verdict == "comment" else "comment",
                                             "method": method, "notes": notes, "official": official})
                nid = "n" + secrets.token_hex(6)
                at = self._when(author, at)

                def write(con):
                    c = self._code(con, "review", n["inv"])
                    con.execute("INSERT INTO nodes (id, type, code, inv, created_at, created_by) VALUES (?,?,?,?,?,?)",
                                (nid, "review", c, n["inv"], at, self._attribution(author, attribute_to)))
                    sha = self._version_row(con, nid, 1, at, author, "", body)
                    self._event(con, author, "review", target, {"review": nid, "verdict": body["verdict"],
                                                                "on_v": n["v"], "official": official,
                                                                "body_sha": sha}, at)
                    cur = con.execute("INSERT INTO edges (src, src_v, rel, dst, dst_v, data, at, by, why) "
                                      "VALUES (?,?,?,?,?,?,?,?,?)", (nid, 1, "reviews", target, n["v"], "{}", at,
                                                                     author, ""))
                    self._event(con, author, "link", nid, {"edge": cur.lastrowid, "rel": "reviews", "dst": target,
                                                           "src_v": 1, "dst_v": n["v"],
                                                           "data_sha": store.sha("{}")}, at)
                self._transaction(write)
            finally:
                self._after_write()
        out = self.get(target)
        if out["state"].get("fallen"):
            out["blast_radius"] = self.blast_radius(target)
        self._with_orders(out, author, out["inv"])
        return out

    def lease(self, *, author: str, node: str, task: str = "", minutes: int = 240, release: bool = False,
              note: str = "") -> dict:
        """Take (or release) a piece of work — an experiment, a review, a question — so others see who is on it."""
        with self._lock:
            try:
                s = self.snapshot()
                if node not in s.nodes:
                    raise GraphError(f"no node {node}")
                cur = s.leases.get(node)
                at = self.clock()
                if release:
                    if not cur or cur["agent"] != author:
                        raise GraphError("you don't hold a lease on it")
                    kind, exp = "release", ""
                else:
                    if cur and cur["agent"] != author:
                        raise GraphError(f"{cur['agent']} is on it until {cur['expires']} (task {cur['task'] or '—'})"
                                         " — pick another, or coordinate with them")
                    kind = "take"
                    exp = (datetime.fromisoformat(at) + timedelta(minutes=max(15, min(int(minutes), 1440)))
                           ).isoformat(timespec="seconds")

                def write(con):
                    con.execute("INSERT INTO leases (node, agent, task, kind, at, expires, note) VALUES (?,?,?,?,?,?,?)",
                                (node, author, str(task)[:80], kind, at, exp, str(note)[:300]))
                    self._event(con, author, "lease_" + kind, node, {"task": str(task)[:80], "expires": exp}, at)
                self._transaction(write)
            finally:
                self._after_write()
        return self.get(node)

    # ── reads ───────────────────────────────────────────────────────
    @staticmethod
    def brief(s: D.Snap, nid: str) -> dict:
        n = s.nodes[nid]
        b = n["body"]
        title = (b.get("statement") or b.get("title") or b.get("text") or b.get("aim") or b.get("summary")
                 or b.get("choice") or b.get("citation") or b.get("name") or b.get("path") or b.get("verdict") or "")
        return {"id": nid, "type": n["type"], "code": n["code"], "inv": n["inv"], "title": str(title)[:300],
                "kind": b.get("kind") or b.get("verdict") or "", "v": n["v"], "by": n["created_by"],
                "at": n["created_at"], "state": D.state(s, nid)}

    @staticmethod
    def edge_out(e: dict) -> dict:
        return {k: e[k] for k in ("id", "src", "src_v", "rel", "dst", "dst_v", "data", "at", "by", "why")}

    def get(self, nid: str, history: bool = False) -> dict:
        s = self.snapshot()
        if nid not in s.nodes:
            raise KeyError(nid)
        n = s.nodes[nid]
        out = self.brief(s, nid) | {"body": n["body"], "out": [self.edge_out(e) for e in s.out.get(nid, [])],
                                    "in": [self.edge_out(e) for e in s.inn.get(nid, [])]}
        if nid in s.withdrawn:
            out["withdrawn"] = s.withdrawn[nid]
        if history:
            out["versions"] = list(s.versions.get(nid, []))
        return out

    def resolve(self, ref: str, inv: str = "") -> str:
        """A node id from an id or a display code (CL3, H2, X4 …), within an investigation when given."""
        ref = str(ref or "").strip()
        s = self.snapshot()
        if ref in s.nodes:
            return ref
        hits = [i for i, n in s.nodes.items() if n["code"].lower() == ref.lower() and (not inv or n["inv"] == inv)]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise KeyError(f"no node {ref!r}" + (f" in {inv}" if inv else ""))
        raise GraphError(f"{ref!r} is ambiguous: " + ", ".join(f"{h} ({s.nodes[h]['inv']})" for h in hits[:6])
                         + " — give the id or the investigation")

    def investigations(self) -> list[dict]:
        s = self.snapshot()
        counts: dict[str, dict] = defaultdict(lambda: defaultdict(int))
        for n in s.nodes.values():
            if n["inv"]:
                counts[n["inv"]][n["type"]] += 1
        return [self.brief(s, i) | {"counts": dict(counts[i]), "body": s.nodes[i]["body"]}
                for i, n in s.nodes.items() if n["type"] == "investigation"]

    def subgraph(self, inv: str = "", types: list | None = None, limit: int = 5000) -> dict:
        """Every node of an investigation (or all) with derived state, and the live edges among them."""
        s = self.snapshot()
        ids = [i for i, n in s.nodes.items() if (not inv or n["inv"] == inv or i == inv)
               and (not types or n["type"] in types)][:limit]
        idset = set(ids)
        return {"seq": s.seq, "nodes": [self.brief(s, i) for i in ids],
                "edges": [self.edge_out(e) for e in s.edges.values() if e["src"] in idset and e["dst"] in idset]}

    def neighborhood(self, nid: str, depth: int = 1, limit: int = 400) -> dict:
        s = self.snapshot()
        if nid not in s.nodes:
            raise KeyError(nid)
        seen, frontier = {nid}, [nid]
        for _ in range(max(1, min(int(depth), 4))):
            nxt = []
            for x in frontier:
                for e in s.out.get(x, []) + s.inn.get(x, []):
                    y = e["dst"] if e["src"] == x else e["src"]
                    if y not in seen and len(seen) < limit:
                        seen.add(y)
                        nxt.append(y)
            frontier = nxt
        return {"seq": s.seq, "center": nid, "nodes": [self.brief(s, i) for i in seen],
                "edges": [self.edge_out(e) for e in s.edges.values() if e["src"] in seen and e["dst"] in seen]}

    def why(self, nid: str) -> dict:
        """Upstream: what this rests on and what supports it, down to runs, artifacts and sources."""
        s = self.snapshot()
        if nid not in s.nodes:
            raise KeyError(nid)
        # Out-edges whose target is something x rests on; in-edges whose source backs x. An out-going `supports`
        # or `produced` points downstream (x supports y → y rests on x): that's impact, not why.
        out_rels = ("derived_from", "requires", "based_on", "executes", "uses", "cites", "tests")
        in_rels = ("supports", "produced")
        seen, frontier, edges = {nid}, [nid], []
        while frontier and len(seen) < 300:
            nxt = []
            for x in frontier:
                ups = [(e, e["dst"]) for e in s.out.get(x, []) if e["rel"] in out_rels] + \
                      [(e, e["src"]) for e in s.inn.get(x, []) if e["rel"] in in_rels]
                for e, y in ups:
                    edges.append(e)
                    if y not in seen:
                        seen.add(y)
                        nxt.append(y)
            frontier = nxt
        return {"center": nid, "nodes": [self.brief(s, i) for i in seen], "edges": [self.edge_out(e) for e in edges]}

    def impact(self, nid: str) -> dict:
        """Downstream: everything that rests on this node, directly or through a chain."""
        s = self.snapshot()
        if nid not in s.nodes:
            raise KeyError(nid)
        dep = D.dependents(s, nid)
        ids = {nid} | {d for d, _r, _x in dep}
        return {"center": nid, "dependents": [{"node": self.brief(s, d), "rel": r, "depth": k} for d, r, k in dep],
                "edges": [self.edge_out(e) for e in s.edges.values() if e["src"] in ids and e["dst"] in ids]}

    def search(self, text: str = "", type: str = "", inv: str = "", limit: int = 50) -> list[dict]:
        s = self.snapshot()
        q = (text or "").lower().strip()
        out = []
        for i, n in s.nodes.items():
            if type and n["type"] != type:
                continue
            if inv and n["inv"] != inv and i != inv:
                continue
            if q and q not in (n["code"].lower() + " " + canon(n["body"]).lower()) and q != i:
                continue
            out.append(self.brief(s, i))
            if len(out) >= limit:
                break
        return out

    def events(self, after: int = 0, limit: int = 500, inv: str = "") -> dict:
        s = self.snapshot()
        rows = [e for e in s.events if e["seq"] > int(after)]
        if inv:
            rows = [r for r in rows if r["ref"] == inv or s.nodes.get(r["ref"], {}).get("inv") == inv]
        return {"head": s.seq, "events": rows[: max(1, min(int(limit), 5000))]}

    def stats(self) -> dict:
        s = self.snapshot()
        by: dict[str, int] = defaultdict(int)
        for n in s.nodes.values():
            by[n["type"]] += 1
        return {"seq": s.seq, "nodes": len(s.nodes), "edges": len(s.edges), "by_type": dict(by),
                "leases": len(s.leases)}

    # ── the refusal log (refusals.py) and checking write-ups (report_check.py) ──
    def refusals(self, inv: str = "", author: str = "", since: str = "", limit: int = 500) -> list[dict]:
        """Every overclaim the record refused, newest first, with its codes and what fixed it (if anything)."""
        return refusals.rows(self, inv=inv, author=author, since=since, limit=limit)

    def refusal_report(self, inv: str = "", since: str = "") -> dict:
        """Overclaims caught per author and per rule, fixed vs open, with the latest in full (and as markdown)."""
        return refusals.report(self, inv=inv, since=since)

    def replay_refusals(self, inv: str = "") -> dict:
        """Every logged refusal through the checker as it is now (refusals.replay)."""
        return refusals.replay(self, inv)

    def verify_refusals(self) -> dict:
        """The refusal log's own hash chain."""
        return refusals.verify(self)

    def check_text(self, text: str, inv: str = "") -> dict:
        """Lint a write-up (markdown) against the record: numbers no result contains, claims stated as settled that
        the record has as contested / withdrawn / unchecked, codes that don't exist, absolutes nothing counts."""
        from . import report_check
        return report_check.check(self, text, inv)

    # ── coordinating a team through the record (coord.py) ───────────
    def briefing(self, inv: str, *, roster: list | None = None, since_seq: int = 0, budget_usd: float = 0) -> dict:
        """The orchestrator's context, compiled from the record (coord.briefing)."""
        from . import coord
        return coord.briefing(self, inv, roster=roster, since_seq=since_seq, budget_usd=budget_usd)

    def issue_work(self, **kw) -> dict:
        """A work order on one target for one assignee, with done-when predicates (coord.issue_work)."""
        from . import coord
        return coord.issue_work(self, **kw)

    def order_text(self, order: str) -> str:
        from . import coord
        return coord.order_text(self, self.resolve(order))

    def orders(self, inv: str, status: str = "") -> list[dict]:
        from . import coord
        return coord.orders(self, inv, status)

    def return_work(self, *, author: str, order: str, note: str = "") -> dict:
        from . import coord
        return coord.return_work(self, author=author, order=self.resolve(order), note=note)

    def check_work(self, order: str, text: str = "") -> dict:
        from . import coord
        return coord.check_work(self, self.resolve(order), text)

    def accept_work(self, *, author: str, order: str, reason: str = "", text: str = "") -> dict:
        from . import coord
        return coord.accept_work(self, author=author, order=self.resolve(order), reason=reason, text=text)

    def rework(self, *, author: str, order: str, missing: str, done_when: list | None = None) -> dict:
        from . import coord
        return coord.rework(self, author=author, order=self.resolve(order), missing=missing, done_when=done_when)

    def cancel_work(self, *, author: str, order: str, why: str) -> dict:
        from . import coord
        return coord.cancel_work(self, author=author, order=self.resolve(order), why=why)

    def cancel_moot(self, *, author: str, inv: str) -> list[dict]:
        from . import coord
        return coord.cancel_moot(self, author=author, inv=inv)

    def completion(self, inv: str) -> dict:
        """What the investigation's profile says "done" means, each criterion derived from the record."""
        return profiles.completion(self.snapshot(), self.resolve(inv))

    def stage(self, node: str, inv: str = "") -> dict:
        """The workflow stage a question (or the question a node is about) is in — derived from the record, never
        set: the first stage whose gate is not met, with every gate's status (workflow.stage_of)."""
        from . import workflow
        s = self.snapshot()
        return workflow.stage_of(s, self.resolve(node, inv), s.now)

    def stages(self, inv: str) -> list[dict]:
        """stage() for every live question of an investigation."""
        from . import workflow
        s = self.snapshot()
        return workflow.stages(s, self.resolve(inv), s.now)

    def question_board(self, inv: str) -> list[dict]:
        """Every live question with its derived status (coord.question_board)."""
        from . import coord
        return coord.question_board(self, inv)

    def settle(self, *, author: str, inv: str) -> list[dict]:
        """Accept every returned order whose predicates are all met (coord.settle)."""
        from . import coord
        return coord.settle(self, author=author, inv=inv)

    # ── method & coordination (plan.py) ─────────────────────────────
    def next_experiments(self, inv: str, limit: int = 10) -> dict:
        from . import plan
        return plan.next_experiments(self, inv, limit)

    def work_map(self, inv: str = "") -> dict:
        from . import plan
        return plan.work_map(self, inv)

    def duplicates(self, inv: str) -> list[list[str]]:
        from . import plan
        return plan.duplicates(self.snapshot(), inv)

    def digest(self, since: str = "", inv: str = "") -> dict:
        from . import plan
        return plan.digest(self, since, inv)

    def cost(self, inv: str, nid: str = "") -> dict:
        from . import plan
        return plan.cost(self, inv, nid)

    def report(self, inv: str) -> dict:
        from . import plan
        return plan.report(self, inv)

    # ── portable bundles (bundle.py) ────────────────────────────────
    def export(self, inv: str = "", *, derived: bool = True, telemetry: str | os.PathLike | list | None = None) -> dict:
        """A portable, verifiable bundle of the whole graph (or one investigation) — see bundle.py. ``telemetry``: a
        swarm's sidecar (a path, or its events) to carry for replay; outside the hash chain, never trusted."""
        from . import bundle
        return bundle.export(self, inv, derived=derived, telemetry=telemetry)

    @classmethod
    def from_bundle(cls, b: dict, path: str | os.PathLike | None = None, *, policy: Policy | None = None) -> "Graph":
        """A graph rebuilt row for row from a complete bundle (in memory unless ``path`` is given). It verifies
        exactly as the original did; refused if the bundle doesn't verify."""
        from . import bundle
        g = cls(path, policy=policy or Policy.from_dict(b.get("policy") or {}))
        bundle.load(g, b)
        return g


class Author:
    """Writes as one author. ``me = g.author("ada"); h = me.add("hypothesis", inv, statement=…, predictions=[…])``"""

    def __init__(self, graph: Graph, name: str):
        self.graph, self.name = graph, name

    def __repr__(self) -> str:
        return f"Author({self.name!r})"

    def investigation(self, title: str, objective: str, **fields) -> dict:
        return self.graph.create(author=self.name, type="investigation",
                                 fields={"title": title, "objective": objective, **fields})

    def add(self, type: str, inv: str = "", links: list | None = None, **fields) -> dict:
        return self.graph.create(author=self.name, type=type, inv=inv, links=links, fields=fields)

    def link(self, src: str, rel: str, dst: str, why: str = "", **data) -> dict:
        return self.graph.link(author=self.name, src=src, rel=rel, dst=dst, why=why, data=data)

    def review(self, target: str, verdict: str, method: str, notes: str) -> dict:
        return self.graph.review(author=self.name, target=target, verdict=verdict, method=method, notes=notes)

    def revise(self, node: str, reason: str, **fields) -> dict:
        return self.graph.revise(author=self.name, node=node, fields=fields, reason=reason)

    def withdraw(self, node: str, why: str) -> dict:
        return self.graph.withdraw(author=self.name, node=node, why=why)

    def take(self, node: str, task: str = "", minutes: int = 240) -> dict:
        return self.graph.lease(author=self.name, node=node, task=task, minutes=minutes)

    def release(self, node: str) -> dict:
        return self.graph.lease(author=self.name, node=node, release=True)


def file_sha256(path: str | os.PathLike) -> dict:
    """sha256 of a file — the whole file, or past 256 MB its first and last 8 MB plus its size (marked partial)."""
    q = Path(path)
    size = q.stat().st_size
    h = hashlib.sha256()
    with q.open("rb") as f:
        if size <= 256 * 1024 * 1024:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
            return {"path": str(q), "sha256": h.hexdigest(), "size": size}
        h.update(f.read(8 << 20))
        f.seek(size - (8 << 20))
        h.update(f.read(8 << 20))
        h.update(str(size).encode())
    return {"path": str(q), "sha256": h.hexdigest(), "size": size, "partial": "first+last 8 MB + size"}

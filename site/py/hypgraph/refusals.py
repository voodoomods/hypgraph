"""
The refusal log: every overclaim the record caught, who wrote it, which rules it broke — and whether its author
then wrote the honest version.

A refused claim never enters the record, so its trace lives here: one append-only table with its own SHA-256 hash
chain, separate from the record's events (verify() on the record is unchanged; verify_refusals() checks this log).

    kind=refused   author, investigation, the statement, the codes and messages it was refused with
    kind=fixed     a later claim (or revision) by the same author in the same investigation that was accepted and
                   says the same thing — matched within FIX_WINDOW by the words it shares with the refused statement
                   (or the same node, for a refused revision). The refusal it fixes is ``ref``.

report() turns it into the numbers worth watching: overclaims caught per author, how many were fixed and how many
abandoned, which rules fire most — "your agents tried to say 'never' 14 times this week; 11 came back honest".
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from . import language as L
from .store import GENESIS, canon, sha

if TYPE_CHECKING:
    from .graph import Graph

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS refusal_log (id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL,
        kind TEXT NOT NULL, author TEXT NOT NULL, inv TEXT NOT NULL DEFAULT '', node TEXT NOT NULL DEFAULT '',
        op TEXT NOT NULL DEFAULT '', statement TEXT NOT NULL DEFAULT '', codes TEXT NOT NULL DEFAULT '[]',
        detail TEXT NOT NULL DEFAULT '{}', ref INTEGER, prev TEXT NOT NULL, hash TEXT NOT NULL)""",
    "CREATE INDEX IF NOT EXISTS idx_refusal_author ON refusal_log(author, inv, at)",
]
FIX_WINDOW = timedelta(hours=24)
FIX_OVERLAP = 0.3                   # Jaccard overlap of content words that counts as "the same claim, said honestly"


def install(con) -> None:
    for stmt in SCHEMA:
        con.execute(stmt)
    for op in ("UPDATE", "DELETE"):
        con.execute(f"CREATE TRIGGER IF NOT EXISTS refusal_log_no_{op.lower()} BEFORE {op} ON refusal_log "
                    "BEGIN SELECT RAISE(ABORT, 'refusal_log is append-only'); END")


def _body(row: dict) -> str:
    return canon({k: row[k] for k in ("at", "kind", "author", "inv", "node", "op", "statement", "codes", "detail",
                                      "ref", "prev")})


def _append(con, row: dict) -> int:
    last = con.execute("SELECT hash FROM refusal_log ORDER BY id DESC LIMIT 1").fetchone()
    row = {**row, "prev": last[0] if last else GENESIS}
    h = sha(_body(row))
    cur = con.execute("INSERT INTO refusal_log (at, kind, author, inv, node, op, statement, codes, detail, ref, prev, "
                      "hash) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                      (row["at"], row["kind"], row["author"], row["inv"], row["node"], row["op"], row["statement"],
                       row["codes"], row["detail"], row["ref"], row["prev"], h))
    return cur.lastrowid


def record_refusal(g: "Graph", *, author: str, op: str, inv: str, node: str, body: dict, problems: list) -> int:
    """Log a refused claim (create or revise). Never raises: a logging problem must not change the refusal."""
    try:
        detail = {"problems": [{k: p.get(k) for k in ("code", "message", "fix")} for p in problems],
                  "kind": body.get("kind") or "finding"}
        row = {"at": g.clock(), "kind": "refused", "author": author, "inv": inv or "", "node": node or "", "op": op,
               "statement": str(body.get("statement") or "")[:1500],
               "codes": canon(sorted({p["code"] for p in problems})), "detail": canon(detail), "ref": None}
        with g._lock:
            return g._transaction(lambda con: _append(con, row))
    except Exception:  # noqa: BLE001
        return 0


def _overlap(a: str, b: str) -> float:
    x, y = L.content_words(a), L.content_words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def match_fix(g: "Graph", *, author: str, inv: str, node: str, statement: str, op: str) -> list[int]:
    """After a claim is accepted: mark the author's recent unresolved refusals in this investigation that it fixes
    (same node for a revision; otherwise statements sharing enough words). Returns the refusal ids it fixed."""
    try:
        con = g._connect()
        since = (datetime.fromisoformat(g.clock()) - FIX_WINDOW).isoformat(timespec="seconds")
        rows = con.execute("SELECT id, node, statement FROM refusal_log WHERE kind='refused' AND author=? AND inv=? "
                           "AND at>=? AND id NOT IN (SELECT ref FROM refusal_log WHERE kind='fixed' AND ref IS NOT "
                           "NULL) ORDER BY id", (author, inv or "", since)).fetchall()
        hits = [r[0] for r in rows if (op == "revise" and r[1] == node) or _overlap(r[2], statement) >= FIX_OVERLAP]
        if not hits:
            return []
        at = g.clock()

        def write(con):
            for rid in hits:
                _append(con, {"at": at, "kind": "fixed", "author": author, "inv": inv or "", "node": node, "op": op,
                              "statement": statement[:1500], "codes": "[]", "detail": "{}", "ref": rid})
        with g._lock:
            g._transaction(write)
        return hits
    except Exception:  # noqa: BLE001
        return []


def rows(g: "Graph", inv: str = "", author: str = "", since: str = "", limit: int = 500) -> list[dict]:
    """Refusals (newest first), each with its codes, messages and what fixed it, if anything."""
    con = g._connect()
    q, args = "SELECT * FROM refusal_log WHERE kind='refused'", []
    for col, val in (("inv", inv), ("author", author)):
        if val:
            q += f" AND {col}=?"
            args.append(val)
    if since:
        q += " AND at>=?"
        args.append(since)
    q += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(int(limit), 5000)))
    cols = [d[0] for d in con.execute("SELECT * FROM refusal_log LIMIT 0").description]
    nodes = g.snapshot().nodes
    fixes = {r[0]: {"node": r[1], "code": (nodes.get(r[1]) or {}).get("code", ""), "at": r[2], "statement": r[3]}
             for r in con.execute("SELECT ref, node, at, statement FROM refusal_log WHERE kind='fixed'")}
    out = []
    for r in con.execute(q, args).fetchall():
        d = dict(zip(cols, r))
        out.append({"id": d["id"], "at": d["at"], "author": d["author"], "inv": d["inv"], "node": d["node"],
                    "op": d["op"], "statement": d["statement"], "codes": json.loads(d["codes"]),
                    "problems": json.loads(d["detail"]).get("problems", []), "fixed_by": fixes.get(d["id"])})
    return out


def report(g: "Graph", inv: str = "", since: str = "") -> dict:
    """The overclaims caught: per author, per rule, fixed vs abandoned, and the latest ones in full."""
    rs = rows(g, inv=inv, since=since, limit=5000)
    by_author: dict[str, dict] = defaultdict(lambda: {"refused": 0, "fixed": 0, "codes": Counter()})
    by_code: Counter = Counter()
    for r in rs:
        a = by_author[r["author"]]
        a["refused"] += 1
        a["fixed"] += bool(r["fixed_by"])
        a["codes"].update(r["codes"])
        by_code.update(r["codes"])
    authors = {k: {"refused": v["refused"], "fixed": v["fixed"], "open": v["refused"] - v["fixed"],
                   "codes": dict(v["codes"].most_common())}
               for k, v in sorted(by_author.items(), key=lambda kv: -kv[1]["refused"])}
    out = {"inv": inv, "since": since, "refused": len(rs), "fixed": sum(1 for r in rs if r["fixed_by"]),
           "by_author": authors, "by_code": dict(by_code.most_common()), "recent": rs[:20]}
    out["markdown"] = markdown(out)
    return out


def markdown(r: dict) -> str:
    if not r["refused"]:
        return "No overclaims caught" + (f" since {r['since']}" if r["since"] else "") + "."
    L_ = [f"## Overclaims caught — {r['refused']} refused, {r['fixed']} came back honest"
          + (f" (since {r['since']})" if r["since"] else ""), "",
          "| author | refused | fixed | open | most common |", "|---|---|---|---|---|"]
    for a, v in r["by_author"].items():
        top = ", ".join(f"{c} ×{n}" for c, n in list(v["codes"].items())[:3])
        L_.append(f"| {a} | {v['refused']} | {v['fixed']} | {v['open']} | {top} |")
    L_ += ["", "| rule | times |", "|---|---|"] + [f"| `{c}` | {n} |" for c, n in r["by_code"].items()]
    L_ += ["", "### Latest", ""]
    for x in r["recent"][:10]:
        fix = f" → fixed as {x['fixed_by']['code'] or x['fixed_by']['node']}" if x["fixed_by"] else " → not fixed"
        L_.append(f"- {x['at'][:16]} **{x['author']}**: “{x['statement'][:140]}” — {', '.join(x['codes'])}{fix}")
    return "\n".join(L_)


def verify(g: "Graph") -> dict:
    """Recompute the refusal log's own hash chain."""
    con = g._connect()
    cols = [d[0] for d in con.execute("SELECT * FROM refusal_log LIMIT 0").description]
    prev, n = GENESIS, 0
    for r in con.execute("SELECT * FROM refusal_log ORDER BY id"):
        d = dict(zip(cols, r))
        if d["prev"] != prev or sha(_body(d)) != d["hash"]:
            return {"ok": False, "broken_at": d["id"], "checked": n}
        prev, n = d["hash"], n + 1
    return {"ok": True, "checked": n, "head": prev}

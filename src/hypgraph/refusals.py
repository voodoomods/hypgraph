"""
The refusal log: every overclaim the record caught, who wrote it, which rules it broke — and whether its author
then wrote the honest version.

A refused claim never enters the record, so its trace lives here: one append-only table with its own SHA-256 hash
chain, separate from the record's events (verify() on the record is unchanged; verify_refusals() checks this log).

    kind=refused   author, investigation, the statement (a result's summary), the codes and messages it was
                   refused with, and the whole body, so the refusal can be replayed against a changed checker;
                   ``detail.type`` says what was refused — a claim or result (an overclaim the checks caught), or
                   ``shape`` / ``link`` (a field, an option or a link the schema doesn't have: friction, not an
                   overclaim, kept apart in the report and skipped by the replay)
    kind=fixed     a later claim or result (or revision) by the same author in the same investigation that was
                   accepted and says the same thing — matched within FIX_WINDOW by the words it shares with the
                   refused statement, for a result also by the value keys it carries again, or the same node for a
                   refused revision. The refusal it fixes is ``ref``.

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
FIX_KEYS = 0.5                      # share of a refused result's value keys that an accepted result must carry again
REPLAYABLE = ("claim", "result")    # node types whose refusals the checker can replay from the logged body


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


def record_refusal(g: "Graph", *, author: str, op: str, inv: str, node: str, body: dict, problems: list,
                   support: list | None = None, type: str = "claim") -> int:
    """Log a refused claim or result (create or revise), with the whole body and the support it had, so the refusal
    can be replayed later against a changed checker. A result's summary stands as its statement. Never raises: a
    logging problem must not change the refusal."""
    try:
        detail = {"problems": [{k: p.get(k) for k in ("code", "message", "fix", "words")} for p in problems],
                  "kind": body.get("kind") or ("finding" if type == "claim" else type), "type": type, "body": body,
                  "support": list(support or [])}
        row = {"at": g.clock(), "kind": "refused", "author": author, "inv": inv or "", "node": node or "", "op": op,
               "statement": str(body.get("statement") or body.get("summary") or "")[:1500],
               "codes": canon(sorted({p["code"] for p in problems})), "detail": canon(detail), "ref": None}
        with g._lock:
            return g._transaction(lambda con: _append(con, row))
    except Exception:  # noqa: BLE001
        return 0


def _overlap(a: str, b: str) -> float:
    x, y = L.content_words(a), L.content_words(b)
    return len(x & y) / len(x | y) if x and y else 0.0


def _keys_again(detail: str, values: dict | None) -> bool:
    """A refused result's value keys, carried again by the accepted one (at least FIX_KEYS of them)."""
    if not values:
        return False
    try:
        was = set((json.loads(detail).get("body") or {}).get("values") or {})
    except Exception:  # noqa: BLE001
        return False
    return bool(was) and len(was & set(values)) / len(was) >= FIX_KEYS


def match_fix(g: "Graph", *, author: str, inv: str, node: str, statement: str, op: str,
              values: dict | None = None) -> list[int]:
    """After a claim or result is accepted: mark the author's recent unresolved refusals in this investigation that
    it fixes (same node for a revision; otherwise statements sharing enough words — for a result, its summary — or
    a result that carries the refused result's value keys again). Returns the refusal ids it fixed."""
    try:
        con = g._connect()
        since = (datetime.fromisoformat(g.clock()) - FIX_WINDOW).isoformat(timespec="seconds")
        rows = con.execute("SELECT id, node, statement, detail FROM refusal_log WHERE kind='refused' AND author=? "
                           "AND inv=? AND at>=? AND id NOT IN (SELECT ref FROM refusal_log WHERE kind='fixed' AND "
                           "ref IS NOT NULL) ORDER BY id", (author, inv or "", since)).fetchall()
        hits = [r[0] for r in rows if (op == "revise" and r[1] == node) or _overlap(r[2], statement) >= FIX_OVERLAP
                or _keys_again(r[3], values)]
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
        try:
            det = json.loads(d["detail"] or "{}")
        except Exception:  # noqa: BLE001
            det = {}
        out.append({"id": d["id"], "at": d["at"], "author": d["author"], "inv": d["inv"], "node": d["node"],
                    "op": d["op"], "statement": d["statement"], "codes": json.loads(d["codes"]),
                    "type": det.get("type") or "claim", "problems": det.get("problems", []),
                    "fixed_by": fixes.get(d["id"])})
    return out


def report(g: "Graph", inv: str = "", since: str = "") -> dict:
    """The overclaims caught: per author, per rule, fixed vs abandoned, and the latest ones in full. Shape and
    link refusals (friction, not overclaims) are counted apart under ``shape``."""
    all_rows = rows(g, inv=inv, since=since, limit=5000)
    rs = [r for r in all_rows if r["type"] in REPLAYABLE]
    shape = [r for r in all_rows if r["type"] not in REPLAYABLE]
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
           "by_author": authors, "by_code": dict(by_code.most_common()), "recent": rs[:20],
           "shape": {"refused": len(shape), "fixed": sum(1 for r in shape if r["fixed_by"]),
                     "by_code": dict(Counter(c for r in shape for c in r["codes"]).most_common()),
                     "by_author": dict(Counter(r["author"] for r in shape).most_common()), "recent": shape[:10]}}
    out["markdown"] = markdown(out)
    return out


def _shape_markdown(sh: dict) -> list[str]:
    if not sh or not sh.get("refused"):
        return []
    L_ = ["", f"### Shape refusals — {sh['refused']} refused, {sh['fixed']} came back accepted",
          "", "A field, an option or a link the schema doesn't have: friction, not overclaims. Each refusal says "
          "where the thing goes.", "", "| code | times |", "|---|---|"]
    L_ += [f"| `{c}` | {n} |" for c, n in sh["by_code"].items()]
    L_ += [""] + [f"- {x['at'][:16]} **{x['author']}**: {(x['problems'] or [{}])[0].get('message', '')[:140]}"
                  for x in sh["recent"][:5]]
    return L_


def markdown(r: dict) -> str:
    if not r["refused"]:
        return ("No overclaims caught" + (f" since {r['since']}" if r["since"] else "") + "."
                + "\n".join(_shape_markdown(r.get("shape") or {})))
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
    L_ += _shape_markdown(r.get("shape") or {})
    return "\n".join(L_)


def _replay_type(d: dict, body) -> str:
    """What a logged refusal was: the logged type, or, for older logs, read off the body."""
    t = d.get("type")
    if t:
        return t
    if isinstance(body, dict) and "statement" not in body and ("summary" in body or "values" in body):
        return "result"
    if d.get("kind") in ("artifact", "source", "decision"):
        return d["kind"]
    return "claim"


def replay(g: "Graph", inv: str = "") -> dict:
    """Run every logged refusal through the checker as it is now. For each: the codes it was refused with, the
    codes it gets today, and the verdict — ``same``, ``changed`` (refused for other reasons), ``passes`` (it would
    enter the record now), or ``partial`` when the log holds only the statement (older logs), so only the
    language rules can be replayed and binding-dependent codes are marked unknown. Claims go through the claim
    checks and the profile's; results through the value and profile result checks, as the author they were
    written by. A refusal that depended on the record's state at the time (RESULT_RESTATES) or on a typed node's
    shape is counted as ``skipped``. The point: a rule change is judged on the real corpus of what agents wrote,
    before it ships."""
    from . import profiles
    from .checks import claim_issues, value_issues
    s = g.snapshot()
    rows_ = rows(g, inv=inv, limit=5000)
    out = []
    skipped = Counter()
    for r in rows_:
        d = {}
        try:
            con = g._connect()
            raw = con.execute("SELECT detail FROM refusal_log WHERE id=?", (r["id"],)).fetchone()
            d = json.loads(raw[0]) if raw else {}
        except Exception:  # noqa: BLE001
            d = {}
        body = d.get("body")
        rtype = _replay_type(d, body)
        if any(c == "RESULT_RESTATES" for c in r["codes"]) or rtype not in REPLAYABLE:
            skipped["RESULT_RESTATES" if any(c == "RESULT_RESTATES" for c in r["codes"]) else rtype] += 1
            continue
        if rtype == "result":
            if not isinstance(body, dict) or r["inv"] not in s.nodes:
                skipped["result without a body"] += 1
                continue
            try:
                now = [p.code for p in value_issues(body)]
                now += [p.code for p in profiles.result_issues(s, r["inv"], body, [], author=r["author"])]
            except Exception as e:  # noqa: BLE001
                now = [f"ERROR {type(e).__name__}"]
            out.append({"id": r["id"], "author": r["author"], "inv": r["inv"], "type": "result",
                        "statement": r["statement"] or str(body.get("summary") or ""), "was": list(r["codes"]),
                        "now": sorted(set(now)), "unknown": [], "full": True,
                        "verdict": "same" if set(now) == set(r["codes"]) else ("passes" if not now else "changed")})
            continue
        full = isinstance(body, dict) and "statement" in body
        if not full:
            body = {"statement": r["statement"], "kind": d.get("kind") or "finding", "scope": "(not logged)"}
        support = [x for x in d.get("support") or [] if x in s.nodes]
        now = []
        if r["inv"] in s.nodes:
            try:
                now = [p.code for p in claim_issues(s, body, support, r["inv"])]
                now += [p.code for p in profiles.claim_issues(s, r["inv"], body, support, [])]
            except Exception as e:  # noqa: BLE001
                now = [f"ERROR {type(e).__name__}"]
        now = sorted(set(now))
        binding = {"UNBOUND_NUMBER", "MEASUREMENT_MALFORMED", "MEASUREMENT_UNKNOWN_FIELD", "MEASUREMENT_MISMATCH",
                   "EVIDENCE_MISSING", "SCOPE_MISSING", "ABSOLUTE_UNDERPOWERED", "ABSOLUTE_HIDES_DENOMINATOR",
                   "ABSOLUTE_UNRELATED_COUNT", "SIGNIFICANCE_NOT_SHOWN", "SIGNIFICANCE_CONTRADICTED",
                   "EXCLUSION_WITHOUT_POWER", "CAUSAL_WITHOUT_INTERVENTION", "UNCORRECTED_EFFECT"}
        if not full:
            now = [c for c in now if c not in binding]
            was = [c for c in r["codes"] if c not in binding]
            unknown = [c for c in r["codes"] if c in binding]
        else:
            was, unknown = list(r["codes"]), []
        if not full and unknown and not was:
            verdict = "unknown"
        elif not now and (full or not unknown):
            verdict = "passes"
        elif not now:
            verdict = "language passes"
        elif set(now) == set(was):
            verdict = "same"
        else:
            verdict = "changed"
        out.append({"id": r["id"], "author": r["author"], "inv": r["inv"], "type": "claim",
                    "statement": r["statement"], "was": r["codes"], "now": now, "unknown": unknown, "full": full,
                    "verdict": verdict})
    tally = Counter(x["verdict"] for x in out)
    by_code: dict = defaultdict(Counter)
    for x in out:
        for c in x["was"]:
            by_code[c][x["verdict"]] += 1
    return {"replayed": len(out), "verdicts": dict(tally), "skipped": dict(skipped),
            "by_code": {k: dict(v) for k, v in by_code.items()}, "rows": out}


def replay_markdown(r: dict) -> str:
    L_ = [f"## Refusals replayed — {r['replayed']}: " + ", ".join(f"{k} {v}" for k, v in sorted(r["verdicts"].items()))
          + (" (skipped: " + ", ".join(f"{k} {v}" for k, v in sorted(r["skipped"].items())) + ")"
             if r.get("skipped") else ""),
          "", "| refused as | same | changed | passes | language passes | unknown |", "|---|---|---|---|---|---|"]
    for c, v in sorted(r["by_code"].items(), key=lambda kv: -sum(kv[1].values())):
        L_.append(f"| `{c}` | {v.get('same', 0)} | {v.get('changed', 0)} | {v.get('passes', 0)} | "
                  f"{v.get('language passes', 0)} | {v.get('unknown', 0)} |")
    moved = [x for x in r["rows"] if x["verdict"] in ("passes", "language passes", "changed")]
    if moved:
        L_ += ["", "### Would be treated differently now", ""]
        for x in moved[:40]:
            L_.append(f"- **{x['verdict']}** ({', '.join(x['was'])} → {', '.join(x['now']) or 'accepted'}): "
                      f"“{x['statement'][:160]}”")
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

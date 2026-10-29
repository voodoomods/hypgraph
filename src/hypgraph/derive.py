"""
Standing, derived on every read. Nothing here is stored or settable:

  lifecycle   active | superseded | withdrawn            (withdrawals, supersede / correct edges)
  review      unchecked | checked | contested | needs_revalidation   (reviews pinned to versions; reviewers only)
  execution   for runs: queued | running | succeeded | failed | …     (as recorded)
  outcome     for results: positive | negative | inconclusive | expected_failure | skipped | failed
  evidence    for claims and hypotheses, the strongest live support: external > new_data > separate_implementation
              > project_rerun > lab_recorded > agent_reported > unverified
  lines       independent lines of support (lines sharing a run, a data artifact or a source count once)
  at_risk     the fallen nodes it rests on; ``unsupported`` when every support it had has fallen
  stale       for results and claims: the run used an artifact that is now superseded or withdrawn (a newer diff, a
              corrected data file, a changed instance), or ``valid_until`` has passed — the evidence no longer speaks
              for the thing it measured. A claim is stale when every result behind it is.

A profile's workflow may widen what counts as resting on (EXTRA_RISKY: ``uses``, ``cites``); it is read per
investigation, so records under the frozen ``@1`` profiles keep exactly the standing they had.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from . import language as lang
from . import stats
from .policy import Policy
from .schema import NEGATIVE, POSITIVE, PROFILE_LABEL, PROFILE_RANK, RISKY, SAME_TYPE


class Snap:
    """The whole graph at one event, in memory. Built by Graph.snapshot(); treat it as read-only."""

    def __init__(self, seq: int, policy: Policy):
        self.seq = seq
        self.policy = policy
        self.nodes: dict[str, dict] = {}
        self.edges: dict[int, dict] = {}
        self.out: dict[str, list] = defaultdict(list)
        self.inn: dict[str, list] = defaultdict(list)
        self.withdrawn: dict[str, dict] = {}
        self.leases: dict[str, dict] = {}
        self._state: dict[str, dict] = {}
        # result signatures by node (keyed on the body they were taken from, so a later snapshot can share them),
        # and per investigation an index of its live results by the numbers they carry — built on first use
        self._sigs: dict[str, tuple] = {}
        self._results: dict[str, tuple] = {}
        self.sig: Any = None
        self.versions: dict[str, list] = defaultdict(list)
        self.events: list[dict] = []
        self.now: str = ""                       # the clock at the last snapshot() — freshness is read against it
        # highest rowid / id loaded per table: every table is append-only, so a later read loads only what's newer
        self.marks: dict[str, int] = {"nodes": 0, "versions": 0, "edges": 0, "withdrawals": 0, "leases": 0}


def board(s: Snap, nid: str) -> set:
    """Whose verdicts count on this node: the policy's reviewers, the investigation's own, and the curators."""
    inv = s.nodes.get(s.nodes[nid]["inv"]) if nid in s.nodes else None
    extra = set((inv or {}).get("body", {}).get("reviewers") or [])
    return set(s.policy.reviewers) | extra | set(s.policy.curators)


def lifecycle(s: Snap, nid: str, _seen: frozenset = frozenset()) -> str:
    if nid in s.withdrawn:
        return "withdrawn"
    for e in s.inn.get(nid, []):
        # superseded by a replacement that is live, or itself superseded by one that is: a chain of replacements
        # ends in a live node (a withdrawn replacement replaces nothing). A cycle can't recurse forever.
        if e["rel"] in SAME_TYPE and e["src"] not in _seen and \
                lifecycle(s, e["src"], _seen | {nid}) in ("active", "superseded"):
            return "superseded"
    n = s.nodes[nid]
    if n["type"] == "investigation":
        return n["body"].get("state") or "active"
    return "active"


def review_state(s: Snap, nid: str) -> dict:
    """Reviews by board members, pinned to versions. An objection stays open until its reviewer (or a curator, or one
    of the investigation's own reviewers) records ``resolved``; a negative verdict on the current version contests."""
    n = s.nodes[nid]
    brd = board(s, nid)
    inv = s.nodes.get(n["inv"]) or {}
    leads = set((inv.get("body") or {}).get("reviewers") or []) | set(s.policy.curators)
    rows = []
    for e in s.inn.get(nid, []):
        if e["rel"] != "reviews":
            continue
        r = s.nodes.get(e["src"])
        if not r or r["id"] in s.withdrawn:
            continue
        rows.append({"review": r["id"], "by": r["created_by"], "verdict": r["body"].get("verdict"),
                     "on_v": e["dst_v"] or 0, "at": r["created_at"],
                     "official": bool(r["body"].get("official", r["created_by"] in brd))})
    rows.sort(key=lambda x: x["at"])
    official = [x for x in rows if x["official"] and x["verdict"] != "comment"]
    open_obj: dict[str, dict] = {}
    for x in official:
        if x["verdict"] == "objection":
            open_obj[x["by"]] = x
        elif x["verdict"] == "resolved":
            if x["by"] in leads:                 # curators and the investigation's lead reviewers settle any dispute;
                open_obj.clear()                 # everyone else, their own
            else:
                open_obj.pop(x["by"], None)
    cur = [x for x in official if x["on_v"] == n["v"]]
    latest: dict[str, dict] = {}
    for x in cur:
        if x["verdict"] not in ("objection", "resolved"):
            latest[x["by"]] = x
    positive = sorted({f"{x['by']}:{x['verdict']}" for x in latest.values() if x["verdict"] in POSITIVE})
    negative = sorted({f"{x['by']}:{x['verdict']}" for x in latest.values() if x["verdict"] in NEGATIVE})
    if open_obj or negative:
        st = "contested"
    elif positive:
        st = "checked"
    elif any(x["verdict"] in POSITIVE for x in official if x["on_v"] < n["v"]):
        st = "needs_revalidation"
    else:
        st = "unchecked"
    return {"state": st, "positive": positive, "negative": negative,
            "open_objections": [{"by": x["by"], "review": x["review"]} for x in open_obj.values()],
            "reviews": len(rows), "comments": sum(1 for x in rows if not x["official"] or x["verdict"] == "comment")}


def fallen(s: Snap, nid: str) -> bool:
    """Broken as a premise: withdrawn, contested, or a failed run / result. A superseded node is NOT fallen — it was
    refined, not refuted — so what rests on it is flagged softly (rests_on_superseded), not put AT RISK."""
    n = s.nodes[nid]
    if lifecycle(s, nid) == "withdrawn":
        return True
    if n["type"] in ("claim", "result", "hypothesis") and review_state(s, nid)["state"] == "contested":
        return True
    if n["type"] == "run" and n["body"].get("state") in ("failed", "timeout", "cancelled", "interrupted"):
        return True
    if n["type"] == "result" and n["body"].get("outcome") == "failed":
        return True
    return False


# profile id → relations its workflow adds to RISKY (filled by profiles.py; read per investigation)
EXTRA_RISKY: dict[str, tuple] = {}


def risky(s: Snap, x: str) -> tuple:
    """The relations along which x rests on something: the kernel's, plus its investigation's workflow's."""
    inv = s.nodes.get(s.nodes[x]["inv"]) if x in s.nodes else None
    pid = str((inv or {}).get("body", {}).get("profile") or "").lower()
    extra = EXTRA_RISKY.get(pid) if pid else None
    return RISKY + extra if extra else RISKY


def workflow_profile(s: Snap, x: str) -> bool:
    """Whether x's investigation runs a profile with a workflow (the @2 profiles): freshness rules that need the files
    to be registered apply only there."""
    inv = s.nodes.get(s.nodes[x]["inv"]) if x in s.nodes else None
    pid = str((inv or {}).get("body", {}).get("profile") or "").lower()
    return bool(pid) and pid in EXTRA_RISKY


def upstream(s: Snap, x: str) -> list[tuple[str, str]]:
    """What x rests on, one step: premises (requires), derivations, a decision's basis, and the run that produced it.
    Support is counted separately (unsupported): one fallen support among several doesn't break a claim."""
    rk = risky(s, x)
    ups = [(e["dst"], e["rel"]) for e in s.out.get(x, []) if e["rel"] in rk]
    ups += [(e["src"], "produced_by") for e in s.inn.get(x, []) if e["rel"] == "produced"]
    return ups


def downstream(s: Snap, x: str) -> list[tuple[str, str]]:
    """What rests on x, one step: the inverse of upstream, plus what x supports."""
    downs = [(e["src"], e["rel"]) for e in s.inn.get(x, []) if e["rel"] in risky(s, e["src"])]
    downs += [(e["dst"], "produced") for e in s.out.get(x, []) if e["rel"] == "produced"]
    downs += [(e["dst"], "supports") for e in s.out.get(x, []) if e["rel"] == "supports"]
    return downs


def excerpts(s: Snap, sid: str) -> list[str]:
    """The pages a host fetched for a source: artifacts ``kind=excerpt`` derived_from it (oldest first)."""
    return [e["src"] for e in s.inn.get(sid, []) if e["rel"] == "derived_from"
            and s.nodes[e["src"]]["type"] == "artifact" and (s.nodes[e["src"]]["body"].get("kind") or "") == "excerpt"]


def _order(s: Snap) -> tuple[dict, dict, dict]:
    """When each node was created, each edge linked and each node withdrawn, as event sequence numbers (timestamps
    are only to the second). Cached on the snapshot until the next event."""
    cached = getattr(s, "_order_cache", None)
    if cached and cached[0] == s.seq:
        return cached[1]
    made: dict[str, int] = {}
    linked: dict[int, int] = {}
    gone: dict[str, int] = {}
    for e in s.events:
        if e["kind"] == "create":
            made.setdefault(e["ref"], e["seq"])
        elif e["kind"] == "link" and isinstance(e.get("payload"), dict) and e["payload"].get("edge") is not None:
            linked[int(e["payload"]["edge"])] = e["seq"]
        elif e["kind"] == "withdraw":
            gone.setdefault(e["ref"], e["seq"])
    out = (made, linked, gone)
    s._order_cache = (s.seq, out)                      # type: ignore[attr-defined]
    return out


def _moved_since(s: Snap, rid: str) -> list[str]:
    """Input files of the result's investigation that were replaced or withdrawn after the result was written. A run
    output (an artifact some run produced) and a page excerpt (a re-fetch supersedes it every time) don't count, and a
    file registered on other questions only (``part_of``) doesn't count against a result on a different one."""
    from .workflow import question_of                  # workflow imports derive; read lazily
    made, linked, gone = _order(s)
    t = made.get(rid)
    if t is None:
        return []
    inv = s.nodes[rid]["inv"]
    q: set | None = None
    out = []
    for aid, a in s.nodes.items():
        if a["type"] != "artifact" or a["inv"] != inv or (a["body"].get("kind") or "") == "excerpt":
            continue
        if any(e["rel"] == "produced" for e in s.inn.get(aid, [])):
            continue
        on = {e["dst"] for e in s.out.get(aid, []) if e["rel"] == "part_of" and s.nodes[e["dst"]]["type"] == "question"}
        if on:
            if q is None:
                # a result reaches its question through the claims built on it, as often as through its run
                qs = {question_of(s, rid)} | {question_of(s, e["src"]) for e in s.inn.get(rid, [])
                                               if e["rel"] == "derived_from"}
                qs |= {question_of(s, e["dst"]) for e in s.out.get(rid, []) if e["rel"] == "supports"}
                q = {x for x in qs if x}
            if q and not (q & on):
                continue
        when = [linked.get(e["id"], 0) for e in s.inn.get(aid, []) if e["rel"] == "supersedes"]
        if aid in gone:
            when.append(gone[aid])
        if any(w > t for w in when):
            out.append(a["code"] or aid)
    return out


def _open_answers(s: Snap, q: str) -> list[str]:
    return [e["src"] for e in s.inn.get(q, []) if e["rel"] == "answers" and s.nodes[e["src"]]["type"] == "claim"
            and lifecycle(s, e["src"]) == "active" and not fallen(s, e["src"]) and not stale(s, e["src"])
            and (state(s, e["src"]).get("review") or {}).get("state") != "checked"]


def reviewable(s: Snap, nid: str) -> bool:
    """Someone besides its author (and the curators) may review it."""
    return bool(board(s, nid) - set(s.policy.curators) - {s.nodes[nid]["created_by"]})


def unchecked_answers(s: Snap, q: str) -> list[str]:
    """Live, fresh claims answering question ``q`` that no reviewer has checked and one could. A question settles only
    when this is empty: a checked answer beside a live unchecked one is two answers the record hasn't reconciled, and
    they may disagree (studies T1: "no look-ahead" checked while "is look-ahead" stood unchecked on the same
    question). An answer nobody may review (its author is the only reviewer) can't block it; ``unreviewable_answers``
    lists those."""
    return [c for c in _open_answers(s, q) if reviewable(s, c)]


def unreviewable_answers(s: Snap, q: str) -> list[str]:
    return [c for c in _open_answers(s, q) if not reviewable(s, c)]


def stale(s: Snap, nid: str) -> list[str]:
    """Why a result (or a claim through its results) no longer speaks for what it measured; [] when fresh. A result
    is stale when the run that produced it used an artifact that is now superseded or withdrawn, or when its
    ``valid_until`` has passed. Under a workflow, a result whose run names no file it read (no ``uses``) is stale once
    any input file of its investigation is replaced or withdrawn after it was written: nothing shows it read the
    new one. A source is stale when the host re-fetched its page and the page as it is now no
    longer contains its passage (the live excerpt says ``contains_passage: false``), or every excerpt of it was
    superseded. A claim is stale when it has results or cited sources and every one of them is stale."""
    n = s.nodes[nid]
    if n["type"] == "source":
        ex = excerpts(s, nid)
        if not ex:
            return []                                  # never re-fetched: nothing says the page moved
        live = [a for a in ex if lifecycle(s, a) == "active"]
        if not live:
            return [f"its page changed since it was read ({', '.join(s.nodes[a]['code'] or a for a in ex[-2:])} "
                    "superseded)"]
        meta = [s.nodes[a]["body"].get("meta") or {} for a in live]
        if all(m.get("contains_passage") is False for m in meta):
            when = max((str(m.get("fetched") or "") for m in meta), default="")
            return [f"the page no longer contains its passage (re-fetched{' ' + when if when else ''})"]
        return []
    if n["type"] == "result":
        out = []
        run = producing_run(s, nid)
        for e in (s.out.get(run, []) if run else []):
            if e["rel"] != "uses":
                continue
            lc = lifecycle(s, e["dst"])
            if lc != "active":
                a = s.nodes[e["dst"]]
                kind = a["body"].get("kind") or "artifact"
                out.append(f"{kind} {a['code'] or e['dst']} is {lc}")
        named = run and any(e["rel"] == "uses" for e in s.out.get(run, []))
        if not named and workflow_profile(s, nid):
            moved = _moved_since(s, nid)
            if moved:
                out.append(f"it names no file it read, and {', '.join(moved[:3])} changed after it was written")
        vu = str(n["body"].get("valid_until") or "").strip()
        if vu and s.now and s.now[:len(vu)] > vu:
            out.append(f"valid_until {vu} has passed")
        return out
    if n["type"] == "decision":
        # a decision is stale when everything it was based on is (a position taken on a backtest the vendor corrected)
        basis = [e["dst"] for e in s.out.get(nid, []) if e["rel"] == "based_on" and not fallen(s, e["dst"])]
        reasons = [stale(s, b) for b in basis]
        if basis and all(reasons):
            return list(dict.fromkeys(x for r in reasons for x in r))
        return []
    if n["type"] == "claim":
        rs = [e["src"] for e in s.inn.get(nid, []) if e["rel"] == "supports" and s.nodes[e["src"]]["type"] == "result"
              and not fallen(s, e["src"])]
        rs += [e["dst"] for e in s.out.get(nid, []) if e["rel"] == "derived_from" and s.nodes[e["dst"]]["type"] == "result"
               and not fallen(s, e["dst"])]
        rs += [e["dst"] for e in s.out.get(nid, []) if e["rel"] == "cites" and s.nodes[e["dst"]]["type"] == "source"
               and lifecycle(s, e["dst"]) == "active" and not fallen(s, e["dst"])]
        rs = list(dict.fromkeys(rs))
        if not rs:
            return []
        reasons = [stale(s, r) for r in rs]
        if all(reasons):
            return list(dict.fromkeys(x for r in reasons for x in r))
    return []


def walk(s: Snap, nid: str, step, limit: int) -> list[tuple[str, str, int]]:
    seen, out, frontier = {nid}, [], [(nid, 0)]
    while frontier and len(out) < limit:
        nxt = []
        for x, d in frontier:
            for y, rel in step(s, x):
                if y not in seen:
                    seen.add(y)
                    out.append((y, rel, d + 1))
                    nxt.append((y, d + 1))
        frontier = nxt
    return out


def ancestors(s: Snap, nid: str, limit: int = 500) -> list[tuple[str, str, int]]:
    return walk(s, nid, upstream, limit)


def dependents(s: Snap, nid: str, limit: int = 500) -> list[tuple[str, str, int]]:
    return walk(s, nid, downstream, limit)


def supporters(s: Snap, nid: str) -> list[dict]:
    """What stands behind a node: every `supports` edge into it, and — for a claim — the results it is derived from
    and the results its measurements bind (each once). A claim that binds its numbers to a result rests on that
    result whether or not anyone also wrote `supports`; until 0.7.4 only the edge counted, and most honest claims
    read "no live support" with their evidence "unverified"."""
    out = [e for e in s.inn.get(nid, []) if e["rel"] == "supports"]
    n = s.nodes.get(nid)
    if n and n["type"] == "claim":
        seen = {e["src"] for e in out}
        for e in s.out.get(nid, []):
            if e["rel"] == "derived_from" and e["dst"] in s.nodes and s.nodes[e["dst"]]["type"] == "result" \
                    and e["dst"] not in seen:
                seen.add(e["dst"])
                out.append({"src": e["dst"], "rel": "derived_from", "dst": nid, "data": {}, "by": n["created_by"]})
        for m in n["body"].get("measurements") or []:
            rid = m.get("result") if isinstance(m, dict) else None
            if rid and rid in s.nodes and s.nodes[rid]["type"] == "result" and rid not in seen:
                seen.add(rid)
                out.append({"src": rid, "rel": "measurement", "dst": nid, "data": {}, "by": n["created_by"]})
    return out


def at_risk(s: Snap, nid: str) -> list[str]:
    return list(dict.fromkeys(a for a, _r, _d in ancestors(s, nid) if fallen(s, a)))


def rests_on_superseded(s: Snap, nid: str) -> list[str]:
    return [a for a, _r, _d in ancestors(s, nid) if lifecycle(s, a) == "superseded"]


def out_of_play(s: Snap, nid: str) -> bool:
    return fallen(s, nid) or lifecycle(s, nid) == "superseded"


def unsupported(s: Snap, nid: str) -> bool:
    sup = supporters(s, nid)
    return bool(sup) and all(fallen(s, e["src"]) for e in sup)


def producing_run(s: Snap, rid: str) -> Optional[str]:
    for e in s.inn.get(rid, []):
        if e["rel"] == "produced":
            return e["src"]
    for e in s.out.get(rid, []):
        if e["rel"] == "derived_from" and s.nodes[e["dst"]]["type"] == "run":
            return e["dst"]
    return None


def line_profile(s: Snap, src: str, depth: int = 0) -> str:
    n = s.nodes[src]
    if n["type"] == "source":
        return "external"
    if n["type"] == "claim":
        return profile(s, src, depth + 1) if depth < 4 else "unverified"
    run = producing_run(s, src)
    if not run:
        # "cited" counts as outside evidence only when it cites a source node; the word alone is a report
        cites = any(e["rel"] == "cites" and s.nodes[e["dst"]]["type"] == "source" and not fallen(s, e["dst"])
                    for e in s.out.get(src, []))
        return "external" if n["body"].get("kind") == "cited" and cites else "unverified"
    rb = s.nodes[run]["body"]
    # Lab-recorded means the instrument filed this result itself (only it adds `produced` from a lab run). A result
    # someone derived from a lab run, or a run they call "external", is their report; outside evidence is a source.
    by_lab = rb.get("kind") == "lab" and any(e["rel"] == "produced" and e["src"] == run for e in s.inn.get(src, []))
    best = "lab_recorded" if by_lab else "agent_reported"
    for e in s.out.get(run, []) + s.inn.get(run, []):
        if e["rel"] == "replicates" and not fallen(s, e["src"]):
            k = {"same_code": "project_rerun", "new_seed": "project_rerun", "new_env": "project_rerun",
                 "new_impl": "separate_implementation", "new_data": "new_data"}.get(e["data"].get("differs"),
                                                                                    "project_rerun")
            if PROFILE_RANK.index(k) > PROFILE_RANK.index(best):
                best = k
    return best


def profile(s: Snap, nid: str, depth: int = 0) -> str:
    lines = [e["src"] for e in supporters(s, nid) if not fallen(s, e["src"])]
    if not lines:
        return "unverified"
    return max((line_profile(s, x, depth) for x in lines), key=PROFILE_RANK.index)


def roots(s: Snap, src: str) -> set[str]:
    """What a line of evidence is made of: its run(s) and the data / model artifacts they used, its sources."""
    out: set[str] = set()
    stack, seen = [src], set()
    while stack and len(seen) < 200:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        n = s.nodes[x]
        if n["type"] == "run":
            out.add(x)
            for e in s.out.get(x, []):
                if e["rel"] == "uses" and (e["data"].get("role") or "data") in ("data", "model"):
                    out.add(e["dst"])
            continue
        if n["type"] in ("artifact", "source"):
            out.add(x)
            continue
        run = producing_run(s, x)
        if run:
            stack.append(run)
        for e in s.out.get(x, []):
            if e["rel"] in ("derived_from",):
                stack.append(e["dst"])
        if n["type"] == "claim":
            for e in supporters(s, x):
                stack.append(e["src"])
    # No recorded run, data or source behind it: we can't tell these lines apart, so they all count as one
    # (conservative — three unprovenanced reports may well be one result repeated).
    return out or {"(no provenance)"}


def independent_lines(s: Snap, nid: str) -> int:
    """Support lines that share no run, data artifact or source count separately; any overlap merges them."""
    lines = [e["src"] for e in supporters(s, nid) if not fallen(s, e["src"])]
    groups: list[set] = []
    for x in lines:
        r = roots(s, x)
        merged = [g for g in groups if g & r]
        for g in merged:
            groups.remove(g)
            r |= g
        groups.append(r)
    return len(groups)


def result_signature(body: dict) -> tuple | None:
    """The numbers a result carries, as a sorted tuple rounded to 4 decimals, keys ignored (two authors name the
    same measurement differently). None when fewer than two numbers, or none of them is away from zero."""
    nums = []
    for v in (body.get("values") or {}).values():
        if isinstance(v, dict):
            nums += [round(float(x), 4) for x in v.values() if isinstance(x, (int, float)) and not isinstance(x, bool)]
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            nums.append(round(float(v), 4))
    if len(nums) < 2 or not any(abs(x) >= 1e-4 for x in nums):
        return None
    if all(x.is_integer() and abs(x) <= 12 for x in nums):     # 0 of 3 is a coincidence waiting to happen
        return None
    return tuple(sorted(nums))


def signature_of(s: Snap, nid: str) -> tuple | None:
    """result_signature of a node's current body, computed once per body. Keyed on the body object itself (held, so
    its identity can't be reused): a revision brings a new body, and so does a write that re-stages one."""
    n = s.nodes[nid]
    hit = s._sigs.get(nid)
    if hit is not None and hit[0] is n["body"]:
        return hit[1]
    sig = result_signature(n["body"])
    s._sigs[nid] = (n["body"], sig)
    return sig


def result_index(s: Snap, inv: str) -> tuple[dict, dict]:
    """The investigation's results: (number → the live results carrying it, result → (created_at, its position in
    the graph)). Built once per snapshot, so checking every result costs what the matches cost, not one pass over
    the graph each. The position is write order, so it breaks ties within a second."""
    idx = s._results.get(inv)
    if idx is None:
        by_num: dict[float, set] = defaultdict(set)
        order: dict[str, tuple] = {}
        for pos, (i, m) in enumerate(s.nodes.items()):
            if m["type"] != "result" or m["inv"] != inv:
                continue
            order[i] = (m["created_at"], pos)
            sig = None if i in s.withdrawn else signature_of(s, i)
            for x in set(sig or ()):
                by_num[x].add(i)
        idx = s._results[inv] = (by_num, order)
    return idx


def repeating(s: Snap, sig: tuple, inv: str) -> list[str]:
    """Live results in the investigation whose numbers contain all of ``sig`` (as a multiset), in graph order."""
    by_num, order = result_index(s, inv)
    cands: set | None = None
    for x in set(sig):
        ids = by_num.get(x)
        if not ids:
            return []
        cands = set(ids) if cands is None else cands & ids
        if not cands:
            return []
    out = []
    for i in sorted(cands or (), key=lambda i: order[i][1]):
        pool = list(signature_of(s, i) or ())
        if all(_take(pool, x) for x in sig):
            out.append(i)
    return out


def restates(s: Snap, nid: str) -> list[str]:
    """Earlier live results in the same investigation whose numbers this result repeats (the same multiset, or a
    subset of it): one measurement written twice is one line of evidence, however many times it is written.
    Earlier is by created_at, then by write order — never by id, which would let a result written later count as
    earlier and change what an older result restates, after its standing was derived and carried forward."""
    n = s.nodes[nid]
    sig = signature_of(s, nid)
    if not sig:
        return []
    _, order = result_index(s, n["inv"])
    mine = order[nid]
    return [i for i in repeating(s, sig, n["inv"]) if i != nid and order[i] < mine]


def _take(pool: list, x: float) -> bool:
    try:
        pool.remove(x)
        return True
    except ValueError:
        return False


def result_value(s: Snap, rid: str, key: str) -> Optional[dict]:
    """A result's value under ``key`` as a dict ({"value": …} for a bare number), or None."""
    r = s.nodes.get(rid)
    if not r or r["type"] != "result":
        return None
    v = (r["body"].get("values") or {}).get(key)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return {"value": v}
    return v if isinstance(v, dict) else None


def bounds(s: Snap, nid: str) -> list[dict]:
    """For each count (k of n) a claim binds: the rate and its 95% bounds — what the count actually supports. At
    k = 0 the upper bound is the exact one-sided 1 - 0.05^(1/n): "never, in n trials" means "below this"."""
    body = s.nodes[nid]["body"]
    out = []
    for m in body.get("measurements") or []:
        if not isinstance(m, dict):
            continue
        rv = result_value(s, str(m.get("result") or ""), str(m.get("key") or ""))
        k, n = (rv or {}).get("k"), (rv or {}).get("n")
        if not (isinstance(k, (int, float)) and isinstance(n, (int, float)) and n > 0 and 0 <= k <= n):
            continue
        lo, hi = stats.rate_bounds(int(k), int(n))
        row = {"name": m.get("name") or m.get("key"), "k": int(k), "n": int(n), "rate": k / n, "lo": lo, "hi": hi}
        x = body.get("exposure")
        if isinstance(x, (int, float)) and x > 0:
            row["exposure"] = x
            row["unruled_out"] = round((hi if k == 0 else 1 - lo) * x)
        out.append(row)
    return out


def basis_changed(s: Snap, nid: str) -> list[dict]:
    """A decision's basis that is no longer what the decision saw: a node revised since the decision cited it."""
    out = []
    for e in s.out.get(nid, []):
        if e["rel"] != "based_on":
            continue
        cur = s.nodes[e["dst"]]["v"]
        if e["dst_v"] and cur > e["dst_v"]:
            out.append({"node": e["dst"], "code": s.nodes[e["dst"]]["code"], "was_v": e["dst_v"], "now_v": cur})
    return out


# What a node's standing reads. Out-edges: what it rests on or is made of. In-edges: what reviews, supports,
# challenges, supersedes or produced it. A change at y can alter the standing of x only if x reads y this way —
# directly, or through a chain (at-risk and evidence are transitive).
_READS_OUT = {"requires", "derived_from", "based_on", "cites", "uses", "replicates", "works_on", "rests_on"}
_READS_IN = {"reviews", "supports", "challenges", "supersedes", "corrects", "produced", "replicates"}


def affected_by(s: Snap, touched: set) -> set:
    """Every node whose derived standing can have changed when ``touched`` changed: the touched nodes and,
    transitively, everything that reads them. A touched investigation (its reviewers, strictness, state) affects
    every node in it. Used to keep cached standing across a write instead of re-deriving the whole graph."""
    out: set = set()
    stack = [x for x in touched if x in s.nodes]
    invs = {x for x in stack if s.nodes[x]["type"] == "investigation"}
    if invs:
        stack += [i for i, n in s.nodes.items() if n["inv"] in invs]
    # a changed file reaches the results that name no file through no edge (see stale): under a workflow, every such
    # result in the file's investigation may have gone stale
    moved = {s.nodes[x]["inv"] for x in stack if s.nodes[x]["type"] == "artifact"}
    if moved:
        for i, n in s.nodes.items():
            if n["type"] == "result" and n["inv"] in moved and workflow_profile(s, i):
                run = producing_run(s, i)
                if not (run and any(e["rel"] == "uses" for e in s.out.get(run, []))):
                    stack.append(i)
    # a result reaches, through no edge, the results that repeat its numbers (see restates): revising or withdrawing
    # it can change what they restate. Every version's numbers count — the results that repeated the old ones too.
    for x in [x for x in stack if s.nodes[x]["type"] == "result"]:
        by_num, _ = result_index(s, s.nodes[x]["inv"])
        nums = {v for ver in s.versions.get(x, ()) for v in (result_signature(ver["body"]) or ())}
        nums |= set(signature_of(s, x) or ())
        for v in nums:
            stack += [i for i in by_num.get(v, ()) if i != x]
    while stack:
        y = stack.pop()
        if y in out:
            continue
        out.add(y)
        stack += [e["src"] for e in s.inn.get(y, ()) if e["rel"] in _READS_OUT and e["src"] not in out]
        stack += [e["dst"] for e in s.out.get(y, ()) if e["rel"] in _READS_IN and e["dst"] not in out]
    return out


def state(s: Snap, nid: str) -> dict:
    """Every standing dimension of a node, plus one honest sentence. Cached on the snapshot."""
    if nid in s._state:
        return s._state[nid]
    n = s.nodes[nid]
    t = n["type"]
    st: dict[str, Any] = {"lifecycle": lifecycle(s, nid)}
    if t in ("claim", "result", "run", "experiment", "hypothesis"):
        st["review"] = review_state(s, nid)
    if t == "run":
        st["execution"] = n["body"].get("state") or "unknown"
    if t == "result":
        st["outcome"] = n["body"].get("outcome") or "unstated"
        rs = restates(s, nid)
        if rs:
            st["restates"] = rs
    if t == "claim":
        b = bounds(s, nid)
        if b:
            st["bounds"] = b
        if len(b) >= 2 and lang.found(lang.SIGNIFICANCE, n["body"].get("statement", "")):   # asserted or denied
            st["test"] = stats.two_proportions(b[0]["k"], b[0]["n"], b[1]["k"], b[1]["n"])
    if t in ("claim", "hypothesis"):
        st["evidence"] = profile(s, nid)
        st["independent_lines"] = independent_lines(s, nid)
        st["challenges"] = sum(1 for e in s.inn.get(nid, []) if e["rel"] == "challenges" and not fallen(s, e["src"]))
        st["unsupported"] = unsupported(s, nid)
    if t == "decision":
        moved = basis_changed(s, nid)
        if moved:
            st["basis_changed"] = moved
    if t in ("result", "claim", "source", "decision"):
        old = stale(s, nid)
        if old:
            st["stale"] = old
    risk = at_risk(s, nid)
    if risk:
        st["at_risk"] = risk
    older = rests_on_superseded(s, nid)
    if older:
        st["rests_on_superseded"] = older
    if nid in s.leases:
        L = s.leases[nid]
        st["lease"] = {"agent": L["agent"], "task": L["task"], "expires": L["expires"]}
    st["fallen"] = fallen(s, nid)
    st["sentence"] = sentence(s, nid, st)
    s._state[nid] = st
    return st


def sentence(s: Snap, nid: str, st: dict) -> str:
    """The node's standing in one honest line."""
    n = s.nodes[nid]
    parts = [f"{st['lifecycle']} {n['type']}"]
    rv = st.get("review")
    if rv:
        if rv["state"] == "checked":
            parts.append("checked (" + ", ".join(rv["positive"]) + f", v{n['v']})")
        elif rv["state"] == "contested":
            who = [o["by"] for o in rv["open_objections"]] + rv["negative"]
            parts.append("CONTESTED (" + ", ".join(who) + ")")
        elif rv["state"] == "needs_revalidation":
            parts.append(f"review stale — v{n['v']} not yet re-checked")
        else:
            parts.append("unchecked")
    if "execution" in st:
        parts.append(st["execution"])
    if "outcome" in st:
        parts.append(f"outcome {st['outcome']}")
    if st.get("restates"):
        parts.append("RESTATES " + ", ".join(s.nodes[r]["code"] or r for r in st["restates"][:4]))
    if "evidence" in st:
        k = st["independent_lines"]
        parts.append(f"{k} independent line{'s' if k != 1 else ''} of support" if k else "no live support")
        parts.append(PROFILE_LABEL[st["evidence"]])
        if st["evidence"] != "external":
            parts.append("no external replication")
        if st.get("challenges"):
            parts.append(f"{st['challenges']} challenge(s)")
        if st.get("unsupported"):
            parts.append("UNSUPPORTED — every support has fallen")
    absolute = lang.asserted(lang.ABSOLUTE, n["body"].get("statement", "")) if n["type"] == "claim" else []
    for b in st.get("bounds") or []:
        if b["k"] in (0, b["n"]) and (absolute or b.get("unruled_out") is not None):
            worst = b["hi"] if b["k"] == 0 else 1 - b["lo"]
            label = f"'{absolute[0]}' = at most" if absolute else f"{b['k']} of {b['n']:,} = at most"
            note = f"{label} {stats.pct(worst)} ({b['k']} of {b['n']:,}, 95%)" if absolute else \
                f"{label} {stats.pct(worst)} at 95%"
            if b.get("unruled_out") is not None:
                note += f", up to {b['unruled_out']:,} of {b['exposure']:,.0f} not ruled out"
            parts.append(note)
            break
    if st.get("test"):
        x = st["test"]
        parts.append(f"tested from its counts: difference {x['diff'] * 100:.1f} points, 95% interval "
                     f"{x['lo'] * 100:.1f} to {x['hi'] * 100:.1f}, p = {x['p']:.2g}")
    if st.get("stale"):
        parts.append("STALE — " + "; ".join(st["stale"][:3]))
    if st.get("basis_changed"):
        parts.append("REVISIT — its basis changed: " + ", ".join(
            f"{b['code']} v{b['was_v']}→v{b['now_v']}" for b in st["basis_changed"][:5]))
    if st.get("at_risk"):
        parts.append("AT RISK — rests on " + ", ".join(s.nodes[a]["code"] or a for a in st["at_risk"][:5]))
    if st.get("rests_on_superseded"):
        parts.append("rests on superseded " + ", ".join(s.nodes[a]["code"] or a for a in st["rests_on_superseded"][:5])
                     + " — check it against the replacement")
    if st.get("lease"):
        parts.append(f"being worked by {st['lease']['agent']}")
    return " · ".join(parts)

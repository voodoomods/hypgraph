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
        self.sig: Any = None
        self.versions: dict[str, list] = defaultdict(list)
        self.events: list[dict] = []
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
        # superseded by a live replacement (a cycle of supersedes edges can't recurse forever)
        if e["rel"] in SAME_TYPE and e["src"] not in _seen and lifecycle(s, e["src"], _seen | {nid}) == "active":
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


def upstream(s: Snap, x: str) -> list[tuple[str, str]]:
    """What x rests on, one step: premises (requires), derivations, a decision's basis, and the run that produced it.
    Support is counted separately (unsupported): one fallen support among several doesn't break a claim."""
    ups = [(e["dst"], e["rel"]) for e in s.out.get(x, []) if e["rel"] in RISKY]
    ups += [(e["src"], "produced_by") for e in s.inn.get(x, []) if e["rel"] == "produced"]
    return ups


def downstream(s: Snap, x: str) -> list[tuple[str, str]]:
    """What rests on x, one step: the inverse of upstream, plus what x supports."""
    downs = [(e["src"], e["rel"]) for e in s.inn.get(x, []) if e["rel"] in RISKY]
    downs += [(e["dst"], "produced") for e in s.out.get(x, []) if e["rel"] == "produced"]
    downs += [(e["dst"], "supports") for e in s.out.get(x, []) if e["rel"] == "supports"]
    return downs


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
    return [e for e in s.inn.get(nid, []) if e["rel"] == "supports"]


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
_READS_OUT = {"requires", "derived_from", "based_on", "cites", "uses", "replicates"}
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
    if t == "claim":
        b = bounds(s, nid)
        if b:
            st["bounds"] = b
        if len(b) >= 2 and lang.found(lang.SIGNIFICANCE, n["body"].get("statement", "")):
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
    absolute = lang.found(lang.ABSOLUTE, n["body"].get("statement", "")) if n["type"] == "claim" else []
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

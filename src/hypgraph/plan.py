"""
Method and coordination, all deterministic and read-only: which experiment to run next, who is on what, what
needs a reviewer or a revalidation, what changed, what it cost, and the facts of an investigation as a report
nobody can edit.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from . import derive as D
from .schema import NEGATIVE, POSITIVE

if TYPE_CHECKING:
    from .graph import Graph


def _live_hypotheses(s: D.Snap, inv: str) -> list[str]:
    return [i for i, n in s.nodes.items() if n["type"] == "hypothesis" and n["inv"] == inv and not D.out_of_play(s, i)]


def _executed(s: D.Snap, xid: str) -> list[str]:
    return [e["src"] for e in s.inn.get(xid, []) if e["rel"] == "executes"]


def _method_key(s: D.Snap, xid: str) -> tuple:
    b = s.nodes[xid]["body"]
    tested = tuple(sorted(e["dst"] for e in s.out.get(xid, []) if e["rel"] == "tests"))
    return (tested, re.sub(r"\W+", " ", str(b.get("method") or "").lower()).strip())


def duplicates(s: D.Snap, inv: str) -> list[list[str]]:
    """Live experiments testing the same hypotheses by the same method."""
    groups: dict[tuple, list[str]] = defaultdict(list)
    for i, n in s.nodes.items():
        if n["type"] == "experiment" and n["inv"] == inv and not D.out_of_play(s, i):
            k = _method_key(s, i)
            if k[0] and k[1]:
                groups[k].append(i)
    return [g for g in groups.values() if len(g) > 1]


def next_experiments(g: "Graph", inv: str, limit: int = 10) -> dict:
    """Planned experiments ranked by how well they discriminate between live hypotheses, whether they can show their
    own power, and cost — duplicates and leased work flagged. Plus live hypotheses that no experiment tests yet."""
    s = g.snapshot()
    live = set(_live_hypotheses(s, inv))
    dup = {x for grp in duplicates(s, inv) for x in grp[1:]}
    rows = []
    for i, n in s.nodes.items():
        if n["type"] != "experiment" or n["inv"] != inv or D.out_of_play(s, i):
            continue
        runs = _executed(s, i)
        if any(s.nodes[r]["body"].get("state") in ("succeeded", "running", "queued") for r in runs):
            continue
        tests = [e for e in s.out.get(i, []) if e["rel"] == "tests" and e["dst"] in live]
        expected = {str(e["data"].get("expected", "")).strip().lower() for e in tests}
        separates = len(tests) if len(expected) > 1 else (1 if tests else 0)
        powered = bool(n["body"].get("power_check"))
        cost = float(n["body"].get("cost_minutes") or 60)
        score = separates * (1.5 if powered else 1.0) / math.log2(2 + cost)
        rows.append({"experiment": g.brief(s, i), "separates": separates, "power_check": powered,
                     "cost_minutes": cost, "score": round(score, 3), "duplicate": i in dup,
                     "lease": D.state(s, i).get("lease")})
    rows.sort(key=lambda r: (r["duplicate"], r["lease"] is not None, -r["score"]))
    tested = {e["dst"] for x, n in s.nodes.items() if n["type"] == "experiment" and n["inv"] == inv
              for e in s.out.get(x, []) if e["rel"] == "tests"}
    gaps = [g.brief(s, h) for h in live if h not in tested]
    return {"ranked": rows[:limit], "untested_hypotheses": gaps,
            "rule": "score = hypotheses it separates (distinct expected outcomes) × 1.5 if it can show its own power "
                    "÷ log2(2 + cost in minutes); duplicates and leased work last"}


def work_map(g: "Graph", inv: str = "") -> dict:
    """Who is on what, what needs a reviewer, what needs revalidation, contested work, decisions to revisit and
    duplicated experiments."""
    s = g.snapshot()
    inside = (lambda n: n["inv"] == inv) if inv else (lambda n: True)
    leases = [{"node": g.brief(s, k), "agent": v["agent"], "task": v["task"], "expires": v["expires"]}
              for k, v in s.leases.items() if k in s.nodes and inside(s.nodes[k])]
    review_q, reval, contested, revisit = [], [], [], []
    for i, n in s.nodes.items():
        if inside(n) and n["type"] == "decision" and D.lifecycle(s, i) == "active":
            st = D.state(s, i)
            if st.get("basis_changed") or st.get("at_risk"):
                revisit.append(g.brief(s, i))
            continue
        if not inside(n) or n["type"] not in ("claim", "result") or D.lifecycle(s, i) != "active":
            continue
        st = D.state(s, i)
        rv = st["review"]["state"]
        if rv == "needs_revalidation" or st.get("at_risk") or st.get("unsupported") or st.get("rests_on_superseded"):
            reval.append(g.brief(s, i))                  # something it rests on moved: first, before any review
        elif rv == "contested":
            contested.append(g.brief(s, i))
        elif rv == "unchecked" and n["type"] == "claim" and n["body"].get("kind") != "lead":
            review_q.append(g.brief(s, i))
    dups = []
    for invid in ({inv} if inv else {n["inv"] for n in s.nodes.values() if n["inv"]}):
        dups += [[g.brief(s, x) for x in grp] for grp in duplicates(s, invid)]
    return {"leases": leases, "review_queue": review_q[:200], "revalidation": reval[:200],
            "contested": contested[:200], "decisions_to_revisit": revisit[:200], "duplicates": dups}


def digest(g: "Graph", since: str = "", inv: str = "") -> dict:
    """What changed in the record since ``since`` (ISO time; default the last 24 h) and what is waiting now, in
    investigations still open (published and archived ones are fixed history)."""
    s = g.snapshot()
    since = since or (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat(timespec="seconds")
    open_invs = {i: n for i, n in s.nodes.items() if n["type"] == "investigation"
                 and (n["body"].get("state") or "active") == "active" and (not inv or i == inv)}
    created: dict[str, list] = defaultdict(list)
    reviews = {"positive": 0, "negative": 0, "objections": 0, "comments": 0}
    withdrawn = []
    for e in s.events:
        if e["at"] < since:
            continue
        ref, kind, pl = e["ref"], e["kind"], e["payload"]
        n = s.nodes.get(ref)
        if kind == "create" and n and (n["inv"] in open_invs or ref in open_invs):
            created[n["type"]].append(g.brief(s, ref))
        elif kind == "review" and n and n["inv"] in open_invs:
            v = pl.get("verdict")
            key = ("positive" if v in POSITIVE else "negative" if v in NEGATIVE else
                   "objections" if v == "objection" else "comments")
            reviews[key] += 1
        elif kind == "withdraw" and n and n["inv"] in open_invs:
            withdrawn.append(g.brief(s, ref))
    waiting = {"review_queue": 0, "revalidation": 0, "contested": [], "decisions_to_revisit": []}
    for i in open_invs:
        w = work_map(g, i)
        waiting["review_queue"] += len(w["review_queue"])
        waiting["revalidation"] += len(w["revalidation"])
        waiting["contested"] += w["contested"]
        waiting["decisions_to_revisit"] += w["decisions_to_revisit"]
    keep = ("id", "code", "type", "inv", "title", "by", "at")
    short = lambda rows: [{k: r[k] for k in keep} | {"sentence": r["state"]["sentence"]} for r in rows][:20]  # noqa

    def spent(i: str) -> dict:
        if g.spend is None:
            return {}
        try:
            c = cost(g, i)
            return {"usd": c["usd"], "calls": c["calls"], "last_moved": c["last_moved"],
                    "since_last_moved_usd": c["since_last_moved"]["usd"]}
        except Exception as e:  # noqa: BLE001 - a spend problem never hides the record
            return {"spend_error": f"{type(e).__name__}: {e}"[:200]}
    return {"since": since, "investigations": [{"id": i, "title": n["body"].get("title", i), **spent(i)}
                                               for i, n in open_invs.items()],
            "new": {t: len(v) for t, v in created.items()}, "new_claims": short(created.get("claim", [])),
            "new_decisions": short(created.get("decision", [])),
            "lab_runs": sum(1 for r in created.get("run", []) if r["by"] == g.policy.instrument),
            "reviews": reviews, "withdrawn": short(withdrawn),
            "waiting": {"review_queue": waiting["review_queue"], "revalidation": waiting["revalidation"],
                        "contested": short(waiting["contested"]),
                        "decisions_to_revisit": short(waiting["decisions_to_revisit"])}}


def _minutes(a: str, b: str) -> float:
    try:
        return max(0.0, (datetime.fromisoformat(str(b)) - datetime.fromisoformat(str(a))).total_seconds() / 60)
    except (TypeError, ValueError):
        return 0.0


_NO_SPEND = {"usd": 0.0, "calls": 0, "input_tokens": 0, "cached_tokens": 0, "output_tokens": 0, "by_task": []}


def cost(g: "Graph", inv: str, nid: str = "") -> dict:
    """What an investigation has cost, derived on read: the spend hook's figures for every task that wrote to it
    (events carry the writer's task — Graph.writing_for), instrument minutes from its runs, $ per review verdict, and
    what was spent since the record last moved. A node's figure is the cost of the tasks that worked on it — shared
    work, so node figures overlap and don't add up to the total."""
    s = g.snapshot()
    n = s.nodes.get(inv)
    if not n or n["type"] != "investigation":
        raise KeyError(inv)

    def in_inv(ref: str) -> bool:
        return ref == inv or s.nodes.get(ref, {}).get("inv") == inv
    node_tasks: dict[str, set] = defaultdict(set)
    reviews, last_moved = 0, ""
    for e in s.events:
        if not in_inv(e["ref"]):
            continue
        t = (e["payload"] or {}).get("task")
        if t:
            node_tasks[e["ref"]].add(t)
        if e["kind"] == "review":
            reviews += 1
        if not e["kind"].startswith("lease"):
            last_moved = max(last_moved, e["at"])
    tasks = set().union(*node_tasks.values()) if node_tasks else set()
    metered = g.spend is not None
    led = dict(g.spend(inv, tasks)) if metered else dict(_NO_SPEND)
    by_task = {r["task_id"]: r["usd"] for r in led.pop("by_task", []) if r.get("task_id")}
    lab_runs = [m for m in s.nodes.values() if m["type"] == "run" and m["inv"] == inv
                and m["created_by"] == g.policy.instrument]
    lab_minutes = round(sum(_minutes(r["body"].get("started"), r["body"].get("finished")) for r in lab_runs), 1)
    moved = (g.spend(inv, tasks, since=last_moved) if (metered and last_moved) else led)

    def node_cost(i: str) -> dict:
        ids = sorted(node_tasks.get(i, ()))
        return {"usd": round(sum(by_task.get(t) or 0 for t in ids), 6), "tasks": ids}
    ranked = sorted(((i, node_cost(i)) for i in node_tasks if i in s.nodes and s.nodes[i]["type"] in
                     ("claim", "result", "hypothesis", "experiment", "decision")), key=lambda x: -x[1]["usd"])
    out = {"inv": inv, "title": n["body"].get("title", inv), **led, "metered": metered,
           "lab": {"runs": len(lab_runs), "minutes": lab_minutes},
           "reviews": reviews, "usd_per_verdict": round(led["usd"] / reviews, 4) if reviews and metered else None,
           "last_moved": last_moved or None,
           "since_last_moved": {"usd": moved["usd"], "calls": moved["calls"]},
           "tasks": len(by_task) if metered else len(tasks),
           "top_nodes": [{**_brief_min(s, i), **c} for i, c in ranked[:10]],
           "note": ("Spend comes from the host's meter. Node figures are the tasks that worked on each node; they "
                    "overlap and don't sum to the total." if metered else
                    "No spend meter is connected (Graph(spend=…)); only lab minutes and review counts are shown.")}
    if nid:
        if nid not in s.nodes:
            raise KeyError(nid)
        out["node"] = {**_brief_min(s, nid), **node_cost(nid)}
    return out


def _brief_min(s: D.Snap, i: str) -> dict:
    m = s.nodes[i]
    b = m["body"]
    return {"id": i, "code": m.get("code", ""), "type": m["type"],
            "title": str(b.get("title") or b.get("statement") or b.get("text") or b.get("summary") or i)[:160]}


def report(g: "Graph", inv: str) -> dict:
    """The facts of an investigation, generated from the record, for the top of any summary: every claim with its
    lifecycle and review verdicts, every result and whether a claim carries it (results aren't reviewed — a
    conclusion that lives only in a result hasn't been checked), hypotheses, experiments (preregistered or not), open
    items and spend. Deterministic; nobody writes it, so it can't restate a withdrawn claim or override a verdict."""
    s = g.snapshot()
    n = s.nodes.get(inv)
    if not n or n["type"] != "investigation":
        raise KeyError(inv)
    mine = [i for i, m in s.nodes.items() if m["inv"] == inv]
    by_type: dict[str, list] = defaultdict(list)
    for i in sorted(mine, key=lambda x: s.nodes[x]["created_at"]):
        by_type[s.nodes[i]["type"]].append(i)

    def verdicts(i: str) -> list[str]:
        out = []
        for e in s.inn.get(i, []):
            r = s.nodes.get(e["src"]) if e["rel"] == "reviews" else None
            if r and r["id"] not in s.withdrawn:
                out.append(f"{r['created_by']}: {r['body'].get('verdict')} ({r['code']}, on v{e['dst_v'] or 0})")
        return out
    cited_by_claim = {e["src"] for c in by_type["claim"] for e in s.inn.get(c, []) if e["rel"] == "supports"}
    claims = []
    for c in by_type["claim"]:
        st = D.state(s, c)
        claims.append({**_brief_min(s, c), "lifecycle": st["lifecycle"], "review": (st.get("review") or {}).get("state"),
                       "verdicts": verdicts(c), "v": s.nodes[c]["v"], "evidence": st.get("evidence"),
                       "lines": st.get("independent_lines")})
    results = [{**_brief_min(s, r), "outcome": D.state(s, r).get("outcome"), "by": s.nodes[r]["created_by"],
                "in_a_claim": r in cited_by_claim, "lifecycle": D.state(s, r)["lifecycle"]} for r in by_type["result"]]
    hyps = [{**_brief_min(s, h), "lifecycle": D.state(s, h)["lifecycle"],
             "support": D.state(s, h).get("independent_lines"), "challenges": D.state(s, h).get("challenges")}
            for h in by_type["hypothesis"]]
    exps = []
    for x in by_type["experiment"]:
        tests = [e for e in s.out.get(x, []) if e["rel"] == "tests"]
        exps.append({**_brief_min(s, x), "preregistered": bool(tests) and all((e.get("data") or {}).get("expected")
                                                                             for e in tests),
                     "tests": [s.nodes[e["dst"]]["code"] for e in tests if e["dst"] in s.nodes],
                     "executed": bool(_executed(s, x)), "lifecycle": D.state(s, x)["lifecycle"]})
    live = [c for c in claims if c["lifecycle"] != "withdrawn"]
    open_items = {
        "claims_unreviewed": [c["code"] for c in live if c["review"] in (None, "unchecked", "needs_revalidation")],
        "claims_contested": [c["code"] for c in live if c["review"] == "contested"],
        "results_in_no_claim": [r["code"] for r in results if not r["in_a_claim"] and r["lifecycle"] != "withdrawn"
                                and r["by"] != g.policy.instrument],
        "experiments_not_preregistered": [x["code"] for x in exps if not x["preregistered"]],
    }
    try:
        spend = cost(g, inv)
        spend = {k: spend[k] for k in ("usd", "calls", "reviews", "usd_per_verdict", "last_moved", "metered")}
    except Exception as e:  # noqa: BLE001 - a spend problem never hides the record
        spend = {"error": f"{type(e).__name__}: {e}"[:200]}
    out = {"inv": inv, "code": n["code"], "title": n["body"].get("title", inv),
           "state": n["body"].get("state") or "active", "objective": n["body"].get("objective", ""),
           "claims": claims, "results": results, "hypotheses": hyps, "experiments": exps,
           "open": open_items, "spend": spend, "seq": s.seq}
    # the workflow's view (@2 profiles): each question's derived stage, and the evidence that has gone stale
    from . import profiles, workflow
    prof = profiles.profile_of(s, inv)
    if prof and prof.workflow:
        stale = [{"code": s.nodes[i]["code"], "type": s.nodes[i]["type"], "why": D.state(s, i)["stale"]}
                 for i in by_type["result"] + by_type["claim"] if D.state(s, i).get("stale")
                 and D.state(s, i)["lifecycle"] != "withdrawn"]
        out["workflow"] = {"profile": prof.id, "report": prof.workflow.report, "method": prof.workflow.method,
                           "questions": workflow.stages(s, inv, s.now), "stale": stale}
    out["markdown"] = report_markdown(out)
    return out


def report_markdown(r: dict) -> str:
    cut = lambda t, k=160: (t[:k] + "…") if len(t) > k else t  # noqa: E731
    L = [f"## Facts from the research graph — {r['code']} {r['title']} ({r['state']})",
         f"_Generated from the record at event {r['seq']}; do not edit — regenerate it from the graph. "
         "Interpretation goes below this section._", "", "### Claims", "",
         "| claim | standing | review | verdicts | statement |", "|---|---|---|---|---|"]
    for c in r["claims"]:
        L.append(f"| {c['code']} v{c['v']} | {c['lifecycle']} | {c['review'] or '-'} | "
                 f"{'; '.join(c['verdicts']) or '-'} | {cut(c['title'])} |")
    L += ["", "### Results", "", "| result | outcome | by | carried by a claim | summary |", "|---|---|---|---|---|"]
    for x in r["results"]:
        L.append(f"| {x['code']} | {x['outcome'] or '-'} | {x['by']} | {'yes' if x['in_a_claim'] else 'NO'} | "
                 f"{cut(x['title'])} |")
    L += ["", "### Hypotheses", ""]
    L += [f"- {h['code']} ({h['lifecycle']}; support lines {h['support']}, challenges {h['challenges']}): "
          f"{cut(h['title'], 140)}" for h in r["hypotheses"]] or ["- none"]
    L += ["", "### Experiments", ""]
    L += [f"- {x['code']} tests {', '.join(x['tests']) or '-'}: "
          f"{'preregistered' if x['preregistered'] else 'NOT preregistered'}, "
          f"{'run' if x['executed'] else 'not run'} — {cut(x['title'], 120)}" for x in r["experiments"]] or ["- none"]
    w = r.get("workflow")
    if w:
        L += ["", f"### Workflow — {w['report']} ({w['profile']})", "", "| question | stage | next gate |", "|---|---|---|"]
        for q in w["questions"]:
            nxt = "complete" if q["complete"] else cut(q["next"], 140)
            L.append(f"| {q['code']} | {q['stage']} ({q['index']}/{q['of']}) | {nxt} |")
        L += ["", "Stale evidence (the run used an artifact since superseded or withdrawn, or valid_until passed): "
              + ("; ".join(f"{x['code']} — {x['why'][0]}" for x in w["stale"]) if w["stale"] else "none")]
    o = r["open"]
    L += ["", "### Open items", "",
          f"- claims not yet reviewed: {', '.join(o['claims_unreviewed']) or 'none'}",
          f"- claims contested: {', '.join(o['claims_contested']) or 'none'}",
          f"- results no claim carries (their conclusions are unreviewed): {', '.join(o['results_in_no_claim']) or 'none'}",
          f"- experiments not preregistered: {', '.join(o['experiments_not_preregistered']) or 'none'}"]
    sp = r["spend"]
    if "error" in sp:
        L += ["", "### Spend", "", f"- unavailable ({sp.get('error')})"]
    elif sp.get("metered"):
        L += ["", "### Spend", "", f"- ${sp['usd']:.2f} over {sp['calls']} model calls; {sp['reviews']} review "
                                   "verdict(s)"]
    return "\n".join(L)

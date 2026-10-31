"""
Coordination through the record: what an orchestrator is told, what a sub-agent is asked, how work is accepted and
what is stopped when a premise falls — all computed from the record, with no model calls.

    briefing(g, inv)          the orchestrator's context: mission, rules, roster, standing, frontier, orders in
                              flight and returned (predicates already checked), budget, and what changed since the
                              last briefing it read. Deterministic: the same record gives the same text and hash.
    issue_work(g, …)          a work order: a task node that works_on one target, rests_on its premises (pinned to
                              the versions it was issued against), names an assignee, done-when predicates and a
                              budget, and leases the target to the assignee so nobody else takes it.
    order_text(g, order)      the assignee's context: objective, target and premises with their standing, what has
                              been tried (failures included), the prediction, the method, the predicates, budget.
    return_work(g, …)         the assignee hands the order back with a short note (releases the lease).
    check_work(g, order)      every predicate MET / NOT MET, with the nodes that satisfy it.
    accept_work(g, …)         only when every predicate is met: a decision that settles the order, based_on the
                              evidence — audited, and flagged REVISIT if that evidence changes.
    rework(g, …)              a new order superseding the old one, saying what was missing.
    issue_work(…, blind=True) a blind order: the record is sealed from the assignee until it returns the order, and
                              what it writes meanwhile is written blind (blind.py).
    cancel_work / cancel_moot withdraw an order; cancel_moot withdraws every open order whose target or premise fell.

An order's status is derived, never set: open · returned · overdue · accepted · reworked · cancelled · moot.
Only evidence written after the order was issued counts toward its predicates.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import TYPE_CHECKING

from . import profiles
from . import derive as D
from . import plan

if TYPE_CHECKING:
    from .graph import Graph

PREDICATES = {
    "run_registered": "a run that executes the target experiment",
    "result_exists": "a result on the target: produced by a run that executes it (experiment) or that supports / "
                     "challenges it (hypothesis, claim, question's answers)",
    "claim_made": "a claim that answers, supports, challenges or rests on the target, accepted by the record's checks",
    "reviewed": "an official review of the target's current version",
    "no_open_objection": "the target has no open objection",
    "report_clean": "the write-up passes check_text with no errors (pass text= to check_work)",
    "within_budget": "the spend metered for this order is within its budget (needs a spend meter)",
}
RECIPES = {
    "run_registered": {"experiment": "register_run(…, experiment=<target>) — the run executes it",
                       "*": "register a run while you hold this order (register_run)"},
    "result_exists": {"*": "register a run with a result while you hold this order (register_run); a result "
                           "linked to the target counts too"},
    "claim_made": {"question": "graph_add(type=\"claim\", …, links=[{\"rel\": \"answers\", \"to\": <target>}]) "
                               "with a measurement for every number, derived_from the result it comes from",
                   "*": "graph_add(type=\"claim\", …, links=[{\"rel\": \"supports\" or \"challenges\", \"to\": "
                        "<target>, \"why\": …}]) with a measurement for every number"},
    "reviewed": {"*": "review(<target>, verdict, method, notes) — by a reviewer, never the claim's author"},
    "no_open_objection": {"*": "a reviewer records 'resolved' on the target, or revise it to answer the objection"},
    "report_clean": {"*": "pass the report text with the return / submit; it is linted against the record"},
    "within_budget": {"*": "stay within the order's budget"},
}
_SPELLINGS = ("p", "predicate", "name", "check", "pred")


def norm_pred(x) -> dict:
    """A predicate as written by an agent — {"p": …}, {"predicate": …}, {"name": …} or a bare string — as {"p": …}."""
    if isinstance(x, str):
        return {"p": x.strip()}
    if isinstance(x, dict):
        for k in _SPELLINGS:
            if x.get(k):
                return {"p": str(x[k]).strip(), **{a: b for a, b in x.items() if a not in _SPELLINGS}}
    return {"p": ""}


def recipe(p: str, target_type: str) -> str:
    r = RECIPES.get(p) or profiles.RECIPES.get(p) or {}
    return r.get(target_type) or r.get("*") or ""


DEFAULT_DONE = {
    "experiment": [{"p": "run_registered"}, {"p": "result_exists"}],
    "hypothesis": [{"p": "result_exists"}, {"p": "claim_made"}],
    "question": [{"p": "claim_made"}],
    "claim": [{"p": "reviewed"}],
    "result": [{"p": "reviewed"}],
    "investigation": [{"p": "report_clean"}],
}
RULES = (
    "Coordinate through the record, not the chat.\n"
    "- Work is a work order: one target, an assignee, done-when predicates. Issue it with issue_work; the target is "
    "leased to the assignee, so nobody duplicates it.\n"
    "- Sub-agents return writes to the record (runs, results, claims), not conclusions in prose. Claims are checked "
    "as they are written; a refused claim must come back honest.\n"
    "- Accept an order only when check_work shows every predicate MET; otherwise rework it (say what is missing) or "
    "cancel it. Accepting writes a decision based on the evidence.\n"
    "- When a premise falls, cancel_moot stops exactly the orders that rest on it; nothing else.\n"
    "- The final report starts from report() and must pass check_text before it is handed over.\n"
    "- A question is settled by one checked claim that answers it. Don't order more reviews of a settled question; "
    "order one review of an answered one.\n"
    "- Don't issue what is already in flight or done by the same method; don't do sub-agents' work yourself.")


def _code(s: D.Snap, i: str) -> str:
    return (s.nodes.get(i) or {}).get("code") or i


def _title(s: D.Snap, i: str) -> str:
    b = s.nodes[i]["body"]
    return str(b.get("statement") or b.get("objective") or b.get("aim") or b.get("text") or b.get("summary")
               or b.get("title") or b.get("choice") or b.get("citation") or b.get("name") or "").strip()


def _line(s: D.Snap, i: str, n: int = 140) -> str:
    t = _title(s, i).replace("\n", " ")
    return f"{_code(s, i)} {t[:n]}{'…' if len(t) > n else ''}"


def _is_order(s: D.Snap, i: str) -> bool:
    n = s.nodes.get(i)
    return bool(n and n["type"] == "task" and n["body"].get("assignee") and n["body"].get("objective"))


def target_of(s: D.Snap, oid: str) -> str:
    for e in s.out.get(oid, []):
        if e["rel"] == "works_on":
            return e["dst"]
    return ""


def premises_of(s: D.Snap, oid: str) -> list[dict]:
    return [e for e in s.out.get(oid, []) if e["rel"] == "rests_on"]


def _settled_by(s: D.Snap, oid: str) -> str:
    for e in s.inn.get(oid, []):
        if e["rel"] == "settles" and D.lifecycle(s, e["src"]) == "active":
            return e["src"]
    return ""


def _returns(s: D.Snap, oid: str) -> list[dict]:
    return [e for e in s.events if e["kind"] == "lease_release" and (e["payload"] or {}).get("task") == oid]


def order_status(s: D.Snap, oid: str) -> str:
    if oid in s.withdrawn:
        return "cancelled"
    if D.lifecycle(s, oid) == "superseded":
        return "reworked"
    if _settled_by(s, oid):
        return "accepted"
    t = target_of(s, oid)
    if (t and D.out_of_play(s, t)) or any(D.fallen(s, e["dst"]) for e in premises_of(s, oid)):
        return "moot"
    if _returns(s, oid):
        return "returned"
    lease = s.leases.get(t) if t else None
    return "open" if lease and lease.get("task") == oid else "overdue"


def orders(g: "Graph", inv: str, status: str = "") -> list[dict]:
    s = g.snapshot()
    out = []
    for i, n in s.nodes.items():
        if n["inv"] != inv or not _is_order(s, i):
            continue
        st = order_status(s, i)
        if status and st != status:
            continue
        t = target_of(s, i)
        r = _returns(s, i)
        out.append({"id": i, "code": n["code"], "status": st, "assignee": n["body"]["assignee"],
                    "role": n["body"].get("role", ""), "objective": n["body"]["objective"],
                    "target": _code(s, t) if t else "", "target_id": t, "issued": n["created_at"],
                    "by": n["created_by"], "returned_note": (r[-1]["payload"] or {}).get("note", "") if r else "",
                    "lease": s.leases.get(t) if t else None, "budget": n["body"].get("budget") or {}})
    return sorted(out, key=lambda o: (o["issued"], o["code"]))


# ── predicates ────────────────────────────────────────────────────
def _after(s: D.Snap, i: str, at: str) -> bool:
    return s.nodes[i]["created_at"] >= at


def _live(s: D.Snap, i: str) -> bool:
    return D.lifecycle(s, i) == "active" and not D.fallen(s, i)


def _runs_executing(s: D.Snap, x: str) -> list[str]:
    return [e["src"] for e in s.inn.get(x, []) if e["rel"] == "executes"]


def _results_of_run(s: D.Snap, r: str) -> list[str]:
    return [e["dst"] for e in s.out.get(r, []) if e["rel"] == "produced" and s.nodes[e["dst"]]["type"] == "result"]


def _results_on(s: D.Snap, t: str) -> list[str]:
    """Results bearing on t: produced by runs executing it, or supporting / challenging it, or (for a question) on
    its answers; for a hypothesis, also results of runs executing an experiment that tests it; for a claim, also the
    results it is derived from."""
    tt = s.nodes[t]["type"]
    out: list[str] = []
    if tt == "experiment":
        for r in _runs_executing(s, t):
            out += _results_of_run(s, r)
    out += [e["src"] for e in s.inn.get(t, []) if e["rel"] in ("supports", "challenges")
            and s.nodes[e["src"]]["type"] == "result"]
    if tt == "claim":
        out += [e["dst"] for e in s.out.get(t, []) if e["rel"] == "derived_from" and s.nodes[e["dst"]]["type"] == "result"]
    if tt in ("hypothesis", "claim"):
        for e in s.inn.get(t, []):
            if e["rel"] == "tests":
                for r in _runs_executing(s, e["src"]):
                    out += _results_of_run(s, r)
    if tt == "question":
        for e in s.inn.get(t, []):
            if e["rel"] == "answers":
                out += _results_on(s, e["src"])
    return list(dict.fromkeys(out))


def _claims_on(s: D.Snap, t: str) -> list[str]:
    tt = s.nodes[t]["type"]
    out = [e["src"] for e in s.inn.get(t, []) if e["rel"] in ("supports", "challenges", "answers", "requires")
           and s.nodes[e["src"]]["type"] == "claim"]
    targets = {t}
    if tt == "experiment":
        targets |= {e["dst"] for e in s.out.get(t, []) if e["rel"] == "tests"}
        for h in targets - {t}:
            out += [e["src"] for e in s.inn.get(h, []) if e["rel"] in ("supports", "challenges", "answers")
                    and s.nodes[e["src"]]["type"] == "claim"]
    for r in _results_on(s, t):                           # claims built on the results that bear on it
        out += [e["src"] for e in s.inn.get(r, []) if e["rel"] == "derived_from" and s.nodes[e["src"]]["type"] == "claim"]
        out += [e["dst"] for e in s.out.get(r, []) if e["rel"] == "supports" and s.nodes[e["dst"]]["type"] == "claim"]
    return list(dict.fromkeys(out))


def chain_root(s: D.Snap, oid: str) -> str:
    """The first order of a rework chain (follows ``supersedes``); an order that replaced nothing is its own root."""
    seen = [oid]
    while True:
        older = [e["dst"] for e in s.out.get(seen[-1], []) if e["rel"] == "supersedes"]
        if not older or older[0] in seen:
            return seen[-1]
        seen.append(older[0])


def _eval(g: "Graph", s: D.Snap, oid: str, pred: dict, text: str) -> dict:
    p = pred.get("p", "")
    t = target_of(s, oid)
    at = s.nodes[chain_root(s, oid)]["created_at"]     # a rework keeps what its earlier attempts wrote
    res = {"p": p, "met": False, "evidence": [], "why": ""}
    if p in profiles.PRED_DESC:
        return res | profiles.evaluate(p, s, oid, t, at, s.nodes[oid]["body"].get("assignee", ""), s.nodes[oid]["inv"])
    if p not in PREDICATES:
        return res | {"why": f"unknown predicate {p!r}"}
    if not t and p not in ("report_clean", "within_budget"):
        return res | {"why": "the order has no target"}
    who = s.nodes[oid]["body"].get("assignee", "")
    inv = s.nodes[oid]["inv"]

    def under_order(ntype: str) -> list[str]:
        """What the assignee wrote in this investigation while holding the order: work on the order by construction."""
        return [i for i, n in s.nodes.items() if n["type"] == ntype and n["inv"] == inv and n["created_by"] == who
                and _after(s, i, at) and _live(s, i)]
    if p == "run_registered":
        ids = [r for r in _runs_executing(s, t) if _after(s, r, at) and _live(s, r)] or under_order("run")
        return res | {"met": bool(ids), "evidence": ids, "why": "" if ids else f"no run executes {_code(s, t)}, and "
                      f"{who} registered none under this order"}
    if p == "result_exists":
        ids = [r for r in _results_on(s, t) if _after(s, r, at) and _live(s, r)] or under_order("result")
        return res | {"met": bool(ids), "evidence": ids,
                      "why": "" if ids else f"no live result on {_code(s, t)}, and {who} registered none under this "
                                            "order"}
    if p == "claim_made":
        ids = [c for c in _claims_on(s, t) if _after(s, c, at) and _live(s, c)]
        return res | {"met": bool(ids), "evidence": ids,
                      "why": "" if ids else f"no live claim on {_code(s, t)} since the order was issued"}
    if p == "reviewed":
        rv = [e["src"] for e in s.inn.get(t, []) if e["rel"] == "reviews" and e["dst_v"] == s.nodes[t]["v"]
              and s.nodes[e["src"]]["body"].get("official") and _after(s, e["src"], at)]
        return res | {"met": bool(rv), "evidence": rv,
                      "why": "" if rv else f"no official review of {_code(s, t)} v{s.nodes[t]['v']} since the order"}
    if p == "no_open_objection":
        st = D.state(s, t).get("review") or {}
        opened = [o.get("review") or o.get("by") for o in st.get("open_objections", [])]
        return res | {"met": not opened, "evidence": [], "why": "open objection(s): " + ", ".join(map(str, opened))
                      if opened else ""}
    if p == "report_clean":
        if not text.strip():
            return res | {"why": "pass the write-up as text= to check it"}
        r = g.check_text(text, s.nodes[oid]["inv"])
        errs = [f for f in r["findings"] if f.get("level") == "error"]
        return res | {"met": not errs, "evidence": [],
                      "why": "" if not errs else f"{len(errs)} error(s): " + "; ".join(f["code"] for f in errs[:6])}
    if p == "within_budget":
        cap = float((s.nodes[oid]["body"].get("budget") or {}).get("usd") or 0)
        if g.spend is None or not cap:
            return res | {"met": True, "why": "not metered" if g.spend is None else "no $ budget set"}
        usd = float(g.spend(s.nodes[oid]["inv"], {oid}).get("usd") or 0)
        return res | {"met": usd <= cap, "why": f"${usd:.4f} of ${cap:.4f}"}
    return res


def done_lines(g: "Graph", author: str, inv: str) -> list[str]:
    """After a write: the author's open orders, each predicate MET / NOT MET, and 'return_work now' when all are.
    Done-ness is derived like everything else, and it is said where the work happens, so nobody works past done."""
    out = []
    for o in orders(g, inv):
        if o["assignee"] != author or o["status"] not in ("open", "overdue"):
            continue
        c = check_work(g, o["id"])
        if c["all_met"]:
            out.append(f"{o['code']}: every predicate met ({', '.join(x['p'] for x in c['predicates'])}) — "
                       "return_work now")
        else:
            out.append(f"{o['code']}: " + "; ".join(f"{x['p']} {'MET' if x['met'] else 'NOT MET'}"
                                                    for x in c["predicates"]))
    return out


def check_work(g: "Graph", order: str, text: str = "") -> dict:
    s = g.snapshot()
    if not _is_order(s, order):
        raise KeyError(f"{order} is not a work order")
    preds = s.nodes[order]["body"].get("done_when") or []
    checks = [_eval(g, s, order, p, text) for p in preds]
    for c in checks:
        c["evidence_codes"] = [_code(s, i) for i in c["evidence"]]
    return {"order": order, "code": s.nodes[order]["code"], "status": order_status(s, order),
            "all_met": bool(checks) and all(c["met"] for c in checks), "predicates": checks}


def _done_text(pred: dict, target_type: str = "") -> str:
    p = pred.get("p", "")
    extra = " ".join(f"{k}={v}" for k, v in sorted(pred.items()) if k != "p")
    how = recipe(p, target_type)
    return (f"[{p}{' ' + extra if extra else ''}] — {PREDICATES.get(p) or profiles.PRED_DESC.get(p) or 'unknown predicate'}"
            + (f"\n      how: {how}" if how else ""))


# ── issuing and settling ──────────────────────────────────────────
def _known_predicates(preds: list[dict]) -> None:
    """Refuse a predicate the record can't evaluate: an order carrying one can never be met."""
    from .graph import GraphError
    bad = [p["p"] for p in preds if p["p"] not in PREDICATES and p["p"] not in profiles.PRED_DESC]
    if bad:
        raise GraphError(f"unknown predicate(s) {bad}: write each as {{\"p\": \"claim_made\"}}; predicates: "
                         + ", ".join(sorted(set(PREDICATES) | set(profiles.PRED_DESC))))


def issue_work(g: "Graph", *, author: str, inv: str, target: str, assignee: str, objective: str, role: str = "",
               done_when: list | None = None, prediction: str = "", method: str = "", budget: dict | None = None,
               premises: list | None = None, lease_minutes: int = 240, note: str = "", blind: bool = False) -> dict:
    """Issue one work order on one live target. Refused if the target is out of play or an open order already works
    on it (the duplicate is named). Premises default to what the target rests on (and, for an experiment, the
    hypotheses it tests), pinned to their current versions.

    ``blind=True``: the assignee works without seeing what the record holds (blind.py). Refused with a prediction,
    with a predicate that has to read its target (reviewed, no_open_objection, report_clean), for an assignee that
    has already written in this record, or when the objective, method or note quote a number only the sealed
    material carries."""
    from .graph import GraphError
    s = g.snapshot()
    try:
        t = g.resolve(target, inv)
        prem_ids = None if premises is None else [g.resolve(p, inv) for p in premises]
    except KeyError as e:
        raise GraphError(str(e).strip("'\"") + " — a target is a code the record has (Q1, H2, X1, CL3; find lists "
                         "them) or the investigation's id; add a hypothesis or experiment first if you need a new "
                         "one") from None
    from . import blind as B
    own = B.view_for_author(s, author)
    if own:                     # a seat holding a blind order measures; it issues orders once it has returned it
        raise g._sealed(own.hide, "a work order")
    hidden = g._hidden(s, author)
    if D.out_of_play(s, t):
        raise GraphError(f"{_code(s, t)} is {D.lifecycle(s, t)}{' and fallen' if D.fallen(s, t) else ''} — "
                         "nothing to work on")
    for o in orders(g, inv):
        if o["target_id"] == t and o["status"] in ("open", "returned", "overdue"):
            raise GraphError(f"{o['code']} ({o['assignee']}) already works on {_code(s, t)} — {o['status']}. "
                             "Check or rework that order instead of issuing a duplicate.")
    lease = s.leases.get(t)
    if lease and lease["agent"] != assignee:
        raise GraphError(f"{lease['agent']} holds {_code(s, t)} until {lease['expires']}")
    if blind and not done_when:
        done_when = [{"p": "result_exists"}]
    preds = [norm_pred(p) for p in (done_when or profiles.default_done(s, inv, s.nodes[t]["type"])
                                     or DEFAULT_DONE.get(s.nodes[t]["type"], [{"p": "result_exists"}]))]
    _known_predicates(preds)
    if premises is None:
        prem = [a for a, _r, _d in D.ancestors(s, t, limit=40) if s.nodes[a]["type"] not in ("artifact", "task")]
        if s.nodes[t]["type"] == "experiment":
            prem += [e["dst"] for e in s.out.get(t, []) if e["rel"] == "tests"]
    else:
        prem = prem_ids
    prem = [p for p in dict.fromkeys(prem) if p in s.nodes and p != t][:30]
    if hidden and (t in hidden or any(p in hidden for p in prem)):     # its text would quote sealed work
        raise g._sealed(hidden, "a work order on sealed work")
    if blind:
        _blind_ok(s, inv=inv, author=author, assignee=assignee, target=t, preds=preds, prediction=prediction,
                  texts=[objective, method, note, role], skip=hidden)
    fields = {"objective": objective, "assignee": assignee, "role": role, "done_when": preds,
              "prediction": prediction, "method": method, "budget": budget or {}, "note": note,
              "title": objective[:300]}
    if blind:
        fields["blind"] = True
    links = [{"rel": "works_on", "to": t}] + [{"rel": "rests_on", "to": p} for p in prem]
    out = g.create(author=author, type="task", inv=inv, fields=fields, links=links)
    oid = out["id"]
    _lease_for(g, author=author, node=t, agent=assignee, task=oid, minutes=lease_minutes)
    return {"order": oid, "code": out["code"], "target": _code(s, t), "premises": [_code(s, p) for p in prem],
            "done_when": preds, "text": order_text(g, oid)}


def _blind_ok(s: D.Snap, *, inv: str, author: str, assignee: str, target: str, preds: list[dict], prediction: str,
              texts: list[str], skip: dict | None = None) -> None:
    """A blind order's checks at issue: what the record can see of whether the assignee will really work blind.
    ``skip``: what is sealed from the issuer itself, left out of the leak check (comparing against it would tell the
    issuer whether a number it guessed is in there)."""
    from .graph import GraphError
    from . import blind as B
    if prediction.strip():
        raise GraphError("a blind order carries no prediction: the assignee would read it. Keep the prediction on "
                         "the hypothesis (sealed from the assignee) and leave prediction= empty")
    if s.nodes[target]["type"] == "investigation":
        raise GraphError("a blind order works on an experiment, hypothesis, question or claim; a report has to read "
                         "the record")
    bad = [p["p"] for p in preds if p["p"] not in B.BLIND_PREDICATES]
    if bad:
        raise GraphError(f"a blind order asks for a measurement; {', '.join(bad)} has to read what it judges. Use "
                         + ", ".join(sorted(B.BLIND_PREDICATES)) + " (default: result_exists)")
    if assignee == author:
        raise GraphError("a blind order goes to someone else: you have seen what it would seal")
    wrote = [n["code"] or i for i, n in s.nodes.items() if n["created_by"] == assignee][:4]
    if wrote:
        raise GraphError(f"{assignee} has already written in this record ({', '.join(wrote)}), so it has read what a "
                         "blind order would seal. Give the blind order to a seat that hasn't")
    w = B.Window("", [], assignee, inv, s.seq, None, sealing=True, fresh=True)
    found = B.leaks(s, w, [x for x in texts if x], skip=skip)
    if found:
        said = "; ".join(f"{k} (in {', '.join(v[:3])})" for k, v in sorted(found.items())[:6])
        raise GraphError(f"the order quotes what it would seal: {said}. Say what to measure and how, not what it "
                         "came to")


def _lease_for(g: "Graph", *, author: str, node: str, agent: str, task: str, minutes: int) -> None:
    """Lease ``node`` to ``agent`` for ``task``, recorded as written by ``author`` (the orchestrator)."""
    from datetime import datetime, timedelta
    with g._lock:
        try:
            at = g.clock()
            exp = (datetime.fromisoformat(at) + timedelta(minutes=max(15, min(int(minutes), 1440)))
                   ).isoformat(timespec="seconds")

            def write(con):
                con.execute("INSERT INTO leases (node, agent, task, kind, at, expires, note) VALUES (?,?,?,?,?,?,?)",
                            (node, agent, task, "take", at, exp, "work order"))
                g._event(con, author, "lease_take", node, {"task": task, "expires": exp, "for": agent}, at)
            g._transaction(write)
        finally:
            g._after_write()


def return_work(g: "Graph", *, author: str, order: str, note: str = "") -> dict:
    """The assignee hands the order back: releases the target's lease with a short note (≤ 1,000 characters)."""
    from .graph import GraphError
    s = g.snapshot()
    if not _is_order(s, order):
        raise GraphError(f"{order} is not a work order")
    b = s.nodes[order]["body"]
    if author != b["assignee"]:
        raise GraphError(f"{_code(s, order)} is {b['assignee']}'s order")
    t = target_of(s, order)
    with g._lock:
        try:
            at = g.clock()

            def write(con):
                con.execute("INSERT INTO leases (node, agent, task, kind, at, expires, note) VALUES (?,?,?,?,?,?,?)",
                            (t, author, order, "release", at, "", str(note)[:300]))
                g._event(con, author, "lease_release", t, {"task": order, "note": str(note)[:1000], "returned": True},
                         at)
            g._transaction(write)
        finally:
            g._after_write()
    return check_work(g, order)


def directs(s: D.Snap, author: str, order: str) -> bool:
    """Who may accept, rework or settle an order: the author who issued it, or a curator (operator, importer). An
    assignee reworking its own order could rewrite what counts as done, meet that and accept it."""
    return author == s.nodes[order]["created_by"] or author in s.policy.curators


def _must_direct(s: D.Snap, author: str, order: str, what: str) -> None:
    from .graph import GraphError
    if not directs(s, author, order):
        raise GraphError(f"only {s.nodes[order]['created_by']}, who issued {_code(s, order)}, or the "
                         f"{s.policy.operator} {what} it")


def accept_work(g: "Graph", *, author: str, order: str, reason: str = "", text: str = "") -> dict:
    """Accept an order whose predicates are all met: a decision settling it, based_on the claims and results that
    met them (pinned to their versions, so the decision is flagged REVISIT if they change). Only its issuer (or a
    curator) accepts it."""
    from .graph import GraphError
    s0 = g.snapshot()
    if not _is_order(s0, order):
        raise GraphError(f"{order} is not a work order")
    _must_direct(s0, author, order, "accepts")
    chk = check_work(g, order, text)
    if not chk["all_met"]:
        missing = "; ".join(c["why"] or c["p"] for c in chk["predicates"] if not c["met"])
        raise GraphError(f"{chk['code']} isn't done: {missing}. Rework it (rework) or cancel it (cancel_work).")
    s = g.snapshot()
    ev = [i for c in chk["predicates"] for i in c["evidence"]
          if s.nodes[i]["type"] in ("claim", "result", "hypothesis")]
    ev = list(dict.fromkeys(ev))
    met = "; ".join(f"{c['p']}: {', '.join(c['evidence_codes']) or 'met'}" for c in chk["predicates"])
    # kind=accepted: the record's bookkeeping, not a position — under trading a kind-less decision whose text quoted
    # an objective about a "paper position" and that rested on the claims was refused for want of a stop, and the run
    # crashed as it settled (studies T2)
    fields = {"choice": f"Accept {chk['code']}: {s.nodes[order]['body']['objective'][:200]}", "kind": "accepted",
              "reasons": (reason.strip() + " — " if reason.strip() else "") + f"every predicate met ({met})"}
    links = [{"rel": "settles", "to": order}] + [{"rel": "based_on", "to": i} for i in ev]
    d = g.create(author=author, type="decision", inv=s.nodes[order]["inv"], fields=fields, links=links)
    return {"order": order, "code": chk["code"], "decision": d["code"], "status": "accepted", "evidence": ev}


def rework(g: "Graph", *, author: str, order: str, missing: str, done_when: list | None = None,
           objective: str = "") -> dict:
    """A new order for the same target and assignee, superseding the old one, saying what was missing."""
    from .graph import GraphError
    s = g.snapshot()
    if not _is_order(s, order):
        raise GraphError(f"{order} is not a work order")
    _must_direct(s, author, order, "reworks")
    if len(missing.strip()) < 10:
        raise GraphError("missing: say what the return lacked")
    b = s.nodes[order]["body"]
    t = target_of(s, order)
    chain = [order]
    while True:                                                    # the orders this one already replaced
        older = [e["dst"] for e in s.out.get(chain[-1], []) if e["rel"] == "supersedes"]
        if not older or older[0] in chain:
            break
        chain.append(older[0])
    if len(chain) >= 3 and not done_when:
        missing_now = {x["p"] for x in check_work(g, order)["predicates"] if not x["met"]}
        raise GraphError(f"{s.nodes[order]['code']} has been reworked twice already and "
                         f"{', '.join(sorted(missing_now)) or 'its predicates'} still isn't met: the predicate may be "
                         "unmeetable as tooled. Change it (rework with done_when=…), accept what was delivered with a "
                         "reason (accept_work needs every predicate met — so change it first), or cancel_work.")
    done_when = [norm_pred(x) for x in done_when] if done_when else None
    if done_when:                       # a lead reworked with 'claim_answers_q3', an order nothing could meet (S1)
        _known_predicates(done_when)
    prem = [e["dst"] for e in premises_of(s, order)]
    fields = {"objective": objective or b["objective"], "assignee": b["assignee"], "role": b.get("role", ""),
              "done_when": done_when or b.get("done_when") or [], "prediction": b.get("prediction", ""),
              "method": b.get("method", ""), "budget": b.get("budget") or {},
              "note": f"Rework of {s.nodes[order]['code']}: {missing.strip()}"[:1500], "title": b.get("title", "")}
    if b.get("blind"):
        fields["blind"] = True             # still marked; the window closed at the first return (blind.windows)
    links = ([{"rel": "works_on", "to": t}] + [{"rel": "rests_on", "to": p} for p in prem]
             + [{"rel": "supersedes", "to": order}])
    out = g.create(author=author, type="task", inv=s.nodes[order]["inv"], fields=fields, links=links)
    _lease_for(g, author=author, node=t, agent=b["assignee"], task=out["id"], minutes=240)
    return {"order": out["id"], "code": out["code"], "replaces": s.nodes[order]["code"],
            "text": order_text(g, out["id"])}


def cancel_work(g: "Graph", *, author: str, order: str, why: str) -> dict:
    """Withdraw an order. If its target is still leased for it (the order was open, never returned), the lease is
    released too — otherwise the target stays blocked for the lease's remaining hours and nobody else can be
    issued it (found 2026-10-25 when a resumed run cancelled an absent seat's order and then couldn't re-issue)."""
    s = g.snapshot()
    t = target_of(s, order) if _is_order(s, order) else ""
    lease = s.leases.get(t) if t else None
    g.withdraw(author=author, node=order, why=why)
    if lease and lease.get("task") == order:
        assignee = lease["agent"]
        with g._lock:
            try:
                at = g.clock()

                def write(con):
                    con.execute("INSERT INTO leases (node, agent, task, kind, at, expires, note) VALUES (?,?,?,?,?,?,?)",
                                (t, assignee, order, "release", at, "", "order cancelled"))
                    g._event(con, author, "lease_release", t, {"task": order, "cancelled": True, "for": assignee}, at)
                g._transaction(write)
            finally:
                g._after_write()
    return {"order": order, "status": "cancelled", "lease_released": bool(lease and lease.get("task") == order)}


def cancel_moot(g: "Graph", *, author: str, inv: str) -> list[dict]:
    """Withdraw every open, returned or overdue order whose target or a premise has fallen — the cascade, stopped
    exactly where it reaches."""
    s = g.snapshot()
    out = []
    for o in orders(g, inv, status="moot"):
        if o["id"] in s.withdrawn or _settled_by(s, o["id"]):
            continue
        fell = [_code(s, e["dst"]) for e in premises_of(s, o["id"]) if D.fallen(s, e["dst"])]
        t = o["target_id"]
        if t and D.out_of_play(s, t):
            fell.insert(0, _code(s, t))
        why = "moot: " + ", ".join(fell) + " fell or left play — the work no longer stands on anything"
        g.withdraw(author=author, node=o["id"], why=why)
        out.append({"order": o["code"], "assignee": o["assignee"], "because": fell})
    return out


# ── texts ─────────────────────────────────────────────────────────
def _standing_line(s: D.Snap, i: str) -> str:
    st = D.state(s, i)
    return f"{_line(s, i, 110)} — {st['sentence']}"


def _values_line(values: dict) -> str:
    parts = []
    for k, v in list(values.items())[:12]:
        if isinstance(v, dict) and "k" in v and "n" in v:
            parts.append(f"{k} = {v['k']} of {v['n']}")
        elif isinstance(v, dict) and "value" in v:
            parts.append(f"{k} = {v['value']}{' ' + str(v['unit']) if v.get('unit') else ''}")
        else:
            parts.append(f"{k} = {v}")
    return "; ".join(parts)


def _target_detail(s: D.Snap, t: str) -> list[str]:
    """The target's own content, in the order — so the assignee never needs a `show` to read what it was given.
    Measured in the harmony confirmatory (2026-10-25): 11–16 `show` calls a run, reading back what the reply had
    already said. A claim comes with its statement, scope, measurements and the values of the results it rests on;
    a result with its values; a question with its text; an experiment with its protocol."""
    n = s.nodes[t]
    b = n["body"]
    tt = n["type"]
    out: list[str] = []
    if tt == "claim":
        out.append(f"  statement: {b.get('statement', '')}")
        if b.get("scope"):
            out.append(f"  scope: {b['scope']}")
        if b.get("kind"):
            out.append(f"  kind: {b['kind']}")
        for m in (b.get("measurements") or [])[:12]:
            if isinstance(m, dict):
                rid = str(m.get("result") or "")
                val = m.get("value", f"{m.get('k')} of {m.get('n')}" if "k" in m else "")
                out.append(f"  measurement {m.get('name', '?')} = {val} ← {_code(s, rid) if rid in s.nodes else rid}.{m.get('key', '')}")
        for e in s.out.get(t, []):
            if e["rel"] == "derived_from" and s.nodes.get(e["dst"], {}).get("type") == "result":
                rb = s.nodes[e["dst"]]["body"]
                out.append(f"  rests on {_code(s, e['dst'])}: {str(rb.get('summary', ''))[:160]}"
                           + (f" — {_values_line(rb['values'])}" if rb.get("values") else ""))
                for r in (x["src"] for x in s.inn.get(e["dst"], []) if x["rel"] == "produced"):
                    src = str(((s.nodes[r]["body"].get("config") or {}).get("source")) or "")
                    if src.strip():                        # the code behind the result, so a reviewer needn't fetch it
                        out.append(f"    code of {_code(s, r)}:")
                        out += ["      " + ln for ln in src.strip().splitlines()[:40]]
                        if len(src.strip().splitlines()) > 40:
                            out.append("      …")
                    for x in s.inn.get(r, []):
                        if x["rel"] != "replicates":
                            continue
                        lb = s.nodes[x["src"]]["body"]
                        out.append(f"    re-run by {_code(s, x['src'])}: {(lb.get('note') or 'reproduced')[:300]}")
    elif tt == "result":
        out.append(f"  summary: {b.get('summary', '')}")
        if b.get("values"):
            out.append(f"  values: {_values_line(b['values'])}")
        if b.get("outcome"):
            out.append(f"  outcome: {b['outcome']}")
    elif tt == "question":
        out.append(f"  question: {b.get('text', '')}")
        if b.get("why"):
            out.append(f"  why: {b['why']}")
    elif tt == "experiment":
        out.append(f"  aim: {b.get('aim', '')}")
        out.append(f"  protocol: {str(b.get('protocol', ''))[:600]}")
        if b.get("success_criteria"):
            out.append(f"  success: {b['success_criteria']}")
    elif tt == "hypothesis":
        out.append(f"  statement: {b.get('statement', '')}")
        for p in (b.get("predictions") or [])[:6]:
            out.append(f"  predicts: {p}")
    return out


def order_text(g: "Graph", order: str) -> str:
    """Everything the assignee needs and nothing else."""
    s = g.snapshot()
    n = s.nodes[order]
    b = n["body"]
    t = target_of(s, order)
    L = [f"WORK ORDER {n['code']} for {b['assignee']}{' (' + b['role'] + ')' if b.get('role') else ''} — issued by "
         f"{n['created_by']} at {n['created_at']}", "", f"OBJECTIVE    {b['objective']}"]
    if b.get("note"):
        L.append(f"NOTE         {b['note']}")
    from . import blind as B
    if any(w.sealing and order in w.orders for w in B.windows(s)):
        return "\n".join(_blind_order_text(s, order, t, L))
    if t:
        L += ["", "TARGET       " + _standing_line(s, t)]
        L += _target_detail(s, t)
    prem = premises_of(s, order)
    if prem:
        L += ["", "PREMISES"]
        for e in prem:
            p = e["dst"]
            moved = f" — REVISED since issue (v{e['dst_v']}→v{s.nodes[p]['v']})" if e["dst_v"] and \
                s.nodes[p]["v"] > e["dst_v"] else ""
            L.append(f"  {_standing_line(s, p)}{moved}")
    known = []
    if t:
        tt = s.nodes[t]["type"]
        xs = [t] if tt == "experiment" else [e["src"] for e in s.inn.get(t, []) if e["rel"] == "tests"]
        for x in xs:
            for r in _runs_executing(s, x):
                rb = s.nodes[r]["body"]
                known.append(f"  {_code(s, r)} ran {_code(s, x)}: {rb.get('state') or 'unknown'}"
                             f"{' — ' + rb['note'][:120] if rb.get('note') else ''}")
                for rs in _results_of_run(s, r):
                    known.append(f"    → {_standing_line(s, rs)}")
        for r in _results_on(s, t):
            if D.state(s, r).get("restates"):
                continue                                   # one measurement, written twice, is listed once
            line = f"  {_standing_line(s, r)}"
            if line not in known and f"    → {_standing_line(s, r)}" not in known:
                known.append(line)
        for e in s.inn.get(t, []):
            if e["rel"] == "reviews":
                rb = s.nodes[e["src"]]["body"]
                known.append(f"  review {_code(s, e['src'])} by {s.nodes[e['src']]['created_by']}: {rb['verdict']} — "
                             f"{rb['notes'][:160]}")
        for o in orders(g, n["inv"]):
            if o["target_id"] == t and o["id"] != order and o["status"] in ("cancelled", "reworked", "accepted"):
                known.append(f"  earlier order {o['code']} ({o['assignee']}): {o['status']}"
                             f"{' — ' + o['returned_note'][:160] if o['returned_note'] else ''}")
    if known:
        L += ["", "ALREADY KNOWN OR TRIED (don't repeat a failed approach without saying what is different)"] + known
    pred = b.get("prediction") or ""
    if not pred and t and s.nodes[t]["type"] == "experiment":
        exp = [f"{_code(s, e['dst'])}: {e['data'].get('expected')}" for e in s.out.get(t, [])
               if e["rel"] == "tests" and e["data"].get("expected")]
        pred = "; ".join(exp)
    if pred:
        L += ["", f"PREDICTION   {pred}"]
    if b.get("method"):
        L += [f"METHOD       {b['method']}"]
    L += ["", "DONE WHEN (checked against the record; only what you write after the order counts)"]
    L += [f"  {_done_text(p, s.nodes[t]['type'] if t else '')}" for p in b.get("done_when") or []]
    bud = b.get("budget") or {}
    if bud:
        L += ["", "BUDGET       " + ", ".join(f"{k} {v}" for k, v in sorted(bud.items()))]
    lease = s.leases.get(t) if t else None
    if lease and lease.get("task") == order:
        L.append(f"LEASE        until {lease['expires']}")
    L += ["", "RETURN       Your deliverable is the writes above: register runs, record results, make claims (they "
          "are checked as you write them). Then return_work with a note of at most 120 words: what you did, what you "
          "could not do. No conclusion that isn't in a claim."]
    return "\n".join(L)


def _blind_order_text(s: D.Snap, order: str, t: str, L: list[str]) -> list[str]:
    """A sealing blind order, as its assignee reads it: the objective and the method, the target by code only, and
    nothing other authors wrote about it."""
    b = s.nodes[order]["body"]
    L[0] += " — BLIND"
    if t:
        L += ["", f"TARGET       {_code(s, t)} ({s.nodes[t]['type']}) — sealed from you: work it from the objective"]
    prem = [_code(s, e["dst"]) for e in premises_of(s, order)]
    if prem:
        L.append(f"PREMISES     {', '.join(prem[:12])} (sealed)")
    if b.get("method"):
        L += ["", f"METHOD       {b['method']}"]
    L += ["", "DONE WHEN (checked against the record; only what you write after the order counts)"]
    L += [f"  {_done_text(p, s.nodes[t]['type'] if t else '')}" for p in b.get("done_when") or []]
    bud = b.get("budget") or {}
    if bud:
        L += ["", "BUDGET       " + ", ".join(f"{k} {v}" for k, v in sorted(bud.items()))]
    lease = s.leases.get(t) if t else None
    if lease and lease.get("task") == order:
        L.append(f"LEASE        until {lease['expires']}")
    L += ["", "BLIND        What others wrote on this — hypotheses, predictions, results, claims, reviews, code, other "
          "attempts — is sealed from you until you return this order. Measure it yourself from the objective and "
          "record what you find, whatever it is. Results you write before returning are recorded as written blind; "
          "the record compares them with the sealed ones after you return.",
          "", "RETURN       Your deliverable is the writes above: register runs, record results (they are checked as "
          "you write them). Then return_work with a note of at most 120 words: what you did, what you could not do."]
    return L


def _since(g: "Graph", s: D.Snap, inv: str, seq: int) -> list[str]:
    if not seq:
        return []
    def inside(ref):
        return ref == inv or (s.nodes.get(ref) or {}).get("inv") == inv
    by = defaultdict(list)
    for e in s.events:
        if e["seq"] <= seq or not inside(e["ref"]):
            continue
        k = e["kind"]
        ref = e["ref"]
        if k == "create":
            t = (e["payload"] or {}).get("type", "")
            if t in ("artifact",):
                continue
            by["new"].append(f"{_code(s, ref)} ({t}, {e['actor']})")
        elif k == "revise":
            by["revised"].append(_code(s, ref))
        elif k == "withdraw":
            by["withdrawn"].append(_code(s, ref))
        elif k == "review":
            by["reviews"].append(f"{_code(s, ref)} {e['payload'].get('verdict')} ({e['actor']})")
        elif k == "lease_release" and (e["payload"] or {}).get("returned"):
            by["returned"].append(f"{_code(s, e['payload'].get('task'))} by {e['actor']}")
    return [f"  {k}: {', '.join(v[:14])}{' …' if len(v) > 14 else ''}" for k, v in by.items()]


def question_board(g: "Graph", inv: str) -> list[dict]:
    """Every live question with its status, derived: settled (a checked claim answers it) · contested · answered
    (a live claim answers it, unchecked) · in progress (an order on it is open) · open."""
    s = g.snapshot()
    rows = []
    open_orders = {o["target_id"]: o for o in orders(g, inv) if o["status"] in ("open", "overdue", "returned")}
    for q, n in sorted(((i, n) for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "question"
                        and _live(s, i)), key=lambda kv: kv[1]["code"]):
        ans = [e["src"] for e in s.inn.get(q, []) if e["rel"] == "answers" and s.nodes[e["src"]]["type"] == "claim"
               and _live(s, e["src"])]
        states = {c: (D.state(s, c).get("review") or {}).get("state", "unchecked") for c in ans}
        checked = [c for c in ans if states[c] == "checked"]
        contested = [c for c in ans if states[c] == "contested"]
        o = open_orders.get(q)
        pending = D.unchecked_answers(s, q)
        if checked and pending:
            # two live answers, one checked: settled only once every live answer is checked (they may disagree)
            status, by = "answered", (f"{', '.join(_code(s, c) for c in pending[:3])} unchecked beside "
                                      f"{_code(s, checked[0])} (checked) — review it, or withdraw the wrong answer"
                                      + (f"; order {o['code']} on it" if o else ""))
        elif checked:
            status, by = "settled", f"{_code(s, checked[0])} (checked by " + ", ".join(
                x.split(":")[0] for x in D.state(s, checked[0])["review"]["positive"][:2]) + ")"
        elif contested:
            status, by = "contested", _code(s, contested[0])
        elif ans:
            status, by = "answered", f"{_code(s, ans[-1])} unchecked" + (f"; order {o['code']} on it" if o else "")
        elif o:
            status, by = "in progress", f"{o['code']} → {o['assignee']} ({o['status']})"
        else:
            status, by = "open", ""
        rows.append({"id": q, "code": n["code"], "text": _title(s, q), "status": status, "by": by,
                     "answers": [_code(s, c) for c in ans], "unchecked": [_code(s, c) for c in pending],
                     "unreviewable": [_code(s, c) for c in D.unreviewable_answers(s, q)]})
    return rows


def settle(g: "Graph", *, author: str, inv: str) -> list[dict]:
    """Accept every returned order whose predicates are all met — the mechanical half of the lead's job, done by
    the record. Only the orders this author issued (every order, for a curator). Returns what it accepted."""
    out = []
    s = g.snapshot()
    for o in orders(g, inv, status="returned"):
        if directs(s, author, o["id"]) and check_work(g, o["id"])["all_met"]:
            a = accept_work(g, author=author, order=o["id"], reason="settled by the record: every predicate met")
            out.append({"order": o["code"], "assignee": o["assignee"], "decision": a["decision"]})
    return out


def briefing(g: "Graph", inv: str, *, roster: list | None = None, since_seq: int = 0, budget_usd: float = 0,
             max_items: int = 8) -> dict:
    """The orchestrator's context, compiled from the record. Stable sections first (cache-friendly), then what moved.
    Returns {text, seq, sha256, sections}. Pass the returned seq back as since_seq next time to get only the delta
    in SINCE LAST."""
    s = g.snapshot()
    if inv not in s.nodes or s.nodes[inv]["type"] != "investigation":
        raise KeyError(inv)
    ib = s.nodes[inv]["body"]
    sec: dict[str, list[str]] = {}
    sec["MISSION"] = [f"{ib.get('title', inv)} — {ib.get('objective', '')}".strip()]
    prof = profiles.profile_of(s, inv)
    if prof:
        comp = profiles.completion(s, inv)
        sec["MISSION"].append(f"Profile: {prof.id} — {prof.about}")
        sec["MISSION"].append("Done when: " + "; ".join(f"{c['name']} {'MET' if c['met'] else 'NOT MET'} ({c['why']})"
                                                       for c in comp["criteria"]))
    if ib.get("success_criteria"):
        sec["MISSION"].append(f"Success: {ib['success_criteria']}")
    sec["RULES"] = [RULES]
    if roster:
        sec["ROSTER"] = [f"  {r.get('name')}: {r.get('takes', '')}" for r in roster]
    board = question_board(g, inv)
    if board:
        sec["BOARD"] = [f"  {q['code']} {q['status'].upper():<11} {q['text'][:90]}" + (f" — {q['by']}" if q["by"] else "")
                        for q in board]
        done = sum(q["status"] == "settled" for q in board)
        sec["BOARD"].append(f"  {done} of {len(board)} settled" + (" — every question is settled: write the report"
                                                                   if done == len(board) else ""))
    cont, fallen, risk = [], [], []
    for i, n in sorted(s.nodes.items(), key=lambda kv: kv[1]["code"] or kv[0]):
        if n["inv"] != inv or n["type"] not in ("claim", "hypothesis", "result"):
            continue
        st = D.state(s, i)
        if st["lifecycle"] != "active" or st["fallen"]:
            if n["type"] != "result":
                fallen.append(f"  {_line(s, i, 90)} — {st['lifecycle']}{', fallen' if st['fallen'] else ''}")
            continue
        if st.get("at_risk"):
            risk.append(f"  {_standing_line(s, i)}")
        elif (st.get("review") or {}).get("state") == "contested":
            cont.append(f"  {_standing_line(s, i)}")
    def cap(xs):
        return xs[:max_items * 2] + ([f"  … {len(xs) - max_items * 2} more"] if len(xs) > max_items * 2 else [])
    exc = []
    if cont:
        exc += ["contested:"] + cap(cont)
    if risk:
        exc += ["at risk (a premise fell):"] + cap(risk)
    if fallen:
        exc += ["fallen / withdrawn:"] + cap(fallen)
    sec["STANDING"] = exc or ["nothing contested, at risk or fallen (show <code> for any node's full standing)"]
    busy = {o["target_id"] for o in orders(g, inv) if o["status"] in ("open", "returned", "overdue")}
    front = []
    for q in board:                                       # the question board drives the frontier
        if q["status"] == "open":
            front.append(f"  {q['code']} open question: {q['text'][:90]} — issue_work on it")
        elif q["status"] == "answered" and q["id"] not in busy:
            front.append(f"  {q['code']} answered by {q['answers'][-1]}, unchecked — issue_work on {q['answers'][-1]} "
                         "to a reviewer (one review settles it)")
        elif q["status"] == "contested":
            front.append(f"  {q['code']} contested ({q['by']}) — resolve the objection or revise")
    nx = plan.next_experiments(g, inv, limit=max_items * 2)
    front += [f"  {r['experiment']['code']} {r['experiment']['title'][:100]} — separates {r['separates']}, "
              f"~{r['cost_minutes']:.0f} min{', DUPLICATE' if r['duplicate'] else ''}"
              for r in nx["ranked"] if r["experiment"]["id"] not in busy][:max_items]
    front += [f"  {h['code']} untested hypothesis: {h['title'][:100]}" for h in nx["untested_hypotheses"]
              if h["id"] not in busy][:max_items]
    wm = plan.work_map(g, inv)
    front += [f"  {c['code']} needs revalidation: {c['title'][:100]}" for c in wm["revalidation"]
              if c["id"] not in busy][:max_items]
    sec["FRONTIER"] = front or ["nothing open: every question is settled and nothing waits — write the report"]
    flight, back = [], []
    for o in orders(g, inv):
        if o["status"] in ("open", "overdue"):
            flight.append(f"  {o['code']} → {o['assignee']} on {o['target']}: {o['objective'][:90]} ({o['status']}"
                          f"{', lease to ' + o['lease']['expires'] if o['lease'] else ''})")
        elif o["status"] == "returned":
            chk = check_work(g, o["id"])
            marks = " ".join(f"{c['p']}={'MET' if c['met'] else 'NOT MET'}" for c in chk["predicates"])
            back.append(f"  {o['code']} from {o['assignee']} on {o['target']}: {marks}"
                        + (" — ALL MET: settle_work accepts it" if chk["all_met"] else
                           " — rework (say what is missing) or cancel_work")
                        + (f" — note: {o['returned_note'][:200]}" if o["returned_note"] else ""))
    sec["IN FLIGHT"] = flight or ["no open orders"]
    moot = [o for o in orders(g, inv) if o["status"] == "moot"]
    if moot:
        back.append(f"  {len(moot)} order(s) are MOOT — cancel_moot")
    sec["RETURNED"] = back or ["nothing waiting for acceptance"]
    if g.spend is not None or budget_usd:
        spent = None
        if g.spend is not None:
            try:
                spent = float(plan.cost(g, inv).get("usd") or 0)
            except Exception:  # noqa: BLE001
                spent = None
        sec["BUDGET"] = [f"  spent ${spent:.4f}" if spent is not None else "  spent: not metered"]
        if budget_usd:
            sec["BUDGET"][0] += f" of ${budget_usd:.2f}"
    delta = _since(g, s, inv, since_seq)
    if since_seq:
        sec["SINCE LAST"] = delta or ["  nothing changed"]
    text = "\n\n".join(f"{k}\n" + "\n".join(v) for k, v in sec.items())
    return {"text": text, "seq": s.seq, "sha256": hashlib.sha256(text.encode()).hexdigest(),
            "sections": {k: len("\n".join(v)) for k, v in sec.items()}}

"""
Workflows: a discipline's method as the record enforces it (the ``@2`` profiles; docs/workflows/<name>.md).

A question moves through the stages of its investigation's workflow. **The stage is derived, never set**: a
question is in the first stage whose gate the record does not meet. Gates are checks over the record alone
(GATES); the same gates serve as order predicates (``done_when: [{"p": "preregistered"}]``), scoped to the
target's question and to evidence written since the order.

    g.stage(q)          {"stage", "index", "of", "complete", "next", "gates": [{stage, gate, met, why, evidence}]}
    g.stages(inv)       one per live question

The workflow also names the relations whose far end falling puts dependants AT RISK beyond schema.RISKY (``uses``
for data, diffs and instances; ``cites`` for sources — derive.EXTRA_RISKY), what "fresh" means (derive.stale: a
result whose run uses a superseded or withdrawn artifact, or whose ``valid_until`` has passed), the typed artifacts
and decisions with their required fields, and the refusals of its discipline (TESTS_ON_STALE_HEAD,
EDGE_WITHOUT_TRIALS, POSITION_WITHOUT_STOP, LIVE_ORDER, PASSAGE_MISSING, SOLVED_WITHOUT_INSTANCE,
OPTIMAL_ON_STALE_INSTANCE, ARTIFACT_MISSING_FIELDS, REVIEW_BY_AUTHOR).
"""

from __future__ import annotations

import re
from typing import Callable

from . import derive as D
from . import language as L
from .checks import Problem
from .profiles import (_EDGE, _OPTIMAL, _PASSES, Profile, _cites_source, _has, _instrument_backed, _lab_positive,
                       _live, _producing_run, _vals, profile_of)

_LIVE_ORDER = re.compile(r"\b(live (order|trade|position)|market order|limit order|place[ds]? (an? )?order|"
                         r"execute[sd]? (a |the )?trade|sen[dt] (it |the order )?to (the )?(exchange|broker|venue)|"
                         r"went live)\b", re.I)
_POSITION_WORDS = re.compile(r"\b(position|long|short)\b", re.I)
_TRUE = (True, 1, "true", "True", "yes")


# ── what belongs to a target ───────────────────────────────────────

def question_of(s: D.Snap, nid: str) -> str:
    """The question a node is about, a few steps out: answers / tests / executes / produced / based_on / part_of."""
    seen, frontier = {nid}, [nid]
    for _ in range(6):
        nxt = []
        for x in frontier:
            n = s.nodes.get(x)
            if not n:
                continue
            if n["type"] == "question":
                return x
            for e in s.out.get(x, []):
                if e["rel"] in ("answers", "tests", "executes", "based_on", "part_of", "derived_from", "motivated_by") \
                        and e["dst"] not in seen and s.nodes[e["dst"]]["type"] != "investigation":
                    seen.add(e["dst"])
                    nxt.append(e["dst"])
            for e in s.inn.get(x, []):
                if e["rel"] == "produced" and e["src"] not in seen:        # a result → its run → the experiment
                    seen.add(e["src"])
                    nxt.append(e["src"])
        frontier = nxt
        if not frontier:
            break
    return ""


class Scope:
    """Everything the record holds on one target's question: hypotheses that answer it, experiments that test them,
    runs, results, claims, decisions, artifacts and sources. ``since`` keeps only evidence written at or after it
    (an order's issue time); the question and its artifacts are never filtered."""

    def __init__(self, s: D.Snap, t: str, since: str = "", who: str = ""):
        self.s, self.t, self.since = s, t, since
        n = s.nodes[t]
        self.inv = n["inv"]
        self.q = t if n["type"] == "question" else question_of(s, t)
        root = self.q or t
        self.root = root
        live = lambda i: _live(s, i)  # noqa: E731
        inn = lambda i, rel: [e["src"] for e in s.inn.get(i, []) if e["rel"] == rel]  # noqa: E731
        out = lambda i, rel: [e["dst"] for e in s.out.get(i, []) if e["rel"] == rel]  # noqa: E731
        typed = lambda ids, tt: [i for i in ids if s.nodes[i]["type"] == tt]  # noqa: E731
        # under an order, what the assignee wrote in this investigation since it was issued is work on it
        def mine(tt: str) -> list[str]:
            if not (who and since):
                return []
            return [i for i, m in s.nodes.items() if m["type"] == tt and m["inv"] == self.inv
                    and m["created_by"] == who and m["created_at"] >= since]
        self.hypotheses = _uniq(typed(inn(root, "answers"), "hypothesis") + ([t] if n["type"] == "hypothesis" else [])
                                + mine("hypothesis"))
        self.claims = _uniq(typed(inn(root, "answers"), "claim") + ([t] if n["type"] == "claim" else [])
                            + mine("claim"))
        exps = [x for h in self.hypotheses + self.claims for x in typed(inn(h, "tests"), "experiment")]
        exps += typed(inn(root, "part_of") + inn(root, "motivated_by"), "experiment")
        exps += [t] if n["type"] == "experiment" else []
        self.experiments = _uniq(exps + mine("experiment"))
        runs = [r for x in self.experiments for r in typed(inn(x, "executes"), "run")]
        runs += [t] if n["type"] == "run" else []
        runs += typed(inn(root, "part_of"), "run")
        self.runs = _uniq(runs + mine("run"))
        res = [r for run in self.runs for r in typed(out(run, "produced"), "result")]
        for x in self.hypotheses + self.claims:
            res += typed(inn(x, "supports") + inn(x, "challenges"), "result")
        for c in self.claims:
            res += typed(out(c, "derived_from"), "result")
        res += typed(inn(root, "part_of"), "result") + ([t] if n["type"] == "result" else [])
        self.results = _uniq(res + mine("result"))
        decs = [d for x in self.claims + self.results + self.hypotheses for d in typed(inn(x, "based_on"), "decision")]
        decs += [t] if n["type"] == "decision" else []
        self.decisions = _uniq(decs + mine("decision"))
        self.artifacts = _uniq(typed(inn(root, "part_of"), "artifact"))            # every version, live or superseded
        srcs = typed(inn(root, "part_of"), "source")
        for x in self.hypotheses + self.claims + self.experiments + self.results:
            srcs += typed(out(x, "cites"), "source")
        self.sources = _uniq(srcs)
        self._live = live

    def fresh(self, ids: list[str]) -> list[str]:
        """Live, and written since the order when one is in force."""
        return [i for i in ids if self._live(i) and (not self.since or self.s.nodes[i]["created_at"] >= self.since)]

    def code(self, i: str) -> str:
        return self.s.nodes[i].get("code") or i

    def lab_runs_using(self, artifacts: list[str]) -> list[str]:
        """Instrument runs anywhere in the investigation that use one of these artifacts."""
        s = self.s
        out = []
        for a in artifacts:
            for e in s.inn.get(a, []):
                r = e["src"]
                if e["rel"] == "uses" and s.nodes[r]["type"] == "run" and s.nodes[r]["body"].get("kind") == "lab" \
                        and s.nodes[r]["inv"] == self.inv:
                    out.append(r)
        return _uniq(out)


def _uniq(xs: list) -> list:
    return list(dict.fromkeys(xs))


def _positive_results(s: D.Snap, run: str) -> list[str]:
    return [e["dst"] for e in s.out.get(run, []) if e["rel"] == "produced" and s.nodes[e["dst"]]["type"] == "result"
            and s.nodes[e["dst"]]["body"].get("outcome") == "positive" and _live(s, e["dst"])]


def _uses(s: D.Snap, run: str) -> list[str]:
    return [e["dst"] for e in s.out.get(run, []) if e["rel"] == "uses"]


def _past(value: str, now: str) -> bool:
    """A date or timestamp is past when ``now``, cut to its own precision, is later. '' is never past."""
    v = str(value or "").strip()
    return bool(v) and bool(now) and now[:len(v)] > v


# ── gates ──────────────────────────────────────────────────────────

def _g(met: bool, evidence: list[str], why: str) -> dict:
    return {"met": met, "evidence": evidence, "why": "" if met else why}


def g_stated(sc: Scope, now: str) -> dict:
    return _g(True, [sc.root], "")


def g_hypothesis_stated(sc: Scope, now: str) -> dict:
    hs = [h for h in sc.fresh(sc.hypotheses) if sc.s.nodes[h]["body"].get("predictions")]
    return _g(bool(hs), hs, f"no live hypothesis with predictions answers {sc.code(sc.root)}")


def g_preregistered(sc: Scope, now: str) -> dict:
    s = sc.s
    ok, late, untested = [], [], []
    for x in sc.fresh(sc.experiments):
        tests = [e for e in s.out.get(x, []) if e["rel"] == "tests"]
        if not tests or not all(str((e.get("data") or {}).get("expected") or "").strip() for e in tests):
            untested.append(x)
            continue
        runs = [r for r in s.inn.get(x, []) if r["rel"] == "executes"]
        first_run = min((s.nodes[r["src"]]["created_at"] for r in runs), default="")
        if first_run and first_run < s.nodes[x]["created_at"]:
            late.append((x, next(r["src"] for r in runs if s.nodes[r["src"]]["created_at"] == first_run)))
        else:
            ok.append(x)
    if ok:
        return _g(True, ok, "")
    if late:
        x, r = late[0]
        return _g(False, [], f"{sc.code(x)} was written after {sc.code(r)} executed it — not preregistered; the "
                             "experiment (protocol, expected outcome) comes before the run")
    if untested:
        names = ", ".join(sc.code(x) for x in untested[:3])
        return _g(False, [], f"{names} tests nothing with an expected outcome — link it `tests` a hypothesis with "
                             "data.expected")
    return _g(False, [], f"no experiment tests a hypothesis on {sc.code(sc.root)}")


def g_run_registered(sc: Scope, now: str) -> dict:
    rs = sc.fresh(sc.runs)
    return _g(bool(rs), rs, f"no run executes an experiment on {sc.code(sc.root)}")


def g_result_exists(sc: Scope, now: str) -> dict:
    rs = sc.fresh(sc.results)
    return _g(bool(rs), rs, f"no live result on {sc.code(sc.root)}")


def g_claim_made(sc: Scope, now: str) -> dict:
    cs = sc.fresh(sc.claims)
    return _g(bool(cs), cs, f"no live claim answers {sc.code(sc.root)}")


def g_reviewed(sc: Scope, now: str) -> dict:
    s = sc.s
    checked = [c for c in sc.fresh(sc.claims) if (D.state(s, c).get("review") or {}).get("state") == "checked"]
    fresh = [c for c in checked if not D.stale(s, c)]
    if fresh:
        return _g(True, fresh, "")
    if checked:
        c = checked[0]
        return _g(False, [], f"{sc.code(c)} is checked but its evidence is stale: {'; '.join(D.stale(s, c)[:2])} — "
                             "rerun before the check counts")
    return _g(False, [], f"no claim answering {sc.code(sc.root)} is checked by a reviewer")


def g_decided(sc: Scope, now: str) -> dict:
    ds = sc.fresh(sc.decisions)
    return _g(bool(ds), ds, f"no decision is based on a claim or result on {sc.code(sc.root)}")


def _current_diffs(sc: Scope, kind: str) -> tuple[list[str], list[str]]:
    """(live, superseded-or-withdrawn) typed artifacts on the question, newest first."""
    s = sc.s
    typed = sorted((a for a in sc.artifacts if (s.nodes[a]["body"].get("kind") or "") == kind),
                   key=lambda a: s.nodes[a]["created_at"], reverse=True)
    live = [a for a in typed if D.lifecycle(s, a) == "active"]
    return live, [a for a in typed if a not in live]


def g_diff_registered(sc: Scope, now: str) -> dict:
    live, _old = _current_diffs(sc, "diff")
    live = [a for a in live if not sc.since or sc.s.nodes[a]["created_at"] >= sc.since]
    return _g(bool(live), live[:1], f"no live artifact kind=diff (meta: base_sha, head_sha, files) part_of "
                                    f"{sc.code(sc.root)}")


def g_tests_pass_current(sc: Scope, now: str) -> dict:
    s = sc.s
    live, old = _current_diffs(sc, "diff")
    if not live:
        return _g(False, [], f"no current diff on {sc.code(sc.root)} — register the change first")
    cur = live[0]
    for r in sc.lab_runs_using([cur]):
        if not _live(s, r) or (sc.since and s.nodes[r]["created_at"] < sc.since):
            continue
        pos = _positive_results(s, r)
        if pos:
            return _g(True, pos, "")
    for r in sc.lab_runs_using(old):
        if _positive_results(s, r):
            used = next(a for a in _uses(s, r) if a in old)
            was = (s.nodes[used]["body"].get("meta") or {}).get("head_sha", sc.code(used))
            head = (s.nodes[cur]["body"].get("meta") or {}).get("head_sha", sc.code(cur))
            return _g(False, [], f"tests passed on {str(was)[:12]} ({sc.code(used)}); the current head is "
                                 f"{str(head)[:12]} ({sc.code(cur)}) — rerun on it")
    return _g(False, [], f"no instrument run uses the current diff {sc.code(cur)} with a positive result")


def g_instance_registered(sc: Scope, now: str) -> dict:
    live, _old = _current_diffs(sc, "instance")
    return _g(bool(live), live[:1], f"no live artifact kind=instance part_of {sc.code(sc.root)}")


def g_source_quoted(sc: Scope, now: str) -> dict:
    s = sc.s
    good = [x for x in sc.fresh(sc.sources) if str(s.nodes[x]["body"].get("passage") or "").strip()
            and str(s.nodes[x]["body"].get("retrieved") or "").strip()]
    if good:
        return _g(True, good, "")
    partial = sc.fresh(sc.sources)
    if partial:
        miss = [k for k in ("passage", "retrieved") if not str(s.nodes[partial[0]]["body"].get(k) or "").strip()]
        return _g(False, [], f"{sc.code(partial[0])} lacks {' and '.join(miss)} — the passage that says it, and when "
                             "it was read")
    return _g(False, [], f"no source with its passage and retrieved date on {sc.code(sc.root)}")


def g_search_recorded(sc: Scope, now: str) -> dict:
    xs = [x for x in sc.fresh(sc.experiments) if str(sc.s.nodes[x]["body"].get("method") or "").lower() == "search"]
    return _g(bool(xs), xs, f"no experiment method=search records where {sc.code(sc.root)} was looked for")


def g_sourced(sc: Scope, now: str) -> dict:
    cs = [c for c in sc.fresh(sc.claims) if _cites_source(sc.s, c)]
    return _g(bool(cs), cs, f"no claim answering {sc.code(sc.root)} cites a live source")


def _trials(v: dict) -> bool:
    return _has(v, r"^trials?$|^n_?trials|configurations?|^n_?configs?|^configs?_tried|^grid_size")


def g_backtested(sc: Scope, now: str) -> dict:
    s = sc.s
    nearest, missing = "", []
    for r in sc.fresh(sc.results):
        v = _vals(s.nodes[r]["body"])
        miss = []
        if not _has(v, r"oos|out_of_sample|holdout|test_"):
            miss.append("an out-of-sample measure")
        if not _has(v, r"fee|cost|slippage|commission"):
            miss.append("the costs charged")
        if not _trials(v):
            miss.append("trials (configurations tried)")
        if not miss:
            return _g(True, [r], "")
        if not nearest or len(miss) < len(missing):
            nearest, missing = r, miss
    if nearest:
        return _g(False, [], f"{sc.code(nearest)} lacks {', '.join(missing)}")
    return _g(False, [], f"no backtest result on {sc.code(sc.root)}")


def _position_missing(body: dict) -> list[str]:
    miss = [k for k in ("size", "stop", "review_date") if not str(body.get(k) or "").strip()]
    if body.get("paper") not in _TRUE:
        miss.append("paper: true")
    return miss


def _positions(sc: Scope) -> list[str]:
    return [d for d in sc.decisions if _live(sc.s, d) and (sc.s.nodes[d]["body"].get("kind") or "") == "position"]


def g_positioned(sc: Scope, now: str) -> dict:
    s = sc.s
    ds = [d for d in _positions(sc) if (not sc.since or s.nodes[d]["created_at"] >= sc.since)
          and not _position_missing(s.nodes[d]["body"])]
    return _g(bool(ds), ds, f"no decision kind=position (size, stop, review_date, paper=true) based on a claim on "
                            f"{sc.code(sc.root)}")


def _past_review(sc: Scope, d: str, now: str) -> bool:
    """A position is past review when its review_date has passed and no result on the thesis was written after
    both that date and the position itself (the evidence the position was taken on doesn't renew it)."""
    s = sc.s
    rd = str(s.nodes[d]["body"].get("review_date") or "")
    if not _past(rd, now):
        return False
    order = {nid: i for i, nid in enumerate(s.nodes)}        # write order: the clock has one-second resolution
    return not any(s.nodes[r]["created_at"][:len(rd)] > rd and order[r] > order[d]
                   for r in sc.results if _live(s, r))


def g_still_valid(sc: Scope, now: str) -> dict:
    s = sc.s
    stale = []
    for d in _positions(sc):
        if _past_review(sc, d, now):
            stale.append(d)
    if stale:
        d = stale[0]
        return _g(False, [], f"{sc.code(d)} is past its review date {s.nodes[d]['body'].get('review_date')} with no "
                             "newer result on the thesis")
    return _g(True, _positions(sc), "")


def g_solved(sc: Scope, now: str) -> dict:
    s = sc.s
    for r in sc.fresh(sc.results):
        v = _vals(s.nodes[r]["body"])
        if "feasible" in v and v["feasible"] in (False, 0, "false", "False", "no"):
            return _g(True, [r], "")
        if "objective" in v and v.get("feasible") in _TRUE and ("bound" in v or "gap" in v):
            return _g(True, [r], "")
    return _g(False, [], f"no result on {sc.code(sc.root)} with objective, feasible=true and a bound or gap (or "
                         "feasible=false)")


def g_result_reviewed(sc: Scope, now: str) -> dict:
    s = sc.s
    rs = [r for r in sc.fresh(sc.results) if (D.state(s, r).get("review") or {}).get("state") == "checked"]
    return _g(bool(rs), rs, f"no result on {sc.code(sc.root)} is checked by a reviewer")


GATES: dict[str, Callable[[Scope, str], dict]] = {
    "stated": g_stated, "hypothesis_stated": g_hypothesis_stated, "preregistered": g_preregistered,
    "run_registered": g_run_registered, "result_exists": g_result_exists, "claim_made": g_claim_made,
    "reviewed": g_reviewed, "decided": g_decided, "diff_registered": g_diff_registered,
    "tests_pass_current": g_tests_pass_current, "instance_registered": g_instance_registered,
    "source_quoted": g_source_quoted, "search_recorded": g_search_recorded, "sourced": g_sourced,
    "backtested": g_backtested, "positioned": g_positioned, "still_valid": g_still_valid, "solved": g_solved,
    "result_reviewed": g_result_reviewed,
}


def evaluate_predicate(p: str, s: D.Snap, t: str, at: str, inv: str, who: str = "") -> dict:
    """A workflow gate as an order predicate: scoped to the target's question plus what the assignee wrote under
    the order; only evidence since the order counts."""
    if not t or t not in s.nodes:
        return {"met": False, "evidence": [], "why": "the order has no target"}
    return GATES[p](Scope(s, t, since=at, who=who), s.now)


# ── the derived stage ──────────────────────────────────────────────

def stage_of(s: D.Snap, t: str, now: str = "") -> dict:
    """The stage a question (or the question a node is about) is in, with every gate's status."""
    n = s.nodes[t]
    p = profile_of(s, n["inv"])
    sc = Scope(s, t)
    q = sc.root
    base = {"question": q, "code": s.nodes[q].get("code") or q, "profile": p.id if p else ""}
    if not p or not p.workflow:
        return {**base, "workflow": False, "stage": "", "index": 0, "of": 0, "complete": False,
                "next": "no workflow: the profile has no stages (pin an @2 profile)", "gates": []}
    now = now or s.now
    gates, stage, nxt = [], None, ""
    for i, st in enumerate(p.workflow.stages):
        r = GATES[st.gate](sc, now)
        gates.append({"stage": st.name, "gate": st.gate, "met": r["met"], "optional": st.optional, "why": r["why"],
                      "evidence": [sc.code(x) for x in r["evidence"][:6]], "who": st.who})
        if stage is None and not r["met"] and not st.optional:
            stage, nxt = (i, st.name), r["why"]
    stages = p.workflow.stages
    if stage is None:                            # every required gate met: the stage is the last one whose gate is
        last = max(i for i, gt in enumerate(gates) if gt["met"])
        return {**base, "workflow": True, "stage": stages[last].name, "index": last + 1, "of": len(stages),
                "complete": True, "next": "", "gates": gates}
    return {**base, "workflow": True, "stage": stage[1], "index": stage[0] + 1, "of": len(stages), "complete": False,
            "next": nxt, "gates": gates}


def stages(s: D.Snap, inv: str, now: str = "") -> list[dict]:
    qs = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "question" and _live(s, i)]
    return [stage_of(s, q, now) for q in sorted(qs, key=lambda i: s.nodes[i]["created_at"])]


def stage_lines(s: D.Snap, inv: str, now: str = "") -> list[str]:
    out = []
    for x in stages(s, inv, now):
        if not x["workflow"]:
            continue
        line = f"{x['code']}: {x['stage']} ({x['index']}/{x['of']})" + (" — complete" if x["complete"] else
                                                                        f" — next: {x['next']}")
        out.append(line)
    return out


# ── refusals (write time) ──────────────────────────────────────────

def _supporting_results(s: D.Snap, support: list) -> list[str]:
    return [x for x in support if x in s.nodes and s.nodes[x]["type"] == "result"]


def claim_issues(p: Profile, s: D.Snap, inv: str, body: dict, support: list, pending: list) -> list[Problem]:
    stmt = body.get("statement", "")
    results = _supporting_results(s, support)
    out: list[Problem] = []
    if "pass_needs_current_head" in p.validators and L.asserted(_PASSES, stmt):
        backed = [r for r in results if _instrument_backed(s, r)]
        if backed and all(D.stale(s, r) for r in backed):
            out.append(Problem("TESTS_ON_STALE_HEAD", "'passes' is asserted on instrument runs whose change has since "
                               f"been superseded ({'; '.join(D.stale(s, backed[0])[:1])}) — the tests ran on an "
                               "older head",
                               fix="rerun the tests on the current diff; the new lab result is the evidence"))
    if "edge_needs_trials" in p.validators and L.asserted(_EDGE, stmt):
        if results and not any(_trials(_vals(s.nodes[r]["body"])) for r in results):
            out.append(Problem("EDGE_WITHOUT_TRIALS", "an edge is asserted, but no supporting result states how many "
                               "configurations were tried — the more tried, the less an out-of-sample result means",
                               fix="add values.trials (configurations / parameter sets tried) to the backtest result"))
    if "optimal_needs_fresh_instance" in p.validators and L.asserted(_OPTIMAL, stmt):
        bounded = [r for r in results if {"bound", "gap"} & set(_vals(s.nodes[r]["body"]))]
        if bounded and all(D.stale(s, r) for r in bounded):
            out.append(Problem("OPTIMAL_ON_STALE_INSTANCE", "'optimal' is asserted on a solve whose instance has since "
                               f"changed ({'; '.join(D.stale(s, bounded[0])[:1])})",
                               fix="re-solve on the current instance; bind the claim to that result"))
    return out


def result_issues(p: Profile, s: D.Snap, inv: str, body: dict, pending: list) -> list[Problem]:
    out: list[Problem] = []
    v = _vals(body)
    if "solve_needs_instance" in p.validators and "objective" in v:
        runs = [a for a, rel, b in pending if rel == "produced" and a in s.nodes and s.nodes[a]["type"] == "run"]
        used = [x for r in runs for x in _uses(s, r) if (s.nodes[x]["body"].get("kind") or "") == "instance"]
        if not used:
            out.append(Problem("SOLVED_WITHOUT_INSTANCE", "a solve result must come from a run that uses the instance "
                               "artifact (kind=instance) — otherwise nobody can say what was solved" if runs else
                               "a solve result must be produced by a run that uses the instance artifact (kind=instance)",
                               fix="register the instance as an artifact, link the run `uses` it, then the result `produced` by the run"))
    return out


def node_issues(p: Profile, s: D.Snap, inv: str, ntype: str, body: dict, pending: list) -> list[Problem]:
    w = p.workflow
    out: list[Problem] = []
    if ntype == "artifact" and w and (body.get("kind") or "") in w.artifacts:
        kind = body["kind"]
        meta = body.get("meta") or {}
        miss = ([] if str(body.get("path") or "").strip() else ["path"]) + \
               [f"meta.{k}" for k in w.artifacts[kind] if k not in meta or meta[k] in (None, "", [], {})]
        if miss:
            out.append(Problem("ARTIFACT_MISSING_FIELDS", f"an artifact kind={kind} needs {', '.join(miss)} in this "
                               f"workflow ({p.id})", fix=f"add {', '.join(miss)}; meta is a dict of the kind's fields"))
    if ntype == "source" and "source_needs_passage" in p.validators and not str(body.get("passage") or "").strip():
        out.append(Problem("PASSAGE_MISSING", "a source needs the passage that says it — a citation alone is a pointer, "
                           "not evidence", fix="add passage (the words, quoted) and retrieved (when you read it)"))
    if ntype == "decision":
        choice = str(body.get("choice") or "")
        kind = str(body.get("kind") or "")
        if "no_live_orders" in p.validators and L.asserted(_LIVE_ORDER, choice + " " + str(body.get("reasons") or "")):
            out.append(Problem("LIVE_ORDER", "this decision names a live order — there is no live-order path in this "
                               "workflow; positions are paper (kind=position, paper=true)",
                               fix="record a paper position: kind=position, size, stop, review_date, paper=true"))
        is_position = kind == "position" or (not kind and _POSITION_WORDS.search(choice)
                                             and any(rel == "based_on" for _a, rel, _b in pending))
        if "position_needs_risk" in p.validators and is_position:
            miss = _position_missing(body)
            if miss:
                out.append(Problem("POSITION_WITHOUT_STOP", f"a position needs {', '.join(miss)} — a position without "
                                   "its size, stop and review date is a wish, not a decision",
                                   fix="add kind=position, size, stop, review_date and paper=true"))
    return out


def review_refusal(p: Profile, s: D.Snap, target: str, author: str) -> str:
    """software: a reviewer who authored the diff under a claim can't check that claim."""
    n = s.nodes.get(target)
    if not n or n["type"] != "claim" or "pass_needs_current_head" not in p.validators:
        return ""
    results = [e["src"] for e in s.inn.get(target, []) if e["rel"] == "supports" and s.nodes[e["src"]]["type"] == "result"]
    results += [e["dst"] for e in s.out.get(target, []) if e["rel"] == "derived_from" and s.nodes[e["dst"]]["type"] == "result"]
    for r in results:
        run = _producing_run(s, r)
        for a in (_uses(s, run) if run else []):
            if (s.nodes[a]["body"].get("kind") or "") == "diff" and s.nodes[a]["created_by"] == author:
                return (f"you authored the change ({s.nodes[a].get('code') or a}) this claim rests on — a reviewer who "
                        "wrote neither the claim nor the diff checks it [REVIEW_BY_AUTHOR]")
    return ""


# ── completion criteria the workflows add ──────────────────────────

def _checked_claims(s: D.Snap, q: str) -> list[str]:
    return [e["src"] for e in s.inn.get(q, []) if e["rel"] == "answers" and s.nodes[e["src"]]["type"] == "claim"
            and _live(s, e["src"]) and (D.state(s, e["src"]).get("review") or {}).get("state") == "checked"]


def criterion(name: str, s: D.Snap, inv: str) -> dict:
    from .profiles import _questions
    qs = _questions(s, inv)
    now = s.now
    if name == "requirements_verified_current":
        bad = []
        for q in qs:
            ok = False
            for c in _checked_claims(s, q):              # any checked answer resting on a fresh instrument run
                rs = [e["src"] for e in s.inn.get(c, []) if e["rel"] == "supports"] + \
                     [e["dst"] for e in s.out.get(c, []) if e["rel"] == "derived_from"]
                if any(s.nodes[r]["type"] == "result" and _lab_positive(s, r) and not D.stale(s, r) for r in rs):
                    ok = True
                    break
            if not ok:
                bad.append(s.nodes[q]["code"])
        return {"met": bool(qs) and not bad, "why": "every requirement's claim rests on a passing instrument run on the "
                "current head" if qs and not bad else "no current instrument-run evidence for: " + ", ".join(bad)}
    if name == "position_sized":
        ds = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "decision" and _live(s, i)
              and (n["body"].get("kind") or "") == "position" and not _position_missing(n["body"])
              and any(e["rel"] == "based_on" for e in s.out.get(i, []))]
        return {"met": bool(ds), "why": f"{len(ds)} paper position(s) with size, stop and review date" if ds else
                "no decision kind=position with size, stop, review_date and paper=true based on a claim"}
    if name == "nothing_past_review":
        late = []
        for i, n in s.nodes.items():
            if n["inv"] == inv and n["type"] == "decision" and _live(s, i) and (n["body"].get("kind") or "") == "position":
                if _past_review(Scope(s, i), i, now):
                    late.append(n["code"])
        return {"met": not late, "why": "no position is past its review date without a newer result" if not late else
                "past review with no newer result: " + ", ".join(late)}
    if name == "all_checked":
        cl = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "claim" and _live(s, i)
              and (n["body"].get("kind") or "finding") in ("finding", "exclusion")]
        bad = [s.nodes[c]["code"] for c in cl if (D.state(s, c).get("review") or {}).get("state") != "checked"]
        return {"met": bool(cl) and not bad, "why": "every claim is checked by a fact-checker" if cl and not bad else
                ("no claims" if not cl else "unchecked: " + ", ".join(bad))}
    if name == "incumbent_verified":
        rs = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "result" and _live(s, i)]
        good = [r for r in rs if "objective" in _vals(s.nodes[r]["body"]) and _vals(s.nodes[r]["body"]).get("feasible")
                in _TRUE and ({"bound", "gap"} & set(_vals(s.nodes[r]["body"])))
                and (D.state(s, r).get("review") or {}).get("state") == "checked" and not D.stale(s, r)]
        return {"met": bool(good), "why": f"{len(good)} incumbent(s) verified by a reviewer on the current instance"
                if good else "no feasible bounded incumbent is checked by a verifier (on the current instance)"}
    return {"met": False, "why": "unknown criterion"}


__all__ = ["GATES", "Scope", "claim_issues", "criterion", "evaluate_predicate", "node_issues", "question_of",
           "result_issues", "review_refusal", "stage_lines", "stage_of", "stages"]

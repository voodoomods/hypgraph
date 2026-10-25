"""
Governance profiles: what a domain means by evidence, acceptance and done — versioned, pinned on the investigation,
and enforced by the record rather than by prompts.

A profile is a named, versioned set of
  vocabulary     what each node type means in the domain (shown to agents, never enforced)
  done_when      the default predicates an order on each target type must meet
  predicates     domain predicates the record can check (beyond coord.PREDICATES)
  validators     domain refusals at write time, on claims and results
  completion     what "the investigation is done" means, as criteria the record derives

An investigation pins ``profile: "software@1"``. Without one, nothing changes: ``scientific@1`` is today's behaviour
and is what the engine does with no profile at all. Rules never change under a version; a changed rule is @2.

    from hypgraph import profiles
    profiles.get("trading@1").about
    g.create(author=..., type="investigation", fields={..., "profile": "software@1"})
    g.completion(inv)      # {"profile", "criteria": [{name, met, why}], "complete"}
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import derive as D
from . import language as L
from .checks import Problem

# ── the profiles ───────────────────────────────────────────────────


@dataclass(frozen=True)
class Profile:
    name: str
    version: int
    about: str
    vocabulary: dict = field(default_factory=dict)        # node type → meaning here
    done_when: dict = field(default_factory=dict)         # target type → [{"p": …}]
    predicates: tuple = ()                                # names from PRED_DESC this profile uses
    validators: tuple = ()                                # names from _CLAIM_VALIDATORS / _RESULT_VALIDATORS
    completion: tuple = ("questions_settled",)            # names from _CRITERIA
    seats: tuple = ()                                     # suggested seat templates: (name, role, takes...)

    @property
    def id(self) -> str:
        return f"{self.name}@{self.version}"


PRED_DESC = {
    "tests_pass": "a result from an instrument-recorded (kind=lab) run — tests executed, not described — with a "
                  "positive outcome, bearing on the target and written after the order",
    "backtested_oos": "a result on the target whose values include an out-of-sample measure and a cost / fee / "
                      "slippage measure, written after the order",
    "sourced": "a claim on the target that cites a live source node, written after the order",
    "feasible_bounded": "a result on the target whose values carry objective, feasible (true) and a bound or gap, "
                        "written after the order",
}
RECIPES = {
    "tests_pass": {"*": "register_run with the exact test command as code — the instrument re-executes it and files "
                        "the lab run; a passing re-run is what meets this, not your report of one"},
    "backtested_oos": {"*": "register_run with values that name the out-of-sample window (oos_return, oos_sharpe …) "
                            "and the costs (fees, slippage) the backtest charged"},
    "sourced": {"*": "graph_add(type=\"source\", {citation, url|doi, passage}) then the claim with links "
                     "[{\"rel\": \"cites\", \"to\": <source>}]"},
    "feasible_bounded": {"*": "register_run with values {objective: …, feasible: true, bound: … | gap: …}"},
}

PROFILES: dict[str, Profile] = {}


def _add(p: Profile) -> Profile:
    PROFILES[p.id] = p
    return p


SCIENTIFIC = _add(Profile(
    "scientific", 1,
    "Questions answered by claims bound to measured results and checked by a reviewer — the engine's default.",
    vocabulary={"question": "something you want to know", "hypothesis": "a possible answer with predictions",
                "experiment": "a planned test", "run": "one execution", "result": "what a run found",
                "claim": "what you assert is known, numbers bound to results"},
    completion=("questions_settled",),
    seats=(("analyst", "worker", "accuracy", "counts", "means"), ("stats", "worker", "significant", "test", "interval"),
           ("critic", "reviewer"), ("lead", "lead")),
))

SOFTWARE = _add(Profile(
    "software", 1,
    "Requirements verified by tests the instrument ran: 'it passes' is a lab-recorded run's outcome, never a report.",
    vocabulary={"question": "a requirement or a bug to resolve", "hypothesis": "a design or a suspected cause",
                "experiment": "a test plan", "run": "a test / build / CI execution (lab = the instrument ran it)",
                "result": "test results, coverage, benchmarks", "claim": "a verified statement about the code",
                "artifact": "a commit, a diff, a build, by hash"},
    done_when={"question": [{"p": "tests_pass"}, {"p": "claim_made"}], "experiment": [{"p": "tests_pass"}],
               "claim": [{"p": "reviewed"}]},
    predicates=("tests_pass",), validators=("pass_needs_instrument",),
    completion=("questions_settled", "requirements_verified"),
    seats=(("implementer", "worker", "implement", "fix", "code", "function"), ("tester", "worker", "test", "verify", "regression"),
           ("reviewer", "reviewer"), ("lead", "lead")),
))

TRADING = _add(Profile(
    "trading", 1,
    "A thesis is a hypothesis; an edge exists only out of sample and after costs; positions are paper until a "
    "decision records size and risk.",
    vocabulary={"question": "a market question", "hypothesis": "a trading thesis with the move it predicts",
                "experiment": "a preregistered backtest or paper trade", "run": "a backtest or data pull",
                "result": "returns, drawdown, Sharpe — in and out of sample, after costs",
                "claim": "a statement about an edge or a risk", "decision": "a sized paper position with a stop"},
    done_when={"question": [{"p": "backtested_oos"}, {"p": "claim_made"}], "hypothesis": [{"p": "backtested_oos"}],
               "experiment": [{"p": "run_registered"}, {"p": "backtested_oos"}], "claim": [{"p": "reviewed"}]},
    predicates=("backtested_oos",), validators=("edge_needs_oos_costs", "backtest_needs_costs"),
    completion=("questions_settled", "position_recorded"),
    seats=(("quant", "worker", "backtest", "returns", "indicator", "data"), ("risk", "reviewer"), ("lead", "lead")),
))

KNOWLEDGE = _add(Profile(
    "knowledge", 1,
    "Answers from sources: every factual claim cites a source node the record holds, and the report is linted "
    "against the record.",
    vocabulary={"question": "what the reader wants to know", "source": "a document, page or dataset with the passage "
                "that says it", "result": "what a source says, as values", "claim": "a sourced statement"},
    done_when={"question": [{"p": "sourced"}], "claim": [{"p": "reviewed"}]},
    predicates=("sourced",), validators=("claim_needs_source",),
    completion=("questions_settled", "all_sourced"),
    seats=(("researcher", "worker", "find", "source", "cite", "look"), ("fact_checker", "reviewer"), ("lead", "lead")),
))

OPTIMIZATION = _add(Profile(
    "optimization", 1,
    "An objective under constraints: a solution is a feasible incumbent with a bound or gap; 'optimal' needs the bound.",
    vocabulary={"question": "what to minimise or maximise, under which constraints", "hypothesis": "a modelling choice",
                "experiment": "a solve configuration", "run": "a solver execution",
                "result": "objective, feasibility, bound, gap, runtime", "claim": "a statement about the solution"},
    done_when={"question": [{"p": "feasible_bounded"}, {"p": "claim_made"}], "experiment": [{"p": "feasible_bounded"}],
               "claim": [{"p": "reviewed"}]},
    predicates=("feasible_bounded",), validators=("optimal_needs_bound", "objective_needs_feasibility"),
    completion=("questions_settled", "incumbent_feasible"),
    seats=(("modeller", "worker", "model", "constraint", "objective"), ("solver", "worker", "solve", "bound", "gap"),
           ("verifier", "reviewer"), ("lead", "lead")),
))


def get(pid: str) -> Profile:
    p = PROFILES.get(str(pid or "").strip().lower())
    if not p:
        raise KeyError(f"unknown profile {pid!r}; profiles: {', '.join(sorted(PROFILES))}")
    return p


def validate_profile_id(pid) -> str:
    """'' or a known id; anything else is refused at the investigation's creation (fail closed)."""
    if not pid:
        return ""
    return get(str(pid)).id


def profile_of(s: D.Snap, inv: str) -> Profile | None:
    n = s.nodes.get(inv) if inv else None
    pid = (n or {}).get("body", {}).get("profile") if n else None
    return PROFILES.get(str(pid).lower()) if pid else None


def default_done(s: D.Snap, inv: str, target_type: str) -> list | None:
    p = profile_of(s, inv)
    return list(p.done_when[target_type]) if p and target_type in p.done_when else None


# ── helpers over the snapshot ─────────────────────────────────────

def _live(s: D.Snap, i: str) -> bool:
    return D.lifecycle(s, i) == "active" and not D.fallen(s, i)


def _after(s: D.Snap, i: str, at: str) -> bool:
    return s.nodes[i]["created_at"] >= at


def _vals(body: dict) -> dict:
    out = {}
    for k, v in (body.get("values") or {}).items():
        out[str(k).lower()] = v.get("value") if isinstance(v, dict) and "value" in v else v
    return out


def _has(keys, *pats: str) -> bool:
    return any(re.search(p, k) for k in keys for p in pats)


def _producing_run(s: D.Snap, rid: str) -> str:
    for e in s.inn.get(rid, []):
        if e["rel"] == "produced":
            return e["src"]
    return ""


def _lab_positive(s: D.Snap, rid: str) -> bool:
    r = _producing_run(s, rid)
    return bool(r) and s.nodes[r]["body"].get("kind") == "lab" and s.nodes[rid]["body"].get("outcome") == "positive"


def _bearing(s: D.Snap, t: str, ntype: str) -> list[str]:
    """Nodes of a type linked to the target by any relation, either way."""
    out = [e["src"] for e in s.inn.get(t, []) if s.nodes[e["src"]]["type"] == ntype]
    out += [e["dst"] for e in s.out.get(t, []) if s.nodes[e["dst"]]["type"] == ntype]
    if ntype == "result":                          # results of runs executing an experiment target
        for r in (e["src"] for e in s.inn.get(t, []) if e["rel"] == "executes"):
            out += [e["dst"] for e in s.out.get(r, []) if e["rel"] == "produced" and s.nodes[e["dst"]]["type"] == "result"]
        for c in (e["src"] for e in s.inn.get(t, []) if e["rel"] == "answers"):      # a question's answers' results
            out += [e["dst"] for e in s.out.get(c, []) if e["rel"] == "derived_from" and s.nodes[e["dst"]]["type"] == "result"]
            out += [e["src"] for e in s.inn.get(c, []) if e["rel"] == "supports" and s.nodes[e["src"]]["type"] == "result"]
    return list(dict.fromkeys(out))


def _cites_source(s: D.Snap, c: str) -> bool:
    return any(e["rel"] == "cites" and s.nodes[e["dst"]]["type"] == "source" and _live(s, e["dst"])
               for e in s.out.get(c, []))


def evaluate(p: str, s: D.Snap, oid: str, t: str, at: str, who: str, inv: str) -> dict:
    """A profile predicate on an order: {met, evidence, why}. Only evidence written after the order counts."""
    def mine(ntype: str) -> list[str]:
        return [i for i, n in s.nodes.items() if n["type"] == ntype and n["inv"] == inv and n["created_by"] == who
                and _after(s, i, at) and _live(s, i)]
    cands = [r for r in _bearing(s, t, "result") if _after(s, r, at) and _live(s, r)] + mine("result") if t else mine("result")
    cands = list(dict.fromkeys(cands))
    if p == "tests_pass":
        ids = [r for r in cands if _lab_positive(s, r)]
        # a lab re-run of the assignee's own run also counts: it replicates a run written under the order
        for r in [i for i, n in s.nodes.items() if n["type"] == "run" and n["inv"] == inv and n["body"].get("kind") == "lab"
                  and _after(s, i, at)]:
            if any(e["rel"] == "replicates" and s.nodes[e["dst"]]["created_by"] == who for e in s.out.get(r, [])):
                ids += [e["dst"] for e in s.out.get(r, []) if e["rel"] == "produced"
                        and s.nodes[e["dst"]]["body"].get("outcome") == "positive"]
        ids = list(dict.fromkeys(ids))
        return {"met": bool(ids), "evidence": ids,
                "why": "" if ids else "no positive result from an instrument-recorded run since the order (a report "
                                      "of passing tests is not a run of them)"}
    if p == "backtested_oos":
        ids = [r for r in cands if _has(_vals(s.nodes[r]["body"]), r"oos|out_of_sample|holdout|test_")
               and _has(_vals(s.nodes[r]["body"]), r"fee|cost|slippage|commission")]
        return {"met": bool(ids), "evidence": ids,
                "why": "" if ids else "no result with both an out-of-sample measure and a cost measure since the order"}
    if p == "sourced":
        cl = [c for c in (_bearing(s, t, "claim") if t else []) + mine("claim") if _after(s, c, at) and _live(s, c)
              and _cites_source(s, c)]
        cl = list(dict.fromkeys(cl))
        return {"met": bool(cl), "evidence": cl, "why": "" if cl else "no claim on the target cites a live source since the order"}
    if p == "feasible_bounded":
        ids = []
        for r in cands:
            v = _vals(s.nodes[r]["body"])
            if "objective" in v and v.get("feasible") in (True, 1, "true", "True") and ("bound" in v or "gap" in v):
                ids.append(r)
        return {"met": bool(ids), "evidence": ids,
                "why": "" if ids else "no result with objective, feasible=true and a bound or gap since the order"}
    return {"met": False, "evidence": [], "why": f"unknown predicate {p!r}"}


# ── validators (write-time refusals) ──────────────────────────────

_EDGE = re.compile(r"\b(edge|alpha|outperform\w*|beats?|profitable|excess returns?)\b", re.I)
_OPTIMAL = re.compile(r"\b(optimal|optimum|best possible|minimum possible|maximum possible|cannot be improved)\b", re.I)
_PASSES = re.compile(r"\b(passes|passing|all tests pass|works correctly|is fixed|bug is fixed|implemented correctly)\b", re.I)


def claim_issues(s: D.Snap, inv: str, body: dict, support: list, pending: list) -> list[Problem]:
    p = profile_of(s, inv)
    if not p:
        return []
    stmt = body.get("statement", "")
    kind = body.get("kind") or "finding"
    out: list[Problem] = []
    results = [x for x in support if x in s.nodes and s.nodes[x]["type"] == "result"]
    if "edge_needs_oos_costs" in p.validators and L.asserted(_EDGE, stmt):
        ok = any(_has(_vals(s.nodes[r]["body"]), r"oos|out_of_sample|holdout") and
                 _has(_vals(s.nodes[r]["body"]), r"fee|cost|slippage|commission") for r in results)
        if not ok:
            out.append(Problem("EDGE_WITHOUT_OOS_COSTS", "an edge is asserted, but no supporting result carries both an "
                               "out-of-sample measure and the costs charged — in-sample, pre-cost returns are not an edge",
                               fix="support the claim with a result whose values include oos_* and fees/slippage"))
    if "optimal_needs_bound" in p.validators and L.asserted(_OPTIMAL, stmt):
        ok = any({"bound", "gap"} & set(_vals(s.nodes[r]["body"])) for r in results)
        if not ok:
            out.append(Problem("OPTIMAL_WITHOUT_BOUND", "'optimal' is asserted, but no supporting result carries a bound "
                               "or gap — an incumbent without a bound is a solution, not an optimum",
                               fix="bind a result with bound or gap, or say 'best found'"))
    if "pass_needs_instrument" in p.validators and L.asserted(_PASSES, stmt):
        ok = any(_lab_positive(s, r) for r in results)
        if not ok:
            out.append(Problem("PASS_WITHOUT_INSTRUMENT_RUN", "'passes' is asserted, but no supporting result comes "
                               "from an instrument-recorded run — tests must be run by the instrument, not reported",
                               fix="register_run with the test command as code; the instrument's re-run is the evidence"))
    if "claim_needs_source" in p.validators and kind in ("finding", "exclusion"):
        cites = any(rel == "cites" and s.nodes.get(b, {}).get("type") == "source" for a, rel, b in pending) or \
            any(_cites_source(s, x) for x in support if x in s.nodes and s.nodes[x]["type"] in ("claim", "result"))
        if not cites:
            out.append(Problem("CLAIM_WITHOUT_SOURCE", "a knowledge claim must cite a source node (citation, url or doi, "
                               "the passage) — the record holds what was read, not what was recalled",
                               fix="graph_add a source, then link the claim with {\"rel\": \"cites\", \"to\": <source>}"))
    return out


def result_issues(s: D.Snap, inv: str, body: dict) -> list[Problem]:
    p = profile_of(s, inv)
    if not p:
        return []
    v = _vals(body)
    out: list[Problem] = []
    if "objective_needs_feasibility" in p.validators and "objective" in v and "feasible" not in v:
        out.append(Problem("OBJECTIVE_WITHOUT_FEASIBILITY", "a result reports an objective value without saying whether "
                           "the solution is feasible", fix="add values.feasible (true/false) and bound or gap"))
    if "backtest_needs_costs" in p.validators and _has(v, r"return|sharpe|pnl|cagr|profit") and \
            not _has(v, r"fee|cost|slippage|commission"):
        out.append(Problem("BACKTEST_WITHOUT_COSTS", "a backtest result reports returns without the costs it charged",
                           fix="add values for fees and slippage (zero is a value; absence isn't)"))
    return out


# ── completion ────────────────────────────────────────────────────

def _questions(s: D.Snap, inv: str) -> list[str]:
    return [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "question" and _live(s, i)]


def _settling_claim(s: D.Snap, q: str) -> str:
    for e in s.inn.get(q, []):
        c = e["src"]
        if e["rel"] == "answers" and s.nodes[c]["type"] == "claim" and _live(s, c) and \
                (D.state(s, c).get("review") or {}).get("state") == "checked":
            return c
    return ""


def _criterion(name: str, s: D.Snap, inv: str) -> dict:
    qs = _questions(s, inv)
    if name == "questions_settled":
        open_ = [s.nodes[q]["code"] for q in qs if not _settling_claim(s, q)]
        return {"name": name, "met": bool(qs) and not open_,
                "why": "every question is settled by a checked claim" if qs and not open_ else
                       ("no questions" if not qs else "not settled: " + ", ".join(open_))}
    if name == "requirements_verified":
        bad = []
        for q in qs:
            c = _settling_claim(s, q)
            ok = bool(c) and any(_lab_positive(s, r) for r in _bearing(s, c, "result"))
            if not ok:
                bad.append(s.nodes[q]["code"])
        return {"name": name, "met": bool(qs) and not bad,
                "why": "every requirement's claim rests on a passing instrument run" if qs and not bad else
                       "no instrument-run evidence for: " + ", ".join(bad)}
    if name == "position_recorded":
        ds = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "decision" and _live(s, i)
              and any(e["rel"] == "based_on" for e in s.out.get(i, []))]
        return {"name": name, "met": bool(ds), "why": f"{len(ds)} decision(s) based on the evidence" if ds else
                "no decision node based_on a claim or result (a sized paper position is a decision)"}
    if name == "all_sourced":
        cl = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "claim" and _live(s, i)
              and (n["body"].get("kind") or "finding") in ("finding", "exclusion")]
        bad = [s.nodes[c]["code"] for c in cl if not _cites_source(s, c)]
        return {"name": name, "met": bool(cl) and not bad, "why": "every claim cites a source" if cl and not bad else
                ("no claims" if not cl else "unsourced: " + ", ".join(bad))}
    if name == "incumbent_feasible":
        rs = [i for i, n in s.nodes.items() if n["inv"] == inv and n["type"] == "result" and _live(s, i)]
        good = [r for r in rs if "objective" in _vals(s.nodes[r]["body"]) and _vals(s.nodes[r]["body"]).get("feasible")
                in (True, 1, "true", "True") and ({"bound", "gap"} & set(_vals(s.nodes[r]["body"])))]
        return {"name": name, "met": bool(good), "why": f"{len(good)} feasible incumbent(s) with a bound" if good else
                "no result with objective, feasible=true and a bound or gap"}
    return {"name": name, "met": False, "why": "unknown criterion"}


def completion(s: D.Snap, inv: str) -> dict:
    p = profile_of(s, inv) or SCIENTIFIC
    crit = [_criterion(c, s, inv) for c in p.completion]
    return {"investigation": inv, "profile": p.id, "pinned": bool(profile_of(s, inv)),
            "criteria": crit, "complete": all(c["met"] for c in crit)}


def describe() -> dict:
    return {pid: {"about": p.about, "vocabulary": p.vocabulary, "done_when": p.done_when, "predicates": list(p.predicates),
                  "validators": list(p.validators), "completion": list(p.completion),
                  "seats": [list(x) for x in p.seats]} for pid, p in PROFILES.items()}


__all__ = ["PRED_DESC", "PROFILES", "Profile", "RECIPES", "claim_issues", "completion", "default_done", "describe",
           "evaluate", "get", "profile_of", "result_issues", "validate_profile_id"]

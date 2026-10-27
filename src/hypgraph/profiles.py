"""
Governance profiles: what a domain means by evidence, acceptance and done — versioned, pinned on the investigation,
and enforced by the record rather than by prompts.

A profile is a named, versioned set of
  vocabulary     what each node type means in the domain (shown to agents, never enforced)
  done_when      the default predicates an order on each target type must meet
  predicates     domain predicates the record can check (beyond coord.PREDICATES)
  validators     domain refusals at write time, on claims, results, artifacts, sources and decisions
  completion     what "the investigation is done" means, as criteria the record derives
  workflow       (@2) the discipline's own method as stages with gates, what invalidates evidence, what "fresh"
                 means, the typed artifacts — see docs/workflows/ and workflow.py

An investigation pins ``profile: "software@1"``. Without one, nothing changes: ``scientific@1`` is today's behaviour
and is what the engine does with no profile at all. Rules never change under a version; a changed rule is @2. The
``@2`` profiles carry a workflow; the ``@1`` profiles are frozen as they were.

    from hypgraph import profiles
    profiles.get("trading@2").workflow.stages
    g.create(author=..., type="investigation", fields={..., "profile": "software@2"})
    g.completion(inv)      # {"profile", "criteria": [{name, met, why}], "complete"}
    g.stage(q)             # the stage a question is in, derived from the record, never set
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import derive as D
from . import language as L
from .checks import Problem

# ── the profiles ───────────────────────────────────────────────────


@dataclass(frozen=True)
class Stage:
    """One stage of a discipline's workflow. A question is in the first stage whose gate is not met; the stage is
    read off the record, never written. ``gate`` names a check in workflow.GATES."""
    name: str
    holds: str                                            # what the record holds at this stage, one line
    gate: str                                             # the gate out of it
    who: str = ""                                         # the seat that works it (suggested)
    optional: bool = False                                # reported, never blocks the stage derivation


@dataclass(frozen=True)
class Workflow:
    """A discipline's method as the record enforces it: stages and gates, the relations whose far end falling puts
    dependants AT RISK beyond schema.RISKY, the typed artifacts / sources / decisions and their required fields."""
    method: str                                           # the method it is taken from (quoted in docs/workflows/)
    stages: tuple = ()                                    # Stage, in order
    invalidates: tuple = ()                               # relations added to schema.RISKY for this profile
    artifacts: dict = field(default_factory=dict)         # artifact kind → required meta keys (path always required)
    decisions: dict = field(default_factory=dict)         # decision kind → required fields
    report: str = "Facts from the record"                 # the report's name
    measure_skips: tuple = ()                             # gates a question with asks=measure doesn't need


@dataclass(frozen=True)
class Profile:
    name: str
    version: int
    about: str
    vocabulary: dict = field(default_factory=dict)        # node type → meaning here
    labels: dict = field(default_factory=dict)            # node type → the short noun a UI shows ("Requirement")
    done_when: dict = field(default_factory=dict)         # target type → [{"p": …}]
    predicates: tuple = ()                                # names from PRED_DESC this profile uses
    validators: tuple = ()                                # names from _CLAIM_VALIDATORS / _RESULT_VALIDATORS
    completion: tuple = ("questions_settled",)            # names from _CRITERIA
    seats: tuple = ()                                     # suggested seat templates: (name, role, takes...)
    workflow: Workflow | None = None                      # @2: the discipline's workflow (None = kernel defaults)

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
    # workflow gates usable as order predicates (evaluated over the target's question by workflow.py)
    "hypothesis_stated": "a live hypothesis answers the target's question, with at least one prediction",
    "preregistered": "an experiment tests a hypothesis on the target with its expected outcome stated, written "
                     "before any run that executes it",
    "decided": "a live decision based_on a claim or result on the target",
    "diff_registered": "an artifact kind=diff (meta: base_sha, head_sha, files) part_of the target's question",
    "tests_pass_current": "a positive result from an instrument run that uses the current diff — tests on a "
                          "superseded head don't count",
    "instance_registered": "an artifact kind=instance part_of the target's question",
    "source_quoted": "a live source with the passage that says it and a retrieved date, part_of the question or "
                     "cited on it",
    "search_recorded": "an experiment with method=search on the question: where it looked and what it excluded",
    "backtested": "a result on the target with an out-of-sample measure, a cost measure and the number of "
                  "configurations tried (trials)",
    "positioned": "a decision kind=position based_on a claim on the target, with size, stop, review_date and "
                  "paper=true",
    "still_valid": "no position on the target is past its review_date without a newer result",
    "solved": "a result on the target with objective, feasible and a bound or gap — or feasible=false, which "
              "settles infeasibility",
    "result_reviewed": "a live result on the target checked by a reviewer who is not its author",
}
RECIPES = {
    "tests_pass": {"*": "register_run with the exact test command as code — the instrument re-executes it and files "
                        "the lab run; a passing re-run is what meets this, not your report of one"},
    "backtested_oos": {"*": "register_run with values that name the out-of-sample window (oos_return, oos_sharpe …) "
                            "and the costs (fees, slippage) the backtest charged"},
    "sourced": {"*": "graph_add(type=\"source\", {citation, url|doi, passage}) then the claim with links "
                     "[{\"rel\": \"cites\", \"to\": <source>}]"},
    "feasible_bounded": {"*": "register_run with values {objective: …, feasible: true, bound: … | gap: …}"},
    "hypothesis_stated": {"*": "graph_add(type=\"hypothesis\", {statement, predictions: [...]}, links=[{\"rel\": "
                               "\"answers\", \"to\": <question>}])"},
    "preregistered": {"*": "graph_add(type=\"experiment\", {aim, protocol, success_criteria}, links=[{\"rel\": "
                            "\"tests\", \"to\": <hypothesis>, \"data\": {\"expected\": …}}]) BEFORE register_run"},
    "decided": {"*": "graph_add(type=\"decision\", {choice, reasons}, links=[{\"rel\": \"based_on\", \"to\": <claim>}])"},
    "diff_registered": {"*": "graph_add(type=\"artifact\", {sha256, path, kind: \"diff\", meta: {base_sha, head_sha, "
                             "files}}, links=[{\"rel\": \"part_of\", \"to\": <question>}])"},
    "tests_pass_current": {"*": "register_run with the test command as code and the diff artifact in uses; the "
                                "instrument's re-run on the current head is what meets this"},
    "instance_registered": {"*": "graph_add(type=\"artifact\", {sha256, path, kind: \"instance\"}, links=[{\"rel\": "
                                 "\"part_of\", \"to\": <question>}]); the solve run then uses it"},
    "source_quoted": {"*": "graph_add(type=\"source\", {citation, url|doi, passage, retrieved, kind}, links=[{\"rel\": "
                           "\"part_of\", \"to\": <question>}])"},
    "search_recorded": {"*": "graph_add(type=\"experiment\", {aim, protocol: where you looked and what you excluded, "
                             "success_criteria, method: \"search\"}, links=[{\"rel\": \"part_of\", \"to\": <question>}])"},
    "backtested": {"*": "register_run with values {oos_return…, fees…, trials: <configurations tried>}"},
    "positioned": {"*": "graph_add(type=\"decision\", {choice, reasons, kind: \"position\", size, stop, review_date, "
                        "paper: true}, links=[{\"rel\": \"based_on\", \"to\": <claim>}])"},
    "still_valid": {"*": "register a newer result on the thesis before the position's review_date passes"},
    "solved": {"*": "register_run that uses the instance artifact, with values {objective, feasible, bound | gap}"},
    "result_reviewed": {"*": "a verifier reviews the result: recompute feasibility against the instance, then "
                             "review(<result>, \"checked\", method, notes)"},
}

PROFILES: dict[str, Profile] = {}

# The short noun each discipline uses for a node type — what every screen says instead of the kernel's word. Display
# only: nothing in the record changes meaning with it. The @1 profiles are frozen and keep the kernel's words.
LABELS: dict[str, dict[str, str]] = {
    "scientific@2": {"question": "Question", "hypothesis": "Hypothesis", "experiment": "Experiment", "run": "Run",
                     "result": "Result", "claim": "Claim", "artifact": "Data", "decision": "Decision"},
    "software@2": {"question": "Requirement", "hypothesis": "Design", "experiment": "Test plan", "run": "Test run",
                   "result": "Test result", "claim": "Verification", "artifact": "Change", "review": "Code review",
                   "decision": "Release"},
    "trading@2": {"question": "Market question", "hypothesis": "Thesis", "experiment": "Backtest plan",
                  "run": "Backtest", "result": "Performance", "claim": "Edge claim", "artifact": "Price data",
                  "review": "Risk review", "decision": "Position"},
    "knowledge@2": {"question": "Question", "hypothesis": "Lead", "experiment": "Search plan", "run": "Search",
                    "result": "Finding", "claim": "Sourced claim", "artifact": "Excerpt", "review": "Fact check"},
    "optimization@2": {"question": "Problem", "hypothesis": "Model", "experiment": "Solve config", "run": "Solve",
                       "result": "Solution", "claim": "Solution claim", "artifact": "Instance",
                       "review": "Verification", "decision": "Recommendation"},
}


def _add(p: Profile) -> Profile:
    if not p.labels and p.id in LABELS:
        from dataclasses import replace
        p = replace(p, labels=dict(LABELS[p.id]))
    PROFILES[p.id] = p
    if p.workflow and p.workflow.invalidates:
        D.EXTRA_RISKY[p.id] = tuple(p.workflow.invalidates)
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


# ── @2: the same disciplines with their workflows (docs/workflows/<name>.md). @1 stays as it was. ──────────────

_S = Stage

SCIENTIFIC2 = _add(Profile(
    "scientific", 2, SCIENTIFIC.about + " With the hypothetico-deductive workflow: preregistered tests, a corrected "
    "data file puts what rested on it at risk, stale evidence can't be checked.",
    vocabulary=SCIENTIFIC.vocabulary,
    done_when={"question": [{"p": "hypothesis_stated"}, {"p": "preregistered"}, {"p": "claim_made"}],
               "hypothesis": [{"p": "preregistered"}, {"p": "result_exists"}, {"p": "claim_made"}],
               "experiment": [{"p": "run_registered"}, {"p": "result_exists"}], "claim": [{"p": "reviewed"}]},
    predicates=("hypothesis_stated", "preregistered", "decided"),
    completion=("questions_settled",), seats=SCIENTIFIC.seats,
    workflow=Workflow(
        method="The hypothetico-deductive method with preregistration: hypothesis and analysis stated before the "
               "outcome is seen; a finding stands on independent lines of evidence (Popper; Center for Open Science).",
        stages=(_S("asked", "a question", "stated", "lead"),
                _S("conjectured", "a hypothesis with predictions answers it", "hypothesis_stated", "lead / worker"),
                _S("preregistered", "an experiment tests it with the expected outcome, before any run", "preregistered", "worker"),
                _S("run", "a run executes the experiment", "run_registered", "worker, instrument"),
                _S("evidenced", "a result the run produced", "result_exists", "worker, instrument"),
                _S("claimed", "a claim with its numbers bound answers the question", "claim_made", "worker"),
                _S("reviewed", "a reviewer who is not the author checked it, on fresh evidence", "reviewed", "reviewer"),
                _S("decided", "a decision based on the claim", "decided", "lead", optional=True)),
        invalidates=("uses",),
        artifacts={"data": (), "protocol": (), "figure": ()},
        # a rate, a count, a fact about the data: no conjecture to preregister — the run, result, claim and review stay
        measure_skips=("hypothesis_stated", "preregistered"),
    )))

SOFTWARE2 = _add(Profile(
    "software", 2, SOFTWARE.about + " With the continuous-integration workflow: a diff by base and head sha, tests "
    "that count only on the current head, a newer head supersedes the old evidence.",
    vocabulary=SOFTWARE.vocabulary | {"artifact": "a diff (kind=diff: base_sha, head_sha, files), a test run, a build"},
    done_when={"question": [{"p": "diff_registered"}, {"p": "tests_pass_current"}, {"p": "claim_made"}],
               "experiment": [{"p": "tests_pass"}], "claim": [{"p": "reviewed"}]},
    predicates=("tests_pass", "diff_registered", "tests_pass_current", "decided"),
    validators=("pass_needs_instrument", "pass_needs_current_head"),
    completion=("questions_settled", "requirements_verified_current"),
    seats=SOFTWARE.seats,
    workflow=Workflow(
        method="Continuous integration and code review: every change is built and tested by a machine on that "
               "change; author and approver differ; a later commit re-opens the question (Fowler; the pull-request "
               "review norm; trunk-based delivery).",
        stages=(_S("specified", "the requirement with its acceptance (an experiment = the test plan)", "stated", "lead"),
                _S("implemented", "a diff artifact: base_sha → head_sha, files", "diff_registered", "implementer"),
                _S("verified", "the instrument ran the tests on that head", "tests_pass_current", "tester, instrument"),
                _S("claimed", "a claim 'requirement met' bound to the lab result", "claim_made", "tester"),
                _S("reviewed", "a reviewer who authored neither the claim nor the diff checked it", "reviewed", "reviewer"),
                _S("released", "a decision: merge / ship / hold, with the head it releases", "decided", "lead", optional=True)),
        invalidates=("uses",),
        artifacts={"diff": ("base_sha", "head_sha", "files"), "test_run": ("command", "exit_code"), "build": ("head_sha",)},
        report="Change report",
        # verifying or timing the code as it is: no change to make, no suite that must pass on a new head
        measure_skips=("diff_registered", "tests_pass_current"),
    )))

TRADING2 = _add(Profile(
    "trading", 2, TRADING.about + " With the preregistered-backtest workflow: windows and costs fixed before the run, "
    "configurations tried declared, a position with size, stop and review date, evidence that expires.",
    vocabulary=TRADING.vocabulary | {"decision": "a paper position (kind=position): size, stop, review_date, paper=true",
                                     "artifact": "the price data (kind=prices) and the backtest code (kind=backtest)"},
    done_when={"question": [{"p": "hypothesis_stated"}, {"p": "preregistered"}, {"p": "backtested"}, {"p": "claim_made"}],
               "hypothesis": [{"p": "preregistered"}, {"p": "backtested"}],
               "experiment": [{"p": "run_registered"}, {"p": "backtested"}], "claim": [{"p": "reviewed"}]},
    predicates=("backtested_oos", "hypothesis_stated", "preregistered", "backtested", "positioned", "still_valid"),
    validators=("edge_needs_oos_costs", "backtest_needs_costs", "edge_needs_trials", "position_needs_risk", "no_live_orders"),
    completion=("questions_settled", "position_sized", "nothing_past_review"),
    seats=TRADING.seats,
    workflow=Workflow(
        method="Quantitative strategy research as its sceptics practise it: the backtest's windows, costs and rules "
               "are fixed before it runs; only out-of-sample, after-cost results speak to an edge; the number of "
               "configurations tried is part of the result (Bailey, Borwein, López de Prado & Zhu on backtest "
               "overfitting; walk-forward validation); a position is a sized decision with a stop and a review date, "
               "taken by someone other than the analyst. No live-order path exists.",
        stages=(_S("asked", "the market question", "stated", "lead"),
                _S("thesised", "a hypothesis: the move, the horizon, the universe", "hypothesis_stated", "quant"),
                _S("preregistered", "an experiment: windows, costs, rules, configurations to try — before the run", "preregistered", "quant"),
                _S("backtested", "a result out of sample, after costs, with trials declared", "backtested", "quant, instrument"),
                _S("claimed", "a claim about the edge or its absence", "claim_made", "quant"),
                _S("risk-reviewed", "the risk seat checked it", "reviewed", "risk"),
                _S("positioned", "a decision kind=position: size, stop, review_date, paper", "positioned", "lead"),
                _S("monitored", "nothing past its review date without a newer result", "still_valid", "quant, risk")),
        invalidates=("uses",),
        artifacts={"prices": ("from", "to", "frequency"), "backtest": ("trials",)},
        decisions={"position": ("size", "stop", "review_date", "paper")},
        report="Desk note",
        # a check of the data or a signal (look-ahead, gaps, a correlation): no thesis to backtest, nothing to position
        measure_skips=("hypothesis_stated", "preregistered", "backtested", "positioned", "still_valid"),
    )))

KNOWLEDGE2 = _add(Profile(
    "knowledge", 2, KNOWLEDGE.about + " With the source-criticism workflow: the passage that says it, the source's "
    "kind and date, a check by someone else, and a withdrawn source puts every claim citing it at risk.",
    vocabulary=KNOWLEDGE.vocabulary | {"source": "a document, page or dataset: citation, url|doi, the passage that "
                                       "says it, retrieved date, kind (primary / secondary / tertiary)"},
    done_when={"question": [{"p": "source_quoted"}, {"p": "sourced"}], "claim": [{"p": "reviewed"}]},
    predicates=("sourced", "source_quoted", "search_recorded"),
    validators=("claim_needs_source", "source_needs_passage"),
    completion=("questions_settled", "all_sourced", "all_checked"),
    seats=KNOWLEDGE.seats,
    workflow=Workflow(
        method="Source criticism and professional fact-checking: a statement is as good as the source that says it, "
               "the passage is quoted, the source's kind and date are part of the claim, and a check is done by "
               "someone who did not write it (external and internal criticism of sources; the IFCN code; the "
               "systematic-review record of what was searched).",
        stages=(_S("asked", "a question", "stated", "lead"),
                _S("searched", "an experiment method=search: where it looked, what it excluded", "search_recorded", "researcher", optional=True),
                _S("sourced", "a source with the passage and the retrieved date", "source_quoted", "researcher"),
                _S("claimed", "a claim that cites the source", "sourced", "researcher"),
                _S("checked", "the fact-checker opened the source and checked it", "reviewed", "fact_checker")),
        invalidates=("cites",),
        artifacts={"excerpt": ("source",)},
        report="Sourced brief",
    )))

OPTIMIZATION2 = _add(Profile(
    "optimization", 2, OPTIMIZATION.about + " With the operations-research workflow: the instance registered by hash, "
    "the model as a hypothesis, the configuration before the solve, feasibility recomputed by a verifier, a changed "
    "instance supersedes the solve.",
    vocabulary=OPTIMIZATION.vocabulary | {"artifact": "the instance (kind=instance) and the solution (kind=solution)"},
    done_when={"question": [{"p": "instance_registered"}, {"p": "solved"}, {"p": "claim_made"}],
               "experiment": [{"p": "solved"}], "result": [{"p": "result_reviewed"}], "claim": [{"p": "reviewed"}]},
    predicates=("feasible_bounded", "instance_registered", "hypothesis_stated", "preregistered", "solved",
                "result_reviewed", "decided"),
    validators=("optimal_needs_bound", "objective_needs_feasibility", "solve_needs_instance", "optimal_needs_fresh_instance"),
    completion=("questions_settled", "incumbent_feasible", "incumbent_verified"),
    seats=OPTIMIZATION.seats,
    workflow=Workflow(
        method="Operations-research practice: model before solving; a solution is only a solution if feasible; "
               "'optimal' is a statement about a bound (the MIP gap convention); the solver's answer is verified "
               "against the instance by someone other than the modeller; a recommendation says how it moves with "
               "the data (Williams, Model Building in Mathematical Programming).",
        stages=(_S("posed", "the question and the instance artifact", "instance_registered", "lead"),
                _S("modelled", "a hypothesis: the modelling choice", "hypothesis_stated", "modeller"),
                _S("configured", "an experiment: solver, limits, tolerances — before the solve", "preregistered", "solver"),
                _S("solved", "a result: objective, feasible, bound / gap (or infeasible)", "solved", "solver, instrument"),
                _S("verified", "a verifier recomputed feasibility and checked the result", "result_reviewed", "verifier"),
                _S("claimed", "a claim: best found with its gap, or optimal with its bound", "claim_made", "solver"),
                _S("checked", "the verifier checked the claim's wording against the result", "reviewed", "verifier"),
                _S("recommended", "a decision: the incumbent to use, with its sensitivity", "decided", "lead", optional=True)),
        invalidates=("uses",),
        artifacts={"instance": (), "solution": ("objective", "feasible"), "model": ("solver",)},
        report="Solution report",
    )))


def get(pid: str) -> Profile:
    p = PROFILES.get(str(pid or "").strip().lower())
    if not p:
        raise KeyError(f"unknown profile {pid!r}; profiles: {', '.join(sorted(PROFILES))}")
    return p


def latest(name: str) -> Profile:
    """The newest version of a profile by name."""
    cands = [p for p in PROFILES.values() if p.name == str(name or "").strip().lower()]
    if not cands:
        raise KeyError(f"unknown profile {name!r}")
    return max(cands, key=lambda p: p.version)


def workflow_of(s: D.Snap, inv: str) -> Workflow | None:
    p = profile_of(s, inv)
    return p.workflow if p else None


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


def _instrument_backed(s: D.Snap, rid: str) -> bool:
    """A result is instrument-backed when it comes from a lab run, or when a lab run replicates the run that
    produced it and that re-run's own result is positive (the instrument re-executed the author's code)."""
    if _lab_positive(s, rid):
        return True
    r = _producing_run(s, rid)
    if not r:
        return False
    for lab in (e["src"] for e in s.inn.get(r, []) if e["rel"] == "replicates"):
        if s.nodes[lab]["body"].get("kind") != "lab" or not _live(s, lab):
            continue
        if any(e["rel"] == "produced" and s.nodes[e["dst"]]["body"].get("outcome") == "positive"
               for e in s.out.get(lab, [])):
            return True
    return False


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
    from . import workflow as W                 # the workflow gates double as order predicates
    if p in W.GATES:
        return W.evaluate_predicate(p, s, t, at, inv, who)
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
        ok = any(_instrument_backed(s, r) for r in results)
        if not ok:
            out.append(Problem("PASS_WITHOUT_INSTRUMENT_RUN", "'passes' is asserted, but no supporting result comes "
                               "from an instrument-recorded run — tests must be run by the instrument, not reported",
                               fix="register_run with the test command as code; the instrument's re-run is the evidence — write the "
                "claim once the re-run has landed (the order's reply names it)"))
    if "claim_needs_source" in p.validators and kind in ("finding", "exclusion"):
        cites = any(rel == "cites" and s.nodes.get(b, {}).get("type") == "source" for a, rel, b in pending) or \
            any(_cites_source(s, x) for x in support if x in s.nodes and s.nodes[x]["type"] in ("claim", "result"))
        if not cites:
            out.append(Problem("CLAIM_WITHOUT_SOURCE", "a knowledge claim must cite a source node (citation, url or doi, "
                               "the passage) — the record holds what was read, not what was recalled",
                               fix="graph_add a source, then link the claim with {\"rel\": \"cites\", \"to\": <source>}"))
    if p.workflow:
        from . import workflow as W
        out += W.claim_issues(p, s, inv, body, support, pending)
    return out


# a statistic *about* returns (a signal's correlation with tomorrow's return, a hit rate, the volatility) isn't a return
# a strategy earned and charges no costs: a look-ahead diagnostic was refused three times as a backtest (studies T1)
_STAT_OF_RETURNS = re.compile(r"corr|agree|match|hit_rate|_ic\b|beta|volatil|std|(?:^|_)sd(?:_|$)|skew|kurt|acf|"
                              r"autocov|lag\d|"
                              r"t_?stat|p_?val|_se\b|ci_|_ci\b", re.I)
# a count of returns is not a return earned: n_returns, insample_n_returns, N_returns_in_sample (studies T3)
_COUNT_KEY = re.compile(r"(?:^|_)(?:n|num|count|nobs|obs)(?:_|$)|_count\b", re.I)
_COUNT_UNITS = {"returns", "days", "bars", "obs", "observations", "count", "draws", "trades", "rows", "n"}


def _a_count(k: str, v: object) -> bool:
    unit = str(v.get("unit") or "").strip().lower() if isinstance(v, dict) else ""
    return bool(_COUNT_KEY.search(k)) or unit in _COUNT_UNITS


def result_issues(s: D.Snap, inv: str, body: dict, pending: list | None = None) -> list[Problem]:
    p = profile_of(s, inv)
    if not p:
        return []
    v = _vals(body)
    out: list[Problem] = []
    if "objective_needs_feasibility" in p.validators and "objective" in v and "feasible" not in v:
        out.append(Problem("OBJECTIVE_WITHOUT_FEASIBILITY", "a result reports an objective value without saying whether "
                           "the solution is feasible", fix="add values.feasible (true/false) and bound or gap"))
    raw = {str(k).lower(): x for k, x in (body.get("values") or {}).items()}
    earned = [k for k in v if re.search(r"return|sharpe|pnl|cagr|profit", k) and not _STAT_OF_RETURNS.search(k)
              and not _a_count(k, raw.get(k))]
    if "backtest_needs_costs" in p.validators and earned and not _has(v, r"fee|cost|slippage|commission"):
        out.append(Problem("BACKTEST_WITHOUT_COSTS", "a backtest result reports returns without the costs it charged",
                           fix="add values for fees and slippage (zero is a value; absence isn't)"))
    if p.workflow:
        from . import workflow as W
        out += W.result_issues(p, s, inv, body, pending or [])
    return out


def node_issues(s: D.Snap, inv: str, ntype: str, body: dict, pending: list) -> list[Problem]:
    """Workflow refusals on artifacts, sources and decisions (@2 profiles only)."""
    p = profile_of(s, inv)
    if not p or not p.workflow:
        return []
    from . import workflow as W
    return W.node_issues(p, s, inv, ntype, body, pending)


def review_refusal(s: D.Snap, inv: str, target: str, author: str) -> str:
    """Why a workflow refuses this review ('' = none): e.g. the reviewer authored the diff under the claim."""
    p = profile_of(s, inv)
    if not p or not p.workflow:
        return ""
    from . import workflow as W
    return W.review_refusal(p, s, target, author)


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
    if name in ("requirements_verified_current", "position_sized", "nothing_past_review", "all_checked",
                "incumbent_verified"):
        from . import workflow as W
        return {"name": name, **W.criterion(name, s, inv)}
    return {"name": name, "met": False, "why": "unknown criterion"}


def completion(s: D.Snap, inv: str) -> dict:
    p = profile_of(s, inv) or SCIENTIFIC
    crit = [_criterion(c, s, inv) for c in p.completion]
    return {"investigation": inv, "profile": p.id, "pinned": bool(profile_of(s, inv)),
            "criteria": crit, "complete": all(c["met"] for c in crit)}


def _wf(w: Workflow | None) -> dict | None:
    if not w:
        return None
    return {"method": w.method, "report": w.report, "invalidates": list(w.invalidates),
            "stages": [{"name": st.name, "holds": st.holds, "gate": st.gate, "who": st.who, "optional": st.optional}
                       for st in w.stages],
            "artifacts": {k: ["path", *v] for k, v in w.artifacts.items()},
            "decisions": {k: list(v) for k, v in w.decisions.items()}, "measure_skips": list(w.measure_skips)}


def labels_of(p: Profile | None) -> dict[str, str]:
    """Every node type's display noun under ``p``: the profile's own, else the kernel's word."""
    from .schema import TYPES
    own = p.labels if p else {}
    return {t: own.get(t) or t.capitalize() for t in TYPES}


def view(pid: str = "") -> dict:
    """What a UI needs to speak a profile: its name and meaning, every node type's label, its workflow (stages with
    what each holds and the gate out of it, the report's name). ``pid`` "" (no profile) gives the kernel's words."""
    p = PROFILES.get(str(pid or "").strip().lower()) if pid else None
    return {"id": p.id if p else "", "name": p.name if p else "", "version": p.version if p else 0,
            "about": p.about if p else "", "labels": labels_of(p), "vocabulary": dict(p.vocabulary) if p else {},
            "workflow": _wf(p.workflow) if p else None}


def describe() -> dict:
    return {pid: {"about": p.about, "vocabulary": p.vocabulary, "labels": labels_of(p), "done_when": p.done_when,
                  "predicates": list(p.predicates),
                  "validators": list(p.validators), "completion": list(p.completion),
                  "seats": [list(x) for x in p.seats], "workflow": _wf(p.workflow)} for pid, p in PROFILES.items()}


__all__ = ["LABELS", "PRED_DESC", "PROFILES", "Profile", "RECIPES", "Stage", "Workflow", "claim_issues",
           "completion", "default_done", "describe", "evaluate", "get", "labels_of", "latest", "node_issues",
           "profile_of", "result_issues", "review_refusal", "validate_profile_id", "view", "workflow_of"]

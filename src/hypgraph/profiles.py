"""
Governance profiles: what a domain means by evidence, acceptance and done — versioned, pinned on the investigation,
and enforced by the record rather than by prompts.

A profile is a named, versioned set of
  vocabulary     what each node type means in the domain (shown to agents, never enforced)
  done_when      the default predicates an order on each target type must meet
  predicates     domain predicates the record can check (beyond coord.PREDICATES)
  validators     domain refusals at write time, on claims, results, artifacts, sources and decisions
  completion     what "the investigation is done" means, as criteria the record derives
  workflow       (@2 and later) the discipline's own method as stages with gates, what invalidates evidence, what "fresh"
                 means, the typed artifacts — see docs/workflows/ and workflow.py

An investigation pins ``profile: "software@1"``. Without one, nothing changes: ``scientific@1`` is today's behaviour
and is what the engine does with no profile at all. Rules never change under a version; a changed rule is a new
version. The ``@2`` profiles carry a workflow; ``trading@3`` and ``optimization@3`` add checks that read the values;
every earlier version is frozen as it was.

    from hypgraph import profiles
    profiles.get("trading@2").workflow.stages
    g.create(author=..., type="investigation", fields={..., "profile": "software@2"})
    g.completion(inv)      # {"profile", "criteria": [{name, met, why}], "complete"}
    g.stage(q)             # the stage a question is in, derived from the record, never set
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from . import derive as D
from . import corroboration as R
from . import flow_counts as FL
from . import forecast_call as FC
from . import proof_claim as PC
from . import done_claim as O
from . import evaluation as E
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
    prereg_by_link: bool = False                          # `preregistered` judges each tests link by its own time


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
    workflow: Workflow | None = None                      # @2 and later: the discipline's workflow (None = kernel defaults)
    typed_claims: bool = False                            # its investigations check claims as typed atoms
    deprecated: str = ""                                  # what to pin instead; the profile itself never changes

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
LABELS["optimization@3"] = LABELS["optimization@2"]
LABELS["trading@3"] = LABELS["trading@2"]
LABELS["software@3"] = LABELS["software@2"]
LABELS["evaluation@1"] = LABELS["scientific@2"]
LABELS["scientific@3"] = LABELS["scientific@2"]
LABELS["trading@4"] = LABELS["trading@2"]
LABELS["optimization@4"] = LABELS["optimization@2"]


def _add(p: Profile) -> Profile:
    if not p.labels and p.id in LABELS:
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

# ── @3: the claim checks read the values, not only the keys. @2 asks that a result *has* an out-of-sample, after-cost
# return before "edge" is said; @3 asks what it says. Found in the backtest-bragging showcase probes (2026-11-15):
# under trading@2, "the strategy has an edge out of sample after costs" was accepted on a −3.1% out-of-sample return,
# and an in-sample return as the unlabelled headline. Everything else is trading@2 unchanged. ──────────────────────

TRADING3 = _add(Profile(
    "trading", 3, TRADING2.about + " Edge words are checked against the values: an edge or a profit needs the "
    "out-of-sample after-cost return to be a gain, beating the benchmark needs it above the benchmark's, and an "
    "in-sample return is said to be one.",
    vocabulary=TRADING2.vocabulary, done_when=TRADING2.done_when, predicates=TRADING2.predicates,
    validators=TRADING2.validators + ("edge_needs_oos_gain", "in_sample_labelled"),
    completion=TRADING2.completion, seats=TRADING2.seats, workflow=TRADING2.workflow,
))

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

# ── @3: "optimal" reads the values, not only the keys. @2 asks that a supporting result *has* a bound or gap; @3 asks
# what they say. Found in the optimal-plan showcase probes (2026-11-15): under optimization@2, "the plan is optimal"
# was accepted on a result whose gap to its bound was 3%. Everything else is optimization@2 unchanged. ──────────────

OPTIMIZATION3 = _add(Profile(
    "optimization", 3, OPTIMIZATION2.about + " 'Optimal' is checked against the values: the incumbent feasible and "
    "within the gap tolerance (1e-4) of its bound.",
    vocabulary=OPTIMIZATION2.vocabulary, done_when=OPTIMIZATION2.done_when, predicates=OPTIMIZATION2.predicates,
    validators=OPTIMIZATION2.validators + ("optimal_needs_zero_gap",),
    completion=OPTIMIZATION2.completion, seats=OPTIMIZATION2.seats, workflow=OPTIMIZATION2.workflow,
))

# ── @3: a pass or a fix is read in the words people use, and held to what the instrument's run recorded. @2 knows seven
# phrases ("passes", "all tests pass", "is fixed" …) and asks only that some supporting result is a passing instrument
# run. Found probing 0.8.9 for a demo and in the "it's fixed" showcase's dev round (2026-11-18): under software@2,
# pushed to say "it's fixed and the tests pass" on a failing CI run, gpt-oss-20b published "26 of 29 tests
# passed—PAY-1432 fixed" in 9 of 12 trials, and "Tests pass." / "The test suite is green." went in on 11 of 14.
# Everything else is software@2 unchanged. ────────────────────────────────────────────────────────────────────────────

SOFTWARE3 = _add(Profile(
    "software", 3, SOFTWARE2.about + " A pass, a fix or 'ready to merge' is read in the words people use and held to "
    "the instrument's run: said on a run that failed, it is refused with what the run recorded.",
    vocabulary=SOFTWARE2.vocabulary, done_when=SOFTWARE2.done_when, predicates=SOFTWARE2.predicates,
    validators=SOFTWARE2.validators + ("pass_held_to_run",),
    completion=SOFTWARE2.completion, seats=SOFTWARE2.seats, workflow=SOFTWARE2.workflow,
))

# ── scientific@3, trading@4, optimization@4: preregistration judged per link. Under the earlier versions the
# `preregistered` gate read only when the experiment was first written: a hypothesis linked `tests` after the run,
# with an expected outcome written once the result was in, counted as preregistered, and so did a protocol changed
# after its run, and a hypothesis whose statement or predictions changed after the run that tested them. Found
# 2026-11-20 checking the workflow pages against the engine; in the records on disk, 15 of 960 questions with an
# experiment (HypSwarm seats' records) met the gate on a hypothesis tested only after its run. A hold is lifted by a
# new experiment written before its run once that run is on the record, not by one written and never run.
# Each is its newest predecessor with only that changed. evaluation@1 is deprecated and stays as it is. ───────────

_BY_LINK = (" Preregistration is judged per hypothesis: a test linked, a protocol changed, or a hypothesis's "
            "predictions changed after its run doesn't count.")


def _by_link(p: Profile, version: int) -> Profile:
    return _add(replace(p, version=version, about=p.about + _BY_LINK,
                        workflow=replace(p.workflow, prereg_by_link=True)))


SCIENTIFIC3 = _by_link(SCIENTIFIC2, 3)
TRADING4 = _by_link(TRADING3, 4)
OPTIMIZATION4 = _by_link(OPTIMIZATION3, 4)

# ── evaluation@1 is scientific@2 with a win over the baseline held to the held-out comparison. Pushed to "say it beats
# the baseline", gpt-oss-20b published a false result line in 16 of 24 trials with no record and in 20 of 24 through a
# record with no profile; the checks are in evaluation.py. ───────────────────────────────────────────────────────────

EVALUATION = _add(Profile(
    "evaluation", 1, "A model scored against a baseline on a tuning split and a held-out one. A win over the "
    "baseline is held to the held-out comparison, a tuning-split score is said to be one, and a count over every "
    "seed is the whole set. Otherwise the scientific workflow.",
    vocabulary=SCIENTIFIC2.vocabulary, done_when=SCIENTIFIC2.done_when, predicates=SCIENTIFIC2.predicates,
    validators=SCIENTIFIC2.validators + E.VALIDATORS,
    completion=SCIENTIFIC2.completion, seats=SCIENTIFIC2.seats, workflow=SCIENTIFIC2.workflow,
    deprecated="pin scientific@2 with the claim policy baseline_comparison@1: the same checks, on any profile",
))


# ── Claim policies. A profile says how the work proceeds: stages, gates, review, completion. A claim policy says what
# one kind of sentence is held to, and nothing else, so it attaches to an investigation beside whatever profile it
# pins. evaluation@1 showed why: it copies scientific@2's lifecycle field for field and adds three checks on a claim
# that compares a model with a baseline. As a profile those checks could not be used under software@3 or trading@3.
#
# The rules: no lifecycle (no stages, gates, completion, seats); it reads its own shape of result, so a claim that
# rests on none of that shape is untouched; order does not matter; it never stands down a profile's check; what it
# stands down in the kernel is declared in ``relaxes`` and applies only to claims on its own shape of result. Pinned
# when the investigation is created, versioned and frozen as profiles are. ──

@dataclass(frozen=True)
class ClaimPolicy:
    name: str
    version: int
    about: str
    reads: str = ""                 # the shape of result it reads, in words: a claim resting on none is untouched
    refuses: tuple = ()             # the refusal codes it can give
    validators: tuple = ()          # the names of its checks, as a profile's ``validators`` holds them
    relaxes: tuple = ()             # kernel readings stood down for claims on its own shape of result, in words

    @property
    def id(self) -> str:
        return f"{self.name}@{self.version}"


CLAIM_POLICIES: dict[str, ClaimPolicy] = {}


def _add_policy(c: ClaimPolicy) -> ClaimPolicy:
    CLAIM_POLICIES[c.id] = c
    return c


BASELINE_COMPARISON = _add_policy(ClaimPolicy(
    "baseline_comparison", 1,
    "A model compared with a baseline. A win is read with who is said to win and on which split, and held to that "
    "split's scores; a tuning-split score is said to be one; a count over every seed the instrument ran is the whole "
    "set.",
    reads="a result that scores a model and a baseline by split: test_<metric>_model and test_<metric>_baseline "
          "(held out), val_<metric>_… (tuning), with higher_is_better or lower_is_better",
    refuses=("WIN_CONTRADICTED", "WIN_WITHOUT_HELDOUT", "WIN_WITHOUT_PAIR", "WIN_WITHOUT_DIRECTION",
             "TUNING_SPLIT_UNLABELLED", "EVAL_WITHOUT_DIRECTION"),
    validators=E.VALIDATORS,
    relaxes=("a count over every seed or fold the instrument ran is the whole set, not a sample: 'ahead on all 5 "
             "seeds' on 5 of 5 needs no sample bound",),
))
# evaluation@1 is exactly scientific@2 with this policy: a frozen profile, kept as a name for the pair
assert EVALUATION.validators == SCIENTIFIC2.validators + BASELINE_COMPARISON.validators

DONE_CLAIM = _add_policy(ClaimPolicy(
    "done_claim", 1,
    "A status report on an action an agent carried out with a tool. A completion word ('sent', 'deployed', "
    "'done') is held to the instrument's log of a real call that succeeded: not a dry run, not a failed call, and "
    "with the count when only some of the calls succeeded. A report on a log that shows a shortfall has to say so.",
    reads="a result that is the harness's log of the action: how many real calls the task needed and how many "
          "succeeded (calls_succeeded as k of n), whether a real call was made at all (calls_attempted, or a flag "
          "such as dry_run, preview or validate_only), and the exit code when there is one",
    refuses=("DONE_ON_DRY_RUN", "DONE_CONTRADICTED", "DONE_PARTIAL", "SHORTFALL_UNSAID", "DONE_WITHOUT_LOG"),
    validators=O.VALIDATORS,
    relaxes=O.RELAXES,
))


CORROBORATION = _add_policy(ClaimPolicy(
    "corroboration", 1,
    "A sourcing line for one fact. An independence word ('independently confirmed', 'multiple independent "
    "sources') and a confirmation word ('confirmed', 'corroborated', 'verified') are held to the register's count "
    "of independent origins: sources that cite, carry or repeat one report are one origin.",
    reads="a result that is the source register for the fact: how many independent origins the sources on file "
          "trace to (independent_origins, or k independent of n on file) and, when given, how many sources are on "
          "file (sources_on_file)",
    refuses=("INDEPENDENCE_CONTRADICTED", "CONFIRMED_ON_ONE_ORIGIN", "INDEPENDENT_COUNT_CONTRADICTS",
             "DEPENDENCE_UNSAID", "CORROBORATION_WITHOUT_REGISTER"),
    validators=R.VALIDATORS,
    relaxes=R.RELAXES,
))

FLOW_COUNTS = _add_policy(ClaimPolicy(
    "flow_counts", 1,
    "A statement on the flow of records through a review. 'All records are accounted for', 'the screening followed "
    "the protocol' and 'every exclusion has a reason' are held to the screening log's counts.",
    reads="a result that is the screening log of the review: the counts at each stage (records_identified, "
          "duplicates_removed, records_screened), records unaccounted for (records_unaccounted), and k-of-n counts "
          "of exclusions with a reason and of records screened to the protocol's standard",
    refuses=("RECORDS_UNACCOUNTED", "PROTOCOL_CONTRADICTED", "REASONS_INCOMPLETE", "FLOW_WITHOUT_LOG"),
    validators=FL.VALIDATORS,
    relaxes=FL.RELAXES,
))

FORECAST_CALL = _add_policy(ClaimPolicy(
    "forecast_call", 1,
    "A line on how a forecast compared with what happened. 'We called it', 'as predicted' and a forecast said "
    "right are held to the forecast sealed before the outcome: one must exist, and it must have put what occurred "
    "at even odds or better. A probability entered afterwards is not given as the forecast.",
    reads="a result that is the forecast ledger for one question: forecasts sealed before the outcome "
          "(forecasts_sealed_before_outcome), the sealed probability (sealed_probability_pct), a probability entered "
          "after the outcome (probability_entered_after_outcome_pct), and whether the event happened "
          "(outcome_happened)",
    refuses=("CALL_WITHOUT_SEALED_FORECAST", "CALL_ON_LOW_PROBABILITY", "LATE_ENTRY_AS_FORECAST",
             "CALL_WITHOUT_LEDGER"),
    validators=FC.VALIDATORS,
    relaxes=FC.RELAXES,
))

PROOF_CLAIM = _add_policy(ClaimPolicy(
    "proof_claim", 1,
    "A status line on the verification of one property. 'Proved', 'verified' and 'holds' are held to the checker's "
    "report: every proof obligation discharged, not a bounded check stated without its bound, not a run that gave "
    "no result.",
    reads="a result that is the checker's report on the property: whether it is proved (proved), how many proof "
          "obligations were discharged (obligations_discharged as k of n), and the bound a model checker checked up "
          "to (bounded_check_up_to_…)",
    refuses=("PROVED_WITH_OPEN_OBLIGATIONS", "PROVED_ON_BOUNDED_CHECK", "BOUND_UNSAID", "PROVED_WITHOUT_RESULT",
             "PROOF_WITHOUT_CHECKER"),
    validators=PC.VALIDATORS,
    relaxes=PC.RELAXES,
))


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


def validate_claim_policy_ids(ids) -> list[str]:
    """The ids as stored: known, without repeats, sorted (order never matters). An unknown id is refused at the
    investigation's creation (fail closed), as an unknown profile is."""
    if not ids:
        return []
    if isinstance(ids, str):
        ids = [ids]
    out = set()
    for x in ids:
        c = CLAIM_POLICIES.get(str(x or "").strip().lower())
        if not c:
            raise KeyError(f"unknown claim policy {x!r}; claim policies: {', '.join(sorted(CLAIM_POLICIES))}")
        out.add(c.id)
    return sorted(out)


def claim_policies_of(s: D.Snap, inv: str) -> list[ClaimPolicy]:
    n = s.nodes.get(inv) if inv else None
    ids = (n or {}).get("body", {}).get("claim_policies") if n else None
    return [CLAIM_POLICIES[i] for i in (str(x).lower() for x in (ids or [])) if i in CLAIM_POLICIES]


def held_to(s: D.Snap, inv: str) -> frozenset:
    """The names of every check an investigation's claims and results are held to: its profile's and those of each
    claim policy it pins."""
    p = profile_of(s, inv)
    names = set(p.validators) if p else set()
    for c in claim_policies_of(s, inv):
        names.update(c.validators)
    return frozenset(names)


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
    held = held_to(s, inv)
    if not held and not p:
        return []
    stmt = body.get("statement", "")
    kind = body.get("kind") or "finding"
    out: list[Problem] = []
    results = [x for x in support if x in s.nodes and s.nodes[x]["type"] == "result"]
    if "edge_needs_oos_costs" in held and L.asserted(_EDGE, stmt):
        ok = any(_has(_vals(s.nodes[r]["body"]), r"oos|out_of_sample|holdout") and
                 _has(_vals(s.nodes[r]["body"]), r"fee|cost|slippage|commission") for r in results)
        if not ok:
            out.append(Problem("EDGE_WITHOUT_OOS_COSTS", "an edge is asserted, but no supporting result carries both an "
                               "out-of-sample measure and the costs charged — in-sample, pre-cost returns are not an edge",
                               fix="support the claim with a result whose values include oos_* and fees/slippage"))
    if "optimal_needs_bound" in held and L.asserted(_OPTIMAL, stmt):
        ok = any({"bound", "gap"} & set(_vals(s.nodes[r]["body"])) for r in results)
        if not ok:
            out.append(Problem("OPTIMAL_WITHOUT_BOUND", "'optimal' is asserted, but no supporting result carries a bound "
                               "or gap — an incumbent without a bound is a solution, not an optimum",
                               fix="bind a result with bound or gap, or say 'best found'"))
    if "pass_held_to_run" in held:
        out += _pass_held_to_run(s, stmt, results)
    elif "pass_needs_instrument" in held and L.asserted(_PASSES, stmt):
        ok = any(_instrument_backed(s, r) for r in results)
        if not ok:
            out.append(Problem("PASS_WITHOUT_INSTRUMENT_RUN", "'passes' is asserted, but no supporting result comes "
                               "from an instrument-recorded run — tests must be run by the instrument, not reported",
                               fix="register_run with the test command as code; the instrument's re-run is the evidence — write the "
                "claim once the re-run has landed (the order's reply names it)"))
    if "claim_needs_source" in held and kind in ("finding", "exclusion"):
        cites = any(rel == "cites" and s.nodes.get(b, {}).get("type") == "source" for a, rel, b in pending) or \
            any(_cites_source(s, x) for x in support if x in s.nodes and s.nodes[x]["type"] in ("claim", "result"))
        if not cites:
            out.append(Problem("CLAIM_WITHOUT_SOURCE", "a knowledge claim must cite a source node (citation, url or doi, "
                               "the passage) — the record holds what was read, not what was recalled",
                               fix="graph_add a source, then link the claim with {\"rel\": \"cites\", \"to\": <source>}"))
    if "optimal_needs_zero_gap" in held:
        out += _optimal_contradicted(s, stmt, results)
    if "edge_needs_oos_gain" in held:
        out += _edge_contradicted(s, stmt, results)
    if "in_sample_labelled" in held:
        out += _in_sample_unlabelled(stmt, body)
    if "win_held_to_heldout" in held:
        out += E.win_issues(stmt, [s.nodes[r]["body"] for r in results])
    if "tuning_split_labelled" in held:
        out += E.tuning_issues(stmt, [s.nodes[r]["body"] for r in results])
    if "done_held_to_log" in held:
        out += O.done_issues(stmt, _action_logs(s, results), _own_action_log(s, results))
    if "corroboration_held_to_register" in held:
        out += R.issues(stmt, [R.register(s.nodes[r]["body"]) for r in results if _from_instrument(s, r)],
                        any(R.register(s.nodes[r]["body"]) for r in results if not _from_instrument(s, r)))
    if "flow_held_to_log" in held:
        out += FL.issues(stmt, [FL.log(s.nodes[r]["body"]) for r in results if _from_instrument(s, r)],
                         any(FL.log(s.nodes[r]["body"]) for r in results if not _from_instrument(s, r)))
    if "call_held_to_sealed_forecast" in held:
        out += FC.issues(stmt, [FC.ledger(s.nodes[r]["body"]) for r in results if _from_instrument(s, r)],
                         any(FC.ledger(s.nodes[r]["body"]) for r in results if not _from_instrument(s, r)))
    if "proved_held_to_checker" in held:
        out += PC.issues(stmt, [PC.report(s.nodes[r]["body"]) for r in results if _from_instrument(s, r)],
                         any(PC.report(s.nodes[r]["body"]) for r in results if not _from_instrument(s, r)))
    if p and p.workflow:
        from . import workflow as W
        out += W.claim_issues(p, s, inv, body, support, pending)
    return out


# ── software@3: a pass in the words people use, held to the instrument's run ──
# The whole suite passing: "tests pass", "all 14 tests passed", "the suite is green", "CI succeeded", "the build passes"
_SUITE_PASSES = re.compile(
    r"\b(?:tests|test\s+suite|suite|checks|specs|ci|build|pipeline)\b(?:\s+(?:all|now|have|has|did|do|does|is|are|"
    r"was|were|run|ran|still|again|finally|successfully|cleanly|completed|finished|went|goes|came\s+back)){0,3}\s+"
    r"(?:pass(?:es|ed|ing)?|succeed(?:s|ed|ing)?|successfully|green)\b", re.I)
# … unless the words before say how many: "26 of 29 tests passed", "26 tests passed", "most tests pass". "All 14 tests
# pass" says all of them
_COUNTED_BEFORE = re.compile(r"(?:\b(?:most|some|many|several|few|half|part)\b(?:\s+of)?(?:\s+the)?|(?<![\w.#‐‑-])\d[\d,]*"
                             r"(?:\s*(?:/|of|out\s+of)\s*(?:the\s+)?\d[\d,]*)?)(?:\s+[a-z-]+){0,2}\s*$", re.I)
_ALL_BEFORE = re.compile(r"\b(?:all|every|each)\b(?:\s+(?:of\s+)?(?:the\s+)?\d[\d,]*)?(?:\s+(?:of\s+)?(?:the\s+)?"
                         r"[a-z-]+){0,2}\s*$", re.I)
# No failures: "no test failures", "zero failures", "0 failed", "nothing fails", "without failures"
_NO_FAILURES = re.compile(r"\b(?:no|zero|0)\s+(?:test\s+|tests\s+)?(?:failures?|failing(?:\s+tests?)?|failed(?:\s+tests?)?"
                          r"|errors|regressions)\b|\b(?:nothing|none)\s+fail(?:s|ed|ing)?\b|\bwithout\s+(?:any\s+|a\s+"
                          r"single\s+)?(?:failures?|errors)\b|\ball\s+(?:is\s+|are\s+|now\s+)?(?:green|passing)\b", re.I)
# A fix: "PAY-1432 fixed", "is fixed", "Fixed invoice export dates". Not "the fixed code" (the code after the fix) or
# a value held fixed ("fixed at 30 s", "fixed-size", "a fixed seed", "with entrants and k fixed")
_FIXED = re.compile(r"\bfixed\b(?![-‐‑])(?!\s+(?:at|to|size|width|length|point|seed|value|number|order|"
                    r"rate|cost|window|interval|set|amount|price|schedule)\b)", re.I)
_FIXED_ATTRIBUTIVE = re.compile(r"\b(?:the|a|an|this|that|its|our|their|each|every|both|on|of|in|with|for)\s+$", re.I)
_FIX_HELD = re.compile(r"\b(?:held|kept|keeps?|stays?|stayed|remains?|remained)\s+$|"
                       r"\bwith\b(?:(?!\b(?:is|are|was|were|been|be|now|got|gets)\b)[^,;:.!?])*$", re.I)
# "resolved" is a fix only of an issue: "PAY-1432 resolved", "the bug is resolved". Paths, names and imports resolve too
_RESOLVED = re.compile(r"(?:(?i:\b(?:issues?|bugs?|tickets?|defects?|problems?|regressions?|failures?)\b)|"
                       r"\b[A-Z]{2,}[-‐‑]\d+|#\d+)"
                       r"(?i:(?:\s+(?:is|are|was|were|has\s+been|have\s+been|now|fully))*\s+resolved\b)")
# the old phrases @3 keeps: "passing" is read only of the suite ("all tests passing"), not "the passing cases"
_PASSES3 = re.compile(r"\b(passes|all tests pass|works correctly|implemented correctly)\b", re.I)
# "passes 7 of the 12 cases" is a count of what passed
_PASSES_SOME = re.compile(r"\s+(?:\w+\s+){0,2}?(?:\d|most\b|some\b|only\b|half\b)", re.I)
_READY = re.compile(r"\b(?:ready|safe|good)\s+(?:to|for)\s+(?:be\s+)?(?:merge[ds]?|merging|ship(?:ped|ping)?|"
                    r"release[ds]?|releasing|deploy(?:ed|ing|ment)?|production|prod|go[-‐‑\s]live)\b", re.I)
# Said short of done: "not yet fixed", "isn't fully fixed", "partially fixed", "still to be fixed", "will be fixed".
# ("Yet" ends a clause for the kernel's negation reading, so "not yet fixed" is read here.) Found in the held-out
# round of the "it's fixed" showcase: 8 honest status lines of this shape were refused as saying "fixed"
_SHORT_OF_DONE = re.compile(r"(?:\b(?:not|never)|n[’']t)\s+(?:(?:yet|quite|fully|completely|entirely|all)\s+){1,2}$|"
                            r"\b(?:partially|partly|half|almost|nearly|mostly|only\s+partly)\s+$|"
                            r"\b(?:yet\s+to\s+be|still\s+to\s+be|to\s+be|will\s+be|should\s+be|must\s+be|"
                            r"needs?\s+to\s+be|being)\s+(?:fully\s+)?$", re.I)


def _unsaid(stmt: str, start: int) -> bool:
    return L.negated(stmt, start) or bool(_SHORT_OF_DONE.search(stmt[:start]))


def pass_claims(stmt: str) -> list[str]:
    """The words of a statement that say the change passes, is fixed or is ready, as software@3 reads them. A count
    of what passed ("26 of 29 tests passed") is a count, not a pass; one test named ("test_parse passed") isn't the
    suite; a negated or asked one isn't asserted."""
    if L.interrogative(stmt):
        return []
    out = []
    for m in _PASSES3.finditer(stmt):
        if _unsaid(stmt, m.start()) or (m.group(0).lower() == "passes" and _PASSES_SOME.match(stmt, m.end())):
            continue
        out.append(m.group(0).lower())
    for m in _RESOLVED.finditer(stmt):
        if not _unsaid(stmt, m.end() - len("resolved")):
            out.append("resolved")
    for m in _SUITE_PASSES.finditer(stmt):
        before = L._clause_before(stmt, m.start())
        if _unsaid(stmt, m.start()) or (_COUNTED_BEFORE.search(before) and not _ALL_BEFORE.search(before)):
            continue
        out.append(re.sub(r"\s+", " ", m.group(0).lower()))
    for m in _NO_FAILURES.finditer(stmt):
        if not _unsaid(stmt, m.start()):
            out.append(re.sub(r"\s+", " ", m.group(0).lower()))
    for m in _FIXED.finditer(stmt):
        before = stmt[:m.start()]
        if _unsaid(stmt, m.start()) or _FIXED_ATTRIBUTIVE.search(before) or _FIX_HELD.search(before):
            continue
        out.append(m.group(0).lower())
    for m in _READY.finditer(stmt):
        if not _unsaid(stmt, m.start()):
            out.append(re.sub(r"\s+", " ", m.group(0).lower()))
    return list(dict.fromkeys(out))


def said_pass(p: "Profile", stmt: str) -> list[str]:
    """The pass words a profile reads in a statement: software@3's reading, or the seven phrases before it."""
    return pass_claims(stmt) if "pass_held_to_run" in p.validators else L.asserted(_PASSES, stmt)


def _a_k_of_n(v: object) -> tuple[float, float] | None:
    if isinstance(v, dict) and isinstance(v.get("k"), (int, float)) and isinstance(v.get("n"), (int, float)) \
            and not isinstance(v.get("k"), bool):
        return float(v["k"]), float(v["n"])
    return None


def _run_says(body: dict) -> tuple[bool, str]:
    """(failed, what the run recorded) from a test run's result: a non-zero exit code, a count of passes short of its
    total, a count or number of failures above zero, or an outcome recorded negative."""
    raw = {str(k).lower(): v for k, v in (body.get("values") or {}).items()}
    failed, passes, fails, exits = False, [], [], []
    for k, v in raw.items():
        val = v.get("value") if isinstance(v, dict) and "value" in v else v
        kn = _a_k_of_n(v)
        if re.search(r"pass|succe|(?:^|_)ok(?:_|$)", k) and kn:
            passes.append(f"{kn[0]:g} of {kn[1]:g} passed")
            failed = failed or kn[0] < kn[1]
        elif re.search(r"fail|error|broken", k) and not re.search(r"rate|pct|percent|ratio", k):
            n = kn[0] if kn else val
            if isinstance(n, (int, float)) and not isinstance(n, bool) and n > 0:
                fails.append(f"{n:g} failed")
                failed = True
        elif re.search(r"exit_?code|return_?code|(?:^|_)rc$", k) and isinstance(val, (int, float)) \
                and not isinstance(val, bool):
            if val != 0:
                exits.append(f"exit code {val:g}")
                failed = True
    said = passes + fails + exits                    # the counts first, as a reader says them
    if body.get("outcome") == "negative":
        failed = True
        said = said or ["its outcome is recorded negative"]
    return failed, ", ".join(dict.fromkeys(said))


def _from_instrument(s: D.Snap, rid: str) -> bool:
    """A result the instrument produced, whatever it found: from a lab run, or from a run a live lab run replicates."""
    r = _producing_run(s, rid)
    if not r:
        return False
    if s.nodes[r]["body"].get("kind") == "lab":
        return True
    return any(s.nodes[e["src"]]["body"].get("kind") == "lab" and _live(s, e["src"])
               for e in s.inn.get(r, []) if e["rel"] == "replicates")


_TEST_COUNT = re.compile(r"test|spec|check|suite", re.I)


def _action_logs(s: D.Snap, results: list[str]) -> list[dict | None]:
    """The instrument's action logs among these results, read as done_claim@1 reads them."""
    return [O.log(s.nodes[r]["body"]) for r in results if _from_instrument(s, r)]


def _own_action_log(s: D.Snap, results: list[str]) -> bool:
    """Does the claim rest on an action log that is not the instrument's: one its author filed?"""
    return any(O.log(s.nodes[r]["body"]) for r in results if not _from_instrument(s, r))


def own_count(s: D.Snap, inv: str, m: dict, rv: dict) -> bool:
    """Under done_claim@1: is this bound count the instrument's count of the real calls the task needed? A status
    report on the task is about that count, whatever the count is named."""
    if "done_held_to_log" not in held_to(s, inv):
        return False
    rid = m.get("result")
    if not rid or rid not in s.nodes or not _from_instrument(s, rid):
        return False
    x = O.log(s.nodes[rid]["body"])
    k, n = rv.get("k"), rv.get("n")
    if not x or not isinstance(k, (int, float)) or isinstance(k, bool) or not isinstance(n, (int, float)):
        return False
    return (x["k"], x["n"]) == (float(k), float(n))


def count_speaks_for_claim(s: D.Snap, inv: str, stmt: str, m: dict, rv: dict) -> bool:
    """Under done_claim@1, the instrument's count of the real calls a task needed is the whole set when it is 0 or
    all of them: \"nothing was sent\" on 0 of 1 real calls, \"sent to all five contacts\" on 5 of 5. Elsewhere a
    count is read as about a sentence only when its name shares a word with it."""
    return O.census(rv) and own_count(s, inv, m, rv)


def causal_is_the_logs(s: D.Snap, inv: str, stmt: str, support: list[str]) -> bool:
    """Under done_claim@1, a reason given for a failure the instrument's log records (\"failed due to permission
    denied\") is the log's own error line, not a causal claim that needs an experiment."""
    if "done_held_to_log" not in held_to(s, inv):
        return False
    return O.reason_is_the_logs(stmt, _action_logs(s, [x for x in support if x in s.nodes
                                                       and s.nodes[x]["type"] == "result"]))


def vouched_words(s: D.Snap, inv: str, m: dict, stmt: str = "") -> frozenset:
    """The absolute words a pinned claim policy vouches for, for a claim that binds a count from the instrument's
    result of that policy's own shape."""
    held = held_to(s, inv)
    rid = m.get("result")
    if not rid or rid not in s.nodes or not _from_instrument(s, rid):
        return frozenset()
    body = s.nodes[rid]["body"]
    out: frozenset = frozenset()
    if "flow_held_to_log" in held:
        x = FL.log(body)
        if x and FL.clean(x):
            out |= FL.VOUCHED
    if "proved_held_to_checker" in held:
        x = PC.report(body)
        if x and x["state"] == "proved":
            out |= PC.VOUCHED
        elif x and x["state"] == "bounded" and PC.says_bound(stmt):
            out |= PC.VOUCHED_BOUNDED
    return out


def register_whole_set(s: D.Snap, inv: str, m: dict, rv: dict) -> bool:
    """Under corroboration@1: is this bound value the instrument register's count of the sources on file? Those
    sources are every source there is on the fact, not a sample of them, so "all three carry the same wire report"
    needs no k-of-n count behind it."""
    if "corroboration_held_to_register" not in held_to(s, inv):
        return False
    rid = m.get("result")
    if not rid or rid not in s.nodes or not _from_instrument(s, rid):
        return False
    x = R.register(s.nodes[rid]["body"])
    return bool(x) and x["sources"] is not None and R.count(rv) == x["sources"]


def census_count(s: D.Snap, inv: str, stmt: str, m: dict, rv: dict) -> bool | frozenset:
    """Is this bound count a census the statement's pass claim speaks of? Under software@3, the instrument's run of a
    test suite ran every test: "all tests pass" on its 14 of 14 says what was counted, where "all" on 14 trials of
    something open-ended would be a sample. The count must be of tests, complete (k = n), and from an instrument run
    that passed; the statement must make a pass claim."""
    p = profile_of(s, inv)
    if "win_held_to_heldout" in held_to(s, inv):         # the baseline comparison: every seed the instrument ran
        rid = m.get("result")
        if rid and rid in s.nodes and _from_instrument(s, rid) and E.census(m, rv):
            return E.CENSUS_WORDS            # truthy; checks.py adds these words to the ones a census answers
        return False
    if not p or "pass_held_to_run" not in p.validators:
        return False
    k, n = rv.get("k"), rv.get("n")
    if not isinstance(k, (int, float)) or isinstance(k, bool) or not n or k != n:
        return False
    if not _TEST_COUNT.search(f"{m.get('name') or ''} {m.get('key') or ''}"):
        return False
    rid = m.get("result")
    if not rid or rid not in s.nodes or not _instrument_backed(s, rid) or _run_says(s.nodes[rid]["body"])[0]:
        return False
    return bool(pass_claims(stmt))


def _pass_held_to_run(s: D.Snap, stmt: str, results: list[str]) -> list[Problem]:
    """A pass, a fix or 'ready to merge' needs an instrument run that passed. When the instrument's run is there and
    failed, the refusal says what it recorded; when no supporting result is the instrument's, it says that."""
    said = pass_claims(stmt)
    if not said:
        return []
    if any(_instrument_backed(s, r) and not _run_says(s.nodes[r]["body"])[0] for r in results):
        return []
    for r in results:
        failed, what = _run_says(s.nodes[r]["body"])
        if failed and _from_instrument(s, r):
            return [Problem("PASS_CONTRADICTED",
                            f"'{said[0]}' is asserted, but the instrument's run it rests on says otherwise: {what} — "
                            "say what the run recorded, and that it isn't passing yet",
                            fix="state the run's counts ('k of n tests pass; the rest fail') and drop the pass or the "
                                "fix until the instrument's run on this change passes", words=said)]
    return [Problem("PASS_WITHOUT_INSTRUMENT_RUN", f"'{said[0]}' is asserted, but no supporting result comes "
                    "from an instrument-recorded run that passed — tests must be run by the instrument, not reported",
                    fix="register_run with the test command as code; the instrument's re-run is the evidence — write "
                        "the claim once the re-run has landed (the order's reply names it)", words=said)]


# ── optimization@3: the values behind "optimal" ──
# The MIP convention: a solve is optimal when the relative gap |bound − objective| / |objective| is within the solver's
# tolerance (1e-4 is the default of CPLEX, Gurobi, HiGHS and SCIP) and the incumbent is feasible.
GAP_TOLERANCE = 1e-4
_FALSE = (False, 0, "false", "False", "no", "No")
# 'optimal' as a reference point, not said of the plan: "within 1% of optimal", "the gap to the optimum", "the optimal
# bound", "close to the optimum"
_OPT_REFERENCE_BEFORE = re.compile(r"(?:\b(?:of|to|from|on|than|versus|vs|relative|above|below|within|near|close|"
                                   r"nearly|approximately|about|towards?)\b[\s,]*(?:(?:the|an?)\s+(?:[\w‐‑-]+\s+)?|"
                                   r"(?:true|proven|known|global|exact|real|lp|best|theoretical)\s+)?)$",
                                   re.I)
_OPT_REFERENCE_AFTER = re.compile(r"^[ \t‐‑-]*(?:bounds?|gap)\b", re.I)
_OPT_UNKNOWN = re.compile(r"\b(?:not (?:known|proven|proved|certain)|unknown|unproven|unproved)\b", re.I)
_OPT_CLAUSE = re.compile(r"[;:!?—]|\.(?!\d)")
# A sentence that denies something isn't a bare optimality claim: audits name the optimum to measure a plan against
# it ("the plan is not optimal; the optimal value is 656", "the rota is infeasible …, whereas the exact minimum cost of
# a rule-abiding rota is 112"). 5 of the 7 corpus sentences the value check alone refused were these.
_OPT_DENIED = re.compile(r"\b(?:no|not|never|none|neither|nor|without|cannot|infeasible|unusable|fail(?:s|ed)?)\b|"
                         r"n't\b", re.I)


def _said_optimal(stmt: str) -> str:
    """The first optimal word said *of* the solution, in a clause that asserts it: '' when every one is a reference
    point (within 1% of optimal, the gap to the optimum, the optimal bound), negated, hedged or unknown, and in a
    sentence that denies anything (_OPT_DENIED): precision over recall."""
    if not L.asserted(_OPTIMAL, stmt or "") or _OPT_DENIED.search(stmt):
        return ""
    for clause in _OPT_CLAUSE.split(stmt):
        if _OPT_UNKNOWN.search(clause) or not L.asserted(_OPTIMAL, clause):
            continue
        for m in _OPTIMAL.finditer(clause):
            if _OPT_REFERENCE_BEFORE.search(clause[:m.start()]) or _OPT_REFERENCE_AFTER.search(clause[m.end():]):
                continue
            return m.group(1)
    return ""


def _gap_of(body: dict) -> tuple[str, float] | None:
    """A result's distance from optimal: ('feasible = false', inf) for an infeasible incumbent, else the relative gap
    from objective and bound when both are numbers (unambiguous), else the recorded gap; None when it says none."""
    v = _vals(body)
    if "feasible" in v and v["feasible"] in _FALSE:
        return "feasible = false", float("inf")

    def num(k):
        x = v.get(k)
        return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None
    obj, bound, gap = num("objective"), num("bound"), num("gap")
    if obj is not None and bound is not None:
        d = abs(bound - obj)
        rel = d / abs(obj) if obj else (0.0 if d <= 1e-9 else float("inf"))
        return f"objective {obj:g} against bound {bound:g}, a relative gap of {rel:.3g}", (rel if d > 1e-6 else 0.0)
    if gap is not None and 0 <= gap <= 1:    # above 1 it's a percentage or an absolute shortfall: units unknown
        return f"gap = {gap:g}", gap
    return None


def _optimal_contradicted(s: D.Snap, stmt: str, results: list[str]) -> list[Problem]:
    """OPTIMAL_CONTRADICTED: 'optimal' said of a solution whose supporting results deny it — an infeasible incumbent,
    or a gap above the tolerance. Refused only when every supporting result that says something denies it."""
    word = _said_optimal(stmt)
    if not word:
        return []
    denials = []
    for r in results:
        g = _gap_of(s.nodes[r]["body"])
        if g is None:
            continue
        if g[1] <= GAP_TOLERANCE:
            return []
        denials.append(g[0])
    if not denials:
        return []
    return [Problem("OPTIMAL_CONTRADICTED", f"'{word}' is asserted, but the result it rests on says otherwise: "
                    f"{denials[0]} — optimal means a feasible incumbent within {GAP_TOLERANCE:g} of its bound",
                    fix="say 'best found' with its gap (or 'within X of the bound'), or solve until the gap closes",
                    words=[word])]
# ── trading@3: the values behind the edge words ──
_OOS_KEY = re.compile(r"oos|out_?of_?sample|holdout|(?:^|_)test(?:_|$)", re.I)
_RETURN_KEY = re.compile(r"return|pnl|profit|cagr", re.I)
_IS_KEY = re.compile(r"(?:^|_)(?:is|in_?sample|insample|train(?:ing)?)(?:_|$)", re.I)
_NAMES_BENCHMARK = re.compile(r"buy[\s‐‑-]*(?:and|&)[\s‐‑-]*hold|benchmark|\bthe market\b|\bindex\b|passive|holding", re.I)
_SAYS_IN_SAMPLE = re.compile(r"in[\s‐‑-]?sample|insample|training|\btrain(?:ed)?\b|fitted|fitting|tuning|tuned|"
                             r"calibrat\w*|estimation (?:window|period)|optimi[sz]ation (?:window|period)|"
                             r"first [\d,]+ (?:trading )?days", re.I)
# A sentence that denies something isn't a bare edge claim: honest audits name the edge to refute it ("there is no
# out-of-sample, after-cost edge", "the in-sample edge did not carry over", "only 2 of the 20 settings beat buy and
# hold", "it underperforms buy and hold"). 27 of 34 corpus sentences the value check alone refused were these.
_EDGE_DENIED = re.compile(r"\b(?:no|not|never|none|neither|nor|without|cannot|fail(?:s|ed)?|los(?:e|es|t|ing)|"
                          r"trail(?:s|ed|ing)?|underperform\w*|shortfall|worse|negative|declin(?:e|es|ed)|beaten|"
                          r"revers\w*)\b|n't\b|\b\d+\s+of\s+(?:the\s+)?\d+\b", re.I)


def _oos_returns(body: dict) -> tuple[tuple[str, float] | None, tuple[str, float] | None]:
    """The strategy's out-of-sample return and the benchmark's, from one result's values: (key, value) each, or None
    when there's none or more than one candidate. The strategy's prefers the after-cost figure (net / after_cost),
    then one that says neither, then the gross one — costs only lower a return, so a gross loss is a net loss and a
    gross shortfall to the benchmark a net one. Statistics of returns, counts and benchmarks are not the strategy's."""
    v, raw = _vals(body), {str(k).lower(): x for k, x in (body.get("values") or {}).items()}
    strat, bench = [], []
    for k, x in v.items():
        if not isinstance(x, (int, float)) or isinstance(x, bool) or not (_OOS_KEY.search(k) and _RETURN_KEY.search(k)):
            continue
        if _STAT_OF_RETURNS.search(k) or _a_count(k, raw.get(k)):
            continue
        (bench if _BENCHMARK.search(k) else strat).append((k, float(x)))

    def tier(k: str) -> int:
        return 0 if re.search(r"net|after_?costs?", k) else 2 if re.search(r"gross|before_?costs?", k) else 1
    pick = None
    if strat:
        best = min(tier(k) for k, _ in strat)
        top = [x for x in strat if tier(x[0]) == best]
        pick = top[0] if len(top) == 1 else None
    return pick, (bench[0] if len(bench) == 1 else None)


def _edge_contradicted(s: D.Snap, stmt: str, results: list[str]) -> list[Problem]:
    """EDGE_CONTRADICTED: an edge word the supporting results' values deny. 'profitable' and 'edge' need the
    out-of-sample after-cost return to be a gain; 'edge', 'alpha' and 'excess return' need it above the benchmark's
    when one is recorded, and 'beats' / 'outperforms' when the sentence names the benchmark (buy-and-hold, the
    index, the market). Refused only when every supporting result that says something denies it, and never in a
    sentence that denies something itself (_EDGE_DENIED): precision over recall."""
    words = [w.lower() for w in L.asserted(_EDGE, stmt)]
    if not words or _EDGE_DENIED.search(stmt):
        return []
    names = bool(_NAMES_BENCHMARK.search(stmt))
    need_gain = any(w in ("edge", "profitable") for w in words)
    need_beat = any(w == "edge" or w.startswith(("alpha", "excess")) or (w.startswith(("outperform", "beat")) and names)
                    for w in words)
    if not (need_gain or need_beat):
        return []
    denials = []
    for r in results:
        strat, bench = _oos_returns(s.nodes[r]["body"])
        if not strat:
            continue
        k, x = strat
        if need_gain and x <= 0:
            denials.append(f"{k} = {x:g}, not a gain")
        elif need_beat and bench and x <= bench[1]:
            denials.append(f"{k} = {x:g}, not above {bench[0]} = {bench[1]:g}")
        else:
            return []
    if not denials:
        return []
    return [Problem("EDGE_CONTRADICTED", f"'{words[0]}' is asserted, but the result it rests on says otherwise: "
                    f"{denials[0]} — out of sample, after costs, that is no edge",
                    fix="state the out-of-sample after-cost return (and the benchmark's) without the edge word",
                    words=words)]


def _in_sample_unlabelled(stmt: str, body: dict) -> list[Problem]:
    """IN_SAMPLE_UNLABELLED: the claim's only bound returns are in sample (is_*, in_sample_*, train_*) and the
    sentence doesn't say so — "the strategy returned 14.2% after costs" reads as the result, and the in-sample return
    is the one the configurations were chosen on. A claim that also binds an out-of-sample return has its headline
    (the in-sample figure bound beside it is context)."""
    keys = [str(m.get("key") or "") for m in body.get("measurements") or [] if isinstance(m, dict)]
    returns = [k for k in keys if _RETURN_KEY.search(k)]
    is_keys = [k for k in returns if _IS_KEY.search(k) and not _OOS_KEY.search(k)]
    if not is_keys or any(_OOS_KEY.search(k) for k in returns) or _SAYS_IN_SAMPLE.search(stmt or ""):
        return []
    return [Problem("IN_SAMPLE_UNLABELLED", f"the claim binds an in-sample return ({', '.join(is_keys[:3])}) but "
                    "doesn't say it is in sample — it reads as the strategy's result, and it is the figure the "
                    "configuration was chosen on", fix="say 'in sample' (or 'on the training window') in the sentence",
                    words=is_keys[:3])]


# a statistic *about* returns (a signal's correlation with tomorrow's return, a hit rate, the volatility) isn't a return
# a strategy earned and charges no costs: a look-ahead diagnostic was refused three times as a backtest (studies T1)
_STAT_OF_RETURNS = re.compile(r"corr|agree|match|hit_rate|_ic\b|beta|volatil|std|(?:^|_)sd(?:_|$)|skew|kurt|acf|"
                              r"autocov|lag\d|"
                              r"t_?stat|p_?val|_se\b|ci_|_ci\b", re.I)
# a benchmark's return is not a return the strategy earned: buy-and-hold, flat, an index (studies T1-T3)
_BENCHMARK = re.compile(r"buy_?(?:and_?)?hold|(?:^|_)bh(?:_|$)|benchmark|(?:^|_)flat(?:_|$)|index", re.I)
# a count of returns is not a return earned: n_returns, insample_n_returns, N_returns_in_sample (studies T3)
_COUNT_KEY = re.compile(r"(?:^|_)(?:n|num|count|nobs|obs)(?:_|$)|_count\b", re.I)
_COUNT_UNITS = {"returns", "days", "bars", "obs", "observations", "count", "draws", "trades", "rows", "n"}


def _a_count(k: str, v: object) -> bool:
    unit = str(v.get("unit") or "").strip().lower() if isinstance(v, dict) else ""
    return bool(_COUNT_KEY.search(k)) or unit in _COUNT_UNITS


def result_issues(s: D.Snap, inv: str, body: dict, pending: list | None = None, author: str = "") -> list[Problem]:
    p = profile_of(s, inv)
    held = held_to(s, inv)
    if not held and not p:
        return []
    v = _vals(body)
    out: list[Problem] = []
    # the instrument's re-execution records what the code printed and asserts nothing: the value validators
    # (feasibility beside an objective, costs beside returns) were asked of the original result
    if author and author == s.policy.instrument:
        return out + (W_result_issues(p, s, inv, body, pending or []) if p and p.workflow else [])
    if "objective_needs_feasibility" in held and "objective" in v and "feasible" not in v:
        out.append(Problem("OBJECTIVE_WITHOUT_FEASIBILITY", "a result reports an objective value without saying whether "
                           "the solution is feasible", fix="add values.feasible (true/false) and bound or gap"))
    if "eval_needs_direction" in held:
        out += E.result_issues(body)
    raw = {str(k).lower(): x for k, x in (body.get("values") or {}).items()}
    earned = [k for k in v if re.search(r"return|sharpe|pnl|cagr|profit", k) and not _STAT_OF_RETURNS.search(k)
              and not _a_count(k, raw.get(k)) and not _BENCHMARK.search(k)]
    if "backtest_needs_costs" in held and earned and not _has(v, r"fee|cost|slippage|commission"):
        out.append(Problem("BACKTEST_WITHOUT_COSTS", "a backtest result reports returns (" + ", ".join(earned[:4])
                           + ") without the costs it charged — add values.fees (and slippage) to this result; zero "
                           "is a value, absence isn't", fix="add values.fees and values.slippage to the result"))
    if p and p.workflow:
        out += W_result_issues(p, s, inv, body, pending or [])
    return out


def W_result_issues(p: "Profile", s: D.Snap, inv: str, body: dict, pending: list) -> list[Problem]:
    from . import workflow as W
    return W.result_issues(p, s, inv, body, pending)


def node_issues(s: D.Snap, inv: str, ntype: str, body: dict, pending: list) -> list[Problem]:
    """Workflow refusals on artifacts, sources and decisions (profiles with a workflow: @2 and later)."""
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
    if D.unchecked_answers(s, q):              # a checked answer beside an unchecked one doesn't settle it
        return ""
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
                  "seats": [list(x) for x in p.seats], "workflow": _wf(p.workflow)}
                 | ({"deprecated": p.deprecated} if p.deprecated else {}) for pid, p in PROFILES.items()}


def describe_claim_policies() -> dict:
    """Every claim policy: what it holds, the shape of result it reads, the refusals it can give, and what it stands
    down in the kernel for claims on that shape."""
    return {cid: {"about": c.about, "reads": c.reads, "refuses": list(c.refuses), "validators": list(c.validators),
                  "relaxes": list(c.relaxes)} for cid, c in CLAIM_POLICIES.items()}


def pinned(s: D.Snap, inv: str) -> dict:
    """What an investigation is held to, for a viewer: its profile id and its claim policies."""
    p = profile_of(s, inv)
    return {"profile": p.id if p else "", "claim_policies": [c.id for c in claim_policies_of(s, inv)]}


__all__ = ["CLAIM_POLICIES", "ClaimPolicy", "LABELS", "PRED_DESC", "PROFILES", "Profile", "RECIPES", "Stage",
           "Workflow", "claim_issues", "claim_policies_of", "completion", "default_done", "describe",
           "describe_claim_policies", "evaluate", "get", "held_to", "labels_of", "latest", "node_issues", "pinned",
           "profile_of", "result_issues", "review_refusal", "validate_claim_policy_ids", "validate_profile_id",
           "view", "workflow_of"]

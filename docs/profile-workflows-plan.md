# Profiles as workflows — plan

*Written 2026-10-26. Status: plan. Nothing in it is built yet beyond what §1 lists as present.*

## 0. The question this answers

HypSwarm's trading and software profiles run on HypGraph's scientific graph with discipline labels. Is that a
feature of HypSwarm bolted onto a scientific HypGraph, or should HypGraph itself be built from each discipline's
method the way it is built from the scientific one?

**Answer: the record's kernel should stay one thing — the general shape of justified belief, which the scientific
method happens to be the clearest statement of — and each discipline's *workflow* should become a first-class,
versioned object inside a HypGraph profile that the kernel enforces and HypSwarm executes.** Today the workflow
exists only as a paragraph in the profile's notes and as a diagram on hypswarm.com. That is the gap.

## 1. What a profile is today, and what it is not

| a profile controls today (hypgraph 0.4.3) | a profile does not control |
|---|---|
| vocabulary: a meaning per node type ("experiment = a test plan") | the node types and relations (fixed, 12 + 22) |
| `done_when` per target type (which predicates an order needs) | the **stages** a question passes through and the gate between each |
| domain predicates: `tests_pass`, `backtested_oos`, `sourced`, `feasible_bounded` | what **invalidates** a claim later: `RISKY` is fixed to the scientific relations; `cites` is not in it, so a withdrawn source leaves a knowledge claim standing |
| write-time validators: `PASS_WITHOUT_INSTRUMENT_RUN`, `EDGE_WITHOUT_OOS_COSTS`, … | the **evidence ranking** (`external > new_data > separate_implementation > …` is scientific replication; software needs *runs on the current code*, trading needs *out of sample, after costs, recent*) |
| completion criteria (`requirements_verified`, `position_recorded`, …) | typed **artifacts** (a diff with its base commit, a position with size and stop, a source with the passage that says it) — all are `artifact` / `decision` / `source` with no required discipline fields |
| suggested seats | the **report**: every profile prints "Facts from the research graph" |
| | the **order**: HypSwarm issues from the question board, not from the stage a question is in |

The discovery study (HypSwarm `studies/discovery/`) showed what this costs: 110 of 118 refusals were vocabulary
friction because the models were writing discipline work into scientific slots, and the honesty rules by themselves
did not beat a prompt. What a prompt cannot do is remember that the code changed since the tests ran, that the
source was retracted, that the regime moved, that the teammate's number is stale — the workflow's *invalidation*
and *gates*. That is where the record should win, and it is exactly what profiles don't yet encode.

## 2. The design: one kernel, five workflows

A **Workflow** is data on the Profile, versioned with it (`software@2`), hash-chained with the investigation that
pins it:

```python
@dataclass(frozen=True)
class Stage:
    name: str                      # "specified", "implemented", "verified", "reviewed", "released"
    holds: tuple[str, ...]         # node types that live in this stage ("experiment", "artifact")
    gate: tuple[str, ...]          # predicates that must hold to leave it (existing + new ones)
    who: str                       # the role that works it (worker | reviewer | lead | instrument)

@dataclass(frozen=True)
class Workflow:
    stages: tuple[Stage, ...]      # in order; a question is "in" the first stage whose gate is not met
    invalidates: tuple[str, ...]   # relations that put dependants at risk when the far end changes or falls
    freshness: dict[str, str]      # per node type: what "current" means ("artifact": "same sha as the run used")
    artifacts: dict[str, dict]     # typed artifacts: kind → required fields ("diff": {base_sha, head_sha, files})
    evidence_rank: tuple[str, ...] # the profile's own ranking for `evidence`
    report: str                    # the report template's name
```

The kernel keeps: twelve node types, hash chain, append-only, derived standing, refusals, the instrument. The
profile supplies: which relations are risky here, what fresh means, what each stage needs, what the report says.
HypSwarm reads the stage and issues the next gate's order to the seat whose role owns that stage.

### The five workflows (the §P0 deliverable is one page each; this is the shape)

| profile | stages | gates (new predicates in bold) | invalidation | typed artifacts |
|---|---|---|---|---|
| scientific | asked → conjectured → tested → evidenced → claimed → reviewed → decided | hypothesis stated, experiment preregistered, run registered, result, claim, review | the present `RISKY` | data (sha), protocol |
| software | specified → implemented → verified → reviewed → released | requirement question; **diff registered** (base + head sha); `tests_pass` on **that head**; review; decision | a new head sha supersedes the diff → every `tests_pass` result on the old head is **stale**, its claims AT RISK | diff, build, test-run |
| trading | asked → thesised → preregistered → backtested → risk-reviewed → positioned → monitored | hypothesis with the move it predicts; experiment with window + costs **before** the run; `backtested_oos`; review by risk; decision with size/stop/review_date; **`still_valid`** (data newer than the backtest's window, regime check) | time: a result **expires** at `review_date`; a regime-change notice puts positions AT RISK | backtest, position (paper) |
| knowledge | asked → sourced → claimed → checked → compiled | source with passage + retrieved; `sourced` claim; fact-checker review; report lint | **`cites` becomes risky**: a withdrawn or superseded source puts its claims AT RISK; a source older than `max_age` is stale | source, excerpt |
| optimization | modelled → solved → bounded → verified → recommended | hypothesis = modelling choice; experiment = solve config; `feasible_bounded`; verifier review; decision names the incumbent | a changed instance artifact (new sha) supersedes every solve on it | instance, solution |

Two cross-cutting rules the workflow makes possible and the kernel can't express today:

- **Freshness.** A result is *current* only if the artifacts its run `uses` are the live versions. Software and
  optimization need this most; it is the "code changed since the tests ran" case nothing in a prompt survives.
- **Expiry.** A trading result carries `valid_until`; past it the standing says STALE and the claim needs a rerun.

## 3. Phases, gates, spend

| phase | work | where | gate |
|---|---|---|---|
| **P0 — specs** | one page per profile: stages, gates, invalidation, artifacts, report; reviewed before code | `HypGraph/docs/workflows/<profile>.md` | the user reads all five and agrees the stages are the discipline's, not ours |
| **P1 — kernel** | `Workflow` / `Stage` on `Profile`; profile-defined `invalidates` merged into at-risk derivation; `freshness` in `derive`; typed artifacts (required fields by `kind`); `Graph.stage(question)`; `evidence_rank` per profile; report templates; new predicates (`diff_registered`, `still_valid`, `fresh`); schema bump with migration (old records = `@1`) | HypGraph, tests per profile + a replay of the discovery records to see what would change | 100 % of existing tests pass; every old record derives the same standing under `@1` |
| **P2 — orders from stages** | the scheduler asks the record which stage each question is in and issues that gate's order to the role that owns it; order text names stage and gate; the lead's report comes from the profile's template; `completion` reads the last stage | HypSwarm, scripted-model tests for every path (as now) | the stub discovery run settles every family through its stages |
| **P3 — the test that can show it** | extend the discovery harness with the change-per-discipline cases: a commit after the tests (software), a retracted source (knowledge), a regime notice and an expired backtest (trading), a changed instance (optimization), a corrected file (scientific); P vs R; predictions first | HypSwarm `studies/discovery/`, ≈ $2 | this is where a prompt cannot hold state and the record can; if R does not win **here**, the workflow design is wrong |
| **P4 — docs** | profiles presented as HypGraph's, with the workflow on hypgraph.com as it is on hypswarm.com; the engineers pages; `hypgraph profiles` prints stages | both sites | — |

P1 is the considerable part: two to three days of kernel work with tests, and the first schema version bump that
needs a migration story. P0 is a day and decides whether P1 is right. P3 is the only spend.

## 4. What stays as it is, on purpose

- Twelve node types. A commit is an artifact with required fields, not a new type; a position is a decision with
  required fields. The spec, the Atlas, the MCP tools and the playground don't fork per discipline.
- One hash chain and one `verify`. A workflow is data the chain covers, not code the chain can't see.
- Dependency-free kernel. Workflows are tables and predicates, like profiles are now.
- The honesty rules. They held in the discovery study; the workflow adds the state they can't carry.

## 5. Risks

- **Over-specifying a discipline we don't practise.** P0 is where a trader or an engineer corrects the stages; the
  specs should quote the method they're taken from (preregistration, CI gates, source criticism, verification).
- **Schema version.** Old records must keep deriving identically; `profile@1` is the frozen behaviour.
- **Stage inference, not stage setting.** A question's stage must be *derived* from what the record holds (the
  first unmet gate), never written by an agent — same rule as standing.

# Harmony vs chaos: coordinating agent teams through the record

*Plan, draft 1, 2026-10-24. Internal: not committed, not published. Everything here is a hypothesis until the case
study below has been run.*

**The claim we want to earn:** when a team of agents coordinates through a shared evidence record, the team gets
more right for less money than the same agents coordinating through conversation. The record does three jobs:
it compiles each agent's context, it accepts work against checkable criteria, and it says exactly what to stop
when a premise falls.

We will only say "harmony is cheap and effective, chaos is expensive and wrong" if a preregistered study on tasks
with known answers shows it. If it doesn't, we publish that instead. HypGraph's slogan applies to HypGraph.

---

## 1. What Pegasus's own ledger already shows

This is a free look-back with no model calls (2026-10-24). The proxy metered every model call. 96 % of spend is
attributed to a task, so spend can be joined to the kanban.

| | |
|---|---|
| Metered spend, 2026-10-04 → 10-24 | **$126.66**, 21,220 calls, 610 tasks |
| Input : output tokens | **100 : 1** (725.8 M in, 92.6 % from cache; 7.63 M out) |
| Mean input per call | **34,865 tokens** |
| Spend on tasks later **cancelled** | **$18.63 (15.3 %)**, 70 tasks |
| Spend on **repeats** of an earlier task with the same title | **$18.51 (15.2 %)**, 211 tasks |
| Largest repeat groups | "Consider proposing a skill for … pattern": 107 tasks, ≈ $5.6 (×49 for `shell_exec` alone). "Daily dispatch: … 57 idle teammates": 15 runs, $2.82. Several research checkpoints ran twice. |

How to read it:
- **This is observational.** It shows *where waste could be*, not how much coordination would save. Some repeats are
  legitimate routines, and the cancelled and repeated sets overlap. It doesn't prove anything. It does tell the
  study where to look.
- **The money is reading, not thinking.** At 100:1, almost all of the cost is context sent in, and most of it is
  served from cache. Savings come from two places, and the study has to measure them separately:
  - **fewer calls:** no duplicate, abandoned or dead-branch work, and stopping when the question is settled;
  - **smaller context per call:** a compiled brief instead of history.

  Because 92 % of input is already cached, shrinking context saves much less than the raw token count suggests.
  We'll report both effects in dollars, not in tokens.
- The repeat groups look like what chaos produces: work generated from events with no shared state to say "this
  is already open, already done, or already decided".

---

## 2. The idea: coordinate through the record, not the conversation

Most multi-agent systems coordinate the way a group chat does. An orchestrator reads a growing transcript,
writes prose briefs, gets prose back and decides by impression. Nothing stops two agents taking the same angle,
an agent building on a result that has since been withdrawn, or a confident sentence travelling up three levels
unchecked. Every round re-reads everything.

**Record-coordinated** teams replace each of those with something computed from HypGraph, with no model calls:

| Job | In chaos | In harmony (computed from the record) |
|---|---|---|
| **What the orchestrator knows** | the transcript and summaries of summaries | a **compiled brief**: what's established, contested or fallen; the ranked frontier; what's in flight; budget left; only what changed since the last brief |
| **What a sub-agent is asked** | a prose brief | a **work order**: one node to move, pinned to its version, with its premises and their standing, what has already been tried (failures included), the prediction that would refute it, the method required, checkable done-when criteria, a budget and a lease |
| **What comes back** | prose | **writes to the record** (runs, results, claims), each one checked as it's written, plus a short note |
| **How work is accepted** | the orchestrator's impression | **predicates checked against the record**, each MET / NOT MET with the node that proves it |
| **What happens when a premise falls** | nothing, unless someone notices | the **blast radius** lists exactly which orders and claims rest on it; those orders are cancelled or revalidated, and nothing else is touched |
| **Duplicates** | discovered afterwards, if ever | an order's target is **leased**; the frontier excludes leased work and work already done by the same method |

**Prior art, said plainly.** A shared workspace for coordination is old: blackboard systems (Hearsay-II), tuple
spaces, stigmergy. Recent multi-agent LLM frameworks such as MetaGPT's SOPs, AutoGen and ChatDev structure the
conversation. What we think is new, and the study has to test:
- the shared workspace **derives epistemic standing** (review, independence, fallen premises) instead of storing it;
- it **refuses overclaims at write time**;
- **briefs and acceptance are compiled from it deterministically**, so coordination costs no model calls and leaves
  an audit trail that anyone can verify by hash.

The literature review is a phase-6 task. Every citation will be checked before it's used, including the MAST
failure taxonomy (Cemri et al., 2025).

---

## 3. The exact context: what each agent receives

Each context is deterministic and has a token budget. Stable sections come first so the provider's cache covers
them. Every line is traceable to a node and version, and each brief carries a hash of its inputs.

### 3.1 The orchestrator's brief: `g.brief(inv, role="orchestrator")`

```
MISSION        the investigation's question and the success test (one paragraph, from the investigation node)
RULES          how claims are checked, how work is accepted (compressed, about 150 tokens, never changes → cached)
ROSTER         role → kinds of work it takes (supplied by the host: Pegasus's org chart, or a list)
STANDING       established · contested · fallen · at risk: one line each, code + sentence + level
FRONTIER       next experiments, ranked (plan.next_experiments): why, what it would decide, estimated cost
               from the measured cost of similar nodes
IN FLIGHT      open orders: assignee, age, spend so far, lease expiry
RETURNED       orders waiting for acceptance, with their predicate results already computed
BUDGET         spent / cap for the investigation (from the spend hook)
SINCE LAST     what changed since the last brief this orchestrator read (event delta). On later turns this is
               the only section that grows; the rest is cached
```

Target size: about 2,500 tokens on the first turn and a few hundred after that, against Pegasus's current 34,865
mean input per call. The orchestrator's tools are `issue_work`, `check_work`, `accept_work`, `cancel_work` and
`report`. It can't write results itself; producing them is the sub-agents' job.

### 3.2 A sub-agent's work order: `g.order_brief(order)`

```
OBJECTIVE      move EX4 (v2): "Does the 2.8-point gap survive a paired test at n = 1,000?"
PREMISES       RS2 v1 "A 812/1000, B 784/1000": unchecked, 1 line of support
               CL1 v3 "…": established (fisher, v3)
KNOWN          RN3 tried an unpaired z-test → RS4 (p = 0.04). A critic objected: wrong test for paired items.
               Don't repeat it.
PREDICTION     if the gap is real, the paired test gives p < 0.05. If p ≥ 0.05, H2 is not supported at this n
METHOD         paired test on the item-level file (data/items.csv); register the run (register_run)
DONE WHEN      [result_exists rel=tests target=H2 from_run executes=EX4]
               [claim_accepted about=H2]           ← the record's own claim checks must pass
               [no_open_objection target=EX4]
BUDGET         ≤ 40 calls / $0.05 · lease until 14:20
RETURN         your deliverable is the writes above. Your note: ≤ 120 words, what you did and anything you
               couldn't do. No conclusions that aren't in a claim.
```

### 3.3 Acceptance and re-planning

- `check_work(order)` evaluates each predicate against the record. All MET → `accept_work` writes a **decision**
  node `based_on` the evidence versions, so it's audited and flagged REVISIT if the evidence changes. A NOT MET
  gives a rework order (at most 2), then escalates.
- On a withdrawal or a contesting verdict, `blast_radius` lists the dependent orders. The host cancels them with
  the reason, and only them, and the next brief shows what was cancelled.
- The final report starts from `report(inv)` and is run through `check_text` before it's handed over.

### 3.4 Predicates, a small closed set

`result_exists(rel, target, from_run?, run_kind?)` · `claim_accepted(about)` · `run_registered(executes)` ·
`measured_with(method_trial)` · `no_open_objection(target)` · `report_clean(text|path)` ·
`within_budget(order)`. Each one is deterministic and returns the ids that satisfy it.

### 3.5 What changes in HypGraph (0.4.0 candidate, unpublished until the study is done)

- **Library:** `coord.py` with `brief`, `order_brief`, `issue_work`, `check_work`, `accept_work`, `cancel_work`.
  - Orders are `task` nodes with new optional fields: objective, premises@version, prediction, method,
    done_when, budget, assignee, lease. Their status (open / returned / accepted / reworked / cancelled) is
    derived from events, never set.
  - `works_on` joins the blast-radius relations, so orders resting on a fallen node are listed.
- **Surfaces:** MCP tools of the same names, `hypgraph brief`, and an Atlas card for orders.
- **Tests:** predicates, determinism (same record → same brief hash), the delta brief, and cascade cancellation.

### 3.6 What changes in Pegasus

- **Study harness** (`dev/study_run.py`): runs one task instance under one condition. Each run gets a fresh
  per-run graph file, a fresh scratch folder and a fixed roster. Memory, company search, awareness and findings
  are off. Model calls go through the proxy labelled `X-Pegasus-Investigation: study-<run>`, so the ledger meters
  each run exactly.
- **Isolation:** the live company and heartbeat never touch study runs, so the team isn't disturbed and can't
  contaminate a run.
- **Answer keys:** they never enter the container (agent tools include a shell). Instances are generated on the
  host, only the data is copied in, scoring happens on the host, and each run's folder is pulled out and removed
  before the next run starts.
- **Later:** `research.coordination: prose|record` per investigation, for the team's real work.

---

## 4. The case study

### 4.1 Question

On research tasks whose answers are known, does a record-coordinated team get more right for less money than
teams that coordinate in prose?

### 4.2 Conditions

All four conditions use the same model, tools, roster (an orchestrator plus 4 sub-agents: analyst, statistician,
engineer, critic) and per-run cap.

| | Condition | What it stands for |
|---|---|---|
| **A** | *Chat*: shared transcript, prose delegation, prose returns, no checks | the common framework setup. The chaos baseline |
| **B** | *Pegasus today*: delegate with done_when, war room, focused check, prose returns, no graph | a strong, already-improved baseline, so we aren't beating a strawman |
| **C** | *Record-coordinated*: compiled brief, work orders, writes as returns, predicate acceptance, blast-radius re-planning, checked report | harmony |
| **D** | *C without the gates*: compiled briefs and orders, but acceptance is the orchestrator's judgement and claims aren't refused | ablation: how much comes from the gates and how much from the briefs |

### 4.3 Tasks: generated instances with planted answers

Each family is a generator. Every run gets a fresh instance from a seed, so nothing can be memorised. Each
instance is decomposable into 3–6 sub-questions (otherwise there's nothing to coordinate) and contains one trap.
Only the host holds its key.

| Family | Planted truth | Trap |
|---|---|---|
| F1 eval comparison | A beats B by a planted margin, which is or isn't significant at n | "significantly better", or an unbound number |
| F2 rare failure | 0 of 50 failures in the logs, while the true rate is 1 in 500 | "never" |
| F3 leaky split | the validation split leaks, and the true accuracy is lower | reporting the headline number |
| F4 confounded uplift | a confounder explains the uplift | a causal claim |
| F5 weak null | no difference seen, but the test is underpowered | "no effect" |
| F6 disguised duplicate | two sub-questions are the same question | does the team do the work twice? |
| F7 premise fall | a data file is declared corrupt at time T, the same notice in every condition | is spending on dependent work after T stopped? |
| F8 cipher, known key | Pegasus's cipher generators, real multi-angle work | declaring a break without a margin over the null |
| F9 synthetic calls | the bioacoustics generator, with known calls | quoting detections without the card |
| F10 conflicting sources | two sources disagree because one is in the wrong unit | averaging them |

Each family needs:
- a **reference solution** checked deterministically;
- a **pilot showing a single agent can't solve it in one call**; if one can, the family is dropped, since it would
  measure nothing.

### 4.4 Outcomes (preregistered)

- **Primary 1, correctness:** the fraction of sub-questions answered correctly, scored by a deterministic parser.
  Every condition must end with the same structured answer block. A run counts as *correct* when every core
  sub-question is.
- **Primary 2, cost:** metered dollars per run from the proxy ledger, every call included, plus **dollars per
  correct run**.
- **Secondary:**
  - overclaims that survive into the final report: a per-instance trap list scored by a fixed rubric, plus a
    blinded human review of a sample;
  - dollars on duplicated work (F6), and on dependent work after the fall (F7);
  - calls, input / cached / output tokens, and wall time;
  - how often runs hit the cap. Hitting the cap is a *result*, not an exclusion.
- **Waste accounting:** each call is labelled with its run and order, so spend splits into accepted work vs.
  rework, cancelled, duplicated and post-fall work. This is the number for "the cost savings".

### 4.5 Design and analysis

- **Paired:** every instance runs under all four conditions, in a randomised, interleaved order, so provider load
  and time-of-day affect every condition alike.
- **Planned size:** 10 families × 3 instances × 4 conditions = **120 runs**. The final count is fixed by a rule
  written now and applied to pilot variance before the confirmatory run. Pilot data is excluded from the analysis.
- **Cost:** the paired log ratio per instance, with a bootstrap CI over instances.
- **Correctness:** paired comparison per instance, plus mixed-effects logistic regression with family as a random
  effect.
- **Contrasts:** C vs A and C vs B are primary, with Holm correction; D vs C is secondary.
- **Power, stated before the run:** with 30 paired instances, cost differences of about 20 % or more are
  detectable (paired, low variance). For correctness, 30 instances detect roughly 40 % → 80 % but not 60 % → 75 %.
  We'll say which one we're powered for and won't claim the other. (`hypgraph.stats.detectable` will compute it.)

### 4.6 Hypotheses (directional, with what counts as failure)

| | Prediction | Fails if |
|---|---|---|
| H1 | C costs less per run than A | the 95 % CI of the cost ratio C/A includes 1 |
| H2 | C is at least 20 points more correct than A | the CI lower bound is below +20 points |
| H3 | C is no less correct than B (margin 10 points) **and** cheaper | either part fails |
| H4 | after a premise falls (F7), C spends less on dependent work than A and B | the CI includes 0 |
| H5 | C's final reports contain fewer surviving overclaims | the CI includes 0 |

We commit to reporting every hypothesis, including the ones that fail. One honest risk for H1: harmony adds tool
calls (writes, checks), so it may cost *more* per run and still win on dollars per correct run. If that happens,
that's what we claim, and nothing more.

### 4.7 Blinding and independence

- **The record is never the judge of its own success.** Answer keys and scoring sit outside HypGraph.
- **Human review** sees the normalised answer text with node codes such as CL3 stripped out, because codes would
  reveal condition C. Some unblinding risk remains, and the paper will list it as a limitation.
- **The analysis script is written and frozen in phase 0.**

### 4.8 Preregistration

`prereg.md` + `analysis.py` + the generator code and seeds are hashed, and the hash goes into a commit **before**
any confirmatory run. The hypotheses are also entered into a separate, sealed HypGraph record (we use our own
tool), and its chain head is part of the commitment. Whether to publish the hash early, as a timestamp, is the
user's call.

---

## 5. Phases, gates and spend

| Phase | Work | Model spend | Gate to go on |
|---|---|---|---|
| **P0** | prereg, metrics, analysis script, look-back write-up | $0 | user approves the prereg |
| **P1** | HypGraph `coord` (brief, orders, predicates, cascade) + tests; Pegasus study harness, isolation, labels | $0 | determinism + isolation tests pass; dry run on a stub model |
| **P2** | the 10 task generators + reference solutions + scorers | $0 | every reference solution scores 100 %, every trap is detected |
| **P3** | **pilot**: 2 families × 4 conditions × 1 instance on the cheap tier | **≤ $5** | instrumentation is complete; no family is trivially solvable; the sample size is fixed by the written rule |
| **P4** | **confirmatory run** from a frozen commit | **est. $20–50** on DeepSeek-V4.1-Flash (≈ $0.001/call at our cache rate) · ≈ 6× that on the current seats' mix | user approves the budget |
| **P5** | frozen analysis, blinded review, internal report | $0 | — |
| **P6** | showcase page, preprint, paper draft | $0 | **publishing is the user's decision** |

A robustness slice (2 families × C vs A) on a stronger model is optional after P4. It shows the effect isn't a
weak-model artefact.

---

## 6. The showcase: what chaos and harmony look like (hypgraph.com/harmony, built only from real runs)

- **Two lanes, same instance, same model:** chaos on the left, harmony on the right, replayed from the recorded
  runs, not animated from imagination.
- **Per lane:** agents as nodes and hand-offs as arcs, with a live **cost meter** fed by the ledger.
  - **Chaos:** duplicates flash and overclaims travel upward. When the premise falls, a shockwave passes and the
    lane keeps spending on the dead branch.
  - **Harmony:** the refused claim bounces back and returns honest. The fall cancels exactly its blast radius.
- **The scoreboard:** correct sub-questions, dollars, dollars per correct answer and waste by kind, with CIs from
  the study rather than single runs.
- **"Verify this run":** every replay ships its bundle, so anyone can check it by hash in the browser. Chaos runs
  are recorded too: their transcripts are hashed alongside.

---

## 7. Paper path

- **Working title:** *Coordinating LLM agent teams through a derived-standing evidence record.*
- **Contributions:**
  1. the method: compiled briefs, work orders, predicate acceptance and cascade containment, all deterministic;
  2. an open, generated benchmark of decomposable research tasks with planted traps;
  3. the preregistered study, with metered cost;
  4. released artefacts: code, generators, bundles and ledgers.
- **Route:** internal report → preprint → IEEE venue (chosen in P6; we'll check its policy on preprints and
  artefacts first).
- **Data note:** nothing from the unpublished D'Agapeyeff work goes in. Whether the aggregate look-back numbers in
  §1 may appear is the user's call.

---

## 8. Positioning: drafts, held until the results are in

| Result | What we'd say |
|---|---|
| H1–H5 hold | "HypGraph is the shared truth agent teams coordinate on: they stay true, stay focused, and cost less." The evidence layer becomes the coordination layer. |
| Correctness wins, cost doesn't | "More right per dollar." No claim about cheaper runs. |
| Neither wins | Keep "the evidence layer", and publish the negative result. That's also a contribution. |

The slogan stays either way.

---

## 9. Risks

- **The baselines must be built as well as we build harmony.** B is Pegasus's best current practice, partly for
  this reason.
- **The tasks could favour graph-shaped work.** Mitigation: families F8–F10 aren't graph-shaped, and every family
  must show that it needs coordination at all.
- **Provider noise** (429s, latency). Mitigation: interleaved order, metered cost rather than wall time as primary,
  errors counted.
- **Small n for correctness.** It's stated up front, and the cost analysis carries the power.
- **The orchestrator could game the predicates** (writing a result to satisfy one). Mitigation: claims pass the
  write-time checks, the critic reviews, and the score comes from the answer key, not the predicates.

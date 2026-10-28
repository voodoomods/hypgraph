# The HypGraph record format — `hypgraph/1`

Status: draft 3 (HypGraph 0.3). Licence: CC BY 4.0. This page is enough to write another implementation, a
verifier or a viewer.

## 1. Model

A record is a set of **nodes** (typed, versioned), **edges** (typed links between two nodes), **withdrawals**,
**retractions** (of edges), **leases** (who is working on a node) and **events**. Every table is append-only: a
correction is a new row, never an edited one.

- A node has an `id`, a `type`, a display `code` (H1, CL3 …, unique per type within its investigation), the
  investigation it belongs to (`inv`, empty for an investigation itself), `created_at` and `created_by`.
- Its content lives in **versions** `(node, v, at, by, reason, body)`. `body` is the canonical JSON (§3) of the
  node's fields. The current version is the highest `v`.
- An edge records the version of each end when it was made (`src_v`, `dst_v`). A review or decision is about *that*
  version.

## 2. Vocabulary

| type | code | fields (\* required) | what it is |
|---|---|---|---|
| `investigation` | INV | **title**\*, **objective**\*, success_criteria, scope, state, reviewers, constants, strict_claims, keywords, projects, doi, note, legacy_case | The study: an objective, its scope, who reviews it. Every other node belongs to one. |
| `question` | Q | **text**\*, why | Something you want to know. |
| `hypothesis` | H | **statement**\*, assumptions, **predictions**\*, distinguishing, open_questions | A possible answer, with the predictions that would show it wrong. |
| `claim` | CL | **statement**\*, scope, limitations, kind, measurements, evidence_note, exposure, exposure_unit, legacy | What you assert is known, with its scope and its numbers bound to results. |
| `experiment` | X | **aim**\*, **protocol**\*, controls, **success_criteria**\*, method, budget, power_check, cost_minutes, seed | A planned test: aim, protocol, controls, success criteria, and what each hypothesis expects. |
| `run` | RUN | **kind**\*, job_id, name, state, code, inputs, outputs, args, config, seed, env, started, finished, exit_code, log_sha256, note | One execution: code, inputs and outputs hashed, seed, state. `kind=lab` only from an instrument. |
| `result` | RS | **summary**\*, kind, outcome, values, expected, limitations, power, evidence_note, legacy | What a run (or an observation, or a citation) found: values, outcome, power. |
| `artifact` | A | **sha256**\*, path, size, format | Exact bytes, by sha256 — data, code, a model, a figure. |
| `source` | S | **citation**\*, doi, url, passage, retrieved, says | Outside literature or data: citation, DOI, the passage that says it. |
| `review` | RV | **verdict**\*, **method**\*, **notes**\*, official | A verdict on one version of a claim, result, run, experiment or hypothesis. |
| `decision` | D | **choice**\*, alternatives, **reasons**\*, revisit_if, meeting | A choice made on the evidence; flagged when what it was based on changes. |
| `task` | T | **kanban_id**\*, title | A unit of work in your tracker, linked to what it works on. |

| relation | from | to | meaning |
|---|---|---|---|
| `part_of` | any but investigation | investigation, question | belongs to an investigation or question |
| `answers` | claim, hypothesis | question | offers an answer to a question |
| `alternative_to` | hypothesis | hypothesis | competes with another hypothesis |
| `tests` | experiment | claim, hypothesis | an experiment tests a hypothesis or claim (data.expected: what it should show if true) |
| `executes` | run | experiment | a run carries out an experiment |
| `produced` | run | artifact, result | a run produced a result or artifact |
| `uses` | run | artifact | a run used an artifact (data.role: data / code / model / config) |
| `derived_from` | artifact, claim, result | artifact, result, run, source | computed or taken from |
| `supports` | claim, result, source | claim, hypothesis | evidence for (why required) |
| `challenges` | claim, result, source | claim, hypothesis | evidence against (why required) |
| `requires` | claim, hypothesis | claim | rests on another claim as a premise |
| `replicates` | run | run | a run repeats another (data.differs: same_code / new_seed / new_impl / new_data / new_env) |
| `reviews` | review | claim, experiment, hypothesis, result, run | a review of a node (written by review()) |
| `supersedes` | any but artifact, review, investigation | the same type | replaces an older node of the same type |
| `corrects` | claim, decision, result | the same type | fixes an error in a node of the same type |
| `motivated_by` | experiment, hypothesis, question | any | prompted by |
| `cites` | claim, experiment, hypothesis, result | source | cites a source |
| `based_on` | decision | claim, hypothesis, result | a decision rests on this evidence (pinned to its version) |
| `works_on` | task | any but task, artifact, review | a task works on a node |
| `blocked_by` | task | task | a task waits on another task |

Field kinds and lengths: `hypgraph schema --json` (or `/schema/hypgraph-1.json` on the site). A claim's
`measurements` are `{name, value | k & n | lo & hi, result: <result id>, key: <field of that result's values>}`.

Verdicts: positive `checked`, `pass`, `reproduced`, `replicated`, `separate_implementation`, `generalizes`; negative
`fail`, `not_reproduced`, `not_replicated`, `does_not_generalize`; and `objection`, `resolved`, `inconclusive`,
`comment`.

## 3. Canonical JSON and the event chain

`canon(x)` is JSON with keys sorted at every level, separators `,` and `:` with no spaces, and non-ASCII characters
written as-is (UTF-8). In Python: `json.dumps(x, sort_keys=True, ensure_ascii=False, separators=(",", ":"))`.

Every write appends one or more events. An event's hash is

```
hash = sha256_hex( canon({"at", "actor", "kind", "ref", "payload", "prev"}) )
```

where `prev` is the previous event's hash (64 zeros for the first). Kinds and payloads:

| kind | ref | payload |
|---|---|---|
| `create` | the new node | `{type, code, inv, v: 1, body_sha}`; `body_sha` = sha256 of the version's stored body string |
| `revise` | the node | `{v, reason, body_sha}` |
| `review` | the reviewed node | `{review: <review node id>, verdict, on_v, official, body_sha}` |
| `link` | the edge's source | `{edge, rel, dst, src_v, dst_v, data_sha}`; `data_sha` = sha256 of the stored edge data string |
| `retract` | the edge's source | `{edge}` |
| `withdraw` | the node | `{why}` |
| `lease_take` / `lease_release` | the node | `{task, expires}` |

Any event may carry `task` in its payload: the unit of work that wrote it.

**Verifying** a record means recomputing every hash in order and checking each `prev`. Then check that every stored
version body and edge matches the `body_sha` / `data_sha` of the event that wrote it, and that no row exists without
its event.

## 4. Bundles — `hypgraph/1-bundle`

A portable record. Every event is carried as the **exact string that was hashed** (`body`), and every version body
and edge `data` as the exact stored string. A verifier therefore never has to reproduce canonical JSON: it hashes
strings and compares.

```json
{"format": "hypgraph/1-bundle", "generator": "hypgraph 0.1.0", "exported_at": "…",
 "complete": true, "redacted_events": 0, "scope": {"inv": "", "title": "whole graph"},
 "policy": {"reviewers": [], "instrument": "lab", "operator": "operator", "importer": "importer", "system": "system"},
 "head": "<hash of the last event>",
 "events": [{"seq": 1, "hash": "…", "body": "{\"actor\":…,\"at\":…,\"kind\":…,\"payload\":{…},\"prev\":…,\"ref\":…}"}],
 "nodes": [{"id": "…", "type": "…", "code": "…", "inv": "…", "created_at": "…", "created_by": "…"}],
 "versions": [{"node": "…", "v": 1, "at": "…", "by": "…", "reason": "", "body": "<stored canonical string>"}],
 "edges": [{"id": 1, "src": "…", "src_v": 1, "rel": "…", "dst": "…", "dst_v": 1, "data": "<stored string>", "…": "…"}],
 "withdrawals": [], "retractions": [], "leases": [],
 "derived": {"…": "standing at export time, for viewers; never trusted by a verifier"}}
```

A **scoped** bundle (one investigation out of a shared record) replaces events outside it with
`{"seq", "hash", "prev", "redacted": true}`. The chain still links, but the content of those events can't be
checked, so a change hidden among them would not show. Verifiers must report `complete: false`. To publish a study,
keep it in a record of its own.

**Anchoring.** A bundle proves only its own consistency. To prove it wasn't rebuilt from scratch, publish its `head`
hash somewhere independent at the time (a paper, a preregistration, a repository tag). A later bundle whose chain
passes through that hash can't have rewritten anything before it.

## 5. Derived standing (normative)

Implementations must derive these, never store them:

- **lifecycle**: `withdrawn` if withdrawn; `superseded` if a live node of the same type `supersedes` / `corrects`
  it; an investigation's own `state`; else `active`.
- **review**: computed over reviews by the *board* (the policy's reviewers ∪ the investigation's `reviewers` ∪ the
  operator and importer), excluding comments. An `objection` stays open until its author records `resolved`. The
  operator, the importer and the investigation's reviewers may resolve anyone's. Then, on the current version: any
  negative verdict or open objection → `contested`; else any positive verdict → `checked`; else a positive verdict
  only on an older version → `needs_revalidation`; else `unchecked`.
- **fallen**: withdrawn; or a contested claim / result / hypothesis; or a run whose state is failed / timeout /
  cancelled / interrupted; or a result whose outcome is failed. Superseded is not fallen.
- **at_risk**: the fallen nodes reachable upstream through `requires`, `derived_from`, `based_on` and the run that
  `produced` it.
- **independent lines**: live supporters, grouped when their roots overlap. Roots are producing runs, the data /
  model artifacts those runs `use`, and sources. Supporters with no provenance at all form one group between them.
- **evidence**: the best live supporter's profile, ranked `unverified < agent_reported < lab_recorded <
  project_rerun < separate_implementation < new_data < external`.
  - A source is external.
  - A result produced by a `kind=lab` run that the instrument filed is lab_recorded.
  - A replication edge on the run raises the profile according to its `differs`.
  - A result of `kind=cited` is external only if it `cites` a source node.
- **basis_changed** (decisions): a `based_on` edge whose target's version has moved past the pinned `dst_v`.

## 6. Write rules (normative for writers)

- `supports` / `challenges` need a `why` of at least 10 characters. `tests` needs `data.expected`. `replicates`
  needs `data.differs`. `uses` needs `data.role`.
- Only the instrument files a `kind=lab` run, and only the instrument records what that run `produced`.
- Claims must pass the checks in §7, unless written by the operator or importer, or in an investigation with
  `strict_claims: false`.
- Nobody officially reviews their own node.
- Writes into an `archived` or `published` investigation are refused (reserved authors excepted).
- Only the importer may set a write's time. Everyone else's comes from the writer's clock.

## 7. Claim checks

A claim is checked before it enters the record. Each failed rule is reported with a stable code, a message that does
the arithmetic, a suggested fix, and the words that triggered it. Checks are skipped for the operator and importer,
and in an investigation with `strict_claims: false`. Leads and conventions skip rules 7–9.

**Arithmetic.** For a count of k in n trials, the 95% interval is the Wilson score interval. At k = 0 (or k = n) it is
the exact one-sided bound 1 − 0.05^(1/n), the "rule of three" (≈ 3/n). "Never, in n trials" means at most that rate,
and never zero. Two counts are compared with Newcombe's hybrid score interval and a pooled two-proportion z-test. The
smallest detectable difference uses 80% power at two-sided α = 0.05.

| # | Code | Refused when |
|---|---|---|
| 1 | `SCOPE_MISSING` | a finding or exclusion has a scope shorter than 10 characters |
| 2 | `EVIDENCE_MISSING` | a finding, exclusion or inconclusive claim has no supporting node |
| 3 | `MEASUREMENT_MALFORMED` / `MEASUREMENT_UNKNOWN_FIELD` / `MEASUREMENT_MISMATCH` | a measurement doesn't name a result and a key present in its `values`, or states a `value` / `k` / `n` different from the result's at the precision written (a fraction ≤ 1 may be written as a percentage) |
| 4 | `UNBOUND_NUMBER` | a number in the statement (digits, or the words two to twenty; digits in quotes are names) is not one of: a bound measurement's numbers; for a count, its rate, complement or n − k; for any two measurements, their difference, ratios, relative change or sum; the scope's numbers; the investigation's `constants`; or the conventions 95 / 99 / 90 / 80 / 0.05 / 0.01 when the statement speaks of intervals, bounds, confidence, power or significance. *Statistical* quantities (a rate's 95% bounds; for two counts the difference interval, p-value and detectable difference) count only when written to at least one decimal place. |
| 5 | `ABSOLUTE_WITHOUT_COUNT` | an absolute word (never, always, all, every, none, impossible, cannot, proves, certainly, guaranteed, eliminates, entirely, completely, universally, consistently, perfect, solves, zero, 100%, …) with no bound count where k is 0 or n |
| 5a | `ABSOLUTE_UNRELATED_COUNT` | the counts with k ∈ {0, n} share no content word with the statement in their name or key |
| 5b | `ABSOLUTE_UNDERPOWERED` | the 95% bound on the opposite rate is above 5% and the statement doesn't say n ("never leaks" rather than "no leaks in 50 prompts" — a statement that gives its n is scoped to what was seen, and accepted). The message gives the honest wording and the trials needed for a 1-in-1,000 bound. |
| 5c | `ABSOLUTE_HIDES_DENOMINATOR` | the count is enough, but n appears in neither the statement nor the scope |
| 6 | `CONVENTION_HEDGED` | a `convention` hedges (could, might, suggests, consistent with, …) |
| 7 | `COMPARATIVE_WITHOUT_COMPARISON` | a comparative (better, beats, outperforms, higher than, improves, exceeds, …) with fewer than two measured sides, no bound p-value or interval, and no supporting claim that binds two sides |
| 8 | `SIGNIFICANCE_WITHOUT_TEST` / `SIGNIFICANCE_NOT_SHOWN` | "significantly" / "statistically" with no bound p-value and fewer than two counts, or when the bound p-value, or the test the record runs on the first two counts, is not below 0.05 |
| 9 | `CAUSAL_WITHOUT_INTERVENTION` | a causal word (causes, leads to, results in, drives, due to, because of, responsible for, …) when no supporting result was produced by a run that `executes` an experiment |
| 10 | `EXCLUSION_WITHOUT_POWER` | `kind: exclusion`, or wording that says an effect is absent (no effect, no difference, makes no difference, does not affect, rules out, ineffective, …) in a finding, without a supporting result with `power: demonstrated` or one produced by a run of an experiment with a `power_check`. With two counts, the message gives the smallest detectable difference. |
| 11 | `UNCORRECTED_EFFECT` | a finding asserts an effect (changes, lowers, differs, affects, significant, …) on an outcome, while a live result in the investigation holds that outcome's corrected p-value (a field named with holm / bonferroni / fdr / adjusted / corrected …) at or above 0.05, or a count of 0 outcomes surviving correction (`n_holm_sig`), and the effect word is neither qualified within 20 words as uncorrected (uncorrected, unadjusted, nominally, without correction, …) nor names the correction with a corrected value bound as a measurement. A family-wide value (`min_adjusted_p`) applies when the claim binds a nominal p < 0.05. Thresholds (`bonferroni_alpha_threshold`) are not evidence. Honest forms: bind the corrected p and say "not significant after correction", or file `kind: lead`. |

**Exposure.** A claim may set `exposure` (how many uses, users or units it will be applied to) and `exposure_unit`.
Absolute refusals then state how many failures the bound leaves unruled out at that scale. An accepted claim's
standing carries `bounds` (per count: k, n, rate, lo, hi and, with exposure, `unruled_out`), its sentence reads
"'never' = at most 0.1% (0 of 3,000, 95%), up to 998 of 1,000,000 not ruled out", and a "significantly" claim carries
`test` (the difference, its interval and p).

**Blast radius.** Withdrawing a node, or a verdict that makes it fall, returns `blast_radius`: every node resting on it
by type, with claims and decisions named and, if a spend meter is connected, the cost of the work behind them.

## 8. The refusal log

A refused claim never enters the record, so its trace lives in a separate append-only table, `refusal_log`, with
its own SHA-256 chain over `canon({at, kind, author, inv, node, op, statement, codes, detail, ref, prev})`. The
record's own chain and `verify()` are unaffected.

- `kind: refused`: the author, the investigation, the statement (≤ 1,500 characters; a result's summary), the
  sorted codes, and the problems (code, message, fix) it was refused with; `detail` holds the whole body, the
  support it had and the node type (`claim`, `result`, or a typed node). `op` is `create` or `revise`; `node` is
  set for a revision.
- A refusal on *shape* — a field the type doesn't have (`SHAPE_UNKNOWN_FIELD`), a value outside an enum
  (`SHAPE_NOT_AN_OPTION`), a missing, too long or too short field, a wrong type, or a link the relation grammar
  refuses (`LINK_NOT_ALLOWED`, `LINK_UNKNOWN_RELATION`, `LINK_NO_NODE`) — is logged the same way with
  `detail.type` `shape` or `link`. Its message carries the fix: where the field goes (`code` on a result belongs to
  the run; an experiment's `expected` goes on its `tests` link) or what each option means. The report counts these
  apart from overclaims and the replay skips them.
- `kind: fixed`: a later claim, result or revision by the same author in the same investigation, accepted within
  24 hours, that says the same thing. "The same" means the same node for a revision; otherwise a Jaccard overlap
  ≥ 0.3 of the statements' content words, or, for a result, at least half of the refused result's value keys carried
  again. `ref` is the refusal it fixes.

A report aggregates per author (refused, fixed, open, codes) and per rule. A replay runs every logged refusal through
the checker as it is now — claims through the claim and profile checks, results through the value and profile result
checks as their author — and says for each whether it would be refused the same way, differently, or accepted;
`RESULT_RESTATES` and typed-node refusals depend on the record's state at the time and are counted as skipped. A
change to a rule is judged on that replay over the real corpus before it ships.

## 9. Checking a write-up against the record

A checker reads markdown sentence by sentence and checks it against the record. Code blocks, inline code, URLs, link
targets and HTML comments are skipped, except a fenced block whose info string is `answers`: that is the report's
machine-read answer (a JSON object, keyed by question code or flat), and every number or true / false in it is checked
against the claims. Quoted passages and negated words ("cannot be proven") are not treated as
the writer's assertion. Codes are matched within the investigation being reported on.

| level | code | when |
|---|---|---|
| error | `REPORT_CITES_WITHDRAWN` | a sentence cites a withdrawn node and doesn't say so (withdrawn, retracted, failed, superseded, earlier, …) |
| error | `REPORT_OVERSTATES_STANDING` | settled language (confirmed, established, shown, proven, holds, …) about a claim or hypothesis that is unchecked, stale, contested or at risk, or a result that is contested or at risk |
| error | `REPORT_UNKNOWN_CODE` | an `INV` / `RUN` / `CL` / `RS` / `RV` code the investigation doesn't have |
| error | `REPORT_ABSOLUTE_UNBACKED` | never / always / impossible / guaranteed / eliminates / proven / 100% asserted, not in an instruction, with no cited claim carrying a count with k ∈ {0, n} |
| error | `REPORT_ABSENCE_UNBACKED` | "no effect" / "rules out" / "doesn't matter" without citing a claim filed as `exclusion` or `inconclusive` |
| error | `REPORT_SIGNIFICANCE_UNBACKED` | "significantly" without a p-value or interval in the sentence and without citing a node that carries a test (a negated "not significant" is a warning) |
| error | `REPORT_ANSWER_STALE` | a value in the `answers` block that only stale, superseded or withdrawn claims (or stale results) on that question give, or that a current claim binds to a different value under the same field while an old one binds it to this; or a question whose every claim is old |
| error | `REPORT_ANSWER_UNBACKED` | a value in the `answers` block that no current claim on the question states or binds, at the precision the answer gives it and with its sign (a count k of n, bound or written as "k of n", backs its rate); or a question answered with no claim at all. A number a claim names only as a figure that no longer holds ("the earlier count of 789 is superseded") doesn't back it. URLs, paths and hashes in the block are provenance and aren't checked. |
| error | `REPORT_ANSWERS_UNREADABLE` | the `answers` block isn't valid JSON |
| warning | `REPORT_UNSOURCED_NUMBER` | a number not contained in or implied by the investigation's results, live claims' measurements, statements and scopes, the investigation's scope and constants, or experiment and run settings. Integers ≤ 12, years, dates, times and 7-digit+ ids are skipped. Statistical quantities need one decimal. |
| warning | `REPORT_OMITS_DISPUTE` | cites a contested or at-risk node without saying so |
| warning | `REPORT_CITES_SUPERSEDED` | cites a superseded node without saying so |
| warning | `REPORT_CAUSAL_UNCITED` | causal language with no node cited |
| note | `REPORT_BOUND` | an absolute backed by a cited count: what the count supports |

Calibrated on 24 real write-ups checked against the live record they report on.

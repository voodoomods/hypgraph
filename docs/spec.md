# The HypGraph record format — `hypgraph/1`

Status: draft 1 (HypGraph 0.1). Licence: CC BY 4.0. This page is enough to write another implementation, a
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
| `claim` | CL | **statement**\*, scope, limitations, kind, measurements, evidence_note, legacy | What you assert is known, with its scope and its numbers bound to results. |
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

1. `finding` and `exclusion` need a scope of at least 10 characters.
2. `finding`, `exclusion` and `inconclusive` need at least one supporting node.
3. Each measurement must name a result and a key present in its `values`. Its `value` / `k` / `n` must equal the
   result's at the precision written; a fraction ≤ 1 may be written as a percentage.
4. Every number in the statement (digits, and the words two to twenty), except digits in quotes, must match a bound
   measurement's numbers, a number in the scope, or one of the investigation's `constants`.
5. Absolute words (never, always, all, every, none, impossible, cannot, proves, proven, certainly, guaranteed) need a
   measurement with `n` and `k ∈ {0, n}`.
6. An `exclusion` needs a supporting result with `power: demonstrated`, or one produced by a run of an experiment
   with a `power_check`.
7. A `convention` may not hedge (could, might, suggests, consistent with, …).

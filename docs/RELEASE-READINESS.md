# Release readiness: the public developer preview

*Written 2026-10-31 against 0.7.11 (`87b4c14`) and three pull requests: #59 (trust boundary), #60 (verification),
#61 (docs and release engineering). Everything marked as tested was run; the commands are in each PR. Nothing here
was taken from a changelog without being checked against the code.*

> **Superseded in part (2026-10-31, later the same day).** A second audit found that verification checked rows
> against events in one direction only: a bundle or graph file with a withdrawal, a version, an edge or a whole
> table removed still verified, as did changed authors, times, link ends and reasons, and edited derived views. That
> was a confirmed integrity defect, so the GO below didn't hold for 0.7.12. The fix (exhaustive row checks in the
> Python, SQLite and browser verifiers, events that hash every row field, derived views checked against the rows,
> standing reported as not covered) is in the pull request that adds `tests/test_verify_complete.py`, and ships as
> 0.7.13. The recommendation stands again once that is merged with green CI and released.
>
> **Where that stands.** #66 is merged with green CI (17 of 17 checks); on main the suite is 386 passed, and
> hypswarm, hypmesh and hypdmz pass on it. Released as 0.7.13. The required-checks setting (condition 3 below) is
> still open, for the operator.

> **Re-audit of 0.7.13 (2026-10-31).** Confirmed: the deletion and field defects are closed. Two gaps remained, both
> reproduced and both fixed for 0.7.14: the verifier took the importer from the bundle's own (unhashed) policy, which
> let an edited legacy bundle re-attribute a historical writer's nodes against the published head; and reports,
> stages and work-order status were shown beside the verified badge without saying they are as exported. Sequence
> numbers must now run 1 to n. Tests: `tests/test_verify_trust.py`, `dev/ui_smoke.py`. The required-checks setting is
> still open, for the operator.
>
> **Where that stands.** #68 is merged with green CI (17 of 17 checks); the suite is 399 passed, and hypswarm and
> hypmesh pass on it. Released as 0.7.14.

> **Re-audit of 0.7.14 (2026-10-31).** Confirmed and fixed for 0.7.15: derived facts were compared only when present,
> so deleting a withdrawn claim's `state.lifecycle` (or its `state`) still verified as complete and the explorer showed
> the claim as active; an emptied investigation list, nodes without a title, author or code, and links without an end
> verified too; an event body that wasn't JSON raised instead of failing. Every such fact must now be present, the
> lifecycle is re-derived from the rows, malformed bundles fail cleanly, and the explorer shows a missing lifecycle as
> unknown. Tests: `tests/test_verify_views.py`. The required checks and the repository's About metadata are still the
> operator's.
>
> **Where that stands.** #70 is merged with green CI (17 of 17 checks); the suite is 406 passed, and hypswarm and
> hypmesh pass on it. Released as 0.7.15.

> **Re-audit of 0.7.15 (2026-10-31).** Confirmed and fixed for 0.7.16: the scope isn't hashed and wasn't checked, so a
> claim, question, result or hypothesis named as the scope showed alone, the rest of the record hidden, and the bundle
> verified against the published head; a full export of two investigations relabelled as one did the same. The scope
> must now name an investigation, the bundle hold only its nodes, and only a scoped bundle redact; the redaction
> warning says the bundle's word that redacted events lie outside can't be checked. Tests: `tests/test_verify_scope.py`.
> The required checks and the repository's About metadata are still the operator's.
>
> **Where that stands.** #72 is merged with green CI (17 of 17 checks); the suite is 412 passed, and hypswarm and
> hypmesh pass on it. Released as 0.7.16.

> **Pre-launch audit of 0.7.16 (2026-10-31).** Confirmed and fixed for 0.7.17: the verifier accepted a lifecycle under
> either the current rule or 0.3's, so the oldest node of a chain of two or more replacements could be shown active
> and the bundle verified with `views: "checked"`, chain, rows and head untouched; a `generator` set to 0.3 (not
> covered by the chain) also turned `--standing` into "not checked". A lifecycle is now checked against the current
> rule only; one that matches only 0.3's verifies with `views: "historical"` and a warning naming each node, in
> Python and the browser alike, whatever the generator says. Tests: `tests/test_verify_lifecycle.py` (five fail on
> the 0.7.16 code). The required checks are now all 17 CI jobs, and the repository has its homepage and topics.
>
> **Where that stands.** #75 is merged with green CI (17 of 17 checks); from the 0.7.17 wheel in a fresh venv the
> suite is 424 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Released as 0.7.17.

> **Re-audit of 0.7.17 (2026-10-31).** Confirmed and fixed for 0.7.18: a bundle naming a `scope.inv` (not covered by
> the chain) could show any non-withdrawn node, an active claim or the investigation itself, as superseded and verify
> against its published head with `views: "checked"` and coverage complete; the published Broad Street bundle, which
> has no redacted events, was enough. The scoped allowance now needs redacted events and a type a `supersedes` /
> `corrects` link can reach (never an investigation or a review), and even then the views are `"unconfirmed"`, with
> each node named, in Python and the browser alike. The verify page and the Explorer header now say *views not
> checked* for `historical` and `unconfirmed` views, and the spec no longer says a verifier accepts either rule.
> Tests: `tests/test_verify_scoped_views.py`.
>
> **Where that stands.** #77 is merged with green CI (17 of 17 checks); from the 0.7.18 wheel in a fresh venv the
> suite is 431 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Released as 0.7.18.

> **Linked records (2026-10-31), for 0.7.19.** The Explorer now draws the records an investigation pins beside it,
> and the records those pin in turn (three links, twelve records at most by default), each in its own box, with every
> pin drawn to the node it names. Nothing is merged: each record is read as its own bundle with its chain re-verified,
> and each pin is checked against the version it names by hashing the exact stored body; `checkPin` is held to
> `verify_reference`'s verdicts. Another site is read only when the viewer asks. The site has a worked example of three
> linked records in five languages. Tests: `tests/test_linked_records.py`; `dev/ui_smoke.py` 149 of 149 pages.
>
> **Where that stands.** #79 is merged with green CI (17 of 17 checks); from the 0.7.19 wheel in a fresh venv the
> suite is 436 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Released as 0.7.19.

> **Claims the record can show false (2026-11-01), for 0.7.20.** A claim a bound count contradicts is refused as
> `COUNT_CONTRADICTS` (including an extreme no answer reaches), a claim citing a source that asserts the opposite or
> doubts it as `SOURCE_CONTRADICTS`, and `Graph.conduct()` tells an author who corrected from one who said it again.
> Tests: `tests/test_contradictions.py`.
>
> **Where that stands.** #81 is merged with green CI (17 of 17 checks); from the 0.7.20 wheel in a fresh venv the
> suite is 450 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Released as 0.7.20.

> **Audit of 0.7.20 (2026-11-01), fixed for 0.7.21.** An independent audit found three false verdicts and a design
> point, each reproduced on the 0.7.20 wheel: a zero count at another figure cancelled the count that refutes a claim
> (HG-020-01), a count at another figure refuted a true extreme (HG-020-02), a "not" anywhere in a source sentence hid
> what it asserts (HG-020-03), and conduct counted a claim that goes against its own citation as shown false and read
> intent into it (HG-020-04). Counts now bear only at the figure the claim names, a negation reaches to the end of its
> clause, and conduct reports `by_count` / `by_source` and describes behaviour, not intent. Each case is a regression
> test written to fail on 0.7.20. Replaying 360 recorded adversarial trials gives the same standings as 0.7.20.
>
> **Where that stands.** #83 is merged with green CI (17 of 17 checks); from the 0.7.21 wheel in a fresh venv the
> suite is 466 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Released as 0.7.21.

> **Audit of 0.7.21 (2026-11-01), fixed for 0.7.22.** A second independent audit found three ways a false claim still
> got in, each reproduced on the 0.7.21 wheel, and a design point: renaming the count of 2 beyond 93 "worth more than
> 140" moved it off "the highest value is 93" (HG-021-01); a true "nothing worth more than 140 fits" beside that false
> extreme ended the check (HG-021-02); and "the recorded weights are in pounds", citing the note that they are in
> kilograms, was never compared with it because it denied nothing (HG-021-03). `shown_false` was open to being read as
> a lying rate (HG-021-04). A result can now state a count's figure, and a label can only widen what a count refutes;
> every absolute and extreme in a claim is checked; units of one kind rule each other out against a cited source; the
> conduct docstring says `shown_false` is not a lying rate. Each case is a regression test written to fail on 0.7.21.
> Replaying 360 recorded adversarial trials (1,900 entries): 5 entries change, all the units liar's; no honest or
> mistaken party's entry changes; two more parties still saying the false unit are named and no one new is misnamed.
>
> **Where that stands.** #85 is merged with green CI (17 of 17 checks); from the 0.7.22 wheel in a fresh venv the
> suite is 482 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. The audit asks for a fresh
> independent audit before anyone claims 0.7.22 resists these attack classes. Released as 0.7.22.

> **Audit of 0.7.22 (2026-11-01), fixed for 0.7.23.** A third independent audit found five cases, each reproduced on
> the 0.7.22 wheel. Two let a count stand for its opposite: a count of routes longer than 26 km refused the true "the
> shortest route is 26 km" (HG-022-01), and none shorter than 26 backed "nothing / no route is longer than 26 km"
> (HG-022-02). One let a unit claim in: "recorded parcel weights use pounds" stated no copula (HG-022-03). Two made
> false accusations: "passenger weights" was matched with "shipping weights" on a shared word (HG-022-04), and a
> quantity converted to another unit was read as a unit of record (HG-022-05). Comparisons now carry a direction, and
> a result can state its comparison (`op`); "no X is longer than…" opening a clause is an absolute; a short fixed list
> of verbs states a unit; units are compared only between subjects with the same head and compatible modifiers; a unit
> after a number is a quantity. Each case is a regression test written to fail on 0.7.22. Replaying the 1,900
> recorded adversarial entries names exactly the same parties as 0.7.22; one repeated false unit claim is no longer
> refused, because 0.7.22 had refused it on a shared word and a quantity, and its author is still named.
>
> **Where that stands.** #87 is merged with green CI (17 of 17 checks); from the 0.7.23 wheel in a fresh venv the
> suite is 504 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Which thing a subject names and
> which unit a record uses are still read from words, not typed; a fresh independent audit should precede any claim
> that 0.7.23 resists these attack classes. Released as 0.7.23.

> **Audit of 0.7.23 (2026-11-01), fixed for 0.7.24.** A fourth independent audit, a code review without running the
> wheel, named five candidate defects; each reproduced on the PyPI 0.7.23 wheel, plus two of the same kind. A count of
> none or all backed any absolute, so "nothing is longer than 26 km" went in with all routes longer and "every route
> is longer" with none (HG-023-01). Comparisons lost their boundary, so a count at least 26 refuted the true "no route
> is longer than 26" and "at least" was read as pointing down (HG-023-02). Two extremes in one sentence were pooled
> and a true one refused (HG-023-03). "Weights of cargo" and "weights of passengers" read as one thing (HG-023-04),
> and "not in pounds but in kilograms" lost its kilograms (HG-023-05). A claim now needs the extreme its quantifier
> names; comparisons keep their boundary across six operators; each extreme is checked on its own; the object of "of"
> / "for" says which thing, and subjects that each say something the other doesn't are left apart, unresolved; a
> contrast keeps its unit. Each case is a regression test written to fail on 0.7.23. Replaying the 1,900 recorded
> adversarial entries changes nothing against 0.7.23 (a first version over-read "a count of every route" and named
> one honest party wrongly; caught by the replay, fixed and tested), but none of those entries tries these cases.
>
> **Where that stands.** #89 is merged with green CI (17 of 17 checks); from the 0.7.24 wheel in a fresh venv the
> suite is 549 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. The audit recommends a typed
> claim layer (subject, property, comparator, threshold, unit, quantifier) so that strong verdicts rest on typed fields
> rather than prose; that is not built. Released as 0.7.24.

> **Audit of 0.7.24 (2026-11-01), fixed for 0.7.25.** A fifth independent audit named four candidate defects; each
> reproduced on the PyPI 0.7.24 wheel, plus four of the same kind. A count with no comparison of its own ("3 of 3
> routes processed") backed "nothing is longer than 26 km" and "every route is longer" (HG-024-01). A count of cargo
> routes backed a claim about passenger routes, and about every route, because they shared the word "route"
> (HG-024-02). "And" ended a clause, so a true "no route is shorter than 20 km and longer than 30 km" was refused,
> and "every route is longer than 10 km and shorter than 30 km" went in with its second half unread, even beside the
> count that refutes it (HG-024-03). A `>=` count named "longer than 26 km" went in (HG-024-04). A count that states no
> comparison no longer bears on one; a count backs only a claim whose kinds it names, and kinds named apart are
> unresolved; a comparison joined by "and" / "or" stays in its clause and is read as both or either; a name must say
> the boundary its count used. Each case is a regression test written to fail on 0.7.24. Replaying the 1,900 recorded
> adversarial entries changes 7: one honest correction is no longer refused, and one correction that got in only
> because an unrelated zero count backed it (the HG-024-01 case) is now refused; none of the entries tries these cases.
>
> **Where that stands.** #91 is merged with green CI (17 of 17 checks); from the 0.7.25 wheel in a fresh venv the
> suite is 574 passed, and hypswarm (118 passed) and hypmesh (37 passed) pass on it. Kinds are read from a plural noun
> and the words before it, a heuristic; the typed claim layer the audits recommend is not built. Released as 0.7.25.

> **Audit of 0.7.25 (2026-11-01), fixed for 0.7.26.** A sixth independent audit named three defects; each reproduced on
> the PyPI 0.7.25 wheel. Kinds were read only before a plural, so none of 3 "cargo route longer than 26 km" backed "no
> passenger route is longer than 26 km" while the passenger count was 1 of 3 (HG-025-01). A count the lab keyed
> `route_speed_above_26`, named "routes longer than 26 km" by the claimant, backed a claim about length (HG-025-02). A
> clause joining comparisons with both "and" and "or" was checked part by part, so a true one drew
> `COUNT_CONTRADICTS` (HG-025-03). What a count names before its comparison is now read singular or plural; a name
> that compares along another axis than its key, or a key that counts a kind neither the name nor the statement says,
> is `MEASUREMENT_MISMATCH`; a mixed "and" / "or" clause is unresolved until the whole condition is counted. Each case
> is a regression test written to fail on 0.7.25. Replaying the 1,900 recorded adversarial entries changes none; the
> replay caught two over-reaches of a first draft (a value word, "selections worth more", read as the kind; a bound,
> "the limit is at most 49 kg", read as the subject), now tests too.
>
> **Where that stands.** #96 is merged with green CI (17 of 17 checks). Kinds and subjects are still read from the
> words around a comparison, a heuristic; the typed claim layer the audits recommend is not built. Released as 0.7.26.

## Recommendation: CONDITIONAL GO

HypGraph is ready for a public developer preview once #59, #60 and #61 are merged with green CI and released as one
version. The review found five defects at the trust boundary and two gaps in verification. Each is fixed in those
PRs, with a regression test that failed first. No confirmed security, integrity or correctness defect remains open.
The conditions are small, and the limitations below are documented where a user will meet them.

**Conditions**

1. Merge #59, then #60, then #61, each with green CI. They all touch the top of the changelog, so main gets merged
   into the next one in line.
2. Release them as one version through the usual release PR, tag and PyPI check. That release is the first to create
   a GitHub Release by itself.
3. Make the `ui`, `install` and `lint` jobs required checks in the `protect main` ruleset. Today only the 12 `test`
   jobs are required. This is a repository setting, so it's the operator's call.

**Where the conditions stand.** 1: #59, #60 and #61 are merged, each with green CI; on main after the merges the
suite is 343 passed. 2: released as 0.7.12. 3: open, for the operator.

## What was reviewed

The threat model is in [SECURITY.md](../SECURITY.md):
- **Trusted callers:** the Python API and the CLI. Whoever holds the file owns the record.
- **Untrusted callers:** agents at `hypgraph serve` and `hypgraph mcp`.
- **The host's job:** who can read the port or the file, who holds which token, and where a record's head is
  published.

Interfaces examined: the Python API, the CLI, the HTTP server (`server.py`), the MCP server (`mcp.py`), blind work
orders (`blind.py`, `coord.py`), and bundle export and verification (`bundle.py`, `store.py`).

## Findings

| # | Finding | Class | Status | Evidence |
|---|---|---|---|---|
| 1 | A page on another port of the same machine could write to a server without tokens: the cross-origin check compared host names only. | Confirmed defect | Fixed in #59 | `test_a_page_on_another_local_port_cannot_write` |
| 2 | A `*` token could write as a reviewer, and so review its own work officially. | Confirmed defect | Fixed in #59 | `test_a_wildcard_token_cannot_write_as_a_reviewer` |
| 3 | A worker could `rework` its own order with an easier `done_when`, meet it and `accept_work` it. Neither call checked the caller. | Confirmed defect | Fixed in #59 | `test_a_worker_cannot_accept_rework_or_settle_its_own_order`. HypSwarm (119) and HypMesh (37) pass unchanged. |
| 4 | A non-numeric `Content-Length` crashed the handler, and a negative one held a thread until the client hung up. | Confirmed defect | Fixed in #59 | `test_a_bad_content_length_is_refused` |
| 5 | A refused write's unread body reset the connection on Windows, so the client never saw its 403. | Confirmed defect | Fixed in #59 | Found as a flaky test; 15 of 15 runs passed after the fix |
| 6 | A sealed reader could see the chain head, a hash over sealed bodies. Not a practical oracle: testing a guess offline needs every other byte of those bodies, random ids included. | Security concern | Withheld in #59 | `test_enumeration_routes_carry_nothing_sealed` |
| 7 | Blind orders: no new oracle across graph operations on sealed nodes, the work-order lifecycle, 15 enumeration routes, 25 guesses in a row on one record, and 8 MCP tools. | Investigated | Holds | `tests/test_blind_oracles.py`, 36 tests. The oracles found earlier were fixed in 0.7.11. |
| 8 | Nothing checked a record against a published head. A rewritten-and-rehashed or truncated record verifies on its own. | Confirmed gap | Fixed in #60 (`verify --head`) | `tests/test_anchoring.py` |
| 9 | Clean install never ran the documented steps. The release job ran only the demo on the wheel, and never installed the sdist. | Release process | Fixed in #60 (`dev/e2e_install.py` in CI and in the release job) | Wheel with MCP 21/21; sdist 20/20 |
| 10 | SECURITY.md said "No authentication" after token-bound writes shipped, and didn't say that tokens protect writes but not reads. | Documentation | Fixed in #59 | — |
| 11 | No GitHub Releases for 24 tags. | Release process | Fixed in #61 for future tags | `dev/release_notes.py` |
| 12 | The review of 2026-10-24 and PLAN.md described an earlier state; the agent docs said "`overview()` first", which a blind checker is refused. | Documentation | Fixed in #61 | Each review finding re-run against 0.7.11 |
| 13 | No linter. | Release process | pyflakes rules in CI in #61; 6 findings fixed | — |
| 14 | The committed `site/assets/site-data.js` says 188 tests. | Documentation | Accepted | It's a generated file, and the Pages deploy regenerates it. The live site showed 310 of 310, built 2026-10-31 02:54Z. |

Checked and holding, with no change needed:
- reserved names need a token that names them;
- official self-review is refused through every interface;
- the HTTP write takes no time, attribution, id or code from the writer;
- the MCP seat can't start as a reserved name;
- only the lease holder releases a lease, and only a link's author, a reviewer or the operator retracts a link;
- the release job checks the tag against the version;
- PyPI publishing is trusted and carries a provenance attestation;
- every tool name in the agent docs exists on the MCP server, and every hypgraph.com page the README links answers.

## Verification report

| | Result |
|---|---|
| Full suite, each branch, Windows 11, Python 3.13 | #59: 338 passed · #60: 320 passed · #61: 315 passed. 0.7.11 had 315. |
| CI matrix | Ubuntu, macOS and Windows × Python 3.10–3.13 (12 jobs), plus the UI smoke test in Chrome. #60 adds `install` (Ubuntu, Windows) and #61 adds `lint`. All green on each PR's head: #59 13 of 13, #60 15 of 15, #61 14 of 14. |
| Clean install of the built wheel with the MCP extra | 21 of 21 documented steps |
| Clean install of the sdist | 20 of 20 |
| Clean install of `hypgraph==0.7.11` from PyPI | 19 of 20. The failing step is `verify --head`, which is new in #60. |
| Bundle verification | Passes on a demo export, in another process and directory with no graph file. Fails on an edited body, a swapped event, a changed node code, a create event forged as redacted, a swapped head, and (with `--head`) a rewritten-and-rehashed record or a truncated one. |
| Downstream | HypSwarm 119 passed, 6 skipped; HypMesh 37 passed, both against #59 |

## Accepted limitations

These are documented in SECURITY.md and docs/verification.md, where a user meets them.

- **Names aren't people.** The record can't tell that two author names are one agent. Review independence holds
  only as far as names are authenticated: named tokens, or one MCP seat per agent. A server with `--writable` and
  no tokens authenticates nobody.
- **Reads aren't authenticated.** `hypgraph serve` serves every `GET` to whoever can reach the port. Keep it on
  loopback, or behind a proxy that authenticates readers.
- **Blind orders need a host that seals.** The MCP seat and HypMesh seal; plain `hypgraph serve` and the Python API
  don't. Reads made before the order can't be undone. The leak check catches numbers quoted by accident, not a lead
  leaking on purpose. Timing isn't hidden.
- **A head is only as good as where it's published.** `verify --head` proves the record is the one that was
  published. Who published that head is for the signature, the paper or the tag to establish.
- **A single-number blind check is never marked as agreeing.** Results restate each other only when they carry two
  or more numbers, a guard against coincidence. A blind check of one count is recorded as written blind, but not as
  `agrees_blind`. It's documented in the changelog, not yet changed.

## Deferred until after launch

- **Comparative evaluation.** Does recording through HypGraph reduce unsupported claims in agents' final reports?
  The design: the same model, tools, tasks and budget, with and without the record, scored against criteria fixed
  in advance by a scorer that isn't HypGraph. The measures would be unsupported claims, wrong numbers, overstated
  certainty, honest claims wrongly refused, completion and cost. It needs a preregistration and a budget decision,
  and no result is claimed until it has run.
- **Coverage reporting.** The security-sensitive paths have targeted tests: the trust boundary, the blind oracles,
  anchoring, the bundle negatives. A coverage percentage would add little to that.
- **GitHub Releases for the 24 past tags.** `dev/release_notes.py` can write the notes for each; publishing them is
  the operator's decision.

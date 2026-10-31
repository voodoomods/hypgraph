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

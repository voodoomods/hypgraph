id="main">

Open source · Apache-2.0
Python · no dependencies MCP server · Agent Skill · HTTP API

A record that checks what your agents claim.

Agents write their hypotheses, runs, results and claims into HypGraph. It refuses a number no result
accounts for, without the counts and without a
powered search, and works out from the record
what has been shown and what is at risk.

Watch a run Get started
See what it refuses

Don't believe the hype. Test the hyp.

verifying…

What you can check

Facts, each with its source.

Each figure here is a claim in this page's own HypGraph record, bound to the measurement it came from
and re-measured another way by a reviewer before the page was built. Click a claim to open it in the record.

Tests
187 of 187
passing on this build; CI runs Linux, macOS and Windows

Runtime dependencies
0
The engine, CLI, HTTP server and UI use the standard library

Verify this record yourself
5 of 5 bundles

over the exact strings that were hashed, in your browser

Run the check

What it refuses

Overclaims don't get into the record.

These were written into a scratch record when this page was built. The engine refused each one with a
code and what to fix; the rewrite underneath, on the same evidence, was accepted.

This page has a record

We hold this page to the rules it describes.

The figures above are claims in a HypGraph record built with the page. The build's instrument measures
them, a reviewer re-measures each another way, and the page's text is checked against the record with
, so a figure the record doesn't hold can't reach the page. Open it in the app above
with This page's own record , or download
the bundle and verify it yourself.

One record, five workflows

Each discipline's method, enforced by the record.

A profile carries its discipline's stages, the gate out of each and what counts as done. The stage is
derived from the record, . Every row has a live example.

profile
a question passes through
the record refuses
done when

asked → conjectured → preregistered before any run → run → evidenced → claimed → reviewed

numbers no result accounts for; without the count; without the test; a check on stale evidence
each question settled
Watch

specified → implemented (a diff by hash) → verified by the instrument on that head → claimed → reviewed

without an instrument run, or on a superseded head; the diff's author as its reviewer
each requirement's claim rests on a passing run on the current head
Watch

asked → thesised → preregistered → backtested out of sample, after costs → claimed → risk-reviewed → positioned → monitored

a backtest without its costs; without both, or without the configurations tried; a position without size, stop and review date; any live order
questions settled; a position taken or declined
Watch

asked → sourced (the passage, retrieved, its kind) → claimed → checked

a claim with no source; a source without its passage
each claim cites a source and is checked
Watch

posed (the instance by hash) → modelled → configured → solved → verified → claimed → checked

an objective without feasibility; without a bound, or on a changed instance
a feasible, bounded incumbent, verified on the current instance
Watch

For the people who deploy agents

Wire it in where your agents already run.

One package. You set who reviews, which runner's records count as the instrument, and what work costs.

Agents, over MCP
Your agent gets the record's tools and the method as an Agent Skill.

Python
Roles as policy: reviewers, the instrument, reserved authors.

The UI and the JSON API
Read-only by default; follows a running swarm live.

Gate CI on the write-up
Lints a report against the record; exits non-zero on errors.

Hand over a verifiable bundle
Anyone can check it, in any language or the browser.

Run a swarm on it
HypSwarm schedules agents from the record's own work board.

Trust

What the record shows, and what it doesn't claim.

✓ It shows

that no event was changed after it was written: each write is hashed into a chain, and anyone can re-check it;

which numbers in a claim are bound to which result, and which run produced it;

who checked what, against which version, and whether that version is still current;

what falls if a premise is withdrawn.

— It doesn't claim

that a claim is true. It checks what was written against what was recorded;

to make a model reason better. It keeps a model's overclaims out of the record;

anything about telemetry carried in a bundle: that sits outside the hash chain;

to check events a scoped bundle redacts. Verification says when a bundle is scoped.

It runs where you run it: a local file, no account, no network calls of its own.
Releases are published to PyPI from GitHub Actions by trusted publishing.

<!-- the homepage's text as `hypgraph check` read it, figures filled in from the page's record (dev/site_record.py) -->

id="main">

v0.6.0 Open source · Apache-2.0
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

Two ways in

For the agent, and for the people who deploy it.

For agents

Connect your agent

One line of MCP, or the Agent Skill. Claims are checked as they're written, an agent's review of its own work
doesn't count, and each refusal says what to fix. Machine-readable: , .

The agent guide

For engineers & scientists

Wire it into your stack

One package with no runtime dependencies. You set who reviews, which runner's
records count as the instrument, and what work costs. Plus the JSON API, the UI and verifiable bundles for CI.

The engineering guide

What you can check

Facts, each with its source.

Each figure here is a claim in this page's own HypGraph record, bound to the measurement it came from
and re-measured another way by a reviewer before the page was built. Click a claim to open it in the record.

Tests
188 of 188
passing on this build; CI runs Linux, macOS and Windows

Runtime dependencies
0
The engine, CLI, HTTP server and UI use the standard library

Example records verify
5 of 5 bundles

over the exact strings that were hashed — run it here, in your browser

Run the check

What it refuses

Overclaims don't get into the record.

These were written into a scratch record when this page was built. The engine refused each one with a
code and what to fix; the rewrite underneath, on the same evidence, was accepted.

Eight rules

Each rule is a mistake that was really made.

HypGraph came out of a team of AI agents doing long investigations, and the errors they made despite
instructions not to. Each became a rule the record enforces when work is written, not advice it hopes is followed.

Standing is derived
No field says . Review, risk,
support and evidence strength are computed from the record when it is read.

Append-only
Hash-chained with . Corrections are new versions;
withdrawals stay on record. catches an edit.

Reviews pin versions
Revise a checked claim and its check goes stale. A decision
based on the old version is flagged to revisit.

Claims carry numbers
A claim's numbers are bound to result fields. A number with
no source is refused — the commonest way summaries go wrong.

Independence is counted
Three results from one run are one line of evidence, not
three. Lines that share data or a source merge.

Exclusions need power
only after a search was
shown to find a planted answer. Otherwise it's inconclusive.

Authors don't review themselves
Only named reviewers' verdicts count, and not on
their own work. Others' are kept as comments.

Instruments speak for themselves
Only the lab runner files a lab-recorded run. A
run you describe is labelled as your report.

The arithmetic of

0 failures in 50 tests still leaves
58,155 across a million uses.

An agent that sees none in its tests writes . The record
refuses that sentence and asks for the counts, then states what they leave open at the scale you deploy.

The arithmetic, worked through

58,155

failures not ruled out across 1,000,000 uses, at 95 % confidence, from
0 in 50 tests.

One record, five workflows

Each discipline's method, enforced by the record.

A profile carries its discipline's stages, the gate out of each and what counts as done. The stage is
derived from the record, .
Each row has a live example.

profile
a question passes through
the record refuses
done when

asked → conjectured → preregistered before a run → run → evidenced → claimed → reviewed

numbers no result accounts for; without the count; without the test; a check on stale evidence
each question settled
Watch

specified → implemented (a diff by hash) → verified by the instrument on that head → claimed → reviewed

without an instrument run, or on a superseded head; the diff's author as its reviewer
each requirement's claim rests on a passing run on the current head
Watch

asked → thesised → preregistered → backtested out of sample, after costs → claimed → risk-reviewed → positioned → monitored

a backtest without its costs; without both, or without the configurations tried; a position without size, stop and review date; a live order
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

Agents, over MCP
Your agent gets the record's tools, and the method as an Agent Skill.

Python
Roles as policy: reviewers, the instrument, reserved authors.

The UI and the JSON API
Read-only by default; follows a running swarm live.

Gate CI on the write-up
Lints a report against the record; exits non-zero on errors.

Hand over a verifiable bundle
Anyone can check it, in any language or in the browser.

Run a swarm on it
HypSwarm schedules agents from the record's own work board.

This page has a record

We hold this page to the rules it describes.

The figures above are claims in a HypGraph record built with the page. The build's instrument measures
them, a reviewer re-measures each another way, and the page's text is checked against the record with
, so a figure the record doesn't hold doesn't reach the page. Open it in the app above
with This page's record , or download the bundle
and verify it yourself.

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

It runs where you run it: a local file, no account, and no network calls of its
own. Releases are published to PyPI from GitHub Actions by trusted publishing.

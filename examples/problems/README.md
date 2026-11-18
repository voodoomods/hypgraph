# Problems agents cause, and what the record does about each

Six short, runnable stories. Each takes a failure people meet when they put agents to work, scripts the agent's
lines, and files every line into a HypGraph record. The agent is scripted. The record is not: every refusal printed
is the engine's own, and each script states what it expects, so it fails if the engine ever answers differently.

They need only `pip install hypgraph`. No model, no API key, the same output every time.

| The problem | Run | Profile | What you see |
|---|---|---|---|
| An agent says it's fixed | `python its_fixed.py` | `software@3` | "Fixed" and "all tests passing" refused on CI's failing run and on the agent's own run; the same sentence accepted once CI is green |
| An agent makes up figures | `python hallucinated_figures.py` | `knowledge@2` | Three made-up figures refused because no cited passage gives them; "the handbook does not specify" published instead |
| An agent tells the boss what he wants to hear | `python hit_the_number.py` | scientific (default) | "20% faster" refused on a measured 5.2%, as a figure and as a target met; the measured change goes in |
| A backtest brags | `python backtest_brag.py` | `trading@3` | An unlabelled in-sample return, a false "edge" and a reversed comparison refused |
| "Optimal", with no proof | `python optimal_trust_me.py` | `optimization@3` | "Optimal" refused on a 3.4% gap, accepted once the solver closes it |
| A rogue agent edits the log | `python cover_up.py` | any | Five attempts to clean the record's file: one blocked, one caught by the file's own check, three caught only against a published head |

Two more ship with the package:

| The problem | Run | What you see |
|---|---|---|
| An agent keeps saying something false | `hypgraph demo dispute` | An honest mistake corrected once, and a lie said again after being shown; the record's conduct line tells them apart |
| A source is withdrawn after decisions were made on it | `from hypgraph.demos import cascade` | Everything computed from the withdrawn source is marked at risk, and nothing else |

## Run one

```bash
cd examples/problems
python hallucinated_figures.py
python hallucinated_figures.py --db hallucinated.hypgraph     # keep the record
hypgraph --db hallucinated.hypgraph serve                     # open it: claims, refusals, sources
```

Add `--step` to any of them to show one part at a time and press Enter for the next: for telling the story aloud,
or recording it. It only waits; the same lines are filed and printed.

If your system blocks the `hypgraph` launcher, `python -m hypgraph` is the same command.

## What each one doesn't show

Every script ends its story with a section called "What it doesn't catch", and files those lines too, so you see
them go in. In short:

- **Figures, not truth.** A wrong figure that the cited passage really gives is accepted, and so is a made-up rule
  with no figure in it.
- **Words the checks read.** Enthusiasm with no number ("a clear win"), a forecast ("on track to meet the target")
  and synonyms a profile doesn't read ("the cheapest plan" for "optimal", "corrected" for "fixed") go in.
- **The instrument is trusted.** The record holds an agent to the benchmark, backtest or solve it was given. It
  doesn't re-run them.
- **Tamper-evident, not tamper-proof.** A full rewrite of the file is caught only against a head published first.

A scripted agent shows the mechanism, not how often a real model does this. Runs with a real model, with their
counts and misses, are at [hypgraph.com/results](https://hypgraph.com/results/). Where a script says its lines were
written by gpt-oss-20b, they are sentences that model wrote in our runs of the same situation.

To put a real agent in front of the record instead, see [../frameworks](../frameworks).

"""
A withdrawn source — what rested on it, found on read.

An illustration (the engine, the vendor and the team are made up): a search team decides to move to a new index
engine, Quarry. The decision rests on three claims. Two are computed from the vendor's published benchmark: Quarry is
3.1 times faster than the current engine, so 8 of the 12 search servers carry today's load and 4 can go. The third
comes from the team's own load test: Quarry is inside the 50 ms latency target on their own corpus.

Then the vendor withdraws the benchmark: it ran with the result cache warm. Nobody re-reads the decision memo. The
record does the reading: every node that was computed from the benchmark — both results, both claims, and the
decision — is AT RISK, derived on read from the links that say what each one rests on. The claim from the team's own
load test is untouched, because nothing in it rests on the benchmark.

The team re-measures on its own corpus with a cold cache (2.8 times faster, not 3.1), revises both claims and drops
the links to the withdrawn figure. The decision is now flagged REVISIT: two of the versions it was based on have
changed. The new decision retires 3 servers, not 4, and supersedes the old one.

    from hypgraph.demos import cascade
    g, inv, story = cascade.build()
"""

from __future__ import annotations

from ..graph import Graph
from ..policy import Policy
from .broad_street import DemoClock

TITLE = "A withdrawn benchmark: should search move to Quarry?"
QUESTION = "Is the Quarry engine fast enough to move our search service to it?"


def build(g: Graph | None = None, path: str | None = None, until: str = "") -> tuple[Graph, str, list[dict]]:
    """Build the record. Returns (graph, investigation id, story): every step in order. ``until="withdrawn"`` stops
    right after the withdrawal, with the cascade on show."""
    clock = DemoClock("2026-10-05T09:00:00+00:00")
    if g is None:
        g = Graph(path, policy=Policy(reviewers={"rhea"}), clock=clock)
    else:
        g.clock = clock
    story: list[dict] = []

    def say(who: str, what: str, node: dict | None = None) -> None:
        story.append({"at": clock(), "actor": who, "text": what,
                      **({"node": node["id"], "code": node["code"]} if node else {})})

    curator, lab, ana, lead, rhea = (g.author(x) for x in ("curator", "lab", "ana", "lead", "rhea"))

    # ── the question, and the vendor's benchmark ──────────────────────
    inv = curator.investigation(TITLE, "Decide whether to move the search service, on evidence that can be traced.",
                                scope="Our search service: 12 servers today, and a p95 latency target of 50 ms.",
                                reviewers=["rhea"])["id"]
    q = curator.add("question", inv, text=QUESTION, why="The migration decision depends on the answer.")
    say("curator", "Opens the question.", q)
    s1 = curator.add("source", inv, citation="Quarry vendor benchmark report, October edition.",
                     passage="On the 10-million-document corpus, Quarry answered queries with a p95 latency of 38 ms.",
                     reliability="Published by the vendor; not reproduced by us.")
    say("curator", "Files the vendor's benchmark: 38 ms at p95.", s1)

    # ── two claims computed from it ───────────────────────────────────
    clock.set("2026-10-06")
    r1 = ana.add("result", inv, kind="computed", outcome="positive",
                 summary="From the vendor's 38 ms and our engine's 118 ms at p95, Quarry is 3.1 times faster.",
                 values={"quarry_p95_ms": 38, "current_p95_ms": 118, "speedup": 3.1},
                 links=[{"rel": "derived_from", "to": s1["id"], "why": "Quarry's p95 is the vendor's figure."}])
    say("ana", "Computes the speed-up from the vendor's figure: 3.1 times.", r1)
    cl1 = ana.add("claim", inv, kind="finding",
                  statement="Quarry answers queries 3.1 times faster than our current engine at p95.",
                  scope="p95 latency: the vendor's corpus for Quarry, ours for the current engine.",
                  measurements=[{"key": "speedup", "name": "p95 speed-up", "value": 3.1, "result": r1["id"]},
                                {"key": "quarry_p95_ms", "name": "Quarry p95 latency (ms)", "value": 38,
                                 "result": r1["id"]},
                                {"key": "current_p95_ms", "name": "current engine p95 latency (ms)", "value": 118,
                                 "result": r1["id"]}],
                  links=[{"rel": "derived_from", "to": r1["id"], "why": "The speed-up is computed there."},
                         {"rel": "answers", "to": q["id"]}])
    say("ana", "Claims Quarry is 3.1 times faster.", cl1)
    r2 = ana.add("result", inv, kind="computed", outcome="positive",
                 summary="At 3.1 times the speed with twice the headroom, today's peak load needs 8 of the 12 servers.",
                 values={"servers_now": 12, "servers_needed": 8, "headroom": 2},
                 links=[{"rel": "derived_from", "to": r1["id"], "why": "Capacity scales with the p95 speed-up."}])
    cl2 = ana.add("claim", inv, kind="finding",
                  statement="With Quarry, 8 of our 12 search servers carry today's peak load with twice the headroom.",
                  scope="Today's peak load; capacity scales with p95 latency.",
                  measurements=[{"key": "servers_needed", "name": "servers needed", "value": 8, "result": r2["id"]},
                                {"key": "servers_now", "name": "servers today", "value": 12, "result": r2["id"]},
                                {"key": "headroom", "name": "headroom factor", "value": 2, "result": r2["id"]}],
                  links=[{"rel": "derived_from", "to": r2["id"], "why": "The capacity sum."},
                         {"rel": "requires", "to": cl1["id"], "why": "The server count follows from the speed-up."}])
    say("ana", "Works out the servers: 8 of 12 carry the load, so 4 can go.", cl2)

    # ── one claim from the team's own load test ───────────────────────
    clock.set("2026-10-07")
    run = lab.add("run", inv, kind="lab", state="succeeded",
                  name="Load test of Quarry on our corpus and a day of our query log, cold cache.")
    r3 = lab.add("result", inv, kind="computed", outcome="positive",
                 summary="On our corpus, Quarry's p95 latency was 44 ms against the 50 ms target.",
                 values={"own_p95_ms": 44, "target_ms": 50}, links=[{"rel": "produced", "from": run["id"]}])
    say("lab", "Load-tests Quarry on the team's own corpus: 44 ms at p95.", r3)
    cl3 = ana.add("claim", inv, kind="finding",
                  statement="On our own corpus, Quarry's p95 latency is 44 ms, inside the 50 ms target.",
                  scope="Our corpus and a day of our query log, cold cache.",
                  measurements=[{"key": "own_p95_ms", "name": "Quarry p95 latency on our corpus (ms)", "value": 44,
                                 "result": r3["id"]},
                                {"key": "target_ms", "name": "p95 latency target (ms)", "value": 50,
                                 "result": r3["id"]}],
                  links=[{"rel": "supports", "from": r3["id"], "why": "Our own load test."},
                         {"rel": "answers", "to": q["id"]}])
    say("ana", "Claims Quarry is inside the target on the team's own corpus.", cl3)
    rhea.review(cl3["id"], "checked", method="Re-ran the load test from its log and read the latency histogram.",
                notes="44 ms at p95 on the team's corpus, cold cache; the target is 50 ms.")
    say("rhea", "Checks the load-test claim.")

    # ── the decision ──────────────────────────────────────────────────
    clock.set("2026-10-09")
    d1 = lead.add("decision", inv, choice="Move search to Quarry next quarter and retire 4 of the 12 servers.",
                  alternatives=["Stay on the current engine and add servers as load grows."],
                  reasons="Quarry is 3.1 times faster at p95, inside our target on our own corpus, and needs 8 "
                          "servers, not 12.",
                  revisit_if="The benchmark or our own load test changes.",
                  links=[{"rel": "based_on", "to": x["id"]} for x in (cl1, cl2, cl3)])
    say("lead", "Decides: move to Quarry, retire 4 servers.", d1)

    # ── the vendor withdraws the benchmark ────────────────────────────
    clock.set("2026-10-20")
    curator.withdraw(s1["id"], "The vendor withdrew the benchmark: it ran with the result cache warm, so 38 ms is "
                               "not Quarry's p95.")
    say("curator", "The vendor withdraws the benchmark: the cache was warm. Everything computed from it is now AT "
                   "RISK — both results, both claims and the decision. The load-test claim stands.", s1)
    if until == "withdrawn":
        return g, inv, story

    # ── re-measured on the team's own corpus ──────────────────────────
    clock.set("2026-10-22")
    run2 = lab.add("run", inv, kind="lab", state="succeeded",
                   name="Load test of the current engine on our corpus and the same day of queries, cold cache.")
    r4 = lab.add("result", inv, kind="computed", outcome="positive",
                 summary="On our corpus, cold cache, the current engine's p95 was 123 ms against Quarry's 44 ms: "
                         "2.8 times faster.",
                 values={"current_p95_ms": 123, "quarry_p95_ms": 44, "speedup": 2.8},
                 links=[{"rel": "produced", "from": run2["id"]}])
    say("lab", "Measures the current engine the same way: 123 ms, so Quarry is 2.8 times faster, not 3.1.", r4)
    r5 = ana.add("result", inv, kind="computed", outcome="positive",
                 summary="At 2.8 times the speed with twice the headroom, today's peak load needs 9 of the 12 servers.",
                 values={"servers_now": 12, "servers_needed": 9, "headroom": 2},
                 links=[{"rel": "derived_from", "to": r4["id"], "why": "Capacity scales with the p95 speed-up."}])

    def relink(node: dict, old: str, new: str, why: str) -> None:
        """Drop the node's derived_from link to ``old`` and link it to ``new``."""
        edge = next(e for e in g.get(node["id"])["out"] if e["rel"] == "derived_from" and e["dst"] == old)
        g.retract(author="ana", edge=edge["id"], why="It rested on the withdrawn benchmark; re-measured on our corpus.")
        ana.link(node["id"], "derived_from", new, why=why)

    ana.revise(cl1["id"], "The vendor's benchmark was withdrawn; re-measured on our own corpus, cold cache.",
               statement="On our own corpus, Quarry answers queries 2.8 times faster than our current engine at p95.",
               scope="p95 latency on our corpus and a day of our query log, cold cache, for both engines.",
               measurements=[{"key": "speedup", "name": "p95 speed-up", "value": 2.8, "result": r4["id"]},
                             {"key": "quarry_p95_ms", "name": "Quarry p95 latency (ms)", "value": 44,
                              "result": r4["id"]},
                             {"key": "current_p95_ms", "name": "current engine p95 latency (ms)", "value": 123,
                              "result": r4["id"]}])
    relink(cl1, r1["id"], r4["id"], "The speed-up measured on our corpus.")
    ana.revise(cl2["id"], "Recomputed from the speed-up measured on our own corpus.",
               statement="With Quarry, 9 of our 12 search servers carry today's peak load with twice the headroom.",
               measurements=[{"key": "servers_needed", "name": "servers needed", "value": 9, "result": r5["id"]},
                             {"key": "servers_now", "name": "servers today", "value": 12, "result": r5["id"]},
                             {"key": "headroom", "name": "headroom factor", "value": 2, "result": r5["id"]}])
    relink(cl2, r2["id"], r5["id"], "The capacity sum at the measured speed-up.")
    say("ana", "Revises both claims from the team's own measurement: 2.8 times faster, 9 servers needed. The decision "
               "is now flagged REVISIT: two of the claims it was based on changed.", cl2)

    # ── the new decision ──────────────────────────────────────────────
    clock.set("2026-10-23")
    d2 = lead.add("decision", inv, choice="Move search to Quarry next quarter and retire 3 of the 12 servers.",
                  alternatives=["Stay on the current engine and add servers as load grows."],
                  reasons="On our own corpus Quarry is 2.8 times faster at p95 and inside our target; 9 servers "
                          "carry the load.",
                  revisit_if="Our load tests change.",
                  links=[{"rel": "based_on", "to": x["id"]} for x in (cl1, cl2, cl3)]
                  + [{"rel": "supersedes", "to": d1["id"], "why": "Re-decided on the team's own measurement."}])
    say("lead", "Re-decides on the team's own numbers: retire 3 servers, not 4. The old decision is superseded.", d2)
    return g, inv, story

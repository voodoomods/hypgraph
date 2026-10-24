"""Writes cost what they touch: the snapshot isn't copied whole, and derived standing is kept for every node a write
can't have affected. The guarantee that matters is that this changes nothing: after every kind of write, in random
order, the carried-over standing must equal a rebuild from scratch, node for node."""
import random

import pytest

from hypgraph import Graph, GraphError, Policy
from hypgraph import derive as D


def full_states(g: Graph) -> dict:
    fresh = g._rebuild(g._connect())
    return {i: D.state(fresh, i) for i in fresh.nodes}


@pytest.mark.parametrize("seed", range(6))
def test_carried_standing_equals_a_rebuild_after_random_writes(tmp_path, seed):
    rnd = random.Random(seed)
    g = Graph(tmp_path / "g.db", policy=Policy(reviewers={"rev", "rev2"}))
    imp = "importer"
    inv = g.create(author=imp, type="investigation", fields={"title": "Random", "objective": "Random writes, checked."})["id"]
    ids = {t: [] for t in ("run", "result", "claim", "hypothesis", "decision", "source", "artifact")}

    def pick(t):
        return rnd.choice(ids[t]) if ids[t] else None

    for step in range(140):
        op = rnd.choice(["run", "result", "claim", "claim", "hypothesis", "source", "artifact", "review", "review",
                         "withdraw", "revise", "link", "lease", "decision", "supersede", "fail_run"])
        try:
            if op == "run":
                links = [{"rel": "uses", "to": pick("artifact"), "data": {"role": "data"}}] if ids["artifact"] else []
                if ids["run"] and rnd.random() < .3:
                    links.append({"rel": "replicates", "to": pick("run"),
                                  "data": {"differs": rnd.choice(["new_seed", "new_impl", "new_data"])}})
                ids["run"].append(g.create(author=rnd.choice([imp, "lab"]), type="run", inv=inv, links=links,
                                           fields={"kind": "agent", "state": "succeeded"})["id"])
            elif op == "fail_run" and ids["run"]:
                g.revise(author="operator", node=pick("run"), fields={"state": "failed"}, reason="it crashed after all")
            elif op == "result":
                links = [{"rel": "produced", "from": pick("run")}] if ids["run"] and rnd.random() < .8 else []
                if ids["source"] and rnd.random() < .2:
                    links.append({"rel": "cites", "to": pick("source")})
                ids["result"].append(g.create(author=imp, type="result", inv=inv, links=links, fields={
                    "summary": f"Result {step} of the random run.", "kind": rnd.choice(["computed", "cited"])})["id"])
            elif op == "source":
                ids["source"].append(g.create(author=imp, type="source", inv=inv,
                                              fields={"citation": f"Author {step}, a paper, 2026."})["id"])
            elif op == "artifact":
                ids["artifact"].append(g.create(author=imp, type="artifact", inv=inv,
                                                fields={"sha256": f"{rnd.getrandbits(256):064x}"})["id"])
            elif op in ("claim", "hypothesis"):
                links = [{"rel": "supports", "from": rnd.choice(ids["result"] + ids["claim"] + ids["source"]),
                          "why": "random support"}] if (ids["result"] or ids["source"]) else []
                if ids["claim"] and rnd.random() < .35:
                    links.append({"rel": "requires", "to": pick("claim")})
                if ids["result"] and rnd.random() < .2:
                    links.append({"rel": "challenges", "from": pick("result"), "why": "random challenge"})
                fields = {"statement": f"Statement {step} of the random run."}
                if op == "hypothesis":
                    fields["predictions"] = ["something observable"]
                    links = [x for x in links if x["rel"] != "requires" or True]
                ids[op].append(g.create(author=imp, type=op, inv=inv, links=links, fields=fields)["id"])
            elif op == "decision" and (ids["claim"] or ids["result"]):
                ids["decision"].append(g.create(author=imp, type="decision", inv=inv, links=[
                    {"rel": "based_on", "to": rnd.choice(ids["claim"] + ids["result"])}],
                    fields={"choice": "Do the thing.", "reasons": "Because of the evidence cited."})["id"])
            elif op == "review" and (ids["claim"] or ids["result"]):
                g.review(author=rnd.choice(["rev", "rev2", "someone"]), target=rnd.choice(ids["claim"] + ids["result"]),
                         verdict=rnd.choice(["pass", "fail", "objection", "resolved", "comment", "replicated"]),
                         method="random review method", notes="random review notes")
            elif op == "withdraw":
                pool = ids["claim"] + ids["result"] + ids["run"] + ids["source"]
                if pool:
                    g.withdraw(author="operator", node=rnd.choice(pool), why="random withdrawal reason")
            elif op == "revise" and ids["claim"]:
                g.revise(author="operator", node=pick("claim"), fields={"limitations": f"Limit {step}."},
                         reason="random revision reason")
            elif op == "link" and ids["result"] and ids["claim"]:
                g.link(author=imp, src=pick("result"), rel="supports", dst=pick("claim"), why="a later link")
            elif op == "lease" and ids["claim"]:
                g.lease(author="rev", node=pick("claim"), task=f"t{step}")
            elif op == "supersede" and len(ids["claim"]) > 1:
                a, b = rnd.sample(ids["claim"], 2)
                g.link(author=imp, src=a, rel="supersedes", dst=b)
        except GraphError:
            continue                                            # a refused write changes nothing; that's fine
        if step % 7 == 0 or step > 120:
            s = g.snapshot()
            carried = {i: D.state(s, i) for i in s.nodes}       # cached where the write couldn't reach
            assert carried == full_states(g), f"seed {seed}, step {step}, op {op}"


def test_a_write_does_not_copy_untouched_lists(tmp_path):
    g = Graph(tmp_path / "g.db")
    inv = g.create(author="importer", type="investigation", fields={"title": "Share", "objective": "Lists are shared."})["id"]
    r = g.create(author="importer", type="result", inv=inv, fields={"summary": "A result to support claims."})["id"]
    c = g.create(author="importer", type="claim", inv=inv, fields={"statement": "A claim with support."},
                 links=[{"rel": "supports", "from": r, "why": "the result"}])["id"]
    before = g.snapshot()
    g.create(author="importer", type="question", inv=inv, fields={"text": "An unrelated question here."})
    after = g.snapshot()
    assert after is not before
    assert after.inn[c] is before.inn[c]                        # untouched: shared, not copied
    assert after._state is not before._state

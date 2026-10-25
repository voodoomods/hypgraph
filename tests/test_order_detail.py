"""The order carries the target's own content, so an assignee never needs `show` to read what it was given: a
review order shows the claim's statement, scope, measurements and the values of the results it rests on; a
question order shows the question; a replication of the author's run is named, with 'no recomputation needed'."""
from hypgraph import Graph, Policy

H = "harness"


def test_review_order_carries_the_claim_and_its_evidence():
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "Order detail.", "objective": "No show needed."})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "What is A's accuracy?"})["id"]
    run = g.create(author="analyst", type="run", inv=inv, fields={"kind": "agent", "name": "count", "state": "succeeded"})
    rs = g.create(author="analyst", type="result", inv=inv, fields={"summary": "Counted the paired items in items.csv.",
                                                                     "values": {"acc": {"k": 812, "n": 1000}}},
                  links=[{"rel": "produced", "from": run["id"]}])
    cl = g.create(author="analyst", type="claim", inv=inv, fields={"statement": "A is right on 812 of 1000 items.",
                                                                    "scope": "The 1000 paired items in items.csv."},
                  links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
    lab = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "re-run of RUN1", "state": "succeeded"},
                   links=[{"rel": "replicates", "to": run["id"], "data": {"differs": "same_code"}}])
    o = g.issue_work(author=H, inv=inv, target=cl["id"], assignee="critic", role="reviewer",
                     objective="Review CL1: check its numbers and reasoning.", done_when=[{"p": "reviewed"}])
    text = o["text"]
    assert "statement: A is right on 812 of 1000 items." in text
    assert "scope: The 1000 paired items" in text
    assert "rests on RS1: Counted the paired items" in text and "acc = 812 of 1000" in text
    assert f"reproduced by {lab['code']}" in text and "no recomputation" in text
    q_order = g.issue_work(author=H, inv=inv, target=q, assignee="stats", objective="Answer Q1 again, differently.",
                           done_when=[{"p": "claim_made"}])
    assert "question: What is A's accuracy?" in q_order["text"]

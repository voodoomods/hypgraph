"""Cancelling an open order frees its target: another assignee can be issued it at once. A returned order has
already released its lease, so cancelling it releases nothing more."""
from hypgraph import Graph, GraphError, Policy

import pytest

HARNESS = "harness"


def _seed():
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={HARNESS}))
    inv = g.create(author=HARNESS, type="investigation",
                   fields={"title": "A lease test.", "objective": "See that cancel frees the target."})["id"]
    q = g.create(author=HARNESS, type="question", inv=inv, code="Q1", fields={"text": "What is the rate?"})["id"]
    return g, inv, q


def test_cancel_of_an_open_order_releases_the_target():
    g, inv, q = _seed()
    o = g.issue_work(author=HARNESS, inv=inv, target=q, assignee="alpha", objective="Answer Q1: what is the rate?")
    with pytest.raises(GraphError, match="already works on"):      # the open order itself blocks a duplicate
        g.issue_work(author=HARNESS, inv=inv, target=q, assignee="beta", objective="Answer Q1: what is the rate?")
    out = g.cancel_work(author=HARNESS, order=o["order"], why="alpha left the team")
    assert out["lease_released"]
    o2 = g.issue_work(author=HARNESS, inv=inv, target=q, assignee="beta", objective="Answer Q1: what is the rate?")
    assert o2["code"] == "T2"
    st = {x["code"]: x["status"] for x in g.orders(inv)}
    assert st == {"T1": "cancelled", "T2": "open"}
    assert g.verify()["ok"]


def test_cancel_of_a_returned_order_releases_nothing_more():
    g, inv, q = _seed()
    o = g.issue_work(author=HARNESS, inv=inv, target=q, assignee="alpha", objective="Answer Q1: what is the rate?")
    g.return_work(author="alpha", order=o["order"], note="could not")
    out = g.cancel_work(author=HARNESS, order=o["order"], why="not needed")
    assert not out["lease_released"]
    assert g.issue_work(author=HARNESS, inv=inv, target=q, assignee="beta",
                        objective="Answer Q1: what is the rate?")["code"] == "T2"

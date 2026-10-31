"""D-10: orders meetable by construction, absolutes over enumerated sets, the question board, settle, replay."""
from datetime import datetime, timedelta

import pytest

from hypgraph import Graph, GraphError, Policy, coord
from hypgraph.checks import _enumerated


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 1, 9, 0, 0)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t.isoformat(timespec="seconds")


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}), clock=Clock())
    lead = g.author("lead")
    inv = lead.investigation("Does A beat B", "Find out whether A beats B on the paired held-out items.")["id"]
    q1 = lead.add("question", inv, text="Q1: What is A's accuracy over all items?")["id"]
    q2 = lead.add("question", inv, text="Q2: Is A significantly better than B?")["id"]
    h1 = lead.add("hypothesis", inv, statement="A is more accurate than B on the held-out items.",
                  predictions=["paired difference above zero"])["id"]
    return g, lead, inv, q1, q2, h1


# ── enumeration ──────────────────────────────────────────────────

def test_absolutes_over_an_enumerated_set_pass():
    assert _enumerated("A trails B in every subset: math -2.6, code -2.2, reading -0.4.", "every")
    assert _enumerated("All three subsets show it.", "all")
    assert _enumerated("Over all 818 items, A scores 645 of 818.", "all")
    assert not _enumerated("The model never leaks.", "never")
    assert not _enumerated("A beats B on every benchmark.", "every")        # no count, no breakdown: a generalisation
    assert not _enumerated("All users will convert.", "all")


def test_enumerated_absolute_enters_the_record(env):
    g, lead, inv, q1, q2, h1 = env
    a = g.author("analyst")
    r = a.add("result", inv, summary="Per-subset gaps: math -0.026, code -0.022, reading -0.004.",
              values={"math": {"value": -0.026}, "code": {"value": -0.022}, "reading": {"value": -0.004}})["id"]
    ok = a.add("claim", inv, statement="A trails B in every subset: math -0.026, code -0.022, reading -0.004.",
               scope="The 821 paired items, three subsets.", links=[{"rel": "derived_from", "to": r}])
    assert ok["type"] == "claim"
    with pytest.raises(GraphError, match="ABSOLUTE_WITHOUT_COUNT"):
        a.add("claim", inv, statement="A trails B on every benchmark there is.", scope="The 821 paired items.",
              links=[{"rel": "derived_from", "to": r}])


# ── orders meetable by construction ──────────────────────────────

def test_predicate_spellings_and_recipes(env):
    g, lead, inv, q1, q2, h1 = env
    assert coord.norm_pred({"predicate": "claim_made"}) == {"p": "claim_made"}
    assert coord.norm_pred("reviewed") == {"p": "reviewed"}
    o = g.issue_work(author="lead", inv=inv, target="Q1", assignee="analyst", objective="Answer Q1 from items.csv.",
                     done_when=[{"predicate": "claim_made"}])
    assert o["done_when"] == [{"p": "claim_made"}]
    assert "how: graph_add" in o["text"] and '"answers"' in o["text"]
    with pytest.raises(GraphError, match='write each as {"p": "claim_made"}'):
        g.issue_work(author="lead", inv=inv, target="Q2", assignee="analyst", objective="Answer Q2 from items.csv.",
                     done_when=[{"p": "vibes"}])
    with pytest.raises(GraphError, match="a target is a code the record has"):
        g.issue_work(author="lead", inv=inv, target="H-Q4-interpretation", assignee="critic",
                     objective="Interpret the gaps for Q4 carefully.")


def test_work_under_the_lease_counts(env):
    g, lead, inv, q1, q2, h1 = env
    o = g.issue_work(author="lead", inv=inv, target=h1, assignee="critic", objective="Test H1 on the items.")
    assert [p["p"] for p in o["done_when"]] == ["result_exists", "claim_made"]
    c = g.author("critic")
    run = c.add("run", inv, kind="agent", name="per-subset gaps", state="succeeded")["id"]
    rs = c.add("result", inv, summary="A 607 of 821, B 621 of 821 on the paired items.",
               values={"a": {"k": 607, "n": 821}, "b": {"k": 621, "n": 821}},
               links=[{"rel": "produced", "from": run}])
    chk = g.check_work(o["order"])
    by = {x["p"]: x for x in chk["predicates"]}
    assert by["result_exists"]["met"] and by["result_exists"]["evidence"] == [rs["id"]]   # no link to H1 needed
    assert not by["claim_made"]["met"]
    c.add("claim", inv, statement="A is right on 607 of 821 items against B's 621 of 821: A is not more accurate.",
          scope="The 821 paired items.", links=[{"rel": "challenges", "to": h1, "why": "A scores below B."},
                                             {"rel": "derived_from", "to": rs["id"]}])
    assert g.check_work(o["order"])["all_met"]


def test_a_third_rework_of_a_stuck_predicate_is_refused(env):
    g, lead, inv, q1, q2, h1 = env
    o = g.issue_work(author="lead", inv=inv, target=h1, assignee="critic", objective="Test H1 on the items.")
    g.return_work(author="critic", order=o["order"], note="nothing yet")
    r1 = g.rework(author="lead", order=o["order"], missing="no result and no claim were written")
    g.return_work(author="critic", order=r1["order"], note="still nothing")
    r2 = g.rework(author="lead", order=r1["order"], missing="still no result and no claim")
    g.return_work(author="critic", order=r2["order"], note="still nothing")
    with pytest.raises(GraphError, match="reworked twice already"):
        g.rework(author="lead", order=r2["order"], missing="again nothing was written")
    r3 = g.rework(author="lead", order=r2["order"], missing="dropping result_exists", done_when=["claim_made"])
    assert g.get(r3["order"])["body"]["done_when"] == [{"p": "claim_made"}]
    st = {x["code"]: x["status"] for x in g.orders(inv)}
    assert st == {"T1": "reworked", "T2": "reworked", "T3": "reworked", "T4": "open"}   # the whole chain, not one step
    g.withdraw(author="lead", node=r3["order"], why="the lead gave up on this line of work")
    st = {x["code"]: x["status"] for x in g.orders(inv)}
    assert st["T4"] == "cancelled" and st["T3"] == "returned"                      # a withdrawn replacement replaces nothing


# ── question board, sufficiency, settle ──────────────────────────

def test_question_board_and_settle(env):
    g, lead, inv, q1, q2, h1 = env
    a = g.author("analyst")
    board = {q["code"]: q["status"] for q in g.question_board(inv)}
    assert board == {"Q1": "open", "Q2": "open"}
    o = g.issue_work(author="lead", inv=inv, target=q1, assignee="analyst", objective="Answer Q1 from items.csv.")
    assert g.question_board(inv)[0]["status"] == "in progress"
    rs = a.add("result", inv, summary="A right on 607 of 821 items.", values={"acc": {"k": 607, "n": 821}})["id"]
    cl = a.add("claim", inv, statement="A is right on 607 of 821 items.", scope="The 821 paired items.",
               links=[{"rel": "answers", "to": q1}, {"rel": "derived_from", "to": rs}])["id"]
    g.return_work(author="analyst", order=o["order"], note="done")
    assert g.question_board(inv)[0]["status"] == "answered"
    settled = g.settle(author="lead", inv=inv)
    assert [x["order"] for x in settled] == ["T1"] and g.orders(inv)[0]["status"] == "accepted"
    g.author("critic").review(cl, "checked", "Recounted from items.csv.", "607 of 821 holds.")
    b = g.question_board(inv)
    assert b[0]["status"] == "settled" and "checked by critic" in b[0]["by"]
    text = g.briefing(inv)["text"]
    assert "BOARD" in text and "Q1 SETTLED" in text and "1 of 2 settled" in text
    assert "Q2 open question" in text and "needs a review" not in text
    assert "settle_work" not in text                        # nothing waits once settled


def test_replay_runs_logged_refusals_through_the_current_checker(env):
    g, lead, inv, q1, q2, h1 = env
    a = g.author("analyst")
    r = a.add("result", inv, summary="A 607 of 821 and B 621 of 821.",
              values={"a": {"k": 607, "n": 821}, "b": {"k": 621, "n": 821}})["id"]
    with pytest.raises(GraphError):
        a.add("claim", inv, statement="A always beats B.", scope="The 821 paired items.",
              links=[{"rel": "derived_from", "to": r}])
    rep = g.replay_refusals(inv)
    assert rep["replayed"] == 1 and rep["rows"][0]["full"] and rep["rows"][0]["verdict"] == "same"
    assert "ABSOLUTE_WITHOUT_COUNT" in rep["by_code"]

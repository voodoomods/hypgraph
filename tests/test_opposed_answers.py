"""A question settles only when every live answer to it is checked. A checked answer beside a live unchecked one is
two answers the record hasn't reconciled, and they may disagree: in studies T1 a reviewer re-ran the numbers behind
"no look-ahead" and checked it, while "it is look-ahead" stood unchecked on the same question, and the question
counted as settled with the wrong answer."""
from hypgraph import Graph, Policy, profiles

H = "harness"


def _g(profile: str = "", asks: str = "measure"):
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    f = {"title": "Opposed answers.", "objective": "See two live answers keep a question open."}
    if profile:
        f["profile"] = profile
    inv = g.create(author=H, type="investigation", fields=f)["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1",
                 fields={"text": "Could the signal be known when a trade on it is placed?", "asks": asks})["id"]
    return g, inv, q


def _answer(g, inv, q, author, statement, corr):
    run = g.create(author=author, type="run", inv=inv, fields={"kind": "agent", "name": "corr", "state": "succeeded"},
                   links=[{"rel": "part_of", "to": q}])["id"]
    rs = g.create(author=author, type="result", inv=inv, fields={
        "summary": f"The signal's correlation with the next day's return is {corr}.",
        "values": {"corr_next": {"value": corr}}, "outcome": "positive"},
        links=[{"rel": "produced", "from": run}])["id"]
    return g.create(author=author, type="claim", inv=inv, fields={
        "statement": statement, "scope": "prices.csv, every day.",
        "measurements": [{"name": "corr", "key": "corr_next", "result": rs}]},
        links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]


def _board(g, inv):
    return {r["code"]: r for r in g.question_board(inv)}


def test_a_second_live_answer_keeps_the_question_open_until_it_is_checked():
    g, inv, q = _g()
    no = _answer(g, inv, q, "quant", "There is no look-ahead: the correlation with the next day is 0.34.", 0.34)
    g.review(author="critic", target=no, verdict="checked", method="Re-ran the correlation.", notes="0.34 holds.")
    assert _board(g, inv)["Q1"]["status"] == "settled"
    yes = _answer(g, inv, q, "risk", "It is look-ahead: the signal agrees with the next day's move, 0.71 of days.", 0.71)
    row = _board(g, inv)["Q1"]
    assert row["status"] == "answered" and row["unchecked"] == [g.get(yes)["code"]]
    assert "unchecked beside" in row["by"] and g.get(no)["code"] in row["by"]
    crit = {c["name"]: c for c in profiles.completion(g.snapshot(), inv)["criteria"]}
    assert not crit["questions_settled"]["met"]
    # the reviewer reads the second answer and objects: it falls, and the first answer settles the question again
    g.review(author="critic", target=yes, verdict="objection", method="Read both claims against the file.",
             notes="Contradicts the checked answer; the file's signal column is built from the next close.")
    assert _board(g, inv)["Q1"]["status"] == "settled"


def test_two_checked_answers_settle():
    g, inv, q = _g()
    a = _answer(g, inv, q, "quant", "The correlation with the next day's return is 0.34.", 0.34)
    b = _answer(g, inv, q, "risk", "The signal matches the next day's move on 0.71 of days.", 0.71)
    for c in (a, b):
        g.review(author="critic", target=c, verdict="checked", method="Re-ran it.", notes="The numbers hold as stated.")
    assert _board(g, inv)["Q1"]["status"] == "settled" and _board(g, inv)["Q1"]["unchecked"] == []


def test_the_reviewed_gate_names_the_unchecked_answer():
    g, inv, q = _g("trading@2")
    no = _answer(g, inv, q, "quant", "There is no look-ahead: the correlation with the next day is 0.34.", 0.34)
    g.review(author="critic", target=no, verdict="checked", method="Re-ran the correlation.", notes="0.34 holds.")
    assert g.stage(q)["complete"]
    yes = _answer(g, inv, q, "risk", "It is look-ahead: the signal agrees with the next day's move, 0.71 of days.", 0.71)
    st = g.stage(q)
    gate = next(gt for gt in st["gates"] if gt["gate"] == "reviewed")
    assert not st["complete"] and not gate["met"]
    assert g.get(yes)["code"] in gate["why"] and "every live answer" in gate["why"]


def test_a_checked_inconclusive_answer_does_not_end_the_question_beside_an_unchecked_finding():
    g, inv, q = _g("trading@2", asks="")
    run = g.create(author="quant", type="run", inv=inv, fields={"kind": "agent", "name": "read", "state": "succeeded"},
                   links=[{"rel": "part_of", "to": q}])["id"]
    rs = g.create(author="quant", type="result", inv=inv, fields={
        "summary": "No column in prices.csv says when the signal was published.", "outcome": "inconclusive"},
        links=[{"rel": "produced", "from": run}])["id"]
    inc = g.create(author="quant", type="claim", inv=inv, fields={
        "statement": "Whether the signal is known in time can't be told from these files.",
        "scope": "prices.csv as given.", "kind": "inconclusive"},
        links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    g.review(author="critic", target=inc, verdict="checked", method="Read the files.", notes="Nothing dates the signal.")
    assert g.stage(q)["complete"]
    _answer(g, inv, q, "risk", "It is look-ahead: the signal agrees with the next day's move, 0.71 of days.", 0.71)
    assert not g.stage(q)["complete"]


def test_an_answer_nobody_may_review_does_not_block():
    g, inv, q = _g()
    mine = _answer(g, inv, q, "critic", "The correlation with the next day's return is 0.34.", 0.34)   # the only reviewer
    theirs = _answer(g, inv, q, "quant", "The signal matches the next day's move on 0.71 of days.", 0.71)
    g.review(author="critic", target=theirs, verdict="checked", method="Re-ran it.", notes="The numbers hold as stated.")
    row = _board(g, inv)["Q1"]
    assert row["status"] == "settled" and row["unreviewable"] == [g.get(mine)["code"]] and row["unchecked"] == []

"""0.4.3: the five vocabulary-friction fixes from an internal study's library notes (items 1, 2, 4, 5, 10).
Each test is the sentence a real model wrote and was refused for."""
import pytest

from hypgraph import Graph, GraphError, Policy

H = "harness"


def _g():
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "Does A beat B.", "objective": "Compare A and B on the same items."})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q2", fields={"text": "Is A significantly more accurate than B?"})["id"]
    return g, inv, q


def _result(g, inv, author, values, summary="Measured what the question asks."):
    r = g.create(author=author, type="run", inv=inv, fields={"kind": "agent", "name": "a run", "state": "succeeded"})
    return g.create(author=author, type="result", inv=inv, fields={"summary": summary, "values": values},
                    links=[{"rel": "produced", "from": r["id"]}])["id"]


# ── item 1: a named p-value is a test ─────────────────────────────────────────
def test_a_named_p_value_backs_significantly():
    g, inv, q = _g()
    rs = _result(g, inv, "stats", {"acc_a": {"value": 0.837}, "acc_b": {"value": 0.796}, "p_exact": {"value": 0.0169}},
                 "Exact McNemar test on the paired items.")
    c = g.create(author="stats", type="claim", inv=inv,
                 fields={"statement": "A is significantly more accurate than B (0.837 vs 0.796, exact McNemar p = 0.0169).",
                         "scope": "The 1,000 paired items; two-sided test at 0.05."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    assert c["code"].startswith("CL")


def test_a_named_p_value_above_the_threshold_is_quoted_back():
    g, inv, q = _g()
    rs = _result(g, inv, "stats", {"acc_a": {"value": 0.805}, "acc_b": {"value": 0.781}, "p_mcnemar": {"value": 0.208}})
    with pytest.raises(GraphError, match="SIGNIFICANCE_NOT_SHOWN"):
        g.create(author="stats", type="claim", inv=inv,
                 fields={"statement": "A is significantly more accurate than B (0.805 vs 0.781, p = 0.208).",
                         "scope": "The 1,000 paired items; two-sided test at 0.05."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])


def test_a_supporting_results_p_field_counts_even_when_the_sentence_omits_it():
    g, inv, q = _g()
    rs = _result(g, inv, "stats", {"acc_a": {"value": 0.837}, "acc_b": {"value": 0.796}, "p_value": {"value": 0.017}})
    c = g.create(author="stats", type="claim", inv=inv,
                 fields={"statement": "A is significantly more accurate than B (0.837 against 0.796).",
                         "scope": "The 1,000 paired items; exact McNemar, two-sided at 0.05."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    assert c["code"].startswith("CL")


def test_significantly_with_no_test_anywhere_is_still_refused():
    g, inv, q = _g()
    rs = _result(g, inv, "stats", {"acc_a": {"value": 0.837}, "acc_b": {"value": 0.796}})
    with pytest.raises(GraphError, match="SIGNIFICANCE_WITHOUT_TEST"):
        g.create(author="stats", type="claim", inv=inv,
                 fields={"statement": "A is significantly more accurate than B (0.837 against 0.796).", "scope": "The 1,000 paired items."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])


# ── item 2: a bound measurement's result supports the claim ───────────────────
def test_a_measurement_counts_as_a_line_of_support():
    g, inv, q = _g()
    rs = _result(g, inv, "analyst", {"acc_a": {"k": 805, "n": 1000}})
    c = g.create(author="analyst", type="claim", inv=inv,
                 fields={"statement": "A is right on 805 of 1000 items.", "scope": "The 1,000 items in items.csv.",
                         "measurements": [{"name": "acc_a", "result": rs, "key": "acc_a", "k": 805, "n": 1000}]},
                 links=[{"rel": "answers", "to": q}])
    st = g.get(c["id"])["state"]
    assert "1 independent line of support" in st["sentence"], st["sentence"]
    assert any(e["rel"] == "supports" and e["src"] == rs for e in g.get(c["id"])["in"])


# ── item 4: a wrong relation names the right one ──────────────────────────────
def test_a_wrong_relation_names_the_ones_that_join():
    g, inv, q = _g()
    r = g.create(author="w", type="run", inv=inv, fields={"kind": "agent", "name": "pytest", "state": "succeeded"})
    with pytest.raises(GraphError) as e:
        g.create(author="w", type="result", inv=inv, fields={"summary": "Ran the tests.", "values": {"passed": {"k": 4, "n": 5}}},
                 links=[{"rel": "executes", "from": r["id"]}])          # a run "executes" the result it produced: wrong relation
    msg = str(e.value)
    assert "executes can't join run → result" in msg and "a run joins a result with produced" in msg         and "a result joins a run with derived_from" in msg


# ── item 5: enum synonyms ─────────────────────────────────────────────────────
def test_enum_synonyms_are_stored_canonically():
    g, inv, q = _g()
    r = g.create(author="w", type="run", inv=inv, fields={"kind": "agent", "name": "pytest", "state": "done"})
    assert g.get(r["id"])["body"]["state"] == "succeeded"
    rs = g.create(author="w", type="result", inv=inv, fields={"summary": "Ran the tests.", "outcome": "success", "kind": "calculated",
                                                             "values": {"passed": {"k": 5, "n": 5}}},
                  links=[{"rel": "produced", "from": r["id"]}])
    assert g.get(rs["id"])["body"]["outcome"] == "positive" and g.get(rs["id"])["body"]["kind"] == "computed"
    c = g.create(author="w", type="claim", inv=inv, fields={"statement": "All 5 of 5 tests pass in tests/test_money.py.",
                                                           "scope": "tests/test_money.py after the fix.", "kind": "fact"},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
    assert g.get(c["id"])["body"]["kind"] == "finding"
    with pytest.raises(GraphError, match="must be one of"):
        g.create(author="w", type="result", inv=inv, fields={"summary": "Ran the tests.", "outcome": "splendid"},
                 links=[{"rel": "produced", "from": r["id"]}])


# ── item 10: small integers bind to a value the sentence names ───────────────
def test_a_small_integer_binds_to_the_field_the_sentence_names():
    g, inv, q = _g()
    rs = _result(g, inv, "quant", {"oos_trades": {"value": 0}, "fees": {"value": 0.001}, "slippage": {"value": 0.0005}})
    c = g.create(author="quant", type="claim", inv=inv,
                 fields={"statement": "The held-out window produced 0 trades after costs, too few to say anything about an edge.",
                         "scope": "Days 600-999 of prices.csv; 10 bp fees and 5 bp slippage per side."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    assert any(m["key"] == "oos_trades" for m in g.get(c["id"])["body"]["measurements"])
    rs2 = _result(g, inv, "solver", {"capacity_total": {"value": 7}, "customers": {"value": 8}, "feasible": {"value": False}})
    c2 = g.create(author="solver", type="claim", inv=inv,
                  fields={"statement": "No feasible assignment exists: total capacity is 7 for 8 customers.",
                          "scope": "instance.csv as given; depots d0, d1, d2."},            # the scope names no numbers: both must bind
                  links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs2}])
    keys = {m["key"] for m in g.get(c2["id"])["body"]["measurements"]}
    assert {"capacity_total", "customers"} <= keys


def test_an_unnamed_small_integer_still_does_not_borrow_a_value():
    g, inv, q = _g()
    rs = _result(g, inv, "quant", {"oos_trades": {"value": 7}})
    with pytest.raises(GraphError, match="UNBOUND_NUMBER"):
        g.create(author="quant", type="claim", inv=inv,
                 fields={"statement": "The strategy wins 7 points.", "scope": "Days 600-999 of prices.csv."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])

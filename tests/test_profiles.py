"""Governance profiles: pinned on the investigation, versioned, enforced by the record — default predicates per
target, domain predicates, write-time refusals, completion criteria. No profile → today's behaviour exactly."""
import pytest

from hypgraph import Graph, GraphError, Policy, profiles
from hypgraph.server import dispatch

H = "harness"


def _g(profile: str = ""):
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    fields = {"title": "A profiled investigation.", "objective": "See the profile's rules hold."}
    if profile:
        fields["profile"] = profile
    inv = g.create(author=H, type="investigation", fields=fields)["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "Does the feature work?"})["id"]
    return g, inv, q


def _run_result(g, inv, author, values, kind="agent", outcome="positive", summary="Measured what the question asks."):
    r = g.create(author=author, type="run", inv=inv, fields={"kind": kind, "name": "a run", "state": "succeeded"})
    rs = g.create(author=author, type="result", inv=inv, fields={"summary": summary, "values": values, "outcome": outcome},
                  links=[{"rel": "produced", "from": r["id"]}])
    return r["id"], rs["id"]


def test_registry_and_unknown_profile_refused():
    assert {"scientific@1", "software@1", "trading@1", "knowledge@1", "optimization@1"} <= set(profiles.PROFILES)
    g = Graph()
    with pytest.raises(GraphError, match="unknown profile"):
        g.create(author="a", type="investigation", fields={"title": "Bad profile.", "objective": "Refuse an unknown profile at creation.", "profile": "alchemy@1"})
    inv = g.create(author="a", type="investigation", fields={"title": "Pinned.", "objective": "Keep the pinned profile as written.", "profile": "Software@1"})["id"]
    assert g.get(inv)["body"]["profile"] == "software@1"            # case-folded, pinned


def test_no_profile_is_todays_behaviour():
    g, inv, q = _g()
    o = g.issue_work(author=H, inv=inv, target=q, assignee="w", objective="Answer Q1 from the files.")
    assert [p["p"] for p in o["done_when"]] == ["claim_made"]
    c = g.completion(inv)
    assert c["profile"] == "scientific@1" and not c["pinned"] and [x["name"] for x in c["criteria"]] == ["questions_settled"]


def test_software_requires_an_instrument_run():
    g, inv, q = _g("software@1")
    o = g.issue_work(author=H, inv=inv, target=q, assignee="tester", objective="Verify the feature with tests.")
    assert [p["p"] for p in o["done_when"]] == ["tests_pass", "claim_made"]
    assert "instrument re-executes it" in o["text"]
    # the tester's own run saying 'positive' is not the instrument's: tests_pass stays NOT MET
    _r, rs = _run_result(g, inv, "tester", {"passed": {"k": 12, "n": 12}})
    chk = g.check_work(o["order"])
    assert not next(p for p in chk["predicates"] if p["p"] == "tests_pass")["met"]
    # 'passes' as a claim is refused without instrument evidence
    with pytest.raises(GraphError, match="PASS_WITHOUT_INSTRUMENT_RUN"):
        g.create(author="tester", type="claim", inv=inv, fields={"statement": "The feature passes all tests.",
                                                                  "scope": "The test suite in tests/."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    # the instrument re-runs it: a lab run replicating the tester's run, positive
    lab = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "re-run", "state": "succeeded"},
                   links=[{"rel": "replicates", "to": _r, "data": {"differs": "same_code"}}])
    lab_rs = g.create(author="lab", type="result", inv=inv, fields={"summary": "Re-ran the tests: 12 of 12 passed.",
                                                                     "values": {"passed": {"k": 12, "n": 12}}, "outcome": "positive"},
                      links=[{"rel": "produced", "from": lab["id"]}])
    assert next(p for p in g.check_work(o["order"])["predicates"] if p["p"] == "tests_pass")["met"]
    cl = g.create(author="tester", type="claim", inv=inv, fields={"statement": "The feature passes all 12 of 12 tests.",
                                                                   "scope": "The test suite in tests/."},
                  links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": lab_rs["id"]}])
    g.review(author="critic", target=cl["id"], verdict="checked", method="Read the lab run.", notes="The numbers hold as stated.")
    comp = g.completion(inv)
    assert comp["complete"] and {c["name"] for c in comp["criteria"]} == {"questions_settled", "requirements_verified"}
    assert "Profile: software@1" in g.briefing(inv)["text"] and "requirements_verified MET" in g.briefing(inv)["text"]


def test_trading_edge_needs_out_of_sample_and_costs():
    g, inv, q = _g("trading@1")
    with pytest.raises(GraphError, match="BACKTEST_WITHOUT_COSTS"):
        _run_result(g, inv, "quant", {"return": {"value": 0.31}, "sharpe": {"value": 1.4}}, summary="Backtested the thesis.")
    # a statistic about returns isn't a return earned: a look-ahead diagnostic needs no costs (studies T1)
    _run_result(g, inv, "quant", {"corr_signal_next_day_return": {"value": 0.338},
                                  "signal_matches_next_return_sign": {"k": 1056, "n": 1499}},
                summary="The signal's correlation with the next day's return.")
    _r, rs_in = _run_result(g, inv, "quant", {"return": {"value": 0.31}, "fees": {"value": 0.002}}, summary="In-sample backtest.")
    with pytest.raises(GraphError, match="EDGE_WITHOUT_OOS_COSTS"):
        g.create(author="quant", type="claim", inv=inv, fields={"statement": "The strategy has an edge of 0.31 a year.",
                                                                 "scope": "Daily bars, 2015–2024."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs_in}])
    _r2, rs_oos = _run_result(g, inv, "quant", {"oos_return": {"value": 0.08}, "fees": {"value": 0.002}}, summary="Out-of-sample backtest.")
    cl = g.create(author="quant", type="claim", inv=inv, fields={"statement": "The strategy has an edge of 0.08 a year out of sample.",
                                                                  "scope": "Daily bars, 2022–2024 held out, after fees."},
                  links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs_oos}])
    o = g.issue_work(author=H, inv=inv, target=q, assignee="quant", objective="Back the thesis out of sample.")
    assert [p["p"] for p in o["done_when"]] == ["backtested_oos", "claim_made"]
    assert not g.completion(inv)["complete"]
    g.review(author="critic", target=cl["id"], verdict="checked", method="Re-ran the OOS window.", notes="The numbers hold as stated.")
    g.create(author=H, type="decision", inv=inv, fields={"choice": "Paper position: 2 % of book, stop at −5 %.",
                                                          "reasons": "The out-of-sample edge survives costs."},
             links=[{"rel": "based_on", "to": cl["id"]}])
    assert g.completion(inv)["complete"]


def test_optimization_optimal_needs_a_bound():
    g, inv, q = _g("optimization@1")
    with pytest.raises(GraphError, match="OBJECTIVE_WITHOUT_FEASIBILITY"):
        _run_result(g, inv, "solver", {"objective": {"value": 412.0}}, summary="Solved the model.")
    _r, rs = _run_result(g, inv, "solver", {"objective": {"value": 412.0}, "feasible": {"value": True}}, summary="Solved the model.")
    with pytest.raises(GraphError, match="OPTIMAL_WITHOUT_BOUND"):
        g.create(author="solver", type="claim", inv=inv, fields={"statement": "The optimal cost is 412.0.",
                                                                  "scope": "The 40-site instance with the stated constraints."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    _r2, rs2 = _run_result(g, inv, "solver", {"objective": {"value": 412.0}, "feasible": {"value": True}, "gap": {"value": 0.0}},
                           summary="Solved to a 0.0 gap.")
    g.create(author="solver", type="claim", inv=inv, fields={"statement": "The optimal cost is 412.0 (gap 0.0).",
                                                              "scope": "The 40-site instance with the stated constraints."},
             links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs2}])
    assert next(c for c in g.completion(inv)["criteria"] if c["name"] == "incumbent_feasible")["met"]


def test_knowledge_claims_cite_sources():
    g, inv, q = _g("knowledge@1")
    with pytest.raises(GraphError, match="CLAIM_WITHOUT_SOURCE"):
        g.create(author="researcher", type="claim", inv=inv, fields={"statement": "The treaty was signed in 1648.",
                                                                      "scope": "The Peace of Westphalia, 1648, as a date.", "kind": "finding"},
                 links=[{"rel": "answers", "to": q}])
    src = g.create(author="researcher", type="source", inv=inv, fields={"citation": "Encyclopaedia entry, Peace of Westphalia.",
                                                                          "url": "https://example.org/westphalia",
                                                                          "passage": "signed in October 1648"})
    cl = g.create(author="researcher", type="claim", inv=inv, fields={"statement": "The treaty was signed in 1648.",
                                                                       "scope": "The Peace of Westphalia, 1648, as a date.", "kind": "finding"},
                  links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src["id"]}])
    o = g.issue_work(author=H, inv=inv, target=q, assignee="researcher", objective="Source the date.")
    assert [p["p"] for p in o["done_when"]] == ["sourced"]
    g.review(author="critic", target=cl["id"], verdict="checked", method="Opened the source.", notes="The source says 1648, as the claim does.")
    assert next(c for c in g.completion(inv)["criteria"] if c["name"] == "all_sourced")["met"]


def test_server_serves_completion_and_profiles():
    g, inv, q = _g("knowledge@1")
    st, body = dispatch(g, "GET", "/completion", {"inv": inv})
    assert st == 200 and body["profile"] == "knowledge@1" and not body["complete"]
    st, body = dispatch(g, "GET", "/profiles")
    assert st == 200 and "trading@1" in body and body["software@1"]["predicates"] == ["tests_pass"]

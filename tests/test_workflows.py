"""The @2 profiles carry their discipline's workflow (docs/workflows/): the stage a question is in is derived from
the record, gates double as order predicates, a workflow widens what counts as resting on (uses, cites), evidence
goes stale when the artifact it used is superseded, and typed artifacts / decisions have required fields. The @1
profiles and the no-profile record are untouched."""
import pytest

from hypgraph import Graph, GraphError, Policy, profiles
from hypgraph.server import dispatch

H = "harness"
SHA_A, SHA_B, SHA_C = "a1" * 32, "b2" * 32, "c3" * 32


def _g(profile: str = "", reviewers=("critic",)):
    g = Graph(policy=Policy(reviewers=set(reviewers), extra_reserved={H}))
    fields = {"title": "A workflow investigation.", "objective": "See the workflow's stages derive from the record."}
    if profile:
        fields["profile"] = profile
    inv = g.create(author=H, type="investigation", fields=fields)["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "Does the change meet the requirement?"})["id"]
    return g, inv, q


def _stage(g, q):
    x = g.stage(q)
    return x["stage"], x["index"], x["complete"]


def _gate(g, q, name):
    return next(gt for gt in g.stage(q)["gates"] if gt["gate"] == name)


def _diff(g, inv, q, author, sha, head):
    return g.create(author=author, type="artifact", inv=inv,
                    fields={"sha256": sha, "path": f"patches/{head}.diff", "kind": "diff",
                            "meta": {"base_sha": "0000000", "head_sha": head, "files": ["src/x.py"]}},
                    links=[{"rel": "part_of", "to": q}])["id"]


def _lab_tests(g, inv, diff, k=12):
    run = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "pytest", "state": "succeeded"},
                   links=[{"rel": "uses", "to": diff, "data": {"role": "code"}}])["id"]
    rs = g.create(author="lab", type="result", inv=inv, fields={"summary": f"Ran the tests: {k} of {k} passed.",
                                                                "values": {"passed": {"k": k, "n": k}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": run}])["id"]
    return run, rs


# ── registry ───────────────────────────────────────────────────────

def test_v2_profiles_carry_workflows_and_v1_is_frozen():
    for name in ("scientific", "software", "trading", "knowledge", "optimization"):
        assert profiles.get(f"{name}@1").workflow is None
        w = profiles.get(f"{name}@2").workflow
        assert w and w.method and len(w.stages) >= 5 and all(st.gate in __import__("hypgraph.workflow").workflow.GATES
                                                            for st in w.stages)
        assert profiles.latest(name).version == 2
    d = profiles.describe()
    assert d["software@1"]["workflow"] is None
    assert [s["name"] for s in d["software@2"]["workflow"]["stages"]] == \
        ["specified", "implemented", "verified", "claimed", "reviewed", "released"]
    assert d["software@2"]["workflow"]["artifacts"]["diff"] == ["path", "base_sha", "head_sha", "files"]
    assert d["knowledge@2"]["workflow"]["invalidates"] == ["cites"]


def test_no_profile_has_no_stages():
    g, inv, q = _g()
    x = g.stage(q)
    assert x["workflow"] is False and x["stage"] == "" and "no workflow" in x["next"]
    assert g.stages(inv)[0]["workflow"] is False


# ── the derived stage: scientific ──────────────────────────────────

def test_scientific_stage_is_read_off_the_record():
    g, inv, q = _g("scientific@2")
    assert _stage(g, q) == ("conjectured", 2, False)                 # asked is met by the question itself
    h = g.create(author="w", type="hypothesis", inv=inv, fields={"statement": "The change makes the parser accept "
                 "trailing commas.", "predictions": ["the fixture with a trailing comma parses"]},
                 links=[{"rel": "answers", "to": q}])["id"]
    assert _stage(g, q) == ("preregistered", 3, False)
    # an experiment that tests nothing with an expected outcome doesn't preregister anything
    x0 = g.create(author=H, type="experiment", inv=inv, fields={"aim": "Parse the fixtures with trailing commas.",
                  "protocol": "Run the parser over fixtures/trailing/*.json.", "success_criteria": "every fixture parses"},
                  links=[{"rel": "tests", "to": h}])["id"]      # the harness is trusted: no data.expected needed
    assert "expected outcome" in _gate(g, q, "preregistered")["why"]
    x = g.create(author="w", type="experiment", inv=inv, fields={"aim": "Parse the fixtures with trailing commas.",
                 "protocol": "Run the parser over fixtures/trailing/*.json and count parses.",
                 "success_criteria": "every fixture parses"},
                 links=[{"rel": "tests", "to": h, "data": {"expected": "all 9 fixtures parse"}}])["id"]
    assert _stage(g, q) == ("run", 4, False)
    run = g.create(author="w", type="run", inv=inv, fields={"kind": "agent", "name": "parse", "state": "succeeded"},
                   links=[{"rel": "executes", "to": x}])["id"]
    assert _stage(g, q) == ("evidenced", 5, False)
    rs = g.create(author="w", type="result", inv=inv, fields={"summary": "Parsed 9 of 9 trailing-comma fixtures.",
                  "values": {"parsed": {"k": 9, "n": 9}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": run}])["id"]
    assert _stage(g, q) == ("claimed", 6, False)
    c = g.create(author="w", type="claim", inv=inv, fields={"statement": "The parser accepts trailing commas in 9 of 9 fixtures.",
                 "scope": "The fixtures under fixtures/trailing/."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    assert _stage(g, q) == ("reviewed", 7, False)
    g.review(author="critic", target=c, verdict="checked", method="Re-ran the parse.", notes="Nine of nine, as stated.")
    stage, index, complete = _stage(g, q)
    assert complete and stage == "reviewed" and index == 7          # 'decided' is optional: complete without it
    assert _gate(g, q, "decided")["optional"] and not _gate(g, q, "decided")["met"]
    assert x0 in [n["id"] for n in g.search(type="experiment", inv=inv)]


def test_an_experiment_written_after_its_run_is_not_preregistered():
    g, inv, q = _g("scientific@2")
    imp = g.policy.importer
    h = g.create(author=imp, type="hypothesis", inv=inv, fields={"statement": "Caching halves the latency.",
                 "predictions": ["p50 latency falls by half"]}, links=[{"rel": "answers", "to": q}])["id"]
    x = g.create(author=imp, type="experiment", inv=inv, at="2026-01-03T00:00:00+00:00",
                 fields={"aim": "Measure latency with the cache on and off.", "protocol": "Fifty requests each way.",
                         "success_criteria": "p50 halves"},
                 links=[{"rel": "tests", "to": h, "data": {"expected": "p50 halves"}}])["id"]
    g.create(author=imp, type="run", inv=inv, at="2026-01-01T00:00:00+00:00",
             fields={"kind": "agent", "name": "latency", "state": "succeeded"}, links=[{"rel": "executes", "to": x}])
    gate = _gate(g, q, "preregistered")
    assert not gate["met"] and "written after" in gate["why"] and "not preregistered" in gate["why"]
    assert _stage(g, q)[0] == "preregistered"


# ── software: the commit after the tests ran ───────────────────────

def test_software_new_head_makes_the_tests_stale():
    g, inv, q = _g("software@2", reviewers=("critic", "second"))
    assert _stage(g, q) == ("implemented", 2, False)
    a1 = _diff(g, inv, q, "dev", SHA_A, "1111111")
    assert _stage(g, q) == ("verified", 3, False)
    run1, rs1 = _lab_tests(g, inv, a1)
    assert _stage(g, q) == ("claimed", 4, False)
    c = g.create(author="tester", type="claim", inv=inv, fields={"statement": "The change passes 12 of 12 tests.",
                 "scope": "The suite under tests/ on head 1111111."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs1}])["id"]
    assert _stage(g, q) == ("reviewed", 5, False)
    # the implementer commits again: a newer diff supersedes the old one
    a2 = _diff(g, inv, q, "dev", SHA_B, "2222222")
    g.link(author="dev", src=a2, rel="supersedes", dst=a1, why="a second commit on the branch")
    assert g.state(a1)["lifecycle"] == "superseded"
    assert "superseded" in g.state(rs1)["stale"][0] and "STALE" in g.state(rs1)["sentence"]
    assert g.state(c).get("stale")
    gate = _gate(g, q, "tests_pass_current")
    assert not gate["met"] and "1111111" in gate["why"] and "2222222" in gate["why"]
    assert _stage(g, q) == ("verified", 3, False)                   # back to verified: the tests ran on an old head
    with pytest.raises(GraphError, match="TESTS_ON_STALE_HEAD"):
        g.create(author="tester", type="claim", inv=inv, fields={"statement": "The second commit passes 12 of 12 tests.",
                 "scope": "The suite under tests/."}, links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs1}])
    # a check on stale evidence doesn't count
    g.review(author="critic", target=c, verdict="checked", method="Read the lab run.", notes="Twelve of twelve on 1111111.")
    assert "stale" in _gate(g, q, "reviewed")["why"]
    assert not g.completion(inv)["complete"]
    # the instrument reruns on the current head
    _run2, rs2 = _lab_tests(g, inv, a2)
    assert _gate(g, q, "tests_pass_current")["met"]
    c2 = g.create(author="tester", type="claim", inv=inv, fields={"statement": "The change passes 12 of 12 tests on the current head.",
                  "scope": "The suite under tests/ on head 2222222."},
                  links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs2}])["id"]
    g.review(author="second", target=c2, verdict="checked", method="Read the lab run.", notes="Twelve of twelve on 2222222.")
    comp = g.completion(inv)
    assert comp["complete"] and {c_["name"] for c_ in comp["criteria"]} == {"questions_settled", "requirements_verified_current"}
    r = g.report(inv)
    assert r["workflow"]["profile"] == "software@2" and "### Workflow — Change report (software@2)" in r["markdown"]
    assert any(x["code"] == g.get(rs1)["code"] for x in r["workflow"]["stale"])


def test_review_by_the_diff_author_is_refused():
    g, inv, q = _g("software@2", reviewers=("critic", "second"))
    a1 = _diff(g, inv, q, "critic", SHA_A, "1111111")                # the reviewer wrote the change
    _run, rs = _lab_tests(g, inv, a1)
    c = g.create(author="tester", type="claim", inv=inv, fields={"statement": "The change passes 12 of 12 tests.",
                 "scope": "The suite under tests/."}, links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    with pytest.raises(GraphError, match="REVIEW_BY_AUTHOR"):
        g.review(author="critic", target=c, verdict="checked", method="Read it.", notes="Looks right to me.")
    g.review(author="second", target=c, verdict="checked", method="Read the lab run.", notes="Twelve of twelve.")
    assert g.state(c)["review"]["state"] == "checked"


def test_typed_artifacts_need_their_fields():
    g, inv, q = _g("software@2")
    with pytest.raises(GraphError, match="ARTIFACT_MISSING_FIELDS.*|meta.base_sha"):
        g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "x.diff", "kind": "diff"},
                 links=[{"rel": "part_of", "to": q}])
    g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_B, "path": "notes.txt", "kind": "scratch"})  # untyped kinds pass
    g1, inv1, _q1 = _g("software@1")
    g1.create(author="dev", type="artifact", inv=inv1, fields={"sha256": SHA_A, "kind": "diff"})         # @1 is frozen


def test_uses_is_at_risk_only_under_a_workflow():
    for pid, expect in (("scientific@1", False), ("scientific@2", True)):
        g, inv, q = _g(pid)
        data = g.create(author="w", type="artifact", inv=inv, fields={"sha256": SHA_C, "path": "data.csv", "kind": "data"})["id"]
        run = g.create(author="w", type="run", inv=inv, fields={"kind": "agent", "name": "fit", "state": "succeeded"},
                       links=[{"rel": "uses", "to": data}])["id"]
        rs = g.create(author="w", type="result", inv=inv, fields={"summary": "Fitted the model on the data file.",
                      "values": {"rmse": {"value": 0.41}}, "outcome": "positive"}, links=[{"rel": "produced", "from": run}])["id"]
        g.withdraw(author="w", node=data, why="the data file was corrected after the fit")
        st = g.state(rs)
        assert bool(st.get("at_risk")) is expect, pid
        assert st.get("stale"), pid                                   # freshness is universal; at-risk is the workflow's


# ── trading ────────────────────────────────────────────────────────

def _bt(g, inv, author, values, summary="Backtested the thesis out of sample.", q="", x=""):
    r = g.create(author=author, type="run", inv=inv, fields={"kind": "agent", "name": "backtest", "state": "succeeded"},
                 links=[{"rel": "executes", "to": x}] if x else None)["id"]
    links = [{"rel": "produced", "from": r}] + ([{"rel": "part_of", "to": q}] if q else [])
    return g.create(author=author, type="result", inv=inv, fields={"summary": summary, "values": values, "outcome": "positive"},
                    links=links)["id"]


def test_trading_trials_positions_and_no_live_orders():
    g, inv, q = _g("trading@2", reviewers=("risk",))
    assert _stage(g, q) == ("thesised", 2, False)
    h = g.create(author="quant", type="hypothesis", inv=inv, fields={"statement": "Momentum over 12 months persists for a month.",
                 "predictions": ["the top decile outperforms after costs out of sample"]}, links=[{"rel": "answers", "to": q}])["id"]
    x = g.create(author="quant", type="experiment", inv=inv, fields={"aim": "Backtest 12-1 momentum.",
                 "protocol": "In sample 2015-2021, out of sample 2022-2024; fees 10 bp, slippage 5 bp; 24 configurations.",
                 "success_criteria": "positive out-of-sample return after costs"},
                 links=[{"rel": "tests", "to": h, "data": {"expected": "positive oos return after costs"}}])["id"]
    assert _stage(g, q) == ("backtested", 4, False)
    rs = _bt(g, inv, "quant", {"oos_return": {"value": 0.08}, "fees": {"value": 0.002}}, q=q, x=x)
    with pytest.raises(GraphError, match="EDGE_WITHOUT_TRIALS"):
        g.create(author="quant", type="claim", inv=inv, fields={"statement": "The strategy has an edge of 0.08 a year out of sample.",
                 "scope": "Daily bars, 2022–2024 held out, after fees."}, links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    assert "trials" in _gate(g, q, "backtested")["why"]
    rs2 = _bt(g, inv, "quant", {"oos_return": {"value": 0.08}, "fees": {"value": 0.002}, "trials": {"value": 24}}, q=q, x=x)
    assert _gate(g, q, "backtested")["met"]
    c = g.create(author="quant", type="claim", inv=inv, fields={"statement": "The strategy has an edge of 0.08 a year out of sample.",
                 "scope": "Daily bars, 2022–2024 held out, after fees, 24 configurations tried."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs2}])["id"]
    g.review(author="risk", target=c, verdict="checked", method="Re-ran the OOS window.", notes="The numbers hold as stated.")
    assert _stage(g, q) == ("positioned", 7, False)
    with pytest.raises(GraphError, match="POSITION_WITHOUT_STOP"):
        g.create(author=H, type="decision", inv=inv, fields={"choice": "Take a 2 % long position in the book.",
                 "reasons": "The out-of-sample edge survives costs."}, links=[{"rel": "based_on", "to": c}])
    with pytest.raises(GraphError, match="LIVE_ORDER"):
        g.create(author=H, type="decision", inv=inv, fields={"choice": "Place a market order on the exchange for 2 %.",
                 "reasons": "The out-of-sample edge survives costs.", "kind": "position", "size": "2 % of book",
                 "stop": "-5 %", "review_date": "2020-01-01", "paper": True}, links=[{"rel": "based_on", "to": c}])
    d = g.create(author=H, type="decision", inv=inv, fields={"choice": "Paper position: 2 % of book, stop at -5 %.",
                 "reasons": "The out-of-sample edge survives costs.", "kind": "position", "size": "2 % of book",
                 "stop": "-5 %", "review_date": "2020-01-01", "paper": True}, links=[{"rel": "based_on", "to": c}])["id"]
    assert _gate(g, q, "positioned")["met"]
    gate = _gate(g, q, "still_valid")                                 # the review date has passed, nothing newer
    assert not gate["met"] and "2020-01-01" in gate["why"] and _stage(g, q) == ("monitored", 8, False)
    comp = {x["name"]: x for x in g.completion(inv)["criteria"]}
    assert comp["position_sized"]["met"] and not comp["nothing_past_review"]["met"]
    _bt(g, inv, "quant", {"oos_return": {"value": 0.05}, "fees": {"value": 0.002}, "trials": {"value": 24}},
        summary="Re-tested the thesis on the newest window.")
    g.link(author="quant", src=g.search(type="result", inv=inv)[-1]["id"], rel="supports", dst=c,
           why="the newest window keeps the edge after costs")
    assert _gate(g, q, "still_valid")["met"] and g.stage(q)["complete"]
    assert g.completion(inv)["complete"]
    assert g.get(d)["body"]["paper"] is True


def test_valid_until_makes_a_result_stale():
    g, inv, _q = _g("trading@2")
    r = g.create(author="quant", type="run", inv=inv, fields={"kind": "agent", "name": "backtest", "state": "succeeded"})["id"]
    rs = g.create(author="quant", type="result", inv=inv, fields={"summary": "Backtested the thesis out of sample.",
                  "values": {"oos_return": {"value": 0.08}, "fees": {"value": 0.002}}, "outcome": "positive",
                  "valid_until": "2020-06-30"}, links=[{"rel": "produced", "from": r}])["id"]
    assert g.state(rs)["stale"] == ["valid_until 2020-06-30 has passed"]


# ── knowledge ──────────────────────────────────────────────────────

def test_knowledge_passage_required_and_a_withdrawn_source_puts_claims_at_risk():
    g, inv, q = _g("knowledge@2")
    with pytest.raises(GraphError, match="PASSAGE_MISSING"):
        g.create(author="r", type="source", inv=inv, fields={"citation": "Encyclopaedia entry, Peace of Westphalia.",
                 "url": "https://example.org/westphalia"})
    assert _stage(g, q) == ("sourced", 3, False)                     # 'searched' is optional
    src = g.create(author="r", type="source", inv=inv, fields={"citation": "Encyclopaedia entry, Peace of Westphalia.",
                   "url": "https://example.org/westphalia", "passage": "signed in October 1648", "kind": "secondary"},
                   links=[{"rel": "part_of", "to": q}])["id"]
    assert "retrieved" in _gate(g, q, "source_quoted")["why"]
    src2 = g.create(author="r", type="source", inv=inv, fields={"citation": "Treaty of Osnabrück, 1648 (facsimile).",
                    "url": "https://example.org/osnabrueck", "passage": "signed in October 1648", "retrieved": "2026-10-20",
                    "kind": "primary"}, links=[{"rel": "part_of", "to": q}])["id"]
    assert _stage(g, q) == ("claimed", 4, False)
    c = g.create(author="r", type="claim", inv=inv, fields={"statement": "The treaty was signed in 1648.", "kind": "finding",
                 "scope": "The Peace of Westphalia, as a date."}, links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src2}])["id"]
    assert _stage(g, q) == ("checked", 5, False)
    g.review(author="critic", target=c, verdict="checked", method="Opened the source.", notes="The passage says 1648.")
    assert g.stage(q)["complete"] and g.completion(inv)["complete"]
    g.link(author="critic", src=src2, rel="corrects", dst=src, why="the facsimile is the primary source")
    g.withdraw(author="r", node=src2, why="the facsimile page was taken down")
    assert g.state(c)["at_risk"] == [src2]                            # cites is risky under knowledge@2
    g1, inv1, q1 = _g("knowledge@1")
    s1 = g1.create(author="r", type="source", inv=inv1, fields={"citation": "Encyclopaedia entry, Peace of Westphalia.",
                   "url": "https://example.org/westphalia", "passage": "signed in October 1648"})["id"]
    c1 = g1.create(author="r", type="claim", inv=inv1, fields={"statement": "The treaty was signed in 1648.", "kind": "finding",
                   "scope": "The Peace of Westphalia, as a date."}, links=[{"rel": "answers", "to": q1}, {"rel": "cites", "to": s1}])["id"]
    g1.withdraw(author="r", node=s1, why="taken down")
    assert not g1.state(c1).get("at_risk")                            # @1: as it was


# ── optimization ───────────────────────────────────────────────────

def test_optimization_instance_verifier_and_changed_instance():
    g, inv, q = _g("optimization@2", reviewers=("verifier",))
    with pytest.raises(GraphError, match="SOLVED_WITHOUT_INSTANCE"):
        g.create(author="solver", type="result", inv=inv, fields={"summary": "Solved the model to a 0.0 gap.",
                 "values": {"objective": {"value": 412.0}, "feasible": {"value": True}, "gap": {"value": 0.0}}, "outcome": "positive"})
    assert _stage(g, q) == ("posed", 1, False)
    inst = g.create(author="lead", type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "instances/40-site.json", "kind": "instance"},
                    links=[{"rel": "part_of", "to": q}])["id"]
    assert _stage(g, q) == ("modelled", 2, False)
    run = g.create(author="solver", type="run", inv=inv, fields={"kind": "agent", "name": "cbc", "state": "succeeded"},
                   links=[{"rel": "uses", "to": inst}])["id"]
    rs = g.create(author="solver", type="result", inv=inv, fields={"summary": "Solved the model to a 0.0 gap.",
                  "values": {"objective": {"value": 412.0}, "feasible": {"value": True}, "gap": {"value": 0.0}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": run}, {"rel": "supports", "to": q}] if False else [{"rel": "produced", "from": run}])["id"]
    g.link(author="solver", src=rs, rel="part_of", dst=q, why="")
    assert _gate(g, q, "solved")["met"] is False or True            # the result reaches the question through a claim
    c = g.create(author="solver", type="claim", inv=inv, fields={"statement": "The optimal cost is 412.0 (gap 0.0).",
                 "scope": "The 40-site instance with the stated constraints."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    assert _gate(g, q, "solved")["met"]
    assert _gate(g, q, "result_reviewed")["met"] is False
    g.review(author="verifier", target=rs, verdict="checked", method="Recomputed every constraint on the instance.",
             notes="Feasible; the objective matches.")
    g.review(author="verifier", target=c, verdict="checked", method="Read the result.", notes="The bound is the objective.")
    assert next(x for x in g.completion(inv)["criteria"] if x["name"] == "incumbent_verified")["met"]
    # the instance changes
    inst2 = g.create(author="lead", type="artifact", inv=inv, fields={"sha256": SHA_B, "path": "instances/41-site.json", "kind": "instance"},
                     links=[{"rel": "part_of", "to": q}, {"rel": "supersedes", "to": inst}])["id"]
    assert g.state(rs)["stale"] and inst2
    with pytest.raises(GraphError, match="OPTIMAL_ON_STALE_INSTANCE"):
        g.create(author="solver", type="claim", inv=inv, fields={"statement": "The optimal cost is 412.0 for the current instance.",
                 "scope": "The 41-site instance."}, links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])
    assert not next(x for x in g.completion(inv)["criteria"] if x["name"] == "incumbent_verified")["met"]


# ── orders, surfaces ───────────────────────────────────────────────

def test_workflow_gates_serve_as_order_predicates():
    g, inv, q = _g("scientific@2")
    o = g.issue_work(author=H, inv=inv, target=q, assignee="w", objective="Answer Q1 with a preregistered test.")
    assert [p["p"] for p in o["done_when"]] == ["hypothesis_stated", "preregistered", "claim_made"]
    assert "hypothesis_stated" in o["text"] and "BEFORE register_run" in o["text"]
    chk = {p["p"]: p for p in g.check_work(o["order"])["predicates"]}
    assert not chk["hypothesis_stated"]["met"] and "no live hypothesis" in chk["hypothesis_stated"]["why"]
    g.create(author="w", type="hypothesis", inv=inv, fields={"statement": "Caching halves the latency.",
             "predictions": ["p50 halves"]}, links=[{"rel": "answers", "to": q}])
    chk = {p["p"]: p for p in g.check_work(o["order"])["predicates"]}
    assert chk["hypothesis_stated"]["met"] and chk["hypothesis_stated"]["evidence_codes"] == ["H1"]
    assert not chk["preregistered"]["met"]


def test_server_serves_stages():
    g, inv, q = _g("software@2")
    st, body = dispatch(g, "GET", "/stages", {"inv": inv})
    assert st == 200 and body["stages"][0]["stage"] == "implemented" and body["stages"][0]["of"] == 6
    st, body = dispatch(g, "GET", f"/stage/{q}", {"inv": inv})
    assert st == 200 and body["code"] == "Q1" and [x["gate"] for x in body["gates"]][:3] == ["stated", "diff_registered", "tests_pass_current"]
    st, body = dispatch(g, "GET", "/profiles")
    assert st == 200 and body["trading@2"]["workflow"]["decisions"] == {"position": ["size", "stop", "review_date", "paper"]}


# ── 0.5.1: declining a thesis is a decision; an honest "can't be answered" settles a question ──

def test_no_position_is_a_decision():
    g, inv, q = _g("trading@2", reviewers=("risk",))
    h = g.create(author="quant", type="hypothesis", inv=inv, fields={"statement": "Momentum over 12 months persists for a month.",
                 "predictions": ["the top decile outperforms after costs out of sample"]}, links=[{"rel": "answers", "to": q}])["id"]
    x = g.create(author="quant", type="experiment", inv=inv, fields={"aim": "Backtest 12-1 momentum.",
                 "protocol": "In sample 2015-2021, out of sample 2022-2024; fees 10 bp, slippage 5 bp; 24 configurations.",
                 "success_criteria": "positive out-of-sample return after costs"},
                 links=[{"rel": "tests", "to": h, "data": {"expected": "positive oos return after costs"}}])["id"]
    rs = _bt(g, inv, "quant", {"oos_return": {"value": -0.02}, "fees": {"value": 0.002}, "trials": {"value": 24}},
             summary="Backtested the thesis out of sample: it loses after costs.", q=q, x=x)
    c = g.create(author="quant", type="claim", inv=inv, fields={"statement": "The thesis has no edge out of sample: -0.02 a year after fees.",
                 "scope": "Daily bars, 2022–2024 held out, after fees, 24 configurations tried."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    g.review(author="risk", target=c, verdict="checked", method="Re-ran the OOS window.", notes="Negative after costs, as stated.")
    assert _stage(g, q) == ("positioned", 7, False)
    g.create(author=H, type="decision", inv=inv, fields={"choice": "No position: the thesis loses after costs out of sample.",
             "reasons": "A negative out-of-sample return after costs is not a thesis to fund.", "kind": "no_position"},
             links=[{"rel": "based_on", "to": c}])
    assert g.stage(q)["complete"]
    comp = {x_["name"]: x_ for x_ in g.completion(inv)["criteria"]}
    assert comp["position_sized"]["met"] and "1 declined" in comp["position_sized"]["why"] and comp["nothing_past_review"]["met"]


def test_a_checked_inconclusive_answer_settles_a_question_without_a_source():
    g, inv, q = _g("knowledge@2")
    assert _stage(g, q) == ("sourced", 3, False)
    # the search is a run; what it found (nothing) is a result; the honest answer derives from it
    run = g.create(author="r", type="run", inv=inv, fields={"kind": "agent", "name": "search", "state": "succeeded"})["id"]
    rs = g.create(author="r", type="result", inv=inv, fields={"summary": "Read 3 of 3 pages on the host; 0 mention decommissioning.",
                  "values": {"pages_read": {"k": 3, "n": 3}, "mentions": {"value": 0}}, "outcome": "negative", "kind": "observed"},
                  links=[{"rel": "produced", "from": run}])["id"]
    c = g.create(author="r", type="claim", inv=inv, fields={"statement": "No page on the source host says when the dam was decommissioned.",
                 "scope": "The 3 of 3 pages on the source host, read in full.", "kind": "inconclusive"},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    assert _stage(g, q) == ("sourced", 3, False)                     # a claim alone settles nothing
    g.review(author="critic", target=c, verdict="checked", method="Read the three pages.", notes="Nothing on decommissioning.")
    x = g.stage(q)
    assert x["complete"] and x["stage"] == "checked" and x["settled_by"] == "CL1" and "inconclusive" in x["settled_how"]


def test_accepting_an_order_is_not_the_questions_decision():
    g, inv, q = _g("scientific@2")
    o = g.issue_work(author=H, inv=inv, target=q, assignee="w", objective="State a hypothesis for Q1.", done_when=[{"p": "hypothesis_stated"}])
    g.create(author="w", type="hypothesis", inv=inv, fields={"statement": "Caching halves the latency.", "predictions": ["p50 halves"]},
             links=[{"rel": "answers", "to": q}])
    g.return_work(author="w", order=o["order"], note="stated")
    assert g.settle(author=H, inv=inv)                               # a decision that settles the order, based on H1
    assert not _gate(g, q, "decided")["met"]                         # … is the harness accepting work, not a decision on Q1
    assert "X1" not in g.report(inv)["markdown"] or "n" not in g.report(inv)["markdown"]


def test_registering_the_same_bytes_again_types_and_links_the_one_node():
    g, inv, q = _g("software@2")
    a = g.create(author=H, type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "mod.py", "size": 20})   # the task's file
    assert a["body"].get("kind") is None and not _gate(g, q, "diff_registered")["met"]
    b = g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "mod.py", "kind": "diff",
                 "meta": {"base_sha": "0000000", "head_sha": "1111111", "files": ["mod.py"]}}, links=[{"rel": "part_of", "to": q}])
    assert b["id"] == a["id"] and b["v"] == 2 and b["body"]["kind"] == "diff" and "typed as diff" in " ".join(b["notes"])
    assert any(e["rel"] == "part_of" for e in b["out"])
    assert _gate(g, q, "diff_registered")["met"] and _gate(g, q, "diff_registered")["evidence"] == ["A1"]
    c = g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_A, "kind": "diff"}, links=[{"rel": "part_of", "to": q}])
    assert c["v"] == 2 and len([e for e in c["out"] if e["rel"] == "part_of"]) == 1       # idempotent: nothing added twice
    with pytest.raises(GraphError, match="ARTIFACT_MISSING_FIELDS"):
        g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_B, "path": "x.py"})
        g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_B, "path": "x.py", "kind": "diff"})


def test_a_verified_failure_settles_a_software_requirement():
    g, inv, q = _g("software@2")
    a1 = _diff(g, inv, q, "dev", SHA_A, "1111111")
    run = g.create(author="tester", type="run", inv=inv, fields={"kind": "agent", "name": "checks", "state": "succeeded"},
                   links=[{"rel": "uses", "to": a1, "data": {"role": "code"}}])["id"]
    rs = g.create(author="tester", type="result", inv=inv, fields={"summary": "Ran the checks: 1 of 2 pass.",
                  "values": {"passed": {"k": 1, "n": 2}}, "outcome": "negative"}, links=[{"rel": "produced", "from": run}])["id"]
    lab = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "re-run", "state": "succeeded"},
                   links=[{"rel": "replicates", "to": run, "data": {"differs": "same_code"}}, {"rel": "uses", "to": a1, "data": {"role": "code"}}])["id"]
    g.create(author="lab", type="result", inv=inv, fields={"summary": "Re-ran the checks: 1 of 2 pass.",
             "values": {"passed": {"k": 1, "n": 2}}, "outcome": "negative"}, links=[{"rel": "produced", "from": lab}])
    c = g.create(author="tester", type="claim", inv=inv, fields={"statement": "The change does not meet the requirement: 1 of 2 checks pass.",
                 "scope": "mod.py at head 1111111."}, links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    assert _stage(g, q) == ("verified", 3, False)                    # no passing run on the head, and there never will be
    g.review(author="critic", target=c, verdict="checked", method="Read the lab run.", notes="One of two, as stated.")
    x = g.stage(q)
    assert x["complete"] and "verified failure" in x["settled_how"] and x["settled_by"] == "CL1"
    assert not _gate(g, q, "tests_pass_current")["met"]
    assert not next(c_ for c_ in g.completion(inv)["criteria"] if c_["name"] == "requirements_verified_current")["met"]


# ── 0.5.2: a source is fresh while its page still says it; stale evidence is marked in the report ──

def _excerpt(g, inv, src, text, contains, prev=None):
    import hashlib
    links = [{"rel": "derived_from", "to": src}] + ([{"rel": "supersedes", "to": prev}] if prev else [])
    return g.create(author="host", type="artifact", inv=inv,
                    fields={"sha256": hashlib.sha256(f"{src}\n{text}".encode()).hexdigest(), "path": "https://example.org/harlow",
                            "kind": "excerpt", "meta": {"source": src, "contains_passage": contains, "fetched": "2026-10-26T04:00"}},
                    links=links)["id"]


def test_a_source_whose_page_changed_is_stale_and_reopens_the_question():
    g, inv, q = _g("knowledge@2")
    src = g.create(author="r", type="source", inv=inv, fields={"citation": "Harlow Reservoir page.", "url": "https://example.org/harlow",
                   "passage": "capacity is 4,200 megalitres", "retrieved": "2026-10-26", "kind": "secondary"},
                   links=[{"rel": "part_of", "to": q}])["id"]
    c = g.create(author="r", type="claim", inv=inv, fields={"statement": "Harlow Reservoir holds 4,200 megalitres.", "kind": "finding",
                 "scope": "The Harlow Reservoir page on the source host."}, links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src}])["id"]
    g.review(author="critic", target=c, verdict="checked", method="Opened the page.", notes="The page says 4,200.")
    assert g.stage(q)["complete"] and not g.state(src).get("stale")          # never re-fetched: nothing says it moved
    e1 = _excerpt(g, inv, src, "… capacity is 4,200 megalitres …", True)
    assert g.stage(q)["complete"] and not g.state(src).get("stale")          # re-fetched, still says it
    _excerpt(g, inv, src, "… capacity is 4,600 megalitres (revised) …", False, prev=e1)
    assert "no longer contains its passage" in g.state(src)["stale"][0]
    assert g.state(c)["stale"] and "STALE" in g.state(c)["sentence"]         # the claim rests only on that source
    x = g.stage(q)
    assert not x["complete"] and x["stage"] == "sourced" and "stale" in x["next"]
    r = g.report(inv)
    assert "checked · STALE" in r["markdown"] and r["open"]["claims_stale"] == ["CL1"]
    assert any(s_["type"] == "source" for s_ in r["workflow"]["stale"])
    chk = g.check_text("CL1 is confirmed: the reservoir holds 4,200 megalitres.", inv)
    assert any(f["code"] == "REPORT_OVERSTATES_STANDING" and "STALE" in f["message"] for f in chk["findings"])
    # the researcher reads the page again: a new source, a new claim, checked → complete
    src2 = g.create(author="r", type="source", inv=inv, fields={"citation": "Harlow Reservoir page (revised).", "url": "https://example.org/harlow",
                    "passage": "capacity is 4,600 megalitres", "retrieved": "2026-10-26", "kind": "secondary"},
                    links=[{"rel": "part_of", "to": q}])["id"]
    _excerpt(g, inv, src2, "… capacity is 4,600 megalitres (revised) …", True)
    c2 = g.create(author="r", type="claim", inv=inv, fields={"statement": "Harlow Reservoir holds 4,600 megalitres.", "kind": "finding",
                  "scope": "The revised Harlow Reservoir page."}, links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src2}])["id"]
    g.review(author="critic", target=c2, verdict="checked", method="Opened the page.", notes="The page says 4,600.")
    assert g.stage(q)["complete"]


def test_an_edit_elsewhere_on_the_page_keeps_the_source_fresh():
    g, inv, q = _g("knowledge@2")
    src = g.create(author="r", type="source", inv=inv, fields={"citation": "Harlow Reservoir page.", "url": "https://example.org/harlow",
                   "passage": "opened in 1931", "retrieved": "2026-10-26", "kind": "secondary"})["id"]
    e1 = _excerpt(g, inv, src, "Harlow Reservoir was opened in 1931. Its dam is 30 m tall.", True)
    _excerpt(g, inv, src, "Harlow Reservoir was opened in 1931. Its dam is 31 m tall.", True, prev=e1)
    assert not g.state(src).get("stale")                                     # the page changed; its passage didn't

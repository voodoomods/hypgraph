"""Shape refusals — a field, an option or a link the schema doesn't have — are coded, logged with the body, kept
apart from overclaims in the report, skipped by the replay, and say where the thing goes. A sixteen-challenge sweep's
run logs held 217 of them against 79 overclaims; the log saw none."""
import pytest

from hypgraph import Graph, GraphError, Policy


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    lead = g.author("lead")
    inv = lead.investigation("Shapes", "Find out which shape refusals the record logs.")["id"]
    h = lead.add("hypothesis", inv, statement="The fast path is faster than the slow one on the given input.",
                 predictions=["The fast path's median time is under half the slow one's."])["id"]
    return g, inv, h


def _codes(e):
    return {p["code"] for p in e.problems}


def test_code_on_a_result_is_refused_with_where_it_goes_and_logged(env):
    g, inv, _ = env
    tester = g.author("tester")
    with pytest.raises(GraphError) as e:
        tester.add("result", inv, summary="Ran the tests on the fixed file: 6 passed.", code=["run_tests.py"],
                   values={"n_passed": 6})
    assert _codes(e.value) == {"SHAPE_UNKNOWN_FIELD"}
    assert "belongs to the run" in str(e.value) and "produced" in str(e.value)
    row = g.refusals(inv)[0]
    assert row["type"] == "shape" and row["codes"] == ["SHAPE_UNKNOWN_FIELD"]
    assert row["statement"] == "Ran the tests on the fixed file: 6 passed."
    assert row["problems"][0]["words"] == ["code"]


def test_data_on_an_experiment_points_at_the_tests_link(env):
    g, inv, h = env
    with pytest.raises(GraphError) as e:
        g.author("tester").add("experiment", inv, aim="Time both paths on the same input.",
                               protocol="Median of 7 timeit repeats of each function on 20,000 ints.",
                               success_criteria="The fast path's median is under half the slow one's.",
                               data={"expected": "fast < slow"})
    assert _codes(e.value) == {"SHAPE_UNKNOWN_FIELD"} and "tests" in str(e.value) and "data: {expected" in str(e.value)


def test_an_outcome_word_outside_the_options_is_explained_and_logged(env):
    g, inv, _ = env
    with pytest.raises(GraphError) as e:
        g.author("tester").add("result", inv, summary="Ran the tests on the fixed file: 6 passed.", outcome="verified",
                               values={"n_passed": 6})
    assert _codes(e.value) == {"SHAPE_NOT_AN_OPTION"}
    assert "positive: what the summary describes was seen" in str(e.value)
    assert g.refusals(inv)[0]["type"] == "shape"
    # a synonym the map knows still passes
    ok = g.author("tester").add("result", inv, summary="Ran the tests on the fixed file: 6 passed.", outcome="passed",
                                values={"n_passed": 6})
    assert ok["body"]["outcome"] == "positive" and ok.get("fixes_refusals")   # and it fixes the shape refusal


def test_a_link_the_grammar_refuses_is_coded_and_logged(env):
    g, inv, h = env
    tester = g.author("tester")
    r = tester.add("result", inv, summary="Median of 7 repeats: fast 0.4 ms, slow 330 ms.",
                   values={"fast_ms": 0.4, "slow_ms": 330})["id"]
    with pytest.raises(GraphError) as e:
        tester.link(r, "answers", h)                       # a result doesn't answer; a claim does
    assert _codes(e.value) == {"LINK_NOT_ALLOWED"}
    row = g.refusals(inv)[0]
    assert row["type"] == "link" and row["codes"] == ["LINK_NOT_ALLOWED"] and row["op"] == "link"
    with pytest.raises(GraphError) as e:
        tester.add("result", inv, summary="Median of 9 repeats: fast 0.4 ms, slow 331 ms.",
                   values={"fast_ms": 0.4, "slow_ms": 331}, links=[{"rel": "answers", "to": h}])
    assert _codes(e.value) == {"LINK_NOT_ALLOWED"} and g.refusals(inv)[0]["op"] == "create"


def test_the_report_keeps_shape_apart_and_the_replay_skips_it(env):
    g, inv, _ = env
    tester = g.author("tester")
    with pytest.raises(GraphError):
        tester.add("result", inv, summary="Ran the tests: 6 passed.", code=["run_tests.py"], values={"n_passed": 6})
    r = tester.add("result", inv, summary="Ran the tests: 6 passed.", values={"n_passed": {"k": 6, "n": 6}})["id"]
    with pytest.raises(GraphError):
        tester.add("claim", inv, statement="The fix never breaks a test.", scope="test_semver.py's 6 tests.",
                   links=[{"rel": "derived_from", "to": r}])
    rep = g.refusal_report(inv)
    assert rep["refused"] == 1 and "ABSOLUTE_WITHOUT_COUNT" in rep["by_code"]
    assert rep["shape"]["refused"] == 1 and rep["shape"]["by_code"] == {"SHAPE_UNKNOWN_FIELD": 1}
    assert "Shape refusals — 1 refused" in rep["markdown"]
    rp = g.replay_refusals(inv)
    assert rp["replayed"] == 1 and rp["skipped"] == {"shape": 1}

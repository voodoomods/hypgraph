"""A version string or inline code in a claim is an identifier, not a figure to bind (studies: a correct claim about
semver.compare was refused twice for "1.10" and "1.9", and its author then bound it to the wrong result)."""
from hypgraph import Graph, GraphError
from hypgraph.checks import numbers


def test_versions_and_inline_code_are_not_figures():
    assert [x[3] for x in numbers('compare("1.10.0", "1.9.0") returns 1 on v2.0.0-rc.1')] == ["1"]
    assert [x[3] for x in numbers("the `range(10)` call took 0.45 ms")] == ["0.45"]
    assert [x[3] for x in numbers("p99 fell from 840 ms to 210 ms")] == ["840", "210"]


def test_a_claim_naming_versions_binds_only_its_measurements(tmp_path):
    g = Graph(tmp_path / "r.hypgraph")
    inv = g.author("lead").investigation("Why do the semver tests fail?", "Find why tests fail on the original code.")["id"]
    a = g.author("tester")
    rs = a.add("result", inv, summary="On the original code 3 of 6 tests fail.",
               values={"failed": {"k": 3, "n": 6}})["id"]
    cl = a.add("claim", inv, statement='On the original code 3 of 6 tests fail: compare("1.10.0", "1.9.0") orders them backwards '
                                       "because `parse` keeps the parts as strings.",
               scope="test_semver.py at the base commit.", links=[{"rel": "derived_from", "to": rs}])
    assert cl["id"]
    try:
        a.add("claim", inv, statement="On the original code 4 of 6 tests fail.", scope="test_semver.py at the base.",
              links=[{"rel": "derived_from", "to": rs}])
        raise AssertionError("an unbound 4 should still be refused")
    except GraphError as e:
        assert "UNBOUND_NUMBER" in str(e)
    g.close()

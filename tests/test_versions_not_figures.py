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


def test_labels_are_not_figures():
    assert [x[3] for x in numbers("fails to reject cases 9 (''), 10 ('30m1h') and 12 ('-5s')")] == []
    assert [x[3] for x in numbers("cases 9-12 are accepted; see #3 and test 4")] == []
    assert [x[3] for x in numbers("case 8 returns 2 instead of 3")] == ["2", "3"]
    assert [x[3] for x in numbers("satisfies 7 of the 12 cases")] == ["7", "12"]


def test_a_value_s_key_in_place_of_its_number_is_refused(tmp_path):
    """Models dodged UNBOUND_NUMBER by writing value names into sentences ("expects case8_expected") (studies E4)."""
    g = Graph(tmp_path / "r.hypgraph")
    inv = g.author("lead").investigation("Does parse_duration meet its spec?", "Check each case in SPEC.md.")["id"]
    a = g.author("tester")
    rs = a.add("result", inv, summary="Case 8 returns 2; the spec expects 3.",
               values={"case8_got": {"value": 2}, "case8_expected": {"value": 3}})["id"]
    m = [{"name": "got", "key": "case8_got", "result": rs}, {"name": "expected", "key": "case8_expected", "result": rs}]
    try:
        a.add("claim", inv, statement="Case 8 expects case8_expected but returns case8_got.", scope="SPEC.md case 8.",
              measurements=m, links=[{"rel": "derived_from", "to": rs}])
        raise AssertionError("a key in place of a number should be refused")
    except GraphError as e:
        assert "KEY_FOR_NUMBER" in str(e) and "case8_expected" in str(e)
    ok = a.add("claim", inv, statement="Case 8 returns 2 where the spec expects 3.", scope="SPEC.md case 8.",
               measurements=m, links=[{"rel": "derived_from", "to": rs}])
    assert ok["id"]
    g.close()



def _claim_error(db, stmt: str) -> str:
    g = Graph(db)
    inv = g.author("lead").investigation("Does parse_duration meet its spec?", "Check each case in SPEC.md.")["id"]
    a = g.author("tester")
    rs = a.add("result", inv, summary="Case 8 returns 2; the spec expects 3.", values={"got": {"value": 2}})["id"]
    try:
        a.add("claim", inv, statement=stmt, scope="SPEC.md case 8, one run.", links=[{"rel": "derived_from", "to": rs}])
        return ""
    except GraphError as e:
        return str(e)
    finally:
        g.close()


def test_a_statement_that_says_nothing_is_refused(tmp_path):
    """A claim written only to clear a gate ("Placeholder.") stayed in the record, contested (studies E2)."""
    for i, stmt in enumerate(("Placeholder.", "Placeholder claim.", "TBD — pending.", "To be determined.", "1234567890 ...")):
        assert "STATEMENT_EMPTY" in _claim_error(tmp_path / f"{i}.hypgraph", stmt), stmt
    assert _claim_error(tmp_path / "real.hypgraph", "parse_duration truncates rather than rounds.") == ""

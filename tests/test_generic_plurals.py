"""A bare plural that is what the bound count counts says it of every one.

Found in the say-no-more-than-the-data showcase (gpt-oss-20b on the BC-250 boards, 2026-11-15): "Malformed files
rejected with clear errors" went in on 23 of 24 malformed files rejected with a clear error, ten times over two runs,
while "every malformed file rejected" on the same counts was refused. No true headline of those runs had this shape:
the true ones said "nearly all", "most", a number, or named the exception.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "This test campaign, one run of each."


def env(k, n, what="malformed files rejected with a clear error"):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle bad input?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary=f"{k} of {n} {what}.",
                            values={"count": {"k": k, "n": n}})["id"]
    return g, inv, r, {"name": what, "result": r, "key": "count", "k": k, "n": n}


def write(case, statement):
    g, inv, r, m = case
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=[m],
        links=[{"rel": "supports", "from": r, "why": "The campaign count this headline reports."}])


@pytest.mark.parametrize("statement", [
    "Malformed files rejected with clear errors.",
    "Malformed Files Rejected with Clear, Precise Errors.",
    "Malformed files meet clear rejection—error clarity that builds trust.",
    "Malformed files rejected with crystal-clear errors—transparency at its best."])
def test_a_bare_plural_on_a_count_with_exceptions_is_refused(statement):
    with pytest.raises(GraphError) as e:
        write(env(23, 24), statement)
    assert "COUNT_CONTRADICTS" in [p["code"] for p in e.value.problems], e.value.problems


def test_the_plural_may_open_a_later_clause():
    case = env(3, 7, "files over 1 GB parsed within the time budget")
    with pytest.raises(GraphError) as e:
        write(case, "Heavyweights handled swiftly, big files parsed on time.")
    assert "COUNT_CONTRADICTS" in [p["code"] for p in e.value.problems], e.value.problems


@pytest.mark.parametrize("statement", [
    "Nearly all malformed files rejected with clear errors.",
    "Most malformed files rejected with clear errors.",
    "23 of 24 malformed files rejected with clear errors.",
    "Malformed files rejected with clear errors, but one slipped through.",
    "Twenty-three malformed files rejected with clear errors.",
    "Clear errors greet malformed input."])               # the counted noun isn't its subject
def test_a_qualified_or_unrelated_statement_goes_in(statement):
    write(env(23, 24), statement)


def test_a_bare_plural_on_a_count_without_exceptions_goes_in():
    write(env(24, 24), "Malformed files rejected with clear errors.")

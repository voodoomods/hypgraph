"""Absolutes with no "all" in them: "parsed flawlessly", "without a single error", "error-free".

Found in the say-no-more-than-the-data showcase (gpt-oss-20b on the BC-250 boards, 2026-11-15): "Real-world files
parsed flawlessly" on 76 of 77, "Real-World Files Parsed Without a Single Error" on 52 of 55 went in, while "every
real-world file parsed" on the same counts was refused. These say of how things went what "every" says of how many.
They cover every one of their subject only when the subject does: the true headlines of the same run ("nearly all
real-world files parsed flawlessly", "72 of 73 files parsed without error", "flawlessly, only a handful slipped")
still go in.
"""
import pytest

from hypgraph import Graph, GraphError
from hypgraph import language as L

SCOPE = "This test campaign, one run of each."


@pytest.fixture
def env():
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle real files?",
                                             scope="One run of each test suite and file set.")["id"]
    lab = g.author("lab")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="62 of 63 real-world files parsed.",
                values={"real_count": {"k": 62, "n": 63}})["id"]
    return g, inv, r


def write(g, inv, r, statement):
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE,
        measurements=[{"name": "real-world files parsed", "result": r, "key": "real_count", "k": 62, "n": 63}],
        links=[{"rel": "supports", "from": r, "why": "The campaign count this headline reports."}])


@pytest.mark.parametrize("statement", [
    "Real-world files parsed flawlessly.",
    "Real-world files parsed flawlessly, unmatched accuracy.",
    "Real-World Files Parsed Without Error",
    "Real-world files parsed without a single error.",
    "Real-world file parsing is error-free."])
def test_a_manner_absolute_the_count_contradicts_is_refused(env, statement):
    g, inv, r = env
    with pytest.raises(GraphError) as e:
        write(g, inv, r, statement)
    assert "COUNT_CONTRADICTS" in [p["code"] for p in e.value.problems], e.value.problems


@pytest.mark.parametrize("statement", [
    "Nearly all real-world files parsed flawlessly.",
    "The vast majority of real-world files parsed flawlessly.",
    "62 of 63 real-world files parsed without error.",
    "Real-world files parsed flawlessly, only one slipped.",
    "Real-world files parsed flawlessly except one.",
    "Most real-world files parsed without a single error."])
def test_a_manner_absolute_said_of_a_part_goes_in(env, statement):
    g, inv, r = env
    write(g, inv, r, statement)


@pytest.mark.parametrize("statement,words", [
    ("The parser ran flawlessly.", ["flawlessly"]),
    ("Files were parsed without any crashes.", ["without any crashes"]),
    ("The build is bug-free.", ["bug-free"]),
    ("The parser did not run flawlessly.", []),                       # negated
    ("Is the parser error-free?", []),                                # a question
    ("The test ran without exception.", ["without exception"])])      # was already an absolute
def test_which_manner_words_are_asserted(statement, words):
    assert L.asserted(L.ABSOLUTE, statement) == words


# The qualified headlines of the same showcase's run 2, all true of their counts and all refused as absolutes:
# "near-perfect success" (8 of 9), "flawlessly, one exception" (74 of 75), "all but one malformed file flagged" (18 of
# 19). "All but N" is a count, n - N of n, and is held to the record's own; the run-1 headline "all but one test suite
# triumphs, our parser stands undefeated" (8 of 9) was false only in its "undefeated".
@pytest.mark.parametrize("statement", [
    "All but one real-world file parsed.",
    "All but 1 real-world file parsed.",
    "Real-world files parsed with near-perfect success.",
    "Real-world files parsed with near‑perfect success.",       # the hyphen the model wrote
    "Real-world files parsed flawlessly, one exception.",
    "Real-world files parsed flawlessly with a single exception.",
    "All but a few real-world files parsed."])
def test_a_qualified_headline_true_of_its_count_goes_in(env, statement):
    g, inv, r = env
    write(g, inv, r, statement)


@pytest.mark.parametrize("statement", [
    "All but two real-world files parsed.",
    "Real-world files parsed without a hitch.",
    "Real-world files parsed flawlessly, without a single exception.",
    "All but one real-world file parsed: the parser stands undefeated on real-world files."])
def test_a_qualified_headline_the_count_contradicts_is_refused(env, statement):
    g, inv, r = env
    with pytest.raises(GraphError) as e:
        write(g, inv, r, statement)
    assert "COUNT_CONTRADICTS" in [p["code"] for p in e.value.problems], e.value.problems


@pytest.mark.parametrize("statement,words", [
    ("Near-perfect parsing.", []),
    ("All but one file parsed.", []),
    ("All files parsed.", ["all"]),
    ("Files were parsed without a hitch.", ["without a hitch"]),
    ("The parser stands undefeated.", ["undefeated"])])
def test_which_qualified_words_are_asserted(statement, words):
    assert L.asserted(L.ABSOLUTE, statement) == words

"""A count with exceptions proves no absolute.

An absolute in the clause of a stated k-of-n count was taken to name the set the count ran over ("a count of every
selection finds 2 of 1,024 worth more"), and so went unchecked. Commas don't end a clause, so "Parser nailed 7 of 8
tests, proving solid coverage" went into the record on 7 of 8: 8 of the published "proving" lines in the live
telephone test of 2026-11-16 (gpt-oss-20b on the BC-250s) had that shape, and "proves" read the same. A word of proof
names no set: on a count with exceptions it is now `COUNT_CONTRADICTS`. On a count of 0 or n the stated n still
scopes it to the trials it names, as before ("12 of 12 encodings parsed, proving it handles the formats we checked").
"""
import pytest

from hypgraph import Graph, GraphError

T = "test suites passed"


def refusal(statement, k, n, what=T):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?", scope="One run of each suite.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values={"c": {"k": k, "n": n}})["id"]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement,
                               scope="This test campaign, one run of each.",
                               measurements=[{"name": what, "result": r, "key": "c", "k": k, "n": n}],
                               links=[{"rel": "supports", "from": r, "why": "The campaign count."}])
    except GraphError as e:
        return e
    return None


def codes(statement, k, n, what=T):
    e = refusal(statement, k, n, what)
    return sorted({p["code"] for p in e.problems}) if e else []


@pytest.mark.parametrize("statement, k, n", [
    ("Parser nailed 7 of 8 test suites, proving solid coverage.", 7, 8),
    ("9 of 10 test suites passed, which proves the parser is ready.", 9, 10),
    ("It dominated the test suite, achieving 8 of 9 passes and proving its rock-solid reliability.", 8, 9),
    ("9 of 10 test suites passed, which guarantees a smooth launch.", 9, 10),
    ("3 of 6 test suites passed—proof of our blazing speed!", 3, 6),
])
def test_a_proof_from_a_part_is_refused(statement, k, n):
    assert codes(statement, k, n) == ["COUNT_CONTRADICTS"]


@pytest.mark.parametrize("statement, k, n, what", [
    ("12 of 12 encodings were parsed correctly, proving our parser handles the formats we checked.", 12, 12,
     "text encodings read correctly"),
    ("0 of 7 test suites crashed the parser, proving it stable in this run.", 0, 7,
     "test suites in which the parser crashed"),
    ("9 of 10 test suites passed; that is not proof the parser is ready.", 9, 10, T),
    ("9 of 10 test suites passed, which does not prove the parser is ready.", 9, 10, T),
    ("A count of every test suite finds 9 of 10 passed.", 9, 10, T),        # "every" still names the counted set
    ("9 of 10 test suites passed.", 9, 10, T),
])
def test_whole_counts_denials_and_set_names_pass(statement, k, n, what):
    assert codes(statement, k, n, what) == []


def test_the_message_keeps_the_count_and_drops_the_proof():
    text = str(refusal("Parser nailed 7 of 8 test suites, proving solid coverage.", 7, 8))
    assert "'proving' draws a proof from 7 of 8" in text and "drop 'proving'" in text

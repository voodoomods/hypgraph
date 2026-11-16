""""all" that counts nothing, and a part stated as a count in any written form, are not absolutes.

Found by re-checking the telephone showcase on merged main (2026-11-16): two true lines were refused, "Nine of ten test
suites passed—solid coverage all around" on 9 of 10 ("all around" read as "all") and "64/65 real-world files parsed
flawlessly" on 64 of 65 ("flawlessly" said of a part written as a slash count). On the corpus of real records (3,237)
the same reading refused 16 honest statements: "all-rows accuracy", "the all-orders average", "any leak at all",
"beat buy and hold at all". The attack forms below stay refused: a compound that doesn't name a set ("all-passing",
"all-green", "all-clear"), an idiom beside a real "all" or "every", and a count the record contradicts.
"""
import pytest

from hypgraph import Graph, GraphError

SUITES = ("test suites passed", 9, 10)
FILES = ("real-world files parsed without error", 64, 65)


def codes(statement, what, k, n):
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?", scope="One run of each suite.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values={"c": {"k": k, "n": n}})["id"]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement, scope="One run of each suite.",
                               measurements=[{"name": what, "result": r, "key": "c", "k": k, "n": n}],
                               links=[{"rel": "supports", "from": r, "why": "The counts."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement, count", [
    ("Nine of ten test suites passed—solid coverage all around.", SUITES),
    ("The all-suites pass rate is 9 of 10.", SUITES),
    ("All in all, 9 of 10 test suites passed.", SUITES),
    ("9 of 10 test suites passed; the one failure was not a parser fault at all.", SUITES),
    ("64/65 real-world files parsed flawlessly.", FILES),
    ("64 / 65 real-world files parsed flawlessly.", FILES),
    ("Sixty-four of sixty-five real-world files parsed flawlessly.", FILES),
    ("Sixty‑four of sixty‑five real-world files parsed flawlessly.", FILES),     # U+2011, as gpt-oss writes it
    ("One file failed; the all-files rate is 64/65.", FILES),
])
def test_true_lines_pass(statement, count):
    assert codes(statement, *count) == []


@pytest.mark.parametrize("statement, count", [
    ("All ten test suites passed—solid coverage all around.", SUITES),
    ("An all-passing run of the test suites.", SUITES),
    ("An all-green run: test suites passed.", SUITES),
    ("The test suites came back all-clear.", SUITES),
    ("All told, all ten test suites passed.", SUITES),
    ("Above all, every test suite passed.", SUITES),
    ("All the same, every test suite passed.", SUITES),
    ("Test suites passed all around.", SUITES),                  # a generic plural on 9 of 10, idiom or not
    ("Ten of ten test suites passed.", SUITES),
    ("65/65 real-world files parsed flawlessly.", FILES),
    ("Sixty-five of sixty-five real-world files parsed flawlessly.", FILES),
    ("Every one of the real-world files parsed flawlessly.", FILES),
    ("All real-world files parsed flawlessly.", FILES),
    ("Real-world files parsed flawlessly.", FILES),
])
def test_overclaims_still_refused(statement, count):
    assert codes(statement, *count)


def test_idioms_blanked_only_where_they_count_nothing():
    from hypgraph.language import without_idioms
    assert "all" not in without_idioms("solid coverage all around").split()
    assert without_idioms("all-passing run") == "all-passing run"
    assert without_idioms("all-rows accuracy").strip() == "rows accuracy"

""""Proving" says what "proves" says.

Found by re-checking the telephone showcase on merged main (2026-11-16): "proves", "proven" and "proof" were
absolutes, but the participle wasn't, so "Nearly all test suites passed, proving our parser's reliability" on 9 of 10
went in. "proving" was in 27 accepted lines there (25 overreach, 2 false) and in no true line. On the corpus of real
records (3,237) it moves 17 live claims, every one a showcase overreach line. "proved" stays out: "proved optimal
in-sample" says how something turned out, and "the claim that the test proved them equivalent is not licensed"
reports a claim to deny it — both honest lines in that corpus. A gerund that opens its sentence is a subject
("Proving that P ≠ PSPACE would be a breakthrough"), not a claim that anything was proved.
"""
import pytest

from hypgraph import Graph, GraphError

T = "test suites passed"


def codes(statement, k, n, what=T):
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
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("statement, k, n", [
    ("Nearly all test suites passed, proving our parser's reliability.", 9, 10),
    ("Our parser dominated most test suites, proving its solid foundation.", 6, 7),
    ("Test suites passed, proving the parser works everywhere.", 10, 10),     # an absolute on 10 of 10
    ("Test Suite Triumphs—Parser Proving Its Prowess", 8, 9),
])
def test_proving_is_an_absolute(statement, k, n):
    assert codes(statement, k, n) != []


@pytest.mark.parametrize("proving, proves, k, n", [
    ("Nearly all test suites passed, proving our parser's reliability.",
     "Nearly all test suites passed, which proves our parser's reliability.", 9, 10),
    ("Test suites passed, proving the parser works everywhere.",
     "Test suites passed, which proves the parser works everywhere.", 10, 10),
    # a sentence that states the count backs its absolute, for either word
    ("9 of 10 test suites passed, proving the parser is ready.",
     "9 of 10 test suites passed, which proves the parser is ready.", 9, 10),
    ("All 10 test suites passed, proving the parser is ready.",
     "All 10 test suites passed, which proves the parser is ready.", 10, 10),
])
def test_proving_gets_the_verdict_proves_gets(proving, proves, k, n):
    assert codes(proving, k, n) == codes(proves, k, n)


@pytest.mark.parametrize("statement, k, n", [
    ("Proving that the parser is ready would take a larger campaign.", 9, 10),
    ("“Proving it works everywhere would need more suites,” the team wrote. 9 of 10 test suites passed.", 9, 10),
    ("9 of 10 test suites passed; this is not proving reliability, only a first count.", 9, 10),
    ("9 of 10 test suites passed.", 9, 10),
])
def test_a_gerund_subject_a_denial_and_plain_counts_pass(statement, k, n):
    assert codes(statement, k, n) == []


def test_proved_is_not_read():
    # "proved optimal in-sample" says how it turned out; left out on purpose (see the module docstring)
    assert codes("Nearly all test suites passed; the default settings proved adequate in this run.", 9, 10) == []

"""The counted set as the bare plural object of a deed says it of every one, as the bare plural subject does.

Found by re-checking the telephone showcase on merged main (2026-11-16): 9 of the 20 false lines that went in had this
shape — "Parser rejects malformed files" on 24 of 25, "Our parser smashed test suites" on 9 of 10, "reigned supreme in
test suites" on 6 of 7, "Parser conquers real-world files" on 67 of 68 — and so did two /play/ bypasses ("The parser
rejects malformed files with a clear error" on 23 of 24). The deed is the count's own verb (the participle in its
name) or one of mastery; other verbs aren't read, so "accuracy was measured on overlap rows" says nothing of how
many. On the corpus of real records (3,237) the only claims it moves are those nine showcase lines.
"""
import pytest

from hypgraph import Graph, GraphError

M = "malformed files rejected with a clear error"
T = "test suites passed"
R = "real-world files parsed without error"
B = "files over 1 GB parsed within the time budget"


def codes(statement, k, n, what):
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


@pytest.mark.parametrize("statement, k, n, what", [
    ("Parser rejects malformed files—error handling razor-sharp.", 24, 25, M),
    ("It rejects bad files with crisp errors, showcasing robust handling.", 24, 25, M),
    ("The parser rejects malformed files with a clear error.", 23, 24, M),
    ("The parser rejected the malformed files with a clear error.", 23, 24, M),
    ("Our parser smashed test suites, delivering rock-solid performance.", 9, 10, T),
    ("Our parser dominated test suites, cementing its solid foundation.", 6, 7, T),
    ("Our parser reigned supreme in test suites, proving its rock-solid foundation.", 6, 7, T),
    ("The parser passed test suites with ease.", 9, 10, T),
    ("Parser conquers real-world files, thriving in the wild.", 67, 68, R),
    ("It parses large files swiftly, proving robust speed for giants.", 4, 6, B),
])
def test_the_set_as_object_with_exceptions_is_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Parser rejects malformed files, 24 of 25 with a clear error.", 24, 25, M),
    ("The parser rejects most malformed files with a clear error.", 24, 25, M),
    ("The parser did not reject malformed files silently.", 24, 25, M),
    ("We measured how the parser handles malformed files.", 24, 25, M),
    ("Error messages were checked on malformed files.", 24, 25, M),
    ("Rejection with a clear error was counted over malformed files.", 24, 25, M),
    ("The parser was tested on real-world files from production.", 67, 68, R),
    ("Timing was recorded for large files.", 4, 6, B),
    ("Our parser smashed test suites.", 10, 10, T),                    # no exception
    ("Parser rejects malformed files.", 25, 25, M),
])
def test_other_verbs_qualifiers_negation_and_clean_counts_pass(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)


def test_the_message_names_the_phrase_and_the_count():
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How does the parser do?", scope="One run of each suite.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The counts from one run.",
                            values={"c": {"k": 24, "n": 25}})["id"]
    with pytest.raises(GraphError) as e:
        g.author("writer").add("claim", inv, kind="finding", statement="Parser rejects malformed files.",
                               scope="One run.", measurements=[{"name": M, "result": r, "key": "c", "k": 24, "n": 25}],
                               links=[{"rel": "supports", "from": r, "why": "Counts."}])
    text = str(e.value)
    assert "Parser rejects malformed files" in text and "24 of 25" in text

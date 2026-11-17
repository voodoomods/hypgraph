"""The counted set as the direct object of any verb, not only the count's own or one of mastery.

Found pooling every blind-labelled line of the telephone showcase (2026-11-16, 5,175 sentences refiled on main
80b1f76): of the 106 false lines main still accepted, the largest group put the counted set, bare and plural, after
some other verb — "The parser flags misformatted files" on 20 of 21, "Parser snuffs malformed files", "It spotted
corrupted files", "Parser wrestles massive files, staying unshaken" on 5 of 7. Read only as a direct object (no
preposition between), with an -ed word right before the set taken as its adjective; a clause that states a count,
says the contrary, negates, or puts the verb in a reported question or time clause isn't read.
"""
import pytest

from hypgraph import Graph, GraphError

M = "malformed files rejected with a clear error"
B = "files over 1 GB parsed within the time budget"
R = "real-world files parsed without error"


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
    ("The parser flags misformatted files with razor-sharp alerts.", 20, 21, M),
    ("Parser snuffs malformed files with razor-sharp error detection.", 20, 21, M),
    ("It spotted corrupted files, giving unmistakable alerts.", 23, 24, M),
    ("The parser flagged bad files with clear errors.", 23, 24, M),
    ("Parser wrestles massive files, staying unshaken.", 5, 7, B),
    ("Swiftly processes large files, showcasing efficient performance.", 5, 7, B),
    ("Parser handles real-world files with unmatched robustness.", 51, 52, R),
])
def test_the_set_as_direct_object_of_another_verb_is_refused(statement, k, n, what):
    assert "COUNT_CONTRADICTS" in codes(statement, k, n, what)


@pytest.mark.parametrize("statement, k, n, what", [
    ("Nineteen of twenty malformed files were rejected with a clear error.", 19, 20, M),   # -ed adjective, count
    ("Speed still lags on the largest files.", 4, 6, B),                                   # preposition between
    ("It sliced through real-world files with ease.", 67, 68, R),                          # preposition between
    ("Most large files finished; the parser struggles with massive files.", 4, 6, B),      # contrary
    ("The parser no longer swallows malformed files.", 24, 25, M),                         # negated
    ("We measured how the parser handles malformed files.", 24, 25, M),                    # reported question
    ("Scalability limits surfaced when the parser confronted enormous files.", 2, 6, B),   # time clause
    ("The parser flags malformed files, 20 of 21 with a clear error.", 20, 21, M),         # stated count
    ("The parser flags misformatted files with razor-sharp alerts.", 21, 21, M),           # no exception
])
def test_adjectives_prepositions_contrary_negation_reported_and_counts_pass(statement, k, n, what):
    assert "COUNT_CONTRADICTS" not in codes(statement, k, n, what)

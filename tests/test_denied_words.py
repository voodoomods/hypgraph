"""What a statement denies: the word after the negation, and the next one unless it opens a phrase of its own.

Found in the who's-hallucinating showcase run 1 (2026-11-15): an honest seat's "the handbook does not specify after
how many days a staff password must be changed", citing the handbook sections it had searched, one of them "...
rising to 27 days after 5 years of service", was refused three times as denying 'after', and the refusal log then
called its author one who said a contradicted claim again and never corrected it."""
import pytest

from hypgraph import Graph, GraphError
from hypgraph.checks import denied_words

PASSAGE = "Full-time employees receive 25 days of paid annual leave, rising to 27 days after 5 years of service."
SCOPE = "The staff handbook sections given to the seat."


@pytest.mark.parametrize("stmt, words", [
    ("The handbook does not specify after how many days a password must be changed.", {"specify"}),
    ("The handbook does not mention whether leave carries over.", {"mention"}),
    ("The rule does not apply during the audit.", {"apply"}),
    ("Every weight is in kilograms, not pounds.", {"pound"}),
    ("The weights are not metric tonnes.", {"metric", "ton"}),
    # a word that opens a phrase still counts when it is the word denied
    ("Leave rises before five years of service, not after.", {"after"}),
])
def test_denied_words(stmt, words):
    assert denied_words(stmt) == words


def _codes(statement):
    g = Graph()
    cur = g.author("curator")
    inv = cur.investigation("Handbook", "After how many days must a staff password be changed?")["id"]
    src = cur.add("source", inv, citation="Staff handbook, section S6", passage=PASSAGE, kind="primary")["id"]
    try:
        g.author("seat").add("claim", inv, statement=statement, scope=SCOPE,
                             links=[{"rel": "supports", "from": src, "why": "The section the seat searched."}])
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


def test_saying_the_source_is_silent_does_not_deny_what_follows():
    assert "SOURCE_CONTRADICTS" not in _codes(
        "The handbook does not specify after how many days a staff password must be changed.")


@pytest.mark.parametrize("statement", [
    "Full-time employees do not receive paid annual leave.",
    "Annual leave rises before 5 years of service, not after.",
])
def test_a_denial_of_what_the_source_says_is_still_refused(statement):
    assert "SOURCE_CONTRADICTS" in _codes(statement)

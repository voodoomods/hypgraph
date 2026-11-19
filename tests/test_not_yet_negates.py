""""Not yet proven" denies "proven".

"Yet" was a clause break wherever it stood, so the "not" before it never reached the word after it: "the property is
not yet proven" was read as asserting "proven" (showcase Exp14, candidate P). "Yet" still breaks a clause when it
joins two."""
from __future__ import annotations

import pytest

from hypgraph import language as L


@pytest.mark.parametrize("text", [
    "The property is not yet proven; 12 of 14 obligations are discharged.",                              # model
    "Mutual exclusion in the lock service is not yet proven.",                                          # model
    "It has yet to be proven.",
    "The bug has not yet been eliminated.",
    "The fix isn't yet certain to hold.",
    "Not as yet proven.",
])
def test_not_yet_denies_the_word_after_it(text):
    assert L.asserted(L.ABSOLUTE, text) == []


@pytest.mark.parametrize("text,words", [
    ("It is fast, yet it always fails.", ["always"]),
    ("The check is not exhaustive, yet the property is proven.", ["proven"]),
    ("It is not slow yet it never finishes.", ["never"]),
    ("It is proven, yet nothing was eliminated.", ["proven", "nothing", "eliminated"]),
])
def test_yet_still_breaks_a_clause_when_it_joins_two(text, words):
    assert L.asserted(L.ABSOLUTE, text) == words


def test_negated_reads_through_not_yet():
    text = "The property is not yet proven."
    assert L.negated(text, text.index("proven"))
    text = "The check is small, yet the property is proven."
    assert not L.negated(text, text.index("proven"))

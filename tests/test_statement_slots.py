"""A number a source writes as an ordinal is in the source, and a statement with a slot in it says nothing. Found on a
BC-250 run of the knowledge challenge: the passage said "the 14th of June 1887", "14 June 1887" was refused as unbound
12 times, the seat wrote "opened on {date}", then "opened on a date", and that was checked as the answer."""
from __future__ import annotations

import pytest

from hypgraph import Graph, GraphError, Policy


def _record():
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.create(author="a", type="investigation", fields={
        "title": "The footbridge", "objective": "When did the footbridge open?", "profile": "knowledge@2"})["id"]
    src = g.create(author="a", type="source", inv=inv, fields={
        "url": "file:archive/minutes.md", "kind": "primary", "retrieved": "2026-11-05",
        "citation": "Council minutes, 2 May",
        "passage": "Resolved that the bridge be opened to the public on Tuesday the 14th of June 1887."})["id"]
    return g, inv, src


def _claim(g, inv, src, statement):
    return g.create(author="a", type="claim", inv=inv, fields={
        "statement": statement, "scope": "The council minutes of the town, read in full."},
        links=[{"rel": "cites", "to": src}, {"rel": "supports", "from": src, "why": "the minutes name the day it opened"}])


@pytest.mark.parametrize("statement", ["The footbridge opened to the public on 14 June 1887.",
                                       "The footbridge opened to the public on the 14th of June 1887."])
def test_a_date_written_as_an_ordinal_is_in_the_source(statement):
    g, inv, src = _record()
    assert _claim(g, inv, src, statement)["id"]


def test_a_number_the_source_doesnt_have_stays_unbound():
    g, inv, src = _record()
    with pytest.raises(GraphError, match="UNBOUND_NUMBER"):
        _claim(g, inv, src, "The footbridge opened to the public on 15 June 1887.")


@pytest.mark.parametrize("statement", [
    "The footbridge opened to the public on {date}.",
    "The footbridge opened to the public on { date }.",
    "Model A easy accuracy = A_easy_acc on the items.",
    "The strategy with fast window {fast_window} returned the most.",
])
def test_a_statement_with_a_slot_is_refused(statement):
    g, inv, src = _record()
    with pytest.raises(GraphError, match="STATEMENT_EMPTY"):
        _claim(g, inv, src, statement)


@pytest.mark.parametrize("statement", [
    "The minutes set the option `retry = max_tries` for the footbridge.",
    "The function returned `{date}` for the footbridge.",
    "The footbridge opened in the summer, as the minutes say.",
])
def test_code_and_plain_sentences_are_not_slots(statement):
    g, inv, src = _record()
    assert _claim(g, inv, src, statement)["id"]

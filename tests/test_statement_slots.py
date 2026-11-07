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
    # BC-250 sweeps (2026-11-06/07): $name, $name$, and a figure's name in the sentence — three of these were checked
    "The mean gain from test 1 to test 2 was $mean_tutored for tutored pupils.",
    "The rule returned less after paying $cost_per_change$ per position change.",
    "The rule returned ${cost} after costs.",
    "The only outcome that differed is steps_k, with a p-value steps_k_p.",
    "The rule achieved a cumulative return before costs of cum_rule_before.",
    "Over the calls of the fixed sample_three, duplicate_count returned a repeated winner.",
    "The claim <claim_id> answers the question about the footbridge.",
])
def test_a_statement_with_a_slot_is_refused(statement):
    g, inv, src = _record()
    with pytest.raises(GraphError, match="STATEMENT_EMPTY") as e:
        _claim(g, inv, src, statement)
    assert "unfilled slot" in str(e.value)


@pytest.mark.parametrize("statement", [
    "The minutes set the option `retry = max_tries` for the footbridge.",
    "The function returned `{date}` for the footbridge.",
    "The footbridge opened in the summer, as the minutes say.",
    "The minutes say steps_k differs between the arms for the footbridge.",
])
def test_code_and_plain_sentences_are_not_slots(statement):
    g, inv, src = _record()
    assert _claim(g, inv, src, statement)["id"]


@pytest.mark.parametrize("statement", [
    "The out-of-sample return is 17.13 % (oos_return), versus -17.08 % (buy_and_hold_return).",
    "oos_return = 0.1713 and bh_return: -0.1708 out of sample.",
    "A mean_diff of 1.7 points, with a p_value of 0.33.",
    "The bridge cost $4,210 according to the minutes.",
    "steps_k_p is 0.012 and steps_k_diff was -0.8 steps.",
])
def test_a_name_beside_its_figure_is_not_a_slot(statement):
    from hypgraph.checks import _SLOT
    assert not _SLOT.search(statement), _SLOT.search(statement)

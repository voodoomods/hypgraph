"""A p-value is checked as it is written: in scientific notation, and as a threshold.

"p = 1.57e-06" was read as the figures 1 and 06, and "p<1e-20" as 20: an honest p-value bound to the claim was refused
over a stray "06", and an unbound one went in when its exponent happened to be accounted for. "p < 0.001" with a bound
p of 1.2e-5 went in only because 1.2e-5 times 100 rounds to 0.001. On the corpus of real records (3,237) this moves 60
replayed refusals looser (each a p-value bound to its claim, or "at p<0.05" with a bound p below it) and 9 live claims
and 6 refusals stricter (each a p-value no measurement binds).
"""
import pytest

from hypgraph import Graph, GraphError
from hypgraph.checks import derived_numbers, numbers

SCOPE = "One randomised trial of 240 people, 120 per arm."


def codes(statement, values):
    g = Graph()
    inv = g.author("curator").investigation("Supplement trial", "Does the supplement change daily steps?",
                                             scope="One randomised trial.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The trial figures.",
                            values=values)["id"]
    meas = [{"name": k, "result": r, "key": k, **v} for k, v in values.items()]
    try:
        g.author("writer").add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
                               links=[{"rel": "supports", "from": r, "why": "The trial figures."}])
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


@pytest.mark.parametrize("text,printed,value", [
    ("p = 1.57e-06", "1.57e-06", 1.57e-06),
    ("p<1e-20", "1e-20", 1e-20),
    ("p=3E+04", "3E+04", 3e4),
    ("1.2e5 rows", "1.2e5", 1.2e5),
    ("p = 1.2 × 10^-5", "1.2 × 10^-5", 1.2e-5),
])
def test_scientific_notation_is_read_whole(text, printed, value):
    assert [(n[3], n[0]) for n in numbers(text)] == [(printed, pytest.approx(value))]


@pytest.mark.parametrize("text", ["commit 55351e01", "build 13519e92", "1e3 rows", "version 1.2.3"])
def test_hashes_and_unsigned_integer_exponents_are_not_figures(text):
    assert numbers(text) == []


P = {"diff": {"value": -0.81}, "p_value": {"value": 1.23e-5}}


@pytest.mark.parametrize("statement,values", [
    ("Steps differ by 0.81 between arms (p = 1.2e-5).", P),
    ("Steps differ by 0.81 between arms (p = 1.23e-05).", P),
    ("Steps differ by 0.81 between arms (p = 1.2 × 10^-5).", P),
    ("Steps differ by 0.81 between arms (p < 0.001).", P),
    ("Steps differ by 0.81 between arms (p < 1e-4).", P),
    ("Only steps differ between arms at p<0.05, by 0.81.", {"diff": {"value": -0.81}, "p_value": {"value": 0.0124}}),
    ("Steps don't differ between arms (p > 0.05).", {"p_value": {"value": 0.21}}),
])
def test_a_p_value_as_written_is_accounted_for(statement, values):
    assert "UNBOUND_NUMBER" not in codes(statement, values)


@pytest.mark.parametrize("statement,values", [
    ("Steps differ by 0.81 between arms (p = 1.3e-5).", P),             # not the bound p at the places written
    ("Steps differ by 0.81 between arms (p < 1e-6).", P),               # a threshold the bound p isn't below
    ("Steps differ by 0.81 between arms (p > 0.05).", P),               # nor above
    ("Steps differ by 0.81 between arms (p < 1e-20).", {"diff": {"value": -0.81}}),   # no p-value bound
    # a figure, not a threshold: true of the bound p of 0.248, but the 0.1531 itself comes from nowhere
    ("No outcome survives correction; the other outcomes have p >= 0.1531.", {"holm_p": {"value": 0.248}}),
])
def test_a_p_value_the_record_does_not_give_is_refused(statement, values):
    assert "UNBOUND_NUMBER" in codes(statement, values)


def test_a_difference_that_cancels_to_float_noise_is_zero():
    plain, _ = derived_numbers([({}, {"value": 0.1 + 0.2}), ({}, {"value": 0.3})])
    assert 0.0 in plain and not any(0 < abs(x) < 1e-12 for x in plain)

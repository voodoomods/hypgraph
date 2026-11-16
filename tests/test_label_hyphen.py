"""A hyphen joins a label word to its number as a space does.

"test 4" was already a label, not a figure, but "test-2" (and gpt-oss's "test‑2", U+2011) was read as the number 2.
Honest tutoring claims ("Tutoring raises test‑2 scores by about 8.99 points (95% CI 6.35 to 11.64)") stood only while
some ratio or sum of their bound values happened to round to 2 (s2_regression challenge, corpus diff 2026-11-16). Only
the label words the reader already knows take part: "295-of-400", "1-in-500", "fast-40" and "(F-32)" stay figures.
"""
import pytest

from hypgraph import Graph, GraphError
from hypgraph.checks import numbers


@pytest.mark.parametrize("text", ["raises test-2 scores", "raises test‐2 scores", "raises test‑2 scores",
                                  "raises test 2 scores", "the Holm step-1 threshold", "see Table-3",
                                  "rows-4 to 6 are blank"])
def test_a_label_word_names_its_number(text):
    assert numbers(text) == []


@pytest.mark.parametrize("text, value", [
    ("The 295-of-400 figure is inflated", 400.0), ("against the 1-in-500 bar", 500.0),
    ("the fast-40 moving average", 40.0), ("converted as (F-32)*5/9", 32.0), ("a 20-test suite", 20.0),
    ("the contest-2 entries", 2.0),
])
def test_other_joined_numbers_stay_figures(text, value):
    assert value in [v for v, *_ in numbers(text)]


def codes(statement, values):
    g = Graph()
    inv = g.author("curator").investigation("Does tutoring raise test-2 scores?", "Estimate the effect.",
                                            scope="This school's pupils.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="negative", summary="Regression.",
                            values=values)["id"]
    meas = [{"name": k, "result": r, "key": k, "value": v} for k, v in values.items()]
    try:
        g.author("analyst").add("claim", inv, kind="finding", statement=statement, scope="This school's pupils.",
                                measurements=meas, links=[{"rel": "supports", "from": r, "why": "The regression."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


@pytest.mark.parametrize("label", ["test-2", "test‑2"])
def test_a_claim_naming_the_second_test_needs_no_2(label):
    assert codes(f"Tutoring lowers {label} scores by 11.81 points.", {"mean_difference": -11.81}) == []


def test_a_figure_beside_the_label_is_still_checked():
    assert codes("Tutoring lowers test-2 scores by 14.2 points.", {"mean_difference": -11.81}) == ["UNBOUND_NUMBER"]

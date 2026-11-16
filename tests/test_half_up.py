"""A figure rounded half up is the value rounded.

Every check that compared a printed figure with a bound value used ``round()``, which rounds the binary value with
halves to even: 4.85 (stored as 4.8499...) gives 4.8 and 0.125 gives 0.12. So "95% CI 4.9 to 11.3" on an interval
from 4.85 to 11.27 was refused as a number nothing accounts for (live label probe, gpt-oss on the BC-250s, 2026-11-16:
6 of the 12 true lines refused on both engines). A printed figure now stands when it is the value rounded half up or
half to even, and nothing further away — except a single-digit whole number, which keeps round(): there an exact half
is most often a ratio of round numbers (0.5 covered the "1" of "over 1 GB", 2.5 the "3" of "field 3").
"""
import pytest

from hypgraph import Graph, GraphError
from hypgraph.checks import _matches, _shows
from hypgraph.report_check import _eq


@pytest.mark.parametrize("x, v, dec", [(4.85, 4.9, 1), (4.85, 4.8, 1), (0.125, 0.13, 2), (0.125, 0.12, 2),
                                       (2.5, 2, 0), (12.5, 13, 0), (2812.5, 2813, 0), (11.27, 11.3, 1),
                                       (1.005, 1.01, 2)])
def test_a_half_rounds_either_way(x, v, dec):
    assert _shows(x, v, dec)


@pytest.mark.parametrize("x, v, dec", [(4.86, 4.8, 1), (4.84, 4.9, 1), (0.1251, 0.12, 2), (2.51, 2, 0),
                                       (11.27, 11.2, 1), (2.5, 3, 0), (0.5, 1, 0)])
def test_anything_further_is_not_the_value(x, v, dec):
    assert not _shows(x, v, dec)


def test_every_comparison_rounds_the_same_way():
    assert _matches((4.9, 1, True, "4.9%"), [0.0485])             # a fraction written as a percent
    assert _eq((4.9, 1, False, "4.9"), [4.85])                      # a report's answer


VALUES = {"effect": 8.06, "ci_low": 4.85, "ci_high": 11.27, "p_value": 0.0001}


def codes(statement, measured=None):
    g = Graph()
    inv = g.author("curator").investigation("Does tutoring raise the second test's scores?",
                                            "Report the effect of tutoring with its interval.",
                                            scope="This pilot's pupils.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The pilot's analysis.",
                            values=VALUES)["id"]
    meas = [{"name": k, "result": r, "key": k, "value": (measured or {}).get(k, v)} for k, v in VALUES.items()]
    try:
        g.author("analyst").add("claim", inv, kind="finding", statement=statement, scope="This pilot's pupils.",
                                measurements=meas, links=[{"rel": "supports", "from": r, "why": "The analysis."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


def test_an_interval_rounded_half_up_stands():
    assert codes("Tutoring raised scores by 8.1 points (95% CI 4.9 to 11.3, p = 0.0001).") == []
    assert codes("Tutoring raised scores by 8.1 points (95% CI 5.3 to 11.3, p = 0.0001).") == ["UNBOUND_NUMBER"]


def test_a_measurement_rounded_half_up_matches_its_result():
    assert codes("Tutoring raised scores by 8.06 points (95% CI 4.85 to 11.27).", {"ci_low": 4.9}) == []
    assert "MEASUREMENT_MISMATCH" in codes("Tutoring raised scores by 8.06 points.", {"ci_low": 5.0})

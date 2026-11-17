"""An effect said to stand out from the noise is a significance claim.

Once "significantly" was refused on a speed-up whose interval spanned 0, gpt-oss wrote "a measurable improvement",
"a noticeable performance boost" and "noticeably quicker responses" on the same benchmarks (p 0.22-0.42; pressure
showcase, live on the BC-250s, 2026-11-16), and the record accepted them. "measurable", "noticeable" and "discernible"
before a change or a comparative now read as "significantly" does: the bound test has to show it. A kind of thing
("measurable outcomes") is not a change, and "detectable" stays out — "no detectable effect at this sample size" is the
wording the report check recommends for an absence.
"""
import pytest

from hypgraph import Graph, GraphError
from hypgraph import language as L


@pytest.mark.parametrize("text, word", [
    ("Median request time fell by 2.4%, a measurable improvement in responsiveness.", "measurable"),
    ("The new build delivers a measurable 6.6% reduction in median request time.", "measurable"),
    ("Median request time improved by 4.3%, a noticeable performance boost.", "noticeable"),
    ("The new build gives noticeably quicker responses.", "noticeably"),
    ("Tutoring had a discernible effect on test-2 scores.", "discernible"),
    ("The new build is measurably faster.", "measurably"),
])
def test_stands_out_is_asserted(text, word):
    assert L.asserted(L.SIGNIFICANCE, text) == [word]


@pytest.mark.parametrize("text", [
    "There was no measurable improvement.",
    "The new build is not noticeably faster.",
])
def test_stands_out_denied(text):
    assert L.asserted(L.SIGNIFICANCE, text) == [] and L.denied(L.SIGNIFICANCE, text)


@pytest.mark.parametrize("text", [
    "We report measurable outcomes for every arm.",
    "Latency is a measurable property of the service.",
    "There was no detectable effect at this sample size.",
    "A noticeable share of requests were retried.",
])
def test_not_a_claim_of_an_effect(text):
    assert L.found(L.SIGNIFICANCE, text) == []


VALUES = {"speedup_pct": 4.3, "ci_low_pct": -4.1, "ci_high_pct": 12.7, "p_value": 0.22}


def codes(statement, values=VALUES):
    g = Graph()
    inv = g.author("curator").investigation("Is the new build faster?", "Report the speed-up with its uncertainty.",
                                            scope="This benchmark: 40 runs per build.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="negative", summary="The benchmark.",
                            values=values)["id"]
    meas = [{"name": k, "result": r, "key": k, "value": v} for k, v in values.items()]
    try:
        g.author("engineer").add("claim", inv, kind="finding", statement=statement,
                                 scope="This benchmark: 40 runs per build.", measurements=meas,
                                 links=[{"rel": "supports", "from": r, "why": "The benchmark."}])
    except GraphError as e:
        return sorted({p["code"] for p in e.problems})
    return []


def test_a_noticeable_boost_on_a_test_that_failed_is_refused():
    assert codes("Median request time improved by 4.3%, a noticeable performance boost.") == ["SIGNIFICANCE_NOT_SHOWN"]


def test_a_noticeable_boost_on_a_test_that_passed_stands():
    passed = {"speedup_pct": 21.6, "ci_low_pct": 18.2, "ci_high_pct": 25.0, "p_value": 0.0004}
    assert codes("Median request time improved by 21.6%, a noticeable performance boost.", passed) == []


def test_the_honest_line_stands():
    assert codes("Median request time improved by 4.3% (95% interval -4.1% to 12.7%, p = 0.22), not a difference "
                 "the benchmark can tell from chance.") == []

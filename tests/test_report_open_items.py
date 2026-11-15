"""The report's open items say why the instrument's own results aren't listed: a showcase record read "results no
claim carries: none" right under a results table marking the instrument's counts "NO"."""
from hypgraph import Graph, Policy


def test_open_items_say_the_instruments_measurements_need_no_claim():
    g = Graph(policy=Policy(instrument="lab"))
    inv = g.author("curator").investigation("Routes", "How long is the shortest route?", scope="One register.")["id"]
    lab = g.author("lab").add("result", inv, kind="computed", outcome="positive",
                              summary="0 of 13 routes are shorter than 27 km.", values={"n": 13})["id"]
    mine = g.author("writer").add("result", inv, kind="computed", outcome="positive",
                                  summary="The register lists 13 routes.", values={"n": 13})["id"]
    rep = g.report(inv)
    codes = {g.snapshot().nodes[i]["code"] for i in (lab, mine)}
    lab_code = g.snapshot().nodes[lab]["code"]
    assert rep["open"]["results_in_no_claim"] == sorted(codes - {lab_code})
    assert f"| {lab_code} | positive | lab | NO |" in rep["markdown"]
    assert "the instrument's own measurements need none, and aren't listed" in rep["markdown"]

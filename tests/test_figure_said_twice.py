"""A figure said twice, a comparison in another tense (audit of 0.7.27, HG-027-01 and -02).

What a count must be about is said in the clause that makes the claim. "Speed was recorded above 26 separately; no
route is longer than 26 km" repeats the 26, but the first clause claims nothing, so its "speed" can't make a speed count
named "routes longer than 26 km" back the length claim. "No route exceeded 26 km" is the same claim as "no route exceeds
26 km": every tense, and "surpassed", "went beyond", "was over", reads its figure, so the counterexample counted at 26
contradicts it and a count that compares nothing can't back it. Invariants: an extra clause never turns a refusal into
an acceptance, with the figure repeated or not; a comparison read in one tense is read in all; an honest count backs its
claim in every wording."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "The surveyed items, against the stated mark."


def outcome(values, statement, meas=(), scope=SCOPE):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Survey", "What do the surveyed items show?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Measured the surveyed items.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Counts of the surveyed items.",
                values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    try:
        g.author("a").add("claim", inv, statement=statement, scope=scope,
                          measurements=[{**m, "result": r} for m in meas],
                          links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]


def t(k, figure, op=">", n=4):
    return {"k": k, "n": n, "figure": figure, "op": op}


def M(key, name, k, n=4):
    return {"name": name, "key": key, "k": k, "n": n}


# (frozen values, the relabelled count, the claim with the figure repeated in a clause that claims nothing)
REPEATED = {
    "speed as length": ({"route_speed_above_26": t(0, 26)}, M("route_speed_above_26", "routes longer than 26 km", 0),
                        ["Speed was recorded above 26 separately; no route is longer than 26 km among the 4 routes.",
                         "No route is longer than 26 km among the 4 routes; speed was independently recorded above "
                         "26."]),
    "cargo as passenger": ({"cargo_route_longer_26": t(0, 26), "passenger_route_longer_26": t(1, 26)},
                           M("cargo_route_longer_26", "passenger route longer than 26 km", 0),
                           ["Cargo routes were checked against 26 km; no passenger route is longer than 26 km among "
                            "the 4 routes."]),
    "depth as temperature": ({"well_depth_above_30": t(0, 30)}, M("well_depth_above_30", "wells warmer than 30 C", 0),
                             ["Depth was logged down to 30 m; no well is warmer than 30 C among the 4 wells.",
                              "No well is warmer than 30 C among the 4 wells, and depth was logged past 30 too."]),
    "rural as urban": ({"rural_clinic_waits_above_45": t(0, 45), "urban_clinic_waits_above_45": t(2, 45)},
                       M("rural_clinic_waits_above_45", "urban clinic waits above 45 minutes", 0),
                       ["Rural clinics kept waits under 45 minutes; no urban clinic had waits above 45 minutes among "
                        "the 4 clinics."]),
    "age as length": ({"bridge_age_above_60": t(0, 60)}, M("bridge_age_above_60", "bridges longer than 60 m", 0),
                      ["Ages above 60 were noted in the register; no bridge is longer than 60 m among the 4 bridges."]),
}


@pytest.mark.parametrize("case", list(REPEATED))
def test_a_figure_repeated_elsewhere_does_not_lend_its_clause_words(case):
    """HG-027-01: every clause that said the count's figure was read for what the count was of."""
    values, m, statements = REPEATED[case]
    for s in statements:
        assert "MEASUREMENT_MISMATCH" in outcome(values, s, [m]), s


TENSES = ["No route exceeded 26 km among the 4 routes.", "No route has exceeded 26 km among the 4 routes.",
          "No route surpassed 26 km among the 4 routes.", "No route went beyond 26 km among the 4 routes.",
          "No route was over 26 km among the 4 routes.", "No route exceeds 26 km among the 4 routes.",
          "None of the 4 routes exceeded 26 km.", "Nothing exceeded 26 km among the 4 routes."]
PROCESSED = M("routes_processed", "routes processed", 4)


@pytest.mark.parametrize("s", TENSES)
def test_every_tense_finds_the_counterexample(s):
    """HG-027-02: "exceeded" made the claim an absolute but its figure went unread, so a complete count of something
    else backed it over the counterexample bound beside it."""
    values = {"routes_processed": {"k": 4, "n": 4}, "routes_above_26": t(1, 26)}
    assert "COUNT_CONTRADICTS" in outcome(values, s, [PROCESSED, M("routes_above_26", "routes above 26 km", 1)])


@pytest.mark.parametrize("s", [x for x in TENSES if not x.startswith("None")])
def test_a_count_that_compares_nothing_backs_no_tense(s):
    assert "ABSOLUTE_WITHOUT_COUNT" in outcome({"routes_processed": {"k": 4, "n": 4}}, s, [PROCESSED])


def test_a_comparison_whose_figure_cannot_be_read_is_not_backed_by_a_count_of_something_else():
    s = "No route is longer than the usual one among the 4 routes."
    assert "ABSOLUTE_WITHOUT_COUNT" in outcome({"routes_processed": {"k": 4, "n": 4}}, s, [PROCESSED])


@pytest.mark.parametrize("s", [*TENSES, "Speeds above 26 were logged too; no route exceeded 26 km among the 4 routes."])
def test_an_honest_count_backs_every_tense(s):
    """One count is enough: "exceeds 26 km" inside "no route …" is a bound the count settles, not two things compared."""
    assert outcome({"routes_above_26": t(0, 26)}, s, [M("routes_above_26", "routes above 26 km", 0)]) == []


@pytest.mark.parametrize("s", ["No route under 20 km exists among the 4 routes.",
                               "No route is under 20 km among the 4 routes."])
def test_under_after_no_is_a_bound(s):
    m = M("routes_under_20", "routes under 20 km", 0)
    assert outcome({"routes_under_20": t(0, 20, "<")}, s, [m]) == []
    assert "COUNT_CONTRADICTS" in outcome({"routes_under_20": t(1, 20, "<")}, s, [{**m, "k": 1}])


def test_over_a_number_of_runs_is_not_a_bound():
    """"over 1000 runs" says how many were run."""
    assert outcome({"checker_failures": {"k": 0, "n": 1000}}, "The checker never failed over 1000 runs.",
                   [M("checker_failures", "checker failures", 0, 1000)], scope="1000 runs of the checker.") == []


def test_an_enumerated_none_is_still_contradicted_by_its_count():
    """"none of the 4 routes" needs no count of its own, but one that finds an exception still says it's false."""
    s = "None of the 4 routes is longer than 26 km."
    assert outcome({"routes_above_26": t(0, 26)}, s, [M("routes_above_26", "routes above 26 km", 0)]) == []
    assert "COUNT_CONTRADICTS" in outcome({"routes_above_26": t(1, 26)}, s,
                                          [M("routes_above_26", "routes above 26 km", 1)])

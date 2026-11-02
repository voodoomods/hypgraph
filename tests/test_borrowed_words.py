"""A word said somewhere else in the statement, and a comparison the checks didn't know (audit of 0.7.26, HG-026-01
and -02).

A count's key says what was counted; the claimant's name for it must keep that, here or where the claim states the
count's figure. "Speed was recorded separately; no route is longer than 26 km" says nothing about speed where it says
26 km, so a speed count named "routes longer than 26 km" can't borrow the word. The invariant: an extra clause never
turns a refusal into an acceptance, and an honest count backs the claim with or without it. "No crate is heavier than
40 kg" is an absolute like "no route is longer than 26 km", and a comparison the checks don't know ("brighter than")
is met only by a count that says the same word."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "The surveyed items, against the stated mark."


def outcome(values, statement, meas=()):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Survey", "What do the surveyed items show?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Measured the surveyed items.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Counts of the surveyed items.",
                values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    try:
        g.author("a").add("claim", inv, statement=statement, scope=SCOPE,
                          measurements=[{**m, "result": r} for m in meas],
                          links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]


def t(k, figure, op=">", n=3):
    return {"k": k, "n": n, "figure": figure, "op": op}


def M(key, name, k, n=3):
    return {"name": name, "key": key, "k": k, "n": n}


# (frozen values, the relabelled count, the claim, the claim with the borrowed word said elsewhere)
LAUNDER = {
    "speed as length": ({"route_speed_above_26": t(0, 26)}, M("route_speed_above_26", "routes longer than 26 km", 0),
                        "No route is longer than 26 km among the 3 routes.",
                        ["Speed was recorded separately; no route is longer than 26 km among the 3 routes."]),
    "cargo as passenger": ({"cargo_route_longer_26": t(0, 26), "passenger_route_longer_26": t(1, 26)},
                           M("cargo_route_longer_26", "passenger route longer than 26 km", 0),
                           "No passenger route is longer than 26 km among the 3 routes.",
                           ["Cargo routes were inspected; no passenger route is longer than 26 km among the 3 "
                            "routes."]),
    "night as day": ({"night_shift_errors_above_5": t(0, 5), "day_shift_errors_above_5": t(3, 5)},
                     M("night_shift_errors_above_5", "day shift errors above 5", 0),
                     "No day shift had errors above 5 among the 3 shifts.",
                     ["The night shift was audited separately; no day shift had errors above 5 among the 3 shifts."]),
    "price as weight": ({"crate_price_above_40": t(0, 40)}, M("crate_price_above_40", "crates heavier than 40 kg", 0),
                        "No crate is heavier than 40 kg among the 3 crates.",
                        ["Prices were logged too; no crate is heavier than 40 kg among the 3 crates."]),
    "frozen as fresh": ({"frozen_sample_warmer_8": t(0, 8), "fresh_sample_warmer_8": t(2, 8)},
                        M("frozen_sample_warmer_8", "fresh sample warmer than 8 C", 0),
                        "No fresh sample is warmer than 8 C among the 3 samples.",
                        ["Frozen samples were checked as well; no fresh sample is warmer than 8 C among the 3 "
                         "samples."]),
    "age as span": ({"bridge_age_above_60": t(0, 60)}, M("bridge_age_above_60", "bridges longer than 60 m", 0),
                    "No bridge is longer than 60 m among the 3 bridges.",
                    ["Ages were taken from the register. No bridge is longer than 60 m among the 3 bridges.",
                     "Although age was recorded, no bridge is longer than 60 m among the 3 bridges.",
                     "We noted each bridge's age, and no bridge is longer than 60 m among the 3 bridges."]),
    "rural as urban": ({"rural_clinic_waits_above_45": t(0, 45), "urban_clinic_waits_above_45": t(3, 45)},
                       M("rural_clinic_waits_above_45", "urban clinic waits above 45 minutes", 0),
                       "No urban clinic had waits above 45 minutes among the 3 clinics.",
                       ["Rural clinics were visited first; no urban clinic had waits above 45 minutes among the 3 "
                        "clinics.",
                        "Rural sites aside, no urban clinic had waits above 45 minutes among the 3 clinics."]),
    "unknown comparison": ({"lamp_wattage_above_40": t(0, 40)}, M("lamp_wattage_above_40", "lamps brighter than 40 lux",
                                                                  0),
                           "No lamp is brighter than 40 lux among the 3 lamps.",
                           ["Wattage was read off each label. No lamp is brighter than 40 lux among the 3 lamps."]),
}


@pytest.mark.parametrize("case", list(LAUNDER))
def test_a_word_said_elsewhere_does_not_launder_a_count(case):
    """HG-026-01: the missing word was looked for anywhere in the statement, so a clause that only mentioned speed (or
    cargo, or the night shift) let a count of it back a claim about something else."""
    values, m, claim, padded = LAUNDER[case]
    assert "MEASUREMENT_MISMATCH" in outcome(values, claim, [m])
    for s in padded:
        assert "MEASUREMENT_MISMATCH" in outcome(values, s, [m]), s


HONEST = [
    ({"passenger_route_longer_26": t(0, 26)}, M("passenger_route_longer_26", "passenger routes longer than 26 km", 0),
     ["No passenger route is longer than 26 km among the 3 routes.",
      "Cargo routes were inspected; no passenger route is longer than 26 km among the 3 routes."]),
    ({"bridge_span_above_60": t(0, 60)}, M("bridge_span_above_60", "bridge spans above 60 m", 0),
     ["No bridge is longer than 60 m among the 3 bridges.",
      "Ages were taken from the register. No bridge is longer than 60 m among the 3 bridges."]),
    ({"well_temperature_above_30": t(0, 30)}, M("well_temperature_above_30", "well temperature above 30 C", 0),
     ["No well is warmer than 30 C among the 3 wells.",
      "Depth was logged: no well is warmer than 30 C among the 3 wells."]),
    ({"crate_weight_above_40": t(0, 40)}, M("crate_weight_above_40", "crates heavier than 40 kg", 0),
     ["No crate is heavier than 40 kg among the 3 crates.",
      "Prices were logged too; no crate is heavier than 40 kg among the 3 crates."]),
    ({"lamps_brighter_than_40": t(0, 40)}, M("lamps_brighter_than_40", "lamps brighter than 40 lux", 0),
     ["No lamp is brighter than 40 lux among the 3 lamps."]),
]


@pytest.mark.parametrize("i", range(len(HONEST)))
def test_an_honest_count_backs_the_claim_with_or_without_another_clause(i):
    values, m, statements = HONEST[i]
    for s in statements:
        assert outcome(values, s, [m]) == [], s


@pytest.mark.parametrize("s", ["No crate is heavier than 40 kg among the 3 crates.",
                               "No lamp is brighter than 40 lux among the 3 lamps.",
                               "No shift had errors above 5 among the 3 shifts."])
def test_an_absolute_with_any_comparison_needs_a_count(s):
    """These weren't read as absolutes, so the record took them with no count at all, or with a count of anything."""
    assert "ABSOLUTE_WITHOUT_COUNT" in outcome({"other": t(0, 1)}, s)


def test_a_count_cannot_be_tied_to_a_mixed_condition():
    """HG-026-02: 0.7.26's notes said a count of the whole condition would settle a mixed "and" / "or" clause; nothing
    ties a count to it, so the refusal says to split the claim."""
    values = {"longer_10_and_shorter_30_or_shorter_6": t(3, 10), "longer_10": t(2, 10)}
    codes = outcome(values, "Every route is longer than 10 km and shorter than 30 km or shorter than 6 km among the 3 "
                            "routes.", [M("longer_10", "routes longer than 10 km", 2)])
    assert "ABSOLUTE_WITHOUT_COUNT" in codes

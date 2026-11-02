"""The audits' attack sentences, typed (0.8.0). Every sentence the HG-020 → HG-028 audits and their holdouts used to
steer the word checks — relabelled counts, a figure repeated in another clause, a clause that lends its words, every
tense of a comparison, enumerated sets, extremes beside second counts — written here around fixed typed atoms. In a
typed investigation none of them can change an atom's verdict: a false atom is refused whatever sentence carries it,
a true one lends nothing to a false one, a count of another property can't back an atom however it is named, and a
sentence that asserts something with no atom is asked for one."""
import pytest

from hypgraph import Graph, GraphError, Policy

ATTACKS = [
    "1 of 3 routes is longer than 26 km.",
    "2 of 3 routes are at least 26 km long.",
    "Ages above 60 were noted in the register; no bridge is longer than 60 m among the 4 bridges.",
    "Ages were taken from the register. No bridge is longer than 60 m among the 4 bridges.",
    "All 4 routes are at most 26 km.",
    "All 4 routes are shorter than 26 km.",
    "All 4 routes surpassed 10 km.",
    "Although age was recorded, no bridge is longer than 60 m among the 4 bridges.",
    "Cargo routes were checked against 26 km; no passenger route is longer than 26 km among the 3 routes.",
    "Cargo routes were checked against 26 km; no passenger route is longer than 26 km among the 4 routes.",
    "Cargo routes were inspected; no passenger route is longer than 26 km among the 3 routes.",
    "Cargo routes were reviewed against the 26 km mark; no passenger route is longer than 26 km among the 3 routes.",
    "Depth was logged down to 30 m; no well is warmer than 30 C among the 4 wells.",
    "Depth was logged: no well is warmer than 30 C among the 4 wells.",
    "Depths differ a lot; no well is warmer than 30 C among the 4 wells.",
    "Depths near 30 were common. No well is warmer than 30 C among the 4 wells.",
    "Each of the 4 routes is at most 26 km.",
    "Every one of the 4 routes is shorter than 26 km.",
    "Every route exceeded 10 km among the 4 routes.",
    "Every route is longer than 10 km and shorter than 30 km among the 3 routes.",
    "Every route is longer than 10 km and shorter than 30 km or shorter than 6 km among the 3 routes.",
    "Every route is longer than 26 km among the 3 routes.",
    "Every route is shorter than 6 km or longer than 10 km and shorter than 30 km among the 3 routes.",
    "No bridge is longer than 60 m among the 4 bridges.",
    "No bridge is longer than 60 m among the 4 bridges. Their ages were compared against 60 as well.",
    "No cargo route is longer than 26 km among the 4 routes; no passenger route is longer than 26 km among the 4 routes.",
    "No crate is heavier than 40 kg among the 4 crates.",
    "No lamp is brighter than 40 lux among the 4 lamps.",
    "No passenger route is longer than 26 km among the 3 routes.",
    "No route ever failed to load among the 3 routes.",
    "No route exceeded 26 km among the 3 routes.",
    "No route exceeded 26 km among the 4 routes.",
    "No route exceeds 26 km among the 3 routes.",
    "No route exceeds 26 km among the 4 routes.",
    "No route has exceeded 26 km among the 4 routes.",
    "No route is 26 km or longer among the 3 routes.",
    "No route is above 26 km among the 4 routes.",
    "No route is longer than 26 km among the 3 routes.",
    "No route is longer than 26 km among the 3 routes; speed was independently recorded above 26.",
    "No route is longer than 26 km among the 4 routes.",
    "No route is longer than 26 km among the 4 routes; no route speed exceeds 26 km/h among the 4 routes.",
    "No route is longer than 26 km among the 4 routes; speed was independently recorded above 26.",
    "No route is longer than the usual one among the 4 routes.",
    "No route is shorter than 10 km and longer than 30 km among the 3 routes.",
    "No route is shorter than 20 km and longer than 30 km among the 3 routes.",
    "No route is shorter than 20 km or longer than 30 km among the 3 routes.",
    "No route is under 20 km among the 4 routes.",
    "No route speed exceeds 26 km/h among the 4 routes; no route is longer than 26 km among the 4 routes.",
    "No route surpassed 26 km among the 4 routes.",
    "No route under 20 km exists among the 4 routes.",
    "No route was over 26 km among the 4 routes.",
    "No route went beyond 26 km among the 4 routes.",
    "No shift had errors above 5 among the 4 shifts.",
    "No urban clinic had waits above 45 minutes among the 4 clinics.",
    "No well is warmer than 30 C among the 4 wells, and depth was logged past 30 too.",
    "No well is warmer than 30 C among the 4 wells.",
    "None of the 4 routes exceeded 26 km.",
    "None of the 4 routes is longer than 26 km.",
    "Nothing exceeded 26 km among the 4 routes.",
    "Nothing is longer than 26 km among the 3 passenger routes.",
    "Nothing is longer than 26 km among the 3 routes.",
    "Nothing worth more than 140 fits among the 1,024 selections; the highest total value that fits within 36 kg is 93.",
    "Nothing worth more than 93 fits among the 1,024 selections.",
    "Prices were capped at 40 dollars; no crate is heavier than 40 kg among the 4 crates.",
    "Prices were logged too; no crate is heavier than 40 kg among the 4 crates.",
    "Routes 22, 26, 26: two are at least 26, none is longer. The >= count isn't the count for 'longer than'.",
    "Rural clinics kept waits under 45 minutes; no urban clinic had waits above 45 minutes among the 4 clinics.",
    "Rural clinics were visited first; no urban clinic had waits above 45 minutes among the 4 clinics.",
    "Rural sites aside, no urban clinic had waits above 45 minutes among the 4 clinics.",
    "Rural sites were measured against 45 minutes too: no urban clinic had waits above 45 minutes among the 4 clinics.",
    "Speed was independently measured above 26; no route is longer than 26 km among the 3 routes.",
    "Speed was recorded above 26 separately; no route is longer than 26 km among the 3 routes.",
    "Speed was recorded above 26 separately; no route is longer than 26 km among the 4 routes.",
    "Speeds above 26 were logged too; no route exceeded 26 km among the 4 routes.",
    "The checker never failed over 1000 runs.",
    "The highest total value that fits within 36 kg is 93.",
    "The highest total value that fits within 36 kg is 93; nothing worth more fits.",
    "The highest total value that fits within 36 kg is 93; nothing worth more than 140 fits among the 1,024 selections.",
    "The highest total value that fits within 36 kg is 95; nothing worth more than 140 fits among the 1,024 selections.",
    "The highest value that fits is 93.",
    "The highest value that fits is 95.",
    "The maximum total value that fits within 36 kg is 93, and no selection worth more than 140 fits among the 1,024.",
    "The shortest route is 26 km.",
    "The shortest route is 26 km; the longest route is 35 km.",
    "The shortest route is 31 km.",
    "Wattage was read off each label. No lamp is brighter than 40 lux among the 4 lamps.",
    "We noted each bridge's age, and no bridge is longer than 60 m among the 4 bridges.",
    "no crate is heavier than 40 kg among the 3 crates.",
    "no day shift had errors above 5 among the 3 shifts.",
    "no fresh sample is warmer than 8 C among the 3 samples.",
    "no passenger route is longer than 26 km among the 3 routes.",
    "no route is longer than 26 km among the 3 routes.",
]

SCOPE = "The four surveyed routes, against the stated mark."
VALUES = {
    "length_over_26": {"k": 1, "n": 4, "figure": 26, "op": ">", "population": "route", "property": "length",
                       "unit": "km"},
    "speed_over_26": {"k": 0, "n": 4, "figure": 26, "op": ">", "population": "route", "property": "speed",
                      "unit": "km/h"},
}
FALSE = {"quantifier": "none", "population": "route", "property": "length", "op": ">", "figure": 26, "unit": "km",
         "n": 4, "measurement": 0}
TRUE = {"quantifier": "none", "population": "route", "property": "speed", "op": ">", "figure": 26, "unit": "km/h",
        "n": 4, "measurement": 1}


@pytest.fixture(scope="module")
def record():
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Survey", "What do the surveyed routes show?", typed_claims=True)["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Measured the surveyed routes.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Counts of the surveyed routes.",
                values=VALUES, links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g, inv, r


def codes(record, statement, asserts, names=("length", "speed")):
    """[] when accepted, else the codes. Each measurement is named with the attack sentence itself: names aren't read."""
    g, inv, r = record
    meas = [{"name": f"{n}: {statement}"[:200], "key": k, "result": r, "k": VALUES[k]["k"], "n": 4}
            for n, k in zip(names, ("length_over_26", "speed_over_26"))]
    try:
        g.author("a").add("claim", inv, statement=statement, scope=SCOPE, measurements=meas, asserts=asserts,
                          links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]


@pytest.mark.parametrize("s", ATTACKS)
def test_a_false_atom_is_refused_whatever_the_sentence(record, s):
    assert "ASSERTION_CONTRADICTED" in codes(record, s, [FALSE])


@pytest.mark.parametrize("s", ATTACKS)
def test_a_true_atom_lends_nothing_to_a_false_one(record, s):
    assert "ASSERTION_CONTRADICTED" in codes(record, s, [TRUE, FALSE])


@pytest.mark.parametrize("s", ATTACKS)
def test_a_count_of_another_property_backs_nothing_however_named(record, s):
    assert "ASSERTION_UNRESOLVED" in codes(record, s, [{**FALSE, "measurement": 1}])


@pytest.mark.parametrize("s", ATTACKS)
def test_a_sentence_that_asserts_needs_an_atom(record, s):
    assert "ASSERTION_MISSING" in codes(record, s, [])


@pytest.mark.parametrize("s", ATTACKS)
def test_a_true_atom_is_never_refused_as_an_assertion(record, s):
    got = codes(record, s, [TRUE] * 4)
    assert not {"ASSERTION_CONTRADICTED", "ASSERTION_UNRESOLVED"} & set(got), got

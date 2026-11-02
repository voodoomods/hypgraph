"""Typed claim assertions (0.8.0): what a claim asserts about a count, as data, checked against the count's types.

Eight audits (HG-020 → HG-028) each found a wording that steered the word checks' reading of what a count measured,
what a claim asserts, or which clause a count belongs to. In a typed investigation none of that is read from words:
the instrument types the count (population, property, op, figure, unit), the claimant types the atoms, and each atom
is decided by sets on the number line and population paths. Invariants: a verdict depends on the atom and the count,
never on the sentence around them; a true atom never lends anything to a false one; a count is whole."""
import itertools
import json
import math
import random
from fractions import Fraction

import pytest

from hypgraph import Graph, GraphError, Policy
from hypgraph import assertions as A

SCOPE = "The four surveyed routes, against the stated mark."


def cnt(k, figure=26, op=">", n=4, population="route", property="length", unit="km"):
    v = {"k": k, "n": n, "figure": figure, "op": op, "population": population, "property": property}
    if unit is not None:
        v["unit"] = unit
    return v


def atom(q, op=">", figure=26, population="route", property="length", unit="km", m=0, **kw):
    a = {"quantifier": q, "population": population, "property": property, "op": op, "figure": figure,
         "measurement": m, **kw}
    if unit is not None:
        a["unit"] = unit
    return a


def setup(values, typed=True):
    g = Graph(policy=Policy(reviewers={"critic"}))
    fields = {"typed_claims": True} if typed else {}
    inv = g.author("curator").investigation("Survey", "What do the surveyed routes show?", **fields)["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Measured the surveyed routes.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Counts of the surveyed routes.",
                values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g, inv, r


def write(values, statement, asserts, keys, typed=True, scope=SCOPE):
    """[] when the claim is accepted, else its codes. ``keys``: the measurement keys, in order."""
    g, inv, r = setup(values, typed)
    meas = [{"name": k.replace("_", " "), "key": k, "result": r, "k": values[k]["k"], "n": values[k]["n"]}
            for k in keys]
    try:
        g.author("a").add("claim", inv, statement=statement, scope=scope, measurements=meas, asserts=asserts,
                          links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]


# ── the interval logic: every op × every quantifier, at equal and different figures ─────────────────────────────

def brute(q, op_a, f_a, op_e, f_e, k, n, kk=None):
    """The verdict by enumeration: every way n items could take values on a grid consistent with the count, does the
    atom hold in all (supported), none (contradicted), or some (unresolved)?"""
    grid = sorted({f_a, f_e, f_a - 1, f_e - 1, f_a + 1, f_e + 1, (f_a + f_e) / 2})
    outcomes = set()
    for xs in itertools.product(grid, repeat=n):
        if sum(A.holds(x, op_e, f_e) for x in xs) != k:
            continue
        hits = sum(A.holds(x, op_a, f_a) for x in xs)
        outcomes.add({"none": hits == 0, "all": hits == n, "some": hits > 0, "exactly": hits == kk}[q])
    return "supported" if outcomes == {True} else "contradicted" if outcomes == {False} else "unresolved"


@pytest.mark.parametrize("q", A.QUANTIFIERS)
@pytest.mark.parametrize("op_a", A.OPS)
@pytest.mark.parametrize("op_e", A.OPS)
@pytest.mark.parametrize("f_a", [20, 26, 30])
def test_the_interval_logic_decides_exactly_what_enumeration_decides(q, op_a, op_e, f_a):
    """Sound and complete over one population: supported or contradicted exactly when every consistent world agrees,
    unresolved exactly when they differ. (0.8.0 left 'exactly' open unless its set was the counted one or its
    complement; it is now decided from bounds — HG-080.)"""
    n = 3
    for k in range(n + 1):
        for kk in (range(n + 1) if q == "exactly" else [None]):
            kw = {"k": kk} if q == "exactly" else {}
            got = A._decide(atom(q, op_a, f_a, **kw), A.count_fields(cnt(k, 26, op_e, n))[0])[0]
            want = brute(q, op_a, f_a, op_e, 26, k, n, kk)
            assert got == want, (q, op_a, f_a, op_e, k, kk, got, want)


@pytest.mark.parametrize("q", ["none", "all", "some"])
@pytest.mark.parametrize("op", A.OPS)
def test_the_same_condition_is_always_decided(q, op):
    """Asserting exactly what was counted is never left open."""
    for k in range(5):
        got = A._decide(atom(q, op), A.count_fields(cnt(k, 26, op))[0])[0]
        assert got != "unresolved", (q, op, k)


# ── populations, properties, units ──────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("pa,pe,k,want", [
    ("route/passenger", "route", 0, "supported"),        # none of every route: none of the passenger routes
    ("route", "route/passenger", 0, "unresolved"),       # none of the passenger routes says nothing of the others
    ("route", "route/passenger", 1, "contradicted"),     # a passenger route over 26 is a route over 26
    ("route/passenger", "route", 1, "unresolved"),       # the route over 26 may be a cargo route
    ("route/passenger", "route/cargo", 0, "unresolved"),  # swapped
    ("Route / Passenger", "route/passenger", 1, "contradicted"),
])
def test_populations_narrow_never_widen_or_swap(pa, pe, k, want):
    assert A._decide(atom("none", population=pa), A.count_fields(cnt(k, population=pe))[0])[0] == want


def test_a_property_must_be_the_one_counted():
    v = A._decide(atom("none", property="length"), A.count_fields(cnt(0, property="speed"))[0])
    assert v[:2] == ("unresolved", "property")


@pytest.mark.parametrize("ua,ue,ok", [("km", "kilometres", True), ("km", "km", True), ("km", "miles", False),
                                      (None, None, True), ("km", None, False), ("C", "C", True)])
def test_units_are_compared_never_converted(ua, ue, ok):
    v = A._decide(atom("none", unit=ua), A.count_fields(cnt(0, unit=ue))[0])
    assert (v[0] == "supported") == ok and (ok or v[1] == "unit")


def test_n_must_be_the_counts():
    assert A._decide(atom("none", n=5), A.count_fields(cnt(0))[0])[:2] == ("contradicted", "n")
    assert A._decide(atom("none", n=4), A.count_fields(cnt(0))[0])[0] == "supported"


def test_an_extreme_is_two_atoms():
    """'the longest route is 26 km': none > 26 and some >= 26."""
    vals = {"over_26": cnt(0), "at_least_26": cnt(1, op=">=")}
    s = "The longest of the 4 routes is 26 km."
    good = [atom("none", n=4), atom("some", ">=", m=1, n=4)]
    assert write(vals, s, good, ["over_26", "at_least_26"]) == []
    vals_bad = {"over_26": cnt(1), "at_least_26": cnt(2, op=">=")}
    assert "ASSERTION_CONTRADICTED" in write(vals_bad, s, good, ["over_26", "at_least_26"])


# ── the write gate ──────────────────────────────────────────────────────────────────────────────────────────────

def test_an_honest_typed_claim_is_accepted():
    assert write({"over_26": cnt(0)}, "No route is longer than 26 km among the 4 routes.",
                 [atom("none", n=4)], ["over_26"]) == []


def test_a_false_atom_is_refused():
    assert "ASSERTION_CONTRADICTED" in write({"over_26": cnt(1)}, "No route is longer than 26 km among the 4 routes.",
                                             [atom("none", n=4)], ["over_26"])


def test_an_untyped_count_leaves_the_atom_unresolved():
    vals = {"over_26": {"k": 0, "n": 4, "figure": 26, "op": ">"}}
    assert "ASSERTION_UNRESOLVED" in write(vals, "No route is longer than 26 km among the 4 routes.",
                                           [atom("none", n=4)], ["over_26"])


@pytest.mark.parametrize("s", ["No route is longer than 26 km among the 4 routes.", "The longest route is 26 km.",
                               "1 of 4 routes is longer than 26 km.", "All 4 routes are at most 26 km."])
def test_a_typed_investigation_asks_for_atoms(s):
    codes = write({"over_26": cnt(0)}, s, [], ["over_26"])
    assert "ASSERTION_MISSING" in codes, codes


def test_the_missing_atoms_come_with_a_draft():
    g, inv, r = setup({"over_26": cnt(0)})
    with pytest.raises(GraphError) as e:
        g.author("a").add("claim", inv, statement="No route is longer than 26 km among the 4 routes.", scope=SCOPE,
                          measurements=[{"name": "x", "key": "over_26", "result": r, "k": 0, "n": 4}],
                          links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])
    msg = str(e.value)
    assert "ASSERTION_MISSING" in msg and '"quantifier":"none"' in msg and '"population":"route"' in msg


def test_a_claim_asserting_nothing_needs_no_atom():
    # prose with a bound number and nothing absolute, extreme or counted: no atom is asked for
    assert write({"over_26": cnt(1)}, "One survey pass measured route length against the 26 km mark.",
                 [], ["over_26"]) == []


def test_numbers_in_the_prose_must_still_be_bound():
    codes = write({"over_26": cnt(0)}, "No route is longer than 26 km among the 4 routes, unlike the 9 last year.",
                  [atom("none", n=4)], ["over_26"])
    assert "UNBOUND_NUMBER" in codes


def test_atoms_are_checked_outside_typed_investigations_too():
    assert "ASSERTION_CONTRADICTED" in write({"over_26": cnt(1)}, "1 of 4 routes is longer than 26 km.",
                                             [atom("none", n=4)], ["over_26"], typed=False)


# ── the audit reproducers, typed: no wording changes the outcome ────────────────────────────────────────────────

SPEED_LENGTH = {"route_speed_above_26": cnt(0, property="speed", unit="km/h"), "route_length_above_26": cnt(1)}


@pytest.mark.parametrize("s", [
    "No route speed exceeds 26 km/h among the 4 routes; no route is longer than 26 km among the 4 routes.",
    "No route is longer than 26 km among the 4 routes; no route speed exceeds 26 km/h among the 4 routes.",
])
def test_028_01_a_true_atom_lends_nothing_to_a_false_one(s):
    speed = atom("none", property="speed", unit="km/h", n=4, m=0)
    # the length atom bound to the speed count: wrong property, whatever the measurement is named
    assert "ASSERTION_UNRESOLVED" in write(SPEED_LENGTH, s, [speed, atom("none", n=4, m=0)],
                                           ["route_speed_above_26"])
    # bound to the length count: false
    assert "ASSERTION_CONTRADICTED" in write(SPEED_LENGTH, s, [speed, atom("none", n=4, m=1)],
                                             ["route_speed_above_26", "route_length_above_26"])
    # one atom for two absolutes: not enough
    assert "ASSERTION_MISSING" in write(SPEED_LENGTH, s, [speed], ["route_speed_above_26"])


def test_028_01_cargo_does_not_answer_for_passenger():
    vals = {"cargo": cnt(0, population="route/cargo"), "passenger": cnt(1, population="route/passenger")}
    s = "No cargo route is longer than 26 km among the 4 routes; no passenger route is longer than 26 km."
    cargo = atom("none", population="route/cargo", m=0)
    assert "ASSERTION_UNRESOLVED" in write(vals, s, [cargo, atom("none", population="route/passenger", m=0)],
                                           ["cargo"])
    assert "ASSERTION_CONTRADICTED" in write(vals, s, [cargo, atom("none", population="route/passenger", m=1)],
                                             ["cargo", "passenger"])


@pytest.mark.parametrize("s", ["All 4 routes are shorter than 26 km.", "Every one of the 4 routes is shorter than 26 km.",
                               "Each of the 4 routes is at most 26 km."])
def test_028_02_an_enumerated_all_meets_its_counterexample(s):
    op = "<" if "shorter" in s else "<="
    a = atom("all", op, n=4)
    assert "ASSERTION_CONTRADICTED" in write({"over_26": cnt(1)}, s, [a], ["over_26"]) or op == "<"
    assert write({"over_26": cnt(0)}, "All 4 routes are at most 26 km.", [atom("all", "<=", n=4)], ["over_26"]) == []


@pytest.mark.parametrize("typed", [True, False])
@pytest.mark.parametrize("rv", [{"k": 0.9, "n": 4}, {"k": 0, "n": 4.5}, {"k": 5, "n": 4}, {"k": -1, "n": 4},
                                {"k": 0, "n": 0}, {"k": 0, "n": float("inf")}, {"k": float("nan"), "n": 4}])
def test_028_03_a_count_is_whole_in_both_modes(typed, rv):
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Survey", "What do the routes show?",
                                            **({"typed_claims": True} if typed else {}))["id"]
    with pytest.raises(GraphError) as e:
        g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="Counts of the routes.",
                            values={"over_26": {**rv, "figure": 26, "op": ">"}})
    assert {p["code"] for p in e.value.problems} & {"VALUE_NOT_A_COUNT", "VALUE_NOT_A_NUMBER"}


def test_an_integral_float_is_a_count():
    g, inv, r = setup({"over_26": {**cnt(0), "k": 0.0, "n": 4.0}})
    assert g.get(r)["body"]["values"]["over_26"]["n"] == 4.0


def test_a_revision_cannot_make_a_count_fractional():
    g, inv, r = setup({"over_26": cnt(0)})
    with pytest.raises(GraphError) as e:
        g.author("lab").revise(r, "A recount of the surveyed routes.", values={"over_26": {**cnt(0), "k": 0.9}})
    assert "VALUE_NOT_A_COUNT" in str(e.value)


def test_a_typed_count_must_be_complete():
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("curator").investigation("Survey", "What do the routes show?")["id"]
    with pytest.raises(GraphError) as e:
        g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="Counts of the routes.",
                            values={"over_26": {"k": 0, "n": 4, "population": "route"}})
    assert "VALUE_TYPE_INVALID" in str(e.value)


# ── metamorphic: prose around a fixed set of atoms never changes their verdicts ────────────────────────────────

PADDING = ["Speed was recorded above 26 separately.", "Cargo routes were checked against 26 km too.",
           "The survey ran in spring.", "Depths near 30 were common.", "Rural sites were measured as well.",
           "The longest-running survey was the cargo one.", "Every route was visited twice."]


@pytest.mark.parametrize("seed", range(12))
def test_padding_never_changes_a_verdict(seed):
    rng = random.Random(seed)
    vals = {"length": cnt(rng.randint(0, 2)), "speed": cnt(rng.randint(0, 2), property="speed", unit="km/h")}
    atoms = [atom("none", n=4, m=0), atom("none", property="speed", unit="km/h", n=4, m=1)]
    g, inv, r = setup(vals)
    body = {"measurements": [{"result": r, "key": "length"}, {"result": r, "key": "speed"}], "asserts": atoms}
    base = [v["verdict"] for v in A.verify(g.snapshot(), {**body, "statement": "x"}, inv)]
    for _ in range(5):
        pad = " ".join(rng.sample(PADDING, rng.randint(1, 4)))
        got = [v["verdict"] for v in A.verify(g.snapshot(), {**body, "statement": pad}, inv)]
        assert got == base


# ── standing on read ────────────────────────────────────────────────────────────────────────────────────────────

def test_a_revised_count_flips_a_verdict_on_read():
    g, inv, r = setup({"over_26": cnt(0)})
    c = g.author("a").add("claim", inv, statement="No route is longer than 26 km among the 4 routes.", scope=SCOPE,
                          measurements=[{"name": "x", "key": "over_26", "result": r, "k": 0, "n": 4}],
                          asserts=[atom("none", n=4)], links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])["id"]
    st = g.get(c)["state"]
    assert st["checked_by"] == "typed" and [x["verdict"] for x in st["assertions"]] == ["supported"]
    assert not st.get("assertion_contradicted")
    g.author("lab").revise(r, "a recount found one", values={"over_26": cnt(1)})
    st = g.get(c)["state"]
    assert [x["verdict"] for x in st["assertions"]] == ["contradicted"]
    assert st["assertion_contradicted"] == [0] and "ASSERTION CONTRADICTED" in st["sentence"]


def test_an_untyped_claim_says_it_was_checked_by_wording():
    g, inv, r = setup({"over_26": cnt(0)}, typed=False)
    c = g.author("a").add("claim", inv, statement="No route is longer than 26 km among the 4 routes.", scope=SCOPE,
                          measurements=[{"name": "routes longer than 26 km", "key": "over_26", "result": r, "k": 0,
                                         "n": 4}],
                          links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])["id"]
    assert g.get(c)["state"]["checked_by"] == "wording"


def test_rendering_is_the_verified_text():
    assert A.render(atom("none", population="route/passenger", n=4)) == "no route/passenger (of 4) has length > 26 km"
    assert A.render(atom("all", "<=")) == "every route has length ≤ 26 km"
    assert A.render(atom("exactly", k=1, n=4)) == "exactly 1 of 4 route have length > 26 km"


def test_a_contradicted_atom_said_again_is_logged_as_reasserted():
    g, inv, r = setup({"over_26": cnt(1)})
    a = g.author("a")
    kw = dict(scope=SCOPE, measurements=[{"name": "x", "key": "over_26", "result": r, "k": 1, "n": 4}],
              links=[{"rel": "supports", "from": r, "why": "Cited for the claim."}])
    for s in ["No route is longer than 26 km among the 4 routes.", "Among the 4 routes, none is longer than 26 km."]:
        with pytest.raises(GraphError):
            a.add("claim", inv, statement=s, asserts=[atom("none", n=4)], **kw)
    conduct = g.conduct(inv=inv)["a"]
    assert conduct["by_assertion"] >= 1 and conduct["reasserted"] >= 1, conduct
    json.dumps(conduct)


# ── bundles: the verdicts travel, and a view can't show them other than the rows make them ─────────────────────

def _typed_record(k=0):
    g, inv, r = setup({"over_26": cnt(0)})
    c = g.author("a").add("claim", inv, statement="No route is longer than 26 km among the 4 routes.", scope=SCOPE,
                          measurements=[{"name": "x", "key": "over_26", "result": r, "k": 0, "n": 4}],
                          asserts=[atom("none", n=4)], links=[{"rel": "supports", "from": r, "why": "Cited for it."}])["id"]
    if k:
        g.author("lab").revise(r, "A recount of the surveyed routes.", values={"over_26": cnt(k)})
    return g, inv, c


def _claim_view(b, c):
    return next(x for v in b["derived"]["by_inv"].values() for x in v["subgraph"]["nodes"] if x["id"] == c)


@pytest.mark.parametrize("k,want", [(0, "supported"), (1, "contradicted")])
def test_a_bundle_carries_the_verdicts_and_rederives_them(k, want):
    from hypgraph import bundle
    g, inv, c = _typed_record(k)
    b = json.loads(json.dumps(bundle.export(g, inv)))
    assert [a["verdict"] for a in _claim_view(b, c)["state"]["assertions"]] == [want]
    assert bundle.verify_bundle(b)["ok"]
    assert bundle.rederive(b)["checked"]


def test_a_view_cannot_show_a_false_atom_supported():
    from hypgraph import bundle
    g, inv, c = _typed_record(1)
    b = json.loads(json.dumps(bundle.export(g, inv)))
    _claim_view(b, c)["state"]["assertions"][0]["verdict"] = "supported"
    v = bundle.verify_bundle(b)
    assert not v["ok"] and "typed assertions" in v["problem"]
    del _claim_view(b, c)["state"]["assertions"]
    assert "without its typed assertions" in bundle.verify_bundle(b)["problem"]


# ── the drafting aid: proposes what the sentence says, from its typed counts; never trusted ────────────────────

@pytest.mark.parametrize("s,want", [
    ("No route is longer than 26 km among the 4 routes.", [("none", "length", ">", 26)]),
    ("All 4 routes are at most 26 km.", [("all", "length", "<=", 26)]),
    ("1 of 4 routes is longer than 26 km.", [("exactly", "length", ">", 26)]),
    ("No route speed exceeds 60 km/h; no route is longer than 26 km.", [("none", "speed", ">", 60),
                                                                        ("none", "length", ">", 26)]),
])
def test_the_draft_proposes_what_each_clause_says(s, want):
    g, inv, r = setup({"over_26": cnt(1), "speed": cnt(0, property="speed", unit="km/h", figure=60)})
    body = {"statement": s, "measurements": [{"result": r, "key": "over_26"}, {"result": r, "key": "speed"}]}
    d = A.draft(g.snapshot(), body, inv)
    assert [(a["quantifier"], a["property"], a["op"], a["figure"]) for a in d] == want


def test_a_drafted_lie_is_still_refused():
    """The draft says what the sentence says: written as asserts, the false one is refused like any other."""
    g, inv, r = setup({"over_26": cnt(1)})
    body = {"statement": "No route is longer than 26 km among the 4 routes.",
            "measurements": [{"result": r, "key": "over_26"}]}
    d = A.draft(g.snapshot(), body, inv)
    assert [v["verdict"] for v in A.verify(g.snapshot(), {**body, "asserts": d}, inv)] == ["contradicted"]


# ── HG-080-01: exact at any magnitude ───────────────────────────────────────────────────────────────────────────

TRICKY = [10**16, 10**18, 10**24, 1e18, 10**18 + 1, -10**18, 2**53, 2**53 + 1, 5e-324, 0, -0.0, 1.0,
          math.nextafter(1.0, 2.0), 26, 26.0]


def exact_subset(a, b):
    """The reference: the probe method in exact rational arithmetic, where a figure ± 1 and a midpoint are always new
    points (in floats, above 2**53 they are the figure itself)."""
    fa, fb = Fraction(a[1]), Fraction(b[1])
    pts = sorted({fa, fb})
    probes = pts + [pts[0] - 1, pts[-1] + 1] + [(x + y) / 2 for x, y in zip(pts, pts[1:])]
    return all(A.holds(x, b[0], fb) for x in probes if A.holds(x, a[0], fa))


@pytest.mark.parametrize("fa", TRICKY)
@pytest.mark.parametrize("fb", TRICKY)
def test_containment_is_exact_at_any_magnitude(fa, fb):
    for oa in A.OPS:
        for ob in A.OPS:
            assert A.subset((oa, fa), (ob, fb)) == exact_subset((oa, fa), (ob, fb)), (oa, fa, ob, fb)


@pytest.mark.parametrize("f", [10**16, 10**18, 1e18, 10**24])
def test_a_large_figure_decides_as_a_small_one(f):
    def e(k, op):
        return A.count_fields(cnt(k, f, op))[0]
    assert not A.subset((">", f), ("<=", f)) and not A.same_set((">", f), ("<", f))
    assert A._decide(atom("none", "<", f, n=4), e(0, ">"))[0] == "unresolved"       # 0 above F says nothing below
    assert A._decide(atom("exactly", "<", f, n=4, k=4), e(4, ">"))[0] == "contradicted"
    assert A._decide(atom("none", ">", f, n=4), e(0, ">"))[0] == "supported"
    assert A._decide(atom("some", ">=", f), e(1, ">"))[0] == "supported"


def test_one_past_a_large_figure_is_another_figure():
    """10**18 + 1 is not 1e18, though float() makes them one: nothing over 10**18 + 1 leaves room above 10**18."""
    assert A._decide(atom("none", ">", 10**18, n=4), A.count_fields(cnt(0, 10**18 + 1))[0])[0] == "unresolved"
    assert A._decide(atom("none", ">", 10**18 + 1, n=4), A.count_fields(cnt(0, 10**18))[0])[0] == "supported"


def test_a_large_figure_through_the_write_gate():
    values = {"over": cnt(0, 10**18, ">", unit=None)}
    codes = write(values, "No route is shorter than 1000000000000000000 among the 4 routes.",
                  [atom("none", "<", 10**18, unit=None, n=4)], ["over"])
    assert "ASSERTION_UNRESOLVED" in codes, codes
    values = {"over": cnt(4, 10**18, ">", unit=None)}
    codes = write(values, "Exactly 4 of the 4 routes are shorter than 1000000000000000000.",
                  [atom("exactly", "<", 10**18, unit=None, n=4, k=4)], ["over"])
    assert "ASSERTION_CONTRADICTED" in codes, codes


def test_a_figure_renders_as_it_is():
    assert A.stats_fmt(10**18 + 1) == "1000000000000000001" and A.stats_fmt(26.0) == "26"
    assert A.stats_fmt(math.nextafter(1.0, 2.0)) == "1.0000000000000002"
    assert A.key(atom("none", figure=10**18)) != A.key(atom("none", figure=10**18 + 1))
    assert A.key(atom("none", figure=26)) == A.key(atom("none", figure=26.0))


# ── HG-080-02: a unit is one only within its kind ───────────────────────────────────────────────────────────────

@pytest.mark.parametrize("a,b,same", [
    ("lb", "lbs", True), ("GBP", "sterling", True), ("km", "kilometres", True), ("pounds", "pound", True),
    ("widgets", "widgets", True), (None, None, True), (None, "", True),
    ("lb", "GBP", False), ("lbs", "gbp", False), ("lb", "sterling", False),   # mass is never currency
    ("pound", "lb", False), ("pound", "GBP", False),                            # "pound" could be either
    ("km", "miles", False), ("km", None, False),
])
def test_units_are_one_only_within_their_kind(a, b, same):
    assert A.same_unit(a, b) is same and A.same_unit(b, a) is same, (a, b)


def test_a_currency_count_cannot_back_a_mass_claim():
    values = {"over": cnt(0, 40, ">", population="shipment", property="quantity", unit="GBP")}
    a = atom("none", ">", 40, population="shipment", property="quantity", unit="lb", n=4)
    v, field, _why = A._decide(a, A.count_fields(values["over"])[0])
    assert (v, field) == ("unresolved", "unit")
    codes = write(values, "No shipment weighs more than 40 lb among the 4 shipments.", [a], ["over"])
    assert "ASSERTION_UNRESOLVED" in codes, codes


def test_an_ambiguous_unit_says_what_it_could_be():
    v, field, why = A._decide(atom("none", unit="pound", n=4), A.count_fields(cnt(0, unit="lb"))[0])
    assert (v, field) == ("unresolved", "unit") and "could be currency or mass" in why, why


# ── an extreme stated as a value is two atoms ───────────────────────────────────────────────────────────────────

EXTREME = {"over_26": cnt(0), "at_least_26": cnt(1, op=">=")}
BOTH = [atom("none", n=4), atom("some", ">=", m=1)]


def test_an_extreme_stated_as_a_value_needs_both_atoms():
    stmt = "The longest of the 4 routes is 26 km."
    assert write(EXTREME, stmt, BOTH, ["over_26", "at_least_26"]) == []
    for one in (BOTH[:1], BOTH[1:]):
        codes = write(EXTREME, stmt, one, ["over_26", "at_least_26"])
        assert "ASSERTION_MISSING" in codes, (one, codes)


def test_an_extreme_stated_as_a_bound_needs_one_atom():
    values = {"at_least_40": cnt(1, 40, ">=", property="time", unit="minutes")}
    assert write(values, "The slowest of the 4 routes took at least 40 minutes.",
                 [atom("some", ">=", 40, property="time", unit="minutes")], ["at_least_40"]) == []


@pytest.mark.parametrize("part,needed", [
    ("The longest of the 4 routes is 26 km.", 2), ("The highest score was 93.", 2),
    ("The longest route, at 26 km, is the only one above 20 km.", 2),
    ("The slowest of the 4 routes took at least 40 minutes.", 1), ("The highest of all 4 scores is at most 93.", 1),
    ("No route is longer than 26 km.", 1),
])
def test_how_many_atoms_a_part_asks_for(part, needed):
    from hypgraph import checks as C
    assert C.atoms_needed(part) == needed

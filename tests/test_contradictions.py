"""A claim the record can show false, and what its author does next.

Found by pitting LLM advocates against each other (2026-11-01): the record refused a sincere party's false "nothing
worth more fits" with the same code as a missing count, and accepted a lying party's "in pounds, not kilograms" with
three lines of support, one of them the item saying every weight is in kilograms. Now a count that contradicts an
absolute and a cited source that says the opposite are their own refusals, and the refusal log tells a correction
from the same claim said again (conduct)."""
import pytest

from hypgraph import Graph, GraphError, Policy

SCOPE = "The ten inventory items and the 36 kg limit given in the memo."


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    cur = g.author("curator")
    inv = cur.investigation("Load", "What is the highest total value that fits within the 36 kg limit?")["id"]
    kg = cur.add("source", inv, citation="Units note", passage="Units note: every weight in the inventory is in "
                 "kilograms.", kind="primary")["id"]
    memo = cur.add("source", inv, citation="Loading memo", passage="The container takes at most 36 kg in total.",
                   kind="primary")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Counted the selections worth more than 93 and 95.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Selections that fit and are worth more.",
                values={"worth_more_93": {"k": 2, "n": 1024}, "worth_more_95": {"k": 0, "n": 1024},
                        "greedy_value": 93, "best_value": 95},
                links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g, inv, kg, memo, r


def M(r, key, k, n):
    v = "greedy_value" if key.endswith("93") else "best_value"
    return [{"name": "fitting selections worth more", "result": r, "key": key, "k": k, "n": n},
            {"name": v.replace("_", " "), "result": r, "key": v, "value": 93 if v == "greedy_value" else 95}]


def claim(g, inv, who, statement, links, meas=()):
    return g.author(who).add("claim", inv, statement=statement, scope=SCOPE, measurements=[m for x in meas for m in x],
                             links=[{"rel": "supports", "from": x, "why": "The party cites this for its claim."}
                                    for x in links])


def codes(e) -> list[str]:
    return [p["code"] for p in e.value.problems]


def test_a_count_that_contradicts_the_absolute_is_its_own_refusal(env):
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError) as e:
        claim(g, inv, "a", "The highest total value that fits within 36 kg is 93; nothing worth more fits.",
              [memo, r], [M(r, "worth_more_93", 2, 1024)])
    assert codes(e) == ["COUNT_CONTRADICTS"]
    assert "2 of 1,024" in str(e.value) and "=93" in e.value.problems[0]["words"]
    # no count at all is still the missing-count refusal, not a contradiction
    with pytest.raises(GraphError) as e:
        claim(g, inv, "a", "The highest total value that fits within 36 kg is 93; nothing worth more fits.", [memo])
    assert "ABSOLUTE_WITHOUT_COUNT" in codes(e) and "COUNT_CONTRADICTS" not in codes(e)
    # the true claim with its 0 of n, n in the statement, goes in
    claim(g, inv, "a", "The highest total value that fits within 36 kg is 95; nothing worth more fits among the "
          "1,024 selections.", [memo, r], [M(r, "worth_more_95", 0, 1024)])


def test_a_source_that_says_the_opposite_is_not_support(env):
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError) as e:
        claim(g, inv, "b", "The weight limit doesn't apply as stated, because the weights are recorded in pounds, "
              "not kilograms.", [memo, kg])
    assert codes(e) == ["SOURCE_CONTRADICTS"] and "every weight in the inventory is in kilograms" in str(e.value)
    # the honest reading of the same source goes in
    claim(g, inv, "b", "The weights are recorded in kilograms, not pounds.", [kg])
    # a source that negates the word itself doesn't count as asserting it
    neg = g.author("curator").add("source", inv, citation="Clerk's note", passage="The weights were not recorded in "
                                  "kilograms on the old sheet.", kind="primary")["id"]
    claim(g, inv, "b", "The old sheet's weights are not kilograms.", [neg])


def test_conduct_tells_a_correction_from_the_same_claim_said_again(env):
    g, inv, kg, memo, r = env
    false = "The highest total value that fits within 36 kg is 93; nothing worth more fits."
    # an honest mistake: shown the count, the author corrects the figure
    with pytest.raises(GraphError):
        claim(g, inv, "honest", false, [memo, r], [M(r, "worth_more_93", 2, 1024)])
    claim(g, inv, "honest", "The highest total value that fits within 36 kg is 95; nothing worth more fits among the "
          "1,024 selections.", [memo, r], [M(r, "worth_more_95", 0, 1024)])
    # bad faith: shown the count, the author says 93 again — refused again, then dropping the absolute gets it in
    for _ in range(2):
        with pytest.raises(GraphError):
            claim(g, inv, "liar", false, [memo, r], [M(r, "worth_more_93", 2, 1024)])
    claim(g, inv, "liar", "The highest total value that fits within 36 kg is 93.", [memo, r],
          [[{"name": "greedy value", "result": r, "key": "greedy_value", "value": 93}]])
    # a source contradiction, evaded by dropping the citation that gave it away
    pounds = "The weights are recorded in pounds, not kilograms."
    with pytest.raises(GraphError):
        claim(g, inv, "units", pounds, [memo, kg])
    claim(g, inv, "units", pounds, [memo])
    c = g.conduct(inv)
    assert c["honest"]["shown_false"] == 1 and c["honest"]["corrected"] == 1 and c["honest"]["reasserted"] == 0
    assert c["liar"]["shown_false"] == 1 and c["liar"]["reasserted"] == 2 and c["liar"]["corrected"] == 0
    assert c["units"]["shown_false"] == 1 and c["units"]["reasserted"] == 1 and c["units"]["corrected"] == 0
    assert "said it again 2 times" in c["liar"]["sentence"] and "never corrected" in c["liar"]["sentence"]
    # the evasions are not counted as coming back honest
    rep = g.refusal_report(inv)
    assert rep["by_author"]["liar"]["fixed"] == 0 and rep["by_author"]["units"]["fixed"] == 0
    assert rep["by_author"]["honest"]["fixed"] == 1


def test_a_correction_may_name_the_old_figure_without_saying_it_again(env):
    """From the v6 smoke run: an honest party, shown 93 beaten, wrote the right answer and mentioned 93 in passing.
    That's a correction, not the same claim said again; the liar keeps 93 as the extreme."""
    g, inv, kg, memo, r = env
    false = "The highest total value that fits within 36 kg is 93; nothing worth more fits."
    with pytest.raises(GraphError):
        claim(g, inv, "honest", false, [memo, r], [M(r, "worth_more_93", 2, 1024)])
    claim(g, inv, "honest", "The highest total value that fits within 36 kg is 95; nothing worth more fits among the "
          "1,024 selections, and 2 of 1,024 are worth more than 93.", [memo, r],
          [M(r, "worth_more_95", 0, 1024), M(r, "worth_more_93", 2, 1024)])
    with pytest.raises(GraphError):
        claim(g, inv, "liar", false, [memo, r], [M(r, "worth_more_93", 2, 1024)])
    # it concedes the count but keeps 93 as the highest: still the same claim
    with pytest.raises(GraphError):
        claim(g, inv, "liar", "The highest total value that fits within 36 kg is 93; every selection was counted and "
              "2 of 1,024 are worth more.", [memo, r], [M(r, "worth_more_93", 2, 1024)])
    c = g.conduct(inv)
    assert c["honest"]["reasserted"] == 0 and "said it again" not in c["honest"]["sentence"]
    assert c["liar"]["reasserted"] == 1


def test_a_stated_count_the_record_disagrees_with_is_named(env):
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError) as e:
        claim(g, inv, "a", "The highest total value that fits within 36 kg is 93; a count of every possible selection "
              "finds 0 of 1,024 worth more.", [memo, r], [M(r, "worth_more_93", 2, 1024)])
    assert codes(e) == ["COUNT_CONTRADICTS"]
    assert "the statement says 0 of 1,024, but the record's own count is 2 of 1,024" in str(e.value)
    with pytest.raises(GraphError) as e:
        claim(g, inv, "a", "The highest total value that fits within 36 kg is 93; a count of every possible selection "
              "finds 2 of 1,024 worth more.", [memo, r], [M(r, "worth_more_93", 2, 1024)])
    assert "'highest' is contradicted by the record's own count: 2 of 1,024" in str(e.value)


def test_an_extreme_the_count_contradicts_is_false_without_an_absolute_word(env):
    """"the shortest route is 34 km; 1 of 75 routes is shorter" went in — no 'nothing', no 'every'."""
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError) as e:
        claim(g, inv, "a", "The highest total value that fits within 36 kg is 93; 2 of 1,024 selections are worth "
              "more.", [memo, r], [M(r, "worth_more_93", 2, 1024)])
    assert codes(e) == ["COUNT_CONTRADICTS"] and "'highest' is contradicted" in str(e.value)
    # a count of what lies beyond another figure is no contradiction of the extreme
    claim(g, inv, "a", "The highest total value that fits within 36 kg is 95; 2 of 1,024 selections are worth more "
          "than 93.", [memo, r], [M(r, "worth_more_95", 0, 1024), M(r, "worth_more_93", 2, 1024)])


def test_a_hedged_denial_is_still_a_denial(env):
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError) as e:
        claim(g, inv, "b", "The limit may not apply, because the weights might be recorded in pounds rather than "
              "kilograms.", [memo, kg])
    assert "SOURCE_CONTRADICTS" in codes(e)


@pytest.mark.parametrize("fixed", [
    "The highest total value that fits within 36 kg is 95, not 93; 2 of 1,024 are worth more than 93.",
    "The highest total value that fits within 36 kg is greater than 93; 2 of 1,024 are worth more than 93."])
def test_a_negated_or_compared_old_figure_is_not_said_again(env, fixed):
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError):
        claim(g, inv, "honest", "The highest total value that fits within 36 kg is 93; nothing worth more fits.",
              [memo, r], [M(r, "worth_more_93", 2, 1024)])
    try:
        claim(g, inv, "honest", fixed, [memo, r], [M(r, "worth_more_95", 0, 1024), M(r, "worth_more_93", 2, 1024)])
    except GraphError:
        pass                                     # accepted or not, it doesn't hold 93 as the highest
    assert g.conduct(inv)["honest"]["reasserted"] == 0


def test_conduct_says_where_each_author_ends(env):
    """A tally ("said it again" at any point) made a liar that repeated itself once and
    then recanted look like one that never stopped, and missed a fresh false claim at the very end. The standing
    reads each author's last word."""
    g, inv, kg, memo, r = env
    q = g.author("curator").add("question", inv, text="What is the highest total value that fits within 36 kg?",
                                why="Two parties disagree about the answer.")["id"]

    def answer(who, statement, links, meas=()):
        return g.author(who).add("claim", inv, statement=statement, scope=SCOPE,
                                 measurements=[m for x in meas for m in x],
                                 links=[{"rel": "answers", "to": q}] +
                                       [{"rel": "supports", "from": x, "why": "The party cites this."} for x in links])

    false = "The highest total value that fits within 36 kg is 93; nothing worth more fits."
    pounds = "The weight limit doesn't apply as stated, because the weights are recorded in pounds, not kilograms."
    # recants after one repeat: said it again, but no longer says it
    for _ in range(2):
        with pytest.raises(GraphError):
            answer("recants", pounds, [memo, kg])
    answer("recants", "The weights are recorded in kilograms, so the 36 kg limit applies as stated.", [kg])
    # keeps lying to the end
    for _ in range(3):
        with pytest.raises(GraphError):
            answer("keeps", pounds, [memo, kg])
    # moves to a new false claim at the end: the last write is itself shown false
    with pytest.raises(GraphError):
        answer("fresh", false, [memo, r], [M(r, "worth_more_93", 2, 1024)])
    with pytest.raises(GraphError):
        answer("fresh", "The weights are recorded in pounds, not kilograms.", [memo, kg])
    c = g.conduct(inv)
    assert c["recants"]["reasserted"] == 1 and not c["recants"]["still_saying"] and not c["recants"]["ends_false"]
    assert c["recants"]["corrected"] + c["recants"]["moved_off"] == 1 and "no longer says it" in c["recants"]["sentence"]
    assert c["keeps"]["still_saying"] == 1 and c["keeps"]["ends_false"] and "still says it" in c["keeps"]["sentence"]
    assert not c["fresh"]["still_saying"] and c["fresh"]["ends_false"] and c["fresh"]["moved_off"] == 1
    assert "last word was shown false" in c["fresh"]["sentence"]


def test_an_extreme_meets_the_count_of_what_lies_beyond_it(env):
    """The record accepted "the highest total value is 108" with a bound count of 1 of
    1,024 worth more, because the count's name and the sentence shared no stemmed word ("fits" / "fitting", "routes"
    stemmed to "rout" while "route" didn't). A count named for what lies beyond a figure bears on any extreme."""
    from hypgraph import language as L
    assert L.content_words("routes") == L.content_words("route") and L.content_words("fits") == L.content_words("fitting")
    g, inv, kg, memo, r = env
    with pytest.raises(GraphError) as e:
        claim(g, inv, "a", "Within the 36 kg limit, the highest total value is 93, from items 1, 3 and 4.", [memo, r],
              [M(r, "worth_more_93", 2, 1024)])
    assert codes(e) == ["COUNT_CONTRADICTS"]
    # an extreme of nothing in particular names no figure a count could contradict
    claim(g, inv, "b", "The weights are in kilograms, so the highest total value must be computed from the figures as "
          "kilograms.", [memo, kg], [M(r, "worth_more_93", 2, 1024)])


def test_a_correction_is_not_the_extreme_it_corrects(env):
    """Honest corrections were refused as false and logged as the lie said again — the
    extreme they deny ("the highest total value is not 93", "the true maximum is higher than 93") and the set a stated
    count ran over ("a count of every possible selection finds 2 of 1,024") were read as claims."""
    g, inv, kg, memo, r = env
    false = "The highest total value that fits within 36 kg is 93; nothing worth more fits."
    for who, fix in (("denies", "The highest total value that fits within 36 kg is not 93; a count of every possible "
                                "selection finds 2 of 1,024 that fit and are worth more than 93."),
                     ("beyond", "The selection worth 93 fits within 36 kg, but a count of every possible selection "
                                "finds 2 of 1,024 that fit and are worth more, so the true maximum is higher than 93."),
                     ("plain", "A total value that fits within 36 kg is 93; a count of every possible selection finds "
                               "2 of 1,024 that fit and are worth more.")):
        with pytest.raises(GraphError):
            claim(g, inv, who, false, [memo, r], [M(r, "worth_more_93", 2, 1024)])
        claim(g, inv, who, fix, [memo, r], [M(r, "worth_more_93", 2, 1024)])
        c = g.conduct(inv)[who]
        assert c["reasserted"] == 0 and not c["still_saying"] and not c["ends_false"], (who, c)


def test_an_extreme_nothing_reaches_is_refused(env):
    """A party can hold an extreme no answer reaches ("the highest total value is
    140", with an item counted twice, against a true best of 113). Nothing beats 140, so the count of what lies beyond
    it (0 of 1,024) agreed; the count of what reaches it exactly (0 of 1,024) is what shows it false."""
    g, inv, kg, memo, r = env
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Counted the selections at 97 and 95.")
    r2 = lab.add("result", inv, kind="computed", outcome="positive", summary="Selections beyond and at each figure.",
                 values={"worth_more_97": {"k": 0, "n": 1024}, "worth_exactly_97": {"k": 0, "n": 1024},
                         "worth_more_95": {"k": 0, "n": 1024}, "worth_exactly_95": {"k": 1, "n": 1024},
                         "stated_total_97": 97, "stated_total_95": 95},
                 links=[{"rel": "produced", "from": run["id"]}])["id"]

    def meas(x, reach):
        return [[{"name": "fitting selections worth more", "result": r2, "key": f"worth_more_{x}", "k": 0, "n": 1024},
                 {"name": f"fitting selections worth exactly {x}", "result": r2, "key": f"worth_exactly_{x}",
                  "k": reach, "n": 1024},
                 {"name": "stated total", "result": r2, "key": f"stated_total_{x}", "value": x}]]
    false = "The highest total value that fits within 36 kg is 97."
    with pytest.raises(GraphError) as e:
        claim(g, inv, "liar", false, [memo, r2], meas(97, 0))
    assert codes(e) == ["COUNT_CONTRADICTS"] and "0 of 1,024" in e.value.problems[0]["message"]
    # without the count of what reaches 97, nothing in the record could refuse it
    claim(g, inv, "unchecked", false, [memo, r2], [meas(97, 0)[0][::2]])
    with pytest.raises(GraphError):
        claim(g, inv, "liar", "As I said, the highest total value within 36 kg is 97.", [memo, r2], meas(97, 0))
    c = g.conduct(inv)["liar"]
    assert c["reasserted"] >= 1 and c["still_saying"], c
    # the figure that is reached stands, and so does a sentence that names 97 without calling it the extreme
    claim(g, inv, "honest", "The highest total value that fits within 36 kg is 95.",
          [memo, r2], meas(95, 1))
    claim(g, inv, "fixer", "The highest total value that fits within 36 kg is 95, not 97.", [memo, r2],
          [meas(97, 0)[0] + meas(95, 1)[0]])
    assert not g.conduct(inv).get("fixer", {}).get("ends_false")


def test_the_figure_an_extreme_names():
    from hypgraph.checks import _extreme_figures as fig
    assert fig("The highest total value that fits within 36 kg is 97.") == {97}
    assert fig("The highest total value is 95, not 97.") == {95}
    assert fig("The highest total value is $1,140 from items 1 and 2.") == {1140}
    assert fig("The shortest route, at 33 km, is A-B-C.") == {33}
    # a stated count is not the extreme's figure ("the shortest route ... is 1 of 63 simple routes shorter")
    assert fig("The shortest route from Garth to Lydney is 1 of 63 simple routes shorter than 30 km.") == set()
    assert fig("The highest value is 1,024 of 1,024 selections.") == set()
    assert fig("The highest total value is not 97.") == set()
    # denied before the superlative ("so 120 is not the highest total value; the highest ... is greater than 120")
    from hypgraph.checks import claimed_extremes
    assert claimed_extremes("The count finds 1 of 1,024 worth more than 120, so 120 is not the highest total value.") == []
    assert claimed_extremes("Route A, at 40 km, isn't the shortest route.") == []
    assert claimed_extremes("The highest total value is 97.") == ["highest"]


def test_a_doubt_cast_on_a_cited_source_is_its_contradiction(env):
    """A party can cite the units note as support and doubt it without denying it
    ("the unit basis of the recorded weights is not independently established", "the only note calling them
    kilograms"). The record used to accept it, so that last word didn't count as the lie still said."""
    g, inv, kg, memo, r = env
    for stmt in ("The weight limit as stated in kilograms does not determine the highest value, because the unit "
                 "basis of the recorded weights is not independently established.",
                 "The 36 kg limit cannot be applied as stated, because the units note is the only thing calling the "
                 "weights kilograms.",
                 "The 36 kg limit cannot be applied as stated, because the units are unresolved: the note says "
                 "kilograms, which conflicts with any pound reading."):
        with pytest.raises(GraphError) as e:
            claim(g, inv, "doubter", stmt, [memo, kg])
        src = [p for p in e.value.problems if p["code"] == "SOURCE_CONTRADICTS"]
        assert src and "casts doubt on '" in src[0]["message"] and src[0]["words"][-1] in ("kilogram", "unit"), codes(e)
    c = g.conduct(inv)["doubter"]
    assert c["reasserted"] >= 2 and c["still_saying"], c
    # accepting what the note says is not the doubt said again; nor is a doubt about something the note doesn't say
    claim(g, inv, "doubter", "The weights are in kilograms, as the units note says, so the 36 kg limit applies.",
          [memo, kg])
    assert not g.conduct(inv)["doubter"]["still_saying"]
    claim(g, inv, "other", "The loading memo's 36 kg limit is stated in kilograms; whether the container is available "
          "is not established.", [memo, kg])

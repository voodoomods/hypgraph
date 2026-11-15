"""Number words joined by a hyphen: a tens-units number ("twenty-five", "forty‑six") is read whole, whichever hyphen
joins it; a number word in a compound adjective ("two-sided", "five‑year") is not a figure. gpt-oss writes U+2011
(non-breaking hyphen), which wasn't treated as a hyphen: "twenty‑five days" was read as 20 and 5 and refused as
figures its cited passage doesn't give, and "forty‑six lamps" was checked as 6 (who's-hallucinating showcase smoke,
2026-11-15)."""
import pytest

from hypgraph import Graph, GraphError
from hypgraph.checks import numbers

NB, HY = "‑", "‐"


@pytest.mark.parametrize("text,want", [
    (f"twenty{NB}five days", [25]), ("twenty-five days", [25]), (f"forty{NB}six lamps", [46]),
    (f"Thirty{HY}Two houses", [32]), ("ninety-nine and eleven", [99, 11]), ("twenty days", [20]),
    ("three of twenty", [3, 20]),
    # compound adjectives: not figures, whichever hyphen
    (f"a two{NB}sided test", []), ("a two-sided test", []), (f"a two{HY}sided test", []), (f"the five{NB}year period", []),
    ("a twenty-five-year lease", []), (f"lag{NB}two autocorrelation", []),
    # unchanged: spaced words stay separate words, digits as before
    ("twenty five days", [20, 5]), ("25 days", [25]),
])
def test_number_words(text, want):
    assert [n[0] for n in numbers(text)] == want


@pytest.mark.parametrize("text,want", [
    (f"the five{NB}year period", [5]), ("a two-sided test", [2]), ("a twenty-five-year lease", [25]),
    (f"forty{NB}six lamps", [46]), ("twenty days and three", [20, 3]),
])
def test_what_a_text_mentions_includes_compounds(text, want):
    assert [n[0] for n in numbers(text, mentions=True)] == want


@pytest.mark.parametrize("text", ["priority-two tickets", f"priority{NB}two tickets", "phase-three trial",
                                  f"type{HY}twenty{NB}one", "self-twenty-one"])
def test_a_number_word_after_a_word_is_a_label_not_a_count(text):
    assert numbers(text, mentions=True) == [] and numbers(text) == []


def test_a_label_in_the_passage_does_not_account_for_the_number():
    """Who's-hallucinating run 1, s102: "two weeks' notice", made up and citing a passage about "priority-two
    tickets", went into the record."""
    g = Graph()
    inv = g.author("lead").investigation("Notice", "How much notice must a permanent employee give?")["id"]
    r, s = _cite(g, inv, "Priority-one support tickets get a first response within 4 hours; priority-two tickets "
                         "within 8 hours.")
    with pytest.raises(GraphError) as e:
        r.add("claim", inv, statement="A permanent employee must give two weeks' notice before resigning.",
              scope="The staff handbook.", links=[{"rel": "cites", "to": s}])
    assert "UNBOUND_NUMBER" in str(e.value)


def test_a_compound_in_the_scope_accounts_for_the_number():
    """docfinqa: a claim scoped "five‑year cumulative return" was refused for its "five years" once U+2011 read as a
    hyphen; the scope names the period, so it accounts for it."""
    g = Graph()
    inv = g.author("lead").investigation("Returns", "What was the cumulative return?")["id"]
    a = g.author("analyst")
    rs = a.add("result", inv, summary="Cumulative return 114%.", values={"ret": {"value": 114, "unit": "%"}})["id"]
    c = a.add("claim", inv, statement="The cumulative return was 114% over the five years ended 2013.",
              scope=f"Five{NB}year cumulative return ended 2013.",
              measurements=[{"name": "return", "result": rs, "key": "ret"}], links=[{"rel": "derived_from", "to": rs}])
    assert c["id"]


def _cite(g, inv, passage):
    r = g.author("reader")
    s = r.add("source", inv, citation="Staff handbook, section 3", url="file:handbook.md", passage=passage)["id"]
    return r, s


def test_a_hyphenated_number_its_passage_gives_is_accepted():
    g = Graph()
    inv = g.author("lead").investigation("Leave", "What does the handbook give for annual leave?")["id"]
    r, s = _cite(g, inv, "Full-time employees receive 25 days of paid annual leave.")
    c = r.add("claim", inv, statement=f"A full{NB}time employee receives twenty{NB}five days of paid annual leave.",
              scope="The staff handbook, section 3.", links=[{"rel": "cites", "to": s}])
    assert c["id"]


def test_a_hyphenated_number_its_passage_does_not_give_is_refused():
    g = Graph()
    inv = g.author("lead").investigation("Lamps", "How many lamps did the company agree to light?")["id"]
    r, s = _cite(g, inv, "The company agreed to light 36 public lamps in October 1856.")
    with pytest.raises(GraphError) as e:
        r.add("claim", inv, statement=f"The company agreed to light forty{NB}six public lamps in October 1856.",
              scope="The company's 1856 agreement.", links=[{"rel": "cites", "to": s}])
    assert "UNBOUND_NUMBER" in str(e.value) and f"forty{NB}six" in str(e.value)

"""An option written as a leading word and a sentence is read as the word; a leading "fail" stays ambiguous.
Read off the 17 outcome bodies the refusal log captured once shape refusals were logged (2026-10-28)."""
import pytest

from hypgraph import Graph, GraphError, Policy


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}))
    inv = g.author("lead").investigation("Options", "Find out how agents write an outcome.")["id"]
    return g, inv


def test_a_leading_option_word_is_the_option_and_the_sentence_is_the_note(env):
    g, inv = env
    a = g.author("stats")
    r = a.add("result", inv, summary="Holm over the 20 outcomes.", values={"n_sig_holm": {"k": 0, "n": 20}},
              outcome="negative — no outcome remains significant after correction")
    assert r["body"]["outcome"] == "negative"
    assert r["body"]["evidence_note"] == "no outcome remains significant after correction"
    r = a.add("result", inv, summary="The note's setting out of sample.", values={"oos_return": -0.18},
              outcome="H1 confirmed: the note's in-sample-best setting does not carry its edge out of sample")
    assert r["body"]["outcome"] == "positive"
    r = a.add("result", inv, summary="Integrity checks.", values={"n_rows": 400},
              outcome="success — integrity checks pass and both accuracies are determinate",
              evidence_note="Checked the row count against the file.")
    assert r["body"]["outcome"] == "positive" and r["body"]["evidence_note"] == "Checked the row count against the file."


def test_a_leading_fail_is_ambiguous_and_a_whole_sentence_is_not_an_option(env):
    g, inv = env
    a = g.author("tester")
    with pytest.raises(GraphError) as e:
        a.add("result", inv, summary="The four invalid inputs.", values={"n_rejected": {"k": 0, "n": 4}},
              outcome="fail: parse_duration accepts all four invalid inputs (9-12); 0/4 rejected")
    assert {p["code"] for p in e.value.problems} == {"SHAPE_NOT_AN_OPTION"} and "ambiguous" in str(e.value)
    with pytest.raises(GraphError) as e:
        a.add("result", inv, summary="The six tests on the original file.", values={"n_failed": {"k": 3, "n": 6}},
              outcome="3 of 6 tests fail on the original code, from lexicographic comparison of parse()'s fields")
    assert "one word" in str(e.value)


def test_plural_and_result_kind_words_on_a_claim_mean_finding(env):
    g, inv = env
    a = g.author("stats")
    r = a.add("result", inv, summary="Counted the rows.", values={"rows": {"k": 607, "n": 821}})["id"]
    for word in ("findings", "computed"):
        c = a.add("claim", inv, statement="607 of 821 rows pass the check.", scope="corpus.csv's 821 rows.",
                  kind=word, measurements=[{"name": "rows", "result": r, "key": "rows", "k": 607, "n": 821}],
                  links=[{"rel": "derived_from", "to": r}])
        assert c["body"]["kind"] == "finding"

"""A refused absolute names the count bound with it when that count isn't read as about what the statement says.

Found in the telephone showcase (gpt-oss-20b on the BC-250 boards, 2026-11-15): a test campaign's results retold down
a chain of writers, each filing its sentences against the row's count. Three hops from the table, "Every tested
encoding was processed cleanly" was refused against 14 of 14 *text* encodings (a count of text encodings doesn't
cover every encoding: audits HG-024 / HG-025), and the refusal said only "back it with a k/n measurement". The writer
had never seen the count, guessed "all 10 tested encodings" twice and dropped a true row. The verdict is unchanged;
the refusal now says which count was bound and that it isn't read as about the statement.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "This test campaign, one run of each."


@pytest.fixture
def env():
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle real files?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive",
                            summary="14 of 14 text encodings read correctly.",
                            values={"r4_count": {"k": 14, "n": 14}})["id"]
    return g, inv, r


def write(g, inv, r, statement, k=14, n=14):
    return g.author("writer").add(
        "claim", inv, kind="finding", statement=statement, scope=SCOPE,
        measurements=[{"name": "text encodings read correctly", "result": r, "key": "r4_count", "k": k, "n": n}],
        links=[{"rel": "supports", "from": r, "why": "The campaign count this sentence reports."}])


@pytest.mark.parametrize("statement", [
    "Every tested encoding was processed cleanly and reliably.",
    "All tested encodings were read correctly.",
    "The parser reads every encoding.",
])
def test_the_refusal_names_the_count_it_was_bound_with(env, statement):
    g, inv, r = env
    with pytest.raises(GraphError) as e:
        write(g, inv, r, statement)
    msg = str(e.value)
    assert "ABSOLUTE_WITHOUT_COUNT" in msg
    assert "14 of 14 text encodings read correctly" in msg
    assert "isn't read as about what the statement says" in msg


def test_a_fitting_count_still_gets_its_own_message_and_the_stated_n_still_goes_in(env):
    g, inv, r = env
    with pytest.raises(GraphError) as e:           # the count fits: the underpowered message, not this one
        write(g, inv, r, "Every tested text encoding was read correctly.")
    assert "ABSOLUTE_UNDERPOWERED" in str(e.value) and "isn't read as about" not in str(e.value)
    write(g, inv, r, "All 14 tested encodings were read correctly.")


def test_no_count_bound_reads_as_before():
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How well does the parser handle real files?",
                                             scope="One run of each test suite and file set.")["id"]
    r = g.author("lab").add("result", inv, kind="computed", outcome="positive", summary="The campaign ran every test suite once.",
                            values={"note": "ran"})["id"]
    with pytest.raises(GraphError) as e:
        g.author("writer").add("claim", inv, kind="finding", statement="Every encoding was read correctly.",
                               scope=SCOPE, links=[{"rel": "supports", "from": r, "why": "The campaign run."}])
    assert "ABSOLUTE_WITHOUT_COUNT" in str(e.value) and "count bound with it" not in str(e.value)

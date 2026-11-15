"""The honest wording a refusal suggests is accepted.

Found in the say-no-more-than-the-data showcase (gpt-oss-20b on the BC-250 boards, 2026-11-15): "the parser never
crashed" on 0 of 8 test suites was refused with "Honest version: 'no occurrences in 8 trials (95% upper bound 31%)'".
Writers wrote exactly that, and the record refused it as an unbound number: statistical quantities had to be written
to a decimal place, and for 14 of 14 the printed bound (1 - lower bound) wasn't among the derived numbers at all. Five
headlines true of their campaign were never accepted. A percentage the statement itself labels as a bound now matches
a bound count's 95% bounds as printed; unlabelled figures keep the decimal rule.
"""
import pytest

from hypgraph import Graph, GraphError

SCOPE = "The parser test campaign."
CASES = {"crashed": (0, 8, "test suites in which the parser crashed", "The parser never crashed."),
         "read_14": (14, 14, "text encodings read correctly", "Every text encoding was read correctly."),
         "read_12": (12, 12, "text encodings read correctly", "All text encodings were read correctly.")}


@pytest.fixture
def env():
    g = Graph()
    inv = g.author("curator").investigation("Parser", "How reliable is the parser?")["id"]
    lab = g.author("lab")
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Ran the parser test campaign.")
    r = lab.add("result", inv, kind="computed", outcome="positive", summary="Parser test campaign.",
                values={k: {"k": a, "n": b} for k, (a, b, _w, _s) in CASES.items()},
                links=[{"rel": "produced", "from": run["id"]}])["id"]
    return g, inv, r


def write(g, inv, r, key, statement):
    k, n, what, _ = CASES[key]
    return g.author("writer").add("claim", inv, statement=statement, scope=SCOPE,
                                  measurements=[{"name": what, "result": r, "key": key, "k": k, "n": n}],
                                  links=[{"rel": "supports", "from": r, "why": "The campaign's count."}])


@pytest.mark.parametrize("key", list(CASES))
def test_the_suggested_honest_version_is_accepted(env, key):
    g, inv, r = env
    with pytest.raises(GraphError) as e:
        write(g, inv, r, key, CASES[key][3])
    fix = next(p["fix"] for p in e.value.problems if p["code"] == "ABSOLUTE_UNDERPOWERED")
    assert "upper bound" in fix
    write(g, inv, r, key, fix[0].upper() + fix[1:] + ".")


@pytest.mark.parametrize("key,statement", [
    ("crashed", "No crashes in 8 test suites; the crash rate is at most 31%."),
    ("read_14", "All 14 text encodings were read correctly: failures happen at most 19% of the time at 95% confidence."),
    ("read_12", "12 of 12 text encodings read correctly (failures: upper 95% confidence bound 22%)."),
    ("crashed", "No crashes in 8 test suites (95% upper bound 31.2%)."),
    ("read_14", "No failures in 14 encodings (95% upper bound 19.3%).")])
def test_a_bound_written_the_way_bound_prints_it_is_accepted(env, key, statement):
    g, inv, r = env
    write(g, inv, r, key, statement)


@pytest.mark.parametrize("key,statement", [
    ("crashed", "The parser crashed in 31% of the test suites."),             # unlabelled: no borrowing
    ("crashed", "No crashes in 8 test suites (95% upper bound 25%)."),        # labelled, but not the bound
    ("read_14", "All 14 encodings read; failures happen at most 5% of the time."),
    ("crashed", "Throughput rose 31% over the 8 test suites (upper bound 31%).")])
def test_a_figure_that_is_not_the_bound_is_still_unbound(env, key, statement):
    g, inv, r = env
    with pytest.raises(GraphError) as e:
        write(g, inv, r, key, statement)
    assert "UNBOUND_NUMBER" in [p["code"] for p in e.value.problems]


def test_a_bound_needs_a_count_behind_it(env):
    g, inv, r = env
    with pytest.raises(GraphError) as e:
        g.author("writer").add("claim", inv, statement="Crashes happen at most 31% of the time.", scope=SCOPE,
                               links=[{"rel": "supports", "from": r, "why": "The campaign."}])
    assert "UNBOUND_NUMBER" in [p["code"] for p in e.value.problems]


def test_a_write_up_may_quote_the_bound_as_printed(env):
    g, inv, r = env
    write(g, inv, r, "crashed", "No occurrences in 8 trials (95% upper bound 31%).")
    text = "# Parser\n\nThe parser had no crashes in 8 test suites (95% upper bound 31%).\n"
    issues = g.check_text(text, inv)
    flagged = [i for i in issues.get("findings", []) if i.get("code") == "REPORT_UNSOURCED_NUMBER"]
    assert not flagged, flagged
    issues = g.check_text("# Parser\n\nThe parser had no crashes in 8 test suites (95% upper bound 25%).\n", inv)
    assert [i for i in issues.get("findings", []) if i.get("code") == "REPORT_UNSOURCED_NUMBER"]

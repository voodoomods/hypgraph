"""The fixes the harmony pilots asked for: honest negations pass, the record binds the numbers it already holds,
every write tells the author whether its order is done, and a result written twice is written once."""
import pytest

from datetime import datetime, timedelta

from hypgraph import Graph, GraphError, Policy, language as L

SCOPE = "1,000 paired held-out items, one seed."


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 1, 9, 0, 0)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t.isoformat(timespec="seconds")


@pytest.fixture
def env():
    g = Graph(policy=Policy(reviewers={"critic"}), clock=Clock())
    me = g.author("analyst")
    inv = me.investigation("Does A beat B", "Find out whether A beats B on the paired held-out items.")["id"]
    r = me.add("result", inv, summary="A 812 of 1000 and B 800 of 1000 on the same items; C 900 of 1000.",
               values={"a": {"k": 812, "n": 1000}, "b": {"k": 800, "n": 1000}, "c": {"k": 900, "n": 1000},
                       "mean_a": {"value": 6.707, "unit": "mg/L"}})["id"]
    return g, me, inv, r


def M(r, name, key, **kw):
    return {"name": name, "result": r, "key": key, **kw}


def codes(e) -> list[str]:
    return [p["code"] for p in e.value.problems]


# ── 1. negation ──────────────────────────────────────────────────

def test_asserted_reads_the_clause():
    assert L.asserted(L.SIGNIFICANCE, "A is not significantly better than B.") == []
    assert L.asserted(L.SIGNIFICANCE, "A is significantly better than B.") == ["significantly"]
    assert L.asserted(L.SIGNIFICANCE, "There is no significant difference.") == []
    assert L.asserted(L.SIGNIFICANCE, "B is worse, but A is significantly better than C.") == ["significantly"]
    assert L.asserted(L.ABSOLUTE, "There is no evidence that it never fails.") == []
    assert L.asserted(L.ABSOLUTE, "We cannot conclude that it never fails.") == []
    assert L.asserted(L.ABSOLUTE, "The model cannot be jailbroken.") == ["cannot"]
    assert L.asserted(L.CAUSAL, "The feature does not cause conversions.") == []
    assert L.asserted(L.EXCLUSION, "The prompt format has no effect.") == ["no effect"]
    assert L.denied(L.SIGNIFICANCE, "The gap is not statistically significant.") == ["statistically", "significant"]


def test_honest_negation_is_accepted_and_the_overclaim_still_refused(env):
    g, me, inv, r = env
    ab = [M(r, "A", "a", k=812, n=1000), M(r, "B", "b", k=800, n=1000)]
    ok = me.add("claim", inv, statement="A is not significantly more accurate than B (812 of 1000 vs 800 of 1000).",
                scope=SCOPE, measurements=ab, links=[{"rel": "derived_from", "to": r}])
    assert ok["type"] == "claim" and "p = 0.5" in ok["state"]["sentence"]
    with pytest.raises(GraphError) as e:
        me.add("claim", inv, statement="A is significantly more accurate than B (812 of 1000 vs 800 of 1000).",
               scope=SCOPE, measurements=ab, links=[{"rel": "derived_from", "to": r}])
    assert codes(e) == ["SIGNIFICANCE_NOT_SHOWN"]
    me.add("claim", inv, statement="We cannot conclude that A beats B from 812 of 1000 against 800 of 1000.",
           scope=SCOPE, measurements=ab, links=[{"rel": "derived_from", "to": r}])


def test_denying_a_real_difference_is_refused_too(env):
    g, me, inv, r = env
    cb = [M(r, "C", "c", k=900, n=1000), M(r, "B", "b", k=800, n=1000)]
    with pytest.raises(GraphError) as e:
        me.add("claim", inv, statement="C is not significantly better than B (900 of 1000 vs 800 of 1000).",
               scope=SCOPE, measurements=cb, links=[{"rel": "derived_from", "to": r}])
    assert codes(e) == ["SIGNIFICANCE_CONTRADICTED"] and "p = " in e.value.problems[0]["message"]


# ── 2. auto-binding ──────────────────────────────────────────────

def test_the_record_binds_numbers_it_already_holds(env):
    g, me, inv, r = env
    n = me.add("claim", inv, statement="A is right on 812 of 1000 items (81.2%), a mean of 6.707 mg/L at A.",
               scope=SCOPE)                                    # no measurements, no links: the record finds them
    assert n["auto_bound"] == ["812 → RS1.a", "6.707 → RS1.mean_a"]       # 1000 is the n of the same count
    meas = n["body"]["measurements"]
    assert {m["key"] for m in meas} == {"a", "mean_a"} and meas[0]["k"] == 812
    assert any(e["rel"] == "supports" and e["src"] == r for e in n["in"])
    assert any("bound by the record" in x for x in n["notes"])
    assert "1 independent line of support" in n["state"]["sentence"]


def test_binding_prefers_linked_results_and_only_the_authors_own(env):
    g, me, inv, r = env
    other = g.author("engineer").add("result", inv, summary="An unrelated tally that happens to hold 812.",
                                     values={"x": {"value": 812}, "y": {"value": 7}})["id"]
    n = me.add("claim", inv, statement="A is right on 812 of 1000 items.", scope=SCOPE)
    assert all(m["result"] == r for m in n["body"]["measurements"])          # not the engineer's 812
    with pytest.raises(GraphError) as e:                                      # a number nobody has is still refused
        me.add("claim", inv, statement="A is right on 812 of 1000 items, a 20000-item margin.", scope=SCOPE)
    assert "UNBOUND_NUMBER" in codes(e) and e.value.problems[0]["words"] == ["20000"]
    assert other


def test_small_integers_bind_only_to_counts_or_a_named_value(env):
    g, me, inv, r = env
    me.add("result", inv, summary="Seven of nine probes leaked.", values={"leaks": {"k": 7, "n": 9}, "limit": {"value": 5}})
    with pytest.raises(GraphError) as e:                   # 5 is not bound to 'limit' when the sentence doesn't name it
        me.add("claim", inv, statement="7 of 9 probes leaked, 5 of them twice.", scope=SCOPE)
    assert e.value.problems[0]["words"] == ["5"]
    n = me.add("claim", inv, statement="7 of 9 probes leaked, against a limit of 5 mg/L.", scope=SCOPE)
    assert {m["key"] for m in n["body"]["measurements"]} == {"leaks", "limit"}   # 0.4.3: the sentence names the field


def test_revise_binds_too(env):
    g, me, inv, r = env
    n = me.add("claim", inv, statement="A was measured on the held-out items.", scope=SCOPE,
               links=[{"rel": "derived_from", "to": r}])
    v2 = me.revise(n["id"], "state the number", statement="A is right on 812 of 1000 held-out items.")
    assert v2["v"] == 2 and v2["auto_bound"] == ["812 → RS1.a"]


# ── 3. the done signal ───────────────────────────────────────────

def test_every_write_tells_the_author_whether_its_order_is_done(env):
    g, me, inv, r = env
    q = g.author("lead").add("question", inv, text="Q1: What is A's accuracy over all items?")["id"]
    g.issue_work(author="lead", inv=inv, target=q, assignee="analyst", objective="Answer Q1 from the record.")
    rs = me.add("result", inv, summary="A right on 812 of 1000, recomputed by item with seed 42.",
                values={"acc": {"k": 812, "n": 1000}, "seed": {"value": 42}})
    assert rs["orders"] == ["T1: claim_made NOT MET"]
    cl = me.add("claim", inv, statement="A is right on 812 of 1000 items.", scope=SCOPE,
                links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs["id"]}])
    assert cl["orders"] == ["T1: every predicate met (claim_made) — return_work now"]
    assert "orders" not in g.author("engineer").add("result", inv, summary="A tally by the engineer, nothing ordered.",
                                                    values={"z": {"value": 1}})


# ── 4. result deduplication ──────────────────────────────────────

def test_the_same_numbers_again_are_refused_unless_a_declared_rerun(env):
    g, me, inv, r = env
    with pytest.raises(GraphError) as e:
        me.add("result", inv, summary="The same tally again under new names.",
               values={"model_a": {"k": 812, "n": 1000}, "model_b": {"k": 800, "n": 1000},
                       "model_c": {"k": 900, "n": 1000}, "site_a_mean": {"value": 6.707}})
    assert codes(e) == ["RESULT_RESTATES"] and "RS1" in str(e.value)
    assert g.refusal_report(inv)["by_code"] == {"RESULT_RESTATES": 1}
    with pytest.raises(GraphError, match="RESULT_RESTATES"):                 # a subset of its numbers, too
        me.add("result", inv, summary="Just the A and B counts.", values={"a": {"k": 812, "n": 1000}, "b": {"k": 800, "n": 1000}})
    run0 = me.add("run", inv, kind="agent", name="eval", state="succeeded")["id"]
    run1 = me.add("run", inv, kind="agent", name="eval, new seed", state="succeeded",
                  links=[{"rel": "replicates", "to": run0, "data": {"differs": "new_seed"}}])["id"]
    again = me.add("result", inv, summary="The same numbers from a rerun with a new seed.",
                   values={"a": {"k": 812, "n": 1000}, "b": {"k": 800, "n": 1000}},
                   links=[{"rel": "produced", "from": run1}])
    assert again["restates"] == ["RS1"] and "RESTATES RS1" in again["state"]["sentence"]


def test_another_authors_restatement_is_kept_and_marked(env):
    g, me, inv, r = env
    crit = g.author("critic").add("result", inv, summary="Independently recomputed: 812 and 800 of 1000.",
                                  values={"acc_a": {"k": 812, "n": 1000}, "acc_b": {"k": 800, "n": 1000}})
    assert crit["restates"] == ["RS1"]
    tiny = me.add("result", inv, summary="A tiny count: 0 of 3.", values={"hits": {"k": 0, "n": 3}})
    me.add("result", inv, summary="Another tiny count: 0 of 3, different thing.", values={"misses": {"k": 0, "n": 3}})
    assert "restates" not in tiny["state"]                 # small integers alone never match

"""The refusal log (overclaims caught per author, fixed or open, on its own hash chain) and `hypgraph check` (a
write-up linted against the record) — including the false positives found calibrating on real write-ups."""
import json
import sqlite3
import threading
import urllib.request

import pytest

from hypgraph import Graph, GraphError, Policy
from hypgraph.cli import main
from hypgraph.demos import broad_street

SCOPE = "50 extraction prompts from the red-team set, temperature 0."


@pytest.fixture
def env(tmp_path):
    clock = broad_street.DemoClock("2026-10-24T09:00:00+00:00")
    g = Graph(tmp_path / "g.hypgraph", policy=Policy(reviewers={"critic"}), clock=clock)
    a = g.author("agent")
    inv = a.investigation("Ship?", "Find out whether the model leaks training data under red-team prompts.")["id"]
    r = a.add("result", inv, summary="Red-team run: 50 extraction prompts, no leaks.",
              values={"leaks": {"k": 0, "n": 50}, "ft": {"k": 1624, "n": 2000}, "bl": {"k": 1568, "n": 2000}})["id"]
    return g, a, inv, r, clock


def leak(r):
    return [{"name": "leaks", "result": r, "key": "leaks", "k": 0, "n": 50}]


def sup(r):
    return [{"rel": "supports", "from": r, "why": "the red-team run"}]


# ── the refusal log ───────────────────────────────────────────────

def test_refusals_are_logged_and_a_later_honest_claim_fixes_them(env):
    g, a, inv, r, clock = env
    with pytest.raises(GraphError):
        a.add("claim", inv, statement="The model never leaks training data.", scope=SCOPE, measurements=leak(r),
              links=sup(r), exposure=1_000_000, exposure_unit="users")
    with pytest.raises(GraphError):
        g.author("other").add("claim", inv, statement="Prompt format makes no difference.", scope=SCOPE, links=sup(r))
    log = g.refusals(inv=inv)
    assert [x["author"] for x in log] == ["other", "agent"]
    assert log[1]["codes"] == ["ABSOLUTE_UNDERPOWERED"] and "58,155" in log[1]["problems"][0]["message"]
    assert all(x["fixed_by"] is None for x in log)
    clock.set("2026-10-24", "09:05:00")
    ok = a.add("claim", inv, statement="The model leaked no training data in 50 extraction prompts.", scope=SCOPE,
               measurements=leak(r), links=sup(r))
    assert ok["fixes_refusals"] == [log[1]["id"]]
    rep = g.refusal_report(inv=inv)
    assert rep["refused"] == 2 and rep["fixed"] == 1
    assert rep["by_author"]["agent"] == {"refused": 1, "fixed": 1, "open": 0, "codes": {"ABSOLUTE_UNDERPOWERED": 1}}
    assert rep["by_author"]["other"]["open"] == 1 and rep["by_code"]["EXCLUSION_WITHOUT_POWER"] == 1
    assert "2 refused, 1 came back honest" in rep["markdown"]


def test_an_unrelated_claim_does_not_count_as_a_fix_and_old_refusals_expire(env):
    g, a, inv, r, clock = env
    with pytest.raises(GraphError):
        a.add("claim", inv, statement="The model never leaks training data.", scope=SCOPE, measurements=leak(r),
              links=sup(r))
    a.add("claim", inv, statement="The fine-tune got 1,624 of 2,000 held-out items right.",
          scope="2,000 held-out items, one seed.", links=sup(r),
          measurements=[{"name": "ft", "result": r, "key": "ft", "k": 1624, "n": 2000}])
    assert g.refusals(inv=inv)[0]["fixed_by"] is None
    clock.set("2026-10-26")                                   # past the 24-hour window
    a.add("claim", inv, statement="The model leaked no training data in 50 extraction prompts.", scope=SCOPE,
          measurements=leak(r), links=sup(r))
    assert g.refusals(inv=inv)[0]["fixed_by"] is None


def test_a_refused_revision_is_logged_and_fixed_by_the_accepted_one(env):
    g, a, inv, r, clock = env
    c = a.add("claim", inv, statement="The model leaked no training data in 50 extraction prompts.", scope=SCOPE,
              measurements=leak(r), links=sup(r))["id"]
    with pytest.raises(GraphError):
        a.revise(c, "make it punchier for the launch note", statement="The model never leaks training data.")
    assert g.refusals(inv=inv)[0]["node"] == c
    out = a.revise(c, "say the denominator, as the record asked",
                   statement="The model leaked nothing in 50 of 50 prompts.")
    assert out["fixes_refusals"]


def test_the_refusal_log_has_its_own_chain_and_leaves_the_record_alone(env):
    g, a, inv, r, _ = env
    before = g.verify()
    with pytest.raises(GraphError):
        a.add("claim", inv, statement="The model eliminates leaks entirely.", scope=SCOPE, links=sup(r))
    assert g.verify() == before                               # the record's chain didn't move
    assert g.verify_refusals()["ok"] and g.verify_refusals()["checked"] == 1
    con = sqlite3.connect(g.path)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("DELETE FROM refusal_log")
    con.execute("DROP TRIGGER refusal_log_no_update")
    con.execute("UPDATE refusal_log SET statement='nothing to see here'")
    con.commit()
    con.close()
    assert not g.verify_refusals()["ok"]


# ── hypgraph check ────────────────────────────────────────────────

@pytest.fixture(scope="module")
def demo():
    return broad_street.build()


def codes(r):
    return sorted({f["code"] for f in r["findings"] if f["level"] == "error"})


def test_an_honest_summary_passes(demo):
    g, inv, _ = demo
    text = """# Broad Street, 1854
Houses supplied by Southwark and Vauxhall died at 315 per 10,000 houses against 37 for Lambeth (CL2), 8.5 times the
rate; the difference is 278 per 10,000. Of the 535 workhouse inmates, 5 died (CL1), and CL1 is checked on v2.
CL2 is unchecked: no reviewer has looked at it yet. H2 is challenged by RS5.
"""
    r = g.check_text(text, inv)
    assert r["ok"] and r["errors"] == 0, r["markdown"]


def test_each_overclaim_in_a_summary_is_caught(demo):
    g, inv, _ = demo
    text = """CL2 is now established beyond doubt.
The pump caused roughly 700 deaths across London.
The workhouse well never spread cholera.
Water source had no effect on the Hampstead case.
Southwark and Vauxhall houses died at a significantly higher rate.
As CL9 shows, the miasma theory is dead.
"""
    r = g.check_text(text, inv)
    assert codes(r) == ["REPORT_ABSENCE_UNBACKED", "REPORT_ABSOLUTE_UNBACKED", "REPORT_OVERSTATES_STANDING",
                        "REPORT_SIGNIFICANCE_UNBACKED", "REPORT_UNKNOWN_CODE"]
    assert any(f["code"] == "REPORT_UNSOURCED_NUMBER" and "700" in f["message"] for f in r["findings"])
    assert [f["line"] for f in r["findings"] if f["code"] == "REPORT_UNKNOWN_CODE"] == [6]


def test_what_isnt_the_writers_claim_is_left_alone(demo):
    g, inv, _ = demo
    text = """Run `hypgraph show CL2` or see https://example.org/CL9 — never mind.
```
seed = 99999   # CL7 never
```
H1 cannot be proven with the counts we have.
The draft said "CL2 is established", which the reviewer struck.
Use the development set, never the evaluation set.
In 1854, three investigators met on 2026-10-24 at 10:00.
"""
    r = g.check_text(text, inv)
    assert r["errors"] == 0, r["markdown"]


def test_citing_a_withdrawn_claim(tmp_path):
    g = Graph(policy=Policy(reviewers={"critic"}))
    a = g.author("agent")
    inv = a.investigation("Withdrawal test", "Find out something worth finding out here.")["id"]
    r = a.add("result", inv, summary="A measured outcome.", values={"x": {"k": 3, "n": 10}})["id"]
    c = a.add("claim", inv, statement="It happened in 3 of 10 trials.", scope="Ten trials of the setup.",
              measurements=[{"name": "x", "result": r, "key": "x", "k": 3, "n": 10}],
              links=[{"rel": "supports", "from": r, "why": "the result"}])
    a.withdraw(c["id"], "the trials used the wrong configuration")
    assert codes(g.check_text("As CL1 found, it happens in 3 of 10 trials.", inv)) == ["REPORT_CITES_WITHDRAWN"]
    assert g.check_text("CL1 (withdrawn) had said 3 of 10.", inv)["errors"] == 0


def test_cli_check_and_refusals(tmp_path, capsys, demo):
    g, inv, _ = demo
    db = str(tmp_path / "d.hypgraph")
    assert main(["--db", db, "demo"]) == 0
    good, bad = tmp_path / "good.md", tmp_path / "bad.md"
    good.write_text("Southwark and Vauxhall: 315 per 10,000 houses, Lambeth 37 (CL2).\n", encoding="utf-8")
    bad.write_text("CL2 is established.\nThe pump caused 700 deaths.\n", encoding="utf-8")
    capsys.readouterr()
    assert main(["--db", db, "check", str(good)]) == 0
    assert main(["--db", db, "check", str(bad)]) == 1
    out = capsys.readouterr().out
    assert "bad.md:1: error REPORT_OVERSTATES_STANDING" in out and "bad.md:2: warning REPORT_UNSOURCED_NUMBER" in out
    bad.write_text("The pump caused 700 deaths (CL2).\n", encoding="utf-8")
    assert main(["--db", db, "check", str(bad)]) == 0                 # a warning alone passes …
    assert main(["--db", db, "check", "--strict", str(bad)]) == 1     # … unless --strict
    assert main(["--db", db, "refusals"]) == 0
    assert "came back honest" in capsys.readouterr().out             # the demo's three refusals by 'you'


def test_http_routes(tmp_path):
    from hypgraph.server import make_server
    db = tmp_path / "s.hypgraph"
    broad_street.build(path=str(db))
    srv = make_server(str(db), port=0)                                # read-only: check is still allowed
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/api/graph"
    try:
        rep = json.loads(urllib.request.urlopen(base + "/refusals").read())
        assert rep["refused"] == 3 and set(rep["by_author"]) == {"you"}
        req = urllib.request.Request(base + "/check", data=json.dumps({"text": "CL2 is established."}).encode(),
                                     method="POST", headers={"Content-Type": "application/json"})
        res = json.loads(urllib.request.urlopen(req).read())
        assert res["errors"] == 1 and res["findings"][0]["code"] == "REPORT_OVERSTATES_STANDING"
    finally:
        srv.shutdown()
        srv.server_close()


def test_a_negated_exclusion_is_not_an_absence_claim(tmp_path):
    """'Not ruled out' hedges; it doesn't say an effect is absent — the bound note says it in those words itself."""
    g = Graph(tmp_path / "r.hypgraph")
    inv = g.author("lead").investigation("Does the cache leak?", "Look for leaks in the cache under load.")["id"]
    hedge = g.check_text("Up to 58,155 failures in 1,000,000 uses are not ruled out.\n\nA leak cannot be ruled out.\n", inv)
    assert "REPORT_ABSENCE_UNBACKED" not in {f["code"] for f in hedge["findings"]}
    claim = g.check_text("The cache rules out leaks.\n", inv)
    assert "REPORT_ABSENCE_UNBACKED" in {f["code"] for f in claim["findings"]}
    g.close()

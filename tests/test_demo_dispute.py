"""The disputed-answer demo (hypgraph.demos.dispute): an honest mistake and a lie, told apart by the record alone.

The README and the website show its Evidence view (one claim checked, the other contested) and its conduct log. These
tests hold the demo to what those pages say: the refusals come from the record's own checks, the honest party ends
cleared and the liar ends named, and the whole record verifies."""
import json

from hypgraph import cli
from hypgraph.demos import DEMOS, dispute


def test_the_routes_are_what_the_story_says():
    assert [d for _p, d in dispute.routes()] == [29, 30, 45, 62]


def test_each_refusal_is_the_records_own_check():
    _g, _inv, story = dispute.build()
    refused = [(s["actor"], s["refused"]) for s in story if "refused" in s]
    assert [a for a, _ in refused] == ["ada", "mallory", "mallory"]
    assert "[COUNT_CONTRADICTS]" in refused[0][1] and "1 of 4" in refused[0][1]
    assert all("[SOURCE_CONTRADICTS]" in r and "kilometres" in r for _a, r in refused[1:])


def test_the_reviewer_checks_one_answer_and_the_other_is_contested():
    g, _inv, story = dispute.build()
    codes = {s["code"]: s["node"] for s in story if s.get("code", "").startswith("CL")}
    assert set(codes) == {"CL1", "CL2"}
    assert g.get(codes["CL1"])["state"]["review"]["state"] == "checked"
    assert g.get(codes["CL2"])["state"]["review"]["state"] == "contested"


def test_the_conduct_log_clears_the_honest_party_and_names_the_liar():
    g, inv, _ = dispute.build()
    c = g.conduct(inv)
    assert c["ada"]["corrected"] == 1 and c["ada"]["reasserted"] == 0
    assert not c["ada"]["still_saying"] and not c["ada"]["ends_false"]
    assert c["mallory"]["by_source"] == 1 and c["mallory"]["reasserted"] == 2 and c["mallory"]["corrected"] == 0
    assert c["mallory"]["still_saying"] and c["mallory"]["ends_false"]


def test_the_record_verifies(tmp_path):
    g, _inv, _ = dispute.build(path=str(tmp_path / "d.hypgraph"))
    assert g.verify()["ok"]


def test_hypgraph_demo_dispute(tmp_path, capsys):
    assert "dispute" in DEMOS
    db = tmp_path / "d.hypgraph"
    assert cli.main(["--db", str(db), "demo", "dispute", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["conduct"]["mallory"]["ends_false"] and not out["conduct"]["ada"]["ends_false"]
    assert sum("refused" in s for s in out["story"]) == 3

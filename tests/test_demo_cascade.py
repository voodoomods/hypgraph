"""The withdrawn-benchmark demo (hypgraph.demos.cascade): what rested on a withdrawn source is found on read."""
from hypgraph.demos import cascade


def states(g, inv):
    return {n["code"]: n["state"] for n in g.subgraph(inv)["nodes"]}


def test_the_withdrawal_puts_everything_computed_from_it_at_risk_and_nothing_else():
    g, inv, _ = cascade.build(until="withdrawn")
    st = states(g, inv)
    assert st["S1"]["lifecycle"] == "withdrawn"
    for code in ("RS1", "RS2", "CL1", "CL2", "D1"):
        assert st[code].get("at_risk"), code
    for code in ("RS3", "CL3"):                    # the team's own load test rests on nothing the vendor published
        assert not st[code].get("at_risk"), code
    assert st["CL3"]["review"]["state"] == "checked"


def test_re_measured_the_claims_clear_and_the_old_decision_is_flagged_and_superseded():
    g, inv, story = cascade.build()
    st = states(g, inv)
    for code in ("CL1", "CL2", "D2"):
        assert not st[code].get("at_risk"), code
    assert st["D1"]["lifecycle"] == "superseded"
    assert {b["code"] for b in st["D1"]["basis_changed"]} == {"CL1", "CL2"}
    assert st["D2"]["lifecycle"] == "active" and not st["D2"].get("basis_changed")
    assert g.verify_chain()["ok"]
    assert [s["actor"] for s in story][-1] == "lead"


def test_the_cli_builds_it_and_its_hint_for_an_existing_file_is_a_command_that_runs(tmp_path, capsys):
    from hypgraph import cli
    db = tmp_path / "cascade.hypgraph"
    assert cli.main(["--db", str(db), "demo", "cascade"]) == 0
    assert "AT RISK" in capsys.readouterr().out
    assert cli.main(["--db", str(db), "demo", "cascade"]) != 0          # the file exists now
    hint = capsys.readouterr()
    hint = (hint.out + hint.err).split("choose another file: ")[1].strip()
    assert hint == "hypgraph --db cascade-2.hypgraph demo cascade"
    args = hint.split()[1:]
    args[1] = str(tmp_path / args[1])
    assert cli.main(args) == 0                                           # --db comes before the command

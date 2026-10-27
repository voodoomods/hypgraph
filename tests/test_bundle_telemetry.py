"""A bundle can carry a swarm's telemetry sidecar (`export(..., telemetry=)`, `hypgraph export --telemetry`), so a page
with no server can replay the run — the site's live examples do. Telemetry is observation: outside the hash chain,
ignored by verification and by `from_bundle`, and off unless asked for."""
import json
import subprocess
import sys

from hypgraph import Graph
from hypgraph.bundle import read_sidecar, verify_bundle

from .test_telemetry_stream import _line


def _record(tmp_path):
    g = Graph(tmp_path / "r.hypgraph")
    a = g.author("ada").investigation("A beats B?", "Test whether variant A beats variant B on the eval set.")["id"]
    b = g.author("ada").investigation("Another study", "A second investigation in the same record, to scope against.")["id"]
    side = tmp_path / "r.hypgraph.telemetry.jsonl"
    side.write_text(_line(a, "run_start", span="s0") + _line(a, "model_end", span="s1", usd=0.001) + "not json\n"
                    + _line(b, "model_end", span="s2") + _line("", "decision", event="noted") + '{"kind": "tool_',
                    encoding="utf-8")
    return g, a, b, side


def test_a_bundle_carries_the_sidecar_outside_its_chain(tmp_path):
    g, a, b, side = _record(tmp_path)
    plain = g.export(a)
    assert "telemetry" not in plain                                        # off unless asked for
    bundle = g.export(a, telemetry=side)
    t = bundle["telemetry"]
    assert t["source"] == side.name and t["covered_by_chain"] is False
    assert [e["kind"] for e in t["events"]] == ["run_start", "model_end", "decision"]   # this investigation's, + unscoped
    assert verify_bundle(bundle) == verify_bundle(plain) and verify_bundle(bundle)["ok"]
    assert {e["inv"] for e in g.export(telemetry=side)["telemetry"]["events"]} == {a, b, ""}   # the whole graph: all
    assert [e["kind"] for e in g.export(b, telemetry=[{"inv": b, "kind": "x"}, {"inv": a, "kind": "y"}, "junk"])
            ["telemetry"]["events"]] == ["x"]                              # events handed over directly
    whole = g.export(telemetry=side)
    copy = Graph.from_bundle(json.loads(json.dumps(whole)))                # telemetry never enters a rebuilt record
    assert copy.verify()["ok"] and copy.export()["head"] == whole["head"] and "telemetry" not in copy.export()
    g.close()


def test_read_sidecar_skips_torn_and_foreign_lines(tmp_path):
    _g, a, _b, side = _record(tmp_path)
    _g.close()
    assert len(read_sidecar(side)) == 4                                    # "not json" and the torn tail skipped
    assert [e["kind"] for e in read_sidecar(side, {a})] == ["run_start", "model_end", "decision"]


def test_the_cli_exports_with_telemetry_only_when_asked(tmp_path):
    g, a, _b, side = _record(tmp_path)
    db = g.path
    g.close()
    run = lambda *x: subprocess.run([sys.executable, "-m", "hypgraph", "--db", db, "export", "--inv", a, *x],  # noqa: E731
                                    capture_output=True, text=True, encoding="utf-8")
    out = tmp_path / "b.json"
    r = run("-o", str(out), "--telemetry")                                 # default: <db>.telemetry.jsonl
    assert r.returncode == 0 and "3 telemetry events" in r.stdout
    assert len(json.loads(out.read_text(encoding="utf-8"))["telemetry"]["events"]) == 3
    assert run("-o", str(out)).returncode == 0 and "telemetry" not in json.loads(out.read_text(encoding="utf-8"))
    r = run("-o", str(out), "--telemetry", str(tmp_path / "missing.jsonl"))
    assert r.returncode == 2 and "no telemetry at" in r.stderr

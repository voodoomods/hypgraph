"""`hypgraph serve` serves a swarm's telemetry sidecar (<db>.telemetry.jsonl, written by hypswarm) and tails it into the
live stream beside the record's events, so the UI's Live view shows model and tool calls as they happen. Telemetry is
observation: it is shown, never trusted for standing."""
import json
import threading
import time
import urllib.request

import pytest

from hypgraph import Graph
from hypgraph.server import make_server, read_telemetry

from .test_ui_engine import _inv, _parse, _read_stream


def _line(inv, kind, **f):
    return json.dumps({"v": 1, "ts": time.time(), "inv": inv, "kind": kind, **f}) + "\n"


def test_reading_the_sidecar_takes_complete_lines_only(tmp_path):
    p = tmp_path / "r.hypgraph.telemetry.jsonl"
    assert read_telemetry(p, 0) == ([], 0)                                     # not there yet
    p.write_text(_line("inv-a", "model_start", span="s1") + "not json\n" + _line("inv-b", "tool_start") + '{"kind": "mo',
                 encoding="utf-8")
    evs, nxt = read_telemetry(p, 0)
    assert [e["kind"] for e in evs] == ["model_start", "tool_start"]           # the bad line is skipped
    assert nxt == p.read_bytes().rfind(b"\n") + 1                              # the half-written line waits
    assert [e["inv"] for e in read_telemetry(p, 0, inv="inv-a")[0]] == ["inv-a"]
    with p.open("a", encoding="utf-8") as f:
        f.write('del_end"}\n')                                                 # the writer finishes the line
    more, nxt2 = read_telemetry(p, nxt)
    assert [e["kind"] for e in more] == ["model_end"] and nxt2 == p.stat().st_size
    p.write_text(_line("inv-a", "run_start"), encoding="utf-8")                # rotated: shorter than our offset
    assert [e["kind"] for e in read_telemetry(p, nxt2)[0]] == ["run_start"]
    p.write_text("".join(_line("inv-a", "tool_end", i=i) for i in range(5)), encoding="utf-8")
    first, off = read_telemetry(p, 0, limit=2)
    assert [e["i"] for e in first] == [0, 1] and [e["i"] for e in read_telemetry(p, off)[0]] == [2, 3, 4]


@pytest.fixture
def served(tmp_path):
    db = tmp_path / "live.hypgraph"
    g = Graph(str(db))
    inv = _inv(g)
    srv = make_server(g, port=0)                                               # telemetry="auto": <db>.telemetry.jsonl
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield db, inv, f"http://127.0.0.1:{srv.server_address[1]}/api/graph", tmp_path / "live.hypgraph.telemetry.jsonl"
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_telemetry_route_pages_by_offset(served):
    _db, inv, base, side = served
    get = lambda q: json.loads(urllib.request.urlopen(f"{base}/telemetry?{q}").read())   # noqa: E731
    out = get(f"inv={inv}")
    assert out == {"events": [], "next": 0, "source": side.name, "exists": False}
    side.write_text(_line(inv, "run_start") + _line("inv-other", "run_start") + _line(inv, "model_start"), encoding="utf-8")
    out = get(f"inv={inv}")
    assert [e["kind"] for e in out["events"]] == ["run_start", "model_start"] and out["exists"]
    assert get(f"inv={inv}&after={out['next']}")["events"] == []


def test_the_stream_carries_telemetry_written_while_it_is_open(served):
    db, inv, base, side = served
    side.write_text(_line(inv, "run_start", span="s-run"), encoding="utf-8")   # a run already under way

    def swarm():
        time.sleep(0.5)
        with side.open("a", encoding="utf-8") as f:
            f.write(_line(inv, "model_start", span="s-m1", parent="s-run", seat="analyst", order="T1", model="m"))
        Graph(str(db)).create(author="analyst", type="hypothesis", inv=inv, fields={
            "statement": "Quoting the field with the csv module keeps the comma.",
            "predictions": "The importer returns three rows with the comma inside the field."})
        with side.open("a", encoding="utf-8") as f:
            f.write(_line(inv, "model_end", span="s-m1", parent="s-run", seat="analyst", order="T1", ok=True))

    t = threading.Thread(target=swarm)
    t.start()
    text = _read_stream(f"{base}/stream?inv={inv}&max_seconds=2&poll=0.1")
    t.join()
    blocks = [b for b in text.strip().split("\n\n") if "event: telemetry" in b or "event: record" in b]
    tel = [json.loads(b.split("data: ", 1)[1]) for b in blocks if "event: telemetry" in b]
    assert [e["kind"] for e in tel] == ["run_start", "model_start", "model_end"]
    assert any(e["actor"] == "analyst" for k, _i, e in _parse(text) if k == "record")      # the record's write too
    ids = [line[4:] for b in blocks for line in b.splitlines() if line.startswith("id: ")]
    assert all(":" in i for i in ids)                                          # seq:offset — both resume
    last = ids[-1]
    again = _read_stream(f"{base}/stream?inv={inv}&max_seconds=0.4&poll=0.1", {"Last-Event-ID": last})
    assert "event: telemetry" not in again and [k for k, _i, _e in _parse(again)] == ["end"]   # nothing repeated

"""What the HypGraph UI needs from the engine (docs/ui-plan.md, P1): each profile's labels, a bundle that carries the
workflow views so a viewer needs no engine, the profile as a UI speaks it, and the record's events pushed as they are
written — including writes from another process on the same file, which is how a running swarm is watched."""
import json
import threading
import time
import urllib.error
import urllib.request

import pytest

from hypgraph import Graph, profiles
from hypgraph.bundle import verify_bundle
from hypgraph.schema import TYPES
from hypgraph.server import dispatch, make_server

H = "harness"


def _inv(g, profile="software@2"):
    inv = g.create(author=H, type="investigation", fields={"title": "Importer keeps quoted commas",
                   "objective": "Verify the importer keeps a comma inside a quoted field.", "profile": profile})["id"]
    g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "Does the importer keep the comma?"})
    return inv


def test_each_v2_profile_speaks_its_own_words_and_v1_keeps_the_kernel_s():
    assert profiles.get("software@2").labels["question"] == "Requirement"
    assert profiles.get("trading@2").labels["hypothesis"] == "Thesis"
    assert profiles.get("optimization@2").labels["result"] == "Solution"
    for pid in ("scientific@2", "software@2", "trading@2", "knowledge@2", "optimization@2"):
        v = profiles.view(pid)
        assert set(v["labels"]) == set(TYPES) and all(v["labels"].values())      # every type has a word
        assert v["workflow"]["stages"] and v["workflow"]["report"]
    assert profiles.get("software@1").labels == {}                             # frozen: the kernel's words
    assert profiles.view("software@1")["labels"]["question"] == "Question"
    plain = profiles.view("")
    assert plain["id"] == "" and plain["labels"]["claim"] == "Claim" and plain["workflow"] is None
    assert profiles.describe()["knowledge@2"]["labels"]["claim"] == "Sourced claim"


def test_a_bundle_carries_the_workflow_views_and_still_verifies():
    g = Graph()
    inv = _inv(g)
    b = g.export(inv)
    v = b["derived"]["by_inv"][inv]
    assert v["profile"]["id"] == "software@2" and v["profile"]["labels"]["question"] == "Requirement"
    assert v["stages"][0]["code"] == "Q1" and v["stages"][0]["profile"] == "software@2"
    assert v["completion"]["profile"] == "software@2" and not v["completion"]["complete"]
    assert v["board"][0]["code"] == "Q1" and v["orders"] == []
    assert "report" in v and verify_bundle(b)["ok"]                            # derived views are never part of the chain


def test_the_profile_route_speaks_the_investigation_s_profile():
    g = Graph()
    inv = _inv(g, "trading@2")
    st, v = dispatch(g, "GET", "/profile", {"inv": inv})
    assert st == 200 and v["id"] == "trading@2" and v["labels"]["decision"] == "Position"
    assert v["workflow"]["report"] == "Desk note"
    assert dispatch(g, "GET", "/profile", {})[1]["labels"]["question"] == "Question"    # no inv: the kernel's words
    assert dispatch(g, "GET", "/profile", {"inv": "inv-nope"})[0] == 404


def _read_stream(url, headers=None, timeout=10):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        assert r.headers["Content-Type"].startswith("text/event-stream")
        return r.read().decode()


def _parse(text):
    out = []
    for block in text.strip().split("\n\n"):
        f = {}
        for line in block.splitlines():
            if ":" in line and not line.startswith(":"):
                k, v = line.split(":", 1)
                f[k] = v.strip()
        if f.get("event") in ("record", "end"):
            out.append((f["event"], f.get("id"), json.loads(f["data"])))
    return out


@pytest.fixture
def served(tmp_path):
    db = tmp_path / "live.hypgraph"
    g = Graph(str(db))
    inv = _inv(g)
    srv = make_server(g, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/api/graph"
    try:
        yield db, inv, base
    finally:
        srv.shutdown()
        srv.server_close()


def test_the_stream_pushes_writes_from_another_process_as_they_happen(served):
    db, inv, base = served
    other = Graph(str(db))                     # a second connection to the same file: the swarm, in another process

    def write_later():
        time.sleep(0.6)
        other.create(author="analyst", type="hypothesis", inv=inv, fields={
            "statement": "Quoting the field with the csv module keeps the comma.",
            "predictions": "The importer returns three rows with the comma inside the field."})

    t = threading.Thread(target=write_later)
    t.start()
    text = _read_stream(f"{base}/stream?inv={inv}&max_seconds=2&poll=0.1")
    t.join()
    evs = _parse(text)
    records = [e for kind, _id, e in evs if kind == "record"]
    assert [e["seq"] for e in records] == sorted(e["seq"] for e in records)    # in order
    assert records[0]["kind"] == "create" and records[0]["ref"] == inv          # from the start of the investigation
    assert any(e["kind"] == "create" and e["actor"] == "analyst" for e in records)   # the other writer's event arrived
    assert evs[-1][0] == "end" and evs[-1][2]["head"] == records[-1]["seq"]
    assert all(i == str(e["seq"]) for kind, i, e in evs if kind == "record")  # ids are seqs: resumable


def test_the_stream_resumes_from_last_event_id_and_refuses_bad_requests(served):
    db, inv, base = served
    first = [e for k, _i, e in _parse(_read_stream(f"{base}/stream?inv={inv}&max_seconds=0.3&poll=0.1")) if k == "record"]
    head = first[-1]["seq"]
    again = _parse(_read_stream(f"{base}/stream?inv={inv}&max_seconds=0.3&poll=0.1", {"Last-Event-ID": str(head)}))
    assert [k for k, _i, _e in again] == ["end"]                               # nothing new since that id
    with pytest.raises(urllib.error.HTTPError) as e:
        _read_stream(f"{base}/stream?inv=inv-nope&max_seconds=0.3")
    assert e.value.code == 404
    with pytest.raises(urllib.error.HTTPError) as e:
        _read_stream(f"{base}/stream?after=soon")
    assert e.value.code == 400

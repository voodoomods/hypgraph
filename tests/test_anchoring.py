"""What a verified chain shows, and what only a published head adds (pre-launch review, 2026-10-31).

A chain is consistent with itself: an edited row, a dropped or reordered event, a forged redaction all fail. But
whoever can write the record can rewrite it and recompute every hash, or cut it short, and the result verifies.
Holding the bundle against a head published elsewhere (``verify_bundle(b, head=...)``, ``hypgraph verify --head``)
rules both out."""
import copy
import hashlib
import json
import subprocess
import sys

import pytest

from hypgraph import anchored, verify_bundle
from hypgraph.demos import broad_street
from hypgraph.store import GENESIS


@pytest.fixture(scope="module")
def bundle():
    g, inv, _ = broad_street.build()
    return json.loads(json.dumps(g.export())), g


def sha(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def rechain(b: dict) -> dict:
    """What someone holding the record can do: recompute every event's prev and hash after an edit, and the head."""
    prev = GENESIS
    for ev in sorted(b["events"], key=lambda e: e["seq"]):
        body = json.loads(ev["body"])
        body["prev"] = prev
        ev["body"] = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ev["hash"] = prev = sha(ev["body"])
    b["head"] = prev
    return b


def rewrite_claim(b: dict) -> dict:
    """Change a claim's words and fix up its event so every row still matches: a rewrite, not a tamper."""
    b = copy.deepcopy(b)
    i = next(k for k, x in enumerate(b["versions"]) if "Golden Square outbreak was spread" in x["body"])
    v = b["versions"][i]
    v["body"] = v["body"].replace("5 of the 535", "none of the 535")
    for ev in b["events"]:
        body = json.loads(ev["body"])
        p = body.get("payload") or {}
        if body.get("kind") in ("create", "revise") and body.get("ref") == v["node"] and int(p.get("v", 1)) == v["v"]:
            p["body_sha"] = sha(v["body"])
            ev["body"] = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return rechain(b)


def test_internal_consistency_catches_edits(bundle):
    b, _ = bundle
    assert verify_bundle(b)["ok"]
    bad = copy.deepcopy(b)                                  # an event's body edited, its hash left
    bad["events"][5]["body"] = bad["events"][5]["body"].replace('"kind":', '"kind" :', 1)
    assert not verify_bundle(bad)["ok"]
    bad = copy.deepcopy(b)                                  # two events swapped
    bad["events"][3]["seq"], bad["events"][4]["seq"] = bad["events"][4]["seq"], bad["events"][3]["seq"]
    assert not verify_bundle(bad)["ok"]
    bad = copy.deepcopy(b)                                  # a node's code changed
    bad["nodes"][0]["code"] = "ZZ9"
    assert not verify_bundle(bad)["ok"]
    bad = copy.deepcopy(b)                                  # an event marked redacted to hide what it says
    k = next(i for i, e in enumerate(bad["events"]) if json.loads(e["body"])["kind"] == "create")
    bad["events"][k] = {"seq": bad["events"][k]["seq"], "redacted": True, "prev": json.loads(bad["events"][k]["body"])["prev"],
                        "hash": bad["events"][k]["hash"]}
    assert not verify_bundle(bad)["ok"]                     # the node it created now has no event
    bad = copy.deepcopy(b)                                  # the head swapped for another
    bad["head"] = "f" * 64
    assert not verify_bundle(bad)["ok"]


def test_a_rewritten_record_verifies_on_its_own_but_not_against_its_published_head(bundle):
    b, _ = bundle
    published = b["head"]
    forged = rewrite_claim(b)
    assert "none of the 535" in json.dumps(forged)
    assert verify_bundle(forged)["ok"]                      # internally consistent: the chain can't tell
    v = verify_bundle(forged, head=published)
    assert not v["ok"] and not v["anchored"] and "not the record that was published" in v["problem"]
    assert verify_bundle(b, head=published) | {} == verify_bundle(b) | {"anchored": True}


def test_a_record_cut_short_verifies_on_its_own_but_not_against_its_published_head(bundle):
    b, _ = bundle
    published = b["head"]
    cut = copy.deepcopy(b)
    cut["events"] = sorted(cut["events"], key=lambda e: e["seq"])[:-3]
    cut["head"] = cut["events"][-1]["hash"]
    dropped = {json.loads(e["body"])["ref"] for e in sorted(b["events"], key=lambda e: e["seq"])[-3:]}
    cut["nodes"] = [n for n in cut["nodes"] if n["id"] not in dropped]
    cut["versions"] = [v for v in cut["versions"] if v["node"] not in dropped]
    cut["edges"] = [e for e in cut["edges"] if e["src"] not in dropped and e["dst"] not in dropped]
    keep = {int(json.loads(e["body"])["payload"].get("edge", -1)) for e in cut["events"] if json.loads(e["body"])["kind"] == "link"}
    cut["edges"] = [e for e in cut["edges"] if e["id"] in keep]
    cut["withdrawals"] = []
    cut["retractions"] = []
    if verify_bundle(cut)["ok"]:                            # cut cleanly: consistent with itself
        assert not verify_bundle(cut, head=published)["ok"]
    assert not verify_bundle(cut, head=published)["ok"]


def test_the_anchor_takes_a_prefix_but_not_a_short_one(bundle):
    b, _ = bundle
    assert verify_bundle(b, head=b["head"][:16])["anchored"]
    assert not verify_bundle(b, head=b["head"][:8])["ok"]
    assert not verify_bundle(b, head="not-hex-at-all-really")["ok"]
    assert anchored({"ok": False, "problem": "x"}, b["head"]) == {"ok": False, "problem": "x"}


def test_the_cli_verifies_against_a_published_head_in_a_separate_process(bundle, tmp_path):
    """Another process, another directory, no graph file: only the bundle and the head someone published."""
    b, _ = bundle
    f = tmp_path / "study.bundle.json"
    f.write_text(json.dumps(b), encoding="utf-8")
    run = lambda *a: subprocess.run([sys.executable, "-m", "hypgraph", "verify", str(f), *a], cwd=tmp_path,
                                    capture_output=True, text=True, encoding="utf-8")
    ok = run("--head", b["head"])
    assert ok.returncode == 0 and b["head"] in ok.stdout and "matches the anchored head" in ok.stdout
    plain = run()
    assert plain.returncode == 0 and "--head" in plain.stdout
    f.write_text(json.dumps(rewrite_claim(b)), encoding="utf-8")
    assert run().returncode == 0                            # the rewrite is consistent with itself
    bad = run("--head", b["head"])
    assert bad.returncode == 1 and "not the record that was published" in bad.stdout

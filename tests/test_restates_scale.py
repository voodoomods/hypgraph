"""derive.restates at scale: which earlier results a result repeats, found through a per-snapshot index of the
investigation's results by the numbers they carry, instead of a pass over the whole graph for every result. The
answers must be exactly what the old pass gave (a reference copy of it is below), and deriving every result must
cost one signature per result, not one per pair."""
import random
import time

from hypgraph import Graph, Policy
from hypgraph import derive as D


def reference_restates(s, nid):
    """The pass this replaced, kept as the oracle — with its one change: a tie within a second goes by write order
    (graph position), no longer by id."""
    n = s.nodes[nid]
    sig = D.result_signature(n["body"])
    if not sig:
        return []
    pos = {i: k for k, i in enumerate(s.nodes)}
    out = []
    for i, m in s.nodes.items():
        if i == nid or m["type"] != "result" or m["inv"] != n["inv"] or i in s.withdrawn:
            continue
        if (m["created_at"], pos[i]) >= (n["created_at"], pos[nid]):
            continue
        other = D.result_signature(m["body"])
        if not other:
            continue
        pool = list(other)
        if all(D._take(pool, x) for x in sorted(sig)):
            out.append(i)
    return out


def synthetic(n_results: int, seed: int, invs: int = 3, pool: int = 30) -> D.Snap:
    """An in-memory snapshot of results whose numbers come from a small pool, so repeats and subsets are common;
    some withdrawn, some sharing a creation second, some with too few numbers to sign."""
    rng = random.Random(seed)
    s = D.Snap(0, Policy())
    for k in range(n_results):
        nid = f"n{k:06d}{rng.choice('abc')}"
        nums = [rng.randrange(pool) + rng.choice((0, 0.5)) for _ in range(rng.choice((1, 2, 2, 3, 4)))]
        values = {f"v{j}": ({"k": x, "n": 100 + x} if rng.random() < 0.3 else x) for j, x in enumerate(nums)}
        s.nodes[nid] = {"id": nid, "type": "result", "inv": f"inv{rng.randrange(invs)}", "code": "", "v": 1,
                        "created_at": f"2026-10-26T00:{k // 60 % 60:02d}:{k % 60 // 2:02d}Z",
                        "body": {"values": values}}
        if rng.random() < 0.05:
            s.withdrawn[nid] = {"why": "test"}
    s.nodes["q1"] = {"id": "q1", "type": "question", "inv": "inv0", "code": "Q1", "v": 1,
                     "created_at": "2026-10-26T00:00:00Z",
                     "body": {"text": "?"}}
    return s


def test_same_answers_as_the_pass_it_replaced():
    for seed in range(6):
        s = synthetic(400, seed)
        for nid, n in s.nodes.items():
            if n["type"] == "result":
                assert D.restates(s, nid) == reference_restates(s, nid), (seed, nid)


def test_deriving_every_result_signs_each_once(monkeypatch):
    s = synthetic(6000, seed=7, invs=2, pool=4000)
    calls = []
    real = D.result_signature
    monkeypatch.setattr(D, "result_signature", lambda body: calls.append(1) or real(body))
    t0 = time.perf_counter()
    for nid, n in s.nodes.items():
        if n["type"] == "result":
            D.restates(s, nid)
    took = time.perf_counter() - t0
    results = sum(1 for n in s.nodes.values() if n["type"] == "result")
    assert len(calls) <= results                      # one per result; the old pass made one per pair (~18M here)
    assert took < 5, took                             # generous: well under a second on a laptop


def test_the_record_still_refuses_and_derives_restatements(tmp_path):
    """Through the engine: a second author repeating a result is derived as restating it, the same author is
    refused at write time, and a revision or a withdrawal is seen by the next read."""
    g = Graph(tmp_path / "r.hypgraph", policy=Policy(max_creates_per_minute=10**6))
    inv = g.author("lead").investigation("Does A beat B?", "Compare A with B on the 821 held-out items.")["id"]
    a, b = g.author("ana"), g.author("ben")
    r1 = a.add("result", inv, summary="A right on 621 of 821.", values={"a": {"k": 621, "n": 821}})["id"]
    r2 = b.add("result", inv, summary="A right on 621 of 821, recounted.", values={"acc": {"k": 621, "n": 821}})["id"]
    s = g.snapshot()
    assert D.state(s, r2).get("restates") == [r1] and "restates" not in D.state(s, r1)   # in write order, even
    # within one second: r1's standing, derived while r2 was being written, stays right when carried forward
    try:
        a.add("result", inv, summary="A right on 621 of 821 again.", values={"x": {"k": 621, "n": 821}})
        raise AssertionError("the same author's repeat should be refused")
    except Exception as e:                            # noqa: BLE001 — GraphError, checked by its code
        assert "RESULT_RESTATES" in str(e)
    a.revise(r1, "The items were recounted and one more was right.", values={"a": {"k": 622, "n": 821}},
             summary="A right on 622 of 821.")
    s = g.snapshot()
    assert "restates" not in D.state(s, r1) and "restates" not in D.state(s, r2)    # the numbers differ now
    r3 = a.add("result", inv, summary="B right on 607 of 821.", values={"b": {"k": 607, "n": 821}})["id"]
    r4 = b.add("result", inv, summary="B right on 607 of 821, recounted.", values={"b2": {"k": 607, "n": 821}})["id"]
    assert D.state(g.snapshot(), r4).get("restates") == [r3]
    g.author("operator").withdraw(r3, "the count was from the wrong split")
    assert "restates" not in D.state(g.snapshot(), r4)             # a withdrawn result is no line of evidence
    g.close()

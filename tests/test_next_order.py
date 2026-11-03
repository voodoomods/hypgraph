"""The next-experiments view lists untested hypotheses in the record's order, not the hash order of a set.

``next_experiments`` built ``untested_hypotheses`` by iterating a set of live hypothesis ids. String hashing is salted
per process, so the order changed from run to run, and ``hypgraph verify --standing`` failed on any bundle with two or
more untested hypotheses exported in another process: the bundle carried one order, the re-derivation another.
Invariants: the list follows the order the hypotheses were added; re-deriving a bundle's standing under any hash seed
agrees with what it carries."""
import json
import os
import subprocess
import sys

from hypgraph import Graph

TITLES = [f"Candidate {c} explains the readings." for c in "ABCDEFGH"]


def record():
    g = Graph()
    inv = g.author("curator").investigation("Readings", "Which candidate explains the readings?")["id"]
    a = g.author("a")
    hs = [a.add("hypothesis", inv, statement=t, predictions=["it fits the held-out readings"])["id"] for t in TITLES]
    a.add("experiment", inv, aim="Compare candidates A and B on the held-out readings.",
          protocol="Fit both candidates to the same held-out readings.", success_criteria="A fit for each.",
          method="least squares",
          links=[{"rel": "tests", "to": hs[0], "data": {"expected": "A fits"}},
                 {"rel": "tests", "to": hs[1], "data": {"expected": "B fits"}}])
    return g, inv, hs


def test_untested_follow_the_record_order():
    g, inv, hs = record()
    got = [h["id"] for h in g.next_experiments(inv)["untested_hypotheses"]]
    assert got == hs[2:]


def test_standing_verifies_under_any_hash_seed(tmp_path):
    g, inv, _ = record()
    f = tmp_path / "b.json"
    f.write_text(json.dumps(g.export(inv)), encoding="utf-8")
    for seed in ("0", "1", "2", "3", "4", "5"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        r = subprocess.run([sys.executable, "-m", "hypgraph", "verify", "--standing", str(f)], cwd=tmp_path, env=env,
                           capture_output=True, text=True, encoding="utf-8")
        assert r.returncode == 0, (seed, r.stdout, r.stderr)

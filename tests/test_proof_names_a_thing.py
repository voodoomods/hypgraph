""""Proof" naming a thing is not a claim that something is proved.

On a proof with open obligations, every honest line a model wrote was refused: "12 of 14 proof obligations
discharged; 2 remain open" as drawing a proof from 12 of 14, and "2 of 14 proof obligations remaining" as
contradicting it (showcase Exp14, candidate P: 25 of 25). The lines marked "model" are sentences it wrote there,
labelled true blind."""
from __future__ import annotations

import pytest

from hypgraph import Graph
from hypgraph import language as L
from hypgraph.graph import GraphError

SCOPE = "The checker's report for the property: mutual exclusion in the lock service."


def filed(statement: str, values: dict, meas: list[dict]) -> list[str]:
    g = Graph(None)
    cur, lab = g.author("curator"), g.author("lab")
    inv = cur.investigation("Is the property proved?", "Report the verification status of the property.",
                            scope=SCOPE)["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Checker: the verification run.")
    res = lab.add("result", inv, kind="computed", outcome="negative", summary="The checker's report.", values=values,
                  links=[{"rel": "produced", "from": run["id"]}])["id"]
    try:
        g.author("verification-agent").add(
            "claim", inv, kind="finding", statement=statement, scope=SCOPE,
            measurements=[dict(m, result=res) for m in meas],
            links=[{"rel": "supports", "from": res, "why": "The checker's report."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]
    finally:
        g.close()


OPEN = ({"proved": False, "obligations_discharged": {"k": 12, "n": 14}},
        [{"key": "obligations_discharged", "name": "proof obligations discharged", "k": 12, "n": 14}])
BOUNDED = ({"proved": False, "bounded_check_up_to_processes": 3, "violations_found": 0},
           [{"key": "bounded_check_up_to_processes", "name": "largest number of processes checked", "value": 3}])


@pytest.mark.parametrize("line", [
    "Mutual exclusion in lock service: 12 of 14 proof obligations discharged, 2 remain open.",          # model
    "12 of 14 proof obligations discharged; 2 remain open; the property is not fully proved.",          # model
    "The property is not proved: 12 of 14 proof obligations discharged, 2 remain open.",                # model
    "The property remains unproven, with 12 of 14 proof obligations discharged and 2 still open.",      # model
    "The property remains unproven, with 2 of 14 proof obligations still open.",
    "The proof attempt discharged 12 of 14 obligations.",
    "The proof assistant checked 12 of 14 obligations; 2 are open.",
])
def test_a_count_of_proof_obligations_is_a_count(line):
    assert filed(line, *OPEN) == []


@pytest.mark.parametrize("line", [
    "Mutual exclusion verified for up to 3 processes, but unbounded proof not attempted – property remains "
    "unproven.",                                                                                        # model
    "Property not proven; exhaustive checking up to 3 processes found no violations, but unbounded proof was not "
    "attempted.",                                                                                       # model
    "Mutual exclusion verified for configurations up to 3 processes, but proof for unbounded process counts remains "
    "incomplete.",                                                                                      # model
    "No violations were found in any of the 3 configurations tested; proof for an unbounded number of processes was "
    "not attempted.",                                                                                   # model
])
def test_a_proof_said_missing_is_not_a_proof_claimed(line):
    assert filed(line, *BOUNDED) == []


@pytest.mark.parametrize("line", [
    "This is proof that the lock service is correct.",
    "The bounded check is proof of mutual exclusion.",
    "We have a proof of mutual exclusion.",
    "The proof is complete.",
    "The proof was attempted and is complete.",
])
def test_a_proof_claimed_is_still_read(line):
    assert "proof" in L.asserted(L.ABSOLUTE, line)
    assert filed(line, *BOUNDED) != []


def test_a_proof_drawn_from_a_count_with_exceptions_is_still_refused():
    assert filed("12 of 14 obligations discharged, which is proof the property holds.", *OPEN) == ["COUNT_CONTRADICTS"]


@pytest.mark.parametrize("text,said", [
    ("proof obligations", False), ("proof-of-concept build", False), ("a proof sketch", False),
    ("the proof is pending", False), ("a proof has not yet been found", False), ("proof positive", True),
    ("proof that it holds", True), ("the proof, which was not attempted elsewhere, holds", True),
])
def test_the_reading_of_the_word(text, said):
    assert ("proof" in L.asserted(L.ABSOLUTE, text)) is said

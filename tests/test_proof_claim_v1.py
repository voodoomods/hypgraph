"""proof_claim@1: "it's proved" is held to the checker's report.

With no profile, 31 of 39 false lines a model wrote on a checker's report that is not a proof went in (showcase
Exp14 candidate P and Exp16). The lines marked "model" are sentences it wrote there, labelled blind; the rest are
hand probes."""
from __future__ import annotations

import pytest

from hypgraph import Graph, profiles
from hypgraph import proof_claim
from hypgraph.graph import GraphError

POLICY = "proof_claim@1"
SCOPE = "The checker's report for the property: no lost update in the replicated counter."
PROVED = {"proved": True, "obligations_discharged": {"k": 14, "n": 14}}
OPEN = {"proved": False, "obligations_discharged": {"k": 12, "n": 14}}
BOUNDED = {"proved": False, "bounded_check_up_to_processes": 3, "violations_found": 0}
NONE = {"proved": False}


def filed(values: dict, statement: str, pin: str | dict | None = POLICY, by: str = "lab") -> list[str]:
    """File one status line against a checker's report; the refusal codes, or [] when it goes in."""
    g = Graph(None)
    cur, who = g.author("curator"), g.author(by)
    kw = {"claim_policies": [pin]} if pin == POLICY else dict(pin) if isinstance(pin, dict) else \
        {"profile": pin} if pin else {}
    inv = cur.investigation("Is the property proved?", "Report the verification status of the property.",
                            scope=SCOPE, **kw)["id"]
    run = who.add("run", inv, kind="lab" if by == "lab" else "external", state="succeeded", name="The checker's run.")
    res = who.add("result", inv, kind="computed", outcome="positive" if values.get("proved") else "negative",
                  summary="The checker's report.", values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = []
    if "obligations_discharged" in values:
        meas.append(dict(values["obligations_discharged"], key="obligations_discharged",
                         name="proof obligations discharged", result=res))
    if "bounded_check_up_to_processes" in values:
        meas.append({"key": "bounded_check_up_to_processes", "name": "largest number of processes checked",
                     "value": values["bounded_check_up_to_processes"], "result": res})
    try:
        g.author("verification-agent").add("claim", inv, kind="finding", statement=statement, scope=SCOPE,
                                           measurements=meas,
                                           links=[{"rel": "supports", "from": res, "why": "The checker's report."}])
        return []
    except GraphError as e:
        return [p["code"] for p in e.problems]
    finally:
        g.close()


def test_proof_claim1_is_a_claim_policy_and_not_a_profile():
    c = profiles.CLAIM_POLICIES[POLICY]
    assert c.validators == proof_claim.VALIDATORS and c.relaxes == proof_claim.RELAXES
    assert set(c.refuses) == {"PROVED_WITH_OPEN_OBLIGATIONS", "PROVED_ON_BOUNDED_CHECK", "BOUND_UNSAID",
                              "PROVED_WITHOUT_RESULT", "PROOF_WITHOUT_CHECKER"}
    assert POLICY not in profiles.PROFILES


@pytest.mark.parametrize("values,code", [(OPEN, "PROVED_WITH_OPEN_OBLIGATIONS"), (BOUNDED, "PROVED_ON_BOUNDED_CHECK"),
                                         (NONE, "PROVED_WITHOUT_RESULT")])
@pytest.mark.parametrize("line", [
    "The property 'no lost update in the replicated counter' has been proved.",                         # model
    "The property 'no lost update in the replicated counter' is proved.",                               # model
    "Property 'no lost update in the replicated counter' has been formally proved.",
    "No lost update in the replicated counter is guaranteed.",
])
def test_proved_is_refused_on_a_report_that_is_not_a_proof(values, code, line):
    assert filed(values, line) == [code]
    assert code not in filed(values, line, pin=None)


@pytest.mark.parametrize("line", [
    "The property 'no lost update in the replicated counter' has been proved.",                         # model
    "The property has been proven with all proof obligations discharged.",                              # model
    "The property has been proven.",                                                                    # model
    "All 14 proof obligations are discharged and the property is proved.",
])
def test_proved_goes_in_on_a_proof(line):
    assert filed(PROVED, line) == []


def test_the_checkers_verdict_vouches_for_the_proof_words():
    """The declared relaxation: without the policy the kernel refuses "proven" for want of a count named after it."""
    line = "The property has been proven."
    assert filed(PROVED, line, pin=None) != []
    assert filed(PROVED, line) == []
    assert "PROOF_WITHOUT_CHECKER" in filed(PROVED, line, by="verification-agent")


@pytest.mark.parametrize("line", [
    "The property is not yet proved; 12 of 14 proof obligations discharged, 2 remain open.",            # model
    "12 of 14 proof obligations discharged; 2 remain open; the property is not fully proved.",          # model
    "The property remains unproven, with 12 of 14 proof obligations discharged and 2 still open.",      # model
    "The property has been largely verified: 12 of 14 obligations were discharged, leaving 2 open.",    # model
    "The property is not proved.",
])
def test_honest_lines_on_open_obligations_go_in(line):
    assert filed(OPEN, line) == []


@pytest.mark.parametrize("line", [
    "Mutual exclusion verified for up to 3 processes, but unbounded proof not attempted – property remains "
    "unproven.",                                                                                        # model
    "The property is verified for all configurations up to 3 processes, but remains unproven for larger, unbounded "
    "system sizes.",                                                                                    # model
    "The property holds for all configurations up to 3 processes; no proof was attempted for unbounded "
    "processes.",                                                                                       # model
    "No violation was found for up to 3 processes; the property is not proved in general.",
])
def test_a_bounded_check_goes_in_with_its_bound(line):
    assert filed(BOUNDED, line) == []


@pytest.mark.parametrize("line", [
    "The property has been verified.",
    "The property holds.",
    "Verification succeeded.",
    "The property holds in general, as verified for up to 3 processes.",
])
def test_a_bounded_check_without_its_bound_or_said_of_every_case_is_refused(line):
    assert filed(BOUNDED, line) == ["BOUND_UNSAID"]


def test_all_configurations_up_to_the_bound_needs_no_count_under_the_policy():
    line = "The property is verified for all configurations up to 3 processes; it is not proved in general."
    assert "ABSOLUTE_WITHOUT_COUNT" in filed(BOUNDED, line, pin=None)
    assert filed(BOUNDED, line) == []


@pytest.mark.parametrize("line", [
    "The property could not be proven; the model checker stopped at the time limit before finishing.",  # model
    "The property was not proved; the checker gave no result.",
    "The model checker timed out before completing the proof.",                                         # model
])
def test_honest_lines_on_no_result_are_not_refused_by_the_policy(line):
    assert "PROVED_WITHOUT_RESULT" not in filed(NONE, line)


def test_a_negator_in_the_propertys_name_does_not_deny_the_proof():
    assert filed(NONE, "The property 'no lost update in the replicated counter' is proved.") == [
        "PROVED_WITHOUT_RESULT"]


def test_a_claim_that_rests_on_no_checker_report_is_not_read():
    for pin in ({"claim_policies": [POLICY]}, {"profile": "software@3", "claim_policies": [POLICY]}):
        g = Graph(None)
        cur, lab = g.author("curator"), g.author("lab")
        inv = cur.investigation("Does the parser accept the file?", "Report the run.",
                                scope="One run of the parser on the sample file.", **pin)["id"]
        run = lab.add("run", inv, kind="lab", state="succeeded", name="The run.")
        res = lab.add("result", inv, kind="computed", outcome="positive", summary="The run's output.",
                      values={"rows_parsed": 120}, links=[{"rel": "produced", "from": run["id"]}])["id"]
        n = g.author("dev-agent").add(
            "claim", inv, kind="finding", statement="The run verified that the parser reads 120 rows.",
            scope="One run of the parser on the sample file.",
            measurements=[{"key": "rows_parsed", "name": "rows parsed", "value": 120, "result": res}],
            links=[{"rel": "supports", "from": res, "why": "The run counted the rows it parsed."}])
        assert n["code"]
        g.close()


def test_the_report_is_read_from_its_keys():
    r = proof_claim.report
    assert r({"values": PROVED})["state"] == "proved"
    assert r({"values": OPEN}) == {"state": "open", "k": 12.0, "n": 14.0, "bound": None}
    assert r({"values": BOUNDED})["state"] == "bounded" and r({"values": BOUNDED})["bound"] == 3.0
    assert r({"values": NONE})["state"] == "none"
    assert r({"values": {"lemmas_proved": {"k": 7, "n": 7}}})["state"] == "proved"
    assert r({"values": {"rows_parsed": 120}}) is None

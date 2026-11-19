"""The examples in docs/claim-policies/corroboration.md are what the record answers.

Each line of the page's two example tables is filed against the register printed above its table, with the claim
policy pinned alone and beside `software@3`. The answer the page gives (accepted, or refused with
a code and the quoted message) has to be the engine's each way, and without the policy every line the page calls
refused has to go in."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hypgraph import Graph
from hypgraph.graph import GraphError

PAGE = (Path(__file__).resolve().parents[1] / "docs" / "claim-policies" / "corroboration.md").read_text(
    encoding="utf-8")
BLOCKS = re.findall(r"```json\n(.*?)```", PAGE, re.S)        # the pin, the citing register, the wire register
POLICY = ["corroboration@1"]
WAYS = [{"claim_policies": POLICY}, {"profile": "software@3", "claim_policies": POLICY}]
FACT = "the Ashby foundry has stopped production"
ONE_OF_2 = "is asserted, but the register it rests on counts 1 independent origin among 2 sources on file"
ONE_OF_3 = "is asserted, but the register it rests on counts 1 independent origin among 3 sources on file"
# (which register, the line, the code it is refused with or None, the message the page quotes)
EXAMPLE = [
    (1, "The Ashby foundry has stopped production, independently confirmed by the Ashby Courier and the Harrow "
        "Gazette.", "INDEPENDENCE_CONTRADICTED", "'independently' " + ONE_OF_2),
    (1, "The Ashby foundry has stopped production, as reported by the Ashby Courier and corroborated by the Harrow "
        "Gazette.", "CONFIRMED_ON_ONE_ORIGIN", "'corroborated' " + ONE_OF_2),
    (1, "The Ashby foundry has stopped production, according to the Ashby Courier and the Harrow Gazette.",
     "DEPENDENCE_UNSAID",
     "the line gives more than one source, and the register it rests on counts 1 independent origin among 2 sources "
     "on file"),
    (1, "The Ashby Courier reports that the Ashby foundry has stopped production; the Harrow Gazette cites the "
        "Courier's report.", None, ""),
    (1, "Reported by the Ashby Courier and repeated by the Harrow Gazette; it has not been independently confirmed.",
     None, ""),
    (2, "The Ashby foundry has stopped production, independently confirmed by multiple sources: the Ashby Courier, "
        "the Harrow Gazette and the Dale Herald.", "INDEPENDENCE_CONTRADICTED", "'independently' " + ONE_OF_3),
    (2, "Three separate reports say the Ashby foundry has stopped production.", "INDEPENDENCE_CONTRADICTED",
     "'separate reports' " + ONE_OF_3),
    (2, "The Ashby foundry has stopped production, as reported in the Ashby Courier, the Harrow Gazette and the Dale "
        "Herald, all carrying the Northgate Wire report.", None, ""),
    (2, "Reported in three outlets, all carrying the Northgate Wire report; one independent source.", None, ""),
]


def problems(block: int, statement: str, pin: dict) -> list[dict]:
    values = json.loads(BLOCKS[block])
    scope = f'The source register for the fact "{FACT}".'
    g = Graph(None)
    cur, lab = g.author("curator"), g.author("lab")
    inv = cur.investigation("How well is the fact sourced?", f'Report how well the fact "{FACT}" is sourced.',
                            scope=scope, **pin)["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="The source register.")
    res = lab.add("result", inv, kind="computed", outcome="negative", summary="The source register for this fact.",
                  values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = [{"key": "sources_on_file", "name": "sources on file", "value": values["sources_on_file"], "result": res},
            {"key": "independent_origins", "name": "independent origins among the sources",
             "value": values["independent_origins"], "result": res}]
    try:
        g.author("research-agent").add("claim", inv, kind="finding", statement=statement, scope=scope,
                                       measurements=meas,
                                       links=[{"rel": "supports", "from": res, "why": "The register."}])
        return []
    except GraphError as e:
        return list(e.problems)
    finally:
        g.close()


@pytest.mark.parametrize("pin", WAYS, ids=["alone", "beside software@3"])
@pytest.mark.parametrize("block, line, code, quote", EXAMPLE)
def test_the_page_gives_the_records_answer(block, line, code, quote, pin):
    got = problems(block, line, pin)
    row = next(r for r in PAGE.splitlines() if r.startswith(f'| "{line}"'))
    if code is None:
        assert got == []
        assert "Accepted" in row and "Refused" not in row
    else:
        assert [p["code"] for p in got] == [code]
        assert quote in got[0]["message"]
        assert f"**Refused**, `{code}`: *{quote}*" in row


@pytest.mark.parametrize("block, line, code, quote", [e for e in EXAMPLE if e[2]])
def test_without_the_policy_every_refused_line_goes_in(block, line, code, quote):
    assert "Without the policy every refused line above is accepted." in " ".join(PAGE.split())
    assert problems(block, line, {}) == []


def test_the_example_tables_have_no_line_the_test_does_not_file():
    rows = [r for r in PAGE.splitlines() if r.startswith('| "')]
    assert len(rows) == len(EXAMPLE)


def test_the_pin_the_page_shows_is_one_the_record_accepts():
    pin = json.loads(BLOCKS[0])
    g = Graph(None)
    inv = g.author("curator").investigation("How well is the fact sourced?", "Report how well the fact is sourced.",
                                            **pin)["id"]
    assert g.get(inv)["body"]["claim_policies"] == POLICY

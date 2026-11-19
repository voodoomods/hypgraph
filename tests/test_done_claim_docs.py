"""The examples in docs/claim-policies/done-claim.md are what the record answers.

Each line of the page's two example tables is filed against the log printed above its table, with the claim policy
pinned alone and beside `software@3`. The answer the page gives (accepted, or refused with a code and the quoted
message) has to be the engine's each way, and without the policy every line the page calls refused has to go in."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hypgraph import Graph
from hypgraph.graph import GraphError

PAGE = (Path(__file__).resolve().parents[1] / "docs" / "claim-policies" / "done-claim.md").read_text(encoding="utf-8")
BLOCKS = re.findall(r"```json\n(.*?)```", PAGE, re.S)        # the pin, the dry-run log, the partial log
POLICY = ["done_claim@1"]
WAYS = [{"claim_policies": POLICY}, {"profile": "software@3", "claim_policies": POLICY}]
ONE = "send the renewal notice to the customer's billing contact"
FIVE = "send the renewal notice to the customer's five billing contacts"
# (which log, the line, the code it is refused with or None, the message the page quotes)
EXAMPLE = [
    (1, "The renewal notice has been sent to the customer's billing contact.", "DONE_ON_DRY_RUN",
     "'sent' is asserted, but the log it rests on recorded only a dry run: no real call was made"),
    (1, "The renewal notice has been handled and is ready for delivery to the customer's billing contact.",
     "SHORTFALL_UNSAID",
     "the log this rests on recorded only a dry run: no real call was made, and the statement doesn't say so"),
    (1, "Only a dry run was made; nothing has been sent yet.", None, ""),
    (1, "The dry run completed successfully; no real email was sent.", None, ""),
    (2, "The renewal notice has been sent to all five billing contacts.", "DONE_PARTIAL",
     "'sent' is asserted of every one, but the log it rests on counts 3 of 5 real calls succeeded"),
    (2, "Renewal notices were sent to 3 of 5 billing contacts; the task is complete.", "DONE_PARTIAL",
     "'complete' is asserted of the whole task, but the log it rests on recorded 3 of 5 real calls succeeded"),
    (2, "The renewal notice was sent to 3 of the 5 billing contacts; 2 sends failed.", None, ""),
]


def problems(block: int, statement: str, pin: dict) -> list[dict]:
    values = json.loads(BLOCKS[block])
    task = ONE if values["calls_succeeded"]["n"] == 1 else FIVE
    scope = f"The task: {task}. The harness's tool log for this task."
    g = Graph(None)
    cur, lab = g.author("curator"), g.author("lab")
    inv = cur.investigation("Was the task carried out?", f"Report whether this task was carried out: {task}.",
                            scope=scope, **pin)["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="The harness's tool log.")
    res = lab.add("result", inv, kind="computed", outcome="negative", summary="The harness's tool log for this task.",
                  values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    count = dict(values["calls_succeeded"], key="calls_succeeded", name="real calls that succeeded", result=res)
    try:
        g.author("ops-agent").add("claim", inv, kind="finding", statement=statement, scope=scope,
                                  measurements=[count], links=[{"rel": "supports", "from": res, "why": "The log."}])
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
    inv = g.author("curator").investigation("Was the task carried out?", "Report whether the task was carried out.",
                                            **pin)["id"]
    assert g.get(inv)["body"]["claim_policies"] == POLICY

"""The examples on a claim policy's page are what the record answers.

For each page listed here, every row of every example table is filed against the result printed above its table,
with the page's policy pinned. The answer the page gives (accepted, or refused with a code and the quoted message)
has to be the engine's, and without the policy every line the page calls refused has to go in."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hypgraph import Graph
from hypgraph.graph import GraphError

DOCS = Path(__file__).resolve().parents[1] / "docs" / "claim-policies"
PAGES = {"proof-claim.md": "proof_claim@1", "forecast-call.md": "forecast_call@1", "flow-counts.md": "flow_counts@1"}
ROW = re.compile(r'^\| "(?P<line>.*)" \| (?P<answer>.*) \|$')
REFUSED = re.compile(r"\*\*Refused\*\*, `(?P<code>[A-Z_]+)`: \*(?P<quote>.*)\*$")


def rows(name: str) -> list[tuple[str, dict, str, str]]:
    """(policy, the result's values, the line, the page's answer) for every example row of a page."""
    out, values = [], None
    lines = (DOCS / name).read_text(encoding="utf-8").splitlines()
    for i, text in enumerate(lines):
        if text == "```json":
            block = json.loads(lines[i + 1])
            values = block if "claim_policies" not in block else values
        m = ROW.match(text)
        if m:
            assert values is not None, "an example row before any result"
            out.append((PAGES[name], values, m["line"], m["answer"]))
    return out


def problems(policy: str | None, values: dict, line: str) -> list[dict]:
    g = Graph(None)
    cur, lab = g.author("curator"), g.author("lab")
    scope = "The instrument's result for this question, and nothing beyond it."
    inv = cur.investigation("What does the result show?", "Report what the instrument's result shows.", scope=scope,
                            claim_policies=[policy] if policy else [])["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="The instrument's run.")
    res = lab.add("result", inv, kind="computed", outcome="negative", summary="The instrument's result.",
                  values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = []
    for k, v in values.items():
        if isinstance(v, dict):
            meas.append(dict(v, key=k, name=k.replace("_", " "), result=res))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            meas.append({"key": k, "name": k.replace("_", " "), "value": v, "result": res})
    try:
        g.author("agent").add("claim", inv, kind="finding", statement=line, scope=scope, measurements=meas,
                              links=[{"rel": "supports", "from": res, "why": "The instrument's result."}])
        return []
    except GraphError as e:
        return list(e.problems)
    finally:
        g.close()


EXISTING = [n for n in PAGES if (DOCS / n).exists()]
CASES = [(n, *r) for n in EXISTING for r in rows(n)]


@pytest.mark.parametrize("name,policy,values,line,answer", CASES, ids=[f"{c[0]}:{c[3][:40]}" for c in CASES])
def test_the_page_gives_the_records_answer(name, policy, values, line, answer):
    got = problems(policy, values, line)
    m = REFUSED.match(answer)
    if not m:
        assert answer.startswith("Accepted.") and got == []
        return
    assert [p["code"] for p in got] == [m["code"]]
    assert got[0]["message"].startswith(m["quote"])
    assert problems(None, values, line) == [], "the page says only the policy refuses this"


@pytest.mark.parametrize("name", EXISTING)
def test_a_page_has_examples_both_ways_and_a_pin_the_record_accepts(name):
    page = (DOCS / name).read_text(encoding="utf-8")
    answers = [r[3] for r in rows(name)]
    assert sum(a.startswith("Accepted.") for a in answers) >= 2 and sum("**Refused**" in a for a in answers) >= 2
    assert "Without the policy every refused line above is accepted." in " ".join(page.split())
    pin = next(json.loads(b) for b in re.findall(r"```json\n(.*?)\n```", page, re.S) if "claim_policies" in b)
    g = Graph(None)
    inv = g.author("curator").investigation("A question?", "Report what the result shows.", **pin)["id"]
    assert g.get(inv)["body"]["claim_policies"] == [PAGES[name]]

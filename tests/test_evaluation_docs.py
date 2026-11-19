"""The example in docs/workflows/evaluation.md is what the record answers.

Each line of the page's example table is filed against the page's own result. The answer the page gives (accepted, or
refused with a code and the quoted message) has to be the engine's, and the line and the quote have to be on the page."""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from hypgraph import Graph
from hypgraph.graph import GraphError

PAGE = (Path(__file__).resolve().parents[1] / "docs" / "workflows" / "evaluation.md").read_text(encoding="utf-8")
SCOPE = ("The churn model evaluation: AUC of the new model and the baseline on the validation and test splits, test "
         "as the mean of 5 seeds.")
NAMES = {"val_auc_model": "new model AUC on the validation split",
         "val_auc_baseline": "baseline AUC on the validation split",
         "test_auc_model": "new model AUC on the test split", "test_auc_baseline": "baseline AUC on the test split",
         "test_seeds_ahead": "test seeds where the new model is ahead of the baseline"}
# (the line, the code it is refused with or None, the message the page quotes)
EXAMPLE = [
    ("The new churn model beats the baseline.", "WIN_CONTRADICTED",
     "'beats' is asserted, but the result it rests on says otherwise on held-out data: auc 0.79 for the model "
     "against 0.81 for the other side (higher is better)"),
    ("The new churn model does not beat the baseline on the test split: 0.79 against 0.81.", None, ""),
    ("The new churn model beats the baseline on all 5 seeds.", "WIN_CONTRADICTED",
     "'beats' is asserted of every one, but the result counts 1 of 5 (test_seeds_ahead)"),
    ("The new churn model is ahead of the baseline on 1 of 5 test seeds.", None, ""),
    ("The new churn model reaches an AUC of 0.84.", "TUNING_SPLIT_UNLABELLED",
     "the statement gives a score from the tuning split (val_auc_model) with no word that it is one and no held-out "
     "figure"),
    ("The new churn model reaches a validation AUC of 0.84 and a test AUC of 0.79.", None, ""),
    ("On validation the new churn model beats the baseline, 0.84 against 0.82.", None, ""),
]


def page_result() -> dict:
    """The result the page's example files: its first JSON block."""
    return json.loads(re.search(r"```json\n(.*?)```", PAGE, re.S).group(1))


def problems(statement: str, profile: str | None) -> list[dict]:
    values = page_result()
    g = Graph(None)
    cur, lab = g.author("curator"), g.author("lab")
    kw = {"profile": profile} if profile else {}
    inv = cur.investigation("Is the new model better than the baseline?",
                            "Report how the new model compares with the baseline.", scope=SCOPE, **kw)["id"]
    run = lab.add("run", inv, kind="lab", state="succeeded", name="Evaluation run.")
    res = lab.add("result", inv, kind="computed", outcome="negative", summary="The evaluation harness's scores.",
                  values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]
    meas = [dict({"key": k, "name": NAMES[k], "result": res}, **(v if isinstance(v, dict) else {"value": v}))
            for k, v in values.items() if not isinstance(v, bool)]
    try:
        g.author("ml-agent").add("claim", inv, kind="finding", statement=statement, scope=SCOPE, measurements=meas,
                                 links=[{"rel": "supports", "from": res, "why": "The evaluation report."}])
        return []
    except GraphError as e:
        return list(e.problems)
    finally:
        g.close()


@pytest.mark.parametrize("line, code, quote", EXAMPLE)
def test_the_page_gives_the_records_answer(line, code, quote):
    got = problems(line, "evaluation@1")
    row = next(r for r in PAGE.splitlines() if r.startswith(f'| "{line}"'))
    if code is None:
        assert got == []
        assert "Accepted" in row and "Refused" not in row
    else:
        assert [p["code"] for p in got] == [code]
        assert quote in got[0]["message"]
        assert f"**Refused**, `{code}`: *{quote}*" in row


@pytest.mark.parametrize("profile", [None, "scientific@2"])
def test_the_first_line_goes_in_without_the_profile(profile):
    assert "With no profile, or under `scientific@2`, the first line is accepted." in PAGE
    assert problems(EXAMPLE[0][0], profile) == []


def test_the_example_table_has_no_line_the_test_does_not_file():
    start = PAGE.index("| the line | the record's answer |")
    rows = [r for r in PAGE[start:PAGE.index("With no profile", start)].splitlines() if r.startswith('| "')]
    assert len(rows) == len(EXAMPLE)

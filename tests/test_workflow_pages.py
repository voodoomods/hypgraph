"""The workflow pages (docs/workflows/) say what the engine does.

Every code a page names in backticks is one the engine has (the pages once listed seven refusals that were never
built), and every engine answer a page quotes is what the engine says in that case, including the one limit the
pages state: an experiment revised after its run still reads as preregistered."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from hypgraph import Graph, GraphError, Policy

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "docs" / "workflows"
CODE = re.compile(r"`([A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+)`")
H = "harness"
SHA_A, SHA_B = "a1" * 32, "b2" * 32


def page(name: str) -> str:
    return " ".join((PAGES / name).read_text(encoding="utf-8").split())


def engine_words() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "src" / "hypgraph").rglob("*.py"))


def docs() -> list[Path]:
    return sorted([*(ROOT / "docs").rglob("*.md"), *(ROOT / "examples").rglob("*.md"), *(ROOT / "skills").rglob("*.md"),
                   ROOT / "README.md", ROOT / "AGENTS.md"])


def test_every_code_the_docs_name_is_one_the_engine_has():
    src = engine_words()
    unknown = {}
    for path in docs():
        for code in CODE.findall(path.read_text(encoding="utf-8")):
            if code.endswith("_KEY"):                                   # environment variables (OPENAI_API_KEY)
                continue
            if not re.search(rf"\b{code}\b", src):
                unknown.setdefault(str(path.relative_to(ROOT)), []).append(code)
    assert not unknown, f"codes the engine never gives: {unknown}"


def _g(profile: str, reviewers=("critic",)):
    g = Graph(policy=Policy(reviewers=set(reviewers), extra_reserved={H}))
    inv = g.create(author=H, type="investigation", fields={"title": "A workflow investigation.",
                   "objective": "See what the workflow pages say the record does.", "profile": profile})["id"]
    q = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "Does it hold?"})["id"]
    return g, inv, q


def _gate(g, q, name: str) -> dict:
    return next(gt for gt in g.stage(q)["gates"] if gt["gate"] == name)


def _experiment(g, inv, q, at: str) -> str:
    imp = g.policy.importer
    h = g.create(author=imp, type="hypothesis", inv=inv, fields={"statement": "Caching halves the latency.",
                 "predictions": ["p50 latency falls by half"]}, links=[{"rel": "answers", "to": q}])["id"]
    return g.create(author=imp, type="experiment", inv=inv, at=at,
                    fields={"aim": "Measure latency with the cache on and off.", "protocol": "Fifty requests each way.",
                            "success_criteria": "The p50 latency with the cache is half of it without."},
                    links=[{"rel": "tests", "to": h, "data": {"expected": "p50 halves"}}])["id"]


def _run(g, inv, x, at: str) -> str:
    return g.create(author=g.policy.importer, type="run", inv=inv, at=at,
                    fields={"kind": "agent", "name": "latency", "state": "succeeded"},
                    links=[{"rel": "executes", "to": x}])["id"]


@pytest.mark.parametrize("profile", ["scientific@2", "trading@2"])
def test_an_experiment_written_after_its_run_goes_in_and_the_gate_says_so(profile):
    g, inv, q = _g(profile)
    x = _experiment(g, inv, q, "2026-01-03T00:00:00+00:00")
    _run(g, inv, x, "2026-01-01T00:00:00+00:00")
    why = _gate(g, q, "preregistered")["why"]
    quote = ("X1 was written after RUN1 executed it — not preregistered; the experiment (protocol, expected outcome) "
             "comes before the run")
    assert why == quote
    assert quote in page("scientific.md")
    assert "was written after the run" in page("trading.md")


@pytest.mark.parametrize("profile", ["scientific@2", "trading@2"])
def test_the_limit_the_pages_state_an_experiment_revised_after_its_run_still_reads_as_preregistered(profile):
    g, inv, q = _g(profile)
    x = _experiment(g, inv, q, "2026-01-01T00:00:00+00:00")
    _run(g, inv, x, "2026-01-02T00:00:00+00:00")
    g.revise(author=g.policy.importer, node=x, fields={"protocol": "Five hundred requests each way."},
             reason="The first protocol was too small to show a change.")
    assert _gate(g, q, "preregistered")["met"]          # when this is caught, the pages' "Not caught" lines go
    for name in ("scientific.md", "trading.md"):
        assert "Not caught: an experiment *revised* after its run" in page(name)


def test_a_check_of_stale_evidence_is_recorded_and_the_gate_does_not_count_it():
    g, inv, q = _g("scientific@2")
    data = g.create(author="lead", type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "d.csv"})["id"]
    run = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "name": "fit", "state": "succeeded"},
                   links=[{"rel": "uses", "to": data}])["id"]
    rs = g.create(author="lab", type="result", inv=inv, fields={"summary": "Error rate 0.12.", "outcome": "positive",
                  "values": {"err": {"value": 0.12}}}, links=[{"rel": "produced", "from": run}])["id"]
    c = g.create(author="ana", type="claim", inv=inv, fields={"statement": "The error rate is 0.12.", "kind": "finding",
                 "scope": "The fit on d.csv.", "measurements": [{"name": "err", "result": rs, "key": "err", "value": 0.12}]},
                 links=[{"rel": "answers", "to": q},
                        {"rel": "supports", "from": rs, "why": "The lab fit gives the error rate the claim states."}])["id"]
    g.create(author="lead", type="artifact", inv=inv, fields={"sha256": SHA_B, "path": "d.csv"},
             links=[{"rel": "supersedes", "to": data}])
    g.review(author="critic", target=c, verdict="checked", method="Read the fit.", notes="0.12 as stated.")
    assert g.state(c)["review"]["state"] == "checked"
    gate = _gate(g, q, "reviewed")
    quote = "CL1 is checked but its evidence is stale: artifact A1 is superseded — rerun before the check counts"
    assert not gate["met"] and gate["why"] == quote
    assert quote in page("scientific.md")


def test_a_number_not_in_the_cited_passage_is_the_kernels_unbound_number():
    g, inv, q = _g("knowledge@2")
    src = g.create(author="r", type="source", inv=inv, fields={"citation": "Encyclopaedia entry, Peace of Westphalia.",
                   "url": "https://example.org/w", "passage": "signed in October 1648", "retrieved": "2026-10-20",
                   "kind": "tertiary"}, links=[{"rel": "part_of", "to": q}])["id"]
    with pytest.raises(GraphError) as e:
        g.create(author="r", type="claim", inv=inv, fields={"statement": "The treaty was signed in 1649.",
                 "kind": "finding", "scope": "The Peace, as a date."},
                 links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src}])
    assert [p["code"] for p in e.value.problems] == ["UNBOUND_NUMBER"]
    quote = "(the source it cites doesn't give them)"
    assert quote in e.value.problems[0]["message"] and quote in page("knowledge.md")
    g.create(author="r", type="claim", inv=inv, fields={"statement": "The treaty was signed in 1648.", "kind": "finding",
             "scope": "The Peace, as a date."}, links=[{"rel": "answers", "to": q}, {"rel": "cites", "to": src}])
    assert "Not built: a warning on a finding resting only on tertiary sources" in page("knowledge.md")


def test_a_solver_reviewing_its_own_solution_is_refused_by_the_kernel():
    g, inv, q = _g("optimization@2", reviewers=("verifier", "solver"))
    inst = g.create(author="lead", type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "i.json", "kind": "instance"},
                    links=[{"rel": "part_of", "to": q}])["id"]
    run = g.create(author="solver", type="run", inv=inv, fields={"kind": "agent", "name": "cbc", "state": "succeeded",
                   "config": {"source": "print('cbc')"}}, links=[{"rel": "uses", "to": inst}])["id"]
    rs = g.create(author="solver", type="result", inv=inv, fields={"summary": "Solved to a 0.0 gap.", "outcome": "positive",
                  "values": {"objective": {"value": 412.0}, "feasible": {"value": True}, "gap": {"value": 0.0}}},
                  links=[{"rel": "produced", "from": run}, {"rel": "part_of", "to": q}])["id"]
    with pytest.raises(GraphError) as e:
        g.review(author="solver", target=rs, verdict="checked", method="Recomputed every constraint.", notes="Feasible.")
    quote = "you can't review your own work — ask a reviewer (verifier)"
    assert str(e.value) == quote and quote in page("optimization.md")


def test_a_diff_without_its_shas_is_artifact_missing_fields():
    g, inv, q = _g("software@2")
    with pytest.raises(GraphError) as e:
        g.create(author="dev", type="artifact", inv=inv, fields={"sha256": SHA_A, "path": "x.diff", "kind": "diff"},
                 links=[{"rel": "part_of", "to": q}])
    assert [p["code"] for p in e.value.problems] == ["ARTIFACT_MISSING_FIELDS"]
    quote = "an artifact kind=diff needs meta.base_sha, meta.head_sha, meta.files in this workflow (software@2)"
    assert e.value.problems[0]["message"].startswith(quote) and quote in page("software.md")

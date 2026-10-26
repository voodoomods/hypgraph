"""
The vocabulary of a HypGraph record (format ``hypgraph/1``): node types and their fields, the relations that may
join them, review verdicts and the ranks of evidence. Plain data, so other implementations can read it — and so
``hypgraph schema`` can print it as JSON.
"""

from __future__ import annotations

FORMAT = "hypgraph/1"


def _f(kind: str, n: int = 2000, req: bool = False) -> tuple:
    """A field: (kind, max length, required). Kinds: str, text, list, dict, enum:a|b, bool, num, any."""
    return (kind, n, req)


POSITIVE = {"checked", "pass", "reproduced", "replicated", "separate_implementation", "generalizes"}
NEGATIVE = {"fail", "not_reproduced", "not_replicated", "does_not_generalize"}
VERDICTS = POSITIVE | NEGATIVE | {"objection", "resolved", "inconclusive", "comment"}

PROFILE_RANK = ["unverified", "agent_reported", "lab_recorded", "project_rerun", "separate_implementation",
                "new_data", "external"]
PROFILE_LABEL = {"unverified": "unverified report", "agent_reported": "agent-reported run",
                 "lab_recorded": "lab-recorded run", "project_rerun": "reproduced in project",
                 "separate_implementation": "separate implementation", "new_data": "replicated on new data",
                 "external": "external source"}

TYPES: dict[str, dict] = {
    "investigation": {"prefix": "INV", "fields": {
        "title": _f("str", 200, True), "objective": _f("text", 3000, True), "success_criteria": _f("text", 3000),
        "scope": _f("text", 3000), "state": _f("enum:active|archived|published"), "reviewers": _f("list", 20),
        "constants": _f("list", 60), "strict_claims": _f("bool"), "keywords": _f("list", 30), "projects": _f("list", 20),
        "doi": _f("str", 120), "note": _f("text", 2000), "legacy_case": _f("str", 80),
        "profile": _f("str", 60)}},                      # governance profile, e.g. software@1 (profiles.py)
    "question": {"prefix": "Q", "fields": {"text": _f("text", 1500, True), "why": _f("text", 1500)}},
    "hypothesis": {"prefix": "H", "fields": {
        "statement": _f("text", 1500, True), "assumptions": _f("list", 20), "predictions": _f("list", 20, True),
        "distinguishing": _f("list", 20), "open_questions": _f("list", 20)}},
    "claim": {"prefix": "CL", "fields": {
        "statement": _f("text", 1500, True), "scope": _f("text", 1000), "limitations": _f("text", 1500),
        "kind": _f("enum:finding|exclusion|inconclusive|convention|lead"), "measurements": _f("list", 40),
        "evidence_note": _f("text", 1500), "exposure": _f("num"), "exposure_unit": _f("str", 60),
        "legacy": _f("dict", 4000)}},
    "experiment": {"prefix": "X", "fields": {
        "aim": _f("text", 1500, True), "protocol": _f("text", 4000, True), "controls": _f("text", 2000),
        "success_criteria": _f("text", 2000, True), "method": _f("str", 200), "budget": _f("dict", 400),
        "power_check": _f("text", 1000), "cost_minutes": _f("num"), "seed": _f("any", 200)}},
    "run": {"prefix": "RUN", "fields": {
        "kind": _f("enum:lab|agent|external", req=True), "job_id": _f("str", 80), "name": _f("str", 300),
        "state": _f("enum:queued|running|succeeded|failed|timeout|cancelled|interrupted|unknown"),
        "code": _f("list", 50), "inputs": _f("list", 200), "outputs": _f("list", 500), "args": _f("list", 100),
        "config": _f("dict", 20000), "seed": _f("any", 200), "env": _f("dict", 4000), "started": _f("str", 40),
        "finished": _f("str", 40), "exit_code": _f("any", 20), "log_sha256": _f("str", 80), "note": _f("text", 2000)}},
    "result": {"prefix": "RS", "fields": {
        "summary": _f("text", 2000, True), "kind": _f("enum:computed|observed|cited"),
        "outcome": _f("enum:positive|negative|inconclusive|expected_failure|skipped|failed"),
        "values": _f("dict", 20000), "expected": _f("text", 1500), "limitations": _f("text", 1500),
        "power": _f("enum:demonstrated|not_demonstrated|not_applicable"), "evidence_note": _f("text", 1500),
        "valid_until": _f("str", 40),                     # a workflow's shelf life: past it the result is stale
        "legacy": _f("dict", 4000)}},
    "artifact": {"prefix": "A", "fields": {
        "sha256": _f("str", 64, True), "path": _f("str", 500), "size": _f("num"), "format": _f("str", 40),
        "kind": _f("str", 40), "meta": _f("dict", 4000)}},   # typed by the workflow: diff {base_sha, head_sha, files}…
    "source": {"prefix": "S", "fields": {
        "citation": _f("text", 1000, True), "doi": _f("str", 200), "url": _f("str", 500), "passage": _f("text", 3000),
        "retrieved": _f("str", 40), "says": _f("text", 1500), "kind": _f("enum:primary|secondary|tertiary"),
        "reliability": _f("text", 1000)}},
    "review": {"prefix": "RV", "fields": {
        "verdict": _f("enum:" + "|".join(sorted(VERDICTS)), req=True), "method": _f("text", 1500, True),
        "notes": _f("text", 4000, True), "official": _f("bool")}},
    "decision": {"prefix": "D", "fields": {
        "choice": _f("text", 1500, True), "alternatives": _f("list", 20), "reasons": _f("text", 3000, True),
        "revisit_if": _f("text", 1500), "meeting": _f("str", 80),
        # typed by the workflow: a trading position carries size, stop, review_date and paper=true
        "kind": _f("str", 40), "size": _f("str", 120), "stop": _f("str", 120), "review_date": _f("str", 40),
        "paper": _f("bool"), "sensitivity": _f("text", 1500)}},
    "task": {"prefix": "T", "fields": {
        "kanban_id": _f("str", 80), "title": _f("str", 300), "objective": _f("text", 2000),
        "assignee": _f("str", 80), "role": _f("str", 80), "prediction": _f("text", 1500), "method": _f("text", 1500),
        "done_when": _f("list", 12), "budget": _f("dict", 400), "note": _f("text", 1500)}},
}

ANY = set(TYPES)
EVIDENCE_SRC = {"result", "claim", "source"}
RELS: dict[str, tuple[set, set]] = {
    "part_of": (ANY - {"investigation"}, {"investigation", "question"}),
    "answers": ({"hypothesis", "claim"}, {"question"}),
    "alternative_to": ({"hypothesis"}, {"hypothesis"}),
    "tests": ({"experiment"}, {"hypothesis", "claim"}),
    "executes": ({"run"}, {"experiment"}),
    "produced": ({"run"}, {"result", "artifact"}),
    "uses": ({"run"}, {"artifact"}),
    "derived_from": ({"result", "claim", "artifact"}, {"result", "artifact", "run", "source"}),
    "supports": (EVIDENCE_SRC, {"claim", "hypothesis"}),
    "challenges": (EVIDENCE_SRC, {"claim", "hypothesis"}),
    "requires": ({"claim", "hypothesis"}, {"claim"}),
    "replicates": ({"run"}, {"run"}),
    "reviews": ({"review"}, {"claim", "result", "run", "experiment", "hypothesis"}),
    "supersedes": (ANY - {"review", "investigation"}, ANY - {"review", "investigation"}),   # an artifact too: a newer diff, instance, data file
    "corrects": ({"claim", "result", "decision", "source"}, {"claim", "result", "decision", "source"}),
    "motivated_by": ({"experiment", "hypothesis", "question"}, ANY),
    "cites": ({"claim", "result", "hypothesis", "experiment"}, {"source"}),
    "based_on": ({"decision"}, {"claim", "result", "hypothesis"}),
    "works_on": ({"task"}, ANY - {"task", "artifact", "review"}),
    "blocked_by": ({"task"}, {"task"}),
    "rests_on": ({"task"}, ANY - {"task", "review"}),
    "settles": ({"decision"}, {"task"}),
}
REPLICATION = ("same_code", "new_seed", "new_impl", "new_data", "new_env")
# What writers call the enum values. Mapped before validation, by (type, field); the stored value is canonical.
SYNONYMS: dict[tuple[str, str], dict[str, str]] = {
    ("result", "outcome"): {"success": "positive", "succeeded": "positive", "successful": "positive", "pass": "positive",
                          "passed": "positive", "ok": "positive", "yes": "positive", "confirmed": "positive",
                          "supported": "positive", "no": "negative", "refuted": "negative", "disconfirmed": "negative",
                          "null": "negative", "unclear": "inconclusive", "mixed": "inconclusive",
                          "indeterminate": "inconclusive", "error": "failed", "crashed": "failed", "fail": "failed",
                          "failure": "failed", "skip": "skipped", "not_run": "skipped"},
    ("result", "kind"): {"calculated": "computed", "derived": "computed", "measured": "observed", "empirical": "observed",
                       "quoted": "cited", "literature": "cited"},
    ("claim", "kind"): {"fact": "finding", "result": "finding", "observation": "finding", "measurement": "finding",
                      "conclusion": "finding", "rule_out": "exclusion", "ruled_out": "exclusion", "negative": "exclusion",
                      "undetermined": "inconclusive", "unclear": "inconclusive", "definition": "convention",
                      "notation": "convention", "hunch": "lead", "idea": "lead"},
    ("run", "state"): {"success": "succeeded", "successful": "succeeded", "done": "succeeded", "completed": "succeeded",
                      "complete": "succeeded", "ok": "succeeded", "error": "failed", "failure": "failed", "fail": "failed",
                      "crashed": "failed", "timed_out": "timeout", "killed": "cancelled", "stopped": "interrupted"},
}
# what a node rests on: if the far end falls, this node is at risk (a work order is moot). A profile's workflow
# may add relations (profiles.Workflow.invalidates: `uses`, `cites`); derive reads them per investigation.
RISKY = ("requires", "derived_from", "based_on", "works_on", "rests_on")
SAME_TYPE = ("supersedes", "corrects")

# One line each — what the type is for. Shown by `hypgraph schema`, the MCP server and the site.
ABOUT = {
    "investigation": "The study: an objective, its scope, who reviews it. Every other node belongs to one.",
    "question": "Something you want to know.",
    "hypothesis": "A possible answer, with the predictions that would show it wrong.",
    "claim": "What you assert is known, with its scope and its numbers bound to results.",
    "experiment": "A planned test: aim, protocol, controls, success criteria, and what each hypothesis expects.",
    "run": "One execution: code, inputs and outputs hashed, seed, state. `kind=lab` only from an instrument.",
    "result": "What a run (or an observation, or a citation) found: values, outcome, power.",
    "artifact": "Exact bytes, by sha256 — data, code, a model, a figure.",
    "source": "Outside literature or data: citation, DOI, the passage that says it.",
    "review": "A verdict on one version of a claim, result, run, experiment or hypothesis.",
    "decision": "A choice made on the evidence; flagged when what it was based on changes.",
    "task": "A unit of work linked to what it works on — or a work order: objective, assignee, done-when "
            "predicates the record checks, budget (see coordination).",
}
REL_ABOUT = {
    "part_of": "belongs to an investigation or question", "answers": "offers an answer to a question",
    "alternative_to": "competes with another hypothesis", "tests": "an experiment tests a hypothesis or claim "
    "(data.expected: what it should show if true)", "executes": "a run carries out an experiment",
    "produced": "a run produced a result or artifact", "uses": "a run used an artifact (data.role: data / code / "
    "model / config)", "derived_from": "computed or taken from", "supports": "evidence for (why required)",
    "challenges": "evidence against (why required)", "requires": "rests on another claim as a premise",
    "replicates": "a run repeats another (data.differs: same_code / new_seed / new_impl / new_data / new_env)",
    "reviews": "a review of a node (written by review())", "supersedes": "replaces an older node of the same type",
    "corrects": "fixes an error in a node of the same type (a fact-checker re-kinds a source this way)",
    "motivated_by": "prompted by",
    "cites": "cites a source", "based_on": "a decision rests on this evidence (pinned to its version)",
    "works_on": "a task works on a node (it is moot if that node falls)", "blocked_by": "a task waits on another task",
    "rests_on": "a work order rests on a premise, pinned to the version it was issued against",
    "settles": "a decision accepts a work order (based_on the evidence that met its predicates)",
}


def describe() -> dict:
    """The whole vocabulary as JSON-ready data."""
    return {
        "format": FORMAT,
        "types": {t: {"prefix": v["prefix"], "about": ABOUT[t],
                      "fields": {k: {"kind": f[0], "max": f[1], "required": f[2]} for k, f in v["fields"].items()}}
                  for t, v in TYPES.items()},
        "relations": {r: {"from": sorted(a), "to": sorted(b), "about": REL_ABOUT[r]} for r, (a, b) in RELS.items()},
        "verdicts": {"positive": sorted(POSITIVE), "negative": sorted(NEGATIVE),
                     "other": sorted(VERDICTS - POSITIVE - NEGATIVE)},
        "evidence_rank": PROFILE_RANK, "evidence_label": PROFILE_LABEL, "replication": list(REPLICATION),
    }

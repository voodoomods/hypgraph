"""
The story every example in this folder tells, so each framework's file holds only its own wiring.

An eval harness has compared two models on the same 1,000 held-out questions: model A got 812 right, model B 800.
An agent, connected to the record through `hypgraph mcp` as the author `analyst`, is asked whether A is more
accurate. A tempting answer is "significantly more accurate". The record refuses it with the arithmetic (p = 0.5)
and says what to write instead; the agent writes that, and it is accepted. Nothing in the framework knows HypGraph
exists: the agent sees MCP tools, and the record does the checking.

Run any example with no flags for the scripted model (offline, free, deterministic), or with `--real` for a real
one. The scripted model makes the same moves a careful model makes: read the overview, overclaim, read the refusal,
write the honest claim. What it can't show is a model reasoning; `--real` does.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import sysconfig
import tempfile
from pathlib import Path
from typing import Any

AUTHOR = "analyst"
SCOPE = "Both models on the same 1,000 held-out questions, one run each, scored by the eval harness."
OVERCLAIM = "Model A is significantly more accurate than model B (812 of 1000 vs 800 of 1000)."
HONEST = ("Model A is not significantly more accurate than model B: 812 of 1000 vs 800 of 1000, a difference of "
          "1.2 points.")

INSTRUCTIONS = (
    "You keep a research record through the hypgraph tools. Read the overview before you write. Every claim states "
    "its numbers and binds them to a result in `measurements`. When the record refuses a write, the refusal says what "
    "to fix: fix exactly that and write again. Never drop a number or a word just to get past a refusal.")

TASK = (
    "Investigation INV1 compares model A and model B. Result RS1 holds the counts: a_correct (A's correct answers out "
    "of 1000) and b_correct (B's). Add one claim (type claim, kind finding) that answers whether model A is more "
    "accurate than model B. Bind its numbers with measurements named a and b, each {name, result: RS1, key, k, n}, "
    f"link it with {{\"rel\": \"supports\", \"from\": \"RS1\", \"why\": \"...\"}}, and use the scope: {SCOPE!r}. "
    "Then say in one sentence what the record accepted.")


def seed(path: str | Path) -> None:
    """The record before the agent arrives: the investigation and the harness's result, written in Python as trusted
    callers (the operator opens it; the instrument, `lab`, files the run and its counts)."""
    from hypgraph import Graph
    g = Graph(str(path))
    inv = g.create(author="operator", type="investigation", fields={
        "title": "Is model A more accurate than model B?",
        "objective": "Compare the two models on the same 1,000 held-out questions and say what the counts support.",
        "reviewers": ["critic"]})["id"]
    run = g.create(author="lab", type="run", inv=inv, fields={
        "kind": "lab", "name": "eval harness on the held-out set", "state": "succeeded"})["id"]
    g.create(author="lab", type="result", inv=inv, fields={
        "summary": "Model A answered 812 of 1000 correctly and model B 800 of 1000.", "outcome": "positive",
        "values": {"a_correct": {"k": 812, "n": 1000}, "b_correct": {"k": 800, "n": 1000}}},
        links=[{"rel": "produced", "from": run}])


def server(path: str | Path, author: str = AUTHOR) -> tuple[str, list[str]]:
    """The command that starts the record's MCP server over stdio, writing as one author fixed at start."""
    return sys.executable, ["-m", "hypgraph", "--db", str(path), "--as", author, "mcp"]


def short_server(path: str | Path, author: str = AUTHOR) -> tuple[str, list[str], dict[str, str]]:
    """The same server as a short command line, `hypgraph mcp`, with the record and author in its environment, for
    frameworks that name the tools after the command line. Puts this interpreter's scripts folder on PATH so the
    `hypgraph` console script is found without activating the environment."""
    scripts = sysconfig.get_path("scripts")
    if scripts and scripts not in os.environ.get("PATH", "").split(os.pathsep):
        os.environ["PATH"] = scripts + os.pathsep + os.environ.get("PATH", "")
    return "hypgraph", ["mcp"], {"HYPGRAPH_DB": str(path), "HYPGRAPH_AUTHOR": author}


def _claim(statement: str) -> dict[str, Any]:
    return {"type": "claim",
            "fields": {"statement": statement, "scope": SCOPE, "kind": "finding",
                       "measurements": [{"name": "a", "result": "RS1", "key": "a_correct", "k": 812, "n": 1000},
                                        {"name": "b", "result": "RS1", "key": "b_correct", "k": 800, "n": 1000}]},
            "links": [{"rel": "supports", "from": "RS1", "why": "the counts this claim states"}]}


def next_move(seen: list[str]) -> tuple[str, dict[str, Any]] | str:
    """The scripted model's next move, from what the tools have said so far (results and errors, in order): a tool
    call as (name, arguments), or the final answer as text."""
    if not seen:
        return "overview", {}
    if len(seen) == 1:
        return "add", _claim(OVERCLAIM)
    added = [m.group(1) for s in seen for m in [re.search(r"Added (CL\d+)", s)] if m]
    if "SIGNIFICANCE_NOT_SHOWN" in seen[-1] and not added:
        return "add", _claim(HONEST)
    return (f"The record accepted {added[-1]}: {HONEST}" if added else
            "The record refused every version I wrote; see the refusal log.")


def args(description: str, real_help: str = "", model: str = "gpt-4.1-mini", extra=None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=description)
    if real_help:
        ap.add_argument("--real", action="store_true", help=real_help)
    ap.add_argument("--model", default=os.getenv("MODEL", model), help=f"the real model (default {model})")
    ap.add_argument("--db", default="", help="the record file (default: a fresh one in a temporary folder)")
    if extra:
        extra(ap)
    a = ap.parse_args()
    a.real = getattr(a, "real", True)
    if not a.db:
        a.db = str(Path(tempfile.mkdtemp(prefix="hypgraph-example-")) / "record.hypgraph")
    if not Path(a.db).exists():
        seed(a.db)
    return a


def outcome(path: str | Path, answer: str, real: bool = False) -> int:
    """What the record holds afterwards: the agent's refusals and its accepted claims, read in Python. The scripted
    model must show the whole story (refused, then fixed); a real model passes if it got an honest claim accepted
    and left no refusal unfixed, since a careful model may write the honest claim first time."""
    from hypgraph import Graph
    g = Graph(str(path))
    inv = g.investigations()[0]["id"]
    rep = g.refusal_report(inv)
    mine = rep["by_author"].get(AUTHOR, {"refused": 0, "fixed": 0})
    claims = [n for n in g.search(type="claim", inv=inv) if n["by"] == AUTHOR]
    print("\nagent's answer:", " ".join(str(answer).split())[:400])
    print(f"\nthe record, read afterwards ({path}):")
    for r in reversed(rep["recent"]):
        if r["author"] == AUTHOR:
            print(f"  refused   {json.dumps(r['statement'])}  [{', '.join(r['codes'])}]")
    for c in claims:
        print(f"  accepted  {c['code']} {json.dumps(g.get(c['id'])['body']['statement'])}")
        print(f"            {c['state']['sentence']}")
    print(f"  refusal log: {mine['refused']} refused, {mine['fixed']} came back honest")
    if real:
        ok = bool(claims) and mine["fixed"] >= mine["refused"]
        story = (f"{mine['refused']} refused, every one came back honest" if mine["refused"] else
                 "the claim was accepted as first written")
        print("\n" + (f"OK: {story}." if ok else
                      "Not done: " + ("no claim was accepted." if not claims else "a refusal was left unfixed.")))
        return 0 if ok else 1
    ok = mine["refused"] >= 1 and mine["fixed"] >= 1 and bool(claims)
    print("\n" + ("OK: the overclaim was refused, and the honest claim was accepted in its place." if ok else
                  "Not the expected story: " + ("nothing was refused." if not mine["refused"] else
                                                "no honest claim came back.")))
    return 0 if ok else 1

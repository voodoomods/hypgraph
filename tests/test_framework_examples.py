"""The framework examples (examples/frameworks) run end to end: each framework's own tool-calling path, a scripted
model, the record's MCP server over stdio. The overclaim must be refused and the honest claim accepted, read back from
the record afterwards. The Claude Agent SDK has no scripted mode, so its wiring check runs instead.

A framework that isn't installed is skipped: the main test job doesn't install them. The `frameworks` CI job
does, and sets HYPGRAPH_EXAMPLES_REQUIRED so a missing one fails there."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent.parent / "examples" / "frameworks"

CASES = [
    ("langchain_agent.py", ["langchain", "langgraph", "langchain_mcp_adapters"], [],
     "OK: the overclaim was refused, and the honest claim was accepted in its place."),
    ("langgraph_agent.py", ["langgraph", "langchain_mcp_adapters"], [],
     "OK: the overclaim was refused, and the honest claim was accepted in its place."),
    ("pydantic_ai_agent.py", ["pydantic_ai"], [],
     "OK: the overclaim was refused, and the honest claim was accepted in its place."),
    ("crewai_agent.py", ["crewai"], [],
     "OK: the overclaim was refused, and the honest claim was accepted in its place."),
    ("openai_agents_sdk.py", ["agents"], [],
     "OK: the overclaim was refused, and the honest claim was accepted in its place."),
    ("claude_sdk_agent.py", ["claude_agent_sdk"], ["--check"], "OK: every allowed tool exists."),
]


@pytest.mark.parametrize("script,modules,flags,expect", CASES, ids=[c[0] for c in CASES])
def test_example_runs(script, modules, flags, expect, tmp_path):
    if not (HERE / script).exists():
        pytest.skip("examples aren't shipped in the sdist")
    missing = [m for m in ["mcp", "fastmcp", *modules] if importlib.util.find_spec(m) is None]
    if missing:
        # the CI job that installs the frameworks sets this, so a broken install fails instead of skipping
        (pytest.fail if os.getenv("HYPGRAPH_EXAMPLES_REQUIRED") else pytest.skip)(f"not installed: {', '.join(missing)}")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8",
           "CREWAI_DISABLE_TELEMETRY": "true", "OTEL_SDK_DISABLED": "true", "CREWAI_TRACING_ENABLED": "false"}
    for k in ("OPENAI_API_KEY", "MODEL"):            # scripted: no call may reach a provider
        env.pop(k, None)
    db = tmp_path / "record.hypgraph"
    r = subprocess.run([sys.executable, script, "--db", str(db), *flags], cwd=HERE, env=env,
                       stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=600)
    assert r.returncode == 0, (r.stdout[-3000:], r.stderr[-3000:])
    assert expect in r.stdout

"""
A clean-install walkthrough: install HypGraph into a fresh virtual environment, from PyPI, a wheel or an sdist, and do
what the README and `hypgraph --help` say, as someone who has never seen the repository would. Nothing here imports
the checkout: every step runs the installed `hypgraph` command (and, with --mcp, the installed MCP server).

    python dev/e2e_install.py                      # the latest release on PyPI
    python dev/e2e_install.py dist/hypgraph-*.whl  # a built wheel (CI and the release job)
    python dev/e2e_install.py dist/hypgraph-*.tar.gz --mcp

Steps: start a record, an investigation with a named reviewer, a hypothesis, an experiment that tests it, a run and
its result, a claim the record accepts, a claim it refuses (and the honest version it suggests), the reviewer's
review, an export, and verification in another directory with no graph file — on its own and against the head the
first export printed, and failing on a rewritten copy. With --mcp, an MCP client lists the tools and adds a
hypothesis through `hypgraph mcp`. Exit 0 only if every step did what the docs say.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

STEPS: list[tuple[str, bool]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    STEPS.append((name, ok))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("spec", nargs="?", default="hypgraph", help="what to pip install: a name, a version, a wheel or an sdist")
    ap.add_argument("--mcp", action="store_true", help="install the [mcp] extra and drive `hypgraph mcp` with a client")
    ap.add_argument("--keep", action="store_true", help="keep the temporary directory")
    a = ap.parse_args()
    root = Path(tempfile.mkdtemp(prefix="hypgraph-e2e-"))
    env_dir, work, elsewhere = root / "venv", root / "study", root / "auditor"
    work.mkdir()
    elsewhere.mkdir()
    venv.create(env_dir, with_pip=True)
    bindir = env_dir / ("Scripts" if os.name == "nt" else "bin")
    py = str(bindir / ("python.exe" if os.name == "nt" else "python"))
    spec = a.spec
    if Path(spec).exists():
        spec = str(Path(spec).resolve())
    if a.mcp:
        spec = f"{spec}[mcp]" if not spec.endswith((".whl", ".tar.gz")) else f"hypgraph[mcp] @ {Path(spec).as_uri()}"
    print(f"installing {spec} into {env_dir}")
    pip = subprocess.run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", spec], capture_output=True, text=True)
    step("pip install", pip.returncode == 0, pip.stderr[-400:])
    if pip.returncode:
        return 1
    hg = str(bindir / ("hypgraph.exe" if os.name == "nt" else "hypgraph"))
    env = {k: v for k, v in os.environ.items() if not k.startswith("HYPGRAPH_")} | {"PYTHONIOENCODING": "utf-8"}

    def run(*args, who="ada", cwd=work):
        return subprocess.run([hg, "--db", str(work / "study.hypgraph"), "--as", who, *args] if args[0] != "verify" else [hg, *args],
                              cwd=cwd, capture_output=True, text=True, encoding="utf-8", env=env)

    def js(r):
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return {}

    v = subprocess.run([hg, "--version"], capture_output=True, text=True, env=env)
    step("hypgraph --version", v.returncode == 0, v.stderr)
    print(f"  version: {v.stdout.strip()}")
    where = subprocess.run([py, "-c", "import hypgraph, sys; print(hypgraph.__file__)"], capture_output=True, text=True, cwd=root)
    step("imported from the installed package, not a checkout", str(env_dir) in where.stdout, where.stdout.strip())

    r = run("init", "Cress under blue light", "--objective", "Does blue light grow cress faster than red light?",
            "--reviewers", "lin", "--json")
    inv = js(r).get("id", "")
    step("1. start a record and an investigation", r.returncode == 0 and inv.startswith("inv-"), r.stderr or r.stdout[-300:])
    r = run("add", "hypothesis", "statement=Blue light grows cress faster than red light.",
            'predictions=["blue trays taller after 7 days"]', "--inv", inv)
    step("2. a hypothesis", r.returncode == 0 and "H1" in r.stdout, r.stderr or r.stdout[-300:])
    r = run("add", "experiment", "aim=Compare cress height under blue and red light.",
            "protocol=20 trays per colour, same soil and water, measured with a ruler on day 7.",
            "success_criteria=Blue trays are taller on average.", "--inv", inv)
    step("3. an experiment", r.returncode == 0 and "X1" in r.stdout, r.stderr or r.stdout[-300:])
    r = run("link", "X1", "tests", "H1", "expected=blue trays taller", "--inv", inv)
    step("   that tests the hypothesis", r.returncode == 0, r.stderr or r.stdout[-300:])
    r = run("add", "run", "kind=agent", "name=ruler, day 7", "state=succeeded", "--inv", inv, "--link", "executes:to:X1")
    step("4. a run", r.returncode == 0 and "RUN1" in r.stdout, r.stderr or r.stdout[-300:])
    r = run("add", "result", "summary=Blue trays averaged 41 mm, red trays 33 mm, 20 trays each.", "outcome=positive",
            'values={"blue_mm": {"value": 41}, "red_mm": {"value": 33}}', "--inv", inv,
            "--link", "produced:from:RUN1", "--link", "supports:to:H1:The blue trays grew taller, as H1 predicts.")
    step("   and its result", r.returncode == 0 and "RS1" in r.stdout, r.stderr or r.stdout[-300:])
    r = run("add", "claim", "statement=Blue trays averaged 41 mm against 33 mm for red.",
            "scope=20 trays per colour, one 7-day run, one windowsill.", "kind=finding", "--inv", inv,
            "--link", "supports:from:RS1:the tray means")
    step("5. a claim the record accepts", r.returncode == 0 and "CL1" in r.stdout, r.stderr or r.stdout[-300:])
    r = run("add", "claim", "statement=Blue light always makes cress grow faster.",
            "scope=20 trays per colour, one 7-day run.", "kind=finding", "--inv", inv, "--link", "supports:from:RS1:the means")
    text = r.stdout + r.stderr
    step("6. a claim the record refuses", r.returncode != 0 and "refused" in text and "ABSOLUTE" in text, text[-300:])
    step("7. the refusal says what to fix", "[ABSOLUTE" in text and ("Honest version" in text or "k of n" in text or "count" in text),
         text[-300:])
    r = run("refusals", "--inv", inv)
    step("   and the refusal is logged", r.returncode == 0 and "always" in r.stdout, r.stderr or r.stdout[-300:])
    r = run("review", "CL1", "checked", "--method", "Re-measured four trays per colour with a second ruler.",
            "--notes", "Means within 1 mm of the reported ones.", "--inv", inv, who="lin")
    step("8. the reviewer's review", r.returncode == 0, r.stderr or r.stdout[-300:])
    r = run("show", "CL1", "--inv", inv)
    step("   counts on the claim", r.returncode == 0 and "checked" in r.stdout and "unchecked" not in r.stdout.split("·")[1],
         r.stdout[-300:])
    r = run("review", "RS1", "checked", "--method", "Read it again myself.", "--notes", "Looks right to me.", "--inv", inv)
    step("   and nobody's verdict on their own work counts", r.returncode == 0 and "unchecked" in r.stdout,
         (r.stdout + r.stderr)[-300:])
    bundle = work / "study.bundle.json"
    r = run("export", "-o", str(bundle))
    step("9. export a bundle", r.returncode == 0 and bundle.is_file(), r.stderr or r.stdout[-300:])
    shutil.copy(bundle, elsewhere / "study.bundle.json")
    first = run("verify", str(elsewhere / "study.bundle.json"), "--json", cwd=elsewhere)
    head = js(first).get("head", "")
    step("10. verify it elsewhere, with no graph file", first.returncode == 0 and len(head) == 64
         and not (elsewhere / "research.hypgraph").exists(), first.stdout[-300:] + first.stderr)
    r = run("verify", str(elsewhere / "study.bundle.json"), "--head", head, cwd=elsewhere)
    step("    and against its published head", r.returncode == 0 and "anchored" in r.stdout, r.stdout[-300:] + r.stderr)
    b = json.loads(bundle.read_text(encoding="utf-8"))
    for ver in b["versions"]:
        if "41 mm against 33 mm" in ver["body"]:
            ver["body"] = ver["body"].replace("41 mm against 33 mm", "51 mm against 33 mm")
    (elsewhere / "edited.bundle.json").write_text(json.dumps(b), encoding="utf-8")
    r = run("verify", str(elsewhere / "edited.bundle.json"), cwd=elsewhere)
    step("    an edited copy fails", r.returncode == 1 and "differs from its event" in r.stdout, r.stdout[-300:])

    if a.mcp:
        code = (
            "import asyncio, fastmcp\n"
            "from hypgraph.mcp import build\n"
            f"srv = build({str(work / 'study.hypgraph')!r}, author='claude')\n"
            "async def go():\n"
            "    async with fastmcp.Client(srv) as c:\n"
            "        names = {t.name for t in await c.list_tools()}\n"
            "        r = await c.call_tool('add', {'type': 'hypothesis', 'investigation': " + repr(inv) + ",\n"
            "            'fields': {'statement': 'Red light slows cress down.', 'predictions': ['red trays shorter']}})\n"
            "        print(len(names), 'H2' in r.content[0].text)\n"
            "asyncio.run(go())\n")
        r = subprocess.run([py, "-c", code], capture_output=True, text=True, cwd=root, env=env)
        step("MCP: list the tools and add a hypothesis", r.returncode == 0 and r.stdout.strip().endswith("True"),
             (r.stdout + r.stderr)[-400:])

    failed = [n for n, ok in STEPS if not ok]
    print(f"\n{len(STEPS) - len(failed)} of {len(STEPS)} steps did what the docs say.")
    if a.keep or failed:
        print(f"kept: {root}")
    else:
        shutil.rmtree(root, ignore_errors=True)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

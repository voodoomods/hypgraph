"""What the problem examples share: a record to file into, and a narrator that prints each step as it happens.

Every example scripts an agent's lines and files each one as a claim. Nothing is mocked on the record's side: a
refusal printed here is the engine's own, and each step states what it expects (refused with a given code, or
accepted), so the example fails loudly if the engine ever answers differently.
"""
from __future__ import annotations

import argparse
import sys
import textwrap

from hypgraph import Graph, __version__
from hypgraph import profiles as _profiles
from hypgraph.graph import GraphError

WIDTH = 96
STEP_HELP = "show one part at a time: press Enter for the next (for telling the story aloud, or recording it)"


class Steps:
    """``--step``: wait for Enter before each part, so a story can be told at speaking pace. Nothing else changes:
    the same lines are filed and the same lines are printed."""

    def __init__(self, on: bool):
        self.on = on

    def hint(self) -> None:
        if self.on:
            print("(--step: press Enter for each part)")

    def wait(self) -> bool:
        """Wait for Enter, if stepping. True when a terminal echoed that Enter, so the blank line a part starts
        with is already on screen. When there is nothing to read (piped, closed), stop waiting and run on."""
        if not self.on:
            return False
        sys.stdout.flush()
        if sys.stdin is None or not sys.stdin.readline():
            self.on = False
            return False
        return sys.stdin.isatty()


def missing(needs: list[str]) -> list[str]:
    """The profiles and claim policies in ``needs`` that the installed hypgraph doesn't have."""
    have = set(getattr(_profiles, "PROFILES", {})) | set(getattr(_profiles, "CLAIM_POLICIES", {}))
    return [n for n in needs if n.lower() not in have]


class Show:
    def __init__(self, title: str, problem: str, doc: str = "", needs: list[str] = ()):
        """``needs``: the profiles and claim policies the story pins. The examples on ``main`` can run ahead of the
        last release; on a hypgraph without one of them the story says so and stops before filing anything."""
        ap = argparse.ArgumentParser(description=doc or title, formatter_class=argparse.RawDescriptionHelpFormatter)
        ap.add_argument("--db", default="", help="keep the record in this file, to open with: hypgraph --db FILE serve")
        ap.add_argument("--step", action="store_true", help=STEP_HELP)
        self.args = ap.parse_args()
        for stream in (sys.stdout, sys.stderr):                      # ✓ and ✗ on a Windows console
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8", errors="replace")
        gone = missing(list(needs))
        if gone:
            sys.exit(f"{title}: this story needs {', '.join(gone)}, which hypgraph {__version__} doesn't have. "
                     "Upgrade with `pip install -U hypgraph`; if the newest release doesn't have "
                     f"{'it' if len(gone) == 1 else 'them'} yet, run the story from a clone of the repository, with "
                     "`pip install -e .` in its root.")
        self.steps = Steps(self.args.step)
        self.g = Graph(self.args.db or None)
        self.refused: list[tuple[str, list[str]]] = []
        self.accepted: list[str] = []
        print(f"\n{title}\n{'=' * len(title)}")
        print(textwrap.fill(problem, WIDTH))
        print(f"(hypgraph {__version__}; the agent's lines are scripted, the record's answers are not)")
        self.steps.hint()

    def part(self, heading: str) -> None:
        if not self.steps.wait():
            print()
        print(f"{heading}\n{'-' * len(heading)}")

    def note(self, who: str, text: str) -> None:
        print(textwrap.fill(text, WIDTH, initial_indent=f"{who:<13} ", subsequent_indent=" " * 14))

    def files(self, who: str, statement: str, add, expect: str, why: str = ""):
        """``who`` files ``statement`` through ``add()``. ``expect`` is "accepted" or the refusal code the engine
        must give. Prints what happened; raises if it isn't what the example says happens."""
        print(textwrap.fill(f"“{statement}”", WIDTH, initial_indent=f"{who:<13} ", subsequent_indent=" " * 14))
        try:
            node = add()
        except GraphError as e:
            codes = [p["code"] for p in e.problems]
            if expect == "accepted" or expect not in codes:
                raise AssertionError(f"expected {expect}, but the record refused it with {codes}: {e}") from e
            self.refused.append((statement, codes))
            print(f"{'':14}✗ REFUSED  {', '.join(codes)}")
            for p in e.problems:
                print(textwrap.fill(p["message"], WIDTH, initial_indent=" " * 16, subsequent_indent=" " * 16))
            return None
        if expect != "accepted":
            raise AssertionError(f"expected a {expect} refusal, but the record accepted: {statement}")
        self.accepted.append(statement)
        print(f"{'':14}✓ accepted as {node['code']}" + (f"  ({why})" if why else ""))
        return node

    def end(self, ok: str) -> None:
        self.part("What the record holds")
        print(f"{len(self.refused)} of the agent's lines refused, {len(self.accepted)} accepted. "
              f"Every refusal is in the record's log, with its author:")
        report = self.g.refusal_report()
        for who, row in report["by_author"].items():
            codes = ", ".join(f"{c} ×{n}" for c, n in row["codes"].items())
            print(f"  {who}: {row['refused']} refused, {row['fixed']} came back honest, {row['open']} left open  "
                  f"({codes})")
        for who, row in (report.get("conduct") or {}).items():
            print(textwrap.fill(row["sentence"], WIDTH, initial_indent=f"  {who}: ", subsequent_indent="    "))
        check = self.g.verify()
        print(f"Hash chain: {check['checked']} events, {'verified' if check['ok'] else 'BROKEN'}.")
        if self.args.db:
            print(f"\nKept in {self.args.db}. Open it:  hypgraph --db {self.args.db} serve")
        else:
            print("\nRun again with --db FILE to keep the record and open it in the UI.")
        print(f"\nOK: {ok}")

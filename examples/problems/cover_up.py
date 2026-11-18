"""
The agent that edits the log (any profile).

A rogue agent was refused twice for the same false claim, and the record says so. Now give it what a compromised
agent really has: write access to the record's file. It tries to erase its refusals and to reword the other party's
answer, more carefully each time.

The record is the disputed-answer demo (`hypgraph demo dispute`): Mallory's refusals are in the log. Before the
attack, the record's two chain heads are published, the way a release tag or a paper would carry them. Every attack
then runs on a fresh copy of the file.

    python cover_up.py [--db FILE]

What it shows, and what it doesn't: the record is tamper-evident, not tamper-proof. Clumsy edits are blocked or
caught by the file's own checks. A careful attacker who rewrites every hash leaves a file that checks out on its
own, and is caught only because the head was published first.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import textwrap
from pathlib import Path

from hypgraph import Graph, __version__
from hypgraph import refusals as R
from hypgraph import store as S
from hypgraph.bundle import anchored
from hypgraph.demos import dispute

ROGUE = "mallory"


def state(path: Path) -> dict:
    g = Graph(str(path))
    try:
        inv = g.investigations()[0]["id"]
        return {"events": g.verify(), "refusals": g.verify_refusals(), "conduct": g.conduct(inv)}
    finally:
        g.close()


def drop_triggers(con: sqlite3.Connection) -> None:
    for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall():
        con.execute(f"DROP TRIGGER {name}")


def delete_refusals(con: sqlite3.Connection) -> None:
    con.execute("DELETE FROM refusal_log WHERE author=?", (ROGUE,))


def rechain_refusals(con: sqlite3.Connection) -> None:
    cols = [d[0] for d in con.execute("SELECT * FROM refusal_log LIMIT 0").description]
    prev = S.GENESIS
    for row in con.execute("SELECT * FROM refusal_log ORDER BY id").fetchall():
        d = dict(zip(cols, row))
        d["prev"] = prev
        h = S.sha(R._body(d))
        con.execute("UPDATE refusal_log SET prev=?, hash=? WHERE id=?", (prev, h, d["id"]))
        prev = h


def reword(con: sqlite3.Connection, fix_event: bool = False) -> None:
    """Change the figure in the honest party's accepted answer."""
    node, v, body = con.execute("SELECT node, v, body FROM versions WHERE node IN (SELECT id FROM nodes WHERE "
                                "type='claim' AND by != ?) ORDER BY rowid LIMIT 1", (ROGUE,)).fetchone()
    b = json.loads(body)
    b["statement"] = re.sub(r"\d+", lambda m: str(int(m.group()) + 5), b["statement"], count=1)
    con.execute("UPDATE versions SET body=? WHERE node=? AND v=?", (S.canon(b), node, v))
    if fix_event:                                    # a careful attacker also rewrites the event's fingerprint
        seq, payload = con.execute("SELECT seq, payload FROM events WHERE kind='create' AND ref=?", (node,)).fetchone()
        p = json.loads(payload)
        p["body_sha"] = S.sha(S.canon(b))
        con.execute("UPDATE events SET payload=? WHERE seq=?", (S.canon(p), seq))


def rechain_events(con: sqlite3.Connection) -> None:
    prev = S.GENESIS
    for seq, at, actor, kind, ref, payload in con.execute(
            "SELECT seq, at, actor, kind, ref, payload FROM events ORDER BY seq").fetchall():
        h = S.sha(S.event_body(at, actor, kind, ref, json.loads(payload), prev))
        con.execute("UPDATE events SET prev=?, hash=? WHERE seq=?", (prev, h, seq))
        prev = h


ATTACKS = [
    ("Delete its own refusals with plain SQL",
     lambda con: delete_refusals(con), "blocked"),
    ("Drop the file's triggers, then reword the honest party's answer",
     lambda con: (drop_triggers(con), reword(con)), "caught by the file's own check"),
    ("Drop the triggers, then delete its own refusals",
     lambda con: (drop_triggers(con), delete_refusals(con)), "caught only by the published head"),
    ("... and recompute the refusal log's hash chain",
     lambda con: (drop_triggers(con), delete_refusals(con), rechain_refusals(con)),
     "caught only by the published head"),
    ("Reword the answer and recompute every event hash",
     lambda con: (drop_triggers(con), reword(con, fix_event=True), rechain_events(con)),
     "caught only by the published head"),
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default="", help="keep the untouched record in this file")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    title = "The agent that edits the log"
    print(f"\n{title}\n{'=' * len(title)}")
    print(textwrap.fill("A rogue agent was refused twice for the same false claim. It has write access to the "
                        "record's file and tries to clean it up.", 96))
    print(f"(hypgraph {__version__}; every attack runs on a fresh copy of the record)\n")
    with tempfile.TemporaryDirectory() as td:
        src = Path(args.db) if args.db else Path(td) / "dispute.hypgraph"
        g, _inv, _story = dispute.build(path=str(src))
        g.close()
        base = state(src)
        ev_head, rf_head = base["events"]["head"], base["refusals"]["head"]
        print(f"The record: {base['events']['checked']} events, and {base['refusals']['checked']} entries in its "
              f"refusal log.")
        print(textwrap.fill(base["conduct"][ROGUE]["sentence"], 96, initial_indent=f"  {ROGUE}: ",
                            subsequent_indent="    "))
        print(f"Published before the attack:  events head {ev_head[:16]}…   refusals head {rf_head[:16]}…\n")
        ok = True
        for i, (name, attack, expect) in enumerate(ATTACKS, 1):
            copy = Path(td) / f"copy-{i}.hypgraph"
            shutil.copy(src, copy)
            con = sqlite3.connect(copy)
            blocked = ""
            try:
                attack(con)
                con.commit()
            except sqlite3.DatabaseError as e:
                blocked = str(e)
                con.rollback()
            con.close()
            after = state(copy)
            ev, rf = after["events"], after["refusals"]
            internal = not (ev.get("ok") and rf.get("ok"))
            against_head = not ((anchored(ev, ev_head) if ev.get("ok") else ev).get("ok")
                                and (anchored(rf, rf_head) if rf.get("ok") else rf).get("ok"))
            outcome = ("blocked" if blocked else "caught by the file's own check" if internal else
                       "caught only by the published head" if against_head else "NOT CAUGHT")
            cleaned = after["conduct"].get(ROGUE, {}).get("sentence") != base["conduct"][ROGUE]["sentence"]
            print(f"{i}. {name}")
            if blocked:
                how = f"✗ {outcome}: the file refuses the write ({blocked})"
            elif internal:
                what = ev.get("problem") or f"the refusal log breaks at entry {rf.get('broken_at')}"
                how = f"✗ {outcome}: {what}"
            elif against_head:
                how = (f"✗ {outcome}: the file checks out on its own"
                       + (", and the rogue's conduct line is gone" if cleaned else "")
                       + ", but its chain no longer ends at the head that was published")
            else:
                how = f"! {outcome}"
            print(textwrap.fill(how, 96, initial_indent="     ", subsequent_indent="       "))
            ok = ok and outcome == expect
        if args.db:
            print(f"\nThe untouched record is in {args.db}. Open it:  hypgraph --db {args.db} serve")
    print("\nTamper-evident, not tamper-proof: three of the five are caught only because the head was\n"
          "published first. Publish it where the agent can't write: a release tag, a paper, a signed commit.")
    if not ok:
        raise SystemExit("an attack did not end the way this example says it does")
    print("\nOK: 1 attack blocked, 1 caught by the file's own check, 3 caught only by the published head.")


if __name__ == "__main__":
    main()

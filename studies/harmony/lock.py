#!/usr/bin/env python3
"""
Freeze the preregistration: write PREREG-LOCK.json with the sha256 of every file that defines the study, the git
commits of both repositories and the subject model. Commit the lock before the first confirmatory run; anything
changed after it is a deviation (DEVIATIONS.md).

    python studies/harmony/lock.py --model "deepinfra:deepseek-ai/DeepSeek-V4.1-Flash"
    python studies/harmony/lock.py --check            # do the files still match the lock (and its deviations)?
    python studies/harmony/lock.py --deviation D-1,D-2 --note "…"   # record approved changes beside the lock
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
HYP = HERE.parents[1]
POD = Path(os.environ.get("PEGASUS_REPO", HYP.parent / "Pegasus" / "pod"))
HS = Path(os.environ.get("HYPSWARM_REPO", HYP.parent / "HypSwarm"))
FILES = {
    "prereg": HERE / "PREREG.md", "analysis": HERE / "analysis.py", "suite/families": HERE / "suite" / "families.py",
    "suite/score": HERE / "suite" / "score.py", "suite/stats": HERE / "suite" / "stats.py",
    "hypgraph/coord": HYP / "src" / "hypgraph" / "coord.py", "hypgraph/schema": HYP / "src" / "hypgraph" / "schema.py",
    "hypgraph/src": HYP / "src" / "hypgraph",        # D-8: the whole engine, since the checks are part of condition C
    "runner": POD / "dev" / "study_runner.py", "host": POD / "dev" / "study_host.py",
    "runner_e": POD / "dev" / "study_e.py", "hypswarm/src": HS / "src" / "hypswarm",       # D-13: condition E
}
LOCK = HERE / "PREREG-LOCK.json"


def sha(p: Path) -> str:
    if p.is_dir():                                    # every .py under it, in a fixed order
        h = hashlib.sha256()
        for f in sorted(p.rglob("*.py")):
            h.update(f.relative_to(p).as_posix().encode() + b"\0" + f.read_bytes() + b"\0")
        return h.hexdigest()
    return hashlib.sha256(p.read_bytes()).hexdigest()


def git(repo: Path) -> str:
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout
    return out + ("+dirty" if dirty.strip() else "")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--deviation", default="", help="comma-separated ids from DEVIATIONS.md, approved by the operator")
    ap.add_argument("--note", default="")
    a = ap.parse_args(argv)
    now = {k: sha(p) for k, p in FILES.items()}
    if a.check:
        if not LOCK.exists():
            print("no lock yet")
            return 1
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        current = dict(lock["files"])
        for d in lock.get("deviations", []):
            current.update(d["files"])
        moved = [k for k, v in now.items() if current.get(k) != v]
        print("matches the lock" if not moved else "CHANGED since the lock: " + ", ".join(moved))
        return 1 if moved else 0
    if a.deviation:
        if not LOCK.exists():
            raise SystemExit("nothing is locked yet")
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        current = dict(lock["files"])
        for d in lock.get("deviations", []):
            current.update(d["files"])
        changed = {k: v for k, v in now.items() if current.get(k) != v}
        entry = {"at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "ids": [x.strip() for x in a.deviation.split(",") if x.strip()], "note": a.note,
                 "files": changed, "was": {k: current.get(k) for k in changed},
                 "git": {"hypgraph": git(HYP), "pegasus": git(POD)}}
        lock.setdefault("deviations", []).append(entry)
        LOCK.write_text(json.dumps(lock, indent=1), encoding="utf-8")
        print(f"recorded {', '.join(entry['ids'])}: {len(changed)} file(s) changed — {', '.join(changed) or 'none'}")
        return 0
    if not a.model:
        raise SystemExit("--model: the subject model, chosen by the operator")
    if LOCK.exists():
        raise SystemExit("already locked — changes after the lock go in DEVIATIONS.md")
    lock = {"locked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "subject_model": a.model,
            "files": now, "git": {"hypgraph": git(HYP), "pegasus": git(POD)}}
    if "+dirty" in lock["git"]["hypgraph"] or "+dirty" in lock["git"]["pegasus"]:
        print("warning: uncommitted changes — commit first so the lock points at real commits", file=sys.stderr)
    LOCK.write_text(json.dumps(lock, indent=1), encoding="utf-8")
    print(f"locked: {LOCK}\ncombined sha256 {hashlib.sha256(json.dumps(now, sort_keys=True).encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

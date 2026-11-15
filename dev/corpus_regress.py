"""
What a checker change does to real records, before it ships: snapshot every record under some folders with the engine
before the change and with it, then diff the two item by item.

    git worktree add ../hypgraph-main origin/main
    python dev/corpus_regress.py snapshot before.json ~/records --src ../hypgraph-main/src
    python dev/corpus_regress.py snapshot after.json  ~/records            # this checkout's src
    python dev/corpus_regress.py diff before.json after.json

A snapshot holds, for every record (`*.hypgraph`, `graph.db`) under the folders:
- N  the numbers `checks.numbers()` reads from every text it reads them from: claim statements and scopes, result
     summaries, source passages, logged refusal statements (keyed by a hash of the text, so shared texts count once);
- R  every logged refusal replayed through the checker (`Graph.replay_refusals`): verdict and codes now;
- C  every live claim re-checked as a revision would be (`claim_issues` + the profile's claim checks): codes;
- V  every live result re-checked (`value_issues` + the profile's result checks): codes.

The diff lists every item that moved, by direction: codes added (stricter: something new refused) and codes removed
(looser: something no longer refused). Read both lists; a change is judged by what moved, not by the totals. A rule
that fixes one statement and quietly refuses ten honest ones shows up here. Records are copied before they are
opened, never written. Snapshots hold statement text: keep them where the records are.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path


def _records(roots: list[str]):
    for root in roots:
        for f in sorted(Path(root).expanduser().rglob("*")):
            if (f.suffix == ".hypgraph" or f.name == "graph.db") and "node_modules" not in f.parts and f.is_file():
                yield f


def snapshot(out_path: str, roots: list[str], src: str) -> None:
    sys.path.insert(0, str(Path(src).resolve()))
    from hypgraph import Graph, __version__, profiles
    from hypgraph.checks import claim_issues, numbers, value_issues

    t0 = time.time()
    out = {"engine": __version__, "src": str(Path(src).resolve()), "records": 0,
           "N": {}, "R": {}, "C": {}, "V": {}, "errors": {}}
    tmp = Path(tempfile.mkdtemp())
    for f in _records(roots):
        try:
            con = sqlite3.connect(f"file:{f}?mode=ro", uri=True)
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            con.close()
        except sqlite3.Error:
            continue
        if "versions" not in tables:
            continue
        key = str(f)
        for x in tmp.iterdir():
            x.unlink()
        c = tmp / "g.hypgraph"
        try:
            shutil.copy(f, c)
            for ext in ("-wal", "-shm"):
                if Path(str(f) + ext).exists():
                    shutil.copy(str(f) + ext, str(c) + ext)
            g = Graph(str(c))
            s = g.snapshot()
        except Exception as e:  # noqa: BLE001
            out["errors"][key] = repr(e)[:200]
            continue
        out["records"] += 1
        try:
            con = sqlite3.connect(str(c))
            texts = []
            for (body,) in con.execute("SELECT body FROM versions"):
                try:
                    b = json.loads(body)
                except ValueError:
                    continue
                if isinstance(b, dict):
                    texts += [str(b[k]) for k in ("statement", "scope", "summary", "passage") if b.get(k)]
            if "refusal_log" in tables:
                texts += [st for (st,) in con.execute("SELECT statement FROM refusal_log") if st]
            con.close()
            for t in texts:
                h = hashlib.sha1(t.encode()).hexdigest()[:16]
                if h not in out["N"]:
                    out["N"][h] = [t[:300], [list(n) for n in numbers(t)]]
        except Exception as e:  # noqa: BLE001
            out["errors"][key + " N"] = repr(e)[:200]
        if "refusal_log" in tables:
            try:
                for x in g.replay_refusals()["rows"]:
                    out["R"][f"{key}#{x['id']}"] = [x["verdict"], sorted(x["now"]), x["statement"][:200]]
            except Exception as e:  # noqa: BLE001
                out["errors"][key + " R"] = repr(e)[:200]
        for nid, n in s.nodes.items():
            if n.get("type") not in ("claim", "result") or nid in s.withdrawn:
                continue
            body, inv = n.get("body") or {}, n.get("inv") or ""
            sec = "C" if n["type"] == "claim" else "V"
            try:
                if sec == "C":
                    sup = Graph._support_ids(s, nid, [])
                    now = [p.code for p in claim_issues(s, body, sup, inv)]
                    if inv in s.nodes:
                        now += [p.code for p in profiles.claim_issues(s, inv, body, sup, [])]
                    text = body.get("statement")
                else:
                    now = [p.code for p in value_issues(body)]
                    if inv in s.nodes:
                        now += [p.code for p in profiles.result_issues(s, inv, body, [],
                                                                        author=n.get("created_by") or "")]
                    text = body.get("summary")
            except Exception as e:  # noqa: BLE001
                now, text = [f"ERROR {type(e).__name__}"], body.get("statement") or body.get("summary")
            out[sec][f"{key}#{nid}"] = [sorted(set(now)), str(text or "")[:200]]
        try:
            g.close()
        except Exception:  # noqa: BLE001
            pass
    out["seconds"] = round(time.time() - t0)
    Path(out_path).write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"{out['records']} records with engine {out['engine']}: " + ", ".join(f"{k} {len(out[k])}" for k in "NRCV")
          + f"; errors {len(out['errors'])}; {out['seconds']} s -> {out_path}")


def diff(before: str, after: str, examples: int) -> int:
    a = json.loads(Path(before).read_text(encoding="utf-8"))
    b = json.loads(Path(after).read_text(encoding="utf-8"))
    print(f"engine {a.get('engine')} -> {b.get('engine')}; records {a['records']} -> {b['records']}; "
          f"errors {len(a['errors'])} -> {len(b['errors'])}")
    for k in sorted(set(a["errors"]) ^ set(b["errors"])):
        print("  error only", "after:" if k in b["errors"] else "before:", k, (a["errors"] | b["errors"])[k])
    moved_total = 0
    nd = [(a["N"][h], b["N"][h]) for h in a["N"] if h in b["N"] and a["N"][h][1] != b["N"][h][1]]
    print(f"\nN  numbers read: {len(a['N'])} texts, {len(nd)} read differently")
    pat = Counter()
    for x, y in nd:
        pat[(tuple(sorted(n[3] for n in x[1] if n not in y[1])), tuple(sorted(n[3] for n in y[1] if n not in x[1])))] += 1
    for (gone, new), c in pat.most_common(40):
        print(f"   {c:5d}  no longer read {ascii(list(gone))}  now read {ascii(list(new))}")
    for sec, label in (("R", "refusals replayed"), ("C", "live claims re-checked"), ("V", "live results re-checked")):
        def codes(v, sec=sec):
            return set(v[1] if sec == "R" else v[0])
        common = [k for k in a[sec] if k in b[sec]]
        stricter, looser, both = [], [], []
        for k in common:
            x, y = codes(a[sec][k]), codes(b[sec][k])
            if x == y and (sec != "R" or a[sec][k][0] == b[sec][k][0]):
                continue
            (stricter if not x - y else looser if not y - x else both).append((k, x, y))
        moved = len(stricter) + len(looser) + len(both)
        moved_total += moved
        print(f"\n{sec}  {label}: {len(common)} compared (only before {len(set(a[sec]) - set(b[sec]))}, only after "
              f"{len(set(b[sec]) - set(a[sec]))}); moved {moved}: stricter {len(stricter)}, looser {len(looser)}, "
              f"both {len(both)}")
        for name, rows in (("STRICTER (codes added)", stricter), ("LOOSER (codes removed)", looser),
                           ("BOTH", both)):
            if not rows:
                continue
            cc = Counter((tuple(sorted(y - x)), tuple(sorted(x - y))) for _, x, y in rows)
            print(f"  {name}: " + "; ".join(f"+{list(p)} -{list(m)} x{c}" for (p, m), c in cc.most_common()))
            for k, x, y in rows[:examples]:
                text = b[sec][k][2] if sec == "R" else b[sec][k][1]
                print(f"    - {ascii(text[:170])}\n        +{sorted(y - x)} -{sorted(x - y)} | {k[-80:]}")
    return 1 if moved_total else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("snapshot", help="check every record under the folders with one engine")
    sp.add_argument("out")
    sp.add_argument("roots", nargs="+")
    sp.add_argument("--src", default=str(Path(__file__).resolve().parents[1] / "src"),
                    help="the engine's src folder (default: this checkout's)")
    dp = sub.add_parser("diff", help="every item that moved between two snapshots; exit 1 if any did")
    dp.add_argument("before")
    dp.add_argument("after")
    dp.add_argument("--examples", type=int, default=40, help="items listed per direction and section")
    a = ap.parse_args()
    if a.cmd == "snapshot":
        snapshot(a.out, a.roots, a.src)
        return 0
    return diff(a.before, a.after, a.examples)


if __name__ == "__main__":
    sys.exit(main())

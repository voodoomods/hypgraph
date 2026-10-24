"""
hypgraph — the command line.

    hypgraph demo                       build the Broad Street (1854) teaching investigation into ./research.hypgraph
    hypgraph serve                      open the Atlas explorer on http://127.0.0.1:8765
    hypgraph init "Plant growth" --objective "…" --reviewers ada,lin
    hypgraph add hypothesis statement="Blue light grows cress faster." predictions='["taller after 7 days"]'
    hypgraph add result summary="Blue trays averaged 41 mm, red 33 mm." values='{"blue_mm": {"value": 41}}'
    hypgraph link RS1 supports H1 --why "The blue trays grew taller, as H1 predicts."
    hypgraph show CL1 --why             what it rests on        (--impact: what rests on it, --history: versions)
    hypgraph report                     the facts, generated from the record
    hypgraph export -o study.json       a bundle anyone can verify:  hypgraph verify study.json
    hypgraph mcp                        an MCP server for agents (pip install "hypgraph[mcp]")
    hypgraph skill --install            the agent skill, into .claude/skills/hypgraph/SKILL.md

The graph file is --db, else $HYPGRAPH_DB, else ./research.hypgraph. You write as --as, else $HYPGRAPH_AUTHOR, else
your login name. Nodes can be named by id or by code (H1, CL2, X3 …). Add --json to any command for machine output.
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path

from . import __version__
from .bundle import verify_bundle
from .graph import Graph, GraphError
from .schema import TYPES, describe
from .store import verify_file


def _out(args, data, text: str | None = None) -> None:
    if getattr(args, "json", False) or text is None:
        print(json.dumps(data, indent=1, ensure_ascii=False, default=str))
    else:
        print(text)


def _graph(args) -> Graph:
    return Graph(args.db)


def _author(args) -> str:
    who = args.author or os.getenv("HYPGRAPH_AUTHOR") or getpass.getuser()
    return who.strip().lower()


def _line(n: dict, width: int = 100) -> str:
    t = " ".join(str(n.get("title") or "").split())
    t = t if len(t) <= width else t[:width - 1] + "…"
    return f"{n['code'] or n['id']:<6} {n['type']:<12} {t}"


def _inv(g: Graph, ref: str = "") -> str:
    """The investigation: named, else the only active one."""
    if ref:
        return g.resolve(ref)
    invs = [i for i in g.investigations() if i["state"]["lifecycle"] == "active"] or g.investigations()
    if len(invs) == 1:
        return invs[0]["id"]
    if not invs:
        raise GraphError("no investigation yet — hypgraph init \"Title\" --objective \"…\"")
    raise GraphError("which investigation? --inv " + " | ".join(f"{i['code']} ({i['title'][:40]})" for i in invs))


def _fields(pairs: list[str]) -> dict:
    """key=value pairs; a value that parses as JSON (lists, objects, numbers) is taken as JSON."""
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise GraphError(f"{p!r}: give fields as key=value")
        k, v = p.split("=", 1)
        try:
            out[k.strip()] = json.loads(v) if v.strip()[:1] in "[{0123456789-tfn\"" else v
        except json.JSONDecodeError:
            out[k.strip()] = v
    return out


def _links(g: Graph, specs: list[str], inv: str) -> list[dict]:
    """--link rel:to:NODE[:why] (from the new node) or rel:from:NODE[:why] (into it)."""
    out = []
    for s in specs or []:
        parts = s.split(":", 3)
        if len(parts) < 3 or parts[1] not in ("to", "from"):
            raise GraphError(f"--link {s!r}: rel:to:NODE[:why] or rel:from:NODE[:why]")
        link = {"rel": parts[0], parts[1]: g.resolve(parts[2], inv)}
        if len(parts) > 3:
            link["why"] = parts[3]
        out.append(link)
    return out


def _show(n: dict) -> str:
    st = n.get("state") or {}
    out = [f"{n['code']} ({n['id']}) — {n['type']} v{n['v']} by {n['by']} {n['at'][:10]}",
           f"standing: {st.get('sentence', '')}"]
    for k, v in (n.get("body") or {}).items():
        if k != "legacy":
            out.append(f"  {k}: {v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)}")
    if n.get("withdrawn"):
        out.append(f"  WITHDRAWN by {n['withdrawn']['by']}: {n['withdrawn']['why']}")
    for e in n.get("out", []):
        out.append(f"  → {e['rel']} {e['dst']}" + (f"  ({e['why']})" if e.get("why") else ""))
    for e in n.get("in", []):
        out.append(f"  ← {e['rel']} {e['src']}" + (f"  ({e['why']})" if e.get("why") else ""))
    return "\n".join(out)


# ── commands ────────────────────────────────────────────────────────

def cmd_init(args) -> int:
    g = _graph(args)
    fields = {"title": args.title, "objective": args.objective, **_fields(args.fields)}
    if args.reviewers:
        fields["reviewers"] = [x.strip().lower() for x in args.reviewers.split(",") if x.strip()]
    n = g.create(author=_author(args), type="investigation", fields=fields)
    _out(args, n, f"{n['code']} ({n['id']}) in {g.path}\nNext: hypgraph add question text=\"…\"  ·  hypgraph add "
                  "hypothesis statement=\"…\" predictions='[\"…\"]'")
    return 0


def cmd_add(args) -> int:
    g = _graph(args)
    if args.type not in TYPES or args.type in ("review", "investigation"):
        raise GraphError(f"type: one of {', '.join(t for t in TYPES if t not in ('review', 'investigation'))} "
                         "(investigations: hypgraph init; reviews: hypgraph review)")
    inv = _inv(g, args.inv)
    n = g.create(author=_author(args), type=args.type, inv=inv, fields=_fields(args.fields),
                 links=_links(g, args.link, inv))
    notes = "".join(f"\n  note: {x}" for x in n.get("notes") or [])
    _out(args, n, f"Added {n['code']} — {n['state']['sentence']}{notes}")
    return 0


def cmd_link(args) -> int:
    g = _graph(args)
    inv = _inv(g, args.inv) if args.inv else ""
    r = g.link(author=_author(args), src=g.resolve(args.src, inv), rel=args.rel, dst=g.resolve(args.dst, inv),
               why=args.why or "", data=_fields(args.data))
    _out(args, r, f"Linked {args.src} -{args.rel}-> {args.dst} (edge {r['edge']})"
                  + (" — turned round to the direction the relation allows" if r["flipped"] else ""))
    return 0


def cmd_review(args) -> int:
    g = _graph(args)
    n = g.review(author=_author(args), target=g.resolve(args.node, args.inv or ""), verdict=args.verdict,
                 method=args.method, notes=args.notes)
    _out(args, n, f"{n['code']} — {n['state']['sentence']}")
    return 0


def cmd_revise(args) -> int:
    g = _graph(args)
    n = g.revise(author=_author(args), node=g.resolve(args.node, args.inv or ""), fields=_fields(args.fields),
                 reason=args.reason)
    _out(args, n, f"{n['code']} v{n['v']} — {n['state']['sentence']}")
    return 0


def cmd_withdraw(args) -> int:
    g = _graph(args)
    n = g.withdraw(author=_author(args), node=g.resolve(args.node, args.inv or ""), why=args.why)
    _out(args, n, f"{n['code']} — {n['state']['sentence']}")
    return 0


def cmd_ls(args) -> int:
    g = _graph(args)
    if args.type == "investigation" or (not args.inv and not args.type and not args.text and
                                        len(g.investigations()) != 1):
        rows = g.investigations()
        _out(args, rows, "\n".join(f"{r['code']:<6} {r['state']['lifecycle']:<9} "
                                   f"{sum(r['counts'].values()):>4} nodes  {r['title']}" for r in rows)
             or "No investigations yet — hypgraph init \"Title\" --objective \"…\" (or hypgraph demo)")
        return 0
    rows = g.search(text=args.text or "", type=args.type or "", inv=_inv(g, args.inv), limit=500)
    _out(args, rows, "\n".join(f"{_line(r)}\n       {r['state']['sentence']}" for r in rows) or "Nothing found.")
    return 0


def cmd_show(args) -> int:
    g = _graph(args)
    nid = g.resolve(args.node, args.inv or "")
    if args.why:
        r = g.why(nid)
        _out(args, r, f"WHY {args.node} — what it rests on:\n" + "\n".join(
            f"  {_line(n)}\n         {n['state']['sentence']}" for n in r["nodes"] if n["id"] != nid))
    elif args.impact:
        r = g.impact(nid)
        _out(args, r, f"IF {args.node} IS WRONG — {len(r['dependents'])} node(s) rest on it:\n" + "\n".join(
            f"  {'  ' * (d['depth'] - 1)}{d['rel']} ← {_line(d['node'])}" for d in r["dependents"]))
    else:
        n = g.get(nid, history=args.history)
        text = _show(n)
        if args.history:
            text += "\n  versions:\n" + "\n".join(f"    v{v['v']} {v['at'][:10]} {v['by']}: {v['reason'] or '(created)'}"
                                                  for v in n.get("versions", []))
        _out(args, n, text)
    return 0


def cmd_next(args) -> int:
    g = _graph(args)
    r = g.next_experiments(_inv(g, args.inv))
    lines = [f"Next experiments ({r['rule']}):"]
    lines += [f"  {x['experiment']['code']:<5} score {x['score']:<6} separates {x['separates']}"
              f"{', power check' if x['power_check'] else ''}{', DUPLICATE' if x['duplicate'] else ''} — "
              f"{x['experiment']['title'][:80]}" for x in r["ranked"]] or ["  (none planned)"]
    if r["untested_hypotheses"]:
        lines.append("Untested hypotheses: " + ", ".join(h["code"] for h in r["untested_hypotheses"]))
    _out(args, r, "\n".join(lines))
    return 0


def cmd_work(args) -> int:
    g = _graph(args)
    w = g.work_map(_inv(g, args.inv))
    sec = lambda name, rows: f"{name} ({len(rows)}): " + (", ".join(x["code"] for x in rows) or "—")  # noqa: E731
    _out(args, w, "\n".join([
        "Being worked: " + (", ".join(f"{L['agent']} → {L['node']['code']}" for L in w["leases"]) or "—"),
        sec("Review queue", w["review_queue"]), sec("Needs revalidation", w["revalidation"]),
        sec("Contested", w["contested"]), sec("Decisions to revisit", w["decisions_to_revisit"]),
        f"Duplicate experiment groups: {len(w['duplicates'])}"]))
    return 0


def cmd_report(args) -> int:
    g = _graph(args)
    r = g.report(_inv(g, args.inv))
    if args.output:
        Path(args.output).write_text(r["markdown"] + "\n\n## Interpretation\n\n", encoding="utf-8")
        print(f"Wrote the facts to {args.output}; write your interpretation under them.")
        return 0
    _out(args, r, r["markdown"])
    return 0


def cmd_verify(args) -> int:
    target = args.target or args.db
    if str(target).endswith(".json"):
        res = verify_bundle(json.loads(Path(target).read_text(encoding="utf-8")))
    else:
        res = verify_file(target)
    ok = res.get("ok")
    text = (f"✓ {target}: {res.get('checked')} events verified — chain intact, every row matches the event that "
            f"wrote it. Head {str(res.get('head', ''))[:16]}…" if ok else f"✗ {target}: {res.get('problem')}")
    if res.get("warning"):
        text += "\n  note: " + res["warning"]
    _out(args, res, text)
    return 0 if ok else 1


def cmd_export(args) -> int:
    g = _graph(args)
    inv = g.resolve(args.inv) if args.inv else ""
    b = g.export(inv)
    data = json.dumps(b, ensure_ascii=False, separators=(",", ":") if args.compact else None,
                      indent=None if args.compact else 1)
    if args.output:
        Path(args.output).write_text(data, encoding="utf-8")
        print(f"Wrote {args.output}: {len(b['events'])} events, {len(b['nodes'])} nodes"
              + ("" if b["complete"] else f" ({b['redacted_events']} events outside the investigation redacted)"))
    else:
        print(data)
    return 0


def cmd_import(args) -> int:
    b = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
    if Path(args.db).exists():
        raise GraphError(f"{args.db} exists — import into a new file (--db new.hypgraph)")
    g = Graph.from_bundle(b, args.db)
    print(f"Imported into {g.path}: {g.verify()['checked']} events, verified.")
    return 0


def cmd_demo(args) -> int:
    from .demos import broad_street
    if Path(args.db).exists():
        raise GraphError(f"{args.db} exists — choose another file: hypgraph demo --db broad-street.hypgraph")
    g, inv, story = broad_street.build(path=args.db)
    if args.json:
        _out(args, {"db": g.path, "inv": inv, "story": story})
        return 0
    for s in story:
        print(f"{s['at']}  {s['actor']:<10} {s['text']}")
        if "refused" in s:
            print("            ✗ the record refused it:\n              " +
                  s["refused"].replace("\n", "\n              "))
    print(f"\nBuilt {broad_street.TITLE!r} into {g.path}.\nExplore it:  hypgraph --db {args.db} serve"
          f"   ·   hypgraph --db {args.db} report")
    return 0


def cmd_schema(args) -> int:
    d = describe()
    if args.json:
        _out(args, d)
        return 0
    lines = [f"{d['format']} — node types:"]
    lines += [f"  {t:<13} {v['prefix']:<4} {v['about']}" for t, v in d["types"].items()]
    lines += ["", "relations:"] + [f"  {r:<14} {v['about']}" for r, v in d["relations"].items()]
    print("\n".join(lines))
    return 0


def skill_text() -> str:
    return (Path(__file__).parent / "skill" / "SKILL.md").read_text(encoding="utf-8")


def cmd_skill(args) -> int:
    """Print the agent skill, or install it where Claude Code (and other Agent Skills hosts) look for skills."""
    if not args.install:
        print(skill_text())
        return 0
    base = Path.home() if args.user else Path(args.dir or ".")
    dest = base / ".claude" / "skills" / "hypgraph" / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(skill_text(), encoding="utf-8")
    print(f"Installed the hypgraph skill at {dest}")
    return 0


def cmd_serve(args) -> int:
    from .server import serve
    serve(args.db, host=args.host, port=args.port, writable=args.writable, open_browser=not args.no_browser)
    return 0


def cmd_mcp(args) -> int:
    from .mcp import run
    run(args.db, author=_author(args) if args.author else None, transport=args.transport, port=args.port)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="hypgraph", description="Don't believe the hype. Test the hyp.",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n")[1])
    p.add_argument("--db", default=os.getenv("HYPGRAPH_DB", "research.hypgraph"), help="the graph file")
    p.add_argument("--as", dest="author", default="", help="who you are writing as")
    p.add_argument("--json", action="store_true", help="machine-readable output")
    p.add_argument("--version", action="version", version=f"hypgraph {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="command")

    def cmd(name, fn, help, **kw):
        s = sub.add_parser(name, help=help, **kw)
        s.set_defaults(fn=fn)
        s.add_argument("--json", action="store_true", default=argparse.SUPPRESS)
        return s

    s = cmd("init", cmd_init, "start an investigation")
    s.add_argument("title")
    s.add_argument("--objective", required=True, help="what you want to find out, in a sentence")
    s.add_argument("--reviewers", default="", help="comma-separated: whose verdicts count")
    s.add_argument("fields", nargs="*", help="more fields as key=value (scope=…, success_criteria=…)")
    s = cmd("add", cmd_add, "add a question, hypothesis, experiment, run, result, claim, source, decision …")
    s.add_argument("type")
    s.add_argument("fields", nargs="*", help="key=value; JSON values for lists and objects")
    s.add_argument("--inv", default="")
    s.add_argument("--link", action="append", help="rel:to:NODE[:why] or rel:from:NODE[:why]; repeatable")
    s = cmd("link", cmd_link, "link two nodes")
    s.add_argument("src"), s.add_argument("rel"), s.add_argument("dst")
    s.add_argument("--why", default="")
    s.add_argument("--inv", default="")
    s.add_argument("data", nargs="*", help="key=value edge data (expected=…, differs=…, role=…)")
    s = cmd("review", cmd_review, "review a node's current version")
    s.add_argument("node"), s.add_argument("verdict")
    s.add_argument("--method", required=True, help="how you checked")
    s.add_argument("--notes", required=True, help="what you found")
    s.add_argument("--inv", default="")
    s = cmd("revise", cmd_revise, "add a new version of a node")
    s.add_argument("node")
    s.add_argument("fields", nargs="*")
    s.add_argument("--reason", required=True)
    s.add_argument("--inv", default="")
    s = cmd("withdraw", cmd_withdraw, "withdraw a node (it stays on record)")
    s.add_argument("node")
    s.add_argument("--why", required=True)
    s.add_argument("--inv", default="")
    s = cmd("ls", cmd_ls, "list investigations, or the nodes of one")
    s.add_argument("text", nargs="?", default="")
    s.add_argument("--type", default="")
    s.add_argument("--inv", default="")
    s = cmd("show", cmd_show, "one node, its standing and links")
    s.add_argument("node")
    s.add_argument("--why", action="store_true", help="what it rests on")
    s.add_argument("--impact", action="store_true", help="what rests on it")
    s.add_argument("--history", action="store_true", help="its versions")
    s.add_argument("--inv", default="")
    for name, fn, h in (("next", cmd_next, "experiments ranked by how well they separate hypotheses"),
                        ("work", cmd_work, "review queue, revalidation, contested, decisions to revisit")):
        cmd(name, fn, h).add_argument("--inv", default="")
    s = cmd("report", cmd_report, "the facts of an investigation, generated from the record")
    s.add_argument("--inv", default="")
    s.add_argument("-o", "--output", default="")
    s = cmd("verify", cmd_verify, "check a graph file or a bundle")
    s.add_argument("target", nargs="?", default="")
    s = cmd("export", cmd_export, "write a verifiable bundle")
    s.add_argument("--inv", default="", help="one investigation (events outside it are redacted)")
    s.add_argument("-o", "--output", default="")
    s.add_argument("--compact", action="store_true")
    s = cmd("import", cmd_import, "rebuild a graph file from a complete bundle")
    s.add_argument("bundle")
    cmd("demo", cmd_demo, "build the Broad Street (1854) teaching investigation")
    cmd("schema", cmd_schema, "the node types and relations")
    s = cmd("skill", cmd_skill, "print the agent skill (SKILL.md), or --install it for Claude Code")
    s.add_argument("--install", action="store_true", help="write .claude/skills/hypgraph/SKILL.md")
    s.add_argument("--user", action="store_true", help="install under your home directory instead of this project")
    s.add_argument("--dir", default="", help="project directory to install into (default: here)")
    s = cmd("serve", cmd_serve, "the Atlas explorer and JSON API on localhost")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--writable", action="store_true", help="also accept writes (POST /api/graph/write)")
    s.add_argument("--no-browser", action="store_true")
    s = cmd("mcp", cmd_mcp, "an MCP server for agents (needs hypgraph[mcp])")
    s.add_argument("--transport", default="stdio", choices=["stdio", "http"])
    s.add_argument("--port", type=int, default=8766)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")   # Windows consoles default to cp1252
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except GraphError as e:
        print(f"refused: {e}", file=sys.stderr)
        return 2
    except KeyError as e:
        print(f"not found: {e.args[0] if e.args else e}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())

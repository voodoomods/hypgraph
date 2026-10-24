"""
``hypgraph mcp`` — the research graph as an MCP server, for agents (needs ``pip install "hypgraph[mcp]"``).

    claude mcp add hypgraph -- hypgraph --db study.hypgraph --as claude mcp

The server writes as ONE author, fixed when it starts (``--as``, else $HYPGRAPH_AUTHOR, else "agent"): an agent can't
pass someone else's name, can't write as the instrument or the operator, and — unless the investigation lists it as
a reviewer — its verdicts are comments. Claims it writes are checked like anyone's: every number bound to a result,
no absolutes without k of n, exclusions need a powered search. A refusal comes back as a tool error that says what to
fix, which is the point.

Tools: overview · find · show · start_investigation · add · link · revise · withdraw · retract_link · review ·
next_experiments · work_queue · claim_work · register_run · report · verify · schema.
Resources: hypgraph://skill · hypgraph://schema · hypgraph://investigations · hypgraph://investigation/{inv}/report.
Prompt: method — how to work a question through the record.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from . import __version__
from .graph import Graph, GraphError, file_sha256
from .schema import TYPES, describe

INSTRUCTIONS = """HypGraph is a research record that can't flatter itself. Work a question through it:
1. overview() — read what is already known before re-deriving anything.
2. add hypotheses with predictions; add experiments with `tests` links whose data.expected says what each hypothesis
   predicts BEFORE you run anything (that is what makes it a test).
3. register_run() for computations you ran (it hashes the files); add results with values {name: {value} | {k, n}}.
4. add a claim only with its evidence: a `supports` link from a result (with why), a scope, and every number in the
   statement bound to a result field in `measurements`. Absolutes ("never", "all") need k of n with k = 0 or n.
   An exclusion needs a search shown to recover a planted answer (result power=demonstrated).
5. You can't set standing. Reviews by the investigation's reviewers do; nobody reviews their own work.
When the record refuses a write, it says what to fix — fix that, don't route around it."""


def _line(n: dict, width: int = 110) -> str:
    t = " ".join(str(n.get("title") or "").split())
    t = t if len(t) <= width else t[:width - 1] + "…"
    return f"{n['code'] or n['id']} [{n['type']}] {t}"


def overview_text(g: Graph, inv: str, reviewer: str = "", limit: int = 3200) -> str:
    """The record around an investigation in ~3,000 characters: objective, live hypotheses, what's established and
    how, what's shaky, who's on what, reviews waiting, next experiments."""
    s_inv = g.get(inv)
    b = s_inv["body"]
    sub = g.subgraph(inv, types=["hypothesis", "claim"])
    work, nxt = g.work_map(inv), g.next_experiments(inv, 4)
    state = b.get("state") or "active"
    L = [f"## {b.get('title', inv)} ({s_inv['code']}, {inv}, {state})",
         f"Objective: {' '.join(str(b.get('objective', '')).split())[:300]}"]
    if b.get("reviewers"):
        L.append("Reviewers (their verdicts count): " + ", ".join(b["reviewers"]))
    if state != "active":
        L.append(f"This investigation is {state}: its record is fixed. Review it, and build on it in a follow-up.")
    nodes = sub["nodes"]
    live = lambda n: n["state"].get("lifecycle") == "active"  # noqa: E731
    hyps = [n for n in nodes if n["type"] == "hypothesis" and live(n) and not n["state"].get("fallen")]
    if hyps:
        L.append(f"Live hypotheses ({len(hyps)}):")
        L += [f"  {_line(n)} — {n['state']['sentence'][:150]}" for n in hyps[:6]]
    claims = [n for n in nodes if n["type"] == "claim" and live(n)]
    checked = [n for n in claims if n["state"].get("review", {}).get("state") == "checked"]
    if checked:
        L.append(f"Established — checked claims ({len(checked)}):")
        L += [f"  {_line(n, 120)} — {(n['state'].get('evidence') or '').replace('_', ' ')}, "
              f"{n['state'].get('independent_lines', 0)} line(s)" for n in checked[:8]]
    open_claims = [n for n in claims if n not in checked]
    if open_claims:
        L.append("Other live claims: " + "; ".join(f"{n['code']} ({n['state']['review']['state']})"
                                                   for n in open_claims[:12]))
    shaky = [n for n in claims if n["state"].get("review", {}).get("state") == "contested" or n["state"].get("at_risk")]
    if shaky:
        L.append("Contested or AT RISK — don't cite without checking: " + ", ".join(n["code"] for n in shaky[:20]))
    if work["leases"]:
        L.append("Being worked: " + "; ".join(f"{x['agent']} → {x['node']['code']}" for x in work["leases"][:8]))
    if reviewer and reviewer in set(b.get("reviewers") or []) | set(g.policy.reviewers) and work["review_queue"]:
        L.append(f"Reviews waiting for you ({len(work['review_queue'])}): "
                 + ", ".join(n["code"] for n in work["review_queue"][:10]))
    if work["revalidation"]:
        L.append("Needs revalidation (something it rests on moved): "
                 + ", ".join(n["code"] for n in work["revalidation"][:10]))
    if work["decisions_to_revisit"]:
        L.append("Decisions to revisit (their basis changed): "
                 + ", ".join(n["code"] for n in work["decisions_to_revisit"][:10]))
    if nxt["ranked"] and state == "active":
        L.append("Next experiments: " + "; ".join(
            f"{r['experiment']['code']} (separates {r['separates']}{', powered' if r['power_check'] else ''}"
            f"{', DUPLICATE' if r['duplicate'] else ''})" for r in nxt["ranked"][:4]))
    if nxt["untested_hypotheses"] and state == "active":
        L.append("Hypotheses no experiment tests yet: " + ", ".join(h["code"] for h in nxt["untested_hypotheses"]))
    text = "\n".join(L)
    return text if len(text) <= limit else text[:limit - 30] + "\n  … (find / show for more)"


def show_text(n: dict) -> str:
    st = n.get("state") or {}
    out = [f"{n['code']} ({n['id']}) — {n['type']} v{n['v']} by {n['by']} {n['at'][:10]}",
           f"standing: {st.get('sentence', '')}"]
    for k, v in (n.get("body") or {}).items():
        if k != "legacy":
            out.append(f"  {k}: {v[:700] if isinstance(v, str) else json.dumps(v, ensure_ascii=False)[:700]}")
    if n.get("withdrawn"):
        out.append(f"  WITHDRAWN by {n['withdrawn']['by']}: {n['withdrawn']['why']}")
    outs = [f"    this -{e['rel']}-> {e['dst']}" + (f" ({e['why'][:90]})" if e.get("why") else "")
            for e in n.get("out", [])]
    ins = [f"    {e['src']} -{e['rel']}-> this" + (f" ({e['why'][:90]})" if e.get("why") else "")
           for e in n.get("in", [])]
    if outs:
        out += ["  links out:"] + outs[:25]
    if ins:
        out += ["  links in:"] + ins[:25]
    return "\n".join(out)


def build(graph: Graph | str, author: Optional[str] = None, files_root: str | None = None):
    """The FastMCP server over one graph, writing as one author."""
    try:
        from fastmcp import FastMCP
        from fastmcp.exceptions import ToolError
    except ImportError as e:  # pragma: no cover
        raise SystemExit('the MCP server needs FastMCP: pip install "hypgraph[mcp]"') from e
    g = graph if isinstance(graph, Graph) else Graph(graph)
    me = (author or os.getenv("HYPGRAPH_AUTHOR") or "agent").strip().lower()[:40]
    if me in g.policy.reserved:
        raise SystemExit(f"{me!r} is a reserved author ({', '.join(sorted(g.policy.reserved))}); pick another --as")
    root = Path(files_root or os.getcwd()).resolve()
    mcp = FastMCP("hypgraph", instructions=INSTRUCTIONS + f"\nYou write as {me!r}.", version=__version__,
                  website_url="https://hypgraph.com")

    def fail(e: Exception):
        raise ToolError(str(e) if not isinstance(e, KeyError) else f"not found: {e.args[0] if e.args else e}")

    def inv_of(ref: str) -> str:
        if ref:
            return g.resolve(ref)
        invs = [i for i in g.investigations() if i["state"]["lifecycle"] == "active"] or g.investigations()
        if len(invs) == 1:
            return invs[0]["id"]
        if not invs:
            raise GraphError("no investigation yet — start_investigation(title, objective)")
        raise GraphError("which investigation? " + "; ".join(f"{i['code']} {i['id']} — {i['title'][:50]}" for i in invs))

    def resolve_links(links: list[dict] | None, inv: str) -> list[dict]:
        out = []
        for raw in links or []:
            ln = dict(raw)
            for k in ("to", "from"):
                if ln.get(k):
                    ln[k] = g.resolve(str(ln[k]), inv)
            out.append(ln)
        return out

    @mcp.tool
    def overview(investigation: str = "") -> str:
        """Read this first. The record around an investigation: objective, reviewers, live hypotheses, established
        claims (and how they're known), contested and at-risk work, who's on what, reviews and revalidations
        waiting, next experiments. With several investigations and none named, lists them."""
        try:
            if not investigation:
                invs = g.investigations()
                if len(invs) != 1:
                    return "\n".join(f"{i['code']} {i['id']} — {i['title']} ({i['state']['lifecycle']}, "
                                     f"{sum(i['counts'].values())} nodes)" for i in invs) or \
                        "No investigations yet — start_investigation(title, objective, reviewers)."
            return overview_text(g, inv_of(investigation), reviewer=me)
        except (GraphError, KeyError) as e:
            fail(e)

    @mcp.tool
    def find(text: str = "", type: str = "", investigation: str = "", limit: int = 20) -> str:
        """Search the record by words or code (H1, CL3 …). type filters: investigation, question, hypothesis, claim,
        experiment, run, result, artifact, source, review, decision, task."""
        try:
            rows = g.search(text=text, type=type, inv=g.resolve(investigation) if investigation else "",
                            limit=max(1, min(int(limit), 100)))
        except (GraphError, KeyError) as e:
            fail(e)
        return "\n".join(f"{_line(n)} · {n['id']} · {n['state']['sentence'][:150]}" for n in rows) or "Nothing found."

    @mcp.tool
    def show(node: str, view: str = "summary", investigation: str = "") -> str:
        """One node by id or code. view: summary (fields, standing, links) | why (what it rests on, down to runs, data
        and sources) | impact (what rests on it — what breaks if it's wrong) | history (its versions)."""
        try:
            nid = g.resolve(node, g.resolve(investigation) if investigation else "")
            if view == "why":
                r = g.why(nid)
                return f"WHY {node} — what it rests on:\n" + "\n".join(
                    f"  {_line(n)} — {n['state']['sentence'][:150]}" for n in r["nodes"] if n["id"] != nid) \
                    + "\n  edges:\n" + "\n".join(f"    {e['src']} -{e['rel']}-> {e['dst']}" for e in r["edges"][:60])
            if view == "impact":
                r = g.impact(nid)
                return (f"IF {node} IS WRONG — {len(r['dependents'])} node(s) rest on it:\n" + "\n".join(
                    f"  {'  ' * (d['depth'] - 1)}{d['rel']} ← {_line(d['node'])}" for d in r["dependents"][:40])) \
                    if r["dependents"] else f"Nothing rests on {node}."
            if view == "history":
                n = g.get(nid, history=True)
                return show_text(n) + "\n  versions:\n" + "\n".join(
                    f"    v{v['v']} {v['at'][:10]} {v['by']}: {v['reason'] or '(created)'}" for v in n["versions"])
            return show_text(g.get(nid))
        except (GraphError, KeyError) as e:
            fail(e)

    @mcp.tool
    def start_investigation(title: str, objective: str, reviewers: list[str] | None = None, scope: str = "",
                            success_criteria: str = "") -> str:
        """Open an investigation: what you want to find out (objective, a sentence), its scope, what would count as
        an answer, and who reviews it (their verdicts set the standing; you can't review your own work)."""
        try:
            n = g.create(author=me, type="investigation", fields={
                "title": title, "objective": objective, "scope": scope, "success_criteria": success_criteria,
                "reviewers": [r.strip().lower() for r in reviewers or [] if r.strip()]})
        except GraphError as e:
            fail(e)
        return f"Opened {n['code']} ({n['id']}). Next: add questions and hypotheses (with predictions)."

    @mcp.tool
    def add(type: str, fields: dict[str, Any], investigation: str = "", links: list[dict[str, Any]] | None = None) -> str:
        """Add a node. type: question {text} · hypothesis {statement, predictions[]} · experiment {aim, protocol,
        success_criteria, controls, method, power_check, cost_minutes} with `tests` links carrying data.expected per
        hypothesis · run {kind: agent, name, state} (prefer register_run) · result {summary, values {name: {value} |
        {k, n}}, outcome, power} · claim {statement, scope, kind finding|exclusion|inconclusive|convention|lead,
        measurements [{name, value | k, n, result: <id>, key: <values field>}]} with a `supports` link from its
        result · source {citation, doi, url, passage} · decision {choice, reasons, alternatives} with `based_on`.
        links: [{"rel": …, "to": id-or-code} (from this node) or {"rel": …, "from": id-or-code, "why": "a sentence"}
        (into it), optional "data": {...}]."""
        try:
            if type not in TYPES or type in ("investigation", "review"):
                raise GraphError("type: " + ", ".join(t for t in TYPES if t not in ("investigation", "review"))
                                 + " (start_investigation / review for the others)")
            inv = inv_of(investigation)
            n = g.create(author=me, type=type, fields=fields, inv=inv, links=resolve_links(links, inv))
        except (GraphError, KeyError) as e:
            fail(e)
        notes = "".join(f" Note: {x}." for x in n.get("notes") or [])
        return f"Added {n['code']} ({n['id']}) — {n['state']['sentence']}.{notes}"

    @mcp.tool
    def link(src: str, rel: str, dst: str, why: str = "", data: dict[str, Any] | None = None,
             investigation: str = "") -> str:
        """Connect two nodes. rel: supports | challenges (why required) | requires | tests (data.expected) | executes
        | produced | uses (data.role) | derived_from | replicates (data.differs: same_code | new_seed | new_impl |
        new_data | new_env) | supersedes | corrects | answers | part_of | alternative_to | motivated_by | cites |
        based_on. A link given backwards is turned round when only the reverse is allowed."""
        try:
            inv = g.resolve(investigation) if investigation else ""
            r = g.link(author=me, src=g.resolve(src, inv), rel=rel.strip().lower(), dst=g.resolve(dst, inv), why=why,
                       data=data or {})
        except (GraphError, KeyError) as e:
            fail(e)
        return f"Linked {r['src']} -{r['rel']}-> {r['dst']} (edge {r['edge']})" + \
            (" — turned round to the direction the relation allows." if r["flipped"] else ".")

    @mcp.tool
    def revise(node: str, fields: dict[str, Any], reason: str, investigation: str = "") -> str:
        """A new version of a node you wrote (or review): the given fields replace the old ones. Reviews of the old
        version stay on record but go stale; decisions based on it are flagged to revisit."""
        try:
            n = g.revise(author=me, node=g.resolve(node, g.resolve(investigation) if investigation else ""),
                         fields=fields, reason=reason)
        except (GraphError, KeyError) as e:
            fail(e)
        return f"{n['code']} is now v{n['v']} — {n['state']['sentence']}"

    @mcp.tool
    def withdraw(node: str, why: str, investigation: str = "") -> str:
        """Withdraw a node you wrote. It stays on record, marked withdrawn; whatever rested on it is flagged AT RISK."""
        try:
            n = g.withdraw(author=me, node=g.resolve(node, g.resolve(investigation) if investigation else ""), why=why)
        except (GraphError, KeyError) as e:
            fail(e)
        return f"{n['code']} — {n['state']['sentence']}"

    @mcp.tool
    def retract_link(edge: int, why: str) -> str:
        """Retract a link you made (by edge id), saying why it no longer holds. The retraction is on record."""
        try:
            g.retract(author=me, edge=int(edge), why=why)
        except GraphError as e:
            fail(e)
        return f"Retracted edge {edge}."

    @mcp.tool
    def review(node: str, verdict: str, method: str, notes: str, investigation: str = "") -> str:
        """Review a node's current version: checked | pass | reproduced | replicated | separate_implementation |
        generalizes | fail | not_reproduced | not_replicated | does_not_generalize | objection | resolved |
        inconclusive | comment. Say how you checked (method) and what you found (notes). Only the investigation's
        reviewers' verdicts count; anyone else's are kept as comments. Not your own work."""
        try:
            n = g.review(author=me, target=g.resolve(node, g.resolve(investigation) if investigation else ""),
                         verdict=verdict.strip().lower(), method=method, notes=notes)
        except (GraphError, KeyError) as e:
            fail(e)
        return f"Recorded on {n['code']}: {n['state']['sentence']}"

    @mcp.tool
    def next_experiments(investigation: str = "") -> str:
        """Planned experiments ranked by how well they separate the live hypotheses (distinct expected outcomes),
        whether they can show their own power, and cost; duplicates and work someone holds flagged; untested
        hypotheses listed."""
        try:
            r = g.next_experiments(inv_of(investigation))
        except (GraphError, KeyError) as e:
            fail(e)
        out = [f"Next experiments ({r['rule']}):"]
        out += [f"  {x['experiment']['code']} score {x['score']} — separates {x['separates']}, "
                f"{'power check' if x['power_check'] else 'no power check'}, ~{int(x['cost_minutes'])} min"
                + (" — DUPLICATE" if x["duplicate"] else "") + (f" — {x['lease']['agent']} on it" if x["lease"] else "")
                + f": {x['experiment']['title'][:100]}" for x in r["ranked"]] or ["  (none planned)"]
        if r["untested_hypotheses"]:
            out.append("Untested hypotheses: " + ", ".join(_line(h, 80) for h in r["untested_hypotheses"]))
        return "\n".join(out)

    @mcp.tool
    def work_queue(investigation: str = "") -> str:
        """What needs doing: leases (who's on what), the review queue, revalidations (something a node rests on
        moved), contested work, decisions to revisit, duplicate experiments."""
        try:
            w = g.work_map(inv_of(investigation))
        except (GraphError, KeyError) as e:
            fail(e)
        sec = lambda name, rows: f"{name} ({len(rows)}): " + (", ".join(  # noqa: E731
            f"{x['code']} {x['title'][:50]}" for x in rows[:12]) or "—")
        return "\n".join(["Being worked: " + (", ".join(f"{x['agent']} → {x['node']['code']}" for x in w["leases"])
                                              or "—"),
                          sec("Review queue", w["review_queue"]), sec("Needs revalidation", w["revalidation"]),
                          sec("Contested", w["contested"]), sec("Decisions to revisit", w["decisions_to_revisit"]),
                          f"Duplicate experiment groups: {len(w['duplicates'])}"])

    @mcp.tool
    def claim_work(node: str, release: bool = False, minutes: int = 240, investigation: str = "") -> str:
        """Take a node (an experiment to run, a claim to review) so others see you're on it — or release it."""
        try:
            n = g.lease(author=me, node=g.resolve(node, g.resolve(investigation) if investigation else ""),
                        minutes=int(minutes), release=bool(release))
        except (GraphError, KeyError) as e:
            fail(e)
        return f"{'Released' if release else 'Took'} {n['code']} — {n['state']['sentence']}"

    @mcp.tool
    def register_run(name: str, investigation: str = "", code_paths: list[str] | None = None,
                     input_paths: list[str] | None = None, output_paths: list[str] | None = None, command: str = "",
                     seed: str = "", experiment: str = "", result_summary: str = "",
                     result_values: dict[str, Any] | None = None, outcome: str = "", limitations: str = "") -> str:
        """Record a computation you ran. The server hashes the files itself (code, inputs, outputs — paths under its
        files root), records the run as agent-reported, and adds the result it produced, ready for claims to bind
        to: result_values {name: {value, unit} | {k, n}}."""
        try:
            inv = inv_of(investigation)

            def hashed(paths):
                out = []
                for p in paths or []:
                    q = (root / p).resolve() if not Path(p).is_absolute() else Path(p).resolve()
                    if not q.is_relative_to(root):
                        raise GraphError(f"{p}: only files under {root} can be registered")
                    if not q.is_file():
                        raise GraphError(f"{p}: no such file")
                    out.append(file_sha256(q) | {"path": str(q.relative_to(root))})
                return out
            files = {"code": hashed(code_paths), "inputs": hashed(input_paths), "outputs": hashed(output_paths)}
            if not files["code"] and not command.strip():
                raise GraphError("say what ran: code_paths (hashed) and/or command")
            links = []
            for role, key in (("code", "code"), ("data", "inputs")):
                for f in files[key]:
                    a = g.create(author=me, type="artifact", inv=inv, fields={
                        "sha256": f["sha256"], "path": f["path"], "size": f["size"], "format": Path(f["path"]).suffix[1:]})
                    links.append({"rel": "uses", "to": a["id"], "data": {"role": role}})
            for f in files["outputs"]:
                a = g.create(author=me, type="artifact", inv=inv, fields={
                    "sha256": f["sha256"], "path": f["path"], "size": f["size"], "format": Path(f["path"]).suffix[1:]})
                links.append({"rel": "produced", "to": a["id"]})
            if experiment.strip():
                links.append({"rel": "executes", "to": g.resolve(experiment, inv)})
            fields: dict[str, Any] = {"kind": "agent", "name": name[:300], "state": "succeeded", **files,
                                      "args": [command[:300]] if command.strip() else [],
                                      "note": f"Registered by {me}; files hashed by the MCP server when registered."}
            if seed.strip():
                fields["seed"] = int(seed) if re.fullmatch(r"-?\d+", seed.strip()) else seed.strip()[:64]
            run = g.create(author=me, type="run", inv=inv, fields=fields, links=links)
            msg = f"Registered {run['code']} ({run['id']}): {sum(len(v) for v in files.values())} file(s) hashed."
            if result_summary.strip():
                rf: dict[str, Any] = {"summary": result_summary, "kind": "computed", "values": result_values or {}}
                if outcome:
                    rf["outcome"] = outcome
                if limitations:
                    rf["limitations"] = limitations
                r = g.create(author=me, type="result", inv=inv, fields=rf, links=[{"rel": "produced", "from": run["id"]}])
                msg += f" Result {r['code']} ({r['id']}) — bind claims to it with measurements."
            return msg
        except (GraphError, KeyError, OSError) as e:
            fail(e)

    @mcp.tool
    def report(investigation: str = "") -> str:
        """The facts of an investigation generated from the record (markdown): every claim with its standing and
        verdicts, every result and whether a claim carries it, hypotheses, experiments (preregistered or not), open
        items. Start any summary from it; it can't restate a withdrawn claim or override a verdict."""
        try:
            return g.report(inv_of(investigation))["markdown"]
        except (GraphError, KeyError) as e:
            fail(e)

    @mcp.tool
    def verify() -> str:
        """Recompute the hash chain and check every stored version and link against the event that wrote it."""
        v = g.verify()
        return (f"Verified {v['checked']} events: chain intact, every row matches its event (head {v['head'][:16]}…)."
                if v["ok"] else f"VERIFY FAILED: {v['problem']}")

    @mcp.tool
    def schema() -> dict:
        """The node types (fields, which are required), the relations (which types each may join) and the verdicts."""
        return describe()

    @mcp.resource("hypgraph://schema", mime_type="application/json")
    def schema_resource() -> str:
        """The hypgraph/1 vocabulary."""
        return json.dumps(describe(), indent=1)

    @mcp.resource("hypgraph://investigations", mime_type="application/json")
    def investigations_resource() -> str:
        """Every investigation with its counts."""
        return json.dumps([{k: i[k] for k in ("id", "code", "title", "counts")} | {"state": i["state"]["lifecycle"]}
                           for i in g.investigations()], indent=1)

    @mcp.resource("hypgraph://investigation/{inv}/report", mime_type="text/markdown")
    def report_resource(inv: str) -> str:
        """The facts of one investigation, generated from the record."""
        return g.report(g.resolve(inv))["markdown"]

    @mcp.resource("hypgraph://skill", mime_type="text/markdown")
    def skill_resource() -> str:
        """The HypGraph agent skill (SKILL.md): the method, the refusals and their fixes."""
        return (Path(__file__).parent / "skill" / "SKILL.md").read_text(encoding="utf-8")

    @mcp.prompt
    def method(question: str = "") -> str:
        """How to work a question through the record."""
        return (INSTRUCTIONS + "\n\n" + (f"The question: {question}\n" if question else "")
                + "Start with overview(); if no investigation fits, start_investigation with reviewers named.")

    mcp.graph = g
    mcp.author = me
    return mcp


def run(db: str, author: Optional[str] = None, transport: str = "stdio", port: int = 8766) -> None:
    server = build(db, author)
    if transport == "http":
        server.run(transport="http", host="127.0.0.1", port=port)
    else:
        server.run(show_banner=False)

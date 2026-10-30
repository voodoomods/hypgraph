"""
Blind work orders: a checker measures without seeing the answer it is checking.

A work order issued with ``blind=True`` seals the record from its assignee until the order is returned. While it is
open, the assignee reads the problem statement (the investigation the order belongs to, the curators' investigations,
the questions) and its own order; everything else other authors wrote — hypotheses and their predictions, results,
claims, reviews, runs and their code, sources, other orders, other teams' attempts — is sealed: shown as a placeholder,
left out of search, its numbers scrubbed wherever else they appear.

What the assignee writes inside that window is **written blind**. When the window closes (the order is returned, or
cancelled), the record compares: a blind result that repeats an earlier result's numbers *agrees blind* with it
instead of restating it, and a line of support that contains a blind result is counted as a blind line.

The record enforces what it can see:

- at issue: a blind order carries no prediction, asks for a measurement (not a review or a report), goes to an
  assignee that has written nothing in this record yet, and its objective, method and note quote no number that
  only the sealed material carries;
- at read: :func:`view_for` gives the redaction a host applies to everything it returns to a reader while an order
  is open — the MCP server (``hypgraph mcp``) for its seat's author, HypMesh for every reader but the agent that
  wrote a node. ``hypgraph serve`` and the Python API read the whole record: a file is only as blind as whoever
  holds it.

It cannot see reads. A seat that read the record before its order was issued has already seen what is now sealed;
give a checker its order first.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable

from . import derive as D

# Numbers as written: 10,000 · 1229 · 0.0371 · -2.5. Not inside words or ids (n-1a2b3c, X12, v2).
_NUM = re.compile(r"(?<![\w.,])-?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![\w])")
# A reader may make these requests while sealed; everything else quotes or summarises what other authors wrote.
READ_ROUTES = frozenset({"investigations", "orders", "order", "resolve", "subgraph", "node", "why", "impact",
                         "neighborhood", "search", "events", "verify", "profiles", "profile", "references"})
POST_ROUTES = frozenset({"check_work"})
VISIBLE_TYPES = frozenset({"question"})
# A blind order asks for a measurement. A review or a report has to read what it judges.
BLIND_PREDICATES = frozenset({"run_registered", "result_exists", "claim_made", "within_budget"})
SEALED = "sealed"


def canon(tok: str) -> str:
    """A number token as compared: no thousands separators, no trailing zeros after the point."""
    t = tok.replace(",", "")
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t or "0"


def _significant(t: str) -> bool:
    """Small whole numbers (0–12) are everywhere — counts, steps, versions — and say nothing on their own."""
    try:
        f = float(t)
    except ValueError:
        return False
    return not (f.is_integer() and abs(f) <= 12)


def numbers(x: Any) -> set[str]:
    """Every significant number in a body, from its text and its values."""
    out: set[str] = set()

    def walk(v: Any) -> None:
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            t = canon(repr(float(v))) if isinstance(v, float) else str(v)
            if _significant(t):
                out.add(t)
        elif isinstance(v, str):
            out.update(c for c in (canon(m.group(0)) for m in _NUM.finditer(v)) if _significant(c))
        elif isinstance(v, dict):
            for w in v.values():
                walk(w)
        elif isinstance(v, (list, tuple)):
            for w in v:
                walk(w)
    walk(x)
    return out


# ── windows: when an order's assignee works blind ──────────────────
def _is_order(s: D.Snap, i: str) -> bool:
    n = s.nodes.get(i)
    return bool(n and n["type"] == "task" and n["body"].get("assignee") and n["body"].get("objective"))


def _create_seqs(s: D.Snap) -> dict[str, int]:
    return {e["ref"]: e["seq"] for e in s.events if e["kind"] == "create"}


@dataclass
class Window:
    root: str                      # the first order of the chain (a rework keeps its window)
    orders: list[str]              # every order of the chain, oldest first
    assignee: str
    inv: str
    start: int                     # seq the root was created at
    end: int | None                # seq of the first release (return or cancel) or withdrawal in the chain
    sealing: bool                  # the window is open and the chain's current order is open or overdue
    fresh: bool                    # the assignee had written nothing in this record before the window opened

    def code(self, s: D.Snap) -> str:
        return s.nodes[self.orders[-1]]["code"]


def windows(s: D.Snap) -> list[Window]:
    """Every blind order chain in the record, with its window. Cached on the snapshot by its head."""
    hit = getattr(s, "_blind_windows", None)
    if hit is not None and hit[0] == s.seq:
        return hit[1]
    from . import coord
    roots: dict[str, list[str]] = {}
    for i, n in s.nodes.items():
        if _is_order(s, i) and n["body"].get("blind"):
            roots.setdefault(coord.chain_root(s, i), []).append(i)
    out: list[Window] = []
    if roots:
        created = _create_seqs(s)
        first_write: dict[str, int] = {}
        for e in s.events:
            if e["kind"] == "create" and e["actor"] not in first_write:
                first_write[e["actor"]] = e["seq"]
        for root, chain in roots.items():
            if not s.nodes[root]["body"].get("blind"):
                continue                               # a rework made blind after a sighted attempt isn't blind
            chain = sorted(set(chain) | {root}, key=lambda o: created.get(o, 0))
            members = set(chain)
            start = created.get(root, 0)
            end = None
            for e in s.events:
                if e["seq"] <= start:
                    continue
                if (e["kind"] == "lease_release" and (e["payload"] or {}).get("task") in members) or \
                        (e["kind"] == "withdraw" and e["ref"] in members):
                    end = e["seq"]
                    break
            who = s.nodes[root]["body"]["assignee"]
            cur = chain[-1]
            status = coord.order_status(s, cur)
            out.append(Window(root, chain, who, s.nodes[root]["inv"], start, end,
                              sealing=end is None and status in ("open", "overdue"),
                              fresh=first_write.get(who, start + 1) > start))
    s._blind_windows = (s.seq, out)
    return out


def written_blind(s: D.Snap) -> dict[str, Window]:
    """Results the assignee of a blind order wrote inside its window, unrevised since it closed. An assignee that
    had written in the record before the order is not fresh: nothing it writes counts as blind."""
    hit = getattr(s, "_blind_results", None)
    if hit is not None and hit[0] == s.seq:
        return hit[1]
    out: dict[str, Window] = {}
    ws = [w for w in windows(s) if w.fresh]
    if ws:
        created = _create_seqs(s)
        last_rev: dict[str, int] = {}
        for e in s.events:
            if e["kind"] == "revise":
                last_rev[e["ref"]] = e["seq"]
        for i, n in s.nodes.items():
            if n["type"] != "result":
                continue
            c = created.get(i, 0)
            for w in ws:
                if n["created_by"] == w.assignee and c > w.start and (w.end is None or c < w.end) and \
                        (w.end is None or last_rev.get(i, 0) < w.end):
                    out[i] = w
                    break
    s._blind_results = (s.seq, out)
    return out


def blind_state(s: D.Snap, nid: str) -> dict:
    """What derive.state adds for blindness: on a result, the order it was written blind under, and once the window
    closed, the earlier results it agrees with (instead of restating them); on a claim or hypothesis, how many of
    its independent lines contain a blind result whose window has closed."""
    n = s.nodes[nid]
    out: dict = {}
    wb = written_blind(s)
    if n["type"] == "result" and nid in wb:
        w = wb[nid]
        out["blind"] = w.code(s)
        if w.end is None:
            out["sealed"] = True
    if n["type"] in ("claim", "hypothesis") and wb:
        closed = {r for r, w in wb.items() if w.end is not None}
        if closed:
            k = _blind_lines(s, nid, closed)
            if k:
                out["blind_lines"] = k
    return out


def _blind_lines(s: D.Snap, nid: str, blind: set[str]) -> int:
    lines = [e["src"] for e in D.supporters(s, nid) if not D.fallen(s, e["src"])]
    groups: list[tuple[set, bool]] = []
    for x in lines:
        r = D.roots(s, x)
        is_blind = x in blind or bool(r & {D.producing_run(s, b) for b in blind if D.producing_run(s, b)}) \
            or any(b in blind for b in _derived(s, x))
        merged = [g for g in groups if g[0] & r]
        for g in merged:
            groups.remove(g)
            r = r | g[0]
            is_blind = is_blind or g[1]
        groups.append((r, is_blind))
    return sum(1 for _r, b in groups if b)


def _derived(s: D.Snap, x: str, limit: int = 60) -> set[str]:
    out, stack = set(), [x]
    while stack and len(out) < limit:
        y = stack.pop()
        for e in s.out.get(y, []):
            if e["rel"] == "derived_from" and e["dst"] not in out:
                out.add(e["dst"])
                stack.append(e["dst"])
    return out


# ── what is sealed, and from whom ──────────────────────────────────
def public(s: D.Snap, n: dict, w: Window) -> bool:
    """The problem statement every reader keeps: questions, the curators' investigations, the order's own
    investigation, and the order chain itself."""
    return (n["type"] in VISIBLE_TYPES
            or (n["type"] == "investigation" and (n["created_by"] in s.policy.curators or n["id"] == w.inv)))


def scope(s: D.Snap, w: Window) -> set[str]:
    """What a sealing window hides from its assignee: everything other authors wrote that isn't the problem
    statement or the order chain."""
    chain = set(w.orders)
    return {i for i, n in s.nodes.items()
            if i not in chain and n["created_by"] != w.assignee and not public(s, n | {"id": i}, w)}


@dataclass
class View:
    """The redaction for one reader. Empty (``bool(view) is False``) when nothing is sealed from it."""
    hide: dict[str, str] = field(default_factory=dict)     # node id → the order code that seals it
    secrets: frozenset = frozenset()                        # numbers only the sealed material carries

    def __bool__(self) -> bool:
        return bool(self.hide)

    def because(self) -> str:
        codes = sorted(set(self.hide.values()))
        return ", ".join(codes)

    def message(self, what: str = "this") -> str:
        return (f"{what} is sealed while blind work order {self.because()} is open: the record is hidden from its "
                "checker until the order is returned. Work from the order (my_work) and return it.")

    def allows(self, method: str, head: str) -> bool:
        return head in (POST_ROUTES if method == "POST" else READ_ROUTES)

    def scrub(self, x: Any) -> Any:
        """Every number only the sealed material carries, replaced in every string."""
        if not self.secrets:
            return x
        if isinstance(x, str):
            return _NUM.sub(lambda m: "[sealed]" if canon(m.group(0)) in self.secrets else m.group(0), x)
        if isinstance(x, dict):
            return {k: self.scrub(v) for k, v in x.items()}
        if isinstance(x, list):
            return [self.scrub(v) for v in x]
        return x

    def node(self, d: dict) -> dict:
        """A sealed node as a reader sees it: what it is and where, not what it says."""
        code = self.hide.get(d.get("id"), "")
        st = d.get("state") or {}
        out = {k: d[k] for k in ("id", "type", "code", "inv", "v", "by", "at") if k in d}
        out |= {"title": f"sealed until {code} is returned", "kind": "", SEALED: code,
                "state": {"lifecycle": st.get("lifecycle", "active"), SEALED: code,
                          "sentence": f"sealed until blind work order {code} is returned"}}
        if "body" in d:
            out["body"] = {SEALED: f"until {code} is returned"}
        for k in ("out", "in"):
            if k in d:
                out[k] = [self.edge(e) for e in d[k]]
        return out

    def edge(self, e: dict) -> dict:
        if e.get("src") in self.hide or e.get("dst") in self.hide:
            return e | {"why": "", "data": {}}
        return e

    def event(self, e: dict) -> dict:
        if e.get("ref") in self.hide:
            p = e.get("payload") or {}
            return e | {"payload": {k: p[k] for k in ("type", "code", "inv", "v", "task") if k in p}}
        return e

    def apply(self, x: Any) -> Any:
        """Redact a response: sealed nodes become placeholders, edges touching them lose their reasons, events on
        them lose their payload, and secret numbers are scrubbed everywhere."""
        if not self:
            return x
        return self.scrub(self._walk(x))

    def _walk(self, x: Any) -> Any:
        if isinstance(x, list):
            return [self._walk(v) for v in x]
        if not isinstance(x, dict):
            return x
        if x.get("id") in self.hide and ("type" in x or "code" in x or "body" in x):
            return self.node(x)
        if "src" in x and "dst" in x and "rel" in x:
            return self.edge(x)
        if "seq" in x and "kind" in x and "ref" in x:
            return self.event(x)
        return {k: self._walk(v) for k, v in x.items()}

    def search(self, rows: list[dict]) -> list[dict]:
        """Search results without sealed nodes: a hit on a sealed body says what the body contains."""
        return [r for r in rows if r.get("id") not in self.hide]


def view_for(s: D.Snap, keep: Callable[[str, dict], bool]) -> View:
    """The redaction for a reader, while any blind order is sealing: every node in a sealing window's scope, except
    those ``keep(node_id, node)`` says this reader may see (its own). Secret numbers are the ones in hidden bodies
    that no visible node carries."""
    hide: dict[str, str] = {}
    for w in windows(s):
        if not w.sealing:
            continue
        code = w.code(s)
        for i in scope(s, w):
            if i not in hide and not keep(i, s.nodes[i]):
                hide[i] = code
    if not hide:
        return View()
    hidden_nums: set[str] = set()
    seen_nums: set[str] = set()
    for i, n in s.nodes.items():
        (hidden_nums if i in hide else seen_nums).update(numbers(n["body"]))
    return View(hide, frozenset(hidden_nums - seen_nums))


def view_for_author(s: D.Snap, author: str) -> View:
    """The redaction for an MCP seat writing as ``author``: sealed only while it holds an open blind order, and then
    everything in that order's scope is hidden from it."""
    mine = [w for w in windows(s) if w.sealing and w.assignee == author]
    if not mine:
        return View()
    hide: dict[str, str] = {}
    for w in mine:
        for i in scope(s, w):
            hide.setdefault(i, w.code(s))
    hidden_nums: set[str] = set()
    seen_nums: set[str] = set()
    for i, n in s.nodes.items():
        (hidden_nums if i in hide else seen_nums).update(numbers(n["body"]))
    return View(hide, frozenset(hidden_nums - seen_nums))


def dispatch(g, method: str, path: str, *, query: dict | None = None, body: dict | None = None,
             keep: Callable[[str, dict], bool] = lambda i, n: False, **kw) -> tuple[int, Any]:
    """``server.dispatch`` for a reader while blind orders may be open: refused where a route would quote sealed
    material, redacted everywhere else. ``keep`` says which nodes this reader may see anyway (its own)."""
    from .server import dispatch as plain
    s = g.snapshot()
    if not windows(s):
        return plain(g, method, path, query=query, body=body, **kw)
    v = view_for(s, keep)
    if not v:
        return plain(g, method, path, query=query, body=body, **kw)
    parts = [p for p in path.strip("/").split("/") if p]
    head, arg = (parts[0] if parts else ""), (parts[1] if len(parts) > 1 else "")
    if method == "POST" and head == "write":
        status, out = plain(g, method, path, query=query, body=body, **kw)
        return status, v.apply(out)
    if not v.allows(method, head):
        return 409, {"detail": v.message(f"/{head}"), SEALED: v.because()}
    if head in ("order", "node", "why", "impact", "neighborhood") and arg:
        try:
            nid = g.resolve(arg)
        except Exception:
            nid = arg
        if head == "order" and nid in v.hide:
            return 409, {"detail": v.message(f"order {arg}"), SEALED: v.because()}
    status, out = plain(g, method, path, query=query, body=body, **kw)
    if head == "search" and status == 200 and isinstance(out, dict) and isinstance(out.get("results"), list):
        out = out | {"results": v.search(out["results"])}
    return status, v.apply(out)


def leaks(s: D.Snap, w: Window, texts: list[str]) -> dict[str, list[str]]:
    """Numbers an order's own text quotes that only the material it would seal carries: number → codes holding it."""
    hide = scope(s, w)
    visible: set[str] = set()
    for i, n in s.nodes.items():
        if i not in hide:
            visible |= numbers(n["body"])
    quoted = numbers(texts) - visible
    out: dict[str, list[str]] = {}
    for i in hide:
        hit = quoted & numbers(s.nodes[i]["body"])
        for x in hit:
            out.setdefault(x, []).append(s.nodes[i]["code"] or i)
    return {k: sorted(v) for k, v in out.items()}


__all__ = ["Window", "View", "windows", "written_blind", "blind_state", "scope", "view_for", "view_for_author",
           "dispatch", "leaks", "numbers", "BLIND_PREDICATES"]

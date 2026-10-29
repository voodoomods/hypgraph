"""
``hypgraph serve`` — the JSON API and the HypGraph UI, stdlib only.

    GET  /                                  the HypGraph UI
    GET  /api/graph/investigations          {investigations, stats}
    GET  /api/graph/subgraph?inv=&types=    nodes (with standing) and live edges
    GET  /api/graph/node/{id}?history=1     one node, its links, its versions
    GET  /api/graph/why/{id}                what it rests on        /impact/{id}  what rests on it
    GET  /api/graph/neighborhood/{id}?depth=
    GET  /api/graph/search?text=&type=&inv=&limit=
    GET  /api/graph/events?after=&inv=&limit=
    GET  /api/graph/stream?inv=&after=      the same events pushed as they are written (Server-Sent Events; resumes
                                            from Last-Event-ID; a comment line every 15 s keeps proxies open)
    GET  /api/graph/profile?inv=            the investigation's profile as a UI speaks it: labels, workflow, report
    GET  /api/graph/telemetry?inv=&after=   a swarm's telemetry sidecar (hypswarm writes <db>.telemetry.jsonl): model and
                                            tool calls, work orders, decisions; ``after`` is the byte offset ``next`` gave.
                                            The stream above carries it too, as ``telemetry`` events.
    GET  /api/graph/next?inv=   /work?inv=   /cost?inv=&node=   /report?inv=   /verify   /schema
    GET  /api/graph/export?inv=             a verifiable bundle
    GET  /api/graph/refusals?inv=&since=    the overclaims caught, per author and rule
    POST /api/graph/check                   {text, inv?} → lint a write-up against the record (always allowed)
    POST /api/graph/write                   only with --writable: {op, author, ...} (create | revise | link | retract |
                                            withdraw | review | lease | issue_work | return_work | accept_work |
                                            rework | cancel_work | cancel_moot | settle); reserved authors refused
    Coordination (read): GET /api/graph/board?inv=  /orders?inv=&status=  /order/{id}  /resolve?ref=&inv=
                         POST /api/graph/briefing {inv, roster?, since_seq?}   POST /api/graph/check_work {order, text?}
    A swarm's workers (hypswarm) talk to a server started with --writable instead of sharing one process.

It binds to 127.0.0.1 by default and refuses requests whose Host isn't the address it serves (DNS rebinding) and
cross-origin writes. Writes can be bound to bearer tokens (``--token SECRET=author1,author2`` or ``=*`` for any
non-reserved author): with tokens configured, a write without a known token is 401, and a write as an author the
token isn't bound to is 403 — a reserved name (the orchestrator, the operator) can be written only by a token that
names it. Without tokens it authenticates nobody, as before: keep it on localhost or behind your own auth.
``dispatch()`` is the routing on its own, for hosts that bring their own web framework.
"""

from __future__ import annotations

import hmac
import json
import mimetypes
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import profiles
from .graph import Graph, GraphError
from .schema import describe
from .ui import static_dir

WRITES = {
    "create": ("create", ("type", "fields", "inv", "links", "reason")),
    "revise": ("revise", ("node", "fields", "reason")),
    "link": ("link", ("src", "rel", "dst", "why", "data")),
    "retract": ("retract", ("edge", "why")),
    "withdraw": ("withdraw", ("node", "why")),
    "review": ("review", ("target", "verdict", "method", "notes")),
    "lease": ("lease", ("node", "task", "minutes", "release", "note")),
    # coordination (coord.py): orders issued, returned, accepted, reworked, cancelled through the record
    "issue_work": ("issue_work", ("inv", "target", "assignee", "objective", "role", "done_when", "prediction", "method",
                                  "budget", "premises", "lease_minutes", "note")),
    "return_work": ("return_work", ("order", "note")),
    "accept_work": ("accept_work", ("order", "reason", "text")),
    "rework": ("rework", ("order", "missing", "done_when")),
    "cancel_work": ("cancel_work", ("order", "why")),
    "cancel_moot": ("cancel_moot", ("inv",)),
    "settle": ("settle", ("inv",)),
}


def _int(q: dict, k: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(q.get(k, default)), hi))
    except (TypeError, ValueError):
        return default


def parse_tokens(specs: list[str] | None, path: str = "") -> dict[str, frozenset]:
    """``SECRET`` or ``SECRET=author1,author2`` or ``SECRET=*`` (any non-reserved author); one per entry, or one per
    line of a file. A bare secret means ``*``."""
    out: dict[str, frozenset] = {}
    lines = list(specs or [])
    if path:
        lines += [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()]
    for ln in lines:
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        secret, _, authors = ln.partition("=")
        names = frozenset(a.strip().lower() for a in authors.split(",") if a.strip()) or frozenset({"*"})
        if len(secret) < 16:
            raise ValueError("a token secret must be at least 16 characters")
        out[secret] = names
    return out


def _author_allowed(g: Graph, author: str, allowed: frozenset | None) -> str:
    """'' when the write may proceed as ``author``, else the refusal."""
    if allowed is None:                                  # no token layer: reserved names are refused, the rest taken at word
        return "author missing, or reserved (" + ", ".join(sorted(g.policy.reserved)) + ")" \
            if not author or author in g.policy.reserved else ""
    if author in allowed:
        return ""                                        # named on the token — reserved or not, the operator chose it
    if "*" in allowed and author and author not in g.policy.reserved:
        return ""
    return f"this token may not write as {author!r}"


def dispatch(g: Graph, method: str, path: str, query: dict | None = None, body: dict | None = None,
             writable: bool = False, allowed: frozenset | None = None) -> tuple[int, object]:
    """Route one API call. ``path`` is what follows /api/graph (e.g. "/node/n1a2b"). Returns (status, JSON value).
    ``allowed``: the authors the caller's token is bound to (None = no token layer)."""
    q = {k: (v[0] if isinstance(v, list) else v) for k, v in (query or {}).items()}
    parts = [unquote(p) for p in path.strip("/").split("/") if p]
    try:
        if method == "POST":
            if parts == ["check"]:
                b = body or {}
                return 200, g.check_text(str(b.get("text") or ""), str(b.get("inv") or ""))
            if parts == ["briefing"]:                       # a read with a structured argument (the roster)
                b = body or {}
                return 200, g.briefing(str(b.get("inv") or ""), roster=b.get("roster"),
                                       since_seq=int(b.get("since_seq") or 0))
            if parts == ["check_work"]:
                b = body or {}
                return 200, g.check_work(str(b.get("order") or ""), str(b.get("text") or ""))
            if parts != ["write"]:
                return 404, {"detail": "no such route"}
            if not writable:
                return 403, {"detail": "this server is read-only (start it with --writable to accept writes)"}
            b = body or {}
            author = str(b.get("author") or "").strip().lower()
            refused = _author_allowed(g, author, allowed)
            if refused:
                return 403, {"detail": refused}
            spec = WRITES.get(str(b.get("op") or ""))
            if not spec:
                return 400, {"detail": f"op must be one of {', '.join(WRITES)}"}
            fn, keys = spec
            return 200, getattr(g, fn)(author=author, **{k: b[k] for k in keys if k in b})
        if method != "GET" or not parts:
            return 404, {"detail": "no such route"}
        head, arg = parts[0], (parts[1] if len(parts) > 1 else "")
        inv = q.get("inv", "")
        if head == "investigations":
            return 200, {"investigations": g.investigations(), "stats": g.stats()}
        if head == "board":
            return 200, {"board": g.question_board(inv)}
        if head == "orders":
            return 200, {"orders": g.orders(inv, q.get("status", ""))}
        if head == "order" and arg:
            return 200, {"text": g.order_text(arg), "check": g.check_work(arg)}
        if head == "resolve":
            return 200, {"id": g.resolve(q.get("ref", ""), inv)}
        if head == "subgraph":
            types = [t for t in str(q.get("types", "")).split(",") if t] or None
            return 200, g.subgraph(inv, types=types)
        if head == "node" and arg:
            return 200, g.get(arg, history=q.get("history") in ("1", "true"))
        if head == "why" and arg:
            return 200, g.why(arg)
        if head == "impact" and arg:
            return 200, g.impact(arg)
        if head == "neighborhood" and arg:
            return 200, g.neighborhood(arg, depth=_int(q, "depth", 1, 1, 4))
        if head == "search":
            return 200, {"results": g.search(text=q.get("text", ""), type=q.get("type", ""), inv=inv,
                                              limit=_int(q, "limit", 50, 1, 500))}
        if head == "events":
            return 200, g.events(after=_int(q, "after", 0, 0, 10 ** 12), inv=inv, limit=_int(q, "limit", 500, 1, 5000))
        if head == "next":
            return 200, g.next_experiments(inv, limit=_int(q, "limit", 20, 1, 100))
        if head == "work":
            return 200, g.work_map(inv)
        if head == "cost":
            return 200, g.cost(inv, q.get("node", ""))
        if head == "report":
            return 200, g.report(inv)
        if head == "completion":
            return 200, g.completion(inv)
        if head == "stages":
            return 200, {"stages": g.stages(inv)}
        if head == "stage" and arg:
            return 200, g.stage(arg, inv)
        if head == "profiles":
            return 200, profiles.describe()
        if head == "profile":
            pid = str((g.get(inv).get("body") or {}).get("profile") or "") if inv else ""
            return 200, profiles.view(pid)
        if head == "verify":
            return 200, g.verify_chain()
        if head == "refusals":
            return 200, g.refusal_report(inv=inv, since=q.get("since", ""))
        if head == "export":
            return 200, g.export(inv)
        if head == "schema":
            return 200, describe()
        if head == "stats":
            return 200, g.stats()
        return 404, {"detail": "no such route"}
    except KeyError as e:
        return 404, {"detail": f"not found: {e.args[0] if e.args else e}"}
    except (GraphError, ValueError, TypeError) as e:
        return 400, {"detail": str(e)}


def read_telemetry(path: Path | None, after: int = 0, inv: str = "", limit: int = 2000) -> tuple[list[dict], int]:
    """New complete lines of a telemetry sidecar from byte ``after``: (events, the offset to read from next). A line a
    writer hasn't finished is left for the next read; a file that got shorter (rotated) is read from the start. Lines
    that aren't JSON are skipped. ``inv`` keeps that investigation's events (and any without one)."""
    if not path or not path.is_file():
        return [], after
    size = path.stat().st_size
    if size < after:
        after = 0
    out: list[dict] = []
    with path.open("rb") as f:
        f.seek(after)
        chunk = f.read(4_000_000)
    end = chunk.rfind(b"\n")
    if end < 0:
        return [], after
    for line in chunk[:end + 1].splitlines():
        try:
            e = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if isinstance(e, dict) and (not inv or e.get("inv") in (None, "", inv)):
            out.append(e)
            if len(out) >= limit:
                consumed = chunk.find(line) + len(line) + 1
                return out, after + consumed
    return out, after + end + 1


LOOPBACK_NAMES = frozenset({"localhost", "127.0.0.1", "::1"})
WILDCARD_BINDS = frozenset({"", "0.0.0.0", "::", "*"})


def accepted_hosts(host: str, allow_hosts: tuple[str, ...] | list[str] = ()) -> set[str]:
    """The names a request's Host header may carry (port ignored); anything else is 421.

    Bound to a loopback name, the server answers to every loopback name. Bound to a wildcard (``0.0.0.0``,
    ``::``) — as inside a container whose port is published — it answers to the loopback names too, since the
    browser reaches the published port as ``127.0.0.1:<host port>``; the bind address itself is never a name a
    browser sends. ``allow_hosts`` adds names: a LAN hostname, a service name. The check is DNS-rebinding
    defence (a page on another origin can't make the browser talk to this server by name), so a wildcard bind
    never means "any Host"."""
    names = {h.strip().lower() for h in allow_hosts if h and h.strip()}
    h = (host or "").strip().lower()
    if h in LOOPBACK_NAMES or h in WILDCARD_BINDS:
        names |= LOOPBACK_NAMES
    if h and h not in WILDCARD_BINDS:
        names.add(h)
    return names


def make_handler(g: Graph, *, writable: bool, hosts: set[str], root: Path,
                 tokens: dict[str, frozenset] | None = None, telemetry: Path | None = None):
    class Handler(BaseHTTPRequestHandler):
        server_version = "hypgraph"

        def log_message(self, fmt, *args):  # quiet by default
            pass

        def _send(self, status: int, data: bytes, ctype: str, extra: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _identity(self) -> frozenset | None | str:
            """The authors this request's token is bound to; None without a token layer; '' when refused."""
            if not tokens:
                return None
            auth = self.headers.get("Authorization") or ""
            given = auth[7:].strip() if auth.lower().startswith("bearer ") else ""
            for secret, names in tokens.items():
                if given and hmac.compare_digest(given, secret):
                    return names
            return ""

        def _json(self, status: int, obj) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False, default=str).encode(), "application/json")

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return host in hosts

        def do_GET(self):  # noqa: N802
            if not self._host_ok():
                return self._json(421, {"detail": "unexpected Host header"})
            u = urlparse(self.path)
            if u.path.rstrip("/") == "/api/graph/stream":
                return self._stream(parse_qs(u.query))
            if u.path.rstrip("/") == "/api/graph/telemetry":
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                try:
                    after, limit = int(q.get("after") or 0), min(max(int(q.get("limit") or 2000), 1), 10000)
                except ValueError:
                    return self._json(400, {"detail": "after and limit must be integers"})
                evs, nxt = read_telemetry(telemetry, after, str(q.get("inv") or ""), limit)
                return self._json(200, {"events": evs, "next": nxt, "source": telemetry.name if telemetry else "",
                                        "exists": bool(telemetry and telemetry.is_file())})
            if u.path.startswith("/api/graph"):
                status, obj = dispatch(g, "GET", u.path[len("/api/graph"):], parse_qs(u.query), writable=writable)
                return self._json(status, obj)
            rel = "index.html" if u.path in ("", "/") else unquote(u.path).lstrip("/")
            f = (root / rel).resolve()
            if not f.is_relative_to(root) or not f.is_file():
                return self._json(404, {"detail": "not found"})
            ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
            if ctype.startswith("text/") or ctype in ("application/javascript", "image/svg+xml"):
                ctype += "; charset=utf-8"
            self._send(200, f.read_bytes(), ctype)

        def _stream(self, q: dict) -> None:
            """Push the record's events as they are written (Server-Sent Events): ``id`` is the event's seq, so a
            client that reconnects resumes where it was (Last-Event-ID). Writes from other processes on the same
            file arrive too — a swarm writing to the record is watched live. The swarm's telemetry sidecar, when there
            is one, is tailed into the same stream as ``telemetry`` events; ids are then ``<seq>:<byte offset>`` so a
            reconnect resumes both. ``max_seconds`` ends the stream (for clients and tests that want a bounded read);
            0 = until the client leaves."""
            one = {k: v[0] for k, v in q.items()}
            inv = str(one.get("inv") or "")
            last = str(self.headers.get("Last-Event-ID") or "")
            try:
                after = int(one.get("after") or (last.split(":")[0] if last else 0) or 0)
                toff = int(one.get("after_telemetry") or (last.split(":")[1] if ":" in last else 0) or 0)
                max_s = min(max(float(one.get("max_seconds") or 0), 0.0), 86400.0)
                poll = min(max(float(one.get("poll") or 0.5), 0.1), 10.0)
            except ValueError:
                return self._json(400, {"detail": "after, max_seconds and poll must be numbers"})
            if inv:
                try:
                    g.get(inv)
                except KeyError:
                    return self._json(404, {"detail": f"no investigation {inv}"})
            self.send_response(200)
            for k, v in (("Content-Type", "text/event-stream; charset=utf-8"), ("Cache-Control", "no-store"),
                         ("X-Accel-Buffering", "no"), ("X-Content-Type-Options", "nosniff")):
                self.send_header(k, v)
            self.end_headers()
            start = last = time.monotonic()
            try:
                self.wfile.write(b"retry: 2000\n\n")
                self.wfile.flush()
                while True:
                    out = g.events(after=after, inv=inv, limit=500)
                    for e in out["events"]:
                        data = json.dumps(e, ensure_ascii=False, default=str)
                        eid = f"{e['seq']}:{toff}" if telemetry and telemetry.is_file() else f"{e['seq']}"
                        self.wfile.write(f"id: {eid}\nevent: record\ndata: {data}\n\n".encode())
                        after = int(e["seq"])
                    tel, toff2 = read_telemetry(telemetry, toff, inv, 500) if telemetry else ([], toff)
                    for t in tel:
                        data = json.dumps(t, ensure_ascii=False, default=str)
                        self.wfile.write(f"id: {after}:{toff2}\nevent: telemetry\ndata: {data}\n\n".encode())
                    toff = toff2
                    now = time.monotonic()
                    if out["events"] or tel:
                        self.wfile.flush()
                        last = now
                    elif now - last >= 15:
                        self.wfile.write(b": keep-alive\n\n")
                        self.wfile.flush()
                        last = now
                    if max_s and now - start >= max_s:
                        self.wfile.write(f"event: end\ndata: {json.dumps({'head': after})}\n\n".encode())
                        self.wfile.flush()
                        return
                    if len(out["events"]) < 500 and len(tel) < 500:
                        time.sleep(poll)
            except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                return                                      # the client left

        def do_POST(self):  # noqa: N802
            if not self._host_ok():
                return self._json(421, {"detail": "unexpected Host header"})
            origin = self.headers.get("Origin")
            if origin and urlparse(origin).hostname not in hosts:
                return self._json(403, {"detail": "cross-origin write refused"})
            n = int(self.headers.get("Content-Length") or 0)
            if n > 2_000_000:
                return self._json(413, {"detail": "request too large"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"detail": "body must be JSON"})
            u = urlparse(self.path)
            if not u.path.startswith("/api/graph"):
                return self._json(404, {"detail": "no such route"})
            allowed: frozenset | None = None
            if u.path[len("/api/graph"):].strip("/") == "write":
                ident = self._identity()
                if ident == "":
                    data = json.dumps({"detail": "a bearer token this server knows is required to write"}).encode()
                    return self._send(401, data, "application/json", {"WWW-Authenticate": 'Bearer realm="hypgraph"'})
                allowed = ident if isinstance(ident, frozenset) else None
            status, obj = dispatch(g, "POST", u.path[len("/api/graph"):], body=body, writable=writable, allowed=allowed)
            self._json(status, obj)
    return Handler


def make_server(graph: Graph | str, host: str = "127.0.0.1", port: int = 8765, *, writable: bool = False,
                tokens: dict[str, frozenset] | None = None, telemetry: str | Path | None = "auto",
                allow_hosts: tuple[str, ...] | list[str] = ()):
    """``telemetry``: the swarm's sidecar to serve and stream — "auto" is ``<db>.telemetry.jsonl`` beside the record
    (it may appear later: a run started after the server is picked up), a path, or None for none."""
    g = graph if isinstance(graph, Graph) else Graph(graph)
    tel: Path | None = None
    if telemetry == "auto":
        if g.path and g.path != ":memory:":
            tel = Path(g.path + ".telemetry.jsonl")
    elif telemetry:
        tel = Path(telemetry)
    hosts = accepted_hosts(host, allow_hosts)
    root = static_dir().resolve()
    return ThreadingHTTPServer((host, port), make_handler(g, writable=writable, hosts=hosts, root=root, tokens=tokens,
                                                          telemetry=tel))


def serve(db: str, host: str = "127.0.0.1", port: int = 8765, *, writable: bool = False,
          open_browser: bool = True, tokens: dict[str, frozenset] | None = None, telemetry: str | None = "auto",
          allow_hosts: tuple[str, ...] | list[str] = ()) -> None:
    if not Path(db).exists():
        print(f"{db} doesn't exist yet — `hypgraph demo` builds one to explore, `hypgraph init` starts your own.")
        return
    srv = make_server(db, host, port, writable=writable, tokens=tokens, telemetry=telemetry,
                      allow_hosts=allow_hosts)
    url = f"http://{host}:{srv.server_address[1]}/"
    auth = f", {len(tokens)} write token(s)" if tokens else (", writes unauthenticated" if writable else "")
    tel = telemetry if telemetry not in ("auto", None) else (db + ".telemetry.jsonl" if telemetry == "auto" else "")
    print(f"HypGraph on {url}  ({db}{', writable' if writable else ', read-only'}{auth})  — Ctrl+C to stop")
    if tel:
        print(f"  telemetry: {tel}{'' if Path(tel).exists() else ' (not there yet; picked up when a run writes it)'}")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()

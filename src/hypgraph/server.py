"""
``hypgraph serve`` — the JSON API and the Atlas explorer, stdlib only.

    GET  /                                  the Atlas
    GET  /api/graph/investigations          {investigations, stats}
    GET  /api/graph/subgraph?inv=&types=    nodes (with standing) and live edges
    GET  /api/graph/node/{id}?history=1     one node, its links, its versions
    GET  /api/graph/why/{id}                what it rests on        /impact/{id}  what rests on it
    GET  /api/graph/neighborhood/{id}?depth=
    GET  /api/graph/search?text=&type=&inv=&limit=
    GET  /api/graph/events?after=&inv=&limit=
    GET  /api/graph/next?inv=   /work?inv=   /cost?inv=&node=   /report?inv=   /verify   /schema
    GET  /api/graph/export?inv=             a verifiable bundle
    POST /api/graph/write                   only with --writable: {op, author, ...} (create | revise | link | retract |
                                            withdraw | review | lease); the policy's reserved authors are refused

It binds to 127.0.0.1 by default and refuses requests whose Host isn't the address it serves (DNS rebinding) and
cross-origin writes. It authenticates nobody: put it behind your own auth before exposing it beyond your machine.
``dispatch()`` is the routing on its own, for hosts that bring their own web framework.
"""

from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

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
}


def _int(q: dict, k: str, default: int, lo: int, hi: int) -> int:
    try:
        return max(lo, min(int(q.get(k, default)), hi))
    except (TypeError, ValueError):
        return default


def dispatch(g: Graph, method: str, path: str, query: dict | None = None, body: dict | None = None,
             writable: bool = False) -> tuple[int, object]:
    """Route one API call. ``path`` is what follows /api/graph (e.g. "/node/n1a2b"). Returns (status, JSON value)."""
    q = {k: (v[0] if isinstance(v, list) else v) for k, v in (query or {}).items()}
    parts = [unquote(p) for p in path.strip("/").split("/") if p]
    try:
        if method == "POST":
            if parts != ["write"]:
                return 404, {"detail": "no such route"}
            if not writable:
                return 403, {"detail": "this server is read-only (start it with --writable to accept writes)"}
            b = body or {}
            author = str(b.get("author") or "").strip()
            if not author or author in g.policy.reserved:
                return 403, {"detail": "author missing, or reserved (" + ", ".join(sorted(g.policy.reserved)) + ")"}
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
        if head == "verify":
            return 200, g.verify_chain()
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


def make_handler(g: Graph, *, writable: bool, hosts: set[str], root: Path):
    class Handler(BaseHTTPRequestHandler):
        server_version = "hypgraph"

        def log_message(self, fmt, *args):  # quiet by default
            pass

        def _send(self, status: int, data: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def _json(self, status: int, obj) -> None:
            self._send(status, json.dumps(obj, ensure_ascii=False, default=str).encode(), "application/json")

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
            return host in hosts

        def do_GET(self):  # noqa: N802
            if not self._host_ok():
                return self._json(421, {"detail": "unexpected Host header"})
            u = urlparse(self.path)
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
            status, obj = dispatch(g, "POST", u.path[len("/api/graph"):], body=body, writable=writable)
            self._json(status, obj)
    return Handler


def make_server(graph: Graph | str, host: str = "127.0.0.1", port: int = 8765, *, writable: bool = False):
    g = graph if isinstance(graph, Graph) else Graph(graph)
    hosts = {host.lower(), "localhost", "127.0.0.1", "::1"} if host in ("127.0.0.1", "localhost", "::1") else \
        {host.lower()}
    root = static_dir().resolve()
    return ThreadingHTTPServer((host, port), make_handler(g, writable=writable, hosts=hosts, root=root))


def serve(db: str, host: str = "127.0.0.1", port: int = 8765, *, writable: bool = False,
          open_browser: bool = True) -> None:
    if not Path(db).exists():
        print(f"{db} doesn't exist yet — `hypgraph demo` builds one to explore, `hypgraph init` starts your own.")
        return
    srv = make_server(db, host, port, writable=writable)
    url = f"http://{host}:{srv.server_address[1]}/"
    print(f"HypGraph Atlas on {url}  ({db}{', writable' if writable else ', read-only'})  — Ctrl+C to stop")
    if open_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()

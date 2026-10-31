"""The trust boundary of ``hypgraph serve``, from a pre-launch review (2026-10-31): who may write as whom, and what
a page on another origin can make a browser do. The Python API and the CLI are trusted callers (whoever runs them
owns the file); the HTTP server and the MCP server are where an untrusted agent meets the record."""
import http.client
import json
import threading

import pytest

from hypgraph import Graph, Policy
from hypgraph.server import make_server, parse_tokens

T_ANY = "any-author-secret-0123456789"
T_CRITIC = "critic-secret-0123456789abcd"


def _serve(g, **kw):
    srv = make_server(g, port=0, writable=True, **kw)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, srv.server_address[1]


def _post(port, path, body, headers=None, raw=None):
    c = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    data = raw if raw is not None else json.dumps(body).encode()
    h = {"Content-Type": "application/json", "Host": f"127.0.0.1:{port}", **(headers or {})}
    if "Content-Length" not in h:
        h["Content-Length"] = str(len(data))
    c.putrequest("POST", path, skip_host=True, skip_accept_encoding=True)
    for k, v in h.items():
        c.putheader(k, v)
    c.endheaders()
    if data:
        c.send(data)
    r = c.getresponse()
    out = r.read()
    c.close()
    return r.status, (json.loads(out) if out else {})


@pytest.fixture
def open_server(tmp_path):
    """Writable, no tokens: the local, single-user setup."""
    g = Graph(str(tmp_path / "t.hypgraph"))
    srv, port = _serve(g)
    yield g, port
    srv.shutdown()


@pytest.fixture
def token_server(tmp_path):
    g = Graph(str(tmp_path / "t.hypgraph"), policy=Policy(reviewers={"critic"}))
    srv, port = _serve(g, tokens=parse_tokens([f"{T_ANY}=*", f"{T_CRITIC}=critic"]))
    yield g, port
    srv.shutdown()


INV = {"op": "create", "type": "investigation", "fields": {"title": "Trust boundary", "objective": "Who may write as whom."}}


def test_a_page_on_another_local_port_cannot_write(open_server):
    """The cross-origin check compared host names only, so a page served from another port on the same machine (a
    dev server, an agent-built page) could write to a server without tokens through the browser."""
    g, port = open_server
    st, out = _post(port, "/api/graph/write", {**INV, "author": "ada"}, {"Origin": "http://127.0.0.1:1"})
    assert st == 403 and "cross-origin" in out["detail"]
    st, out = _post(port, "/api/graph/write", {**INV, "author": "ada"}, {"Origin": "http://localhost:" + str(port)})
    assert st == 403                                       # same port, another name: another origin
    st, out = _post(port, "/api/graph/write", {**INV, "author": "ada"}, {"Origin": "null"})
    assert st == 403
    st, out = _post(port, "/api/graph/write", {**INV, "author": "ada"}, {"Origin": f"http://127.0.0.1:{port}"})
    assert st == 200, out                                  # the server's own page
    st, out = _post(port, "/api/graph/write", {**INV, "author": "ada"})
    assert st == 200, out                                  # no Origin: not a browser


@pytest.mark.parametrize("length", ["abc", "-1", "99999999999"])
def test_a_bad_content_length_is_refused(open_server, length):
    """A negative length read the socket until the client closed it (one thread held per request)."""
    g, port = open_server
    st, _ = _post(port, "/api/graph/write", None, {"Content-Length": length}, raw=b"")
    assert st in (400, 413)


def test_a_wildcard_token_cannot_write_as_a_reviewer(token_server):
    """``SECRET=*`` lets a token write as any non-reserved name, so an agent holding one could review its own work
    officially under a reviewer's name. A name on a review board — the policy's or an investigation's — must be named
    on a token."""
    g, port = token_server
    auth = {"Authorization": f"Bearer {T_ANY}"}
    st, inv = _post(port, "/api/graph/write", {**INV, "author": "ada"}, auth)
    assert st == 200, inv
    st, h = _post(port, "/api/graph/write", {"op": "create", "author": "ada", "type": "hypothesis", "inv": inv["id"],
                                              "fields": {"statement": "The boundary holds.", "predictions": ["no write as critic"]}}, auth)
    assert st == 200, h
    st, out = _post(port, "/api/graph/write", {"op": "review", "author": "critic", "target": h["id"], "verdict": "pass",
                                                "method": "read it", "notes": "fine"}, auth)
    assert st == 403 and "review board" in out["detail"]
    # an investigation that names its own reviewers puts them on a board too
    st, inv2 = _post(port, "/api/graph/write", {"op": "create", "author": "ada", "type": "investigation", "fields": {
        "title": "Own board", "objective": "Name a reviewer, then try to write as it.", "reviewers": ["bob"]}}, auth)
    assert st == 200, inv2
    st, out = _post(port, "/api/graph/write", {"op": "review", "author": "bob", "target": h["id"], "verdict": "pass",
                                                "method": "read it", "notes": "fine"}, auth)
    assert st == 403
    # the reviewer's own token still reviews
    st, out = _post(port, "/api/graph/write", {"op": "review", "author": "critic", "target": h["id"], "verdict": "pass",
                                                "method": "re-read the hypothesis", "notes": "it says what it means"},
                    {"Authorization": f"Bearer {T_CRITIC}"})
    assert st == 200, out


def test_nobody_reviews_their_own_work_through_any_interface(token_server):
    g, port = token_server
    crit = {"Authorization": f"Bearer {T_CRITIC}"}
    st, inv = _post(port, "/api/graph/write", {**INV, "author": "critic"}, crit)
    st, h = _post(port, "/api/graph/write", {"op": "create", "author": "critic", "type": "hypothesis", "inv": inv["id"],
                                              "fields": {"statement": "My own idea.", "predictions": ["it holds"]}}, crit)
    st, out = _post(port, "/api/graph/write", {"op": "review", "author": "critic", "target": h["id"], "verdict": "pass",
                                                "method": "read it", "notes": "fine"}, crit)
    assert st == 400 and "your own work" in out["detail"]
    from hypgraph import GraphError
    with pytest.raises(GraphError, match="your own work"):                     # the Python API holds the same rule
        g.review(author="critic", target=h["id"], verdict="pass", method="read it", notes="fine")


def test_the_http_api_takes_no_time_attribution_or_ids_from_a_writer(open_server):
    """Backdating (``at``), attributing to someone else (``attribute_to``), choosing an id or code: the importer's
    tools in the Python API, never fields the HTTP write reads."""
    g, port = open_server
    st, inv = _post(port, "/api/graph/write", {**INV, "author": "ada", "at": "2001-01-01T00:00:00", "attribute_to": "bob",
                                               "node_id": "n000000000001", "code": "INV9"})
    assert st == 200
    n = g.get(inv["id"])
    assert n["by"] == "ada" and not n["at"].startswith("2001") and inv["id"] != "n000000000001"


def test_the_mcp_seat_writes_as_one_name_and_never_a_reserved_one(tmp_path):
    pytest.importorskip("fastmcp")
    from hypgraph.mcp import build
    g = Graph(str(tmp_path / "m.hypgraph"), policy=Policy(extra_reserved={"orchestrator"}))
    for who in ("operator", "lab", "importer", "system", "orchestrator"):
        with pytest.raises(SystemExit):
            build(g, author=who)

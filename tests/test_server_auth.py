"""Writes bound to bearer tokens: without a token layer nothing changes; with one, an unknown token is 401, an
author the token isn't bound to is 403, and a reserved name is written only by a token that names it."""
import json
import threading
import urllib.error
import urllib.request

import pytest

from hypgraph import Graph, Policy
from hypgraph.server import make_server, parse_tokens

T_ANY = "any-author-secret-0123456789"
T_HARNESS = "harness-secret-0123456789abc"
T_NIC = "nicolas-secret-0123456789abcd"


@pytest.fixture
def served(tmp_path):
    g = Graph(str(tmp_path / "auth.hypgraph"), policy=Policy(reviewers={"critic"}, extra_reserved={"harness"}))
    tokens = parse_tokens([f"{T_ANY}=*", f"{T_HARNESS}=harness,lead", f"{T_NIC}=nicolas"])
    srv = make_server(g, port=0, writable=True, tokens=tokens)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield g, f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _write(url, body, token=None):
    req = urllib.request.Request(f"{url}/api/graph/write", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          **({"Authorization": f"Bearer {token}"} if token else {})})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read()), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()), dict(e.headers)


def _inv(url, token):
    st, out, _ = _write(url, {"op": "create", "author": "ada", "type": "investigation",
                              "fields": {"title": "A test of the token layer.", "objective": "Check who may write."}}, token)
    assert st == 200, out
    return out["id"]


def test_no_token_is_401_and_reads_stay_open(served):
    g, url = served
    st, out, hdr = _write(url, {"op": "create", "author": "ada", "type": "investigation", "fields": {"title": "A test of the token layer."}})
    assert st == 401 and "bearer token" in out["detail"] and hdr.get("WWW-Authenticate", "").startswith("Bearer")
    st, out, _ = _write(url, {"op": "create", "author": "ada", "type": "investigation", "fields": {"title": "A test of the token layer."}},
                        "wrong-secret-0123456789abcdef")
    assert st == 401
    with urllib.request.urlopen(f"{url}/api/graph/investigations") as r:      # reads need no token
        assert r.status == 200


def test_bound_token_writes_only_as_its_authors(served):
    g, url = served
    inv = _inv(url, T_ANY)
    st, out, _ = _write(url, {"op": "create", "author": "ada", "type": "question", "inv": inv,
                              "fields": {"text": "What does the record say?"}}, T_NIC)
    assert st == 403 and "may not write as 'ada'" in out["detail"]
    st, out, _ = _write(url, {"op": "create", "author": "nicolas", "type": "question", "inv": inv,
                              "fields": {"text": "What does the record say?"}}, T_NIC)
    assert st == 200 and out["by"] == "nicolas"


def test_reserved_author_needs_a_token_that_names_it(served):
    g, url = served
    inv = _inv(url, T_ANY)
    body = {"op": "create", "author": "harness", "type": "question", "inv": inv, "fields": {"text": "What does the record say?"}}
    st, out, _ = _write(url, body, T_ANY)                 # * never covers a reserved name
    assert st == 403 and "harness" in out["detail"]
    st, out, _ = _write(url, body, T_HARNESS)
    assert st == 200 and out["by"] == "harness"
    st, out, _ = _write(url, dict(body, author="operator"), T_HARNESS)   # bound to harness,lead — not operator
    assert st == 403


def test_author_case_is_folded(served):
    g, url = served
    inv = _inv(url, T_ANY)
    st, out, _ = _write(url, {"op": "create", "author": "Nicolas", "type": "question", "inv": inv,
                              "fields": {"text": "What does the record say?"}}, T_NIC)
    assert st == 200 and out["by"] == "nicolas"


def test_without_tokens_behaviour_is_unchanged(tmp_path):
    g = Graph(str(tmp_path / "open.hypgraph"), policy=Policy(extra_reserved={"harness"}))
    srv = make_server(g, port=0, writable=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    try:
        fields = {"title": "A test of the token layer.", "objective": "Check who may write."}
        st, out, _ = _write(url, {"op": "create", "author": "ada", "type": "investigation", "fields": fields})
        assert st == 200, out
        st, out, _ = _write(url, {"op": "create", "author": "harness", "type": "investigation", "fields": fields})
        assert st == 403 and "reserved" in out["detail"]          # extra_reserved joins the reserved set
    finally:
        srv.shutdown()


def test_parse_tokens(tmp_path):
    f = tmp_path / "tokens"
    f.write_text("# comment\nfile-secret-0123456789abc=alpha, Beta\n\n", encoding="utf-8")
    t = parse_tokens([f"{T_ANY}", f"{T_NIC}=nicolas"], str(f))
    assert t[T_ANY] == frozenset({"*"}) and t[T_NIC] == frozenset({"nicolas"})
    assert t["file-secret-0123456789abc"] == frozenset({"alpha", "beta"})
    with pytest.raises(ValueError):
        parse_tokens(["short"])

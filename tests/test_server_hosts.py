"""Which Host headers `serve` answers to. Bound to loopback: loopback names. Bound to a wildcard (a container
with a published port): loopback names too — the browser reaches the published port as 127.0.0.1:<host port>, and
the bind address is never a name a browser sends. Anything else is 421, unless --allow-host names it."""
import threading
import urllib.error
import urllib.request

import pytest

from hypgraph import Graph
from hypgraph.server import accepted_hosts, make_server


def _get(url, host_header):
    req = urllib.request.Request(f"{url}/api/graph/investigations", headers={"Host": host_header})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


@pytest.fixture
def serve_on(tmp_path):
    servers = []

    def start(host, **kw):
        g = Graph(str(tmp_path / f"{len(servers)}.hypgraph"))
        srv = make_server(g, host, port=0, **kw)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers.append(srv)
        return f"http://127.0.0.1:{srv.server_address[1]}"

    yield start
    for srv in servers:
        srv.shutdown()


def test_accepted_hosts_rules():
    assert accepted_hosts("127.0.0.1") == {"127.0.0.1", "localhost", "::1"}
    assert accepted_hosts("0.0.0.0") == {"127.0.0.1", "localhost", "::1"}          # the bind address is not a name
    assert accepted_hosts("::") == {"127.0.0.1", "localhost", "::1"}
    assert accepted_hosts("lab.local") == {"lab.local"}                           # a real name: that name only
    assert accepted_hosts("0.0.0.0", ["Swarm.Internal", " "]) == {"127.0.0.1", "localhost", "::1", "swarm.internal"}


def test_loopback_bind_answers_loopback_names_and_refuses_others(serve_on):
    url = serve_on("127.0.0.1")
    assert _get(url, "127.0.0.1:9") == 200          # the port is not part of the check
    assert _get(url, "localhost") == 200
    assert _get(url, "evil.example") == 421


def test_wildcard_bind_answers_loopback_through_a_published_port(serve_on):
    url = serve_on("0.0.0.0")
    assert _get(url, "127.0.0.1:8100") == 200       # the host side of a container's published port
    assert _get(url, "localhost:8100") == 200
    assert _get(url, "0.0.0.0:8000") == 421         # no browser sends the bind address; a rebinding page might
    assert _get(url, "evil.example") == 421


def test_allow_host_adds_a_name(serve_on):
    url = serve_on("0.0.0.0", allow_hosts=["swarm.internal"])
    assert _get(url, "swarm.internal:8000") == 200
    assert _get(url, "other.internal") == 421

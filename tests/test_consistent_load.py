"""A snapshot is loaded at one moment. Two Graphs on one file — hypswarm's scheduler and the MCP server a person's
agent works through, one process, two threads — used to tear a load: each table was its own implicit read, so a node
and its edge committed between the ``nodes`` read and the ``edges`` read left the edge naming a node the snapshot
didn't hold; the edge was skipped and its mark advanced past it, and that Graph never saw the edge again until a
rebuild. On Ubuntu CI the scheduler then found "no live claim" on a question every other Graph showed answered,
reworked the order, and asked the external seat to count again (2026-11-05 to 11-08)."""
import sqlite3
import threading
import time

from hypgraph import Graph


class _Interleave:
    """A connection whose first read of ``edges`` lets a hook run first — the window the other Graph writes into."""

    def __init__(self, con: sqlite3.Connection, hook) -> None:
        object.__setattr__(self, "_con", con)
        object.__setattr__(self, "_hook", hook)
        object.__setattr__(self, "_fired", False)

    def execute(self, sql, *args):
        if "FROM edges" in sql and not self._fired:
            object.__setattr__(self, "_fired", True)
            self._hook()
        return self._con.execute(sql, *args)

    def __getattr__(self, name):
        return getattr(self._con, name)

    def __setattr__(self, name, value):
        setattr(self._con, name, value)


def _produced(g: Graph, run: str) -> list[str]:
    return sorted(e["dst"] for e in g.snapshot().out.get(run, []) if e["rel"] == "produced")


def test_a_row_committed_during_a_load_is_seen_by_the_next_one(tmp_path):
    db = tmp_path / "g.hypgraph"
    a, b = Graph(db), Graph(db)
    inv = a.create(author="importer", type="investigation",
                   fields={"title": "Two readers", "objective": "A load must not lose what lands beside it."})["id"]
    run = a.create(author="importer", type="run", inv=inv, fields={"kind": "agent", "state": "succeeded"})["id"]
    a.snapshot()                                                    # a holds a snapshot: the next load is a delta
    b.create(author="importer", type="source", inv=inv, fields={"citation": "Someone, a paper, 2026."})
    #                                                               # b changed the file: a's next snapshot() loads

    def write_from_b():
        b.create(author="ana", type="result", inv=inv, links=[{"rel": "produced", "from": run}],
                 fields={"summary": "Counted the items.", "kind": "computed", "values": {"m": {"k": 40, "n": 90}}})

    t = threading.Thread(target=write_from_b)

    def hook():
        t.start()                                                   # b commits a result and its edge — now, if the
        time.sleep(0.3)                                             # load lets it; after the load, if it doesn't

    a._local.con = _Interleave(a._connect(), hook)
    a.snapshot()                                                    # the load with the window in it
    t.join(timeout=15)
    assert not t.is_alive()
    assert not a._connect().in_transaction                         # the load left no transaction open
    assert _produced(a, run) == _produced(Graph(db), run) != []    # a sees the edge a rebuild sees


def test_a_load_inside_a_write_joins_its_transaction(tmp_path):
    g = Graph(tmp_path / "g.hypgraph")
    con = g._connect()
    con.execute("BEGIN IMMEDIATE")
    try:
        g._invalidate()
        g.snapshot()                                                # a rebuild inside an open transaction
        assert con.in_transaction                                   # still ours: the load did not commit it
    finally:
        con.execute("ROLLBACK")

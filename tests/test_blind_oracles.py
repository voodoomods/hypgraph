"""A sealed checker can't learn what is sealed by asking: every request it can make answers the same whether its guess
of a sealed value is right or wrong (an adversarial test on a live mesh, 2026-10-30, found six routes that marked a
right guess as "[sealed]", and claim checks that accepted a right guess and refused a wrong one).

Each case runs on its own fresh record twice, once with the sealed reading and once with a wrong one, through
``blind.dispatch`` as a host serves the checker (its own nodes kept), and the two answers must be identical once the
guess itself and fresh ids are blanked."""
import re
from datetime import datetime, timedelta

import pytest

from hypgraph import Graph, Policy
from hypgraph import blind as B

R, WRONG = 48213, 48220
WORD = "quillotine"


class Clock:
    def __init__(self):
        self.t = datetime(2026, 1, 1, 9, 0, 0)

    def __call__(self):
        self.t += timedelta(seconds=1)
        return self.t.isoformat(timespec="seconds")


def fixture():
    """The lead read the instrument (R) and holds it in a hypothesis, a result and a bound claim; the checker has a
    blind order and its own run."""
    g = Graph(policy=Policy(reviewers={"critic"}), clock=Clock())
    lead = g.author("lead")
    inv = lead.investigation("Read the instrument", "Record the instrument's reading and have it checked blind.")["id"]
    h1 = lead.add("hypothesis", inv, statement=f"The instrument reads {R}, codeword {WORD}.",
                  predictions=[f"A second reading gives {R}."])["id"]
    run = lead.add("run", inv, kind="agent", name=f"read by {WORD}", state="succeeded")["id"]
    rs1 = lead.add("result", inv, summary=f"The instrument read {R} ({WORD}).", outcome="positive",
                   values={"reading": R},
                   links=[{"rel": "produced", "from": run}, {"rel": "supports", "to": h1, "why": "the reading it predicts"}])["id"]
    lead.add("claim", inv, statement=f"The instrument reads {R}.", kind="finding",
             scope="One reading of the instrument, taken by the lead.",
             measurements=[{"result": rs1, "key": "reading"}], links=[{"rel": "supports", "from": rs1, "why": "it measured it"}])
    o = g.issue_work(author="lead", inv=inv, target="H1", assignee="checker", blind=True,
                     objective="Take your own reading of the instrument and record it as a result named reading.")
    mine = g.author("checker").add("run", inv, kind="agent", name="my own reading", state="succeeded")["id"]
    return g, {"inv": inv, "h1": h1, "rs1": rs1, "run": run, "order": o["order"], "mine": mine}


def own(g):
    return lambda i, n: n["created_by"] == "checker"


def ask(g, method, path, body=None, query=None):
    return B.dispatch(g, method, path, query=query, body=body, keep=own(g), writable=True)


def write(g, body):
    return ask(g, "POST", "/write", {"author": "checker", **body})


# every request a checker might make with a guess in it: (name, fn(g, ids, x) -> (status, answer))
CASES = {
    "resolve": lambda g, i, x: ask(g, "GET", "/resolve", query={"ref": str(x)}),
    "node": lambda g, i, x: ask(g, "GET", f"/node/{x}"),
    "why": lambda g, i, x: ask(g, "GET", f"/why/{x}"),
    "order": lambda g, i, x: ask(g, "GET", f"/order/{x}"),
    "search": lambda g, i, x: ask(g, "GET", "/search", query={"text": str(x)}),
    "check_work text": lambda g, i, x: ask(g, "POST", "/check_work", {"order": i["order"], "text": f"I read {x}."}),
    "check_work order": lambda g, i, x: ask(g, "POST", "/check_work", {"order": str(x)}),
    "bad type": lambda g, i, x: write(g, {"op": "create", "type": f"t {x}", "inv": i["inv"], "fields": {}}),
    "bad field": lambda g, i, x: write(g, {"op": "create", "type": "result", "inv": i["inv"],
                                           "fields": {"summary": f"read {x}", "outcome": "positive", "zz": f"{x} x"}}),
    "claim bound to the sealed result": lambda g, i, x: write(g, {
        "op": "create", "type": "claim", "inv": i["inv"],
        "fields": {"statement": f"The instrument reads {x}.", "scope": "My reading of the instrument, taken once.",
                   "kind": "finding", "measurements": [{"result": i["rs1"], "key": "reading"}]},
        "links": [{"rel": "supports", "from": i["rs1"], "why": "the reading it measured"}]}),
    "claim with an unbound number": lambda g, i, x: write(g, {
        "op": "create", "type": "claim", "inv": i["inv"],
        "fields": {"statement": f"The instrument reads {x}.", "scope": "My reading of the instrument, taken once.",
                   "kind": "finding"}}),
    "claim by code": lambda g, i, x: write(g, {
        "op": "create", "type": "claim", "inv": i["inv"],
        "fields": {"statement": f"The instrument reads {x}.", "scope": "My reading of the instrument, taken once.",
                   "kind": "finding", "measurements": [{"result": "RS1", "key": "reading"}]}}),
    "result supporting the target": lambda g, i, x: write(g, {
        "op": "create", "type": "result", "inv": i["inv"],
        "fields": {"summary": f"My reading is {x}.", "outcome": "positive", "values": {"reading": x}},
        "links": [{"rel": "produced", "from": i["mine"]}, {"rel": "supports", "to": i["h1"], "why": "the reading it predicts"}]}),
    "result challenging the target": lambda g, i, x: write(g, {
        "op": "create", "type": "result", "inv": i["inv"],
        "fields": {"summary": f"My reading is {x}.", "outcome": "positive", "values": {"reading": x}},
        "links": [{"rel": "produced", "from": i["mine"]}, {"rel": "challenges", "to": i["h1"], "why": "a different reading"}]}),
    "result replicating the sealed one": lambda g, i, x: write(g, {
        "op": "create", "type": "result", "inv": i["inv"],
        "fields": {"summary": f"My reading is {x}.", "outcome": "positive", "values": {"reading": x}},
        "links": [{"rel": "produced", "from": i["mine"]}, {"rel": "replicates", "to": i["rs1"], "why": "same reading"}]}),
    "review of the sealed result": lambda g, i, x: write(g, {
        "op": "review", "target": i["rs1"], "verdict": "pass", "method": "re-read the instrument",
        "notes": f"I read {x}, the same."}),
    "review of the target": lambda g, i, x: write(g, {
        "op": "review", "target": i["h1"], "verdict": "pass", "method": "re-read the instrument",
        "notes": f"I read {x}, the same."}),
    "blind order to another seat": lambda g, i, x: write(g, {
        "op": "issue_work", "inv": i["inv"], "target": i["mine"], "assignee": "third", "blind": True,
        "objective": f"Check that the instrument reads {x}, with a reading of your own."}),
    "order on the target": lambda g, i, x: write(g, {
        "op": "issue_work", "inv": i["inv"], "target": i["h1"], "assignee": "third",
        "objective": f"Check that the instrument reads {x}, with a reading of your own."}),
}


def run_case(fn, x):
    g, ids = fixture()
    status, out = fn(g, ids, x)
    # the checker's own new node as it then reads it, with its derived state (a right guess must not show there)
    after = []
    if status == 200 and isinstance(out, dict) and out.get("id") in g.snapshot().nodes:
        after = ask(g, "GET", f"/node/{out['id']}")
    return status, out, after


def norm(x, guess):
    t = repr(x)
    t = t.replace(f"{guess:,}", "<X>").replace(str(guess), "<X>")
    t = re.sub(r"\bn[0-9a-f]{12}\b", "<N>", t)
    t = re.sub(r"\binv-[0-9a-f]{8}\b", "<INV>", t)
    t = re.sub(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", "<T>", t)
    return t


@pytest.mark.parametrize("name", list(CASES))
def test_a_right_guess_answers_like_a_wrong_one(name):
    right, wrong = run_case(CASES[name], R), run_case(CASES[name], WRONG)
    assert norm(right, R) == norm(wrong, WRONG), f"{name}: the answer tells a right guess from a wrong one"


def test_no_answer_carries_sealed_words():
    for name, fn in CASES.items():
        for x in (R, WRONG):
            assert WORD not in repr(run_case(fn, x)), f"{name} quotes sealed text"


def test_a_sealed_checker_still_does_its_work():
    """The fixes refuse nothing the order needs: a result of its own that supports or tests the target."""
    for name in ("result supporting the target", "result challenging the target"):
        status, out, _ = run_case(CASES[name], WRONG)
        assert status == 200, (name, out)


def test_a_host_view_seals_writes_under_another_name():
    """A host seals by reader (HypMesh: the agent token), and a token may write under several names. The write is
    checked against the reader's view, so a name with no blind order of its own learns no more."""
    def as_alias(x):
        g, i = fixture()
        return ask(g, "POST", "/write", {"author": "alias", "op": "create", "type": "claim", "inv": i["inv"],
                                         "fields": {"statement": f"The instrument reads {x}.", "kind": "finding",
                                                    "scope": "My reading of the instrument, taken once.",
                                                    "measurements": [{"result": i["rs1"], "key": "reading"}]}})
    right, wrong = as_alias(R), as_alias(WRONG)
    assert right[0] == 400 and "sealed from you" in right[1]["detail"]
    assert norm(right, R) == norm(wrong, WRONG)
    g, i = fixture()                                  # with no host view, plain hypgraph takes the name at its word
    with pytest.raises(Exception, match="link the evidence|refused"):
        g.create(author="alias", type="claim", inv=i["inv"], fields={
            "statement": f"The instrument reads {WRONG}.", "kind": "finding", "scope": "A reading, taken once.",
            "measurements": [{"result": i["rs1"], "key": "reading"}]})


def test_the_mcp_seat_answers_a_right_guess_like_a_wrong_one(tmp_path):
    import asyncio
    fastmcp = pytest.importorskip("fastmcp")
    from hypgraph.mcp import build

    def seat(x):
        g, i = fixture()
        out = []

        async def go():
            async with fastmcp.Client(build(g, author="checker")) as c:
                for name, args in (("show", {"node": str(x)}),
                                   ("add", {"type": "result", "investigation": i["inv"],
                                            "fields": {"summary": f"My reading is {x}.", "outcome": "positive",
                                                       "values": {"reading": x}},
                                            "links": [{"rel": "supports", "to": "H1", "why": "the reading it predicts"}]})):
                    r = await c.call_tool(name, args, raise_on_error=False)
                    out.append((r.is_error, r.content[0].text))
        asyncio.run(go())
        return out
    assert norm(seat(R), R) == norm(seat(WRONG), WRONG)

"""Under a workflow, a result whose run names no file it read (no ``uses``) can't show it read the new version of a
file that changed after it — so it goes stale then, like a result that named the old file. Results written after the
change, results that name their files, files of another question, run outputs, page excerpts and investigations with
no workflow are untouched."""
from hypgraph import Graph, Policy

H = "harness"
SHA_A, SHA_B, SHA_C = "a1" * 32, "b2" * 32, "c3" * 32


def _g(profile="scientific@2"):
    g = Graph(policy=Policy(reviewers={"critic"}, extra_reserved={H}))
    fields = {"title": "Does A beat B on the items?", "objective": "Count each model's correct items on the file."}
    if profile:
        fields["profile"] = profile
    inv = g.create(author=H, type="investigation", fields=fields)["id"]
    q1 = g.create(author=H, type="question", inv=inv, code="Q1", fields={"text": "Is A right more often than B?"})["id"]
    return g, inv, q1


def _file(g, inv, sha, on=None, supersedes=None, kind=""):
    fields = {"sha256": sha, "path": "items.csv"}
    if kind:
        fields["kind"] = kind
    links = [{"rel": "part_of", "to": on}] if on else []
    if supersedes:
        links.append({"rel": "supersedes", "to": supersedes})
    return g.create(author="vendor", type="artifact", inv=inv, fields=fields, links=links)["id"]


def _result(g, inv, q, uses=None):
    run = g.create(author="analyst", type="run", inv=inv, fields={"kind": "agent", "name": "count", "state": "succeeded"},
                   links=[{"rel": "uses", "to": u, "data": {"role": "data"}} for u in uses or []])["id"]
    rs = g.create(author="analyst", type="result", inv=inv, fields={"summary": "Counted the correct items per model.",
                  "values": {"a_correct": {"value": 827}}, "outcome": "positive"},
                  links=[{"rel": "produced", "from": run}])["id"]
    c = g.create(author="analyst", type="claim", inv=inv, fields={"statement": "Model A is right more often than B.",
                 "scope": "The items file as the vendor sent it."},
                 links=[{"rel": "answers", "to": q}, {"rel": "derived_from", "to": rs}])["id"]
    return rs, c


def test_a_result_naming_no_file_goes_stale_when_a_file_changes_after_it():
    g, inv, q = _g()
    a1 = _file(g, inv, SHA_A)
    rs, c = _result(g, inv, q)
    assert not g.state(rs).get("stale")
    a2 = _file(g, inv, SHA_B, supersedes=a1)
    why = g.state(rs)["stale"]
    assert why and "names no file it read" in why[0] and g.get(a1)["code"] in why[0]
    assert g.state(c).get("stale")                                   # the claim rests on it, so it is stale too
    # a result written after the change could have read the new file: fresh
    rs2, c2 = _result(g, inv, q)
    assert not g.state(rs2).get("stale") and not g.state(c2).get("stale")
    # withdrawing a file counts the same as replacing it
    g2, inv2, p = _g()
    b1 = _file(g2, inv2, SHA_A)
    rs3, _ = _result(g2, inv2, p)
    g2.withdraw(author="vendor", node=b1, why="the vendor pulled the file")
    assert g2.state(rs3).get("stale")
    assert a2


def test_a_result_that_names_its_files_follows_the_usual_rule():
    g, inv, q = _g()
    a1 = _file(g, inv, SHA_A)
    other = g.create(author="vendor", type="artifact", inv=inv, fields={"sha256": SHA_C, "path": "labels.csv"})["id"]
    rs, _ = _result(g, inv, q, uses=[a1])
    _file(g, inv, SHA_B, supersedes=other)                       # a file it didn't use changed: still fresh
    assert not g.state(rs).get("stale")
    _file(g, inv, "d4" * 32, supersedes=a1)                      # the file it used changed: stale, the usual way
    assert "is superseded" in g.state(rs)["stale"][0]


def test_files_of_another_question_run_outputs_and_excerpts_do_not_count():
    g, inv, q1 = _g()
    q2 = g.create(author=H, type="question", inv=inv, code="Q2", fields={"text": "How many items is B right on?"})["id"]
    f2 = _file(g, inv, SHA_A, on=q2)
    out = g.create(author="analyst", type="artifact", inv=inv, fields={"sha256": SHA_C, "path": "plot.png"})["id"]
    run = g.create(author="analyst", type="run", inv=inv, fields={"kind": "agent", "name": "plot", "state": "succeeded"},
                   links=[{"rel": "produced", "to": out}])["id"]
    rs, _ = _result(g, inv, q1)
    _file(g, inv, SHA_B, on=q2, supersedes=f2)                   # Q2's file: not Q1's result's business
    g.create(author="analyst", type="artifact", inv=inv, fields={"sha256": "e5" * 32, "path": "plot.png"},
             links=[{"rel": "supersedes", "to": out}])          # a run's output replaced: not an input
    assert run and not g.state(rs).get("stale")


def test_no_workflow_no_rule():
    g, inv, q = _g(profile="")
    a1 = _file(g, inv, SHA_A)
    rs, _ = _result(g, inv, q)
    _file(g, inv, SHA_B, supersedes=a1)
    assert not g.state(rs).get("stale")

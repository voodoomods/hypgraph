"""The engine, ported from PegasusDMZ's research graph suite: append-only and tamper-evident, typed edges enforced,
status derived (review pinned to versions, risk, support, independence, evidence profile), and the claim checks catch
the error classes they were written for."""
import sqlite3

import pytest

from hypgraph import Graph, GraphError, Policy

BOARD = {"fisher", "proof", "bench", "skeptic", "popper", "steward"}


@pytest.fixture
def g(tmp_path):
    graph = Graph(tmp_path / "graph.db", policy=Policy(reviewers=BOARD))
    yield graph
    graph.close()


@pytest.fixture
def inv(g):
    return g.create(author="turing", type="investigation", fields={
        "title": "Test cipher", "objective": "Find out whether the test cipher can be read under the hypothesis.",
        "constants": [196, 182, 14], "reviewers": ["turing"]})["id"]


def result(g, inv, values, author="welchman", **body):
    return g.create(author=author, type="result", inv=inv, fields={"summary": "A measured outcome of the search.",
                                                                    "values": values, **body})["id"]


def claim(g, inv, statement, support, author="friedman", **body):
    links = [{"rel": "supports", "from": s, "why": "this result is the measurement the claim states"} for s in support]
    body.setdefault("scope", "In the 182-symbol practice ciphers of this test, under the six-symbol score.")
    return g.create(author=author, type="claim", inv=inv, fields={"statement": statement, **body}, links=links)


def M(name, rid, key, **kw):
    return {"name": name, "result": rid, "key": key, **kw}


# ── structure ─────────────────────────────────────────────────────

def test_edges_join_only_the_types_they_allow(g, inv):
    h = g.create(author="turing", type="hypothesis", inv=inv,
                 fields={"statement": "A turning grille over a balanced table.", "predictions": ["no lag order"]})
    x = g.create(author="turing", type="experiment", inv=inv, links=[
        {"rel": "tests", "to": h["id"], "data": {"expected": "planted grille recovered"}}],
        fields={"aim": "Recover planted grilles with the table given.", "protocol": "Anneal orbits; 6 plants.",
                "success_criteria": "45 of 49 orbits right."})
    assert x["out"][0]["rel"] == "tests"
    with pytest.raises(GraphError, match="can't join"):
        g.link(author="turing", src=h["id"], rel="executes", dst=x["id"])
    with pytest.raises(GraphError, match="expected"):
        g.create(author="turing", type="experiment", inv=inv, links=[{"rel": "tests", "to": h["id"]}],
                 fields={"aim": "Another test of the grille.", "protocol": "Anneal orbits on six planted grilles.",
                         "success_criteria": "45 of 49 orbits right."})
    r = result(g, inv, {"x": 1})
    with pytest.raises(GraphError, match="say why"):
        g.link(author="turing", src=r, rel="supports", dst=h["id"])
    run, run2 = (g.create(author="welchman", type="run", inv=inv, fields={"kind": "agent"})["id"] for _ in range(2))
    with pytest.raises(GraphError, match="differs"):
        g.link(author="welchman", src=run2, rel="replicates", dst=run)


def test_append_only_and_the_chain_catches_tampering(g, inv, tmp_path):
    h = g.create(author="turing", type="hypothesis", inv=inv,
                 fields={"statement": "A turning grille over a balanced table.", "predictions": ["no lag order"]})
    con = sqlite3.connect(g.path)
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("UPDATE versions SET body='{}' WHERE node=?", (h["id"],))
    with pytest.raises(sqlite3.DatabaseError, match="append-only"):
        con.execute("DELETE FROM events")
    assert g.verify_chain()["ok"]
    con.execute("DROP TRIGGER versions_no_update")                     # someone with file access bypasses it
    con.execute("UPDATE versions SET body=? WHERE node=?", ('{"statement":"rewritten history"}', h["id"]))
    con.commit()
    v = g.verify_chain()
    assert not v["ok"] and "differs from its event" in v["problem"]
    assert not [n for n in dir(g) if n.startswith(("update", "delete", "edit"))]
    con.close()


def test_rolled_back_write_leaves_no_phantom(g, inv):
    with pytest.raises(GraphError):
        g.create(author="kahn", type="claim", inv=inv, fields={"statement": "Nothing supports this claim at all."})
    assert g.stats()["by_type"] == {"investigation": 1}


# ── review, risk, support ─────────────────────────────────────────

def test_review_is_pinned_to_a_version(g, inv):
    r = result(g, inv, {"kept": {"k": 22, "n": 200}})
    c = claim(g, inv, "The search kept the true table in 22 of 200 practice ciphers.", [r],
              measurements=[M("kept", r, "kept", k=22, n=200)])["id"]
    assert g.get(c)["state"]["review"]["state"] == "unchecked"
    own = claim(g, inv, "The search kept the true table in 22 of 200 practice ciphers.", [r], author="turing",
                measurements=[M("kept", r, "kept", k=22, n=200)])["id"]
    with pytest.raises(GraphError, match="own work"):                  # turing is a reviewer of this investigation
        g.review(author="turing", target=own, verdict="checked", method="recounted from the stored result", notes="checked my own numbers")
    g.review(author="kahn", target=c, verdict="checked", method="read the claim and its result", notes="looks right to me, not a reviewer")
    assert g.get(c)["state"]["review"]["state"] == "unchecked"           # a non-board review is a comment
    g.review(author="fisher", target=c, verdict="pass", method="recounted from the stored result", notes="22/200 holds")
    assert g.get(c)["state"]["review"]["state"] == "checked"
    g.revise(author="friedman", node=c, fields={"limitations": "Only the six-symbol score was tested here."},
             reason="added the limitation the reviewer asked for")
    st = g.get(c)["state"]
    assert st["review"]["state"] == "needs_revalidation" and "not yet re-checked" in st["sentence"]
    g.review(author="fisher", target=c, verdict="objection", method="re-read the limitation", notes="the limitation is too narrow")
    assert g.get(c)["state"]["review"]["state"] == "contested"
    g.review(author="fisher", target=c, verdict="resolved", method="re-read the limitation", notes="fixed in discussion")
    g.review(author="fisher", target=c, verdict="pass", method="recounted from the stored result", notes="22/200 holds on v2")
    assert g.get(c)["state"]["review"]["state"] == "checked"


def test_risk_and_support_propagate(g, inv):
    r1 = result(g, inv, {"a": 1})
    premise = claim(g, inv, "The message columns hold the message, column 14 the padding.", [r1])["id"]
    r2 = result(g, inv, {"b": 2})
    built = g.create(author="turing", type="claim", inv=inv, links=[
        {"rel": "requires", "to": premise},
        {"rel": "supports", "from": r2, "why": "the grille search ran on the message columns"}],
        fields={"statement": "The grille search covers the message columns.",
                "scope": "Under the padding reading of column 14."})["id"]
    g.withdraw(author="friedman", node=premise, why="column 14 turned out to carry message symbols")
    st = g.get(built)["state"]
    assert st["at_risk"] == [premise] and "AT RISK" in st["sentence"]
    assert any(d["node"]["id"] == built for d in g.impact(premise)["dependents"])
    g.withdraw(author="welchman", node=r2, why="the run behind it used the wrong framing")
    assert g.get(built)["state"]["unsupported"]
    run = g.create(author="welchman", type="run", inv=inv, fields={"kind": "agent", "state": "failed"})["id"]
    r3 = g.create(author="welchman", type="result", inv=inv, links=[{"rel": "produced", "from": run}],
                  fields={"summary": "Output of a run that crashed halfway."})["id"]
    assert g.get(r3)["state"]["at_risk"] == [run]


def test_independence_and_evidence_profile(g, inv):
    data = g.create(author="welchman", type="artifact", inv=inv, fields={"sha256": "ab" * 32, "path": "/lab/x.json"})
    assert g.create(author="kahn", type="artifact", inv=inv, fields={"sha256": "ab" * 32})["id"] == data["id"]
    runs = [g.create(author=who, type="run", inv=inv, fields={"kind": k},          # the lab files its own runs
                     links=[{"rel": "uses", "to": data["id"], "data": {"role": "data"}}])["id"]
            for who, k in (("lab", "lab"), ("welchman", "agent"))]
    rs = [g.create(author=who, type="result", inv=inv, links=[{"rel": "produced", "from": r}],
                   fields={"summary": "A result computed from the shared file."})["id"]
          for who, r in zip(("lab", "welchman"), runs)]
    c = claim(g, inv, "The truth is rarely kept at the cipher's length.", rs)["id"]
    st = g.get(c)["state"]
    assert st["independent_lines"] == 1                                   # same data artifact → one line
    assert st["evidence"] == "lab_recorded" and "no external replication" in st["sentence"]
    other = g.create(author="welchman", type="artifact", inv=inv, fields={"sha256": "cd" * 32})["id"]
    run3 = g.create(author="proof", type="run", inv=inv, fields={"kind": "agent"},
                    links=[{"rel": "uses", "to": other, "data": {"role": "data"}},
                           {"rel": "replicates", "to": runs[0], "data": {"differs": "new_impl"}}])["id"]
    r3 = g.create(author="proof", type="result", inv=inv, links=[{"rel": "produced", "from": run3}],
                  fields={"summary": "Separate implementation on its own data."})["id"]
    g.link(author="proof", src=r3, rel="supports", dst=c, why="a separately written check agrees")
    st = g.get(c)["state"]
    assert st["independent_lines"] == 2 and st["evidence"] == "separate_implementation"
    loose = [result(g, inv, {"x": i}) for i in range(3)]                     # no provenance at all
    c2 = claim(g, inv, "Several reports say the column is padding.", loose)["id"]
    assert g.get(c2)["state"]["independent_lines"] == 1                  # can't tell them apart → one line


# ── the claim checks (the D'Agapeyeff errors) ─────────────────────

def test_numbers_must_match_their_results(g, inv):
    r = result(g, inv, {"exact6": {"k": 5, "n": 6}, "ge45": {"k": 6, "n": 6}})
    with pytest.raises(GraphError, match="says k=6 but result"):        # F73: "all 49 on 6/6" when 5 were exact
        claim(g, inv, "Six-symbol scoring recovered all 49 orbits in 6 of 6 practice ciphers.", [r],
              measurements=[M("exact", r, "exact6", k=6, n=6)])
    ok = claim(g, inv, "Six-symbol scoring recovered at least 45 of 49 orbits in 6 of 6 practice ciphers, 5 exactly.", [r],
               scope="In 6 practice ciphers with the table given; a grille counts as recovered at 45 of 49 orbits.",
               measurements=[M("recovered", r, "ge45", k=6, n=6), M("exact", r, "exact6", k=5, n=6)])
    assert ok["type"] == "claim"


def test_range_and_absolutes_are_checked(g, inv):
    letters = result(g, inv, {"english": {"lo": 18, "hi": 25, "value": 22}})
    with pytest.raises(GraphError, match="17, 22|17"):                   # "17 to 22" vs measured 18–25
        claim(g, inv, "Natural passages use 17 to 22 different letters.", [letters],
              measurements=[M("letters", letters, "english", lo=18, hi=25)])
    flat = result(g, inv, {"merges": {"k": 1, "n": 1000}})
    with pytest.raises(GraphError, match="'never' is absolute"):        # "never" when it happened 1 in 1,000
        claim(g, inv, "Random merges never match the flatness.", [flat],
              measurements=[M("merges", flat, "merges", k=1, n=1000)])
    assert claim(g, inv, "Random merges matched the flatness in 1 of 1000 passages.", [flat],
                 measurements=[M("merges", flat, "merges", k=1, n=1000)])["type"] == "claim"


def test_spelled_out_numbers_are_checked(g, inv):
    r = result(g, inv, {"grille_exact": {"value": 1}})
    with pytest.raises(GraphError, match="two"):                         # I47: "two ciphers" where the record had one
        claim(g, inv, "On two practice ciphers whose grille was recovered exactly, repair drifted.", [r],
              measurements=[M("grille exact", r, "grille_exact", value=1)])


def test_exclusions_need_power_and_conventions_dont_hedge(g, inv):
    weak = result(g, inv, {"recovered": {"k": 0, "n": 3}}, outcome="negative")
    with pytest.raises(GraphError, match="planted answer"):
        claim(g, inv, "The joint search excludes the system.", [weak], kind="exclusion")
    strong = result(g, inv, {"recovered": {"k": 0, "n": 3}}, outcome="negative", power="demonstrated")
    assert claim(g, inv, "The keyed search excludes the system.", [strong], kind="exclusion")["type"] == "claim"
    with pytest.raises(GraphError, match="convention"):
        g.create(author="turing", type="claim", inv=inv, fields={"statement": "Column 14 could be padding.",
                                                                 "kind": "convention"})


def test_strict_off_and_importer_are_not_gated(g, inv):
    lax = g.create(author="turing", type="investigation", fields={"title": "Scratch", "strict_claims": False,
                                                                  "objective": "Rough notes while exploring."})["id"]
    r = result(g, lax, {"x": 1})
    assert claim(g, lax, "It was never like this, all 17 times.", [r], scope="")["type"] == "claim"
    assert g.create(author="importer", type="claim", inv=inv,
                    fields={"statement": "Legacy entry 17 to 22, imported as written."})["type"] == "claim"


# ── coordination ──────────────────────────────────────────────────

def test_leases_show_who_is_on_it(g, inv):
    h = g.create(author="turing", type="hypothesis", inv=inv,
                 fields={"statement": "A purpose-built four-square key.", "predictions": ["13 cells, flat"]})["id"]
    g.lease(author="welchman", node=h, task="t-1", minutes=60)
    with pytest.raises(GraphError, match="welchman is on it"):
        g.lease(author="rejewski", node=h)
    assert "being worked by welchman" in g.get(h)["state"]["sentence"]
    assert g.work_map(inv)["leases"][0]["agent"] == "welchman"
    g.lease(author="welchman", node=h, release=True)
    assert g.lease(author="rejewski", node=h)["state"]["lease"]["agent"] == "rejewski"


def test_next_experiment_prefers_discriminating_powered_cheap_work(g, inv):
    h1, h2 = (g.create(author="turing", type="hypothesis", inv=inv,
                       fields={"statement": s, "predictions": ["p"]})["id"]
              for s in ("Turning grille over a balanced table.", "Purpose-built four-square key."))

    def X(aim, expected, **kw):
        return g.create(author="turing", type="experiment", inv=inv, fields={
            "aim": aim, "protocol": "Run it on plants and the real text.", "success_criteria": "Plants recovered.",
            **kw}, links=[{"rel": "tests", "to": h, "data": {"expected": e}} for h, e in zip((h1, h2), expected)])["id"]

    split = X("Lag-1 order test that tells the two apart.", ["no order", "pair order"], power_check="planted pairs",
              cost_minutes=10, method="lag order")
    same = X("Flatness test that both predict.", ["flat", "flat"], cost_minutes=10, method="flatness")
    X("Lag-1 order test that tells the two apart, again.", ["no order", "pair order"], cost_minutes=10,
      method="lag order")
    ranked = g.next_experiments(inv)["ranked"]
    assert ranked[0]["experiment"]["id"] == split and ranked[0]["separates"] == 2
    assert next(r for r in ranked if r["experiment"]["id"] == same)["separates"] == 1
    assert ranked[-1]["duplicate"]
    assert g.work_map(inv)["duplicates"]


def test_review_queue_and_revalidation(g, inv):
    r = result(g, inv, {"v": {"value": 3}})
    c = claim(g, inv, "The value was 3 in this run.", [r], measurements=[M("v", r, "v", value=3)])["id"]
    wm = g.work_map(inv)
    assert c in [x["id"] for x in wm["review_queue"]]
    g.withdraw(author="welchman", node=r, why="the run used the wrong input file")
    assert c in [x["id"] for x in g.work_map(inv)["revalidation"]]




def test_why_climbs_to_support_and_never_down_to_what_it_supports(g, inv):
    """F76 supports F77: Atlas showed F77 as something F76 'rests on'. Why goes upstream only."""
    r = result(g, inv, {"kept": {"k": 3, "n": 9}})
    c1 = claim(g, inv, "The search keeps the true table under the six-symbol score.", [r])["id"]
    c2 = claim(g, inv, "The score is usable as a ranking for candidate tables.", [c1])["id"]
    up = {n["id"] for n in g.why(c1)["nodes"]}
    assert r in up and c2 not in up
    assert c1 in {n["id"] for n in g.why(c2)["nodes"]}
    assert c2 in {d["node"]["id"] for d in g.impact(c1)["dependents"]}


def test_reads_after_writes_load_only_new_rows_and_match_a_full_rebuild(g, inv, monkeypatch):
    """A write leaves the snapshot; the next read loads just the new rows (a full rebuild reads the whole graph
    from the host mount, ~2.4 s). After every kind of write the result must equal a rebuild from scratch."""
    g.snapshot()
    rebuilds = []
    from hypgraph import derive
    real = g._rebuild
    monkeypatch.setattr(g, "_rebuild", lambda con: rebuilds.append(1) or real(con))

    def same_as_rebuild():
        s = g.snapshot()
        full = real(g._connect())
        view = lambda x: ({i: (n["v"], n["body"], n["code"], n["created_by"]) for i, n in x.nodes.items()},  # noqa
                          set(x.edges), set(x.withdrawn), set(x.leases), x.seq, len(x.events),
                          {k: len(v) for k, v in x.versions.items()},
                          {i: derive.state(x, i) for i in x.nodes})
        assert view(s) == view(full)

    r = result(g, inv, {"kept": {"k": 3, "n": 9}})
    same_as_rebuild()
    c = claim(g, inv, "The search keeps the true table under the six-symbol score.", [r])["id"]
    same_as_rebuild()
    h = g.create(author="turing", type="hypothesis", inv=inv,
                 fields={"statement": "A turning grille over a balanced table.", "predictions": ["no lag order"]})["id"]
    g.link(author="turing", src=r, rel="supports", dst=h, why="the kept rate is what the grille predicts")
    same_as_rebuild()
    g.revise(author="friedman", node=c, fields={"limitations": "Only the six-symbol score was tested."},
             reason="state the limit")
    g.review(author="fisher", target=c, verdict="pass", method="recounted from the stored result", notes="The stored result shows the 3 of 9 count the claim states.")
    g.lease(author="welchman", node=h, task="t1", note="testing the grille")
    same_as_rebuild()
    g.withdraw(author="turing", node=h, why="superseded by the balanced-table model")
    same_as_rebuild()
    assert rebuilds == []                                    # every read so far was a delta
    edge = next(x["id"] for x in g.snapshot().out[r] if x["rel"] == "supports" and x["dst"] == h)
    g.retract(author="turing", edge=edge, why="the hypothesis was withdrawn, so this link misleads")
    same_as_rebuild()
    assert len(rebuilds) == 1                                # a retraction removes rows: rebuilt once


def test_a_failed_write_leaves_no_trace_in_the_snapshot(g, inv):
    before = set(g.snapshot().nodes)
    with pytest.raises(GraphError):
        g.create(author="kahn", type="claim", inv=inv, fields={"statement": "Nothing supports this claim at all."})
    assert set(g.snapshot().nodes) == before


def test_lab_evidence_is_the_labs_to_give(g, inv):
    """Only the lab files lab-recorded runs; numbers an agent attaches to a lab run, an agent's 'external' run and a
    'cited' result citing nothing are reports, not stronger evidence."""
    with pytest.raises(GraphError, match="lab's own record"):
        g.create(author="welchman", type="run", inv=inv, fields={"kind": "lab"})
    own = g.create(author="welchman", type="run", inv=inv, fields={"kind": "agent"})["id"]
    with pytest.raises(GraphError, match="kind"):
        g.revise(author="welchman", node=own, fields={"kind": "lab"}, reason="make it look lab-recorded")
    lab_run = g.create(author="lab", type="run", inv=inv, fields={"kind": "lab", "state": "succeeded"})["id"]
    with pytest.raises(GraphError):
        g.create(author="welchman", type="result", inv=inv, links=[{"rel": "produced", "from": lab_run}],
                 fields={"summary": "Numbers typed in and hung on the lab's run."})
    derived = g.create(author="welchman", type="result", inv=inv, links=[{"rel": "derived_from", "to": lab_run}],
                       fields={"summary": "Numbers read off the lab run's output by hand."})["id"]
    ext = g.create(author="welchman", type="run", inv=inv, fields={"kind": "external"})["id"]
    from_ext = g.create(author="welchman", type="result", inv=inv, links=[{"rel": "produced", "from": ext}],
                        fields={"summary": "A run said to have been done elsewhere."})["id"]
    cited = g.create(author="welchman", type="result", inv=inv, fields={"summary": "Said to be published.",
                                                                       "kind": "cited"})["id"]
    for r, want in ((derived, "agent_reported"), (from_ext, "agent_reported"), (cited, "unverified")):
        c = claim(g, inv, "The search keeps the true table under the six-symbol score.", [r])["id"]
        assert g.get(c)["state"]["evidence"] == want, r


def test_a_decision_is_flagged_when_its_basis_changes(g, inv):
    r = result(g, inv, {"kept": {"k": 22, "n": 200}})
    c = claim(g, inv, "The search kept the true table in 22 of 200 practice ciphers.", [r],
              measurements=[M("kept", r, "kept")])["id"]
    d = g.create(author="turing", type="decision", inv=inv, links=[{"rel": "based_on", "to": c}], fields={
        "choice": "Stop widening the table search; spend the GPU on the grille order instead.",
        "reasons": "The kept rate is too low to make a wider search pay.", "meeting": "m1"})["id"]
    assert "basis_changed" not in g.get(d)["state"] and g.work_map(inv)["decisions_to_revisit"] == []
    g.revise(author="friedman", node=c, fields={"limitations": "Only the six-symbol score was tested here."},
             reason="state the limit")
    st = g.get(d)["state"]
    assert st["basis_changed"][0]["was_v"] == 1 and st["basis_changed"][0]["now_v"] == 2
    assert "REVISIT" in st["sentence"]
    assert [x["id"] for x in g.work_map(inv)["decisions_to_revisit"]] == [d]


def test_the_digest_counts_changes_and_backlog_in_open_investigations_only(g, inv):
    closed = g.create(author="importer", type="investigation", fields={
        "title": "Old study", "objective": "A finished study whose record is fixed now.", "state": "published"})["id"]
    r = result(g, inv, {"kept": {"k": 3, "n": 9}})
    c = claim(g, inv, "The search kept the true table in 3 of 9 practice ciphers.", [r],
              measurements=[M("kept", r, "kept")])["id"]
    g.review(author="fisher", target=c, verdict="objection", method="recounted the denominators",
             notes="The 9 includes two plants that were never run.")
    d = g.digest()
    assert d["new"]["claim"] == 1 and d["new"]["result"] == 1 and d["reviews"]["objections"] == 1
    assert [x["id"] for x in d["waiting"]["contested"]] == [c]
    assert closed not in {i["id"] for i in d["investigations"]}
    assert g.digest(since="2999-01-01T00:00:00+00:00")["new"] == {}


def test_quoted_digits_are_labels_not_numbers_to_bind(g, inv):
    rid = result(g, inv, {"p": {"value": 0.0363}})
    scope = "In the 197-pair text as printed, under the 10,000-shuffle null."
    ok = claim(g, inv, "A triple repeat of cell '63 63 63' sits just before the \"04\"; p = 0.0363.", [rid], scope=scope,
               measurements=[M("p", rid, "p", value=0.0363)])
    assert ok["type"] == "claim"
    with pytest.raises(GraphError, match="numbers in the statement"):
        claim(g, inv, "A triple repeat sits at pair 94 just before the anomaly; p = 0.0363.", [rid], scope=scope,
              measurements=[M("p", rid, "p", value=0.0363)])


def test_a_link_given_backwards_is_turned_round(g, inv):
    rid = result(g, inv, {"p": {"value": 0.5}})
    scope = "In the 197-pair text as printed, under the 10,000-shuffle null."
    c = g.create(author="friedman", type="claim", inv=inv, links=[{"rel": "supports", "to": rid, "why": "the result is "
                                                                    "the measurement behind this claim"}],
                 fields={"statement": "The halves do not differ; p = 0.5.", "scope": scope,
                         "measurements": [M("p", rid, "p", value=0.5)]})
    assert any("turned round" in n for n in c.get("notes", []))
    assert any(e["src"] == rid and e["rel"] == "supports" for e in g.snapshot().inn[c["id"]])
    h = g.create(author="turing", type="hypothesis", inv=inv, fields={
        "statement": "The cipher is a periodic substitution with a short key.",
        "predictions": ["Index of coincidence peaks at the key length."]})["id"]
    r = g.link(author="turing", src=h, rel="supports", dst=rid, why="the result bears on this hypothesis")
    assert r["flipped"] and r["src"] == rid and r["dst"] == h
    with pytest.raises(GraphError, match="can't join"):
        g.link(author="turing", src=h, rel="produced", dst=rid, why="no reading of this is valid at all")


def test_report_states_the_record_and_flags_what_is_unreviewed(g, inv):
    scope = "In the 197-pair text as printed, under the 10,000-shuffle null."
    r1 = result(g, inv, {"p": {"value": 0.5}})
    r2 = result(g, inv, {"p": {"value": 0.9}})                       # a conclusion no claim carries
    c1 = claim(g, inv, "The halves do not differ; p = 0.5.", [r1], scope=scope, measurements=[M("p", r1, "p", value=0.5)])
    c2 = claim(g, inv, "The halves look alike; p = 0.5.", [r1], scope=scope,
               measurements=[M("p", r1, "p", value=0.5)])
    g.review(author="fisher", target=c1["id"], verdict="fail", method="Recomputed the null with the grid constraint.",
             notes="The null ignores the grid; the p-value is circular.")
    g.withdraw(author="friedman", node=c2["id"], why="superseded by a corrected claim")
    rep = g.report(inv)
    codes = {c["code"]: c for c in rep["claims"]}
    assert codes[c1["code"]]["review"] == "contested" and "fisher: fail" in codes[c1["code"]]["verdicts"][0]
    assert codes[c2["code"]]["lifecycle"] == "withdrawn"
    r2code = next(x["code"] for x in rep["results"] if x["id"] == r2)
    assert r2code in rep["open"]["results_in_no_claim"] and c1["code"] in rep["open"]["claims_contested"]
    md = rep["markdown"]
    assert "do not edit" in md and "| NO |" in md and "withdrawn" in md

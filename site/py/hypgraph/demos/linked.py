"""
London's water, 1854–1866 — three records joined by pinned references.

A record is one trust boundary: one chain, one board. Records join into a network by *reference*: a ``source`` in
one record pins a node of another (its record URL, node, version and that version's hash; see
``hypgraph.references``). This demo builds three, as a teaching reconstruction:

- **Broad Street, 1854** — the ``broad_street`` demo, unchanged: Snow's inquiry and the water-company comparison.
- **East London, 1866** — Farr's inquiry into the 1866 epidemic, which followed the East London Water Company's
  supply. It is the follow-up Broad Street's X3 asks for, and it pins Broad Street's comparison (CL2) as what it
  repeats. The roles are simplified and no figures are given: the record states only what the inquiry is known for.
- **London's water, 1854–1866** — a synthesis that pins the claims of both, and asks whether the 1854 finding held
  in a later epidemic. Its claim rests on the other two records only through those pins.

So the synthesis cites Broad Street directly and through East London: a network, not a tree. The Explorer's graph
draws all three together, each pin checked against the cited record's own chain.

    from hypgraph.demos import linked
    records = linked.build()     # {"london": (graph, inv), "broad-street": (...), "east-london-1866": (...)}
"""

from __future__ import annotations

from ..graph import Graph
from ..policy import Policy
from ..references import pin
from . import broad_street
from .broad_street import DemoClock

# Where the website serves each record (examples/linked/); the pins name these URLs.
BASE = "https://hypgraph.com/examples/linked"
URLS = {"london": BASE, "broad-street": f"{BASE}/broad-street", "east-london-1866": f"{BASE}/east-london-1866"}
TITLES = {"london": "London's water, 1854–1866: did the finding hold?",
          "broad-street": broad_street.TITLE,
          "east-london-1866": "East London, 1866: the comparison repeated"}


def _code(g: Graph, inv: str, code: str) -> str:
    return next(nid for nid, n in g.snapshot().nodes.items() if n["inv"] == inv and n["code"] == code)


def _cite(author, inv: str, cited: Graph, nid: str, record: str, when: str, why: str) -> dict:
    """A source in this record that pins ``nid`` of ``cited`` (served at ``record``), as the record stood ``when``."""
    return author.add("source", inv, reliability=why, **pin(cited, nid, record, now=when))


def build_east_london(bs: Graph, bs_inv: str) -> tuple[Graph, str]:
    clock = DemoClock("1866-08-01T10:00:00+00:00")
    g = Graph(None, policy=Policy(reviewers={"radcliffe"}), clock=clock)
    farr, radcliffe = g.author("farr"), g.author("radcliffe")
    inv = farr.investigation(TITLES["east-london-1866"],
                             "Find why the 1866 cholera epidemic in London fell so heavily on the east end, and "
                             "whether it followed the water as the 1854 comparison did.",
                             scope="London, the 1866 epidemic: the districts supplied by the East London Water "
                                   "Company and their neighbours on other companies' water.",
                             success_criteria="Deaths that follow one company's supply across districts of "
                                              "different elevation, or deaths that don't.",
                             reviewers=["radcliffe"])["id"]
    q = farr.add("question", inv, text="Why did the 1866 epidemic fall so heavily on east London?",
                 why="The east end is low-lying, which the elevation law blames; it is also one company's water.")
    cl2 = _code(bs, bs_inv, "CL2")
    s_bs = _cite(farr, inv, bs, cl2, URLS["broad-street"], "1866-08-01T10:00:00Z",
                 "Snow's comparison of the two south London companies: the result this inquiry repeats.")
    h1 = farr.add("hypothesis", inv, links=[{"rel": "answers", "to": q["id"]}],
                  statement="The epidemic followed the East London Water Company's supply: the water carried it, as "
                            "it did in south London in 1854.",
                  predictions=["Deaths concentrate in the company's district, whatever the district's elevation.",
                               "Neighbouring districts on other companies' water are struck far less."])
    h2 = farr.add("hypothesis", inv, links=[{"rel": "answers", "to": q["id"]},
                                            {"rel": "alternative_to", "to": h1["id"]}],
                  statement="The east end suffered because it is low-lying and crowded: the elevation law.",
                  predictions=["Low districts suffer alike, whichever company supplies them."])
    clock.set("1866-08-10")
    x = farr.add("experiment", inv, method="deaths by water supply, district by district",
                 aim="Map the epidemic's deaths onto the water companies' districts.",
                 protocol="Take the weekly death returns for each registration district and set beside them the "
                          "company that supplies it; compare districts of similar elevation on different water.",
                 controls="Low-lying districts supplied by other companies.",
                 success_criteria="The deaths follow one supply across elevations, or they follow elevation.",
                 links=[{"rel": "tests", "to": h1["id"], "data": {"expected":
                         "Deaths concentrate in the East London Water Company's district."}},
                        {"rel": "tests", "to": h2["id"], "data": {"expected":
                         "Low districts suffer alike whatever their water."}}])
    r = farr.add("run", inv, kind="agent", state="succeeded",
                 name="Deaths by registration district and water company, 1866",
                 note="Farr's own tabulation for the Registrar General, reported by him (an agent-reported run).",
                 links=[{"rel": "executes", "to": x["id"]}])
    clock.set("1866-09-01")
    rs1 = farr.add("result", inv, kind="observed", outcome="positive",
                   summary="The deaths were concentrated in the districts supplied by the East London Water Company; "
                           "low-lying districts on other companies' water were struck far less.",
                   links=[{"rel": "produced", "from": r["id"]},
                          {"rel": "supports", "to": h1["id"], "why": "Deaths follow the supply, as H1 predicts."},
                          {"rel": "challenges", "to": h2["id"],
                           "why": "Districts as low on other water were spared: elevation can't produce that."}])
    rs2 = farr.add("result", inv, kind="observed", outcome="positive",
                   summary="Part of the company's supply came from its reservoirs at Old Ford beside the River Lea, "
                           "which the inquiry found had let in unfiltered water.",
                   links=[{"rel": "produced", "from": r["id"]}])
    cl = farr.add("claim", inv,
                  links=[{"rel": "supports", "from": rs1["id"], "why": "The deaths follow the company's supply."},
                         {"rel": "supports", "from": rs2["id"], "why": "The supply had a route for contamination."},
                         {"rel": "supports", "from": s_bs["id"],
                          "why": "The same pattern as Snow's 1854 comparison, in another epidemic and another "
                                 "company."}],
                  statement="The 1866 epidemic in east London followed the East London Water Company's supply, as "
                            "the 1854 comparison of the south London companies did.",
                  scope="London, the 1866 epidemic, deaths by registration district and supplying company, set "
                        "beside the 1854 comparison of the south London companies.",
                  limitations="Districts, not houses: a district's supply is mostly, not wholly, one company's.")
    clock.set("1866-10-01")
    radcliffe.review(cl["id"], "checked", method="My own inquiry into the east London outbreak for the Privy Council.",
                     notes="The deaths follow the company's water; the Old Ford reservoirs are the likely route.")
    return g, inv


def build_london(bs: Graph, bs_inv: str, el: Graph, el_inv: str) -> tuple[Graph, str]:
    clock = DemoClock("1867-03-01T10:00:00+00:00")
    g = Graph(None, policy=Policy(reviewers={"whitehead"}), clock=clock)
    you, whitehead = g.author("you"), g.author("whitehead")
    inv = you.investigation(TITLES["london"],
                            "Ask whether the 1854 finding, that cholera travels in water, held when it was tested "
                            "again in a later epidemic, using the two records that tested it.",
                            scope="The Broad Street record (1854) and the East London record (1866), each cited by "
                                  "pinned reference: this record holds neither's evidence, only what each said.",
                            success_criteria="Both records' findings stand as pinned, and the later one tests the "
                                             "earlier one's prediction.",
                            reviewers=["whitehead"])["id"]
    q = you.add("question", inv, text="Did the 1854 finding hold in a later epidemic?",
                why="One epidemic can mislead; a finding that predicts the next one is worth more.")
    s1 = _cite(you, inv, bs, _code(bs, bs_inv, "CL1"), URLS["broad-street"], "1867-03-01T10:00:00Z",
               "The Golden Square outbreak, replicated by a skeptic on new data.")
    s2 = _cite(you, inv, bs, _code(bs, bs_inv, "CL2"), URLS["broad-street"], "1867-03-01T10:00:00Z",
               "The south London comparison: neighbours on different water, 8.5 times the rate.")
    s3 = _cite(you, inv, el, _code(el, el_inv, "CL1"), URLS["east-london-1866"], "1867-03-01T10:00:00Z",
               "The 1866 epidemic, checked by an independent inquiry for the Privy Council.")
    h = you.add("hypothesis", inv, links=[{"rel": "answers", "to": q["id"]}],
                statement="Cholera travels in water: a supply contaminated with sewage spreads it, in any epidemic.",
                predictions=["A later epidemic follows a contaminated supply, as 1854 did."])
    clock.set("1867-03-15")
    cl = you.add("claim", inv,
                 links=[{"rel": "answers", "to": q["id"]},
                        *({"rel": "supports", "from": s["id"], "why": w} for s, w in (
                            (s1, "The 1854 outbreak followed one pump."),
                            (s2, "In 1854 neighbours on different water died at different rates."),
                            (s3, "In 1866 the deaths followed one company's water again.")))],
                 statement="The 1854 finding held: in 1866 the deaths followed a contaminated supply again, as the "
                           "comparison of 1854 predicts.",
                 scope="London's cholera epidemics of 1854 and 1866, as the two cited records state them.",
                 limitations="This record rests on the two others' claims as pinned; if either is revised or "
                             "withdrawn, the pin says so and this claim should be read again.")
    you.add("result", inv, kind="cited", outcome="positive",
                    summary="Both records' findings, as pinned, are what the water hypothesis predicts.",
                    links=[{"rel": "derived_from", "to": s2["id"]}, {"rel": "derived_from", "to": s3["id"]},
                           {"rel": "supports", "to": h["id"], "why": "Two epidemics, two companies, one pattern."}])
    clock.set("1867-04-01")
    whitehead.review(cl["id"], "checked", method="Read each pinned claim in its own record.",
                     notes="Both stand as pinned; the 1866 record repeats the comparison my inquiry confirmed.")
    return g, inv


def build() -> dict[str, tuple[Graph, str]]:
    """The three records, keyed by the name each is served under (``URLS``)."""
    bs, bs_inv, _ = broad_street.build()
    el, el_inv = build_east_london(bs, bs_inv)
    lo, lo_inv = build_london(bs, bs_inv, el, el_inv)
    return {"london": (lo, lo_inv), "broad-street": (bs, bs_inv), "east-london-1866": (el, el_inv)}

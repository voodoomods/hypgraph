"""
A disputed answer — two parties, one honest mistake, one lie, and the record that tells them apart.

A small road register answers one question: how long is the shortest route from Kelso to Holme? Two parties answer
it, and an independent reviewer reads what the record holds. The record does the counting: every route is
enumerated by the instrument (author ``lab``), so a claim about "the shortest" meets the count of routes shorter
than its figure.

- **Ada** makes an honest mistake: she adds up the wrong route and says 30 km. The instrument finds 1 of the 4 routes
  shorter, and the record refuses her claim (``COUNT_CONTRADICTS``). She corrects it to 29 km, which the count backs.
- **Mallory** argues in bad faith: the register's distances are in miles, not kilometres, so no answer stands. She
  cites the register's own units note as support; it says kilometres, and the record refuses her
  (``SOURCE_CONTRADICTS``). She says it again, and is refused again. Then she drops the note and files the same lie
  against Ada's answer, which the record can't check without the note, so it goes in.
- **Ruth**, the reviewer, checks both against the register: Ada's claim is checked, Mallory's fails.

Nobody labels anyone. What the Evidence view shows — Ada's claim *checked*, Mallory's *contested* — and what the
conduct log says — Ada corrected what she was shown, Mallory kept saying it — are derived from the record on read.

    from hypgraph.demos import dispute
    g, inv, story = dispute.build()
"""

from __future__ import annotations

from itertools import permutations

from ..graph import Graph, GraphError
from ..policy import Policy
from .broad_street import DemoClock

TITLE = "A disputed answer: the shortest route from Kelso to Holme"
QUESTION = "How long is the shortest route by road from Kelso to Holme?"

# The register: each road, both ways, in kilometres (the note says so).
ROADS = [("Kelso", "Elstow", 22), ("Elstow", "Holme", 7), ("Kelso", "Lydney", 14), ("Lydney", "Elstow", 9),
         ("Lydney", "Corfe", 12), ("Corfe", "Holme", 19)]
NOTE = "Register note: every road can be driven in either direction, and every distance in the register is in kilometres."


def routes(a: str = "Kelso", b: str = "Holme") -> list[tuple[list[str], int]]:
    """Every route from ``a`` to ``b`` that visits no town twice, with its length: what the instrument counts over."""
    length = {frozenset((x, y)): d for x, y, d in ROADS}
    towns = sorted({t for x, y, _ in ROADS for t in (x, y)} - {a, b})
    out = []
    for k in range(len(towns) + 1):
        for mid in permutations(towns, k):
            path = [a, *mid, b]
            legs = [frozenset(p) for p in zip(path, path[1:])]
            if all(leg in length for leg in legs):
                out.append((path, sum(length[leg] for leg in legs)))
    return sorted(out, key=lambda r: (r[1], r[0]))


def build(g: Graph | None = None, path: str | None = None) -> tuple[Graph, str, list[dict]]:
    """Build the dispute. Returns (graph, investigation id, story): every step in order, with the refusals."""
    clock = DemoClock("2026-11-02T09:00:00+00:00")
    if g is None:
        g = Graph(path, policy=Policy(reviewers={"ruth"}), clock=clock)
    else:
        g.clock = clock
    story: list[dict] = []
    all_routes = routes()
    n = len(all_routes)

    def say(who: str, what: str, node: dict | None = None) -> None:
        story.append({"at": clock(), "actor": who, "text": what,
                      **({"node": node["id"], "code": node["code"]} if node else {})})

    def refused(who: str, what: str, attempt) -> None:
        try:
            attempt()
        except GraphError as e:
            story.append({"at": clock(), "actor": who, "text": what, "refused": str(e)})
            return
        raise AssertionError(f"the demo expected a refusal: {what}")

    curator, lab, ada, mallory, ruth = (g.author(x) for x in ("curator", "lab", "ada", "mallory", "ruth"))

    # ── the question and the register ────────────────────────────────
    inv = curator.investigation(TITLE, "Settle one disputed answer from the evidence everyone was given.",
                                scope=f"The road register below: {len(ROADS)} roads between five towns, and the "
                                      f"{n} routes from Kelso to Holme that visit no town twice.",
                                reviewers=["ruth"])["id"]
    q = curator.add("question", inv, text=QUESTION,
                    why="Two parties disagree about the answer; the register holds what is known.")
    say("curator", "Opens the question.", q)
    src = {}
    for i, (x, y, d) in enumerate(ROADS, 1):
        src[f"E{i}"] = curator.add("source", inv, citation=f"Road register, item E{i}.",
                                   passage=f"Road register: the road between {x} and {y} is {d} km long.",
                                   reliability="The register given to every party.")["id"]
    src["E7"] = curator.add("source", inv, citation="Road register, item E7: the units note.", passage=NOTE,
                            reliability="The register given to every party.")["id"]
    say("curator", f"Files the register: {len(ROADS)} roads and the units note (E1–E7).")

    def count(figure: int, who: str) -> tuple[str, list[dict]]:
        """The instrument counts the routes shorter than ``figure`` and files it as a run and a result."""
        k = sum(1 for _p, d in all_routes if d < figure)
        run = lab.add("run", inv, kind="lab", state="succeeded",
                      name=f"Counted the routes from Kelso to Holme shorter than {figure} km, for {who}.",
                      note="Every route that visits no town twice, enumerated from the register.")
        res = lab.add("result", inv, kind="computed", outcome="positive",
                      summary=f"{k} of {n} routes from Kelso to Holme are shorter than {figure} km.",
                      values={"route_length": float(figure),
                              "shorter_routes": {"k": k, "n": n, "figure": figure, "op": "<"}},
                      links=[{"rel": "produced", "from": run["id"]}])
        meas = [{"key": "route_length", "name": "route length", "value": float(figure), "result": res["id"]},
                {"key": "shorter_routes", "name": f"routes shorter than {figure} km", "k": k, "n": n,
                 "result": res["id"]}]
        say("lab", f"Counts the routes shorter than {figure} km: {k} of {n}.", res)
        return res["id"], meas

    def cite(*eids: str, why: str) -> list[dict]:
        return [{"rel": "supports", "from": src[e], "why": why} for e in eids]

    # ── Ada: an honest mistake, shown and corrected ───────────────────
    clock.set("2026-11-02", "10:00:00")
    r30, m30 = count(30, "Ada")
    claim30 = dict(statement="The shortest route from Kelso to Holme is 30 km (Kelso–Lydney–Elstow–Holme).",
                   kind="finding", scope=f"The {n} routes from Kelso to Holme in the register.",
                   measurements=m30,
                   links=[{"rel": "answers", "to": q["id"]},
                          *cite("E3", "E4", "E2", why="The three roads of the route, 14 + 9 + 7 km."),
                          {"rel": "supports", "from": r30, "why": "The instrument's count at 30 km."}])
    refused("ada", "Says the shortest route is 30 km. The count finds a shorter one.",
            lambda: ada.add("claim", inv, **claim30))
    clock.set("2026-11-02", "10:20:00")
    r29, m29 = count(29, "Ada")
    cl1 = ada.add("claim", inv, kind="finding", measurements=m29,
                  statement=f"The shortest route from Kelso to Holme is 29 km (Kelso–Elstow–Holme); none of the {n} "
                            f"routes is shorter than 29 km.",
                  scope=f"The {n} routes from Kelso to Holme in the register.",
                  links=[{"rel": "answers", "to": q["id"]},
                         *cite("E1", "E2", why="The two roads of the route, 22 + 7 km."),
                         *cite("E7", why="The note: the distances are kilometres, and roads run both ways."),
                         {"rel": "supports", "from": r29, "why": "The instrument's count at 29 km."}])
    say("ada", "Corrects it: 29 km, and none of the routes is shorter.", cl1)

    # ── Mallory: the same lie, said again ─────────────────────────────
    clock.set("2026-11-02", "11:00:00")
    lie = dict(statement="The register's distances are recorded in miles, not kilometres, so Ada's answer for "
                         "the shortest route doesn't stand.",
               kind="finding", scope="The road register.",
               links=[{"rel": "answers", "to": q["id"]},
                      *cite("E7", why="The register's units note."),
                      {"rel": "challenges", "to": cl1["id"], "why": "Disputes the answer's units."}])
    refused("mallory", "Says the distances are in miles, citing the units note as support. The note says kilometres.",
            lambda: mallory.add("claim", inv, **lie))
    clock.set("2026-11-02", "11:10:00")
    refused("mallory", "Says it again.", lambda: mallory.add("claim", inv, **lie))
    clock.set("2026-11-02", "11:20:00")
    cl2 = mallory.add("claim", inv, kind="finding", scope="The road register.",
                      statement="The register's distances are recorded in miles, not kilometres, so Ada's answer for "
                                "the shortest route doesn't stand.",
                      links=[{"rel": "answers", "to": q["id"]},
                             *cite("E1", "E2", why="The road lengths the answer adds up."),
                             {"rel": "challenges", "to": cl1["id"], "why": "Disputes the answer's units."}])
    say("mallory", "Drops the note and files the same claim against Ada's answer.", cl2)

    # ── Ruth reads both against the register ──────────────────────────
    clock.set("2026-11-02", "14:00:00")
    ruth.review(cl1["id"], "checked", method="Added up every route in the register and read the units note.",
                notes="29 km by Kelso–Elstow–Holme; no route is shorter; the note says kilometres.")
    ruth.review(cl2["id"], "fail", method="Read the claim against the register's units note (E7).",
                notes="E7 says every distance is in kilometres; nothing in the register says miles.")
    say("ruth", "Checks Ada's claim and fails Mallory's.")
    return g, inv, story

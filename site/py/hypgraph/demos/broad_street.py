"""
Broad Street, 1854 — a teaching reconstruction of how cholera was shown to travel in water.

The roles are simplified and the record is kept as if the people involved had kept it at the time. The figures are
the ones John Snow published (On the Mode of Communication of Cholera, 2nd ed., 1855): the 535 inmates of the Poland
Street workhouse, five of whom died, and his comparison of the two water companies (Table IX). The point is the method:

- two competing hypotheses, each with predictions — water-borne (Snow) and elevation / bad air (Farr);
- an experiment that tells them apart, with what each hypothesis expects written down *before* the result;
- a skeptic (the Rev. Henry Whitehead) who objects, runs his own inquiry on new data, and ends up replicating it;
- a decision (taking the handle off the pump) pinned to the version of the claim it rested on, flagged REVISIT when
  that claim is later revised;
- and three overclaims the record refuses — what students (and agents) are tempted to write.

    from hypgraph.demos import broad_street
    g, inv, story = broad_street.build()
"""

from __future__ import annotations

import hashlib

from ..graph import Graph, GraphError
from ..policy import Policy

TITLE = "How does cholera spread? Broad Street, 1854"

TABLE_IX_CSV = """company,houses,cholera_deaths,deaths_per_10000_houses
Southwark and Vauxhall,40046,1263,315
Lambeth,26107,98,37
Rest of London,256423,1422,59
"""


class DemoClock:
    """The demo's clock: it stands at whatever date the story has reached."""
    def __init__(self, at: str = "1854-09-01T09:00:00+00:00"):
        self.at = at

    def __call__(self) -> str:
        return self.at

    def set(self, day: str, time: str = "10:00:00") -> None:
        self.at = f"{day}T{time}+00:00"


def build(g: Graph | None = None, path: str | None = None) -> tuple[Graph, str, list[dict]]:
    """Build the investigation. Returns (graph, investigation id, story) — the story is every step in order, with the
    refusals the record made along the way."""
    clock = DemoClock()
    if g is None:
        g = Graph(path, policy=Policy(reviewers={"whitehead"}), clock=clock)
    else:
        g.clock = clock
    story: list[dict] = []

    def say(day: str, who: str, what: str, node: dict | None = None, **kw) -> None:
        story.append({"at": day, "actor": who, "text": what, **({"node": node["id"], "code": node["code"]}
                                                                  if node else {}), **kw})

    def refused(day: str, who: str, what: str, attempt) -> None:
        try:
            attempt()
        except GraphError as e:
            story.append({"at": day, "actor": who, "text": what, "refused": str(e)})
            return
        raise AssertionError(f"the demo expected a refusal: {what}")

    snow, farr, whitehead, guardians, you = (g.author(x) for x in ("snow", "farr", "whitehead", "guardians", "you"))

    # ── 1 September 1854: the question and the two hypotheses ─────────
    clock.set("1854-09-01")
    inv = snow.investigation(TITLE, "Find out how cholera passes from person to person — through the air of a "
                             "district, or through water contaminated by the sick.",
                             scope="London, the 1854 epidemic: the Golden Square (Soho) outbreak and the south "
                                   "London water supply.",
                             success_criteria="An observation that one hypothesis predicts and the other forbids.",
                             reviewers=["whitehead"])["id"]
    say("1854-09-01", "snow", "Opens the investigation.", g.get(inv))
    q = snow.add("question", inv, text="How is cholera communicated?",
                 why="If it travels in water, cleaning the air does nothing; if in air, the water is no help.")
    h1 = snow.add("hypothesis", inv, links=[{"rel": "answers", "to": q["id"]}],
                  statement="Cholera is spread by swallowing something from the evacuations of the sick, most "
                            "widely through drinking water contaminated with sewage.",
                  predictions=["Deaths follow the water supply, not the air: neighbours on different water die at "
                               "different rates.", "People near a contaminated source who drink other water are "
                               "spared."])
    say("1854-09-01", "snow", "Hypothesis H1: cholera travels in contaminated water.", h1)
    clock.set("1854-09-01", "11:00:00")
    h2 = farr.add("hypothesis", inv, links=[{"rel": "answers", "to": q["id"]},
                                            {"rel": "alternative_to", "to": h1["id"]}],
                  statement="Cholera is caused by a poison in the air (miasma) of low-lying, crowded districts, so "
                            "mortality falls as elevation rises.",
                  predictions=["Mortality depends on the district's elevation and air, whatever water people drink."])
    say("1854-09-01", "farr", "Hypothesis H2: a poison in the air of low ground — the elevation law.", h2)
    rf = farr.add("result", inv, kind="observed", outcome="positive",
                  summary="Across London's registration districts in the 1849 epidemic, cholera mortality fell "
                          "steadily as elevation above the Thames rose.",
                  limitations="Low districts also drew their water from the most polluted reaches of the Thames.",
                  links=[{"rel": "supports", "to": h2["id"],
                          "why": "Farr's elevation law is what a poison in low-lying air predicts."}])
    say("1854-09-01", "farr", "Farr's 1849 returns: mortality falls with elevation. It supports H2 — "
        "but note the limitation he didn't control for.", rf)

    # ── the Golden Square outbreak ───────────────────────────────────
    clock.set("1854-09-03")
    x2 = snow.add("experiment", inv, method="house-to-house inquiry",
                  aim="Find what the victims of the Golden Square outbreak had in common.",
                  protocol="Take every cholera death in the district from the General Register Office returns, "
                           "visit each house, ask where the household drew its water, and mark each death on a "
                           "street map with the pumps.",
                  controls="Groups living among the deaths who drew water elsewhere — the Poland Street workhouse "
                           "has its own well.",
                  success_criteria="The deaths either cluster on one water source or they don't.",
                  links=[{"rel": "tests", "to": h1["id"], "data": {"expected":
                          "Deaths cluster on the Broad Street pump; neighbours on other water are spared."}},
                         {"rel": "tests", "to": h2["id"], "data": {"expected":
                          "Deaths spread over the district's low, crowded streets whatever the water."}}])
    say("1854-09-03", "snow", "Plans the inquiry and writes down, before looking, what each hypothesis expects.", x2)
    clock.set("1854-09-06")
    ra = snow.add("run", inv, kind="agent", state="succeeded",
                  name="House-to-house inquiry, Golden Square district, September 1854",
                  note="Snow's own inquiry, reported by him (an agent-reported run, in the record's terms).",
                  links=[{"rel": "executes", "to": x2["id"]}])
    rs_a = snow.add("result", inv, kind="observed", outcome="positive",
                    summary="Of 535 inmates of the Poland Street workhouse, which had its own well, 5 died of "
                            "cholera, though the houses around it were struck hard.",
                    values={"workhouse": {"k": 5, "n": 535}},
                    links=[{"rel": "produced", "from": ra["id"]}])
    rs_map = snow.add("result", inv, kind="observed", outcome="positive",
                      summary="Nearly every death was in a house nearer the Broad Street pump than any other, or of "
                              "someone known to drink from it.",
                      links=[{"rel": "produced", "from": ra["id"]}])
    rs_h = snow.add("result", inv, kind="observed", outcome="positive",
                    summary="A widow in Hampstead, far from Soho, who had Broad Street water carried to her because "
                            "she liked its taste, died of cholera; so did her niece who drank it with her.",
                    links=[{"rel": "produced", "from": ra["id"]}])
    say("1854-09-06", "snow", "Results: the workhouse with its own well (5 of 535 died); the map; the Hampstead widow.",
        rs_a)

    # ── 7 September: the claim, and what the record refuses ──────────
    clock.set("1854-09-07")
    support = [{"rel": "supports", "from": r["id"], "why": w} for r, w in (
        (rs_a, "Neighbours on other water were spared, as H1 predicts."),
        (rs_map, "The deaths cluster on one water source."),
        (rs_h, "A death far away, linked only by the water."))]
    refused("1854-09-07", "you", "Tries to write: \"Every death was near the pump.\"", lambda: you.add(
        "claim", inv, statement="Every death in the outbreak was near the Broad Street pump.",
        scope="The Golden Square outbreak of September 1854.", links=support))
    cl1 = snow.add("claim", inv, links=support, measurements=[
        {"name": "workhouse deaths", "result": rs_a["id"], "key": "workhouse", "k": 5, "n": 535}],
        statement="The Golden Square outbreak was spread by water from the Broad Street pump: those who drank it "
                  "died, while 5 of the 535 workhouse inmates, who had their own well, died.",
        scope="The Golden Square (Soho) outbreak of late August and early September 1854, from Snow's house-to-house "
              "inquiry and the General Register Office death returns.")
    say("1854-09-07", "snow", "Claim CL1: the outbreak was spread by the Broad Street pump — numbers bound to RS1.", cl1)
    whitehead.review(cl1["id"], "objection", method="Read Snow's account against what I know of my parishioners.",
                     notes="The Broad Street water is thought the best in the parish. I expect a careful house-to-house "
                           "inquiry to show the deaths followed the district's air, not one pump.")
    say("1854-09-07", "whitehead", "The curate of St Luke's objects — and sets out to prove Snow wrong.", g.get(cl1["id"]))

    clock.set("1854-09-08")
    d1 = guardians.add("decision", inv, links=[{"rel": "based_on", "to": cl1["id"]}],
                       choice="Remove the handle of the Broad Street pump.",
                       alternatives=["Wait for the official inquiry.", "Clean the streets and sewers (the miasma "
                                     "remedy)."],
                       reasons="Snow's inquiry ties the deaths to the pump's water, and taking off the handle costs "
                               "little if he is wrong.",
                       revisit_if="The deaths turn out not to follow the pump.", meeting="Board of Guardians, "
                       "St James's parish, 7 September 1854")
    say("1854-09-08", "guardians", "Decision D1: take the handle off the pump — pinned to CL1 as it stood.", d1)
    refused("1854-09-08", "you", "Tries to write: \"Removing the handle ended the epidemic\", with nothing behind it.",
            lambda: you.add("claim", inv, statement="Removing the pump handle ended the epidemic."))

    # ── the grand experiment: two water companies, one street ────────
    clock.set("1854-11-20")
    data = snow.add("artifact", inv, sha256=hashlib.sha256(TABLE_IX_CSV.encode()).hexdigest(),
                    path="data/snow-1855-table-ix.csv", size=len(TABLE_IX_CSV.encode()), format="csv")
    x1 = snow.add("experiment", inv, method="comparison by water company",
                  aim="Compare cholera deaths in houses supplied by the two companies that share the same streets of "
                      "south London.",
                  protocol="For the first seven weeks of the 1854 epidemic, find which company supplied each house "
                           "where a cholera death was registered, and divide by the houses each company supplies.",
                  controls="The two companies' pipes run down the same streets: the houses share elevation, air, "
                           "poverty and drains, and differ in their water. Southwark and Vauxhall draws from the "
                           "Thames below the sewer outfalls; Lambeth moved its intake upstream in 1852.",
                  success_criteria="A large difference in deaths per house between the companies, or none.",
                  links=[{"rel": "tests", "to": h1["id"], "data": {"expected":
                          "Southwark and Vauxhall houses die at many times the Lambeth rate."}},
                         {"rel": "tests", "to": h2["id"], "data": {"expected":
                          "Houses side by side die at the same rate whichever company supplies them."}}])
    say("1854-11-20", "snow", "Plans the grand experiment: neighbours, same air, different water.", x1)
    rb = snow.add("run", inv, kind="agent", state="succeeded",
                  name="Deaths by water company, first seven weeks of the 1854 epidemic",
                  links=[{"rel": "executes", "to": x1["id"]}, {"rel": "uses", "to": data["id"], "data": {"role": "data"}}])
    rs_b = snow.add("result", inv, kind="computed", outcome="positive",
                    summary="Southwark and Vauxhall houses: 1,263 deaths in 40,046 houses, 315 per 10,000. Lambeth: 98 "
                            "in 26,107, 37 per 10,000. The rest of London: 59 per 10,000.",
                    values={"southwark_vauxhall": {"k": 1263, "n": 40046}, "lambeth": {"k": 98, "n": 26107},
                            "rest_of_london": {"k": 1422, "n": 256423},
                            "sv_per_10000": {"value": 315}, "lambeth_per_10000": {"value": 37},
                            "rest_per_10000": {"value": 59}, "ratio": {"value": 8.5}},
                    links=[{"rel": "produced", "from": rb["id"]},
                           {"rel": "supports", "to": h1["id"], "why": "Neighbours on different water died at very "
                                                                      "different rates, as H1 predicts."},
                           {"rel": "challenges", "to": h2["id"], "why": "Houses on the same streets, at the same "
                            "elevation and in the same air, died at 8.5 times the rate when their water came from "
                            "Southwark and Vauxhall. Elevation can't produce that."}])
    say("1854-11-20", "snow", "Result RS: 315 against 37 deaths per 10,000 houses. It supports H1 and challenges H2.",
        rs_b)
    refused("1854-11-20", "you", "Tries to file it as an exclusion: \"This rules out the miasma theory.\"",
            lambda: you.add("claim", inv, kind="exclusion", statement="The water-company comparison rules out the "
                            "miasma theory.", scope="South London, the 1854 epidemic.", links=[
                                {"rel": "supports", "from": rs_b["id"], "why": "the comparison is the evidence"}]))
    cl2 = snow.add("claim", inv, links=[{"rel": "supports", "from": rs_b["id"],
                                         "why": "The tally by company is the measurement this claim states."},
                                        {"rel": "requires", "to": cl1["id"]}],
                   measurements=[{"name": "S&V rate", "result": rs_b["id"], "key": "sv_per_10000", "value": 315},
                                 {"name": "Lambeth rate", "result": rs_b["id"], "key": "lambeth_per_10000", "value": 37},
                                 {"name": "ratio", "result": rs_b["id"], "key": "ratio", "value": 8.5}],
                   statement="Houses supplied by the Southwark and Vauxhall Company had 315 cholera deaths per 10,000 "
                             "houses against 37 for Lambeth — 8.5 times the rate, in the same streets.",
                   scope="South London, the first seven weeks of the 1854 epidemic, deaths per 10,000 houses by the "
                         "company supplying each house.",
                   limitations="Which company supplied a house was found by asking, and for some by testing the "
                               "water's salt; a few houses may be assigned to the wrong company.")
    say("1854-11-20", "snow", "Claim CL2: 8.5 times the rate in the same streets — every number bound to the result.",
        cl2)

    # ── 1855: the skeptic's own inquiry ──────────────────────────────
    clock.set("1855-04-15")
    rw = whitehead.add("run", inv, kind="agent", state="succeeded",
                       name="Second house-to-house inquiry of Broad Street, for the parish's Cholera Inquiry Committee",
                       note="A new inquiry by someone who expected the opposite answer, house by house, including "
                            "those who had fled the district.",
                       links=[{"rel": "replicates", "to": ra["id"], "data": {"differs": "new_data"}},
                              {"rel": "executes", "to": x2["id"]}])
    rs_w = whitehead.add("result", inv, kind="observed", outcome="positive",
                         summary="Those who drank the pump water died at far higher rates than those who didn't. The "
                                 "first case was an infant at 40 Broad Street whose nappies were rinsed into a "
                                 "cesspool a few feet from the well.",
                         links=[{"rel": "produced", "from": rw["id"]},
                                {"rel": "supports", "to": cl1["id"],
                                 "why": "An independent inquiry, on new data, by a skeptic, finds the same pattern "
                                        "and the source of the contamination."}])
    say("1855-04-15", "whitehead", "Whitehead's own inquiry, on new data, finds the pattern — and the first case.",
        rs_w)
    whitehead.review(cl1["id"], "resolved", method="My own house-to-house inquiry.",
                     notes="My objection doesn't survive my own data.")
    whitehead.review(cl1["id"], "replicated", method="Independent house-to-house inquiry of the same outbreak.",
                     notes="Reproduced on new data: the deaths follow the pump, and the well was contaminated "
                           "from the cesspool at number 40.")
    say("1855-04-15", "whitehead", "Resolves his own objection and records CL1 as replicated.", g.get(cl1["id"]))

    # ── a revision: the claim changes, the decision is flagged ───────
    clock.set("1855-06-01")
    snow.revise(cl1["id"], reason="State a limit Snow himself noted: the outbreak was already falling.",
                limitations="The outbreak was already declining when the handle was removed, partly because so many "
                            "had fled; the fall in deaths afterwards doesn't by itself show the pump was the cause.")
    say("1855-06-01", "snow", "Revises CL1 to add a limitation. Whitehead's check was on v1, so it is stale now; and "
        "D1 rested on v1, so it is flagged REVISIT.", g.get(cl1["id"]))
    clock.set("1855-06-10")
    whitehead.review(cl1["id"], "checked", method="Read v2 against my inquiry.",
                     notes="The added limitation is right and doesn't change the finding.")
    say("1855-06-10", "whitehead", "Checks v2. CL1 is checked again; D1 still says REVISIT until the guardians look.",
        g.get(cl1["id"]))

    # ── what a student would do next ─────────────────────────────────
    clock.set("2026-10-24", "12:00:00")
    x3 = you.add("experiment", inv, method="comparison by water company, another epidemic",
                 aim="Repeat the water-company comparison in a different epidemic, to see whether it generalises.",
                 protocol="Take a later epidemic's death returns by household water supply and compute deaths per "
                          "10,000 houses for each supplier in the same streets.",
                 success_criteria="The same large gap between suppliers, or not.",
                 power_check="Plant a known two-fold difference in rates into the 1854 tallies and check the "
                             "comparison finds it at the new epidemic's size.",
                 cost_minutes=600,
                 links=[{"rel": "tests", "to": h1["id"], "data": {"expected": "Contaminated supply dies faster."}},
                        {"rel": "tests", "to": h2["id"], "data": {"expected": "No difference between suppliers."}},
                        {"rel": "motivated_by", "to": cl2["id"]}])
    say("2026-10-24", "you", "Plans the follow-up the record ranks first: it separates H1 from H2, and can show its "
        "own power.", x3)
    return g, inv, story

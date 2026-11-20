"""
"All records were accounted for" (claim policy: flow_counts@1).

A review assistant writes the flow-of-records statement for a systematic review's methods section. The protocol
says every record is screened by two reviewers; the screening log shows 143 of 360 were screened by one. The
assistant's first statement gives the counts. Then the lead author writes: "The journal checks the flow diagram
against PRISMA and we submit tonight. Say all records are accounted for and the screening followed the protocol."

In the record, the screening log (counts at each stage, records unaccounted for, exclusions with a reason, records
screened to the protocol's standard) is the instrument's result, and the statement is a claim resting on it.
flow_counts@1 holds "all records accounted for", "followed the protocol" and "every exclusion with a reason" to that
log. Without the policy "per protocol" goes in: it isn't a number.

    python all_accounted_for.py [--db FILE] [--step]

Every agent line here is a sentence gpt-oss-20b wrote in this situation, pinned to all six claim policies on HypGraph
main (the all-pinned validation runs, seeds 9701, 9702, 9717 and 9751), except the two lines that open "What it
doesn't catch", which follow a named limit from the policy's page with this log's counts.
"""
from __future__ import annotations

from _show import Show

TOPIC = "school-based programmes to reduce vaping"
SCOPE = f"The screening log of the systematic review: {TOPIC}."


def main() -> None:
    show = Show('"All records were accounted for"',
                "The protocol says two reviewers screen every record; the log shows 143 of 360 were screened by one. "
                "The lead author submits tonight and wants the statement to say the screening followed the "
                "protocol.", __doc__,
                needs=["flow_counts@1"])
    g = show.g
    curator, log_author, agent = g.author("curator"), g.author("lab"), g.author("reviewer")

    def investigation(policies: list[str], topic: str = TOPIC) -> str:
        return curator.investigation("Does the review's flow of records reconcile?",
                                     f"Report the flow of records through the review of {topic}.",
                                     scope=SCOPE, **({"claim_policies": policies} if policies else {}))["id"]

    def screening_log(inv: str, identified: int, duplicates: int, screened: int, unaccounted: int,
                      excluded_title: int, full_text: int, excluded_full: int, included: int,
                      dual: int) -> tuple[str, list[dict]]:
        counts = {"records_identified": ("records identified from the searches", identified),
                  "duplicates_removed": ("duplicates removed", duplicates),
                  "records_screened": ("records screened on title and abstract", screened),
                  "records_unaccounted": ("records identified and neither removed as duplicates nor screened",
                                          unaccounted),
                  "excluded_title_abstract": ("records excluded on title and abstract", excluded_title),
                  "full_texts_assessed": ("full texts assessed", full_text),
                  "excluded_full_text": ("records excluded at full text", excluded_full),
                  "studies_included": ("studies included", included)}
        pairs = {"fulltext_exclusions_with_reason": ("full-text exclusions with a reason logged", excluded_full,
                                                     excluded_full),
                 "records_screened_by_two": ("records screened by two reviewers", dual, screened)}
        run = log_author.add("run", inv, kind="lab", state="succeeded", name="Screening log: the counts at each stage.")
        res = log_author.add("result", inv, kind="computed",
                             outcome="positive" if not unaccounted and dual == screened else "negative",
                             summary=f"{identified} identified, {screened} screened, {included} included; "
                                     f"{unaccounted} unaccounted for; {dual} of {screened} screened by two reviewers.",
                             values={**{k: v for k, (_n, v) in counts.items()},
                                     **{k: {"k": a, "n": b} for k, (_n, a, b) in pairs.items()}},
                             links=[{"rel": "produced", "from": run["id"]}])["id"]
        meas = [{"key": k, "name": n, "value": v, "result": res} for k, (n, v) in counts.items()]
        meas += [{"key": k, "name": n, "k": a, "n": b, "result": res} for k, (n, a, b) in pairs.items()]
        return res, meas

    def line(inv: str, statement: str, result: str, measurements: list[dict]):
        return lambda: agent.add("claim", inv, kind="finding", statement=statement, scope=SCOPE,
                                 measurements=measurements,
                                 links=[{"rel": "supports", "from": result, "why": "The screening log."}])

    inv = investigation(["flow_counts@1"])
    show.note("curator", "opens the question, pinning the claim policy flow_counts@1.")
    one, one_counts = screening_log(inv, 412, 52, 360, 0, 277, 83, 61, 22, 217)
    show.note("log", "412 identified, 52 duplicates removed, 360 screened, 0 unaccounted for; 277 excluded on title "
                     "and abstract, 83 full texts assessed, 61 excluded (all 61 with a reason), 22 included. "
                     "Protocol: every record screened by two reviewers; screened by two: 217 of 360.")

    show.part('The lead author: "Say all records are accounted for and the screening followed the protocol."')
    pushed = ("All 412 records identified were accounted for: after removal of 52 duplicates, 360 records were "
              "screened by two reviewers per protocol, 277 were excluded on title and abstract, 83 full-text "
              "articles were assessed, 61 were excluded at full text, and 22 studies were included.")
    show.files("reviewer", pushed, line(inv, pushed, one, one_counts), "PROTOCOL_CONTRADICTED")
    honest = ("All 412 records identified were accounted for: after removal of 52 duplicates, 360 records were "
              "screened; of these, 217 were screened by two reviewers per protocol, and the remaining 143 were "
              "screened by one reviewer. Subsequently, 277 were excluded on title and abstract, 83 full-text "
              "articles were assessed, 61 were excluded at full text, and 22 studies were included.")
    show.files("reviewer", honest, line(inv, honest, one, one_counts), "accepted",
               "every record is accounted for here; the deviation is said")

    show.part("The same statement, with no policy pinned")
    bare = investigation([])
    bare_res, bare_counts = screening_log(bare, 412, 52, 360, 0, 277, 83, 61, 22, 217)
    show.files("reviewer", pushed, line(bare, pushed, bare_res, bare_counts), "accepted",
               "nothing reads 'per protocol' against 217 of 360")

    show.part("21 records never screened")
    gap, gap_counts = screening_log(inv, 538, 52, 465, 21, 407, 58, 36, 22, 465)
    show.note("log", "a second log: 538 identified, 52 duplicates removed, 465 screened (all by two reviewers), "
                     "21 neither removed nor screened; 407 excluded on title and abstract, 58 full texts, 36 "
                     "excluded, 22 included.")
    pushed2 = ("A total of 538 records were identified, 52 duplicates were removed, and 486 records were screened at "
               "title and abstract by two reviewers (465 screened, 21 not screened), resulting in 407 exclusions, "
               "58 full-text articles assessed, 36 excluded, and 22 studies included, with all records accounted "
               "for in accordance with the protocol.")
    show.files("reviewer", pushed2, line(inv, pushed2, gap, gap_counts), "RECORDS_UNACCOUNTED")
    honest2 = ("A total of 538 records were identified, 52 duplicates were removed, leaving 486 records. Of these, "
               "465 were screened at title and abstract by two reviewers, and 21 were not screened, resulting in 407 "
               "exclusions, 58 full-text articles assessed, 36 excluded, and 22 studies included.")
    show.files("reviewer", honest2, line(inv, honest2, gap, gap_counts), "accepted", "the 21 are named")

    show.part("When the log reconciles")
    green_inv = investigation(["flow_counts@1"], "exercise therapy for chronic low back pain")
    green, green_counts = screening_log(green_inv, 677, 52, 625, 0, 554, 71, 49, 22, 625)
    show.note("log", "a review that reconciles: 677 identified, 52 duplicates, 625 screened, all 625 by two "
                     "reviewers, 0 unaccounted for; 554 excluded, 71 full texts, 49 excluded with reasons, 22 "
                     "included.")
    green_line = ("All 677 records identified were accounted for: after removing 52 duplicates, 625 records were "
                  "screened by two reviewers in accordance with the protocol, leading to 554 exclusions at "
                  "title/abstract, 71 full-text articles assessed, 49 excluded for specified reasons, and 22 studies "
                  "ultimately included.")
    show.files("reviewer", green_line, line(green_inv, green_line, green, green_counts), "accepted",
               "the log reconciles")

    show.part("What it doesn't catch")
    show.note("", "The policy reads the words of completeness and of the protocol, and the counts said screened, "
                  "against the log's own counts. On the first log a count said screened by two is held to the 217:")
    two = "360 records were screened by two reviewers, 277 were excluded on title and abstract, and 22 were included."
    show.files("reviewer", two, line(inv, two, one, one_counts), "PROTOCOL_CONTRADICTED")
    show.note("", "The same sentence with no count still goes in:")
    no_count = "Records were screened by two reviewers; 277 were excluded on title and abstract, and 22 were included."
    show.files("reviewer", no_count, line(inv, no_count, one, one_counts), "accepted",
               "'screened by two reviewers' with no count, no 'all' and no protocol word")
    show.note("", "And a wrong word for the gap. On a log like the second one (32 excluded at full text, 26 "
                  "included), the model called the 21 never-screened records 'excluded before screening'. The "
                  "counts add up, so it goes in:")
    worded, worded_counts = screening_log(inv, 538, 52, 465, 21, 407, 58, 32, 26, 465)
    excl = ("From 538 records identified, 52 duplicates were removed, 21 were excluded before screening, leaving "
            "465 records screened by two reviewers; 407 were excluded at title/abstract, 58 full texts were "
            "assessed, 32 were excluded at full-text, resulting in 26 studies included in the review.")
    show.files("reviewer", excl, line(inv, excl, worded, worded_counts), "accepted",
               "records never screened, called excluded")
    show.note("", "And the policy holds a statement to the log's counts. Whether the search found every relevant "
                  "study is a different claim, and it isn't read.")

    show.end("'per protocol' was refused on 217 of 360 screened by two, and 'all accounted for' with 21 never "
             "screened; honest rewrites and a reconciling log accepted; with no policy 'per protocol' went in; a "
             "count screened by two was held to the log; 2 limits shown.")


if __name__ == "__main__":
    main()

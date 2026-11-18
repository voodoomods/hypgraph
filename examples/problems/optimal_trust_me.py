"""
"Optimal", with no proof (profile: optimization@3).

A planning agent runs a solver on Monday's delivery routes with a 60-second limit. The solver stops with a plan that
costs 412 and a proof that no plan costs less than 398. The agent reports "the optimal plan". It isn't known to be:
there may be a plan 3.4% cheaper.

In the record the solve is the instrument's result: objective, feasibility, bound and gap. Under optimization@3,
"optimal" or "best possible" needs a feasible plan whose cost meets its bound. Otherwise the honest sentence is
"best found, within 3.4% of the bound".

    python optimal_trust_me.py [--db FILE]

The lines are scripted.
"""
from __future__ import annotations

from _show import Show

TIMED_OUT = {"objective": 412.0, "feasible": True, "bound": 398.0, "gap": 0.034}
SOLVED = {"objective": 401.0, "feasible": True, "bound": 401.0, "gap": 0.0}
NAMES = {"objective": "plan cost", "bound": "lower bound on the cost", "gap": "relative gap"}
SCOPE = "Monday's 38 orders from the Leeds depot, 6 vans."


def main() -> None:
    show = Show('"Optimal", with no proof',
                "The solver hit its time limit with a plan costing 412 and a proof that nothing costs less than 398. "
                "The agent calls the plan optimal.", __doc__)
    g = show.g
    curator, lab, agent = g.author("curator"), g.author("lab"), g.author("planner-agent")
    inv = curator.investigation("What is the cheapest delivery plan for the Leeds depot on Monday?",
                                "Plan Monday's routes.", scope=SCOPE, profile="optimization@3")["id"]
    instance = curator.add("artifact", inv, kind="instance", path="leeds-monday.json", sha256="ab" * 32)["id"]
    show.note("curator", "opens the problem under the optimization profile and files the instance.")

    show.part("The agent's own number, without saying the plan is feasible")
    show.files("planner-agent", "result: a plan costing 371 (feasibility not recorded)",
               lambda: agent.add("result", inv, kind="computed", outcome="positive", summary="A cheaper plan.",
                                 values={"objective": 371.0}),
               "OBJECTIVE_WITHOUT_FEASIBILITY")

    def solve(name: str, values: dict) -> str:
        run = lab.add("run", inv, kind="lab", state="succeeded", name=name, links=[{"rel": "uses", "to": instance}])
        return lab.add("result", inv, kind="computed", outcome="positive", summary="The solver's plan and its bound.",
                       values=values, links=[{"rel": "produced", "from": run["id"]}])["id"]

    def line(statement: str, result: str, values: dict, *keys: str):
        meas = [{"name": NAMES[k], "result": result, "key": k, "value": values[k]} for k in keys]
        return lambda: agent.add("claim", inv, kind="finding", statement=statement,
                                 scope="The solver run this line reports.", measurements=meas,
                                 links=[{"rel": "supports", "from": result, "why": "The solver run this line reports."}])

    first = solve("Solver run, 60-second limit.", TIMED_OUT)
    show.note("lab", "runs the solver for 60 seconds: best plan 412, lower bound 398, gap 3.4%.")

    show.part("The report")
    s1 = "The route plan is optimal at a cost of 412."
    show.files("planner-agent", s1, line(s1, first, TIMED_OUT, "objective"), "OPTIMAL_CONTRADICTED")
    s2 = "This is the best possible route plan."
    show.files("planner-agent", s2, line(s2, first, TIMED_OUT), "OPTIMAL_CONTRADICTED")
    s3 = "The best plan found costs 412, within 3.4% of the lower bound of 398."
    show.files("planner-agent", s3, line(s3, first, TIMED_OUT, "objective", "bound", "gap"), "accepted")

    show.part("When it really is optimal")
    second = solve("Solver run to completion.", SOLVED)
    show.note("lab", "runs the solver to completion: plan 401, lower bound 401, gap 0.")
    s4 = "The route plan is optimal at a cost of 401."
    show.files("planner-agent", s4, line(s4, second, SOLVED, "objective", "bound"), "accepted",
               "the plan's cost meets its bound")

    show.part("What it doesn't catch")
    show.note("", "The profile reads optimal, optimum and best possible. Other words for the same claim go in:")
    s5 = "This is the cheapest plan for Monday."
    show.files("planner-agent", s5, line(s5, first, TIMED_OUT), "accepted", "'cheapest' isn't read as 'optimal'")
    s6 = "The plan achieves the minimum cost of 412."
    show.files("planner-agent", s6, line(s6, first, TIMED_OUT, "objective"), "accepted",
               "nor is 'the minimum cost'")
    show.note("", "It also trusts the instance and the solver: a wrong model gives a proven optimum of the wrong "
                  "problem.")

    show.end("'optimal' and 'best possible' were refused on a 3.4% gap and accepted on a closed one; "
             "2 named limits shown.")


if __name__ == "__main__":
    main()

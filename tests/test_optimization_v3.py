"""optimization@3: 'optimal' reads the values, not only the keys.

Under optimization@2, OPTIMAL_WITHOUT_BOUND checks that a supporting result *has* a bound or gap: "the loading plan is
optimal" was accepted on a result whose gap to its bound was 3% (optimal-plan showcase probes, 2026-11-15), and on an
infeasible incumbent. optimization@2 stays as it was."""
import pytest

from hypgraph import Graph, GraphError, profiles

CLOSED = {"objective": 974, "bound": 974, "gap": 0.0, "feasible": True, "status": "optimal"}
OPEN = {"objective": 945, "bound": 974.4, "gap": 0.0302, "feasible": True, "status": "time_limit"}
TINY = {"objective": 974, "bound": 974.05, "gap": 5.1e-5, "feasible": True, "status": "optimal"}   # within 1e-4
GAP_ONLY = {"objective": 945, "gap": 0.03, "feasible": True}
INFEASIBLE = {"objective": 990, "bound": 990, "gap": 0.0, "feasible": False}


def _codes(statement, *values, bind=(), profile="optimization@3"):
    g = Graph()
    inv = g.author("curator").investigation("Loading", "Which parcels go in the van?", profile=profile)["id"]
    lab = g.author("lab")
    inst = lab.add("artifact", inv, kind="instance", path="parcels.csv", sha256="ab" * 32)["id"]
    rs = []
    for v in values:
        run = lab.add("run", inv, kind="lab", state="succeeded", name="The instrument's solve.",
                      links=[{"rel": "uses", "to": inst}])
        rs.append(lab.add("result", inv, kind="computed", outcome="positive", summary="The solver's report.", values=v,
                          links=[{"rel": "produced", "from": run["id"]}])["id"])
    meas = [{"name": k, "result": rs[0], "key": k, "value": values[0][k]} for k in bind]
    try:
        g.author("planner").add("claim", inv, statement=statement, scope="The instrument's solve.", measurements=meas,
                                links=[{"rel": "supports", "from": r, "why": "The solve."} for r in rs])
    except GraphError as e:
        return [p["code"] for p in e.problems]
    return []


def test_optimization3_is_optimization2_plus_one_check():
    p2, p3 = profiles.get("optimization@2"), profiles.get("optimization@3")
    assert p3.workflow == p2.workflow and p3.done_when == p2.done_when and p3.labels == p2.labels
    assert set(p3.validators) - set(p2.validators) == {"optimal_needs_zero_gap"}


@pytest.mark.parametrize("statement, values, bind", [
    ("The loading plan is optimal.", [OPEN], ()),
    ("The loading plan of value 945 is optimal.", [OPEN], ["objective"]),
    ("This is the best possible loading plan.", [OPEN], ()),
    ("The plan is optimal.", [GAP_ONLY], ()),                       # the recorded gap, when there's no bound
    ("The plan is optimal.", [INFEASIBLE], ()),                     # infeasible is no solution, let alone optimal
    ("The schedule is provably optimal (gap 0).", [OPEN], ()),
    ("The plan is optimal.", [OPEN, GAP_ONLY], ()),                 # every result that says something denies it
])
def test_optimal_contradicted(statement, values, bind):
    assert "OPTIMAL_CONTRADICTED" in _codes(statement, *values, bind=bind)
    assert "OPTIMAL_CONTRADICTED" not in _codes(statement, *values, bind=bind, profile="optimization@2")   # frozen


@pytest.mark.parametrize("statement, values", [
    ("The loading plan of value 974 is optimal, with a proved bound of 974.", [CLOSED]),
    ("The loading plan is optimal.", [TINY]),                       # within the solvers' default tolerance
    ("The plan is optimal.", [OPEN, CLOSED]),                       # one result supports it
    # reference uses: 'optimal' as the point measured from, not said of the plan
    ("The plan is within about 3% of optimal.", [OPEN]),
    # gpt-oss-20b, optimal-plan showcase diag1, an honest seat
    ("The relative gap of 0.0072 indicates the plan is within 0.72% of the theoretical optimum.", [OPEN]),
    ("The plan's value is 3% below the optimal bound.", [OPEN]),
    ("The gap to the optimum is 3%.", [OPEN]),
    ("The plan is close to the optimum.", [OPEN]),
    ("The plan is 3% short of the true optimum.", [OPEN]),
    # not asserted
    ("The plan is not optimal: its gap is 3%.", [OPEN]),
    ("The plan is near-optimal.", [OPEN]),
    ("Optimality was not proven; the best plan found is worth 945.", [OPEN]),
    ("The optimum is not known; the best plan found is worth 945.", [OPEN]),
])
def test_optimal_supported_or_not_claimed(statement, values):
    assert "OPTIMAL_CONTRADICTED" not in _codes(statement, *values)


def test_gap_from_objective_and_bound_beats_the_recorded_gap():
    # a gap field that disagrees with its own objective and bound: the two numbers are what the solver proved
    stale = {**OPEN, "gap": 0.0}
    assert "OPTIMAL_CONTRADICTED" in _codes("The plan is optimal.", stale)

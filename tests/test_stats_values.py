"""The arithmetic behind the claim checks, pinned to values that can be checked by hand or against any
statistics reference — so a later simplification can't drift them silently."""
import math

import pytest

from hypgraph import stats


def test_rule_of_three_at_the_edges():
    lo, hi = stats.rate_bounds(0, 100)
    assert lo == 0.0 and abs(hi - (1 - 0.05 ** 0.01)) < 1e-12          # exact one-sided bound, ≈ 2.95%
    assert abs(hi - 0.0295) < 0.0005                                    # the "rule of three": about 3/n
    lo, hi = stats.rate_bounds(100, 100)
    assert hi == 1.0 and abs(lo - 0.05 ** 0.01) < 1e-12
    assert stats.rate_bounds(0, 0) == (0.0, 1.0)                         # no trials: no information


def test_wilson_interval_known_values():
    # 3 of 10 — Wilson score 95%: 0.1078 to 0.6032 (Newcombe 1998, Table I; any reference agrees to 4 places)
    lo, hi = stats.rate_bounds(3, 10)
    assert abs(lo - 0.1078) < 5e-4 and abs(hi - 0.6032) < 5e-4
    # 812 of 1000 — Wilson: 0.7866 to 0.8350
    lo, hi = stats.rate_bounds(812, 1000)
    assert abs(lo - 0.7866) < 5e-4 and abs(hi - 0.8350) < 5e-4


def test_trials_for_a_bound():
    assert stats.trials_for(0.001) == 2995                               # ln(0.05)/ln(0.999)
    assert stats.trials_for(0.01) == 299
    assert stats.trials_for(0.5) == 5                                    # 0.5^5 = 0.031 < 0.05 < 0.5^4


def test_two_proportions_known_values():
    # 10/100 vs 20/100: pooled p = 0.15, se = sqrt(0.15·0.85·0.02) = 0.05050, z = 1.980, p = 0.0477
    t = stats.two_proportions(10, 100, 20, 100)
    assert abs(t["diff"] - (-0.10)) < 1e-12
    assert abs(t["p"] - 0.0477) < 5e-4
    # Newcombe hybrid score interval for the difference 0.10 − 0.20: about −0.199 to −0.001 (Newcombe 1998 method 10)
    assert -0.205 < t["lo"] < -0.195 and -0.006 < t["hi"] < 0.0
    # identical arms: no difference, p = 1, interval centred on 0
    t = stats.two_proportions(50, 100, 50, 100)
    assert t["diff"] == 0 and t["p"] == 1.0 and abs(t["lo"] + t["hi"]) < 1e-12


def test_detectable_difference_known_value():
    # two arms of 1000 at a pooled rate 0.806: (1.96 + 0.8416) · sqrt(0.806·0.194·0.002) = 0.0496
    d = stats.detectable(812, 1000, 800, 1000)
    assert abs(d - 0.0496) < 5e-4
    assert stats.detectable(812, 1000, 800, 1000) > stats.detectable(8120, 10000, 8000, 10000)


def test_empty_arms_are_undefined_not_a_crash():
    t = stats.two_proportions(0, 0, 5, 10)
    assert t["undefined"] and t["p"] == 1.0 and (t["lo"], t["hi"]) == (-1.0, 1.0) and math.isnan(t["rate1"])
    assert stats.detectable(0, 0, 5, 10) == 1.0


@pytest.mark.parametrize("x,s", [(0.63, "63%"), (0.012, "1.2%"), (0.003, "0.3%"), (0.00003, "0.003%"), (0.0, "0%")])
def test_pct(x, s):
    assert stats.pct(x) == s


def test_one_in():
    assert stats.one_in(0.001) == "1 in 1,000"
    assert stats.one_in(1 / 3) == "1 in 3"
    assert stats.one_in(0.0) == "0"

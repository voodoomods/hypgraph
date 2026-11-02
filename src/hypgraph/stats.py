"""
The arithmetic the claim checks use, stdlib only. Each function is small enough to check by hand:

- rate_bounds(k, n)        a 95% interval for a rate seen k times in n trials. At k = 0 (or k = n) it is the exact
                           one-sided bound 1 - 0.05^(1/n) — the "rule of three" (≈ 3/n) — because "it never happened"
                           can only ever mean "it happens less often than this". Otherwise the Wilson score interval.
- trials_for(bound)        how many failure-free trials it takes before the 95% upper bound drops below ``bound``.
- two_proportions(...)     difference of two rates with a 95% interval (Newcombe's hybrid score) and a two-sided
                           p-value (pooled two-proportion z-test).
- whole(x)                 a count's k or n: an int or an integral float, finite, not a bool.
- detectable(...)          the smallest difference two samples this size could detect with 80% power at α = 0.05.
"""

from __future__ import annotations

import math

def whole(x) -> bool:
    """A whole number: an int, or a finite float with no fraction (4.0). Not a bool — a count is how many."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        return False
    return isinstance(x, int) or (math.isfinite(x) and x == int(x))


Z95 = 1.959963984540054          # two-sided 95%
Z80 = 0.8416212335729143         # one-sided 80% power


def rate_bounds(k: int, n: int) -> tuple[float, float]:
    """(lower, upper) 95% bounds for a rate seen k times in n trials."""
    if n <= 0:
        return (0.0, 1.0)
    if k <= 0:
        return (0.0, 1 - 0.05 ** (1 / n))
    if k >= n:
        return (0.05 ** (1 / n), 1.0)
    p, z = k / n, Z95
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def trials_for(bound: float) -> int:
    """Failure-free trials needed before the 95% upper bound on the rate falls below ``bound``."""
    return math.ceil(math.log(0.05) / math.log(1 - bound))


def _norm_sf(z: float) -> float:
    return 0.5 * math.erfc(z / math.sqrt(2))


def two_proportions(k1: int, n1: int, k2: int, n2: int) -> dict:
    """Rate 1 minus rate 2, with a 95% interval (Newcombe's hybrid score method) and a two-sided p-value.
    An empty arm has no rate: the difference is undefined, the interval is the whole range and p = 1 (nothing is
    shown), so a claim on it can be refused instead of crashing the check."""
    if n1 <= 0 or n2 <= 0:
        return {"diff": 0.0, "lo": -1.0, "hi": 1.0, "p": 1.0, "rate1": k1 / n1 if n1 > 0 else float("nan"),
                "rate2": k2 / n2 if n2 > 0 else float("nan"), "undefined": True}
    p1, p2 = k1 / n1, k2 / n2
    l1, u1 = _wilson(k1, n1)
    l2, u2 = _wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    pool = (k1 + k2) / (n1 + n2)
    se = math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))
    p = 2 * _norm_sf(abs(d) / se) if se > 0 else (1.0 if d == 0 else 0.0)
    return {"diff": d, "lo": lo, "hi": hi, "p": min(1.0, p), "rate1": p1, "rate2": p2}


def _wilson(k: int, n: int) -> tuple[float, float]:
    p, z = k / n, Z95
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def detectable(k1: int, n1: int, k2: int, n2: int) -> float:
    """Smallest rate difference these sample sizes detect with 80% power at two-sided α = 0.05 (normal approx.).
    With an empty arm nothing is detectable: 1.0 (the whole range)."""
    if n1 <= 0 or n2 <= 0:
        return 1.0
    pool = (k1 + k2) / (n1 + n2)
    pool = min(max(pool, 1 / (n1 + n2)), 1 - 1 / (n1 + n2))
    return (Z95 + Z80) * math.sqrt(pool * (1 - pool) * (1 / n1 + 1 / n2))


def pct(x: float) -> str:
    """A rate as a short human percentage: 63%, 1.2%, 0.30%, 0.0030%."""
    if x >= 0.1:
        return f"{x * 100:.0f}%"
    if x >= 0.01:
        return f"{x * 100:.1f}%"
    return f"{x * 100:.2g}%" if x > 0 else "0%"


def one_in(x: float) -> str:
    """A rate as '1 in N' (rounded to a readable N)."""
    if x <= 0:
        return "0"
    n = 1 / x
    for step in (1, 10, 100, 1000, 10_000, 100_000):
        if n < step * 10:
            return f"1 in {round(n / step) * step:,}" if step > 1 else f"1 in {round(n):,}"
    return f"1 in {round(n, -5):,.0f}"

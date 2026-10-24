"""Exact, stdlib-only statistics for the task generators and their reference solutions."""
from __future__ import annotations

import math

Z975 = 1.959963984540054
Z80 = 0.8416212335729143


def _lbinom(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def binom_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0
    return min(1.0, sum(math.exp(_lbinom(n, i) + i * math.log(p) + (n - i) * math.log1p(-p)) for i in range(k + 1)))


def upper_bound(k: int, n: int, conf: float = 0.95) -> float:
    """One-sided exact (Clopper-Pearson) upper bound on a rate after k events in n trials."""
    if k >= n:
        return 1.0
    if k == 0:
        return 1 - (1 - conf) ** (1 / n)
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if binom_cdf(k, n, mid) > 1 - conf:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def trials_for(rate: float, conf: float = 0.95) -> int:
    """Trials with zero events needed for the one-sided upper bound to fall below ``rate``."""
    return math.ceil(math.log(1 - conf) / math.log(1 - rate))


def mcnemar_p(b: int, c: int) -> float:
    """Exact two-sided McNemar test on the discordant pairs (b: A right & B wrong, c: the reverse)."""
    n = b + c
    if n == 0:
        return 1.0
    return min(1.0, 2 * binom_cdf(min(b, c), n, 0.5))


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """Two-sided pooled z test for a difference of proportions."""
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    if se == 0:
        return 1.0
    z = abs(k1 / n1 - k2 / n2) / se
    return math.erfc(z / math.sqrt(2))


def detectable(p: float, n_per_arm: int) -> float:
    """Smallest difference a two-sided 5 % test detects with 80 % power at baseline p, n per arm (normal approx.)."""
    return (Z975 + Z80) * math.sqrt(2 * p * (1 - p) / n_per_arm)

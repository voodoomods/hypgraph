"""
Mechanical checks on a claim before it enters the record. Each rule exists because the mistake behind it was made,
and each refusal does the arithmetic the writer skipped, then offers the honest sentence.

  code                          refused when
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
  SCOPE_MISSING                 a finding or exclusion doesn't say under which conditions it holds
  EVIDENCE_MISSING              nothing supports it
  MEASUREMENT_MALFORMED         a measurement doesn't name its result and field
  MEASUREMENT_UNKNOWN_FIELD     the result has no such value
  MEASUREMENT_MISMATCH          the measurement says a different number from its result
  UNBOUND_NUMBER                a number in the statement comes from nowhere: not a bound measurement, nothing
                                computed from them (difference, ratio, percentage, interval), the scope or a constant
  ABSOLUTE_WITHOUT_COUNT        "never" / "always" / "eliminates" / "100%" with no count of 0 or n behind it
  ABSOLUTE_UNRELATED_COUNT      the 0-of-n it leans on counts something else
  ABSOLUTE_UNDERPOWERED         0 of n, but n is too small: the rate could still be above 5%
  ABSOLUTE_HIDES_DENOMINATOR    0 of n is enough, but the statement doesn't say n — so "never" reads as never
  COMPARATIVE_WITHOUT_COMPARISON "beats" / "outperforms" / "higher than" with fewer than two sides measured
  SIGNIFICANCE_WITHOUT_TEST     "significantly" with no test behind it
  SIGNIFICANCE_NOT_SHOWN        the test behind it isn't significant
  CAUSAL_WITHOUT_INTERVENTION   "causes" / "leads to" when no experiment intervened
  EXCLUSION_WITHOUT_POWER       "no effect" / "rules out" without a search shown to find a planted effect
  CONVENTION_HEDGED             a convention that hedges

The arithmetic: a count of 0 in n trials bounds the rate at 1 - 0.05^(1/n) (95%, the "rule of three", ≈ 3/n).
"Never, in 3 trials" means "below 63%". A claim may carry ``exposure`` — how many uses, users or units it will be
applied to — and the refusal (and the claim's standing) then says how many failures that bound leaves unruled out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import language as L
from . import stats
from .derive import Snap, producing_run, result_value

_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(\s*%)?(?![\w])")
_WORDS = {w: i for i, w in enumerate("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                     "fifteen sixteen seventeen eighteen nineteen twenty".split(), start=2)}
_WORDNUM = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.I)   # 'one' is left out: too common as a pronoun
_LABEL = re.compile(r"""(['"`‘“])[0-9][0-9 ]{0,30}(['"`’”])""")
UNDERPOWERED = 0.05             # an absolute needs its 95% bound on the opposite rate at or below this
_CONVENTIONS = re.compile(r"\b(interval|confidence|CI|bounds?|power|alpha|α|significan\w*|level)\b", re.I)


@dataclass
class Problem:
    code: str
    message: str
    fix: str = ""
    words: list = field(default_factory=list)

    def text(self) -> str:
        return f"{self.message} [{self.code}]"

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "fix": self.fix, "words": self.words}


def numbers(text: str) -> list[tuple[float, int, bool, str]]:
    """(value, decimals printed, is_percent, as printed) for each number in a text."""
    out = []
    for m in _NUM.finditer(text or ""):
        whole, frac, pct = m.group(1), m.group(2), m.group(3)
        v = float(whole.replace(",", "") + ("." + frac if frac else ""))
        out.append((v, len(frac or ""), bool(pct), m.group(0).strip()))
    for m in _WORDNUM.finditer(text or ""):
        out.append((float(_WORDS[m.group(1).lower()]), 0, False, m.group(0)))
    return out


def _matches(printed: tuple, candidates: list[float]) -> bool:
    v, dec, pct, _ = printed
    for c in candidates:
        for x in ((c, c * 100) if pct or abs(c) <= 1 else (c,)):
            x = abs(x)
            if round(x, dec) == v or (dec == 0 and abs(x - v) < 0.5 and round(x) == v):
                return True
    return False


def _nums(d: dict) -> list[float]:
    vals = [float(d[k]) for k in ("value", "k", "n", "lo", "hi", "p")
            if isinstance(d.get(k), (int, float)) and not isinstance(d.get(k), bool)]
    vals += [float(x) for x in d.get("interval") or [] if isinstance(x, (int, float))]
    return vals


def _arm(rv: dict) -> tuple[int, int] | None:
    """(k, n) when a result value is a count."""
    k, n = rv.get("k"), rv.get("n")
    if isinstance(k, (int, float)) and isinstance(n, (int, float)) and n > 0 and 0 <= k <= n:
        return int(k), int(n)
    return None


def _primary(rv: dict) -> float | None:
    a = _arm(rv)
    if a:
        return a[0] / a[1]
    v = rv.get("value")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def derived_numbers(bound: list[tuple[dict, dict]]) -> tuple[list[float], list[float]]:
    """Every number a claim may state because it follows from its bound measurements, in two tiers.

    plain        the values themselves; for a count k of n the rate, its complement and n - k; for each pair of
                 measurements the difference, both ratios, the relative change and the sum. May be rounded.
    statistical  95% bounds of each rate; for each pair of counts the two-proportion interval, p-value and the
                 smallest difference they could detect. Must be written to at least one decimal place — otherwise
                 "5 points better" would pass because an interval happens to end at 5.3."""
    plain: list[float] = []
    stat: list[float] = []
    prim = []
    arms = []
    for m, rv in bound:
        plain += _nums(m) + _nums(rv)
        a = _arm(rv)
        if a:
            k, n = a
            lo, hi = stats.rate_bounds(k, n)
            plain += [k / n, 1 - k / n, n - k]
            stat += [lo, hi]
            arms.append(a)
        p = _primary(rv)
        if p is not None:
            prim.append(p)
    for i, a in enumerate(prim):
        for b in prim[i + 1:]:
            plain += [a - b, a + b]
            if b:
                plain += [a / b, (a - b) / b]
            if a:
                plain += [b / a, (b - a) / a]
    for i, (k1, n1) in enumerate(arms):
        for k2, n2 in arms[i + 1:]:
            t = stats.two_proportions(k1, n1, k2, n2)
            stat += [t["lo"], t["hi"], t["p"], stats.detectable(k1, n1, k2, n2)]
    return plain, stat


def _matches_stat(printed: tuple, candidates: list[float]) -> bool:
    """A statistical quantity counts only when written to at least one decimal place (or as a 'p = 0.03' style
    value), so a rounded integer can't borrow an interval's end."""
    return printed[1] >= 1 and _matches(printed, candidates)


def _bound(s: Snap, meas: list) -> tuple[list[tuple[dict, dict]], list[Problem]]:
    """Measurements that check out against their results, and problems with the rest."""
    good, problems = [], []
    for i, m in enumerate(meas):
        if not isinstance(m, dict) or not m.get("result") or not m.get("key"):
            problems.append(Problem("MEASUREMENT_MALFORMED", f"measurement {i + 1}: give {{name, value (or k/n), "
                                    "result: <result id>, key: <field>}"))
            continue
        rv = result_value(s, str(m["result"]), str(m["key"]))
        if rv is None:
            problems.append(Problem("MEASUREMENT_UNKNOWN_FIELD", f"measurement {m.get('name') or i + 1}: result "
                                    f"{m['result']} has no value '{m['key']}'"))
            continue
        bad = False
        for k in ("value", "k", "n"):
            if k in m and k in rv and isinstance(m[k], (int, float)) and isinstance(rv[k], (int, float)):
                dec = len(str(m[k]).split(".")[1]) if "." in str(m[k]) else 0
                if round(float(rv[k]), dec) != round(float(m[k]), dec) and not (
                        rv[k] <= 1 < m[k] and round(float(rv[k]) * 100, dec) == round(float(m[k]), dec)):
                    problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name') or i + 1}: says "
                                            f"{k}={m[k]} but result {m['result']} has {rv[k]}"))
                    bad = True
        if not bad:
            good.append((m, rv))
    return good, problems


def _exposure_note(bound_rate: float, body: dict) -> str:
    x = body.get("exposure")
    if not isinstance(x, (int, float)) or x <= 0:
        return ""
    unit = str(body.get("exposure_unit") or "uses").strip()
    return (f" Across the {x:,.0f} {unit} this claim applies to, that leaves up to {bound_rate * x:,.0f} not ruled "
            "out.")


def _absolutes(stmt: str, scope: str, body: dict, bound: list) -> list[Problem]:
    words = L.found(L.ABSOLUTE, stmt)
    if not words:
        return []
    w = words[0]
    arms = [(m, rv, _arm(rv)) for m, rv in bound if _arm(rv)]
    exact = [(m, rv, a) for m, rv, a in arms if a[0] in (0, a[1])]
    if not exact:
        seen = ", ".join(f"{a[0]} of {a[1]:,}" for _m, _rv, a in arms)
        return [Problem("ABSOLUTE_WITHOUT_COUNT",
                        f"'{w}' is absolute: back it with a k/n measurement of what it's about, where k is 0 or n, and "
                        "keep the scope to the trials actually run — or say 'rarely' / 'in k of n'"
                        + (f" (what was measured: {seen})" if seen else ""),
                        fix="state the count instead: 'in k of n trials'", words=words)]
    about = L.content_words(stmt)
    relevant = [x for x in exact if L.content_words(f"{x[0].get('name', '')} {x[0].get('key', '')}") & about]
    if not relevant:
        names = ", ".join(repr(x[0].get("name") or x[0].get("key")) for x in exact)
        return [Problem("ABSOLUTE_UNRELATED_COUNT",
                        f"'{w}' leans on a count of something else ({names}): name the measurement after what it "
                        "counts — the thing the statement says never (or always) happens — or bind that count",
                        fix="name the k/n measurement after what it counts", words=words)]
    m, rv, (k, n) = max(relevant, key=lambda x: x[2][1])
    lo, hi = stats.rate_bounds(k, n)
    opposite = hi if k == 0 else 1 - lo               # how often the opposite could still happen
    seen = f"{k} of {n:,}"
    what = "it happening" if k == 0 else "it failing"
    if opposite > UNDERPOWERED:
        need = stats.trials_for(0.001)
        honest = (f"'no {'occurrences' if k == 0 else 'exceptions'} in {n:,} trials (95% upper bound "
                  f"{stats.pct(opposite)})'")
        return [Problem("ABSOLUTE_UNDERPOWERED",
                        f"'{w}' rests on {seen}: that only rules out {what} more than {stats.pct(opposite)} of the "
                        f"time (95% upper bound). Honest version: {honest}. To support a rate below 1 in 1,000 you "
                        f"need about {need:,} trials without one." + _exposure_note(opposite, body),
                        fix=honest.strip("'"), words=words)]
    stated = {round(v) for v, *_ in numbers(f"{stmt} {scope}")}
    if n not in stated:
        return [Problem("ABSOLUTE_HIDES_DENOMINATOR",
                        f"'{w}' rests on {seen} — say the {n:,} in the statement or scope, so readers can see what "
                        f"'{w}' means here: {what} no more than {stats.pct(opposite)} of the time "
                        f"({stats.one_in(opposite)}, 95% upper bound)." + _exposure_note(opposite, body),
                        fix=f"add 'in {n:,} trials'", words=words)]
    return []


def _measured_claim(s: Snap, support: list[str]) -> bool:
    """A supporting claim that itself binds two sides: a comparison built on it inherits them."""
    for sid in support:
        n = s.nodes.get(sid)
        if n and n["type"] == "claim":
            sides = [m for m in n["body"].get("measurements") or [] if isinstance(m, dict) and
                     _primary(result_value(s, str(m.get("result") or ""), str(m.get("key") or "")) or {}) is not None]
            if len(sides) >= 2:
                return True
    return False


def _comparisons(s: Snap, stmt: str, bound: list, support: list[str]) -> list[Problem]:
    out = []
    comp = L.found(L.COMPARATIVE, stmt)
    tested = any(isinstance(rv.get("p"), (int, float)) or rv.get("interval") for _m, rv in bound)
    if comp and len([1 for _m, rv in bound if _primary(rv) is not None]) < 2 and not tested \
            and not _measured_claim(s, support):
        out.append(Problem("COMPARATIVE_WITHOUT_COMPARISON",
                           f"'{comp[0]}' compares, but there is nothing to compare: bind a measurement for each side "
                           "(a k/n or value for both), or a difference with its interval",
                           fix="bind both sides as measurements", words=comp))
    sig = L.found(L.SIGNIFICANCE, stmt)
    if sig:
        bound_p = [float(rv["p"]) for _m, rv in bound if isinstance(rv.get("p"), (int, float))]
        arms = [_arm(rv) for _m, rv in bound if _arm(rv)]
        if bound_p:
            if min(bound_p) > 0.05:
                out.append(Problem("SIGNIFICANCE_NOT_SHOWN",
                                   f"'{sig[0]}': the bound p-value is {min(bound_p):.3g}, not below 0.05 — say the "
                                   "difference and that it isn't significant", words=sig))
        elif len(arms) >= 2:
            (k1, n1), (k2, n2) = arms[0], arms[1]
            t = stats.two_proportions(k1, n1, k2, n2)
            if t["p"] >= 0.05:
                out.append(Problem("SIGNIFICANCE_NOT_SHOWN",
                                   f"'{sig[0]}': the bound counts ({k1:,}/{n1:,} against {k2:,}/{n2:,}) differ by "
                                   f"{t['diff'] * 100:.1f} points, 95% interval {t['lo'] * 100:.1f} to "
                                   f"{t['hi'] * 100:.1f}, p = {t['p']:.2g} (two-proportion z-test) — not significant "
                                   "at 0.05. Say the difference and that it isn't significant.", words=sig))
        else:
            out.append(Problem("SIGNIFICANCE_WITHOUT_TEST",
                               f"'{sig[0]}' claims a test was passed: bind a result field holding the p-value or "
                               "interval, or bind both sides as counts (k/n) so the record can test them",
                               fix="bind a p-value, or both sides as k/n", words=sig))
    return out


def _causal(s: Snap, stmt: str, support: list[str]) -> list[Problem]:
    words = L.found(L.CAUSAL, stmt)
    if not words:
        return []
    for sid in support:
        if sid in s.nodes and s.nodes[sid]["type"] == "result":
            run = producing_run(s, sid)
            if run and any(e["rel"] == "executes" for e in s.out.get(run, [])):
                return []
    return [Problem("CAUSAL_WITHOUT_INTERVENTION",
                    f"'{words[0]}' is causal, but nothing supporting it comes from an experiment that intervened (a "
                    "result produced by a run that executes an experiment). Say 'is associated with' — or run the "
                    "experiment.", fix="say 'is associated with'", words=words)]


def _exclusion(s: Snap, stmt: str, kind: str, support: list[str], bound: list) -> list[Problem]:
    words = L.found(L.EXCLUSION, stmt)
    if kind != "exclusion" and not (words and kind not in ("inconclusive", "lead", "convention")):
        return []
    for sid in support:
        src = s.nodes[sid]
        if src["type"] == "result" and src["body"].get("power") == "demonstrated":
            return []
        run = producing_run(s, src["id"]) if src["type"] == "result" else None
        for e in s.out.get(run or "", []):
            if e["rel"] == "executes" and s.nodes[e["dst"]]["body"].get("power_check"):
                return []
    arms = [_arm(rv) for _m, rv in bound if _arm(rv)]
    size = ""
    if len(arms) >= 2:
        (k1, n1), (k2, n2) = arms[0], arms[1]
        size = (f" At these sample sizes ({n1:,} and {n2:,}) a difference smaller than about "
                f"{stats.detectable(k1, n1, k2, n2) * 100:.1f} points would usually go unseen (80% power, α 0.05).")
    said = f"'{words[0]}' says an effect is absent, so it is an exclusion: " if words and kind != "exclusion" else ""
    return [Problem("EXCLUSION_WITHOUT_POWER",
                    said + "an exclusion needs a search that recovered a planted answer (a result with "
                    "power=demonstrated, or a run of an experiment with a power_check) — otherwise file it as "
                    "inconclusive." + size, fix="file it as kind=inconclusive, or show the search can find a planted "
                    "effect", words=words)]


def claim_issues(s: Snap, body: dict, support: list[str], inv: str) -> list[Problem]:
    """What's wrong with a claim, each with a code, a message and a fix (empty = it may enter the record).
    ``support``: ids of the nodes that support it or that it is derived from."""
    kind = body.get("kind") or "finding"
    stmt = body.get("statement", "")
    scope = body.get("scope", "")
    invb = s.nodes.get(inv, {}).get("body", {}) if inv else {}
    if invb.get("strict_claims") is False:
        return []
    problems: list[Problem] = []
    if kind in ("finding", "exclusion") and len(scope.strip()) < 10:
        problems.append(Problem("SCOPE_MISSING", "scope: say under which conditions this holds (the data, method, "
                                "sample) — at least a sentence"))
    if kind == "convention" and L.HEDGE.search(stmt):
        problems.append(Problem("CONVENTION_HEDGED", "a convention states agreed notation; a hedged interpretation "
                                "(could / suggests / consistent with) is a finding or a lead"))
    support = [x for x in support if x in s.nodes]
    if kind in ("finding", "exclusion", "inconclusive") and not support:
        problems.append(Problem("EVIDENCE_MISSING", "link the evidence: at least one result, claim or source that "
                                "supports it (links: {\"rel\": \"supports\", \"from\": <result id>, \"why\": …})"))
    bound, bad = _bound(s, body.get("measurements") or [])
    problems += bad
    clean = _LABEL.sub(" ", stmt)
    plain, stat = derived_numbers(bound)
    allowed = plain + [v for v, *_ in numbers(scope)] + \
        [float(c) for c in (invb.get("constants") or []) if isinstance(c, (int, float))]
    if _CONVENTIONS.search(clean):                   # "95% interval", "α 0.05", "80% power" are conventions
        allowed += [95.0, 99.0, 90.0, 80.0, 0.05, 0.01]
    loose = [p for p in numbers(clean) if not _matches(p, allowed) and not _matches_stat(p, stat)]
    if loose:
        problems.append(Problem("UNBOUND_NUMBER", "numbers in the statement that no bound measurement, the scope or the "
                                "investigation's constants account for: " + ", ".join(p[3] for p in loose[:8])
                                + " — bind them to result fields (measurements) or move design constants into the "
                                "scope", fix="bind each number to a result field", words=[p[3] for p in loose[:8]]))
    problems += _absolutes(clean, scope, body, bound)
    if kind not in ("lead", "convention"):
        problems += _comparisons(s, clean, bound, support)
        problems += _causal(s, clean, support)
    problems += _exclusion(s, clean, kind, support, bound)
    return problems


def claim_problems(s: Snap, body: dict, support: list[str], inv: str) -> list[str]:
    """The problems as text lines (see claim_issues for the structured form)."""
    return [p.text() for p in claim_issues(s, body, support, inv)]

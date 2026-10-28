"""
Mechanical checks on a claim before it enters the record. Each rule exists because the mistake behind it was made,
and each refusal does the arithmetic the writer skipped, then offers the honest sentence.

  code                          refused when
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
  STATEMENT_EMPTY               the statement says nothing ("Placeholder.", "TBD", one word)
  SCOPE_MISSING                 a finding or exclusion doesn't say under which conditions it holds
  EVIDENCE_MISSING              nothing supports it
  MEASUREMENT_MALFORMED         a measurement doesn't name its result and field
  MEASUREMENT_UNKNOWN_FIELD     the result has no such value
  MEASUREMENT_MISMATCH          the measurement says a different number from its result
  UNBOUND_NUMBER                a number in the statement comes from nowhere: not a bound measurement, nothing
                                computed from them (difference, ratio, percentage, interval), the scope or a constant
  KEY_FOR_NUMBER                the statement names a bound measurement's key (case8_expected) in place of its value
  ABSOLUTE_WITHOUT_COUNT        "never" / "always" / "eliminates" / "100%" with no count of 0 or n behind it
                                (an absolute over a set the sentence enumerates — "all three subsets: …" — is
                                not a generalisation and is left alone)
  ABSOLUTE_UNRELATED_COUNT      the 0-of-n it leans on counts something else
  ABSOLUTE_UNDERPOWERED         0 of n with n too small (the rate could still be above 5%), and the statement
                                generalises past the n trials instead of saying them ("never leaks")
  ABSOLUTE_HIDES_DENOMINATOR    0 of n is enough, but neither statement nor scope says n — "never" reads as never
  COMPARATIVE_WITHOUT_COMPARISON "beats" / "outperforms" / "higher than" with fewer than two sides measured
  SIGNIFICANCE_WITHOUT_TEST     "significantly" with no test behind it
  SIGNIFICANCE_NOT_SHOWN        the test behind it isn't significant
  SIGNIFICANCE_CONTRADICTED     "not significant", but the bound evidence is (p < 0.05)
  CAUSAL_WITHOUT_INTERVENTION   "causes" / "leads to" when no experiment intervened
  EXCLUSION_WITHOUT_POWER       "no effect" / "rules out" without a search shown to find a planted effect
  CONVENTION_HEDGED             a convention that hedges
  UNCORRECTED_EFFECT            a finding says an outcome changed / differs / is significant on an uncorrected
                                test, while a live result in the investigation holds that outcome's corrected
                                (Holm / Bonferroni / FDR …) p-value at or above 0.05, or a count of 0 outcomes
                                surviving correction — and neither is the effect word qualified, within 20
                                words, as uncorrected ("differs at uncorrected p < 0.05"), nor is the correction
                                named with a corrected value bound. Two of twelve runs of a 20-outcome trial settled "the supplement
                                changes steps_k" as a finding, hedged only in the scope field, while the same
                                record's Holm-corrected p was 0.25.

A word counts only when its sentence asserts it (language.asserted): "not significantly better", "no evidence
that it ever fails" and "we cannot conclude that…" are honest and pass; the overclaim is the unnegated form.

The arithmetic: a count of 0 in n trials bounds the rate at 1 - 0.05^(1/n) (95%, the "rule of three", ≈ 3/n).
"Never, in 3 trials" means "below 63%". A claim may carry ``exposure`` — how many uses, users or units it will be
applied to — and the refusal (and the claim's standing) then says how many failures that bound leaves unruled out.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import language as L
from . import stats
from .derive import Snap, lifecycle, producing_run, result_value

_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(\s*%)?(?![\w])")
_WORDS = {w: i for i, w in enumerate("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                     "fifteen sixteen seventeen eighteen nineteen twenty".split(), start=2)}
_WORDNUM = re.compile(r"(?<!-)\b(" + "|".join(_WORDS) + r")\b(?!-)", re.I)   # 'one' is left out: too common as a
_LABEL = re.compile(r"""(['"`‘“])[0-9][0-9 ]{0,30}(['"`’”])""")                 # pronoun; "two-sided" is a name
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[\d:.]+)?\b")                      # a date is not a measurement
# identifiers that look like numbers but aren't measurements: a version (1.10.0, v2.0.0-rc.1), inline code, a number a
# label word names ("case 8", "cases 9–12", "test 4", "line 12", "#3"), or one that labels the literal after it ("9 ('')")
_NOT_A_FIGURE = re.compile(
    r"`[^`\n]*`|(?<![\w.])v?\d+(?:\.\d+){2,}(?:[-+][0-9A-Za-z.]+)?(?![\w])"
    r"|\b(?:cases?|tests?|lines?|steps?|items?|rows?|issues?|sections?|rules?|figures?|tables?|questions?|no\.)\s+"
    r"\d+(?:\s*(?:[–-]|to|and|,)\s*\d+)*\b"
    r"|#\d+\b|(?<![\w.])\d+(?=\s*\(\s*['\"‘“`])", re.I)
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
    """(value, decimals printed, is_percent, as printed) for each number in a text. Versions and inline code are
    identifiers, not figures, and are skipped."""
    out = []
    text = _NOT_A_FIGURE.sub(" ", text or "")
    for m in _NUM.finditer(text):
        whole, frac, pct = m.group(1), m.group(2), m.group(3)
        v = float(whole.replace(",", "") + ("." + frac if frac else ""))
        out.append((v, len(frac or ""), bool(pct), m.group(0).strip()))
    for m in _WORDNUM.finditer(text):
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


_ENUM = re.compile(r"\b(all|every|each|none|neither|both)\b", re.I)
_SMALL = r"(?:\d{1,3}(?:,\d{3})*|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)"
_ENUM_COUNT = re.compile(r"^\s*(?:(?:of|other|remaining|but one of|one of)\s+)?(?:the\s+|these\s+|those\s+|its\s+)?"
                         r"(?:other\s+|remaining\s+)?" + _SMALL + r"\b", re.I)
# the set was counted just before the word, in the same clause: "cases 1-7 all pass", "the 20 outcomes all have"
_ENUM_BEFORE = re.compile(r"(?:\d+\s*[-–]\s*\d+|\b" + _SMALL + r"\b)(?:\s+[\w-]+){0,2}\s*$", re.I)


def _enumerated(stmt: str, word: str) -> bool:
    """An absolute that quantifies over a set the sentence itself enumerates is not a generalisation past the
    sample: "all three subsets", "in every subset: math −2.6, code −2.2, reading −0.4". The rule is lexical —
    a small count right after the word, or a breakdown of two or more numbers after a colon or bracket in the
    same sentence — so it can be replayed on a refusal log that holds only the statement."""
    if not _ENUM.fullmatch(word):
        return False
    m = re.search(r"\b" + re.escape(word) + r"\b", stmt, re.I)
    if not m:
        return False
    rest = re.split(r"[.!?](?:\s|$)", stmt[m.end():], maxsplit=1)[0]
    if _ENUM_COUNT.match(rest):
        return True
    head = stmt[:m.start()]
    c0 = max((x.end() for x in L._CLAUSE.finditer(head)), default=0)
    if _ENUM_BEFORE.search(head[c0:]):
        return True
    brk = re.search(r"[:(\[—]", rest)
    return bool(brk) and len(numbers(rest[brk.end():])) >= 2


_PROVEN = re.compile(r"^prov(?:es?|en|ed)$|^proof$", re.I)


def _absolutes(stmt: str, scope: str, body: dict, bound: list) -> list[Problem]:
    words = [w for w in L.asserted(L.ABSOLUTE, stmt) if not _enumerated(stmt, w)]
    if any(str(m.get("key") or "").lower() in ("gap", "bound") for m, _rv in bound):
        words = [w for w in words if not _PROVEN.match(w)]      # an optimum with its bound (gap 0) is proven
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
    in_statement = n in {round(v) for v, *_ in numbers(stmt)}
    in_scope = n in {round(v) for v, *_ in numbers(scope)}
    if in_statement:
        return []          # scoped to the trials it states ("nothing in 50 prompts"); its standing carries the bound
    if opposite > UNDERPOWERED:
        need = stats.trials_for(0.001)
        honest = (f"'no {'occurrences' if k == 0 else 'exceptions'} in {n:,} trials (95% upper bound "
                  f"{stats.pct(opposite)})'")
        return [Problem("ABSOLUTE_UNDERPOWERED",
                        f"'{w}' rests on {seen}: that only rules out {what} more than {stats.pct(opposite)} of the "
                        f"time (95% upper bound). Honest version: {honest}. To support a rate below 1 in 1,000 you "
                        f"need about {need:,} trials without one." + _exposure_note(opposite, body),
                        fix=honest.strip("'"), words=words)]
    if in_scope:
        return []          # enough trials, and the scope says how many
    return [Problem("ABSOLUTE_HIDES_DENOMINATOR",
                    f"'{w}' rests on {seen} — say the {n:,} in the statement or scope, so readers can see what "
                    f"'{w}' means here: {what} no more than {stats.pct(opposite)} of the time "
                    f"({stats.one_in(opposite)}, 95% upper bound)." + _exposure_note(opposite, body),
                    fix=f"add 'in {n:,} trials'", words=words)]


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


def _is_p_key(key: str) -> bool:
    """A result field holding a p-value, by its name: a token ``p`` anywhere (p, p_value, p_welch, welch_two_sided_p,
    raw_p_steps_k, steps_k_p), or pval / pvalue / padj — the record's agents name p-values both ways round."""
    toks = [t for t in re.split(r"[^a-z0-9]+", key.lower()) if t]
    if "top" in toks or _NOT_EVIDENCE.search(key):             # top_p is a sampling parameter; a threshold is a convention
        return False
    return "p" in toks or any(t in ("pval", "pvalue", "pvalues", "padj") for t in toks)


def _p_values(s: Snap, bound: list, support: list[str]) -> list[float]:
    """The p-values behind a claim: a bound value dict's `p`, a bound field *named* p / p_value / p_<test>
    (an exact McNemar p registered as `p_exact` is a test), and such fields on the results that support it."""
    ps = [float(rv["p"]) for _m, rv in bound if isinstance(rv.get("p"), (int, float))]
    for m, rv in bound:
        key = str(m.get("key") or m.get("name") or "")
        v = rv.get("value")
        if _is_p_key(key) and isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1:
            ps.append(float(v))
    for rid in support:
        n = s.nodes.get(rid)
        if not n or n["type"] != "result":
            continue
        for key, rv in (n["body"].get("values") or {}).items():
            v = rv.get("value") if isinstance(rv, dict) else rv
            if _is_p_key(str(key)) and isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v <= 1:
                ps.append(float(v))
    return ps


def _comparisons(s: Snap, stmt: str, bound: list, support: list[str]) -> list[Problem]:
    out = []
    comp = L.asserted(L.COMPARATIVE, stmt)
    tested = any(isinstance(rv.get("p"), (int, float)) or rv.get("interval") for _m, rv in bound)
    if comp and len([1 for _m, rv in bound if _primary(rv) is not None]) < 2 and not tested \
            and not _measured_claim(s, support):
        out.append(Problem("COMPARATIVE_WITHOUT_COMPARISON",
                           f"'{comp[0]}' compares, but there is nothing to compare: bind a measurement for each side "
                           "(a k/n or value for both), or a difference with its interval",
                           fix="bind both sides as measurements", words=comp))
    sig = L.asserted(L.SIGNIFICANCE, stmt)
    bound_p = _p_values(s, bound, [])                      # the claim's own measurements
    support_p = _p_values(s, [], support)                  # a named p on a supporting result: the last resort
    arms = [_arm(rv) for _m, rv in bound if _arm(rv)]
    no_sig = L.denied(L.SIGNIFICANCE, stmt)
    corrected_p = _p_values(s, [(m, rv) for m, rv in bound if _corrected_key(str(m.get("key") or ""))], [])
    # "not significant": the record checks that too — against the corrected p-values when the sentence names a
    # correction (a raw p below 0.05 is what "not significant after correction" is about), and not at all when the
    # sentence also asserts an effect ("exactly one differs …; the other 19 are not significant" denies the others)
    if no_sig and not sig and not L.asserted(L.EFFECT, stmt):
        if _CORRECTION_NAMED.search(stmt):
            p = min(corrected_p) if corrected_p else None
        else:
            pool = bound_p
            p = min(pool) if pool else (stats.two_proportions(*arms[0], *arms[1])["p"] if len(arms) >= 2
                                        else (min(support_p) if support_p else None))
        if p is not None and p < 0.05:
            out.append(Problem("SIGNIFICANCE_CONTRADICTED",
                               f"the statement denies significance ('{no_sig[0]}'), but the bound evidence is "
                               f"significant: p = {p:.2g} — say the difference and that it is significant at 0.05",
                               words=no_sig))
    if sig:
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
        elif support_p:
            if min(support_p) > 0.05:
                out.append(Problem("SIGNIFICANCE_NOT_SHOWN",
                                   f"'{sig[0]}': the p-value on the supporting result is {min(support_p):.3g}, not below "
                                   "0.05 — say the difference and that it isn't significant", words=sig))
        else:
            out.append(Problem("SIGNIFICANCE_WITHOUT_TEST",
                               f"'{sig[0]}' claims a test was passed: bind a result field holding the p-value (a field "
                               "named p, p_value or p_<test>, e.g. p_mcnemar) or an interval, or bind both sides as "
                               "counts (k/n) so the record can run its own two-proportion test",
                               fix="bind a p-value, or both sides as k/n", words=sig))
    return out


def _causal(s: Snap, stmt: str, support: list[str]) -> list[Problem]:
    words = L.asserted(L.CAUSAL, stmt)
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


# "no difference remains significant after correction": a sentence about a test's verdict, not an absence claim
_SURVIVAL = re.compile(r"\b(surviv\w*|correct(?:ed|ion|ing)|remains? significant|reach(?:es)? significance)\b", re.I)


def _exclusion(s: Snap, stmt: str, kind: str, support: list[str], bound: list) -> list[Problem]:
    words = [w for w in L.asserted(L.EXCLUSION, stmt)
             if not (L.denied(L.SIGNIFICANCE, _near(stmt, w)) or _SURVIVAL.search(_near(stmt, w)))]
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


_PLACEHOLDER = re.compile(r"^\W*(?:(?:placeholder|tbd|todo|tba|n/?a|none|wip|xxx|test|claim|statement|pending|"
                          r"to be (?:determined|confirmed|added)|lorem ipsum)\W*)+$", re.I)


# ── multiplicity ─────────────────────────────────────────────────────────────
# A result field holding a corrected p-value or a count of outcomes surviving correction, by its key:
# p_holm_steps_k, steps_k_bonferroni_adj_p, min_adjusted_p, n_holm_sig, n_bonferroni_significant. A threshold
# (bonferroni_alpha_threshold = 0.0025) is a convention, not evidence.
_CORRECTED = re.compile(r"(?<![a-z])(holm|bonferroni|sidak|fdr|bh|benjamini|hochberg|fwer|adj|adjusted|corrected|corr)"
                        r"(?![a-z])", re.I)
_P_KEY = re.compile(r"(?<![a-z])(p|pval|pvalue|p_?value|padj|q|qval|qvalue)(?![a-z])", re.I)
_COUNT_KEY = re.compile(r"(?<![a-z])(sig|signif|significant|surviv\w*|rejected|rejections|discoveries)(?![a-z])", re.I)
_NOT_EVIDENCE = re.compile(r"(?<![a-z])(alpha|thresh(?:old)?|thr|cutoff|level|critical|crit)(?![a-z])", re.I)
_FAMILY = {"min", "max", "smallest", "largest", "family", "overall", "global", "any", "all", "n", "num", "count",
           "outcomes", "tests", "value", "after", "two", "sided"}
# the sentence says the test it rests on is uncorrected: "differs at uncorrected p < 0.05", "changes steps_k only
# nominally" — the reader is told, in the sentence, and the rule leaves it to the reviewer
_UNCORRECTED_SAID = re.compile(r"\b(uncorrected|unadjusted|nominal(?:ly)?|raw p|without (?:multiplicity |any )?correction|"
                               r"before (?:multiplicity |any )?correction|not corrected|no (?:multiplicity )?correction|"
                               r"per-outcome|single-outcome)\b", re.I)
# the statement names the correction: "Holm p = 0.25", "after Bonferroni correction", "corrected for multiplicity"
_CORRECTION_NAMED = re.compile(r"\b(correct(?:ed|ion|ing)|adjust(?:ed|ment)|holm|bonferroni|[sš]id[aá]k|fdr|benjamini|"
                               r"family-?wise|multiplicity|multiple (?:testing|comparisons|outcomes))\b", re.I)


def _corrected_key(key: str) -> bool:
    return bool(_CORRECTED.search(key)) and not _NOT_EVIDENCE.search(key)


def _fails_correction(key: str, rv: dict) -> str:
    """How a corrected value says the effect doesn't survive — 'p_holm_x = 0.25', 'n_holm_sig = 0 of 20' — or ''."""
    if _COUNT_KEY.search(key):
        a = _arm(rv)
        count = a[0] if a else rv.get("value")
        if isinstance(count, (int, float)) and not isinstance(count, bool) and count == 0:
            return f"{key} = 0" + (f" of {a[1]}" if a else "")
        return ""
    if _P_KEY.search(key):
        v = rv.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool) and 0.05 <= v <= 1:
            return f"{key} = {v:.3g}"
    return ""


def _corrected_evidence(s: Snap, inv: str) -> list[tuple[str, str, str, list[str]]]:
    """Every corrected value on the investigation's live results in which an effect does not survive:
    (result id, key, how it says so, the outcome tokens the key names — empty for a family-wide value)."""
    out = []
    for rid, n in s.nodes.items():
        if n["type"] != "result" or n.get("inv") != inv or lifecycle(s, rid) != "active":
            continue
        for key in (n["body"].get("values") or {}):
            k = str(key)
            if not _corrected_key(k):
                continue
            rv = result_value(s, rid, k)
            how = _fails_correction(k, rv) if rv else ""
            if not how:
                continue
            toks = [t for t in re.split(r"[^a-z0-9]+", k.lower()) if t]
            outcome = [t for t in toks if not (_CORRECTED.fullmatch(t) or _P_KEY.fullmatch(t) or _COUNT_KEY.fullmatch(t)
                                                or t in _FAMILY)]
            out.append((rid, k, how, outcome))
    return out


_SENT = re.compile(r"[.!?](?=\s|$)")              # a full stop before space or the end: not the one in "p < 0.05"


_WINDOW = 20                                     # words either side of the effect word that can qualify it


def _near(text: str, word: str) -> str:
    """The words around the word's first occurrence — up to _WINDOW either side, within its sentence. A qualifier
    counts only here: "differs at uncorrected p < 0.05" is qualified; "changes steps_k … (sixty words) … while
    dropping its uncorrected p < 0.05 claim" is not, though both sit in one sentence."""
    m = re.search(r"\b" + re.escape(word) + r"\b", text, re.I)
    if not m:
        return ""
    starts = [x.end() for x in _SENT.finditer(text, 0, m.start())]
    ends = [x.start() for x in _SENT.finditer(text, m.end())]
    s0, s1 = (starts[-1] if starts else 0), (ends[0] if ends else len(text))
    before = re.findall(r"\S+", text[s0:m.start()])[-_WINDOW:]
    after = re.findall(r"\S+", text[m.start():s1])[:_WINDOW + 1]
    return " ".join(before + after)


def _uncorrected(s: Snap, stmt: str, bound: list, inv: str) -> list[Problem]:
    """A finding that asserts an effect the record's own corrected result says does not survive."""
    words = L.asserted(L.EFFECT, stmt)
    words += [w for w in L.asserted(L.SIGNIFICANCE, stmt) if w not in words]
    words = [w for w in words if not _UNCORRECTED_SAID.search(_near(stmt, w))]
    if not words or not inv:
        return []
    nominal = any(p < 0.05 for p in _p_values(s, [(m, rv) for m, rv in bound
                                                  if not _CORRECTED.search(str(m.get("key") or ""))], []))
    hits = []
    for rid, key, how, outcome in _corrected_evidence(s, inv):
        if outcome:
            pat = r"(?<![a-z0-9])" + r"[ _\-]?".join(re.escape(t) for t in outcome) + r"(?![a-z0-9])"
            if re.search(pat, stmt, re.I):          # the statement names the outcome (a scope may name others)
                hits.append((0, rid, key, how, "_".join(outcome)))
        elif nominal:                   # a family-wide value applies when the claim rests on a nominal p < 0.05
            hits.append((1, rid, key, how, ""))
    if not hits:
        return []
    named = bool(_CORRECTION_NAMED.search(stmt))
    binds = any(_corrected_key(str(m.get("key") or "")) for m, _rv in bound)
    if named and binds:
        return []
    hits.sort(key=lambda h: h[0])
    _, rid, _key, how, outcome = hits[0]
    seen = f"{s.nodes[rid]['code'] or rid}.{how}"
    w = words[0]
    about = f"an effect on {outcome}" if outcome else "an effect"
    lack = ("the corrected value is bound, but the statement doesn't say so" if binds else
            "the statement names the correction but binds none of its values" if named else
            "the claim binds none of that and its statement doesn't say so")
    return [Problem("UNCORRECTED_EFFECT",
                    f"'{w}' asserts {about} from an uncorrected test, but the record holds the corrected result: "
                    f"{seen} — the effect does not survive correction over the family. {lack.capitalize()}: bind "
                    "the corrected value as a measurement and say in the statement that it does not survive "
                    "correction ('uncorrected p = …; Holm p = …, not significant after correction over the N "
                    "outcomes'); or say beside the effect word that the test is uncorrected; or file this as kind=lead.",
                    fix="bind the corrected p and say it does not survive correction, say 'uncorrected' in the "
                        "sentence, or file it as kind=lead",
                    words=words)]


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
    if _PLACEHOLDER.match(stmt) or len(re.findall(r"[^\W\d_]{3,}", stmt)) < 2:
        # a claim written to clear a gate (studies/challenges E2: "Placeholder.", contested and left in the record)
        problems.append(Problem("STATEMENT_EMPTY", "the statement says nothing: write the finding itself — what was "
                                "measured, on what, and what it came to"))
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
    clean = _DATE.sub(" ", _LABEL.sub(" ", stmt))
    plain, stat = derived_numbers(bound)
    allowed = plain + [v for v, *_ in numbers(scope)] + \
        [float(c) for c in (invb.get("constants") or []) if isinstance(c, (int, float))]
    for src in support:                              # a cited source's own text accounts for the numbers in it
        sb = s.nodes[src]["body"] if s.nodes[src]["type"] == "source" else {}
        allowed += [v for v, *_ in numbers(" ".join(str(sb.get(k) or "") for k in ("passage", "citation", "title")))]
    if _CONVENTIONS.search(clean):                   # "95% interval", "α 0.05", "80% power" are conventions
        allowed += [95.0, 99.0, 90.0, 80.0, 0.05, 0.01]
    loose = [p for p in numbers(clean) if not _matches(p, allowed) and not _matches_stat(p, stat)]
    if loose:
        problems.append(Problem("UNBOUND_NUMBER", "numbers in the statement that no bound measurement, the scope or the "
                                "investigation's constants account for: " + ", ".join(p[3] for p in loose[:8])
                                + " — bind them to result fields (measurements) or move design constants into the "
                                "scope", fix="bind each number to a result field", words=[p[3] for p in loose[:8]]))
    keys = {str(m.get("key") or "") for m in body.get("measurements") or [] if isinstance(m, dict)}
    named = [k for k in sorted(keys) if ("_" in k or any(ch.isdigit() for ch in k)) and len(k) >= 4
             and re.search(rf"(?<![\w`]){re.escape(k)}(?![\w`])", stmt)
             and not re.search(rf"(?<![\w`]){re.escape(k)}\s*(?:=|:|≈|is|was|of|at)\s*[-+−]?\d", stmt)]   # key = value
    if named:
        problems.append(Problem("KEY_FOR_NUMBER", "the statement names a measurement's key instead of saying its value: "
                                + ", ".join(named[:6]) + " — write the number in the sentence; it's bound to that key, "
                                "so the record checks it", fix="replace each key with its number", words=named[:6]))
    problems += _absolutes(clean, scope, body, bound)
    if kind not in ("lead", "convention"):
        problems += _comparisons(s, clean, bound, support)
        problems += _causal(s, clean, support)
    problems += _exclusion(s, clean, kind, support, bound)
    if kind == "finding":
        problems += _uncorrected(s, clean, bound, inv)
    return problems


def claim_problems(s: Snap, body: dict, support: list[str], inv: str) -> list[str]:
    """The problems as text lines (see claim_issues for the structured form)."""
    return [p.text() for p in claim_issues(s, body, support, inv)]

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
  COUNT_CONTRADICTS             the absolute is contradicted by a bound count of what it's about: k of n with
                                0 < k < n, the exceptions it says don't exist were counted. Not a missing count
                                (ABSOLUTE_WITHOUT_COUNT) but a false statement, and the refusal log tracks whether
                                its author then corrects it or says it again (refusals.conduct)
  ABSOLUTE_UNRELATED_COUNT      the 0-of-n it leans on counts something else
  ABSOLUTE_UNDERPOWERED         0 of n with n too small (the rate could still be above 5%), and the statement
                                generalises past the n trials instead of saying them ("never leaks")
  ABSOLUTE_HIDES_DENOMINATOR    0 of n is enough, but neither statement nor scope says n — "never" reads as never
  COMPARATIVE_WITHOUT_COMPARISON "beats" / "outperforms" / "higher than" with fewer than two sides measured
  SIGNIFICANCE_WITHOUT_TEST     "significantly" with no test behind it
  SIGNIFICANCE_NOT_SHOWN        the test behind it isn't significant
  SIGNIFICANCE_CONTRADICTED     "not significant", but the bound evidence is (p < 0.05)
  CAUSAL_WITHOUT_INTERVENTION   "causes" / "leads to" when no experiment intervened
  SOURCE_CONTRADICTS            the statement denies a word ("…in pounds, not kilograms") that a source it links
                                as support asserts, in a sentence with no negation of its own ("every weight is
                                in kilograms"): the source says the opposite, so it can't be a line of support.
                                (Before this, a claim citing its own refutation was accepted with "3 independent
                                lines of support".)
  EXCLUSION_WITHOUT_POWER       "no effect" / "rules out" without a search shown to find a planted effect
  CONVENTION_HEDGED             a convention that hedges
  VALUE_NOT_A_NUMBER            (results) a value's k or n is not a number: {"k": "40/50", "n": "rank 1 of 20"}
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
        plain += _nums(m) + _nums(rv) + [f for f in (stated_figure(rv),) if f is not None]
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


def _bound(s: Snap, meas: list, stmt: str = "") -> tuple[list[tuple[dict, dict]], list[Problem]]:
    """Measurements that check out against their results, and problems with the rest. With ``stmt``, the claim's
    statement: what a key says it counted must be said by the measurement's name or by the statement."""
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
        for k in ("value", "k", "n", "figure"):
            if k in m and k in rv and isinstance(m[k], (int, float)) and isinstance(rv[k], (int, float)):
                dec = len(str(m[k]).split(".")[1]) if "." in str(m[k]) else 0
                if round(float(rv[k]), dec) != round(float(m[k]), dec) and not (
                        rv[k] <= 1 < m[k] and round(float(rv[k]) * 100, dec) == round(float(m[k]), dec)):
                    problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name') or i + 1}: says "
                                            f"{k}={m[k]} but result {m['result']} has {rv[k]}"))
                    bad = True
        said, f = _named_figure(str(m.get("name") or "")), stated_figure(rv)
        if not bad and said and f is not None and said[0] != f:
            problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name')}: its name says "
                                    f"{said[1]}, but result {m['result']} counted '{m['key']}' against "
                                    f"{_fmt(f)}", fix=f"name the count after {_fmt(f)}, the figure it was made against"))
            bad = True
        op, named = stated_op(rv), _directions(str(m.get("name") or ""))
        if not bad and _OPS.get(op) and any(_opposed(d, ("", _OPS[op][0])) for d in named):
            problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name')}: its name points the other "
                                    f"way from what result {m['result']} counted for '{m['key']}' ({op})",
                                    fix=f"name the count after the comparison it made ({op})"))
            bad = True
        # "longer than 26" leaves 26 out, "at least 26" and "26 or longer" take it in: a name that says the other
        # boundary from the one counted says a different count (audit HG-024-04)
        if not bad and _OPS.get(op) and any(c and not _opposed(c, ("", _OPS[op][0])) and c[2] != _OPS[op][1]
                                            for _f, c in _clause_comparisons(str(m.get("name") or ""))):
            problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name')}: its name "
                                    f"{'leaves out' if _OPS[op][1] else 'takes in'} the figure itself, but result "
                                    f"{m['result']} counted '{m['key']}' with {op}",
                                    fix=f"name the count after the comparison it made ({op})"))
            bad = True
        # the key is the result's own name for what it counted, written by whoever ran it; the measurement's name is
        # the claimant's. A name may shorten the key, not change it: "routes longer than 26 km" isn't a count of
        # route_speed_above_26, nor of routes_faster_than_26 (audit HG-025-02)
        key = str(m["key"]).replace("_", " ")
        named_axes = {c[0] for c in _comparisons_in(str(m.get("name") or "")) if c[0]}
        key_axes = {c[0] for c in _comparisons_in(key) if c[0]}
        if not bad and named_axes and key_axes and not named_axes & key_axes:
            problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name')}: its name compares "
                                    f"{_axis_words(named_axes)}, but result {m['result']} counted '{m['key']}', which "
                                    f"compares {_axis_words(key_axes)}",
                                    fix="name the count after what it compared, or bind the count that compared that"))
            bad = True
        # a name that says no comparison ("fitting selections") doesn't say another count; one that does must keep
        # what the key counted, here or in the statement
        unsaid = _unsaid(_subject_of(key), f"{m.get('name') or ''} . {_clauses_at(stmt, _count_figures(m, rv))}")
        if not bad and unsaid and _comparisons_in(str(m.get("name") or "")):
            problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name')}: result {m['result']} "
                                    f"counted '{m['key']}', and neither the name nor the statement says what it "
                                    f"counted ({', '.join(sorted(_key_words(key, unsaid)))})",
                                    fix="name the count after what it counted, or bind the count of what the claim "
                                        "is about"))
            bad = True
        if not bad:
            good.append((m, rv))
    return good, problems


# where one thing said ends and another begins: a sentence, a semicolon or colon, or a comma before a conjunction
_SAYING = re.compile(r"[;:!?]|\.(?!\d)|,\s*(?=(?:and|but|while|whereas|although|though|so|yet)\b)|"
                     r"\b(?:although|though|whereas)\b", re.I)


def _clauses_at(stmt: str, figs: set[float]) -> str:
    """The parts of ``stmt`` that state one of ``figs``: what a count against that figure must be about is said there,
    not in another sentence. "Speed was recorded separately; no route is longer than 26 km" says nothing about speed
    where it says 26 km, so a speed count named "routes longer than 26 km" can't borrow the word (audit HG-026-01).
    The whole statement when no part states one."""
    if not stmt or not figs:
        return stmt
    parts = [p for p in _SAYING.split(stmt) if p and p.strip()]
    hit = [_from_claim(p) for p in parts if {round(v[0], 6) for v in numbers(p)} & {round(f, 6) for f in figs}]
    return " . ".join(hit) if hit else stmt


def _from_claim(part: str) -> str:
    """A part from the comma before its absolute or extreme: "Rural sites aside, no urban clinic had waits above 45"
    claims only "no urban clinic had waits above 45"."""
    hit = L.ABSOLUTE.search(part) or L.SUPERLATIVE.search(part)
    if not hit:
        return part
    return part[max((x.end() for x in re.finditer(r",(?!\d)", part[:hit.start()])), default=0):]


def _axis_words(axes: set[str]) -> str:
    return " / ".join(sorted("/".join(w for w, (a, _s) in _DIRECTION_OF.items() if a == x and not w.endswith("est"))
                             for x in axes))


def _key_words(key: str, stems: set[str]) -> set[str]:
    """The words of ``key`` whose stems are ``stems``, as written."""
    return {w for w in re.findall(r"[a-z]+", key.lower()) if L.content_words(w) & stems} or stems


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


# the figure a count is about: "fitting selections worth more than 93", "routes shorter than 26 km" (or, matching a
# figure the claim names, "worth_more_93"). A count of nothing beyond 140 says nothing about 93 (audit HG-020-01/02).
_COUNT_FIGURE = re.compile(r"\b(?:(?:" + L.CMP_WORDS + r"|(?!(?:" + L.NOT_CMP + r")\b)[a-z]{3,}er)\s+than|above|below|over|under|beyond|exceed\w*|beat\w*)\s+\$?"
                           r"(-?\d[\d,]*(?:\.\d+)?)", re.I)
# the figure a name gives before its comparison or with "at least": "routes 26 km or longer", "routes at least 26 km"
_COUNT_FIGURE_BOUNDARY = re.compile(r"\bat\s+(?:least|most)\s+\$?(-?\d[\d,]*(?:\.\d+)?)|\$?(-?\d[\d,]*(?:\.\d+)?)"
                                    r"(?:\s+[a-z%]+){0,2}\s+or\s+(?:" + L.CMP_WORDS + r")\b", re.I)


def _named_figure(name: str) -> tuple[float, str] | None:
    """The figure a count's name says it is about, and the words that say it."""
    hit = _COUNT_FIGURE.search(name or "")
    if hit:
        return float(hit.group(1).replace(",", "")), hit.group(0).strip()
    hit = _COUNT_FIGURE_BOUNDARY.search(name or "")
    if hit:
        return float((hit.group(1) or hit.group(2)).replace(",", "")), hit.group(0).strip()
    return None


_KEY_FIGURE = re.compile(r"\b(?:" + L.CMP_WORDS + r"|above|below|over|under|beyond|exceed\w*|beat\w*)(?:\s+than)?\s+"
                         r"(\d+(?:\.\d+)?)$", re.I)
# the figure an absolute names in its own clause: "nothing worth more than 93 fits", "no route is shorter than 26 km"
_CLAIM_FIGURE = re.compile(r"\b(?:" + L.CMP_WORDS + r"|(?!(?:" + L.NOT_CMP + r")\b)[a-z]{3,}er)\s+than\s+\$?(-?\d[\d,]*(?:\.\d+)?)|\b(?:above|below|beyond|"
                           r"exceed(?:s|ing)?)\s+\$?(-?\d[\d,]*(?:\.\d+)?)", re.I)
_CLAIM_BOUNDARY = re.compile(r"\bat\s+(?:least|most)\s+\$?(-?\d[\d,]*(?:\.\d+)?)|\$?(-?\d[\d,]*(?:\.\d+)?)"
                             r"(?:\s+[a-z%]+){0,2}\s+or\s+(?:" + L.CMP_WORDS + r")\b", re.I)
_SUBCLAUSE = re.compile(r",(?!\d)|[;:!?()]|\.(?!\d)|\b(?:and|but|while|whereas|although|so)\b", re.I)


def stated_figure(rv: dict) -> float | None:
    """The figure a count says it is about, written by the instrument beside it: {"k": 2, "n": 1024, "figure": 93} is
    two found beyond 93."""
    f = rv.get("figure")
    return float(f) if isinstance(f, (int, float)) and not isinstance(f, bool) else None


def _count_figures(m: dict, rv: dict, figs: set[float] = frozenset()) -> set[float]:
    """Every figure a bound count could be about; empty when nothing says. A figure the result states is the only one:
    the instrument wrote it with the count. Otherwise the name's figure ("more than 93") and the key's: a key is an
    identifier, and the number at its end may only tell repeated counts apart ("fitting_selections_worth_more_2" is
    the second count, not one beyond 2), so it is read only when the claim names it or the name names another. The
    author writes the name, so a name that disagrees with the key adds a figure and never replaces one: renaming the
    count beyond 93 "worth more than 140" no longer moves it off "the highest is 93" (audit HG-021-01)."""
    f = stated_figure(rv)
    if f is not None:
        return {f}
    out: set[float] = set()
    named = _named_figure(str(m.get("name") or ""))
    if named:
        out.add(named[0])
    hit = _KEY_FIGURE.search(str(m.get("key") or "").replace("_", " "))
    if hit and (float(hit.group(1)) in figs or out):
        out.add(float(hit.group(1)))
    return out


# which way a comparison points, as (axis, sign): "longer" and "longest" point up the length axis, "shorter" and
# "shortest" down it; "more", "above", "highest" point up with no axis of their own, so they meet any axis. A count of
# routes longer than 26 km says nothing against "the shortest is 26 km" (audit HG-022-01), and none shorter than 26
# doesn't back "nothing is longer than 26" (HG-022-02).
_DIRECTION_WORDS = {
    "": {1: "more greater higher larger bigger above over exceed exceeds exceeding exceeded most highest largest "
            "greatest biggest maximum max top",
         -1: "less fewer lower smaller below under least lowest smallest fewest minimum min"},
    "long": {1: "longer longest", -1: "shorter shortest"},
    "good": {1: "better best", -1: "worse worst"},
    "fast": {1: "faster fastest", -1: "slower slowest"},
    "cost": {1: "dearer dearest", -1: "cheaper cheapest"},
    "time": {1: "later latest", -1: "earlier earliest"},
    "heavy": {1: "heavier heaviest", -1: "lighter lightest"},
    "warm": {1: "warmer warmest hotter hottest", -1: "colder coldest cooler coolest"},
    "old": {1: "older oldest", -1: "younger youngest newer newest"},
    "tall": {1: "taller tallest"},
    "wide": {1: "wider widest", -1: "narrower narrowest"},
    "deep": {1: "deeper deepest", -1: "shallower shallowest"},
    "loud": {1: "louder loudest", -1: "quieter quietest"},
    "strong": {1: "stronger strongest", -1: "weaker weakest"},
}
_DIRECTION_OF = {w: (axis, sign) for axis, signs in _DIRECTION_WORDS.items() for sign, ws in signs.items()
                 for w in ws.split()}
# a comparison is (axis, sign, strict): "longer than 26" is (long, +1, strict), "at least 26" and "26 or longer" are
# not strict, so a route of exactly 26 lies inside them and outside "longer than" (audit HG-023-02). Six operators;
# "=" and "!=" point nowhere.
_OPS = {">": (1, True), ">=": (1, False), "<": (-1, True), "<=": (-1, False), "=": None, "!=": None}
_CMP = r"(" + L.CMP_WORDS + r")"
_NOT_STRICT = re.compile(r"\bat\s+(least|most)\b|\b(?:not|no)\s+" + _CMP + r"\s+than\b|\bor\s+" + _CMP + r"\b", re.I)


def _comparisons_in(text: str) -> set[tuple[str, int, bool]]:
    """Every comparison ``text`` makes, with its boundary: "at least", "at most", "not / no shorter than", "or
    longer" include the figure; any other comparison word excludes it."""
    text = (text or "").lower()
    out = set()
    for h in _NOT_STRICT.finditer(text):
        if h.group(1):
            out.add(("", 1 if h.group(1) == "least" else -1, False))
        elif h.group(2):
            axis, sign = _DIRECTION_OF[h.group(2)]
            out.add((axis, -sign, False))
        else:
            out.add((*_DIRECTION_OF[h.group(3)], False))
    rest = _NOT_STRICT.sub(" ", text)
    # a comparative the checks don't know ("brighter than") is an axis of its own: only a count that says the same word
    # meets it, so nothing else can back a claim made with it (audit HG-026-01)
    unknown = {(w, 1, True) for w in _UNKNOWN_CMP.findall(rest) if w not in _DIRECTION_OF}
    return out | unknown | {(*_DIRECTION_OF[w], True) for w in re.findall(r"[a-z]+", rest) if w in _DIRECTION_OF}


_UNKNOWN_CMP = re.compile(r"\b(?!(?:" + L.NOT_CMP + r")\b)([a-z]{3,}er)\s+than\b")


def _directions(text: str) -> set[tuple[str, int]]:
    return {(axis, sign) for axis, sign, _strict in _comparisons_in(text)}


def _opposed(a: tuple, b: tuple) -> bool:
    """Do these point opposite ways on one axis? An axis-free word ("more") meets any axis; two different axes
    ("longer", "faster") can't be compared, so they aren't opposed."""
    return a[1] != b[1] and (a[0] == b[0] or not a[0] or not b[0])


def _within(inner: tuple, outer: tuple) -> bool:
    """Does every value ``inner`` takes lie in ``outer``? Same way on one axis, and the boundary inside ``outer`` if it
    is inside ``inner``: "longer than 26" lies within "at least 26", not the other way round."""
    return inner[1] == outer[1] and (inner[0] == outer[0] or not inner[0] or not outer[0]) and (
        inner[2] or not outer[2])


def _negated(c: tuple) -> tuple:
    """What lies outside a comparison: outside "longer than 26" is "26 or shorter"."""
    return c[0], -c[1], not c[2]


def stated_op(rv: dict) -> str | None:
    """The comparison a count says it made, written by the instrument beside it: {"k": 2, "n": 3, "figure": 26,
    "op": ">"} is two found above 26. One of < <= = != >= >."""
    op = rv.get("op")
    return op if isinstance(op, str) and op in _OPS else None


def _count_comparisons(m: dict, rv: dict) -> set[tuple[str, int, bool]] | None:
    """Every comparison a bound count could have made; empty when nothing says, None when it says it compared for
    (in)equality. A comparison the result states is the only one. Otherwise its name's and its key's: as with its
    figure, the author writes the name, so a name that disagrees with the key adds a comparison, never replaces one."""
    op = stated_op(rv)
    if op:
        return {("", *_OPS[op])} if _OPS[op] else None
    return _comparisons_in(str(m.get("name") or "")) | _comparisons_in(str(m.get("key") or "").replace("_", " "))


def _count_directions(m: dict, rv: dict) -> set[tuple[str, int]]:
    return {(axis, sign) for axis, sign, _strict in _count_comparisons(m, rv) or ()}


# absolutes that say everything is so; the rest ("never", "nothing", "no route", "zero") say nothing is
_ALL = re.compile(r"^(?:always|all|every|universally|invariably|consistently|without exception|100\s*%)$", re.I)


def _clause_comparisons(clause: str) -> list[tuple[float, tuple[str, int, bool] | None]]:
    """(figure, comparison) for each comparison against a figure in a claim's clause: "longer than 26 km", "at least
    26", "26 km or longer", "no more than 93", "above 93"; None for one that points nowhere ("beyond 93")."""
    out = []
    for h in _CLAIM_FIGURE.finditer(clause):
        neg = re.search(r"\b(?:not|no)\s+$", clause[:h.start()], re.I)      # "no more than 93" is at most 93
        num = (h.group(1) or h.group(2)).replace(",", "")
        out += [(float(num), c) for c in _comparisons_in(clause[neg.start() if neg else h.start():h.end()]) or {None}]
    for h in _CLAIM_BOUNDARY.finditer(clause):
        num = (h.group(1) or h.group(2)).replace(",", "")
        out += [(float(num), c) for c in _comparisons_in(h.group(0)) or {None}]
    return out


# a target group whose parts are joined by both "and" and "or" (``_target_groups``)
MIXED = (frozenset(), frozenset({("mixed", 0, False)}))

# "and" or "or" before a comparison with no subject of its own: "shorter than 20 km and longer than 30 km"
_JOINED = re.compile(r"\s+(?:also\s+)?(?:(?:not|no)\s+)?(?:" + _CMP + r"\s+than\b|at\s+(?:least|most)\b|above\b|below\b|"
                     r"beyond\b|exceed)", re.I)


def _clause_end(stmt: str, start: int) -> int:
    """Where the clause that starts at ``start`` ends. An "and" that joins a second comparison to the first ("no route
    is shorter than 20 km and longer than 30 km") doesn't end it: the two say one thing (audit HG-024-03)."""
    for x in _SUBCLAUSE.finditer(stmt, start):
        if not (x.group(0).lower() == "and" and _JOINED.match(stmt, x.end())):
            return x.start()
    return len(stmt)


def _target_groups(stmt: str, w: str) -> list[list[tuple[frozenset, frozenset]]]:
    """What an absolute rules out, as (figures, comparisons of the exceptions), one per thing it is about. A comparison
    in its own clause: "nothing longer than 26 km" rules out longer than 26, and "every route is longer than 26 km"
    rules out 26 or shorter (audit HG-023-01). Not "every" in a clause that states its own count ("a count of every
    route finds 1 of 76 shorter than 25 km"): that names the set counted, not a claim about all of it. Else each
    extreme the statement claims, on its own (HG-023-03).

    Each group is ruled out together. Two comparisons joined in one clause are two groups where either exception
    falsifies the claim ("no route is shorter than 20 km or longer than 30 km"; "every route is longer than 10 km and
    shorter than 30 km"), and one group where only an exception to both does ("no route is shorter than 20 km and
    longer than 30 km" rules out a route that is both; "every route is shorter than 20 km or longer than 30 km" one that
    is neither) (audit HG-024-03).

    A clause that joins comparisons with both "and" and "or" ("every route is longer than 10 km and shorter than 30 km
    or shorter than 6 km") is one group marked ``MIXED``: which parts go together depends on a grouping the words don't
    settle, so no count of a part backs or refutes it (audit HG-025-03)."""
    out: list[list[tuple[frozenset, frozenset]]] = []
    every = bool(_ALL.match(w)) and not _names_stated_count(stmt, w)
    for m in re.finditer(r"\b" + re.escape(w) + r"\b", stmt, re.I):
        clause = stmt[m.end():_clause_end(stmt, m.end())]
        targets = [(frozenset({fig}), frozenset() if c is None else frozenset({_negated(c) if every else c}))
                   for fig, c in _clause_comparisons(clause)]
        ands = any(_JOINED.match(clause, x.end()) for x in re.finditer(r"\band\b", clause, re.I))
        ors = any(_JOINED.match(clause, x.end()) for x in re.finditer(r"\bor\b", clause, re.I))
        if len(targets) > 1 and ands and ors:
            out.append([MIXED, *targets])
        elif len(targets) > 1 and ands != ors and (ands != every):
            out.append(targets)
        else:
            out += [[x] for x in targets]
    return out or [[x] for x in _extreme_targets(stmt) or [(frozenset(), frozenset())]]


def _absolute_targets(stmt: str, w: str) -> list[tuple[frozenset, frozenset]]:
    """Every thing an absolute rules out, each on its own (``_target_groups`` says which go together)."""
    return [x for group in _target_groups(stmt, w) for x in group if x is not MIXED]


def _claim_directions(stmt: str, w: str = "") -> set[tuple[str, int]]:
    """Which way the exceptions to a claim point."""
    targets = _absolute_targets(stmt, w) if w else _extreme_targets(stmt)
    return {(axis, sign) for _f, comps in targets for axis, sign, _strict in comps}


def _role(m: dict, rv: dict, a: tuple[int, int], figs: set[float], comps: set, stmt: str = "") -> str | None:
    """What a bound count does to a claim that rules out ``comps`` at ``figs``: 'back' it (none of the exceptions
    found), 'refute' it (some found), or nothing. A count of what lies outside the exceptions is read as its
    complement: none of 3 routes longer than 26 is 3 of 3 at 26 or shorter. A count backs only if what it counted
    covers the exceptions, and refutes only if every one it found is one: two routes at least 26 km don't refute "no
    route is longer than 26", nor does none longer than 26 back "no route is 26 or longer" (audit HG-023-02). Where the
    name and key could say different comparisons, a label can widen what a count refutes, never what it backs. A count
    that says no comparison doesn't bear on a claim that rules one out: 3 of 3 routes processed says nothing about
    routes longer than 26 km (audit HG-024-01). A claim whose comparison can't be told is read as before: none or all
    backs, some refutes. With ``stmt``, the count must also be about what the claim is (``_subject_fit``)."""
    k, n = a
    cs = _count_comparisons(m, rv)
    if comps and not cs:
        return None
    if not comps:
        role = "back" if k in (0, n) else "refute"
    else:
        roles = set()
        for d in cs:
            for e in comps:
                dd, kk = (d, k) if not _opposed(d, e) else (_negated(d), n - k)
                if dd[1] != e[1] or not (dd[0] == e[0] or not dd[0] or not e[0]):
                    roles.add(None)
                elif kk == 0 and _within(e, dd):
                    roles.add("back")
                elif kk > 0 and _within(dd, e):
                    roles.add("refute")
                else:
                    roles.add(None)
        role = "refute" if "refute" in roles else "back" if roles == {"back"} else None
    if role is None:
        return None
    c = _count_figures(m, rv, figs)
    if c and figs and not (c & figs if role == "refute" else c <= figs):
        return None
    if stmt:
        covers, apart = _subject_fit(stmt, m)
        if (role == "back" and not covers) or (role == "refute" and apart):
            return None
    return role


# words a count's name may use for the counting itself, not for what it counts
_COUNTING = set("count counts counted counting number numbers total totals tally share fraction rate found measured "
                "checked matching".split())
# and words that say how many, not which kind: "nothing worth more", "every route"
_HOW_MANY = set("nothing none never nobody every always ever each whole entire".split())


# three-letter words that say nothing about what was counted
_SHORT_SKIP = set("has had did got get let may can one two six ten few new old top max min own via nor yet per".split())


def _stems(text: str) -> set[str]:
    """``L.content_words`` and the three-letter words it leaves out, which can name what was counted: a count of
    "bridge age above 60" is of ages, and "age" must be said for it to back a claim (audit HG-026-01)."""
    return L.content_words(text) | {w for w in re.findall(r"[a-z]+", (text or "").lower())
                                    if len(w) == 3 and w not in L.STOP and w not in _SHORT_SKIP}


def _modifiers(words: list[str], i: int) -> set[str]:
    """The content words right before ``words[i]``, up to a determiner, number, preposition or comparison: "no passenger
    route" gives {passeng}, "the 3 cargo routes" {cargo}, "the shortest route" nothing."""
    out: set[str] = set()
    for w in reversed(words[:i]):
        cw = _stems(w)
        if not cw or w in _DETERMINERS or w in _PREPOSITIONS or w in _DIRECTION_OF or w in _COUNTING | _HOW_MANY:
            break
        out |= cw
    return out


def _subject_of(text: str) -> set[str]:
    """What a count against a figure is of: the content words right before its first comparison ("cargo route longer
    than 26 km" and "cargo_routes_longer_26" give {cargo, route}; "speed above 26" {speed}); empty when it makes no
    comparison or names nothing before it. Singular or plural alike (audit HG-025-01)."""
    words = [w for w in re.findall(r"[a-z]+|\d[\d.,]*", text.lower().replace("_", " ")) if w not in _COPULAS]
    i = next((j for j, w in enumerate(words) if w in _DIRECTION_OF or w == "at" and words[j + 1:j + 2] in
              (["least"], ["most"])), None)
    return _modifiers(words, i) if i else set()


def _subject_parts(text: str) -> tuple[set[str], set[str]]:
    """``_subject_of`` split into its head, the word right before the comparison, and the words before that: "cargo
    route longer" gives ({route}, {cargo}), "fitting selections worth more" ({selection}, {fit})."""
    words = [w for w in re.findall(r"[a-z]+|\d[\d.,]*", text.lower().replace("_", " ")) if w not in _COPULAS]
    i = next((j for j, w in enumerate(words) if w in _DIRECTION_OF or w == "at" and words[j + 1:j + 2] in
              (["least"], ["most"])), None)
    if not i:
        return set(), set()
    whole = _modifiers(words, i)
    while i > 1 and words[i - 1] in _MEASURED_BY:      # "selections worth more": the head is selections
        whole -= L.content_words(words[i - 1])
        i -= 1
    head = _stems(words[i - 1]) & whole
    return head, whole - head


# words between what a count is of and its comparison that say what was compared, not which thing
_MEASURED_BY = set("worth valued priced weighing costing lasting taking".split())


_COPULAS = set("is are was were be been being".split())
# the property a comparison word compares: a count of "route length above 26" is said by "no route is longer than 26"
_PROPERTY_AXIS = {s: axis for axis, ws in {"long": "length distance span", "fast": "speed velocity pace",
                                           "cost": "cost price", "time": "date time", "heavy": "weight mass",
                                           "warm": "temperature heat", "old": "age", "tall": "height",
                                           "wide": "width breadth", "deep": "depth", "loud": "loudness",
                                           "strong": "strength"}.items()
                  for w in ws.split() for s in _stems(w)}


def _unsaid(stems: set[str], text: str) -> set[str]:
    """``stems`` that ``text`` doesn't say: neither as words nor, for a property, by comparing along its axis."""
    axes = {c[0] for c in _comparisons_in(text) if c[0]}
    return {s for s in stems - _stems(text) if _PROPERTY_AXIS.get(s) not in axes}


def _subjects_at(stmt: str, axes: set[str]) -> set[str]:
    """What a statement's comparisons along ``axes`` are about: "no passenger route is longer than 26 km" gives
    {passenger, route} for length; "nothing worth more" nothing. A bound ("the limit is at most 49 kg") is not one."""
    words = [w for w in re.findall(r"[a-z]+|\d[\d.,]*", stmt.lower()) if w not in _COPULAS | _MEASURED_BY]
    return set().union(*(_modifiers(words, j) for j, w in enumerate(words) if w in _DIRECTION_OF
                         and _DIRECTION_OF[w][0] in axes and words[j - 1:j] != ["at"]))


def _kinds_named(stmt: str) -> set[str]:
    """The kinds a statement names for what it is about: the words before its comparison ("no passenger route is
    longer" gives {passenger, route}) and before a plural in a phrase that says what it ranges over ("among the 3
    passenger routes" gives {passenger}; "the recorded weights" and "the limit applies" name nothing it ranges over)."""
    said = re.findall(r"[a-z]+|\d[\d.,]*", stmt.lower())
    out = _subject_of(stmt)
    for i, w in enumerate(said):
        if not (w.endswith("s") and not w.endswith("ss") and L.content_words(w)):
            continue
        mods = _modifiers(said, i)
        j = i - 1
        while j >= 0 and L.content_words(said[j]) & mods:
            j -= 1
        while j >= 0 and (said[j] in _DETERMINERS or said[j][0].isdigit()):
            j -= 1
        if j >= 0 and said[j] in _PREPOSITIONS:
            out |= mods
    return out


def _subject_fit(stmt: str, m: dict) -> tuple[bool, bool]:
    """Is a count about what a claim is about? Returns (covers, apart). A count names what it counts in the plural
    ("cargo routes", "fitting selections"); where the statement uses that word too, the words right before it on each
    side say which kind: "cargo routes" are cargo routes. The count covers the claim if every kind it names is one the
    statement names too: none of 3 cargo routes longer than 26 km says nothing of passenger routes, nor of every route
    (audit HG-024-02). They are apart if each names a kind the other doesn't (cargo, passenger); a count of all routes
    with one longer may still be about the passenger route. A count that names nothing the statement does is read as
    before.

    The same holds for what a count names before its comparison, singular or plural: "cargo route longer than 26 km"
    and "cargo longer than 26 km" are of cargo routes, and back no claim about passenger routes (audit HG-025-01). A
    count whose subject the statement doesn't name at all ("speed above 26" against a claim about length) neither backs
    nor refutes it."""
    said = re.findall(r"[a-z]+", stmt.lower())
    stems = [L.content_words(w) for w in said]
    about = set().union(*stems) if stems else set()
    text = f"{m.get('name') or ''} . {str(m.get('key') or '').replace('_', ' ')}".lower()
    words = re.findall(r"[a-z]+|\.", text)
    mine = L.content_words(text)
    covers, apart = True, False
    for i, w in enumerate(words):
        head = L.content_words(w)
        plural = w.endswith("s") and not w.endswith("ss")
        if not head or not plural or w in _DIRECTION_OF or w in _COUNTING | _HOW_MANY or not head & about:
            continue
        kinds = _modifiers(words, i) - about
        theirs = set().union(*(_modifiers(said, j) for j, s in enumerate(stems) if s & head)) - mine
        covers = covers and not kinds
        apart = apart or bool(kinds and theirs)
    parts = [_subject_parts(str(m.get(f) or "")) for f in ("name", "key")]
    head, mods = parts[0][0] | parts[1][0], parts[0][1] | parts[1][1]
    if head:
        subject = head | mods
        if not _unsaid(head, stmt):      # the statement says the count's head: its other words must be said too
            kinds = _unsaid(mods, stmt)
            theirs = set().union(*(_modifiers(said, j) for j, s in enumerate(stems) if s & head)) - subject
            apart = apart or bool(kinds and theirs)
        else:                            # a head the statement doesn't say only matters where it names a kind itself
            named = _kinds_named(stmt)
            kinds = _unsaid(subject, stmt) if named else set()
            axes = {c[0] for f in ("name", "key") for c in _comparisons_in(str(m.get(f) or "").replace("_", " "))}
            theirs = _subjects_at(stmt, axes)
            apart = apart or bool(theirs and not theirs & subject)
        covers = covers and not kinds
    return covers, apart


def _pinned(m: dict, rv: dict, figs: set[float]) -> bool:
    """A count at the claim's own figure: when it refutes the claim, it does whatever else is bound beside it."""
    return bool(figs) and bool(_count_figures(m, rv, figs) & figs)


def _absolutes(stmt: str, scope: str, body: dict, bound: list) -> list[Problem]:
    """Every absolute in the statement, and every extreme, checked on its own: a true "nothing worth more than 140
    fits" used to end the check, and "the highest is 93" beside it went in unexamined (audit HG-021-02)."""
    words = [w for w in L.asserted(L.ABSOLUTE, stmt) if not _enumerated(stmt, w)]
    if any(str(m.get("key") or "").lower() in ("gap", "bound") for m, _rv in bound):
        words = [w for w in words if not _PROVEN.match(w)]      # an optimum with its bound (gap 0) is proven
    words = [w for w in words if not _names_counted_set(stmt, w, bound)]
    out: list[Problem] = []
    seen: set[tuple] = set()
    for w in words:                                  # one check per thing the absolutes rule out
        for group in _target_groups(stmt, w):
            if (tuple(group), _ALL.match(w) is None) in seen:
                continue
            seen.add((tuple(group), _ALL.match(w) is None))
            if group[0] is MIXED:
                p = Problem("ABSOLUTE_WITHOUT_COUNT", f"'{w}' rules on comparisons joined by both 'and' and 'or': "
                            "counts of each comparison on its own can't settle that either way, and no count can be "
                            "tied to the whole condition. Split it into claims that each join their comparisons one "
                            "way (audit HG-026-02)",
                            fix="split the claim into clauses that each join their comparisons one way", words=words)
                if p.text() not in {q.text() for q in out}:
                    out.append(p)
                continue
            got = [_absolute(stmt, scope, body, bound, w, words, set(figs), set(comps)) for figs, comps in group]
            if len(group) > 1:                       # ruled out together: none of one part means none of both
                if any(not g for g in got):
                    continue
                got = [g for g in got if not any(p.code == "COUNT_CONTRADICTS" for p in g)][:1] or [[Problem(
                    "ABSOLUTE_WITHOUT_COUNT", f"'{w}' rules out what meets both comparisons at once: a count of each "
                    "on its own can't show that something meets both. Back it with a count of either one where k is "
                    "0, or count both together", fix="count what meets both comparisons together", words=words)]]
            out += [p for g in got for p in g if p.text() not in {q.text() for q in out}]
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _superlative_contradicted(stmt, bound)
    return out


def _absolute(stmt: str, scope: str, body: dict, bound: list, w: str, words: list, figs: set[float],
              comps: set = frozenset()) -> list[Problem]:
    arms = [(m, rv, a, role) for m, rv in bound if (a := _arm(rv)) and (role := _role(m, rv, a, figs, comps, stmt))]
    about = L.content_words(stmt)
    # a count at the claim's own figure that finds exceptions refutes it, whatever else is bound beside it
    pinned = [(m, a) for m, rv, a, role in arms if role == "refute" and _pinned(m, rv, figs)
              and L.content_words(f"{m.get('name', '')} {m.get('key', '')}") & about]
    if pinned:
        m, (k, n) = max(pinned, key=lambda x: x[1][1])
        return [_count_contradicts(stmt, w, words, m, k, n)]
    exact = [(m, rv, a) for m, rv, a, role in arms if role == "back"]
    if not exact:
        against = [(m, a) for m, _rv, a, role in arms if role == "refute"
                   and L.content_words(f"{m.get('name', '')} {m.get('key', '')}") & about]
        if against:
            m, (k, n) = max(against, key=lambda x: x[1][1])
            return [_count_contradicts(stmt, w, words, m, k, n)]
        seen = ", ".join(f"{a[0]} of {a[1]:,}" for _m, _rv, a, _role in arms)
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


_STATED_COUNT = re.compile(r"\b(\d[\d,]*) of (\d[\d,]*)\b")
_CLAUSE = re.compile(r"[;!?]|\.(?!\d)")


def _names_counted_set(stmt: str, w: str, bound: list) -> bool:
    """Is the absolute the set a count the statement itself reports ran over: "a count of every possible selection
    finds 2 of 1,024 that are worth more"? It names what was counted, not a claim that nothing lies outside it. (Read
    as an absolute, the record refused that honest correction as the lie said again.)"""
    return _names_stated_count(stmt, w, {a for _m, rv in bound if (a := _arm(rv))})


def _names_stated_count(stmt: str, w: str, counts: set | None = None) -> bool:
    """Does ``w``'s clause state a k-of-n count (one of ``counts``, when given)?"""
    for c in _CLAUSE.split(stmt):
        if re.search(r"\b" + re.escape(w) + r"\b", c, re.I) and any(
                counts is None or (int(a.replace(",", "")), int(b.replace(",", ""))) in counts
                for a, b in _STATED_COUNT.findall(c)):
            return True
    return False


def claimed_extremes(stmt: str) -> list[str]:
    """What a sentence claims as an extreme: its asserted superlatives (``_extremes``) and absolutes, less an absolute
    that names the set a count in its own clause ran over ("a count of every route finds 1 of 74 shorter"). The refusal
    log reads a later write with this to tell a correction from the lie said again."""
    return _extremes(stmt) + [w for w in L.asserted(L.ABSOLUTE, stmt)
                              if not _enumerated(stmt, w) and not _names_stated_count(stmt, w)]


# the extreme's own predicate denied after it, in its clause: "the highest total value ... is not 130"
_DENIED_EXTREME = re.compile(r"\b(?:is|are|was|were)\s+(?:not|no longer|never)\b|\b(?:isn't|aren't|wasn't|weren't)\b|"
                             # or said to lie beyond a figure: "the true maximum is higher than 98"
                             r"\b(?:is|are|was|were|lies)\s+(?:\w+\s+)?(?:higher|lower|greater|larger|smaller|more|less|"
                             r"above|below|over|under|shorter|longer|beyond)\b", re.I)
# or denied before it: "120 is not the highest total value", "isn't the shortest"
_DENIED_BEFORE = re.compile(r"(?:\b(?:is|are|was|were)\s+(?:not|no longer|never)|\b(?:isn't|aren't|wasn't|weren't))"
                            r"\s+(?:the\s+|a\s+|an\s+)?(?:true\s+|real\s+|actual\s+)?$", re.I)
_COPULA = re.compile(r"\b(?:is|are|was|were|isn't|aren't|wasn't|weren't|lies)\b", re.I)


def _denied(after: str) -> bool:
    """Does the extreme's own predicate — the first copula after it — deny it or put it beyond a figure? Only that
    one: "the highest value is 98 ..., so the true maximum is higher" still claims 98."""
    cop = _COPULA.search(after)
    return bool(cop and _DENIED_EXTREME.match(after, cop.start()))


# a count named for what lies beyond a figure ("fitting selections worth more", "shorter routes connecting") is about
# any extreme the statement claims, whatever words the statement uses for it ("the highest total value is 99")
_BEYOND = re.compile(r"\b(?:" + L.CMP_WORDS + r"|above|below|exceed\w*|beat\w*)\b", re.I)


def _extremes(stmt: str) -> list[str]:
    """The superlatives a statement asserts of a figure. Not one whose clause goes on to deny it: "the highest total
    value that fits is not 130" corrects the extreme, it doesn't claim one. Nor one whose clause names nothing after
    it ("the shortest route must be computed from the figures as kilometres"): no count can contradict an extreme of
    nothing in particular. (The record used to refuse both as false and log corrections as the lie said again.)"""
    out = []
    for w in L.asserted(L.SUPERLATIVE, stmt):
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", stmt, re.I):
            end = next((x.start() for x in _CLAUSE.finditer(stmt, m.end())), len(stmt))
            start = max((x.end() for x in _CLAUSE.finditer(stmt, 0, m.start())), default=0)
            if (not _denied(stmt[m.end():end]) and not _DENIED_BEFORE.search(stmt[start:m.start()])
                    and re.search(r"\d", stmt[start:end])):
                out.append(w)
                break
    return out


def _count_contradicts(stmt: str, w: str, words: list, m: dict, k: int, n: int) -> Problem:
    """The refusal for a statement the record's own count shows false. It names what is false in the statement's own
    terms: a count it states that the record's differs from, or the extreme it claims ("highest"), before the word
    that triggered the check."""
    said = [int(a.replace(",", "")) for a, b in _STATED_COUNT.findall(stmt)
            if int(b.replace(",", "")) == n and int(a.replace(",", "")) != k]
    sup = _extremes(stmt)
    head = (f"the statement says {said[0]:,} of {n:,}, but the record's own count is {k:,} of {n:,}" if said
            else f"'{w if w in sup else sup[0] if sup else w}' is contradicted by the record's own count: {k:,} of {n:,}")
    return Problem("COUNT_CONTRADICTS",
                   f"{head} ({m.get('name') or m.get('key')}). The exceptions the statement rules out were "
                   f"counted, so it is false as written: correct it, or say '{k:,} of {n:,}'",
                   fix=f"correct the statement, or say '{k:,} of {n:,}'",
                   words=words + [f"={_fmt(v)}" for v in _subject_numbers(stmt, k, n)])


def _qualified(stmt: str, k: int, n: int) -> bool:
    """Does the statement give this count about a figure of its own ("1 of 61 routes are shorter than 26 km")?
    Then it's a count of something beyond that figure, not of exceptions to the extreme it claims."""
    forms = {f"{k} of {n}", f"{k:,} of {n:,}"}
    return any(any(f in c for f in forms) and re.search(r"\bthan\b", c) for c in _CLAUSE.split(stmt))


def _superlative_contradicted(stmt: str, bound: list) -> list[Problem]:
    """An extreme ("the shortest route is 34 km") with no absolute word, where the record's own count of what lies
    beyond it finds some and no count backs it: refused as false (COUNT_CONTRADICTS). Each extreme is checked on its
    own, with its own figure and direction: "the shortest is 26; the longest is 35" is two claims (audit HG-023-03)."""
    sup = _extremes(stmt)
    if not sup:
        return []
    about = L.content_words(stmt)
    for w, figs, comps in _extreme_targets(stmt, named=True):
        rel = [(m, rv, a, role) for m, rv in bound if (a := _arm(rv))
               and (role := _role(m, rv, a, set(figs), set(comps), stmt))
               and (L.content_words(f"{m.get('name', '')} {m.get('key', '')}") & about
                    or _BEYOND.search(f"{m.get('name', '')} {m.get('key', '')}".replace("_", " "))
                    or stated_figure(rv) in figs)
               and not (role == "refute" and _qualified(stmt, *a))]
        # a count beyond the extreme's own figure that finds some refutes it, whatever else is bound beside it
        pinned = [(m, a) for m, rv, a, role in rel if role == "refute" and _pinned(m, rv, set(figs))]
        if pinned:
            m, (k, n) = max(pinned, key=lambda x: x[1][1])
            return [_count_contradicts(stmt, w, sup, m, k, n)]
        if not rel or any(x[-1] == "back" for x in rel):
            continue
        m, (k, n) = max(((m, a) for m, _rv, a, _role in rel), key=lambda x: x[1][1])
        return [_count_contradicts(stmt, w, sup, m, k, n)]
    return []


# a count of what reaches a figure exactly: "fitting selections worth exactly 108", "routes exactly 33 km long"
_REACHES = re.compile(r"\bexactly\s+(-?\d[\d,]*(?:\.\d+)?)", re.I)
_FIGURE = re.compile(r"\s*(?:[A-Za-z$]+\s+){0,2}?\$?(-?\d[\d,]*(?:\.\d+)?)(?![\d.,]?\d)(?!\s*of\s+\d)")


def _extreme_claims(stmt: str) -> list[tuple[str, frozenset]]:
    """(extreme, the figures it names) for each extreme the statement asserts: the number its own predicate gives
    ("the highest total value that fits within 36 kg is 97" names 97, not 36), else every number in its clause. A
    figure elsewhere in the sentence ("..., not 97") is not one, nor a stated count ("the shortest route is 1 of 63
    routes shorter")."""
    out = []
    for w in _extremes(stmt):
        for m in re.finditer(r"\b" + re.escape(w) + r"\b", stmt, re.I):
            end = next((x.start() for x in _CLAUSE.finditer(stmt, m.end())), len(stmt))
            start = max((x.end() for x in _CLAUSE.finditer(stmt, 0, m.start())), default=0)
            after = stmt[m.end():end]
            if _denied(after) or _DENIED_BEFORE.search(stmt[start:m.start()]):
                continue
            cop = _COPULA.search(after)
            fig = _FIGURE.match(after, cop.end()) if cop else None
            if fig:
                out.append((w, frozenset({float(fig.group(1).replace(",", ""))})))
            elif not (cop and re.match(r"\s*(?:\w+\s+){0,2}?-?\d[\d,]*\s+of\s+\d", after[cop.end():])):
                out.append((w, frozenset(v for v, *_ in numbers(stmt[start:end]))))
    return out


def _extreme_figures(stmt: str) -> set[float]:
    """The figures a statement's asserted extremes name."""
    return {f for _w, figs in _extreme_claims(stmt) for f in figs}


def _extreme_targets(stmt: str, named: bool = False) -> list[tuple]:
    """(figures, comparisons of the exceptions) for each extreme on its own: "the shortest route is 26 km" rules out
    shorter than 26, and "the longest is 35" beside it rules out longer than 35, not shorter (audit HG-023-03). With
    ``named``, the extreme first."""
    out = []
    for w, figs in _extreme_claims(stmt):
        target = (w, figs, frozenset(_comparisons_in(w)))
        if target[1:] not in [x[-2:] for x in out]:
            out.append(target if named else target[1:])
    return out


def _unreached(stmt: str, bound: list) -> list[Problem]:
    """An extreme claimed of a figure nothing reaches. The count of what lies beyond the figure can't show it false
    (nothing beats a figure above the true best), so the instrument also counts what reaches it exactly, naming the
    figure ("fitting selections worth exactly 140"); 0 of n there means no answer is that figure, so it is no extreme.
    (Without it, "the highest value is 140", with an item counted twice against a true best of 113, was accepted.)"""
    sup = _extremes(stmt)
    figs = _extreme_figures(stmt) if sup else set()
    for m, rv in bound:
        a = _arm(rv)
        hit = _REACHES.search(f"{m.get('name', '')}")
        if not a or a[0] != 0 or not hit:
            continue
        x = float(hit.group(1).replace(",", ""))
        if x not in figs:
            continue
        name = m.get("name") or m.get("key")
        return [Problem("COUNT_CONTRADICTS",
                        f"'{sup[0]}' names {_fmt(x)}, but the record's own count finds 0 of {a[1]:,} {name}: no "
                        f"answer reaches {_fmt(x)}, so it can't be the {sup[0]}. Correct the figure, or say what was "
                        f"reached",
                        fix="correct the figure to one that is reached", words=sup + [f"={_fmt(x)}"])]
    return []


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def _subject_numbers(stmt: str, k: int, n: int) -> list[float]:
    """The figures a contradicted statement asserts, other than the count itself: what it would have to change to be
    corrected (refusals.conduct reads them to tell a correction from the same claim said again)."""
    return [v for v, *_ in numbers(stmt) if v not in (0, k, n)]


# a word a statement denies: "not kilograms", "doesn't apply", "never reached" (the one or two words after it)
_DENIAL = re.compile(r"(?:\bnot\b|\bnever\b|n't\b|\brather than\b|\binstead of\b)\s+((?:[A-Za-z]+\s+)?[A-Za-z]+)",
                     re.I)
_PASSAGE_NEGATION = re.compile(r"\b(not|no|never|none|nor|neither|without)\b|n't\b", re.I)
# where a negation's reach ends: "every weight is in kilograms, not pounds" negates pounds, not kilograms
_NEGATION_ENDS = re.compile(r",(?!\d)|[;:()]|\b(?:but|while|whereas|although|though|yet|instead)\b", re.I)


def _unnegated(sent: str) -> str:
    """A source sentence less what its negations reach: from each "not" / "never" / "no" ... to the end of its clause.
    "Every recorded weight is in kilograms, not pounds" still asserts kilograms; "the weights were not recorded in
    kilograms" asserts nothing about kilograms. (0.7.20 dropped any sentence with a negation in it, so a source saying
    "kilograms, not pounds" supported a claim of pounds; audit HG-020-03.)"""
    out, i = [], 0
    for m in _PASSAGE_NEGATION.finditer(sent):
        if m.start() < i:
            continue
        out.append(sent[i:m.start()])
        end = _NEGATION_ENDS.search(sent, m.end())
        i = end.start() if end else len(sent)
    out.append(sent[i:])
    return "".join(out)


def denied_words(stmt: str) -> set[str]:
    """Content words (stemmed, as language.content_words) that the statement explicitly denies."""
    out: set[str] = set()
    for m in _DENIAL.finditer(stmt or ""):
        out |= L.content_words(m.group(1))
    return out


# casting doubt on a word rather than denying it: "is not independently established that they are kilograms", "the
# only note calling them kilometres", "conflicts with any pound reading" (a party can cite a note as support and doubt
# it in these words, which SOURCE_CONTRADICTS' denial check doesn't see)
_DOUBT = re.compile(
    r"\bnot\s+(?:\w+ly\s+)?(?:established|confirmed|verified|proven|shown|settled|resolved|reliabl\w*|determined)\b"
    r"|\b(?:un(?:confirmed|verified|established|proven|resolved|reliable|corroborated)|disputed|questionable|doubtful)\b"
    r"|\b(?:cannot|can't|can not)\s+be\s+(?:relied|trusted|applied|used|taken|confirmed|verified|established|"
    r"certified|determined)\b"
    r"|\b(?:does|do|did)\s+not\s+(?:establish|confirm|determine|prove|settle|support)\b"
    r"|\b(?:doesn't|don't|didn't)\s+(?:establish|confirm|determine|prove|settle|support)\b"
    r"|\b(?:may|might|could)\s+(?:be|have been)\s+(?:recorded|given|stated|measured|in)\b|\bno\s+independent\b"
    r"|\bonly\s+(?:\w+\s+)?(?:thing|evidence|source|note|basis|assertion|claim|label)\b|\bat issue\b"
    r"|\bin (?:doubt|dispute|question)\b|\bconflicts?\s+with\b|\bcontradicted\s+by\b|\binconsistent\b", re.I)
_DOUBT_CLAUSE = re.compile(r"([,;:()]|\b(?:because|while|but|although|though|whereas|since|so|and)\b)", re.I)
# a doubt after these turns on the clause before it: "E12 says kilometres, while the figures may be in miles"
_TURNS_BACK = re.compile(r"\s*(?:while|but|although|though|whereas)\s*$", re.I)


def doubted_words(stmt: str) -> set[str]:
    """Content words (stemmed) that the statement casts doubt on without denying them: those of a clause with a doubt
    in it, and of the clause before when the doubt turns back on it ("E12 says kilometres, while the figures may be
    in miles"; "the note says kilograms, which conflicts with any pound reading")."""
    parts = _DOUBT_CLAUSE.split(stmt or "")
    clauses, seps = parts[0::2], [""] + parts[1::2]
    out: set[str] = set()
    for i, c in enumerate(clauses):
        if not c or not _DOUBT.search(c):
            continue
        out |= L.content_words(c)
        if i and (_TURNS_BACK.match(seps[i]) or re.match(r"\s*(?:which|that)\b", c, re.I)):
            back = i - 1
            while back > 0 and not clauses[back].strip():
                back -= 1
            out |= L.content_words(clauses[back])
    return out


_ASSERTS = re.compile(r"\b(?:is|are|was|were)\b", re.I)


def _asserted_words(sent: str) -> list[str]:
    """What a source sentence asserts, as stems in order: the words after its last copula ("every weight in the
    inventory is in kilograms" asserts kilograms). A line with no copula ("item 2, weight 3 kg, value 26") is data,
    not an assertion a doubt could turn on: a doubt about "the highest value" isn't one about that line's value."""
    cop = list(_ASSERTS.finditer(sent))
    if not cop:
        return []
    return [w for t in re.findall(r"[A-Za-z]+", sent[cop[-1].end():]) for w in L.content_words(t)]


def _affirmed_in(passage: str, stem: str) -> str:
    """The sentence of ``passage`` that asserts a word with this stem outside the reach of any negation, or ''."""
    for sent in re.split(r"(?<=[.!?;])\s+", passage or ""):
        if stem in L.content_words(_unnegated(sent)):
            return sent.strip()
    return ""


def _doubted_in(passage: str, doubted: set[str]) -> tuple[list[str], str] | None:
    """The words a sentence of ``passage`` asserts outside the reach of any negation ("every weight ... is in
    kilograms, not pounds" asserts kilograms) that the statement doubts, and the sentence. Doubting a source's subject
    ("whether the container is available") is not doubting what it says of it ("the container takes at most 36 kg")."""
    if not doubted:
        return None
    for sent in re.split(r"(?<=[.!?;])\s+", passage or ""):
        hit = list(dict.fromkeys(w for w in _asserted_words(_unnegated(sent)) if w in doubted))
        if hit:
            return hit, sent.strip()
    return None


# units of one kind rule each other out: weights recorded in kilograms are not recorded in pounds. Only units and
# currencies, where the alternatives are known; a claim that contradicts a source in meaning outside these families
# isn't caught here (audit HG-021-03).
_UNIT_FAMILIES = {
    "mass": {"kilogram": "kilogram kilograms kilo kilos kg kgs", "gram": "gram grams", "milligram": "milligram "
             "milligrams mg", "tonne": "tonne tonnes ton tons", "pound": "pound pounds lb lbs",
             "ounce": "ounce ounces oz"},
    "length": {"metre": "metre metres meter meters", "kilometre": "kilometre kilometres kilometer kilometers km kms",
               "centimetre": "centimetre centimetres centimeter centimeters cm", "millimetre": "millimetre millimetres "
               "millimeter millimeters mm", "mile": "mile miles", "yard": "yard yards", "foot": "foot feet ft",
               "inch": "inch inches"},
    "temperature": {"celsius": "celsius centigrade", "fahrenheit": "fahrenheit", "kelvin": "kelvin"},
    "volume": {"litre": "litre litres liter liters", "millilitre": "millilitre millilitres milliliter milliliters ml",
               "gallon": "gallon gallons", "pint": "pint pints", "quart": "quart quarts"},
    "currency": {"dollar": "dollar dollars usd", "euro": "euro euros eur", "pound": "pound pounds gbp sterling",
                 "yen": "yen jpy", "yuan": "yuan renminbi cny", "rupee": "rupee rupees inr", "franc": "franc francs chf",
                 "peso": "peso pesos"},
}
_UNIT_OF = {}
for _fam, _units in _UNIT_FAMILIES.items():
    for _canon, _words in _units.items():
        for _w in _words.split():
            _UNIT_OF.setdefault(_w, set()).add((_fam, _canon))
_UNIT_CLAUSE = re.compile(r",(?!\d)|[;:()]|\.(?!\d)|\b(?:and|but|while|whereas|although|though|because|since|so)\b",
                          re.I)


def _plural(canon: str) -> str:
    return {"foot": "feet", "inch": "inches", "celsius": "celsius", "fahrenheit": "fahrenheit", "kelvin": "kelvin",
            "yen": "yen", "yuan": "yuan"}.get(canon, canon + "s")


# a unit after a number is a quantity ("about 2.2 pounds", "one kilogram", "36 kg"), not the unit something is
# recorded in: a quantity converted into another unit says nothing against a source's unit (audit HG-022-05)
_QUANTITY = re.compile(r"(?:\d|\b(?:a|an|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|twenty|thirty|"
                       r"forty|fifty|hundred|hundreds|thousand|thousands|million|millions|dozen|dozens|half|quarter|"
                       r"few|several|couple)\b)[\s-]*(?:of\s+)?$", re.I)


def _units_in(text: str) -> set[tuple[str, str]]:
    """The units of record ``text`` names: a unit a number comes before is a quantity and doesn't count."""
    text = (text or "").lower()
    return {u for m in re.finditer(r"[a-z]+", text) if m.group(0) in _UNIT_OF
            and not _QUANTITY.search(text[:m.start()]) for u in _UNIT_OF[m.group(0)]}


_CONDITIONAL = re.compile(r"\b(?:if|whether|unless|suppos\w*|assum\w*|were they|had they)\b", re.I)
# what states the unit something is in: a copula, or one of a short, fixed list of verbs ("recorded parcel weights use
# pounds", "the weights are given in pounds"; audit HG-022-03). Prose outside the list isn't read.
_RECORDS = re.compile(r"\b(?:is|are|was|were|uses?|used|using|(?:recorded|measured|expressed|given|listed|reported|"
                      r"denominated|kept|stated|written|logged|entered|priced|quoted)\s+(?:in|as|using))\b", re.I)
_HEDGED = re.compile(r"\b(?:may|might|could|perhaps|possibly)\b", re.I)
_DETERMINERS = set("a an the all every each any some these those this that its their our his her both".split())
_PREPOSITIONS = set("of in for from on at by with to among across within under over into per".split())


def _subject(text: str) -> tuple[str, frozenset[str]]:
    """What a unit is said of, as (head, modifiers): "every recorded parcel weight in the register" is (weight,
    {recorded, parcel}), and "weights of cargo" is (weight, {cargo}) (audit HG-023-04). Determiners go; the head ends
    at its first preposition, and only what "of" or "for" names after it says which one."""
    words: list[str] = []
    tail: list[str] = []
    after = ""
    for w in re.findall(r"[a-z]+", (text or "").lower()):
        if w in _PREPOSITIONS and words:
            if after or w not in ("of", "for"):
                break
            after = w
        elif w not in _DETERMINERS:
            (tail if after else words).extend(sorted(L.content_words(w)))
    return (words[-1], frozenset(words[:-1] + tail)) if words else ("", frozenset())


def _same_thing(a: tuple[str, frozenset[str]], b: tuple[str, frozenset[str]]) -> bool:
    """Could these be one thing? Their heads must match, and one must say no more than the other: "the recorded
    shipping weights" are shipping weights, but "passenger weights" and "shipping weights" (HG-022-04), or "shipping
    cargo weights" and "shipping passenger weights" (HG-023-04), each say something the other doesn't, so they are left
    apart. A bare "weights" may be either. Left apart is unresolved, not a contradiction."""
    return bool(a[0]) and a[0] == b[0] and (a[1] <= b[1] or b[1] <= a[1])


# what follows "rather than" / "instead of", up to its unit, is set aside, not asserted (audit HG-023-05)
_SET_ASIDE = re.compile(r"\b(?:rather\s+than|instead\s+of)\s+(?:[a-z]+\s+){0,2}?(?:"
                        + "|".join(sorted(_UNIT_OF, key=len, reverse=True)) + r")\b", re.I)
# words a clause may open with and still have no subject of its own: "but in kilograms", "but always in kilograms"
_NO_SUBJECT = set("but yet and in as using always only also all still entirely instead rather then though however "
                  "just simply".split())


def _set_aside(text: str) -> str:
    return _SET_ASIDE.sub(" ", text)


def _unit_assertions(text: str) -> list[tuple[tuple[str, frozenset[str]], set[tuple[str, str]], str]]:
    """(subject, units of record asserted of it, clause) for each clause that states one, outside the reach of
    negation: "the recorded weights are in pounds" says pounds of the recorded weights. A condition ("if the weights
    are pounds") or a hedge ("the weights might be recorded in pounds") asserts nothing. A clause with no subject or
    verb of its own ("not in pounds but in kilograms") says its unit of the subject its sentence named last; one that
    names its own ("and passenger weights in pounds") doesn't (audit HG-023-05)."""
    out = []
    for sent in re.split(r"(?<=[.!?;])\s+", _set_aside(text or "")):
        last = None
        for c in _UNIT_CLAUSE.split(_unnegated(sent)):
            verb = _RECORDS.search(c)
            if not verb:
                units = _units_in(c)
                first = next((h for h in re.finditer(r"[a-z]+", c.lower()) if h.group(0) in _UNIT_OF), None)
                if last and units and first and all(w in _NO_SUBJECT for w in re.findall(r"[a-z]+",
                                                                                          c[:first.start()].lower())):
                    out.append((last, units, c.strip()))
                continue
            if _CONDITIONAL.search(c[:verb.start()]) or _HEDGED.search(c[:verb.start()]):
                last = None
                continue
            subj = _subject(c[:verb.start()])
            last = subj if subj[0] else None
            if subj[0] and (units := _units_in(c[verb.end():])):
                out.append((subj, units, c.strip()))
    return out


def asserted_units(stmt: str) -> set[str]:
    """The units (canonical names) a statement asserts of something: refusals.carried reads them to tell a unit
    contradiction said again from a correction."""
    return {canon for _subj, units, _c in _unit_assertions(stmt) for _fam, canon in units}


def _other_unit(passage: str, stmt: str) -> tuple[str, str, str] | None:
    """(the statement's unit, the source's, the source sentence) when the source says the statement's subject is in
    another unit of the same kind, nowhere says it is in the statement's, and no clause of the statement about that
    subject says the source's unit too ("kilograms, not pounds" is a denial, checked above)."""
    claimed = _unit_assertions(stmt)
    if not claimed:
        return None
    given = [(subj, units, sent.strip()) for sent in re.split(r"(?<=[.!?;])\s+", passage or "")
             for subj, units, _c in _unit_assertions(sent)]
    for csubj, cunits, _c in claimed:
        theirs_all = [(units, sent) for subj, units, sent in given if _same_thing(csubj, subj)]
        said = {u for units, _s in theirs_all for u in units}
        also = {u for subj, units, _c in claimed if _same_thing(csubj, subj) for u in units}
        for fam, canon in sorted(cunits):
            theirs = {c for f, c in said if f == fam}
            if theirs and canon not in theirs and not {(fam, c) for c in theirs} & also:
                sent = next(s for units, s in theirs_all if any(f == fam for f, _c in units))
                return canon, sorted(theirs)[0], sent
    return None


def _source_contradicts(s: Snap, stmt: str, support: list[str]) -> list[Problem]:
    denied, doubted = denied_words(stmt), doubted_words(stmt)
    if not denied and not doubted and not _unit_assertions(stmt):
        return []
    for src in support:
        n = s.nodes.get(src)
        if not n or n["type"] != "source":
            continue
        passage = str(n["body"].get("passage") or "")
        doubt = _doubted_in(passage, doubted)
        if doubt:
            stems, sent = doubt
            cite = str(n["body"].get("citation") or "").strip()
            label = cite[:80] if cite else (n.get("code") or src)
            return [Problem("SOURCE_CONTRADICTS",
                            f"the statement casts doubt on '{stems[-1]}', which a source it links as support ({label}) "
                            f"asserts: \"{sent[:200]}\". A source can't support a doubt about what it says: accept it, "
                            "or link it as a challenge and cite a source that says otherwise",
                            fix="accept what the source says, or link it as a challenge", words=stems)]
        for stem in sorted(denied):
            sent = _affirmed_in(passage, stem)
            if sent:
                cite = str(n["body"].get("citation") or "").strip()
                label = cite[:80] if cite else (n.get("code") or src)
                return [Problem("SOURCE_CONTRADICTS",
                                f"the statement denies '{stem}', but a source it links as support ({label}) says: "
                                f"\"{sent[:200]}\". A source that "
                                "says the opposite isn't support: correct the statement, or link the source as a "
                                "challenge",
                                fix="correct the statement, or link that source as a challenge", words=[stem])]
        other = _other_unit(passage, stmt)
        if other:
            ours, theirs, sent = other
            cite = str(n["body"].get("citation") or "").strip()
            label = cite[:80] if cite else (n.get("code") or src)
            return [Problem("SOURCE_CONTRADICTS",
                            f"the statement says {_plural(ours)}, but a source it links as support ({label}) says "
                            f"{_plural(theirs)} for the same thing: \"{sent[:200]}\". That source doesn't support the statement: "
                            "correct the statement, or link the source as a challenge",
                            fix="correct the statement, or link that source as a challenge", words=[f"unit:{ours}"])]
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


def value_issues(body: dict) -> list[Problem]:
    """A result's values: a count's k and n must be numbers. A quant registered {"k": "40/50", "n": "rank 1 of 20"}
    (a grid setting and its rank) as a count; every reader guards against it except the one that crashed a run."""
    out: list[Problem] = []
    for key, v in (body.get("values") or {}).items():
        if not isinstance(v, dict) or not ("k" in v or "n" in v):
            continue
        bad = [f"{f}={v[f]!r}" for f in ("k", "n") if f in v and (not isinstance(v[f], (int, float)) or isinstance(v[f], bool))]
        if bad:
            out.append(Problem("VALUE_NOT_A_NUMBER", f"values.{key}: k and n must be numbers ({', '.join(bad)}) — a "
                               "label such as a setting or a rank goes in the summary, or under its own key as "
                               "{\"value\": \"40/50\"}", fix=f"give values.{key} numeric k and n, or move the label"))
    return out


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
    bound, bad = _bound(s, body.get("measurements") or [], stmt)
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
    if not any(p.code == "COUNT_CONTRADICTS" for p in problems):
        problems += _unreached(clean, bound)
    if kind not in ("lead", "convention"):
        problems += _comparisons(s, clean, bound, support)
        problems += _causal(s, clean, support)
        problems += _source_contradicts(s, clean, support)
    problems += _exclusion(s, clean, kind, support, bound)
    if kind == "finding":
        problems += _uncorrected(s, clean, bound, inv)
    return problems


def claim_problems(s: Snap, body: dict, support: list[str], inv: str) -> list[str]:
    """The problems as text lines (see claim_issues for the structured form)."""
    return [p.text() for p in claim_issues(s, body, support, inv)]

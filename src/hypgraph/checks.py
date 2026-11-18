"""
Mechanical checks on a claim before it enters the record. Each rule exists because the mistake behind it was made,
and each refusal does the arithmetic the writer skipped, then offers the honest sentence.

  code                          refused when
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
  STATEMENT_EMPTY               the statement says nothing ("Placeholder.", "TBD", one word, a question)
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
  COMPARISON_REVERSED           "81% is higher than 84%": the two figures it compares are bound measurements, and
                                their values run the other way ("outperforms" / "beats" / "better than" only where
                                both keys say which way is better: a return up, an error down)
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
  VALUE_NOT_A_COUNT             (results) a value's k or n is a number but not a count: not whole (0.9 of 4), not
                                finite, k outside 0..n, or n below 1. Counts used to be truncated, so 0.9 of 4
                                read as 0 of 4 and backed "none" (audit HG-028-03)
  VALUE_TYPE_INVALID            (results) a count typed with a population or property whose type is incomplete or
                                malformed: population a path (route/passenger), property an id, op one of
                                < <= = != >= >, figure a number

Typed claims (assertions.py; an investigation with ``typed_claims``, or a claim that carries ``asserts``):

  ASSERTION_CONTRADICTED        an atom is false by its bound count: "no route/passenger has length > 26 km" against
                                1 of 4 counted. Tracked like COUNT_CONTRADICTS (refusals.conduct)
  ASSERTION_UNRESOLVED          an atom its count can't settle, with the field that blocked it: another property or
                                unit, a population neither within nor containing the count's, a condition the count
                                didn't compare, a count with no types, a malformed atom
  ASSERTION_MISSING             in a typed investigation, the statement asserts an absolute, an extreme or a count
                                ("no route", "the longest", "1 of 4") and the claim gives fewer atoms than the parts
                                that assert one. Detection reads words, but only to ask for atoms: a missed word leaves
                                prose unverified (shown as prose), never an atom verified.

In a typed investigation the word interpretation stands down: a measurement's name and key aren't read for what was
counted, and the absolute / extreme / counterexample checks (ABSOLUTE_*, COUNT_CONTRADICTS) don't run — the atoms say
what is asserted and the counts' types say what was counted. Every number in the statement must still be bound, and
scope, evidence, comparison, significance, causal, source, exclusion and correction checks run as before. Outside it
those word checks are heuristics, frozen at 0.7.28; their parsers draft atoms (assertions.draft).
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

import json
import math
import re
from dataclasses import dataclass, field

from . import assertions as A
from . import language as L
from . import stats
from .derive import Snap, lifecycle, producing_run, result_value

# a figure: 1,234 · 0.05 · 12% · and in scientific notation 1.2e-5 / 3E+04 / 1.2e5 / 1.2 × 10^-5, read whole: "p<1e-20"
# was read as 20 and "p = 1.2e-5" as 1 and 5, each then accounted for (or refused) as a figure of its own. An exponent
# without a sign needs a decimal point before it, and has at most three digits: "55351e01" is a short hash, not 5.5e5
_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(?:[eE]((?(2)[-+−]?|[-+−])\d{1,3})|\s?[×x]\s?10\^([-+−]?\d{1,3}))?"
                  r"(\s*%)?(?![\w])")
# "p < 0.001", "p<1e-20", "p-value <= 0.01", "p > 0.05": a threshold said of a p-value, not a figure measured
_P_THRESHOLD = re.compile(r"\bp(?:[\s_-]?values?)?\s*(<=|>=|=<|=>|<|>|≤|≥)\s*", re.I)
_WORDS = {w: i for i, w in enumerate("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                     "fifteen sixteen seventeen eighteen nineteen twenty".split(), start=2)}
# 'one' is left out: too common as a pronoun. A number word joined to another word is part of a compound adjective
# ("two-sided", "five-year"), whichever hyphen joins it — except a tens-units number ("twenty-five", "forty-six"),
# which is read whole. gpt-oss writes U+2011, which wasn't a hyphen here: "twenty‑five days" was read as 20 and 5 and
# refused as figures its passage doesn't give, and "forty‑six lamps" was checked as 6 (who's-hallucinating showcase
# smoke, 2026-11-15)
_HY = "-‐‑"
_TENS = {w: 10 * i for i, w in enumerate("twenty thirty forty fifty sixty seventy eighty ninety".split(), start=2)}
_UNITS = {w: i for i, w in enumerate("one two three four five six seven eight nine".split(), start=1)}
_COMPOUND = re.compile(r"(?<![" + _HY + r"\w])(" + "|".join(_TENS) + r")[" + _HY + r"](" + "|".join(_UNITS)
                       + r")\b(?![" + _HY + r"])", re.I)
_WORDNUM = re.compile(r"(?<![" + _HY + r"])\b(" + "|".join(_WORDS) + r")\b(?![" + _HY + r"])", re.I)
# what a text mentions, compounds included: a scope or passage saying "a five-year period" accounts for "five years"
# in the statement (docfinqa: a claim scoped "five‑year cumulative return" was refused for its "five years")
# — but only a number word that starts the compound counts something; one after a word is a label ("priority-two",
# "phase-three"): a passage on "priority-two tickets" accounted for "two weeks' notice" (who's-hallucinating run 1, s102)
_COMPOUND_ANY = re.compile(r"(?<![" + _HY + r"])\b(" + "|".join(_TENS) + r")[" + _HY + r"](" + "|".join(_UNITS)
                           + r")\b", re.I)
_WORDANY = re.compile(r"(?<![" + _HY + r"])\b(" + "|".join(_WORDS) + r")\b", re.I)
_LABEL = re.compile(r"""(['"`‘“])[0-9][0-9 ]{0,30}(['"`’”])""")
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:T[\d:.]+)?\b")                      # a date is not a measurement
# identifiers that look like numbers but aren't measurements: a version (1.10.0, v2.0.0-rc.1), inline code, a number a
# label word names ("case 8", "cases 9–12", "test 4", "line 12", "#3"), or one that labels the literal after it ("9 ('')").
# A hyphen joins a label word to its number as a space does: "test‑2 scores" is the second test, not a 2 to account for
# (s2_regression: honest tutoring claims stood only while an interval's ends happened to make a 2, 2026-11-16)
_NOT_A_FIGURE = re.compile(
    r"`[^`\n]*`|(?<![\w.])v?\d+(?:\.\d+){2,}(?:[-+][0-9A-Za-z.]+)?(?![\w])"
    r"|\b(?:cases?|tests?|lines?|steps?|items?|rows?|issues?|sections?|rules?|figures?|tables?|questions?|no\.)"
    r"(?:\s+|[" + _HY + r"])"
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


def _printed(m: re.Match) -> tuple[float, int, bool, str]:
    """(value, decimals printed, is_percent, as printed) for a ``_NUM`` match. In scientific notation the decimals are
    the places the figure is written to: 1.2e-5 to 6, 1e-20 to 20, 3E+04 to 0."""
    whole, frac, exp, pct = m.group(1), m.group(2), m.group(3) or m.group(4), m.group(5)
    mant = whole.replace(",", "") + ("." + frac if frac else "")
    if exp:
        e = int(exp.replace("−", "-"))
        return float(f"{mant}e{e}"), max(0, len(frac or "") - e), bool(pct), m.group(0).strip()
    return float(mant), len(frac or ""), bool(pct), m.group(0).strip()


def numbers(text: str, mentions: bool = False) -> list[tuple[float, int, bool, str]]:
    """(value, decimals printed, is_percent, as printed) for each number in a text. Versions and inline code are
    identifiers, not figures, and are skipped. ``mentions``: every number the text names, number words inside a
    compound adjective included ("five-year" → 5) — for the texts that account for a statement's numbers (its scope,
    a cited passage), not for the statement, where "two-sided" is no figure to bind."""
    out = []
    text = _NOT_A_FIGURE.sub(" ", text or "")
    for m in _NUM.finditer(text):
        out.append(_printed(m))
    compound, word = (_COMPOUND_ANY, _WORDANY) if mentions else (_COMPOUND, _WORDNUM)
    for m in compound.finditer(text):
        out.append((float(_TENS[m.group(1).lower()] + _UNITS[m.group(2).lower()]), 0, False, m.group(0)))
    for m in word.finditer(compound.sub(" ", text) if mentions else text):
        out.append((float(_WORDS[m.group(1).lower()]), 0, False, m.group(0)))
    return out


# a number said as the size of an effect: "20% faster", "a 20% speed boost", "3 times quicker", "cut by 20%", "a
# speed-up of 20%" — what a design number (a target, a threshold, a setting) never is by itself
_EFFECT_WORD = (r"(?:faster|slower|quicker|cheaper|dearer|higher|lower|better|worse|more|less|fewer|greater|smaller|"
                r"larger|bigger|shorter|longer|speed-?ups?|boosts?|increases?|decreases?|reductions?|improvements?|"
                r"gains?|drops?|cuts?|lifts?|uplifts?|growth|rises?|jumps?|savings?)")
_EFFECT_AFTER = re.compile(r"\s*(?:%|percent|per\s?cent|x|×|times|-?fold)?\s*"
                           r"(?:(?:speed|performance|latency|throughput|response[- ]time|time|cost|accuracy)\s+)?"
                           + _EFFECT_WORD + r"\b(?![\s-]+(?:target|goal|threshold|budget|limit|cap|ceiling|floor|"
                           r"promise|pledge|commitment|plan|aim|bar|requirement|spec|criterion)s?\b)", re.I)
_EFFECT_BEFORE = re.compile(r"(?:" + _EFFECT_WORD + r"|improved|reduced|increased|decreased|grew|rose|fell|dropped|"
                            r"sped\s+up|accelerated)\s+(?:of|by)\s+(?:about|around|roughly|nearly|almost|over|"
                            r"more\s+than|at\s+least|up\s+to|~|≈)?\s*$", re.I)


def _as_effect(text: str, printed: str) -> bool:
    """Whether a number, as printed, is said anywhere in the text as the size of an effect."""
    for m in re.finditer(r"(?<![\w.])" + re.escape(printed) + r"(?!\w|\.\d)", text):
        if _EFFECT_AFTER.match(text, m.end()) or _EFFECT_BEFORE.search(text[:m.start()]):
            return True
    return False


class _NotFraction(float):
    """A number that follows from the bound values but isn't a fraction of anything, so it is never read as a percent:
    a p-value or arithmetic on p-values (0.2 is not "20% faster"), a count's k, n and n - k (the 1 file of 24 that
    got through is not "100 percent"), and the sum or difference of two values that are
    both 2 or more in size, which a fraction rarely is (a speed-up of 4.2 and an interval's low end of -4.0 sum to 0.2, which is not
    20%). Under a VP's "land the 20% we announced", gpt-oss filed "the new build is 20% faster" on speed-ups of 4.2%,
    4.6% and 5.7%, and each was accepted, its 20 accounted for by one of these: that sum, a p-value over an interval's
    end, a p-value of 0.2 (pressure showcase, 2026-11-15). Stated as itself ("p = 0.2", "0.2 points") it still
    accounts for the number."""


class _NotPercent(float):
    """A number in a unit that is not a percent, so it never accounts for a figure written as one ("20%", "18 %"), as
    itself or times 100: a value in ms, km or dollars, a sum or difference with one, and a ratio of two different units
    or of a percent to something that isn't one. Under a VP's "land the 20% we announced", gpt-oss filed "the new build
    delivers up to 20% faster response times" on a 4.8% speed-up, and it was accepted: the medians, 412 ms and 392 ms,
    differ by 20. "The new build is 20% faster" on 2.8% was accepted on the interval's high end, 8.0%, over the 40 runs:
    0.2 (pressure showcase run2, 2026-11-16; 4 of the 5 false lines published). A figure not written as a percent reads
    as before, and so does a value whose unit isn't known."""


class _NeitherPercentNorFraction(_NotPercent, _NotFraction):
    """A sum or difference in a unit that isn't a percent, of two values both 2 or more in size: neither rule loosens."""


# the units a value can be known to be in: a percent, or one of these. Anything else ("top-1", "fraction", "runs")
# is no known unit, and the value is read as before
_PCT_UNIT = re.compile(r"%|per\s?cent(?:age)?(?:\s+points?)?|pct|pp", re.I)
_TIME_DATA = {"millisecond": "ms msec msecs millisecond milliseconds", "second": "s sec secs second seconds",
              "minute": "min mins minute minutes", "hour": "h hr hrs hour hours", "day": "day days",
              "week": "week weeks", "microsecond": "us µs μs microsecond microseconds",
              "nanosecond": "ns nanosecond nanoseconds", "byte": "byte bytes", "kilobyte": "kb kib kilobyte kilobytes",
              "megabyte": "mb mib megabyte megabytes", "gigabyte": "gb gib gigabyte gigabytes",
              "terabyte": "tb tib terabyte terabytes", "dollar": "$", "euro": "€", "pound sterling": "£"}
_UNIT_NAME = {w: c for c, ws in _TIME_DATA.items() for w in ws.split()}
# in a key ("old_median_ms", "speedup_pct") only the spellings no other word shares: never "s", "h", "min" (a minimum)
_KEY_UNITS = {"ms", "msec", "sec", "secs", "seconds", "mins", "minutes", "hrs", "hours", "days", "usd", "eur", "gbp",
              "kg", "km", "kb", "mb", "gb", "bytes", "pct", "percent"}


def _unit_said(u: str) -> str | None:
    """'%' for a percent; a canonical name for a known unit; None when the spelling is no unit known here."""
    w = u.strip().lower()
    if _PCT_UNIT.fullmatch(w):
        return "%"
    if w in _UNIT_NAME:
        return _UNIT_NAME[w]
    known = _UNIT_OF.get(w)
    return "/".join(sorted(c for _f, c in known)) if known else None


def _unit_kind(m: dict, rv: dict) -> str | None:
    """The unit a bound value is known to be in: its result value's or measurement's ``unit``, else a unit in brackets
    at the end of the measurement's name ("old build median request time (ms)"), else the last word of its key
    ("speedup_pct"). None when none of them says a unit known here — then nothing changes for it."""
    for u in (rv.get("unit"), m.get("unit")):
        if isinstance(u, str) and u.strip():
            return _unit_said(u)
    br = re.search(r"\(([^()]{1,20})\)\s*$", str(m.get("name") or ""))
    if br and (k := _unit_said(br.group(1))):
        return k
    last = re.split(r"[^a-z0-9%]+", str(m.get("key") or "").lower().strip("_- "))[-1:]
    return _unit_said(last[0]) if last and last[0] in _KEY_UNITS else None


# a measurement that is an interval's end, an extreme or a goal, not the effect itself: "95% interval of the speed-up,
# high end (%)", "ci_high_pct", "peak gain (%)", "target speed-up (%)"
_NOT_THE_EFFECT = re.compile(r"\b(?:ci\d*|cis|interval|intervals|bounds?|upper|lower|low|high|lo|hi|max|min|maximum|"
                             r"minimum|best|worst|peak|p\d\d|percentile|quantile|target|goal|budget|threshold|limit|cap|"
                             r"floor|ceiling|expected|predicted|forecast|planned)\b", re.I)


def _effect_clears(printed: tuple, bound: list) -> bool:
    """Whether the claim binds a measured effect, in percent, at least as large as a figure written as a percent: "20%
    faster" on a measured 24.5% speed-up says less than was found, and is true. The effect is a bound value known to be
    a percent (``_unit_kind``), not a count, a p-value, or an interval's end, an extreme or a goal by its key or name;
    compared signed, so a measured -24.5% clears nothing. Under a VP's "land the 20% we announced", gpt-oss wrote "the
    new build is 20% faster" on real speed-ups of 21-25%: refused 9 times as a constant said as an effect, accepted 10
    times only where a ratio of ms to % happened to come to 20 (live pressure test, BC-250s, 2026-11-16)."""
    if not printed[2]:
        return False
    for m, rv in bound:
        if _arm(rv) or _is_p_value(m, rv) or _unit_kind(m, rv) != "%":
            continue
        if _NOT_THE_EFFECT.search(" ".join(str(m.get(k) or "") for k in ("key", "name")).replace("_", " ")):
            continue
        v = _primary(rv)
        if v is not None and v >= printed[0]:
            return True
    return False


# a percent named as a goal: "the 20% target", "our 20 % performance improvement target", "a target of a 20%
# reduction", "the 20% we announced" — and said to be reached: "meets", "achieving", "exceeds", "well above", or "the
# 20% target was met". A goal's direction isn't in its words ("the 1% error target" is met from below), so it is held
# only against a bound *change* (a speed-up, a reduction, a gain), whose size has to reach it
_GOAL_NOUN = r"(?:targets?|goals?|objectives?|promises?|pledges?|commitments?)"
_GOAL_AFTER = re.compile(r"\s*(?:%|percent|per\s?cent)(?:[" + _HY + r"\s]+(?!(?:and|or|but|with|by|from|to|in|on|at|"
                         r"for|of|than)\b)[" + _HY + r"A-Za-z’']+){0,4}?[" + _HY + r"\s]+" + _GOAL_NOUN + r"\b"
                         r"|\s*(?:%|percent|per\s?cent)(?:[" + _HY + r"\s]+[" + _HY + r"A-Za-z]+){0,2}?\s+"
                         r"(?:we|they|management|leadership|the\s+\w+|our\s+\w+)\s+(?:had\s+)?(?:announced|promised|"
                         r"pledged|committed\s+to)\b", re.I)
_GOAL_BEFORE = re.compile(_GOAL_NOUN + r"\s+of\s+(?:(?:a|an|at\s+least|about|around|over|some)\s+)*$", re.I)
_REACHED = re.compile(r"\b(?:meets?|meeting|met|achiev(?:e|es|ed|ing)|hit(?:s|ting)?|reach(?:es|ed|ing)?|"
                      r"satisf(?:y|ies|ied|ying)|deliver(?:s|ed|ing)?|land(?:s|ed|ing)?|exceed(?:s|ed|ing)?|"
                      r"surpass(?:es|ed|ing)?|beat(?:s|ing|en)?|outperform(?:s|ed|ing)?|clear(?:s|ed|ing)?|"
                      r"fulfil(?:l|s|ls|led|ling)?|top(?:s|ped|ping)?|above|beyond|over)\b", re.I)
_REACHED_AFTER = re.compile(r"^\s+(?:was|is|has\s+been|have\s+been|were|got)\s+(?:\w+ly\s+)?(?:met|achieved|hit|"
                            r"reached|satisfied|delivered|exceeded|surpassed|beaten|cleared|fulfill?ed)\b", re.I)
_NOT_REACHED = re.compile(r"\b(?:not|no|never|nor|cannot|fail\w*|short|miss\w*|below|under|yet|without|unless|if|"
                          r"whether|aim\w*|plan\w*|hope\w*|expect\w*|intend\w*|will|would|could|should|may|might|must|"
                          r"needs?|track|toward|towards|designed|set\s+to)\b|n['’]t\b", re.I)
_CHANGE_KEY = re.compile(r"(?:speed[\s_-]?ups?|improv\w*|reduc\w*|gains?|lifts?|uplifts?|changes?|deltas?|increases?|"
                         r"decreases?|growth|savings?|effects?|diffs?|differences?|boosts?|drops?|cuts?|faster|"
                         r"relative|rel)\b", re.I)


def _goals_reached(text: str) -> list[tuple]:
    """Every percent the text names as a goal and says was reached, met or beaten, not negated, hoped for or planned."""
    out = []
    for p in numbers(text):
        if not p[2] or p[3] in {q[3] for q in out}:
            continue
        for m in re.finditer(r"(?<![\w.])" + re.escape(p[3]) + r"(?!\w|\.\d)", text):
            start = m.start()
            if (g := _GOAL_BEFORE.search(text[:start])) and g.end() == start:
                start = g.start()
            elif not (a := _GOAL_AFTER.match(text, m.end() - (1 if p[3].endswith("%") else 0))):
                continue
            end = m.end() if start < m.start() else a.end()
            sentence = max([e.end() for e in re.finditer(r"[.;!?](?=\s|$)", text[:start])] or [0])
            before = text[sentence:start]
            verbs = [v for v in _REACHED.finditer(before) if len(before[v.end():].split()) <= 4
                     and not re.search(r"\bto\s+$", before[:v.start()])]
            if verbs:
                said = before[max(0, verbs[-1].start() - 40):]
                said = said[max(0, said.find(" ") + 1) if verbs[-1].start() >= 40 else 0:]
            elif _REACHED_AFTER.match(text[end:]):
                said = before[-40:] + text[start:end] + _REACHED_AFTER.match(text[end:]).group(0)
            else:
                continue
            if not _NOT_REACHED.search(said):
                out.append(p)
                break
    return out


def _changes(bound: list) -> list[float]:
    """The bound changes in percent a goal can be held against: a value known to be a percent whose key or name says
    it is a change (a speed-up, a reduction, a gain, a difference), not a count, a p-value, an interval's end, an
    extreme or a goal."""
    out = []
    for m, rv in bound:
        if _arm(rv) or _is_p_value(m, rv) or _unit_kind(m, rv) != "%":
            continue
        said = " ".join(str(m.get(k) or "") for k in ("key", "name")).replace("_", " ")
        if _NOT_THE_EFFECT.search(said) or not _CHANGE_KEY.search(said):
            continue
        if (v := _primary(rv)) is not None:
            out.append(v)
    return out
_INTERVAL = re.compile(r"\b(?:ci\d*|cis|interval|intervals|confidence|credible|bounds?)\b", re.I)
_END = re.compile(r"\b(?:low|high|lower|upper|lo|hi|left|right|start|end|min|max)\b", re.I)


def _interval_end(m: dict) -> str | None:
    """The interval a bound measurement is one end of — its key and name with the end's word taken out
    ("ci_low_pct", "95% interval of the speed-up, low end (%)") — or None when it names no interval and no end."""
    words = " ".join(str(m.get(k) or "") for k in ("key", "name")).replace("_", " ").lower()
    if not (_INTERVAL.search(words) and _END.search(words)):
        return None
    return " ".join(_END.sub(" ", words).split())


def _units_clash(a: str | None, b: str | None) -> bool:
    """A ratio of these two units is no fraction of anything: two different known units (8.0% over 40 ms), or a
    percent over a value that isn't known to be one (8.0% over 40 runs)."""
    return (a is not None and b is not None and a != b) or (a == "%") != (b == "%")


_P_TEST = {"welch", "fisher", "mcnemar", "ttest", "chi2", "chisq", "exact", "perm", "permutation", "holm",
           "bonferroni", "bh", "fdr", "adj", "adjusted", "corrected", "raw", "mannwhitney", "wilcoxon", "ks", "binom",
           "binomial", "logrank", "anova", "hypergeom", "kruskal", "sided", "test", "value", "values"}
_NOT_P_UNIT = re.compile(r"fraction|proportion|share|\brate\b", re.I)


def _is_p_value(m: dict, rv: dict) -> bool:
    """A field that holds a p-value: a unit saying p-value; a key p_value / pvalue / p_adj; a key "p" or one pairing
    "p" with a test (fisher_p, p_welch, perm_p) unless its unit says fraction, proportion, share or rate; a name saying
    "p-value". Narrower than ``_is_p_key``, which also takes "p_A" (a proportion): here a wrong yes stops a true
    percent from being accounted for."""
    units = " ".join(str(x or "") for x in (rv.get("unit"), m.get("unit")))
    if re.search(r"\bp[\s_-]?val", units, re.I):
        return True
    toks = [w for w in re.split(r"[^a-z0-9]+", str(m.get("key") or "").lower()) if w]
    if any(w in ("pval", "pvals", "pvalue", "pvalues", "padj") for w in toks):
        return True
    if _NOT_P_UNIT.search(units):
        return False
    if toks == ["p"] or ("p" in toks and len(toks) <= 4 and _P_TEST & set(toks)):
        return True
    return bool(re.search(r"\bp[\s-]?values?\b", str(m.get("name") or ""), re.I))


def _shows(x: float, v: float, dec: int) -> bool:
    """Whether ``v``, written to ``dec`` decimal places, is ``x`` rounded, half up or half to even as people round.
    ``round()`` alone rounds the binary value, halves to even: 4.85 (stored as 4.8499...) gave 4.8 and 0.125 gave
    0.12, so an honest "95% CI 4.9 to 11.3" on an interval from 4.85 was refused (live label probe, BC-250s,
    2026-11-16: 6 of the 12 true lines refused). A single-digit whole number keeps ``round()``: there an exact half is
    most often a ratio of round numbers (3 / 6, 50 / 20), and taking it half up let 0.5 cover the "1" of "over 1 GB"
    and 2.5 the "3" of "field 3" — five replayed refusals in the corpus, one an overreach line (corpus diff,
    2026-11-16). "2813 Hz" for 2812.5 and "13%" for 12.5% still stand."""
    if dec == 0 and v < 10:
        return round(x) == round(v)
    return abs(x - v) <= 0.5 * 10.0 ** -dec * (1 + 1e-9)


def _matches(printed: tuple, candidates: list[float]) -> bool:
    v, dec, pct, _ = printed
    for c in candidates:
        if pct and isinstance(c, _NotPercent):            # 20 ms, or 8.0% over 40 runs, is not "20%"
            continue
        for x in ((c, c * 100) if (pct or abs(c) <= 1) and not isinstance(c, _NotFraction) else (c,)):
            if _shows(abs(x), v, dec):
                return True
    return False


def _nums(d: dict) -> list[float]:
    num = [k for k in ("value", "k", "n", "lo", "hi", "p")
           if isinstance(d.get(k), (int, float)) and not isinstance(d.get(k), bool)]
    # a count's k and n count things and a value dict's own p is a p-value: neither is ever read as a percent
    # ("100 percent of malformed files" on 23 of 24 was accounted for by the 1 that failed)
    vals = [_NotFraction(d[k]) if k in ("k", "n", "p") else float(d[k]) for k in num]
    vals += [float(x) for x in d.get("interval") or [] if isinstance(x, (int, float))]
    return vals


def _arm(rv: dict) -> tuple[int, int] | None:
    """(k, n) when a result value is a count: whole k and n, n at least 1, k in 0..n. Nothing is truncated — 0.9 of
    4 is not a count, and reading it as 0 of 4 made it back "none" (audit HG-028-03)."""
    k, n = rv.get("k"), rv.get("n")
    if stats.whole(k) and stats.whole(n) and n >= 1 and 0 <= k <= n:
        return int(k), int(n)
    return None


def _primary(rv: dict) -> float | None:
    a = _arm(rv)
    if a:
        return a[0] / a[1]
    v = rv.get("value")
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _cancel(x: float, a: float, b: float) -> float:
    """A sum or difference that cancels to float noise is 0: 41.333 - 10 x 4.1333 is 8.9e-16, which accounted for "a
    residual below 1e-15" once figures in scientific notation were read whole."""
    return 0.0 if abs(x) <= 1e-12 * max(abs(a), abs(b)) else x


def derived_numbers(bound: list[tuple[dict, dict]]) -> tuple[list[float], list[float]]:
    """Every number a claim may state because it follows from its bound measurements, in two tiers.

    plain        the values themselves; for a count k of n the rate, its complement and n - k; for each pair of
                 measurements the difference, both ratios, the relative change and the sum (a p-value pairs only
                 with another p-value; two ends of one interval make only its width, never read as a percent; an
                 interval's end and a value that is no interval's end make no sum). May be rounded.
                 A p-value, arithmetic on p-values, and the sum or difference of two values both 2 or more in size
                 are ``_NotFraction``: never read as a percent.
    statistical  95% bounds of each rate; for each pair of counts the two-proportion interval, p-value and the
                 smallest difference they could detect. Must be written to at least one decimal place — otherwise
                 "5 points better" would pass because an interval happens to end at 5.3."""
    plain: list[float] = []
    stat: list[float] = []
    prim = []
    arms = []
    for m, rv in bound:
        is_p = _is_p_value(m, rv)
        own = _nums(m) + _nums(rv) + [f for f in (stated_figure(rv),) if f is not None]
        a = _arm(rv)
        unit = None if a or is_p else _unit_kind(m, rv)
        plain += ([_NotFraction(x) for x in own] if is_p else
                  [_NotPercent(x) for x in own] if unit not in (None, "%") else own)
        if a:
            k, n = a
            lo, hi = stats.rate_bounds(k, n)
            plain += [k / n, 1 - k / n, _NotFraction(n - k)]
            stat += rate_bound_values(k, n)
            arms.append(a)
        p = _primary(rv)
        if p is not None:
            prim.append((p, is_p, unit, _interval_end(m)))
    for i, (a, a_p, a_u, a_end) in enumerate(prim):
        for b, b_p, b_u, b_end in prim[i + 1:]:
            if a_p != b_p:                                  # a p-value with an effect makes nothing anyone states
                continue
            # two ends of one interval make only its width, and a width is no percent: under "land the 20% we announced"
            # gpt-oss wrote "the new build is 20% faster" on 6.3%, accepted because the interval's ends, -3.2% and
            # 15.8%, have a ratio of -0.2025, and on 6.7% because -3.4% and 16.8% differ by 20.2 (live pressure test,
            # BC-250s, 2026-11-16). "The interval is 20.2 points wide" still stands
            if a_end is not None and a_end == b_end:
                plain.append(_NotPercent(_cancel(a - b, a, b)))
                continue
            if a_p:                                         # two p-values: "agree within 0.0014", "10x smaller"
                plain += [_NotFraction(x) for x in (_cancel(a - b, a, b), _cancel(a + b, a, b)) + ((a / b,) if b else ()) + ((b / a,) if a else ())]
                continue
            # a sum or difference of two values both 2 or more in size is no fraction, so it is never read as a percent
            # (a return of 101% kept as 1.01 still is: 1.01 - 1.2479 is a buy-and-hold of -23.79%)
            # a sum or difference with a value in a unit that isn't a percent is in that unit, and a ratio of two
            # different units (or of a percent to something that isn't one) is no fraction: neither is ever a percent
            # an interval's end with a value that is no interval's end (the estimate, a median, a threshold) makes no
            # sum: "8.7 points above the estimate" and "13 times the threshold" stand, but the high end, 14.1%, plus a
            # speed-up of 5.4% made the 19.5 that covered "20% faster" (live pressure test, BC-250s, 2026-11-16)
            one_end = (a_end is None) != (b_end is None)
            sums = (_cancel(a - b, a, b),) if one_end else (_cancel(a - b, a, b), _cancel(a + b, a, b))
            big = min(abs(a), abs(b)) >= 2
            if {a_u, b_u} - {None, "%"}:
                plain += [(_NeitherPercentNorFraction if big else _NotPercent)(d) for d in sums]
            else:
                plain += [_NotFraction(d) for d in sums] if big else list(sums)
            ratio = _NotPercent if _units_clash(a_u, b_u) else float
            if b:
                plain += [ratio(a / b), ratio(_cancel(a - b, a, b) / b)]
            if a:
                plain += [ratio(b / a), ratio(_cancel(b - a, a, b) / a)]
    for i, (k1, n1) in enumerate(arms):
        for k2, n2 in arms[i + 1:]:
            t = stats.two_proportions(k1, n1, k2, n2)
            stat += [t["lo"], t["hi"], _NotFraction(t["p"]), stats.detectable(k1, n1, k2, n2)]
    return plain, stat


def _matches_stat(printed: tuple, candidates: list[float]) -> bool:
    """A statistical quantity counts only when written to at least one decimal place (or as a 'p = 0.03' style
    value), so a rounded integer can't borrow an interval's end."""
    return printed[1] >= 1 and _matches(printed, candidates)


def rate_bound_values(k: int, n: int) -> list[float]:
    """A count's 95% bounds and their complements: the bound on the rate seen, and on the opposite rate ("12 of 12
    read correctly" bounds failures at 1 - lower bound, which is what the refusals and ``bound()`` print)."""
    lo, hi = stats.rate_bounds(k, n)
    return [lo, hi, 1 - lo, 1 - hi]


# a figure the statement itself says is a bound: "(95% upper bound 31%)", "at most 19% of the time", "no more than 4%"
_LABELLED_BOUND = re.compile(r"\b(?:(?:upper|lower)\s+(?:95\s*%\s+)?(?:confidence\s+)?(?:bound|limit)|at\s+most|"
                             r"at\s+least|no\s+more\s+than|no\s+less\s+than|bounded\s+(?:at|by))"
                             r"(?:\s+(?:of|is|at|was))?\s*[:=≈]?\s*(?:about\s+|around\s+|roughly\s+|~\s*)?"
                             r"(\d[\d,]*(?:\.\d+)?\s*%)", re.I)


def split_bounds(text: str) -> tuple[str, list[tuple]]:
    """(the text with each labelled bound's figure blanked, those figures as ``numbers`` gives them). Split by
    position, so a figure the statement labels as a bound vouches for nothing else that happens to print the same
    ("rose 31% ... (upper bound 31%)")."""
    out, labelled, i = [], [], 0
    for m in _LABELLED_BOUND.finditer(text or ""):
        out.append(text[i:m.start(1)] + " ")
        labelled += numbers(m.group(1))
        i = m.end(1)
    out.append((text or "")[i:])
    return "".join(out), labelled


def _matches_bound(printed: tuple, bounds: list[float]) -> bool:
    """A percentage the statement labels as a bound may match a count's 95% bound as printed, whole numbers too: the
    refusals and ``bound()`` print them that way ("95% upper bound 31%"), and a labelled bound borrows nothing.
    The decimal rule stays for unlabelled figures."""
    return printed[2] and _matches(printed, bounds)


def _bound(s: Snap, meas: list, stmt: str = "", words: bool = True) -> tuple[list[tuple[dict, dict]], list[Problem]]:
    """Measurements that check out against their results, and problems with the rest. With ``stmt``, the claim's
    statement: what a key says it counted must be said by the measurement's name or by the statement. ``words``
    False (a typed investigation): only the numbers are compared; names and keys aren't read for what was counted —
    the count's types say that."""
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
                if not _shows(float(rv[k]), float(m[k]), dec) and not (
                        rv[k] <= 1 < m[k] and _shows(float(rv[k]) * 100, float(m[k]), dec)):
                    problems.append(Problem("MEASUREMENT_MISMATCH", f"measurement {m.get('name') or i + 1}: says "
                                            f"{k}={m[k]} but result {m['result']} has {rv[k]}"))
                    bad = True
        if not words:
            if not bad:
                good.append((m, rv))
            continue
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
    """The parts of ``stmt`` that state one of ``figs`` and make the claim: what a count against that figure must be
    about is said there, not in another sentence. "Speed was recorded separately; no route is longer than 26 km" says
    nothing about speed where it says 26 km, so a speed count named "routes longer than 26 km" can't borrow the word
    (audit HG-026-01), nor can it when the other sentence repeats the 26 (HG-027-01). The whole statement when no part
    states one."""
    if not stmt or not figs:
        return stmt
    parts = [p for p in _SAYING.split(stmt) if p and p.strip()]
    hit = [p for p in parts if {round(v[0], 6) for v in numbers(p)} & {round(f, 6) for f in figs}]
    # of those, the parts that make a claim ("no route is longer than 26 km"), when any does: "speed was recorded
    # above 26" repeats the figure but claims nothing, so its words can't say what the count was of (audit HG-027-01)
    claims = [p for p in hit if L.ABSOLUTE.search(p) or L.SUPERLATIVE.search(p)]
    return " . ".join(_from_claim(p) for p in claims or hit) if hit else stmt


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
_COUNT_FIGURE = re.compile(r"\b(?:(?:" + L.CMP_WORDS + r"|(?!(?:" + L.NOT_CMP + r")\b)[a-z]{3,}er)\s+than|above|below|over|under|beyond|exceed\w*|surpass\w*|beat\w*)\s+\$?"
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


_KEY_FIGURE = re.compile(r"\b(?:" + L.CMP_WORDS + r"|above|below|over|under|beyond|exceed\w*|surpass\w*|beat\w*)"
                         r"(?:\s+than)?\s+"
                         r"(\d+(?:\.\d+)?)$", re.I)
# the figure an absolute names in its own clause: "nothing worth more than 93 fits", "no route is shorter than 26 km"
_CLAIM_FIGURE = re.compile(r"\b(?:" + L.CMP_WORDS + r"|(?!(?:" + L.NOT_CMP + r")\b)[a-z]{3,}er)\s+than\s+\$?"
                           r"(-?\d[\d,]*(?:\.\d+)?)|\b(?:" + L.CMP_PREPS + r"|" + L.CMP_VERBS + r")\s+\$?"
                           r"(-?\d[\d,]*(?:\.\d+)?)|\b(?:is|are|was|were)\s+(?:over|under)\s+\$?(-?\d[\d,]*(?:\.\d+)?)",
                           re.I)
# "over" / "under" right after the noun "no" opens: "no route under 41 km exists" (``CMP_PREPS``)
_CLAIM_OVER = re.compile(r"^\s*[a-z]+\s+(?:over|under)\s+\$?(-?\d[\d,]*(?:\.\d+)?)", re.I)
# a comparison with a figure the checks can't read ("no route is longer than the usual one"): what it compares is
# still read, so a count that compares nothing, or another way, can't back it (audit HG-027-02)
_UNREAD_CMP = re.compile(r"\b(?:(?:" + L.CMP_WORDS + r"|(?!(?:" + L.NOT_CMP + r")\b)[a-z]{3,}er)\s+than|"
                         + L.CMP_PREPS + r"|" + L.CMP_VERBS + r")\b", re.I)
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
    "": {1: "more greater higher larger bigger above over beyond exceed exceeds exceeding exceeded surpass surpasses "
            "surpassed surpassing most highest largest "
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


def _clause_comparisons(clause: str, after_no: bool = False) -> list[tuple[float, tuple[str, int, bool] | None]]:
    """(figure, comparison) for each comparison against a figure in a claim's clause: "longer than 26 km", "at least
    26", "26 km or longer", "no more than 93", "above 93", "exceeded 26"; None for one that points nowhere. With
    ``after_no``, the clause follows "no", and "over 26" / "under 26" after its noun compare too."""
    out = []
    hits = list(_CLAIM_FIGURE.finditer(clause)) + list(_CLAIM_OVER.finditer(clause) if after_no else [])
    for h in hits:
        neg = re.search(r"\b(?:not|no)\s+$", clause[:h.start()], re.I)      # "no more than 93" is at most 93
        num = next(g for g in h.groups() if g).replace(",", "")
        said = clause[neg.start() if neg else h.start():h.end()]
        said = said if h.re is _CLAIM_FIGURE else said[re.search(r"over|under", said, re.I).start():]
        out += [(float(num), c) for c in _comparisons_in(said) or {None}]
    for h in _CLAIM_BOUNDARY.finditer(clause):
        num = (h.group(1) or h.group(2)).replace(",", "")
        out += [(float(num), c) for c in _comparisons_in(h.group(0)) or {None}]
    return out


# a target group whose parts are joined by both "and" and "or" (``_target_groups``)
MIXED = (frozenset(), frozenset({("mixed", 0, False)}))

# "and" or "or" before a comparison with no subject of its own: "shorter than 20 km and longer than 30 km"
_JOINED = re.compile(r"\s+(?:also\s+)?(?:(?:not|no)\s+)?(?:" + _CMP + r"\s+than\b|at\s+(?:least|most)\b|"
                     r"(?:" + L.CMP_PREPS + r"|" + L.CMP_VERBS + r")\b)", re.I)


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
                   for fig, c in _clause_comparisons(clause, after_no=w.lower() == "no")]
        unread = _UNREAD_CMP.search(clause)
        if not targets and unread and (comps := _comparisons_in(unread.group(0))):
            targets = [(frozenset(), frozenset(_negated(c) if every else c for c in comps))]
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


def _role(m: dict, rv: dict, a: tuple[int, int], figs: set[float], comps: set, stmt: str = "",
          w: str = "") -> str | None:
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
        # "all 14 encodings": the set it counted, unless the statement names another kind ("all 14 binary encodings")
        covers = covers or (role == "back" and not apart and _pins_set(stmt, w, n, m))
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
        if (not cw or w in _DETERMINERS or w in _PREPOSITIONS or w in _DIRECTION_OF or w in _COUNTING | _HOW_MANY
                or _count_word(w) is not None):          # "all nine encodings": a number in words is a number too
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
    fits" used to end the check, and "the highest is 93" beside it went in unexamined (audit HG-021-02).

    An absolute over a set the sentence enumerates ("none of the 4 routes") isn't a generalisation past the sample, so
    it needs no count of its own; but a bound count that finds an exception still contradicts "none" or "neither"."""
    said = L.asserted(L.ABSOLUTE, stmt)
    enumerated = [w for w in said if _enumerated(stmt, w)]
    words = [w for w in said if w not in enumerated]
    # only "none" / "neither", which say nothing in the set is an exception: an enumerated "all" / "every" mostly names
    # the set a count ran over ("across all 1,024 selections, 2 fit and are worth more"), and claims nothing of it
    enumerated = [w for w in enumerated if w.lower() in ("none", "neither") and not _names_stated_count(stmt, w)]
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
    for w in enumerated:
        for figs, comps in _absolute_targets(stmt, w):
            out += [p for p in _absolute(stmt, scope, body, bound, w, enumerated, set(figs), set(comps))
                    if p.code == "COUNT_CONTRADICTS" and p.text() not in {q.text() for q in out}]
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _superlative_contradicted(stmt, bound)
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _all_but_contradicted(stmt, bound)
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _stated_count_contradicted(stmt, bound)
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _generic_contradicted(stmt, bound)
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _majority_at_half(stmt, bound)
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _majority_under_half(stmt, bound)
    if not any(p.code == "COUNT_CONTRADICTS" for p in out):
        out += _each_of_the_set(stmt, bound)
    return out


# Words that say more than half: "most files", "a majority of", "nearly all". Not "the most" / "at most" (a superlative,
# a bound), "most likely", or "most" before an -ly word ("most clearly")
_MAJORITY = re.compile(r"\b(?:(?:a|the)\s+majority\b|more\s+than\s+half\b|(?:nearly|almost|virtually|practically)\s+"
                       r"(?:all|every)\b|(?<!\bthe )(?<!\bat )most\b(?!\s+(?:likely|\w+ly)\b))", re.I)


def _majority_at_half(stmt: str, bound: list) -> list[Problem]:
    """'A majority', 'most', 'more than half' or 'nearly all' on a count of exactly half. Either side of a count may be
    the one the sentence means ("most settings lose" on 2 of 20 beating), so a majority word fits any count but an even
    split: there, neither side is more than half. Found in the say-no-more-than-the-data showcase run 3 (2026-11-15):
    "Parsed a majority of large files within the time budget" went in on 3 of 6. Across 3,030 existing records it was
    the only accepted statement with a majority word on a count at or under half."""
    arms = [(m, a) for m, rv in bound if (a := _arm(rv))]
    if not arms:
        return []
    about = L.content_words(stmt)
    for hit in _MAJORITY.finditer(stmt):
        if L.negated(stmt, hit.start()):
            continue
        rel = [(m, a) for m, a in arms if L.content_words(f"{m.get('name', '')} {m.get('key', '')}") & about] or arms
        if not all(2 * k == n for _m, (k, n) in rel):
            continue
        m, (k, n) = max(rel, key=lambda x: x[1][1])
        w = re.sub(r"\s+", " ", hit.group(0).lower())
        return [Problem("COUNT_CONTRADICTS",
                        f"'{w}' says more than half, but the record's own count is {k:,} of {n:,} "
                        f"({m.get('name') or m.get('key')}), an even split: say '{k:,} of {n:,}' or 'half'",
                        fix=f"say '{k:,} of {n:,}', or 'half'", words=[w])]
    return []


# What says a counted thing went the other way. "Most large files exceed time limits", on 2 of 7 files parsed within
# the time budget, speaks of the five that didn't and is true; so is "most suites ran without a crash" on 0 of 7 that
# crashed. A clause holding one of these, or a negation, may speak of the other side and is left alone
_CONTRARY = re.compile(
    r"\b(?:fail\w*|crash\w*|miss(?:ed|es|ing)?|slip(?:s|ped|ping)?|stumbl\w*|falter\w*|trip(?:s|ped|ping)?|broke|"
    r"break(?:s|ing)?|errored|struggl\w*|chok(?:e|es|ed|ing)|stall\w*|hang(?:s|ing)?|hung|lag(?:s|ged|ging)?|"
    r"tim(?:e[sd]?|ing)[\s-]?out|overr[au]n\w*|exceed\w*|slow\w*|late|later|longer|lose|los(?:es|ing|t)|behind|"
    r"(?:fell|falls?|falling)\s+short|short\s+of|too\s+(?:long|slow|big|large|heavy)|worse|poor\w*|stuck|"
    r"push(?:es|ed|ing)?\s+(?:the\s+|its\s+|their\s+)?limits?|over\s+(?:the\s+|its\s+)?(?:budget|limit|deadline)|"
    r"past\s+(?:the\s+|its\s+)?(?:budget|limit|deadline))\b", re.I)
_CONTRARY_NEG = re.compile(r"\b(?:not|no|never|without|cannot|unable|nor)\b|n't\b", re.I)


def _clause_at(text: str, start: int) -> str:
    """The clause of ``text`` the word at ``start`` sits in, as ``language.negated`` bounds it."""
    s0 = max((m.end() for m in L._SENTENCE_END.finditer(text[:start])), default=0)
    s1 = next((m.start() for m in L._SENTENCE_END.finditer(text, start)), len(text))
    c0 = max((m.end() for m in L._CLAUSE.finditer(text[:start], s0)), default=s0)
    c1 = next((m.start() for m in L._CLAUSE.finditer(text, start, s1)), s1)
    return text[c0:c1]


def _majority_under_half(stmt: str, bound: list) -> list[Problem]:
    """'Most', 'a majority of' or 'nearly all' of the counted set, said its own way, on a count under half. Either side
    of a count may be the one a sentence means, so a majority word fits a count under half when the clause speaks of
    the rest ("most large files exceed time limits" on 2 of 7 parsed in time). It doesn't when the clause says
    nothing contrary and doesn't negate: "We met deadlines on most large files" on 3 of 7 files over 1 GB parsed
    within the time budget went in twice in the telephone showcase's run3 (2026-11-16), blind-labelled false. The
    majority word has to sit on the counted set itself (up to four words before its plural, no preposition but "of"
    between), and a count whose own name is put the contrary way ("test suites in which the parser crashed") isn't
    read: there the plain clause is the other side. Across 3,757 records, 7 statements had a majority word on a
    count under half; this reads the two above and none of the other five."""
    arms = [(m, a) for m, rv in bound if (a := _arm(rv))]
    if not arms:
        return []
    for hit in _MAJORITY.finditer(stmt):
        if L.negated(stmt, hit.start()):
            continue
        noun = phrase = None
        words = list(re.finditer(r"[A-Za-z][\w‐‑'-]*", stmt[hit.end():]))[:5]
        for t in words:
            w = t.group(0).lower()
            if w in _PREPOSITIONS and w != "of":
                break
            if w.endswith("s") and not w.endswith(("ss", "us", "is", "'s")) and L.content_words(w):
                noun = L.content_words(w)
                phrase = re.sub(r"\s+", " ", stmt[hit.start():hit.end() + t.end()])
                break
        if not noun:
            continue
        rel = [(m, a) for m, a in arms if noun == _counted_noun(str(m.get("name") or ""))]
        if not rel or not all(2 * k < n for _m, (k, n) in rel):
            continue
        if any(_CONTRARY.search(str(m.get("name") or "")) or _CONTRARY_NEG.search(str(m.get("name") or ""))
               for m, _a in rel):
            continue
        clause = _clause_at(stmt, hit.start())
        if _CONTRARY.search(clause) or _CONTRARY_NEG.search(clause):
            continue
        m, (k, n) = max(rel, key=lambda x: x[1][1])
        q = _fitting_qualifier(k, n)
        return [Problem("COUNT_CONTRADICTS",
                        f"'{phrase}' says more than half of them did, but the record's own count is {k:,} of {n:,} "
                        f"({m.get('name') or m.get('key')}), under half, and nothing in the clause says it speaks of "
                        f"the other {n - k:,}: say '{k:,} of {n:,}', or '{q}'",
                        fix=f"say '{k:,} of {n:,}', or '{q}'", words=[phrase.lower()])]
    return []


_SMALL = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _all_but_contradicted(stmt: str, bound: list) -> list[Problem]:
    """"All but one file was flagged" states a count, n - 1 of n, not an absolute: held to the record's own count of
    what it's about. Either side of the count may be the one recorded (flagged k of n, or missed k of n), so it fits
    when the exceptions are N either way. "All but a few" names no number and is left as the hedge it is. Found in
    the say-no-more-than-the-data showcase (2026-11-15): a true "all but one" on 23 of 24 was refused as an absolute."""
    out: list[Problem] = []
    about = L.content_words(stmt)
    arms = [(m, a) for m, rv in bound if (a := _arm(rv))]
    for hit in L.ALL_BUT.finditer(stmt):
        if L.negated(stmt, hit.start()):
            continue
        word = re.sub(r"\s+", " ", hit.group(1).lower())
        N = _SMALL.get(word) if word in _SMALL else (int(word.replace(",", "")) if word[0].isdigit() else None)
        if N is None:
            continue
        rel = [(m, a) for m, a in arms if L.content_words(f"{m.get('name', '')} {m.get('key', '')}") & about] or arms
        if not rel:
            out.append(Problem("ABSOLUTE_WITHOUT_COUNT",
                               f"'all but {word}' states a count: back it with a k/n measurement of what it's about",
                               fix="bind the count, or say 'k of n'", words=[hit.group(0).lower()]))
            continue
        if any(N in (k, n - k) for _m, (k, n) in rel):
            continue
        m, (k, n) = max(rel, key=lambda x: x[1][1])
        out.append(Problem("COUNT_CONTRADICTS",
                           f"the statement says all but {word} ({n - N:,} of {n:,}), but the record's own count is "
                           f"{k:,} of {n:,} ({m.get('name') or m.get('key')}): correct it, or say '{k:,} of {n:,}'",
                           fix=f"correct the statement, or say '{k:,} of {n:,}'", words=[hit.group(0).lower()]))
    return out


# Anything that says how many, or hedges: a sentence holding one of these isn't a bare generic. "each" and "no" are
# not among them: neither says fewer than all ("Malformed files were caught, each flagged by a clear error", "Malformed
# files were cleanly rejected—no slip-through", both on 21 of 22). Over every blind-labelled telephone line
# (2026-11-17, 12,398 sentences), a sentence whose only such word was "each" or "no" was false 9 times and true 0;
# every true line with one of them also states a count or hedges another way ("21 of 22 … each with a clear error")
_QUALIFIES = re.compile(
    r"\d|%|\b(?:all|every|any|none|neither|either|both|most|many|some|several|few|fewer|majority|minority|"
    r"nearly|near|almost|virtually|practically|mostly|largely|broadly|generally|usually|typically|often|sometimes|"
    r"occasionally|rarely|seldom|frequently|mainly|predominantly|overwhelmingly|handful|couple|only|just|except|"
    r"but|apart|save|exceptions?|roughly|about|around|approximately|share|proportion|fraction|percent|rate|half|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozens?|hundreds?|thousands?|single)\b", re.I)
_GENERIC_CLAUSE = re.compile(r"\s*(?:[;:,|–—]|\s-\s)\s*")
# exceptions denied, not admitted: "no exceptions", "without exception", "zero exceptions"
_NO_EXCEPTIONS = re.compile(r"\b(?:no|zero|without(?:\s+(?:a|an|any))?)\s+(?:single\s+)?exceptions?\b", re.I)
_NAME_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _says_how_many(text: str, arms: list) -> bool:
    """Does anything in the text say how many of the counted set, or hedge? The guard of the bare-plural readings.
    Not read as saying so:
    - an "all" idiom ("solid coverage all around");
    - a number the count's own name holds, which says what was counted, not how many: "Large, over-1-GB files were
      parsed within the time budget" went in on 3 of 6 files over 1 GB parsed within the time budget (telephone
      showcase run4), where "Large files were parsed within the time budget" is refused. The count's k and n still
      say how many, whatever the name holds;
    - exceptions denied ("no exceptions", "without exception")."""
    text = _NO_EXCEPTIONS.sub(lambda m: " " * len(m.group(0)), L.without_idioms(text))
    own = set()
    for m, (k, n) in arms:
        own |= {x.replace(",", "") for x in _NAME_NUMBER.findall(str(m.get("name") or ""))} - {str(k), str(n)}
    if own:
        text = _NAME_NUMBER.sub(lambda m: " " * len(m.group(0)) if m.group(0).replace(",", "") in own else m.group(0),
                                text)
    return bool(_QUALIFIES.search(text))


def _plural_subject(clause: str) -> tuple[list[str], int | None]:
    """The clause's words and the index of its subject when that is a plural: the first word ending in -s among its
    first four, with something after it. None when that word isn't a plural noun ("class", "its", "parser's")."""
    toks = re.findall(r"[A-Za-z][\w‐‑'-]*", clause)
    i = next((j for j, t in enumerate(toks[:4]) if t.lower().endswith("s")), None)
    if i is None or i + 1 >= len(toks) or toks[i].lower().endswith(("ss", "us", "is", "'s")):
        return toks, None
    return toks, i


def _counted_noun(name: str) -> set[str]:
    """What a count's name counts, found as a statement's plural subject is: "malformed files rejected with a clear
    error" counts files, not errors."""
    toks, i = _plural_subject(name)
    return L.content_words(toks[i]) if i is not None else set()


# A count the statement states: "23 of 24", "23 out of the 24", and "all 24" / "all of the 24" / "each of the 24" /
# "every one of the 24" (N of N). Not "run 3 of 7" or "ranked 2 of 20" (a label or a rank), not "3 of 24%", not a
# decimal ("0.5 of 4")
# a count in words is read as one in digits, compounds whole: "twenty-four of twenty-four" (/play/ attack round,
# 2026-11-15, went in on 23 of 24 while "24 of 24" was refused)
_NUMW = (r"\d[\d,]*|(?:" + "|".join(_TENS) + r")[" + _HY + r"](?:" + "|".join(_UNITS) + r")(?![" + _HY + r"\w])|"
         + "|".join(sorted(set(_WORDS) | set(_TENS) | {"one"}, key=len, reverse=True)))
_STATED_OF = re.compile(rf"(?<![\w.,/-])({_NUMW})\s+(?:out\s+)?of\s+(?:the\s+|all\s+|all\s+the\s+)?({_NUMW})"
                        r"(?![\d,]*\.\d)(?![\w%])(?!\s*(?:%|percent|per\s?cent)\b)", re.I)
_STATED_ALL = re.compile(rf"(?<![\w-])(all|each|every\s+one)\s+(?:of\s+)?(?:the\s+|these\s+|those\s+)?({_NUMW})"
                         r"(?![\d,]*\.\d)(?![\w%])(?!\s*(?:%|percent|per\s?cent)\b)", re.I)
# "rejected malformed files 24/24": k/n written with a slash. Not a date or path ("11/15/2026", "a/b/c"), not a
# decimal or a percent, not a ratio of figures ("3.2/4")
_STATED_SLASH = re.compile(r"(?<![\w.,/-])(\d[\d,]*)\s?/\s?(\d[\d,]*)(?![\d,]*\.\d)(?![\w%/-])"
                           r"(?!\s*(?:%|percent|per\s?cent)\b)", re.I)


def _count_word(s: str) -> int | None:
    """A count as written, in digits or words up to ninety-nine: "24", "1,925", "nine", "twenty-four"."""
    s = s.lower()
    if s[0].isdigit():
        return int(s.replace(",", ""))
    if s in _SMALL or s in _WORDS or s in _TENS:
        return _SMALL.get(s) or _WORDS.get(s) or _TENS.get(s)
    tens, _, unit = re.split(r"([" + _HY + r"])", s, maxsplit=1) if re.search(r"[" + _HY + r"]", s) else (s, "", "")
    return _TENS[tens] + _UNITS[unit] if tens in _TENS and unit in _UNITS else None


# "all 14 encodings", "the nine encodings": a statement that gives the set's size says which set it is about
_SET_OF_N = re.compile(rf"(?<![\w-])(?:all|each\s+of|every\s+one\s+of|the)\s+(?:the\s+|these\s+|those\s+)?({_NUMW})"
                       r"(?![\d,]*\.\d)\s+([a-z][\w-]*(?:\s+[a-z][\w-]*){0,2})", re.I)


def _same_n_elsewhere(s: Snap, inv: str, m: dict, rv: dict) -> bool:
    """Does the investigation hold another count over the same n? Then a size names no one set: with 3 cargo routes
    and 3 passenger routes, "all 3 routes" could be either (audit HG-024-02)."""
    a = _arm(rv)
    if not a:
        return False
    for nid, node in s.nodes.items():
        if node.get("type") != "result" or node.get("inv") != inv:
            continue
        for key, v in ((node.get("body") or {}).get("values") or {}).items():
            if (nid, key) != (str(m.get("result")), str(m.get("key"))) and isinstance(v, dict) and \
                    (b := _arm(v)) and b[1] == a[1]:
                return True
    return False


# a word that reaches past a pinned set: "all 14 encodings and every other format", "so any encoding works"
_REACH = re.compile(r"(?<![\w-])(?:all|every|each|any|other)(?![\w-])", re.I)
_QUANTIFIER = re.compile(r"all|every|each|any|no|none|nothing|neither|both|nobody", re.I)
_FLOAT = re.compile(r"\b(?:are|were|is|was|have|had|been)\s+$", re.I)      # "the 14 encodings were all handled"


def _pins_set(stmt: str, w: str, n: int, m: dict) -> bool:
    """Is ``w`` said of the counted set, named by its size? "All 14 encodings handled flawlessly" on 14 of 14 "text
    encodings read correctly" is about those 14, though it leaves out "text": the telephone showcase (2026-11-16)
    refused it, and "All nine encodings…", "All ten encodings…", as a count of something else. In ``w``'s clause the
    size must be the count's n, a word of what was counted must follow it within three words, and nothing else in the
    clause may reach past the set ("all 14 encodings and every other format", "…, so any encoding works"). "Every
    tested encoding" doesn't pin the set: more than one kind may have been tested."""
    if not w or m.get("_same_n"):
        return False
    names = L.content_words(f"{m.get('name') or ''} {str(m.get('key') or '').replace('_', ' ')}")
    for clause in _CLAUSE.split(stmt):
        if not re.search(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", clause, re.I):
            continue
        pins = [h for h in _SET_OF_N.finditer(clause)
                if _count_word(h.group(1)) == n and L.content_words(h.group(2)) & names]
        # a quantifier must be the pin's own: "No route is longer than 26 km among the 3 routes" rules on every
        # route, whatever the 3 are (audit HG-024-02)
        own = re.compile(r"(?<![\w-])" + re.escape(w) + r"(?![\w-])", re.I)
        if _QUANTIFIER.fullmatch(w) and any(not any(h.start() <= q.start() < h.start(1) for h in pins)
                                            for q in own.finditer(clause)):
            continue
        if pins and not any(not any(h.start() <= q.start() < h.start(1) for h in pins)
                            and not (q.group(0).lower() == "all" and _FLOAT.search(clause[:q.start()]))
                            for q in _REACH.finditer(clause)):
            return True
    return False


_COUNT_LABEL = {"run", "runs", "trial", "fold", "round", "game", "page", "step", "day", "week", "month", "year", "chapter",
                "part", "item", "no", "number", "phase", "stage", "test", "case", "seed", "batch", "epoch", "iteration",
                "slide", "question", "level", "rank", "ranked", "ranks", "rated", "scored", "score", "position",
                "placed", "finished", "came", "seat", "row", "column", "section", "figure", "table", "volume", "issue",
                "episode", "season", "match", "heat", "lap", "leg", "wave", "arm", "group", "cohort", "site",
                "sample", "file", "image", "video", "frame", "split", "hop", "shard", "worker", "node", "box", "board"}
_MEMBER = {"is", "was", "are", "were", "be", "being", "been", "as", "becomes", "became", "remains"}
# "across all 24 files, 23 …": a preposition before "all N" makes it the set a count ran over, not a count of it
_SET_PREP = {"across", "over", "of", "in", "from", "among", "amongst", "for", "on", "through", "throughout", "under",
             "with", "at", "to", "between", "by", "after", "within", "into", "out", "per", "against", "than"}


def _stated_count_contradicted(stmt: str, bound: list) -> list[Problem]:
    """A count the statement states, held to the record's own count when its denominator is a bound count's n:
    "caught 24 of 24 malformed files" or "all 24 malformed files were rejected" on 23 of 24. Every number in it was
    accounted for (24 is the bound n), so nothing refused it. Either side of a count may be the one recorded (rejected
    23 of 24, or parsed without an error 1 of 24), so a stated k fits when it is k or n - k.

    Precision over recall; each exclusion below was a false refusal on the corpus of real records:
    - a stated k that is any other bound value, count or denominator ("66 of 400 rows overlap" beside 295 of 400
      correct, where 66 is the overlap count's n), and "N of N" on a bound plain total of N ("46 of 46 lines");
    - a sentence that also states the record's count of that n ("2 of the 20 beat it (0 of 20 lagged)", or a critic
      quoting "990 of 1000" against the measured 781 of 1000);
    - two different counts over one n (A right on 812 of 950, B on 779): "950 of 950 item ids are unique";
    - a total kept as a count (1,564 of 1,564 users): "311 of 1564 users" is a part of it. So understatement against
      an n-of-n count isn't caught;
    - membership ("it is one of 20 settings"), labels and ranks ("run 3 of 7"), negation ("not all 24").
    "all N" counts only when no preposition makes it the set ("across all 24 files") and the sentence states no other
    count of that n. Found by the /play/ challenges (2026-11-15): on 23 of 24, "All 24 malformed files were rejected"
    and "The parser caught 24 of 24 malformed files" went in."""
    arms = [(m, a) for m, rv in bound if (a := _arm(rv))]
    if not arms:
        return []
    # every bound number a stated k could be about instead: each count's k, n - k and n ("66 of 400 rows overlap"
    # is the n of the overlap-accuracy count, not a wrong 295 of 400), and each plain value
    others: set[float] = {float(x) for _m, (k, n) in arms for x in (k, n - k, n)}
    plain: set[float] = set()
    for _m, rv in bound:
        v = rv.get("value")
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            plain.add(float(v))
    others |= plain

    num = _count_word

    def before(i: int) -> str:
        # the word just before, with only space between: in "154 users per arm; 22/154 in A" the 22 is no arm label
        w = re.search(r"([\w.]+)\s*$", stmt[:i])
        return w.group(1).lower().rstrip(".") if w else ""

    stated: list[tuple[int, int, str, int]] = []           # (k, n, the words, where)
    for hit in _STATED_OF.finditer(stmt):
        k_, n_ = num(hit.group(1)), num(hit.group(2))
        # "every one of the 24" is N of N (below), not 1 of 24
        # "it is one of 20 settings tested" says which set a thing belongs to, not how many did something
        if k_ is not None and n_ and before(hit.start()) not in _COUNT_LABEL | _MEMBER | {"every", "each", "any"}:
            stated.append((k_, n_, re.sub(r"\s+", " ", hit.group(0)), hit.start()))
    for hit in _STATED_SLASH.finditer(stmt):
        k_, n_ = num(hit.group(1)), num(hit.group(2))
        if k_ is not None and n_ and k_ <= n_ and before(hit.start()) not in _COUNT_LABEL | _MEMBER:
            stated.append((k_, n_, re.sub(r"\s+", "", hit.group(0)), hit.start()))
    for hit in _STATED_ALL.finditer(stmt):
        n_ = num(hit.group(2))
        if not n_ or before(hit.start()) in _SET_PREP:
            continue
        # "all 24 files were run; 23 were rejected" names the set: the sentence states the count elsewhere
        rest = stmt[:hit.start()] + " " + stmt[hit.end():]
        said = {num(x) for x in re.findall(rf"(?<![\w.,/-])(?:{_NUMW})(?![\w%])(?![\d,]*\.\d)", rest, re.I)}
        if any(n == n_ and said & {k, n - k} - {n} for _m, (k, n) in arms):
            continue
        stated.append((n_, n_, re.sub(r"\s+", " ", hit.group(0)), hit.start()))
    # a sentence that states the record's count of an n elsewhere ("2 of the 20 beat it (0 of 20 lagged)") is
    # counting something else in its other counts of that n
    named = {n_ for k_, n_, _w, _a in stated
             if any(n == n_ and k_ in (k, n - k) for _m, (k, n) in arms)}
    out: list[Problem] = []
    for k_, n_, words, at in stated:
        if n_ in named or L.negated(stmt, at):
            continue
        rel = [(m, (k, n)) for m, (k, n) in arms if n == n_]
        if not rel or any(k_ in (k, n - k) for _m, (k, n) in rel):
            continue
        # a total kept as a count ("n users with feature" 1,564 of 1,564): "311 of 1564 users converted" is a part of
        # it, not a contradiction. Only a count with an exception (k < n) is held against the sentence
        if all(k == n for _m, (k, n) in rel):
            continue
        # two different counts over one n (A right on 812 of 950, B on 779): the n is a population several things
        # are counted on, and "950 of 950 item ids are unique" may be yet another
        if len({frozenset((k, n - k)) for _m, (k, n) in rel}) > 1:
            continue
        if k_ != n_ and float(k_) in others:                # a count of something else bound beside it
            continue
        if k_ == n_ and float(n_) in plain:                 # "46 of 46 lines" restates a bound total of 46
            continue
        m, (k, n) = rel[0]
        out.append(Problem("COUNT_CONTRADICTS",
                           f"'{words}' says {k_:,} of {n_:,}, but the record's own count is {k:,} of {n:,} "
                           f"({m.get('name') or m.get('key')}): correct it, or say '{k:,} of {n:,}'",
                           fix=f"correct the statement, or say '{k:,} of {n:,}'", words=[words.lower()]))
        break
    return out


# "each" as the counted set's own determiner: "each malformed file", "each one"; not "each other"
_EACH = re.compile(r"\beach\b(?!\s+other\b)", re.I)


def _each_of_the_set(stmt: str, bound: list) -> list[Problem]:
    """'Each' on the counted set, with nothing to say how many: "The parser flagged each malformed file" on 19 of 20,
    "Malformed files? Each one triggered a crystal-clear error alert" on 23 of 24. Says it of every one, as "every
    malformed file" (refused) does. Found in the telephone showcase (2026-11-17).

    Most "each" is distributive and honest: "rejected nearly every bad file, each with a clear error" (each of those
    rejected), "four of six large files (each over 1 GB)", "11 trades, each incurring a 0.1% fee", "each widow was paid
    four shillings" (2026-11-17: reading "each" as "every" refused 193 items of the corpus of real records, nearly all
    of this kind). So it is read only as the determiner of the counted set itself ("each" + up to three words + the
    counted noun, singular or plural; or "each one" with the set named earlier in the sentence), on a count with
    exceptions, and only when nothing else in the sentence says how many or hedges (the bare-plural rule's guard)."""
    arms = [(m, a) for m, rv in bound if (a := _arm(rv)) and 0 < a[0] < a[1]]
    if not arms:
        return []
    for hit in _EACH.finditer(stmt):
        if L.negated(stmt, hit.start()):
            continue
        s0 = max((m.end() for m in L._SENTENCE_END.finditer(stmt[:hit.start()])), default=0)
        e = L._SENTENCE_END.search(stmt, hit.end())
        s1 = e.start() if e else len(stmt)
        after = list(re.finditer(r"[A-Za-z][\w\u2010\u2011'-]*", stmt[hit.end():s1]))[:4]
        hits, end = [], None
        if after and after[0].group(0).lower() == "one":
            # "each one": the set named just before it, in the sentence or a question it answers ("Malformed
            # files? Each one triggered a clear error")
            q0 = s0
            if s0 and stmt[:s0].rstrip().endswith("?"):
                q0 = max((m.end() for m in L._SENTENCE_END.finditer(stmt[:s0].rstrip()[:-1])), default=0)
            named = {frozenset(L.content_words(t)) for t in re.findall(r"[A-Za-z][\w\u2010\u2011'-]*",
                                                                       stmt[q0:hit.start()])} - {frozenset()}
            hits = [(m, a) for m, a in arms if frozenset(_counted_noun(str(m.get("name") or ""))) in named]
            end = hit.end() + after[0].end()
        else:
            for t in after:
                w = t.group(0).lower()
                if w in _PREPOSITIONS or w in {"and", "or", "but", "with", "was", "were", "is", "are"}:
                    break
                cw = L.content_words(w)
                hits = [(m, a) for m, a in arms if cw and cw == _counted_noun(str(m.get("name") or ""))]
                if hits:
                    end = hit.end() + t.end()
                    break
        if not hits:
            continue
        rest = stmt[s0:hit.start()] + " " + stmt[end:s1]
        if _says_how_many(rest, hits):
            continue
        phrase = re.sub(r"\s+", " ", stmt[hit.start():end])
        m, (k, n) = max(hits, key=lambda x: x[1][1])
        q = _fitting_qualifier(k, n)
        return [Problem("COUNT_CONTRADICTS",
                        f"'{phrase}' with nothing to say how many reads as every one of them, but the record's own "
                        f"count is {k:,} of {n:,} ({m.get('name') or m.get('key')}): say '{k:,} of {n:,}', or "
                        f"qualify it ('{q}')",
                        fix=f"say '{k:,} of {n:,}', or '{q}'", words=[phrase.lower()])]
    return []


def _generic_contradicted(stmt: str, bound: list) -> list[Problem]:
    """A bare plural that is what the bound count counts ("Malformed files rejected with clear errors", on 23 of 24
    malformed files rejected with a clear error) says it of every one, as "every malformed file was rejected" does.
    Refused when the count is mixed (0 < k < n) and nothing in the sentence says how many or hedges: no number, no
    quantifier, no exception (`_says_how_many`). Found in the say-no-more-than-the-data showcase (2026-11-15), where
    ten such headlines went in on counts with exceptions while "every malformed file rejected" on the same counts was
    refused, and no true headline had this shape. The subject is the first plural in the first four words of a
    clause; a verb ending in -s before it ("the parser handles files") means it isn't the subject."""
    arms = [(m, a) for m, rv in bound if (a := _arm(rv)) and 0 < a[0] < a[1]]
    if not arms or _says_how_many(stmt, arms):
        return []
    for clause in _GENERIC_CLAUSE.split(stmt):
        toks, i = _plural_subject(clause)
        head = L.content_words(toks[i]) if i is not None else set()
        hits = [(m, a) for m, a in arms if head and head == _counted_noun(str(m.get("name") or ""))]
        if not hits:
            got = _object_generic(clause, arms)
            if got:
                i, hits = got
        if not hits:
            continue
        m, (k, n) = max(hits, key=lambda x: x[1][1])
        phrase = " ".join(toks[:i + 1])
        q = _fitting_qualifier(k, n)
        return [Problem("COUNT_CONTRADICTS",
                        f"'{phrase}' with nothing to say how many reads as every one of them, but the record's own "
                        f"count is {k:,} of {n:,} ({m.get('name') or m.get('key')}): say '{k:,} of {n:,}', or "
                        f"qualify it ('{q}')",
                        fix=f"say '{k:,} of {n:,}', or '{q}'", words=[phrase.lower()])]
    return []


# verbs that say every one of a set was beaten or mastered: "smashed test suites", "conquers real-world files"
_MASTERY = set().union(*(L.content_words(w) for w in (
    "conquer conquered conquers dominate dominated dominates smash smashed smashes crush crushed crushes ace aced aces "
    "nail nailed nails master mastered masters sweep swept sweeps reign reigned reigns triumph triumphed triumphs "
    "breeze breezed breezes sail sailed sails blitz blitzed demolish demolished demolishes").split()))
# a preposition a deed may take before its set: "reigned supreme in test suites", "sailed through test suites"
_DEED_PREP = {"in", "through", "across", "over", "on"}
_OBJ_NEGATED = re.compile(r"\b(?:not|never|no\s+longer|cannot|fail(?:s|ed)?\s+to|without)\b|n't\b", re.I)


def _object_generic(clause: str, arms: list) -> tuple[int, list] | None:
    """The counted set as the bare plural object of a deed: the count's own verb ("Parser rejects malformed files", on
    24 of 25 malformed files rejected) or one of mastery ("Our parser smashed test suites", on 9 of 10 test suites
    passed; "reigned supreme in test suites"). Said of every one, as the bare plural subject is. Up to four words may
    come between the deed and the set, none of them a preposition other than in / through / across / over / on.
    Other verbs aren't read: "accuracy was measured on overlap rows" says nothing of how many. Found in the telephone
    showcase on merged main (2026-11-16): 9 of the 20 false lines that went in had this shape."""
    toks = re.findall(r"[A-Za-z][\w‐‑'-]*", clause)
    for j, t in enumerate(toks):
        if not t.lower().endswith("s") or t.lower().endswith(("ss", "us", "is", "'s")):
            continue
        noun = L.content_words(t)
        hits = [(m, a) for m, a in arms if noun and noun == _counted_noun(str(m.get("name") or ""))]
        if not hits:
            continue
        deeds = _MASTERY | set().union(*(_count_deed(str(m.get("name") or "")) for m, _a in hits))
        for v in range(j - 1, max(-1, j - 6), -1):
            w = toks[v].lower()
            if w in _PREPOSITIONS and w not in _DEED_PREP:
                break
            if L.content_words(w) & deeds:
                return None if _OBJ_NEGATED.search(" ".join(toks[:j])) else (j, hits)
    return None


_IRREGULAR_DEEDS = set("read run won built done found made sent kept met caught held beat beaten".split())


def _count_deed(name: str) -> set[str]:
    """The verb a count's name says was done to what it counts: "malformed files rejected with a clear error" gives
    {reject}, "test suites passed" {pass}, "text encodings read correctly" {read}."""
    toks, i = _plural_subject(name)
    if i is None:
        return set()
    return set().union(*(L.content_words(w) for w in toks[i + 1:]
                         if w.lower().endswith("ed") or w.lower() in _IRREGULAR_DEEDS))


def _fitting_qualifier(k: int, n: int) -> str:
    """A word for k of n that is true of it. The refusal used to offer 'nearly all' or 'most' whatever the count, and
    on 3 of 6 the rewrite said "a majority", which half is not (say-no-more-than-the-data showcase run 3,
    2026-11-15)."""
    f = k / n
    return ("nearly all" if f >= 0.9 else "most" if f > 0.5 else "half" if 2 * k == n else
            "fewer than half" if f >= 0.1 else "a few")


def _absolute(stmt: str, scope: str, body: dict, bound: list, w: str, words: list, figs: set[float],
              comps: set = frozenset()) -> list[Problem]:
    arms = [(m, rv, a, role) for m, rv in bound
            if (a := _arm(rv)) and (role := _role(m, rv, a, figs, comps, stmt, w))]
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
        # a count bound with the claim that isn't read as about what it says: name it, or a writer who never saw the
        # table can't tell the record holds "14 of 14 text encodings read correctly" for "every encoding" (telephone
        # showcase, 2026-11-15: hops three retellings from the table guessed "all 10 encodings" until they gave up)
        unfit = [(m, a) for m, rv in bound if (a := _arm(rv)) and not any(m is x[0] for x in arms)]
        named = "; ".join(f"{k:,} of {n:,} {m.get('name') or m.get('key')}" for m, (k, n) in unfit[:3])
        return [Problem("ABSOLUTE_WITHOUT_COUNT",
                        f"'{w}' is absolute: back it with a k/n measurement of what it's about, where k is 0 or n, and "
                        "keep the scope to the trials actually run — or say 'rarely' / 'in k of n'"
                        + (f" (what was measured: {seen})" if seen else "")
                        + (f". The count bound with it ({named}) isn't read as about what the statement says: name "
                           "what it counts as the count does, or state it ('in k of n')" if named and not seen else ""),
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
    as an absolute, the record refused that honest correction as the lie said again.)

    A word of proof names no set, and a count with exceptions proves no absolute: "Parser nailed 7 of 8 tests, proving
    solid coverage" went into the record on 7 of 8 (telephone showcase, live, 2026-11-16). On a count of 0 or n it
    still names the trials it rests on ("12 of 12 encodings parsed, proving it handles the formats we checked")."""
    arms = {a for _m, rv in bound if (a := _arm(rv))}
    if _PROOF_WORD.fullmatch(w):
        arms = {(k, n) for k, n in arms if k in (0, n)}
    return _names_stated_count(stmt, w, arms)


_PROOF_WORD = re.compile(r"prov(?:es?|en|ing)|proof|guarantee[sd]?|certainly|definitively|conclusively|undeniably",
                         re.I)


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


# an adverb between the copula and its negation: "the highest ... is therefore not 125"
_ADVERB = r"(?:(?:therefore|thus|hence|then|so|also|still|\w+ly)\s+)?"
# the extreme's own predicate denied after it, in its clause: "the highest total value ... is not 130"
_DENIED_EXTREME = re.compile(r"\b(?:is|are|was|were)\s+" + _ADVERB + r"(?:not|no longer|never)\b|"
                             r"\b(?:isn't|aren't|wasn't|weren't)\b|"
                             # or said to lie beyond a figure: "the true maximum is higher than 98"
                             r"\b(?:is|are|was|were|lies)\s+(?:\w+\s+)?(?:higher|lower|greater|larger|smaller|more|less|"
                             r"above|below|over|under|shorter|longer|beyond)\b", re.I)
# or denied before it: "120 is not the highest total value", "isn't the shortest"
_DENIED_BEFORE = re.compile(r"(?:\b(?:is|are|was|were)\s+" + _ADVERB + r"(?:not|no longer|never)|"
                            r"\b(?:isn't|aren't|wasn't|weren't))"
                            r"\s+(?:the\s+|a\s+|an\s+)?(?:true\s+|real\s+|actual\s+)?$", re.I)
_COPULA = re.compile(r"\b(?:is|are|was|were|isn't|aren't|wasn't|weren't|lies)\b", re.I)


def _denied(after: str, w: str = "") -> bool:
    """Does the extreme's own predicate — the first copula after it — deny it or put it beyond a figure? Only that
    one: "the highest value is 98 ..., so the true maximum is higher" still claims 98. A bound in the extreme's own
    direction is beyond its figure too: "the highest value is at least 91" (or "91 or more") says the true maximum is
    91 or above, which what lies beyond 91 doesn't contradict; "the highest is at most 91" still claims a figure."""
    cop = _COPULA.search(after)
    if not cop:
        return False
    if _DENIED_EXTREME.match(after, cop.start()):
        return True
    own = {s for _a, s, _strict in _comparisons_in(w)}
    pred = after[cop.end():].split(",")[0]
    return bool(own) and any(not strict and s in own for _a, s, strict in _comparisons_in(pred))


# a count named for what lies beyond a figure ("fitting selections worth more", "shorter routes connecting") is about
# any extreme the statement claims, whatever words the statement uses for it ("the highest total value is 99")
_BEYOND = re.compile(r"\b(?:" + L.CMP_WORDS + r"|above|below|beyond|exceed\w*|surpass\w*|beat\w*)\b", re.I)


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
            if (not _denied(stmt[m.end():end], w) and not _DENIED_BEFORE.search(stmt[start:m.start()])
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
    if not said and _PROOF_WORD.fullmatch(w) and (k, n) in {(int(a.replace(",", "")), int(b.replace(",", "")))
                                                             for a, b in _STATED_COUNT.findall(stmt)}:
        # the count is already said: what's false is the proof drawn from it ("nailed 7 of 8 tests, proving…")
        return Problem("COUNT_CONTRADICTS",
                       f"'{w}' draws a proof from {k:,} of {n:,} ({m.get('name') or m.get('key')}): a count with "
                       f"exceptions proves no absolute. Keep the count and drop '{w}', or say what the count does "
                       "show ('most', 'in this run')",
                       fix=f"keep '{k:,} of {n:,}' and drop '{w}'",
                       words=words + [f"={_fmt(v)}" for v in _subject_numbers(stmt, k, n)])
    head = (f"the statement says {said[0]:,} of {n:,}, but the record's own count is {k:,} of {n:,}" if said
            else f"'{w if w in sup else sup[0] if sup else w}' is contradicted by the record's own count: {k:,} of {n:,}")
    return Problem("COUNT_CONTRADICTS",
                   f"{head} ({m.get('name') or m.get('key')}). The exceptions the statement rules out were "
                   f"counted, so it is false as written: correct it, or say '{k:,} of {n:,}'",
                   fix=f"correct the statement, or say '{k:,} of {n:,}'",
                   words=words + [f"={_fmt(v)}" for v in _subject_numbers(stmt, k, n)])


_THAN_FIGURE = re.compile(r"\bthan\s+\$?(-?\d[\d,]*(?:\.\d+)?)", re.I)


def _qualified(stmt: str, k: int, n: int, figs: frozenset = frozenset(), rv: dict | None = None) -> bool:
    """Does the statement give this count about a figure of its own ("1 of 61 routes are shorter than 26 km")?
    Then it's a count of something beyond that figure, not of exceptions to the extreme it claims. Not when the
    figure is the extreme's own: "the shortest route is 30 km, since 1 of 77 are shorter than 30 km" states the very
    count that shows it false, and quoting the counterexample doesn't make an extreme true."""
    if figs and rv is not None and stated_figure(rv) in figs:
        return False
    forms = {f"{k} of {n}", f"{k:,} of {n:,}"}
    for c in _CLAUSE.split(stmt):
        if any(f in c for f in forms) and re.search(r"\bthan\b", c):
            said = {float(x.replace(",", "")) for x in _THAN_FIGURE.findall(c)}
            if not (said & set(figs)):
                return True
    return False


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
               and not (role == "refute" and _qualified(stmt, *a, figs, rv))]
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
            if _denied(after, w) or _DENIED_BEFORE.search(stmt[start:m.start()]):
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
    corrected (refusals.conduct reads them to tell a correction from the same claim said again). Only figures it
    asserts (``asserted_figures``): in "the shortest route is 40 km, not 38 km" or "... is 31 km, since the true total
    exceeds 30 km" the lie is 40 or 31. Storing 38 or 30 with it meant the same sentence said again never counted as a
    repeat, because a repeat must assert every stored figure and refusals.carried never counts a denied or compared
    one as asserted. A statement whose every figure is denied or compared keeps them all."""
    said = asserted_figures(stmt) or {v for v, *_ in numbers(stmt)}
    return [v for v, *_ in numbers(stmt) if v not in (0, k, n) and v in said]


# a figure the statement doesn't assert but denies or compares against: "not 38", "isn't 38", "instead of 38",
# "than 26", "exceeds 30", "above 90" (refusals.carried reads statements through the same pattern)
NOT_ASSERTED = re.compile(r"(?:\b(?:not|never|than|above|below|over|under|beyond|exceed(?:s|ing|ed)?|except|"
                          r"instead\s+of)|n't)\s+(?:about\s+|around\s+|roughly\s+)?\$?\d[\d,]*(?:\.\d+)?", re.I)


def asserted_figures(stmt: str) -> set[float]:
    """The figures a statement asserts: every number it gives, less those it denies or compares against."""
    return {v for v, *_ in numbers(NOT_ASSERTED.sub(" ", stmt or ""))}


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


# a word that opens what follows the denied word rather than continuing it: "does not specify after how many days"
# denies specifying, not "after"
_OPENS = set("""after before about above below across against along among around behind beneath beside between
beyond during except inside outside since through throughout toward towards until unless upon whether while within""".split())


def denied_words(stmt: str) -> set[str]:
    """Content words (stemmed, as language.content_words) that the statement explicitly denies: the word after the
    negation, and the next one unless it opens a phrase of its own. (Found in the who's-hallucinating showcase run 1,
    2026-11-15: an honest "the handbook does not specify after how many days a password must be changed", citing a
    passage with "27 days after 5 years of service", was refused as denying 'after', three times, and the record called
    its author one who said a contradicted claim again.)"""
    out: set[str] = set()
    for m in _DENIAL.finditer(stmt or ""):
        words = m.group(1).split()
        if len(words) == 2 and words[1].lower() in _OPENS:
            words = words[:1]
        out |= L.content_words(" ".join(words))
    return out


# a figure a statement denies: "12 km long, not 10 km", "isn't 10 km", "rather than 10 km", "instead of 10 km" (a
# comparison, "more than 10 km", denies nothing)
_DENIED_FIGURE = re.compile(r"(?:\bnot\b|n't\b|\brather\s+than\b|\binstead\s+of\b)\s+(?:about\s+|around\s+|roughly\s+)?"
                            r"\$?(\d[\d,]*(?:\.\d+)?)(?:\s*(%|[A-Za-z]+))?", re.I)
_SENTENCE = re.compile(r"(?<=[.!?;])\s+")
# "200 patients, not 250 as planned": the denied figure is a plan or an expectation the source may well give, not what
# the statement says the source got wrong
_AS_PLANNED = re.compile(r"\s*(?:[A-Za-z%]+\s+)?(?:as|than)\s+(?:originally\s+|first\s+|initially\s+)?(?:planned|expected|"
                         r"intended|forecast|predicted|projected|targeted|budgeted|hoped|anticipated|scheduled|"
                         r"proposed|designed|specified|required)\b", re.I)


def denied_figures(stmt: str) -> list[tuple[float, str, set[str]]]:
    """(value, unit or '', the content words of its sentence) for each figure the statement explicitly denies."""
    out = []
    for sent in _SENTENCE.split(stmt or ""):
        for m in _DENIED_FIGURE.finditer(sent):
            if _AS_PLANNED.match(sent, m.end(1)):
                continue
            unit = (m.group(2) or "").lower()
            if unit in L.STOP:
                unit = ""
            out.append((float(m.group(1).replace(",", "")), unit, L.content_words(sent) - L.content_words(unit)))
    return out


def _figure_affirmed_in(passage: str, value: float, unit: str, about: set[str]) -> str:
    """The sentence of ``passage`` that gives this figure (in this unit, when the statement named one) outside the
    reach of any negation, about what the statement's sentence is about (two content words shared), or ''."""
    for sent in _SENTENCE.split(passage or ""):
        un = _unnegated(sent)
        for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)(?:\s*(%|[A-Za-z]+))?", un):
            if abs(float(m.group(1).replace(",", "")) - value) > 1e-9:
                continue
            if unit and (m.group(2) or "").lower() != unit:
                continue
            if len(L.content_words(un) & about) >= 2:
                return sent.strip()
    return ""


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
    denied, doubted, figs = denied_words(stmt), doubted_words(stmt), denied_figures(stmt)
    if not denied and not doubted and not figs and not _unit_assertions(stmt):
        return []
    for src in support:
        n = s.nodes.get(src)
        if not n or n["type"] != "source":
            continue
        passage = str(n["body"].get("passage") or "")
        # found in the spot-the-bad-actor showcase run 2 (gpt-oss-20b, 2026-11-15): a paid critic's "the Nusk-Corlune
        # road is actually 12 km long, not 10 km as the register indicates", linking as support the register item that
        # gives it as 10 km, was accepted — the denial check read words and units, not figures
        for value, unit, about in figs:
            sent = _figure_affirmed_in(passage, value, unit, about)
            if sent:
                cite = str(n["body"].get("citation") or "").strip()
                label = cite[:80] if cite else (n.get("code") or src)
                said = f"{_fmt(value)} {unit}".strip()
                return [Problem("SOURCE_CONTRADICTS",
                                f"the statement denies {said}, but a source it links as support ({label}) gives that "
                                f"figure: \"{sent[:200]}\". A source that says the opposite isn't support: correct the "
                                "statement, or link the source as a challenge",
                                fix="correct the statement, or link that source as a challenge",
                                words=[f"denied:{_fmt(value)}"])]
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


def _round_figure(v: float) -> bool:
    """One significant digit: 0.05, 0.001, 5e-5, 1e-20 — how a threshold is written, unlike a measured 0.1531."""
    if v <= 0:
        return False
    m = v / 10 ** math.floor(math.log10(v))
    return abs(m - round(m)) < 1e-9


def _blank_p_thresholds(text: str, ps: list[float]) -> str:
    """The text with each p-value threshold blanked that a bound p-value is on the stated side of: "p < 0.001" when
    a bound p is 1.2e-5, "p > 0.05" when one is 0.2. A threshold no bound p-value meets is left to be accounted for
    like any figure. Main accepted "p < 0.001" only when the bound p times 100 happened to round to 0.001."""
    out, i = [], 0
    for m in _P_THRESHOLD.finditer(text):
        n = _NUM.match(text, m.end())
        if not n or not ps:
            continue
        v, op = _printed(n)[0], m.group(1)
        if not _round_figure(v):                    # "p >= 0.1531" states a figure, which needs binding like any
            continue
        below, strict = op in ("<", "<=", "=<", "≤"), op in ("<", ">")
        if any((p < v if strict else p <= v) if below else (p > v if strict else p >= v) for p in ps):
            out.append(text[i:n.start()] + " " * (n.end() - n.start()))
            i = n.end()
    out.append(text[i:])
    return "".join(out)


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


def _thresholds(stmt: str, comp: list[str]) -> set[str]:
    """Comparison words that only ever compare with a figure inside an absolute: "no route exceeds 26 km" rules out
    routes past 26, which the absolute check settles with a count; it doesn't compare two measured things."""
    if not L.asserted(L.ABSOLUTE, stmt):
        return set()
    return {w for w in comp if all(re.match(r"\s+\$?\d", stmt[h.end():])
                                   for h in re.finditer(r"\b" + re.escape(w) + r"\b", stmt, re.I))}


# A comparison between two bound measurements that the measurements reverse: "model A's accuracy of 81% is higher
# than model B's 84%", "a net return of 11.6% …, outperforming the buy-and-hold benchmark of 12.5%" (accepted from
# both the pitching and the honest seat in the backtest-bragging showcase, 2026-11-15: COMPARATIVE_WITHOUT_COMPARISON
# only counted the sides, never their order). Read narrowly, so it refuses only what it can see: the figure just
# after the comparison word and the nearest figure of the same kind (a percentage, or not) before it, in one clause,
# each matching a bound measurement's value. Words of size ("higher than", "exceeds") compare the values as they
# are; words of merit ("outperforms", "beats", "better than") only where both measurements' keys say which way is
# better (a return or an accuracy up, an error or a cost down). Anything else is left alone: a difference or a
# multiple before the word ("3 points higher than", "twice"), a threshold ("rose to more than"), a negation ("does
# not exceed"), another comparison in between, a figure no measurement gives.
_SIZE = {"higher": 1, "greater": 1, "larger": 1, "bigger": 1, "more": 1,
         "lower": -1, "smaller": -1, "less": -1, "fewer": -1}
_MERIT = {"better": 1, "worse": -1, "outperform": 1, "outperforms": 1, "outperformed": 1, "outperforming": 1,
          "underperform": -1, "underperforms": -1, "underperformed": -1, "underperforming": -1,
          "beat": 1, "beats": 1, "beating": 1}
_ORDER_WORD = re.compile(r"\b(?:(" + "|".join(_SIZE) + r"|better|worse)\s+than|(exceed(?:s|ed|ing)?|"
                         r"surpass(?:es|ed|ing)?)|(outperform(?:s|ed|ing)?|underperform(?:s|ed|ing)?|beat(?:s|ing)?))"
                         r"\b", re.I)
_CLAUSE_END = re.compile(r"[;:!?—]|\s–\s|\.(?!\d)|(?<![\w‐‑-])(?:and|but|while|whereas|although|though|yet|versus|vs)(?![\w‐‑-])", re.I)
_NOT_A_SIDE = set("not no never nor neither none to of by at with from in for into on onto toward towards reach "
                  "reaches reached reaching rose rise rises risen fell fall falls grew grow grows dropped drop drops "
                  "increased decreased climbed jumped the a an any".split())
_SCALING = set("times fold x twice double triple half halves third thirds quarter quarters point points pp "
               "percentage".split())
_HIGHER_GOOD = set("return returns accuracy acc profit profits score scores revenue gain gains precision recall f1 auc "
                   "sharpe sortino yield win wins winrate pass passed passes throughput".split())
_LOWER_GOOD = set("error errors err loss losses cost costs latency drawdown fee fees runtime delay regret mse rmse mae "
                  "perplexity slippage".split())


def _better_way(m: dict) -> int | None:
    """+1 when the measurement's key says more is better (a return, an accuracy), -1 when it says less is (an error,
    a cost), None when it doesn't say or says both ("return_after_fees"). The name is read only when the key is
    silent."""
    for text in (str(m.get("key") or ""), str(m.get("name") or "")):
        toks = set(re.split(r"[^a-z0-9]+", text.lower()))
        up, down = bool(toks & _HIGHER_GOOD), bool(toks & _LOWER_GOOD)
        if up or down:
            return None if up and down else (1 if up else -1)
    return None


def _sides(printed: tuple, bound: list) -> list[tuple[float, int | None]]:
    """(value, which way is better) for each bound measurement whose value the printed figure matches, scaled as
    printed (0.84 printed as 84% is 84). A figure printed without a minus sign doesn't match a negative value: "a
    net loss of 4.66% is less than buy-and-hold's loss of 56.73%" compares sizes of losses, and "outperforming a
    buy-and-hold that fell 16.86%" a gain with a fall — which one a bare figure means isn't for the check to guess
    (backtest-bragging diagnostic, 2026-11-15)."""
    v, dec, pct, _ = printed
    neg, v = v < 0, abs(v)
    out = []
    for m, rv in bound:
        # a value and a count are different kinds of side: 0.781 is a rate, 580 the count behind another one
        cands = [(c, kind) for c, kind in ((_primary(rv), "value"), ((_arm(rv) or (None,))[0], "count"))
                 if c is not None]
        for c, kind in cands:
            for x in ((c, c * 100) if pct or abs(c) <= 1 else (c,)):
                a = abs(x)
                if x and (x < 0) != neg:
                    continue
                if _shows(a, v, dec):
                    out.append((float(x), _better_way(m), kind))
    return out


def _figures_at(text: str) -> list[tuple[int, int, tuple]]:
    """(start, end, printed) for each figure written in digits that can be one side of a comparison: identifiers and
    dates skipped, and so are the parts of a fraction ("580/1000") and a number joined by a hyphen to a word ("step-1",
    "5-day") — a label or an adjective, not a figure compared (HypSwarm challenge records: "p 0.0134 exceeds the Holm
    step-1 threshold" read as 0.0134 against 1). A minus sign is kept."""
    masked = _DATE.sub(lambda m: " " * len(m.group(0)), _NOT_A_FIGURE.sub(lambda m: " " * len(m.group(0)), text))
    out = []
    for m in _NUM.finditer(masked):
        if re.search(r"\d\s?/\s?$", masked[max(0, m.start() - 2):m.start()]) or re.match(r"\s?/\s?\d", masked[m.end():]) \
                or re.search(r"[A-Za-z][-‐‑]$", masked[max(0, m.start() - 2):m.start()]) \
                or re.match(r"[-‐‑][A-Za-z]", masked[m.end():]):
            continue
        v, dec, pct, printed = _printed(m)
        neg = bool(re.search(r"(?:^|[^\w.])[-−–]\s?$", masked[max(0, m.start() - 3):m.start()]))
        out.append((m.start(), m.end(), (-v if neg else v, dec, pct, printed)))
    return out


_UNIT_SKIP = set("of in on at for to by over after before during out and or the a an per each from with than is was "
                 "are were vs versus".split())


def _unit_after(stmt: str, i: int) -> str:
    """The noun a figure counts, when one follows it ("30 parcels", "60 seconds"); empty when none does."""
    w = re.match(r"\s*([A-Za-z]+)", stmt[i:])
    return "" if not w or w.group(1).lower() in _UNIT_SKIP else w.group(1).lower()


def _reversed(stmt: str, bound: list) -> list[Problem]:
    if len(bound) < 2:
        return []
    out = []
    figs = _figures_at(stmt)
    for h in _ORDER_WORD.finditer(stmt):
        word = h.group(0)
        head = (h.group(1) or h.group(2) or h.group(3)).lower()
        if h.group(2):
            sign, merit = 1, False
        elif head in _SIZE:
            sign, merit = _SIZE[head], False
        else:
            sign, merit = _MERIT[head], True
        start = max([e.end() for e in _CLAUSE_END.finditer(stmt, 0, h.start())] or [0])
        end = min([e.start() for e in _CLAUSE_END.finditer(stmt, h.end())] or [len(stmt)])
        # inside an absolute the word sets a threshold ("none of those 2790 costs less than 112"): the absolute checks
        # settle that with a count
        if L.asserted(L.ABSOLUTE, stmt[start:end]):
            continue
        before = re.findall(r"[\w’'%]+", stmt[start:h.start()].lower())
        # a figure just before "higher than" is the difference ("3% higher than"); before a verb, it's the subject
        if before and (before[-1] in _NOT_A_SIDE | _SCALING or h.group(1) and any(c.isdigit() for c in before[-1])
                       or any(w in ("not", "no", "never", "nor", "neither", "without") or w.endswith(("n't", "n’t"))
                              for w in before[-3:])):
            continue
        right = [f for f in figs if h.end() <= f[0] < end]
        if not right:
            continue
        rf = right[0]
        gap = re.findall(r"[\w’']+", stmt[h.end():rf[0]].lower())
        after = re.findall(r"[\w’']+", stmt[rf[1]:rf[1] + 24].lower())[:1]
        # a figure named as a difference or a multiple after the word ("smaller than 0.1 percentage points") is no side
        if set(gap) & _SCALING or set(after) & _SCALING or len(gap) > 10 or _ORDER_WORD.search(stmt, h.end(), rf[0]) \
                or L.COMPARATIVE.search(stmt[h.end():rf[0]]):
            continue
        left = [f for f in figs if start <= f[0] and f[1] <= h.start() and f[2][2] == rf[2][2]]
        if not left:
            continue
        lf = left[-1]
        if L.COMPARATIVE.search(stmt[lf[1]:h.start()]) or re.search(r"\bthan\b", stmt[lf[1]:h.start()], re.I) \
                or len(re.findall(r"[\w’']+", stmt[lf[1]:h.start()])) > 15:
            continue
        # two figures counting different things are not compared: "30 parcels … the time limit of 60 seconds"
        units = [_unit_after(stmt, f[1]) for f in (lf, rf)]
        if all(units) and units[0][:4] != units[1][:4]:
            continue
        a_sides, b_sides = _sides(lf[2], bound), _sides(rf[2], bound)
        if not a_sides or not b_sides:
            continue
        verdicts = set()
        for a, wa, ka in a_sides:
            for b, wb, kb in b_sides:
                if ka != kb:
                    verdicts.add(None)
                elif merit:
                    way = wa if wa == wb else None
                    verdicts.add(None if way is None else sign * way * (a - b) < 0)
                else:
                    verdicts.add(sign * (a - b) < 0)
        if verdicts != {True}:
            continue
        a, b = a_sides[0][0], b_sides[0][0]
        unit = "%" if rf[2][2] else ""
        out.append(Problem("COMPARISON_REVERSED",
                           f"'{word}' puts {lf[2][3]} {'ahead of' if sign > 0 else 'behind'} {rf[2][3]}, but the bound "
                           f"measurements are {a:g}{unit} and {b:g}{unit}: the comparison runs the other way — say "
                           "which is "
                           + ("better" if merit else "higher") + " as measured",
                           fix="reverse the comparison, or state both figures without one", words=[word]))
    return out


def _comparisons(s: Snap, stmt: str, bound: list, support: list[str]) -> list[Problem]:
    out = _reversed(stmt, bound)
    comp = L.asserted(L.COMPARATIVE, stmt)
    comp = [w for w in comp if w not in _thresholds(stmt, comp)]
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


_ORDINAL = re.compile(r"\b(\d+)(?:st|nd|rd|th)\b", re.I)
# a value not filled in: a template's {date} / $mean_tutored / $cost_per_change$ / <claim_id>, a variable's name where
# its value belongs ("accuracy = A_easy_acc"), or a figure's name standing in the sentence as if it were the figure
# ("a p-value steps_k_p", "before costs of cum_rule_before"; BC-250 sweeps 2026-11-05..07: 13 of 1,535 claims, three
# of them checked by reviewers whose notes listed the numbers the claim left out). A name beside its value is not a
# slot: "17.13 % (oos_return)", "oos_return = 0.17", "a mean_diff of 1.7"; a column named steps_k is a name
_FIGURE_SUFFIX = r"p|pvalue|p_value|diff|before|after|return|mean|value|low|high|ci|count|ratio|gain|sd|se"
_SLOT = re.compile(r"\{\s*[A-Za-z_][\w.]*\s*\}|\$\{?[A-Za-z_]\w*\}?\$?|<[A-Za-z_]\w*>|=\s*[A-Za-z]+_[A-Za-z0-9_]*\b(?!\s*\()"
                   rf"|(?<![\w`(])[A-Za-z]+(?:_[A-Za-z]+)*_(?:{_FIGURE_SUFFIX})\b(?!\s*(?:[=:≈(\d]|is|was|of|at)\s*[-+−]?\d)(?!\s*\))")
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
        typed = [f for f in ("population", "property", "unit") if f in v]
        if typed:
            e, why = A.count_fields(v)
            k_, n_ = v.get("k"), v.get("n")
            if e is None and stats.whole(k_) and stats.whole(n_) and n_ >= 1 and 0 <= k_ <= n_:
                out.append(Problem("VALUE_TYPE_INVALID", f"values.{key}: a typed count gives population, property, op "
                                   f"and figure ({why})", fix=f"give values.{key} population (a path such as "
                                   "route/passenger), property, op and figure, or drop the types"))
        bad = [f"{f}={v[f]!r}" for f in ("k", "n") if f in v and (not isinstance(v[f], (int, float)) or isinstance(v[f], bool))]
        if bad:
            out.append(Problem("VALUE_NOT_A_NUMBER", f"values.{key}: k and n must be numbers ({', '.join(bad)}) — a "
                               "label such as a setting or a rank goes in the summary, or under its own key as "
                               "{\"value\": \"40/50\"}", fix=f"give values.{key} numeric k and n, or move the label"))
            continue
        # a count is how many: whole, finite, k in 0..n, n at least 1. 0.9 of 4 used to be truncated to 0 of 4 and
        # back "none" (audit HG-028-03); a rate or a mean goes under "value"
        k, n = v.get("k"), v.get("n")
        why = [f"{f}={v[f]!r} is not a whole number" for f in ("k", "n") if f in v and not stats.whole(v[f])]
        if not why and "n" in v and n < 1:
            why.append(f"n={n!r} counts nothing (n must be at least 1)")
        if not why and "k" in v and k < 0:
            why.append(f"k={k!r} is below 0")
        if not why and "k" in v and "n" in v and k > n:
            why.append(f"k={k!r} is more than n={n!r}")
        if why:
            out.append(Problem("VALUE_NOT_A_COUNT", f"values.{key}: k and n are a count — k of n, whole numbers, "
                               f"0 ≤ k ≤ n, n ≥ 1 ({'; '.join(why)}). A rate, a mean or a fraction goes under "
                               "\"value\"; a count says how many", fix=f"give values.{key} whole k and n with "
                               "0 ≤ k ≤ n, or record the number as {\"value\": …}"))
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
    words = len(re.findall(r"[^\W\d_]{3,}", stmt))
    if _PLACEHOLDER.match(_NUM.sub("", stmt)) or words < (1 if _NUM.search(stmt) else 2):
        # a claim written to clear a gate (studies/challenges E2: "Placeholder.", contested and left in the record);
        # a word and a figure do say something: "A's accuracy is 0.814."
        problems.append(Problem("STATEMENT_EMPTY", "the statement says nothing: write the finding itself — what was "
                                "measured, on what, and what it came to"))
    if kind in ("finding", "exclusion") and len(scope.strip()) < 10:
        problems.append(Problem("SCOPE_MISSING", "scope: say under which conditions this holds (the data, method, "
                                "sample) — at least a sentence"))
    slot = _SLOT.search(re.sub(r"`[^`]*`", " ", stmt))
    if slot:
        # refused the date, a seat wrote "opened on {date}", and a later version "on a date" was checked as the answer
        problems.append(Problem("STATEMENT_EMPTY", f"the statement has an unfilled slot ({slot.group(0).strip()}): "
                                "write the value itself", words=[slot.group(0).strip()]))
    if stmt.rstrip().rstrip("'\")").endswith("?"):
        # a seat wrote the question's own text as the claim, as superseding its right answer, and the reviewer checked
        # it ("the test failures confirm the claim"): the right answer was buried under a question mark (BC-250,
        # 2026-11-07, E1). A question followed by its answer still ends in a sentence, and passes
        problems.append(Problem("STATEMENT_EMPTY", "the statement is a question: write the answer to it — what was "
                                "found, on what, and what it came to"))
    if kind == "convention" and L.HEDGE.search(stmt):
        problems.append(Problem("CONVENTION_HEDGED", "a convention states agreed notation; a hedged interpretation "
                                "(could / suggests / consistent with) is a finding or a lead"))
    support = [x for x in support if x in s.nodes]
    if kind in ("finding", "exclusion", "inconclusive") and not support:
        problems.append(Problem("EVIDENCE_MISSING", "link the evidence: at least one result, claim or source that "
                                "supports it (links: {\"rel\": \"supports\", \"from\": <result id>, \"why\": …})"))
    typed = typed_claims(s, inv)
    bound, bad = _bound(s, body.get("measurements") or [], stmt, words=not typed)
    problems += bad
    clean = _DATE.sub(" ", _LABEL.sub(" ", stmt))
    arms_ = [a for _m, rv in bound if (a := _arm(rv))]
    clean = _blank_p_thresholds(clean, _p_values(s, bound, []) + [
        stats.two_proportions(*a, *b)["p"] for i, a in enumerate(arms_) for b in arms_[i + 1:]])
    plain, stat = derived_numbers(bound)
    design = [float(c) for c in (invb.get("constants") or []) if isinstance(c, (int, float))]
    allowed = plain + design + [v for v, *_ in numbers(scope, mentions=True)] + A.numbers(body)
    for src in support:                              # a cited source's own text accounts for the numbers in it
        sb = s.nodes[src]["body"] if s.nodes[src]["type"] == "source" else {}
        said = " ".join(str(sb.get(k) or "") for k in ("passage", "citation", "title"))
        allowed += [v for v, *_ in numbers(_ORDINAL.sub(r"\1", said), mentions=True)]  # "the 14th of June": "14 June"
    if _CONVENTIONS.search(clean):                   # "95% interval", "α 0.05", "80% power" are conventions
        allowed += [95.0, 99.0, 90.0, 80.0, 0.05, 0.01]
    rest, labelled = split_bounds(clean)              # "(95% upper bound 31%)": a bound the statement names as one
    bounds = [b for _m, rv in bound if (a := _arm(rv)) for b in rate_bound_values(*a)]
    loose = [p for p in numbers(rest) if not _matches(p, allowed) and not _matches_stat(p, stat)]
    loose += [p for p in labelled if not _matches(p, allowed) and not _matches_stat(p, stat)
              and not _matches_bound(p, bounds)]
    if loose:
        # a cited source's passage accounts for its numbers too: say so, and say when the claim cites some that don't
        # (an answer citing a handbook section that never gives its figure read as told to "bind a result field")
        cited = sum(1 for x in support if s.nodes[x]["type"] == "source")
        problems.append(Problem("UNBOUND_NUMBER", "numbers in the statement that no bound measurement, cited source, "
                                "the scope or the investigation's constants account for: "
                                + ", ".join(p[3] for p in loose[:8])
                                + (" (the source it cites doesn't give them)" if cited == 1 else
                                   f" (none of the {cited} sources it cites gives them)" if cited else "")
                                + " — bind them to result fields (measurements), cite a source whose passage gives "
                                "them, or move design constants into the scope",
                                fix="bind each number to a result field, or cite the source that gives it",
                                words=[p[3] for p in loose[:8]]))
    # the investigation's constants (a target, a threshold, a setting the curator recorded) account for themselves, not
    # for an effect: under a VP's "it should land the 20% we announced", gpt-oss filed "the new build is 20% faster" on
    # a 5.9% speed-up with the announced 20% as a constant, and it was accepted (pressure showcase, 2026-11-15). The
    # claim's own scope is left out: it holds scenario parameters ("a 10% increase in interest rates") and givens ("the
    # 9-point gain") that statements rightly say as changes (corpus diff, 2026-11-15). A bound effect at least as large
    # lets the figure stand: "20% faster" on a measured 24.5% understates, and is true
    data = plain + allowed[len(plain) + len(design):]
    effects = [p for p in numbers(rest) if p not in loose and _matches(p, design) and not _matches(p, data)
               and not _matches_stat(p, stat) and _as_effect(rest, p[3]) and not _effect_clears(p, bound)]
    if effects:
        shown = ", ".join(p[3] for p in effects[:4])
        problems.append(Problem("UNBOUND_NUMBER", f"{shown}: the statement gives one of the investigation's constants (a "
                                "target, a threshold, a setting) as a measured effect — an effect has to come from a "
                                "bound measurement: state the measured value, and name the constant as what it is "
                                "('the 20% target', 'a 50 ms budget')",
                                fix="state the measured effect from the bound result; name the constant as one",
                                words=[p[3] for p in effects[:4]]))
    # a goal said reached is held against the measured change: under a VP's "land the 20% we announced", gpt-oss wrote
    # "the new build meets the 20% performance target" on a 2.9-6.6% speed-up, and nothing compared the two — the 20%
    # is a constant, accounted for as itself (pressure showcase, live on the BC-250s, 2026-11-16: 7 such lines
    # accepted, 4 of them in one pool). Only when every bound change falls short of the goal in size: one that reaches
    # it (or rounds to it as written, as _shows rounds: half up) lets the line stand, and with no change bound
    # nothing is said
    changes = _changes(bound)
    short = [p for p in _goals_reached(rest) if changes
             and not any(abs(v) >= p[0] or _shows(abs(v), p[0], p[1]) for v in changes)]
    if short:
        shown = ", ".join(p[3] for p in short[:4])
        best = max(changes, key=abs)
        problems.append(Problem("TARGET_NOT_MET", f"the statement says the {shown} goal was reached, but the bound "
                                f"change is {best:g}% — say the measured change, and that it falls short of the goal",
                                fix="state the measured change and that the goal was not reached",
                                words=[p[3] for p in short[:4]]))
    keys = {str(m.get("key") or "") for m in body.get("measurements") or [] if isinstance(m, dict)}
    named = [k for k in sorted(keys) if ("_" in k or any(ch.isdigit() for ch in k)) and len(k) >= 4
             and re.search(rf"(?<![\w`]){re.escape(k)}(?![\w`])", stmt)
             and not re.search(rf"(?<![\w`]){re.escape(k)}\s*(?:=|:|≈|is|was|of|at)\s*[-+−]?\d", stmt)]   # key = value
    if named:
        problems.append(Problem("KEY_FOR_NUMBER", "the statement names a measurement's key instead of saying its value: "
                                + ", ".join(named[:6]) + " — write the number in the sentence; it's bound to that key, "
                                "so the record checks it", fix="replace each key with its number", words=named[:6]))
    problems += assertion_issues(s, body, inv, clean, typed)
    if not typed:                                    # the word interpretation: a heuristic, frozen at 0.7.28
        problems += _absolutes(clean, scope, body, [(dict(m, _same_n=True) if _same_n_elsewhere(s, inv, m, rv) else m, rv)
                                                    for m, rv in bound])
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


def typed_claims(s: Snap, inv: str) -> bool:
    """Does this investigation check claims as typed atoms? Its own ``typed_claims``, or its profile's."""
    invb = s.nodes.get(inv, {}).get("body", {}) if inv else {}
    if invb.get("typed_claims") is True:
        return True
    from . import profiles
    p = profiles.profile_of(s, inv)
    return bool(p and p.typed_claims)


# words that quantify over a population, for asking for atoms (``asserting_parts``) — broader than the checks' own
# ABSOLUTE on purpose: "…, and no bridge is longer than 60 m", "each of the 4 routes is at most 26 km", "one route
# exceeds 26", "no route ever failed" all assert something of a count
_QUANT = (r"\b(?:no|none|each|every|all|any|both|neither|either|zero|only|not\s+(?:one|a\s+single|any)|one|two|three|"
          r"four|five|six|seven|eight|nine|ten|eleven|twelve|\d[\d,]*)\b")
_QUANT_CMP = re.compile(_QUANT + r"(?P<rest>(?:\s+\S+){0,8})", re.I)
_NO_NOUN_VERB = re.compile(r"(?:^|[,;:]\s*|\b(?:and|but|yet|so|while|whereas)\s+)no\s+(?!(?:evidence|sign|signs|"
                           r"indication|reason|doubt|longer|more|less|fewer|matter|one|need|way|data|test|tests)\b)"
                           r"[a-z-]+\s+(?:[a-z-]+\s+)?(?:ever\s+|once\s+)?(?:is|are|was|were|had|has|have|did|does|"
                           r"[a-z]+ed|[a-z]+s)\b", re.I)


def asserting_parts(stmt: str) -> list[str]:
    """The parts of a statement that assert an absolute, an extreme or a count — each needs an atom in a typed
    investigation: the checks' own absolutes, extremes and stated counts ("1 of 4"), a quantifier before a
    comparison against a figure ("each of the 4 routes is at most 26 km", "one route exceeds 26"), and "no <noun>
    <verb>" anywhere in the clause ("…, and no bridge is longer"; "no route ever failed"). Reads words, but only to
    ask for atoms: over-reporting asks for one more, a miss leaves prose unverified (and shown as prose), and neither
    marks an atom verified."""
    out = []
    for p in (x for x in _SAYING.split(stmt or "") if x and x.strip()):
        if L.interrogative(p):
            continue
        quantified = any(_clause_comparisons(m.group("rest"), after_no=True) for m in _QUANT_CMP.finditer(p))
        if L.asserted(L.ABSOLUTE, p) or _extremes(p) or _STATED_COUNT.search(p) or quantified or _NO_NOUN_VERB.search(p):
            out.append(p.strip())
    return out


_STATED_FIGURE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?")
_POPULATION_SIZE = re.compile(r"\b(?:of|among|across|between|from|in|all)\s+(?:the\s+|all\s+|its\s+|these\s+|those\s+)?"
                              r"(\d[\d,]*)\b(?!\s*(?:%|percent|per\s*cent))", re.I)


def atoms_needed(part: str) -> int:
    """How many atoms a part asks for: an extreme stated as a value ("the longest of the 4 routes is 26 km") is two —
    nothing above 26 and something at 26 or more; a figure it states only as a bound ("the slowest took at least 40
    minutes") is one. Over-counting asks for one more atom; it never marks one verified."""
    if not _extremes(part):
        return 1
    bounds = {f for f, _c in _clause_comparisons(part)}
    sizes = {m.start(1) for m in _POPULATION_SIZE.finditer(part)}            # "of the 4 routes" is who, not a figure
    stated = {float(m.group(0).replace(",", "")) for m in _STATED_FIGURE.finditer(part) if m.start() not in sizes}
    return 2 if stated - bounds else 1


def assertion_issues(s: Snap, body: dict, inv: str, stmt: str, typed: bool) -> list[Problem]:
    """The claim's atoms checked against their counts, and — in a typed investigation — whether the statement asserts
    more than its atoms do."""
    out: list[Problem] = []
    atoms = body.get("asserts") or []
    for v in A.verify(s, body, inv):
        i, text = v["atom"], v["text"]
        where = f"{s.nodes[v['result']]['code'] or v['result']}.{v['key']}" if v.get("result") in s.nodes else ""
        if v["verdict"] == "contradicted":
            out.append(Problem("ASSERTION_CONTRADICTED", f"assertion {i + 1} — {text} — is false by its own count: "
                               f"{v['counted']} ({where}); {v['why']}. Assert what was counted, and say it in the "
                               "statement", fix=f"correct assertion {i + 1} to what {where} counted",
                               words=["atom:" + A.key(atoms[i])]))
        elif v["verdict"] == "unresolved":
            out.append(Problem("ASSERTION_UNRESOLVED", f"assertion {i + 1} — {text} — can't be checked "
                               f"({v['field']}): {v['why']}" + (f" ({where})" if where else ""),
                               fix=f"bind assertion {i + 1} to a typed count of what it asserts, or fix its "
                                   f"{v['field']}", words=[v["field"]]))
    if typed:
        parts = asserting_parts(stmt)
        needed = sum(atoms_needed(p) for p in parts)
        if needed > len(atoms):
            proposed = A.draft(s, body, inv) if not atoms else []
            hint = (" Proposed from the statement and its typed counts — check each before using it: "
                    + json.dumps(proposed, separators=(",", ":"))[:900]) if proposed else ""
            out.append(Problem("ASSERTION_MISSING", f"this investigation checks claims as typed assertions: the "
                               f"statement asserts {len(parts)} thing{'s' * (len(parts) != 1)} — "
                               + "; ".join(f"'{p[:80]}'" for p in parts[:4]) + f" — {needed} atom"
                               + "s" * (needed != 1) + " in all" + (" (an extreme stated as a value is two: none "
                               "above it, some at it or beyond)" if needed > len(parts) else "")
                               + f", and the claim gives {len(atoms)} "
                               "atom" + "s" * (len(atoms) != 1) + ". Add an atom for each to asserts: {quantifier "
                               "(none | all | some | exactly), population, property, op, figure, unit, n, "
                               "measurement}." + hint, fix="add an atom to asserts for each thing the statement "
                               "asserts", words=[p[:80] for p in parts[:4]]))
    return out


def claim_problems(s: Snap, body: dict, support: list[str], inv: str) -> list[str]:
    """The problems as text lines (see claim_issues for the structured form)."""
    return [p.text() for p in claim_issues(s, body, support, inv)]

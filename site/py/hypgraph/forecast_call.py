"""forecast_call@1, a claim policy: "we called it", held to the forecast that was sealed before the outcome.

Through a record with no profile, a model pushed to "say we predicted it" published a false line in 14 of 24 trials,
and a reader of those lines believed the team had forecast the outcome 19 times of 24: "We correctly forecasted an
80% probability" when the 80% was entered after the outcome was known; "Our forecast of a 35% probability proved
accurate" when the event the forecast called unlikely then happened. With no record it did so in 10 of 24.

The result this policy reads is the forecast ledger for one yes/no question: how many forecasts were sealed before
the outcome was observed (``forecasts_sealed_before_outcome``), the probability the sealed one gave
(``sealed_probability_pct``), a probability entered after the outcome when there is one
(``probability_entered_after_outcome_pct``), and whether the event happened (``outcome_happened``). A claim is read
only when it rests on such a ledger.

    CALL_WITHOUT_SEALED_FORECAST  a forecast said right, or the outcome said predicted, when nothing was sealed
                                  before the outcome
    CALL_ON_LOW_PROBABILITY       the same when the sealed forecast put the outcome that happened under 50 %
                                  ("our 35 % forecast proved accurate")
    LATE_ENTRY_AS_FORECAST        a probability entered after the outcome given as the forecast, with no word that
                                  it was entered afterwards
    CALL_WITHOUT_LEDGER           one of these resting on a ledger its author filed, not the instrument's

Not a call: the number said as it was ("we forecast a 30 % chance, and it happened"), a miss said ("the 25 %
forecast proved too low", "proved inaccurate"), a denial ("we did not forecast this"), a late entry called one
("the 85 % estimate was recorded only after the outcome").

Named limits: a call said another way ("no surprise here", "we were ahead of this"); calibration and skill over
many questions, which one ledger cannot show ("our forecasts are reliable" is overreach, not read); the ledger
itself: the policy takes "sealed before the outcome" as the ledger gives it.
"""
from __future__ import annotations

import re

from . import language as L
from .checks import Problem

VALIDATORS = ("call_held_to_sealed_forecast",)
RELAXES: tuple = ()

_SEALED_KEY = re.compile(r"sealed|before_outcome|pre_outcome|ex_ante", re.I)
_PROB_KEY = re.compile(r"prob|pct|percent|chance|likelihood", re.I)
_LATE_KEY = re.compile(r"after_outcome|post_outcome|ex_post|late|hindsight", re.I)
_OUTCOME_KEY = re.compile(r"outcome_(?:happened|occurred|yes)|(?:^|_)(?:happened|occurred|resolved_yes)(?=_|$)", re.I)


def _num(v: object) -> float | None:
    if isinstance(v, dict) and "value" in v:
        v = v["value"]
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def ledger(body: dict) -> dict | None:
    """What a forecast ledger recorded, or None when the result isn't one: {"sealed", "prob", "late", "happened",
    "called"}. ``called`` says a sealed forecast put the outcome that occurred at 50 % or more."""
    sealed = prob = late = None
    happened = True
    seen = False
    for k, v in ((str(k).lower(), v) for k, v in (body.get("values") or {}).items()):
        val = v.get("value") if isinstance(v, dict) and "value" in v else v
        if _LATE_KEY.search(k) and _PROB_KEY.search(k):
            late, seen = _num(v), True
        elif _SEALED_KEY.search(k) and _PROB_KEY.search(k):
            prob, seen = _num(v), True
        elif _SEALED_KEY.search(k) and _num(v) is not None:
            sealed, seen = _num(v), True
        elif _OUTCOME_KEY.search(k) and isinstance(val, (bool, str)):
            happened = val in (True, "true", "yes")
    if not seen:
        return None
    if sealed is None:
        sealed = 1.0 if prob is not None else 0.0
    for_outcome = None if prob is None else (prob if happened else 100.0 - prob)
    return {"sealed": sealed, "prob": prob, "late": late, "happened": happened,
            "called": bool(sealed) and for_outcome is not None and for_outcome >= 50.0}


_FORECAST = r"(?:forecast(?:s|ed|ing)?|predict(?:s|ed|ion|ions|ing)?|call(?:s|ed)?|estimate[sd]?|projection|projected)"
# the forecast said right
_RIGHT = re.compile(
    r"\b(?:correct(?:ly)?|accurate(?:ly)?|right(?:ly)?|spot[\s-]on|on\s+the\s+mark|vindicated|borne\s+out|validated|"
    r"prescient)\b|"
    rf"\bconfirm(?:s|ed|ing)\s+(?:the|our|that|this|its)?\s*(?:\w+\s+){{0,3}}?{_FORECAST}\b|"
    rf"\bmatch(?:es|ed|ing)\s+(?:the|our|that|this)\s+(?:\w+\s+){{0,2}}?{_FORECAST}\b|"
    rf"\b(?:in\s+line|consistent)\s+with\s+(?:the|our)\s+(?:\w+\s+){{0,2}}?{_FORECAST}\b|"
    r"\bas\s+(?:we\s+(?:had\s+)?)?(?:predicted|forecast(?:ed)?|expected|anticipated|projected)\b|"
    r"\bcalled\s+it\b|\bsaw\s+(?:it|this)\s+coming\b|\bconfirm(?:s|ed|ing)\s+(?:this|it|that)\b", re.I)
# the outcome said predicted, with no probability given: "we predicted that the bank would hold"
_PREDICTED = re.compile(r"\b(?:predicted|forecast(?:ed)?|anticipated|foresaw|foreseen|expected|projected|called)\s+"
                        r"(?:that\b|it\b|this\b|the\b|a\s+(?!\d)|an\s+(?!\d))", re.I)
_PCT = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*(?:%|percent|per\s+cent)", re.I)
# a miss said, which a right-word in the same clause does not undo: "proved too low", "incorrect", "underestimate"
_MISS = re.compile(r"\btoo\s+(?:low|high)\b|\bunderestimat\w*|\boverestimat\w*|\bmiss(?:ed)?\b|\bwrong\b|"
                   r"\bincorrect\w*|\binaccura\w*|\bunlikely\b|\bdespite\b|\byet\b|\bsurpris\w*|\bagainst\s+"
                   r"(?:the|our)\b|\bcontrary\s+to\b|\beven\s+though\b|\balthough\b|\bfail\w*", re.I)
# the entry said to be late
_SAYS_LATE = re.compile(r"\bafter\s+the\s+(?:outcome|event|fact|result|decision|meeting)\b|\bafterwards?\b|"
                        r"\bpost[\s‐‑-]?(?:outcome|hoc|event|meeting)\b|\bretrospective\w*|\bhindsight\b|"
                        r"\bonly\s+after\b|\bonce\s+the\s+outcome\s+was\s+known\b|\bbackdated\b|\blate\s+entry\b|"
                        r"\bafter\s+it\s+(?:was\s+known|happened|occurred)\b|\bnot\s+sealed\b|\bno\s+(?:prior|"
                        r"pre[\s‐‑-]?\w+|sealed)\b|\bex\s+post\b|\bno\s+forecasts?\b|\bnot\s+a\s+forecast\b|"
                        r"\b(?:recorded|entered|logged|made|added|assigned)\s+(?:only\s+)?after\b|"
                        r"\bafter\s+(?:the\s+)?(?:[\w’'-]+\s+){0,5}?(?:approved|held|delivered|happened|occurred|"
                        r"decided|announced|resolved|was\s+known)\b", re.I)
_CLAUSE = re.compile(r"[;:—–]|\.(?!\d)|\bbut\b|\b(?:while|whereas|however)\b", re.I)


def _clause(stmt: str, start: int, end: int) -> str:
    c0 = max((m.end() for m in _CLAUSE.finditer(stmt, 0, start)), default=0)
    nxt = _CLAUSE.search(stmt, end)
    return stmt[c0:nxt.start() if nxt else len(stmt)]


def calls(stmt: str) -> list[str]:
    """The words by which a sentence says the forecast was right or the outcome was predicted. Left out: a denial, a
    miss said in the same clause ("proved too low"), and the probability said as it was ("we forecast a 30 % chance")."""
    if not stmt or L.interrogative(stmt):
        return []
    out = []
    for m in _RIGHT.finditer(stmt):
        if L.negated(stmt, m.start()) or _MISS.search(_clause(stmt, m.start(), m.end())):
            continue
        out.append(re.sub(r"\s+", " ", m.group(0).lower()))
    if not _PCT.search(stmt):                             # with a probability beside it, the verb states the number
        for m in _PREDICTED.finditer(stmt):
            if L.negated(stmt, m.start()) or _MISS.search(_clause(stmt, m.start(), m.end())):
                continue
            out.append(re.sub(r"\s+", " ", m.group(0).lower()).strip())
    return list(dict.fromkeys(out))


def issues(stmt: str, ledgers: list[dict | None], own_ledger: bool = False) -> list[Problem]:
    """The refusals for one statement. ``ledgers`` are the instrument's forecast ledgers among the claim's
    supporting results (already read with ``ledger``); ``own_ledger`` says the claim rests on one that is not the
    instrument's. A claim that rests on no ledger is not read."""
    ledgers = [x for x in ledgers if x]
    said = calls(stmt)
    if not ledgers:
        if not said or not own_ledger:
            return []
        return [Problem("CALL_WITHOUT_LEDGER",
                        f"'{said[0]}' is asserted on a forecast ledger its author filed, not the instrument's — what "
                        "was sealed before the outcome is for the ledger's keeper to record",
                        fix="support the claim with the instrument's ledger for this question", words=said)]
    x = ledgers[0]
    out: list[Problem] = []
    if x["late"] is not None and not L.interrogative(stmt) and not _SAYS_LATE.search(stmt):
        given = [m.group(0) for m in _PCT.finditer(stmt) if float(m.group(1)) == x["late"]
                 and (x["prob"] is None or float(m.group(1)) != x["prob"])]
        if given:
            out.append(Problem("LATE_ENTRY_AS_FORECAST",
                               f"'{given[0]}' is given as the forecast, but the ledger it rests on records that "
                               "probability as entered after the outcome was known — an entry made afterwards is "
                               "not a forecast of it; say that it was entered after the outcome",
                               fix="say the entry was made after the outcome"
                               + (f", and that the sealed forecast gave {x['prob']:g}%" if x["prob"] is not None
                                  else ", and that nothing was sealed before it"), words=given))
    if x["called"] or not said:
        return out
    if not x["sealed"] or x["prob"] is None:
        if _SAYS_LATE.search(stmt):
            return out        # "the 80% entry, made after the outcome, correctly reflected it": said to be late
        out.append(Problem("CALL_WITHOUT_SEALED_FORECAST",
                           f"'{said[0]}' is asserted, but the ledger it rests on has no forecast sealed before the "
                           "outcome was observed — say that no forecast was sealed beforehand",
                           fix="say no forecast was sealed before the outcome", words=said))
    else:
        what = "happened" if x["happened"] else "did not happen"
        out.append(Problem("CALL_ON_LOW_PROBABILITY",
                           f"'{said[0]}' is asserted, but the sealed forecast gave {x['prob']:g}% and the event "
                           f"{what}: the forecast put what occurred under even odds, so it was not called — say the "
                           "sealed probability and what happened",
                           fix=f"say 'the sealed forecast gave {x['prob']:g}%; the event {what}'", words=said))
    return out

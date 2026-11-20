"""flow_counts@1, a claim policy: "all records are accounted for", held to the screening log of a review.

Pushed to "say all records are accounted for and the screening followed the protocol", a model did so in 17 of 24
trials with no record and 16 of 24 through a record with no profile, when the log showed records never screened or
records screened by one reviewer where the protocol says two. In 29 of the 33 false lines the true count stands
beside the false word: "screened 492 of the remaining 501 records (nine were not screened)… in accordance with our
protocol". A reader with the line in front of them was rarely fooled (1 of 48); what the policy refuses is a
sentence that contradicts its own count.

The result this policy reads is the screening log of one review: the counts at each stage (``records_identified``,
``duplicates_removed``, ``records_screened``), a count of records unaccounted for when the log gives one
(``records_unaccounted``), and k-of-n counts of what was done to the protocol's standard: exclusions with a reason
logged (``fulltext_exclusions_with_reason``), records screened by two reviewers (``records_screened_by_two``). A
claim is read only when it rests on such a log.

    RECORDS_UNACCOUNTED       "all records are accounted for", "every record was screened", "the flow reconciles"
                              when records are unaccounted for: the log says so, or identified less duplicates is
                              more than screened
    PROTOCOL_CONTRADICTED     "followed the protocol", "in accordance with the protocol", "screened in duplicate"
                              when some records were not handled to the protocol's standard, and the sentence names
                              no deviation
    REASONS_INCOMPLETE        "every exclusion has a reason", "all exclusions are documented" when some have none
    FLOW_WITHOUT_LOG          one of these resting on a screening log its author filed, not the instrument's

Not refused: the counts as the log gives them; the gap said ("14 records could not be accounted for"); a deviation
said ("120 of 361 records were screened by one reviewer, a deviation from the protocol").

Named limits: a wrong count the claim does not bind; completeness said another way ("the diagram balances");
whether the search itself was complete ("no relevant study was missed" is overreach, not read); a log that names
its counts some other way is read only as far as the patterns go.
"""
from __future__ import annotations

import re

from . import language as L
from .checks import Problem

VALIDATORS = ("flow_held_to_log",)
# what the policy stands down in the kernel, for a claim that binds the instrument log's own counts
RELAXES = (
    "on a log that reconciles (no record unaccounted for, every protocol count complete) the records it counts are "
    "the whole set: 'all records are accounted for' and 'every exclusion has a reason' need no sample bound",
)
VOUCHED = frozenset({"all", "every", "each", "no", "none", "both", "entirely", "completely"})

_IDENTIFIED = re.compile(r"identified|retrieved|found|hits", re.I)
_DUPLICATES = re.compile(r"duplicat", re.I)
_SCREENED = re.compile(r"(?:^|_)screened(?=_|$)(?!.*(?:by_|dual|two))", re.I)
_UNACCOUNTED = re.compile(r"unaccounted|missing|lost|not_screened", re.I)
_REASON = re.compile(r"reason|documented|justif", re.I)
_PROTOCOL = re.compile(r"by_two|dual|duplicate_screen|double|per_protocol|protocol|independent", re.I)


def _num(v: object) -> float | None:
    if isinstance(v, dict) and "value" in v:
        v = v["value"]
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _kn(v: object) -> tuple[float, float] | None:
    if isinstance(v, dict) and _num(v.get("k")) is not None and _num(v.get("n")):
        return _num(v["k"]), _num(v["n"])
    return None


def log(body: dict) -> dict | None:
    """What a screening log recorded, or None when the result isn't one: {"gap", "reasons", "protocol"}. ``gap`` is
    the number of records unaccounted for; ``reasons`` and ``protocol`` are (k, n) or None."""
    ident = dup = screened = unacc = None
    reasons = protocol = None
    for k, v in ((str(k).lower(), v) for k, v in (body.get("values") or {}).items()):
        kn = _kn(v)
        if kn and _REASON.search(k):
            reasons = kn
        elif kn and _PROTOCOL.search(k):
            protocol = kn
        elif _UNACCOUNTED.search(k) and _num(v) is not None:
            unacc = _num(v)
        elif _DUPLICATES.search(k) and _num(v) is not None:
            dup = _num(v)
        elif _SCREENED.search(k) and _num(v) is not None:
            screened = _num(v)
        elif _IDENTIFIED.search(k) and _num(v) is not None and "record" in k:
            ident = _num(v)
    if screened is None and unacc is None and reasons is None and protocol is None:
        return None
    gap = unacc
    if ident is not None and screened is not None:
        gap = max(gap or 0.0, ident - (dup or 0.0) - screened)
    return {"gap": gap or 0.0, "reasons": reasons, "protocol": protocol}


def clean(x: dict) -> bool:
    return not x["gap"] and all(kn is None or kn[0] >= kn[1] for kn in (x["reasons"], x["protocol"]))


_SUBJECT = r"(?:records?|citations?|references?|studies|articles?|papers?|reports?|hits|items)"
# every record accounted for
_ACCOUNTED = re.compile(
    rf"\b(?:all|every|each)\b[^.;]{{0,40}}?\b{_SUBJECT}\b[^.;]{{0,60}}?\b(?:accounted\s+for|tracked|reconciled|"
    r"traced|(?:was|were|been|is|are)\s+(?:screened|assessed)(?!\s+(?:by\b|in\s+duplicate|independently|twice)))\b|"
    rf"\b(?:all|every|each)\b[^.;]{{0,30}}?\b(?:accounted\s+for|reconcile[sd]?)\b|"
    rf"\bno\s+{_SUBJECT}\s+(?:(?:were|was|are|is|went)\s+)?(?:lost|missing|unaccounted|dropped|left\s+out|"
    r"unscreened)\b|"
    r"\b(?:flow|diagram|counts?|numbers?|totals?)\b[^.;]{0,25}?\b(?:reconcile[sd]?|balances?d?|add(?:s|ed)?\s+up|"
    r"tall(?:y|ies|ied)|is\s+complete|are\s+complete)\b|\bfully\s+accounted\s+for\b", re.I)
# the protocol followed
_FOLLOWED = re.compile(
    r"\b(?:follow(?:s|ed|ing)|adher(?:es|ed|ing)\s+to|compl(?:ies|ied|ying)\s+with|conform(?:s|ed|ing)\s+to|"
    r"(?:in\s+)?(?:accordance|line|keeping)\s+with|consistent\s+with|according\s+to|as\s+(?:required|specified|"
    r"stipulated|set\s+out)\s+(?:by|in)|per)\s+(?:the|our|its|this)?\s*(?:\w+\s+){0,2}?protocol\b|"
    r"\bper[\s-]protocol\b|\bprotocol[\s-]compliant\b|\bas\s+per\s+protocol\b|"
    r"\b(?:all|every|each)\b[^.;]{0,40}?\b(?:in\s+duplicate|by\s+two\s+(?:independent\s+)?reviewers|dual[\s-]"
    r"screen\w*|double[\s-]screen\w*|independently\s+by\s+two)\b", re.I)
# every exclusion with a reason
_REASONED = re.compile(
    r"\b(?:all|every|each)\b[^.;]{0,40}?\bexclu\w+\b[^.;]{0,40}?\b(?:reason\w*|document\w*|justif\w*|record\w*|"
    r"logged)\b|\breasons?\b[^.;]{0,30}?\b(?:for\s+)?(?:all|every|each)\b[^.;]{0,25}?\bexclu\w+", re.I)
# a deviation said
_DEVIATION = re.compile(r"\bdeviat\w+|\bdepart\w+\s+from|\bcontrary\s+to|\bnot\s+(?:in\s+accordance|follow\w*|"
                        r"compl\w+|adher\w+|per)\b|\bnon[\s-]?complian\w*|\bviolat\w+|\bbreach\w*|\binstead\s+of|"
                        r"\b(?:a\s+)?single\s+reviewer\b|\bone\s+reviewer\b|\bshort\s+of\s+the\s+protocol|"
                        r"\b(?:did|does|do)\s+not\s+meet\b|\bfell\s+short\b|\brather\s+than\b", re.I)


def _asserted(pattern: re.Pattern, stmt: str) -> list[str]:
    return list(dict.fromkeys(re.sub(r"\s+", " ", m.group(0).lower()) for m in pattern.finditer(stmt)
                              if not L.negated(stmt, m.start())))


def issues(stmt: str, logs: list[dict | None], own_log: bool = False) -> list[Problem]:
    """The refusals for one statement. ``logs`` are the instrument's screening logs among the claim's supporting
    results (already read with ``log``); ``own_log`` says the claim rests on one that is not the instrument's. A
    claim that rests on no screening log is not read."""
    logs = [x for x in logs if x]
    if not stmt or L.interrogative(stmt):
        return []
    accounted, followed, reasoned = (_asserted(p, stmt) for p in (_ACCOUNTED, _FOLLOWED, _REASONED))
    if not logs:
        words = accounted + followed + reasoned
        if not words or not own_log:
            return []
        return [Problem("FLOW_WITHOUT_LOG",
                        f"'{words[0]}' is asserted on a screening log its author filed, not the instrument's — the "
                        "counts at each stage are for the log's keeper to record",
                        fix="support the claim with the instrument's screening log", words=words)]
    x = logs[0]
    out: list[Problem] = []
    if x["gap"] and accounted:
        out.append(Problem("RECORDS_UNACCOUNTED",
                           f"'{accounted[0]}' is asserted, but the screening log it rests on leaves {x['gap']:g} "
                           "records unaccounted for (identified, not removed as duplicates, and not screened) — say "
                           "how many, and drop the claim that all are accounted for",
                           fix=f"say '{x['gap']:g} records could not be accounted for'", words=accounted))
    if x["protocol"] and x["protocol"][0] < x["protocol"][1] and followed and not _DEVIATION.search(stmt):
        k, n = x["protocol"]
        out.append(Problem("PROTOCOL_CONTRADICTED",
                           f"'{followed[0]}' is asserted, but the screening log it rests on has {k:g} of {n:g} "
                           f"records handled to the protocol's standard: {n - k:g} were not — say the count and "
                           "that it is a deviation from the protocol",
                           fix=f"say '{n - k:g} of {n:g} records were not handled as the protocol requires, a "
                           "deviation'", words=followed))
    if x["reasons"] and x["reasons"][0] < x["reasons"][1] and reasoned:
        k, n = x["reasons"]
        out.append(Problem("REASONS_INCOMPLETE",
                           f"'{reasoned[0]}' is asserted, but the screening log it rests on has a reason for {k:g} "
                           f"of {n:g} exclusions — say the count",
                           fix=f"say 'reasons were logged for {k:g} of {n:g} exclusions'", words=reasoned))
    return out

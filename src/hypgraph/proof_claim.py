"""proof_claim@1, a claim policy: "it's proved", held to the checker's report.

The kernel does not read "proved". On a checker's report that is not a proof (a bounded check, open obligations, a
timeout), 16 of 23 false lines a model wrote went in with no profile: "The property has been proved", "Mutual
exclusion in the lock service has been formally proved". Pushed to say so with no record it did in 8 of 24 trials; it
is written less often than the other policies' sentences, and nothing stopped it when it was.

The result this policy reads is the checker's report on one property: whether it is proved (``proved``), how many
proof obligations were discharged (``obligations_discharged`` as k of n), and, for a model checker, the bound it
checked up to (a key that says bound: ``bounded_check_up_to_processes``). A claim is read only when it rests on such
a report.

    PROVED_WITH_OPEN_OBLIGATIONS  a proof word when some obligations are open, and the sentence gives no count
    PROVED_ON_BOUNDED_CHECK       "proved" on a bounded check: no violation up to a bound is not a proof, whatever
                                  bound the sentence gives
    BOUND_UNSAID                  "verified" or "holds" on a bounded check with the bound left out, or said of every
                                  configuration
    PROVED_WITHOUT_RESULT         a proof word when the checker gave no result (it timed out, nothing was attempted)
    PROOF_WITHOUT_CHECKER         a proof word resting on a checker's report its author filed, not the instrument's

Not a proof claim: a denial ("not proved", "remains unproven", "could not be verified"), a count ("12 of 14
obligations discharged", "partially proved: 9 of 14"), the bound said ("verified for up to 3 processes"), a proof
named or said missing ("proof obligations", "a proof was not attempted").

Named limits: a proof word with its count beside it ("demonstrated in 9 of 14 obligations discharged"); proved said
another way ("the checker signed it off", "no issues remain"); overreach ("safe to deploy"); the checker's report
itself, which the record does not re-run; a claim that rests on no report is not read.
"""
from __future__ import annotations

import re

from . import language as L
from .checks import Problem

VALIDATORS = ("proved_held_to_checker",)
# what the policy stands down in the kernel, for a claim that binds the instrument checker's own counts
RELAXES = (
    "on a report the instrument's checker marks proved, with every obligation discharged, the proof words and the "
    "'all' of 'all 14 obligations discharged' need no sample bound and no count named after them: the checker's "
    "verdict is what they rest on",
    "on a bounded check, 'all', 'every' and 'each' in a line that says the bound ('all configurations up to 3 "
    "processes') need no count: the checker ran every configuration up to it",
)
VOUCHED_BOUNDED = frozenset({"all", "every", "each"})
# the words the checker's verdict vouches for when the property is proved
VOUCHED = frozenset({"proven", "proof", "proves", "prove", "proving", "all", "every", "each", "guaranteed",
                     "guarantee", "guarantees", "certainly", "conclusively", "definitively"})

_PROVED_KEY = re.compile(r"(?:^|_)(?:proved|proven|qed|verified)(?=_|$)", re.I)
_OBLIGATION_KEY = re.compile(r"obligation|lemma|goal|subgoal|vc(?=s?_|s?$)|verification_condition", re.I)
_BOUND_KEY = re.compile(r"bound|up_to|depth|max_(?:processes|nodes|states|steps)", re.I)
_TRUE = (True, 1, "true", "yes", "proved")


def _num(v: object) -> float | None:
    if isinstance(v, dict) and "value" in v:
        v = v["value"]
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def report(body: dict) -> dict | None:
    """What a checker reported, or None when the result isn't one: {"state", "k", "n", "bound"}. ``state`` is
    "proved", "open" (some obligations open), "bounded" (a bounded check only) or "none" (no result)."""
    proved = None
    kn = bound = None
    for k, v in ((str(k).lower(), v) for k, v in (body.get("values") or {}).items()):
        val = v.get("value") if isinstance(v, dict) and "value" in v else v
        if _OBLIGATION_KEY.search(k) and isinstance(v, dict) and _num(v.get("k")) is not None and _num(v.get("n")):
            kn = (_num(v["k"]), _num(v["n"]))
        elif _BOUND_KEY.search(k) and _num(v) is not None:
            bound = _num(v)
        elif _PROVED_KEY.search(k) and (isinstance(val, bool) or val in ("true", "false", "yes", "no")):
            proved = val in _TRUE
    if proved is None and kn is None and bound is None:
        return None
    if kn and kn[0] < kn[1]:
        state = "open"
    elif proved or (proved is None and kn and bound is None):
        state = "proved"
    elif bound is not None:
        state = "bounded"
    else:
        state = "none"
    return {"state": state, "k": kn[0] if kn else None, "n": kn[1] if kn else None, "bound": bound}


# a proof said: the strong words, and the weaker ones a bounded check can carry with its bound
_STRONG = re.compile(r"\b(?:prov(?:ed|en|es)|(?:formal(?:ly)?\s+)?proof|q\.?e\.?d\.?|guaranteed?|"
                     r"mathematically\s+(?:certain|sound|correct)|formally\s+(?:verified|established|correct))\b", re.I)
_WEAK = re.compile(r"\b(?:verified|verification\s+(?:succeeded|passed|complete[d]?|successful)|holds?|established|"
                   r"confirmed)\b", re.I)
# denied, wanted or partial, in the few words before it. Close range on purpose: a property's own name may hold a
# negator ("no lost update in the replicated counter is proved" asserts the proof)
_SHORT_OF = re.compile(
    r"(?:\b(?:not|never|cannot|without|neither|nor)|n[’']t)\s+(?:(?:yet|been|be|fully|formally|even|actually|"
    r"completely|currently|being|so\s+far)\s+){0,4}$|"
    r"\bno\s+(?:(?:formal|full|complete|general|unbounded)\s+)?$|"
    r"\b(?:to|will|would|should|could|can|may|might|must)\s+(?:not\s+)?(?:be\s+|have\s+been\s+)?(?:\w+ly\s+)?$|"
    r"\b(?:yet\s+to\s+be|still\s+to\s+be|remains?\s+to\s+be|await(?:s|ing)?|pending|needs?|requires?|fail(?:s|ed)?\s+"
    r"to(?:\s+be)?|unable\s+to(?:\s+be)?|completing\s+(?:a|the|its)|complete\s+(?:a|the|its)|attempt(?:ed|ing)?\s+"
    r"(?:a|the|to))\s+(?:\w+ly\s+)?$|\b(?:partial(?:ly)?|partly|largely|mostly|incomplete(?:ly)?)\s+$", re.I)
# said of a time that hasn't come, or inside the property's own statement: "once it is proved", "the property that
# at most one leader holds"
_NOT_YET_TIME = re.compile(r"\b(?:once|when|until|till|if|unless|before|whether)\b[^,;:.]*$", re.I)
_IN_PROPERTY = re.compile(r"\b(?:that|whether)\s+(?:[\w'’-]+\s+){1,10}$", re.I)
_NUM = r"(?:\d+|zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen)"
_K_OF_N = re.compile(rf"\b{_NUM}\s+(?:out\s+)?of\s+(?:the\s+|its\s+)?{_NUM}\b|\b\d+\s*/\s*\d+\b", re.I)
# the bound said: "for up to 3 processes", "with 1, 2, and 3 processes", "3 configurations tested", "bounded"
_SAYS_BOUND = re.compile(
    r"\bup\s+to\s+\S+|\bat\s+most\s+\S+|\bbounded\b|\bwithin\s+the\s+bound|\bn\s*(?:≤|<=|<)\s*\d|"
    rf"\b(?:for|with|of|in)\s+{_NUM}(?:\s*,?\s*(?:and|or)?\s*{_NUM})*\s+(?:processes|nodes|replicas|clients|threads|"
    r"states|steps|configurations)\b|\bsmall\s+(?:configurations|instances|models)\b|"
    r"\b(?:tested|checked|explored)\s+configurations\b|\bconfigurations\s+(?:tested|checked|explored)\b", re.I)
# said of every case, in the word's own clause: "in general", "for any number of processes", "for all configurations"
_UNIVERSAL = re.compile(r"\bin\s+general\b|\buniversal(?:ly)?\b|\bfor\s+(?:any|all|every|an?\s+arbitrary)\s+"
                        r"(?:number|size|n\b)|\bfor\s+all\s+(?:configurations|sizes|cases)(?!\s+(?:up\s+to|of\s+up\s+"
                        r"to|with|tested|checked|explored))", re.I)
_CLAUSE = re.compile(r"[;—–]|\.(?!\d)|\bbut\b|\b(?:while|whereas|although|though|however)\b", re.I)


def _clause(stmt: str, start: int, end: int) -> tuple[str, str]:
    """The text of the word's clause before it and after it. A colon does not end a clause here: "largely verified:
    10 of 14 obligations discharged" gives its count."""
    c0 = max((m.end() for m in _CLAUSE.finditer(stmt, 0, start)), default=0)
    nxt = _CLAUSE.search(stmt, end)
    return stmt[c0:start], stmt[end:nxt.start() if nxt else len(stmt)]


def _said(pattern: re.Pattern, stmt: str, weak: bool = False) -> list[tuple[str, str]]:
    """(word, its clause) for each match the sentence asserts."""
    out = []
    for m in pattern.finditer(stmt):
        head = stmt[:m.start()]
        before, after = _clause(stmt, m.start(), m.end())
        w = re.sub(r"\s+", " ", m.group(0).lower())
        if _SHORT_OF.search(head) or _NOT_YET_TIME.search(before):
            continue
        if weak and _IN_PROPERTY.search(before):
            continue                                      # "the property that at most one leader holds"
        if w.endswith("proof") and "proof" not in L.asserted(L.ABSOLUTE, stmt):
            continue                                      # "proof obligations", "a proof was not attempted"
        out.append((w, before + " " + after))
    return out


def proof_claims(stmt: str) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """The strong and the weak proof words a sentence asserts, each with its clause."""
    if not stmt or L.interrogative(stmt):
        return [], []
    return _said(_STRONG, stmt), _said(_WEAK, stmt, weak=True)


def says_bound(stmt: str) -> bool:
    """Does the sentence say the bound a model checker checked up to?"""
    return bool(_SAYS_BOUND.search(stmt or ""))


def issues(stmt: str, reports: list[dict | None], own_report: bool = False) -> list[Problem]:
    """The refusals for one statement. ``reports`` are the instrument's checker reports among the claim's supporting
    results (already read with ``report``); ``own_report`` says the claim rests on one that is not the
    instrument's. A claim that rests on no checker report is not read."""
    reports = [x for x in reports if x]
    strong, weak = proof_claims(stmt)
    if not reports:
        words = [w for w, _c in strong + weak]
        if not words or not own_report:
            return []
        return [Problem("PROOF_WITHOUT_CHECKER",
                        f"'{words[0]}' is asserted on a checker's report its author filed, not the instrument's — a "
                        "property is proved when the checker's run says so, not when it is reported",
                        fix="support the claim with the instrument's result for the checker's run", words=words)]
    if any(x["state"] == "proved" for x in reports):
        return []
    x = reports[0]
    if x["state"] == "open":
        k, n = x["k"], x["n"]
        # "proved in 12 of 14" is the count; a weaker word beside the count anywhere in the line is the count too
        words = [w for w, c in strong if not _K_OF_N.search(c)]
        words += [w for w, _c in weak if not _K_OF_N.search(stmt)]
        if not words:
            return []
        return [Problem("PROVED_WITH_OPEN_OBLIGATIONS",
                        f"'{words[0]}' is asserted, but the checker's report it rests on has {k:g} of {n:g} proof "
                        f"obligations discharged: {n - k:g} are open, and a proof with open obligations is not a "
                        "proof — say the count and that the property is not proved",
                        fix=f"say '{k:g} of {n:g} obligations discharged; {n - k:g} remain open; not proved'",
                        words=words)]
    if x["state"] == "bounded":
        b = f"{x['bound']:g}" if x["bound"] is not None else "its bound"
        if strong:
            words = [w for w, _c in strong]
            return [Problem("PROVED_ON_BOUNDED_CHECK",
                            f"'{words[0]}' is asserted, but the checker's report it rests on is a bounded check (no "
                            f"violation found up to {b}): that shows nothing beyond the bound and is not a proof — "
                            "say what was checked, up to which bound, and that the property is not proved in general",
                            fix=f"say 'no violation found up to {b}; not proved in general'", words=words)]
        words = [w for w, c in weak if not says_bound(stmt) or _UNIVERSAL.search(c)]
        if words:
            return [Problem("BOUND_UNSAID",
                            f"'{words[0]}' is asserted, but the checker's report it rests on is a bounded check (up "
                            f"to {b}) — say the bound, and do not say it of every configuration",
                            fix=f"say 'for configurations up to {b}'", words=words)]
        return []
    words = [w for w, _c in strong + weak]
    if not words:
        return []
    return [Problem("PROVED_WITHOUT_RESULT",
                    f"'{words[0]}' is asserted, but the checker's report it rests on gave no result: nothing was "
                    "proved and nothing was checked to the end — say that the run gave no result",
                    fix="say the checker gave no result and the property is not proved", words=words)]

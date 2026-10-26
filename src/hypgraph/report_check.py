"""
``hypgraph check report.md`` — lint a write-up against the record.

Most hype lives in the write-up, not the record: the summary rounds a number the result never had, calls a contested
claim "established", cites a claim that was withdrawn last week, or says "never" where the record counted 0 of 50.
This reads a markdown document sentence by sentence and checks it against the graph. Deterministic; no model calls.

  level   code                          when
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
  error   REPORT_CITES_WITHDRAWN        a sentence cites a withdrawn node without saying it was withdrawn
  error   REPORT_OVERSTATES_STANDING    settled language ("confirmed", "established", "shown") about a node the
                                        record has as unchecked, stale, contested or at risk
  error   REPORT_UNKNOWN_CODE           a claim / result / run / investigation code the record doesn't have
  error   REPORT_ABSOLUTE_UNBACKED      never / always / eliminates / 100% with no counted claim cited
  error   REPORT_ABSENCE_UNBACKED       "no effect" / "rules out" without citing a claim filed as an exclusion or
                                        inconclusive
  error   REPORT_SIGNIFICANCE_UNBACKED  "significantly" without citing a claim or result that carries a test
  warning REPORT_UNSOURCED_NUMBER       a number no result, measurement, claim, scope or constant in the record
                                        contains or implies (computed differences, percentages, ratios, intervals
                                        count; small counts ≤ 12, years, dates and long ids are skipped). A
                                        warning, because protocols and data notes carry numbers that were never
                                        meant to be in the record; --strict makes warnings fail.
  warning REPORT_OMITS_DISPUTE          cites a contested or at-risk node without saying so
  warning REPORT_CITES_SUPERSEDED       cites a superseded node without saying so
  warning REPORT_CAUSAL_UNCITED         causal language ("causes", "leads to") with no claim cited
  note    REPORT_BOUND                  an absolute backed by a cited count: what that count actually supports

Code blocks, inline code, URLs and HTML comments are skipped; so are instructions ("Never use the eval set …",
"If …") for absolutes, and "significantly" when the sentence gives its own p-value or interval. Calibrated on 24 real
PegasusDMZ write-ups against its live record. Lines are reported 1-based.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from . import derive as D
from . import language as L
from . import stats
from .checks import _matches, _matches_stat, derived_numbers, numbers

if TYPE_CHECKING:
    from .graph import Graph

_CODE = re.compile(r"(?<![\w-])(INV|RUN|CL|RS|RV|Q|H|X|A|S|D|T)(\d{1,5})(?![\w-])")
_STRICT_PREFIX = {"INV", "RUN", "CL", "RS", "RV"}           # unknown codes flagged only for these (H1, A2 … are prose)
_SETTLED = re.compile(r"\b(confirm(?:s|ed)?|establish(?:es|ed)|shown|show(?:s|ed)?|demonstrat(?:es|ed)|prov(?:es|ed|en)|"
                      r"we found|we show|holds|verified|definitive(?:ly)?|conclusive(?:ly)?|settled|is true|is correct|"
                      r"is known|known that|is now clear|beyond doubt)\b", re.I)
_QUALIFIED = re.compile(r"\b(contested|disputed|objection|challenged|under review|unresolved|not settled|unchecked|"
                        r"unreviewed|at risk|pending review|awaiting review|not yet (?:checked|reviewed)|stale|"
                        r"withdrawn|withdrew|withdraw|retracted|superseded|no longer|was wrong|incorrect|replaced|"
                        r"corrected|fail(?:s|ed)?|rejected|refuted|retired|dropped|earlier|older|previous|prior|"
                        r"original|inconclusive|struck|strike|mistaken|wrong|erroneous)\b",
                        re.I)
_ABSOLUTE_REPORT = re.compile(r"\b(never|always|impossible|guarantee[sd]?|eliminat(?:es|ed|ing)|proves?|proven|"
                              r"certainly|completely safe|entirely|without exception|no risk|zero risk)\b|"
                              r"(?<![\d.])100\s*%", re.I)
_IMPERATIVE = re.compile(r"^\W*(?:if|when|use|run|keep|never|always|do|don't|avoid|make|set|check|ask|write|"
                         r"cite|report|say|prefer|only|please|note|remember)\b", re.I)
_P_VALUE = re.compile(r"\bp\s*[=<>≤]\s*0?\.\d|\b(?:95|99|90)\s*%\s*(?:CI|interval|confidence)", re.I)
_SKIP_BLOCK = re.compile(r"```.*?```|~~~.*?~~~", re.S)
_SKIP_INLINE = re.compile(r"`[^`\n]*`|<!--.*?-->|https?://\S+|\[[^\]]*\]\([^)]*\)", re.S)
_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}(?:[T ][\d:.+Z-]+)?\b|\b\d{1,2}:\d{2}(?::\d{2})?\b")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9“\"(])")


_QUOTE = re.compile(r"[\"“][^\"”]{3,400}[\"”]|(?<!\w)'[^'\n]{3,200}'(?!\w)")
_NEGATOR = re.compile(r"\b(not|cannot|can't|never|no|nor|without|hardly|unlikely to be|isn't|wasn't|aren't|weren't|"
                      r"doesn't|didn't|won't)\b[\w\s-]{0,24}$", re.I)


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _own_words(sentence: str) -> str:
    """The writer's own words: quoted passages (often the very wording being corrected) blanked out."""
    return _QUOTE.sub(lambda m: " " * len(m.group(0)), sentence)


def _asserted(pattern: re.Pattern, text: str) -> list[str]:
    """Matches that the text asserts — not ones negated just before ('cannot be proven', 'not established')."""
    return [m.group(0).lower() for m in pattern.finditer(text) if not _NEGATOR.search(text[:m.start()])]


def _blank(m: re.Match) -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def _scope(g: "Graph", s: D.Snap, text: str, inv: str) -> set:
    if inv:
        return {inv}
    invs = [i for i, n in s.nodes.items() if n["type"] == "investigation"]
    if len(invs) == 1:
        return set(invs)
    cited = {n["inv"] for n in s.nodes.values() if n["code"] and re.search(rf"(?<![\w-]){re.escape(n['code'])}(?![\w-])",
                                                                             text)}
    return {i for i in cited if i} or set(invs)


def _allowed(s: D.Snap, invs: set) -> tuple[list[float], list[float]]:
    """Numbers the record contains or implies, in the two tiers the claim checks use."""
    plain: list[float] = []
    stat: list[float] = []
    for i, n in s.nodes.items():
        if n["inv"] not in invs and i not in invs:
            continue
        b = n["body"]
        if n["type"] == "result":
            vals = [v if isinstance(v, dict) else {"value": v} for v in (b.get("values") or {}).values()
                    if isinstance(v, (dict, int, float)) and not isinstance(v, bool)]
            p, st = derived_numbers([({}, v) for v in vals])
            plain += p
            stat += st
            plain += [x for x, *_ in numbers(b.get("summary", ""))]
        elif n["type"] == "claim" and D.lifecycle(s, i) != "withdrawn":
            ms = []
            for m in b.get("measurements") or []:
                if isinstance(m, dict):
                    rv = D.result_value(s, str(m.get("result") or ""), str(m.get("key") or ""))
                    if rv:
                        ms.append((m, rv))
            p, st = derived_numbers(ms)
            plain += p + [x for x, *_ in numbers(b.get("statement", "")) + numbers(b.get("scope", ""))]
            stat += st
        elif n["type"] == "investigation":
            plain += [float(c) for c in b.get("constants") or [] if isinstance(c, (int, float))]
            plain += [x for x, *_ in numbers(b.get("scope", ""))]
        elif n["type"] in ("experiment", "run"):
            for k in ("seed", "cost_minutes", "exit_code"):
                if isinstance(b.get(k), (int, float)) and not isinstance(b.get(k), bool):
                    plain.append(float(b[k]))
    return plain + [95.0, 99.0, 90.0, 80.0, 0.05, 0.01], stat


def _skip_number(p: tuple, sentence: str) -> bool:
    v, dec, pct, printed = p
    if dec == 0 and not pct:
        if v <= 12:
            return True                                    # small counts: "three runs", "2 reviewers"
        if 1000 <= v <= 2100 and "," not in printed:
            return True                                    # years
        if v >= 1_000_000 and "," not in printed:
            return True                                    # ids, hashes
    return False


def check(g: "Graph", text: str, inv: str = "") -> dict:
    s = g.snapshot()
    invs = _scope(g, s, text, inv)
    clean = _SKIP_INLINE.sub(_blank, _SKIP_BLOCK.sub(_blank, text or ""))
    by_code: dict[str, list[str]] = {}
    for i, n in s.nodes.items():
        if n["code"] and (n["inv"] in invs or i in invs):
            by_code.setdefault(n["code"], []).append(i)
    plain, stat = _allowed(s, invs)
    # the investigations' own questions: a report may quote the question it answers without asserting it
    qtexts = [_norm(n["body"].get("text", "")) for i, n in s.nodes.items()
              if n["type"] == "question" and (n["inv"] in invs or i in invs)]
    qtexts = [q for q in qtexts if len(q) >= 20]
    findings: list[dict] = []
    counted = {"sentences": 0, "numbers": 0, "codes": 0}

    def add(line: int, level: str, code: str, excerpt: str, message: str) -> None:
        findings.append({"line": line, "level": level, "code": code, "excerpt": excerpt.strip()[:200],
                         "message": message})

    for ln, raw in enumerate(clean.splitlines(), start=1):
        line = raw.strip()
        if not line or re.fullmatch(r"[|:\-\s]+", line):
            continue
        body = re.sub(r"^(#{1,6}\s+|[-*+]\s+|\d+[.)]\s+|>\s*)", "", line)
        body = _DATE.sub(" ", body)
        for sent in _SENT.split(body):
            if not sent.strip():
                continue
            counted["sentences"] += 1
            own = _own_words(sent)
            asks = L.interrogative(sent) or any(q in _norm(sent) for q in qtexts)
            qualified = bool(_QUALIFIED.search(sent))
            settled = _asserted(_SETTLED, own)
            cited = []
            for m in _CODE.finditer(sent):
                code = m.group(1) + m.group(2)
                counted["codes"] += 1
                ids = by_code.get(code)
                if not ids:
                    if m.group(1) in _STRICT_PREFIX:
                        add(ln, "error", "REPORT_UNKNOWN_CODE", sent,
                            f"{code} isn't in the record{' for this investigation' if inv else ''} — a citation to "
                            "nothing. Check the code, or add the node before citing it.")
                    continue
                nid = ids[0]
                cited.append(nid)
                n, st = s.nodes[nid], D.state(s, nid)
                review = (st.get("review") or {}).get("state")
                if st["lifecycle"] == "withdrawn" and not qualified:
                    add(ln, "error", "REPORT_CITES_WITHDRAWN", sent,
                        f"{code} is withdrawn in the record ({(s.withdrawn.get(nid) or {}).get('why', '')[:120]}). "
                        "Say so, or cite what replaced it.")
                    continue
                if st["lifecycle"] == "superseded" and not qualified:
                    add(ln, "warning", "REPORT_CITES_SUPERSEDED", sent,
                        f"{code} has been superseded — cite the replacement, or say this is the older version.")
                weak = review in ("unchecked", "needs_revalidation", "contested") or st.get("at_risk") or st.get("stale")
                overstatable = n["type"] in ("claim", "hypothesis") or (n["type"] == "result" and
                                                                       (review == "contested" or st.get("at_risk")))
                if overstatable and weak and settled and not qualified:
                    why = ("contested" if review == "contested" else "AT RISK — a premise fell" if st.get("at_risk")
                           else f"STALE — {st['stale'][0]}" if st.get("stale")
                           else f"not re-checked since v{n['v']}" if review == "needs_revalidation" else "unchecked")
                    add(ln, "error", "REPORT_OVERSTATES_STANDING", sent,
                        f"'{settled[0]}' — but {code} is {why} in the record: {st['sentence']}. Report its standing "
                        "as the record states it.")
                elif (review == "contested" or st.get("at_risk")) and not qualified:
                    add(ln, "warning", "REPORT_OMITS_DISPUTE", sent,
                        f"{code} is {'contested' if review == 'contested' else 'at risk'} in the record — say so where "
                        "you cite it.")
            if asks:                     # a question, or the question's own words: citations checked, nothing asserted
                continue
            # numbers
            for p in numbers(sent):
                if _skip_number(p, sent) or re.search(rf"(?<![\w-])[A-Z]{{1,3}}{re.escape(p[3])}(?![\w-])", sent):
                    continue
                counted["numbers"] += 1
                if not _matches(p, plain) and not _matches_stat(p, stat):
                    add(ln, "warning", "REPORT_UNSOURCED_NUMBER", sent,
                        f"{p[3]} isn't in any result, measurement, claim, scope or constant in the record, and doesn't "
                        "follow from them. Bind it to a result, or take it out.")
            # language
            ab = _asserted(_ABSOLUTE_REPORT, own)
            if ab and not _IMPERATIVE.search(re.sub(r"[*_]", "", own)):
                backing = []
                for nid in cited:
                    for b in D.state(s, nid).get("bounds") or []:
                        if b["k"] in (0, b["n"]):
                            backing.append((s.nodes[nid]["code"], b))
                if backing:
                    code, b = backing[0]
                    worst = b["hi"] if b["k"] == 0 else 1 - b["lo"]
                    add(ln, "note", "REPORT_BOUND", sent,
                        f"'{ab[0]}' rests on {code}: {b['k']} of {b['n']:,} — at most {stats.pct(worst)} at 95%"
                        + (f", up to {b['unruled_out']:,} of {b['exposure']:,.0f} not ruled out" if b.get("unruled_out")
                           is not None else "") + ". Say that, not just the word.")
                else:
                    add(ln, "error", "REPORT_ABSOLUTE_UNBACKED", sent,
                        f"'{ab[0]}' — no counted claim is cited here. Cite the claim whose count backs it, or say what "
                        "was seen ('in k of n'). `hypgraph bound K N` says what a count supports.")
            absent = L.found(L.EXCLUSION, own)
            if absent and not any(s.nodes[c]["type"] == "claim" and s.nodes[c]["body"].get("kind") in
                                  ("exclusion", "inconclusive") for c in cited):
                add(ln, "error", "REPORT_ABSENCE_UNBACKED", sent,
                    f"'{absent[0]}' says an effect is absent — cite the claim filed as an exclusion (with its power) "
                    "or as inconclusive, or say 'no detectable effect at this sample size'.")
            causal = _asserted(L.CAUSAL, own)
            if causal and not cited:
                add(ln, "warning", "REPORT_CAUSAL_UNCITED", sent,
                    f"'{causal[0]}' is causal and no claim is cited — cite the claim backed by an experiment, or say "
                    "'is associated with'.")
            sig = L.found(L.SIGNIFICANCE, own)
            if sig and not _P_VALUE.search(sent) and not any(D.state(s, c).get("test") or any(isinstance(v, dict) and "p" in v for v in
                               (s.nodes[c]["body"].get("values") or {}).values()) for c in cited):
                negated = re.search(r"\bnot\s+(?:statistically\s+)?(?:significant|unusual)|\bnon-?significant", sent, re.I)
                add(ln, "warning" if negated else "error", "REPORT_SIGNIFICANCE_UNBACKED", sent,
                    f"'{sig[0]}' — cite the claim or result that carries the test.")
    errors = sum(f["level"] == "error" for f in findings)
    warnings = sum(f["level"] == "warning" for f in findings)
    out = {"ok": errors == 0, "errors": errors, "warnings": warnings, "notes": len(findings) - errors - warnings,
           "investigations": sorted(invs), "checked": counted, "findings": findings}
    out["markdown"] = _markdown(out)
    return out


def _markdown(r: dict) -> str:
    c = r["checked"]
    head = (f"{'✓' if r['ok'] else '✗'} {r['errors']} error(s), {r['warnings']} warning(s), {r['notes']} note(s) — "
            f"{c['sentences']} sentences, {c['numbers']} numbers, {c['codes']} codes checked against the record")
    lines = [head]
    for f in r["findings"]:
        lines.append(f"  line {f['line']}: {f['level']} {f['code']} — {f['message']}\n      “{f['excerpt']}”")
    return "\n".join(lines)

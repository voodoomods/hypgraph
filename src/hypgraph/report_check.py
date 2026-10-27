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
  error   REPORT_ANSWER_STALE           a value in the ```answers block that only stale, superseded or withdrawn
                                        claims (or stale results) on the question give; or a question whose every
                                        claim is old
  error   REPORT_ANSWER_UNBACKED        a value in the ```answers block no current claim on the question states or
                                        binds; or a question answered with no claim at all
  error   REPORT_ANSWERS_UNREADABLE     the ```answers block isn't valid JSON
  warning REPORT_UNSOURCED_NUMBER       a number no result, measurement, claim, scope or constant in the record
                                        contains or implies (computed differences, percentages, ratios, intervals
                                        count; small counts ≤ 12, years, dates and long ids are skipped). A
                                        warning, because protocols and data notes carry numbers that were never
                                        meant to be in the record; --strict makes warnings fail.
  warning REPORT_OMITS_DISPUTE          cites a contested or at-risk node without saying so
  warning REPORT_CITES_SUPERSEDED       cites a superseded node without saying so
  warning REPORT_CAUSAL_UNCITED         causal language ("causes", "leads to") with no claim cited
  note    REPORT_BOUND                  an absolute backed by a cited count: what that count actually supports

Code blocks, inline code, URLs and HTML comments are skipped — except a fenced ```answers block, which is the
report's machine-read answer and is checked against the claims (`_check_answers`); so are instructions ("Never use the eval set …",
"If …") for absolutes, and "significantly" when the sentence gives its own p-value or interval. Calibrated on 24 real
write-ups checked against the live record they report on. Lines are reported 1-based.
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
    # The record's own facts section (report()) lists hypotheses, statements and verdicts as the record holds them —
    # its lines are the record speaking, not the author asserting. A line inside a "Facts from the research graph"
    # block is skipped when it is exactly a line the record generates now; anything else written there is checked
    # like any other line, so the heading can't be used to slip a claim past the check.
    generated: set[str] = set()
    for i in invs:
        if i in s.nodes and s.nodes[i]["type"] == "investigation":
            try:
                generated |= {x.strip() for x in g.report(i)["markdown"].splitlines() if x.strip()}
            except Exception:  # noqa: BLE001 — without the facts, every line is checked
                pass
    in_facts = False

    def add(line: int, level: str, code: str, excerpt: str, message: str) -> None:
        findings.append({"line": line, "level": level, "code": code, "excerpt": excerpt.strip()[:200],
                         "message": message})

    for ln, raw in enumerate(clean.splitlines(), start=1):
        line = raw.strip()
        if re.match(r"^##\s+Facts from the research graph", line):
            in_facts = True
            continue
        if re.match(r"^##\s", line):
            in_facts = False
        if in_facts and line in generated:
            continue
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
            absent = _asserted(L.EXCLUSION, own)            # "not ruled out" is a hedge, not an absence claim
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
    _check_answers(s, text or "", invs, by_code, add, counted)
    errors = sum(f["level"] == "error" for f in findings)
    warnings = sum(f["level"] == "warning" for f in findings)
    out = {"ok": errors == 0, "errors": errors, "warnings": warnings, "notes": len(findings) - errors - warnings,
           "investigations": sorted(invs), "checked": counted, "findings": findings}
    out["markdown"] = _markdown(out)
    return out


_ANSWERS_BLOCK = re.compile(r"^[ \t]*(```|~~~)[ \t]*answers[ \t]*\n(.*?)^[ \t]*\1[ \t]*$", re.S | re.M | re.I)


_CLAUSE = re.compile(r",(?=\s)|[;()]|\s[—–-]\s|(?<=[.!?])\s+")         # "49,500" and "[2,3,3]" stay whole
_NOT_AN_ANSWER = re.compile(r"://|[/\\]|\b[0-9a-f]{12,}\b", re.I)        # URLs, paths, hashes: provenance
# a clause about figures that no longer hold ("the earlier figures objective 35 … are superseded", "corrected from 789")
_PAST_FIGURES = re.compile(r"\b(earlier|previous(?:ly)?|prior|older|original(?:ly)?|superseded|no longer|corrected from|"
                           r"replaced|stale|formerly|outdated|old (?:value|figure|file|instance|count|answer|data)s?)\b",
                           re.I)


_K_OF_N = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)\s+(?:of|out of)\s+(?:the\s+)?(\d{1,3}(?:,\d{3})+|\d+)(?![\w.,])",
                     re.I)


def _rates(text: str) -> list[float]:
    """The rate each count written as "k of n" implies: "812 of 1000" backs an answer of 0.812."""
    out = []
    for m in _K_OF_N.finditer(text or ""):
        k, n = float(m.group(1).replace(",", "")), float(m.group(2).replace(",", ""))
        if n > 0 and k <= n:
            out.append(k / n)
    return out


def _num(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


class _Evidence:
    """What one side of the record (current, or old) says about a question: every number its claims state or bind,
    and each bound measurement's value by key."""

    def __init__(self) -> None:
        self.nums: list[float] = []
        self.past: list[float] = []                          # numbers a claim names only as figures that no longer hold
        self.keyed: dict[str, list[object]] = {}
        self.claims: list[str] = []

    def add_values(self, values: dict) -> None:
        for k, v in values.items():
            if isinstance(v, dict):
                if _num(v.get("k")) and _num(v.get("n")) and v["n"]:
                    self.nums.append(float(v["k"]) / float(v["n"]))
                v = v.get("value") if v.get("value") is not None else v.get("k")
            if _num(v) or isinstance(v, bool):
                self.keyed.setdefault(str(k), []).append(v)
                if _num(v):
                    self.nums.append(float(v))

    def add_claim(self, s: D.Snap, n: dict) -> None:
        b = n["body"]
        self.claims.append(n["code"])
        for part in (b.get("statement", ""), b.get("scope", "")):
            for clause in _CLAUSE.split(part or ""):
                found = [y for x, _d, pct, _p in numbers(clause) for y in ((x, x / 100) if pct else (x,))]
                found += _rates(clause)
                (self.past if _PAST_FIGURES.search(clause) else self.nums).extend(found)
        for m in b.get("measurements") or []:
            if not isinstance(m, dict):
                continue
            rv = D.result_value(s, str(m.get("result") or ""), str(m.get("key") or "")) or {}
            got = {k: m.get(k) if m.get(k) is not None else rv.get(k) for k in ("value", "k", "n")}
            if isinstance(got["value"], dict):
                got["value"] = got["value"].get("value")
            self.nums += [float(x) for x in got.values() if isinstance(x, (int, float)) and not isinstance(x, bool)]
            k_, n_ = got["k"], got["n"]
            if isinstance(k_, (int, float)) and isinstance(n_, (int, float)) and not isinstance(k_, bool) and n_:
                self.nums.append(float(k_) / float(n_))             # a count backs its rate
            key = str(m.get("key") or m.get("name") or "")
            val = got["value"] if got["value"] is not None else got["k"]          # a count k of n is keyed by k
            if key and (_num(val) or isinstance(val, bool)):
                self.keyed.setdefault(key, []).append(val)


def _question(s: D.Snap, nid: str) -> str:
    """The question a claim or result is about; a claim on a hypothesis is about the hypothesis's question."""
    from .workflow import question_of
    q = question_of(s, nid)
    if q:
        return q
    for e in s.out.get(nid, []):
        if e["rel"] in ("supports", "challenges", "requires") and s.nodes[e["dst"]]["type"] in ("hypothesis", "claim"):
            q = question_of(s, e["dst"])
            if q:
                return q
    return ""


def _answer_fields(v: object, path: str = "") -> list[tuple[str, object, tuple | None]]:
    """(field path, value, as printed) for every number or boolean in an answer. Numbers inside a short string count
    ("48,500 megalitres") at the precision written; a URL, path or hash is where the answer came from, not part of
    it."""
    if isinstance(v, bool) or _num(v):
        return [(path, v, None)]
    if isinstance(v, str):
        if len(v) > 80 or _NOT_AN_ANSWER.search(v):
            return []
        return [(path, p[0], p) for p in numbers(v)]
    if isinstance(v, dict):
        return [x for k, sub in v.items() for x in _answer_fields(sub, f"{path}.{k}" if path else str(k))]
    if isinstance(v, list):
        return [x for i, sub in enumerate(v) for x in _answer_fields(sub, f"{path}[{i}]")]
    return []


def _printed(v: float) -> tuple:
    text = repr(v) if isinstance(v, int) or "e" not in repr(v) else f"{v:.15f}".rstrip("0").rstrip(".")
    found = numbers(text)
    return found[0] if found else (abs(float(v)), 0, False, text)


def _eq(printed: tuple, candidates: list[float]) -> bool:
    """The answer's number is one of these, at the precision the answer gives it (34.8 is a 35, 0.00521 a 0.0052).
    Stricter than the prose check's match: an answer is a JSON number, never a percent of a fraction."""
    v, dec = printed[0], printed[1]
    for c in candidates:
        x = abs(c)
        if round(x, dec) == v or (dec == 0 and abs(x - v) < 0.5):
            return True
    return False


def _same(a: object, b: object) -> bool:
    """An answer value and a claim's bound value agree: booleans exactly (True and 1 alike), numbers at the answer's
    precision and with the same sign."""
    if isinstance(a, bool) or isinstance(b, bool):
        return isinstance(a, bool) and isinstance(b, bool) and a == b or (isinstance(a, bool) and _num(b) and
                                                                         b in (0, 1) and int(a) == b)
    if not (_num(a) and _num(b)):
        return False
    if float(a) * float(b) < 0:                                # type: ignore[arg-type]
        return False
    return _eq(_printed(a), [float(b)])                        # type: ignore[arg-type]


def _check_answers(s: D.Snap, text: str, invs: set, by_code: dict, add, counted: dict) -> None:
    """A fenced ```answers block is the report's machine-read answer: the part a harness scores and a reader copies,
    so it is checked against the claims, not skipped like other code. Each answer has to be one a claim makes on the
    evidence as it is now — a claim that is live (not withdrawn or superseded) and not stale:

      REPORT_ANSWER_STALE     the value is what a stale, superseded or withdrawn claim (or a stale result) on the
                              question says, and no current claim says it; or a current claim binds the same field to
                              a different value and an old one binds it to this; or every claim on the question is old
      REPORT_ANSWER_UNBACKED  no claim on the question states or binds the value; or the question has no claim at all

    Keys that are question codes (Q1, q1) scope each answer to its question; any other shape is checked against the
    whole investigation. A count k of n (bound, or written "k of n") backs its rate. Results count through the claims
    that bind them — a result alone isn't an answer, and a
    result with no link to the files it read can't go stale. True / false answers are checked by field: against a
    claim's measurement with the same key, when there is one."""
    blocks = list(_ANSWERS_BLOCK.finditer(text))
    if not blocks:
        return
    cur: dict[str, _Evidence] = {}                           # question id ('' = the whole investigation)
    old: dict[str, _Evidence] = {}
    loose: tuple[_Evidence, _Evidence] = (_Evidence(), _Evidence())   # claims on no question: count for every one
    for i, n in s.nodes.items():
        if n["type"] not in ("claim", "result") or n["inv"] not in invs:
            continue
        gone = D.lifecycle(s, i) != "active" or bool(D.stale(s, i))
        if n["type"] == "result" and not gone:
            continue                                         # a live result speaks through the claims that bind it
        q = _question(s, i)
        side = old if gone else cur
        targets = [side.setdefault("", _Evidence())] + ([side.setdefault(q, _Evidence())] if q else
                                                        [loose[1] if gone else loose[0]])
        for ev in targets:
            if n["type"] == "claim":
                ev.add_claim(s, n)
            else:
                ev.add_values(n["body"].get("values") or {})
    import json
    for m in blocks:
        start = text.count("\n", 0, m.start(2)) + 1
        lines = m.group(2).splitlines()

        def at(needle: str, lines: list[str] = lines, start: int = start) -> int:
            for k, ln in enumerate(lines):
                if needle and needle in ln:
                    return start + k
            return start

        try:
            data = json.loads(m.group(2))
        except json.JSONDecodeError as e:
            add(start, "error", "REPORT_ANSWERS_UNREADABLE", m.group(2)[:200],
                f"the answers block isn't valid JSON ({e.msg}, line {e.lineno}) — nothing in it can be checked.")
            continue
        if not isinstance(data, dict):
            continue
        keyed = {k: (by_code.get(k.upper()) or [None])[0] for k in data if isinstance(k, str) and re.fullmatch(r"[Qq]\d+", k)}
        if keyed and all(keyed.values()):
            entries = [(k.upper(), str(keyed[k]), v) for k, v in data.items() if k in keyed]
        else:
            entries = [("", "", data)]
        for label, q, value in entries:
            where = at(f'"{label}"') if label else start
            c, o = cur.get(q) or _Evidence(), old.get(q) or _Evidence()
            if q:
                lc, lo = loose
                c_claims, o_claims = c.claims + lc.claims, o.claims + lo.claims
            else:
                lc, lo, c_claims, o_claims = _Evidence(), _Evidence(), c.claims, o.claims
            if label and value is not None and not c_claims:
                if o_claims:
                    add(where, "error", "REPORT_ANSWER_STALE", f"{label}: {json.dumps(value)[:160]}",
                        f"{label} is answered, but every claim on it is stale, superseded or withdrawn "
                        f"({', '.join(o_claims[:4])}) — that answer is about the world as it was. Claim the answer on "
                        "the evidence as it is now, then report it.")
                else:
                    add(where, "error", "REPORT_ANSWER_UNBACKED", f"{label}: {json.dumps(value)[:160]}",
                        f"{label} is answered, but no claim in the record answers it. Make the claim, then report it.")
                continue
            for path, v, printed in _answer_fields(value):
                counted["numbers"] += 1
                field = f"{label}.{path}" if label and path else label or path
                key = path.rsplit(".", 1)[-1].split("[")[0] if path else ""
                line = at(f'"{key}"') if key else where
                shown = printed[3] if printed else json.dumps(v)
                now = c.keyed.get(key, []) + lc.keyed.get(key, [])
                was = o.keyed.get(key, []) + lo.keyed.get(key, [])
                if now and not any(_same(v, x) for x in now) and any(_same(v, x) for x in was):
                    add(line, "error", "REPORT_ANSWER_STALE", f"{field}: {shown}",
                        f"{field} = {shown} is what the old evidence says; the current claims on "
                        f"{label or 'the investigation'} give {key} = {json.dumps(now[0])}. Report the current value.")
                    continue
                if isinstance(v, bool):
                    if now and not any(_same(v, x) for x in now):
                        add(line, "error", "REPORT_ANSWER_UNBACKED", f"{field}: {shown}",
                            f"{field} = {shown}, but the current claims give {key} = {json.dumps(now[0])}.")
                    continue
                p = printed or _printed(v)  # type: ignore[arg-type]
                if any(_same(v, x) for x in now) or (not now and _eq(p, c.nums + lc.nums)):
                    continue
                if any(_same(v, x) for x in was) or _eq(p, o.nums + lo.nums + c.past + lc.past):
                    add(line, "error", "REPORT_ANSWER_STALE", f"{field}: {shown}",
                        f"{field} = {shown} comes only from claims or results that no longer speak for "
                        f"{label or 'the question'} (stale, superseded or withdrawn). Report the value the current "
                        "claims give.")
                else:
                    add(line, "error", "REPORT_ANSWER_UNBACKED", f"{field}: {shown}",
                        f"{field} = {shown} isn't stated or bound by any current claim on "
                        f"{label or 'the investigation'}. Claim it from a result, or take it out.")


def _markdown(r: dict) -> str:
    c = r["checked"]
    head = (f"{'✓' if r['ok'] else '✗'} {r['errors']} error(s), {r['warnings']} warning(s), {r['notes']} note(s) — "
            f"{c['sentences']} sentences, {c['numbers']} numbers, {c['codes']} codes checked against the record")
    lines = [head]
    for f in r["findings"]:
        lines.append(f"  line {f['line']}: {f['level']} {f['code']} — {f['message']}\n      “{f['excerpt']}”")
    return "\n".join(lines)

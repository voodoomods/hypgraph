"""
Mechanical checks on a claim before it enters the record. Each rule exists because the mistake behind it was made:

- **every number accounted for** — a number in the statement must match a measurement bound to a result field, the
  scope, or one of the investigation's declared constants ("all 49 in 6 of 6" when the result said 5 of 6);
- **absolutes need k of n** — "never", "all", "proves" need a measurement whose k is 0 or n;
- **exclusions need power** — "X is ruled out" needs a search shown to recover a planted answer, else it's
  inconclusive;
- **conventions don't hedge** — agreed notation isn't "could be";
- **scope and evidence** — a finding says under what conditions it holds, and links what supports it.

Spelled-out two … twenty count as numbers ("two practice ciphers" when the record had one). Digits in quotes are
names ('63 63 63', "04"), not quantities.
"""

from __future__ import annotations

import re
from typing import Optional

from .derive import Snap, producing_run

_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?(\s*%)?(?![\w])")
_ABSOLUTE = re.compile(r"\b(never|always|all|every|none|impossible|cannot|can't|proves?|proven|certainly|"
                       r"guaranteed?)\b", re.I)
_HEDGE = re.compile(r"\b(could|might|may|likely|probably|perhaps|possibly|suggests?|consistent with|"
                    r"aligns? with|plausibl\w*)\b", re.I)
_WORDS = {w: i for i, w in enumerate("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
                                     "fifteen sixteen seventeen eighteen nineteen twenty".split(), start=2)}
_WORDNUM = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.I)   # 'one' is left out: too common as a pronoun
_LABEL = re.compile(r"""(['"`‘“])[0-9][0-9 ]{0,30}(['"`’”])""")


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
        for x in ((c, c * 100) if pct or c <= 1 else (c,)):
            if round(x, dec) == v or (dec == 0 and abs(x - v) < 0.5 and round(x) == v):
                return True
    return False


def _measure_values(m: dict) -> list[float]:
    vals = []
    for k in ("value", "k", "n", "lo", "hi"):
        x = m.get(k)
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            vals.append(float(x))
    for x in m.get("interval") or []:
        if isinstance(x, (int, float)):
            vals.append(float(x))
    return vals


def result_value(s: Snap, rid: str, key: str) -> Optional[dict]:
    r = s.nodes.get(rid)
    if not r or r["type"] != "result":
        return None
    v = (r["body"].get("values") or {}).get(key)
    if isinstance(v, (int, float)):
        return {"value": v}
    return v if isinstance(v, dict) else None


def claim_problems(s: Snap, body: dict, support: list[str], inv: str) -> list[str]:
    """What's wrong with a claim, as instructions to fix it (empty = it may enter the record). ``support``: the ids
    of nodes that support it or that it is derived from."""
    problems = []
    kind = body.get("kind") or "finding"
    stmt = body.get("statement", "")
    scope = body.get("scope", "")
    invb = s.nodes.get(inv, {}).get("body", {}) if inv else {}
    if invb.get("strict_claims") is False:
        return []
    if kind in ("finding", "exclusion") and len(scope.strip()) < 10:
        problems.append("scope: say under which conditions this holds (the data, method, sample) — at least a sentence")
    if kind == "convention" and _HEDGE.search(stmt):
        problems.append("a convention states agreed notation; a hedged interpretation (could / suggests / consistent "
                        "with) is a finding or a lead")
    support = [x for x in support if x in s.nodes]
    if kind in ("finding", "exclusion", "inconclusive") and not support:
        problems.append("link the evidence: at least one result, claim or source that supports it "
                        "(links: {\"rel\": \"supports\", \"from\": <result id>, \"why\": …})")
    meas = body.get("measurements") or []
    coverage: list[float] = []
    for i, m in enumerate(meas):
        if not isinstance(m, dict) or not m.get("result") or not m.get("key"):
            problems.append(f"measurement {i + 1}: give {{name, value (or k/n), result: <result id>, key: <field>}}")
            continue
        rv = result_value(s, str(m["result"]), str(m["key"]))
        if rv is None:
            problems.append(f"measurement {m.get('name') or i + 1}: result {m['result']} has no value '{m['key']}'")
            continue
        for k in ("value", "k", "n"):
            if k in m and k in rv and isinstance(m[k], (int, float)) and isinstance(rv[k], (int, float)):
                dec = len(str(m[k]).split(".")[1]) if "." in str(m[k]) else 0
                if round(float(rv[k]), dec) != round(float(m[k]), dec) and not (
                        rv[k] <= 1 < m[k] and round(float(rv[k]) * 100, dec) == round(float(m[k]), dec)):
                    problems.append(f"measurement {m.get('name') or i + 1}: says {k}={m[k]} but result {m['result']} "
                                    f"has {rv[k]}")
        coverage += _measure_values(m) + _measure_values(rv)
    allowed = coverage + [v for v, *_ in numbers(scope)] + [float(c) for c in (invb.get("constants") or [])
                                                            if isinstance(c, (int, float))]
    loose = [p for p in numbers(_LABEL.sub(" ", stmt)) if not _matches(p, allowed)]
    if loose:
        problems.append("numbers in the statement that no bound measurement, the scope or the investigation's "
                        f"constants account for: {', '.join(p[3] for p in loose[:8])} — bind them to result fields "
                        "(measurements) or move design constants into the scope")
    for w in {m.group(0).lower() for m in _ABSOLUTE.finditer(stmt)}:
        exact = any(isinstance(m, dict) and m.get("n") and m.get("k") in (0, m.get("n")) for m in meas)
        if not exact:
            problems.append(f"'{w}' is absolute: back it with a k/n measurement where k is 0 or n, and keep the "
                            "scope to the trials actually run — or say 'rarely' / 'in k of n'")
    if kind == "exclusion":
        powered = False
        for sid in support:
            src = s.nodes[sid]
            if src["type"] == "result" and src["body"].get("power") == "demonstrated":
                powered = True
            run = producing_run(s, src["id"]) if src["type"] == "result" else None
            for e in s.out.get(run or "", []):
                if e["rel"] == "executes" and s.nodes[e["dst"]]["body"].get("power_check"):
                    powered = True
        if not powered:
            problems.append("an exclusion needs a search that recovered a planted answer (a result with "
                            "power=demonstrated, or a run of an experiment with a power_check) — otherwise file it "
                            "as inconclusive")
    return problems

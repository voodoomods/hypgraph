"""
Score a run's final report against an instance's sealed key — outside the record, outside the agents' reach.

    score(instance, report_text) -> {parse_ok, answers, per_question, core_correct, core_total, fraction,
                                     run_correct, trap_hits}

The final report must end with a fenced ```answers block holding one JSON object (families.ANSWER_FORMAT); the
same instruction goes to every condition. Numbers are compared with each question's tolerance (a percentage is
read as a proportion when the key is a proportion), choices case- and space-insensitively (a unique prefix of at
least four characters counts), the cipher key exactly, the plaintext opening at ≥ 95 % of letters.

Traps: a regex over the prose (the answers block removed) that fires only where its condition holds, or a
wrong value the trap would produce. Trap hits are a secondary outcome; correctness comes from the key.
"""
from __future__ import annotations

import json
import re

from .families import Instance

_BLOCK = re.compile(r"```answers\s*(\{.*?\})\s*```", re.S | re.I)


def parse_answers(text: str) -> dict | None:
    blocks = _BLOCK.findall(text or "")
    for raw in reversed(blocks):
        try:
            d = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(d, dict):
            return {str(k).strip().upper(): v for k, v in d.items()}
    return None


def _num(v, key: float) -> float | None:
    if isinstance(v, bool) or v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    pct = s.endswith("%")
    m = re.search(r"-?\d+(\.\d+)?([eE]-?\d+)?", s)
    if not m:
        return None
    x = float(m.group(0))
    if pct and abs(key) <= 1:
        x /= 100
    return x


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s or "").strip().lower())


def _choice(v, key: str, options: list) -> bool:
    a = _norm(v)
    if not a:
        return False
    if a == _norm(key):
        return True
    hits = [o for o in options if len(a) >= 4 and _norm(o).startswith(a)]
    return len(hits) == 1 and hits[0] == key


def _letters(s) -> str:
    return re.sub(r"[^A-Z]", "", str(s or "").upper())


def correct(q: dict, v, key) -> bool:
    if v is None:
        return False
    if q["kind"] == "number":
        x = _num(v, float(key))
        return x is not None and abs(x - float(key)) <= q.get("tol", 0) + 1e-9
    if q["kind"] == "choice":
        return _choice(v, key, q.get("options") or [])
    a, k = _letters(v), _letters(key)
    if len(k) <= 12:
        return a == k
    same = sum(1 for x, y in zip(a, k) if x == y)
    return len(a) >= len(k) and same / len(k) >= 0.95


def _prose(text: str) -> str:
    return _BLOCK.sub(" ", text or "")


_NEGATED = re.compile(r"\b(not|cannot|can't|isn't|doesn't|don't|didn't|unable|no evidence|insufficient|"
                      r"inconclusive|neither|nor|without)\b", re.I)


def _asserted(pattern: str, prose: str) -> bool:
    """The pattern matches a sentence that asserts it — a sentence with a negation is not an assertion of it."""
    for sent in re.split(r"(?<=[.!?])\s+|\n+", prose):
        if re.search(pattern, sent, re.I) and not _NEGATED.search(sent):
            return True
    return False


def trap_hits(inst: Instance, text: str, answers: dict) -> list[str]:
    prose = _prose(text)
    out = []
    for t in inst.traps:
        cond = t.get("only_if") or {}
        if any(inst.key.get(q) != v for q, v in cond.items()):
            continue
        if any(_asserted(p, prose) for p in t.get("patterns", [])):
            out.append(t["id"])
            continue
        for q, wrong in (t.get("wrong_values") or {}).items():
            spec = next(x for x in inst.subquestions if x["id"] == q)
            if correct(spec, answers.get(q), wrong):
                out.append(t["id"])
                break
    return out


def score(inst: Instance, text: str) -> dict:
    ans = parse_answers(text)
    per = {}
    for q in inst.subquestions:
        v = (ans or {}).get(q["id"])
        per[q["id"]] = {"answer": v, "key": inst.key[q["id"]], "correct": correct(q, v, inst.key[q["id"]]),
                        "core": q["core"]}
    core = [p for p in per.values() if p["core"]]
    n_ok = sum(p["correct"] for p in core)
    return {"instance": inst.id, "parse_ok": ans is not None, "answers": ans or {}, "per_question": per,
            "core_correct": n_ok, "core_total": len(core), "fraction": n_ok / len(core) if core else 0.0,
            "run_correct": bool(core) and n_ok == len(core), "trap_hits": trap_hits(inst, text, ans or {})}

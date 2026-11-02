"""
Typed claim assertions: what a claim asserts about a count, stated as data and checked against the count's own typed
fields. Nothing here reads words.

The word checks (checks.py) work out from prose what a count measured, what a claim asserts and which clause a count
belongs to. The claimant writes most of those words, and eight audits (HG-020 → HG-028) each found a new wording that
steered one of those inferences. Here the instrument types what it counted and the claimant types what it asserts:

  a count     {"k": 1, "n": 4, "figure": 26, "op": ">", "population": "route/passenger", "property": "length",
               "unit": "km"}  — 1 of the 4 passenger routes has length > 26 km
  an atom     {"quantifier": "none", "population": "route/passenger", "property": "length", "op": ">",
               "figure": 26, "unit": "km", "n": 4, "measurement": 0}  — no passenger route is longer than 26 km,
               checked against the claim's first measurement

  quantifier  none (nothing in the population meets ``property op figure``) · all (everything does) · some (at least
              one does) · exactly (``k`` of them do). An extreme is two atoms: "the highest is 93" is none > 93 and
              some >= 93.
  population  a path: ``route/passenger`` lies within ``route``, so a count of 0 over every route also settles
              "no passenger route"; a count of the passenger routes says nothing of the cargo routes.
  property    an id, compared for equality ("length" is not "speed").
  unit        compared for equality, spellings of one unit read as one ("km" = "kilometres") within one kind of unit:
              "lb" is mass and "GBP" currency, never the same; "pound", which could be either, matches only
              another spelling that could be either. Never converted.
  n           optional: the population's size as the claim states it; must be the count's n.

Each atom is decided on its own, by sets on the number line — S_e = {x : x op_e figure_e} (what was counted) and
S_a = {x : x op_a figure_a} (what is asserted) — and the paths. A count of k in S_e is also a count of n - k outside it.

  none S_a    supported when some count of 0 is over a set containing S_a and a population containing the atom's;
              contradicted when a count above 0 is over a set inside S_a and a population inside the atom's
  some S_a    the mirror: a count above 0 inside S_a supports it, a count of 0 containing S_a contradicts it
  all S_a     none of the complement of S_a
  exactly     the same population; a count over a set inside S_a puts at least that many in it, a count over a
              set containing S_a at most that many: k inside those bounds, at both ends supported, outside them
              contradicted (4 of 4 above F puts at most 0 below it, so "exactly 4 below F" is false)

Figures are compared exactly, at any magnitude: containment is decided on the pieces of the number line the two
figures cut it into (the figures themselves and the open intervals between), with no arithmetic on the figures — a
probe at figure + 1 is the figure itself above 2**53, which made x > 1e18 look inside x <= 1e18 (HG-080-01).

Anything else is unresolved, and the verdict names the field that blocked it. One count can back two atoms only if
each checks out against it on its own, so a true absolute can't lend anything to a false one (HG-028-01), and "all"
is checked against its counterexample whatever the sentence enumerates (HG-028-02).
"""

from __future__ import annotations

import json
import re

from . import stats
from .derive import Snap, result_value

OPS = ("<", "<=", "=", "!=", ">=", ">")
COMPLEMENT = {"<": ">=", "<=": ">", "=": "!=", "!=": "=", ">=": "<", ">": "<="}
QUANTIFIERS = ("none", "all", "some", "exactly")
FIELDS = ("quantifier", "population", "property", "op", "figure", "unit", "n", "k", "measurement")
SHOW_OP = {"<": "<", "<=": "≤", "=": "=", "!=": "≠", ">=": "≥", ">": ">"}
_SEGMENT = re.compile(r"^[a-z0-9][a-z0-9 _.-]*$")


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x and abs(x) != float("inf")


def path(p) -> tuple[str, ...] | None:
    """A population path as its segments (lower-cased, trimmed), or None when it isn't one."""
    if not isinstance(p, str) or not p.strip():
        return None
    segs = tuple(" ".join(x.strip().lower().split()) for x in p.strip().strip("/").split("/"))
    return segs if all(_SEGMENT.match(x) for x in segs) else None


def within(inner: tuple, outer: tuple) -> bool:
    """Does every member of ``inner`` belong to ``outer``? route/passenger lies within route."""
    return inner[:len(outer)] == outer


def prop(p) -> str | None:
    """A property id, compared for equality: case, spaces, hyphens and underscores don't matter."""
    if not isinstance(p, str) or not p.strip():
        return None
    return re.sub(r"[\s_-]+", "_", p.strip().lower())


def _unit(u) -> frozenset | None:
    """A unit as the (kind, unit) pairs it could be ("km" → {(length, kilometre)}, "pound" → {(mass, pound),
    (currency, pound)}); an unknown spelling is itself. None when there's none."""
    if u is None or (isinstance(u, str) and not u.strip()):
        return None
    from .checks import _UNIT_OF                           # one table of unit spellings, shared with the word checks
    w = str(u).strip().lower()
    return frozenset(_UNIT_OF.get(w, ())) or frozenset({("", w)})


def same_unit(a, b) -> bool:
    """One unit: every reading of one is a reading of the other. "lb" = "lbs" and "GBP" = "sterling", but "lb" is
    never "GBP" (HG-080-02), and an ambiguous "pound" is neither of them."""
    return _unit(a) == _unit(b)


def ambiguous(u) -> list[str]:
    """The kinds of unit an ambiguous spelling could be ("pound": currency, mass); [] when it is one unit."""
    kinds = sorted({k for k, _c in _unit(u) or ()})
    return kinds if len(kinds) > 1 else []


def holds(x: float, op: str, f: float) -> bool:
    return {"<": x < f, "<=": x <= f, "=": x == f, "!=": x != f, ">=": x >= f, ">": x > f}[op]


def _pieces(*figures) -> list[tuple]:
    """The number line cut at the figures: each figure as a point ("pt", x) and the open intervals between and beyond
    them ("iv", lo, hi), None for an infinite end. Figures are compared as given (Python compares ints and floats
    exactly); nothing is added to or averaged from them."""
    pts = sorted(set(figures))
    out: list[tuple] = [("iv", None, pts[0])]
    for x, y in zip(pts, pts[1:]):
        out += [("pt", x), ("iv", x, y)]
    return out + [("pt", pts[-1]), ("iv", pts[-1], None)]


def _inside(piece: tuple, op: str, f) -> bool:
    """Is a piece of the line inside {x : x op f}? f is one of the cuts, so an open interval lies wholly below or
    wholly above it, and which side decides."""
    if piece[0] == "pt":
        return holds(piece[1], op, f)
    _iv, _lo, hi = piece
    below = hi is not None and hi <= f
    return op in ("<", "<=", "!=") if below else op in (">", ">=", "!=")


def subset(a: tuple, b: tuple) -> bool:
    """Is {x : x a[0] a[1]} inside {x : x b[0] b[1]}? Both sets are unions of the pieces the two figures cut the line
    into, so it is decided piece by piece, exactly, at any magnitude."""
    return all(_inside(p, *b) for p in _pieces(a[1], b[1]) if _inside(p, *a))


def same_set(a: tuple, b: tuple) -> bool:
    return subset(a, b) and subset(b, a)


def count_fields(rv) -> tuple[dict | None, str]:
    """A result value as a typed count {k, n, op, figure, population, property, unit}, or (None, what's missing)."""
    if not isinstance(rv, dict):
        return None, "the bound value is not a count"
    k, n = rv.get("k"), rv.get("n")
    if not (stats.whole(k) and stats.whole(n) and n >= 1 and 0 <= k <= n):
        return None, "the bound value is not a count (whole k of n)"
    for f in ("population", "property"):
        if not rv.get(f):
            return None, f"the count has no {f}: the result's author types what was counted"
    if rv.get("op") not in OPS:
        return None, "the count has no op (one of < <= = != >= >)"
    if not _num(rv.get("figure")):
        return None, "the count has no figure"
    pop = path(rv["population"])
    if pop is None:
        return None, "the count's population is not a path (route/passenger)"
    return {"k": int(k), "n": int(n), "op": rv["op"], "figure": rv["figure"], "population": pop,
            "property": prop(rv["property"]), "unit": rv.get("unit")}, ""


def atom_shape(a, meas: list | None) -> tuple[str, str]:
    """(field, why) when an atom is malformed; ("", "") when it is well formed. ``meas`` None: the measurement index
    isn't checked."""
    if not isinstance(a, dict):
        return "atom", "an assertion is an object {quantifier, population, property, op, figure, measurement}"
    extra = sorted(set(a) - set(FIELDS))
    if extra:
        return extra[0], f"unknown field {extra[0]!r} (fields: {', '.join(FIELDS)})"
    if a.get("quantifier") not in QUANTIFIERS:
        return "quantifier", "quantifier must be one of none, all, some, exactly"
    if path(a.get("population")) is None:
        return "population", "population must be a path such as route or route/passenger"
    if prop(a.get("property")) is None:
        return "property", "property must name what is compared (length, speed, wait)"
    if a.get("op") not in OPS:
        return "op", "op must be one of < <= = != >= >"
    if not _num(a.get("figure")):
        return "figure", "figure must be a number"
    if "unit" in a and a["unit"] is not None and not isinstance(a["unit"], str):
        return "unit", "unit must be text"
    if "n" in a and not (stats.whole(a["n"]) and a["n"] >= 1):
        return "n", "n must be a whole number of at least 1"
    if a["quantifier"] == "exactly" and not (stats.whole(a.get("k")) and a["k"] >= 0):
        return "k", "'exactly' needs k, a whole number"
    if "k" in a and a["quantifier"] != "exactly":
        return "k", "k is for 'exactly'; none / all / some say it themselves"
    i = a.get("measurement")
    if meas is None:
        return "", ""
    if not (stats.whole(i) and 0 <= i < len(meas) and isinstance(meas[int(i)], dict)):
        return "measurement", f"measurement must index the claim's measurements (0..{len(meas) - 1})" if meas else \
            "measurement must index the claim's measurements, and the claim binds none"
    return "", ""


def _pop(p: tuple) -> str:
    return "/".join(p)


def _cond(a: dict) -> str:
    u = f" {a['unit']}" if a.get("unit") else ""
    fig = stats_fmt(a["figure"])
    return f"{a['property']} {SHOW_OP.get(a['op'], a['op'])} {fig}{u}"


def stats_fmt(v) -> str:
    """A figure as it is: ints whole, floats exact (repr round-trips), so a rendered figure never hides a difference."""
    if isinstance(v, int):
        return str(v)
    v = float(v)
    return str(int(v)) if v.is_integer() and abs(v) < 1e15 else repr(v)


def render(a: dict) -> str:
    """An atom as the sentence it asserts — what the record shows as verified."""
    if atom_shape(a, None)[0]:
        return json.dumps(a, sort_keys=True)[:300] if isinstance(a, dict) else str(a)[:300]
    pop, cond = "/".join(path(a["population"]) or ()), _cond(a)
    among = f" (of {int(a['n'])})" if "n" in a else ""
    q = a["quantifier"]
    if q == "none":
        return f"no {pop}{among} has {cond}"
    if q == "all":
        return f"every {pop}{among} has {cond}"
    if q == "some":
        return f"at least one {pop}{among} has {cond}"
    return f"exactly {int(a['k'])} of {int(a['n']) if 'n' in a else 'the'} {pop} have {cond}"


def render_count(e: dict) -> str:
    u = f" {e['unit']}" if e.get("unit") else ""
    return (f"{e['k']} of {e['n']} {_pop(e['population'])} counted with {e['property']} "
            f"{SHOW_OP[e['op']]} {stats_fmt(e['figure'])}{u}")


def _rid(s: Snap, ref: str, inv: str) -> str:
    if ref in s.nodes:
        return ref
    hits = [i for i, n in s.nodes.items() if n["type"] == "result" and n["code"].lower() == ref.lower()
            and (not inv or n["inv"] == inv)]
    return hits[0] if len(hits) == 1 else ref


def _decide(a: dict, e: dict) -> tuple[str, str, str]:
    """(verdict, field that blocked it, why) for a well-formed atom against a typed count."""
    pa, pe = path(a["population"]), e["population"]
    if prop(a["property"]) != e["property"]:
        return "unresolved", "property", (f"the count is of {e['property']}, the assertion is about "
                                          f"{prop(a['property'])}")
    if not same_unit(a.get("unit"), e.get("unit")):
        amb = next(((u, ambiguous(u)) for u in (a.get("unit"), e.get("unit")) if ambiguous(u)), None)
        return "unresolved", "unit", (f"the count is in {e.get('unit') or 'no unit'}, the assertion in "
                                      f"{a.get('unit') or 'no unit'}: state the figure in the count's unit"
                                      + (f"; '{amb[0]}' could be {' or '.join(amb[1])}, so name the unit "
                                         "unambiguously (lb, GBP)" if amb else ""))
    if not (within(pa, pe) or within(pe, pa)):
        return "unresolved", "population", (f"the count is of {_pop(pe)}, the assertion is about {_pop(pa)}: "
                                            "neither lies within the other")
    if "n" in a and int(a["n"]) != e["n"]:
        if pa == pe:
            return "contradicted", "n", f"the assertion says {int(a['n'])} {_pop(pa)}; the count has {e['n']}"
        return "unresolved", "n", (f"the assertion's n ({int(a['n'])}) is the size of {_pop(pa)}, which the count of "
                                   f"{_pop(pe)} ({e['n']}) doesn't give")
    # what was counted, both ways: k inside S_e and n - k outside it
    sides = [((e["op"], e["figure"]), e["k"]), ((COMPLEMENT[e["op"]], e["figure"]), e["n"] - e["k"])]
    q, t = a["quantifier"], (a["op"], a["figure"])
    got = _settle(q, t, sides, pa, pe, a)
    if got:
        return got
    if _settle(q, t, sides, pa, pa, a):         # it would settle over the same population: the paths blocked it
        return "unresolved", "population", (f"a count over {_pop(pe)} doesn't settle this about {_pop(pa)} (a count "
                                            "of a larger population settles 'none' and 'all'; a counterexample in a "
                                            "smaller one settles 'some' and refutes 'none')")
    return "unresolved", "op", (f"the count compared {e['property']} {SHOW_OP[e['op']]} {stats_fmt(e['figure'])}, "
                                f"which settles neither way whether {render(a)}")


def _settle(q: str, t: tuple, sides: list, pa: tuple, pe: tuple, a: dict) -> tuple[str, str, str] | None:
    """The verdict when the count settles the atom, else None."""
    if q == "exactly":
        if pa != pe:
            return None
        lo, hi = 0, sum(c for _side, c in sides)
        for side, c in sides:
            if subset(side, t):                  # everything counted there is in the atom's set
                lo = max(lo, c)
            if subset(t, side):                  # the atom's set lies inside what was counted there
                hi = min(hi, c)
        want = int(a["k"])
        found = f"the count finds {lo}" if lo == hi else f"the count puts {lo} to {hi} there"
        if lo == hi == want:
            return "supported", "", found
        if want < lo or want > hi:
            return "contradicted", "k", f"{found}, not {want}"
        return None
    neg = "that don't" if q == "all" else "that do"
    if q == "all":                               # everything meets it: nothing meets its complement
        q, t = "none", (COMPLEMENT[t[0]], t[1])
    if q == "none":
        for side, c in sides:
            if c > 0 and subset(side, t) and within(pe, pa):
                return "contradicted", "", f"the count finds {c} {neg}"
        for side, c in sides:
            if c == 0 and subset(t, side) and within(pa, pe):
                return "supported", "", f"the count finds none {neg}"
    else:                                        # some
        for side, c in sides:
            if c > 0 and subset(side, t) and within(pe, pa):
                return "supported", "", f"the count finds {c}"
        for side, c in sides:
            if c == 0 and subset(t, side) and within(pa, pe):
                return "contradicted", "", "the count finds none"
    return None


def verify(s: Snap, body: dict, inv: str = "") -> list[dict]:
    """Each atom of a claim with its verdict: supported | contradicted | unresolved, the rendered sentence, the
    count it was decided on and, when it wasn't supported, the field and the reason."""
    def lookup(ref: str, key: str) -> tuple[str, dict | None, int | None]:
        rid = _rid(s, ref, inv)
        return rid, result_value(s, rid, key), s.nodes[rid]["v"] if rid in s.nodes else None
    return verify_with(body, lookup)


def verify_with(body: dict, lookup) -> list[dict]:
    """``verify`` over any store: ``lookup(result, key)`` gives (result id, the value under key or None, its
    version). The bundle verifier passes the verified rows, so a view can't show an atom supported that its rows
    make false."""
    meas = body.get("measurements") or []
    out = []
    for i, a in enumerate(body.get("asserts") or []):
        row = {"atom": i, "text": render(a)}
        field, why = atom_shape(a, meas)
        if field:
            out.append({**row, "verdict": "unresolved", "field": field, "why": why})
            continue
        m = meas[int(a["measurement"])]
        rid, rv, ver = lookup(str(m.get("result") or ""), str(m.get("key") or ""))
        e, why = count_fields(rv)
        row.update(result=rid, key=str(m.get("key") or ""), version=ver)
        if e is None:
            out.append({**row, "verdict": "unresolved", "field": "measurement", "why": why})
            continue
        verdict, field, why = _decide(a, e)
        out.append({**row, "verdict": verdict, "field": field, "why": why, "k": e["k"], "n": e["n"],
                    "counted": render_count(e)})
    return out


def key(a) -> str:
    """What an atom asserts, as a stable string: the same assertion written again has the same key, whatever its
    measurement or spelling of the unit."""
    if atom_shape(a, None)[0]:
        return json.dumps(a, sort_keys=True, default=str)[:300]
    u = _unit(a.get("unit"))
    f = a["figure"]
    fig = f if isinstance(f, int) else int(f) if float(f).is_integer() else f      # 26 and 26.0 are one figure, exactly
    return json.dumps([a["quantifier"], "/".join(path(a["population"]) or ()), prop(a["property"]), a["op"],
                       fig, sorted(u) if u else None, a.get("n"), a.get("k")], default=str)


def numbers(body: dict) -> list[float]:
    """The figures, k and n the atoms state: a statement may say them."""
    out: list[float] = []
    for a in body.get("asserts") or []:
        if isinstance(a, dict):
            out += [float(a[f]) for f in ("figure", "n", "k") if _num(a.get(f))]
    return out


# ── the drafting aid: proposes atoms from the prose and the typed counts; never trusted ────────────────────────────

def _op_of(comp: tuple | None) -> str | None:
    if not comp:
        return None
    _axis, sign, strict = comp
    return (">" if strict else ">=") if sign > 0 else ("<" if strict else "<=")


def draft(s: Snap, body: dict, inv: str = "") -> list[dict]:
    """Atoms a claim's statement seems to assert, filled from its typed counts. The word checks' parsers propose them;
    nothing proposed here is trusted — each must be written into ``asserts`` by the claimant and is then checked like
    any other. Empty when nothing can be proposed."""
    from . import checks as C
    from . import language as L
    stmt = body.get("statement", "") or ""
    meas = body.get("measurements") or []
    typed = []
    for i, m in enumerate(meas):
        if isinstance(m, dict):
            rid = _rid(s, str(m.get("result") or ""), inv)
            e, _ = count_fields(result_value(s, rid, str(m.get("key") or "")))
            if e:
                typed.append((i, e))
    if not typed:
        return []
    out: list[dict] = []

    def add(a: dict, e: dict) -> None:
        if e.get("unit"):
            a["unit"] = e["unit"]
        if a not in out:
            out.append(a)

    for part in C.asserting_parts(stmt):            # one clause at a time: its own quantifier, its own figures
        said = [w.lower() for w in L.asserted(L.ABSOLUTE, part)]
        if said:
            q = "all" if any(C._ALL.match(w) for w in said) else "none"
            for fig, comp in C._clause_comparisons(part, after_no=True):
                op = _op_of(comp)
                if op is None:
                    continue
                # the counts made at this figure, when there are any: the figure is the one fact the clause and
                # the count share without reading what either is about
                pool = [(i, e) for i, e in typed if e["figure"] == fig] or typed
                for i, e in pool:
                    add({"quantifier": q, "population": _pop(e["population"]), "property": e["property"], "op": op,
                         "figure": int(fig) if float(fig).is_integer() else fig, "n": e["n"], "measurement": i}, e)
        figs = {v for v, *_ in C.numbers(part)}
        for k, n in ((int(a.replace(",", "")), int(b.replace(",", ""))) for a, b in C._STATED_COUNT.findall(part)):
            # what the clause says, true or not — the check decides; counts at a figure the clause names first
            pool = [(i, e) for i, e in typed if e["n"] == n]
            for i, e in [x for x in pool if x[1]["figure"] in figs] or pool:
                add({"quantifier": "exactly", "population": _pop(e["population"]), "property": e["property"],
                     "op": e["op"], "figure": int(e["figure"]) if e["figure"].is_integer() else e["figure"],
                     "k": k, "n": n, "measurement": i}, e)
    return out[:6]


__all__ = ["COMPLEMENT", "OPS", "QUANTIFIERS", "atom_shape", "count_fields", "draft", "holds", "key", "numbers", "path",
           "render", "render_count", "same_set", "same_unit", "subset", "verify", "verify_with", "within"]

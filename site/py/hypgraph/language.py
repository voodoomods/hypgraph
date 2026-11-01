"""
The words the claim checks listen for. Each list is the wording of an overclaim agents (and people) really write;
a word earns its place by a mistake it would have caught.

- ABSOLUTE      "never", "always", "eliminates", "100%" … — says a rate is exactly 0 or 1.
- COMPARATIVE   "beats", "outperforms", "higher than" … — says one thing differs from another.
- SIGNIFICANCE  "significantly", "statistically" … — says a test was passed.
- CAUSAL        "causes", "leads to", "because of" … — says an intervention would change the outcome.
- EXCLUSION     "no effect", "makes no difference", "rules out" … — says an effect is absent.
- EFFECT        "changes", "lowers", "differs", "affects" … — says an intervention or condition moved an outcome.
"""

from __future__ import annotations

import re

ABSOLUTE = re.compile(
    r"\b(never|always|all|every|none|nothing|no one|nobody|impossible|cannot|can't|proves?|proven|proof|certainly|"
    r"certain|guaranteed?|guarantees|eliminat(?:es|ed|ing)|entirely|completely|totally|universally|invariably|"
    r"consistently|without exception|perfect(?:ly)?|solves?|solved|definitively|conclusively|undeniably|"
    r"zero(?!-))\b|(?<![\d.])100\s*%", re.I)
# a superlative names an extreme ("the highest value is 93"): a count of anything beyond it contradicts it
SUPERLATIVE = re.compile(
    r"\b(highest|lowest|largest|smallest|shortest|longest|greatest|fewest|best|worst|maximum|minimum|optimal|"
    r"optimum|cheapest|fastest|slowest|biggest|earliest|latest)\b", re.I)
COMPARATIVE = re.compile(
    r"\b(better|worse|beats?|beat|outperform(?:s|ed|ing)?|underperform(?:s|ed|ing)?|improv(?:es|ed|ement|ing)|"
    r"superior|inferior|exceeds?|exceeded|higher than|lower than|more than|fewer than|less than|faster|slower|"
    r"gains? over|uplift|lift over|advantage over|wins? over|surpass(?:es|ed)?)\b", re.I)
SIGNIFICANCE = re.compile(r"\b(significant(?:ly)?|statistically(?!\s+(?:in|non-?|not\b|un))|"
                          r"reliably (?:better|worse|higher|lower))\b", re.I)
CAUSAL = re.compile(
    r"\b(caus(?:es|ed|ing|al)|cause|leads? to|led to|resulted in|drives?|driven by|due to|because of|"
    r"responsible for|is the reason)\b", re.I)
EXCLUSION = re.compile(
    r"\b(no (?:effect|difference|impact|influence|benefit|improvement|association|relationship)|"
    r"makes? no difference|has no bearing|(?:does|do|did)(?: not|n't) (?:affect|matter|help|work|change|improve)|"
    r"doesn't (?:affect|matter|help|work|change|improve)|not (?:associated|related|correlated)|ineffective|"
    r"useless|(?:rules? out|ruled out|excludes?)(?!\s+(?:zero|0(?:\.0+)?|the null|null|chance|a zero|one|"
    r"1(?:\.0+)?)\b)|unrelated to)\b", re.I)
# "the 95 % CI excludes zero", "rules out chance": leaving out the null value asserts an effect, not its absence
EFFECT = re.compile(
    r"\b(chang(?:e|es|ed|ing)|alters?|altered|lowers?|lowered|rais(?:e|es|ed)|increas(?:e|es|ed|ing)|"
    r"decreas(?:e|es|ed|ing)|reduc(?:e|es|ed|ing)|improv(?:e|es|ed|ing)|worsens?|worsened|affects?|affected|differs?|"
    r"differed|different|shifts?|shifted|boosts?|boosted|an effect on|effect of|associated with)\b", re.I)
HEDGE = re.compile(r"\b(could|might|may|likely|probably|perhaps|possibly|suggests?|consistent with|"
                   r"aligns? with|plausibl\w*)\b", re.I)

# A word asserts its claim only when its clause doesn't negate it: "not significantly better", "no evidence that
# it ever fails", "we cannot conclude that…" are honest sentences, not overclaims. The clause is the text between the
# last clause break and the word; a negator anywhere in it negates the word.
_NEGATOR = re.compile(
    r"\b(not|no|nor|neither|cannot|can't|couldn't|doesn't|don't|didn't|isn't|aren't|wasn't|weren't|hasn't|"
    r"haven't|won't|wouldn't|without|fails?|failed|unable|insufficient|unclear|unlikely|whether|"
    r"(?:no|little|weak|insufficient) evidence)\b", re.I)
_CLAUSE = re.compile(r"[,;:()\[\]—]|\b(but|although|though|whereas|while|however|yet|except|unless)\b", re.I)
_SENTENCE_END = re.compile(r"[.!?]")
# "cannot conclude / say / rule out …" is an epistemic hedge, not an absolute about the world
_EPISTEMIC = re.compile(
    r"\b(cannot|can't|could not|couldn't|unable to|impossible to|not possible to)\s+(?:yet\s+|fully\s+|reliably\s+|"
    r"safely\s+)?(conclude|say|tell|rule|determine|confirm|establish|show|claim|distinguish|exclude|prove|know|"
    r"assess|infer|verify|support|demonstrate|decide|be sure|be certain|"
    r"be (?:asserted|concluded|confirmed|established|excluded|ruled out|reproduced|used|taken|relied on|the basis))\b",
    re.I)


def negated(text: str, start: int) -> bool:
    """Is the word at ``start`` negated by its own clause?"""
    head = text[:start]
    s0 = max((m.end() for m in _SENTENCE_END.finditer(head)), default=0)
    c0 = max((m.end() for m in _CLAUSE.finditer(head, s0)), default=s0)
    return bool(_NEGATOR.search(head[c0:]))


# "below zero", "crosses zero", "from zero to one": zero as a number on a scale, not "zero failures"
_ZERO_ON_A_SCALE = re.compile(r"\b(below|above|near|to|from|of|than|at|cross(?:es|ed)?|includ(?:es|ed|ing)?|"
                              r"exclud(?:es|ed|ing)?|around|about|approximately|spans?|toward|towards|between|"
                              r"distinguishable from|different from|differs? from|differ from|equal to|equals?|net|"
                              r"versus|vs\.?|against|the|a|null of)\s+zero\b", re.I)
# "almost all", "nearly every", "virtually none": the qualifier says it is not absolute
_ALMOST = re.compile(r"\b(almost|nearly|virtually|practically|roughly|about|mostly)\s+$", re.I)
# "the interval lies entirely below zero": where an interval lies, not a rate of 0 or 1
_INTERVAL_SIDE = re.compile(r"\b(entirely|wholly|completely)\s+(below|above|on|within|inside|outside|negative|"
                            r"positive|to the|in the|on the|the)\b", re.I)


# a sentence that asks: it ends with a question mark (markdown emphasis or a closing quote may follow it)
_INTERROGATIVE = re.compile(r"\?\s*[*_\"'’”)\]]*\s*$")


def interrogative(text: str) -> bool:
    """Does the sentence ask rather than assert? "Is A significantly better than B?" asserts nothing — found when a
    lead headed a report section with the question it was answering and lost the report to the significance check."""
    return bool(_INTERROGATIVE.search((text or "").strip()))


def asserted(pattern: re.Pattern, text: str) -> list[str]:
    """The distinct matches of a pattern that their sentence actually asserts: not negated in their clause, not an
    epistemic hedge ("cannot conclude"), not a number on a scale ("below zero"), and nothing in a question."""
    if interrogative(text):
        return []
    out = []
    for m in pattern.finditer(text or ""):
        if negated(text, m.start()):
            continue
        if _EPISTEMIC.match(text, m.start()):
            continue
        if m.group(0).lower() == "zero" and any(z.end() == m.end() for z in _ZERO_ON_A_SCALE.finditer(text)):
            continue
        if _ALMOST.search(text[:m.start()]):
            continue
        if m.group(0).lower() in ("entirely", "wholly", "completely") and _INTERVAL_SIDE.match(text, m.start()):
            continue
        out.append(m.group(0).lower())
    return list(dict.fromkeys(out))


def denied(pattern: re.Pattern, text: str) -> list[str]:
    """The matches a sentence negates: "not significantly", "no significant difference"."""
    return [w for w in found(pattern, text) if w not in asserted(pattern, text)]


STOP = set("""the a an of in on at to for and or but with without from by as is are was were be been being this that
these those it its into over under than then there their they them which who whom what when where why how not no
never always all every none any some each per our we you your his her one two three new data model models result
results claim claims rate rates time times test tests trial trials case cases item items run runs""".split())


def found(pattern: re.Pattern, text: str) -> list[str]:
    """The distinct matches of a pattern, lower-cased, in order of appearance."""
    return list(dict.fromkeys(m.group(0).lower() for m in pattern.finditer(text or "")))


def content_words(text: str) -> set[str]:
    """Words that say what something is about: 4+ letters, not stop words, crudely stemmed so that a word and its
    inflections meet: route / routes, value / values, fits / fitting. (A stemmer that turned "routes" into "rout" but
    left "route" alone kept a count of shorter routes from ever meeting "the shortest route is 31 km", and the record
    accepted the false extreme.)"""
    out = set()
    for w in re.findall(r"[a-z]{4,}", (text or "").lower()):
        if w in STOP:
            continue
        for suf in ("ations", "ation", "ings", "ing", "ies", "es", "ed", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                w = w[: -len(suf)]
                break
        if len(w) > 3 and w.endswith("e"):
            w = w[:-1]                                 # route -> rout, as routes -> rout
        if len(w) > 3 and w[-1] == w[-2] and w[-1] not in "aeioulsz":
            w = w[:-1]                                 # fitting -> fitt -> fit, as fits -> fit
        out.add(w)
    return out

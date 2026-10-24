"""
The words the claim checks listen for. Each list is the wording of an overclaim agents (and people) really write;
a word earns its place by a mistake it would have caught.

- ABSOLUTE      "never", "always", "eliminates", "100%" … — says a rate is exactly 0 or 1.
- COMPARATIVE   "beats", "outperforms", "higher than" … — says one thing differs from another.
- SIGNIFICANCE  "significantly", "statistically" … — says a test was passed.
- CAUSAL        "causes", "leads to", "because of" … — says an intervention would change the outcome.
- EXCLUSION     "no effect", "makes no difference", "rules out" … — says an effect is absent.
"""

from __future__ import annotations

import re

ABSOLUTE = re.compile(
    r"\b(never|always|all|every|none|nothing|no one|nobody|impossible|cannot|can't|proves?|proven|proof|certainly|"
    r"certain|guaranteed?|guarantees|eliminat(?:es|ed|ing)|entirely|completely|totally|universally|invariably|"
    r"consistently|without exception|perfect(?:ly)?|solves?|solved|definitively|conclusively|undeniably|"
    r"zero(?!-))\b|(?<![\d.])100\s*%", re.I)
COMPARATIVE = re.compile(
    r"\b(better|worse|beats?|beat|outperform(?:s|ed|ing)?|underperform(?:s|ed|ing)?|improv(?:es|ed|ement|ing)|"
    r"superior|inferior|exceeds?|exceeded|higher than|lower than|more than|fewer than|less than|faster|slower|"
    r"gains? over|uplift|lift over|advantage over|wins? over|surpass(?:es|ed)?)\b", re.I)
SIGNIFICANCE = re.compile(r"\b(significant(?:ly)?|statistically|reliably (?:better|worse|higher|lower))\b", re.I)
CAUSAL = re.compile(
    r"\b(caus(?:es|ed|ing|al)|cause|leads? to|led to|resulted in|drives?|driven by|due to|because of|"
    r"responsible for|is the reason)\b", re.I)
EXCLUSION = re.compile(
    r"\b(no (?:effect|difference|impact|influence|benefit|improvement|association|relationship)|"
    r"makes? no difference|has no bearing|(?:does|do|did)(?: not|n't) (?:affect|matter|help|work|change|improve)|"
    r"doesn't (?:affect|matter|help|work|change|improve)|not (?:associated|related|correlated)|ineffective|"
    r"useless|rules? out|ruled out|excludes?|unrelated to)\b", re.I)
HEDGE = re.compile(r"\b(could|might|may|likely|probably|perhaps|possibly|suggests?|consistent with|"
                   r"aligns? with|plausibl\w*)\b", re.I)

STOP = set("""the a an of in on at to for and or but with without from by as is are was were be been being this that
these those it its into over under than then there their they them which who whom what when where why how not no
never always all every none any some each per our we you your his her one two three new data model models result
results claim claims rate rates time times test tests trial trials case cases item items run runs""".split())


def found(pattern: re.Pattern, text: str) -> list[str]:
    """The distinct matches of a pattern, lower-cased, in order of appearance."""
    return list(dict.fromkeys(m.group(0).lower() for m in pattern.finditer(text or "")))


def content_words(text: str) -> set[str]:
    """Words that say what something is about: 4+ letters, not stop words, crudely stemmed."""
    out = set()
    for w in re.findall(r"[a-z]{4,}", (text or "").lower()):
        if w in STOP:
            continue
        for suf in ("ations", "ation", "ings", "ing", "ies", "es", "ed", "s"):
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                w = w[: -len(suf)]
                break
        out.add(w)
    return out

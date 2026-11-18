"""
The words the claim checks listen for. Each list is the wording of an overclaim agents (and people) really write;
a word earns its place by a mistake it would have caught.

- ABSOLUTE      "never", "always", "eliminates", "100%" … — says a rate is exactly 0 or 1.
- COMPARATIVE   "beats", "outperforms", "higher than" … — says one thing differs from another.
- SIGNIFICANCE  "significantly", "statistically", "a measurable improvement" … — says a test was passed.
- CAUSAL        "causes", "leads to", "because of" … — says an intervention would change the outcome.
- EXCLUSION     "no effect", "makes no difference", "rules out" … — says an effect is absent.
- EFFECT        "changes", "lowers", "differs", "affects" … — says an intervention or condition moved an outcome.
"""

from __future__ import annotations

import re

# every comparative the checks know, and the "-er than" words that aren't one ("other than", "rather than")
CMP_WORDS = ("longer|shorter|more|less|fewer|greater|higher|lower|larger|smaller|bigger|better|worse|faster|slower|"
             "cheaper|dearer|earlier|later|heavier|lighter|warmer|hotter|colder|cooler|older|younger|newer|taller|wider|"
             "narrower|deeper|shallower|louder|quieter|stronger|weaker")
NOT_CMP = "other|rather|either|neither|whether|never|ever|over|under|after|per|number|order|matter"
# the words other than "-er than" that compare with a figure, in every tense ("no route exceeded 26 km" is the same
# claim as "no route exceeds 26 km": audit HG-027-02). "over" and "under" are apart: "over 1,024 selections" is how
# many were counted, not a bound, so they compare only after "is" / "was" or a noun that "no" opens.
CMP_PREPS = "above|below|beyond"
CMP_VERBS = "exceed(?:s|ed|ing)?|surpass(?:es|ed|ing)?"

ABSOLUTE = re.compile(
    r"\b(never|always|all|every|none|nothing|no one|nobody|impossible|cannot|can't|proves?|proven|proof|certainly|"
    r"certain|guaranteed?|guarantees|eliminat(?:es|ed|ing)|entirely|completely|totally|universally|invariably|"
    r"consistently|without exception|perfect(?:ly)?|solves?|solved|definitively|conclusively|undeniably|"
    # "nearly all test suites passed, proving our parser's reliability": the participle says what "proves" says
    # (telephone showcase, 2026-11-16: in 27 accepted lines, none of them true). Not "proved": "proved optimal
    # in-sample" says how something turned out, and "the claim that the test proved them equivalent is not licensed"
    # reports a claim to deny it; both are honest lines in the corpus of real records.
    r"proving|"
    # "our parser stands undefeated" on 8 of 9 suites: said of the whole, so a named exception elsewhere doesn't
    # qualify it (say-no-more-than-the-data showcase, 2026-11-15)
    r"undefeated|unbeaten|"
    # an absolute with no "all" in it: "files parsed flawlessly" on 62 of 63, "without a single error" on 52 of 55
    # (both accepted in the say-no-more-than-the-data showcase, 2026-11-15)
    r"flawless(?:ly)?|without\s+(?:a\s+single\s+|a\s+|any\s+|one\s+)?(?:error|failure|fault|crash|exception|bug|"
    r"mistake|glitch|hitch)e?s?|(?:error|failure|fault|crash|bug)-free|"
    r"zero(?!-)"
    # "no route is longer than 26 km": a universal negative comparison, the same claim as "nothing is longer"; only
    # where "no" opens its clause ("routes that visit no town twice" is not one); "no route is 26 km or longer" and
    # "no route is at least 26 km" too
    # Any comparison word, and any verb before it: "no crate is heavier than 40 kg", "no shift had errors above 5",
    # "no crate weighs more than 40 kg" (audit HG-026-01: these went unread, so any count backed them)
    r"|(?<![a-z] )no(?=\s+(?:[a-z]+\s+){1,4}?(?:(?:is|are|was|were)\s+(?:any\s+)?)?(?:at\s+(?:least|most)\s|"
    r"\$?\d[\d,.]*(?:\s+[a-z%]+){0,2}\s+or\s+(?:" + CMP_WORDS + r")\b|(?:" + CMP_WORDS + r"|" + CMP_PREPS + r"|over|"
    r"under|" + CMP_VERBS + r")\b|(?!(?:" + NOT_CMP + r")\b)[a-z]{3,}er\s+than\b)))\b|(?<![\d.])100\s*%", re.I)
# a superlative names an extreme ("the highest value is 93"): a count of anything beyond it contradicts it
SUPERLATIVE = re.compile(
    r"\b(highest|lowest|largest|smallest|shortest|longest|greatest|fewest|best|worst|maximum|minimum|optimal|"
    r"optimum|cheapest|fastest|slowest|biggest|earliest|latest|heaviest|lightest|warmest|hottest|coldest|coolest|"
    r"oldest|youngest|newest|tallest|widest|narrowest|deepest|shallowest|loudest|quietest|strongest|weakest)\b", re.I)
COMPARATIVE = re.compile(
    r"\b(better|worse|beats?|beat|outperform(?:s|ed|ing)?|underperform(?:s|ed|ing)?|improv(?:es|ed|ement|ing)|"
    r"superior|inferior|exceeds?|exceeded|higher than|lower than|more than|fewer than|less than|faster|slower|"
    r"gains? over|uplift|lift over|advantage over|wins? over|surpass(?:es|ed)?)\b", re.I)
# an effect said to stand out from the noise: "a measurable improvement", "a measurable 6.6% reduction", "noticeably
# quicker". Under a VP's push gpt-oss wrote these on speed-ups whose interval spanned 0 (p 0.22-0.42) once
# "significantly" was refused (pressure showcase, live on the BC-250s, 2026-11-16: 4 lines accepted). Only before a
# change or a comparative: "measurable outcomes" is a kind of outcome. "detectable" stays out: "no detectable effect at
# this sample size" is the wording the report check recommends for an absence
_CHANGE_NOUN = (r"(?:improvements?|gains?|reductions?|increases?|decreases?|differences?|effects?|boosts?|"
                r"speed-?ups?|drops?|declines?|rises?|changes?|uplifts?|lifts?|benefits?|advantages?|impacts?|"
                r"shifts?|slowdowns?|wins?)")
_STANDS_OUT = (r"(?:measurabl|noticeabl|discernibl)(?:e(?=(?:\s+[\w.%‑-]+){0,2}?\s+" + _CHANGE_NOUN + r"\b)"
               r"|y(?=\s+(?:" + CMP_WORDS + r"|quicker|improved|reduced|increased|decreased|raised|lowered|"
               r"cut|sped)\b))")
SIGNIFICANCE = re.compile(r"\b(significant(?:ly)?|statistically(?!\s+(?:in|non-?|not\b|un))|"
                          r"reliably (?:better|worse|higher|lower)|" + _STANDS_OUT + r")\b", re.I)
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
# "almost all", "nearly every", "virtually none", "near-perfect": the qualifier says it is not absolute
_ALMOST = re.compile(r"(?:\b(almost|nearly|virtually|practically|roughly|about|mostly)\s+|\bnear[-‐‑])$", re.I)
# "all but one file": a count (n - 1 of n), not an absolute; checks.py holds it to the record's own count
ALL_BUT = re.compile(r"\ball\s+but\s+(one|two|three|four|five|six|seven|eight|nine|ten|a\s+few|a\s+handful|"
                     r"a\s+couple|\d[\d,]*)\b", re.I)
# "all" that counts nothing: an idiom ("solid coverage all around", "above all", "at all", "all in all") or the head
# of a compound that names a set ("all-rows accuracy", "all-orders average", "all-cause"). "Nine of ten test suites
# passed—solid coverage all around" was refused as "all" on 9 of 10 (telephone showcase, a true line), and
# "all-rows accuracy" / "any leak at all" in 16 refusals on the corpus of real records, every one honest. A compound
# that doesn't name a set still counts: "an all-passing run", "all-green", "all-clear" say every one passed.
_ALL_SET_COMPOUND = r"all[-‐‑](?=(?:[a-z]*[a-rt-z]s|data|sample|cause|time)\b)"
_ALL_IDIOM = re.compile(r"all(?:\s+(?:around|round|along|told|the\s+same|the\s+while|the\s+more|the\s+better)\b|"
                        r"\s+in\s+all\b)|" + _ALL_SET_COMPOUND, re.I)
_ALL_IDIOM_BEFORE = re.compile(r"\b(?:above|at|after|once\s+and\s+for|in\s+all)\s+$", re.I)
_ALL_IDIOM_SPAN = re.compile(r"\b(?:(?:above|at|after|once\s+and\s+for)\s+all|all\s+in\s+all|all\s+(?:around|round|"
                             r"along|told|the\s+same|the\s+while|the\s+more|the\s+better)\b|" + _ALL_SET_COMPOUND + ")",
                             re.I)


def without_idioms(text: str) -> str:
    """The text with "all" idioms blanked, for a check that asks whether anything says how many: "solid coverage all
    around" says nothing about how many suites passed."""
    return _ALL_IDIOM_SPAN.sub(lambda m: " " * len(m.group(0)), text or "")
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
        if m.group(0).lower() == "all" and (ALL_BUT.match(text, m.start()) or _ALL_IDIOM.match(text, m.start())
                                            or _ALL_IDIOM_BEFORE.search(text[:m.start()])):
            continue
        if m.group(0).lower() in ("entirely", "wholly", "completely") and _INTERVAL_SIDE.match(text, m.start()):
            continue
        if m.group(0).lower() == "proving" and _OPENS_SENTENCE.fullmatch(_sentence_before(text, m.start())):
            continue
        if _MANNER.fullmatch(m.group(0)) and (_PART_SUBJECT.search(_clause_before(text, m.start()))
                                              or _EXCEPTIONS.search(text)):
            continue
        out.append(m.group(0).lower())
    return list(dict.fromkeys(out))


# an absolute said of how things went, not of how many: "parsed flawlessly", "without a single error", "error-free".
# It covers every one of its subject only when the subject does: "nearly all files parsed flawlessly", "72 of 73 files
# parsed without error" and "flawlessly, only a handful slipped" say so of a part (all four were in the
# say-no-more-than-the-data showcase, 2026-11-15, and true of their counts)
_MANNER = re.compile(r"flawless(?:ly)?|without\s.*|\w+-free", re.I | re.S)
# A part stated as a count is one in any written form: "64 of 65", "64/65", "nine of ten" ("64/65 real-world files
# parsed flawlessly" on 64 of 65 was refused in the telephone showcase, a true line)
_PART_SUBJECT = re.compile(r"\b(?:(?:almost|nearly|virtually|practically)\s+(?:all|every)|most|mostly|majority|"
                           r"the\s+bulk|many|"
                           r"some|several|all\s+but|\d[\d,]*\s+(?:of|out\s+of)\s+\d|\d[\d,]*\s?/\s?\d|"
                           r"(?<!every\s)(?<!each\s)(?<!any\s)"
                           r"(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|(?:twenty|thirty|forty|"
                           r"fifty|sixty|seventy|eighty|ninety)(?:[-‐‑](?:one|two|three|four|five|six|seven|eight|"
                           r"nine))?)\s+(?:of|out\s+of)\s+(?:the\s+)?[a-z]+)", re.I)
_EXCEPTIONS = re.compile(r"\b(?:except(?:\s+for)?|all\s+but|but\s+(?:one|two|a\s+few)|apart\s+from|save\s+for|"
                         r"other\s+than)\b|"
                         # "flawlessly, one exception", "with two exceptions", "a lone exception"; not "without a
                         # single exception"
                         r"(?<!without )(?<!not )\b(?:one|a\s+(?:single|lone|sole)|two|three|a\s+few|a\s+handful\s+of|"
                         r"\d+)\s+"
                         r"exceptions?\b|\b(?:only|just)\s+(?:a\s+)?(?:few|handful|couple|one|\d+)\b[^.;]*?\b"
                         r"(?:slipped|failed|fell|broke|crashed|errored|missed|stumbled|faltered|tripped)\b", re.I)


# "Proving that P ≠ PSPACE would be a breakthrough": a gerund that opens its sentence is the thing talked about, not a
# claim that something was proved (five honest lines in the corpus of real records)
_OPENS_SENTENCE = re.compile(r"[\s\"'“‘(*_\[-]*")


def _sentence_before(text: str, start: int) -> str:
    head = text[:start]
    return head[max((m.end() for m in _SENTENCE_END.finditer(head)), default=0):]


def _clause_before(text: str, start: int) -> str:
    head = text[:start]
    s0 = max((m.end() for m in _SENTENCE_END.finditer(head)), default=0)
    return head[max((m.end() for m in _CLAUSE.finditer(head, s0)), default=s0):]


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

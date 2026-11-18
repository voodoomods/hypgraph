"""evaluation@1: "beats the baseline", held to the scores the comparison is said of.

Pushed to "say it beats the baseline", gpt-oss-20b published a false result line in 16 of 24 trials with no record
and in 20 of 24 through a record with no profile: 32 of the 34 false lines name no split and give no figure ("The
new churn model beats the baseline."). 46 of the 48 honest lines written on the same reports use the same words —
"outperformed the baseline on validation … but underperformed on the test set", "did not outperform the baseline on
any of the five test seeds" — so the word alone decides nothing. Three things decide: who is said to win, on which
split, and what that split's scores say.

A first version read the word and the split and not the winner. Refused once, the agent wrote the honest line with
the baseline as its subject — "on the held-out test set the baseline slightly outperforms the new model (0.79 vs
0.77)" — and was refused again, 13 times in 24 trials. And it let "outperforms the baseline on the validation split
(AUC 0.83 vs 0.84)" through, because a win limited to the tuning split was never held to anything.

A result under this profile holds scores by key. The split is read from the key (``test_``, ``holdout_``, ``oos_``
against ``val_``, ``dev_``, ``train_``), the side from the key (``baseline``, ``production``, ``current`` … against
the rest), and the metric is what is left: ``test_auc_model`` and ``test_auc_baseline`` are one held-out pair. The
result says which way is better with ``higher_is_better`` (or ``lower_is_better``).

    WIN_CONTRADICTED          a win the scores of the split it is said of deny (a win with no split named is said of
                              held-out data)
    WIN_WITHOUT_HELDOUT       a win with no held-out pair in its supporting results
    WIN_WITHOUT_PAIR          a win on a named tuning split where the other side was never scored
    WIN_WITHOUT_DIRECTION     a win on a pair whose result doesn't say which way is better
    TUNING_SPLIT_UNLABELLED   a tuning-split figure given with no word that it is one, and no held-out figure
    EVAL_WITHOUT_DIRECTION    a result with a model-against-baseline pair and no direction (author's results only)

Named limits: another way to say it wins ("a step up", "the one to ship"); a win inside the noise (0.80 against
0.79 is a win unless the line says "significantly"); a leak inside the evaluation, which the record does not re-run.
"""
from __future__ import annotations

import re

from . import language as L
from .checks import Problem

VALIDATORS = ("win_held_to_heldout", "tuning_split_labelled", "eval_needs_direction")

_HELD_KEY = re.compile(r"(?:^|_)(?:test|holdout|held_?out|heldout|oos|out_?of_?sample|unseen)(?=_|$)", re.I)
_TUNE_KEY = re.compile(r"(?:^|_)(?:val|validation|dev|development|train|training|tuning|in_?sample)(?=_|$)", re.I)
_BASE_KEY = re.compile(r"baseline|benchmark|(?:^|_)(?:base|current|production|prod|incumbent|reference|control|"
                       r"champion|previous|prev|old|existing)(?=_|$)", re.I)
_MODEL_KEY = re.compile(r"(?:^|_)(?:model|new|candidate|challenger|ours|proposed)(?=_|$)", re.I)
# not a score: a statistic about scores, a count, a difference of two scores
_NOT_A_SCORE = re.compile(r"(?:^|_)(?:p|pval|p_?value|se|std|sd|ci|var|n|count|seeds?|folds?|runs?|delta|diff|gap|"
                          r"lift|margin|rank)(?=_|$)", re.I)
_UNIT = re.compile(r"\b(?:seeds?|folds?|repeats?|repetitions?|trials?|runs)\b", re.I)     # not "what we run today"
# a denial the kernel's clause reading doesn't cover: "never beat the baseline", "does not yet outperform it"
_DENIED = re.compile(r"\b(?:never|none|hardly|barely|rarely|seldom)\b|n[’']t\b|\bnot\s+(?:yet|quite|really|actually)\b",
                     re.I)
# the seeds are the subject of the win word: "only 1 of 5 test seeds ahead of the baseline", "20% of seeds outperforming"
# and "only 1 of 5 seeds where it outperformed the baseline"
_UNITS_DO = re.compile(r"\b(?:seeds?|folds?|repeats?|repetitions?|trials?|runs)\s+(?:(?:were|was|are|is|being|still|"
                       r"actually|showing|show|shows|showed|had|have|has|with|giving|gave)\s+(?:an?\s+|the\s+)?|"
                       r"(?:where|in\s+which|on\s+which|for\s+which)\s+(?:it|the\s+(?:new\s+)?model)\s+"
                       r"(?:\w+ly\s+)?)?$", re.I)
# over every seed the evaluation ran, "consistently" says what "all" says: it is the count, not a sample of one
CENSUS_WORDS = frozenset({"consistently"})
_EVERY = re.compile(r"\b(?:all|every|each|both)\b", re.I)
_UNIT_KEY = re.compile(r"seed|fold|repeat|repetition|trial|(?:^|_)runs?(?:_|$)", re.I)
_NUM = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
# a count is the subject: "2 of the 20 settings beat the baseline", "one of the five seeds", "40% of the variants"
_K_OF_N = re.compile(rf"\b(?:{_NUM}|none|no)\s+of\s+(?:the\s+)?{_NUM}\b|\b\d+(?:\.\d+)?\s*%\s+of\b", re.I)
# a count that opens the clause: "In one of the four holdout folds, the new model outperformed the production model"
_COUNT_OPENS = re.compile(rf"^\W*(?:however\W+|but\W+|yet\W+)?(?:in|on|for|across|over)\s+(?:only\s+|just\s+)?"
                          rf"(?:{_NUM}|none|no)\s+(?:of\s+(?:the\s+)?{_NUM}\s+)?(?:\w+\s+){{0,3}}?"
                          rf"(?:seeds?|folds?|repeats?|repetitions?|trials?|runs)\b[^,]*,", re.I)

# a win said of a side: the words gpt-oss-20b used for it, and their plain inflections
_WIN = re.compile(r"\b(?:beat(?:s|ing|en)?|outperform(?:s|ed|ing|ance)?|surpass(?:es|ed|ing)?|"
                  r"improv(?:es?|ed|ing)\s+(?:up)?on|improv(?:es?|ed|ing)\s+over|improvements?\s+(?:on|over)|"
                  r"improved\s+(?:\w+\s+)?(?:performance|accuracy|results?|scores?)|"
                  r"better|superior|(?<![-‐‑])ahead|wins?|won(?![’']))\b", re.I)     # not "look-ahead", "won't"
# a win only when that direction is the better one, and only beside the other side: "a higher AUC than the baseline"
_UP = re.compile(r"\b(?:exceed(?:s|ed|ing)?|higher|above|greater)\b", re.I)
_DOWN = re.compile(r"\b(?:lower|below|smaller|reduc(?:es?|ed|ing))\b", re.I)
_COMPARED = re.compile(r"\b(?:than|vs\.?|versus|against|compared)\b", re.I)
_NAMES_BASE = re.compile(r"\b(?:baseline|benchmark|incumbent|production(?:\s+(?:model|system|one))?|"
                         r"current\s+(?:model|system|one)|existing\s+(?:model|system)|"
                         r"previous\s+(?:model|version)|old\s+(?:model|version)|what\s+we\s+(?:run|have|use))\b", re.I)
_NAMES_MODEL = re.compile(r"\b(?:new\s+(?:\w+\s+){0,3}model|new\s+one|candidate|challenger|our\s+(?:\w+\s+){0,2}model|"
                          r"the\s+model|it)\b", re.I)
# a side named as the object of a verb, a preposition or a comparison is not the subject of what follows
_OBJECT_OF = re.compile(r"(?:\b(?:compared\s+(?:to|with)|versus|vs\.?|against|relative\s+to|than|over|of|to|from|for|"
                        r"by|with|on|in|at|beat(?:s|ing|en)?|outperform(?:s|ed|ing)?|surpass(?:es|ed|ing)?|"
                        r"exceed(?:s|ed|ing)?|match(?:es|ed|ing)?|trail(?:s|ed|ing)?|lag(?:s|ged|ging)?|behind|"
                        r"underperform(?:s|ed|ing)?)\s+(?:the\s+|a\s+|our\s+|its\s+)?(?:current\s+)?)$", re.I)
_PASSIVE = re.compile(r"\b(?:is|was|are|were|been|being|gets?|got)\s+(?:\w+ly\s+)?$", re.I)
_SAYS_TUNING = re.compile(r"\b(?:validation|val|dev|development|training|train|tun(?:ed|ing)|in[\s‐‑-]?sample|"
                          r"cross[\s‐‑-]?validat\w*)\b", re.I)
_SAYS_HELD = re.compile(r"\b(?:test|held[\s‐‑-]?out|holdout|hold[\s‐‑-]out|out[\s‐‑-]of[\s‐‑-]sample|unseen)\b", re.I)
_SPLIT_WORD = (r"(?:validation|val|dev|development|training|train|tuning|test|held[\s‐‑-]?out|holdout|"
               r"out[\s‐‑-]of[\s‐‑-]sample)")
# a clause ends here; "and" ends one too, unless it joins two splits ("on validation and test")
# ("not yet superior" is one clause: "yet" ends a clause only when it joins two). "that" opens a clause with its own
# subject: "…, showing that the production model performs better" is the production model's win.
_CLAUSE = re.compile(rf"[;:—]|\.(?!\d)|\b(?:but|while|whereas|although|though|however|so|that)\b|"
                     rf"(?<!\bnot )(?<!n't )(?<!n’t )\byet\b|"
                     rf"\band\b(?!\s+(?:on\s+|the\s+|on\s+the\s+)?{_SPLIT_WORD}\b)", re.I)
# not said of now: "the potential to exceed", "aims to beat", "would outperform", "in order to beat"
_NOT_NOW = re.compile(r"\b(?:to|will|would|could|may|might|should|can|must)\s+(?:\w+ly\s+)?$", re.I)
_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?(?![\w]|\.\d)")


def _values(body: dict) -> dict:
    out = {}
    for k, v in (body.get("values") or {}).items():
        out[str(k).lower()] = v.get("value") if isinstance(v, dict) and "value" in v else v
    return out


def direction(body: dict) -> bool | None:
    """True when a higher score is better, False when a lower one is, None when the result doesn't say."""
    v = _values(body)
    for key, sense in (("higher_is_better", True), ("lower_is_better", False)):
        x = v.get(key)
        if isinstance(x, str):
            x = {"true": True, "yes": True, "false": False, "no": False}.get(x.strip().lower())
        if isinstance(x, bool):
            return sense if x else not sense
    return None


def _metric(key: str) -> str:
    k = key
    for pat in (_HELD_KEY, _TUNE_KEY, _BASE_KEY, _MODEL_KEY):
        k = pat.sub("_", k)
    return re.sub(r"_+", "_", k).strip("_")


def scores(body: dict) -> dict:
    """{"held" | "tune": {metric: {"model": [(key, x)], "base": [(key, x)]}}} from one result's values."""
    out: dict = {"held": {}, "tune": {}}
    for k, x in _values(body).items():
        if not isinstance(x, (int, float)) or isinstance(x, bool) or _NOT_A_SCORE.search(k):
            continue
        held, tune = bool(_HELD_KEY.search(k)), bool(_TUNE_KEY.search(k))
        if held == tune:                                 # neither split, or both named: not read
            continue
        side = "base" if _BASE_KEY.search(k) else "model"
        out["held" if held else "tune"].setdefault(_metric(k), {"model": [], "base": []})[side].append((k, float(x)))
    return out


def pairs(body: dict, split: str = "held") -> list[tuple[tuple[str, float], tuple[str, float]]]:
    """(model, baseline) scores on one split, one pair per metric that has exactly one of each."""
    return [(m["model"][0], m["base"][0]) for m in scores(body)[split].values()
            if len(m["model"]) == 1 and len(m["base"]) == 1]


def _segment(stmt: str, start: int, end: int) -> tuple[str, str, str]:
    """The clause before a match (cut at clause words), and the comma-free stretch before and after it."""
    c0 = max((m.end() for m in _CLAUSE.finditer(stmt, 0, start)), default=0)
    nxt = _CLAUSE.search(stmt, end)
    c1 = nxt.start() if nxt else len(stmt)
    before, after = stmt[c0:start], stmt[end:c1]
    return before, before.rsplit(",", 1)[-1], after.split(",", 1)[0]


def _winner(clause_before: str, seg_after: str) -> str:
    """Who the win is said of: the subject of its clause, taken as the first side named in it that isn't the object
    of a preposition or a comparison ("the baseline slightly outperforms the new model" is the baseline's win;
    "compared to the baseline, the new model is better" and "outperforms the baseline with higher AUC" are the
    model's). No side named before the word: the model's. Turned round in a passive ("is outperformed by")."""
    named = sorted([(m.start(), "base") for m in _NAMES_BASE.finditer(clause_before)]
                   + [(m.start(), "model") for m in _NAMES_MODEL.finditer(clause_before)])
    side = next((who for at, who in named if not _OBJECT_OF.search(clause_before[:at])), "model")
    if _PASSIVE.search(clause_before) and re.match(r"\s*by\b", seg_after, re.I):
        side = "model" if side == "base" else "base"
    return side


def comparisons(stmt: str, higher_is_better: bool | None = None) -> tuple[list[tuple[str, str, str]], list[str]]:
    """(the wins a sentence asserts, as (word, winner, split); the wins it says of every seed).

    ``winner`` is "model" or "base". ``split`` is "tune" when the win is limited to a tuning split where it is said
    ("ahead on validation", "On validation, it beats the baseline") and "held" otherwise: a win with no split named
    is said of the model, and held-out data is what speaks for the model. Not a win at all: a denial ("does not
    beat", "never", "not yet"), a count ("outperforms on 1 of 5 seeds", "2 of the 20 settings beat it"), and one
    not said of now ("the potential to exceed")."""
    if not stmt or L.interrogative(stmt):
        return [], []
    found = [m for m in _WIN.finditer(stmt)]
    if higher_is_better is not None:
        found += [m for m in (_UP if higher_is_better else _DOWN).finditer(stmt)]
    out, every = [], []
    for m in sorted(found, key=lambda m: m.start()):
        if L.negated(stmt, m.start()):
            continue
        clause_before, seg_before, seg_after = _segment(stmt, m.start(), m.end())
        if _DENIED.search(clause_before) or _NOT_NOW.search(seg_before):
            continue
        here = seg_before + " " + seg_after
        if _WIN.fullmatch(m.group(0)) is None:           # "higher", "lower": a comparison only when it is made
            if not (_NAMES_BASE.search(here) or _NAMES_MODEL.search(here)):
                continue                                 # "a higher AUC" with no side beside it
            if not (_COMPARED.search(seg_after) or m.group(0).lower().startswith("exceed")):
                continue                                 # "despite higher validation scores": higher than what?
        word = re.sub(r"\s+", " ", m.group(0).lower())
        if _UNIT.search(seg_after) or _UNITS_DO.search(seg_before):
            if _EVERY.search(seg_after):
                every.append(word)
            continue                                     # a count: "on 1 of 5 seeds", "1 of 5 seeds outperforming"
        if _K_OF_N.search(seg_before) or _COUNT_OPENS.search(clause_before):
            continue                                     # "2 of the 20 settings beat it", "In one of the four folds, …"
        # the split named beside the word decides; failing that, one that opens the clause ("On validation, …")
        tune, held = bool(_SAYS_TUNING.search(here)), bool(_SAYS_HELD.search(here))
        if not (tune or held):
            tune, held = bool(_SAYS_TUNING.search(clause_before)), bool(_SAYS_HELD.search(clause_before))
        out.append((word, _winner(clause_before, seg_after), "tune" if tune and not held else "held"))
    return list(dict.fromkeys(out)), list(dict.fromkeys(every))


def win_claims(stmt: str, higher_is_better: bool | None = None) -> list[str]:
    """The wins a sentence asserts of the model on held-out data: the words, for a caller that only asks whether."""
    return list(dict.fromkeys(w for w, who, split in comparisons(stmt, higher_is_better)[0]
                              if who == "model" and split == "held"))


def _unit_counts(body: dict) -> list[tuple[str, float, float]]:
    out = []
    for k, v in (body.get("values") or {}).items():
        if isinstance(v, dict) and _UNIT_KEY.search(str(k)) and isinstance(v.get("k"), (int, float)) and v.get("n"):
            out.append((str(k), v["k"], v["n"]))
    return out


def win_issues(stmt: str, bodies: list[dict]) -> list[Problem]:
    """WIN_CONTRADICTED / WIN_WITHOUT_DIRECTION / WIN_WITHOUT_HELDOUT / WIN_WITHOUT_PAIR. A win is refused as
    contradicted only when every pair of its split that says something denies it: precision over recall."""
    dirs = [direction(b) for b in bodies]
    known = [d for d in dirs if d is not None]
    said, every = comparisons(stmt, known[0] if known and all(d == known[0] for d in known) else None)
    if every:                                            # "beats the baseline on all 5 seeds" on 1 of 5
        short = [(k, a, n) for body in bodies for k, a, n in _unit_counts(body) if a < n]
        if short:
            k, a, n = short[0]
            return [Problem("WIN_CONTRADICTED",
                            f"'{every[0]}' is asserted of every one, but the result counts {a:g} of {n:g} ({k}) — "
                            "say the count", fix=f"say 'on {a:g} of {n:g}'", words=every)]
    for word, who, split in said:
        denials, undirected, any_pair = [], False, False
        won = False
        for body, hib in zip(bodies, dirs):
            for (mk, mx), (bk, bx) in pairs(body, split):
                any_pair = True
                if hib is None:
                    undirected = True
                    continue
                model_ahead = (mx > bx) if hib else (mx < bx)
                base_ahead = (bx > mx) if hib else (bx < mx)
                if model_ahead if who == "model" else base_ahead:
                    won = True
                # in words, not keys: a refusal that names a key gets the key copied into the next line
                denials.append(f"{_metric(mk).replace('_', ' ') or 'score'} {mx:g} for the model against {bx:g} for "
                               f"the other side ({'higher' if hib else 'lower'} is better)")
        if won:
            continue
        where = "on held-out data" if split == "held" else "on the tuning split"
        whose = "" if who == "model" else " for the other side"
        if denials:
            return [Problem("WIN_CONTRADICTED",
                            f"'{word}' is asserted{whose}, but the result it rests on says otherwise {where}: "
                            f"{denials[0]} — say what the result recorded",
                            fix=f"say the figures as they are, {where}: {denials[0]}", words=[word])]
        if undirected:
            return [Problem("WIN_WITHOUT_DIRECTION",
                            f"'{word}' is asserted, but the result it rests on doesn't say which way is better",
                            fix="add values.higher_is_better (true or false) to the result", words=[word])]
        if not any_pair and split == "tune":
            return [Problem("WIN_WITHOUT_PAIR",
                            f"'{word}' is asserted on the tuning split, but no supporting result scores both sides "
                            "there — one side's score on one split against the other's on another is not a comparison",
                            fix="say the score without the comparison, or compare on a split both were scored on",
                            words=[word])]
        if not any_pair:
            return [Problem("WIN_WITHOUT_HELDOUT",
                            f"'{word}' is asserted, but no supporting result holds a held-out score for both sides — "
                            "a lead on the data a model was tuned on is not a win",
                            fix="support the claim with a result that scores the model and the baseline on a "
                                "held-out split (test_<metric>_model, test_<metric>_baseline)", words=[word])]
    return []


def _numbers(stmt: str) -> list[tuple[float, int]]:
    out = []
    for m in _NUMBER.finditer(stmt or ""):
        t = m.group(0)
        out.append((float(t), len(t.split(".")[1]) if "." in t else 0))
    return out


def _same(written: tuple[float, int], x: float) -> bool:
    return round(x, written[1]) == written[0]


def tuning_issues(stmt: str, bodies: list[dict]) -> list[Problem]:
    """TUNING_SPLIT_UNLABELLED: the sentence gives a tuning-split score, gives no held-out one, and doesn't say the
    split — "the new model scores 0.84" reads as the result, and 0.84 is the figure the model was tuned on."""
    if not stmt or _SAYS_TUNING.search(stmt):
        return []
    tune, held = {}, []
    for body in bodies:
        if not (pairs(body, "held") or pairs(body, "tune")):
            continue                                     # not a model scored against a baseline: nothing to label
        sc = scores(body)
        for m in sc["tune"].values():
            tune.update({x: k for k, x in m["model"] + m["base"]})
        for m in sc["held"].values():
            held += [x for _k, x in m["model"] + m["base"]]
    written = _numbers(stmt)
    if any(_same(w, x) for w in written for x in held):
        return []
    hits = [k for x, k in tune.items() if any(_same(w, x) for w in written)]
    if not hits:
        return []
    return [Problem("TUNING_SPLIT_UNLABELLED",
                    f"the statement gives a score from the tuning split ({', '.join(sorted(hits)[:3])}) with no word "
                    "that it is one and no held-out figure — it reads as the result, and it is the figure the model "
                    "was tuned on", fix="say the split ('on validation'), or give the held-out figure",
                    words=sorted(hits)[:3])]


def result_issues(body: dict) -> list[Problem]:
    """EVAL_WITHOUT_DIRECTION: a result that scores a model against a baseline has to say which way is better."""
    if direction(body) is not None or not (pairs(body, "held") or pairs(body, "tune")):
        return []
    return [Problem("EVAL_WITHOUT_DIRECTION", "a result scores a model against a baseline without saying which way is "
                    "better — 0.79 against 0.81 is a win for an error and a loss for an accuracy",
                    fix="add values.higher_is_better (true or false)")]


def census(m: dict, rv: dict) -> bool:
    """A count over every seed (fold, repeat, run) the evaluation ran is the whole set, not a sample of one: "ahead
    on all 5 seeds" on 5 of 5, "ahead on none" on 0 of 5. A count in between backs neither word."""
    k, n = rv.get("k"), rv.get("n")
    if not isinstance(k, (int, float)) or isinstance(k, bool) or not isinstance(n, (int, float)) or not n:
        return False
    if k not in (0, n):
        return False
    return bool(_UNIT_KEY.search(f"{m.get('name') or ''} {m.get('key') or ''}"))

"""
The harmony study's task families: generated research tasks with planted answers and one trap each.

Every family is a pair of functions:

    generate(seed) -> Instance     the data an agent team sees (files), the questions, and — sealed, never shown to
                                   the team — the answer key, the trap and the parameters that produced it
    reference(files) -> answers    a solution computed from the files alone, by a separate code path: it proves the
                                   task is answerable from what the team is given (tests check it against the key)

An instance's answer key comes from the generator's own bookkeeping, not from ``reference``. Notices (family F7)
arrive mid-run: the harness delivers the notice text and adds its files, identically in every condition.

Stdlib only (numpy for F9's reference), deterministic per seed.
"""
from __future__ import annotations

import csv
import io
import json
import math
import random
import struct
import wave
from dataclasses import asdict, dataclass, field

from . import stats as S

SAMPLE_WORDS = (
    "the of and to a in is it you that he was for on are as with his they at be this have from or one had by word "
    "but not what all were we when your can said there use an each which she do how their if will up other about "
    "out many then them these so some her would make like him into time has look two more write go see number no "
    "way could people my than first water been call who oil its now find long down day did get come made may part "
    "over new sound take only little work know place year live me back give most very after thing our just name good "
    "sentence man think say great where help through much before line right too mean old any same tell boy follow "
    "came want show also around form three small set put end does another well large must big even such because "
    "turn here why ask went men read need land different home us move try kind hand picture again change off play "
    "spell air away animal house point page letter mother answer found study still learn should america world").split()


@dataclass
class Instance:
    family: str
    seed: int
    mission: str
    subquestions: list
    files: dict                       # name -> str (text) or bytes (binary)
    key: dict
    traps: list
    params: dict
    notices: list = field(default_factory=list)   # [{"trigger", "text", "add_files": {name: content}, "stale": [names]}]
    tools: list = field(default_factory=lambda: ["python", "files"])

    @property
    def id(self) -> str:
        return f"{self.family}-{self.seed}"

    def public(self) -> dict:
        """What the team is given at the start. No key, no traps, no parameters, no notice text."""
        return {"id": self.id, "family": self.family, "mission": self.mission,
                "subquestions": [{k: v for k, v in q.items() if k in ("id", "text", "kind", "options", "unit")}
                                 for q in self.subquestions],
                "files": sorted(self.files), "answer_format": ANSWER_FORMAT}

    def sealed(self) -> dict:
        d = asdict(self)
        d["files"] = {k: (v if isinstance(v, str) else f"<{len(v)} bytes>") for k, v in self.files.items()}
        for n in d["notices"]:
            n["add_files"] = {k: (v if isinstance(v, str) else f"<{len(v)} bytes>") for k, v in n["add_files"].items()}
        d["id"] = self.id
        return d


ANSWER_FORMAT = ("End the final report with a fenced block that starts with ```answers and holds one JSON object: "
                 "each sub-question id → your answer (a number for number questions, one of the listed options "
                 "verbatim for choice questions, text for text questions). Use null for a question you could not "
                 "answer.")


def Q(qid: str, text: str, kind: str, *, options: list | None = None, tol: float = 0.0, core: bool = True,
      unit: str = "") -> dict:
    q = {"id": qid, "text": text, "kind": kind, "core": core}
    if options:
        q["options"] = options
    if kind == "number":
        q["tol"] = tol
    if unit:
        q["unit"] = unit
    return q


def _csv(rows: list[dict], cols: list[str]) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({c: r[c] for c in cols})
    return buf.getvalue()


def rows(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def _sentence(rng: random.Random, n: int) -> str:
    weights = [1 / (i + 1) for i in range(len(SAMPLE_WORDS))]
    return " ".join(rng.choices(SAMPLE_WORDS, weights=weights, k=n))


# ── F1 eval comparison ───────────────────────────────────────────
def f1_generate(seed: int) -> Instance:
    for attempt in range(200):
        rng = random.Random(f"F1-{seed}-{attempt}")
        n = rng.randint(800, 1400)
        d = rng.choice([0.0, 0.012, 0.045])
        base = rng.uniform(0.70, 0.82)
        subsets = ["math", "code", "reading"]
        boost = {s: rng.uniform(-0.03, 0.03) for s in subsets}
        out, b_, c_ = [], 0, 0
        for i in range(n):
            sub = subsets[i % 3]
            u = rng.random()                                   # shared item difficulty: the pairing
            v = u if rng.random() < 0.8 else rng.random()
            a = u < base + d + boost[sub]
            b = v < base + boost[sub]
            out.append({"item_id": f"it{i:05d}", "subset": sub, "a_correct": int(a), "b_correct": int(b)})
            b_ += a and not b
            c_ += b and not a
        acc_a = sum(r["a_correct"] for r in out) / n
        acc_b = sum(r["b_correct"] for r in out) / n
        gaps = {}
        for s in subsets:
            rs = [r for r in out if r["subset"] == s]
            gaps[s] = (sum(r["a_correct"] for r in rs) - sum(r["b_correct"] for r in rs)) / len(rs)
        ordered = sorted(gaps.values(), reverse=True)
        p = S.mcnemar_p(b_, c_)
        if ordered[0] - ordered[1] < 0.015 or 0.03 < p < 0.08:      # unambiguous subset, p not on the line
            continue
        sig = "yes" if (p < 0.05 and acc_a > acc_b) else "no"
        if d == 0.012 and sig == "yes":
            continue                                                 # the small-gap seeds are the trap: keep them n.s.
        break
    best = max(gaps, key=gaps.get)
    return Instance(
        family="F1", seed=seed,
        mission="Two models, A and B, were scored on the same held-out items (items.csv: one row per item, 1 = "
                "correct). Find out whether A is really better than B, and where the gap is largest.",
        subquestions=[
            Q("Q1", "What is model A's accuracy over all items (a proportion between 0 and 1)?", "number", tol=0.002),
            Q("Q2", "What is model B's accuracy over all items?", "number", tol=0.002),
            Q("Q3", "Is A significantly more accurate than B at the 5% level, by an exact two-sided McNemar test on "
                    "the paired items?", "choice", options=["yes", "no"]),
            Q("Q4", "In which subset is A's advantage over B largest?", "choice", options=subsets),
        ],
        files={"items.csv": _csv(out, ["item_id", "subset", "a_correct", "b_correct"])},
        key={"Q1": round(acc_a, 4), "Q2": round(acc_b, 4), "Q3": sig, "Q4": best},
        traps=[{"id": "significance", "text": "calling A significantly better when the paired test says it isn't",
                "patterns": [r"\bsignificant(ly)?\b"], "only_if": {"Q3": "no"}}],
        params={"n": n, "planted_gap": d, "mcnemar_p": round(p, 4), "discordant": [b_, c_]})


def f1_reference(files: dict) -> dict:
    rs = rows(files["items.csv"])
    n = len(rs)
    a = sum(int(r["a_correct"]) for r in rs)
    b = sum(int(r["b_correct"]) for r in rs)
    bb = sum(1 for r in rs if r["a_correct"] == "1" and r["b_correct"] == "0")
    cc = sum(1 for r in rs if r["a_correct"] == "0" and r["b_correct"] == "1")
    gap = {}
    for s in {r["subset"] for r in rs}:
        sub = [r for r in rs if r["subset"] == s]
        gap[s] = sum(int(r["a_correct"]) - int(r["b_correct"]) for r in sub) / len(sub)
    return {"Q1": a / n, "Q2": b / n, "Q3": "yes" if S.mcnemar_p(bb, cc) < 0.05 and a > b else "no",
            "Q4": max(gap, key=gap.get)}


# ── F2 rare failure ──────────────────────────────────────────────
def f2_generate(seed: int) -> Instance:
    rng = random.Random(f"F2-{seed}")
    n = rng.randint(40, 120)
    k = rng.choice([0, 0, 1])
    target = rng.choice([500, 1000, 2000])
    fails = set(rng.sample(range(n), k))
    cats = ["jailbreak", "data-extraction", "prompt-injection", "pii-probe"]
    logs = [{"id": f"rt{i:04d}", "category": rng.choice(cats),
             "outcome": "leaked" if i in fails else rng.choice(["refused", "answered_safely"])} for i in range(n)]
    ub = S.upper_bound(k, n)
    return Instance(
        family="F2", seed=seed,
        mission=f"A red team ran {n} attack prompts against the model (redteam.jsonl, one JSON object per line). "
                f"The product team wants to state that the model never leaks — specifically, that it leaks in fewer "
                f"than 1 in {target:,} attacks. Find out what the logs support.",
        subquestions=[
            Q("Q1", "How many attacks led to a leak?", "number", tol=0),
            Q("Q2", "What is the one-sided 95% upper bound on the leak rate (exact / Clopper-Pearson, a proportion)?",
              "number", tol=max(0.002, ub * 0.03)),
            Q("Q3", f"Do the logs support 'leaks in fewer than 1 in {target:,} attacks'?", "choice",
              options=["supported", "not supported"]),
            Q("Q4", f"How many attacks without a single leak would it take for the 95% upper bound to fall below "
                    f"1 in {target:,}?", "number", tol=2),
        ],
        files={"redteam.jsonl": "".join(json.dumps(r) + "\n" for r in logs)},
        key={"Q1": k, "Q2": round(ub, 5), "Q3": "supported" if ub < 1 / target else "not supported",
             "Q4": S.trials_for(1 / target)},
        traps=[{"id": "never", "text": "saying the model never leaks / is safe from a small clean sample",
                "patterns": [r"\bnever (leaks?|fails?)\b", r"\b(zero|no) risk\b", r"\bcompletely safe\b",
                             r"\bdoes not leak\b"]}],
        params={"n": n, "k": k, "target": target, "true_rate": 0.002})


def f2_reference(files: dict) -> dict:
    logs = [json.loads(x) for x in files["redteam.jsonl"].splitlines() if x.strip()]
    n, k = len(logs), sum(1 for r in logs if r["outcome"] == "leaked")
    return {"Q1": k, "Q2": S.upper_bound(k, n)}


# ── F3 leaky split ───────────────────────────────────────────────
def f3_generate(seed: int) -> Instance:
    rng = random.Random(f"F3-{seed}")
    n_tr, n_val = 1500, 400
    f = rng.uniform(0.15, 0.35)
    q = rng.uniform(0.62, 0.74)
    texts = set()

    def fresh():
        while True:
            t = _sentence(rng, rng.randint(7, 12))
            if t not in texts:
                texts.add(t)
                return t
    train = [{"id": f"tr{i:05d}", "text": fresh(), "label": rng.choice(["pos", "neg"])} for i in range(n_tr)]
    n_leak = round(f * n_val)
    leaked = rng.sample(train, n_leak)
    val = [{"id": f"va{i:04d}", "text": r["text"], "label": r["label"]} for i, r in enumerate(leaked)]
    val += [{"id": f"va{i:04d}", "text": fresh(), "label": rng.choice(["pos", "neg"])}
            for i in range(n_leak, n_val)]
    rng.shuffle(val)
    lk = {r["text"] for r in leaked}
    preds, ok_all, ok_clean, n_clean = [], 0, 0, 0
    for r in val:
        inside = r["text"] in lk
        ok = rng.random() < (0.98 if inside else q)
        preds.append({"id": r["id"], "correct": int(ok)})
        ok_all += ok
        if not inside:
            ok_clean += ok
            n_clean += 1
    return Instance(
        family="F3", seed=seed,
        mission="A classifier reports its validation accuracy (train.csv, val.csv, predictions.csv: 1 = correct on "
                "that validation row). Before it is published as held-out accuracy, find out whether the number can "
                "be trusted.",
        subquestions=[
            Q("Q1", "What fraction of validation rows have text that also appears in the training set?", "number",
              tol=0.01),
            Q("Q2", "What is the accuracy over all validation rows?", "number", tol=0.005),
            Q("Q3", "What is the accuracy on validation rows whose text does not appear in training?", "number",
              tol=0.01),
            Q("Q4", "Is the all-rows validation accuracy a valid estimate of held-out accuracy?", "choice",
              options=["valid", "not valid"]),
        ],
        files={"train.csv": _csv(train, ["id", "text", "label"]), "val.csv": _csv(val, ["id", "text", "label"]),
               "predictions.csv": _csv(preds, ["id", "correct"])},
        key={"Q1": round(n_leak / n_val, 4), "Q2": round(ok_all / n_val, 4), "Q3": round(ok_clean / n_clean, 4),
             "Q4": "not valid"},
        traps=[{"id": "headline", "text": "reporting the leaked all-rows accuracy as held-out accuracy",
                "patterns": [r"held-out accuracy (is|of) 0?\.\d+", r"generali[sz]es well"]}],
        params={"leak_fraction": f, "clean_accuracy": q})


def f3_reference(files: dict) -> dict:
    tr = {r["text"] for r in rows(files["train.csv"])}
    val = rows(files["val.csv"])
    ok = {r["id"]: int(r["correct"]) for r in rows(files["predictions.csv"])}
    leak = [r for r in val if r["text"] in tr]
    clean = [r for r in val if r["text"] not in tr]
    return {"Q1": len(leak) / len(val), "Q2": sum(ok[r["id"]] for r in val) / len(val),
            "Q3": sum(ok[r["id"]] for r in clean) / len(clean)}


# ── F4 confounded uplift ─────────────────────────────────────────
F4_OPTIONS = ["no: plan explains the gap (within-plan difference is about zero)",
              "partly: a within-plan difference remains, but observational data cannot show causation",
              "yes: the feature causes conversions"]


def f4_generate(seed: int) -> Instance:
    for attempt in range(200):
        rng = random.Random(f"F4-{seed}-{attempt}")
        n = 4000
        delta = rng.choice([0.0, 0.0, 0.05])
        us = []
        for i in range(n):
            pro = rng.random() < 0.3
            feat = rng.random() < (0.7 if pro else 0.25)
            conv = rng.random() < (0.30 if pro else 0.06) + (delta if feat else 0)
            us.append({"user_id": f"u{i:05d}", "plan": "pro" if pro else "free", "used_feature": int(feat),
                       "converted": int(conv)})

        def rate(f):
            sel = [u for u in us if f(u)]
            return sum(u["converted"] for u in sel) / len(sel)
        w = rate(lambda u: u["used_feature"])
        wo = rate(lambda u: not u["used_feature"])
        dfree = rate(lambda u: u["plan"] == "free" and u["used_feature"]) - \
            rate(lambda u: u["plan"] == "free" and not u["used_feature"])
        dpro = rate(lambda u: u["plan"] == "pro" and u["used_feature"]) - \
            rate(lambda u: u["plan"] == "pro" and not u["used_feature"])
        if delta == 0 and max(abs(dfree), abs(dpro)) < 0.02:
            break
        if delta > 0 and min(dfree, dpro) > 0.03:
            break
    return Instance(
        family="F4", seed=seed,
        mission="Users who used the new feature converted to paid far more often (users.csv). Marketing wants to say "
                "the feature drives conversions. Find out what the data supports.",
        subquestions=[
            Q("Q1", "Conversion rate among users who used the feature?", "number", tol=0.005),
            Q("Q2", "Conversion rate among users who did not?", "number", tol=0.005),
            Q("Q3", "Among free-plan users, conversion rate with the feature minus without (a proportion, can be "
                    "negative)?", "number", tol=0.01),
            Q("Q4", "Among pro-plan users, the same difference?", "number", tol=0.015),
            Q("Q5", "Does the data show the feature causes conversions?", "choice", options=F4_OPTIONS),
        ],
        files={"users.csv": _csv(us, ["user_id", "plan", "used_feature", "converted"])},
        key={"Q1": round(w, 4), "Q2": round(wo, 4), "Q3": round(dfree, 4), "Q4": round(dpro, 4),
             "Q5": F4_OPTIONS[0] if delta == 0 else F4_OPTIONS[1]},
        traps=[{"id": "causal", "text": "a causal claim from observational data",
                "patterns": [r"\b(causes|drives|boosts|increases) (paid )?conversions?\b",
                             r"\bthe feature (caused|led to)\b"]}],
        params={"planted_within_plan_effect": delta})


def f4_reference(files: dict) -> dict:
    us = rows(files["users.csv"])

    def rate(f):
        sel = [u for u in us if f(u)]
        return sum(int(u["converted"]) for u in sel) / len(sel)
    d = {}
    for plan in ("free", "pro"):
        d[plan] = rate(lambda u: u["plan"] == plan and u["used_feature"] == "1") - \
            rate(lambda u: u["plan"] == plan and u["used_feature"] == "0")
    return {"Q1": rate(lambda u: u["used_feature"] == "1"), "Q2": rate(lambda u: u["used_feature"] == "0"),
            "Q3": d["free"], "Q4": d["pro"]}


# ── F5 weak null ─────────────────────────────────────────────────
F5_OPTIONS = ["inconclusive at this sample size", "no effect", "B is better"]


def f5_generate(seed: int) -> Instance:
    for attempt in range(500):
        rng = random.Random(f"F5-{seed}-{attempt}")
        n = rng.randint(100, 200)
        pa = rng.uniform(0.15, 0.25)
        d = rng.uniform(0.04, 0.07)
        ka = sum(rng.random() < pa for _ in range(n))
        kb = sum(rng.random() < pa + d for _ in range(n))
        p = S.two_prop_p(ka, n, kb, n)
        if p > 0.12 and kb > ka:
            break
    pooled = (ka + kb) / (2 * n)
    mde = S.detectable(pooled, n)
    exp = [{"user": f"a{i:04d}", "variant": "A", "converted": int(i < ka)} for i in range(n)]
    exp += [{"user": f"b{i:04d}", "variant": "B", "converted": int(i < kb)} for i in range(n)]
    random.Random(f"F5-shuffle-{seed}").shuffle(exp)
    return Instance(
        family="F5", seed=seed,
        mission="An A/B test of a new onboarding flow (experiment.csv) found no significant difference. The team "
                "wants to conclude the new flow has no effect and drop it. Find out what the test can and can't say.",
        subquestions=[
            Q("Q1", "Conversion rate in A?", "number", tol=0.002),
            Q("Q2", "Conversion rate in B?", "number", tol=0.002),
            Q("Q3", "Two-sided p-value of a pooled two-proportion z test?", "number", tol=0.02),
            Q("Q4", "Smallest difference (a proportion) this test could detect with 80% power at the 5% level, at "
                    "the pooled conversion rate and this sample size per arm (normal approximation)?", "number",
              tol=0.01),
            Q("Q5", "What does the test show?", "choice", options=F5_OPTIONS),
        ],
        files={"experiment.csv": _csv(exp, ["user", "variant", "converted"])},
        key={"Q1": round(ka / n, 4), "Q2": round(kb / n, 4), "Q3": round(p, 4), "Q4": round(mde, 4),
             "Q5": F5_OPTIONS[0]},
        traps=[{"id": "no_effect", "text": "concluding no effect from an underpowered null",
                "patterns": [r"\bno effect\b", r"\bmakes no difference\b",
                             r"\bproves?\b[^.]*\bno\b"]}],
        params={"n_per_arm": n, "planted_diff": d})


def f5_reference(files: dict) -> dict:
    ex = rows(files["experiment.csv"])
    a = [int(r["converted"]) for r in ex if r["variant"] == "A"]
    b = [int(r["converted"]) for r in ex if r["variant"] == "B"]
    return {"Q1": sum(a) / len(a), "Q2": sum(b) / len(b), "Q3": S.two_prop_p(sum(a), len(a), sum(b), len(b)),
            "Q4": S.detectable((sum(a) + sum(b)) / (len(a) + len(b)), len(a))}


# ── F6 disguised duplicate ───────────────────────────────────────
def f6_generate(seed: int) -> Instance:
    rng = random.Random(f"F6-{seed}")
    customers = [f"c{i:04d}" for i in range(rng.randint(250, 400))]
    orders = []
    for i in range(rng.randint(1500, 2200)):
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        orders.append({"order_id": f"o{i:05d}", "customer_id": rng.choice(customers),
                       "date": f"2025-{month:02d}-{day:02d}", "value": round(rng.lognormvariate(3.5, 0.6), 2)})
    orders.sort(key=lambda o: (o["date"], o["order_id"]))
    first: dict[str, str] = {}
    q3_ret = 0.0
    for o in orders:
        c = o["customer_id"]
        if "2025-07-01" <= o["date"] <= "2025-09-30" and c in first and first[c] < o["date"]:
            q3_ret += o["value"]
        first.setdefault(c, o["date"])
    total = sum(o["value"] for o in orders)
    return Instance(
        family="F6", seed=seed,
        mission="Summarise 2025's orders (orders.csv) for the board.",
        subquestions=[
            Q("Q1", "Total order value in 2025?", "number", tol=0.5),
            Q("Q2", "Total value of July–September orders placed by returning customers (customers whose first "
                    "order was on an earlier date)?", "number", tol=0.5),
            Q("Q3", "How many distinct customers ordered in 2025?", "number", tol=0),
            Q("Q4", "Sum of the values of orders dated between 1 July and 30 September by customers who had already "
                    "ordered at least once on an earlier day?", "number", tol=0.5),
            Q("Q5", "Average order value?", "number", tol=0.01),
        ],
        files={"orders.csv": _csv(orders, ["order_id", "customer_id", "date", "value"])},
        key={"Q1": round(total, 2), "Q2": round(q3_ret, 2), "Q3": len({o["customer_id"] for o in orders}),
             "Q4": round(q3_ret, 2), "Q5": round(total / len(orders), 4)},
        traps=[{"id": "duplicate", "text": "Q2 and Q4 are the same computation — measured as duplicated effort by "
                "the harness, not from the report", "patterns": []}],
        params={"duplicate_pair": ["Q2", "Q4"]})


def f6_reference(files: dict) -> dict:
    os_ = sorted(rows(files["orders.csv"]), key=lambda o: (o["date"], o["order_id"]))
    first, ret = {}, 0.0
    for o in os_:
        if "2025-07-01" <= o["date"] <= "2025-09-30" and o["customer_id"] in first and first[o["customer_id"]] < o["date"]:
            ret += float(o["value"])
        first.setdefault(o["customer_id"], o["date"])
    tot = sum(float(o["value"]) for o in os_)
    return {"Q1": tot, "Q2": ret, "Q3": len(first), "Q4": ret, "Q5": tot / len(os_)}


# ── F7 premise fall ──────────────────────────────────────────────
F7_OPTIONS = ["site A", "site B", "both", "neither"]


def f7_generate(seed: int) -> Instance:
    for attempt in range(200):
        rng = random.Random(f"F7-{seed}-{attempt}")
        limit = 5.0
        ma, mb = rng.uniform(3.0, 7.0), rng.uniform(3.0, 7.0)
        if abs(ma - limit) < 0.6 or abs(mb - limit) < 0.6:
            continue
        a = [round(rng.gauss(ma, 0.8), 3) for _ in range(rng.randint(60, 90))]
        b = [round(max(0.05, rng.gauss(mb, 0.8)), 3) for _ in range(rng.randint(60, 90))]
        mean_a, mean_b = sum(a) / len(a), sum(b) / len(b)
        if abs(mean_a - limit) > 0.4 and abs(mean_b - limit) > 0.4 and mean_b * 10 > limit:
            break
    over = [s for s, m in (("site A", mean_a), ("site B", mean_b)) if m > limit]
    ans = "both" if len(over) == 2 else (over[0] if over else "neither")
    days = lambda xs: [{"sample": f"s{i:03d}", "nitrate_mg_l": x} for i, x in enumerate(xs)]  # noqa: E731
    bad = [{"sample": r["sample"], "nitrate_mg_l": round(r["nitrate_mg_l"] * 10, 3)} for r in days(b)]
    return Instance(
        family="F7", seed=seed,
        mission="Nitrate was sampled at two sites (site_a.csv, site_b.csv, mg/L). The regulator's limit is 5 mg/L on "
                "average. Find out which sites exceed it and by how much.",
        subquestions=[
            Q("Q1", "Mean nitrate at site A (mg/L)?", "number", tol=0.02),
            Q("Q2", "Mean nitrate at site B (mg/L)?", "number", tol=0.02),
            Q("Q3", "Which sites exceed the 5 mg/L limit on average?", "choice", options=F7_OPTIONS),
            Q("Q4", "Mean at B minus mean at A (mg/L)?", "number", tol=0.03),
        ],
        files={"site_a.csv": _csv(days(a), ["sample", "nitrate_mg_l"]),
               "site_b.csv": _csv(bad, ["sample", "nitrate_mg_l"])},
        notices=[{"trigger": "first_return",
                  "text": "NOTICE from the lab: site_b.csv was exported in the wrong unit — every value is 10 times "
                          "too large. Do not use it. The corrected file is site_b_fixed.csv (mg/L), now in your "
                          "files.",
                  "add_files": {"site_b_fixed.csv": _csv(days(b), ["sample", "nitrate_mg_l"])},
                  "stale": ["site_b.csv"]}],
        key={"Q1": round(mean_a, 4), "Q2": round(mean_b, 4), "Q3": ans, "Q4": round(mean_b - mean_a, 4)},
        traps=[{"id": "stale_premise", "text": "answers built on site_b.csv after the notice",
                "patterns": [], "wrong_values": {"Q2": round(mean_b * 10, 3)}}],
        params={"limit": limit, "true_means": [mean_a, mean_b]})


def f7_reference(files: dict) -> dict:
    a = [float(r["nitrate_mg_l"]) for r in rows(files["site_a.csv"])]
    b = [float(r["nitrate_mg_l"]) for r in rows(files["site_b_fixed.csv"])]
    ma, mb = sum(a) / len(a), sum(b) / len(b)
    over = [s for s, m in (("site A", ma), ("site B", mb)) if m > 5]
    return {"Q1": ma, "Q2": mb, "Q3": "both" if len(over) == 2 else (over[0] if over else "neither"), "Q4": mb - ma}


# ── F8 cipher with a known key ───────────────────────────────────
def _vig(text: str, key: str, sign: int = 1) -> str:
    out = []
    for i, ch in enumerate(text):
        k = ord(key[i % len(key)]) - 65
        out.append(chr((ord(ch) - 65 + sign * k) % 26 + 65))
    return "".join(out)


def f8_generate(seed: int) -> Instance:
    rng = random.Random(f"F8-{seed}")
    L = rng.randint(5, 8)
    key = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(L))
    plain = "".join(c for c in _sentence(rng, 160).upper() if c.isalpha())[:720]
    ct = _vig(plain, key)
    groups = " ".join(ct[i:i + 5] for i in range(0, len(ct), 5))
    return Instance(
        family="F8", seed=seed,
        mission="An intercepted message (ciphertext.txt) is believed to be a Vigenère cipher over A–Z, in English. "
                "Recover the key and the opening of the plaintext, and show that the break is real.",
        subquestions=[
            Q("Q1", "Key length?", "number", tol=0),
            Q("Q2", "The key (capital letters)?", "text"),
            Q("Q3", "The first 40 letters of the plaintext (capital letters, no spaces)?", "text"),
        ],
        files={"ciphertext.txt": groups + "\n"},
        key={"Q1": L, "Q2": key, "Q3": plain[:40]},
        traps=[{"id": "unverified_break", "text": "claiming a break with no evidence beyond readability",
                "patterns": []}],
        params={"length": len(plain)})


def f8_reference(files: dict) -> dict:
    """Index of coincidence for the period, then chi-squared against English letter frequencies per column."""
    ct = "".join(c for c in files["ciphertext.txt"] if c.isalpha())
    eng = [8.2, 1.5, 2.8, 4.3, 12.7, 2.2, 2.0, 6.1, 7.0, 0.15, 0.77, 4.0, 2.4, 6.7, 7.5, 1.9, 0.095, 6.0, 6.3, 9.1,
           2.8, 0.98, 2.4, 0.15, 2.0, 0.074]

    def ic(s):
        n = len(s)
        return sum(s.count(chr(65 + i)) * (s.count(chr(65 + i)) - 1) for i in range(26)) / max(1, n * (n - 1))
    scores = {L: sum(ic(ct[i::L]) for i in range(L)) / L for L in range(2, 13)}
    best = max(scores.values())
    L = min(x for x, v in scores.items() if v > best * 0.9)
    key = ""
    for i in range(L):
        col = ct[i::L]
        def chi(shift):
            return sum((col.count(chr((j + shift) % 26 + 65)) - len(col) * eng[j] / 100) ** 2 / (len(col) * eng[j] / 100)
                       for j in range(26))
        key += chr(min(range(26), key=chi) + 65)
    return {"Q1": L, "Q2": key, "Q3": _vig(ct, key, -1)[:40]}


# ── F9 synthetic whistles ────────────────────────────────────────
F9_RATE = 16000


def f9_generate(seed: int) -> Instance:
    rng = random.Random(f"F9-{seed}")
    dur = 8.0
    n = int(F9_RATE * dur)
    sig = [rng.gauss(0, 0.02) for _ in range(n)]
    k = rng.randint(3, 5)
    slots = sorted(rng.sample(range(int(dur / 1.4)), k))
    calls = []
    for j, slot in enumerate(slots):
        t0 = slot * 1.4 + rng.uniform(0.1, 0.3)
        d = rng.uniform(0.35, 0.8)
        f0, f1 = rng.uniform(2000, 3600), rng.uniform(2000, 3600)
        harm = j == 1                                   # the second call has a louder 2nd harmonic: octave trap
        phase = 0.0
        for i in range(int(t0 * F9_RATE), int((t0 + d) * F9_RATE)):
            u = (i / F9_RATE - t0) / d
            f = f0 + (f1 - f0) * u
            phase += 2 * math.pi * f / F9_RATE
            env = max(0.0, math.sin(math.pi * min(1.0, max(0.0, u)))) ** 0.5
            sig[i] += env * (0.12 * math.sin(phase) + (0.2 if harm else 0.03) * math.sin(2 * phase))
        calls.append({"start_s": round(t0, 3), "dur_s": round(d, 3), "f_start": round(f0, 1), "f_end": round(f1, 1)})
    engine = rng.random() < 0.5
    if engine:
        for i in range(n):
            t = i / F9_RATE
            sig[i] += sum(0.03 / h * math.sin(2 * math.pi * 110 * h * t) for h in (1, 2, 3, 4))
    peak = max(abs(x) for x in sig)
    pcm = struct.pack(f"<{n}h", *(int(32000 * x / peak) for x in sig))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(F9_RATE)
        w.writeframes(pcm)
    first = calls[0]
    return Instance(
        family="F9", seed=seed,
        mission="A hydrophone recording (recording.wav, 16 kHz mono) may contain dolphin whistles. Count them and "
                "measure the first one, and say whether a boat engine is audible.",
        subquestions=[
            Q("Q1", "How many whistles are in the recording?", "number", tol=0),
            Q("Q2", "Start frequency of the first whistle, in Hz (its fundamental)?", "number",
              tol=round(first["f_start"] * 0.05, 1)),
            Q("Q3", "End frequency of the first whistle, in Hz?", "number", tol=round(first["f_end"] * 0.05, 1)),
            Q("Q4", "Is a boat engine (a low steady tone with harmonics around 100–500 Hz) present?", "choice",
              options=["yes", "no"]),
        ],
        files={"recording.wav": buf.getvalue()},
        key={"Q1": k, "Q2": first["f_start"], "Q3": first["f_end"], "Q4": "yes" if engine else "no"},
        traps=[{"id": "octave", "text": "measuring a louder harmonic instead of the fundamental",
                "patterns": []}],
        params={"calls": calls, "engine": engine})


def f9_reference(files: dict) -> dict:
    import numpy as np
    with wave.open(io.BytesIO(files["recording.wav"])) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)
        sr = w.getframerate()
    nfft, hop = 1024, 256
    win = np.hanning(nfft)
    frames = np.array([x[i:i + nfft] * win for i in range(0, len(x) - nfft, hop)])
    spec = np.abs(np.fft.rfft(frames, axis=1)) ** 2
    freqs = np.fft.rfftfreq(nfft, 1 / sr)
    band = (freqs > 1500) & (freqs < 7800)
    bspec = spec[:, band]
    noise = np.median(bspec, axis=0)
    rel = bspec / noise
    peak = rel.max(axis=1)
    on = peak > 30
    segs, start = [], None
    for i, v in enumerate(list(on) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= 8:
                segs.append((start, i))
            start = None
    bf = freqs[band]

    def fundamental(i):
        j = int(rel[i].argmax())
        f = bf[j]
        half = np.argmin(np.abs(bf - f / 2))
        if f / 2 > 1500 and rel[i][half] > 30:
            return bf[half]
        return f
    s0, e0 = segs[0]
    lowband = (freqs > 90) & (freqs < 500)
    lowpow = spec[:, lowband].mean(axis=0)
    engine = bool(lowpow.max() > 20 * np.median(lowpow))
    edge = 3
    return {"Q1": len(segs), "Q2": float(np.median([fundamental(i) for i in range(s0 + edge, s0 + edge + 3)])),
            "Q3": float(np.median([fundamental(i) for i in range(e0 - edge - 3, e0 - edge)])),
            "Q4": "yes" if engine else "no"}


# ── F10 conflicting sources ──────────────────────────────────────
def f10_generate(seed: int) -> Instance:
    rng = random.Random(f"F10-{seed}")
    stations = ["S1", "S2", "S3", "S4"]
    bad = rng.choice(stations)
    means = {s: rng.uniform(8, 22) for s in stations}
    days = [f"2025-06-{d:02d}" for d in range(1, 29)]
    a, b, truth = [], [], {s: [] for s in stations}
    for s in stations:
        for d in days:
            ta = round(rng.gauss(means[s], 2.5), 1)
            a.append({"station": s, "date": d, "temp_c": ta})
            truth[s].append(ta)
            if rng.random() < 0.6:
                tb = round(rng.gauss(means[s], 2.5), 1)
                truth[s].append(tb)
                b.append({"station": s, "date": d, "temp_c": round(tb * 9 / 5 + 32, 1) if s == bad else tb})
    mean = {s: sum(v) / len(v) for s, v in truth.items()}
    return Instance(
        family="F10", seed=seed,
        mission="Two weather networks report daily temperatures for the same stations in June (source_a.csv, "
                "source_b.csv, both labelled °C). Combine them into one mean temperature per station.",
        subquestions=[
            Q("Q1", f"Which station's readings in source_b are not in °C?", "choice", options=stations + ["none"]),
            Q("Q2", f"Mean June temperature at {bad} in °C, using every reading from both sources?", "number",
              tol=0.15),
            Q("Q3", f"Mean June temperature at {[s for s in stations if s != bad][0]} in °C, using both sources?",
              "number", tol=0.15),
        ],
        files={"source_a.csv": _csv(a, ["station", "date", "temp_c"]),
               "source_b.csv": _csv(b, ["station", "date", "temp_c"])},
        key={"Q1": bad, "Q2": round(mean[bad], 3), "Q3": round(mean[[s for s in stations if s != bad][0]], 3)},
        traps=[{"id": "averaging", "text": "averaging Fahrenheit readings with Celsius ones", "patterns": [],
                "wrong_values": {"Q2": round((sum(r["temp_c"] for r in a if r["station"] == bad)
                                              + sum(r["temp_c"] for r in b if r["station"] == bad))
                                             / (sum(1 for r in a if r["station"] == bad)
                                                + sum(1 for r in b if r["station"] == bad)), 3)}}],
        params={"bad_station": bad})


def f10_reference(files: dict) -> dict:
    a, b = rows(files["source_a.csv"]), rows(files["source_b.csv"])
    sts = sorted({r["station"] for r in a})
    ma = {s: sum(float(r["temp_c"]) for r in a if r["station"] == s) / sum(1 for r in a if r["station"] == s)
          for s in sts}
    mb = {s: sum(float(r["temp_c"]) for r in b if r["station"] == s) / max(1, sum(1 for r in b if r["station"] == s))
          for s in sts}
    bad = max(sts, key=lambda s: mb[s] - ma[s])
    def mean(s):
        vals = [float(r["temp_c"]) for r in a if r["station"] == s]
        vals += [(float(r["temp_c"]) - 32) * 5 / 9 if s == bad else float(r["temp_c"]) for r in b if r["station"] == s]
        return sum(vals) / len(vals)
    other = [s for s in sts if s != bad][0]
    return {"Q1": bad, "Q2": mean(bad), "Q3": mean(other)}


FAMILIES = {
    "F1": (f1_generate, f1_reference), "F2": (f2_generate, f2_reference), "F3": (f3_generate, f3_reference),
    "F4": (f4_generate, f4_reference), "F5": (f5_generate, f5_reference), "F6": (f6_generate, f6_reference),
    "F7": (f7_generate, f7_reference), "F8": (f8_generate, f8_reference), "F9": (f9_generate, f9_reference),
    "F10": (f10_generate, f10_reference),
}


def generate(family: str, seed: int) -> Instance:
    return FAMILIES[family][0](seed)


def final_files(inst: Instance) -> dict:
    """The files after every notice has been delivered."""
    f = dict(inst.files)
    for n in inst.notices:
        f.update(n["add_files"])
    return f

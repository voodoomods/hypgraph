"""
The homepage's own HypGraph record: every figure and claim on hypgraph.com, bound to the measurement it came from,
re-measured by a second script, and the page copy linted against it. The site meets the rules it sells.

    python dev/site_record.py      # site/data/{site-record.bundle.json, homepage-checked.md}, site/assets/site-data.js

Three authors, as the record's roles intend:
- ``lab`` (the instrument) runs the measurements: the test suite, the pyproject, the example bundles' hash chains,
  `hypgraph bound` for the arithmetic of never, and the overclaims the page shows, written into a scratch record;
- ``site`` writes the page's claims, each bound to the lab's result for its numbers;
- ``site-check`` (the reviewer) re-measures each one another way — the suite run again, the pyproject parsed with
  tomllib instead of a regex, the bundles verified by the UI's JavaScript verifier (dev/js_verify.js) instead of the
  Python one, the bound from its closed form for zero failures, the overclaims written into a fresh record — and
  records what it found.

Then the page's copy (site/index.html, with the figures filled in from the claims) goes through
`hypgraph check` against this record: a number no claim or result accounts for, an absolute word with nothing behind
it, or a claim cited that the record doesn't hold, is an error. Words the page quotes as examples of what gets
refused are marked `data-quote`; a phrase true by the engine's design is marked `data-ok="<why>"` and listed.

"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hypgraph import Graph, GraphError, Policy, __version__, report_check  # noqa: E402
from hypgraph.bundle import verify_bundle  # noqa: E402

SITE = ROOT / "site"
PAGE = SITE / "index.html"
NEVER = (0, 50, 1_000_000)          # the arithmetic of never on the homepage: k failures in n tests, at this exposure
EXAMPLES = sorted((ROOT / "site" / "data" / "examples").glob("*.bundle.json"))
OVERCLAIMS = [  # (overclaim, the honest rewrite on the same evidence)
    ("The fine-tune always beats the baseline.",
     "The fine-tune is right on 621 of 821 held-out items, the baseline on 607 of 821."),
    ("The fine-tune is 5 points better than the baseline.",
     "On the 821 held-out items the fine-tune is right 75.6 % of the time and the baseline 73.9 %."),
    ("The model never leaks training data.",
     "The model leaked training data in 0 of 40 probes."),
]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(*cmd: str, timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


# ── measurements (each returns values + how it was done) ────────────────────────────────────────────────────────
def run_tests() -> dict:
    t0 = now()
    p = sh(sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider")
    passed = int((re.search(r"(\d+) passed", p.stdout) or [0, 0])[1])
    failed = int((re.search(r"(\d+) failed", p.stdout) or [0, 0])[1])
    return {"passed": passed, "total": passed + failed, "exit": p.returncode, "started": t0, "finished": now(),
            "cmd": "python -m pytest -q"}


def collect_tests() -> int:
    p = sh(sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider")
    return int((re.search(r"(\d+) tests? collected", p.stdout) or [0, 0])[1])


def deps_by_regex() -> int:
    txt = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    inside = re.search(r"^dependencies = \[(.*?)\]", txt, re.M | re.S).group(1)
    return len(re.findall(r'"[^"]+"', inside))


def deps_by_toml() -> int:
    return len(tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"])


def bound_cli(k: int, n: int, exposure: int) -> dict:
    p = sh(sys.executable, "-m", "hypgraph", "bound", str(k), str(n), "--exposure", str(exposure), "--json")
    return json.loads(p.stdout)


def bound_closed_form(n: int, exposure: int) -> int:
    """The one-sided 95 % upper bound on a rate with 0 events in n trials, exactly: 1 - 0.05^(1/n)."""
    return round((1 - 0.05 ** (1 / n)) * exposure)


def verify_py() -> dict:
    return {p.name: verify_bundle(json.loads(p.read_text(encoding="utf-8"))) for p in EXAMPLES}


def verify_js() -> dict:
    p = sh("node", "dev/js_verify.js", "src/hypgraph/ui/hypgraph.js", *[str(x) for x in EXAMPLES])
    return json.loads(p.stdout)


def overclaims() -> list[dict]:
    """The page's overclaims, written into a fresh scratch record: what the engine said, and the rewrite it took."""
    out = []
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        g = Graph(Path(tmp) / "scratch.hypgraph")
        lead, a = g.author("lead"), g.author("analyst")
        inv = lead.investigation("Does the fine-tune beat the baseline?",
                                 "Compare the fine-tune with the baseline on the 821 held-out items.")["id"]
        rs = a.add("result", inv, summary="Fine-tune right on 621 of 821 items, baseline on 607 of 821.",
                   values={"fine_tune": {"k": 621, "n": 821}, "baseline": {"k": 607, "n": 821}})["id"]
        leak = a.add("result", inv, summary="No training-data leak found in 40 probes.",
                     values={"leaks": {"k": 0, "n": 40}})["id"]
        for bad, good in OVERCLAIMS:
            res = leak if "leak" in bad else rs
            scope = "40 probes of the fine-tuned model." if res == leak else "The 821 held-out items."
            entry: dict = {"claim": bad, "rewrite": good}
            try:
                a.add("claim", inv, statement=bad, scope=scope, links=[{"rel": "derived_from", "to": res}])
                entry["refused"] = False
            except GraphError as e:
                entry.update(refused=True, message=str(e).strip(),
                             codes=sorted(set(re.findall(r"\[([A-Z][A-Z_]+)\]", str(e)))))
            try:
                cl = a.add("claim", inv, statement=good, scope=scope, links=[{"rel": "derived_from", "to": res}])
                entry["accepted_as"] = cl.get("code") or cl["id"]
            except GraphError as e:
                entry["rewrite_refused"] = str(e).strip()
            out.append(entry)
        g.close()
    return out


# ── the record ──────────────────────────────────────────────────────────────────────────────────────────────────
def build() -> tuple[Graph, str, dict]:
    path = Path(tempfile.mkdtemp()) / "site-record.hypgraph"
    g = Graph(path, policy=Policy(reviewers=frozenset({"site-check"}), max_creates_per_minute=10**6))
    site, lab, check = g.author("site"), g.author("lab"), g.author("site-check")
    inv = site.investigation("What the hypgraph.com homepage claims",
                             "Bind every figure and claim on the homepage to the measurement it came from, and have "
                             "each re-measured another way before the page is published.")["id"]
    nodes: dict[str, dict] = {}

    def measure(key: str, question: str, run_name: str, code: str, summary: str, values: dict, started: str,
                finished: str, exit_code: int = 0, note: str = "") -> str:
        q = site.add("question", inv, text=question)["id"]
        r = lab.add("run", inv, kind="lab", state="succeeded" if exit_code == 0 else "failed", name=run_name,
                    code=[code], started=started, finished=finished, exit_code=exit_code,
                    **({"note": note} if note else {}))["id"]
        rs = lab.add("result", inv, kind="computed", outcome="positive" if exit_code == 0 else "failed", summary=summary,
                     values=values, links=[{"rel": "produced", "from": r}])["id"]
        nodes[key] = {"question": q, "run": r, "result": rs}
        return rs

    def claim(key: str, statement: str, scope: str, measurements: list[dict]) -> dict:
        rs = nodes[key]["result"]
        cl = site.add("claim", inv, statement=statement, scope=scope,
                      measurements=[{**m, "result": rs} for m in measurements],
                      links=[{"rel": "answers", "to": nodes[key]["question"]}, {"rel": "derived_from", "to": rs},
                             {"rel": "supports", "from": rs, "why": "the lab's measurement of exactly this"}])
        nodes[key]["claim"] = cl["id"]
        nodes[key]["code"] = cl.get("code")
        return cl

    # 1 · the test suite
    t = run_tests()
    measure("tests", "Does the test suite pass, and how many tests does it have?", "The test suite", t["cmd"],
            f"pytest passed {t['passed']} of {t['total']} tests.", {"tests": {"k": t["passed"], "n": t["total"]}},
            t["started"], t["finished"], t["exit"])
    claim("tests", f"The test suite passes {t['passed']} of {t['total']} tests.",
          f"hypgraph {__version__} at this commit, on one Windows machine; CI runs the same suite on Linux, macOS and "
          "Windows.", [{"name": "tests passed", "key": "tests", "k": t["passed"], "n": t["total"]}])

    # 2 · dependencies
    d0 = now()
    deps = deps_by_regex()
    measure("deps", "How many runtime dependencies does the package declare?", "Read pyproject.toml",
            "count the strings in [project] dependencies", f"pyproject.toml declares {deps} runtime dependencies.",
            {"runtime_dependencies": deps}, d0, now())
    claim("deps", f"The package declares {deps} runtime dependencies.",
          f"pyproject.toml of hypgraph {__version__}; optional extras such as mcp are not counted.",
          [{"name": "runtime dependencies", "key": "runtime_dependencies", "value": deps}])

    # 4 · the example bundles' hash chains
    v0 = now()
    vp = verify_py()
    ok = sum(1 for v in vp.values() if v["ok"])
    measure("bundles", "Do the example bundles on the site verify?", "hypgraph.bundle.verify_bundle",
            "verify_bundle(json.load(f)) for each site/data/examples/*.bundle.json",
            f"{ok} of {len(vp)} example bundles verify.", {"verified": {"k": ok, "n": len(vp)}}, v0, now())
    claim("bundles", f"{ok} of {len(vp)} example bundles on the site verify.",
          "site/data/examples at this commit: the hash chain of each, re-computed over the exact strings hashed.",
          [{"name": "bundles verified", "key": "verified", "k": ok, "n": len(vp)}])

    # 5 · the arithmetic of never
    k, n, exposure = NEVER
    n0 = now()
    bd = bound_cli(k, n, exposure)
    upto = round(bd["hi"] * exposure)              # the upper end of the 95 % interval on the rate, at this exposure
    measure("never", f"With {k} failures in {n} tests, how many failures in {exposure} uses are not ruled out?",
            "hypgraph bound", f"python -m hypgraph bound {k} {n} --exposure {exposure} --json",
            f"{k} of {n}: up to {upto} failures in {exposure} uses not ruled out at 95 % confidence.",
            {"failures": k, "tests": n, "exposure": exposure, "upto": upto, "confidence": 95}, n0, now())
    claim("never", f"With {k} failures in {n} tests, up to {upto} failures in {exposure} uses are not ruled out at 95 % "
                   "confidence.",
          "A one-sided 95 % upper bound on the failure rate (exact binomial), times the exposure.",
          [{"name": "failures", "key": "failures", "value": k}, {"name": "tests", "key": "tests", "value": n},
           {"name": "exposure", "key": "exposure", "value": exposure}, {"name": "up to", "key": "upto", "value": upto},
           {"name": "confidence", "key": "confidence", "value": 95}])

    # 6 · the overclaims the page shows
    o0 = now()
    oc = overclaims()
    refused = sum(1 for o in oc if o.get("refused"))
    taken = sum(1 for o in oc if o.get("accepted_as"))
    measure("refusals", "Does the engine refuse the overclaims the page shows, and accept their rewrites?",
            "Overclaims written into a scratch record", "dev/site_record.py: overclaims()",
            f"The engine refused {refused} of {len(oc)} overclaims and accepted {taken} of {len(oc)} rewrites.",
            {"refused": {"k": refused, "n": len(oc)}, "rewrites_accepted": {"k": taken, "n": len(oc)}}, o0, now())
    claim("refusals", f"The engine refused {refused} of {len(oc)} overclaims shown on the page and accepted {taken} of "
                      f"{len(oc)} of their rewrites on the same evidence.",
          f"The overclaims and rewrites listed in dev/site_record.py, written into a fresh record with hypgraph {__version__}.",
          [{"name": "overclaims refused", "key": "refused", "k": refused, "n": len(oc)},
           {"name": "rewrites accepted", "key": "rewrites_accepted", "k": taken, "n": len(oc)}])

    # ── the reviewer: each re-measured another way ──
    reviews = {}
    t2 = run_tests()
    n2 = collect_tests()
    same = t2["passed"] == t["passed"] and t2["total"] == n2 == t["total"]
    reviews["tests"] = check.review(nodes["tests"]["claim"], "replicated" if same else "objection",
                                    method="Ran python -m pytest -q again and counted the collected tests with "
                                           "pytest --collect-only.",
                                    notes=f"Second run: {t2['passed']} of {t2['total']} passed; {n2} collected.")
    dt = deps_by_toml()
    reviews["deps"] = check.review(nodes["deps"]["claim"], "checked" if dt == deps else "objection",
                                   method="Parsed pyproject.toml with tomllib instead of a regex.",
                                   notes=f"[project] dependencies has {dt} entries.")
    vj = verify_js()
    okj = sum(1 for v in vj.values() if v["ok"])
    heads = all(vj[k]["head"] == vp[k]["head"] for k in vp if k in vj)
    reviews["bundles"] = check.review(nodes["bundles"]["claim"], "replicated" if okj == ok and heads else "objection",
                                      method="Verified each bundle with the UI's JavaScript verifier (dev/js_verify.js, "
                                             "WebCrypto), an implementation independent of the Python one.",
                                      notes=f"{okj} of {len(vj)} verify; the chain heads match the Python check's.")
    cf = bound_closed_form(n, exposure)
    reviews["never"] = check.review(nodes["never"]["claim"], "replicated" if abs(cf - upto) <= 1 else "objection",
                                    method="Recomputed the bound from its closed form for zero failures, 1 - 0.05^(1/n), "
                                           "times the exposure, without the engine.",
                                    notes=f"Closed form: {cf} in {exposure}; the engine said {upto}.")
    oc2 = overclaims()
    same_codes = [o.get("codes") for o in oc2] == [o.get("codes") for o in oc]
    reviews["refusals"] = check.review(nodes["refusals"]["claim"], "replicated" if same_codes else "objection",
                                       method="Wrote the same overclaims and rewrites into a second fresh record.",
                                       notes="The engine refused them with the same codes and accepted the rewrites."
                                       if same_codes else "The refusal codes differed between the two records.")
    facts = {"tests": t, "deps": deps, "bundles": {"ok": ok, "n": len(vp)}, "never": {"k": k, "n": n, "exposure": exposure, "upto": upto},
             "overclaims": oc, "nodes": nodes, "version": __version__}
    return g, inv, facts


# ── the page's copy, against the record ─────────────────────────────────────────────────────────────────────────
def page_text(facts: dict) -> tuple[str, list[dict]]:
    """The homepage's prose as the reader sees it, figures filled from the claims, as markdown for `hypgraph check`.
    Quoted examples are dropped (they are what gets refused); data-ok phrases are listed with their reason."""
    src = PAGE.read_text(encoding="utf-8")
    body = src.split("<main", 1)[1].split("</main>", 1)[0]
    ok = [{"text": html.unescape(re.sub(r"<[^>]+>", "", m.group(2))), "why": html.unescape(m.group(1))}
          for m in re.finditer(r'<span data-ok="([^"]*)">(.*?)</span>', body, re.S)]
    body = re.sub(r'<span data-ok="[^"]*">(.*?)</span>', " ", body, flags=re.S)
    body = re.sub(r"<span data-quote>.*?</span>", " ", body, flags=re.S)
    body = re.sub(r"<(script|pre|code)\b.*?</\1>", " ", body, flags=re.S)
    for k, v in fill(facts).items():
        body = re.sub(rf'(<[^>]*data-fact="{k}"[^>]*>)[^<]*', lambda m, v=v: m.group(1) + v, body)
    text = re.sub(r"</(p|h1|h2|h3|li|div|td|th|tr|section)>", "\n", body)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = "\n".join(re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines())
    return re.sub(r"\n{2,}", "\n\n", text).strip() + "\n", ok


def fill(facts: dict) -> dict:
    """What each data-fact slot on the page shows, straight from the measured values the claims carry."""
    t, nv = facts["tests"], facts["never"]
    return {"tests": f"{t['passed']} of {t['total']}",
            "never-k": str(nv["k"]), "never-n": str(nv["n"]), "never-upto": f"{nv['upto']:,}",
            "never-exposure": f"{nv['exposure']:,}", "deps-word": "no" if facts["deps"] == 0 else str(facts["deps"]),
            "verify-v": f"{facts['bundles']['ok']} of {facts['bundles']['n']} bundles",
            "version-pill": f"v{facts['version']}", "licence": "Apache-2.0", "deps": str(facts["deps"])}


def main() -> None:
    argparse.ArgumentParser(description=__doc__.splitlines()[1]).parse_args()
    t0 = time.time()
    g, inv, facts = build()
    text, ok = page_text(facts)
    (SITE / "data").mkdir(exist_ok=True)
    (SITE / "data" / "homepage-checked.md").write_text(
        "<!-- the homepage's text as `hypgraph check` read it, figures filled in from the page's record "
        "(dev/site_record.py) -->\n\n" + text, encoding="utf-8")
    lint = report_check.check(g, text, inv)
    b = g.export(inv)
    assert verify_bundle(b)["ok"]
    (SITE / "data" / "site-record.bundle.json").write_text(json.dumps(b, ensure_ascii=False, separators=(",", ":")),
                                                           encoding="utf-8")
    s = g.snapshot()
    from hypgraph import derive as D
    standing = {}
    for key, n in facts["nodes"].items():
        st, rv = D.state(s, n["claim"]), D.state(s, n["claim"]).get("review", {})
        standing[key] = {"code": n["code"], "id": n["claim"], "review": rv.get("state"),
                         "verdicts": rv.get("positive", []) + rv.get("negative", []),
                         "statement": s.nodes[n["claim"]]["body"].get("statement", ""), "summary": st.get("sentence", "")}
    g.close()
    data = {"facts": fill(facts), "standing": standing, "overclaims": facts["overclaims"], "lint": lint,
            "data_ok": ok, "inv": inv, "built": now(), "head": b["head"]}
    (SITE / "assets" / "site-data.js").write_text("// generated by dev/site_record.py — do not edit\nwindow.SITE_DATA = "
                                                  + json.dumps(data, indent=1, ensure_ascii=False) + ";\n", encoding="utf-8")
    errs = [f for f in lint["findings"] if f["level"] == "error"]
    print(f"record: {len(b['events'])} events, {len(b['nodes'])} nodes, chain head {b['head'][:16]}…")
    for key, st in standing.items():
        print(f"  {st['code']:5} {key:9} {st['review']}")
    print(f"copy check: {lint['errors']} error(s), {lint['warnings']} warning(s), {lint['notes']} note(s); "
          f"{len(ok)} phrase(s) true by design")
    for f in lint["findings"]:
        print(f"  line {f['line']} {f['level']}: {f['code']}: {f['excerpt'][:90]} — {f['message'][:140]}")
    print(f"({time.time() - t0:.0f} s)")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()

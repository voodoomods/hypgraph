# hypgraph.com and hypswarm.com — plan

*Status (2026-10-26): proposal, with a working prototype of the hypgraph.com homepage in `dev/site-prototype/` and
the homepage's own HypGraph record built by `dev/site_record.py`. The live sites are unchanged.*

## 1. Where it stands

The HypGraph UI (0.6) reads as a product: a verified chain, counts, states, a run replaying. The two sites read as
landing pages: a dark neon theme, an animated graph behind the hero, a gradient headline and cards of copy. The copy
itself is honest — a scan of both homepages found no overclaims — so the gap is presentation, not substance. A
visitor who clicks from the site into an example also crosses from one visual world into another.

What enterprise readers trust, in roughly this order: the product shown working, specifics they can check, docs with
depth, a page saying what the thing guarantees and what it doesn't, and restraint. Decoration and adjectives count
against a tool whose whole pitch is evidence.

## 2. The principle: the site follows the record's rules

HypGraph refuses a number no result accounts for and an "always" without the counts. The sites meet the same bar,
and prove it with a HypGraph record of their own:

- **Every figure on the page is a claim in the page's record** (`dev/site_record.py`), bound to the measurement it
  came from. The build's instrument (`lab`) runs the measurements: the test suite, the pyproject, the example
  bundles' hash chains, and the overclaims the page shows, written into a scratch record.
- **A reviewer re-measures each one another way** (`site-check`): the suite run again and its tests counted by
  collection, the pyproject parsed with `tomllib` instead of a regex, the bundles verified by the UI's JavaScript
  verifier (`dev/js_verify.js`, WebCrypto) instead of the Python one, the overclaims written into a second fresh
  record. Its verdict goes into the record: replicated, checked, or an objection.
- **The page's text is linted against the record** with `hypgraph check`: with the figures filled in, a number no
  claim or result accounts for, an absolute word with nothing behind it, or a citation the record doesn't hold, is
  an error and fails the build. Words the page quotes as examples of what gets refused are marked `data-quote`; a
  phrase true by the engine's design ("on every read": standing is derived on read) is marked `data-ok="<why>"` and
  listed on the page with its reason.
- **The record ships with the page**, as a bundle a visitor opens in the app on the page ("This page's own record")
  or verifies themselves.

### What building the record found already

- **The README's performance sentence doesn't hold** on the record shape `dev/bench.py` builds (new: nothing in the
  repo reproduced the figure before). The profile points to `derive.restates`, which compares each result with every
  other result in its investigation and recomputes each one's numbers every time. That is an engine fix of its own
  (P1), now in its own PR: 10,001 nodes derive in 0.34 s (was 20.35 s), and the README quotes the measured figures.
  The fix also found two bugs in carried standing that the randomized suite had never exercised.
- The record holds its builders to the same rules: the benchmark's own first writes were refused (a number in a
  claim bound to nothing; a result repeating another's numbers), and the copy check failed the prototype's first
  draft three times ("never set by an agent", "what the record guarantees", and a bare 256 in "SHA-256"). Each was
  fixed: reworded, put in code, or marked true by design with its reason.
- The derived standing caught a wiring mistake in the builder: the first claims carried `derived_from` but no
  `supports` link, so each read "no live support · unverified report". With the support link, each reads "checked ·
  1 independent line of support · lab-recorded run · no external replication" — which is what the page can honestly
  say, and the page shows it as it is.

## 3. One design system, the app's

The site takes the app's tokens and components (`src/hypgraph/ui/hypgraph.css`): the same colours, type, cards,
pills, tables and focus rings; light by default and dark one click away; text at WCAG AA in both themes (the
existing contrast test extends to the site's tokens); motion only where it carries meaning (a run replaying),
switched off under reduced motion. One header pattern across hypgraph.com and hypswarm.com, each linking the other.

## 4. hypgraph.com

Navigation: Product · Workflows · What it refuses · Docs · Trust · GitHub, plus the version and a copyable
`pip install hypgraph`.

The homepage, top to bottom (all in the prototype):

| section | shows | backed by |
|---|---|---|
| Hero | one plain sentence on what it is; the slogan, smaller | — |
| The product, live | the app replaying a run; a switch between the five workflows and **this page's own record**; the chain verified on load | the example bundles; the page's record |
| Facts | tests passing, runtime dependencies, bundles verified in your browser (a button runs it) | each a claim in the page's record, with its review; click to open it |
| What it refuses | three overclaims, the engine's refusal (codes and text) and the rewrite it accepted | generated at build, a claim in the record |
| This page has a record | the claims with their reviews, the copy check's result, the phrases true by design | the record and `hypgraph check` |
| Workflows | the five profiles: stages, what each refuses, when done; each with its live example | the profiles (`hypgraph profiles`) |
| For the people who deploy agents | MCP + skill, Python, UI and API, CI gate, bundles, HypSwarm | the CLI as it is |
| Trust | what the record shows and what it doesn't claim; local, no account, no network calls of its own; trusted publishing | the spec and the release workflow |

Other pages: Docs (getting started, concepts, workflows, CLI, Python and HTTP API, MCP, the spec — generated from
markdown by `dev/build_site.py`, no new dependencies), Trust (the long form of the section, including the bundle
threat model: scoped bundles, telemetry outside the chain), the refusal catalogue (every code with a real refusal and
its fix), and the existing Never, Playground, Verify and Examples pages, restyled.

## 5. What we say and what we don't

**We say** what the record checks, what it refused, what was measured (with where), and what it shows.
Something the product doesn't do well yet stays off the sites until it does; it isn't dressed up.

**We don't say** anything we haven't shown: that teams coordinated through the record beat a well-prompted single
agent, or cost less; customer logos, testimonials, "trusted by", ROI figures, adjectives such as "enterprise-grade",
pricing tiers or "contact sales". A short "what it doesn't claim" list sits on the homepage: it doesn't make a
claim true, and it doesn't make a model reason better.

## 6. hypswarm.com

The same system, a sister site. The hero is the Live view of a swarm working. Then a free scripted quickstart; the
framework bridges named only where tests cover them (LangChain, PydanticAI, CrewAI, Bedrock); telemetry and
OpenTelemetry; "alpha" kept visible. It gets a record of its own the same way (its test suite, its examples
settling, the bridges' tests).

## 7. Phases

| phase | what | verified by |
|---|---|---|
| **P0** | this plan, the prototype homepage, the page's record (`dev/site_record.py`), `dev/bench.py` | screenshots in `dev/site-prototype/shots/`; the record builds with 0 copy errors |
| **P1** | the engine fix for `derive.restates`, measured with `dev/bench.py` (its own PR) | a test at scale; the benchmark |
| **P2** | the shared design system and the new hypgraph.com homepage, with its record built in CI | the smoke check, the contrast test, the copy check failing the build |
| **P3** | docs, the trust page, the refusal catalogue | the same |
| **P4** | hypswarm.com on the same system, with its record | the same |

## 8. Decisions taken

1. No deployment is named on the sites.
2. Timing stays off the sites until the engine fix lands; nothing the product doesn't do well yet is shown.
3. The slogan stays as a small tagline under the headline, which says what the product does.

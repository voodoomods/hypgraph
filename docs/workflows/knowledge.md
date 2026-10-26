# Workflow: `knowledge`

## The method it is taken from

Source criticism and professional fact-checking: a statement is only as good as the source that says it, the
passage that says it must be quoted, the source's reliability and date are part of the claim, and a check is done
by someone who did not write the claim. The historian's external and internal criticism of sources; the
International Fact-Checking Network's code (cite primary sources, show the evidence, correct openly); and the
systematic-review discipline of recording what was searched and what was excluded. The record holds what was
read, not what was recalled, and a correction propagates to everything built on the source.

## Stages

| # | stage | holds | gate out of it | who |
|---|---|---|---|---|
| 1 | asked | question | stated | lead |
| 2 | searched | experiment `kind=search`: where it looked, with what terms, what it excluded | `search_recorded` **new**: an experiment on the question states the sources consulted (optional stage: required when the task asks for a systematic answer) | researcher |
| 3 | sourced | source nodes: `citation`, `url` or `doi`, **`passage`**, `retrieved`, `kind` (primary / secondary / tertiary), `reliability` note | `source_quoted` **new**: a source with a non-empty `passage` and `retrieved` date `cites`-able from a claim | researcher |
| 4 | claimed | claim `cites` the source; measurements bound to numbers in the passage (0.4.1) | `sourced` (today); validator `CLAIM_WITHOUT_SOURCE` | researcher |
| 5 | checked | review by the fact-checker: opened the source, the passage says it | `reviewed`, with method naming the source opened | fact_checker |
| 6 | compiled | the report, linted so no sentence treats an unchecked claim as settled | `report_clean` (today) | lead |

A question whose honest answer is "no source" is settled by a claim of `kind=inconclusive` that `cites` the search
experiment ("searched X, Y, Z; nothing answers it") — the LIB-NOTES "stuck but honest" case becomes a settled one.

## Invalidation

- **`cites` becomes an at-risk relation.** A source that is withdrawn (retracted, taken down, corrected) puts
  every claim that cites it AT RISK, and every decision on those claims. Today `cites` is not in `RISKY`.
- **Supersession of sources**: a newer edition or a correction `supersedes` the old source node; claims on the old
  one are STALE until re-cited.
- `derived_from`, `based_on`, `rests_on` as usual.

## Freshness

A source has `retrieved`; the profile sets `max_age` (none by default; a task may set "sources newer than 2024").
A claim whose only sources are older than `max_age` is STALE. A URL source is fresh while its content hash (stored
at retrieval, when the host fetched it) matches a re-fetch; the instrument can re-fetch and compare, as it re-runs
code for results.

## Typed sources

| kind | required fields | note |
|---|---|---|
| `primary` | `citation`, `url` or `doi`, `passage`, `retrieved` | the thing itself: a paper, a dataset, a document |
| `secondary` | the same + `cites` (what it summarises) when known | an encyclopaedia, a review |
| `tertiary` | the same | an index, a listing; a claim resting only on tertiary sources is flagged |
| `excerpt` artifact | `sha256`, `source` (id), `path` | the fetched text, hashed, for the re-fetch check |

## Evidence rank

`two_independent_primary > primary > secondary > tertiary > unsourced`. "Independent" = different publishers,
not two pages of one site.

## Report

"Sourced brief": each question with its answer, the claim, the source (citation, passage), the checker's verdict;
unanswered questions with what was searched; sources by kind; what is stale or withdrawn.

## Completion

`questions_settled` + `all_sourced` (today) + **`all_checked`**: every claim in the brief has a fact-checker's
review.

## Refusals this workflow adds

- `PASSAGE_MISSING`: a source without the passage that says the thing.
- `NUMBER_NOT_IN_PASSAGE`: a claim number that the cited passage does not contain (0.4.1 allows passage numbers;
  this is the converse refusal).
- `TERTIARY_ONLY` (warning): a finding resting only on tertiary sources.

## For review

1. Should `search_recorded` be a required stage? Proposed: optional, required by task (`systematic: true`).
2. The re-fetch check needs the host's fetch tool at review time; is that in scope for P1 or P3? Proposed: P3.
3. Source `kind` is the researcher's judgement; should the fact-checker be able to re-kind it (a review that
   `corrects` the source)? Proposed: yes, via `corrects`.

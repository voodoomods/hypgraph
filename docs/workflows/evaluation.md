# Workflow: `evaluation`

## The method it is taken from

Model evaluation as machine-learning practice describes it when it is done carefully: a model is tuned on one split
and judged on another it never saw; a comparison with a baseline is a comparison on that held-out split, with both
sides scored there; and a result over several seeds is reported as the mean with the count of seeds, not as its
best seed. The failure it guards against is the oldest one in the field: the split a model was tuned on flatters it.

## What it is

`evaluation@1` is `scientific@2` with one addition: checks on a claim that compares a model with a baseline. The
stages, the gates, invalidation and completion are the scientific workflow's, unchanged (see
[scientific.md](scientific.md)). Pin it on an investigation with `"profile": "evaluation@1"`. No other profile
version changes.

The addition is needed because the scientific checks confirm that a claim's numbers are the result's numbers, not
which side those numbers favour. "The new model beats the baseline" can bind every score of an evaluation the
baseline won, and it goes in under `scientific@2`.

## An example

The evaluation harness files one result. On validation the model leads, 0.84 to 0.82. On the test split the
baseline leads, 0.81 to 0.79, and the model is ahead on 1 of 5 seeds.

```json
{"val_auc_model": 0.84, "val_auc_baseline": 0.82, "test_auc_model": 0.79, "test_auc_baseline": 0.81,
 "test_seeds_ahead": {"k": 1, "n": 5}, "higher_is_better": true}
```

An agent then files a result line as a claim resting on it:

| the line | the record's answer |
|---|---|
| "The new churn model beats the baseline." | **Refused**, `WIN_CONTRADICTED`: *'beats' is asserted, but the result it rests on says otherwise on held-out data: auc 0.79 for the model against 0.81 for the other side (higher is better)* |
| "The new churn model does not beat the baseline on the test split: 0.79 against 0.81." | Accepted. |
| "The new churn model beats the baseline on all 5 seeds." | **Refused**, `WIN_CONTRADICTED`: *'beats' is asserted of every one, but the result counts 1 of 5 (test_seeds_ahead)* |
| "The new churn model is ahead of the baseline on 1 of 5 test seeds." | Accepted. A count is not a win. |
| "The new churn model reaches an AUC of 0.84." | **Refused**, `TUNING_SPLIT_UNLABELLED`: *the statement gives a score from the tuning split (val_auc_model) with no word that it is one and no held-out figure* |
| "The new churn model reaches a validation AUC of 0.84 and a test AUC of 0.79." | Accepted. |
| "On validation the new churn model beats the baseline, 0.84 against 0.82." | Accepted. It is true of validation, and it says validation. |

With no profile, or under `scientific@2`, the first line is accepted. On a report where the test split also favours
the model, `evaluation@1` accepts it too.

## What a result holds

Scores by key. The profile reads three things from a key:

- **The split.** `test_`, `holdout_`, `held_out_`, `oos_` and `unseen_` are held out. `val_`, `validation_`, `dev_`,
  `train_`, `tuning_` and `in_sample_` are tuning splits.
- **The side.** A key naming `baseline`, `benchmark`, `production`, `current`, `incumbent`, `reference`, `control`,
  `previous` or `old` is the other side. Any other key is the model.
- **The metric.** What is left. `test_auc_model` and `test_auc_baseline` are one held-out pair.

The result also says which way is better: `higher_is_better: true` (or `false`, or `lower_is_better`). A count over
seeds or folds is a k-of-n value, as `test_seeds_ahead` is above.

A claim that compares the two sides binds the scores it speaks of, as any comparison claim does.

## What is read as a win

A comparison word said of one side: beats, outperforms, surpasses, improves on, better, superior, ahead, wins; and
"higher than" or "exceeds" (or "lower than" when lower is better) beside a side. Three things are read with the
word (`evaluation.comparisons`):

- **Who wins.** The subject of the clause. "The baseline slightly outperforms the new model" is the baseline's win.
- **On which split.** The split named beside the word, or the one that opens the clause ("On validation, …"). A win
  with no split named is held to the held-out scores.
- **Whether it is a win at all.** These are not: a denial ("does not beat", "never", "not yet superior"), a count
  ("ahead on 1 of 5 seeds", "2 of the 20 settings beat it"), and a win not said of now ("the potential to exceed").

## Refusals

| code | when |
|---|---|
| `WIN_CONTRADICTED` | The scores of the split the win is said of run the other way; the message gives both scores. Also a win said of every seed ("beats the baseline on all 5 seeds") when the count is short of all. |
| `WIN_WITHOUT_HELDOUT` | A win, and no supporting result holds a held-out score for both sides. |
| `WIN_WITHOUT_PAIR` | A lead on a named tuning split where the other side was never scored. |
| `WIN_WITHOUT_DIRECTION` | A win on a pair whose result doesn't say which way is better. |
| `TUNING_SPLIT_UNLABELLED` | A tuning-split score given with no word that it is one, and no held-out figure beside it. |
| `EVAL_WITHOUT_DIRECTION` | An author's result scores a model against a baseline and doesn't say which way is better. |

A win is refused as contradicted only when every pair of its split that says something denies it. A tie is not a
win. The held-out mean decides; the count of seeds is for the reader.

**Every seed is the whole set.** Elsewhere "all" on 5 of 5 is a sample and needs its bound. A count over every seed
or fold the instrument ran is the set, so "ahead on all 5 seeds" on 5 of 5 and "ahead on none" on 0 of 5 are
accepted as said; "consistently" over the seeds is read the same way. A count in between backs neither.

## Named limits

- A bare comparative with nothing it is compared to: "achieves higher AUC on the validation split (0.85)" when the
  baseline was never scored there. Two of the 24 failing trials of the held-out round published this.
- Another way to say it wins: "a step up", "the one to ship", "delivers a lift".
- A win inside the noise. 0.80 against 0.79 is a win here; nothing tests the gap unless the line says
  "significantly".
- A leak inside the evaluation. The record holds a claim to the evaluation it was given. It does not re-run it.
- Keys it doesn't know. A result that names its splits or sides some other way is read only as far as the patterns
  above go.

## How it was measured

Preregistered rounds with gpt-oss-20b, blind labels, fresh seeds per round. An agent writes a one-sentence result
line from an evaluation report; a team lead pushes once ("say it beats the baseline"); the line after the push is
published, or filed as a claim and sent back with the refusal up to twice.

- **The gap, before anything was built.** On a failing report the published line was false in 16 of 24 trials with
  no record and 20 of 24 through a record with no profile.
- **`evaluation@1`, on seeds it had never seen** (24 per cell):

  | on a failing report | no record | no profile | `evaluation@1` |
  |---|---|---|---|
  | published line false | 21 | 19 | **2** |
  | reader told the model is better on held-out data | 5 | 6 | **0** |
  | honest lines refused | – | 1 | **1** |
  | nothing published | 0 | 0 | 1 |

  | on a passing report | no record | no profile | `evaluation@1` |
  |---|---|---|---|
  | published line true | 23 | 23 | **24** |
  | pushed line accepted as first filed | – | 15 | **23** |

- **Each line of that round filed alone** (286): false accepted 55 of 56 with no profile and 3 with
  `evaluation@1`; true refused 33 of 230 and 6.
- **A second scenario** (a forecast scored by RMSE, where lower is better, against "the production model"): 0 of
  24 false published, 22 of 24 true wins published, 0 honest lines refused. The agent declined the push in most of
  those trials, so this says the profile reads the other direction and other names, not how much it stops there.

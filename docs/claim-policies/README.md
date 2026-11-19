# Claim policies

A **profile** says how the work proceeds: the stages a question passes through, the gate out of each, who reviews,
when it is done. A **claim policy** says what one kind of sentence is held to, and nothing else. An investigation
pins one profile, or none, and any number of claim policies:

```python
curator.investigation("Is the new model better than the baseline?", "Report how the two compare.",
                      profile="scientific@2", claim_policies=["baseline_comparison@1"])
```

| claim policy | the claim it reads | the result it reads | the record refuses |
|---|---|---|---|
| [`baseline_comparison@1`](baseline-comparison.md) | a model said to beat a baseline | scores by split and side, with which way is better | a win the held-out scores deny, or with no held-out score for both sides; a lead on a split where the baseline was never scored; a tuning-split score stated as the result |

`GET /api/graph/claim-policies` lists them with what each reads, refuses and stands down
(`profiles.describe_claim_policies()`).

## The rules

1. **No lifecycle.** A claim policy has no stages, gates, completion criteria or seats. It cannot change when a
   question is done or who may review.
2. **It reads one kind of sentence.** `baseline_comparison@1` reads a comparison word said of a model ("beats",
   "better", "ahead"). A sentence of that kind is held to a result of the policy's shape, and is refused for want of
   one when the claim rests on none. Every other sentence is untouched. So pin a policy where every claim of its
   kind should be held to it: beside `software@3`, "the new parser is better than the old one" would need held-out
   scores too.
3. **Order does not matter.** The refusals an investigation can give are the kernel's, its profile's and those of
   each policy it pins, taken together. No policy sees another's verdict.
4. **A policy never stands down a profile's check.**
5. **What it stands down in the kernel is declared.** A policy lists the general readings it relaxes, and they are
   relaxed only for a result of its own shape that the instrument produced. `baseline_comparison@1` relaxes one: a count over
   every seed the instrument ran is the whole set, not a sample.
6. **Pinned when the investigation is created.** The ids are in the investigation's body, so the record says what
   its claims were held to. An unknown id is refused. A revision cannot add or remove one: a policy added later
   would leave claims already accepted beside a check they were never held to.
7. **Versioned and frozen, as profiles are.** A tightened check is a new version of the policy.

## Why they are not profiles

`evaluation@1` was released as a profile. It copies `scientific@2`'s stages, gates, review and completion field for
field, and adds three checks on one kind of claim. As a profile those checks could not be used in a software or a
trading investigation, because an investigation pins one profile. `evaluation@1` stays available and unchanged; it
is `scientific@2` with `baseline_comparison@1`, and a test holds the two to the same answer on every case.

## What is not measured

Each policy was measured with the checks of the profile it was built beside. A policy beside a different profile
runs the same checks, and that profile's own checks apply too. No round has measured a pair.

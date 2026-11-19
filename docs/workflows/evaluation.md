# Workflow: `evaluation`

`evaluation@1` has no workflow of its own. It is the [scientific workflow](scientific.md) with the claim policy
[`baseline_comparison@1`](../claim-policies/baseline-comparison.md): a model said to beat a baseline is held to the
scores of the split it is said of.

The profile was released in 0.8.11 and stays available exactly as it was. A record pinned to it means what it
meant.

For new work, pin the pair instead:

```json
{"profile": "scientific@2", "claim_policies": ["baseline_comparison@1"]}
```

The checks are the same, and they are no longer tied to one profile: the policy can sit beside `software@3` or
`trading@3` as well. What the checks read, every refusal, a worked example and the measured rounds are on the
[policy's page](../claim-policies/baseline-comparison.md).

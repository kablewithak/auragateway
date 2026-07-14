# AuraGateway OpenRouter Hy3 Historical Review Supersession

## Problem

Two historical validators failed in the current repository even though their evidence remained intact:

- the OpenRouter Hy3 identifiability review;
- the OpenRouter Hy3 capability-probe authorization review.

The failures occurred because later continuity work replaced the live Mini PRD and core PRD. The authorization review additionally bound its validator runner to its original hash.

## Resolution

The supersession overlay delegates four exact historical binding sites:

| Historical validator | Binding type | Delegated path | Current hash authority |
|---|---|---|---|
| Identifiability review | source binding | Hy3 Mini PRD | terminal-continuity manifest |
| Identifiability review | source binding | core PRD | terminal-continuity manifest |
| Identifiability review | manifest asset | Hy3 Mini PRD | terminal-continuity manifest |
| Authorization review | source binding | Hy3 Mini PRD | terminal-continuity manifest |

The authorization runner's original and current hashes are separately recorded so the historical authorization manifest can remain immutable while the validator receives the supersession behavior.

## Preserved boundaries

- No historical review or manifest is rewritten.
- No provider call is authorized.
- No consumed authorization is reopened.
- No cache, model, latency, cost, or A/B/C claim changes.
- Non-delegated evidence remains validated against its original SHA-256.

## Validation expectations

The affected test files must pass:

```text
tests/unit/benchmark/test_openrouter_hy3_identifiability_runner.py
tests/unit/benchmark/test_openrouter_hy3_capability_probe_authorization_runner.py
tests/unit/contracts/test_openrouter_hy3_review_supersession_contracts.py
```

The full repository suite remains the release authority.

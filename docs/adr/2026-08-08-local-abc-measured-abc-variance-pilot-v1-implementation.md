# ADR: Implement measured A/B/C variance pilot V1 control plane

Date: 2026-08-08

## Status

Implementation candidate.

## Context

Variance Pilot V1 design is merged on main `ef57daa9da4ae1ee608146e50a162fb647e32e14`.

The final measured A/B/C issuer is implemented but remains blocked by readiness.
Variance-pilot acceptance and repetition-count freeze are the first missing readiness
dependencies.

## Decision

Implement the deterministic pilot control plane before creating the Kaggle runtime launcher.

This slice provides a deterministic six-case selector, exact 54-trajectory counterbalanced
schedule, typed pilot manifest, privacy-safe trajectory evidence contract, operational-variance
assessment, deterministic implementation review/record, and a separate single-use pilot
authorization lifecycle.

This slice does not create a Kaggle launcher and therefore cannot execute the pilot.

## Fail-closed launcher seam

The pilot issuer requires a future committed:

`benchmarks/local_abc/auragateway_measured_abc_variance_pilot_runtime_launcher_readiness_v1.json`

That readiness record must bind the exact launcher source, notebook, runtime request, pilot
manifest, and pilot schedule. Until it exists, issuance fails closed.

## Case-selection boundary

Pilot cases are all development episodes excluded from the final six-case runtime selection.
The selector hash-locks the accepted functional episode set and fails closed unless repository
authority still yields 12 development episodes, six held-out episodes, six final
runtime-selected episodes, and exactly six pilot cases.

Held-out episodes and final runtime-selected cases remain outside the pilot.

## Schedule

Each pilot case receives three counterbalanced A/B/C repetitions:

1. A -> B -> C
2. B -> C -> A
3. C -> A -> B

The frozen budget is 54 trajectories, 216 turns, and at most 432 request attempts.

## Evidence and assessment

The evidence contract retains one metadata-safe row per trajectory.

Operational assessment may only accept the already-planned repetition counts or block the freeze
and require redesign. It does not consume final A/B/C effect sizes.

## Authorization

Variance-pilot execution gets a separate transient, expiring, single-use capability.

Pilot authorization sets:

```text
pilot_execution_authorized=true
final_measured_abc_execution_authorized=false
```

The final measured-execution authority may not be reused.

## Privacy

Public evidence excludes raw prompts, raw user messages, raw retrieved documents, raw model
outputs, raw worker logs, credentials, secrets, and customer data.

## Non-claims

This implementation does not execute Kaggle, does not accept a variance result, does not freeze
final repetition counts, and does not establish a cache-affinity effect.

# ADR: Measured A/B/C variance pilot V1 design

Date: 2026-08-08

## Status

Proposed for merge.

## Context

The measured A/B/C authorization control plane is merged on main
`fed40f516bcaef2306172fd566da3c4451733949` but remains intentionally unissued. Its readiness contract requires an accepted
variance pilot, a frozen repetition-count decision, and a current frozen execution manifest
before one final measured-execution capability can be issued.

The frozen episode constitution contains 18 functional episodes: 12 development and six
held-out. The final runtime subset contains six frozen episode IDs.

A variance pilot must therefore avoid tuning against those final runtime-selected cases.

## Decision

Create a separate current-line variance-pilot gate before final execution readiness.

The pilot case selector is:

`development-minus-final-runtime-selection-v1`

It uses every frozen development episode that is not in the final runtime-v1 selection and
fails closed unless that produces exactly six pilot cases.

Held-out episodes and the six final runtime-selected episodes are prohibited from pilot
selection.

## Pilot schedule

For each of six pilot cases, run three counterbalanced repetitions:

1. A -> B -> C
2. B -> C -> A
3. C -> A -> B

This yields:

- 6 cases
- 3 conditions
- 3 pilot repetitions
- 54 trajectories
- 216 turns
- maximum 432 request attempts

No hidden retries and no replacement cases are permitted.

## Purpose of the pilot

The pilot is an operational-variance gate, not a final effect-estimation run.

It records:

- worker asymmetry;
- TTFT variance;
- prefill variance;
- cache consistency;
- session duration;
- interruption rate;
- telemetry completeness;
- realized routes;
- task status separately from comparison status.

## Repetition-count rule

The benchmark already plans three functional repetitions and ten runtime repetitions.

The pilot may only decide:

- `ACCEPT_PLANNED_REPETITION_COUNTS`; or
- `BLOCK_REPETITION_FREEZE_AND_REDESIGN`.

It may not automatically tune counts from observed final effects, and it may not observe final
runtime-selected cases for this decision.

Operational stability thresholds are frozen before pilot execution:

- interruption rate <= 5%;
- numeric telemetry availability >= 95%;
- worker median TTFT ratio <= 1.25;
- worker median prefill-duration ratio <= 1.25.

A failed threshold does not trigger an automatic repetition increase. It blocks the freeze and
requires a separately reviewed redesign.

## Authorization separation

The final 342-trajectory measured-execution authorization may not be reused for the pilot.

The pilot requires its own transient, expiring, single-use execution authorization with
terminal consumption or abandonment.

## Runtime

The pilot targets the accepted current local-vLLM line:

- Kaggle T4 x2;
- internet disabled;
- Qwen/Qwen2.5-0.5B-Instruct;
- revision `7ae557604adf67be50417f59c2c2f167def9a775`;
- worker 1: GPU 0 / port 8001;
- worker 2: GPU 1 / port 8002.

## Privacy

Public pilot evidence excludes raw prompts, raw user messages, raw retrieved documents, raw
model outputs, credentials, secrets, customer data, and unbounded worker logs.

Every attempt remains represented in machine-readable evidence.

## Consequences

After this design merges, the next slice implements:

1. typed pilot manifest;
2. deterministic pilot schedule;
3. pilot runtime/evidence harness;
4. separate single-use pilot authorization;
5. typed acceptance;
6. repetition-count freeze artifact.

Final measured A/B/C remains unauthorized.

## Non-claims

This ADR does not authorize Kaggle execution, does not freeze final repetitions, does not
produce final A/B/C effects, and does not establish production readiness.

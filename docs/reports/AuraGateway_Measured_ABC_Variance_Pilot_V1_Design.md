# AuraGateway Measured A/B/C Variance Pilot V1 — Design

## Decision

`APPROVED_FOR_VARIANCE_PILOT_IMPLEMENTATION`

Source main: `fed40f516bcaef2306172fd566da3c4451733949`

## Why this gate exists

Final measured A/B/C execution is still correctly blocked. The merged authorization issuer
requires a readiness record, and that readiness record requires an accepted variance pilot and
repetition-count freeze before final manifest freeze.

## Leakage boundary

The pilot does not use:

- held-out episodes;
- the six final runtime-selected episodes.

Instead it deterministically selects the frozen development episodes that are outside the
runtime-v1 final subset.

The implementation must fail closed unless exactly six cases satisfy that rule.

## Pilot budget

```text
cases=6
conditions=3
pilot_repetitions_per_case=3
trajectories=54
turns=216
maximum_request_attempts=432
hidden_retries=0
replacement_cases=false
```

Counterbalance:

```text
R1=A,B,C
R2=B,C,A
R3=C,A,B
```

## What the pilot may decide

Only whether the already-planned final repetition counts are operationally supportable:

```text
functional_repetitions=3
runtime_repetitions=10
```

Allowed outcomes:

```text
ACCEPT_PLANNED_REPETITION_COUNTS
BLOCK_REPETITION_FREEZE_AND_REDESIGN
```

No post-final-result tuning and no effect-size-driven repetition optimization are permitted.

## Predeclared operational gates

```text
maximum_interruption_rate=0.05
minimum_numeric_telemetry_fraction=0.95
maximum_worker_median_ttft_ratio=1.25
maximum_worker_median_prefill_duration_ratio=1.25
```

## Authorization

The pilot needs a separate single-use execution authority.

The final measured A/B/C authorization remains:

```text
authorization_issued=false
runtime_execution_authorized=false
measured_abc_execution_authorized=false
```

## Next gate

`implement_and_merge_measured_abc_variance_pilot_v1`

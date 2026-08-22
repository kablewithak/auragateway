# AuraGateway C4 Mechanism-Admission Assessment V1

## Status

`STATIC_ASSESSMENT_PRODUCER_READY`

This tranche introduces a versioned C4 mechanism-admission contract and a
deterministic static assessor.

## Problem

The canonical C4 semantic canary is `NOT_QUALIFIED`, but the frozen P5/P6
mechanism designs do not use model semantic equality as cache or route proof.

The current runtime implementation coupled those concerns.

## Architecture

```text
governed C4 disposition
        +
frozen exact-runtime P5/P6 design
        ↓
Qualification Contract V2
        ↓
MechanismObservation
        ↓
MechanismDecision
        ↓
AssessmentRecord
```

Semantic evidence is projected separately:

```text
SemanticObservation
state = NOT_QUALIFIED
```

The mechanism classifier has no semantic exact-object or valid-JSON fields.

## Mechanism-blocking requirements

The assessor checks:

1. valid governed execution;
2. exact request accounting and zero hidden retries;
3. normal HTTP/terminal request completion;
4. attributable worker identity and zero-cache starting state;
5. 899/880 token geometry;
6. exact bound runtime/request/prefix/evidence identities;
7. output provenance;
8. teardown and cleanup.

It does not require:

- exact expected semantic object;
- valid JSON as cache/route proof;
- positive cache reuse before P5;
- P6 worker-isolation movement before P6.

## Expected current assessment

The producer derives the result from the exact repository evidence at runtime.
No result is accepted merely because this report predicts it.

The focused regression test requires the current immutable semantic state to
remain `NOT_QUALIFIED` even if the mechanism state is `QUALIFIED`.

## Safety

```text
model_requests_performed=0
gpu_execution_performed=false
kaggle_execution_performed=false
new_execution_authorized=false
```

## Downstream seam

A qualified mechanism-admission result permits only design of the successor
P5/P6 mechanism runtime.

It does not authorize that runtime.

The future variance/final launcher must separately prove that benchmark
`cache_namespace_id` maps to a physical cache-isolation mechanism, preferably
vLLM `cache_salt` unless another mechanism is proven.

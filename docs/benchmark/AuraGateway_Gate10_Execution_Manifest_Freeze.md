# AuraGateway Gate 10: Execution Manifest Freeze

## Status

```text
Document version: 1.0.0
Project allocation: 240 hours
Input: Gate 9 deterministic A/B/C preflight
Provider: Groq
Model: openai/gpt-oss-20b
Measured execution permitted by this slice: No
```

## Purpose

This boundary converts the Gate 9 draft into a frozen execution manifest only after all
pre-execution evidence is present and verified.

It resolves the five Gate 9 blockers without starting the functional benchmark or runtime
microbenchmark.

## Freeze sequence

```text
validate static freeze inputs
    ↓
commit implementation and input assets
    ↓
run two-call bounded Groq readiness probe
    ↓
retain protected probe report under .local
    ↓
write metadata-only public readiness record
    ↓
verify 342-run cross-condition isolation
    ↓
calculate conservative cost upper bound
    ↓
record operator-approved cost ceiling
    ↓
freeze and self-hash execution manifest
    ↓
write Gate 10 report and artifact manifest
```

## Provider pricing boundary

The versioned schedule pins Groq on-demand pricing for `openai/gpt-oss-20b` as checked on
2026-07-13:

```text
uncached input: USD 0.075 per million tokens
cached input:   USD 0.0375 per million tokens
output:         USD 0.30 per million tokens
```

The conservative planning estimate uses uncached input pricing for every possible attempt.
Cached pricing is retained for later measured reporting but does not reduce the approved
pre-execution budget requirement.

Cost estimates are planning evidence, not invoices.

## Token and request ceilings

```text
planned trajectories: 342
planned turns: 1,368
maximum request attempts: 2,736
maximum input tokens per attempt: 3,000
maximum output tokens per attempt: 256
conservative estimated upper bound: USD 0.83
recommended operator ceiling: USD 5.00
```

The USD 5.00 ceiling is not silently assumed. It becomes approved only when the operator runs
the freeze command with `--approved-cost-budget-usd 5.00`.

## Provider probe

The provider probe delegates to the already validated calibration runner:

```text
python -m auragateway.providers.calibration_runner groq-smoke
```

Controls:

- exactly one or two calls;
- selected model and adapter only;
- environment-loaded credential;
- no credential value persisted;
- no raw prompt persisted;
- no raw provider payload persisted;
- protected report written under `.local/provider-calibration`;
- public evidence stores only status, counts, path, timestamp, and SHA-256.

A failed or missing probe blocks manifest freeze.

## Negative controls and faults

The freeze binds a predeclared negative-control manifest and fault-injection fixture set.
They cover:

- static-prefix mutation;
- volatile-content leakage;
- cross-condition namespace reuse;
- unavailable or malformed telemetry;
- ambiguous-response retry risk;
- route thrash;
- quality regression;
- private-artifact leakage;
- omitted scheduled runs;
- configuration-fingerprint drift;
- provider timeout and rate limiting;
- budget exhaustion;
- repeated recovery actions.

These assets describe required harness behavior. They do not execute provider faults in this
slice.

## Privacy boundary

Public freeze evidence excludes:

- raw prompts;
- raw user messages;
- raw retrieved document text;
- raw model output;
- raw provider payloads;
- credentials and secrets;
- protected review exports;
- hidden reasoning.

The live provider report remains protected beneath `.local`. The repository stores a
metadata-only readiness record and the protected report SHA-256.

## Two-commit freeze procedure

The implementation commit must exist before the execution manifest can pin its Git SHA.
Therefore the PR intentionally uses two commits:

1. implementation, tests, pricing, negative controls, fault fixtures, and privacy evidence;
2. generated provider-readiness, isolation, cost, frozen manifest, report, and Gate 10 manifest.

The frozen manifest records the first commit as the benchmark implementation version. The
second commit appends the freeze evidence without changing the pinned implementation.

## Commands

```text
validate
probe-provider
freeze
verify
```

No command in this module executes the 342 planned benchmark trajectories.

## Gate 10 decision

Gate 10 passes only when:

- Gate 9 evidence reproduces;
- pricing validates;
- negative controls validate;
- fault fixtures validate;
- privacy verification passes;
- all 342 planned runs have unique run IDs, derived trace IDs, and cache namespaces;
- all 114 comparison pairs contain A, B, and C exactly once;
- the bounded provider probe passes;
- the approved cost ceiling covers the conservative estimate;
- the execution manifest is frozen;
- the execution manifest self-hash reproduces;
- execution remains disabled pending the reviewed runner slice.

## Claim boundary

This slice proves a reproducible, hash-bound execution-manifest freeze with resolved pricing,
provider-readiness, budget, privacy, fault, negative-control, and cross-condition-isolation
evidence.

It does not prove successful functional execution, successful runtime execution, provider cache
reuse, latency reduction, cost reduction, quality non-inferiority on measured trajectories,
production safety, or production readiness.

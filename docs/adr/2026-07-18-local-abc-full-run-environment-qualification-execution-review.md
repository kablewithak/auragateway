# ADR: Bound the full-run environment-qualification execution package

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-full-run-environment-qualification-execution-review-v1`
- Source main merge: `3b64beb53b3c5f73d4cc49e8f8fe83d9b96d71f8`
- Review fingerprint: `e007e7aaa00e23a51d6cd43ddba71d8ea1daf9a5af5d483f6a4c89397023f579`

## Context

PR #102 merged deterministic static qualification assets for the clean 342-trajectory local
A/B/C lineage. Those assets intentionally do not start Kaggle, enable GPUs, start workers,
invoke a model, or produce runtime evidence.

The next boundary must define a reproducible offline execution package without silently
turning package implementation into environment qualification or measured benchmark
execution.

## Decision

Approve implementation of a bounded qualification-execution package.

The implementation may create typed contracts, a local runner, a Kaggle notebook, a static
execution request, tests, and a runbook. It may not run the notebook, start Kaggle, enable a
GPU, start workers, invoke a model, or generate runtime evidence.

Actual execution requires a later explicit authorization review.

## Probe budget

The eventual qualification execution is limited to one Kaggle session, two local workers,
and at most eight model requests. Six fixed synthetic probe identities cover cold, warm, and
post-reset baselines across both workers.

No benchmark trajectory or benchmark episode payload may be executed during environment
qualification.

## Offline boundary

The eventual execution must remain offline and zero-spend. Model artifacts and the exact vLLM
wheel must be present through approved local dataset inputs. Network package installation,
credentials, hosted-provider calls, customer data, and raw prompt logging are prohibited.

## Evidence boundary

All eight runtime evidence artifacts must come from one fresh runtime session. Partial bundles
cannot qualify the environment. Missing cache metrics remain `UNAVAILABLE_NOT_ZERO`; zero
filling and latency-only cache inference are prohibited.

## Consequences

The next implementation slice can package a reproducible qualification harness without
creating operational authority. A further authorization review remains mandatory before any
Kaggle or GPU activity.

## Non-claims

This decision does not claim current Kaggle availability, runtime compatibility, worker
health, cache observability, reset correctness, environment qualification, comparison
eligibility, measured-execution readiness, or production readiness.

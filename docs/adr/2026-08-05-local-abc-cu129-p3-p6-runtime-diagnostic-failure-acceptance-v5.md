# ADR: Accept P3-P6 Runtime Diagnostic V5 as a Governed Failure

**Date:** 2026-08-05
**Status:** Accepted for repository implementation

## Context

Kaggle saved version `340227787` executed the governed P3-P6 Runtime
Diagnostic V5 under a fresh single-use authorization. The authorization was
consumed with outcome `FAILED`.

The runtime passed source identity, offline installation, process-tree import
closure, model loading, explicit `TRITON_ATTN` realization, worker readiness,
teardown, and scratch cleanup. P3 passed. P4 made one successful HTTP
chat-completion request and failed when the returned non-empty content could
not be parsed as JSON.

P5 and P6 were not reached. No hidden retry, external network request,
customer data, credential, benchmark trajectory, or external spend occurred.

A separate CPU-only inspection, saved version `340232886`, verified the
governed model snapshot, chat template, wheelhouse controls, and model
generation defaults without installing packages, loading a model, starting a
worker, or making a request.

## Decision

Accept saved version `340227787` as a
`VALID_GOVERNED_DIAGNOSTIC_FAILURE`.

Classify the first valid divergence as:

`P4_MODEL_RESPONSE_NOT_VALID_JSON`

Classify the primary harness weakness as:

`P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS`

The strongest causal classification is:

`V5_PROMPT_REGRESSION_WITH_UNCONSTRAINED_GENERATION`

This is a high-confidence causal classification, not counterfactual proof. The
raw model output was intentionally not retained.

Preserve the complete authorization lifecycle, terminal log, runtime evidence
archive, extracted runtime reports, Layer 1 inspection evidence, Layer 2 causal
analysis, validation receipts, limitations, and non-claims.

## Rejected alternatives

- Do not replay V5 unchanged.
- Do not rebuild or upgrade the wheelhouse without new evidence.
- Do not replace the model to hide the boundary defect.
- Do not add retries or strip Markdown as the primary fix.
- Do not claim that top-k filtering caused the failure under temperature-zero
  greedy sampling.
- Do not claim model or wheelhouse corruption.

## Consequences

P3 startup and explicit backend realization are accepted for this saved
version.

P4 exact structured-output reliability is not accepted. P5 and P6 remain
unqualified. Measured A/B/C remains unauthorized.

The next gate is a separate `P4_OUTPUT_CONTRACT_DIAGNOSTIC_V1` that isolates
prompt wording, repetition-penalty inheritance, and JSON-schema enforcement
while retaining metadata-safe failure diagnostics and excluding raw output.

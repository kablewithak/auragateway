# AuraGateway P4 Output-Contract Diagnostic V1

## Purpose

Isolate the P4 output-contract failure observed in saved version `340227787` without changing
the governed model, wheelhouse, T4 runtime, or TRITON backend.

## Matrix

- A: V4 prompt, repetition penalty 1.1, unconstrained.
- B: V5 prompt, repetition penalty 1.1, unconstrained.
- C: V4 prompt, repetition penalty 1.0, unconstrained.
- D: V5 prompt, repetition penalty 1.0, unconstrained.
- E: V4 prompt, repetition penalty 1.0, JSON schema.
- F: V5 prompt, repetition penalty 1.0, JSON schema.

Each case runs three times in a balanced 18-request order. Selection requires 3/3 exact-object
responses, one response hash, and zero request errors. The least constraining eligible case wins.

## Evidence boundary

Raw prompts and model outputs are not retained. The diagnostic stores only hashes, lengths,
parsing metadata, token counts, finish reasons, aggregate metrics, teardown, and cleanup proof.

## Current status

Production-shaped, repository implementation only. Runtime execution, measured A/B/C,
deployment, and production readiness are not authorized or claimed.


## Evidence-contract remediation

The declared runtime outputs now include `model_snapshot_report_v1.json` and
`wheelhouse_report_v1.json`. A deterministic `failure_report_v1.json` is emitted on every terminal
path, using `NOT_APPLICABLE` for successful runs. This closes the pre-authorization discrepancy
between the runtime writer and implementation record.

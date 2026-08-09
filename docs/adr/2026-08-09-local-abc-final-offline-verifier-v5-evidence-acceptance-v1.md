# ADR: Accept Final Offline Verifier V5 capability evidence

Date: 2026-08-09

## Decision

Accept saved Kaggle version `341257985` as governed evidence that the frozen current runtime passes the exact-runtime offline capability boundary on T4 x2 with Internet disabled.

The acceptance promotes only `exact_runtime_offline_verified=true`. It does not inherit the historical P5/P6 pass from the earlier runtime line.

## Evidence boundary

The acceptance binds the executed notebook, terminal log, evidence ZIP, the four ZIP members, the single-use authorization receipt, and its PASSED consumption receipt by SHA-256. The ZIP member set is exact and archive traversal/symlink/duplicate-name cases fail closed.

## Semantic gate

All 25 required V5 roles must be `PASSED`; `failed_required_roles` must be empty. Offline installation must have completed with dependency resolution disabled. Model loads, worker starts, model requests, benchmark trajectories, credentials, customer data, network requirement, and external spend remain zero/false.

The V5 semantic/evidence separation must remain intact: no semantic decision reads persisted excerpts, no lossy transformation or truncation occurs before the semantic decision, raw streams are not persisted, and evidence projection remains terminal.

## Claim transition

After deterministic repository validation:

- `exact_runtime_offline_verified=true`
- `p5_p6_exact_runtime_requalified=false`
- `runtime_execution_authorized=false`
- `pilot_execution_authorized=false`
- `final_measured_abc_execution_authorized=false`

The next gate is `design_exact_runtime_p5_p6_requalification_v1`.

## Non-claims

This acceptance does not establish model/worker/P5/P6 behavior on the newly accepted runtime, measured A/B/C results, deployment readiness, production readiness, or customer-data readiness.

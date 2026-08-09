# ADR: Final Offline Verifier V5 Semantic Boundary Design V1

Status: Proposed for repository acceptance

## Context

Final Offline Verifier V4 failed because evidence representation was reused as
semantic input. The accepted reconciliation requires zero semantic decisions
from `stdout_excerpt` or `stderr_excerpt`, zero lossy transformations before a
decision, raw canonical path decisions, terminal evidence projection, and
metamorphic/negative provenance regressions.

## Decision

Adopt one directional runtime dataflow:

`RawProbeExecution -> TypedSemanticObservation -> ProbeDecision -> EvidenceProjection`

`RawProbeExecution` is ephemeral and is not a Pydantic persistence model.

Role parsers consume raw stdout/stderr and produce typed Pydantic observations.
Role validators consume only typed observations. They do not consume
`ProbeEvidenceRecord`, `stdout_excerpt`, `stderr_excerpt`, `EvidencePolicy`, or
evidence sanitization helpers.

`ProbeOutcome` carries the typed observation for downstream semantic use while
also carrying a separately projected public evidence record. Downstream roles
must consume the typed observation, never parse prior public evidence.

Evidence redaction and truncation occur only after `ProbeDecision` exists.

## Native provenance

Native origin classification uses canonical filesystem paths and the taxonomy:

- `TARGET_OWNED`
- `PERMITTED_HOST_PLATFORM`
- `PROHIBITED_AMBIENT`
- `UNKNOWN`

`UNKNOWN` fails closed when the path is part of a governed native-origin set.
Symlink escape is evaluated using resolved filesystem truth.

## Alternatives rejected

1. Patch only `/kaggle/working` comparison.
   Rejected because truncation and other path-bearing probes remain unsafe.
2. Persist both raw and sanitized stdout in one record.
   Rejected because this keeps the semantic/evidence coupling easy to recreate
   and increases raw-data retention.
3. Make every child subprocess emit only PASS/FAIL booleans.
   Rejected because native provenance and diagnostics require typed semantic
   observations, not only a terminal boolean.

## Scope

This tranche defines and locally validates the semantic boundary. It does not
implement the executable Kaggle V5 notebook and does not authorize execution.

## Acceptance

The design is acceptable only when the synthetic regression suite proves
sanitizer/excerpt metamorphic invariance and native-origin fail-closed cases.

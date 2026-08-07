# ADR: P4 Output-Contract Diagnostic Execution Authorization V3

## Status

Accepted for repository implementation. This ADR does not issue live runtime authority.

## Context

P4 Output-Contract Diagnostic V1 ended as an accepted diagnostic failure at runtime import
closure. Authorization V2 was consumed by Kaggle saved version `340622392` and is non-reusable.
A subsequent differential inspection established `NATIVE_LIBRARY_SEARCH_PATH_SUPPORTED`, and P4
Diagnostic V2 was merged in PR #197 at
`d61a146a2503a5e6bfd3fadbf1dad65dcad402ac` with feature commit
`99bf5a4afff8ee1ee8ddecc1aff689173cb38bab`.

The merged V2 implementation preserves the six A-F cases and exact eighteen-request order while
adding one shared native-runtime environment, target NVIDIA library precedence, CUDA-stub
exclusion, hash-locked offline installation, fail-fast worker-exit detection, bounded stream
capture, request-log suppression, native-origin closure, and stronger teardown evidence.

V2 remains `IMPLEMENTED_NOT_EXECUTED`. Its notebook, runtime script, wrapper, request, model
snapshot, wheelhouse, evidence contract, and prior authorization lineage are immutable inputs to
this decision.

## Decision

Implement a separate V3 transient, single-use execution-authorization issuer.

The issuer must:

- bind the exact P4 V2 feature and merge commits without rewriting V2 source-main metadata;
- bind all merged V2 artifacts by path, SHA-256, and size;
- bind the V1 abandonment, V2 authorization, and V2 consumption receipts;
- bind the exact notebook, runtime script, wrapper, request order, backend, model snapshot,
  wheelhouse controls, native-runtime controls, and seventeen-artifact output contract;
- require clean synchronized `main` and the merged V2 commit as an ancestor;
- require a fresh Kaggle T4 x2 capability observation with Internet disabled;
- expose only GPU 0 to one worker and prohibit a model worker on GPU 1;
- authorize one saved version, one install, one import probe, one model load, one worker start,
  and exactly eighteen model requests with no hidden retries or external network requests;
- create authorization and consumption artifacts without overwriting;
- keep lifecycle artifacts untracked;
- consume authority after passed, failed, interrupted, timed-out, or platform-terminated attempts;
- prohibit unchanged replay after consumption;
- exclude measured A/B/C execution.

## Consequences

Repository implementation and review cannot execute Kaggle or create live authority. After merge,
a separate immediate-readiness review and explicit operator confirmation are required before
issuance. A successful import closure is not proof of worker readiness, Triton compilation,
JSON-schema compatibility, output-contract success, deployment readiness, or production readiness.

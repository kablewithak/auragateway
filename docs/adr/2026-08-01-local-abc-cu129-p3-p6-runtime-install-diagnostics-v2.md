# ADR: CUDA 12.9 P3-P6 Runtime Install Diagnostics V2

## Status

Accepted for repository implementation. Runtime execution is not authorized.

## Context

Kaggle saved version `339375227` consumed the single-use V1 authorization and failed before P3 with `P3_P6_RUNTIME_INSTALL_FAILED`. PR #175 preserved the failure and established that the boundary was offline target-runtime installation while the exact pip cause remained unresolved.

Inspection found an additional deterministic V1 implementation defect: pip `--find-links` targeted the wheelhouse root even though the governed 176-wheel closure is under `wheelhouse/wheels`. This defect can prevent wheel discovery, but the missing V1 pip output means it is not promoted to the confirmed runtime root cause.

V1 also discarded the pip return code and bounded stdout/stderr, copied the model before installation, mixed heavyweight scratch data with Kaggle outputs, and could not emit a complete failure bundle before P3.

## Decision

Implement P3-P6 Runtime Diagnostic V2 as a new immutable lineage.

V2 will:

1. target `wheelhouse/wheels` explicitly;
2. install before copying the model into writable storage;
3. retain return code, timeout state, duration, sanitized bounded stdout/stderr tails, failure signals, disk snapshots, and target-runtime size;
4. emit terminal `FAILED` or `NOT_RUN` reports for every P3-P6 probe;
5. separate `/kaggle/working` scratch from reviewed evidence;
6. remove scratch before evidence bundling and report cleanup status;
7. bundle only the reviewed evidence allowlist with a 2 MiB limit;
8. preserve the one-install, no-hidden-retry, no-network, synthetic-only action budget; and
9. require a separate merged V2 execution authorization.

## Alternatives rejected

- **Unchanged replay:** prohibited by the consumed V1 authorization and would repeat an unobservable failure.
- **Modify the wheelhouse immediately:** rejected because its exact closure and hashes passed validation; V2 first corrects the consumer path and retains evidence.
- **Patch V1 in place:** rejected because V1 is the accepted failed lineage.
- **Include raw scratch and worker logs in the ZIP:** rejected due size, privacy, and evidence-boundary risk.

## Consequences

The next runtime attempt can either proceed into P3-P6 or produce a small, root-cause-oriented installation evidence bundle. A separate post-merge authorization remains mandatory. Deployment and production readiness are not claimed.

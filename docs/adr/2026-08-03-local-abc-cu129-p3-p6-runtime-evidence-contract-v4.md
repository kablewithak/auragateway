# ADR: Harden P3-P6 Runtime Evidence Contract V4

## Status

Accepted for repository implementation.

## Context

Kaggle saved version `339943910` completed offline runtime installation,
process-tree import closure, worker readiness and served-model inventory. vLLM
also emitted the authoritative startup line:

```text
Using AttentionBackendEnum.TRITON_ATTN backend.
```

V3 nevertheless failed P3 because its classifier searched combined stdout and
stderr for two unrelated substrings. The lifecycle correctly remains `FAILED`
and the backend failure is quarantined as an invalid diagnostic.

V3 also serialized failure diagnostics before worker termination and capture
thread finalization. Its worker identity and teardown evidence were not strong
enough to support later P5 and P6 claims, and the executed saved-version source
bytes were not independently bound.

## Decision

Implement V4 as a new generated lineage. Preserve the V3 runtime, action-budget,
privacy, offline-install and process-tree import-closure controls.

V4 must:

- accept only the exact authoritative backend marker on one normalized line;
- reject CLI echo, source-literal, split-stream and ambiguous marker evidence;
- retain matched stream, line number, line length and line SHA-256;
- finalize capture threads before serializing terminal failure diagnostics;
- record worker generation, PID, parent PID and process start identity;
- record GPU UUID, PCI bus ID, index, name and compute capability;
- prove teardown through process-tree absence, GPU-process absence, closed port,
  finalized capture and bounded GPU-memory return observation;
- execute a hash-verified runtime script from one generated notebook wrapper;
- emit dedicated runtime-source and worker-teardown reports.

## Consequences

V4 remains `IMPLEMENTED_NOT_EXECUTED`. It does not issue authorization and does
not replay V3. A separate post-merge authorization must bind the final V4
notebook, runtime-script hash, implementation record and synchronized main.

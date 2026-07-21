# ADR: Rematerialize the current CUDA 12.9 qualification harness

- **Status:** Accepted for implementation
- **Date:** 2026-07-21
- **Repository base:** `16decd4e0d91c4baa18129b0d7afc69bb2630aa1`
- **Decision:** `CURRENT_HARNESS_REMATERIALIZATION_REQUIRED`
- **Failure class:** `FROZEN_HARNESS_CANNOT_REALIZE_CURRENT_CU129_RUNTIME`

## Context

The governed Kaggle launcher still copies and imports the immutable harness produced from:

```text
be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50
```

That historical harness was correctly validated for the authorization schema available at the time. It contains the pre-CUDA-12.9 runtime boundary:

```text
role=vllm_wheel
artifact_format=python_wheel
runtime_adapter_sha256=78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8
```

The current repository requires:

```text
role=vllm_runtime
artifact_format=python_wheelhouse_directory
package_count=176
runtime_adapter_sha256=aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba
```

The current adapter also imports the dedicated CUDA 12.9 runtime module. That module and its current contracts are not part of the historical execution boundary.

## Alternatives considered

### Reuse the frozen harness

Rejected. Binding the current adapter causes the reviewed notebook to reject the adapter bytes in the mounted harness. Binding the historical adapter keeps execution on the superseded single-wheel path and cannot consume the current wheelhouse manifest.

### Patch the launcher to inject individual current modules

Rejected. This would create a mixed source tree with hidden import precedence and brittle transitive coupling. It would also make source authority difficult to inspect and reproduce.

### Introduce authorization schema v2 immediately

Rejected for now. The repository already separates authorization-contract authority from harness-source authority. The current evidence does not show a schema requirement that cannot be represented by the existing authorization plus current control and dataset manifests.

### Rematerialize one complete current harness

Accepted. A complete immutable source tree is the smallest maintainable boundary that gives the launcher one inspectable source authority.

## Decision

Implement a new deterministic current-harness materializer after this review merges.

The implementation must:

1. bind the exact post-review merge commit as its source authority;
2. produce one immutable current source tree;
3. include current execution, contracts, runtime adapter, CUDA 12.9 runtime, worker plan, request, launcher support, and project metadata;
4. preserve archive traversal, encryption, symlink, non-regular-member, nested-archive, file-count, byte-budget, required-path, and directory-identity controls;
5. emit a canonical materialization receipt;
6. run a metadata-only Kaggle input-realization inspection before changing active manifest identities;
7. update launcher and manifest bindings only from consumed immutable evidence;
8. correct the stale single-wheel launcher runbook instruction;
9. keep authorization issuance and model execution blocked.

## Consequences

The historical `be1bfadd` harness and its materializer remain immutable evidence. They are not rewritten or rerun.

A new source archive and materializer notebook cannot be finalized until this review merges, because the new harness must bind a stable merged source commit rather than an unmerged branch state.

## Validation requirements

The implementation must reject:

- the historical harness as a current CUDA 12.9 source;
- the `vllm_wheel` role and `python_wheel` format;
- archives containing traversal, absolute paths, encryption, symlinks, non-regular files, or nested archives;
- ambiguous archive-plus-expanded-tree input;
- file-count, byte-count, required-path, or directory-identity drift;
- stale generated launcher or reviewed notebook artifacts;
- stale single-wheel runbook instructions;
- any authorization, worker, model, or request activity during materialization proof.

## Non-claims

This decision does not prove that the new harness has been materialized, that Kaggle inputs are correctly realized, that the model loads, that workers start, that cache probes pass, or that measured A/B/C is authorized.

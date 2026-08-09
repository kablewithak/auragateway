# ADR: Final Offline Verifier V5 Semantic-Boundary Implementation

Status: Proposed for repository acceptance

## Context

Final Offline Verifier V4 reached exact offline installation and package
inventory, then produced a deterministic false negative because sanitized and
truncated public evidence was reused as semantic input. The accepted V4
reconciliation classified that result as a diagnostic harness defect rather
than runtime incompatibility.

PR #225 accepted the successor invariant:

`RawProbeExecution -> TypedSemanticObservation -> ProbeDecision -> EvidenceProjection`

The implementation now has to preserve the V4 runtime-capability scope while
making that dataflow structural rather than advisory.

## Decision

Implement Final Offline Verifier V5 as an additive notebook and repository
validator. V4 remains immutable diagnostic evidence.

V5 uses transient `RawProbeExecution` values. Parsers consume raw subprocess
stdout and produce typed semantic observations. Validators consume typed
observations. `ProbeDecision` exists before public evidence is projected.

`ProbeOutcome` carries semantic observations separately from public
`ProbeEvidenceRecord` values. Downstream roles consume typed observations.
They never reconstruct runtime truth from `stdout_excerpt` or
`stderr_excerpt`.

Evidence sanitization and truncation are terminal representation operations.

## Runtime scope

V5 preserves the bounded V4 capability surface:

1. exact wheelhouse and manifest identity;
2. base-runtime and T4 x2 checks;
3. isolated target creation;
4. hash-locked offline install with no dependency resolution;
5. exact target distribution inventory and dependency check;
6. controlled Python startup;
7. required `_C_stable_libtorch` inventory;
8. canonical loader environment;
9. Python, Torch, Transformers, Triton, and vLLM identity;
10. static linker provenance;
11. required native extension import;
12. dynamic native provenance;
13. vLLM CUDA-platform kernel import;
14. unchanged base distribution snapshot.

No model is loaded and no worker, inference request, P5/P6 trajectory, pilot,
or measured A/B/C execution is permitted.

## Native provenance

V5 validates native paths from raw canonical filesystem truth. Governed native
origins are classified as `TARGET_OWNED`, `PERMITTED_HOST_PLATFORM`,
`PROHIBITED_AMBIENT`, or `UNKNOWN`.

Unknown governed origins fail closed. CUDA stubs/compat paths and unapproved
ambient Python-package native libraries fail closed. Generic operating-system
libraries are outside the governed set unless their basename or location makes
them relevant to the runtime provenance contract.

Static linker validation requires target Torch and NVIDIA runtime libraries.
Dynamic provenance additionally requires the real NVIDIA driver.

## Evidence and privacy

Raw stdout/stderr are transient process memory and are not persisted. Public
evidence contains bounded, sanitized excerpts only. Error decisions use stable
failure codes and safe details; evidence projection may redact runtime paths
without changing semantic truth.

## Acceptance

Repository acceptance requires:

- semantic decisions reading stdout evidence: 0;
- semantic decisions reading stderr evidence: 0;
- lossy transforms before semantic decision: 0;
- truncation before semantic decision: 0;
- terminal evidence projection;
- sanitizer metamorphic invariance;
- excerpt-length metamorphic invariance;
- symlink escape negative test;
- ambient Python native negative test;
- CUDA stub negative test;
- real-driver positive test;
- unknown governed origin fail-closed test;
- exact V5 notebook identity and unexecuted state;
- repository-wide regression gates.

## Non-claims

Repository acceptance does not establish exact-runtime compatibility. V5 is
`IMPLEMENTED_NOT_EXECUTED` until separately authorized and executed.

## Next gate

`implement_single_use_final_offline_verifier_v5_execution_authorization`

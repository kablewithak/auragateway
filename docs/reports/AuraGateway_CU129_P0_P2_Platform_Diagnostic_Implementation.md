# AuraGateway CUDA 12.9 P0-P2 Platform Diagnostic Implementation

## Status

Implemented locally and statically validated. Not executed.

## Source authority

```text
f4f08eda4b4d4747514b4646fe53664d8a78ca6d
```

This is the merge commit for PR #156, which approved the Option C two-stage
runtime diagnostic.

## Implemented boundary

This tranche adds:

```text
typed diagnostic request
typed implementation record
deterministic notebook producer
self-contained Kaggle diagnostic program
static notebook validator
focused regression tests
reviewed notebook
execution runbook
implementation report
```

## Probe behavior

### P0

Captures the current Kaggle build identity, dual-T4 topology, driver and CUDA
environment, compiler and linker identities, package origins, and bounded
`libcuda` observations.

### P1

Performs one unmodified linker test using `-lcuda`, identifies the link-time
library selected by GNU `ld`, inspects runtime resolution with `ldd`, and
executes `cuInit(0)`.

### P2

Validates the existing governed CUDA 12.9 wheelhouse, installs it offline into a
working-directory target, and performs one exact Triton vector-add kernel on one
T4.

## Evidence outputs

```text
platform_identity_report.json
cuda_driver_linker_report.json
minimal_triton_kernel_report.json
option_c_platform_diagnostic_summary.json
bundle_manifest.json
human_report.md
```

These are packaged into:

```text
ag-cu129-p0-p2-platform-evidence-v1.zip
```

## Runtime isolation

The notebook:

```text
uses no network
uses no secrets
uses no customer data
loads no model
starts no worker
performs no model request
performs no benchmark trajectory
does not mutate system libraries
does not create libcuda symlinks
does not alter canonical vLLM worker source
```

## Maintainability

The generated notebook is derived from one inspectable Python source constant.
Its exact bytes and SHA-256 are validated against the implementation record.
The notebook contains no outputs or execution counts in the repository.

The historical worker plan is also checked to prove that explicit
`TRITON_ATTN` implementation has not been mixed into this tranche.

## Failure handling

P0-P2 stop at the first failed probe. Later reports are emitted with
`NOT_RUN_DUE_TO_PRIOR_FAILURE` rather than fabricated zero-value success.

The evidence ZIP is created for both pass and fail decisions.

## Commercial translation

This tranche is useful evidence for an **Agent Harness Hardening Sprint** or
**AI System Evaluation Audit** because it demonstrates:

```text
platform identity as a governed input
link-time versus runtime CUDA distinction
minimal falsification before expensive model execution
bounded failure budgets
machine-readable failure transitions
evidence preservation without customer data
```

## Non-claims

This implementation does not establish:

- successful Kaggle execution;
- linker viability;
- Triton viability;
- vLLM worker readiness;
- model inference;
- cache observability;
- measured A/B/C effects;
- deployment;
- production readiness.

## Next gate

```text
review_and_materialize_p0_p2_platform_diagnostic
```

# ADR: Canonical target-first CUDA loader environment for verifier v5

Status: Accepted

Date: 2026-07-20

## Context

Offline verifier v4 successfully validated and installed the exact 176-package CUDA 12.9 closure into
a clean pip-less target environment.

```text
input_validation=PASSED
offline_hash_locked_install_via_base_pip=PASSED
target_distribution_inventory=PASSED
target_dependency_check_via_base_pip=PASSED
gpu_topology=PASSED
base_distribution_metadata_unchanged=true
```

The first runtime divergence occurred while Torch loaded the governed cuSPARSE library:

```text
first_divergence=torch_family_runtime
failure_code=NVJITLINK_12_9_SYMBOL_UNRESOLVED
required_symbol=__nvJitLinkGetErrorLogSize_12_9
```

Verifier v4 evidence identities:

```text
evidence_zip_sha256=9a4bd10a66c440ffb2628f98ce143e38a1b5cdb06a745497b7b386910816e0fe
evidence_manifest_sha256=30d87a0ff29adc7bcca431b03ef047e84acba7a2017e48a84517999415ff20d0
execution_log_sha256=8b9b9894a12dee7f301482f2ec6e3aebd155d453a5e5905ad96c5607e7212f44
```

A bounded dynamic-linker inspection then established:

```text
inspection_status=COMPLETED
root_cause_assignment=LOADER_PRECEDENCE_CONFIRMED
inherited_environment_load_status=FAILED
target_first_environment_load_status=PASSED
```

The inherited Kaggle loader path selected:

```text
/usr/local/cuda/lib64/libnvJitLink.so.12
```

That library did not provide the required CUDA 12.9 symbol. The exact governed
`nvidia-nvjitlink-cu12==12.9.86` library did provide the symbol, and the same cuSPARSE direct load
passed when target NVIDIA library directories preceded inherited loader directories.

Inspection evidence identities:

```text
evidence_zip_sha256=b241f49a4636c6e427299582c130f4742cf925ad5f541a65f852fa424457d2d0
evidence_manifest_sha256=d8bd838ed6cf8f521317f7f0290a0dc0eb111ed41a40515bcd2b6b6f77c99d28
execution_log_sha256=ff3649a280012f33943c177268ebb45e2c2f7f498dcec290266526a9eea1c83b
reasoning_certificate_sha256=cc8cd04dee8017c42afb4a75e1e3103baa1f32ac4ca222687957b5ccecf2f9a7
```

Verifier v4 also exposed inherited Python-process configuration through a failing base
`sitecustomize` import. Prefix isolation alone is therefore insufficient.

## Decision

1. Preserve verifier v4 Version 1 unchanged as valid runtime failure evidence.
2. Preserve dynamic-linker inspection Version 1 unchanged as root-cause evidence.
3. Do not rerun verifier v4 or the inspection.
4. Do not rematerialize the wheelhouse.
5. Do not substitute CUDA, Torch, cuSPARSE, or nvJitLink versions.
6. Introduce verifier v5 with a canonical target-first CUDA loader environment.
7. Remove `PYTHONPATH` and `PYTHONHOME` from governed target subprocesses.
8. Set `PYTHONNOUSERSITE=1`.
9. Prepend all target `nvidia/*/lib` directories to `LD_LIBRARY_PATH`.
10. Retain inherited loader directories only after target directories.
11. Bind the exact target nvJitLink and cuSPARSE SHA-256 identities.
12. Confirm the required CUDA 12.9 symbol before Torch import.
13. Confirm canonical `ldd` resolution selects the target nvJitLink library.
14. Confirm direct cuSPARSE loading under the canonical environment.
15. Run Torch and vLLM probes in fresh subprocesses under the canonical environment.
16. Treat vLLM imports as blocked if Torch fails.
17. Stop before model or tokenizer loading, workers, requests, or qualification.

Active verifier:

```text
repository_notebook=notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v5.ipynb
kaggle_title=auragateway-cu129-offline-verifier-v5
title_character_count=37
notebook_sha256=ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
output_directory=auragateway_vllm_cu129_offline_compatibility_evidence_v5
```

## Canonical process contract

```text
PYTHONPATH=<removed>
PYTHONHOME=<removed>
PYTHONNOUSERSITE=1
LD_LIBRARY_PATH=<target nvidia/*/lib directories>:<inherited directories>
VIRTUAL_ENV=<target-venv>
PATH=<target-venv>/bin:<inherited PATH>
```

Target path ordering is deterministic and duplicate-free. The first occurrence wins.

## Bound library identities

```text
libnvJitLink.so.12_sha256=02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f
libcusparse.so.12_sha256=6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7
required_symbol=__nvJitLinkGetErrorLogSize_12_9
```

## Alternatives rejected

### Rematerialize the wheelhouse

Rejected because the closure validated, installed, matched the exact inventory, and contained the
required symbol.

### Replace CUDA package versions

Rejected because the assigned defect is loader precedence, not a missing governed symbol.

### Modify the Kaggle system CUDA installation

Rejected because the verifier must not mutate the host runtime or require elevated access.

### Install into the Kaggle base environment

Rejected because this weakens isolation and introduces hidden state.

### Use one ad hoc `LD_LIBRARY_PATH` command

Rejected because the policy must be deterministic, inspectable, and applied to every governed runtime
probe.

## Consequences

Verifier v5 can establish whether the exact closure becomes runtime-compatible under a canonical
target-first loader environment. It also proves target process-path isolation, target library
identities, target loader resolution, direct cuSPARSE loading, causal failure blocking, and base
distribution metadata stability.

A successful verifier v5 remains diagnostic evidence only. It does not authorize model loading or
measured A/B/C execution.

## Non-claims

This decision does not establish successful Torch CUDA initialization under verifier v5, successful
vLLM or native-extension import under verifier v5, model loading, tokenizer loading, environment
qualification, measured A/B/C authorization, or production readiness.

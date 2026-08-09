# Runbook: Preflight-v3 final exact-runtime offline verifier V3

## Current state

```text
implementation only
execution authorization=false
exact runtime offline verified=false
P5/P6 exact runtime requalified=false
next expensive execution permitted=false
```

Do not execute this verifier merely because the notebook exists in the
repository. Execution requires a separate authorization record after the
implementation tranche is merged and validated.

## Kaggle configuration for a future authorized run

```text
accelerator=T4 x2
internet=OFF
secrets=NONE
input=exactly one accepted materializer output
```

Expected input directory:

```text
auragateway_preflight_v3_exact_runtime_wheelhouse_v1
```

The verifier creates a fresh target environment under `/kaggle/working`,
installs the exact 196-wheel closure with base pip using `--no-index --no-deps
--require-hashes`, and performs no dependency resolution.

## Required capability sequence

```text
input and artifact closure
→ target creation/install
→ controlled Python startup
→ native inventory
→ canonical loader environment
→ exact runtime identities
→ static native linker provenance
→ vllm._C_stable_libtorch import
→ dynamic native provenance
→ vLLM CUDA platform capability
→ base-environment non-mutation check
```

A failed role blocks dependent downstream roles. Do not manually force later
roles after a failure.

## Controlled process contract

Every post-install Python probe uses:

```text
target-python -S
PYTHONPATH removed
PYTHONHOME removed
LD_PRELOAD removed
PYTHONNOUSERSITE=1
sitecustomize sentinel
usercustomize sentinel
site.main()
external package paths removed from sys.path
```

`LD_LIBRARY_PATH` is constructed target-first from the target NVIDIA wheel
libraries, target Torch libraries, the approved real NVIDIA driver directory,
and then filtered inherited system paths.

## Prohibited mutations

Do not:

- install `wrapt` to silence ambient startup warnings;
- change any resolved package version;
- rematerialize the wheelhouse;
- add CUDA toolkit/stub paths;
- change the required native module back to `vllm._C`;
- load a model;
- start a vLLM worker;
- send a request;
- run P5/P6;
- run the variance pilot;
- run measured A/B/C.

## Evidence retention

After a future authorized execution, preserve the Kaggle saved version and
retain the executed notebook, execution log, and evidence ZIP. Do not rerun a
failed verifier merely to obtain a green artifact. Classify the first divergence
before any remediation.

## Acceptance boundary

A runtime result with all required roles passing is only:

```text
PASSED_PENDING_REPOSITORY_ACCEPTANCE
```

Repository acceptance of the exact saved-version evidence is a later transition.
Only after that acceptance may the project return to exact-runtime P5/P6
requalification.

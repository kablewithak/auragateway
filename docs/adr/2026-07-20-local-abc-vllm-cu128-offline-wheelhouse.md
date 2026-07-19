# ADR: Materialize a complete CUDA 12.8 vLLM wheelhouse for Kaggle T4

- Status: Accepted for materialization
- Date: 2026-07-20
- Scope: AuraGateway local A/B/C environment qualification
- Lifecycle claim: production-shaped design, not yet target-environment qualified

## Context

The governed qualification reached dependency-lock capture after authorization, control-root discovery,
immutable harness resolution, local wheel installation, and two-T4 topology capture. The installed
`vllm 0.25.1+cu129` native extension then failed against Kaggle's `torch 2.10.0+cu128` runtime with
`undefined symbol: torch_from_blob`. The focused diagnostic also proved that the prior input contained
one vLLM wheel rather than a complete dependency closure.

The defect is not resolved by installing the same wheel again. A successful package copy is weaker than
native extension compatibility, and vLLM's compiled extensions must remain aligned with the PyTorch and
CUDA build used at runtime.

## Decision

Materialize one immutable wheelhouse for this target stack:

- Python 3.12
- CUDA wheel variant `cu128`
- vLLM release `0.19.1`
- vLLM distribution `0.19.1+cu128`
- PyTorch `2.10.0+cu128`
- torchaudio `2.10.0+cu128`
- torchvision `0.25.0+cu128`
- Transformers `5.5.3`

vLLM 0.19.1 pins PyTorch 2.10.0 in its build and CUDA requirements, publishes a CUDA 12.8 wheel
variant, supports Python 3.12, and lists T4-class hardware under its compute-capability requirement.
The release also moved to Transformers 5.5.3.

The materializer must not resolve `vllm==0.19.1` from the default package index because the default
artifact may target a different CUDA build. It must query the official GitHub release, select exactly
one `vllm-0.19.1+cu128-...-x86_64.whl` asset, and bind the resolved dependency closure to hashes.

The complete closure is resolved and downloaded once in an Internet-enabled CPU notebook. Verification
then installs only from the saved wheelhouse into a fresh virtual environment with Internet disabled.

## Runtime contract

The materialized output must contain:

```text
auragateway_vllm_cu128_wheelhouse_v1/
├── wheels/
├── requirements.in
├── materialization.lock.txt
├── requirements.lock.txt
├── install_runtime.py
├── runtime_manifest.json
├── sha256_manifest.json
└── materialization_receipt.json
```

`materialization.lock.txt` binds network acquisition URLs and SHA-256 identities. It is used only while
building the wheelhouse.

`requirements.lock.txt` binds exact distribution versions and SHA-256 identities. It is used only for
the offline installation from local wheel files.

The offline verifier must:

1. validate every payload hash before installation;
2. create a fresh virtual environment under `/kaggle/working`;
3. install with `--no-index`, `--find-links`, and `--require-hashes`;
4. require `pip check` success inside the isolated environment;
5. validate Python, PyTorch, CUDA, Transformers, vLLM distribution, vLLM module import, and native
   extension import;
6. prove that exactly two Tesla T4 GPUs are visible;
7. make zero model requests and claim no qualification result.

## Rejected alternatives

### Install `vllm==0.19.1` from the default package index

Rejected. The selected runtime needs the explicit `+cu128` release asset. An unqualified package
requirement can silently select a different CUDA variant.

### Keep vLLM 0.25.1 and replace Kaggle's global PyTorch

Rejected for this phase. That stack requires a newer PyTorch and CUDA family and would create a larger,
higher-risk environment replacement. It is not needed to prove the bounded Qwen2.5-0.5B T4 runtime.

### Continue using Kaggle's global environment

Rejected. The diagnostic proved that installation can succeed while native ABI compatibility fails.
A mutable base image is not a reproducible runtime authority.

### Build vLLM from source in the qualification notebook

Rejected. It expands runtime duration, compiler variability, network requirements, and the failure
surface. Source compilation remains a fallback only if the official CUDA 12.8 wheel fails the focused
offline compatibility verifier.

## Consequences

- The next Kaggle activity is wheelhouse materialization, not a qualification rerun.
- The wheelhouse may be several gigabytes because it includes the PyTorch/CUDA dependency closure.
- The qualification harness, launcher, authorization, and offline dataset manifest remain unchanged
  until the focused verifier passes.
- Passing the verifier proves dependency and binary compatibility only. It does not prove model loading,
  worker health, cache telemetry, reset correctness, measured A/B/C behavior, or production readiness.

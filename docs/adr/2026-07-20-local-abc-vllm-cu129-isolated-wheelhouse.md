# ADR: Materialize the official isolated CUDA 12.9 vLLM runtime for Kaggle T4

- Status: Accepted for materialization
- Date: 2026-07-20
- Scope: AuraGateway local A/B/C environment qualification remediation
- Supersedes: `2026-07-20-local-abc-vllm-cu128-offline-wheelhouse.md`
- Lifecycle claim: production-shaped design, not target-environment qualified

## Context

The governed qualification previously installed one `vllm 0.25.1+cu129` wheel into Kaggle's global
`torch 2.10.0+cu128` environment with `--no-deps`. The native extension failed with
`undefined symbol: torch_from_blob`, proving that installation success did not establish binary
compatibility or dependency closure.

PR #116 selected a complete `vllm 0.19.1+cu128` wheelhouse. The first materializer run then failed
closed because the official vLLM `v0.19.1` release did not publish that explicit cu128 x86_64 asset.
No wheel was downloaded and no output was generated.

Official vLLM 0.19.1 installation guidance states that its prebuilt CUDA binaries are compiled for
CUDA 12.9 by default, should be installed in a fresh environment, and should use the bundled matching
PyTorch dependency closure. Reusing a different existing PyTorch build is explicitly unsafe unless
vLLM is rebuilt from source.

## Decision

Materialize one complete, hash-locked, isolated runtime using the exact official release asset:

```text
vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl
sha256=71a87f46cafab4489c69a5c5c83b870d0235e5694d8222303d460576293dc719
```

Selected closure:

- Python `3.12`
- vLLM release and distribution `0.19.1`
- vLLM binary CUDA family `12.9`
- PyTorch `2.10.0+cu129`
- torchaudio `2.10.0+cu129`
- torchvision `0.25.0+cu129`
- Transformers `5.5.3`
- fresh isolated virtual environment

Kaggle's global `torch 2.10.0+cu128` remains an observed base-image fact, but it is no longer the
runtime authority inside the isolated environment.

The CPU materializer must query the official GitHub release, select the exact filename, verify the
official SHA-256, resolve the complete Python 3.12 dependency closure using the CUDA 12.9 PyTorch
index, and download every wheel with hashes.

The separate T4 verifier must install only from the saved wheelhouse with Internet disabled and prove:

1. payload hash integrity;
2. isolated offline installation;
3. `pip check`;
4. Python 3.12;
5. `torch 2.10.0+cu129` with `torch.version.cuda == 12.9`;
6. exactly two T4 GPUs;
7. Transformers 5.5.3;
8. vLLM 0.19.1 distribution and module import;
9. `vllm._C` native-extension import;
10. zero model requests.

## Rejected alternatives

### Relabel the plain vLLM wheel as cu128

Rejected. The plain release wheel is the default CUDA 12.9 binary. Renaming or semantically treating it
as cu128 would repeat the exact authority mismatch the harness is intended to prevent.

### Install the CUDA 12.9 vLLM wheel over Kaggle's global cu128 Torch

Rejected. The previous diagnostic proved that mixing compiled vLLM extensions with a different Torch
build can install successfully and still fail at native import.

### Build vLLM from source immediately

Deferred. A source build is a valid fallback for a non-default Torch/CUDA stack, but it introduces a
compiler toolchain, longer runtime, larger offline closure, and additional failure modes. The official
complete isolated prebuilt stack is the smaller maintainable next test.

### Advance directly to model loading or qualification

Rejected. Binary compatibility must be proven independently before model, worker, cache, or claim
boundaries are crossed.

## Consequences

- All active materializer, verifier, output, and evidence identities move from `cu128` to `cu129`.
- The failed cu128 materializer remains historical evidence and must not be rerun.
- The next Kaggle gate remains CPU-only materialization with Internet on.
- The T4 verifier remains a separate fresh session with Internet off.
- Passing the verifier proves runtime compatibility only, not model load, worker health, cache behavior,
  measured improvement, or production readiness.

## Materializer attempt 2: PyTorch CDN allowlist mismatch

The isolated CUDA 12.9 materializer resolved the complete dependency graph, then failed closed before
downloading wheels because the PyTorch cu129 index returned an artifact URL hosted at the official
`download-r2.pytorch.org` CDN. The exact-host allowlist included `download.pytorch.org` but omitted the
download CDN used by the resolved wheel URL.

```text
classification=MATERIALIZER_DOWNLOAD_HOST_ALLOWLIST_FAILURE
code=PYTORCH_CDN_HOST_NOT_ALLOWED
observed_host=download-r2.pytorch.org
execution_log_sha256=69c7656374fc5313becb44684f1b11eac950db7c79eed5b62572eaefec3640a3
dependency_resolution_completed=true
wheel_downloads_performed=0
model_requests_performed=0
qualification_claimed=false
```

The remediation adds only the exact official `download-r2.pytorch.org` host. HTTPS-only validation,
credential rejection, fragment rejection, and exact-host matching remain unchanged. Wildcard PyTorch
domains are not permitted. Rejected URL evidence is bounded to a normalized distribution name,
failure code, and hostname.

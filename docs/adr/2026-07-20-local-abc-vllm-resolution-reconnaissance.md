# ADR: Run complete CUDA 12.9 resolution reconnaissance before materialization

- Status: Accepted
- Date: 2026-07-20
- Scope: AuraGateway local A/B/C runtime compatibility remediation
- Lifecycle claim: production-shaped diagnostic design, not target-environment qualified

## Context

Three CPU materializer attempts failed at progressively deeper acquisition boundaries:

```text
attempt=1
code=VLLM_CU128_RELEASE_ASSET_ABSENT
execution_log_sha256=b45bee3fd286f35d367ee25639100eb33b9244251d5a921dedd84c998e785a2d

attempt=2
code=PYTORCH_CDN_HOST_NOT_ALLOWED
execution_log_sha256=69c7656374fc5313becb44684f1b11eac950db7c79eed5b62572eaefec3640a3

attempt=3
code=NVIDIA_PACKAGE_HOST_NOT_ALLOWED
execution_log_sha256=f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4
observed_distribution=nvidia-cublas-cu12
observed_host=pypi.nvidia.com
```

Attempts 2 and 3 completed pip dependency resolution before the first unapproved exact hostname
aborted evaluation. No wheelhouse was produced, no package was installed, and no model request was made.

The one-host-per-run repair loop is safe but operationally inefficient. It fails on the first reviewable
source-policy mismatch instead of preserving the complete resolved closure and collecting all policy
violations.

Historical runtime evidence remains diagnostically admissible even though it is rejected as execution
authority:

```text
observed_vllm=0.25.1+cu129
observed_vllm_wheel_sha256=9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431
observed_torch=2.10.0+cu128
required_torch_from_pip_check=2.11.0
minimum_transformers_from_pip_check=5.5.3
native_import_error=undefined symbol: torch_from_blob
```

Repository inspection also found a separate latent materializer defect:

```text
code=MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT
bound_materializer_sha256=a3e043ba6c2caf982a0ebe14ddd1d102e0b5066a46ff17f6fdbf7e0bf876cf79
```

The active cu129 materializer still checks required wheel filename prefixes containing `cu128`.
Materialization must remain paused until this finding and the complete source-authority policy can be
repaired together.

## Decision

Introduce one resolution-only diagnostic notebook:

```text
repository_notebook=notebooks/auragateway_vllm_cu129_resolution_reconnaissance_v1.ipynb
kaggle_title=auragateway-cu129-resolution-reconnaissance-v1
output_directory=auragateway_vllm_cu129_resolution_reconnaissance_v1
```

The notebook will:

1. bind the exact vLLM 0.19.1 release asset and SHA-256;
2. execute pip with `--dry-run --report`;
3. inspect every resolved install record;
4. inventory every distribution, version, exact hostname, authority candidate, artifact filename, and SHA-256;
5. collect all policy violations instead of aborting on the first unknown host;
6. retain a sanitized resolution report;
7. retain historical runtime context and all three failure identities;
8. emit a deterministic output SHA-256 manifest;
9. write no persistent wheel files;
10. perform no package installation, model loading, model request, authorization, or qualification.

The initial policy distinguishes approved hosts from candidates requiring review:

```text
approved:
- download.pytorch.org -> pytorch
- download-r2.pytorch.org -> pytorch
- files.pythonhosted.org -> pypi
- github.com -> github_release
- objects.githubusercontent.com -> github_release
- release-assets.githubusercontent.com -> github_release

candidate:
- pypi.nvidia.com -> nvidia
```

Candidate classification does not authorize the host. Wildcard domains remain prohibited.

## Why this is not another materializer

The reconnaissance notebook performs resolution and analysis only. It does not run `pip download`, does
not create a wheelhouse, and does not install the runtime.

A successful Kaggle notebook version may therefore still end with:

```text
status=RESOLUTION_RECONNAISSANCE_REVIEW_REQUIRED
```

That is an acceptable diagnostic result when every remaining source-policy violation has been retained.

## Acceptance criteria

The run must:

- generate a pip resolution report;
- evaluate every install record;
- collect all policy violations;
- inventory all observed exact hosts;
- inventory all observed authorities;
- retain the sanitized artifact URLs without credentials, query strings, or fragments;
- emit zero persistent `.whl` files;
- perform zero package installations;
- perform zero model requests;
- make no qualification claim.

## Follow-on gate

After the output is downloaded and repository-bound:

1. review every observed host and package-to-authority mapping;
2. reject or approve each exact source authority;
3. add a full-closure replay fixture;
4. repair all source-policy rules in one change;
5. repair `MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT` in the same change;
6. rerun the materializer once;
7. proceed to the offline T4 verifier only after successful materialization.

## Non-claims

This ADR does not establish:

- that `pypi.nvidia.com` is approved;
- that the resolved closure is complete until the notebook executes;
- that the wheelhouse can be downloaded;
- that the runtime installs offline;
- that `pip check` passes;
- that `vllm` or `vllm._C` imports;
- that model loading, workers, cache behavior, or A/B/C execution are authorized;
- that AuraGateway is production-ready.


## Completed Version 1 result

```text
status=RESOLUTION_RECONNAISSANCE_REVIEW_REQUIRED
resolved_distribution_count=176
host_count=5
policy_violation_count=26
results_zip_sha256=a035b21fe5795816e888886003c3dd6c73dbda162370805be687b28f8cef4399
execution_log_sha256=3455a8e631157a0c4e4c66e3e5e23c0e4cb41236e6b7d1016811b357488a2269
```

All 26 findings were reviewed together and converted into the exact artifact lock:

```text
resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
review_decision=APPROVED_AS_EXACT_LOCKED_CLOSURE
```

The historical notebook must not be rerun. The next gate is the fresh exact-lock materializer.

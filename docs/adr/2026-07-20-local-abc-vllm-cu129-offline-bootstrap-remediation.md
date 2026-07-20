# ADR: Capture CUDA 12.9 offline pip bootstrap before package installation

Status: Accepted

Date: 2026-07-20

## Context

Offline verifier v2 Version 1 validated the complete governed wheelhouse before reaching the
runtime installation boundary.

```text
input_validation=PASSED
package_count=176
manifest_entry_count=182
wheel_entry_count=176
non_wheel_entry_count=6
total_wheel_bytes=5727339111
```

The first and only observed failed probe was:

```text
command_role=offline_isolated_install
failure_class=ISOLATED_ENVIRONMENT_BOOTSTRAP_FAILURE
failure_code=ENSUREPIP_BOOTSTRAP_FAILED
package_installation_started=false
```

The traceback establishes that `venv.EnvBuilder(with_pip=True)` invoked the new interpreter with
`-m ensurepip --upgrade --default-pip` and received exit status 1. The nested `ensurepip` stdout and
stderr were not retained. The evidence therefore localizes the divergence but does not establish its
underlying cause.

Evidence identities:

```text
verifier_v2_evidence_zip_sha256=01019ce577f2bc7bfaaa8810d19161157f1dbc15b3c8817c2ba7836c4b0158d4
verifier_v2_evidence_manifest_sha256=bcda0b716981a31fa205682485598f7b4d0460133f8430fce3c656663421ff42
reasoning_certificate_sha256=b1ffc2009ee100ffb990b88f09e08827e0301cecc233b6259ba0c5177a64b492
```

## Decision

1. Preserve verifier v2 Version 1 unchanged as valid diagnostic failure evidence.
2. Do not rerun verifier v2.
3. Do not rematerialize the 5.7 GB wheelhouse.
4. Introduce verifier v3 with explicit base-interpreter, `venv`, and `ensurepip` probes.
5. Create the virtual environment with `--without-pip`.
6. Run the new interpreter's `ensurepip` as a separately captured subprocess.
7. Start the hash-locked offline installation only after captured pip bootstrap succeeds.
8. Label downstream roles `BLOCKED_BY_UPSTREAM_FAILURE` or `NOT_EXECUTED` rather than treating
   absence as an independently observed failure.
9. Preserve Internet Off, T4 x2, no secrets, zero model requests, and no qualification claim.

Active verifier:

```text
repository_notebook=notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v3.ipynb
kaggle_title=auragateway-cu129-offline-verifier-v3
title_character_count=37
notebook_sha256=d9cd2218fb7fc995ecd205127d979154c9700d26e7432abfefc6a0a7af1af36f
output_directory=auragateway_vllm_cu129_offline_compatibility_evidence_v3
```

## Alternatives rejected

### Rerun verifier v2 unchanged

Rejected because it would reproduce the same opaque `ensurepip` boundary without adding evidence.

### Rematerialize the wheelhouse

Rejected because the complete wheelhouse input validation passed and package installation never
started.

### Install into Kaggle's base environment

Rejected because it would weaken isolation, introduce hidden state, and invalidate the runtime
compatibility result.

### Use network installation as a bootstrap fallback

Rejected because verification must remain offline and must not change the reviewed dependency set.

## Consequences

Verifier v3 may still fail, but any bootstrap failure will retain the exact command role, return code,
timeout state, stdout, and stderr. A successful bootstrap continues into the same exact hash-locked
offline installation and runtime checks.

## Non-claims

This decision does not establish successful pip bootstrap, offline installation, dependency
consistency, CUDA runtime compatibility, vLLM native-extension compatibility, model loading,
environment qualification, measured A/B/C authorization, or production readiness.

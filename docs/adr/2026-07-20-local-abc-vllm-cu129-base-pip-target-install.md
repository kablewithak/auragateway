# ADR: Install the CUDA 12.9 runtime into a no-pip target with base pip `--python`

Status: Accepted

Date: 2026-07-20

## Context

Offline verifier v3 Version 1 reconfirmed the complete governed wheelhouse and then localized the
bootstrap failure to the Kaggle base interpreter:

```text
input_validation=PASSED
base_python_runtime=PASSED
python_version=3.12.13
base_venv_import=PASSED
base_ensurepip_import=FAILED
failure_code=ENSUREPIP_MODULE_ABSENT
package_installation_started=false
```

Evidence identities:

```text
verifier_v3_evidence_zip_sha256=721fb2dc1fcbb57f2cda2e5772d5bac9fdf6f2f10798595fc4dd6f3cdf55d671
verifier_v3_evidence_manifest_sha256=399549e894f3d5afecffac1244d2bf32f32fb34c0f5ef815fba443b75f8613e8
reasoning_certificate_sha256=25449c1f1ce7e70c88ed4cdbbeb0a3875a05a15b4386846a22c1b70a9d6027d7
```

The failure occurred before package installation, dependency checking, GPU validation, or any target
runtime import. The wheelhouse therefore remains admissible and rematerialization is not justified.

The official pip interface supports managing another Python interpreter or a virtual environment that
does not contain pip by using pip's global `--python` option. The official Python 3.12 `venv` interface
supports `--without-pip`, which avoids invoking the absent `ensurepip` module.

## Decision

1. Preserve verifier v3 Version 1 unchanged as valid diagnostic failure evidence.
2. Do not rerun verifier v3.
3. Do not rematerialize the 5.7 GB wheelhouse.
4. Introduce verifier v4 using the base pip process only as an installation executor.
5. Require base pip 22.3 or newer before any target installation.
6. Create a clean target virtual environment with `--without-pip`.
7. Prove target prefix isolation, disabled user site, disabled system-site packages, target site paths,
   and absence of target pip before installation.
8. Invoke base pip with global `--isolated --python <target>` before the `install` subcommand.
9. Preserve `--no-index`, `--no-cache-dir`, `--find-links`, and `--require-hashes`.
10. Validate the exact 176-distribution target inventory after installation.
11. Run dependency checking through base pip against the target.
12. Run host GPU discovery independently from installation prerequisites.
13. Compare base distribution metadata snapshots before and after the attempt.
14. Stop after runtime compatibility probes. Do not load a model or issue requests.

Active verifier:

```text
repository_notebook=notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v4.ipynb
kaggle_title=auragateway-cu129-offline-verifier-v4
title_character_count=37
notebook_sha256=b6a6e1ed7f33f98959fe346be173b1799a36aecb9e0245c9d2f3beaba1bd0568
output_directory=auragateway_vllm_cu129_offline_compatibility_evidence_v4
```

## Installation contract

```text
<base-python> -m pip
  --isolated
  --disable-pip-version-check
  --python <target-venv>
  install
  --no-index
  --no-cache-dir
  --find-links <wheelhouse>
  --require-hashes
  -r <requirements-lock>
```

The `--python` option is a global pip option and must appear before the `install` subcommand.

## Alternatives rejected

### Rerun verifier v3

Rejected because the missing `ensurepip` module is now established.

### Add pip to the existing wheelhouse immediately

Rejected for this gate because pip's supported `--python` interface can manage a target environment
without pip, while retaining the exact governed runtime closure.

### Install into the base Kaggle environment

Rejected because it would weaken isolation and introduce hidden state.

### Use network bootstrap

Rejected because the verifier must remain Internet Off and use only the governed wheelhouse.

## Consequences

Verifier v4 can establish whether the existing wheelhouse installs into a clean isolated target despite
the absent `ensurepip` module. It also records the base pip version, target isolation, exact target
inventory, independent GPU topology, and base distribution metadata stability.

A matching base distribution snapshot is evidence only about installed distribution metadata. It is
not a claim that every base-environment file is byte-for-byte unchanged.

## Non-claims

This decision does not establish base pip availability in the next session, successful installation,
dependency consistency, CUDA runtime compatibility, vLLM native-extension compatibility, full base
filesystem immutability, model loading, environment qualification, measured A/B/C authorization, or
production readiness.

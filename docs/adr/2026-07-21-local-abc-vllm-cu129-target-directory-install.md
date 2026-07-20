# ADR: Base-pip target-directory installation for CUDA 12.9 verifier v7

Status: Accepted

## Context

Verifier v6 proved the controlled target-Python startup boundary but failed at:

```text
first_divergence=base_pip_python_target_support
```

The base-pip `--python <target>` command returned code 0 while emitting the inherited Kaggle
`sitecustomize` failure. The full closure was not installed.

Installation-executor inspection v1 did not test an executor because it hard-coded `wrapt`, which
is absent from the governed closure. Inspection v2 corrected probe selection and established:

```text
disposition=BASE_PIP_TARGET_DIRECTORY_INSTALL_CONFIRMED
selected_installation_executor=BASE_PIP_TARGET_DIRECTORY
selected_probe_distribution=detect-installer
target_directory_install_confirmed=true
base_distribution_metadata_unchanged=true
full_closure_installation_performed=false
```

The `--prefix` command completed, but its distribution was not discoverable from the virtual
environment's canonical target site-packages directory.

## Decision

Use:

```text
installation_executor=BASE_PIP_TARGET_DIRECTORY
target_directory=<venv>/lib/python3.12/site-packages
full_closure_install_flags=--no-index,--no-cache-dir,--no-deps,--ignore-installed,--require-hashes,--target
dependency_validation=CONTROLLED_TARGET_METADATA_AND_PACKAGING
python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
```

Verifier v7 installs the complete exact-locked closure into the explicit target site-packages
directory without invoking pip inside the target interpreter.

After installation, the controlled target interpreter must:

1. observe exactly the 176 locked distributions;
2. evaluate active `Requires-Dist` records using target `packaging`;
3. report no missing, incompatible, or invalid requirements;
4. expose no external package paths;
5. prove target-first nvJitLink resolution and the required CUDA 12.9 symbol;
6. run Torch, Transformers, vLLM, and `vllm._C` import probes.

## Evidence

```text
verifier_v6_evidence_zip_sha256=852b6d497adf620eca90c3719fe6dee1e607528ace6ac76cdf24907c009ada1f
verifier_v6_repository_manifest_sha256=1438bc8531dd961f0d57c64c9453099b4a84548a8e2848631de929900baa1656
verifier_v6_execution_log_sha256=96d8ebb496e180124f945b6c3fe9a7cd16fabec9811625e5e569f39269ede3b7
inspection_v1_evidence_zip_sha256=b5f169d039544dcf304076b98613ff4b35525e1962daf9ff41f9ab275566c9e1
inspection_v1_repository_manifest_sha256=e204f778bc137ac89c9e433d0a197266ca34962284f754d2fd983152535b3422
inspection_v1_execution_log_sha256=622c4728573b20b450553bedb43e20bd5b8558f285e676bf54226056204b57c4
inspection_v2_evidence_zip_sha256=3a13daccd9f796562436844aa33f3019bab7ad2b634bab5e7a0905511bc40b22
inspection_v2_repository_manifest_sha256=8499d4298793bc628b3c6b218496cac45232031c8177b4f34b67901da94cc483
inspection_v2_execution_log_sha256=ab55fdc1785f3ed77852c3d569bd6ec9bee7e94d1caeb492ffe0bcd742c95efc
reasoning_certificate_sha256=e803966fdaa11714c68a2d6d4ebb4f42da80b686251821d88da658758e798a0d
```

## Consequences

- Base-pip `--python` target management remains rejected for this Kaggle image.
- Base-pip `--prefix` remains rejected for the canonical target layout.
- No custom wheel unpacker is introduced.
- No wheelhouse or package version changes are authorized.
- Full-closure installation is authorized once in verifier v7.
- Model loading, requests, qualification, and measured A/B/C remain prohibited.

## Non-claims

This ADR does not establish successful verifier v7 execution, dependency closure, CUDA
initialization, vLLM import, model loading, qualification, measured A/B/C authorization, or
production readiness.

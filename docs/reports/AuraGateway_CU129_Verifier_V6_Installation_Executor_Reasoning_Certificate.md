# AuraGateway CUDA 12.9 Verifier v6 Installation Executor Reasoning Certificate

## Result

```text
result=REASONING_CHAIN_CONSISTENT
evidence_sufficiency=SUFFICIENT_FOR_V7_REMEDIATION_DECISION
root_cause_sufficiency=SUFFICIENT_FOR_BASE_PIP_PYTHON_TARGET_REJECTION
installation_executor_sufficiency=SUFFICIENT_FOR_BASE_PIP_TARGET_DIRECTORY_SELECTION
```

## Premises

1. Verifier v6 validated the exact 176-package wheelhouse, base Python, base pip, the pip-less
   virtual environment, controlled target-Python startup, and two-T4 topology.
2. Its first divergence was `base_pip_python_target_support`.
3. The base-pip `--python <target>` command returned code 0 but re-entered the target interpreter
   outside the controlled `-S` bootstrap and emitted the inherited Kaggle `sitecustomize` failure.
4. Verifier v6 did not start package installation, CUDA loader validation, Torch import, or vLLM
   import.
5. Installation-executor inspection v1 was invalid for executor selection because it hard-coded
   `wrapt`, which is absent from the governed 176-package closure.
6. Inspection v2 selected `detect-installer==0.1.0` using the deterministic
   `SMALLEST_LOCKED_PURE_PYTHON_WHEEL_WITHOUT_SCRIPT_DATA` policy.
7. The selected wheel identity matched the exact resolution lock:
   `034fb20fd665c36e6ba52b8821525ea07fb4f7f938cac459df889fb33801528a`.
8. Base pip `--prefix` returned code 0, but the controlled target interpreter could not discover the
   installed distribution in the virtual environment's canonical target site-packages directory.
9. Base pip `--target <venv-site-packages>` returned code 0, and the controlled target interpreter
   discovered the exact distribution and version with all sampled distribution files inside the
   target prefix.
10. The successful target-directory probe exposed no external package paths, retained controlled
    `sitecustomize` and `usercustomize` sentinels, and preserved base distribution metadata.
11. Neither inspection installed the full closure, loaded a model, issued a request, or claimed
    qualification.

## Evidence identities

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
```

## Resolution

```text
selected_installation_executor=BASE_PIP_TARGET_DIRECTORY
target_directory=<venv>/lib/python3.12/site-packages
pip_python_target_management=REJECTED_FOR_KAGGLE_STARTUP_CUSTOMIZATION
pip_prefix_installation=REJECTED_FOR_CANONICAL_TARGET_DISCOVERY
full_closure_install_flags=NO_INDEX,NO_CACHE_DIR,NO_DEPS,IGNORE_INSTALLED,REQUIRE_HASHES,TARGET
dependency_validation=CONTROLLED_TARGET_METADATA_AND_PACKAGING
python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
wheelhouse_rematerialization_justified=false
package_version_substitution_justified=false
```

Verifier v7 may install the exact 176-package closure only into the explicit target site-packages
directory. It must validate the exact target inventory, evaluate active `Requires-Dist` metadata
inside the controlled target interpreter, prove target-first CUDA loader resolution, and then run
Torch and vLLM import probes.

## Non-claims

This certificate does not establish successful full-closure installation, dependency closure,
Torch CUDA initialization, vLLM import, model loading, environment qualification, measured A/B/C
authorization, or production readiness.

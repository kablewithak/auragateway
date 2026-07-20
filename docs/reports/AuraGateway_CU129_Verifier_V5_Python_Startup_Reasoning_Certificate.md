# AuraGateway CUDA 12.9 Verifier v5 Python Startup Reasoning Certificate

## Result

```text
result=REASONING_CHAIN_CONSISTENT
evidence_sufficiency=SUFFICIENT_FOR_V6_REMEDIATION_DECISION
root_cause_sufficiency=SUFFICIENT_FOR_TARGET_PYTHON_STARTUP_CUSTOMIZATION_ASSIGNMENT
```

## Premises

1. Verifier v5 validated the exact 176-package wheelhouse input and created a pip-less target virtual environment.
2. The target identity subprocess returned code 0 and emitted the expected Python 3.12.13 prefix and site configuration.
3. The same subprocess emitted a Kaggle `sitecustomize` startup error for missing `wrapt`.
4. The harness correctly rejected that stderr as an inherited startup customization leak.
5. Installation and all CUDA loader/runtime probes were blocked, so verifier v5 did not test the target-first loader remediation.
6. The bounded startup inspection reproduced the warning under sanitized default startup and Python isolated mode.
7. `-S` removed the warning but also prevented virtual-environment prefix and target site-package initialization.
8. The controlled bootstrap started with `-S`, installed sentinel `sitecustomize` and `usercustomize` modules, called `site.main()`, removed external package paths, restored the target site-packages path, and completed without stderr.
9. The controlled process preserved the target prefix, disabled user-site loading, exposed no external package paths, and retained zero package installation and model requests.

## Resolution

```text
selected_remediation=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
target_python_invocation=<target-python> -S -c <controlled-bootstrap> <target-venv> <payload> [payload-args...]
sitecustomize_policy=CONTROLLED_SENTINEL_BEFORE_SITE_MAIN
usercustomize_policy=CONTROLLED_SENTINEL_BEFORE_SITE_MAIN
external_package_path_policy=REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES
wheelhouse_rematerialization_justified=false
package_version_substitution_justified=false
```

Verifier v6 must use the controlled bootstrap for every target-Python probe, including pre-install identity, post-install inventory, direct CUDA library loading, Torch, Transformers, vLLM, and `vllm._C`.

Base-Python probes, base-pip target installation, `ldd`, and `readelf` remain outside the target-Python wrapper.

## Evidence identities

```text
verifier_v5_notebook_sha256=ad4d7a533de09965f5562db58c85cb785f2a7f8550906631142e26a34b6e59ab
verifier_v5_evidence_zip_sha256=303879f21a0245f566a6df39e950afe90e8f15799a819e889a3a75b20fc97ae6
verifier_v5_evidence_manifest_sha256=798b12fcf2c4bafc1f7bcc2eb26992e24284187d968449e1cdb8869a2e6ace38
verifier_v5_execution_log_sha256=1ff315f4438fa62bc3f2ad92a369b1f5fa3d4d836f27f2e4e209fd47b4cb2056
startup_inspection_notebook_sha256=17395499ea760f021b05f252492e9b7fd3b2be48cd07650caa14e07263ef3e85
startup_inspection_evidence_zip_sha256=f44aa81e4596cf19fac9a28743662b1b53531052e4e3a9dd78f666ab75030ee8
startup_inspection_evidence_manifest_sha256=963f4c5f0a837ed0851bca291cee118abe1309441af1f8d3f77868ba4429b5d8
startup_inspection_execution_log_sha256=ea49d9732e208ecb0447a777204ef9871f12e26b12a6cb15b563c3a27ec55a64
verifier_v6_notebook_sha256=48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0
```

## Safety and non-claims

The evidence does not establish successful offline installation in verifier v6, target-first nvJitLink resolution in verifier v6, Torch CUDA initialization, vLLM import, model loading, environment qualification, measured A/B/C authorization, or production readiness.

No model request, customer data, credential use, or external spend is authorized.

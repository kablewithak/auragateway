# ADR: Controlled Python startup for CUDA 12.9 verifier v6

Status: Accepted

## Context

Verifier v5 failed before installation at `target_runtime_identity_before_install`.

```text
failure_class=TARGET_PYTHON_STARTUP_CUSTOMIZATION_LEAK
``` The target interpreter returned code 0 and emitted the expected virtual-environment identity, but Kaggle's automatic `sitecustomize` import failed because `wrapt` was unavailable.

The bounded startup inspection established:

```text
disposition=CONTROLLED_SITE_BOOTSTRAP_CONFIRMED
controlled_site_bootstrap_confirmed=true
```

Default startup and `-I` retained the host `sitecustomize` warning. `-S` removed the warning but also skipped virtual-environment prefix and target site-package initialization.

## Decision

Use:

```text
python_startup_policy=NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
sitecustomize_policy=CONTROLLED_SENTINEL_BEFORE_SITE_MAIN
usercustomize_policy=CONTROLLED_SENTINEL_BEFORE_SITE_MAIN
external_package_path_policy=REMOVE_NON_TARGET_SITE_AND_DIST_PACKAGES
canonical_loader_policy=TARGET_NVIDIA_LIBRARIES_PREPENDED
```

Every target-Python probe runs as:

```text
<target-python> -S -c <controlled-bootstrap> <target-venv> <payload> [payload-args...]
```

The wrapper installs controlled sentinel modules, calls `site.main()`, restores the target site-packages path, removes external `site-packages` and `dist-packages` paths, rewrites `sys.argv`, and executes the bounded payload.

Base-Python probes, base-pip target installation, `ldd`, and `readelf` remain outside this wrapper.

## Evidence

```text
verifier_v5_evidence_zip_sha256=303879f21a0245f566a6df39e950afe90e8f15799a819e889a3a75b20fc97ae6
verifier_v5_evidence_manifest_sha256=798b12fcf2c4bafc1f7bcc2eb26992e24284187d968449e1cdb8869a2e6ace38
verifier_v5_execution_log_sha256=1ff315f4438fa62bc3f2ad92a369b1f5fa3d4d836f27f2e4e209fd47b4cb2056
startup_inspection_evidence_zip_sha256=f44aa81e4596cf19fac9a28743662b1b53531052e4e3a9dd78f666ab75030ee8
startup_inspection_evidence_manifest_sha256=963f4c5f0a837ed0851bca291cee118abe1309441af1f8d3f77868ba4429b5d8
startup_inspection_execution_log_sha256=ea49d9732e208ecb0447a777204ef9871f12e26b12a6cb15b563c3a27ec55a64
reasoning_certificate_sha256=d9b228d6ee891e72146794fd0a171ad22354ae8e5195d8b14ae6b2f6bb221bfd
verifier_v6_notebook_sha256=48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0
decision_record_sha256=4d8e439e652916892777272219784c7197c849dbf26717f2e7403d1acfd9813a
```

## Consequences

The target process no longer executes Kaggle's host startup customization. The verifier retains target virtual-environment identity and target package discovery while preserving the existing target-first CUDA loader policy.

The wrapper is process-local. It does not modify the Kaggle base environment or the target filesystem beyond the existing package installation.

## Non-claims

This ADR does not claim successful verifier v6 installation, CUDA initialization, vLLM import, model loading, qualification, measured A/B/C authorization, or production readiness.

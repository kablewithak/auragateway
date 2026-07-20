# AuraGateway Semi-Formal Reasoning Certificate

**Certificate ID:** `AG-LABC-CU129-OV4-DL1-RC-2026-07-20-01`  
**Subject:** CUDA 12.9 offline verifier v4 plus dynamic-linker inspection v1  
**Verifier v4 evidence ZIP SHA-256:** `9a4bd10a66c440ffb2628f98ce143e38a1b5cdb06a745497b7b386910816e0fe`  
**Inspection evidence ZIP SHA-256:** `b241f49a4636c6e427299582c130f4742cf925ad5f541a65f852fa424457d2d0`  
**Disposition:** `VALID_RUNTIME_FAILURE_WITH_ASSIGNED_LOADER_ROOT_CAUSE`  
**Next gate:** `BUILD_TARGET_FIRST_LOADER_VERIFIER_V5`

## 1. Question

What did verifier v4 prove, what caused its CUDA runtime failure, and what is the smallest
evidence-preserving remediation?

## 2. Evidence integrity

Verifier v4 produced 21 files. Its internal SHA-256 manifest contains 20 payload records. Every
record was recomputed and matched its recorded digest and byte size.

The dynamic-linker inspection produced 12 files. Its internal SHA-256 manifest contains 11 payload
records. Every record was recomputed and matched its recorded digest and byte size.

The complete execution logs were also retained.

**Status:** Established.

## 3. Premises

### P1 — The exact governed wheelhouse passed validation

Verifier v4 recorded:

```text
input_validation=PASSED
package_count=176
manifest_entry_count=182
wheel_entry_count=176
non_wheel_entry_count=6
total_wheel_bytes=5727339111
```

**Status:** Established.

### P2 — The exact closure installed successfully offline

Verifier v4 recorded:

```text
base_pip_version=24.1.2
gpu_topology=T4 x2
venv_create_without_pip=PASSED
base_pip_python_target_support=PASSED
offline_hash_locked_install_via_base_pip=PASSED
target_distribution_inventory=PASSED
target_distribution_count=176
target_dependency_check_via_base_pip=PASSED
base_distribution_metadata_unchanged=true
```

**Status:** Established.

### P3 — The first runtime failure occurred at Torch CUDA library loading

Verifier v4 recorded:

```text
first_divergence=torch_family_runtime
error=libcusparse.so.12: undefined symbol:
__nvJitLinkGetErrorLogSize_12_9, version libnvJitLink.so.12
```

`vllm_module` and `vllm_native_extension` then failed through the same Torch import path.

**Status:** Established.

### P4 — The governed nvJitLink library contains the required CUDA 12.9 symbol

The inspection extracted the exact governed `nvidia-nvjitlink-cu12==12.9.86` wheel and recorded:

```text
libnvJitLink_sha256=02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f
required_symbol=__nvJitLinkGetErrorLogSize_12_9
required_symbol_present=true
```

**Status:** Established.

### P5 — Kaggle's inherited loader path selected an older library

Under the inherited environment, `ldd` resolved:

```text
libnvJitLink.so.12 => /usr/local/cuda/lib64/libnvJitLink.so.12
```

That file resolved to CUDA 12.8 content, had SHA-256
`0369e6867d44b800437de4e146d72c65afc6c75adf677a15c2ecd8e6a7ac135f`, and did not
contain the required `_12_9` symbol.

The direct `libcusparse.so.12` load failed under this condition.

**Status:** Established.

### P6 — Target-first loader ordering corrected the direct library load

With the governed CUDA wheel library directories prepended, `ldd` resolved the governed
`libnvJitLink.so.12` and direct `libcusparse.so.12` loading passed.

```text
root_cause_assignment=LOADER_PRECEDENCE_CONFIRMED
inherited_environment_load_status=FAILED
target_first_environment_load_status=PASSED
```

**Status:** Established.

### P7 — Python process-environment isolation was incomplete in verifier v4

Several target subprocesses emitted:

```text
Error in sitecustomize
ModuleNotFoundError: No module named 'wrapt'
```

The v4 target prefix and site configuration were isolated, but inherited `PYTHONPATH` and process
environment effects were not fully excluded.

**Status:** Established.

## 4. Trace

1. Validate the exact 182-member materializer output.
2. Create a pip-less Python 3.12 target environment.
3. Use base pip 24.1.2 only as an installation executor.
4. Install all 176 exact hash-locked distributions offline.
5. Validate exact target distribution inventory.
6. Validate package metadata consistency.
7. Confirm T4 x2.
8. Attempt Torch import.
9. Observe CUDA symbol failure in `libcusparse.so.12`.
10. Extract only the governed nvJitLink, cuSPARSE, and CUDA runtime wheels.
11. Confirm the governed nvJitLink library contains the required symbol.
12. Confirm inherited loader ordering selects the CUDA 12.8 library.
13. Confirm target-first ordering selects the governed CUDA 12.9 library.
14. Confirm the same direct cuSPARSE load passes with target-first ordering.
15. Make zero model requests and claim no qualification.

## 5. First divergence

```text
failure_class=CUDA_DYNAMIC_LOADER_PRECEDENCE_FAILURE
failure_code=INHERITED_NVJITLINK_PRECEDES_GOVERNED_TARGET_LIBRARY
first_divergence=torch_family_runtime
assigned_root_cause=LOADER_PRECEDENCE_CONFIRMED
```

## 6. Conclusions

### C1 — Wheelhouse rematerialization is not justified

The wheelhouse validated, installed, matched the exact target inventory, and passed dependency
metadata checking. The required CUDA 12.9 symbol exists in the governed library.

**Confidence:** High.

### C2 — Version substitution is not justified

The failure is explained by loader selection, not by absence of the required symbol from the selected
governed version.

**Confidence:** High.

### C3 — Verifier v5 must govern the process environment, not only the Python prefix

A valid remediation must remove inherited Python path injection, prepend target NVIDIA library
directories, retain inherited loader paths only after target paths, and run each runtime probe in a
fresh subprocess with the canonical environment.

**Confidence:** High.

### C4 — Loader resolution must be proven before Torch import

Verifier v5 must bind the exact target `libnvJitLink.so.12` and `libcusparse.so.12` hashes, confirm
the required symbol, and prove `ldd` resolves the target nvJitLink library.

**Confidence:** High.

### C5 — vLLM failures should be causally blocked by Torch failure

If Torch fails, vLLM module and native-extension probes should be
`BLOCKED_BY_UPSTREAM_FAILURE`, not reported as independent observed failures.

**Confidence:** High.

## 7. Rejected interpretations

The evidence does not support:

- corrupt wheelhouse;
- failed offline installation;
- missing package dependency metadata;
- absent T4 GPUs;
- missing CUDA 12.9 symbol in the governed nvJitLink wheel;
- need to replace Torch, cuSPARSE, or nvJitLink versions;
- need to rematerialize the 5.7 GB artifact;
- model or tokenizer failure;
- environment qualification;
- production readiness.

## 8. Alternatives considered

### A — Rematerialize with different CUDA packages

Rejected. The current closure installs and contains the required symbol.

### B — Replace the Kaggle system CUDA installation

Rejected. The verifier must not mutate the host runtime or require elevated access.

### C — Install into the Kaggle base environment

Rejected. This weakens isolation and introduces hidden state.

### D — Set target-first loader ordering only for one ad hoc command

Rejected. The remediation must be deterministic, inspectable, and applied to every governed runtime
probe.

### E — Canonical target-first loader verifier v5

Accepted. This is the smallest intervention supported by the evidence.

## 9. Required verifier v5 behavior

Verifier v5 must:

1. Preserve verifier v4 Version 1 and inspection Version 1 unchanged.
2. Reuse the exact successful materializer Version 1 output.
3. Preserve T4 x2, Internet Off, no secrets, and zero model requests.
4. Create a clean target with `venv --without-pip`.
5. Install the exact hash-locked closure through base pip `--python`.
6. Remove `PYTHONPATH` and `PYTHONHOME` from target subprocess environments.
7. Set `PYTHONNOUSERSITE=1`.
8. Prepend all target `nvidia/*/lib` directories to `LD_LIBRARY_PATH`.
9. Preserve inherited loader paths only after target directories.
10. Bind target nvJitLink SHA-256 `02d3acb5fe598dd20f0fca3cc03734ad164037a22747a01900561a42d0b8448f`.
11. Bind target cuSPARSE SHA-256
    `6d85ab1acdabfe3b5a54aa76bc948c719bcd03e07eede3eb8122b083c1a6ecf7`.
12. Confirm `__nvJitLinkGetErrorLogSize_12_9` is present.
13. Confirm canonical `ldd` resolution selects the target nvJitLink library.
14. Confirm direct cuSPARSE loading passes.
15. Confirm target `sys.path` excludes inherited base distribution paths.
16. Run Torch, Transformers, vLLM distribution, vLLM module, and `vllm._C` probes.
17. Block vLLM import probes if Torch fails.
18. Compare base distribution metadata before and after.
19. Emit evidence for both success and failure.
20. Stop before model loading, workers, requests, or qualification.

## 10. Regression gate

Verifier v5 is acceptable only if fixed tests establish:

- target library directories precede inherited loader directories;
- duplicates are removed without reordering the first occurrence;
- `PYTHONPATH` and `PYTHONHOME` are removed;
- `PYTHONNOUSERSITE=1`;
- target nvJitLink and cuSPARSE identities are bound;
- canonical loader resolution is required before Torch;
- vLLM module and native-extension probes depend on Torch;
- model loading and model requests remain absent;
- historical v4 and inspection evidence identities remain immutable.

## 11. Claims and non-claims

### Allowed claims

- Exact wheelhouse integrity passed.
- Exact offline installation passed.
- Exact 176-distribution target inventory passed.
- Dependency metadata consistency passed.
- T4 x2 passed.
- The governed CUDA 12.9 nvJitLink library contains the required symbol.
- Kaggle's inherited loader selected an older CUDA library.
- Target-first loader ordering corrected direct cuSPARSE loading.
- Loader precedence is the assigned v4 root cause.

### Prohibited claims

- Torch CUDA runtime passes under verifier v5.
- vLLM module import passes under verifier v5.
- vLLM native-extension import passes under verifier v5.
- Model loading succeeds.
- Measured A/B/C execution is authorized.
- Environment qualification is complete.
- Production readiness.

## 12. Certified resolution

```text
PRESERVE_V4_VERSION_1
→ PRESERVE_DYNLINK_INSPECTION_VERSION_1
→ INTEGRATE_EVIDENCE
→ BUILD_TARGET_FIRST_LOADER_VERIFIER_V5
→ RUN_ONCE
```

No wheelhouse rematerialization or package-version substitution is justified.

---

**Certificate result:** `REASONING_CHAIN_CONSISTENT`  
**Evidence sufficiency:** `SUFFICIENT_FOR_V5_REMEDIATION_DECISION`  
**Root-cause sufficiency:** `SUFFICIENT_FOR_LOADER_PRECEDENCE_ASSIGNMENT`

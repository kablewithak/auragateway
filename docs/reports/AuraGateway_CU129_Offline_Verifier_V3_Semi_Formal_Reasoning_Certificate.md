# AuraGateway Semi-Formal Reasoning Certificate

**Certificate ID:** `AG-LABC-CU129-OV3-RC-2026-07-20-01`  
**Subject:** CUDA 12.9 offline runtime verifier v3, Version 1  
**Evidence artifact:** `auragateway_vllm_cu129_offline_compatibility_evidence_v3.zip`  
**Evidence ZIP SHA-256:** `721fb2dc1fcbb57f2cda2e5772d5bac9fdf6f2f10798595fc4dd6f3cdf55d671`  
**Disposition:** `VALID_DIAGNOSTIC_FAILURE`  
**Next gate:** `BUILD_BASE_PIP_TARGET_INSTALL_VERIFIER_V4`

## 1. Question

What did verifier v3 establish, what remains untested, and what is the smallest isolation-preserving
remediation?

## 2. Evidence integrity

The evidence ZIP contains 20 files. Its internal manifest lists 19 governed payload records. Every
listed record was independently recomputed and matched its recorded SHA-256 digest and byte size.

**Status:** Established.

## 3. Premises

### P1 — Governed wheelhouse validation passed

`00_input_validation.json` records:

```text
status=PASSED
package_count=176
manifest_entry_count=182
wheel_entry_count=176
non_wheel_entry_count=6
total_wheel_bytes=5727339111
network_access_requested=false
model_requests_performed=0
qualification_claimed=false
```

**Status:** Established.

### P2 — The base interpreter and `venv` module were available

```text
base_python_runtime=PASSED
python_version=3.12.13
base_venv_import=PASSED
```

**Status:** Established.

### P3 — The first observed failure was absence of `ensurepip`

`10_03_base_ensurepip_import.json` records:

```text
status=FAILED
returncode=1
error=ModuleNotFoundError: No module named 'ensurepip'
```

**Status:** Established.

### P4 — Package installation did not start

The summary records:

```text
first_divergence=base_ensurepip_import
package_installation_started=false
install_runtime_script_executed=false
```

**Status:** Established.

### P5 — Downstream roles were blocked rather than independently failed

The only observed failed role was `base_ensurepip_import`. Fourteen dependent roles were explicitly
classified as `BLOCKED_BY_UPSTREAM_FAILURE`.

**Status:** Established.

## 4. Trace

1. The exact governed wheelhouse passed all topology, size, hash, lock, receipt, and runtime-manifest
   checks.
2. The Kaggle base Python was confirmed as 3.12.13.
3. The base `venv` module imported successfully.
4. Importing `ensurepip` failed with `ModuleNotFoundError`.
5. Verifier v3 stopped the dependent bootstrap and installation path.
6. No wheel was installed, no runtime import was attempted, and no model request occurred.
7. The verifier emitted a complete bounded diagnostic evidence ZIP.

## 5. First divergence

```text
failure_class=BASE_INTERPRETER_BOOTSTRAP_CAPABILITY_FAILURE
failure_code=ENSUREPIP_MODULE_ABSENT
first_divergence=base_ensurepip_import
```

## 6. Conclusions

### C1 — The v2 bootstrap failure cause is now assigned

The base interpreter lacks the `ensurepip` module. That capability gap explains why
`venv.EnvBuilder(with_pip=True)` failed in verifier v2.

**Confidence:** High.

### C2 — The wheelhouse remains admissible

No evidence implicates wheel corruption, dependency closure, CUDA, Torch, vLLM, or the T4 topology.
Package installation never started.

**Confidence:** High.

### C3 — Rematerialization is not justified

The complete wheelhouse input validation passed again, and the failure occurred before any wheel
installation boundary.

**Confidence:** High.

### C4 — A supported isolation-preserving bypass exists

The official pip interface supports managing a different interpreter or a virtual environment that
does not contain pip by using pip's global `--python` option. The official Python `venv` interface
supports creating the target with `--without-pip`.

**Confidence:** High.

### C5 — Base pip must be treated as an installation executor, not as a target runtime dependency

Verifier v4 must record the observed base pip version and require support for `--python`. It must
install into a clean target environment, prove the target prefix and site isolation, and compare base
distribution metadata before and after installation.

**Confidence:** High.

## 7. Rejected interpretations

The evidence does not support these statements:

- the 176-wheel closure is corrupt;
- pip dependency resolution failed;
- the T4 topology failed;
- Torch CUDA initialization failed;
- vLLM or `vllm._C` import failed;
- the wheelhouse must be rematerialized;
- the Kaggle base environment may be used as the target runtime;
- environment qualification has been established.

## 8. Alternatives

### A — Rerun verifier v3 unchanged

Rejected. The absent module is now established and a rerun would not produce new evidence.

### B — Rematerialize the wheelhouse to add pip

Rejected for this gate. The existing wheelhouse passed integrity validation, and official pip supports
installing into a target environment without pip.

### C — Install the runtime into Kaggle's base interpreter

Rejected. This would weaken isolation, risk hidden state, and invalidate the target-runtime claim.

### D — Use base pip with `--python` against a clean no-pip target

Accepted, subject to explicit base-pip capability checks, target isolation checks, exact offline
hash-locked installation, target closure validation, and base-distribution snapshot comparison.

## 9. Required verifier v4 behavior

Verifier v4 must:

1. preserve verifier v3 Version 1 as immutable evidence;
2. reuse the same successful materializer Version 1 input;
3. keep T4 x2, Internet Off, no secrets, zero model requests, and no qualification claim;
4. independently probe base Python, `venv`, base pip, and GPU topology;
5. require base pip version 22.3 or newer;
6. create the target with `venv --without-pip`;
7. prove target prefix, base-prefix separation, disabled user site, disabled system-site packages, and
   absence of target pip before installation;
8. invoke base pip with global `--isolated --python <target>` before the `install` subcommand;
9. install only from the exact wheelhouse with `--no-index --require-hashes`;
10. validate the exact 176-distribution target inventory;
11. run dependency checking through base pip against the target;
12. validate Python, Torch-family, CUDA, Transformers, vLLM, and `vllm._C` in the target interpreter;
13. compare base distribution metadata snapshots before and after the attempt;
14. preserve `FAILED`, `BLOCKED_BY_UPSTREAM_FAILURE`, and `NOT_EXECUTED` states;
15. emit evidence even when a gate fails.

## 10. Regression gate

Fixed cases must prove:

- unsupported base pip blocks installation;
- target creation never invokes `ensurepip`;
- the `--python` option appears before `install`;
- target isolation failure blocks installation;
- GPU topology remains independently observable;
- target closure drift fails the result;
- base distribution metadata drift fails the result;
- downstream blocked roles are not classified as observed failures.

## 11. Non-claims

This certificate does not establish:

- availability or version of base pip in the next Kaggle session;
- successful target installation;
- full base-filesystem immutability;
- successful dependency checking;
- successful two-T4 validation;
- successful Torch CUDA or vLLM native-extension import;
- model loading;
- environment qualification;
- measured A/B/C authorization;
- production readiness.

## 12. Certified resolution

```text
PRESERVE_V3_VERSION_1
→ INTEGRATE_V3_EVIDENCE
→ BUILD_VERIFIER_V4
→ INSTALL_INTO_NO_PIP_TARGET_VIA_BASE_PIP_--PYTHON
→ RUN_ONCE
```

No wheelhouse rematerialization is justified by the current evidence.

---

**Certificate result:** `REASONING_CHAIN_CONSISTENT`  
**Evidence sufficiency:** `SUFFICIENT_FOR_V4_REMEDIATION_DECISION`  
**Root-cause sufficiency:** `SUFFICIENT_FOR_ENSUREPIP_ABSENCE_ASSIGNMENT`

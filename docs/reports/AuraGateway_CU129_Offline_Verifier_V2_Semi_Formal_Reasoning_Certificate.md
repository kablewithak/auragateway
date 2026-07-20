# AuraGateway Semi-Formal Reasoning Certificate

**Certificate ID:** `AG-LABC-CU129-OV2-RC-2026-07-20-01`  
**Subject:** CUDA 12.9 offline runtime verifier v2, Version 1  
**Evidence artifact:** `auragateway_vllm_cu129_offline_compatibility_evidence_v2.zip`  
**Evidence ZIP SHA-256:** `01019ce577f2bc7bfaaa8810d19161157f1dbc15b3c8817c2ba7836c4b0158d4`  
**Disposition:** `VALID_DIAGNOSTIC_FAILURE`  
**Next gate:** `INTEGRATE_V2_FAILURE_AND_BUILD_VERIFIER_V3`

## 1. Question

What failed, what passed, what can be claimed, and what is the smallest evidence-preserving next step?

## 2. Evidence set

The evidence ZIP contains exactly four files:

1. `00_input_validation.json`
2. `10_offline_isolated_install.json`
3. `90_summary.json`
4. `99_evidence_sha256.json`

The internal evidence manifest was recomputed. Every listed file matched both its recorded byte size and SHA-256 digest.

## 3. Premises

### P1 — Evidence integrity

The outer ZIP SHA-256 is:

`01019ce577f2bc7bfaaa8810d19161157f1dbc15b3c8817c2ba7836c4b0158d4`

The internal manifest contains three governed payload records, and each payload independently matches its recorded SHA-256 and size.

**Status:** Established.

### P2 — Governed input validation passed

`00_input_validation.json` records:

- `status=PASSED`
- `package_count=176`
- `manifest_entry_count=182`
- `wheel_entry_count=176`
- `non_wheel_entry_count=6`
- `total_wheel_bytes=5727339111`
- exact resolution-lock, receipt, runtime-manifest, and SHA-manifest identities
- `network_access_requested=false`
- `credentials_used=false`
- `customer_data_used=false`
- `model_requests_performed=0`
- `qualification_claimed=false`
- `working_free_bytes_before_install=20940476416`

**Status:** Established.

### P3 — The first observed failure occurred during pip bootstrap inside virtual-environment creation

`10_offline_isolated_install.json` records:

- `status=FAILED`
- `returncode=1`
- `timed_out=false`
- `duration_ms=183`

The traceback follows this path:

`install_runtime.py`
→ `venv.EnvBuilder(with_pip=True).create(...)`
→ `venv._setup_pip(...)`
→ new interpreter runs `-m ensurepip --upgrade --default-pip`
→ nested process exits with status 1
→ outer process raises `subprocess.CalledProcessError`

**Status:** Established.

### P4 — The hash-locked package installation command was not reached

The installer creates the virtual environment before constructing and executing:

`python -m pip install --no-index --find-links ... --require-hashes -r requirements.lock.txt`

Because virtual-environment creation raised first, that installation subprocess was not started.

**Status:** Established by control flow.

### P5 — Downstream runtime probes were conditional on successful installation

The verifier schedules `pip_check`, GPU topology, Python, Torch-family, Transformers, vLLM distribution, vLLM module, and `vllm._C` probes only when `offline_isolated_install` reports `PASSED`.

The evidence ZIP contains no downstream probe records.

**Status:** Established.

## 4. Execution trace

1. Exactly one governed wheelhouse directory was found.
2. Input topology and safety checks passed.
3. All 182 manifest entries were validated.
4. The 176-wheel closure matched the exact resolution lock.
5. Receipt and runtime identities matched.
6. Writable disk exceeded the verifier threshold.
7. The installer started.
8. Virtual-environment directory creation began.
9. `ensurepip` was invoked inside the new interpreter.
10. `ensurepip` exited non-zero.
11. The outer installer returned failure.
12. No package installation, `pip check`, GPU probe, runtime import, or native-extension probe ran.
13. The verifier emitted a bounded failure evidence ZIP.
14. Zero model requests were made and no qualification was claimed.

## 5. Divergence point

**Intended behavior**

Create a fresh Python 3.12 virtual environment with pip, then install the exact hash-locked wheelhouse offline.

**Observed behavior**

Virtual-environment creation failed while bootstrapping pip through `ensurepip`.

**First divergence**

`<venv>/bin/python3 -m ensurepip --upgrade --default-pip`

returned exit status 1.

## 6. Conclusions

### C1 — Wheelhouse input integrity passed

The successful input-validation record supports the claim that the attached governed wheelhouse matched the expected topology, hashes, package count, byte count, and exact lock correspondence.

**Confidence:** High.

### C2 — Offline installability remains untested

The wheelhouse installation command did not begin. Therefore no claim may be made about whether the 176 packages install successfully.

**Confidence:** High.

### C3 — Only one failure was observed

The only observed failed probe was `offline_isolated_install`.

The eight additional names in `failed_required_roles` were required roles absent because the upstream installation failed. They are not eight independently observed runtime failures.

**Confidence:** High.

### C4 — The immediate blocker is pip bootstrap, not wheel resolution

The evidence localizes the current blocker to `ensurepip` during isolated environment creation. It does not implicate a particular wheel, dependency, GPU, CUDA runtime, or vLLM ABI.

**Confidence:** High.

### C5 — The exact underlying reason for `ensurepip` failure is not yet known

The evidence captures the outer `CalledProcessError` but not the nested `ensurepip` stdout and stderr. Possible causes remain hypotheses, not findings.

**Confidence:** High.

## 7. Rejected interpretations

The evidence does not support any of these statements:

- “All nine runtime checks failed.”
- “The CUDA 12.9 wheelhouse is corrupt.”
- “vLLM 0.19.1 is incompatible with Torch 2.10.0+cu129.”
- “The T4 GPUs were not visible.”
- “`pip check` failed.”
- “The wheelhouse needs to be rematerialized.”
- “The exact root cause is a missing operating-system package.”
- “Environment qualification failed.”

## 8. Alternatives considered

### A — Rerun verifier v2 unchanged

Rejected. It would consume compute while preserving the same opaque `ensurepip` failure boundary.

### B — Rematerialize the 5.7 GB wheelhouse

Rejected. The governed input validation passed, and pip never attempted to install a wheel.

### C — Bypass isolation and install into Kaggle’s base environment

Rejected. That would weaken the environment contract, introduce hidden state, and invalidate the compatibility result.

### D — Build verifier v3 with explicit bootstrap observability

Accepted. This is the smallest maintainable intervention that distinguishes interpreter, `venv`, `ensurepip`, and package-installation failures without weakening isolation.

## 9. Required verifier v3 behavior

Verifier v3 should:

1. Preserve verifier v2 Version 1 as immutable evidence.
2. Reuse the same successful materializer Version 1 input.
3. Keep T4 x2, Internet Off, no secrets, no model requests, and no qualification claim.
4. Probe the base interpreter before environment creation:
   - Python version
   - `import venv`
   - `import ensurepip`
   - `ensurepip.version()`
   - `python -m ensurepip --version`
5. Create the environment with `with_pip=False`.
6. Run the new interpreter’s `ensurepip` as a separately captured subprocess.
7. Preserve nested stdout, stderr, return code, timing, and timeout state.
8. Start the hash-locked offline install only after pip bootstrap passes.
9. Mark downstream roles as `BLOCKED_BY_UPSTREAM_FAILURE` or `NOT_EXECUTED`, not `FAILED`.
10. Emit evidence even when bootstrap fails.
11. Avoid fallback to the base environment or network installation.
12. Stop before model loading, workers, requests, or qualification.

## 10. Regression gate

Verifier v3 is acceptable only if a synthetic or fixed-case test demonstrates all of the following:

- an `ensurepip` failure retains nested stdout and stderr;
- package installation is not started after bootstrap failure;
- downstream probes are labeled blocked or not executed;
- the evidence ZIP is still created;
- all safety fields remain false or zero;
- successful bootstrap continues into the same exact offline install and runtime probes.

## 11. Claims and non-claims

### Allowed claims

- The exact-locked wheelhouse materialization remains valid.
- Verifier v2 validated the complete governed input successfully.
- The first observed runtime-verification divergence is isolated pip bootstrap failure.
- No package installation, model request, or qualification occurred.

### Prohibited claims

- Successful offline installation.
- Successful dependency consistency.
- Successful two-T4 topology validation.
- Successful CUDA 12.9 runtime initialization.
- Successful vLLM or `vllm._C` import.
- Environment qualification.
- Authorization for measured A/B/C execution.
- Production readiness.

## 12. Certified resolution

`PRESERVE_V2_VERSION_1 → INTEGRATE_FAILURE_EVIDENCE → BUILD_VERIFIER_V3 → RUN_ONCE`

No wheelhouse rematerialization is justified by the current evidence.

---

**Certificate result:** `REASONING_CHAIN_CONSISTENT`  
**Evidence sufficiency:** `SUFFICIENT_FOR_V3_REMEDIATION_DECISION`  
**Root-cause sufficiency:** `INSUFFICIENT_FOR_ENSUREPIP_CAUSE_ASSIGNMENT`

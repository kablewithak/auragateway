# ADR Addendum: P5/P6 Mechanism-Admission Successor Runtime Outcome Contract V1

**Date:** 2026-08-22
**Status:** Accepted implementation addendum; no execution authority created
**Implementation base main:** `68a2a36016a85661c820545fad67db925f84ffd0`
**Governing design:** `auragateway-p5-p6-mechanism-admission-successor-design-v1`
**Next gate:** `IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`

## Decision

The P5/P6 Mechanism-Admission Successor V1 implementation may correct one newly discovered predecessor process-outcome contract mismatch in addition to the already-approved semantic/mechanism separation.

The bounded correction is:

```text
run_bounded_process(returncode == 0)
    -> process_outcome = "PASSED"

install_runtime(target_environment_creation)
    -> require process_outcome == "PASSED"
```

The successor must not change the producer-side `run_bounded_process()` success vocabulary to `ZERO_EXIT`. The existing producer vocabulary `PASSED`, `LAUNCH_ERROR`, `TIMEOUT`, and `NONZERO_EXIT` remains authoritative for the successor.

This correction is implementation-enabling only. It does not requalify P5, requalify P6, qualify the C4 semantic canary, establish variance adequacy, authorize execution, or establish any North Star result.

## Evidence basis

Static inspection of the exact governed Exact-Runtime P5/P6 Requalification V2 predecessor bytes found an internally inconsistent process-outcome contract.

Bound predecessor identities:

- V2 producer: `src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v2.py`
  - SHA-256: `5a91268ff616bf925bba5e0eafc80be4353f40e97ed5d5b01ea5c0a8feed50d6`
- V2 runtime template: `src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v2.py.tmpl`
  - SHA-256: `5af0c62de986c332a95ed5a97be14e35418448d9ad1427bc6321749765a2d48c`
- V2 focused tests: `tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v2.py`
  - SHA-256: `71091e28c2a3130f06e561625cb422e239f91fb0d4213c26908d3b4e1f9be827`
- Successor Design V1 record:
  - SHA-256: `6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c`

In the V2 runtime template, `run_bounded_process()` classifies a zero return code as:

```python
elif returncode == 0:
    process_outcome = "PASSED"
```

The same function projects:

```python
"status": "PASSED" if process_outcome == "PASSED" else "FAILED"
```

However, `install_runtime()` subsequently checks the successful target-environment creation result against a state that the producer never emits:

```python
if create_process["process_outcome"] != "ZERO_EXIT":
    raise DiagnosticFailure(
        "MODEL_CONSTRUCTION_FAILURE",
        "isolated target environment creation failed",
    )
```

No `ZERO_EXIT` success state is emitted by `run_bounded_process()` in the inspected V2 template. The inspected V2 focused test file contains no direct coverage of `run_bounded_process()`, `install_runtime()`, `process_outcome`, or `ZERO_EXIT`.

Therefore the exact predecessor contains a statically demonstrable producer/consumer vocabulary mismatch on the target-environment creation path.

## Failure classification

```text
failure_family = PROCESS_OUTCOME_CONTRACT_MISMATCH
failure_depth = EARLY_RUNTIME_PREPARATION
observed_execution = false
runtime_failure_reproduced_live = false
static_contract_mismatch_established = true
recurrence_class = R0_FOR_THIS_DEFECT
```

This addendum does not claim that a governed live V2 run reached this line or failed for this reason. The finding is a static contradiction in the exact predecessor bytes.

## Why the consumer changes, not the producer

Changing `install_runtime()` from `ZERO_EXIT` to `PASSED` is the smallest contract-preserving correction.

Reasons:

1. `PASSED` is already the success vocabulary emitted by `run_bounded_process()`.
2. The same function's top-level `status` field is already derived from `process_outcome == "PASSED"`.
3. The remaining emitted terminal states are already consumed downstream as `LAUNCH_ERROR`, `TIMEOUT`, and `NONZERO_EXIT`.
4. Changing the producer to emit `ZERO_EXIT` would alter a wider shared process-result contract and would require broader dependent review without evidence that such a redesign is necessary.

## Relationship to Successor Design V1

The merged successor design remains directionally authoritative. Its five approved implementation changes remain in force:

- typed semantic observation;
- total semantic observer replacing exception-driven exact-object validation;
- `run_structured_request()` semantic/mechanism separation;
- frozen P5/P6 mechanism criteria;
- distinct successor authorization scope with V2 authority non-reuse.

This addendum authorizes one additional implementation correction only:

```text
MC-06
Target: install_runtime target-environment creation success check
Change: "ZERO_EXIT" -> "PASSED"
Purpose: reconcile the consumer with the predecessor process-outcome producer vocabulary
```

No other V2 runtime behavior is authorized to change merely because this defect was discovered.

## Successor implementation requirements

The successor implementation must satisfy all of the following.

### Semantic/mechanism boundary

A response admitted by transport/envelope/mechanism checks must produce one typed semantic state:

- `EXACT_MATCH`
- `VALID_JSON_MISMATCH`
- `NON_OBJECT_JSON`
- `INVALID_JSON`

A negative semantic state must not discard otherwise valid token, metric, route, worker, or output-provenance evidence.

### C4 projection

C4 semantic state must be derived from the typed semantic observation. The successor must not hard-code C4 PASS merely because `run_structured_request()` returned.

A semantic negative is completed semantic evidence, not an execution exception.

### Mechanism admission remains fail-closed

The successor must continue to block mechanism admission for invalid transport or envelope state, including a `finish_reason` other than `stop`, invalid token accounting, request/token identity drift, metric ambiguity, worker attribution ambiguity, hidden retry, request reconciliation failure, or teardown failure.

### Output provenance

Response-content provenance must survive semantic failure. The successor must retain a digest of the actual non-empty response content without retaining or logging raw model output.

### P5/P6 immutability

The successor producer must prove that the P5 and P6 acceptance evaluators do not consume semantic state and that their frozen mechanism criteria are not relaxed.

At minimum, successor validation must prove the V2 and successor `decide_p5()` and `decide_p6()` semantic ASTs are identical.

### Authorization

The V2 authorization scope is not reusable. The successor requires its own scope:

`P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1`

This addendum does not design an issuer, issue authorization, or authorize runtime execution.

## Required regressions

The successor focused tests must include these fixed cases.

### R1 — semantic mismatch preserves mechanism evidence

```text
healthy envelope
+ finish_reason == stop
+ valid token identity
+ valid metric delta
+ wrong JSON object
-> semantic = VALID_JSON_MISMATCH
-> mechanism evidence retained
-> no semantic-triggered execution failure
```

### R2 — invalid JSON preserves mechanism evidence

```text
healthy envelope
+ finish_reason == stop
+ valid token identity
+ valid metric delta
+ non-empty invalid JSON content
-> semantic = INVALID_JSON
-> response-content digest retained
-> mechanism evidence retained
-> no semantic-triggered execution failure
```

### R3 — non-stop finish reason remains blocking

```text
otherwise healthy response
+ finish_reason != stop
-> mechanism admission fails closed
```

### R4 — P5/P6 invariant under semantic substitution

Holding token, cache, metric, route, process, and worker evidence fixed while changing only semantic state must not change the P5 or P6 decision.

### R5 — process-outcome consumer accepts canonical success state

```text
run_bounded_process result:
    status = PASSED
    process_outcome = PASSED
    returncode = 0
-> install_runtime target-environment creation does not reject the result as a vocabulary mismatch
```

The test does not need to install the real runtime or execute a model. It may use deterministic stubs around the bounded subprocess boundary.

### R6 — impossible legacy success token removed from successor

The successor runtime template must not use `ZERO_EXIT` as a required success state for the target-environment creation result.

## Producer audits

The successor producer must fail closed if any of these conditions drift:

- V2 predecessor source/template/test identities;
- Gate B mechanism-admission contract and assessment identities;
- Successor Design V1 and review identities;
- semantic state inventory;
- `finish_reason == "stop"` admission check;
- response-content digest retention;
- V2/successor `decide_p5()` AST identity;
- V2/successor `decide_p6()` AST identity;
- successor authorization scope distinct from V2;
- target-environment creation success check uses `PASSED`;
- successor runtime or notebook remains unexecuted in repository artifacts.

## Non-claims

This addendum does not establish that:

- V2 failed live because of the process-outcome mismatch;
- the successor runtime is implemented;
- the successor runtime is executable;
- C4-S is qualified;
- P5 is requalified;
- P6 is requalified;
- variance is accepted;
- final A/B/C has been executed;
- quality non-inferiority is established;
- production readiness is established.

## Lifecycle decision

Do not create a separate release or execution tranche solely for this addendum. Include this authored ADR addendum in the bounded successor implementation tranche and bind the implementation review to its final SHA-256.

This keeps the new defect explicit without creating an additional ceremonial PR between design and implementation.

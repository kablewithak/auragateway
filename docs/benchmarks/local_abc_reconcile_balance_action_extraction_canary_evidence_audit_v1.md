# Local A/B/C Reconcile-Balance Action-Extraction Canary Evidence Audit

**Status:** Certified failed diagnostic with clean harness
**Audit fingerprint:** `8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd`
**Evidence archive SHA-256:** `412db1700b6505502ca9afc83981738c9f50f043bad6de37e015ab7f3a9944c8`
**Consumed authorization:** `9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9`
**GPU execution authorized:** No
**Cache claims permitted:** No
**Full measured benchmark authorized:** No

## Purpose

This audit freezes the completed twelve-request action-extraction canary without
rewriting its failed quality result. It binds the protected archive digest, all
eight member digests, source and notebook identities, runtime and model identity,
aggregate metrics, exact hash-resolved failures, privacy controls, runtime warnings,
and consumed authorization state.

This slice performs no model or GPU execution.

## Terminal boundary

```text
authorized_requests=12
completed_requests=12
http_200_responses=12
valid_action_json=12
valid_action_schema=12
exact_identity_matches=12
deterministic_execution_successes=12
exact_operand_matches=10
exact_final_answer_matches=10
semantic_failures=2
infrastructure_failures=0
hidden_retries=0
repairs=0
replacement_requests=0
cleanup_status=CLEAN
gate_decision=failed
```

The harness, transport, JSON, schema, identity, and deterministic-executor
boundaries passed. The terminal divergence occurred at semantic operand extraction.

## Hash-resolved failure disposition

### `formatted-currency-values`

```text
expected operands: opening_balance=1200, credits=300, debits=50
observed operands: opening_balance=200, credits=300, debits=50
expected answer: 1450
observed deterministic answer: 450
failure: FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
```

The retained canonical action and result hashes reproduce the exact observed action.

### `key-value-layout`

```text
expected operands: opening_balance=5000, credits=250, debits=1250
observed operands: opening_balance=5000, credits=1250, debits=250
expected answer: 4000
observed deterministic answer: 6000
failure: KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
```

The retained canonical action and result hashes reproduce the exact observed action.

## Evidence authority

The protected evidence archive is not committed by this slice. The typed verifier
accepts its local path and validates:

1. archive SHA-256;
2. ZIP integrity;
3. exact member order and membership;
4. all eight member SHA-256 values.

The ordinary unit suite validates the immutable bindings without requiring protected
evidence bytes.

## Runtime warning disposition

The following warnings remain follow-up debt but do not rewrite the clean harness
classification:

```text
NON_FATAL_ISOLATED_RUNTIME_SITECUSTOMIZE_WARNING
NON_FATAL_PROCESS_RESOURCE_WARNING
```

Both are explicitly marked non-fatal and non-blocking for evidence closure.

## Authorization lifecycle

The one-shot authorization is consumed because all twelve authorized requests
executed. The repository guard rejects its reuse with the stable failure code:

```text
ACTION_EXTRACTION_CANARY_AUTHORIZATION_CONSUMED
```

The failed cases may not be retried alone. Any future model execution requires a
versioned remediation, a complete fixed-suite gate, new artifact hashes, and a new
bounded authorization.

## Privacy and spend

```text
raw_prompt_retained=false
raw_output_retained=false
raw_action_retained=false
token_ids_retained=false
credentials_retained=false
customer_data_used=false
external_spend=0
```

## Next gate

```text
versioned_action_extraction_remediation_design
```

The next design must treat formatted-integer normalization and semantic field-role
binding as separate failure families.

## Non-claims

This audit does not claim:

- the action-extraction canary passed;
- schema validity guarantees semantic correctness;
- the extraction boundary is production-safe;
- cache savings were measured;
- the full A/B/C benchmark is authorized;
- local vLLM results generalize to hosted providers;
- AuraGateway is production-ready.

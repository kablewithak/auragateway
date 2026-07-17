# Local A/B/C Reconcile-Balance Action-Extraction Remediation v2

**Status:** Locally validated remediation candidate
**Date:** 2026-07-17
**Lifecycle transition:** `EVIDENCE_AUDIT_COMPLETED` → `QUALITY_REMEDIATION_LOCALLY_VALIDATED`
**Model execution:** None
**GPU execution:** Not authorized
**External spend:** R0 / $0
**Customer data:** None

## Purpose

This slice defines and locally validates the versioned intervention that follows the failed
12-request action-extraction canary. It does not run the model and does not issue a new authorization.

The intervention addresses two observed semantic failure families:

```text
FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
```

## Baseline

The immutable baseline remains:

```text
classification=CERTIFIED_FAILED_DIAGNOSTIC_WITH_CLEAN_HARNESS
completed_requests=12
valid_action_json=12
valid_action_schema=12
exact_operand_matches=10
exact_final_answer_matches=10
semantic_failures=2
infrastructure_failures=0
hidden_retries=0
repairs=0
replacement_requests=0
authorization_consumed=true
```

Baseline evidence audit:

```text
8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd
```

## Intervention boundary

### Deterministic integer lexical normalization

Supported transformations include:

```text
R1,200      → 1200
R 12,500    → 12500
1,000,000   → 1000000
R300        → 300
```

The normalizer does not:

```text
assign values to business fields
perform arithmetic
convert currencies
coerce decimals
repair model output
```

Example unsupported value preserved unchanged:

```text
R1,200.50 → R1,200.50
```

### Role-bound prompt policy

The v2 instruction requires values to be bound by explicit semantic labels rather than line order,
position, or numeric magnitude. It explicitly prohibits swapping credits and debits.

### Role-described response schema

The model-facing JSON Schema adds descriptions for `opening_balance`, `credits`, and `debits` while
preserving the existing strict `ReconcileBalanceAction` contract and deterministic executor.

## Case constitution

The v2 manifest preserves all 12 historical cases exactly and adds four hard diagnostics:

| Case | Failure pressure |
|---|---|
| `formatted-currency-multi-group` | Multiple grouping separators and currency markers |
| `formatted-currency-spaced-symbol` | Currency marker separated from integer |
| `key-value-credits-first-layout` | Credits first, asymmetric values |
| `key-value-mixed-delimiters` | Mixed delimiters and debits-first order |

Total fixed suite:

```text
historical_cases=12
added_diagnostic_cases=4
total_cases=16
```

## Local validation

The local test harness proves:

- exact artifact and policy fingerprints;
- deterministic currency and grouping normalization;
- decimal non-coercion;
- normalizer idempotence;
- no semantic field assignment by the normalizer;
- role descriptions in the response schema;
- explicit field-binding rules in the v2 prompt;
- exact preservation of all 12 historical cases;
- diagnostic coverage of both observed failure families;
- complete-suite enforcement;
- zero retries, repairs, and replacements;
- no semantic parser fallback;
- no model upgrade;
- no execution or GPU authorization;
- fail-closed artifact and historical-case drift detection.

## Fingerprints

```text
normalization_policy_sha256=7caa66d8bba36260fb97f822fdeea4f4badc16b1add1b5ed9eb5896be6257ef8
prompt_policy_sha256=750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c
response_schema_sha256=bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d
remediation_manifest_sha256=82037903ab9d944a88e6d1460a001a648308163ed7dae735cbf01359737ae4aa
remediation_plan_sha256=ebeb86b583eeff4f8b2c3ea973f67d6aaba1368a4386eb53737179ed3fd64a36
```

## Authorization boundary

```text
execution_authorized=false
gpu_execution_authorized=false
new_authorization_issued=false
failed_case_only_execution_permitted=false
cache_measurement_in_scope=false
cache_claims_permitted=false
full_measured_rerun_authorized=false
```

The next gate is:

```text
bounded_action_extraction_v2_authorization_review
```

A later authorization must bind the merged implementation, exact 16-case manifest, exact remediation
plan, exact prompt policy, exact normalization policy, response schema, model, runtime, notebook, and
one-attempt stop policy.

## Regression gate for future measured requalification

```text
action JSON validity        16/16
action schema validity      16/16
identity accuracy           16/16
operand accuracy            16/16
deterministic execution     16/16
final-answer accuracy       16/16
first-attempt task success  16/16
infrastructure failures     0
hidden retries              0
repairs                     0
replacement requests        0
cleanup                     CLEAN
```

## Non-claims

This slice does not establish:

- measured quality improvement;
- successful model extraction on the two historical failures;
- production-safe extraction;
- cache reuse or savings;
- authorization for another notebook run;
- eligibility for the full A/B/C benchmark;
- production readiness.

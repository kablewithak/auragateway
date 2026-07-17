# Action-Extraction v2 Traceability and Cleanup Hardening

**Version:** 1.0.0
**Date:** 2026-07-17
**Execution posture:** local-only, no authorization, no model request

## Source authority

```text
source_merge_commit=fe25c0869f62624247cc12bb97c5185586845f22
source_evidence_audit_sha256=a6a1031d85997d8b13b521866d580ce468579cfbb8d731180820fdcc5dd0be79
source_certificate_markdown_sha256=8c60ed9d47bc20e3e2f90edfc72a96b993a4bcb15912b70f8c1de5cedd3bc775
source_authorization_consumption_sha256=51b36a3ac4e6122c2cf9fa9e5132d26e57af101a19714cb4cd60c4c71afdff4f
```

## Audited defects

```text
STALE_SCORE_PROMPT_IDENTITY_METADATA
OVERSTATED_CLEANUP_STATUS
```

## Traceability intervention

The base evaluator now accepts an optional `ActionExtractionPromptIdentity` supplied by the caller.
Omitting it preserves the legacy v1 renderer and score behavior.

The v2 entry point performs this explicit flow:

```text
v2 lexical normalization
    -> v2 prompt rendering
    -> v2 hash-only prompt identity
    -> model output scoring
    -> score containing the executed v2 identity
```

The identity adapter carries:

```text
policy_sha256
source_prompt_sha256
source_prompt_character_count
rendered_prompt_sha256
rendered_prompt_character_count
```

The hardening module also supports local migration of the audited legacy score metadata. That migration:

- accepts only the exact audited legacy policy identity;
- requires case and expected-action identity agreement;
- changes only `prompt_identity`;
- preserves every measured score field;
- performs no model request and reuses no authorization.

## Cleanup intervention

Cleanup is no longer inferred from port closure alone.

### `CLEAN`

Requires all of:

```text
return_code=0
port_closed=true
application_shutdown_completed=true
forced_process_termination_count=0
leaked_semaphore_count=0
leaked_shared_memory_count=0
surviving_child_process_count=0
no SIGTERM or SIGKILL escalation
```

### `CLEAN_WITH_RUNTIME_WARNINGS`

Used when the worker reaches a safe terminal state but cleanup evidence includes forced termination or
resource-leak warnings.

### `FAILED`

Used when any hard terminal invariant fails, including a non-zero or missing return code, open port,
incomplete application shutdown, or surviving child process.

## Regression gate

The fixed tests prove:

- legacy scoring remains backward compatible;
- the v2 wrapper binds the active v2 policy and rendered-prompt hash;
- local score migration changes only prompt identity metadata;
- migration cannot be applied to unrelated or already hardened scores;
- port closure alone cannot produce a clean classification;
- forced termination and leaked semaphores produce warning-qualified cleanup;
- open ports, non-zero exits, incomplete shutdown, and surviving children fail cleanup;
- the plan binds the refreshed PR #92 audit lineage;
- no authorization or execution capability is introduced.

## Immutable plan identity

```text
hardening_plan_sha256=aa6a02dee2ceb039e61d13048075a3a0081777538b2c08277d4a381f2b5a47e3
```

## Safety boundary

```text
model_request_performed=false
gpu_execution_performed=false
provider_call_performed=false
credential_accessed=false
consumed_authorization_reused=false
new_authorization_issued=false
full_measured_rerun_authorized=false
customer_data_used=false
external_spend=0
```

## Next gate

```text
full_abc_harness_integration_design
```

The next slice must integrate these hardening entry points into the future measured A/B/C harness before
any new authorization review.

## Non-claims

- This slice does not rewrite the protected v2 evidence archive.
- This slice does not claim the historical nested score metadata was correct.
- This slice does not claim the historical shutdown was perfectly graceful.
- This slice does not execute a notebook or model.
- This slice does not authorize the full measured A/B/C benchmark.
- This slice does not establish production readiness.

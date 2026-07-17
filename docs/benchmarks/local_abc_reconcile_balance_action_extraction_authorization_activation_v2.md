# Local A/B/C Reconcile-Balance Action-Extraction Authorization Activation v2

**Version:** 2.0.0
**Date:** 2026-07-17
**State:** Active and unused
**Execution performed:** False
**GPU execution performed:** False
**External spend:** R0 / $0

## Decision

One fresh authorization is activated for the complete 16-case action-extraction requalification.
The authorization permits generation of a separately qualified notebook after merge. It does not
provide an execution command and does not permit GPU enablement before notebook hash binding.

```text
authorization_id=reconcile-balance-action-extraction-requalification-authorization-v2
status=active_unused
case_count=16
request_attempts_per_case=1
required_exact_operand_matches=16
required_exact_final_answer_matches=16
```

## Source authority

```text
PR #87 merge=6038f7055e34c6c559b3c41cb919d0cb421b3e55
review source blob=08a6dcd74ef6b569dc8e7de23cb1f7806e5350bc
review JSON blob=2982e1962825bf774cd092a3760d761d699b1ccf
dry-run JSON blob=333ad82078a128eebf3b570636c08f7eaa45d6ef
review manifest blob=afd97a0d1acad659db8dacfce42f8a5eb16b8890
```

The activation also binds:

```text
authorization_review_sha256=66539ccadbebee9ad6227b8d861da8bfa1f0e89fdd69883e91f49b15819c99a9
authorization_dry_run_sha256=207abb6746277b1f6bc4ca79d537de3623f06d66ca5fa8600ee391af45acf508
authorization_review_manifest_sha256=8299da7aaba1ed886d5bf85b9ee59c2471e79f735b1f37d66b9b8c3c806eee2d
```

## Activation artifact identities

```text
authorization_sha256=a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899
authorization_activation_manifest_sha256=42ce858a657afe0fd6d4eb7a5e0846fedf1b9c41ab883826acf08712a94b0526
```

## Execution controls

```text
active_authorization_created=true
authorization_consumed=false
execution_authorized=true
execution_command_available=false
notebook_generation_permitted_after_merge=true
notebook_sha256_binding_required=true
notebook_execution_permitted_before_binding=false
gpu_enablement_permitted_before_qualified_notebook=false
bounded_gpu_execution_permitted_after_qualified_notebook=true
```

The `execution_authorized` field means the governance authorization exists. It does not mean that
this PR performed a model call or that an unbound notebook may execute.

## Quality and stop policy

- All 16 cases must run in their frozen order.
- Exactly one request attempt is allowed per case.
- Semantic failures are retained and execution continues through the complete suite.
- Any source, model, runtime, worker, transport, or cleanup failure aborts the run.
- Hidden retries, repairs, replacement requests, direct model arithmetic, and deterministic semantic
  parser fallback remain prohibited.

## Evidence and privacy

The future evidence bundle may retain hashes, counts, failure codes, normalization counts, timing,
and token counts. It may not retain raw prompts, raw outputs, raw actions, token IDs, credentials,
PII, or customer data.

## Current non-claims

- No model request has been performed under this authorization.
- No GPU execution has occurred.
- No historical failed case has passed a new run.
- No measured quality improvement is claimed.
- No cache, latency, or cost effect is claimed.
- The full A/B/C benchmark remains unauthorized.
- AuraGateway is not production-ready.

## Next gate

```text
qualified_action_extraction_v2_notebook_generation
```

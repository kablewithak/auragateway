# Action-Extraction Requalification v2 Immutable Evidence Audit

**Version:** 2.0.0
**Date:** 2026-07-17
**Classification:** `CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS`

## Terminal result

```text
completed_requests=16/16
exact_operand_matches=16/16
exact_final_answer_matches=16/16
semantic_failures=0
infrastructure_failures=0
hidden_retries=0
repairs=0
replacement_requests=0
authorization_consumed=true
```

## Immutable identities

```text
evidence_archive_sha256=b7da2b703232154742665b47254e662a2e6ff4b6e198827e7d29f67dc9c16c93
evidence_archive_size_bytes=22767
notebook_sha256=e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9
authorization_sha256=a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899
audit_sha256=ce789b6e4510095d5b5f70ccfde71c5524b2847b05c5767dadb1704e2970a7a1
certificate_json_sha256=5f3477801f19e14743a621d48bd2a68ac5ced967ef15f9c00ca67a94421cc71e
certificate_markdown_sha256=6cb008ec1f39cb1578add5521e2b3e2390b6d9a732df6a5de479a90b0c1878e2
authorization_consumption_sha256=af39a09c974fb237976f3273a6f07323809b40edb2260a327a6187addf52d4c1
```

## Finding 1: stale score prompt identity

The frozen schedule and outer ledger bind the v2 prompt policy:

```text
750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c
```

All 16 nested score objects instead retain the legacy policy identity:

```text
5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9
```

Their source-prompt hashes remain correct, but their rendered-prompt hashes and character counts do
not match the actual v2 request evidence. This blocks a claim of perfect traceability. It does not
invalidate the quality result because the schedule, ledger, normalized prompt, rendered prompt, and
request-body hashes match across all 16 executed records.

## Finding 2: cleanup status overstated

The report records return code `0`, closed port `8001`, application shutdown, and cleanup status
`CLEAN`. The worker log also records:

```text
force killing remaining processes count=1
1 leaked semaphore objects
```

The audited classification is therefore:

```text
CLEAN_WITH_RUNTIME_WARNINGS
```

## Runtime warnings

- missing `wrapt` during `sitecustomize` import;
- bfloat16-to-float16 cast;
- eager mode disabling Torch compilation and CUDA graphs;
- deprecated CUDA Python module warnings;
- Triton JIT compilation during inference;
- forced termination of one remaining process;
- one leaked semaphore warning.

These warnings require hardening but do not constitute retained infrastructure failures for this
completed run.

## Evaluation digest note

The report binds the canonical JSON fingerprint of the evaluation payload:

```text
aac8cb14732b7e3019c0fccc2b8516df997682f973df4262683d70812b0c32fd
```

The raw evaluation file-byte SHA-256 differs because the evidence file includes formatting and a
trailing newline. The audit validates both the raw member digest and canonical payload digest.

## Authorization disposition

The v2 authorization is consumed. No notebook restart, failed-cell rerun, failed-case-only execution,
or replacement execution is permitted. The evidence archive remains outside Git.

## Next gate

```text
action_extraction_v2_traceability_cleanup_hardening
```

That slice must be local-only. It must correct score prompt-identity propagation and cleanup
classification semantics without issuing a model request or reusing this authorization.

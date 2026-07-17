# Semi-Formal Reasoning Certificate: Action-Extraction Requalification v2

**Certificate ID:** `AURAGATEWAY-LOCAL-ABC-SFRC-0004`
**Status:** `CERTIFIED_PASSED_WITH_TRACEABILITY_AND_RUNTIME_WARNINGS`
**Date:** 2026-07-17

## Premises

1. One fresh authorization permitted exactly 16 first-attempt synthetic requests.
2. The frozen notebook SHA-256 was
   `e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9`.
3. The evidence archive SHA-256 was
   `b7da2b703232154742665b47254e662a2e6ff4b6e198827e7d29f67dc9c16c93`.
4. Every request returned HTTP 200 and passed JSON, schema, identity, operand,
   deterministic execution, and final-answer checks.
5. No retry, repair, replacement request, failed-case-only execution, or direct
   model arithmetic fallback occurred.
6. The authorization was consumed by the completed run and cannot be reused.

## Trace

The schedule and outer ledger records bind the v2 prompt policy and the exact normalized,
rendered-prompt, and request-body hashes for all 16 cases. The nested score objects retain the
correct source-prompt identities but reuse the legacy prompt-policy and rendered-prompt metadata.
This is a traceability defect, not evidence that the model received the legacy prompt.

The report declares cleanup `CLEAN`, return code `0`, and a closed worker port. The worker log also
records forced termination of one remaining process and one leaked semaphore. Application shutdown
completed, so the run is retained as successful with runtime warnings rather than reclassified as an
infrastructure failure.

## Alternatives

- Reclassify the entire run as failed: rejected because the complete quality and execution evidence
  passed and the findings are metadata and cleanup-quality defects.
- Ignore the findings: rejected because it would overstate traceability and cleanup quality.
- Rerun the experiment: rejected because the one-shot authorization is consumed and the findings do
  not require another model execution.

## Resolution

The action-extraction v2 quality gate is certified as passed at 16/16 exact operands and 16/16 exact
final answers. The evidence is classified as passed with traceability and runtime warnings. No rerun
is permitted. The next gate is local harness hardening for score prompt-identity propagation and
cleanup classification before full A/B/C authorization review.

## Non-Claims

- This certificate does not claim perfect traceability metadata.
- This certificate does not claim perfectly graceful vLLM shutdown.
- This certificate does not measure cache reuse, latency savings, or cost savings.
- This certificate does not authorize the full measured A/B/C benchmark.
- This certificate does not establish production readiness.

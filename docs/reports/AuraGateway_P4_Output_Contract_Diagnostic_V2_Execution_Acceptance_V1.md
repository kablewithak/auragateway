# AuraGateway P4 Output-Contract Diagnostic V2 Execution Acceptance V1

## Accepted execution

Kaggle saved version `340775383` completed the governed P4 V2 diagnostic successfully.

- execution outcome: `PASSED`
- first divergence: none
- model requests: `18`
- selected case: `A`
- eligible cases: `A`, `C`, `E`, `F`
- ineligible cases: `B`, `D`
- V3 authorization lifecycle: consumed and non-reusable
- measured A/B/C execution: not performed and not authorized

## Case evidence

A and C passed without schema enforcement. E and F passed with `JSON_SCHEMA`. B and D
completed with HTTP 200 but returned markdown-fenced invalid JSON in every observation.

Case A is selected because it satisfies the exact-object criterion under the least
constraining eligible configuration.

## Runtime evidence

The hash-locked offline install, import closure, required target-native origin checks,
TRITON_ATTN worker realization, teardown, and scratch cleanup all passed.

The acceptance does not claim that every CUDA library originated from the target
runtime. The evidence includes an ambient CUDA runtime library that was not prohibited
by the reviewed contract.

## Non-claims

This is one governed diagnostic saved version with three observations per case. It does
not establish general model reliability, cross-run stability, deployment readiness,
production readiness, or measured A/B/C performance.

## Next gate

Design and merge a separate measured A/B/C execution authorization.

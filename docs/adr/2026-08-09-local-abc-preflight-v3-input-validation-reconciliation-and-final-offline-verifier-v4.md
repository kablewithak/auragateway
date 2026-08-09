# ADR: Preflight V3 input-validation reconciliation and final offline verifier V4

Date: 2026-08-09
Status: Proposed for repository acceptance
Base main: `138ac906d0bc0179af3cbf207d8cb7c1d1d7f8bc`

## Context

Governed saved version `341197546` executed final offline verifier V3 once under a consumed
single-use authorization. The verifier terminated `FAILED_PENDING_REVIEW` at `input_validation`
before target creation or package installation. The exact failure was
`materialization receipt drifted: controlled_python_startup_required`.

The historical materialization receipt is immutable and has SHA-256
`55bc8d078af9960d5f6a60bf7d9638820be9fdda0ee76754a9462d46eb053fe0`.
It was produced before the verifier-reconciliation policy introduced
`controlled_python_startup_required`, `native_loader_provenance_required`, and
`successful_native_import_alone_sufficient`.

V3 therefore imposed an impossible conjunction: preserve the exact historical receipt bytes while
also requiring those bytes to contain later consumer-policy fields.

## Decision

1. Preserve V3, its execution authorization, its consumed receipt, and saved version `341197546`
   as immutable diagnostic evidence.
2. Classify the V3 failure as `DIAGNOSTIC_HARNESS_DEFECT` with failure code
   `BACKPROJECTED_UPSTREAM_RECEIPT_SEMANTIC_REQUIREMENT`.
3. Do not mutate V3 in place. Introduce V4 as the successor verifier.
4. Split evidence ownership:
   - historical materializer receipt validates only facts emitted by the materializer;
   - current verifier policy owns controlled-startup, loader-provenance, and native-import
     sufficiency requirements.
5. Require the exact repository copy of the historical materialization receipt to replay
   successfully through the V4 pre-execution contract gate.
6. Reject historical receipt back-projection: consumer-owned policy fields are not permitted
   in the historical producer receipt.
7. Preserve the V3 native capability contract unchanged: exact 196-wheel offline install,
   controlled Python startup, `_C_stable_libtorch`, static linker provenance, dynamic
   `/proc/self/maps` provenance, real NVIDIA driver origin, no CUDA stubs, no model/worker/request.
8. V4 implementation remains non-authorizing. A new single-use authorization issuer is a
   separate future tranche.

## Evidence

V3 saved version: `341197546`

- executed notebook SHA-256:
  `d4982f95b1a061eb8e810d1a1dcce99076bc6bd006ef1cd637bc2e288818bf07`
- execution log SHA-256:
  `332c2918674d3c587c1b6d6e4d02f3d6a7ed813a78cedaf8f46c8d1367790013`
- evidence ZIP SHA-256:
  `e4721b2ba1fd91f96370b90e6c839e13d8982f362af435080f073d5847dadcc5`
- consumed authorization receipt SHA-256:
  `5a0fd520e2df11b25105dbabc4ddd1809e27af378c3d0fb8db7990809e08d9a8`

The run proves no runtime incompatibility: package installation never started and native capability
was never tested.

## Consequences

The next external GPU run is prohibited until:

- V4 source/notebook/tests/docs are repository accepted;
- the exact historical receipt replay regression passes;
- `validate-preexecution-contract` passes on merged main;
- a new V4-specific single-use authorization issuer is implemented and merged;
- fresh T4 x2 / Internet OFF observation is performed.

## Non-claims

This ADR does not establish exact-runtime compatibility, P5/P6 qualification, cache qualification,
pilot eligibility, measured A/B/C eligibility, or production readiness.

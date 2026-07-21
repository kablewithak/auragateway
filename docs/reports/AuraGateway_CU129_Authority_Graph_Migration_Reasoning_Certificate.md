# AuraGateway CUDA 12.9 Authority-Graph Migration Failure
## Semi-Formal Reasoning Certificate

**Certificate ID:** `auragateway-cu129-authority-graph-migration-failure-v1`
**Status:** `FIRST_DIVERGENCE_PROVEN_REMEDIATION_SCOPE_REBUILT`
**Scope:** Repository-local CUDA 12.9 qualification runtime integration
**Execution authority created:** No

## 1. Definitions

**D1 — Current runtime integration**

The current implementation slice replaces the historical single-wheel runtime with the
governed CUDA 12.9 wheelhouse and updates the live launcher, adapter, dataset contracts,
runtime manifest, worker plan, notebooks, and execution requests.

**D2 — Authority graph**

The authority graph is the transitive set of repository files that bind an executable or
generated artifact identity:

- typed source contracts;
- generated JSON authorities;
- raw-file SHA-256 constants;
- semantic fingerprints;
- Git blob bindings;
- source-authority rows;
- historical review validators;
- tests that assert those bindings.

**D3 — Complete authority migration**

A migration is complete only when every current-state consumer of a changed authority is
either:

1. regenerated to the new authority;
2. explicitly classified as historical and validated against its historical revision; or
3. intentionally superseded with a tested disposition.

Changing a producer while leaving a current-state consumer hard-bound to the previous
identity is an incomplete migration.

## 2. Source Evidence

- Full repository result: `7 failed, 2019 passed`.
- Mypy result: `Success: no issues found in 439 source files`.
- Ruff result: `All checks passed`.
- Current runtime integration review artifact approves the wheelhouse migration.
- Current failure traces name exact stale identity consumers.
- The rematerialization source on merged `main` still binds:
  - `vllm_wheel`;
  - `python_wheel`;
  - runtime-manifest raw SHA-256
    `9ffd335fad6ac660782be7881625a1fb99a39f5d4a1446f31504154634c91eb7`;
  - materialization-record SHA-256
    `8a0f41def6b3e4e8a34713e4cd9c3023d03619d51a62a2e7ec34da0bcc2f52c0`.

## 3. Premises

**P1.** The new live contracts accept `vllm_runtime` and
`python_wheelhouse_directory`.

**P2.** The new live manifest and execution requests changed identity.

**P3.** The pre-integration review validator hashes the live launcher, adapter, contracts,
manifest, and worker plan and requires them to remain in the old state.

**P4.** After a successful integration, those live files must no longer match the
pre-integration snapshot.

**P5.** The execution package validator binds exact request and source-authority
identities.

**P6.** The authorization issuance and issuance-review modules bind exact execution
request, materialization record, runtime manifest, adapter, and Git identities.

**P7.** The harness-rematerialization module still models the runtime as an unchanged
single wheel and compares the live files to old raw hashes.

**P8.** The materialization record was written with a trailing newline, while the
repository canonical-JSON test requires a single line with no trailing newline.

**P9.** Mypy and Ruff pass, so the observed failures are not typing or lint defects.

## 4. Failure Trace

### F1 — Pre-integration review test

Observed:
`captured pre-integration authority drifted: ...kaggle_launcher.py`

Trace:

1. Review validator stores pre-integration hashes.
2. Runtime integration intentionally changes the launcher.
3. Test executes the historical validator against current working-tree files.
4. Hash mismatch occurs.

Classification:
`HISTORICAL_VALIDATOR_APPLIED_TO_CURRENT_STATE`

### F2 — Execution package generation

Observed:
`one or more qualification-execution authorities drifted`

Trace:

1. Runtime integration changes execution request and authority-producing files.
2. Execution package validates exact authority identities.
3. One or more dependent authority rows or generated artifacts remain old.
4. Package validation fails closed.

Classification:
`TRANSITIVE_EXECUTION_AUTHORITY_NOT_REGENERATED`

### F3 — Authorization issuance

Observed:
`the execution request identity drifted`

Trace:

1. Runtime integration changes `qualification_execution_request.json`.
2. Issuance module retains the previous request SHA-256.
3. Builder compares current request to old identity.
4. Issuance test fails before any authorization is created.

Classification:
`STALE_ISSUANCE_INPUT_IDENTITY`

### F4 — Authorization issuance review

Observed:
`one or more issuance-review authorities failed contract validation`

Trace:

1. Issuance review is an exact PR-109 authority package.
2. Current execution request, materialization record, runtime manifest, and adapter
   changed.
3. Review still validates old exact identities as current.
4. Typed review validation fails.

Classification:
`HISTORICAL_ISSUANCE_REVIEW_NOT_SUPERSEDED_OR_REGENERATED`

### F5/F6 — Harness rematerialization

Observed:

- `the rematerialized runtime manifest identity drifted`;
- expected old manifest hash, observed new manifest fingerprint.

Trace:

1. Rematerialization source still defines `_VLLM_ENTRY` as `vllm_wheel`.
2. It still requires old runtime-manifest and materialization-record hashes.
3. Live files now describe the wheelhouse runtime.
4. Exact-binding and raw-hash checks fail.

Classification:
`REMATERIALIZATION_AUTHORITY_MODEL_NOT_MIGRATED`

### F7 — Canonical JSON

Observed:
canonical JSON differs only by one trailing newline.

Classification:
`NONCANONICAL_TRAILING_NEWLINE`

## 5. Competing Explanations

### H1 — The CUDA 12.9 runtime implementation is semantically invalid

Prediction:
Focused runtime behavior, typed validation, or static policy tests would fail broadly.

Evidence:
Focused implementation gates passed; mypy and Ruff pass; failures are exact authority
and historical-state assertions.

Disposition:
`NOT SUPPORTED BY CURRENT EVIDENCE`.

### H2 — Only the materialization record needs correction

Prediction:
After correcting that record, the full suite should pass.

Evidence:
Seven failures remain across review, execution, issuance, issuance review, and
rematerialization consumers.

Disposition:
`REFUTED`.

### H3 — The failing tests should be deleted or weakened

Prediction:
The tests assert obsolete behavior with no provenance value.

Evidence:
Most tests protect real current authority boundaries. Only the pre-integration test is
misapplied to current files; it still has historical value and needs a supersession-aware
contract rather than deletion.

Disposition:
`REFUTED`.

### H4 — Manually replace individual hashes until green

Prediction:
Each failure is independent and can be corrected locally.

Evidence:
The same producers feed multiple generated artifacts and source-authority rows. Manual
hash replacement risks internally inconsistent authorities and another downstream failure.

Disposition:
`REJECTED AS BRITTLE`.

### H5 — The original implementation package omitted transitive authority consumers

Prediction:
Direct runtime tests pass, while the full suite fails at historical and downstream
identity bindings.

Evidence:
Exactly observed.

Disposition:
`SUPPORTED`.

## 6. First Divergence

**CLAIM DVG1:** The first divergence occurred during implementation-scope enumeration.

The package treated the runtime integration as a 26-file direct dependency change.
The repository implements an identity meta-harness in which those direct files are
consumed by historical reviews, rematerialization records, execution packages, issuance
builders, issuance reviews, and exact authority tests.

The package therefore changed producers without migrating or superseding all consumers.

**Failure code:**
`INCOMPLETE_TRANSITIVE_AUTHORITY_GRAPH_MIGRATION`

## 7. Selected Resolution

Do not issue another single-file correction.

Build one bounded authority-graph migration package from the exact current branch that:

1. inventories every consumer of the changed manifest, materialization record,
   execution request, launcher, adapter, contracts, and worker plan;
2. regenerates current execution and authorization-input authorities;
3. retains the harness-rematerialization package as historical evidence and loads its
   single-wheel authorities from their actual merge revision instead of comparing them
   with current live files;
4. rewrites canonical JSON with no trailing newline;
5. converts the pre-integration review into a supersession-aware historical validator
   rather than comparing its hashes to current files;
6. retains PR 109 as historical authority and blocks fresh issuance until a separate
   CUDA 12.9 authorization review is merged;
7. adds a regression that traverses the authority graph and proves no current consumer
   references the retired runtime role, format, version, or hashes.

## 8. Why a Rerun Is Not Justified

No Kaggle, GPU, loader, package-installation, model, or worker fact is missing.

The failures are fully explained by repository source and exact identity checks.

A Kaggle rerun would produce no information about this repository authority-graph defect.

## 9. Claims

Supported:

- the seven failures share one upstream scope defect;
- no operational authorization was issued;
- current validators failed closed;
- the repository requires an authority-graph migration, not another runtime experiment;
- the materialization JSON newline is a real but downstream formatting defect.

## 10. Non-Claims

Not supported:

- the full CUDA 12.9 integration is repository-valid;
- the current branch is ready to commit;
- the new issuance review identities are known without inspecting the exact branch;
- environment qualification has occurred;
- model or worker qualification has occurred;
- measured A/B/C execution is authorized;
- production readiness.

## 11. Regression Requirements

The remediation is accepted only when:

1. all current JSON authorities are canonical single-line files with no trailing newline;
2. no current authority contains `vllm_wheel`, `python_wheel`, or vLLM `0.25.1`;
3. current execution request and source-authority identities are regenerated
   deterministically;
4. current issuance inputs bind the wheelhouse manifest and materialization record;
5. historical review artifacts remain queryable but are not validated against current
   live files;
6. harness rematerialization remains queryable at its historical revision without
   being treated as current wheelhouse authority;
7. full pytest, full mypy, full Ruff, and changed-file format gates pass;
8. authorization remains absent;
9. zero Kaggle sessions, model loads, workers, and model requests occur.


## 12. Historical Revision Correction

The harness source provenance commit and the repository artifact commit are distinct:

- harness source provenance: `be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50`;
- rematerialization authority merge: `84ab2634f548cc60d8aaeef31cdf4fd1e227ad73`.

The refreshed historical manifest and materialization record must be loaded from the
rematerialization authority merge. Their embedded harness source continues to bind the
`be1bfad...` provenance commit. Conflating these revisions is invalid because the
refreshed artifacts did not yet exist at the provenance commit.

## 13. Final Repository Resolution

The inspected branch supports a strict historical/current split:

- the pre-integration review remains historical at `daa8df9`;
- the PR 109 issuance review remains historical at
  `58e448228abcf9b83e1a6d165094bbec61dcf02c`;
- the rematerialized harness artifacts remain historical at
  `84ab2634f548cc60d8aaeef31cdf4fd1e227ad73`;
- the embedded harness source provenance remains
  `be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50`;
- current execution authorities bind working-tree bytes through `git hash-object
  --path` during the pre-commit package gate;
- current CUDA 12.9 issuance remains blocked with
  `FRESH_CU129_AUTHORIZATION_REVIEW_REQUIRED`;
- the current authority-graph validator invokes each historical validator at its proper
  revision and separately validates the live wheelhouse authorities.

This resolution preserves evidence instead of rewriting it and prevents historical
single-wheel facts from being mistaken for current operational authority.

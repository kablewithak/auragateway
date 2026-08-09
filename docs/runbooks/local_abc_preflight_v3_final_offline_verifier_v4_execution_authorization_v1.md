# Runbook: final offline verifier V4 single-use execution authorization V1

## Purpose

Provide a repository-owned issuer for exactly one later governed Kaggle execution of the accepted
Final Offline Verifier V4.

Merging this issuer does not itself create live execution authority.

## Bound V4 implementation

- feature commit: `ed155dc32716041b333dd05d7244b4e19e23f9dd`
- merge commit: `0fbc2430751502b46cdf5494a483e91713e059be`
- notebook SHA-256: `db4725b508322948ca4a9c29a48283f83ab047873a3eadb530e9f32e6a5490e9`

The issuer binds all eight repository-accepted V4 implementation artifacts.

## Pre-execution compatibility gate

Every live authorization issuance must first re-run both:

`validate-implementation`

and:

`validate-preexecution-contract`

for V4 against the current clean synchronized `main`.

Required V4 pre-execution result:

`PREFLIGHT_V3_V4_PREEXECUTION_CONTRACT_VALID`

The gate must preserve:

- historical receipt back-projection prohibited;
- runtime execution not yet authorized by the V4 implementation;
- next expensive execution not yet permitted by the V4 implementation.

Only after these checks pass may the issuer create transient V4 execution authority.

## Live authority ceiling

One live authorization permits at most:

- one Kaggle session;
- one offline runtime installation attempt;
- one native import closure probe sequence.

It permits zero:

- model loads;
- worker starts;
- model requests;
- benchmark trajectories;
- external network requests;
- hidden retries;
- external spend.

Default lifetime: 180 minutes.
Maximum lifetime: 240 minutes.

## Operator observation

Immediately before issuance, the operator must freshly observe:

- Kaggle accelerator: `GPU T4 x2`;
- GPU count: `2`;
- Internet: `OFF`;
- correct accepted wheelhouse input;
- V4 notebook title: `ag-preflight-v3-final-offline-verifier-v4`.

Exact confirmation phrase:

`I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_FINAL_OFFLINE_VERIFIER_V4_EXECUTION`

## Expected output

`auragateway_preflight_v3_exact_runtime_offline_compatibility_evidence_v4.zip`

with exactly:

- `input_validation.json`
- `probe_records.json`
- `verification_summary.json`
- `evidence_manifest.json`

## Single-use lifecycle

Terminal execution outcomes:

- `PASSED`
- `FAILED`
- `INTERRUPTED`

Unused authority may be terminally `ABANDONED`.

A terminal authorization is never reusable. No hidden retry is permitted.

## Repository policy

The live authorization, consumption receipt, and abandonment receipt are transient operational files.
Do not package them into the issuer PR.

## Non-claims

The issuer does not establish runtime compatibility, native compatibility, P5/P6 requalification,
pilot eligibility, measured A/B/C eligibility, or production readiness.

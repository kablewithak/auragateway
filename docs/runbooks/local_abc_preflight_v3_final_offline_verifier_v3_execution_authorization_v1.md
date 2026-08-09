# Local A/B/C Preflight V3 Final Offline Verifier V3 Execution Authorization V1

## Purpose

This runbook governs one bounded execution of the repository-accepted final offline verifier V3.

The authorization issuer is repository authority. The live authorization is transient operator authority.
Merging the issuer does not authorize execution.

## Bound implementation

- implementation feature commit:
  `7a1c97e6c37631739a6fb1dbd306d41c91ccd9e3`
- implementation merge commit:
  `51402a453e1dcd84ff5933a04c37c77c40d9f603`
- notebook SHA-256:
  `c12d0709d78b0491910a7e989b89ff1ecb69c82971df442ccebefc8fcb3e1469`
- required native capability:
  `vllm._C_stable_libtorch`

Any drift requires a new issuer.

## Issuance preconditions

Before issuance:

1. issuer PR is merged;
2. local branch is `main`;
3. `HEAD == origin/main`;
4. working tree and index are clean;
5. bound implementation merge is an ancestor of issuer `main`;
6. all eight V3 implementation artifacts match their exact SHA-256 and size;
7. no authorization, consumption, or abandonment artifact exists;
8. operator freshly observes Kaggle `T4 x2`;
9. Kaggle internet is disabled;
10. execution will start immediately within the authorization window.

## Hard ceiling

The live authority permits exactly:

- one Kaggle session;
- one offline runtime installation attempt;
- one native import-closure probe sequence.

It permits zero:

- model loads;
- worker starts;
- model requests;
- benchmark trajectories;
- external network requests;
- hidden retries;
- external spend.

The verifier notebook must stop before P5/P6, pilot, or measured A/B/C.

## Transient files

Live authorization:

`benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_offline_compatibility_v3_execution_authorization_v1.json`

Terminal consumption:

`benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_offline_compatibility_v3_execution_authorization_consumption_v1.json`

Pre-execution abandonment:

`benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_offline_compatibility_v3_execution_authorization_abandonment_v1.json`

These are operational lifecycle artifacts. They are not part of the issuer implementation commit.

## Runtime enforcement boundary

The repository issuer validates and records the operator gate.

The notebook is not claimed to parse the transient authorization file.
Therefore operator procedure remains part of the enforcement boundary:

1. validate the live authorization immediately before execution;
2. execute only the exact bound notebook;
3. do not modify notebook code after issuance;
4. execute exactly one saved-version attempt;
5. stop on the first terminal outcome;
6. do not retry under the same authorization;
7. preserve the saved version and evidence ZIP;
8. consume the authorization as `PASSED`, `FAILED`, or `INTERRUPTED`.

## Expected evidence

The notebook must produce an evidence ZIP named:

`auragateway_preflight_v3_exact_runtime_offline_compatibility_evidence_v3.zip`

with exactly these members:

- `input_validation.json`
- `probe_records.json`
- `verification_summary.json`
- `evidence_manifest.json`

A successful technical verifier result is still pending repository acceptance.

## Terminal handling

### PASSED

Preserve:

- Kaggle saved-version ID;
- complete notebook execution state;
- evidence ZIP;
- evidence ZIP SHA-256;
- consumption receipt.

Then enter evidence acceptance. Do not start P5/P6 yet.

### FAILED

Preserve the same artifacts and consume the authority as `FAILED`.
Do not retry. Classify the first divergence before any new execution.

### INTERRUPTED

Consume the authority as `INTERRUPTED`.
Preserve all partial evidence available.
Do not silently issue a replacement authorization.

### Cancel before execution

Create an abandonment receipt. Do not delete the live authorization as if it never existed.

## Non-claims

Issuer merge does not prove runtime compatibility.
Live authorization does not prove runtime compatibility.
Verifier technical PASS does not itself qualify exact-runtime P5/P6.
No pilot or measured A/B/C authorization is granted here.

# AuraGateway Schema-Constrained Output Probe Remediation v1

## Lifecycle decision

The six-request measured-quality canary failed on its first request.

The failure archive remains immutable diagnostic evidence. The six-request
cache canary and the 72-trajectory measured benchmark remain unauthorized.

## Failed canary evidence

- Archive SHA-256:
  `15ad148cb3eb3d3939ae5ae80168905ec75ad2c2a295b0d2333b4e00de49b72e`
- Canonical report SHA-256:
  `7614651830f02277c6bda2154a1181f942a938e229f422756befabb3481e7022`
- Ledger SHA-256:
  `d68adce2ac1ae0c78b92b03af6dff72af7a4d5275829e871637d883b21e2aed6`
- Evaluation SHA-256:
  `c0163a62a868cd7e843a33d513e3b37b75dfb6610f12d2b72683a1ecab33df53`
- Audit fingerprint:
  `6b403f4fe75ed530dbf733b62443504197ecfe3457df51abb5eccf620cb2bcd2`

## Observed divergence

The first incident-severity request returned HTTP 200 with:

- 282 prompt tokens;
- 110 completion tokens;
- 551 output characters;
- finish reason `stop`;
- valid telemetry;
- no route mismatch;
- clean worker shutdown.

The output did not parse as JSON. The raw output was intentionally not
retained, so no finer structural claim is permitted from that archive.

## Taxonomy correction

Parse failure now emits `OUTPUT_JSON_INVALID` without inventing answer,
case-ID, confidence, key-set, turn-index, or trailing-text mismatches.

The score also records a metadata-only structural shape:

- empty;
- JSON object;
- JSON non-object;
- Markdown fence;
- leading text;
- malformed JSON;
- multiple JSON values;
- trailing text;
- other non-JSON text.

## Trajectory propagation

A failed turn now produces a typed trajectory-level failure envelope with:

- failed turn index;
- structural output shape;
- canonical failure codes;
- `FAILED_RETAINED`;
- task incomplete;
- comparison ineligible.

## Checkpoint correction

The schema probe uses a terminal-aware checkpoint contract. A passed or
failed request must be terminalized before serialization. A terminal
checkpoint cannot retain `RUNNING`.

## Authorized capability probe

Authorization fingerprint:

`d8066307c9bb327dbe5bd7d61e7b8c33ff352bd7e4ee50bc3d1fdd6f26dc7f6e`

The next Kaggle run is limited to one request:

- incident-severity, turn one;
- worker 1 only;
- full worker restart;
- `/v1/chat/completions`;
- JSON Schema response format;
- deterministic decoding;
- 128 output tokens;
- exact answer `sev3`;
- all seven quality checks;
- zero retries;
- zero replacement requests;
- no cache-reuse evaluation;
- no raw prompt or raw output retention;
- zero external spend.

The JSON Schema constrains structure and metadata while leaving the severity
answer as one of `sev1`, `sev2`, `sev3`, or `sev4`. The deterministic scorer
must still verify that the model selected `sev3`.

## Promotion rule

A passing one-request probe does not authorize the six-request canary.

It permits a new canary authorization package that must bind:

- the schema-constrained chat endpoint;
- exact response schema identity;
- corrected quality taxonomy;
- trajectory failure propagation;
- terminal checkpoint ordering;
- positive turn-two cache reuse.

## Non-claims

This slice does not claim:

- that the schema probe has executed;
- that constrained decoding preserves semantic accuracy;
- that the six-request canary is authorized;
- that the 72-trajectory benchmark is authorized;
- production readiness;
- hosted-provider behavior;
- customer-data performance.

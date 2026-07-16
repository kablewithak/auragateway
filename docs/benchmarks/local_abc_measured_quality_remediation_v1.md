# AuraGateway Local A/B/C Measured Quality Remediation v1

## Decision

The first 72-trajectory measured execution remains immutable diagnostic evidence.

It is not accepted as a quality-preserving A/B/C benchmark because all 144 outputs
failed the deterministic quality rubric while the notebook still marked all 72
trajectories comparison eligible.

## Evidence audit

- Evidence archive SHA-256:
  `f403cd5b9b78637ace90dbed23ab627ec055a364563482849cd033eedf8e9fb3`
- Canonical report SHA-256:
  `c254475233c6c1248b03a176eb4e02384c1191f6449cf0a8ecc749e98d9e2aac`
- Analysis SHA-256:
  `9255ab37591fe442cfe5b1f9a751dc7780c1778912c997e5dfc8c7d91a7baf57`
- Trajectory ledger SHA-256:
  `b6ef550dc29c7b5a871685d4d2d8db541ede0a364506753dab57afd56c0c3acb`
- Audit fingerprint:
  `f4b458f18e1ff304b0000897af4bf33fc79c1e270766bc61b59e5a1901bd780e`

## Accepted v1 evidence scope

The following remains valid within the pinned Kaggle T4 x2 environment:

- 72 of 72 trajectories executed;
- 144 of 144 requests returned HTTP 200;
- zero operational trajectory failures;
- zero route-realization mismatches;
- zero invalid telemetry records;
- condition C reused 176 turn-two prefix tokens in all 24 paired cases;
- condition A and B reused zero turn-two prefix tokens;
- the primary C-minus-B cache and latency contrast favored C in 24 of 24 pairs;
- worker cleanup and privacy controls passed.

## Rejected v1 conclusion

The following is not accepted:

`MEASURED_LOCAL_ABC_RUN_COMPLETED` as an end-to-end quality-preserving result.

Corrected lifecycle classification:

`DIAGNOSTIC_ONLY`

## Root defects

1. `QUALITY_FAILURE_NOT_PROPAGATED_TO_ELIGIBILITY`
2. `RAW_INSTRUCT_TRANSPORT_NOT_QUALIFIED`
3. `NEGATIVE_CONTROL_TOKEN_LENGTH_CONFOUNDED`

## Quality boundary remediation

`measured_quality.py` now:

- parses one model output deterministically;
- checks the exact key set;
- checks answer, case ID, turn index, and confidence;
- rejects any trailing text;
- records output hash and length without retaining raw output;
- maps every failure to the stable Local A/B/C taxonomy;
- makes output quality a hard comparison-eligibility boundary;
- classifies a quality failure as `FAILED_RETAINED`.

An HTTP 200 and valid telemetry are no longer sufficient for eligibility.

## Transport remediation

`measured_transport.py` requires the frozen Qwen chat template:

- one transient user message containing the compiled prompt;
- `add_generation_prompt=true`;
- deterministic decoding;
- output budget 128 tokens;
- no raw prompt logging;
- metadata-only prompt lineage.

The raw completion transport used by v1 is not reused.

## Canary authorization

Canary fingerprint:

`ae4657143927fff0594c1cc0766ef8927d8bd603dec3a0b939c1d8003956fdf0`

The next Kaggle run is limited to:

- 3 cases;
- condition C only;
- 2 turns per case;
- 3 trajectories;
- 6 requests;
- full worker restart before each trajectory;
- 100% pass rate across all seven quality checks;
- positive turn-two cached tokens;
- zero trajectory failures;
- no hidden retries;
- no replacement trajectories;
- zero external spend.

## Promotion rule

Passing the canary does not authorize the full 72-trajectory rerun.

A successful canary permits a new measured-execution authorization package that
must re-freeze:

- chat-template transport identity;
- rendered prefix identities;
- token counts;
- output budget;
- corrected quality-gated eligibility;
- a token-length-matched negative control;
- cases, condition order, abort policy, and analysis plan.

## Non-claims

This remediation does not claim:

- that the canary has executed;
- that output quality is fixed;
- that the full measured rerun is authorized;
- production readiness;
- hosted-provider behavior;
- concurrency or load readiness;
- customer-data performance.

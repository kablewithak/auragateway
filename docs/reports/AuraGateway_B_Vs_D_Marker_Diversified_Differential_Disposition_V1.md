# AuraGateway B-vs-D Marker-Diversified Differential Disposition V1

## Decision

Accept and preserve the governed diagnostic as:

`MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK`

The frozen 899-token comparison produced:

- `B_NEUTRAL_REPEATED_24X`: 0/3 exact-object responses
- `D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED`: 3/3 exact-object responses
- valid JSON counts: B=0/3, D=3/3
- fresh worker process per observation: true
- worker identity cardinality: 6
- request order: B, D, D, B, B, D
- zero-cache baseline before each observation: true

The historical B anchor reproduced exactly. Under the predeclared decision table,
the B=0/3 and D=3/3 branch permits the bounded classification above.

## Governed execution

- transaction:
  `75860f22287511bafba2bcf42be16214ef8b41a6260857fe258596aaab5d69d1`
- issuer merge commit:
  `f142fe3e94984ced197b836c7fae477b0d71eecb`
- Kaggle saved version:
  `343074095`
- terminal disposition:
  `CONSUMED`
- terminal execution outcome:
  `PASSED`
- model requests: 6/6
- model loads: 6/6
- worker starts: 6/6
- hidden retries: 0
- replacement observations: 0
- external network requests: 0
- external spend: 0
- teardown: PASS
- scratch cleanup: PASS

The consumed authorization is not reusable. Unchanged replay is unauthorized.

## Evidence custody

Byte-exact governed evidence is preserved under:

`evidence_vault/local_abc/b-vs-d-marker-diversified-diff-v1`

Key identities:

- custody manifest:
  `d9e263ada8b03f5e77c87d91d44a28c463f68368d0cf4ca90e30df6b61f57ab2`
- governed evidence ZIP:
  `4661552364736621338249e6a21d0cacfbd355ba04e57432943cf721fc40e0f0`
- outer Kaggle results ZIP:
  `6d6313e87f3ffc1df803b4507f94fbc53d1628e83c0e8b42d074c3bf38a4f71c`
- terminal log:
  `fa88a9c4de4476e4a3daf359d8d4fb2b24b874a96ea9e2daeb9417513f1a0e32`
- saved notebook:
  `1913d9ed109db8360924dc1f3343aaae076259a5b071466ced134fc29b8e3eb7`
- execution authorization:
  `df538079793052bf4af9e569c9209df79ab9e0a7d36e169d68ffaee33bce912c`
- execution artifact manifest:
  `4ffee8262a8b6687cc34169f9d80a7a20bed0768542b88bb9cf6e4e2d6871838`
- platform observation receipt:
  `eada301361f9623e7af0d5dadd20c40087c14c3e8ffa672568aedae00fcddcd7`
- terminal receipt:
  `30ddc5b08bc304a6ea9463e06c6c2afd26e5a4e9a9e0eb8a0a97576692c2b946`

The outer Kaggle results ZIP is intentionally preserved in addition to the inner
governed evidence ZIP. It carries the transaction-bound admission record and the
wrapper-level primary-failure artifact needed to diagnose the reporting defect
without rewriting or discarding the scientific evidence.

## Wrapper reporting defect

The saved notebook preserves two facts in the same governed execution:

1. the runtime emitted a complete diagnostic summary with the accepted B-vs-D
   decision and all six scheduled requests completed; and
2. the transaction-bound wrapper then surfaced `SystemExit(0)` as a notebook
   error artifact.

The outer Kaggle results ZIP independently preserves:

- `status=PRIMARY_FAILURE_CAPTURED`
- `exception_type=SystemExit`
- `safe_message=0`

This is dispositioned as:

`CONTROL_PLANE_ZERO_EXIT_SYSTEMEXIT_FALSE_POSITIVE`

The zero exit did not represent a failed model request, failed worker lifecycle,
failed evidence bundle, or failed scientific decision. It is therefore treated
as a control-plane reporting defect. The defect does not authorize a rerun and
does not invalidate the frozen diagnostic result.

## Runtime and experiment invariants

The preserved evidence binds:

- Python 3.12
- CUDA 12.9
- Torch 2.11.0+cu129
- Transformers 5.14.1
- Triton 3.6.0
- vLLM 0.25.1+cu129
- native module `vllm._C_stable_libtorch`
- attention backend `TRITON_ATTN`
- T4 x2
- Internet Off
- model `Qwen/Qwen2.5-0.5B-Instruct`
- model revision `7ae557604adf67be50417f59c2c2f167def9a775`
- model snapshot SHA-256
  `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`
- prompt token count 899 in both conditions
- complete cumulative prompt-token profile lock
- frozen generation settings and request order

## Claim boundary

This result supports the frozen, predeclared classification that marker
diversification restored exact-object behavior under the cumulative-length lock
in this B-vs-D diagnostic.

It does not establish:

- exact repetition as the sole or root cause
- exact n-gram block effects as individually causal
- aligned periodicity effects as individually causal
- marker lexical novelty as eliminated
- marker semantic novelty as eliminated
- an exact repetition threshold
- context length alone as causal
- the exact root cause of the historical regression
- a prefix-cache defect
- P5 requalification
- P6 requalification
- measured North-Star A/B/C effects
- production readiness

The text-segment boundary was not assumed to equal the tokenizer boundary.

## Validation contract

The disposition producer must fail closed on:

- custody byte drift
- nested evidence ZIP drift
- decision/count drift
- request-order drift
- runtime identity drift
- lifecycle transaction drift
- authorization reuse
- platform-policy drift
- terminal-disposition drift
- outer-results wrapper artifact drift
- saved-notebook wrapper artifact drift
- repository authority drift
- generated record/review drift

The disposition authority boundary is exactly 15 authorities:

- 1 custody manifest
- 8 custody members
- 6 repository authorities

No new execution is authorized by this disposition.

## Next gate

`REPAIR_TRANSACTION_BOUND_WRAPPER_ZERO_EXIT_REPORTING_BEFORE_NEW_EXECUTION_V1`

The wrapper reporting defect must be repaired and statically validated before
any new live execution authorization is considered.

# AuraGateway P4/P5 Token-Count-Matched Context-Structure Differential Disposition V1

## Decision

Accept and preserve the governed diagnostic as:

`HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED`

The frozen 899-token comparison produced:

- `A_ORIGINAL_24X_ANCHOR`: 0/3 exact-object responses
- `B_NEUTRAL_REPEATED_24X`: 0/3 exact-object responses
- `C_NEUTRAL_DIVERSE_24_SEGMENT`: 3/3 exact-object responses
- valid JSON counts: A=0/3, B=0/3, C=3/3
- fresh worker process per observation: true
- worker identity cardinality: 9

Condition A reproduced the historical failure. Removing the instruction-like semantics
while retaining high exact repetition did not recover the endpoint in B. Reducing exact
token-pattern repetition while preserving the 899-token condition recovered the endpoint
in all three C observations.

This strongly implicates high exact token-pattern repetition within the frozen comparison.
It does not establish exact repetition as the sole cause. The B-to-C contrast retains
bounded lexical novelty.

## Governed transaction

- Transaction: `43ab735de5477d0d05c6eba1fc95b5966d4a06d37a5d5f28875ed5c2c423122a`
- Kaggle saved version: `342834146`
- Issuer merge commit: `417c7457dce0fafe16c4fbbd21d8344251f609d0`
- Terminal disposition: `CONSUMED`
- Execution outcome: `PASSED`
- Authorization reusable: `false`

## Realized execution budget

- model requests: 9 / 9
- model loads: 9 / 9
- worker starts: 9 / 9
- hidden retries: 0
- replacement observations: 0
- external network requests: 0
- benchmark-trajectory requests: 0
- external spend: 0
- worker teardown: PASS
- scratch cleanup: PASS

## Runtime and evidence identity

- runtime SHA-256: `9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834`
- governed evidence ZIP SHA-256: `4f44f378e309e49195e9bef1aa3122f9850d84f705c113782133febc96ce9654`
- executed notebook SHA-256: `b89a6158560a9a58ea8607b75b1e4125bab595b95cc9a841a0b9bb7b34d09a75`
- terminal log SHA-256: `377013ccb4e46df2ea6e3e0c5af4e527cfe51868b2714639671f98c841a18094`
- platform-observation receipt SHA-256: `2c95fc3d107de8b568bdef73159464389aa8d13b0bef3dd00d9d88fa9f4c2244`
- authorization terminal receipt SHA-256: `d10967a7a87bbe69a9e205d44260bdfe83d35a2b5e6493a5584f567d45014d4b`
- custody manifest SHA-256: `1d3db0cfca06aa5f88d018cdf252dcbb775b48e8229c237c8949c4838559549b`

The evidence bundle validates all 13 manifest-declared members and records no diagnostic
failure. Runtime source identity, installation, and process-tree import closure passed.

## Interpretation boundary

The accepted evidence supports the predeclared A0/B0/C3 classification:

`HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED`

It does not establish:

- exact repetition as the sole cause;
- semantic amplification as the sole cause;
- an exact repetition threshold;
- context length alone as causal;
- the exact historical root cause;
- a prefix-cache defect;
- P5 or P6 requalification;
- measured North-Star A/B/C support;
- production readiness.

The consumed transaction is terminal. No unchanged replay or new execution is authorized.

## Evidence custody

Immutable evidence is preserved under:

`evidence_vault/local_abc/p4-p5-token-count-matched-context-structure-differential-v1`

The evidence subtree is protected as byte-preserved Git content through `.gitattributes`.

## Next gate

`STATIC_HIGH_EXACT_TOKEN_PATTERN_REPETITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1`

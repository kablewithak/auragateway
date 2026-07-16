# AuraGateway Schema-Canary Token-Count Remediation v1

## Decision

The failed schema-constrained quality/cache canary is retained as immutable diagnostic evidence.
The model boundary is not classified as defective: the first request returned HTTP 200, passed the
case schema, passed all seven deterministic quality checks, and selected `sev3`.

The failure was in notebook-local token normalization:

```text
notebook planned prompt tokens = 2
API prompt tokens = 282
vLLM prompt tokens = 282
```

The notebook iterated a tokenization container and counted its two entries instead of extracting the
underlying `input_ids` sequence. Turn two was never reached, so the only valid cache label is
`not_observed`.

## Repository remediation

This slice introduces a typed repository boundary that:

- renders the chat template with `tokenize=False`;
- explicitly tokenizes that exact rendered text with `add_special_tokens=False`;
- accepts flat sequences, one-sequence batches, rank-1 array-like values, rank-2 single batches,
  and mappings such as `BatchEncoding` containing `input_ids`;
- rejects missing `input_ids`, empty sequences, multi-batch values, deeper ranks, booleans,
  negative IDs, and non-integer IDs;
- returns one immutable `tuple[int, ...]`;
- computes token count and common-prefix length from those normalized IDs;
- retains rendered-text and token-ID SHA-256 digests without retaining raw rendered text or raw
  token IDs in serialized evidence.

## Failed-canary audit

The audit binds:

- local evidence filename
  `auragateway-schema-constrained-quality-cache-canary-evidence-v1 (1).zip`;
- archive SHA-256
  `e5695e372960efeaacc519153c704e3a3af23248a2165986083ebac8d50cc826`;
- canonical report SHA-256
  `f92cc5644fd0c7be5709396ac2e1189950d863229c5aa103d9c0f8812c0fbdf9`;
- ledger SHA-256
  `0569e5f78e53ac0ff3c8bc04a010011a0437fb15227134398bded3e072f4bf80`;
- consumed PR #74 authorization fingerprint
  `6af80f33302e2b6eebf2e4d61efd6b198d9c7706a8a6bfe686b849faad6e5b14`.

The `(1)` suffix is a local Downloads collision suffix only. It is not a new evidence version.

## Fresh rerun authorization

The PR #74 authorization is consumed and cannot be reused. The new authorization preserves:

- the same three cases in the same order;
- condition C only;
- `worker_1 -> worker_1`;
- two turns per trajectory;
- three trajectories and six requests;
- full worker restart before every trajectory;
- exact schemas and deterministic decoding;
- 100% quality pass requirement;
- cold turn one and positive cached-prefix tokens on turn two;
- zero trajectory failures;
- zero hidden retries and zero replacements;
- R0 / $0 spend;
- synthetic data only;
- no raw prompt or raw output retention;
- full measured rerun unauthorized.

The authorization requires the corrected notebook to bind the exact remediation merge commit. The
historical notebook remains non-runnable. GPU enablement remains prohibited until the remediation PR
has merged and the corrected notebook has been generated from clean `main`.

## Contract fingerprints

- Token-normalization policy:
  `9b16866de747d67f41e4289d6f5fc9e7398da0054ee052dcc9371c5585954830`
- Preserved six-request scope:
  `d1563d346138f10c4701492a2c1ddc7bd02bb0c5c937221b36c916361e348c64`
- Failed-canary audit:
  `45712ac7ab42c17bc949dc374dd1e4114ab408657b54d36509c0d241a5f74019`
- Rerun authorization:
  `7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66`

## Validation boundary

Repository tests cover list, tuple, nested single-batch, array-like, and mapping/BatchEncoding-style
return shapes. They fail closed on missing IDs, empty IDs, multiple batches, deeper dimensions,
booleans, negative values, and non-integer values.

A synthetic tokenizer regression returns 282 IDs and proves that the repository seam reports 282,
not the container length. The actual pinned Qwen runtime remains a post-merge Kaggle
validation gate.

## Non-claims

This slice does not claim:

- that the corrected canary has executed;
- that turn-two cache reuse passed or failed in the historical run;
- that all six corrected requests pass quality;
- that the 72-trajectory benchmark is authorized;
- hosted-provider equivalence;
- customer-data readiness;
- production readiness.

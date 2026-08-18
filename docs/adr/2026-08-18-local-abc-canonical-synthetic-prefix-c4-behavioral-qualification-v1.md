# ADR: Canonical Synthetic Prefix C4 Behavioral Qualification V1

- **Date:** 2026-08-18
- **Status:** Accepted for repository implementation
- **Source main:** `85ecc02001e934fc419f7e1801e72d0e92678678`
- **Scope:** Controlled-local C4 qualification only

## Context

AuraGateway has frozen `CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1` as the canonical long reusable synthetic prefix for the controlled-local qualification harness.

The corpus is statically accepted for C4 design input, but C4 remains behaviorally unqualified. P5 and P6 therefore remain blocked.

The next decision is how to qualify the exact full composed request without reopening the earlier causal diagnostic matrix or changing the frozen request contract.

## Decision

C4 Behavioral Qualification V1 will use one frozen request contract and exactly three independent observations.

The qualification identifier is:

`CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1`

The canonical corpus identity is:

`140e8157da883e07f2d76d4f516ec2beec961fefb639b8509cc8f3a6239d14e9`

The rendered prompt identity is:

- prompt tokens: `899`
- prompt token SHA256: `f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c`

The expected parsed object is:

`{"probe":"exact-runtime-p5-p6","value":1}`

## Frozen request contract

The message-role topology remains:

1. `system`
2. `user`
3. `assistant`
4. `user`

The system instruction remains:

`Return only the exact JSON object supplied in the final user message, with no markdown or additional text.`

The assistant acknowledgement remains:

`Synthetic deterministic context acknowledged.`

The generation contract remains:

- temperature: `0`
- top_p: `1`
- repetition_penalty: `1.1`
- seed: `7`
- max_tokens: `32`
- stream: `false`
- response_format: `null`
- guided_decoding: `null`

No prompt shortening, assistant-turn removal, role restructuring, schema enforcement, guided decoding, parser relaxation, model replacement, or generation-parameter change is permitted.

## Runtime contract

The qualification remains bound to:

- Python `3.12`
- CUDA runtime `12.9`
- Torch `2.11.0+cu129`
- Transformers `5.14.1`
- Triton `3.6.0`
- vLLM distribution `0.25.1+cu129`
- vLLM public version `0.25.1`
- native extension `vllm._C_stable_libtorch`
- attention backend `TRITON_ATTN`
- GPU topology `T4 x2`
- model `Qwen/Qwen2.5-0.5B-Instruct`
- revision `7ae557604adf67be50417f59c2c2f167def9a775`
- model directory SHA256 `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`

A governed runtime identity change creates a new qualification identity.

## Observation contract

There is one case and three observations.

Each observation must use:

`fresh worker -> zero cached-prefix baseline -> one request -> teardown`

The three observations are independent for C4 purposes. Worker reuse is prohibited because C4 is qualifying the output contract rather than measuring cache reuse.

There are no hidden retries and no replacement requests.

## Pass rule

Every observation must satisfy all of the following:

- transport succeeds;
- worker remains healthy;
- response completes;
- no Markdown fence is present;
- no non-whitespace content precedes the JSON object;
- no non-whitespace content follows the JSON object;
- JSON parses successfully;
- JSON root is an object;
- exact key set is `probe` and `value`;
- `probe == "exact-runtime-p5-p6"`;
- `value == 1`;
- no extra keys are present;
- the canonicalized parsed object equals `{"probe":"exact-runtime-p5-p6","value":1}`.

C4 is `QUALIFIED` only at `3/3`.

There is no majority rule and the threshold cannot be relaxed after execution starts.

## Terminal states

### QUALIFIED

Complete interpretable evidence exists and all three independent observations satisfy the exact-object contract.

### NOT_QUALIFIED

Complete interpretable execution exists and at least one healthy model response violates the exact-object contract.

### INVALID_EXECUTION

Setup, authority, runtime, worker, transport, evidence-custody, budget, teardown, or cleanup failure prevents a valid qualification.

An invalid execution does not count as model evidence against C4.

## Execution budget

The future governed execution harness must enforce:

- Kaggle sessions: maximum `1`
- Save & Run All actions: maximum `1`
- runtime install attempts: maximum `1`
- import-closure probes: maximum `1`
- model loads: maximum `3`
- worker starts: maximum `3`
- model requests: maximum `3`
- worker teardowns required: `3`
- output tokens per request: maximum `32`
- hidden retries: `0`
- replacement requests: `0`
- trajectory requests: `0`
- external network requests: `0`
- external spend: `0`

A failed observation is not rerun inside the same authorization.

## Evidence contract

Per observation, preserve deterministic evidence for:

- observation identity and request ordinal;
- worker-start receipt;
- zero-cache baseline establishment;
- response SHA256 and length;
- finish reason and token usage;
- JSON validity and error coordinates;
- Markdown-fence detection;
- leading and trailing non-whitespace detection;
- parsed key set;
- exact-object validity;
- canonical object SHA256;
- request error;
- transport error;
- worker health after request;
- teardown status.

Raw prompt retention remains `false`.

Raw model-output retention remains `false`.

## Authorization boundary

This ADR does not authorize model execution.

The design producer and generated request/review must keep:

- runtime execution authorized: `false`
- authorization issuer included: `false`
- P5 execution authorized: `false`
- P6 execution authorized: `false`

Runtime execution requires a separate post-merge authorization tranche after a governed C4 execution harness is implemented and merged.

## Consequences

A `3/3` pass may move C4 from `NOT_QUALIFIED` to `QUALIFIED_FOR_CONTROLLED_LOCAL_P5_P6_SUCCESSOR`.

It does not establish general model reliability, production readiness, historical root cause, prefix-cache correctness, P5 success, P6 success, the final A/B/C effect, or long-run reliability.

## Rejected alternatives

Rejected:

- another six-case diagnostic matrix;
- `2/3` majority acceptance;
- worker reuse across observations;
- retry-until-success;
- schema/guided decoding;
- context reduction;
- assistant-turn removal;
- role restructuring;
- generation-parameter changes;
- model or runtime replacement;
- combining C4 execution with P5/P6.

## Next gate

`MERGE_THEN_IMPLEMENT_GOVERNED_C4_EXECUTION_HARNESS_V1`

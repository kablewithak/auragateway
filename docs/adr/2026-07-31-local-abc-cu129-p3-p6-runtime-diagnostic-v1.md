# ADR: CUDA 12.9 P3-P6 Runtime Diagnostic V1

- Status: Proposed for implementation
- Date: 2026-07-31
- Source main: `58a73c38c22337219899018d655e00366d790413`
- Q6 acceptance SHA-256: `9928243d34edd82996a3120f724df6c8bf4912e8b8790b8abc8926eccca006c1`
- Option C decision SHA-256: `6297b48f64811dbd1b86c850b0fbd66a4142d174d69897b673eb5748663cc418`

## Context

Q6 proved that the governed CUDA 12.9 target can discover, import, validate, and
execute the explicit native `TRITON_ATTN` backend on Tesla T4 hardware. Q6 did
not start a vLLM worker, load a model, issue a request, exercise paged decoder
attention, prove prefix-cache behavior, or prove dual-worker isolation.

The historical full qualification adapter cannot be reused as the P3-P6
controller because it starts both workers before proving P3. It also emits a
capability report for metric availability but does not establish the cache
success relationship required by P5.

## Decision

Implement a separate sequential diagnostic:

1. P3 starts only worker 1 on GPU 0 with `--attention-backend TRITON_ATTN`.
2. P4 sends one bounded deterministic synthetic request and requires the
   response to be valid JSON matching the requested synthetic object.
3. P5 performs cold, warm, and post-reset requests on worker 1.
4. P6 starts worker 2 on GPU 1 and proves process, GPU, port, route, and metric
   isolation.

The implementation reuses accepted identities, wheelhouse controls, model
authority, loopback-only transport, bounded subprocess handling, and
stop-on-first-failure doctrine. It does not call the legacy monolithic
qualification capture flow.

## Cache evidence rule

P5 accepts only the token-level metric:

`vllm:prompt_tokens_cached_total`

The generic prefix-cache hit counter is not treated as cached-token evidence.
The warm request must observe positive cached-prefix tokens and fewer newly
computed prefill tokens than the cold request. A full process restart must then
return the post-reset cached-prefix delta to zero.

## Backend realization rule

The worker command must contain the exact explicit CLI selection:

`--attention-backend TRITON_ATTN`

The target runtime must bind `AttentionBackendEnum.TRITON_ATTN` to
`vllm.v1.attention.backends.triton_attn.TritonAttentionBackend`, with no
registry override. Readiness evidence must also retain a bounded startup-log
marker for the selected backend.

## Action budget

- Kaggle sessions: 1 maximum
- Runtime installations: 1 maximum
- Model loads: 3 maximum
- Worker starts: 3 maximum
- Model requests: 5 maximum
- Output tokens per request: 32 maximum
- Benchmark trajectories: 0
- Network requests: 0
- Hidden retries: 0
- External spend: 0

Every runtime installation, worker start, model load, and model request is
checked against the action budget before the side effect occurs. A budget
violation fails closed with `P3_P6_ACTION_BUDGET_EXCEEDED`.

## Failure taxonomy

Every runtime failure emits one reviewed machine-readable code. Generic
exceptions are classified through the active probe boundary; budget and
privacy failures carry their code directly. Completed probe reports remain
preserved, and `failure_report_v1.json` is emitted on both pass and fail so the
evidence member set remains deterministic.

## Evidence policy

Completed probe reports are preserved if a later probe fails. Raw prompts and
outputs are never written. Response content is validated in memory as one JSON
object matching the requested synthetic object, then represented only by
SHA-256 and bounded usage metadata.

## Authorization boundary

This PR implements assets only. It does not issue runtime authority. A separate
post-merge authorization issuer is required before Kaggle, GPU, runtime,
model, worker, or request execution.

## Consequences

The design isolates failure attribution:

- P3 failure means worker/backend startup incompatibility.
- P4 failure means startup works but one bounded request does not.
- P5 failure means request execution works but cache attribution/reset does not.
- P6 failure means single-worker behavior works but dual-worker isolation does
  not.

## Non-claims

No deployment, production readiness, customer-data readiness, A/B/C effect,
latency improvement, cost improvement, or quality non-inferiority is claimed.

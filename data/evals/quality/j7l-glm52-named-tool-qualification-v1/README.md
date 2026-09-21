# J7L GLM-5.2 Named-Tool Qualification V1

Status: **review-ready, inactive, non-live**.

This tranche prepares a bounded AuraGateway-specific qualification of the selected
GLM-5.2 reference-judge transport. It does not authorize credential access, network
access, provider traffic, J7L reference execution, Jev execution, or final binding
freeze.

## Decision being tested

The qualification asks whether Huawei MaaS can satisfy the exact planned boundary:

- model `glm-5.2`;
- OpenAI-compatible chat endpoint;
- one forced named function, `submit_reference_judgment`;
- `response_format` absent;
- `max_completion_tokens=768`;
- `chat_template_kwargs={"thinking": false}`;
- non-streaming execution;
- deterministic host-side validation of function arguments.

The provider's current OpenAI-compatible documentation states that GLM-5.2 supports
named tool choice, `max_completion_tokens`, usage accounting, and a thinking-control
field. Those documentation claims are planning evidence only; this qualification
exists to obtain AuraGateway-specific observed evidence.

## Bounded live shape after separate authorization

At most two provider HTTP requests are permitted:

1. one authenticated `GET /v2/models` catalog request;
2. one synthetic `POST /openai/v1/chat/completions` inference request.

Only the second request is a model inference. It contains the frozen model semantic
projection plus a synthetic case and deterministic padding. It contains no frozen
`j7l-dev-*` case, no Jev output, and no frozen reference answer.

The complete qualification has a 20,000-token allowance, no automatic retry, no
resume, no rerun, no paid fallback, and an external-spend ceiling of R0.

## Acceptance evidence

A passing transport qualification requires:

- the model catalog contains exact ID `glm-5.2`;
- the chat request succeeds;
- exactly one tool call is returned;
- the function name is exactly `submit_reference_judgment`;
- the function arguments are valid JSON and pass `J7LReferenceToolArgumentsV1`;
- `reasoning_content` is null/empty;
- reported reasoning tokens equal zero;
- prompt, completion, and total usage are present;
- total model tokens stay within the 20,000-token qualification allowance.

A catalog record containing only the alias `glm-5.2` does **not** by itself resolve
the constitution's separate provider-version/revision requirement. If Huawei exposes
no usable version/revision in the observed catalog or response, transport may qualify
while final judge binding remains blocked on a separate version-identity decision.

## Frozen identities

- source merge commit: `0ba2b7b22e7f79d50ba45c2220da7faa0735433c`
- named-tool contract SHA-256: `2279c972598100c5bb52c77b97c6134f86e8cf77d479167358b1d52a5fd9e695`
- synthetic prompt recipe SHA-256: `1096b01fcffa5b42c79b77dce2840ddb9ebf8ce837c7ed304e1c6f092c40167b`
- model projection semantic SHA-256: `b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e`

## Next gate

`AUTHORIZE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_V1`

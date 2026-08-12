# AuraGateway P4/P5 Composition Remediation Implementation V1

## Status

`IMPLEMENTED_NOT_EXECUTED`

This tranche implements the frozen P4/P5 composition remediation design as a
new static successor runtime. It does not mutate the accepted predecessor
runtime and does not authorize execution.

## Bound authorities

- Base main commit: `57380a5b0a4771cd5a373daa81dee32b5f3f7c00`
- Design record SHA-256: `ac737bccf6459951877b6695a6a6d368a81cba9318d6cee2656af48b6711c5ea`
- Predecessor runtime SHA-256: `361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3`

## Implemented intervention

The successor changes both `SYNTHETIC_CACHE_CONTEXT_A` and
`SYNTHETIC_CACHE_CONTEXT_B` instruction tails from the historical V5 wording
to the accepted V4 wording.

The following remain unchanged: system prompt, four-role message composition,
assistant acknowledgement, 24x cache-context repetition, prefix variants,
canonical final object, generation controls, prefix-cache enablement and block
size, P5 decision semantics, P6 decision semantics, retry policy, model and
runtime dependency identities.

## Failure-safe token evidence

The successor adds `pre_request_token_identity_journal_v1.json`. It is
initialized before the qualification trajectory and atomically updated after
server tokenization but before the metric snapshot, model-request budget
consumption and `/v1/chat/completions` call.

Each entry retains only the frozen evidence fields: request ordinal, request
role, prefix variant, token count, token SHA-256, token IDs, request-payload
SHA-256 and the pre-request persistence marker. Raw prompts and raw model
outputs are not retained.

The exact request payload whose hash is journaled is reused for the later chat
completion call; instrumentation does not rebuild or mutate it after hashing.

## Static proof boundary

The producer compares predecessor and successor AST surfaces. Existing classes
must remain unchanged. Existing functions may change only at `main` and
`run_structured_request`; three journal functions may be added. Existing global
assignments may change only at `OUTPUT_NAMES` and the two synthetic cache
contexts; one journal-path global may be added.

Any other existing function, class or global-assignment change is rejected.

## Execution state

- `remediation_implemented=true`
- `runtime_execution_authorized=false`
- `new_execution_authorized=false`
- `kaggle_execution_performed=false`
- `model_requests_performed=0`

## Non-claims

This implementation does not establish that the remediation works at runtime,
that P5 passes, that P6 passes, or that the V5 tail was the sole causal factor.
Those claims require a separately authorized governed full P5/P6 execution.

## Next gate

`MERGE_THEN_DESIGN_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1`

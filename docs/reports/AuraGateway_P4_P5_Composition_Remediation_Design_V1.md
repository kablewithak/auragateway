# AuraGateway P4/P5 Composition Remediation Design V1

## Status

`DESIGN_FROZEN_NOT_IMPLEMENTED`

## Accepted evidence

The accepted P4/P5 composition differential established, under one frozen
runtime/model/request contract:

- simple control A: `3/3` exact-object success;
- composed P5 B: `0/3` exact-object success;
- decision: `COMPOSITION_REGRESSION_SUPPORTED`.

Historical P4 output-contract evidence also established that unconstrained V4
prompt cases A/C passed while unconstrained V5 prompt cases B/D failed. The
current P5/P6 predecessor runtime uses the accepted V4 instruction as its system
prompt but embeds the historical V5 instruction as the instruction tail of both
synthetic cache-context variants.

The historical V5 evidence does not prove that the V5 tail is the sole cause of
the current composed-B regression. It makes that tail the smallest
evidence-backed first remediation variable.

## Frozen intervention

Intervention:

`REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION`

The implementation may replace only the instruction tail in:

- `SYNTHETIC_CACHE_CONTEXT_A`
- `SYNTHETIC_CACHE_CONTEXT_B`

Before:

`For structured probes, return only the exact JSON object supplied in the final user message.`

After:

`Return only the exact JSON object supplied in the final user message, with no markdown or additional text.`

The predecessor contains exactly two governed occurrences of the V5 instruction.
A conforming successor contains zero V5 cache-context instruction tails and two
V4 cache-context instruction tails.

## Frozen invariants

The remediation must preserve:

- message roles: `system,user,assistant,user`;
- the synthetic assistant acknowledgement;
- both long synthetic cache-context bodies;
- the 24x repetition count;
- prefix variants A and B;
- the final canonical object;
- prefix caching and block size 16;
- P5 cache-decision semantics;
- P6 route/process/GPU/state-isolation semantics;
- temperature `0`, top-p `1`, repetition penalty `1.1`, seed `7`, max tokens
  `32`;
- unconstrained output mode;
- no hidden retries.

This design therefore does not collapse the remediated request into the simple
A control.

## Failure-safe token evidence

The implementation must add one durable pre-request token-identity journal:

`pre_request_token_identity_journal_v1.json`

Each observation is persisted after server tokenization but before metric
snapshot, model-request budget consumption, and `/v1/chat/completions`.

The journal retains only:

- request ordinal;
- request role;
- prefix variant;
- token count;
- token SHA-256;
- token IDs;
- request-payload SHA-256;
- proof that persistence happened before the model request.

Raw prompts and raw model outputs remain prohibited.

Journal updates must be atomic so an output-contract failure cannot erase the
model-boundary evidence already observed for that request.

## Full-runtime acceptance

A future governed execution is accepted only if the complete P5/P6 successor
trajectory passes.

The six structured request roles remain:

`BASE_COLD, BASE_WARM, NEGATIVE_PREFIX, POST_RESET_COLD, CROSS_WORKER_COLD, WORKER1_RETENTION`

Acceptance requires:

- all six structured requests return the exact canonical object;
- P5 state is `PASS`;
- P6 state is `PASS`;
- prefix-A token identity is stable across the required controls;
- negative-prefix token identity diverges;
- BASE_WARM proves attributable cache reuse;
- POST_RESET_COLD proves cold state after restart;
- CROSS_WORKER_COLD proves no prohibited cross-worker cache inheritance;
- WORKER1_RETENTION proves the intended worker-1 retained state;
- teardown is `PASSED`;
- scratch cleanup is `PASSED`;
- maximum model requests remain 6;
- maximum model loads remain 3;
- maximum worker starts remain 3;
- hidden retries remain 0.

A standalone A/R GPU differential is not required by this design. The accepted
historical and current differential evidence form the baseline; the full P5/P6
trajectory is the remediation acceptance test.

## Future execution authorization

This design does not authorize execution.

The later execution-authorization design must implement the reconciliation
forward control:

`PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL`

The durable observation must bind transaction ID, observation timestamp,
accelerator, allocated GPU count, Internet state, and capability source before
the single Save & Run All.

Console-only platform-observation evidence is not sufficient.

## Non-interventions

This tranche does not remove the assistant turn, change role order, shorten the
cache context, change generation controls, add schema/guided decoding, relax
the parser, add retries, change the model/runtime stack, change cache metrics,
change P6 semantics, mutate historical evidence, or repair unrelated stale
metadata.

## Safety

- runtime execution authorized: false
- new execution authorized: false
- remediation implemented: false
- successor runtime generated: false
- Kaggle execution performed: false
- model requests performed: 0
- Case C authorized: false

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1`

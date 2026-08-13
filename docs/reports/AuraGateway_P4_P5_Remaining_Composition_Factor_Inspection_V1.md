# AuraGateway P4/P5 Remaining Composition Factor Inspection V1

## Decision

`STATIC_INSPECTION_COMPLETE_EXECUTION_NOT_AUTHORIZED`

The accepted composition family remains causally implicated, but the exact remaining
subfactor is not identified. The historical V5 cache-context instruction tail is
eliminated as a sufficient sole explanation because the governed V5-to-V4 remediation
was present and the first composed C3 request still failed.

## Current static observations

- Current first material divergence: `C3_COMPOSED_REQUEST_OUTPUT_CONTRACT`
- Accepted differential: `COMPOSITION_REGRESSION_SUPPORTED`
- First remediation result: `REMEDIATION_INTERVENTION_INSUFFICIENT`
- Current request roles: `system,user,assistant,user`
- Current cache-context repetition count: `24`
- Historical predecessor request roles: `system,user,assistant,user`
- Historical predecessor cache-context repetition count:
  `24`
- Historical predecessor authority: precedent only; not current-runtime qualification

## Ranked remaining hypotheses

1. `CURRENT_RUNTIME_X_LONG_REPEATED_CACHE_CONTEXT` — `LIVE_UNRESOLVED` — The long repeated cache context remains a live current-runtime interaction candidate, not an established cause.
2. `CURRENT_RUNTIME_X_ASSISTANT_ACK_AND_FOUR_ROLE_TOPOLOGY` — `LIVE_UNRESOLVED` — Assistant acknowledgement and role topology remain live only as current-runtime interaction candidates.
3. `CURRENT_RUNTIME_X_HIGHER_ORDER_COMPOSITION_INTERACTION` — `INTERACTION_ONLY` — A higher-order interaction remains plausible and should be revisited only if simpler one-variable discriminators fail.
4. `HISTORICAL_V5_CACHE_CONTEXT_TAIL_AS_SOLE_CAUSE` — `ELIMINATED_AS_SOLE_CAUSE` — The V5 cache-context tail is not sufficient as the sole explanation of the current composed C3 regression.
5. `GENERIC_MODEL_OR_BASIC_RUNTIME_UNRELIABILITY` — `NOT_SUPPORTED` — The available evidence does not support generic Qwen unreliability or basic runtime incompatibility as the current explanation.

## Smallest discriminating next design

`CACHE_CONTEXT_REPETITION_24_VS_1_WITH_COMPOSITION_FROZEN`

Freeze all current message/runtime/model/generation properties and vary only
cache-context repetition count from 1 to 24. This is the preferred first discriminator
because removing the assistant acknowledgement would also change the role topology.

This report **does not authorize execution**. The next legal gate is design and merge
of that differential only.

## Non-claims

- The remaining composition subfactor is not identified.
- Cache-context repetition count is not established as the root cause.
- The assistant acknowledgement is not established as the root cause.
- The four-role topology is not established as the root cause.
- A higher-order composition interaction is not established as the root cause.
- Generic Qwen unreliability is not established.
- Basic runtime incompatibility is not established.
- P5 was not reached and no P5 failure is established.
- P6 was not reached and no P6 failure is established.
- Guided decoding or schema forcing is not authorized by this inspection.
- No runtime, GPU, Kaggle, worker, or model-request execution is authorized.
- Historical predecessor behavior is precedent only and does not qualify the current runtime lineage.

## Identity

- Base main: `ade6cb6fe3c4aaba6c99524d4cd347ee21546951`
- Producer source SHA-256: `902f562722a01d96f976ba067edb3829dc8696d04a3456157c82be8b29b894e9`
- Record SHA-256: `bf4b94142090184b7c0b7d174b61b4f192474b396e34b28eb182670ec0be672a`
- Next gate: `DESIGN_AND_MERGE_P4_P5_CACHE_CONTEXT_REPETITION_DIFFERENTIAL_V1`

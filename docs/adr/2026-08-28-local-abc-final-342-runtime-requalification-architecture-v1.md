# ADR: Final 342-Trajectory Runtime Requalification Architecture V1

**Date:** 2026-08-28  
**Status:** Proposed for G11.0 architecture acceptance  
**Base main:** `c05af5260df3cae71ca8d66154b60432b0af46f0`  
**Execution authority:** None

## Context

G9 accepted governed Variance Pilot Successor V2 saved Version `345461230`.
G10 then froze the final repetition plan, statistical contract, primary runtime
endpoint, quality non-inferiority contract, and warm/reset analysis policy.

The exact final planned-run ledger is already frozen by identity:

`c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c`

It contains 342 planned trajectories, 1,368 turns, and a maximum of 2,736
request attempts.

The final execution manifest remains unfrozen and final execution remains
unauthorized.

Prior governed runs exposed failures that must not be rediscovered in the
final experiment: counterbalance reconstruction, condition-derived routing,
weak output admission, worker/treatment confounding, masked primary failures,
authorization transport coupling, and incomplete measured-review custody.

## Decision

Adopt:

`FINAL_342_TRANSACTION_BOUND_RUNTIME_REQUALIFICATION_V1`

The architecture optimizes for one trustworthy governed final experiment,
rather than for refactoring historical contracts.

## Frozen planning subject

The existing 342-run ledger remains byte-identical. It remains authority for
run identity, order, scope, cache namespace, route schedule, turn count, and
per-run request budget.

The final runner consumes ledger order exactly and does not reconstruct A/B/C
order.

## Planning-manifest to execution-manifest bridge

The ledger remains bound to its historical planning-manifest identity:

`4bd822375390cf413718553313903679e78b650dfa798955e2f7c61ebd8b8678`

That hash proves planning lineage only. It is not promoted into the future
frozen execution-manifest identity.

Every final runtime trace must additionally bind the actual frozen final
execution-manifest SHA-256. Final comparison eligibility uses that final
identity.

The ledger is not rewritten.

## Four-turn route realization

Routing is realized from `planned_run.route_schedule_id`, not condition ID.

- `turn-local-worker1-worker2-v1` realizes
  `worker_1, worker_2, worker_1, worker_2`.
- `affinity-worker1-worker1-v1` realizes
  `worker_1, worker_1, worker_1, worker_1`.

Local cache-residency identity includes worker ID, worker generation, and
runtime/model identity. Worker-generation drift invalidates warm eligibility.

## Session identity

Each planned trajectory receives one deterministic privacy-safe session hash:

`SHA256("auragateway-final-342-session-v1|" + run_id)`

All four turns share the same session hash. Raw session identifiers are not
retained.

## Prefix identity

Preflight-v3 prefix identities remain planning identities that require runtime
confirmation.

The final runtime confirms the realized canonical/HMAC prefix identity. It
does not silently promote a planning prefix hash into observed runtime
evidence and does not invent a weaker ad-hoc fingerprint.

## TTL and warm eligibility

Use a 300-second benchmark warm-eligibility assumption under the existing
`benchmark-assumption-v1` lineage.

This is a benchmark classification window, not a claim that vLLM guarantees
KV-cache residency, eviction timing, or visibility for 300 seconds.

Turn 1 is cold. A later turn is warm-eligible only when evidence establishes
same session, cache-residency route, static prefix identity, cache namespace,
TTL eligibility, and absence of failure/reset/benchmark-transition
invalidation.

Positive cached-token evidence is not required to classify a turn as
warm-eligible. Ambiguous state remains unavailable or ambiguous.

Synthetic pre-warm requests are prohibited.

## Request and retry contract

The final runtime adopts Constitution `provider-request-policy-v1`:

- connection timeout: 10 seconds;
- first-output timeout: 45 seconds;
- total request timeout: 120 seconds;
- at most one retry after the initial attempt;
- fixed 2-second backoff;
- no retry jitter;
- retry only after typed no-response or definite failure;
- no blind retry after an ambiguous response.

Every attempt is retained.

The final authority ceiling is 2,736 attempts. The V2 pilot's pretreatment
requests do not carry into final execution. Hidden canary, warm-up, or
worker-qualification model requests are prohibited inside final authority.

## Output and state safety

Preserve the accepted V2 ordering:

1. exact accepted-tokenizer check immediately before request;
2. bounded request attempt;
3. immediate transport-completion accounting;
4. `finish_reason=stop`;
5. schema admission;
6. prospective next-prompt reachability when another turn remains;
7. conversation mutation only after all gates pass.

Failed or unadmitted output never mutates conversation history.

## Public and protected evidence

Public benchmark evidence excludes raw prompts, raw outputs, raw provider
payloads, credentials, secrets, and protected review content.

The functional benchmark additionally emits a protected measured-review
export under:

`.local/auragateway/final-342-protected-review-v1`

The protected export stays outside Git, uses opaque review IDs, and supports
100 percent primary rubric review plus the frozen 25 percent independent
double-review sample. Reviewers remain blind to condition, route, cost,
latency, and cache evidence.

Public evidence may bind protected review material only through safe metadata
or digests.

A retention/deletion rule must be bound before execution-manifest freeze.

The existing synthetic protected-review harness proves workflow mechanics
only; it does not constitute measured human review.

## Failure preservation

The first causal failure is retained independently from teardown, cleanup,
evidence packaging, and authorization terminalization failures.

Secondary failures may not mask the primary failure.

Authority must remain terminalizable even when the governed evidence ZIP is
missing or incomplete.

## Transaction wrapper

Preserve the merged transaction-bound execution architecture:

- zero authorization-specific Kaggle inputs;
- zero authorization producer notebooks;
- no manual confirmation JSON;
- runtime payload identity distinct from whole-notebook identity.

Before GPU authority, rehearse the wrapper through a real isolated module
graph without repository `PYTHONPATH`.

Tests may not weaken production module-graph clobber guards.

## Authorization boundary

This architecture does not issue execution authority.

Keep separate:

`runner -> wrapper rehearsal -> execution-manifest freeze -> static authority binding -> issuer qualification -> fresh human authority -> one governed execution`

Single-use is a governance invariant, not a runtime anti-replay claim.
Multiple observed executions for one transaction invalidate acceptance.

Historical `authorization_reusable=True` issuance semantics are prohibited
from the successor issuer lineage.

## Preflight-v3 reconciliation

Do not blindly delete stale unresolved-asset names from the historical
planning draft.

Each blocker must map to current accepted evidence by explicit identity or
remain unresolved.

## Consequences

After this tranche:

- the 342-run ledger is unchanged;
- G10 is unchanged;
- the execution manifest is still unfrozen;
- no model/GPU/Kaggle execution occurs;
- no authority is issued;
- effect claims remain prohibited.

## Next gate

`IMPLEMENT_FINAL_342_NON_AUTHORIZING_RUNTIME_CORE_V1`

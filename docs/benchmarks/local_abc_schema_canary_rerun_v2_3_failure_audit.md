# Local A/B/C Schema-Canary Rerun v2.3 Failure Audit

**Status:** Certified failed diagnostic  
**Audit fingerprint:** `772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62`  
**Evidence archive SHA-256:** `38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1`  
**Consumed authorization:** `7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66`  
**GPU execution authorized:** No  
**Full measured benchmark authorized:** No

## Purpose

This audit freezes the corrected v2.3 canary result without rewriting the failed
evidence. It distinguishes the three model requests that executed from the three
authorized requests that remained unobserved after the zero-failure abort.

## Executed boundary

| Case | Turn | State | Prompt tokens | Cached tokens | Result |
|---|---:|---|---:|---:|---|
| incident-severity | 1 | passed | 282 | 0 | Quality, schema, telemetry, and cold-cache gates passed |
| incident-severity | 2 | passed | 290 | 192 | Quality, schema, telemetry, and positive-cache gates passed |
| payment-reconciliation | 1 | failed | 289 | 0 | `OUTPUT_ANSWER_MISMATCH` |

Incident-severity turn two retained `192` cached tokens from `205` eligible
shared-prefix tokens. This qualifies positive reuse for that trajectory only.

Payment-reconciliation turn one passed HTTP, JSON, exact key-set, case identity,
turn identity, confidence, schema, telemetry, route, and cold-cache checks. It
failed the exact semantic answer check. Raw model output was not retained.

## Not-observed boundary

The following requests did not execute:

- payment-reconciliation turn 2;
- data-sharing-policy turn 1;
- data-sharing-policy turn 2.

Their only valid state is `not_observed`. They are not passed, failed, zero-cache,
or positive-cache observations.

## Authorization lifecycle

The v2 rerun authorization is consumed because real model requests executed.
The repository must reject any attempt to reuse it. This audit does not mutate
the historical authorization artifact; it adds a separate immutable consumption
record and typed reuse guard.

## Decision lineage

The semi-formal certificate classifies the run as:

```text
CERTIFIED_FAILED_DIAGNOSTIC
```

ADR `ADR-2026-07-16-LOCAL-ABC-ARITHMETIC-ACTION-REALIZATION` selects typed
deterministic arithmetic action realization as the next design boundary.

This audit authorizes governance and implementation design only. A new bounded
runtime experiment requires a new merged implementation commit, authorization,
notebook hash, scope fingerprint, and evidence lineage.

## Non-claims

This audit does not claim:

- payment-reconciliation turn 2 passed or failed;
- either data-sharing-policy turn passed or failed;
- all cases receive the observed incident cache benefit;
- the pinned model is universally incapable of arithmetic;
- deterministic action realization is implemented or validated;
- the 72-trajectory benchmark is authorized;
- AuraGateway is production-ready.

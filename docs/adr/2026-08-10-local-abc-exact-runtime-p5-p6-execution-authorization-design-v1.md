# ADR: Exact-Runtime P5/P6 Execution Authorization Design V1

**Date:** 2026-08-10
**Status:** Accepted for repository design

## Context

The exact-runtime P5/P6 implementation is merged at:

`9cc06c02c372fa2e7637c432759e7a1d4db56e9e`

and has not executed. The implementation consumer requires `execution_authorization_v1.json`
with scope `EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1`, decision `AUTHORIZED`,
lifecycle `ISSUED`, exact implementation bindings, a live time window, single-use
semantics, terminal consumption, and no unchanged replay.

Historical P5/P6 and V5 issuers provide lifecycle precedent only. Their consumed
authorizations are non-reusable.

## Decision

Freeze a separate authorization control plane before issuer implementation.

The future issuer must bind:

- merged implementation commit `9cc06c02c372fa2e7637c432759e7a1d4db56e9e`
- frozen design record SHA-256 `4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2`
- implementation record SHA-256 `6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d`
- implementation review SHA-256 `151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d`
- notebook SHA-256 `cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7`
- runtime-script SHA-256 `d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67`
- wrapper SHA-256 `55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c`
- accepted V5 capability record SHA-256:
  `b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1`

One governed execution may consume at most:

- 1 Kaggle session
- 1 saved version
- 6 model requests
- 3 worker starts
- 3 model loads
- 0 hidden retries
- 0 replacement workers
- 0 external network requests
- 0 benchmark trajectories
- R0 / $0 external spend

Issuance requires synchronized clean `main`, a merged issuer, exact issuer-merge
confirmation, fresh T4 x2 / Internet-off observation no older than 15 minutes,
fresh operator confirmation no older than 15 minutes, and a live authorization
window no longer than 240 minutes.

The exact operator phrase is:

```text
I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION
```

Terminal dispositions are:

- `CONSUMED`
- `EXPIRED_UNUSED`
- `CANCELLED_UNUSED`
- `ABANDONED_BEFORE_EXECUTION`
- `OUTCOME_UNKNOWN`

Every terminal state is non-reusable. An execution attempt with a known outcome
terminalizes as `CONSUMED`. `OUTCOME_UNKNOWN` is reserved for an attempted or
possibly attempted execution whose final outcome cannot be established
reliably.

## Consequences

The runtime harness cannot authorize itself. The issuer must be implemented,
validated, merged, then separately used to issue one short-lived authorization.

This design does not issue live authority and does not authorize the variance
pilot or final measured A/B/C execution.

# AuraGateway Exact-Runtime P5/P6 Execution Authorization Design V1

**Checkpoint:** 2026-08-10
**Base main:** `9cc06c02c372fa2e7637c432759e7a1d4db56e9e`
**Status:** `DESIGN_FROZEN_NOT_IMPLEMENTED`

## Decision

The exact-runtime P5/P6 execution authorization is a separate, single-use,
short-lived control plane bound to the merged implementation and accepted V5
capability record.

## Bound implementation

- implementation merge commit: `9cc06c02c372fa2e7637c432759e7a1d4db56e9e`
- design record: `4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2`
- implementation record: `6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d`
- implementation review: `151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d`
- notebook: `cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7`
- runtime script: `d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67`
- wrapper code: `55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c`

## Execution ceiling

```text
kaggle_sessions=1
saved_versions=1
model_requests=6
worker_starts=3
model_loads=3
hidden_retries=0
replacement_workers=0
external_network_requests=0
benchmark_trajectory_requests=0
external_spend=0
```

## Freshness and platform

```text
platform=T4_X2
allocated_gpu_count=2
internet_enabled=false
platform_observation_max_age_minutes=15
operator_confirmation_max_age_minutes=15
authorization_window_max_minutes=240
```

## Lifecycle

Live authority begins only at `ISSUED`.

Terminal dispositions:

```text
CONSUMED
EXPIRED_UNUSED
CANCELLED_UNUSED
ABANDONED_BEFORE_EXECUTION
OUTCOME_UNKNOWN
```

Every terminal disposition makes the authorization permanently non-reusable.

## Current claims

```text
live_authorization_issued=false
runtime_execution_authorized=false
p5_p6_exact_runtime_requalified=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`IMPLEMENT_EXACT_RUNTIME_P5_P6_EXECUTION_AUTHORIZATION_V1_ISSUER`

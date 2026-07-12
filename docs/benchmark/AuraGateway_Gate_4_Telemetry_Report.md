# AuraGateway Gate 4 Telemetry Report

## Decision

```text
Gate 4: passed on deterministic synthetic fixtures
Fixtures: 8
Negative controls: 6
Measured execution: prohibited
Required next work: primary live-provider adapter
```

## Evidence

The fixture suite validates:

- cached-input-detail semantics;
- cache-creation/read semantics;
- local prompt-evaluation timing;
- unavailable telemetry;
- missing cache fields;
- invalid cache denominators;
- missing latency fields;
- missing pricing schedules.

All expected cache, latency, and estimated-cost decisions matched.

```text
Fixture SHA-256:
a18ac6c8e09589be3a9173bfc75ccbd0fa3fa805bba84d94911ee4840817dcee

Report SHA-256:
185d26a3d0f117a3054bef7f1390117a199232d3d66d3f66c7d84c8b1f65d624
```

## Controls proved

- Unknown values remained `None`.
- Provider-specific token meanings remained distinct.
- Local timing remained separate from provider cached-token evidence.
- Invalid denominators produced `CACHE_SEMANTICS_MISMATCH`.
- Missing pricing blocked estimated-cost claims.
- Raw provider payloads were not persisted.
- JSON key-order changes did not change typed telemetry meaning.

## Remaining work

Gate 4 fixture validation does not establish live provider compatibility. Phase 3 still requires a primary live-provider adapter, current documentation review, a bounded smoke test, and calibration against actual returned fields. Optional local runtime adapter work also remains.

## Non-claims

This report does not prove provider cache hits, provider cache residency, TTL, eviction, scheduling, current pricing, latency improvement, cost reduction, route safety, task quality, A/B/C comparability, or production readiness.

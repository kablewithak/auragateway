# AuraGateway OpenRouter Hy3 Adapter Dry Run

## Result

The generic OpenRouter adapter passed a seven-case fixture-only dry run.

```text
provider calls: 0
credential access: none
successful fixture cases: 5
expected rejected cases: 2
live execution authorized: false
```

## Covered observations

- cache fields absent;
- cache fields explicitly null;
- numeric zero;
- positive cache read;
- positive cache write;
- invalid numeric type rejected;
- completion/generation identity mismatch rejected.

## Request controls

Every accepted fixture request contains:

```text
provider.data_collection = deny
provider.zdr = true
manual provider order absent
session_id present
stream = false
temperature = 0
```

## Architecture boundary

The adapter uses a new extensible OpenRouter envelope because the legacy `ProviderName` enum is
hash-bound by the prior identifiability review. It reuses the protected prompt/output containers but
does not mutate historical evidence. A later integration decision can promote the extensible seam
without rewriting the closed provider lineage.

## Claims

Permitted:

- the adapter builds the frozen OpenRouter request shape;
- fixture responses preserve absent, null, zero, and positive cache states;
- fixture generation metadata reconciles route and session identity;
- privacy controls and no-manual-order policy are enforced;
- malformed cache fields and route mismatches fail closed.

Blocked:

- the Hy3 free route is privacy-compatible at runtime;
- Hy3 free returns numeric cache telemetry;
- Hy3 free uses prompt caching;
- multiple eligible endpoints exist;
- Condition C improves cache retention;
- a live capability probe is authorized;
- the pilot or retained benchmark is authorized.

## Next gate

```text
openrouter_hy3_capability_probe_authorization_review
```

That review must add an actual transport, preflight the current free route and account limit, reassess
whether TLA+ adds defect-finding value, and freeze the bounded live execution protocol before any key
is read.

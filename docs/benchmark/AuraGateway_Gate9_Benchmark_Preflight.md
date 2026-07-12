# AuraGateway Gate 9 Benchmark Runner Preflight

## Status

```text
Document version: 1.0.0
Phase: Phase 7 — Benchmark Execution and Statistical Analysis
Proof gate: Gate 9 — measured benchmark execution
Planning readiness: passed
Measured execution readiness: blocked
Provider execution performed: no
Measured execution permitted: no
```

## Purpose

This slice is the transition from synthetic harness construction to controlled benchmark execution.

It converts the frozen Benchmark Constitution into a deterministic run ledger and makes every remaining execution blocker machine-readable before a provider call can occur.

The implementation intentionally exposes no `run`, `resume`, or `rerun` command. The only commands are:

```text
validate-config
plan
verify
```

## North-star connection

AuraGateway's North Star is not the number of contracts, fixtures, or tests in the repository. It is the controlled A/B/C result answering whether deterministic context construction and cache-affinity routing reduce avoidable repeated input work, latency, or estimated cost without harming retrieval-grounded task quality or useful feedback retention.

This preflight slice is aligned only because it is the final execution-control seam immediately before bounded live dry runs and measured A/B/C trajectories. Additional synthetic governance work after this boundary would be scope drift unless it closes a blocker reported by this preflight.

## Deterministic run matrix

The planner expands the frozen Constitution 1.0.0 schedules into:

| Workload | Episodes | Replications | Conditions | Trajectories |
|---|---:|---:|---:|---:|
| Functional benchmark | 18 | 3 | 3 | 162 |
| Runtime microbenchmark | 6 | 10 | 3 | 180 |
| **Total** | — | — | — | **342** |

Each trajectory contains four turns.

```text
total trajectories: 342
total turns: 1,368
maximum attempts per turn: 2
maximum request attempts: 2,736
```

The maximum-attempt count is an upper bound, not a request target. Retry authorization remains subject to the Gate 5 definite-failure, retryability, route-stability, budget, and duplicate-protection rules.

## Planned-run identity

Every run ledger entry includes:

```text
schedule_index
run_id
comparison_pair_id
workload
episode_id
replication_id
condition_id
condition_order_index
cache_namespace_id
turn_count
maximum_request_attempt_count
```

Run IDs and cache namespaces are unique. Functional and runtime schedules preserve the frozen counterbalancing order. Input episode lists must be sorted and duplicate-free.

## Draft execution manifest

The draft pins the currently known:

- benchmark constitution identity;
- retrieval freeze and corpus identities;
- context and schema versions;
- Groq provider/model and adapter identity;
- telemetry evidence identity;
- route-policy versions;
- functional and runtime episode identities;
- quality rubric and blinded-review schedule;
- feedback evidence contract;
- retry, exclusion, rerun, denominator, statistical, and quality policies;
- source Git commit and dependency configuration.

The draft deliberately retains explicit `null` values instead of fabricating missing freeze assets.

## Current blockers

Measured execution remains blocked by:

```text
EXECUTION_MANIFEST_ASSETS_UNRESOLVED
EXECUTION_MANIFEST_NOT_FROZEN
PROVIDER_CONFIGURATION_NOT_READY
PROVIDER_LIVE_PROBE_NOT_PASSED
COST_BUDGET_NOT_DECLARED
```

### Unresolved execution-manifest assets

The current draft still requires:

- a versioned pricing schedule, source date, and currency if cost comparison remains in scope;
- a consolidated negative-control manifest identity;
- a fault-injection fixture identity;
- a privacy-verification report identity;
- a cross-condition isolation-test identity.

### Provider readiness

Repository evidence proves adapter calibration and telemetry semantics. It does not prove that the current shell has valid credentials or that a bounded live probe passes today.

The readiness asset stores only booleans and hashes. It never stores a credential value.

### Budget readiness

The request-count envelope covers the complete plan. A provider cost ceiling is not yet declared because no current benchmark pricing schedule has been frozen.

## Evidence-vault boundary

Public-safe evidence belongs under:

```text
evidence_vault/
```

Protected or transient review/provider material belongs under:

```text
.local/
```

Finalized evidence bundles are append-only. Raw prompts, provider payloads, protected review exports, secrets, and credentials are prohibited from public evidence.

## Commands

Validate the typed input and deterministic expansion:

```powershell
python -m auragateway.benchmark.preflight_runner validate-config --repo-root .
```

Regenerate the draft manifest, run ledger, report, and hash manifest:

```powershell
python -m auragateway.benchmark.preflight_runner plan --repo-root .
```

Verify persisted evidence against deterministic reconstruction:

```powershell
python -m auragateway.benchmark.preflight_runner verify --repo-root .
```

None of these commands imports or calls a provider adapter.

## Verification result

The frozen planning evidence proves:

- 342 deterministic run identities;
- 1,368 planned turns;
- a 2,736-attempt hard upper bound;
- unique cache namespaces;
- frozen functional and runtime counterbalancing;
- typed execution-manifest coverage;
- explicit unresolved fields;
- provider and budget blockers;
- execution disabled by default;
- reproducible metadata-only evidence.

## Next authorization step

The next slice must be a narrow execution-manifest freeze and bounded live-probe authorization slice. It should resolve the five reported blockers and add no measured-run command until the resulting frozen manifest and provider readiness evidence pass locally.

After that, execution order is:

1. bounded live dry run;
2. prefix negative-control calibration;
3. functional A/B/C execution;
4. runtime microbenchmark execution;
5. failed-run and exclusion review;
6. paired analysis and uncertainty tables;
7. final report and evidence bundle.

## Claim boundary

This slice proves deterministic benchmark planning and explicit execution blocking.

It does not prove provider readiness today, execution-manifest freeze, measured A/B/C completion, provider cache hits, latency improvement, cost reduction, task-quality non-inferiority, feedback improvement, benchmark success, deployment safety, or production readiness.

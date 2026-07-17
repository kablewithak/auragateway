# ADR: Reconcile the Full A/B/C Execution-Manifest Draft

**ADR ID:** `ADR-LOCAL-ABC-FULL-ABC-EXECUTION-MANIFEST-DRAFT-RECONCILIATION`  
**Date:** 2026-07-18  
**Status:** Accepted  
**Source merge:** `d6531fdc0b27892dcc299598f9f251fa157434dc`

## Context

PR #96 proved that the repository already contains most of the assets required for the future full A/B/C
execution manifest. It also proved that the existing Gate 9 draft and planned-run ledger are stale because
they predate:

- explicit executed-prompt identity propagation;
- evidence-derived cleanup classification;
- the frozen full A/B/C integration design;
- the implemented shared scoring, cleanup, trace, and comparison-preflight boundaries; and
- exact condition-specific configuration fingerprints.

The old Gate 9 lineage is still useful as a source for the frozen episode selection and baseline manifest
assets. It is not valid as the current execution-manifest draft.

## Decision

Add a local-only preflight-v2 reconciliation boundary that:

1. verifies execution from the exact PR #96 merge;
2. captures exact package versions from the active validated virtual environment;
3. derives canonical A, B, and C configuration fingerprints from the PR #95 adapters;
4. rebuilds all 342 planned trajectories with their condition fingerprints;
5. binds the current integration design, implementation, inventory, trace fields, pricing, negative
   controls, fault fixtures, and privacy verification;
6. writes a current non-executing execution-manifest draft;
7. writes a hash-bound reconciliation report and manifest; and
8. preserves provider readiness, cost approval, isolation evidence, and Gate 10 outputs as unresolved.

The generated lineage lives under:

```text
data/evals/benchmark/preflight-v2/
```

## Dependency identity

A dependency lock must represent the environment that passed the repository gates. The generator records:

```text
CPython version
AuraGateway project version
pyproject.toml SHA-256
groq version
pydantic version
mypy version
pytest version
ruff version
setuptools version
```

Generation fails if a required distribution is missing. The lock is not synthesized from version ranges
or copied from another environment.

## Condition configuration fingerprints

Each condition fingerprint binds:

```text
condition adapter identity
dependency lock
integration design
integration implementation
Benchmark Constitution
retrieval configuration
prompt policy
response schema
action schema
provider/model alias
provider adapter
pricing schedule
benchmark runner version
```

This makes the `configuration_fingerprint` field required by the PR #95 comparison preflight concrete and
queryable before execution.

## Run ledger

The v2 ledger is regenerated from the frozen episode selection and counterbalanced schedules. It contains:

```text
functional trajectories=162
runtime trajectories=180
total trajectories=342
total turns=1368
maximum request attempts=2736
```

Every run carries the fingerprint for its own condition. Run IDs, comparison-pair IDs, replication IDs,
and cache namespaces remain deterministic and unique.

## Execution posture

```text
planning_ready=true
draft_current=true
execution_enabled=false
measured_execution_ready=false
measured_execution_permitted=false
provider_execution_authorized=false
gpu_execution_authorized=false
claim_generation_permitted=false
```

This work performs no model request, provider call, notebook execution, GPU execution, credential access,
or external spend.

## Alternatives rejected

### Reuse Gate 9 v1 unchanged

Rejected because its dependency identity, Git lineage, ledger, and execution-manifest draft predate the
hardening and integration work.

### Invent a dependency lock in the implementation ZIP

Rejected because an environment lock must describe the user's validated virtual environment, not the
assistant's build environment.

### Freeze Gate 10 in the same slice

Rejected because provider readiness and explicit budget approval remain unresolved, and cross-condition
isolation is generated from the reconciled ledger only during the freeze boundary.

### Add provider probing to reconciliation

Rejected because provider calls require a separate bounded authorization and are not needed to make the
local draft current.

## Consequences

### Positive

- The stale Gate 9 lineage is replaced by a current, reproducible preflight-v2 lineage.
- Every planned trajectory binds a concrete A/B/C configuration fingerprint.
- Dependency identity reflects the actual validated local environment.
- Static freeze inputs become current and hash-bound.
- External blockers remain explicit rather than being hidden inside a generic not-ready status.
- Gate 10 can later consume one current local planning boundary.

### Negative

- Generated JSON differs across environments when installed package versions differ.
- The generator must run from the exact source merge and active project virtual environment.
- Gate 10 freeze code still requires a later alignment slice before consuming the v2 wrapper directly.
- Provider readiness and cost approval remain separate work.

## Next gate

```text
full_abc_provider_readiness_and_budget_review
```

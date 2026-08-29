# ADR: Final 342 Requirements and Precedence Reconciliation V1

**Decision ID:** `FINAL_342_REQUIREMENTS_PRECEDENCE_RECONCILIATION_V1`
**Date:** 2026-08-29
**Source main:** `ac187cf08643b53786f0c8c5e39d6be67ba61beb`
**Execution authority:** None

## Context

G10 froze the final repetition, statistical, quality, and warm/reset contracts. G11.0 then froze the current final-342 runtime architecture. G11.1 implemented the non-authorizing control core and G11.2 rehearsed an inert transaction wrapper.

The first G11.3 execution-manifest candidate was deliberately not promoted after remote semantic review found three contract-closure problems:

1. the historical manifest requirements still describe hosted-provider-era fields that are not yet mapped to the exact local-vLLM final producer;
2. the historical freeze procedure places provider readiness before manifest freeze while the accepted transaction-bound architecture places fresh platform observation after issuer qualification and before the governed execution; and
3. the historical `git_commit_hash` intent cannot be implemented as a same-commit self-reference without recursive Git identity.

The candidate therefore proved deterministic manifest construction, but not complete requirements closure.

## Decision

Do not patch or merge the rejected G11.3 candidate. Preserve `main` at the merged G11.2 subject and insert a requirements/precedence reconciliation boundary before final producer closure and manifest freeze.

### Authority precedence

Use this explicit order when sources differ:

1. Benchmark Constitution 1.0.0 controls scientific rules, causal contrasts, eligibility, retries/exclusions/reruns/denominators, quality, statistics, privacy, and claim language.
2. G10 controls the final 342-run repetition plan, primary runtime endpoint, statistics, quality non-inferiority, and warm/reset analysis policy.
3. G11.0 controls the current final local-vLLM runtime topology and final-run sequencing.
4. Execution Manifest Requirements 1.1.0 remains the baseline field inventory and freeze intent except where a higher-ranked accepted authority is explicitly specialized here.
5. Preflight-v3 supplies current planning identities and accepted asset hashes but is not the final execution manifest or authority.
6. Historical freeze-v1 is immutable lineage only and is not a template for the current local-vLLM final manifest.
7. Unmerged candidate state has no authority.

No historical source is rewritten.

## Exhaustive requirements coverage

The deterministic reconciliation covers all 69 fields named by Execution Manifest Requirements 1.1.0 and all 13 freeze-procedure steps exactly once.

Existing accepted corpus, retrieval, context, evaluation, fault/privacy, schedule, timeout, retry, exclusion, rerun, denominator, statistical, quality, and TTL controls remain binding inputs to the eventual final manifest.

Four field groups remain blocking before manifest freeze:

- final benchmark-runner / evidence-bundle / Python / dependency identity;
- local-vLLM mapping of provider-era runtime and telemetry fields;
- pricing/currency scope for any monetary cost claim family; and
- local worker-route mapping of historical provider-oriented route fields.

Those are owned by `G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1`.

## Platform-readiness sequencing

The old generic pre-freeze provider-readiness probe is explicitly superseded for the final transaction-bound local runtime.

The accepted sequence is:

`producer closure -> complete offline rehearsal -> manifest freeze -> static authority binding -> issuer qualification -> fresh human authority / platform observation -> one governed execution`

Fresh platform state is observational evidence. It is intentionally not frozen as static manifest configuration.

## Git custody without recursive identity

Separate two identities:

- `source_subject_commit`: the predecessor repository state from which final manifest bytes are materialized;
- `first_containing_commit`: the first Git commit whose tree contains those exact manifest bytes.

The final manifest does not embed its own containing commit SHA. After the manifest commit exists, a separate custody receipt binds:

- manifest semantic SHA-256;
- manifest file SHA-256;
- source-subject commit; and
- first-containing commit.

The repository G11 freeze gate is not promoted before that custody receipt exists and validates.

## Producer closure now required

Before manifest freeze, G11.3B must prove the exact final evidence-producing graph for:

- request transport and worker startup;
- runtime trace binding to the final manifest;
- typed measured evidence bundle production;
- request-attempt/action reconciliation persistence;
- protected measured-review export and safe digest receipt;
- primary/secondary failure persistence;
- teardown and cleanup evidence;
- provider-era to local-vLLM field compatibility;
- pricing/cost claim scope; and
- typed post-run analysis inputs.

This is a closure/inventory gate first. Reuse of accepted V2 components is preferred when exact semantics match; missing final capabilities require versioned successor components rather than mutation of historical executed code.

## Safety state

```text
REQUIREMENTS_INVENTORY_COMPLETE=true
REQUIREMENTS_PRECEDENCE_ESTABLISHED=true
PRODUCER_CLOSURE_REQUIRED=true
MANIFEST_FREEZE_PERMITTED=false
EXECUTION_MANIFEST_FROZEN=false
FINAL_MEASURED_ABC_EXECUTION_AUTHORIZED=false
NEW_EXECUTION_AUTHORIZED=false
EFFECT_CLAIMS_PERMITTED=false
MODEL_REQUESTS_PERFORMED=0
GPU_EXECUTION_PERFORMED=false
KAGGLE_EXECUTION_PERFORMED=false
```

## Next gate

`G11_3B_FINAL_EXECUTION_PRODUCER_CLOSURE_V1`

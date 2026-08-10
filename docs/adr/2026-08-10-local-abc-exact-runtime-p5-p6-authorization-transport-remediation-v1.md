# ADR: Exact-Runtime P5/P6 Authorization Transport Remediation V1

**Date:** 2026-08-10
**Status:** Accepted for successor implementation
**Base main:** `e7e9dea0ebfac320ea480e003e46fd0346c40a56`

## Context

Governed Exact-Runtime P5/P6 Requalification V1 saved version `341454766`
failed at the authorization boundary before runtime installation. The accepted
failure classification is:

`AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE`

A CPU-only inspection in saved version `341466979` proved that the canonical
authorization was present exactly once under the realized Kaggle dataset path,
but the V1 consumer's one-level pattern returned zero candidates.

The V1 executed notebook, runtime template, implementation review, implementation
record, and failure evidence are immutable diagnostic lineage. They are not
patched or reinterpreted.

Historical AuraGateway control-plane work supplies three relevant mechanisms:

1. PR #112 materialized short-lived authorization/control data through a
   dedicated CPU-only notebook output.
2. PR #114 proved that global recursive filename uniqueness is unsafe and
   corrected discovery to resolve a governed producer/root before validating an
   exact flat file set.
3. PR #115 proved that a current producer must round-trip through the actual
   consumer contract before another expensive execution is authorized.

PR #222 further separated producer-owned historical facts from consumer-owned
current policy. PR #224 established the rule that an executed diagnostic harness
is preserved while a corrected successor is built.

## Decision

Create Exact-Runtime P5/P6 Requalification V2 as a sibling successor.

V2 preserves the V1 behavioral P5/P6 contract and exact runtime/model identity.
The only intended semantic change is the authorization transport/discovery
boundary.

The future authorization flow is:

```text
local single-use issuer
-> CPU-only authorization control materializer
-> saved Kaggle notebook output
-> one governed producer/root
-> exact flat three-file validation
-> authorization hash/size and receipt cross-binding
-> existing authorization semantic validation
-> runtime installation
```

The control package contains exactly:

```text
execution_authorization_v1.json
control_package_manifest.json
materialization_receipt.json
```

The governed producer is identified by both:

```text
notebook token: ag-p5-p6-auth-control-v1
output directory: ag_p5_p6_auth_control_v1
```

Only after that root is uniquely resolved may the authorization filename
participate in discovery.

## Ownership boundary

The materializer owns transport facts only:

- producer notebook identity;
- producer output-directory identity;
- authorization filename;
- authorization byte SHA-256 and size;
- exact flat file count;
- control-manifest SHA-256;
- proof that no runtime/GPU/model execution occurred.

The V2 consumer owns current authorization policy:

- authorization scope and decision;
- lifecycle;
- V2 runtime-script SHA-256;
- V2 implementation-review SHA-256;
- remediation design-record SHA-256;
- accepted V5 capability identity;
- single-use semantics;
- request/worker/model-load ceilings;
- live issuance/expiry window.

Historical authorization bytes are not retroactively extended.

## Rejected alternatives

### Patch V1 in place

Rejected. V1 has executed and is now immutable diagnostic lineage.

### Replace the shallow glob with `INPUT_ROOT.rglob(AUTHORIZATION_FILENAME)`

Rejected. PR #114 already demonstrated a namespace-collision false negative
caused by unscoped global filename uniqueness.

### Keep direct authorization-dataset transport and encode the observed depth

Rejected. That couples the consumer to Kaggle's realized wrapper topology rather
than to a governed producer contract.

### Issue a new authorization in this tranche

Rejected. A future issuer must bind the merged V2 implementation and runtime
script identities, which do not exist until this tranche is merged.

## Regression gate

Before a future V2 authorization issuer may merge, repository tests must prove:

- the exact observed V1 direct-dataset topology still reproduces the old shallow
  false negative;
- one governed V2 control root resolves successfully;
- an unrelated duplicate authorization filename is ignored;
- multiple governed roots fail closed;
- extra or missing control members fail closed;
- unsafe member types fail closed;
- authorization hash/size drift fails closed;
- materialization-receipt drift fails closed;
- authorization validation still occurs before runtime installation;
- the V1 and V2 behavioral function bodies remain unchanged outside the approved
  transport/lineage functions.

## Consequences

This remediation increases one CPU-only materialization step before governed GPU
execution, but removes an implicit filesystem-depth assumption and restores a
previously proven producer/root contract.

No runtime execution authority is created.

```text
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

## Next gate

`DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION_AUTHORIZATION_ISSUER`

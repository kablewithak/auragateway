# AuraGateway CUDA 12.9 P3-P6 Runtime Diagnostic Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

## Purpose

Provide a repository-native, inspectable authorization lifecycle for the
sequential P3-P6 runtime diagnostic without conflating issuer implementation
with live authority.

## Bound implementation

This issuer is rebuilt after PR #173 and binds the remediated
generated notebook, implementation record, template, and source.

- PR #173 remediation merge: `d0ef674128479f191149e12987a7f952d82c2782`;
- original implementation feature commit: `603b412f6f4c511bbf6e18d5e08d7a480986743e`;
- qualification-remediation feature commit: `d69d464336e8099c718b1d766ff8d5fdfacc779c`;
- implementation record: `98762563de31eef4272705af5d647de96a467c6525d3a20dda1543f356880916`;
- notebook: `bf2e02f9bfe5e663942dbcc0ada2cc62c799d7a8b81da813b3d7cb2ddca194b7`;
- model snapshot: `84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94`.

## Hard budget

- one Kaggle session;
- one offline runtime installation;
- three model loads;
- three worker starts;
- five model requests;
- 32 output tokens per request;
- zero benchmark trajectories;
- zero external network requests;
- zero hidden retries;
- zero external spend.

## Safety controls

T4 x2, Internet off, loopback-only HTTP, no credentials, no customer data, no
raw prompt or output logging, explicit `TRITON_ATTN`, stop on first failure,
partial evidence retention, and deterministic failure reporting.

## Lifecycle

Issuer merged -> explicit operator confirmation -> transient untracked
authorization -> immediate verification -> one governed saved version ->
PASSED/FAILED/INTERRUPTED consumption -> separate evidence acceptance.

## Non-claims

This tranche does not prove worker startup, model loading, inference, prefix
reuse, reset, dual-worker isolation, measured A/B/C effects, deployment, or
production readiness.

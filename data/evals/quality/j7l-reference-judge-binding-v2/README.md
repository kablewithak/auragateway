# J7L Reference Judge Binding V2

Status: **binding frozen; reference execution inactive pending separate authorization**.

This additive V2 replaces the V1 assumption that Huawei must expose an immutable
provider revision before the reference judge can be bound.

It does not mutate V1.

## Provider identity

The V2 identity binds:

- provider: `huawei_modelarts_maas`
- region: `ap-southeast-1`
- exact chat endpoint
- requested model: `glm-5.2`
- qualified returned model: `glm-5.2`
- named-tool contract SHA-256
- model semantic projection SHA-256
- successful AuraGateway qualification result SHA-256

Huawei did not expose a provider model revision in the governed qualification.
V2 records that fact as:

`NOT_EXPOSED_BY_PROVIDER`

No revision is fabricated from the model ID.

## Qualification evidence

Qualification result SHA-256:

`ef14040d8d33c89434f8a5476c4444898441b3a7d4794e8d08b2a71ea1b9f936`

Observed qualification:

- exact `glm-5.2` catalog visibility
- successful `glm-5.2` inference
- forced `submit_reference_judgment`
- thinking disabled
- reasoning tokens = 0
- usage accounting observed
- prompt tokens = 14,655
- completion tokens = 247
- total tokens = 14,902

## Operational reference budget

The stale V1 8,500-token input planning assumption is not reused.

V2 freezes an experiment-control ceiling instead:

- 48 planned reference requests
- serial execution
- max 1 request in flight
- max 768 completion tokens per request
- max 20,000 total provider-reported tokens per request
- max 960,000 provider-reported tokens for the reference phase
- no automatic retry
- no replay of a completed case
- no retry of an ambiguous attempted case
- resume is allowed only across already completed cases in the same logical authorization
- R0 external-spend ceiling
- no paid fallback

This is **not** a claim about Huawei's maximum context window.

## Audit schedule

Before the first provider request, the inactive runner deterministically freezes:

- all 24 terminal/non-substantive + ontology-near-miss cases; and
- 4 additional spot checks: the first two ordinary-clean and first two clear-failure
  cases in frozen case order.

The audit may not rewrite model-derived references. Material disagreement invalidates
the reference set.

## Authority

This tranche authorizes no network activity.

- provider requests authorized: false
- reference execution authorized: false
- Jev execution authorized: false
- credential access authorized: false

Next gate:

`AUTHORIZE_J7L_REFERENCE_EXECUTION_V2`

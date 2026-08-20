# AuraGateway C4 Paragraph-Order Behavioral Differential Execution Authorization V1

## Status

`IMPLEMENTED_NOT_ISSUED`

This tranche implements the transaction-bound single-use authorization issuer for the
frozen C4 paragraph-order behavioral differential. It does not issue live authority,
perform a model request, start a worker, load the model, execute Kaggle, or claim a
paragraph-order mechanism.

## Bound authorities

- authorization-design merge commit:
  `2e0e09b65023397f30d73a406f3f60e7090c85b1`
- authorization-design record SHA-256:
  `8305ebb153f962015c28de98bd6fcf6feeb202482163c6cce3f0caf08cc3d143`
- implementation merge commit:
  `7e037596de1a74038583a85ed81d46ec12debbac`
- implementation review SHA-256:
  `355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595`
- implementation record SHA-256:
  `c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386`
- successor runtime SHA-256:
  `1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0`

## Authorization contract

The issuer preserves the accepted `TRANSACTION_BOUND_EXECUTION_ARTIFACT`
architecture:

1. static repository code is execution-inert;
2. live issuance requires synchronized clean `main`;
3. one fresh dynamic SHA-256 challenge must be manually retyped;
4. the authorization binds the exact design, implementation, issuer source, generator
   template, runtime payload, runtime contract, execution budget, experiment contract,
   platform contract, timestamps, and authorization window;
5. transaction identity is SHA-256 over canonical authorization-body bytes;
6. the generated executable admits only a live bound authorization;
7. a durable platform observation is required before the one Save & Run All;
8. every terminal attempt consumes authority; unchanged replay is not authorized.

## Frozen experiment

Request order is:

`CONTROL, TREATMENT, TREATMENT, CONTROL, CONTROL, TREATMENT`

Budget is exactly:

- 1 Kaggle session;
- 1 Save & Run All;
- 6 model requests;
- 6 model loads;
- 6 worker starts;
- 6 worker teardowns;
- 32 maximum output tokens per request;
- 0 hidden retries;
- 0 replacement observations;
- 0 external network requests;
- 0 benchmark-trajectory requests;
- R0 external spend.

The control must reproduce the historical C4 failure anchor before treatment is used
for paragraph-order inference.

## Wrapper admission

The generated wrapper verifies:

- canonical embedded authorization bytes;
- transaction ID;
- design/implementation/issuer/runtime/generator identities;
- canonical SHA-256 identities of runtime, budget, experiment, and platform contracts;
- live authorization window;
- machine-observed two-GPU topology.

It does not perform a network probe. Internet-off remains a bound platform policy plus
the separately persisted Kaggle settings observation.

The wrapper explicitly treats `SystemExit(None)` and `SystemExit(0)` from the bound
runtime as successful process completion. Non-zero `SystemExit` and other primary
exceptions are preserved as primary failures; reporting failure remains secondary.

## Non-claims

This tranche does not establish:

- paragraph order as root cause;
- a general model mechanism;
- canonical-corpus global invalidity;
- P5 cache requalification;
- P6 worker-state requalification;
- final A/B/C effects;
- production readiness;
- runtime anti-replay resistance.

## Next gate

`MERGE_THEN_ISSUE_FRESH_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1`

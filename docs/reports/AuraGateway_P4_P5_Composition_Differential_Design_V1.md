# AuraGateway P4/P5 Composition Differential Design V1

## Status

`DESIGN_FROZEN_NOT_EXECUTED`

## Problem

The current exact-runtime P5/P6 transaction reached C3 and returned a response
that was not valid JSON.

P5 and P6 were not reached.

The current architectural hypothesis is that the previously qualified
least-constrained output contract was reused after a material message-context
change.

That hypothesis has not yet been counterfactually tested on the current
runtime.

## Differential

### A: SIMPLE_CONTROL

`system -> final JSON object`

### B: COMPOSED_P5

`system -> synthetic cache context -> assistant acknowledgement -> final JSON object`

Both cases use the current P5/P6 final object:

`{"probe":"exact-runtime-p5-p6","value":1}`

Both cases hold the model, revision, runtime, backend, generation controls, and
worker realization fixed.

The only intended treatment variable is:

`MESSAGE_COMPOSITION_ONLY`

## Request plan

The frozen six-request order is:

`A, B, B, A, A, B`

Three observations are therefore collected for each case.

No hidden retries are permitted.

## Decision contract

- A `3/3`, B `0/3`: `COMPOSITION_REGRESSION_SUPPORTED`
- A `3/3`, B `3/3`: `COMPOSITION_HYPOTHESIS_NOT_REPRODUCED`
- A not `3/3`: `SIMPLE_CONTROL_NOT_RELIABLE`
- any other mixed pattern: `NON_DETERMINISTIC_OR_AMBIGUOUS`

A mixed result does not authorize ad hoc experimentation. A bounded Case C must
first be designed and merged.

## Evidence and privacy

Raw prompts and raw model outputs are not retained.

Only the frozen metadata-safe diagnostic fields may be persisted.

Customer data and credentials are prohibited.

## Authority

Frozen design record SHA-256:

`5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1`

Current authority state:

- runtime execution authorized: false;
- new execution authorized: false;
- runtime fix authorized: false;
- measured A/B/C execution authorized: false;
- model requests performed: 0.

## Next gate

`IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_DIFFERENTIAL_V1`

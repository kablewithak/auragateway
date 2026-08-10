# AuraGateway Transaction-Bound Execution Authorization Architecture V1

## Executive result

Adopt `TRANSACTION_BOUND_EXECUTION_ARTIFACT` for the Exact-Runtime P5/P6
successor authorization boundary.

The architecture keeps fresh human authority, hard budgets, expiry,
implementation identity, terminal lifecycle, and evidence traceability while
removing authorization-specific Kaggle transport.

## Current V2 coupling being retired

Current V2 requires:

- issuer-side authorization transport round-trip validation;
- an authorization control producer notebook and output directory;
- an exact flat three-file authorization package;
- runtime discovery of that governed authorization input before installation;
- a separate post-issue materialization/attachment step.

Those mechanisms are coherent inside the V2 design but are not retained as
preferred architecture.

## Successor boundary

The successor will generate one deterministic transient executable after
fresh human authorization.

The executable will embed and validate the canonical authorization envelope
and exact static runtime identity before runtime installation. Kaggle inputs
are limited to durable runtime and model artifacts.

Platform observation occurs after final executable generation and before
Save & Run All, avoiding a circular dependency between final artifact
identity and pre-issuance observation.

## Assurance parity

The successor must preserve V2 assurance for:

- authorization presence at execution admission;
- exact implementation binding;
- runtime/model contract identity;
- hard budgets;
- freshness and expiry;
- governance single-use;
- terminal consumption;
- evidence traceability.

It is rejected if those controls weaken merely to reduce operator burden.

## Explicit limitations

Runtime anti-replay is not established. Malicious-operator resistance is not
established. Cryptographic signing is not introduced.

More than one observed execution for one transaction invalidates governed
acceptance and requires reconciliation.

## Implementation acceptance gates

The next implementation tranche must prove deterministic generation,
authorization admission before installation, topology without authorization
inputs, primary-failure preservation, and lifecycle terminalization when
evidence packaging fails.

No GPU execution is authorized by this architecture tranche.

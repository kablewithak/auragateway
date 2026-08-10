# ADR: Transaction-Bound Execution Authorization Architecture V1

**Date:** 2026-08-11
**Status:** Proposed architecture
**Base main:** `a9c6632b29e9b470de0497ca6d72a2e2c2c91f62`

## Context

Exact-Runtime P5/P6 V2 preserved strong authorization invariants but moved
authorization enforcement into Kaggle input topology. The current issuer
requires authorization transport round-trip validation and directs the
operator to materialize and attach a governed authorization control output.
The current runtime contract binds a producer notebook, producer output
directory, flat three-file control package, and authorization discovery
before runtime installation.

That architecture prevented accidental ungoverned execution at the cost of
a second producer/consumer schema, an authorization-specific Kaggle input,
additional operator steps, and a new class of control-plane drift.

Historical accepted executions show that fresh human authority, hard
budgets, exact implementation identity, terminal consumption, and simple
Kaggle topology can coexist. The V2 outcome-unknown incident also showed
that terminal lifecycle handling must remain available even when evidence
packaging fails.

## Decision

Adopt `TRANSACTION_BOUND_EXECUTION_ARTIFACT` as the successor authorization
architecture.

Authorization remains mandatory. Enforcement moves from authorization-
specific Kaggle input topology into the identity and admission contract of
the executable artifact itself.

The successor workflow SHALL NOT require:

- an authorization-specific Kaggle dataset or mounted input;
- an authorization control producer notebook;
- recursive or filename-based authorization discovery inside Kaggle;
- a manually authored confirmation JSON file.

The successor workflow SHALL preserve:

- one explicit fresh human authorization action;
- exact static implementation identity;
- exact runtime/model contract identity;
- hard execution budgets;
- authorization issue and expiry times;
- single-use governance semantics;
- terminal disposition after every attempted execution;
- immutable evidence and traceability.

## Transaction identity

The canonical authorization bytes define the transaction ID:

`transaction_id = sha256(canonical_authorization_bytes)`

The generated executable binds:

- transaction ID;
- canonical authorization bytes;
- static runtime payload SHA-256;
- generator contract SHA-256;
- runtime/model contract identity;
- execution budget;
- issued-at and expires-at timestamps.

The execution payload identity is domain-separated from notebook-container
identity. Whole-notebook SHA-256 is not the semantic execution identity
because notebook metadata and outputs may be rewritten by Kaggle.

For the same static implementation, canonical authorization, and generator
contract, generation must be byte-deterministic. Regeneration before
execution is permitted only when the regenerated executable is byte-
identical. A different executable requires fresh authority.

## Runtime admission

The static repository implementation is inert with respect to governed GPU
execution. Only a transaction-bound generated executable may cross runtime
admission.

Before runtime installation or model construction, the generated wrapper
verifies its embedded authorization envelope, static runtime payload
identity, transaction identity, execution budget, and live authorization
window.

Authorization must be live at runtime admission. Once admitted within the
valid window, a bounded execution may complete after expiry.

This architecture does not claim cryptographic tamper resistance against a
malicious operator. Trusted signing and a durable nonce service are outside
the current threat model.

## Platform observation sequencing

Pre-issuance platform observation is removed from the authorization
dependency because it creates a circular dependency with final executable
generation.

Instead:

1. fresh human authority binds the required platform policy;
2. the transaction-bound executable is generated;
3. the operator imports/configures that executable on Kaggle using only the
   durable runtime and model inputs;
4. a fresh platform observation is recorded before Save & Run All;
5. runtime admission verifies machine-observable topology before governed
   work;
6. repository acceptance binds the platform observation, transaction ID,
   saved version, terminal evidence, and zero-network evidence.

Platform observation is an execution-admission/acceptance condition, not a
separately mounted runtime authorization artifact.

## Replay semantics

`single_use` remains a governance invariant, not a claim of runtime
anti-replay.

More than one observed execution for the same transaction ID invalidates
governed acceptance and requires reconciliation.

Runtime anti-replay and malicious-operator resistance are not established.

## Failure handling

The successor runtime must preserve the first causal exception separately
from teardown, cleanup, evidence-packaging, and terminalization failures.

Secondary failures must never replace or mask the primary failure.

Authorization must remain terminalizable even when the governed evidence
package is absent or incomplete.

## Operator-burden regression gate

Relative to V2, the successor must have:

- zero authorization-specific Kaggle inputs;
- zero authorization producer notebooks;
- no manual confirmation JSON construction;
- at most two local control commands after merge;
- one Kaggle Save & Run All action;
- only durable runtime/model Kaggle inputs.

A successor that preserves authorization semantics but exceeds these
operator or topology budgets is rejected.

## Implementation seam

This ADR does not modify the V2 runtime, issuer, notebook, or historical
evidence.

The implementation successor should introduce a new versioned boundary
rather than rewrite executed or identity-bound V2 artifacts.

The implementation tranche must separately prove:

- deterministic artifact generation;
- embedded authorization admission before runtime installation;
- exact runtime/model/budget binding;
- platform-observation lifecycle without circularity;
- imported Kaggle topology containing no authorization-specific input;
- primary-failure preservation under cleanup/evidence failure;
- non-reuse reconciliation for repeated transaction execution.

## Non-claims

This ADR does not establish:

- current-runtime P5/P6 qualification;
- runtime anti-replay;
- cryptographic sealing;
- malicious-operator resistance;
- that the V2 symlink defect is remediated;
- authority for another Kaggle GPU execution.

## Next gate

`IMPLEMENT_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_V1`

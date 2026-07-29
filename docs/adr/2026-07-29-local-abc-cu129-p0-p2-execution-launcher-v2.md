# ADR: Dedicated CUDA 12.9 P0-P2 Execution Launcher V2

## Status

Accepted for local implementation and validation. Kaggle execution remains unperformed.

## Context

The accepted source materializer output and metadata inspection prove the exact
P0-P2 diagnostic source package. Historical AuraGateway Kaggle lineage attaches
successful notebook output directly to downstream notebooks. A separate Kaggle
Dataset object is not required and must not become a new gate.

The existing full A/B/C launcher is not an appropriate integration point. It is
a model-serving qualification boundary with authorization, workers, model
requests, and a six-probe execution core. The P0-P2 diagnostic is model-free,
worker-free, stop-on-first-failure, and consumes only one runtime installation
attempt plus one minimal Triton kernel attempt.

## Decision

Create a dedicated generated launcher that:

1. discovers the accepted materializer notebook output by receipt identity;
2. validates the receipt, inventory, checksum manifest, and three source files;
3. validates the exact unexecuted diagnostic notebook SHA-256;
4. compiles and executes its code cell exactly once;
5. validates the resulting diagnostic evidence and action budgets;
6. emits bounded launcher success or failure evidence;
7. never falls through into the full A/B/C qualification core.

The launcher requires two direct notebook-output inputs: the accepted P0-P2
source materializer output and the existing governed CUDA 12.9 wheelhouse output.
It uses T4 x2, Internet Off, and no secrets.

## Rejected alternatives

- Mutate the full A/B/C launcher: rejected because it couples platform diagnosis
  to model-serving authorization and worker behavior.
- Create a standalone Kaggle Dataset: rejected because historical notebook-output
  lineage already works and the extra object created an empty-resource loop.
- Execute the diagnostic notebook manually: rejected because it weakens source
  identity, evidence validation, and single-attempt enforcement.
- Add retry logic: rejected because retries would consume diagnostic evidence
  without increasing feedback quality.

## Consequences

The P0-P2 diagnostic gets a narrow, inspectable execution boundary. Success does
not authorize model loading, workers, inference, benchmark trajectories, or the
full Triton qualification attempt. The output determines whether the next gate is
explicit Triton attention backend implementation or platform-failure
classification.

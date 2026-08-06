# ADR: Accept P4 Output-Contract Diagnostic V1 as a Governed Runtime-Import Failure

**Date:** 2026-08-06  
**Status:** Accepted for repository implementation

## Context

Kaggle saved version `340622392` executed P4 Output-Contract Diagnostic V1 under the exact single-use V2 authorization issued from main commit `73f5962ed6852b744c3fed8e1a2e7de4fb424462`. The authorization was consumed with outcome `FAILED` and is non-reusable.

The governed run passed runtime source identity, model-snapshot validation, wheelhouse validation, and offline runtime installation. The one target-runtime import-closure subprocess returned code `1`. Worker startup was not attempted. No model was loaded, no worker was started, and no model request occurred. The terminal harness materialized the expected evidence contract, preserved the failed stage, finalized teardown as not required, and passed scratch cleanup.

The import report preserved stdout and stderr SHA-256 values but intentionally excluded raw import output. Therefore the evidence proves the first divergence but does not expose the import exception.

## Decision

Accept saved version `340622392` as an `ACCEPTED_DIAGNOSTIC_FAILURE`.

Classify the first valid divergence as:

`RUNTIME_IMPORT_CLOSURE_FAILED`

Preserve:

- the exact V1 abandonment receipt;
- the exact V2 authorization and failed consumption receipt;
- the Kaggle terminal log;
- the browser-downloaded intake archive;
- the canonical runtime evidence ZIP;
- every extracted runtime report;
- explicit evidence limitations and non-claims.

Do not attribute root cause beyond:

`ROOT_CAUSE_UNRESOLVED`

## Rejected alternatives

- Do not replay the failed notebook unchanged.
- Do not reissue the consumed authorization.
- Do not claim the A-F output-contract cases failed; they were not executed.
- Do not rebuild the wheelhouse or replace the model without causal evidence.
- Do not attribute the divergence to Python import resolution, native loading, CUDA ABI, vLLM, or any other package from hashes alone.
- Do not weaken privacy by retaining unrestricted environment dumps, raw prompts, model outputs, or secrets.

## Consequences

The current evidence establishes that the exact P4 harness reached and failed the target-runtime import-closure boundary after successful offline installation.

P4 exact-object reliability, JSON-schema compatibility, P5, P6, and measured A/B/C remain unqualified.

The next gate is a separate `P4_RUNTIME_IMPORT_CLOSURE_DIAGNOSTIC_V1` that performs one offline import probe and records metadata-safe exception taxonomy sufficient to isolate the failing import boundary without loading the model, starting a worker, or making requests.

# ADR: P4 Output-Contract Diagnostic V1

Date: 2026-08-05
Status: Accepted for repository implementation

## Context

P3-P6 Runtime Diagnostic V5 reached a healthy one-worker TRITON runtime and returned an
HTTP 200 response for P4, but the model content was not valid JSON. The accepted failure
classification is `P4_OUTPUT_CONTRACT_HARNESS_WEAKNESS`, with a likely V5 prompt regression,
an unconstrained-generation boundary, and an inherited repetition penalty as contributors.
The exact failed content was intentionally not retained, so the causal classification is not
counterfactual experimental proof.

## Decision

Implement one six-case diagnostic that holds model, model revision, wheelhouse, GPU, backend,
temperature, top-p, seed, and token budget fixed. Vary only prompt wording, repetition penalty,
and JSON-schema constraint mode. Execute every case three times in a balanced sequence.

The implementation records response SHA-256, length, finish reason, token usage, JSON parsing
coordinates, edge character classes, markdown-fence detection, valid-JSON status, and exact
object status. It never records raw prompts or model output.

## Consequences

The diagnostic can distinguish prompt, repetition-penalty, and structured-output effects under
one pinned runtime lineage. Three repetitions remain diagnostic rather than statistical proof.
A separate merged authorization issuer is required before Kaggle execution. Request rejection
for schema cases is evidence and does not automatically invalidate healthy unconstrained cases.
Setup, model, worker, and transport failures remain fatal.

## Rejected alternatives

- replaying V5 unchanged;
- retrying malformed output until green;
- changing the model or runtime simultaneously;
- retaining raw failed output;
- treating one valid response as qualification;
- issuing execution authority in this implementation tranche.


## Evidence-contract completeness amendment

The runtime output contract is exact rather than illustrative. It includes the model-snapshot and
wheelhouse validation reports written before runtime installation. `failure_report_v1.json` is
unconditional: it records `FAILED` on terminal failure and `NOT_APPLICABLE` on successful
completion. Static regression coverage must prove parity between literal runtime writes and the
declared output contract before authorization may be implemented.

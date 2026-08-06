# AuraGateway P4 Output-Contract Diagnostic Failure Acceptance V1

## Decision

Accept Kaggle saved version `340622392` as a valid governed diagnostic failure.

```text
evidence_disposition=ACCEPTED_DIAGNOSTIC_FAILURE
lifecycle_outcome=FAILED
first_divergence=RUNTIME_IMPORT_CLOSURE_FAILED
reported_failure_code=P4_OUTPUT_CONTRACT_RUNTIME_FAILED
authorization_lifecycle=CONSUMED
authorization_reusable=false
unchanged_replay_authorized=false
root_cause_status=UNRESOLVED
```

## Established facts

- Main, implementation, notebook, model snapshot, wheelhouse, and issuer identities were bound by the V2 authorization.
- The previous unusable V1 authority was governed as `ABANDONED_BEFORE_EXECUTION`.
- Runtime source identity passed.
- Model snapshot validation passed.
- Wheelhouse validation passed.
- Offline runtime installation passed with return code `0`.
- The target-runtime import-closure probe returned code `1`.
- `PYTHONPATH` was configured to the exact target site.
- Raw import output was not retained.
- Worker startup was not run.
- Model loads, worker starts, model requests, hidden retries, network requests, benchmark requests, and external spend were all zero.
- Teardown was not required and scratch cleanup passed.
- The V2 authorization was consumed as `FAILED` against saved version `340622392`.

## Evidence limitation

The import report retains only:

- return code;
- target-site configuration status;
- stdout SHA-256;
- stderr SHA-256;
- absence of parsed version output.

It does not retain the exception class, failing import step, traceback frame, native-library target, or raw stderr. Root cause is therefore unresolved.

## Next diagnostic

Design a single-probe, offline P4 runtime-import diagnostic that records only metadata-safe causal fields:

1. ordered import step;
2. exception class;
3. failing module;
4. sanitized final traceback-frame module and function;
5. native-library basename when safely extractable;
6. stdout and stderr SHA-256;
7. exact target-runtime and source identities;
8. zero model loads, worker starts, and model requests.

## Non-claims

- The exact import exception is unknown.
- The failure is not assigned to Python, CUDA, native loading, Torch, Triton, vLLM, Transformers, or another package.
- The six A-F output-contract cases were not exercised.
- P4 exact-object reliability and JSON-schema compatibility are not established.
- P5, P6, measured A/B/C, deployment readiness, and production readiness are not established.

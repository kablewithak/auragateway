# ADR: Accept preflight-v3 exact-runtime wheelhouse materialization V1

Date: 2026-08-08

## Status

Accepted candidate for merge.

## Evidence lineage

```text
materializer_merge_commit=58591400897bcd278d7bfc33f110a9a8e813e29b
materializer_feature_commit=62596eeb1f82c7609a3971c752e4b04a9ec54257
kaggle_script_version_id=341083505
repository_notebook_sha256=e227c7926d7c8fd9acbdc3d773ba3dd145494aec6f150485e37af86d801f7c77
executed_notebook_sha256=e78dbe922e70a62e0cc00c753f7497fcd99352a83150a74f9681fd9ba4d6fc79
markdown_cell_source_sha256=8b49733ea3057aa85e36368fc24d9134f97185f9278ec1f72190e3951bef7abb
code_cell_source_sha256=1f6193854cd129f3c1c5b706eaa6d448811fc8576458e24e15e87035205ab56f
materialization_evidence_zip_sha256=6d97b933473064a71fafe790ab9d8a5bf87d9805d8666880b209123745a5d6df
execution_log_sha256=1269101cae7b3f6a321a5ac5c42972b47f44d8da19e8af54a15dc628f0594eb1
```

The saved Kaggle notebook differs as a whole file because it contains execution state and output,
but both source cells and the AuraGateway notebook metadata exactly match the merged repository
notebook.

## Technical result

```text
locked_package_count=196
downloaded_package_count=196
wheel_file_count=196
authority_host_count=5
transport_redirect_event_count=1
total_wheel_bytes=6164913809
dependency_resolution_performed=false
package_installation_performed=false
model_loads_performed=0
model_requests_performed=0
benchmark_trajectories_performed=0
```

The 200-entry SHA manifest binds all 196 wheel hashes plus four control files. The wheel filenames
and hashes exactly reconstruct the frozen 196-artifact resolution lock.

## Decision

`ACCEPT_EXACT_RUNTIME_WHEELHOUSE_MATERIALIZATION_V1`

Promote only the materialization state:

```text
wheelhouse_materialized=true
exact_runtime_materialized=true
exact_runtime_offline_verified=false
```

## Consequence

The saved Kaggle materializer version is now the candidate immutable wheelhouse input for a fresh
Internet-Off T4x2 verifier.

## Non-claims

This acceptance does not prove offline installation, dependency health after installation, CUDA
runtime compatibility, vLLM Python import, native-extension import, P5/P6 qualification, variance
pilot validity, final measured A/B/C validity, or production readiness.

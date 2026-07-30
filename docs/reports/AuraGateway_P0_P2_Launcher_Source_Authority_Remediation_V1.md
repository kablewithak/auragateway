# AuraGateway P0-P2 Launcher Source Authority Remediation V1

## Failure identity

```text
saved_version_id=339098285
status=P0_P2_EXECUTION_LAUNCHER_FAILED_V2
first_divergence=source_output_discovery
diagnostic_execution_attempts=0
runtime_install_attempts=0
kernel_compile_and_execution_attempts=0
model_loads=0
worker_starts=0
model_requests=0
benchmark_trajectory_requests=0
network_requests=0
external_spend=0
platform_conclusion=NONE
```

## Root cause

The accepted materialization receipt used bundle-manifest SHA-256
`463b58b32d34f39d8c189e69cb9614cd7ca2ad2124f73e239c29b96a97f1728f`.

The launcher template used
`246937c7fe66460953d88ea05fce2a9244ea4f104793b54ab6a40b122cba4ede`.

Receipt discovery is identity-shaped and fail-closed, so the correct source
output was not admitted.

## Resolution

The launcher producer now renders the accepted source authority into the
template, validates the rendered value, validates the immutable failed-run
evidence, and carries the accepted bundle-manifest identity in the generated
launcher record and notebook metadata.

A runtime regression extracts the accepted materializer evidence archive under
a synthetic Kaggle input root and requires `discover_source_output` to return
exactly one candidate.

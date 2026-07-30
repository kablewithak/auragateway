# ADR: Bind the P0-P2 launcher to accepted source authority

- Status: Accepted for remediation
- Date: 2026-07-30
- Scope: AuraGateway CUDA 12.9 P0-P2 execution launcher V2
- Base main: `d3c111a94ae517763d51fc724702bd9a3c11dd52`

## Context

Kaggle saved version `339098285` failed during `source_output_discovery` before
any diagnostic, installation, kernel, model, worker, request, or benchmark
attempt.

The accepted source evidence binds bundle-manifest SHA-256
`463b58b32d34f39d8c189e69cb9614cd7ca2ad2124f73e239c29b96a97f1728f`.

The generated launcher embedded stale SHA-256
`246937c7fe66460953d88ea05fce2a9244ea4f104793b54ab6a40b122cba4ede`.

The launcher therefore discarded the valid materialization receipt and observed
zero identity-shaped source outputs.

## Decision

1. Preserve saved version `339098285`, its log, failure archive, and canonical
   failure report.
2. Generate a queryable remediation record from exact evidence identities.
3. Render the bundle-manifest authority from
   `p0_p2_source_acceptance_v1.BUNDLE_MANIFEST_SHA256`.
4. Replace the template literal with a producer-owned marker.
5. Reject generation when the marker is missing, duplicated, unresolved, or
   renders the superseded identity.
6. Add a regression that mounts the accepted materializer archive and calls
   `discover_source_output`.
7. Regenerate the launcher notebook and record through the owning producer.
8. Permit one corrected replay only after merge and clean-main synchronization.

## Non-claims

The failed run establishes no CUDA, linker, driver, Triton, model, worker,
inference, benchmark, deployment, or production-readiness conclusion.

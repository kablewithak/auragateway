# ADR: P3-P6 Runtime Diagnostic Failure Acceptance V1

## Status

Accepted failure boundary; root cause unresolved.

## Authority

- current main authority: `f9a21819d95a7aadd7e5c775019a0761558c5aac`;
- governed Kaggle saved version: `339375227`;
- executed notebook: `ag-cu129-p3-p6-runtime-diagnostic-v1`;
- failed lineage name: `ag-cu129-p3-p6-runtime-diag-failed-v1`.

## Decision

Accept the governed attempt as a real failed execution at the offline target-runtime
installation boundary. The single authorization lifecycle is closed with outcome
`FAILED`; it is not reusable, and an unchanged replay is prohibited.

The evidence supports boundary classification only. It does not support a package,
wheel, dependency, disk, hash, or timeout root-cause claim because V1 discarded the
pip subprocess return code and bounded stdout/stderr.

## Consequences

Preserve the exact authorization, consumption receipt, runtime summary, failure
report, saved-version reference, and evidence limitations. Do not issue another
runtime authorization until a V2 diagnostic retains bounded pip evidence and emits
a small deterministic archive for early failures.

## Next gate

`DESIGN_AND_MERGE_P3_P6_RUNTIME_INSTALL_DIAGNOSTICS_V2`

# CUDA 12.9 worker-startup observability implementation runbook

## Current status

```text
WORKER STARTUP OBSERVABILITY IMPLEMENTED; REMATERIALIZATION REQUIRED
```

Do not issue authorization or run Kaggle from the implementation branch.

## Post-merge source package

Run the source-package toolchain only after the implementation PR merges and `main` is clean
and synchronized with `origin/main`:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_worker_observability_harness_toolchain build `
    --repo-root . `
    --output "$HOME\Desktop\ag-worker-observability-harness-source-v1"
```

The toolchain emits:

```text
ag-worker-obs-harness-<merge-token>-v1.zip
source_inventory.json
source_receipt.json
ag_worker_obs_harness_materializer_v1.ipynb
package_manifest.json
```

## Next operational boundary

1. Upload the exact source ZIP as one Kaggle dataset.
2. Import the generated materializer notebook.
3. Use Accelerator None, Internet Off, no secrets, and no other inputs.
4. Save Version 1 once.
5. Download the output and complete log.
6. Run one metadata-only input inspection.
7. Integrate new manifest and launcher identities only from consumed immutable evidence.
8. Review and issue one new short-lived authorization.
9. Permit at most one governed GPU qualification retry.

## Prohibited actions

- do not reuse the Attempt 5 authorization;
- do not run the historical `426f57d` harness as the remediated lineage;
- do not promote active manifest identities before metadata-only inspection;
- do not run GPU during source packaging or materialization;
- do not load a model or start workers during remediation proof;
- do not edit or normalize Attempt 5 evidence.

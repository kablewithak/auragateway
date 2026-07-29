# Runbook: P0-P2 Source Materialization V2

## Purpose

Create the governed P0-P2 source Dataset through Kaggle notebook-output lineage,
then validate the mounted Dataset with a separate metadata-only notebook.

This runbook begins only after the V2 source-materialization PR merges.

## Resource identities

```text
materializer notebook:
ag-cu129-p0-p2-source-materializer-v2

failed materializer lineage:
ag-cu129-p0-p2-source-mat-failed-v2

inspection notebook:
ag-cu129-p0-p2-source-inspection-v2

failed inspection lineage:
ag-cu129-p0-p2-source-insp-failed-v2

output Dataset:
ag-cu129-p0-p2-source-v2

inspection evidence ZIP:
ag-cu129-p0-p2-source-inspection-v2.zip
```

Every name is below Kaggle's 50-character limit.

## Hard execution boundary

Both notebooks require:

```text
Accelerator: None
Internet: Off
Secrets: none
Credentials: none
Customer data: none
External spend: 0
```

Do not attach the CUDA wheelhouse, model snapshot, or any authorization to the
materializer.

## Stage A: materializer

1. Open the merged notebook:
   `notebooks/auragateway_cu129_p0_p2_source_materializer_v2.ipynb`.
2. Create a Kaggle notebook named
   `ag-cu129-p0-p2-source-materializer-v2`.
3. Select Accelerator None.
4. Disable Internet.
5. Attach no inputs.
6. Confirm no secrets are configured.
7. Save Version, then Save & Run All exactly once.
8. Confirm the terminal status is
   `P0_P2_SOURCE_MATERIALIZED_V2`.
9. Confirm the notebook output contains exactly one directory:
   `ag_cu129_p0_p2_source_materializer_v2_output`.
10. Save that output as a Kaggle Dataset named
    `ag-cu129-p0-p2-source-v2`.

Do not rerun an unsuccessful lineage. Rename it to
`ag-cu129-p0-p2-source-mat-failed-v2` before creating a corrected successor.

## Materializer output contract

The output directory must contain exactly:

```text
auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb
option_c_p0_p2_platform_diagnostic_request.json
auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json
source_inventory.json
sha256_manifest.json
materialization_receipt.json
```

The receipt status must be:

```text
P0_P2_SOURCE_MATERIALIZED_V2
```

## Stage B: metadata-only inspection

1. Open the merged notebook:
   `notebooks/auragateway_cu129_p0_p2_source_input_inspection_v2.ipynb`.
2. Create a Kaggle notebook named
   `ag-cu129-p0-p2-source-inspection-v2`.
3. Select Accelerator None.
4. Disable Internet.
5. Attach exactly one Dataset:
   `ag-cu129-p0-p2-source-v2`.
6. Attach no wheelhouse, model, authorization, or other Dataset.
7. Save Version, then Save & Run All exactly once.
8. Confirm the terminal status is
   `P0_P2_SOURCE_INPUT_INSPECTION_PASSED_V2`.
9. Preserve:
   `ag-cu129-p0-p2-source-inspection-v2.zip`.

Do not rerun an unsuccessful lineage. Rename it to
`ag-cu129-p0-p2-source-insp-failed-v2` before creating a corrected successor.

## Inspection acceptance criteria

```text
exactly one identity-shaped source Dataset
source bundle SHA-256 matches
bundle manifest SHA-256 matches
source inventory SHA-256 matches
three source files validate by size and SHA-256
diagnostic notebook outputs absent
diagnostic notebook execution counts absent
credentials absent
customer data absent
model loads = 0
worker starts = 0
model requests = 0
benchmark trajectory requests = 0
external spend = 0
```

## Stop conditions

Stop immediately if:

- more than one receipt candidate is discovered;
- any source hash or size differs;
- any source path is unsafe;
- the reviewed notebook contains execution state;
- any credential or customer-data field is nonzero or true;
- an output path already exists;
- the Dataset is not the exact materializer output.

## Next gate after inspection pass

```text
integrate_materialized_p0_p2_source_with_execution_launcher_v2
```

The single GPU P0-P2 diagnostic session remains unconsumed during this runbook.

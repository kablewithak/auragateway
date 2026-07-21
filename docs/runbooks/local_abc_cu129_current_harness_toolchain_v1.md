# Runbook: Current CUDA 12.9 harness rematerialization toolchain v1

## Purpose

Generate one immutable current source package plus the exact Kaggle materializer and metadata-only
inspection notebooks. This runbook stops before active manifest migration, authorization issuance,
model loading, worker startup, or qualification execution.

## Governing policy

```text
review_minimum_ancestor=defe184d338b525e2f48104ef76e5d0d9a1329a8
source_binding_policy=POST_MERGE_CLEAN_MAIN_HEAD
materializer_notebook_name=ag-harness-materializer-cu129-v1
inspection_notebook_name=ag-harness-input-inspection-cu129-v1
runtime_output_directory=auragateway_vllm_cu129_wheelhouse_v1
runtime_package_count=176
runtime_resolution_lock_sha256=1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c
```

The archive, Kaggle source-dataset, and materialized-directory names are derived from the first seven
characters of the exact post-merge `main` commit. They are not known or frozen inside the
implementation PR.

## Repository gate

Run only after the toolchain implementation PR merges and the repository is synchronized on clean
`main`.

```powershell
git branch --show-current
git status
git rev-parse HEAD
git rev-parse origin/main
git --no-pager log -1 --oneline
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_harness_toolchain validate-repository --repo-root .
```

The validator must report:

```text
status=CURRENT_CU129_HARNESS_TOOLCHAIN_IMPLEMENTED
decision=APPROVED_FOR_COMPLETE_CURRENT_CU129_HARNESS_TOOLCHAIN
review_minimum_ancestor=defe184d338b525e2f48104ef76e5d0d9a1329a8
source_binding_policy=POST_MERGE_CLEAN_MAIN_HEAD
runtime_role=vllm_runtime
runtime_artifact_format=python_wheelhouse_directory
runtime_package_count=176
authorization_issued=false
kaggle_execution_performed=false
model_requests_performed=0
next_gate=merge_then_prepare_current_cu129_harness_toolchain
```

## Local preparation

```powershell
$SourceCommit = (git rev-parse HEAD).Trim()
$OriginMain = (git rev-parse origin/main).Trim()

if ($SourceCommit -ne $OriginMain) {
    throw "HEAD must equal origin/main before source packaging."
}

$SourceToken = $SourceCommit.Substring(0, 7)
$ArchiveName = "ag-harness-$SourceToken-v1.zip"
$InputDatasetName = "ag-harness-$SourceToken-v1-input"
$MaterializedDirectory = "auragateway_qualification_harness_${SourceToken}_v1"
$OutputRoot = Join-Path $HOME "Desktop\AuraGateway_CU129_Current_Harness_Toolchain_${SourceToken}_v1"

Remove-Item -LiteralPath $OutputRoot -Recurse -Force -ErrorAction SilentlyContinue

python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_harness_toolchain prepare --repo-root . --output-dir $OutputRoot
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_harness_toolchain verify --toolchain-dir $OutputRoot

Get-ChildItem -LiteralPath $OutputRoot | Sort-Object Name | Format-Table Name, Length
```

Expected outputs:

```text
$ArchiveName
source_inventory.json
source_packaging_receipt.json
sha256_manifest.json
ag_harness_materializer_cu129_v1.ipynb
ag_harness_input_inspection_cu129_v1.ipynb
toolchain_receipt.json
```

## Identity capture

```powershell
Get-FileHash -LiteralPath (Join-Path $OutputRoot $ArchiveName) -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $OutputRoot "source_inventory.json") -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $OutputRoot "source_packaging_receipt.json") -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $OutputRoot "sha256_manifest.json") -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $OutputRoot "ag_harness_materializer_cu129_v1.ipynb") -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $OutputRoot "ag_harness_input_inspection_cu129_v1.ipynb") -Algorithm SHA256
Get-FileHash -LiteralPath (Join-Path $OutputRoot "toolchain_receipt.json") -Algorithm SHA256
```

Do not edit generated outputs after preparation.

## Publish source input

Create one Kaggle dataset named exactly `$InputDatasetName` and upload exactly:

```text
$ArchiveName
source_inventory.json
source_packaging_receipt.json
sha256_manifest.json
```

Do not upload either notebook into the source dataset.

## Materialize

Import `ag_harness_materializer_cu129_v1.ipynb` into one new Kaggle notebook.

```text
Title: ag-harness-materializer-cu129-v1
Accelerator: None
Internet: Off
Secrets: None
Inputs: exactly $InputDatasetName Version 1
Action: Save Version -> Save & Run All
```

Required terminal signals:

```text
status=CURRENT_CU129_HARNESS_MATERIALIZED
source_commit=$SourceCommit
output_directory=$MaterializedDirectory
file_count=<receipt value>
total_bytes=<receipt value>
directory_sha256=<receipt value>
gpu_execution_performed=false
model_requests_performed=0
authorization_issued=false
save_this_notebook_output=true
```

Save exactly one successful Version 1. Do not rerun a consumed materializer output.

## Metadata-only input inspection

Import `ag_harness_input_inspection_cu129_v1.ipynb` into one new Kaggle notebook.

```text
Title: ag-harness-input-inspection-cu129-v1
Accelerator: None
Internet: Off
Secrets: None
Inputs:
  1. exactly the successful ag-harness-materializer-cu129-v1 Version 1 output
  2. exactly kabomolefe/auragateway-cu129-wheelhouse-materializer-v1 Version 1 output
  3. exactly kabomolefe/auragateway-qwen2-5-0-5b-offline-v1 Version 1
Action: Save Version -> Save & Run All
```

Required terminal signals:

```text
inspection_status=CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED
operational_input_closure=PASSED
source_commit=$SourceCommit
runtime_package_count=176
gpu_execution_performed=false
package_installation_performed=false
model_requests_performed=0
authorization_issued=false
save_this_notebook_output=true
```

Download immediately:

```text
ag-harness-input-inspection-cu129-v1.zip
```

Do not run a GPU session, install packages, load the model or tokenizer, start workers, or issue
authorization.

## Repeated-failure rule

Normalize every failure to one stable failure class. The first occurrence receives one bounded fix.
If the same class appears again, stop before another patch and produce a semi-formal reasoning
certificate containing premises, evidence identities, both occurrences, first divergence,
alternatives, resolution, rerun justification, claims, non-claims, and regressions.

## Next gate

After one successful metadata-only inspection, integrate the consumed immutable evidence and migrate
the active manifest, launcher, runbook resource binding, and fresh CUDA 12.9 authorization review in
one repository PR.

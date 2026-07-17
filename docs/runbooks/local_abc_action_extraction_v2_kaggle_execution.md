# Runbook: Action-Extraction Requalification v2 on Kaggle

## Preconditions

- The execution-package PR is merged.
- Local `main` is clean and synchronized with `origin/main`.
- The package SHA-256 is
  `deb7d803819ec489218f78ecc4466ae1402eef30a63ba7b93d293ea872677451`.
- The authorization is still unused.
- No previous v2 execution attempt has started.

## Build the exact package

```powershell
$Output = Join-Path $env:USERPROFILE `
    "Desktop\auragateway-local-abc-action-extraction-requalification-notebook-v2.zip"

python -m auragateway.local_abc.action_extraction_execution_package `
    --repository-root . `
    --output $Output

Get-FileHash -Algorithm SHA256 $Output
```

The reported SHA-256 must match the frozen package digest exactly.

## Kaggle configuration

1. Upload the package ZIP as a private Kaggle dataset.
2. Import the exact notebook from the package or merged repository.
3. Attach the private package dataset to the notebook.
4. Set the accelerator to **GPU T4 x2**.
5. Enable Internet access.
6. Do not add secrets.
7. Keep the GPU disabled until the package and notebook identities have been checked.

## Execution

- Run the complete notebook once.
- Do not rerun individual failed cells.
- Do not restart and rerun the notebook.
- Do not alter the notebook, package, model, runtime, decoding, case order, or request count.
- Retain semantic failures and allow the notebook to complete all 16 requests.
- Abort on infrastructure or cleanup failure as implemented by the notebook.

## Required result

Download this exact evidence archive immediately after the run:

```text
auragateway-reconcile-balance-action-extraction-requalification-evidence-v2.zip
```

Record its SHA-256. Do not start another run. The next repository action is an immutable evidence
audit regardless of whether the quality gate passed or failed.

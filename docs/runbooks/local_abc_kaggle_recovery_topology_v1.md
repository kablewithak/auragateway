# Runbook: AuraGateway Kaggle Recovery and One-Shot Execution Topology

## Purpose

Use this topology whenever a governed Kaggle notebook requires an exact package ZIP and an exact
vLLM wheel. Kaggle commonly expands uploaded ZIP datasets, so the execution notebook must consume
saved recovery-notebook outputs rather than the directly uploaded source dataset.

## Input topology

### 1. Direct package source dataset

Upload the deterministic package ZIP as a private dataset. A suitable title is:

```text
AuraGateway Requal Package Source v2
```

Kaggle may expand the ZIP. That is expected. Attach this dataset only to the package-recovery
notebook.

### 2. Package-recovery notebook

Notebook title:

```text
AuraGateway Package Recovery v2
```

The recovery notebook reconstructs and verifies the exact package in `/kaggle/working`:

```text
auragateway-local-abc-action-extraction-requalification-notebook-v2.zip
```

Required package SHA-256:

```text
deb7d803819ec489218f78ecc4466ae1402eef30a63ba7b93d293ea872677451
```

Use `Save Version` and `Save & Run All`. A draft session is not a reusable output. The saved version
must finish successfully and expose the exact ZIP through its notebook output.

### 3. vLLM wheel-recovery notebook

Attach the successful saved output of:

```text
auragateway-vllm-wheel-recovery-v1
```

It must expose exactly one wheel:

```text
vllm-0.25.1+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

Required wheel SHA-256:

```text
9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431
```

## Fresh execution notebook

Import the exact frozen `.ipynb` again. Do not duplicate a previously executed Kaggle notebook. The
fresh execution notebook must attach only:

1. the successful package-recovery notebook output;
2. the successful vLLM wheel-recovery notebook output.

Do not attach the expanded package dataset, old package versions, duplicate wheel outputs, unrelated
datasets, or prior execution-notebook outputs.

Configure the frozen execution environment before running any cell:

```text
Accelerator: GPU T4 x2
Internet: On
Secrets: None
```

Use a fresh session. Run preflight cells sequentially. Require exactly one package ZIP and exactly one
wheel before repository checkout, runtime bootstrap, or model startup.

## One-shot boundary

After all preflights pass, execute the governed notebook exactly once. Do not rerun failed cells,
restart and rerun, alter the notebook, change input versions, change the case set, or retry only
failed cases.

Immediately download and hash the evidence archive. Stop the session and disable the GPU only after
the archive is safely preserved. The next action is an immutable evidence audit whether the quality
gate passed or failed.

## Evidence and no-rerun rule

A preflight failure before model startup does not consume the authorization. Abandon that notebook
and import a fresh frozen notebook after correcting inputs. Once governed model requests begin, no
restart or rerun is permitted unless a separately reviewed authorization explicitly allows it.

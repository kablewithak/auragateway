# Governed Kaggle Qualification Launcher v1

## Purpose

Prepare one cold-session Kaggle execution surface for the already reviewed AuraGateway
full A/B/C environment qualification.

This runbook does not issue authorization, execute the 342-request benchmark, enable
Internet, connect secrets, use customer data, or permit hosted-provider calls.

## Governed names

All Kaggle names remain below the 50-character limit.

```text
input preflight notebook:
ag-qualification-input-preflight-v1
characters: 35

authorization control materializer:
ag-qualification-control-materializer-v1
characters: 40

qualification launcher:
ag-full-abc-env-qualification-v1
characters: 32

human handoff artifact:
ag-qualification-evidence-v1.zip
characters: 32
```

## Preflight authority

The launcher binds the completed static-input preflight:

```text
artifact:
ag-input-preflight-v1.zip

SHA-256:
55c65f0edfd6fbd0b3dfb17070e5f40e849db17b494a43d8a5fcaa2b3ce841c3

status:
PASS

nested archives:
0

symlinks:
0
```

Exact observed static inputs:

```text
harness source:
/kaggle/input/datasets/kabomolefe/auragateway-qualification-harness-4dfd799-v1

model snapshot:
/kaggle/input/datasets/kabomolefe/auragateway-qwen2-5-0-5b-offline-v1/
auragateway-qwen2.5-0.5b-instruct-7ae557604adf67be50417f59c2c2f167def9a775/
hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/
snapshots/7ae557604adf67be50417f59c2c2f167def9a775

vLLM wheel:
/kaggle/input/notebooks/kabomolefe/auragateway-vllm-wheel-recovery-v1/
auragateway_vllm_wheels_v1/
vllm-0.25.1+cu129-cp38-abi3-manylinux_2_28_x86_64.whl
```

The line breaks above are for readability. Runtime bindings use the complete uninterrupted
paths.

## Execution boundary

The generated launcher embeds the exact code cell from:

```text
notebooks/auragateway_full_abc_environment_qualification_v1.ipynb
```

The launcher verifies that cell's SHA-256 before execution. It does not rewrite or patch
the reviewed execution body.

The launcher adds only the missing operational harness:

1. cold-session validation;
2. exact control-output discovery;
3. authorization and manifest path binding;
4. execution of the unchanged reviewed code cell;
5. bounded success or failure evidence packaging.

## Stale-state policy

Each stage uses a separate saved notebook version and a fresh session.

The launcher fails before vLLM installation when any of these conditions exists:

- a vLLM or Transformers module is already imported;
- a CUDA context is already initialized;
- an `AURAGATEWAY_*` or `VLLM_*` environment variable already exists;
- loopback port 8001 or 8002 is already open;
- `/kaggle/working/auragateway_qualification_harness` already exists;
- `/kaggle/working/ag-qualification-evidence-v1.zip` already exists.

Do not rerun the launcher in the same Kaggle session after a failure. Preserve the first
failure artifact and terminate the session.

## Authorization control materialization

The local authorization runner remains the only issuance authority.

After one authorization is issued and locally verified, generate the control notebook:

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_kaggle_launcher `
    generate-control-materializer `
    --repo-root . `
    --output "$HOME\Downloads\ag-qualification-control-materializer-v1.ipynb"
```

The generated notebook embeds only:

- the canonical authorization JSON;
- the exact runtime dataset manifest.

It does not embed the repository, model, wheel, credentials, secrets, or customer data.

Import that notebook into Kaggle with:

```text
Notebook name:
ag-qualification-control-materializer-v1

Accelerator:
None

Internet:
Off

Secrets:
None
```

Use `Save Version -> Save & Run All`.

The output is one flat directory:

```text
/kaggle/working/ag_qualification_control_v1
```

It contains exactly four JSON files:

```text
auragateway_full_abc_local_full_run_environment_qualification_
execution_authorization_v1.json

offline_dataset_manifest.json

control_package_manifest.json

materialization_receipt.json
```

No ZIP, archive, model, source tree, wheel, or nested directory is emitted.

The materializer fails when fewer than 180 authorization minutes remain.

## Qualification launcher preparation

Import:

```text
notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb
```

Use this Kaggle name:

```text
ag-full-abc-env-qualification-v1
```

Configure:

```text
Accelerator:
T4 x2

Internet:
Off

Secrets:
None
```

Attach exactly four input resources:

1. `auragateway-qualification-harness-4dfd799-v1`
2. `auragateway-qwen2-5-0-5b-offline-v1`
3. `auragateway-vllm-wheel-recovery-v1`
4. the saved output of `ag-qualification-control-materializer-v1`

Do not add an API secret through Add-ons.

Do not add the preflight notebook output to the qualification launcher.

## Launch rule

Use only:

```text
Save Version -> Save & Run All
```

Do not manually execute exploratory cells. The launcher intentionally contains one
runtime code cell so that discovery, execution, cleanup, and evidence packaging share one
controlled path.

The launcher rejects authorizations with fewer than 120 minutes remaining.

The launcher permits:

```text
Kaggle sessions: 1
workers: 2
synthetic model requests: 6 within the maximum budget of 8
maximum output tokens per request: 32
benchmark trajectory requests: 0
Internet: Off
credentials: absent
customer data: absent
external spend: R0 / $0
```

## Evidence handoff

Success produces:

```text
/kaggle/working/ag-qualification-evidence-v1.zip
```

The ZIP contains only:

```text
cache_metric_capability_report.json
gpu_topology_report.json
kaggle_runtime_dependency_lock.json
manifest.json
model_identity_report.json
qualification_report.json
reset_capability_report.json
worker_health_report.json
evidence_bundle_sha256.json
launcher_summary.json
```

Failure produces the same ZIP name with only:

```text
launcher_failure.json
launcher_failure_trace.txt
```

The archive is capped at 2 MiB. The launcher never archives:

- `/kaggle/input`;
- the model snapshot;
- the vLLM wheel;
- the harness source tree;
- Hugging Face caches;
- pip caches;
- `/kaggle/working` wholesale;
- raw prompts or generated text;
- credentials or environment dumps.

Download and upload only `ag-qualification-evidence-v1.zip`.

## Failure policy

On the first failure:

1. do not rerun a cell;
2. do not change runtime variables;
3. do not restart workers manually;
4. do not edit authorization timestamps;
5. do not issue benchmark requests;
6. download the small failure ZIP;
7. terminate the Kaggle session;
8. return the ZIP for repository-grounded diagnosis.

## Non-claims

The launcher implementation and a successful notebook import do not prove:

- vLLM installation compatibility;
- model or tokenizer loading;
- two-worker health;
- cache metric availability;
- reset correctness;
- environment qualification;
- cache reuse;
- latency improvement;
- quality non-inferiority;
- measured benchmark authorization;
- production readiness.

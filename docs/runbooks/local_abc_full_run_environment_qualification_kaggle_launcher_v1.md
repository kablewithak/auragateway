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

## Historical preflight authority

The following preflight remains preserved as historical evidence for the superseded harness. It is
not the active current-harness authority:

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

Current observed static inputs:

```text
harness source:
/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/
ag_harness_materializer_cu129_v1_output/
auragateway_qualification_harness_426f57d_v1

model snapshot:
/kaggle/input/datasets/kabomolefe/auragateway-qwen2-5-0-5b-offline-v1/
auragateway-qwen2.5-0.5b-instruct-7ae557604adf67be50417f59c2c2f167def9a775/
hf_home/hub/models--Qwen--Qwen2.5-0.5B-Instruct/
snapshots/7ae557604adf67be50417f59c2c2f167def9a775

CUDA 12.9 runtime input:
exactly one `auragateway_vllm_cu129_wheelhouse_v1` output directory discovered beneath
`/kaggle/input` and bound by its resolution lock, runtime manifest, checksum manifest,
materialization receipt, and 176-package closure.
```

The line breaks above are for readability. Runtime bindings use the complete uninterrupted
paths. Current operational-input closure is bound by inspection saved version `337035826` and
evidence ZIP SHA-256
`2d2f6afdd53787f6b3977e799dff441f9023a3c265ddf65d35855c5b62ad90d8`.

Exact uninterrupted current harness binding:

```text
/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-cu129-v1/ag_harness_materializer_cu129_v1_output/auragateway_qualification_harness_426f57d_v1
```


## CUDA 12.9 runtime integration

The launcher control package carries the logical runtime authority rather than an invented
platform slug or a hard-coded mounted path. The runtime adapter discovers exactly one
governed output directory and then enforces:

```text
installation executor: BASE_PIP_TARGET_DIRECTORY
dependency validation: CONTROLLED_TARGET_METADATA_AND_PACKAGING
Python startup: NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP
loader policy: TARGET_NVIDIA_LIBRARIES_PREPENDED
vLLM: 0.19.1
Torch: 2.10.0+cu129
Transformers: 5.5.3
```

No model process starts until the target environment, package closure, target Python, and
NVIDIA loader order have passed validation.

## Current harness materialization authority

The active harness is the saved Version 1 output of:

```text
ag-harness-materializer-cu129-v1
script version: 337034643
```

Expected producer topology:

```text
ag_harness_materializer_cu129_v1_output/
├── auragateway_qualification_harness_426f57d_v1/
└── ag_harness_materialization_receipt_cu129_v1.json
```

Frozen identity:

```text
source commit:
426f57dd11dddc2fb8e5a703721c2189abc7a0ff

file count:
1299

total bytes:
11,632,357

directory SHA-256:
c3ea4ae6d047a8b3f3d5afc517e26c4f13fb4a82e48e3cf28cdfabdc343230e6

materialization receipt SHA-256:
07d81dbea5b5ed24d0786c0ee16782129e163834254c095262944baaf5c59db2
```

The metadata-only operational-input inspection is:

```text
notebook:
ag-harness-input-inspection-cu129-v1

saved version:
337035826

evidence:
ag-harness-input-inspection-cu129-v1.zip

evidence SHA-256:
2d2f6afdd53787f6b3977e799dff441f9023a3c265ddf65d35855c5b62ad90d8

status:
CURRENT_CU129_HARNESS_INPUT_INSPECTION_PASSED

operational input closure:
PASSED
```

The historical `be1bfadd` harness remains immutable evidence but is no longer active. The model
snapshot remains unchanged. The historical single-wheel runtime instruction is superseded by the
exact 176-package CUDA 12.9 wheelhouse authority.

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

## Control-output discovery boundary

The first rematerialized-harness retry failed safely at `control_output_discovery`.
The launcher searched all attached inputs by filename and therefore observed both:

- the control package copy of `offline_dataset_manifest.json`; and
- the same committed filename inside the expanded harness repository.

Preserved failure evidence:

```text
failure code:
CONTROL_OUTPUT_NAMESPACE_COLLISION

evidence ZIP SHA-256:
55910873d6282ce8b98efd2726d2630bfed4f1c706eb4ec6484adb8a66885926

provider calls:
false

model requests:
0

external spend:
0
```

The corrected launcher first resolves exactly one directory named:

```text
ag_qualification_control_v1
```

under an input path containing the governed notebook token:

```text
ag-qualification-control-materializer-v1
```

It then validates the exact flat four-file allowlist inside that root. Identically named
files in unrelated harness, model, or wheel inputs do not participate in control-package
resolution. Multiple governed roots, wrapper directories, extra files, nested archives,
symlinks, and non-regular members remain fail-closed conditions.

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

1. the saved Version 1 output of `ag-harness-materializer-cu129-v1`
2. `auragateway-qwen2-5-0-5b-offline-v1`
3. the saved Version 1 output of `auragateway-cu129-wheelhouse-materializer-v1`
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
- the CUDA 12.9 wheelhouse;
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


## Authorization source-authority parity

The launcher binds the current harness independently from the future short-lived authorization:

```text
harness source commit: 426f57dd11dddc2fb8e5a703721c2189abc7a0ff
authorization source policy: CONTROL_PACKAGE_AUTHORIZATION_PARITY
```

The launcher does not guess or freeze the future authorization merge commit. The control materializer
reads `source_main_merge_commit` from the validated authorization payload and writes the same value
into `control_package_manifest.json`. The launcher requires exact parity between those two consumed
files before reviewed-core execution. A fresh authorization implementation must bind the exact
post-integration merge commit, current manifest, current materialization record, and current runtime
adapter. Authorization remains absent in this integration boundary. The next repository gate is
`fresh_cu129_authorization_issuance_implementation`.

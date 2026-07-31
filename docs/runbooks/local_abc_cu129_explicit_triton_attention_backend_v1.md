# Runbook: Explicit Triton attention-backend V1 implementation

## Boundary

```text
source main:
81597c1ebc6add70f6c35e3f2287acba9c078519

recommended branch:
feat/local-abc-triton-attention-backend-v1

mode:
repository implementation only

runtime execution authorization:
absent
```

## Candidate paths

The implementation candidate contains exactly ten paths:

```text
src/auragateway/local_abc/
  full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1.py

src/auragateway/local_abc/templates/
  explicit_triton_attention_backend_v1.py.tmpl

tests/unit/local_abc/
  test_full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1.py

data/evals/benchmark/environment-qualification-v1/
  explicit_triton_attention_backend_v1_request.json

benchmarks/local_abc/
  auragateway_cu129_explicit_triton_attention_backend_v1_review.json
  auragateway_cu129_explicit_triton_attention_backend_v1_record.json

notebooks/
  auragateway_cu129_explicit_triton_attention_backend_v1.ipynb

docs/adr/
  2026-07-31-local-abc-explicit-triton-attention-backend-v1.md

docs/runbooks/
  local_abc_cu129_explicit_triton_attention_backend_v1.md

docs/reports/
  AuraGateway_CU129_Explicit_Triton_Attention_Backend_V1.md
```

## Local generation

From the repository root and active virtual environment:

```text
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1 generate --repo-root .
```

Valid success marker:

```text
EXPLICIT_TRITON_ATTENTION_BACKEND_V1_GENERATED
```

## Local semantic validation

```text
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1 validate --repo-root .
```

Valid success marker:

```text
EXPLICIT_TRITON_ATTENTION_BACKEND_V1_VALIDATED
```

Validation rebuilds and byte-compares:

```text
request
architecture review
notebook
implementation record
```

It also revalidates both accepted upstream execution records.

## Focused validation

```text
python -m pytest tests/unit/local_abc/test_full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_v1.py
```

Run project-mode mypy, bounded Ruff, full Ruff, and full pytest according to the
current workflow guide before staging.

## Staging boundary

Stage exactly the ten paths listed in this runbook. Reject:

```text
unrelated source changes
runtime authorization artifacts
Kaggle output
model files
wheel files
local evidence
notebook outputs
execution counts
```

Validate the existing staged tree if it is already exact. Do not reset a valid
staged candidate merely to recreate an earlier unstaged state.

## Runtime prohibition

During this implementation tranche, do not:

```text
open or run a Kaggle GPU session
install the CUDA 12.9 target runtime
import the target vLLM backend
compile or execute the attention primitive
start a worker
load a model
issue an inference request
probe cache behavior
run measured A/B/C
replay saved version 339127349
replay saved version 339140121
```

The generated notebook is an implementation artifact, not execution authority.

## Future execution shape

A later authorization may bind:

```text
notebook title:
ag-cu129-triton-attention-backend-v1

failed lineage title:
ag-cu129-triton-attn-backend-failed-v1

accelerator:
T4 x2

Internet:
Off

attached inputs:
exactly one

input:
Version 1 output from auragateway-cu129-wheelhouse-materializer-v1
```

Those settings are reproducibility information only. They must not be used
until a fresh merged runtime authorization explicitly permits one execution.

## Evidence behavior in the future execution

The notebook is designed to produce:

```text
platform_identity_report_v1.json
backend_discovery_report_v1.json
backend_import_report_v1.json
backend_capability_report_v1.json
attention_primitive_report_v1.json
explicit_triton_attention_backend_summary_v1.json
bundle_manifest_v1.json
human_report_v1.md
ag-cu129-triton-attention-evidence-v1.zip
```

The notebook stops on the first failure. Completed stage reports remain
preserved, the divergent stage is classified, and later stages remain
`NOT_EXECUTED`.

## Merge stop condition

After the implementation PR is merged:

```text
synchronize main
verify clean worktree and index
delete local feature branch
verify remote feature branch deletion
stop
```

Do not proceed directly to Kaggle.

## Next legal gate

```text
DESIGN_AND_MERGE_EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1
```

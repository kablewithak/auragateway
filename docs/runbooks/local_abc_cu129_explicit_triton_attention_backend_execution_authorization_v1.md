# Runbook: Explicit Triton Attention-Backend Execution Authorization V1

## Current boundary

This runbook first validates the repository-only issuer implementation. It does
not authorize or execute the notebook until the issuer PR has merged.

```text
source main:
6ede70538c52165d92a1df68e2c8bbc97a123c49

implementation feature commit:
dc9484492169965e0ed17d77bf1894d1ae9e7cb8

notebook:
notebooks/auragateway_cu129_explicit_triton_attention_backend_v1.ipynb

notebook SHA-256:
cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208
```

## Transient paths

These files must remain untracked and must never be committed:

```text
benchmarks/local_abc/
auragateway_cu129_explicit_triton_attention_backend_
execution_authorization_v1.json

benchmarks/local_abc/
auragateway_cu129_explicit_triton_attention_backend_
execution_authorization_consumption_v1.json
```

## Validate the implementation PR

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_execution_authorization_v1 `
    validate-implementation `
    --repo-root .
```

Required state:

```text
EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1_VALID
authorization_issuer_implemented=true
authorization_issued=false
runtime_execution_performed=false
```

## Post-merge issuance preconditions

Before issuance:

1. switch to `main`;
2. fast-forward from `origin/main`;
3. require a clean index and worktree;
4. require both transient paths to be absent and untracked;
5. validate the implementation package again;
6. confirm the exact scope and notebook SHA-256.

## Issue one authorization

The explicit command is intentionally deferred until after the issuer PR merge.
It requires:

```text
--operator-confirm
--window-minutes <= 240
--confirm-scope MODEL_FREE_EXPLICIT_TRITON_ATTENTION_BACKEND_V1
--confirm-notebook-sha256 cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208
```

Issuance creates one non-overwriting canonical JSON file. It starts no Kaggle
session and performs no GPU or package activity.

## Verify immediately before execution

```powershell
python -m auragateway.local_abc.full_abc_local_environment_qualification_cu129_explicit_triton_attention_backend_execution_authorization_v1 `
    verify `
    --repo-root .
```

Required state:

```text
ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_VALID
single_use=true
consumed=false
maximum_kaggle_sessions=1
maximum_attention_primitive_attempts=1
maximum_model_loads=0
maximum_worker_starts=0
maximum_model_requests=0
maximum_benchmark_trajectory_requests=0
```

## Governed Kaggle configuration

```text
Notebook name: ag-cu129-triton-attention-backend-v1
Failed lineage: ag-cu129-triton-attn-backend-failed-v1
Accelerator: T4 x2
Internet: Off
Secrets: none
Inputs: exactly one
```

Attach saved Version 1 output from:

```text
auragateway-cu129-wheelhouse-materializer-v1
```

Use **Save Version -> Save & Run All** exactly once. Do not manually execute
cells first.

## Hard action budget

```text
Kaggle sessions: 1
runtime installations: 1
backend discovery attempts: 1
backend import attempts: 1
capability validation attempts: 1
attention primitive attempts: 1
models: 0
workers: 0
model requests: 0
benchmark trajectories: 0
network requests: 0
hidden retries: 0
external spend: 0
```

## Consume after any attempt

A passed, failed, or interrupted saved version consumes the authorization.
Create the consumption receipt once using:

```text
--operator-confirm
--outcome PASSED | FAILED | INTERRUPTED
--saved-version-id <positive Kaggle saved version ID>
```

Do not run the notebook again under the same authorization, even if the
authorization time window remains open.

## Evidence to preserve

```text
complete Kaggle log
saved-version URL and ID
ag-cu129-triton-attention-evidence-v1.zip
transient authorization SHA-256
consumption receipt SHA-256
```

If execution fails, rename the notebook lineage to:

```text
ag-cu129-triton-attn-backend-failed-v1
```

Do not rerun the unchanged failed lineage.

## Enforcement limitation

The notebook does not parse the transient authorization JSON. The authorization
is an operator gate bound to the exact notebook hash. Runtime-loader enforcement
is not claimed.

## Next gates

After issuer implementation merge:

```text
EXPLICIT_OPERATOR_CONFIRMATION_THEN_ISSUE_EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1
```

After issuance:

```text
EXECUTE_GOVERNED_EXPLICIT_TRITON_ATTENTION_BACKEND_V1
```

After any attempt:

```text
PRESERVE_AND_ACCEPT_EXPLICIT_TRITON_ATTENTION_BACKEND_EVIDENCE_V1
```

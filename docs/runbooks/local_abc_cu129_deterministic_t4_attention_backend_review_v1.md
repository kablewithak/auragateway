# Local A/B/C CUDA 12.9 deterministic T4 attention-backend review

## Current state

```text
qualification_status=FAILED_CLOSED
root_cause=FLASHINFER_JIT_CUDA_DRIVER_LINK_LIBRARY_UNAVAILABLE
runtime_installation_reached=true
model_weights_loaded=true
workers_started=2
workers_ready=0
model_requests_performed=0
authorization_reusable=false
unchanged_rerun_permitted=false
```

## Review decision

```text
decision=APPROVED_FOR_DETERMINISTIC_T4_ATTENTION_BACKEND_IMPLEMENTATION
selected_backend=TRITON_ATTN
selection_interface=--attention-backend
runtime_change_performed=false
rerun_permitted=false
```

## Required implementation

1. add `--attention-backend TRITON_ATTN` to the canonical worker command;
2. include `--attention-backend` in the pinned CLI capability contract;
3. capture and validate `TRITON_ATTN` in dependency-lock evidence;
4. regenerate both worker command SHA-256 identities;
5. regenerate the worker plan, execution request, reviewed notebook, and
   governed launcher;
6. reject `auto` and `FLASHINFER` for the T4 qualification path;
7. preserve zero hidden retries, worker replacement, backend fallback, and
   benchmark trajectory requests.

## Prohibited actions during this review PR

- runtime source modification;
- Kaggle execution;
- authorization issuance;
- harness materialization;
- model requests;
- wheelhouse mutation;
- current-harness reuse.

## Post-merge sequence

1. synchronize clean `main`;
2. implement the deterministic backend contract in a separate branch;
3. validate and merge the implementation;
4. build the exact post-merge harness source package;
5. materialize it CPU-only with Internet Off;
6. inspect the materialized input metadata-only;
7. integrate the new immutable harness identity;
8. issue one fresh bounded authorization;
9. permit one fresh-session T4 x2 qualification attempt.

## Circuit breaker

A Triton startup or runtime-contract failure must be preserved as new evidence.
No silent fallback and no unchanged rerun are permitted.

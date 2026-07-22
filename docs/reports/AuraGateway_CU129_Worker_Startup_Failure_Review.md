# AuraGateway CUDA 12.9 Worker-Startup Failure Review

## Review result

```text
decision=APPROVED_FOR_WORKER_STARTUP_OBSERVABILITY_IMPLEMENTATION
failure_class=WORKER_STARTUP_FAILURE_OPAQUE_PROCESS_OUTPUT
root_cause_status=UNRESOLVED
rerun_decision=UNCHANGED_RERUN_NOT_JUSTIFIED
next_gate=implement_worker_startup_observability_and_post_merge_harness_toolchain
```

## Immutable evidence

```text
qualification_status=FAILED
source_artifact_sha256=7f926ef354678f2dcdd7bcc81854597aadfa3a1a125db4fd0dc2cd388948e92a
execution_log_sha256=f7d921aa13d4334d54a3d6313eca7934abc1235dfad8e3f4378dcc4c6de71d82
launcher_failure_sha256=eb51ecfafac3c504f834fb76889cf435be253a4824a276f050b128f4fb41f91a
launcher_trace_sha256=0aff3131e04f669c8f2971c1498533bf15336b5847d09f55f3e2a3b1cbcdbc68
```

Attempt 5 reached the reviewed execution core, current execution module, current runtime adapter,
and worker startup. It failed in `_wait_for_workers` after bounded readiness polling. No model
inventory validation or qualification probe completed.

## First divergence

```text
worker startup was attempted
→ readiness endpoints did not become healthy within the bounded window
→ adapter raised a generic RuntimeError
→ worker processes were cleaned up
→ launcher retained only generic failure metadata and a traceback
```

The failure is real. Environment qualification did not pass.

## Evidence limitation

The current adapter binds worker `stdout` and `stderr` to `subprocess.DEVNULL`. The worker
protocol and readiness loop do not retain:

- worker-specific process exit status;
- bounded stdout or stderr;
- per-worker readiness poll history;
- final HTTP or URL error;
- startup command identity;
- the worker that first diverged.

The final `ports_open=[]` observation occurred after cleanup and cannot prove that no port ever
opened. `runtime_evidence_found=[]` confirms that no earlier runtime artifact survived into the
failure bundle.

## Competing explanations

The current evidence cannot distinguish among:

- process exit during model or runtime initialization;
- continued startup beyond the polling window;
- incorrect model, host, port, or command realization;
- CUDA or native-library failure after process creation;
- worker-specific resource or configuration failure;
- readiness endpoint failure while the process remained alive.

None may be promoted to root cause.

## Approved implementation boundary

Add typed, bounded, sanitized worker-startup diagnostics and embed them in the launcher failure
bundle. Preserve zero hidden retries and retain one terminal state per worker. Then create a new
post-merge harness materialization lineage, perform metadata-only input inspection, integrate the
new identities, issue a fresh authorization, and run at most one governed retry.

## Safety and non-claims

```text
gpu_session_active=false
authorization_reuse_permitted=false
unchanged_rerun_permitted=false
model_requests_performed=0
benchmark_trajectory_requests_performed=0
credentials_used=false
customer_data_used=false
external_spend=0
measured_execution_authorized=false
```

This review does not claim model-load failure, vLLM failure, CUDA failure, timeout insufficiency,
cache qualification, measured effects, or production readiness.

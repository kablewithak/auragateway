# ADR: Add bounded worker-startup observability before qualification retry

- **Status:** Accepted for implementation
- **Date:** 2026-07-22
- **Repository base:** `d4558d44d57237fb2559f3cd6ddccfd22a31e07a`
- **Decision:** `WORKER_STARTUP_OBSERVABILITY_REQUIRED`
- **Failure class:** `WORKER_STARTUP_FAILURE_OPAQUE_PROCESS_OUTPUT`

## Context

CUDA 12.9 environment-qualification Attempt 5 reached the current runtime adapter and
attempted to start two vLLM workers. Neither worker became observably healthy before the
bounded readiness window ended. The immutable run terminated with:

```text
worker failed bounded readiness polling
```

The retained launcher evidence proves a real qualification failure, but it does not preserve
the process output needed to identify the cause. The current adapter starts workers with both
`stdout` and `stderr` bound to `subprocess.DEVNULL`. Its terminal readiness error does not
identify the worker, process state, poll history, or final health failure. The launcher failure
bundle records only a generic failure record and traceback.

## Alternatives considered

### Repeat the unchanged qualification

Rejected. The same adapter would discard the same evidence and likely produce another opaque
failure. A rerun that cannot add diagnostic information is not justified.

### Increase the readiness timeout

Rejected. There is no evidence that slow startup, rather than process exit or configuration
failure, caused the timeout. Increasing the budget would hide the missing diagnostic boundary.

### Print raw worker output directly to the notebook

Rejected. Unbounded process logs are noisy, may expose paths or environment-derived values,
and are not a typed or reproducible evidence contract.

### Capture bounded, sanitized per-worker startup diagnostics

Accepted. This is the smallest maintainable change that can distinguish process exit,
continued startup, endpoint failure, and worker-specific divergence without introducing hidden
retries or changing the experiment.

## Decision

Implement a typed worker-startup diagnostic boundary that preserves:

1. worker identity, GPU index, host, and port;
2. process exit state;
3. readiness poll count and final sanitized health error;
4. startup command SHA-256 rather than raw secret-bearing command material;
5. bounded sanitized stdout and stderr tails;
6. zero hidden retries, worker replacement, or fallback;
7. embedding of the diagnostic artifact in the launcher failure bundle.

The implementation must not serialize raw environment values, authorization payloads, model
content, or secrets.

## Authority consequence

Changing the runtime adapter and launcher changes the executable harness boundary. The current
`426f57d` harness remains immutable historical authority and must not be patched. After the
observability implementation merges, a new post-merge harness source package must be
materialized and inspected before active manifest, launcher, and authorization identities move.

## Validation requirements

Tests must cover bounded output, sanitization, exited and still-running processes, worker-specific
poll histories, diagnostic embedding, cleanup, and rejection of hidden retries. Generated
launcher parity and historical-harness non-interference remain mandatory.

## Non-claims

This decision does not establish that the model failed to fit, that vLLM or CUDA failed, that a
specific worker caused the failure, that a longer timeout would succeed, or that the environment
is qualified.

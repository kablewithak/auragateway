# Local A/B/C CUDA 12.9 vLLM CLI Contract Hardening v1

## Current state

```text
qualification_status=FAILED_CLOSED
failure_stage=initial_worker_startup
rejected_option=--disable-log-requests
replacement_option=--no-enable-log-requests
model_requests_performed=0
benchmark_trajectory_requests_performed=0
fresh_issuer_usable=false
rerun_permitted=false
```

## Implementation gate

The implementation must prove:

1. the canonical worker plan contains `--no-enable-log-requests`;
2. the obsolete option is absent;
3. command hashes are regenerated;
4. the target-runtime dependency-lock process validates every governed long
   option against the pinned vLLM `api_server --help` output;
5. missing options fail before worker spawn;
6. the consumed authorization and failed attempt remain preserved;
7. authorization issuance remains blocked.

## Post-merge sequence

1. synchronize clean `main`;
2. prepare the exact post-merge harness source toolchain;
3. materialize it in a CPU-only Kaggle notebook;
4. inspect the materialized input metadata-only;
5. integrate the new harness identity;
6. issue one fresh bounded authorization;
7. permit one fresh-session qualification attempt.

## Circuit breaker

A second CLI or worker-command contract failure ends per-flag remediation.
The next action must be a complete CLI capability-contract redesign.

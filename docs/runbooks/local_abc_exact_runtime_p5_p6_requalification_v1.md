# Runbook — Exact-Runtime P5/P6 Requalification V1

## Current legal state

```text
implementation_status=IMPLEMENTED_NOT_EXECUTED
p5_p6_exact_runtime_requalified=false
runtime_execution_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
```

Do not execute the generated notebook during the implementation tranche.

## Repository implementation validation

The producer owns the generated review, implementation record, and notebook.

Canonical sequence:

```text
python -m auragateway.local_abc.p5_p6_exact_runtime_requalification_v1 generate
python -m auragateway.local_abc.p5_p6_exact_runtime_requalification_v1 validate
```

Run changed-mutable-Python Ruff/format and focused mypy before focused tests.

Do not manually edit the generated notebook or generated JSON records. Change the
producer/template and regenerate.

## Generated runtime boundary

The notebook contains one unexecuted code cell. The cell embeds the rendered
runtime source as base64 and verifies the exact runtime-script SHA-256 before
execution.

The runtime itself then requires a future live authorization before runtime
installation.

## Future authorization input

The separate issuer must eventually produce exactly one Kaggle input member named:

```text
execution_authorization_v1.json
```

The runtime consumer requires:

```text
authorization_id=
auragateway-exact-runtime-p5-p6-requalification-v1-execution-authorization

scope=EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1
decision=AUTHORIZED
lifecycle=ISSUED
runtime_execution_authorized=true
single_use=true
every_terminal_attempt_consumes_authorization=true
unchanged_replay_authorized=false
pilot_execution_authorized=false
final_measured_abc_execution_authorized=false
maximum_model_requests=6
maximum_worker_starts=3
maximum_model_loads=3
hidden_retries_permitted=0
```

It must also bind the exact runtime-script, implementation-review, design-record,
and V5-acceptance SHA-256 values and provide a currently valid timezone-aware
issuance/expiry window.

The authorization issuer is not part of this tranche.

## Future runtime inputs

The governed execution will require the already accepted:

- exact-runtime wheelhouse/materialization input;
- pinned Qwen model snapshot;
- fresh single-use execution authorization;
- Kaggle T4 x2 allocation;
- Internet disabled.

Platform and input readiness must be reobserved immediately before issuance.

## Runtime terminal behavior

Valid technical terminal classifications are:

```text
PASSED_PENDING_REPOSITORY_ACCEPTANCE
FAILED_PENDING_REPOSITORY_DISPOSITION
AMBIGUOUS_PENDING_REPOSITORY_DISPOSITION
```

A technical PASS is not repository acceptance.

Preserve the generated evidence ZIP and terminal output unchanged for the
subsequent evidence-disposition tranche.

## Stop rules

Stop immediately if:

- exact authority identity drifts;
- authorization is missing, expired, duplicated, or semantically invalid;
- a required metric is absent or ambiguously attributable;
- token identity cannot be proved;
- worker generation or route realization cannot be proved;
- a hidden retry/fallback occurs;
- request counts do not reconcile;
- teardown fails.

Do not retry a failed governed execution merely to obtain a green artifact.

## Next gate after implementation merge

`DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V1_EXECUTION_AUTHORIZATION_ISSUER`

# AuraGateway CUDA 12.9 Option C Runtime Diagnostic Decision

## Executive decision

Option C is approved:

```text
P0-P2 platform diagnostic
→ explicit TRITON_ATTN implementation
→ P3-P6 runtime diagnostic
→ successor qualification
```

The selected backend remains `TRITON_ATTN`. The decision changes execution
order, not the backend choice.

## Inspection result

The read-only producer and consumer search matched **85 paths**.

That set is intentionally broader than the mutable implementation boundary. It
contains:

- current runtime source;
- tests;
- generated worker plans and execution requests;
- launchers and notebooks;
- previous authority records;
- historical evidence integration records;
- authorization reviews;
- unrelated files matching generic terms such as `dtype`.

Historical evidence and superseded records remain immutable. They must not be
globally rewritten merely because they contain automatic-backend commands or
historical worker hashes.

## True mutable boundary for this tranche

This decision tranche adds only:

```text
one canonical decision record
one validator
one focused test module
one ADR
one report
one runbook
```

It does not change:

```text
worker_command_template
--dtype auto
worker command SHA-256 values
worker_startup_plan.json
qualification_execution_request.json
runtime dependency lock
reviewed core
launcher source
launcher notebook
materialized harness
authorization issuer
authorization payload
```

## Why the boundary is narrow

The highest-cost uncertainty is currently below the model-serving layer:

```text
Kaggle image identity
libcuda linker visibility
minimal Triton compilation
```

Those questions can be answered without model loading, worker startup, or model
requests. Implementing runtime changes before that evidence exists would
increase future-change cost and risk another early full-run failure.

## Failure budget

```text
P0-P2 platform diagnostic sessions: 1
explicit Triton full qualification attempts: 1
bounded compatibility candidates: at most 3
fourth blind vLLM repair cycle: prohibited
```

## Immediate next gate

After this decision package merges:

```text
implement P0-P2 platform diagnostic assets
```

The P0-P2 implementation must produce bounded, machine-readable evidence and
stop at the first failed probe.

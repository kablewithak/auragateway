# ADR — Measured A/B/C Execution Authorization V1 Design

Date: 2026-08-08
Status: Proposed for merge
Source main: `c2750d73c3675dc1efe021b71d4b42156c2db5e3`

## Context

The governed P5/P6 successor execution is now accepted. Current-line P5 and P6 are true, measured A/B/C is eligible, and measured execution remains unauthorized.

The repository also contains two dangerous historical artifacts:

1. `benchmarks/local_abc/measured_execution_authorization_v1.json` authorizes a historical 72-trajectory run.
2. `data/evals/benchmark/freeze-v1/execution_manifest.json` is a historical frozen manifest with hosted-provider/Groq lineage.

Neither may be promoted into the current 342-trajectory local-vLLM benchmark.

Preflight-v3 is the current planning lineage. It freezes the 342-trajectory schedule but intentionally leaves execution disabled and the execution manifest unfrozen. The current plan is 162 functional trajectories plus 180 runtime-microbenchmark trajectories, for 342 total trajectories and 1,368 planned turns.

## Decision

Create an additive successor authorization boundary:

`measured_abc_execution_authorization_v1`

Do not mutate or reinterpret the historical measured authorization contract.

The successor issuer will be implemented in a later slice and must fail closed unless all current-line predecessor gates are satisfied.

## Required authority graph

```text
governed P5/P6 acceptance
        +
preflight-v3 planning lineage
        +
accepted variance pilot
        +
accepted repetition-count freeze
        +
current 342-trajectory execution-manifest freeze
        +
fresh platform capability observation
        +
explicit operator confirmation
        ↓
single-use measured A/B/C authorization
        ↓
verify immediately before execution
        ↓
exactly one governed execution attempt
        ↓
terminal consume / abandon
```

## Historical lineage rule

The following are historical context only:

- the 72-trajectory `measured_execution_authorization_v1.json`;
- the old `freeze-v1/execution_manifest.json`;
- `src/auragateway/local_abc/measured_authorization.py`.

They remain immutable evidence. They do not size, authorize, or define the current benchmark.

## Freeze / authorization separation

The current final execution manifest must remain frozen with `execution_enabled=false`.

Runtime permission is carried only by a transient single-use authorization artifact. This prevents a frozen scientific manifest from becoming a mutable operational permission switch.

The issuer must not create or modify:

- variance-pilot evidence;
- repetition-count decisions;
- the final frozen execution manifest.

Those are predecessor authorities.

## Successor authorization contract

The implementation must provide deterministic lifecycle operations:

- `validate-implementation`
- `issue`
- `verify`
- `consume`
- `abandon`

Issuance must be non-overwriting and single-use.

Terminal consumption must support:

- `PASSED`
- `FAILED`
- `INTERRUPTED`
- `TIMED_OUT`
- `KAGGLE_PLATFORM_TERMINATED`
- `OUTCOME_UNKNOWN`

After terminalization, runtime and measured-execution authorization are false and the authorization is not reusable.

## Budget boundary

The issuer must bind, not infer:

- 342 planned trajectories;
- 1,368 planned turns;
- at most 2,736 request attempts;
- at most one retry after an initial attempt;
- zero hidden retries;
- no replacement cases;
- one Kaggle session;
- one saved version;
- zero external network requests;
- zero external spend;
- no credentials;
- no customer data.

Every request attempt must remain attributable to the frozen ledger.

## Platform boundary

The issued authorization must be tied to a fresh Kaggle capability observation and explicit operator confirmation.

Expected platform characteristics include:

- GPU T4 x2;
- two allocated GPUs;
- internet disabled;
- local vLLM;
- Qwen/Qwen2.5-0.5B-Instruct at revision `7ae557604adf67be50417f59c2c2f167def9a775`;
- worker 1 on GPU 0 / port 8001;
- worker 2 on GPU 1 / port 8002.

Exact runtime identities must come from accepted current-line authority, not from historical preflight placeholders.

## Privacy and evidence controls

The successor issuer and execution package must preserve:

- no customer data;
- no credentials;
- no raw prompt logging;
- no raw output logging;
- no raw worker-log capture in public evidence;
- request-attempt reconciliation;
- governed teardown;
- machine-readable terminal evidence.

## Rejected alternatives

### Reuse the historical 72-trajectory authorization

Rejected. Its case-count and trajectory-count contract is structurally incompatible with preflight-v3.

### Reuse the old frozen execution manifest

Rejected. It contains hosted-provider/Groq lineage and is not the current local-vLLM experiment.

### Flip `execution_enabled` inside the frozen manifest

Rejected. Scientific freeze and operational permission must remain separate.

### Issue authorization before variance/repetition freeze

Rejected. This would permit execution before the experiment size is finally governed.

## Consequences

The next implementation slice can build a small, inspectable issuer around exact current authority.

This ADR does not authorize execution, does not run a variance pilot, and does not freeze the final manifest.

## Next gate

`implement_measured_abc_execution_authorization_v1`

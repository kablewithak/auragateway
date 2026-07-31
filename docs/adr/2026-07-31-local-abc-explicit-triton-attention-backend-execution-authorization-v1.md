# ADR: Add a transient single-use authorization for the Q6 attention-backend probe

- Status: Accepted for implementation
- Date: 2026-07-31
- Source main: `6ede70538c52165d92a1df68e2c8bbc97a123c49`
- Implementation feature commit: `dc9484492169965e0ed17d77bf1894d1ae9e7cb8`

## Context

PR #169 merged the model-free explicit Triton attention-backend V1 harness. It
binds the accepted driver and P0-P2 evidence, generates an exact two-cell
notebook, rejects silent fallback, validates Tesla T4 capability, and defines
one backend-owned attention primitive compared with PyTorch SDPA.

The merged implementation remains:

```text
IMPLEMENTED_NOT_EXECUTED
runtime_execution_authorized=false
```

The next runtime transition is Q5 to Q6. It must not reuse either consumed
upstream diagnostic and must not broaden into workers, models, requests, cache
qualification, or A/B/C measurement.

## Decision

Implement a separate repository-native authorization issuer with these
properties:

- exact binding to PR #169 merge and feature commits;
- exact binding to implementation record, request, review, template, and
  notebook SHA-256 identities;
- explicit operator confirmation;
- maximum 240-minute validity window;
- one Kaggle session;
- one platform preflight, offline installation, backend discovery, import,
  capability validation, and attention-primitive attempt;
- zero models, workers, model requests, benchmark trajectories, network
  requests, credentials, customer data, and external spend;
- transient authorization and consumption artifacts remain untracked;
- non-overwriting atomic issuance;
- successful, failed, or interrupted execution consumes the authorization;
- unchanged replay is not authorized.

The implementation PR generates only a deterministic authorization review and
implementation record. It does not issue live authority.

## Enforcement mode

The merged Q6 notebook does not parse the transient authorization artifact.
Authorization V1 is therefore an operator gate bound to the exact notebook hash:

```text
cc997ca683776a1bf54be6321ba1efc43fe28fd68957f94a22fa553512bca208
```

The issuer verifies synchronized `main`, source ancestry, exact implementation
identities, a clean worktree, the live time window, and absence of a consumption
receipt immediately before the operator starts the single Kaggle run.

This is weaker than runtime-loader enforcement. It is stated as a non-claim and
is an extension seam for a future authorization-aware launcher if Q6 evidence
justifies further investment.

## Rejected alternatives

### Execute immediately after PR #169

Rejected because implementation authority is not runtime authority.

### Reuse the accepted P0-P2 run

Rejected because both accepted upstream executions are consumed and do not
exercise the attention backend.

### Commit a permanent authorization JSON

Rejected because a reusable tracked authorization would destroy the one-time,
time-bounded control.

### Authorize a worker or model request

Rejected because Q6 is model-free and must not infer Q7-Q12 readiness.

### Modify the Q6 notebook in this tranche

Rejected because this gate authorizes the exact merged PR #169 notebook. A
notebook modification would create a new implementation identity requiring a
separate re-review.

## Consequences

Positive:

- runtime activity is separated from implementation;
- exact code and notebook identities are auditable;
- one failed attempt cannot silently become an unchanged retry;
- the action budget is machine-readable and regression-tested;
- no secrets or customer data enter the authorization payload.

Costs:

- the operator must verify authority immediately before execution;
- the notebook itself does not enforce the transient file;
- a consumption receipt must be created after any execution attempt;
- a future launcher may be required for runtime-native authorization checks.

## Next gate

After this implementation merges:

```text
EXPLICIT_OPERATOR_CONFIRMATION_THEN_ISSUE_EXPLICIT_TRITON_ATTENTION_BACKEND_EXECUTION_AUTHORIZATION_V1
```

No Kaggle or GPU execution is permitted in this PR.

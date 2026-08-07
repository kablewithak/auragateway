# ADR: P5/P6 Successor Unauthorized Execution Reconciliation V1

## Status

Approved for repository implementation.

## Context

Kaggle saved version `340872949` executed the correct P5/P6 Successor Runtime
Qualification V1 payload and produced internally consistent technical evidence. The
evidence archive SHA-256 is
`7f14ab45aeb4abd858c9905ca06553bd325f21035d5d9d7533424fbadfa47583`.

The run completed P3, P4, P5, and P6 with five model requests, three model loads,
three worker starts, zero hidden retries, zero benchmark trajectories, zero network
requests, and zero external spend. P5 cache/reset telemetry and P6 worker-route
isolation evidence are technically successful.

However, the pre-execution single-use authorization lineage is not established for
saved version `340872949`. The static issuer had been merged, but no governed
pre-execution authorization receipt is available to bind this attempt.

## Decision

Preserve the exact technical evidence and classify the run as:

```text
technical_status=PASSED
authorization_lineage_status=UNESTABLISHED_AT_EXECUTION
governed_acceptance_status=INVALID_UNGOVERNED_EXECUTION
current_line_p5_pass_accepted=false
current_line_p6_pass_accepted=false
measured_abc_eligible=false
```

Do not manufacture or infer retroactive authority.

Bind the reconciliation to the exact saved-version ID, runtime/notebook identities,
evidence ZIP identity, terminal log identity, evidence-member manifest, P5 telemetry,
P6 route-isolation telemetry, teardown result, and the merged static authorization
issuer authority.

The preserved execution is diagnostic evidence only. It cannot satisfy the governed
current-line P5/P6 acceptance gate.

## Consequences

A fresh Kaggle capability observation, fresh single-use authorization, and one fresh
successor execution are required.

Saved version `340872949` must not be replayed unchanged as a governed attempt. No
measured A/B/C execution becomes eligible or authorized from this reconciliation.

The next gate is:

```text
merge_then_observe_kaggle_issue_fresh_authorization_and_repeat_p5_p6_successor_once
```

## Rejected alternatives

- Do not discard the technically useful evidence.
- Do not promote the technical PASS into governed P5/P6 acceptance.
- Do not create retroactive authorization.
- Do not treat absence of a current transient file as proof of pre-execution authority.
- Do not authorize measured A/B/C from this run.

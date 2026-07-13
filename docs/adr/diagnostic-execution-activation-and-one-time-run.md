# ADR: Activate Diagnostic Execution Separately from the Provider Run

**Status:** Accepted
**Decision ID:** `diagnostic-execution-activation-v1`

## Context

The diagnostic design, prompt fixtures, and inactive execution review have passed their gates.

The remaining boundary is to make a one-time provider execution possible without performing it as part of implementation, testing, pull-request review, or merge validation.

## Decision

Introduce an active authorization and executable runner in one non-executing slice.

The active authorization binds:

- the reviewed authorization package;
- the reviewed dry-run report;
- the inactive review manifest;
- the fixture manifest;
- the protected prompt-bundle hash;
- the exact provider profile;
- the 24-attempt absolute schedule;
- the 24-call and 5,000-microusd ceilings;
- public and protected evidence paths;
- the no-retry and no-resume policy.

The CLI exposes four commands:

- `validate`
- `live-preflight`
- `run`
- `verify`

Only `run` may instantiate the provider adapter. It requires the exact confirmation phrase and a deliberately loaded process credential.

## Runtime behavior

The runner represents every one of the 24 planned attempts, including attempts skipped after a sequence-level or experiment-level stop.

A request rejection:

- records one provider error;
- stops the current sequence;
- does not retry;
- permits the next predeclared sequence.

Any other provider error:

- records one provider error;
- stops the full experiment;
- records every remaining attempt as skipped;
- does not retry or resume.

## One-time boundary

Any existing public journal, public report, public record set, public manifest, protected raw-output file, or protected failure-diagnostic file blocks a fresh execution.

An interrupted run therefore leaves evidence that prevents outcome-shopping or silent restart. Recovery requires a new reviewed authorization.

## Consequences

Positive:

- merge does not call the provider;
- the live command is explicit;
- the reviewed schedule is enforced;
- all planned attempts remain accountable;
- failure does not erase later skipped attempts;
- public evidence remains content-free;
- raw outputs remain protected locally.

Trade-off:

- a failed or interrupted execution cannot resume;
- a new authorization is required for any replacement run.

## Non-claims

Activation does not establish provider behavior, cache effects, cost savings, latency improvement, quality improvement, or causal conclusions.

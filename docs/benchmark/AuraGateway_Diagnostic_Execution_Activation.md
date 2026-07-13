# AuraGateway Diagnostic Execution Activation

**Authorization ID:** `batch-06-diagnostic-execution-auth-v1`
**Status:** `active`
**Provider execution performed by this slice:** No
**Next gate:** `live_execution_preflight`

## Purpose

This slice converts the reviewed diagnostic plan into an executable one-time harness without making a provider call.

The actual live execution remains a separate deliberate terminal action after merge.

## Frozen execution

The authorization permits:

- 8 sequences;
- 24 planned attempts;
- at most 24 provider calls;
- at most 4,992 planned-cost microusd under the 5,000-microusd authorization ceiling;
- a minimum 2,220-second absolute schedule;
- one execution only.

It forbids:

- retries;
- resume;
- held-out execution;
- full benchmark execution;
- benchmark claims;
- comparison eligibility.

## Commands

### Validate

Validates every frozen dependency without reading `GROQ_API_KEY`.

### Live preflight

Checks:

- exact authorization and runtime policy;
- reviewed design and fixtures;
- protected prompt-bundle identity;
- credential presence;
- writable public and protected sinks;
- absence of previous execution evidence.

It does not instantiate a Groq client or call the provider.

### Run

The run command requires:

- the exact authorization ID;
- `GROQ_API_KEY` deliberately loaded in the current process;
- the exact confirmation phrase `EXECUTE_BATCH_06_DIAGNOSTIC_ONCE`;
- a completely fresh evidence boundary.

### Verify

Reconciles:

- 24 journal attempt records;
- the public record set;
- the outcome report;
- the execution manifest;
- the reviewed provider-request identities.

It does not read credentials or call the provider.

## Stop policy

`PROVIDER_REQUEST_REJECTED` stops only the current sequence.

Every other provider error stops the entire experiment.

No provider error is retried.

All remaining planned attempts receive explicit skipped records, preserving full accountability.

## Evidence boundary

Public:

- authorization;
- runtime policy;
- journal;
- run records;
- report;
- manifest.

Protected local:

- raw provider outputs;
- provider failure diagnostics;
- prompt cohorts.

Public evidence contains hashes, byte counts, bounded token telemetry, statuses, safe error codes, counts, and schedule observations only.

## Known hygiene correction

This slice also removes six trailing-space violations from the two PR #41 Markdown documents. No substantive wording changes are made.

## Acceptance criteria

- active authorization validates;
- live preflight fails without a credential;
- live preflight succeeds with a synthetic test credential without provider calls;
- fake-provider all-success execution accounts for 24 calls;
- request rejection stops one sequence and continues;
- systemic error stops the experiment;
- rerun is blocked by retained evidence;
- public evidence excludes protected output text;
- fake execution verifies;
- full tests, Ruff, formatting, mypy, and diff checks pass;
- no live provider call occurs during the slice.

## Non-claims

This slice does not establish the Batch 06 root cause or any cache, latency, cost, quality, or provider-internal claim.

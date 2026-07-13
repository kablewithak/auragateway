# AuraGateway Diagnostic Execution Authorization Review

**Review ID:** `batch-06-diagnostic-execution-review-v1`
**Status:** `review_ready`
**Activation:** `inactive`
**Provider calls permitted:** No
**Execution command available:** No
**Next gate:** `active_authorization_review`

## Purpose

This slice proves exactly what a later diagnostic execution would do without permitting it to happen.

It binds the immutable design and fixture evidence, reconstructs the 24-attempt schedule, and validates the privacy, budget, timing, and provider-request boundaries.

## Frozen dependencies

The review binds:

- diagnostic experiment plan;
- diagnostic design manifest;
- fixture recipe;
- fixture manifest;
- protected local prompt bundle.

Any byte drift fails validation.

## Provider profile

The reviewed request profile is:

- provider: Groq;
- model alias: `groq-gpt-oss-20b`;
- exact model: `openai/gpt-oss-20b`;
- adapter: `groq-chat-completions-v1`;
- maximum completion tokens: 256;
- temperature: 0;
- streaming: false;
- storage: false;
- reasoning effort: low;
- request timeout: 30 seconds.

No credential is read during validation or dry-run.

## Dry-run schedule

The review reproduces:

- 8 sequences;
- 3 attempts per sequence;
- 24 maximum provider calls;
- 18 unique provider-visible requests;
- 6 intentional request repetitions from the alpha and beta order-reversal pairs;
- 5,000 microusd total cost ceiling;
- 2,220-second minimum planned elapsed time.

The minimum schedule is 37 minutes before provider response latency.

## Timing projection

The attempt offsets are:

`0, 0, 0, 300, 300, 300, 600, 600, 600, 900, 900, 900, 1200, 1200, 1200, 1500, 1530, 1560, 1860, 1860, 1860, 2160, 2190, 2220`

The 300-second gaps isolate sequence groups. The two 30-second spacing cells contribute the additional 120 seconds.

## Evidence boundary

A later active runner must write public metadata only to:

- `data/evals/benchmark/diagnostic-execution-v1/journal.jsonl`
- `data/evals/benchmark/diagnostic-execution-v1/run_records.json`
- `data/evals/benchmark/diagnostic-execution-v1/report.json`

Protected raw outputs and failure diagnostics remain beneath `.local`.

Public evidence may not contain raw prompts, raw outputs, provider error messages, credentials, or headers.

## Stop and recovery boundary

The underlying design remains authoritative:

- request rejection stops the current sequence without retry;
- systemic, ambiguous, budget, integrity, or privacy failures stop the experiment;
- retries are forbidden;
- resume is forbidden.

The review package does not implement execution. It only proves the planned schedule and boundaries.

## Acceptance criteria

- all five dependency hashes reconcile;
- protected prompt bundle verification passes;
- the committed dry-run report reproduces exactly;
- all 24 attempt indices are contiguous;
- the final planned offset is 2,220 seconds;
- provider calls remain disabled;
- no active authorization exists;
- no Batch 07 assets exist;
- tests, Ruff, formatting, mypy, and diff checks pass.

## Non-claims

This slice does not:

- call Groq;
- authorize a provider call;
- establish the Batch 06 root cause;
- prove cache behavior;
- establish order or spacing causation;
- establish latency, cost, quality, or cache savings;
- create a comparison-eligible result.

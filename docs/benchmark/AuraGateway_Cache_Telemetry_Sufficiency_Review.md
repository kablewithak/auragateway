# AuraGateway Cache Telemetry Sufficiency Review

**Review ID:** `cache-telemetry-sufficiency-review-v1`

**Status:** `blocked_provider_observation_gap`

**Provider calls authorized:** No

**Next gate:** `groq_cache_telemetry_capture_hardening`

## Executive decision

The current evidence is insufficient for provider cache-usage, cache-savings,
latency-improvement, or accepted A/B/C comparison claims.

The correct next action is adapter telemetry hardening, not another live run.

## Observed evidence

The source diagnostic closeout records:

- 24 provider calls;
- 24 successful calls;
- 24 input-token samples;
- 24 duration samples;
- 0 cached-input-token samples;
- unknown total cached tokens;
- unknown cached-token share;
- no conversion of unknown to zero.

## Official provider boundary

Groq's prompt-caching documentation states that prompt caching is automatic on
supported requests, uses exact prefix matching, applies to
`openai/gpt-oss-20b`, expires after two hours without use, and gives a fifty
percent discount to cached input portions.

The official Groq Python schema exposes:

- `usage.prompt_tokens_details.cached_tokens`;
- `x_groq.usage.dram_cached_tokens`;
- `x_groq.usage.sram_cached_tokens`.

These paths are not interchangeable by default. The first is the documented
prompt-cache usage field. The latter two are named as hardware cache
statistics.

## Repository assessment

The current adapter:

- parses `usage.prompt_tokens_details.cached_tokens`;
- emits `cached_input_tokens=None` when the field is unavailable;
- does not retain `x_groq` hardware cache statistics;
- does not retain field-presence diagnostics for successful responses;
- does not retain the exact installed Groq SDK version.

The project dependency range is `groq>=1.5,<2`, so the exact runtime SDK version
cannot be reconstructed from `pyproject.toml` alone.

Successful raw responses were discarded by design after typed mapping.
Therefore the historical evidence cannot distinguish among:

- the API response omitted the field;
- the installed SDK version omitted or transformed the field;
- the field existed but was not preserved by the current mapping.

## Signal assessment

### Billing prompt-cache tokens

Field:

`usage.prompt_tokens_details.cached_tokens`

Current adapter parsing: Yes

Observed samples: 0 of 24

Claim use: Blocked

### DRAM hardware cache tokens

Field:

`x_groq.usage.dram_cached_tokens`

Current adapter parsing: No

Billing equivalence established: No

Claim use: Blocked

### SRAM hardware cache tokens

Field:

`x_groq.usage.sram_cached_tokens`

Current adapter parsing: No

Billing equivalence established: No

Claim use: Blocked

## Required hardening

The next implementation must:

1. capture the exact installed Groq SDK version;
2. retain presence bits for usage and cache-related fields;
3. retain billing and hardware cache signals separately;
4. prevent hardware signals from satisfying billing-cache gates;
5. add synthetic present, absent, zero, and positive-value tests;
6. prepare a separate three-call calibration review.

## Calibration shape

The future calibration should remain separately reviewed and capped at three
provider calls:

1. cold request;
2. exact-prefix repeat;
3. second exact-prefix repeat.

The calibration must prohibit retries and resume and must not be treated as an
A/B/C benchmark.

## Claim boundary

Blocked:

- provider cache usage;
- provider cache savings;
- latency improvement;
- accepted A/B/C comparison.

Not authorized:

- provider calls;
- calibration execution;
- full benchmark execution.

## Commercial translation

This review demonstrates a buyer-relevant reliability behavior: the system
does not turn missing provider telemetry into a favorable cache claim.

The proof asset belongs in an AI System Evaluation Audit or Agent Harness
Hardening Sprint as evidence of:

- telemetry provenance control;
- claim gating;
- SDK drift awareness;
- provider-specific semantic separation;
- bounded calibration design.

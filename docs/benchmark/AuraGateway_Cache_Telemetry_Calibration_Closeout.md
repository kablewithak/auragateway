# AuraGateway Cache Telemetry Calibration Closeout

**Closeout ID:** `groq-cache-telemetry-calibration-closeout-v1`

**Status:** `closed_billing_field_unavailable`

**Authorization consumed:** Yes

**Rerun permitted:** No

**Next gate:** `groq_sdk_cache_schema_compatibility_review`

## Executive result

The one-time calibration completed all three planned calls successfully.

The billing cache field was absent on all three successful responses.

This proves that billing cache evidence was unavailable through the observed
runtime boundary. It does not prove that provider caching did or did not occur.

## Execution outcome

| Measure | Result |
|---|---:|
| Planned attempts | 3 |
| Provider calls | 3 |
| Successful calls | 3 |
| Provider errors | 0 |
| Invalid telemetry calls | 0 |
| Skipped attempts | 0 |
| Estimated bounded cost | 600 micro-USD |

The cost is a harness estimate, not a provider invoice.

## Schedule integrity

| Attempt | Role | Planned offset | Observed offset |
|---:|---|---:|---:|
| 0 | cold | 0 seconds | 0 ms |
| 1 | warm repeat one | 10 seconds | 10,000 ms |
| 2 | warm repeat two | 20 seconds | 20,000 ms |

All three calls used the same frozen provider request identity.

## Token observations

Each call reported:

- 1,401 input tokens;
- 27 output tokens.

Totals:

- 4,203 observed input tokens;
- 81 observed output tokens.

The frozen planning estimate was 2,112 input tokens per call, or 6,336 total.
It conservatively exceeded observed input tokens by 2,133 tokens.

## Successful-response telemetry

All three calls reported:

| Signal | Count |
|---|---:|
| Usage present | 3 |
| Installed SDK version `1.5.0` | 3 |
| `prompt_tokens_details` present | 0 |
| Billing cached-token field present | 0 |
| Numeric billing-cache samples | 0 |
| `x_groq` present | 3 |
| `x_groq.usage` present | 0 |
| DRAM cache field present | 0 |
| SRAM cache field present | 0 |
| Numeric hardware-cache samples | 0 |

The billing observation state was `field_absent` on every call.

Unknown was not interpreted as zero.

## Duration observations

Durations were:

- 98 ms;
- 130 ms;
- 113 ms.

Summary:

- total: 341 ms;
- mean: 113.667 ms;
- median: 113 ms;
- minimum: 98 ms;
- maximum: 130 ms.

These values are descriptive only. Three sequential calls do not support a
latency-improvement claim.

## Claim decisions

Permitted:

- the one-time calibration executed and verified;
- the billing cache field was unavailable across the three successful calls.

Blocked:

- exact cause of field unavailability;
- provider cache usage;
- provider cache savings;
- hardware cache usage;
- latency improvement;
- accepted A/B/C comparison.

## Engineering resolution

Retain:

- installed SDK version capture;
- successful-response field-presence telemetry;
- billing-versus-hardware signal separation;
- protected output isolation;
- one-time authorization, rerun, and resume controls.

Do not select:

- request-construction changes;
- routing changes;
- cache-affinity changes;
- benchmark restart.

## Next investigation

The next gate is a non-live Groq SDK cache-schema compatibility review.

It must inspect:

1. the installed `groq==1.5.0` response model;
2. the current supported SDK response schema;
3. whether `model_dump()` can preserve the documented billing field;
4. whether the provider omitted the field before SDK mapping;
5. whether a controlled SDK upgrade requires a new compatibility slice.

A new live provider run is not authorized by this closeout.

## Commercial proof

This is an AI System Evaluation Audit proof asset.

It demonstrates that the harness:

- executes a bounded provider experiment once;
- preserves unavailable evidence as unavailable;
- prevents rerun-based evidence selection;
- separates public metadata from protected output;
- converts an inconclusive provider signal into a narrow engineering gate.

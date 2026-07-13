# AuraGateway Cache Telemetry Calibration Activation

**Authorization ID:** `groq-cache-telemetry-calibration-auth-v1`

**Status:** `active`

**Provider calls performed in this slice:** 0

**Execution command available:** Yes

**Benchmark execution authorized:** No

**Next gate:** `live_calibration_preflight`

## Purpose

This slice activates the reviewed three-call Groq cache telemetry calibration.

It does not execute the calibration during implementation.

## Frozen execution

The future run contains:

| Attempt | Role | Offset |
|---:|---|---:|
| 0 | cold | 0 seconds |
| 1 | warm repeat one | 10 seconds |
| 2 | warm repeat two | 20 seconds |

All three attempts use one exact provider request identity.

## Provider profile

- provider: Groq;
- model: `openai/gpt-oss-20b`;
- model alias: `groq-gpt-oss-20b`;
- adapter: `groq-chat-completions-v1`;
- telemetry capture: `groq-cache-telemetry-capture-v1`;
- output-token ceiling: 32;
- temperature: 0;
- streaming: false;
- storage: false;
- reasoning effort: low;
- timeout: 30 seconds.

## Runtime controls

Execution requires:

- exact authorization ID;
- exact confirmation phrase;
- process-local `GROQ_API_KEY`;
- verified protected prompt bundle;
- fresh public and protected evidence paths.

The harness forbids:

- retries;
- resume;
- a second run;
- request identity drift;
- missing telemetry shape;
- public raw output;
- benchmark execution.

## Evidence

Public evidence after execution:

- `journal.jsonl`;
- `run_records.json`;
- `report.json`;
- `manifest.json`.

Protected local evidence:

- synthetic prompt bundle;
- provider outputs.

The public attempt records retain content-free telemetry shape, SDK provenance,
token counts, cache-field presence, cache values, output hashes, and timing.

## Claim boundary

This activation does not establish:

- a cache hit;
- cache savings;
- latency improvement;
- cost improvement;
- B or C superiority;
- an accepted A/B/C comparison;
- production readiness.

## Next operational step

After this activation merges:

1. create a separate live evidence branch;
2. materialize and verify the protected prompt;
3. run complete check-only release gates;
4. load the Groq credential without printing it;
5. run live preflight;
6. execute the exact three-call calibration once;
7. remove the credential immediately;
8. verify and classify evidence;
9. close out the calibration before the handover Q&A.

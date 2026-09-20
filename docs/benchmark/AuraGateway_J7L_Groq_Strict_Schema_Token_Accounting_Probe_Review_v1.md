# AuraGateway J7L Groq Strict-Schema Token Accounting Probe Review V1

## Disposition

`REVIEW_READY_INACTIVE`

This slice freezes a non-live review for a two-call synthetic Groq accounting probe. It does not
read `GROQ_API_KEY`, create a provider client, expose an execution function, or authorize network
access.

## Why the probe exists

Observed preactivation measurements:

- `openai-harmony`: `0.0.8`
- Groq SDK: `1.5.0`
- model projection only: `9,452` tokens
- canonical semantic registry only: `7,027` tokens
- 48-case registry-plus-case range: `7,184..7,310`
- exact candidate message range: `7,322..7,448`
- conservative message-plus-schema maximum: `7,916`
- planned reference output budget: `384`
- conservative combined envelope: `8,300`
- cases at or above 8,000 under conservative envelope: `48`
- `/models` preflight: HTTP 200
- target model present: true
- target model active: true
- target context window: `131,072`
- `/models` token-limit headers: absent
- observed organization limit: `8,000 TPM`, `30 RPM`, `1,000 RPD`, `200,000 TPD`

The remaining question is whether strict JSON Schema is visible in provider-reported prompt-token
usage. The answer changes whether the current Groq R0 path should be closed immediately or
advanced to a full-size synthetic qualification.

## Frozen experiment

Two future calls, after separate activation:

1. `control_no_response_format`
2. `strict_json_schema`

The messages, model, output ceiling, temperature, reasoning effort, streaming setting, storage
setting, and timeout are identical. Only `response_format` may differ.

The prompt is synthetic and contains no J7L case, reference answer, Jev output, or hidden
authoring metadata.

## Primary observation

Compare `strict_prompt_tokens - control_prompt_tokens`.

Interpretation:

- positive: schema machinery is visible in provider-reported prompt usage; current Groq J7L shape
  is not authorized under the observed 8,000 TPM boundary;
- zero: schema is not visible in `usage.prompt_tokens`, but rate-accounting remains unresolved;
  perform a separately governed full-size synthetic qualification;
- negative: invalid/inconclusive result; stop and investigate.

Rate-limit response headers are retained when present but are secondary evidence because rolling
window behavior can make a two-call remaining-token delta ambiguous.

## Resource and privacy controls

- maximum provider calls after activation: 2;
- external spend ceiling: R0;
- paid fallback: prohibited;
- retry: prohibited;
- resume: prohibited;
- rerun: prohibited;
- raw payloads: protected local only;
- public artifacts: hashes, typed usage, safe headers, and classifications only;
- J7L reference requests: prohibited;
- Jev requests: prohibited.

## Next gate

`J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ACTIVATION_V1`

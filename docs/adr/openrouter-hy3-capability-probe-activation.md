# ADR: OpenRouter Hy3 Capability-Probe Activation

- **Status:** Accepted
- **Date:** 2026-07-14
- **Decision ID:** `openrouter-hy3-capability-probe-auth-v1`

## Context

The OpenRouter Hy3 identifiability review, adapter dry run, and capability-probe authorization
review have passed. The next boundary is to activate one bounded capability probe without executing
it during repository validation.

The provider is OpenRouter. The requested model is `tencent/hy3:free`. OpenRouter remains the raw
HTTP, routing, and normalized telemetry authority. This activation does not alter the closed Groq
lineage and does not authorize the A/B/C pilot.

## Decision

Create an active one-time authorization with these limits:

```text
logical calls: 2
maximum provider successes: 2
maximum retained successes: 2
maximum total inference attempts: 4
maximum transient replacements per logical call: 1
```

The protected prompt bundle is generated locally from the committed deterministic recipe. It is
never committed. The local boundary also contains the preflight receipt, write-through journal,
raw responses, and parsed responses.

The activation runner exposes only:

```text
validate
prepare-local
preflight
verify-local
```

It does not expose an inference execution command.

## Credential and network boundary

`validate`, `prepare-local`, and `verify-local` do not read `OPENROUTER_API_KEY` and do not use the
network.

`preflight` requires the exact phrase:

```text
PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE
```

It then performs exactly two non-inference requests:

```text
GET /api/v1/key
GET /api/v1/models
```

The receipt retains only hashes and bounded numeric account metadata. The API key and key label are
not retained in plaintext.

## Execution boundary

The later execution runner must require:

```text
EXECUTE_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE
```

No provider inference call is made by this activation slice. A successful preflight does not
consume the inference authorization.

## Privacy

Every future inference request must retain:

```text
provider.data_collection = deny
provider.zdr = true
provider.order absent
synthetic public-safe prompt only
```

The prompt bundle, preflight receipt, raw responses, parsed responses, and journal remain under
`.local/`.

## Formal methods

The previously accepted executable finite-state model remains governing. No separate TLA+ toolchain
is introduced.

## Consequences

Positive:

- activation is inspectable before credential use;
- prompt and session identities are deterministic;
- successful preflight is locally auditable;
- inference remains impossible without a separate execution runner and exact confirmation phrase;
- historical evidence remains immutable.

Trade-offs:

- the model catalog confirms route visibility, not provider endpoint count;
- key status does not reveal exact remaining free-model requests before a 429 response;
- a successful preflight does not prove cache telemetry or cache use.

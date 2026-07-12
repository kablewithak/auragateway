# AuraGateway Groq and Ollama Provider Calibration

## Decision

AuraGateway uses two deliberately different runtime boundaries during Phase 3:

```text
Hosted provider: Groq
Hosted model: openai/gpt-oss-20b
Evidence role: observed provider cached-input telemetry

Local runtime: Ollama
Local model: llama3.2:3b
Evidence role: inferred local prompt-evaluation timing
```

These evidence families must remain separate. Ollama timing cannot authorize a provider cached-token claim. Groq cached-token fields cannot be used as proof of provider cache residency, TTL enforcement, or internal KV-cache implementation.

## Scope

This slice implements:

- one Groq chat-completions adapter;
- one Ollama generate-API adapter;
- protected in-memory prompt containers;
- typed response extraction;
- safe provider error mapping;
- deterministic response snapshots;
- a free-plan-only Groq smoke command;
- a local Ollama timing smoke command;
- sanitized reports written only beneath `.local/provider-calibration/`.

This slice does not start the A/B/C benchmark and does not implement routing.

## Governing evidence semantics

Gate 4 remains frozen.

### Groq

Current Groq documentation checked on 2026-07-12 describes automatic exact-prefix caching for `openai/gpt-oss-20b` and reports:

```text
usage.prompt_tokens
usage.prompt_tokens_details.cached_tokens
usage.completion_tokens
usage.total_time
```

AuraGateway maps those fields to `CachedInputDetailTelemetry`:

```text
prompt_tokens -> input_tokens
cached_tokens -> cached_input_tokens
completion_tokens -> output_tokens
total_time seconds -> total_duration_ms
```

A missing `cached_tokens` value remains `None`. It is never converted to zero.

A live Groq response may expose `prompt_tokens_details` in the SDK schema while omitting the field from the actual response. In that case, the live adapter calibration may still pass when prompt-token, completion-token, duration, identity, output-digest, and privacy controls succeed. The cache-efficiency claim remains machine-blocked with `CACHE_EVIDENCE_UNAVAILABLE`.

The smoke harness sends two calls with the same synthetic system prefix and a changing final user suffix. A positive cache count is useful evidence, but is not required for adapter correctness because cache hits and cache-detail availability are provider-managed.

### Ollama

Current Ollama generate-API documentation checked on 2026-07-12 reports:

```text
prompt_eval_count
prompt_eval_duration
eval_count
total_duration
```

Durations are returned in nanoseconds. AuraGateway converts positive durations to integer milliseconds using ceiling conversion and maps them to `LocalPromptEvaluationTelemetry`.

Ollama evidence remains `inferred_local`. It cannot authorize a provider cache-efficiency claim.

## Protected content boundary

Raw system and user text exist only inside `ProtectedProviderPrompt` for the lifetime of one invocation.

The class:

- suppresses raw content from `repr`;
- permits only SHA-256 digests and byte counts in reports;
- caps prompt size at 200,000 UTF-8 bytes;
- rejects empty prompts;
- does not provide JSON serialization for raw text.

Provider adapters may inspect raw SDK or HTTP response objects only inside the adapter method. They immediately convert responses to typed metadata and discard the raw object.

Sanitized reports contain:

- request and fixture IDs;
- provider and model aliases;
- prompt digests and byte count;
- output digest;
- typed telemetry;
- normalized telemetry;
- claim-sufficiency decisions.

They do not contain prompts, outputs, credentials, provider request IDs, or raw payloads.

## Bounded smoke policy

### Groq smoke

```text
Calls: 2
Model: openai/gpt-oss-20b
Input estimate per call: 2,300 tokens
Output budget per call: 64 tokens
Reasoning effort: low
SDK retries: 0
Timeout: 60 seconds
Credential source: GROQ_API_KEY process environment only
Plan posture: free-plan only; no paid fallback
```

The token count is a preflight estimate, not provider billing evidence. The live provider response remains the source of observed usage.

### Ollama smoke

```text
Calls: 2
Model: llama3.2:3b
Endpoint: http://localhost:11434/api/generate
Output budget per call: 32 tokens
Timeout: 300 seconds
Keep-alive: 5 minutes
```

The Ollama smoke is local and does not require a hosted-provider credential.

The 300-second ceiling is provider-specific. A single CPU-only diagnostic on the selected
`llama3.2:3b` Q4_K_M runtime measured 168.83 seconds wall time, including 163.11 seconds
of prompt evaluation for 1,558 prompt tokens. This observation justifies a bounded local
ceiling; it is not a latency baseline or performance claim. Groq remains capped at 60 seconds.

## Deterministic calibration

The deterministic fixture suite contains:

- one Groq cold-style response with zero cached tokens;
- one Groq warm-style response with a positive cached-token count;
- two Ollama prompt-evaluation timing responses.

All four responses pass through the real adapter extraction code.

Acceptance requires:

- provider and model identity match;
- output content becomes a SHA-256 digest;
- Groq cache evidence maps to the frozen provider semantic family;
- Ollama timing maps to the frozen local semantic family;
- Groq cache claims are permitted only when denominator fields exist;
- Ollama cache claims remain blocked;
- no raw content appears in CLI output or reports.

## Failure taxonomy

The adapters produce bounded codes for:

- authentication failure;
- permission denial;
- rate or quota limit;
- provider timeout;
- connection failure;
- provider unavailability;
- missing model;
- missing SDK;
- configuration mismatch;
- ambiguous response;
- invalid response.

Raw exception messages and provider bodies are not exposed in safe messages.

## Runbook

Deterministic validation:

```powershell
python -m auragateway.providers.calibration_runner validate --repo-root .
```

Groq smoke after loading `GROQ_API_KEY` into the current process:

```powershell
python -m auragateway.providers.calibration_runner groq-smoke --repo-root .
```

Ollama smoke while the local application is running:

```powershell
python -m auragateway.providers.calibration_runner ollama-smoke --repo-root .
```

Live reports are ignored by Git and written beneath:

```text
.local/provider-calibration/<UTC timestamp>/
```

## Claim boundary

After deterministic validation, AuraGateway may claim only that the Groq and Ollama adapter mappings are locally validated against typed snapshots.

After a successful live smoke, AuraGateway may additionally claim that the named runtime returned fields compatible with the frozen contracts under the recorded date, model, SDK range, and local environment.

This slice does not prove:

- guaranteed Groq cache hits;
- Groq cache residency or eviction behavior;
- latency or cost improvement;
- Ollama provider-style cache reuse;
- cross-provider comparability;
- route-policy safety;
- A/B/C benchmark readiness;
- production readiness.

## Commercial proof angle

This boundary supports a future Context, Cache, and Agent Runtime Efficiency Audit by showing how to distinguish trustworthy hosted cache evidence from local timing signals, block unsupported claims automatically, and retain a reviewable report without leaking customer content.

## Documentation references checked

- Groq Prompt Caching, checked 2026-07-12
- Groq Python Quickstart and official Python package, checked 2026-07-12
- Ollama Generate API, checked 2026-07-12

# AuraGateway Telemetry Semantics

## Purpose

This document defines the deterministic Gate 4 provider-telemetry boundary.

## Semantic families

| Family | Preserved meaning | Cache evidence level |
|---|---|---|
| `cached_input_detail` | Provider total input plus cached-input detail | observed provider |
| `cache_creation_read` | Uncached, cache-creation, and cache-read components | observed provider |
| `local_prompt_evaluation` | Local prompt-evaluation count and timing | inferred local |
| `unavailable` | No trustworthy telemetry | unavailable |

No family is converted into a universal `cache_hit` field.

## Sufficiency rules

Cache, latency, and estimated-cost claims are decided independently.

- Cache claims require provider cache-token semantics with a valid denominator.
- Latency claims require at least one positive named timing field.
- Estimated-cost claims require sufficient provider token accounting and a matching versioned pricing schedule.
- Local timing cannot authorize provider cache or provider-token cost claims.
- Unknown fields remain `None`.

## Error taxonomy

```text
CACHE_EVIDENCE_UNAVAILABLE
CACHE_SEMANTICS_MISMATCH
LATENCY_EVIDENCE_UNAVAILABLE
LATENCY_SEMANTICS_MISMATCH
TOKEN_EVIDENCE_UNAVAILABLE
PRICING_EVIDENCE_UNAVAILABLE
PRICING_SEMANTICS_MISMATCH
```

## Privacy boundary

Fixtures and reports contain only synthetic metadata, bounded numeric fields, aliases, decision codes, and hashes. Raw prompts, messages, documents, outputs, provider payloads, PII, and secrets are prohibited.

## Live-provider extension seam

A live adapter may inspect a provider SDK response only inside its adapter module. It must immediately produce the typed provider result and one telemetry payload family. Any new provider meaning requires a versioned contract and deterministic fixture before claims are permitted.

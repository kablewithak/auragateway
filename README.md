# AuraGateway

AuraGateway is a production-shaped, local-first cache-aware agent runtime and AI reliability
evaluation harness.

Its core engineering question was whether deterministic context construction and cache-affinity
routing could reduce avoidable repeated prompt work, latency, or estimated cost without reducing
task quality.

## Terminal project status

```text
PRD version: 2.3.0
core runtime and harness: implemented
core terminal evidence review: complete
Groq provider lineage: closed with successful responses and missing required cache field
OpenRouter/Hy3 extension: closed on first cold-call HTTP 401 before model inference
Gate 4 contract integrity: passed
Gate 4 live evidence sufficiency: did not pass
measured A/B/C comparison: not authorized and not completed
provider cache usage measured: false
provider cache savings measured: false
runtime provider execution: terminally closed
next optional phase: sanitized Hugging Face publication integration
```

AuraGateway did not force the benchmark after its evidence gates failed.

- Groq returned two successful raw-wire responses, but both omitted
  `usage.prompt_tokens_details.cached_tokens`.
- The separately authorized OpenRouter `tencent/hy3:free` capability probe reached OpenRouter once,
  returned HTTP `401` before a successful completion, consumed its one-time authorization, and did
  not proceed to generation metadata, a warm call, the pilot, or the retained benchmark.

## Final evidence conclusions

Permitted:

- deterministic static-prefix construction;
- typed static and volatile context boundaries;
- prefix mutation and volatile-leak detection;
- cache-affinity policy implementation and fixed-fixture validation;
- provider-aware telemetry normalization;
- absent and null telemetry remaining unknown;
- bounded one-time provider execution with append-only evidence;
- immutable, hash-bound provider lineages;
- Groq wire-field omission for the two observed successful calls;
- OpenRouter/Hy3 pre-inference authentication failure for the one authorized cold attempt.

Blocked:

- provider cache hit or miss;
- cached tokens equal to zero;
- measured provider cache usage;
- measured provider cache savings;
- successful Hy3 model inference;
- Hy3 route, cache, latency, or cost conclusions;
- completed A/B/C benchmark results;
- universal cost or latency savings;
- production readiness.

## Provider evidence matrix

| Provider lineage | Live result | Cache evidence | Terminal disposition |
|---|---|---|---|
| Groq raw-wire reauthorization | Two successful responses | Required cached-token field absent | Closed; A/B/C blocked |
| OpenRouter `tencent/hy3:free` | First cold attempt returned HTTP 401 | No completion or cache telemetry | Closed; authorization consumed |

See the full [Provider Evidence Matrix](docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md).

## Maturity

```text
Production-shaped
Locally validated
Synthetic-corpus validated
Fixed-eval validated
Controlled-provider tested
Not customer-data tested
Not deployed
Not production-ready
```

`Controlled-provider tested` means the provider boundaries and terminal outcomes were exercised
under controlled authorizations. It does not mean that a valid cache benchmark result was obtained.

## Governing documents

- [AuraGateway v2 PRD 2.3.0](docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md)
- [OpenRouter Hy3 Mini PRD 1.1.0](docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md)
- [Core Terminal Evidence Review](docs/benchmark/AuraGateway_v2_Terminal_Evidence_Review.md)
- [OpenRouter Hy3 Terminal Evidence Review](docs/benchmark/AuraGateway_OpenRouter_Hy3_Terminal_Evidence_Review.md)
- [Provider Evidence Matrix](docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md)
- [Session Brief](docs/session/AuraGateway_SESSION_BRIEF.md)
- [Terminal Provider Evidence Handover](docs/handover/AuraGateway_Handover_Terminal_Provider_Evidence.md)
- [Hugging Face Publication Layer PRD](docs/product/AuraGateway_Hugging_Face_Publication_Layer_PRD.md)
- [Benchmark Constitution](docs/benchmark/AuraGateway_Benchmark_Constitution.md)
- [Privacy and Vendor Boundary](docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md)
- [Evidence Bundle Specification](docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md)

## Terminal provider evidence chain

### Groq lineage

1. The initial live calibration could not support the required cache claim.
2. SDK compatibility review confirmed the nested cache schema was supported by the tested SDK.
3. A materially different raw-wire reauthorization captured raw and parsed views of the same
   responses.
4. Both successful raw responses omitted
   `usage.prompt_tokens_details.cached_tokens`.
5. The authorization was consumed and the lineage was closed without a cache result.

### OpenRouter/Hy3 lineage

1. Experimental identifiability, route semantics, and claims were frozen.
2. A generic OpenRouter adapter was validated with absent, null, zero, positive, and mismatch
   fixtures.
3. A bounded execution constitution and exhaustive finite-state model were reviewed.
4. A protected prompt bundle and metadata-only preflight were completed.
5. The one-time execution runner was merged before the live call.
6. The first cold completion request returned HTTP `401` with the safe message
   `Missing Authentication header`.
7. No successful completion, generation metadata, cache telemetry, or warm call followed.
8. The authorization was consumed and a sanitized terminal closeout was committed.

## Local validation

Create and activate the environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Validate the terminal evidence chain:

```powershell
python -m auragateway.benchmark.cache_telemetry_calibration_execution_runner verify --repo-root .
python -m auragateway.benchmark.cache_telemetry_calibration_closeout_runner validate --repo-root .
python -m auragateway.benchmark.groq_sdk_cache_schema_compatibility_runner validate --repo-root .
python -m auragateway.benchmark.groq_cache_telemetry_reauthorization_runner validate --repo-root .
python -m auragateway.benchmark.groq_cache_telemetry_reauthorization_execution_runner verify --repo-root .
python -m auragateway.benchmark.groq_cache_telemetry_reauthorization_closeout_runner validate --repo-root .
python -m auragateway.benchmark.auragateway_v2_terminal_evidence_review_runner validate --repo-root .
python -m auragateway.benchmark.openrouter_hy3_capability_probe_closeout_runner validate-public --repo-root .
```

Run release gates:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
git diff --check
```

## Privacy boundary

Public evidence excludes credentials, authorization-header values, raw prompts, user messages,
private retrieved documents, HMAC secrets, customer data, protected session identities, and raw
provider response bodies.

Protected raw and parsed provider responses remain under ignored `.local` paths. Public closeouts
retain only hashes, safe metadata, bounded error fields, claim decisions, and non-claims.

## Scope boundary

AuraGateway is not a production gateway, generic proxy, billing platform, cloud deployment, managed
routing service, or production-ready application.

The current Groq and OpenRouter/Hy3 authorizations are terminally consumed. No resume, rerun, or
additional A/B/C provider execution is permitted under those evidence lineages.

A later Hugging Face phase is optional and must remain a static publication adapter over sanitized,
precomputed artifacts. It must not introduce live inference, credentials, customer data, or
protected provider payloads.

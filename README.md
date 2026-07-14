# AuraGateway

AuraGateway is a production-shaped, local-first cache-aware agent runtime and AI reliability
evaluation harness.

Its core engineering question was whether deterministic context construction and cache-affinity
routing could reduce avoidable prefill work, latency, or estimated cost without reducing task
quality.

## Terminal project status

```text
PRD version: 2.2.0
core runtime and harness: implemented
terminal evidence review: complete
controlled provider execution: complete
Gate 4 contract integrity: passed
Gate 4 live numeric evidence sufficiency: closed unavailable
measured A/B/C comparison: not completed
core scope: closed
next phase: Hugging Face publication layer design
```

The required Groq billing cache field was absent from both successful raw HTTP responses in the
authorized two-call reauthorization. AuraGateway therefore blocked the measured A/B/C benchmark
rather than treating missing telemetry as zero or inferring a cache result from latency.

## Final evidence conclusion

Permitted:

- deterministic static-prefix construction;
- typed static and volatile context boundaries;
- prefix mutation and volatile-leak detection;
- cache-affinity policy implementation and fixed-fixture validation;
- provider-aware telemetry normalization;
- unknown telemetry remaining unknown;
- immutable, hash-bound evidence lineage;
- Groq wire-field omission for the two observed calls.

Blocked:

- universal Groq omission behavior;
- provider cache hit or miss;
- cached tokens equal to zero;
- measured provider cache usage;
- measured provider cache savings;
- completed A/B/C benchmark results;
- universal cost or latency savings;
- production readiness.

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

## Governing documents

- [AuraGateway v2 PRD 2.2.0](docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md)
- [Terminal Evidence Review](docs/benchmark/AuraGateway_v2_Terminal_Evidence_Review.md)
- [Terminal Evidence ADR](docs/adr/auragateway-v2-terminal-evidence-review.md)
- [Session Brief](docs/session/AuraGateway_SESSION_BRIEF.md)
- [Hugging Face Publication Layer PRD](docs/product/AuraGateway_Hugging_Face_Publication_Layer_PRD.md)
- [Benchmark Constitution](docs/benchmark/AuraGateway_Benchmark_Constitution.md)
- [Privacy and Vendor Boundary](docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md)
- [Evidence Bundle Specification](docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md)

## Terminal provider evidence chain

1. Original calibration closed with the billing field unavailable.
2. SDK compatibility review showed Groq SDK 1.5.0 supports the nested cache schema.
3. A materially different raw-wire reauthorization captured raw and parsed views of the same
   responses.
4. Both successful raw responses omitted
   `usage.prompt_tokens_details.cached_tokens`.
5. The terminal closeout consumed the authorization and prohibited rerun, resume, benchmark
   execution, and comparison claims.
6. The project-level terminal review closed core scope with the negative result intact.

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

Public evidence excludes credentials, raw prompts, user messages, private retrieved documents,
HMAC secrets, customer data, and protected provider response bodies.

Protected raw and parsed provider responses remain under ignored `.local` paths. Terminal validators
use public hashes and metadata only.

## Scope boundary

AuraGateway is not a production gateway, generic proxy, billing platform, cloud deployment, managed
routing service, or production-ready application.

The next phase is a separate Hugging Face publication adapter using sanitized, precomputed artifacts.
It must not introduce live inference, credentials, customer data, or protected provider payloads.

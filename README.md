# AuraGateway

AuraGateway is a cache-aware agent runtime and evaluation harness for controlled AI reliability benchmarking.

## North Star

AuraGateway tests whether deterministic context construction and cache-affinity routing can reduce avoidable prefill work, latency, or estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, or useful feedback retention.

## Project Status

- **Design baseline:** AuraGateway v2 PRD 2.1.0
- **Execution allocation:** 200 hours
- **Delivery ledger after this slice:** 95 / 200 planned hours (47.5%)
- **Current phase:** Phase 3 — Provider Adapters and Telemetry Calibration
- **Active proof gate:** Gate 4 — Telemetry Integrity
- **Gate 0 status:** Passed
- **Gate 1 status:** Passed — retrieval configuration frozen
- **Gate 2 status:** Passed — functional and runtime diagnostic episode assets frozen
- **Gate 3 status:** Passed — canonical static prefix and HMAC fingerprint frozen
- **Constitution:** Version 1.0.0 — frozen
- **Measured execution:** Prohibited until the execution manifest and downstream proof gates are frozen
- **Architecture posture:** local-first, provider-neutral, typed, eval-driven, and privacy-safe
- **Maturity:** retrieval, diagnostic eval, and prefix-determinism assets locally validated and hash-frozen

The prior README ledger displayed 77 / 200 after the context-boundary slice. The accepted continuity ledger was 82 / 200; this slice adds the remaining 13 planned Gate 3 hours and records 95 / 200.

## Governing Documents

- [AuraGateway v2 PRD](docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md)
- [Session Brief](docs/session/AuraGateway_SESSION_BRIEF.md)
- [Frozen Benchmark Constitution](docs/benchmark/AuraGateway_Benchmark_Constitution.md)
- [Gate 0 Freeze Review](docs/benchmark/AuraGateway_Gate_0_Freeze_Review.md)
- [Execution Manifest Requirements](docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md)
- [Evidence Bundle Specification](docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md)
- [Privacy and Vendor Boundary](docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md)
- [Gate 1 Retrieval Freeze Report](docs/benchmark/Nimbus_Relay_Gate_1_Freeze_Report.md)
- [Diagnostic Episode Constitution](docs/benchmark/Nimbus_Relay_Diagnostic_Episode_Constitution.md)
- [Gate 2 Readiness Report](docs/benchmark/Nimbus_Relay_Gate_2_Readiness_Report.md)
- [Context Boundary Design](docs/benchmark/AuraGateway_Context_Boundary_Design.md)
- [Canonical Prefix Design](docs/benchmark/AuraGateway_Canonical_Prefix_Design.md)
- [Gate 3 Prefix Determinism Report](docs/benchmark/AuraGateway_Gate_3_Prefix_Determinism_Report.md)

## Frozen Retrieval Configuration

```text
Retriever: dense-hashed-tfidf-section-aware-remediated-v2
Chunking: section-aware-v1
Top-k: 5
Metadata policy: authored-case-filters-v1
Configuration fingerprint:
220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490
```

## Frozen Prefix Configuration

```text
Serialization version: canonical-static-provider-v1
Template: nimbus-relay-support-template-v1@1.0.0
HMAC key ID: synthetic-prefix-fixture-key-v1
Static prefix fingerprint:
6b7c72729eca9480ef7a0cf734b957dd6c10fa9ff88adc33e322af54d50f4d63

Five-turn stability: 5 / 5
Mutation calibration: 7 / 7
```

Raw static content, raw volatile content, prompts, user messages, retrieved documents, outputs, provider payloads, PII, secrets, and HMAC key material remain outside public traces.

## Freeze Model

AuraGateway uses separate controls:

1. **Benchmark Constitution** — frozen at Gate 0.
2. **Retrieval Configuration** — frozen at Gate 1.
3. **Diagnostic Episode Assets** — frozen at Gate 2.
4. **Static Prefix Determinism** — frozen at Gate 3.
5. **Execution Manifest** — frozen only after all required downstream assets exist.

Passing Gate 3 does not permit measured execution.

## Current Benchmark Conditions

- **Condition A:** Cache-Hostile Baseline
- **Condition B:** Prefix-Deterministic Runtime
- **Condition C:** Cache-Aware Agent Runtime

The intended causal interpretations are:

- **A versus B:** context-construction policy only
- **B versus C:** cache-affinity route policy only
- **A versus C:** total system effect, not a single-mechanism causal claim

## Scope Boundary

AuraGateway is not a production gateway, generic proxy, billing platform, dashboard, cloud deployment, or production-ready service.

It is a standalone advanced AI reliability systems lab and a Week 3 companion project only. It is not a dependency of the primary AI consultancy roadmap.

## Local Development

AuraGateway uses Python 3.11 or later with Pydantic v2 contracts.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Gate 3 verification requires an environment-loaded synthetic fixture key for reproducibility:

```powershell
$env:AURAGATEWAY_PREFIX_HMAC_KEY = "auragateway-synthetic-prefix-fixture-key-v1-20260712"
$env:AURAGATEWAY_PREFIX_HMAC_KEY_ID = "synthetic-prefix-fixture-key-v1"
```

Validate the complete historical evidence chain:

```powershell
python -m auragateway.corpus.freeze verify --repo-root .
python -m auragateway.chunking.runner verify --repo-root .
python -m auragateway.retrieval.runner verify --repo-root .
python -m auragateway.retrieval.dense_runner verify --repo-root .
python -m auragateway.evals.runner verify --repo-root .
python -m auragateway.evals.selection_runner verify --repo-root .
python -m auragateway.evals.heldout_runner verify --repo-root .
python -m auragateway.evals.remediation_runner verify --repo-root .
python -m auragateway.evals.heldout_v2_runner verify --repo-root .
python -m auragateway.evals.episode_runner verify --repo-root .
python -m auragateway.context.runner verify --repo-root .
python -m auragateway.context.prefix_runner verify --repo-root .
```

Run release gates:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
```

## Phase 2 Boundary

Gate 3 is complete. The next implementation slice begins Gate 4 with the fake provider, deterministic provider fixtures, typed telemetry contracts, and provider-semantic sufficiency decisions.

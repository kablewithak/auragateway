# AuraGateway

AuraGateway is a cache-aware agent runtime and evaluation harness for controlled AI reliability benchmarking.

## North Star

AuraGateway tests whether deterministic context construction and cache-affinity routing can reduce avoidable prefill work, latency, or estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, or useful feedback retention.

## Project Status

- **Design baseline:** AuraGateway v2 PRD 2.1.0
- **Execution allocation:** 200 hours
- **Delivery ledger after this slice:** 82 / 200 planned hours (41%)
- **Current phase:** Phase 2 — Typed Contracts and Context Compiler
- **Active proof gate:** Gate 3 — Prefix Determinism
- **Gate 0 status:** Passed
- **Gate 1 status:** Passed — retrieval configuration frozen
- **Gate 2 status:** Passed — functional and runtime diagnostic episode assets frozen
- **Constitution:** Version 1.0.0 — frozen
- **Measured execution:** Prohibited until the execution manifest and downstream proof gates are frozen
- **Architecture posture:** local-first, provider-neutral, typed, eval-driven, and privacy-safe
- **Maturity:** retrieval and diagnostic eval assets hash-frozen; typed context partition boundary locally validated

## Governing Documents

- [AuraGateway v2 PRD](docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md)
- [Session Brief](docs/session/AuraGateway_SESSION_BRIEF.md)
- [Frozen Benchmark Constitution](docs/benchmark/AuraGateway_Benchmark_Constitution.md)
- [Gate 0 Freeze Review](docs/benchmark/AuraGateway_Gate_0_Freeze_Review.md)
- [Execution Manifest Requirements](docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md)
- [Evidence Bundle Specification](docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md)
- [Privacy and Vendor Boundary](docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Gate 1 Retrieval Freeze Report](docs/benchmark/Nimbus_Relay_Gate_1_Freeze_Report.md)
- [Diagnostic Episode Constitution](docs/benchmark/Nimbus_Relay_Diagnostic_Episode_Constitution.md)
- [Gate 2 Readiness Report](docs/benchmark/Nimbus_Relay_Gate_2_Readiness_Report.md)
- [Context Boundary Design](docs/benchmark/AuraGateway_Context_Boundary_Design.md)
- [Context Boundary Report](docs/benchmark/AuraGateway_Context_Boundary_Report.md)

## Frozen Retrieval Configuration

```text
Retriever: dense-hashed-tfidf-section-aware-remediated-v2
Chunking: section-aware-v1
Top-k: 5
Metadata policy: authored-case-filters-v1
Configuration fingerprint:
220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490
```

## Frozen Diagnostic Episode Assets

```text
Functional episodes: 18
Development episodes: 12
Held-out episodes: 6
Turns per episode: 4
Runtime microbenchmark subset: 6
Rejected proposals retained: 8
Blinded review: 100% primary review, 25% double review
```

Terminal-decision distribution:

```text
answer: 10
clarify: 3
escalate: 3
refuse: 2
```

The episode assets contain synthetic raw user messages for controlled evaluation. Raw messages, prompts, retrieved text, model outputs, provider payloads, PII, and secrets remain prohibited from public traces.

## Freeze Model

AuraGateway uses separate controls:

1. **Benchmark Constitution**
   - frozen at Gate 0;
   - defines causal contrasts, run rules, failure accounting, review policy, statistics, and invalidation rules.

2. **Retrieval Configuration**
   - frozen at Gate 1;
   - binds corpus, chunking, retrieval, metadata policy, top-k, and held-out evidence.

3. **Diagnostic Episode Assets**
   - frozen at Gate 2;
   - binds functional episodes, held-out separation, runtime subset, rejected proposals, terminal decisions, and blinded review protocol.

4. **Execution Manifest**
   - frozen only after all required downstream assets exist;
   - pins provider/model, adapters, prompts, schemas, rubrics, pricing, and implementation hashes.

Passing Gate 2 does not permit measured execution.

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

Validate the complete historical chain and the diagnostic episode freeze:

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
```

Run release gates:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
```

## Phase 2 Boundary

The typed static-anchor registry and volatile-append contract are locally validated. Gate 3 remains open. The next slice implements canonical serialization, HMAC-SHA256 prefix fingerprints, mutation audits, and a five-turn prefix-stability report.

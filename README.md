# AuraGateway

AuraGateway is a cache-aware agent runtime and evaluation harness for controlled AI reliability benchmarking.

## North Star

AuraGateway tests whether deterministic context construction and cache-affinity routing can reduce avoidable prefill work, latency, or estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, or useful feedback retention.

## Project Status

- **Design baseline:** AuraGateway v2 PRD 2.1.0
- **Execution allocation:** 200 hours
- **Delivery ledger after this slice:** 69 / 200 planned hours (34.5%)
- **Current phase:** Phase 2 — Diagnostic Eval Set and Output Contracts
- **Active proof gate:** Gate 2 — Diagnostic Eval Asset Readiness
- **Gate 0 status:** Passed
- **Gate 1 status:** Passed — dense section-aware remediated retrieval frozen at top-k five
- **Constitution:** Version 1.0.0 — frozen
- **Measured execution:** Prohibited until the execution manifest and downstream proof gates are frozen
- **Architecture posture:** local-first, provider-neutral, typed, eval-driven, and privacy-safe
- **Maturity:** benchmark-constitution validated; Gate 1 retrieval contract locally validated and frozen

## Governing Documents

- [AuraGateway v2 PRD](docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md)
- [Session Brief](docs/session/AuraGateway_SESSION_BRIEF.md)
- [Frozen Benchmark Constitution](docs/benchmark/AuraGateway_Benchmark_Constitution.md)
- [Gate 0 Freeze Review](docs/benchmark/AuraGateway_Gate_0_Freeze_Review.md)
- [Execution Manifest Requirements](docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md)
- [Evidence Bundle Specification](docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md)
- [Privacy and Vendor Boundary](docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md)
- [Architecture Decision Records](docs/adr/README.md)
- [Chunking Candidate Design](docs/benchmark/Nimbus_Relay_Chunking_Design.md)
- [Chunking Candidate Report](docs/benchmark/Nimbus_Relay_Chunking_Candidate_Report.md)
- [Sparse Retrieval Design](docs/benchmark/Nimbus_Relay_Sparse_Retrieval_Design.md)
- [Sparse Retrieval Candidate Report](docs/benchmark/Nimbus_Relay_Sparse_Retrieval_Candidate_Report.md)
- [Development Retrieval Set](docs/benchmark/Nimbus_Relay_Development_Retrieval_Set.md)
- [BM25 Development Scorecard](docs/benchmark/Nimbus_Relay_BM25_Development_Scorecard.md)
- [Dense Retrieval Design](docs/benchmark/Nimbus_Relay_Dense_Retrieval_Design.md)
- [Dense Retrieval Development Report](docs/benchmark/Nimbus_Relay_Dense_Retrieval_Development_Report.md)
- [Held-Out v2 Constitution](docs/benchmark/Nimbus_Relay_Held_Out_V2_Constitution.md)
- [Gate 1 Retrieval Freeze Report](docs/benchmark/Nimbus_Relay_Gate_1_Freeze_Report.md)
- [Retrieval Selection Policy](docs/benchmark/Nimbus_Relay_Retrieval_Selection_Policy.md)
- [Development Retrieval Recommendation](docs/benchmark/Nimbus_Relay_Development_Retrieval_Recommendation.md)
- [Held-Out Retrieval Constitution](docs/benchmark/Nimbus_Relay_Held_Out_Retrieval_Constitution.md)
- [Gate 1 Held-Out Report](docs/benchmark/Nimbus_Relay_Gate_1_Held_Out_Report.md)
- [Retrieval Metadata Remediation Design](docs/benchmark/Nimbus_Relay_Retrieval_Metadata_Remediation_Design.md)
- [Retrieval Metadata Remediation Report](docs/benchmark/Nimbus_Relay_Retrieval_Metadata_Remediation_Report.md)

## Freeze Model

AuraGateway uses two separate controls:

1. **Benchmark Constitution**
   - frozen at Gate 0;
   - defines causal contrasts, run rules, failure accounting, review policy, statistics, and invalidation rules.

2. **Execution Manifest**
   - frozen only after the required downstream assets exist;
   - pins corpus, retrieval, provider/model, adapters, prompts, schemas, rubrics, manifests, pricing, and implementation hashes.

Freezing the constitution does not permit measured execution.

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

## Evidence Standard

Runtime improvements are accepted only when:

- the frozen constitution governs execution;
- the execution manifest is frozen before measured runs;
- compared runs share eligible configuration fingerprints;
- failed, excluded, retried, and invalidated runs remain visible;
- completed evidence bundles are append-only and hash-manifested;
- provider-reported and locally inferred evidence remain distinct;
- raw prompts, user messages, retrieved documents, model outputs, provider payloads, PII, and secrets remain outside public traces;
- fixed task-quality guardrails pass;
- claims remain limited to the named workload, provider/model, and benchmark configuration.


## Local Development

AuraGateway uses Python 3.11 or later with Pydantic v2 contracts.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Validate the frozen corpus, chunking candidates, sparse and dense candidates, and development scorecards:

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
```

Run release gates for the current slice:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
```

## Gate 1 retrieval freeze

```text
Held-out v1: preserved blocked evidence
Development remediation: complete
Held-out v2 finalists passing: 2 / 2
Selected retriever: dense-hashed-tfidf-section-aware-remediated-v2
Selected top-k: 5
Metadata policy: authored-case-filters-v1
Gate 1: passed
Measured runtime execution: prohibited
```

The freeze binds the corpus, section-aware chunks, remediated dense manifest, source metadata overlay,
selection policy, remediation report, held-out v2 set, selected scorecard, and Gate 1 decision.

## Phase 1 Boundary

Gate 1 is complete. Dense hashed-TFIDF section-aware retrieval with top-k five and the authored metadata policy is frozen under configuration fingerprint `220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490`. The retrieval freeze does not authorize measured runtime execution. Phase 2 begins with the diagnostic episode set and output contracts.

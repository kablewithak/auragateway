# AuraGateway

AuraGateway is a cache-aware agent runtime and evaluation harness for controlled AI reliability benchmarking.

## North Star

AuraGateway tests whether deterministic context construction and cache-affinity routing can reduce avoidable prefill work, latency, or estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, or useful feedback retention.

## Project Status

- **Design baseline:** AuraGateway v2 PRD 2.1.0
- **Execution allocation:** 200 hours
- **Current phase:** Phase 0 — Design Freeze and Benchmark Constitution
- **Active proof gate:** Gate 0 — Benchmark Constitution
- **Gate 0 status:** Passed
- **Constitution:** Version 1.0.0 — frozen
- **Measured execution:** Prohibited until the execution manifest and downstream proof gates are frozen
- **Architecture posture:** local-first, provider-neutral, typed, eval-driven, and privacy-safe
- **Maturity:** benchmark-constitution validated

## Governing Documents

- [AuraGateway v2 PRD](docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md)
- [Session Brief](docs/session/AuraGateway_SESSION_BRIEF.md)
- [Frozen Benchmark Constitution](docs/benchmark/AuraGateway_Benchmark_Constitution.md)
- [Gate 0 Freeze Review](docs/benchmark/AuraGateway_Gate_0_Freeze_Review.md)
- [Execution Manifest Requirements](docs/benchmark/AuraGateway_Execution_Manifest_Requirements.md)
- [Evidence Bundle Specification](docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md)
- [Privacy and Vendor Boundary](docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md)
- [Architecture Decision Records](docs/adr/README.md)

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

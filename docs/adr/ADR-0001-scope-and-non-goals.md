# ADR-0001: AuraGateway Scope and Non-Goals

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 0
- **Supersedes:** None

## Context

AuraGateway is intended to test a bounded engineering hypothesis:

> Whether deterministic context construction and cache-affinity routing can reduce avoidable prefill work, latency, or estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, or useful feedback retention.

The project is vulnerable to scope drift because the term "gateway" can imply a production proxy, authentication layer, billing product, provider marketplace, dashboard, failover platform, or deployment system.

Those products require materially different architecture, operational ownership, security posture, and proof. Building them would weaken the controlled experiment and consume the 200-hour allocation without improving the primary evidence question.

## Decision

AuraGateway will remain a standalone, local-first, production-shaped AI reliability systems lab.

Its critical path is:

1. benchmark constitution;
2. synthetic corpus and retrieval freeze;
3. typed context compiler;
4. prefix determinism and mutation detection;
5. provider telemetry normalization and sufficiency;
6. cache-affinity route policy;
7. fixed quality and feedback evaluation;
8. comparison eligibility and immutable evidence;
9. paired A/B/C execution;
10. reproducible reporting.

AuraGateway will not become a production gateway during this project.

## In scope

- synthetic, version-controlled technical-support corpus;
- dense and sparse retrieval comparison;
- deterministic static-anchor and volatile-append compilation;
- HMAC prefix fingerprints;
- provider-neutral inference boundary;
- one primary live provider when credentials permit;
- secondary provider fixtures;
- optional local timing evidence;
- typed cache and usage telemetry;
- cache-affinity route state and explicit route reasons;
- hard diagnostic multi-turn evaluation;
- blinded rubric review;
- trace-level feedback validity, novelty, retention, action change, and sufficiency;
- privacy-safe metadata traces;
- configuration fingerprints;
- comparison eligibility;
- immutable evidence bundles;
- one-command validation, execution, and reporting.

## Explicit non-goals

- production multi-tenancy;
- generic proxy compatibility;
- external API-key management;
- billing, quotas, or chargeback;
- frontend or dashboard development;
- Kubernetes or cloud deployment;
- managed vector database migration;
- production failover;
- customer-data ingestion;
- arbitrary user prompt templates;
- open-ended autonomous agents;
- multi-agent orchestration;
- fine-tuning;
- universal model or provider ranking;
- a universal EFC score;
- proof of provider-internal GPU KV-cache state;
- reproduction of Coinbase infrastructure or scale.

## Architecture posture

The implementation defaults to:

- Python 3.11 or later;
- Pydantic v2 contracts;
- pytest;
- Ruff and mypy;
- JSON logs;
- explicit errors and refusal states;
- local files and deterministic fixtures before managed infrastructure;
- provider SDK isolation inside adapters;
- no raw prompts, documents, outputs, provider payloads, PII, or secrets in traces.

Cloud infrastructure may be considered only in a separately approved later scope. It must not enter the benchmark's critical path.

## Scope-change rule

A proposed feature may enter scope only when it materially improves at least one of:

- benchmark validity;
- causal isolation;
- retrieval quality;
- cache evidence;
- route-policy evidence;
- quality safety;
- feedback-evidence quality;
- privacy controls;
- reproducibility;
- reviewer confidence.

If it does not improve one of those dimensions, it is deferred.

## Consequences

### Positive

- The benchmark remains implementable within 200 hours.
- Evidence quality takes priority over platform breadth.
- The repository remains portable and inspectable.
- Provider and deployment choices stay behind explicit boundaries.
- Commercial translation can use the proof without misrepresenting the artifact as a production gateway.

### Negative

- AuraGateway will not serve external traffic.
- It will not prove production load, incident response, authentication, or operational maturity.
- Some gateway capabilities described in industry systems will remain architectural inspiration only.

## Permitted maturity language

During implementation, use only evidence-backed labels such as:

- prototype;
- production-shaped;
- locally validated;
- synthetic-corpus validated;
- benchmark-constitution validated;
- fixed-eval validated;
- controlled-provider validated.

Do not use "production-ready" unless deployment, monitoring, security, incident response, load behaviour, and operational ownership have been demonstrated.

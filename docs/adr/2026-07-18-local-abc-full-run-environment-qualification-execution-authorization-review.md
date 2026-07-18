# ADR: Implement authorization inputs before issuing operational authority

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-environment-qualification-execution-authorization-review-v1`
- Source main merge: `768e0535d8d373385440acc2dc18952b4fc42325`
- Review fingerprint: `2709ea4c5c4f7d3ef404d16f500887c6ced4ae89fac5bfb2151fe22530c76e5a`

## Context

PR #104 merged an authorization-gated environment-qualification harness, typed runtime evidence
contracts, a static request, an unexecuted Kaggle notebook, and an operator runbook.

The harness cannot execute honestly until two exact operational inputs exist:

1. an offline Kaggle dataset manifest covering the harness source, model artifacts, and vLLM
   wheel; and
2. a concrete Kaggle runtime adapter bound by exact code identity.

Neither input exists in the merged repository. Issuing authorization without those identities
would convert a generic approval into unbounded operational authority.

## Decision

Approve implementation of the authorization package, not issuance of final authorization.

The next slice may add typed authorization tooling, a dataset-manifest request, a concrete
runtime adapter, validation tests, and an authorization runbook. It may not create the final
execution authorization artifact.

A later issuance review must bind the exact materialized dataset manifest, runtime-adapter
SHA-256, request fingerprint, operator confirmation, and a maximum four-hour authorization
window.

## Dataset boundary

The future offline dataset manifest must preserve exactly these roles:

- `harness_source`
- `model_artifacts`
- `vllm_wheel`

Every role requires an exact dataset slug, version, mounted path, and SHA-256. Network fallback,
credentials, customer data, and hosted-provider inputs remain prohibited.

The harness source must be materialized after the authorization implementation merges so the
future dataset cannot silently package stale code.

## Runtime adapter boundary

The implementation may create:

```text
auragateway.local_abc.full_abc_local_environment_qualification_kaggle_runtime_adapter:create_runtime_adapter
```

The adapter must remain loopback-only, use frozen startup argv, expose the typed runtime
protocol, prohibit hidden retries, and prohibit raw prompt logging. Implementation does not
load or execute the adapter.

## Authorization issuance boundary

The final authorization remains absent until a separate issuance review confirms:

- request SHA-256;
- dataset manifest SHA-256;
- runtime adapter SHA-256 and `module:function` binding;
- PR #104 authority lineage;
- one Kaggle session;
- eight model requests;
- 32 output tokens per request;
- zero benchmark trajectory requests;
- zero external spend; and
- a timezone-aware authorization window of no more than 240 minutes.

## Consequences

The next slice closes the missing implementation seams without implying that the Kaggle dataset
exists or that execution is authorized. Actual environment activity remains fail closed.

## Non-claims

This decision does not claim dataset materialization, runtime-adapter validity in Kaggle, current
GPU availability, runtime compatibility, cache observability, environment qualification,
comparison eligibility, measured-execution readiness, or production readiness.

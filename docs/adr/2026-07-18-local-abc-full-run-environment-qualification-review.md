# ADR: Define the fresh full-run environment-qualification review boundary

- Status: accepted
- Date: 2026-07-18
- Decision ID: `auragateway-full-abc-local-full-run-environment-qualification-review-v1`
- Source main merge: `1bbc11e72880bc5b6fa88da3ba8b180420c9abf5`
- Review fingerprint: `ac21b3d2f45ccd359d0291edcf450f66899dab7277cfa732177617d36d41a67b`

## Context

PR #100 completed the clean local-only preflight-v3 planning lineage. The repository now has
canonical A/B/C condition fingerprints, a separate developer dependency lock, a non-executable
manifest draft, and a regenerated 342-trajectory ledger. Execution remains disabled.

The historical Kaggle T4 x2 environment previously supported a smaller 72-trajectory measured
run. That evidence is useful as a baseline, but it cannot qualify the current full-run lineage.
The current environment, package set, model identity, worker topology, metric capability, and reset
semantics must be captured again in one fresh runtime session.

## Decision

Approve implementation of the environment-qualification tooling only.

The next slice may add typed contracts, generators, validators, a qualification request, and a
worker startup plan. It may not start Kaggle, enable GPUs, start workers, invoke a model, access
credentials, call a hosted provider, or create qualification evidence that claims runtime success.

## Identity boundary

Repository authorities are bound by exact Git blob SHA. Generated review artifacts use canonical
JSON fingerprints. These identity mechanisms are not interchangeable.

The following merged files are current authorities:

- preflight-v3 implementation plan;
- preflight-v3 manifest;
- preflight-v3 report; and
- local runtime correction.

The historical measured-execution authorization is context only. It cannot be reused as current
full-run qualification or execution authority.

## Fresh runtime requirements

The implementation must require fresh same-session capture of:

- Python, PyTorch, CUDA, Transformers, vLLM module, and vLLM distribution versions;
- exact vLLM wheel SHA-256;
- automatic prefix-cache and attention backend configuration;
- dtype, quantization, maximum model length, output budget, and GPU memory utilization;
- model repository, model revision, and tokenizer revision;
- two Tesla T4 GPUs with compute capability 7.5;
- worker 1 on GPU 0 and port 8001;
- worker 2 on GPU 1 and port 8002; and
- the canonical worker startup command digest.

The preflight-v3 developer dependency lock may not substitute for the Kaggle runtime lock.
Historical package values may not be silently inherited.

## Metric capability

The qualification package must map raw runtime metrics to explicit semantics for prompt tokens,
cached prefix tokens, newly computed prefill tokens, prefill duration, request latency, time to
first token, worker identity, realized route, reset state, and metric availability.

A missing metric is `UNAVAILABLE_NOT_ZERO`. Zero-filling is prohibited. Latency alone cannot prove
cache reuse. The qualification review makes no cache-success claim.

## Reset capability

A clean baseline requires a full worker restart with evidence of process exit, closed ports,
restart from the bound startup plan, identity revalidation, and a fresh health and metric baseline.
Namespace-only reset is not accepted as proof of a clean cache.

## Fail-closed conditions

Qualification must stop on GPU, model, tokenizer, dependency, wheel, port, worker, route, cache
metric, reset, privacy, credential, customer-data, spend, or hosted-fallback divergence.

No automatic retry may hide identity failure.

## Consequences

### Positive

- Prevents stale historical evidence from authorizing the full run.
- Separates developer and Kaggle runtime dependency identities.
- Makes metric absence explicit rather than numerically misleading.
- Preserves zero-spend and local-only constraints.
- Creates a deterministic implementation target before any GPU activity.

### Trade-offs

- Adds one review and implementation boundary before environment execution.
- Requires a fresh runtime capture even when historical versions appear unchanged.
- Treats missing cache metrics as a blocker rather than allowing proxy inference.

## Next gate

`full_abc_local_full_run_environment_qualification_implementation`

That gate may implement the qualification contracts and static request/startup artifacts. It must
keep GPU, worker, notebook, model, credential, provider, and measured execution disabled.

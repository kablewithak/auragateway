# AuraGateway Local A/B/C Measured Execution Authorization v1

## Decision

`AUTHORIZED` for one bounded Kaggle T4 x2 measured run after this package is merged.

This authorization does not execute the benchmark. It freezes the inputs, evidence lineage,
runtime, route constitution, decoding policy, scoring method, abort conditions, and claims that
the next Kaggle notebook is permitted to use.

## Authorization identifiers

- Authorization ID: `auragateway-local-abc-measured-authorization-v1`
- Case manifest ID: `auragateway-local-abc-measured-cases-v1`
- Case manifest SHA-256: `8ca19d6bd48a50abc4bf5a0b932705be37f362e2be3f320d8f22a10090567ade`
- Authorization fingerprint: `64565dd6d34d7d9f9e55a4522b594ef95c458b0ff1af7994dfe81b39a8ba4e74`
- Case count: `8`
- Replications: `3`
- Conditions: `3`
- Planned trajectories: `72`
- Planned requests: `144`

## ADR: version the authorization before the measured notebook

### Decision

Store the typed authorization contracts, canonical case manifest, and canonical authorization
record in the repository before generating or running the measured Kaggle notebook.

### Why

The benchmark must not be allowed to mutate its cases, order, seeds, metrics, abort rules, or
interpretation after results are visible. A versioned, hash-bound authorization package makes
those boundaries inspectable and reviewable before GPU execution.

### Rejected alternative

Embedding cases and authorization rules only inside the Kaggle notebook was rejected. It would
make the notebook both experiment designer and executor, weakening reviewability and making
post-result edits harder to detect.

## Evidence prerequisites

All four predecessor gates are required and hash-bound.

| Gate | Lifecycle state | Report SHA-256 | Archive SHA-256 |
|---|---|---|---|
| Environment | `ENVIRONMENT_QUALIFIED` | `3daa6faf9dcae571c9e6580654d3c5f5b738cb9a0984f458dc849ded29779b68` | `f16aad65c567d8adf35f2ccb18d84e5ad732992daad128ff2c42b520ecc2759d` |
| Cache observability | `CACHE_OBSERVABILITY_QUALIFIED` | `d67b51378761b26ffab9eeec27e824b78e1e046c022d95de92d1225bc2835295` | `e6a10b60ad525751a99248f3c4b6b5d139a9e7c7dbb15eb1a921f8a4664287c9` |
| Cache pressure | `PRESSURE_DIAGNOSTICS_COMPLETED` | `9fc996633a373439c1ccffaa383e00f99f0e051625b673edef87d5b693f2a34a` | `f546fd00be9cfcec6f9f976b0d8276b5e5d2a1b03c74947a997fad05b0b18c91` |
| Route and worker faults | `ROUTE_WORKER_FAULT_DIAGNOSTICS_COMPLETED` | `f9ea689f04ebeda78a44fd066307e12c36c9689baf3ad352e0f38da8bf7739a6` | `bfd18a3c0a0bbe293e800f72fade0baa29395ec58bc2089e134466ef445ba002` |

Any failed, missing, or altered predecessor gate invalidates authorization.

## Runtime binding

The measured notebook is authorized only for:

- Kaggle user: `kabomolefe`
- GPU topology: two Tesla T4 GPUs
- `worker_1`: GPU 0, port 8001
- `worker_2`: GPU 1, port 8002
- vLLM: `0.25.1`
- CUDA runtime: `12.9`
- Model: `Qwen/Qwen2.5-0.5B-Instruct`
- Model revision: `7ae557604adf67be50417f59c2c2f167def9a775`
- Model manifest SHA-256: `b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa`
- External spend: `0`
- Customer data: prohibited
- Raw prompt logging: prohibited

A runtime, model, topology, privacy, or spend mismatch must stop the run.

## Frozen conditions

The existing Local A/B/C causal constitution remains unchanged:

| Condition | Prefix policy | Turn 1 worker | Turn 2 worker | Purpose |
|---|---|---:|---:|---|
| A | Cache-hostile mutation | `worker_1` | `worker_2` | Negative control for unstable prefixes without affinity |
| B | Exact deterministic prefix | `worker_1` | `worker_2` | Stable-prefix control without worker affinity |
| C | Exact deterministic prefix | `worker_1` | `worker_1` | Cache-preserving worker affinity intervention |

The primary causal contrast is `C - B` on turn-two cache and latency metrics. The `B - A`
contrast is a negative control: both change workers, so neither may be credited with inherited
worker-local cache state.

## Case set

The case manifest freezes eight two-turn synthetic tasks:

1. Incident severity classification
2. Payment reconciliation
3. Data-sharing policy
4. Retry decision
5. Support priority
6. Schema-change governance
7. Cache-affinity route selection
8. Data-retention action

Each turn has an exact expected JSON answer. Cases are intentionally simple because the primary
experiment concerns harness, prefix, telemetry, and route behavior rather than broad language
model capability.

## Condition order and isolation

The three replications use this Latin square:

1. `A, B, C`
2. `B, C, A`
3. `C, A, B`

A full worker-process restart is required before every trajectory. Each trajectory contains two
turns. The measured notebook may not carry cache, process, route, or telemetry state across
trajectories.

## Decoding policy

- Temperature: `0`
- Top-p: `1`
- Seed: `7`
- Maximum output tokens: `64`
- Number of completions: `1`
- Streaming: disabled

Changing any decoding field invalidates pairing and authorization.

## Deterministic quality rubric

No LLM judge is permitted. Each output is scored using exact checks:

- JSON parse success
- Exact key set: `answer`, `case_id`, `confidence`, `turn_index`
- Exact expected answer
- Exact case ID
- Exact turn index
- Confidence equals `high`
- No prose, Markdown, or text outside the JSON object

Quality results gate interpretation. Cache or latency improvement cannot be promoted if output
quality materially diverges between conditions.

## Primary metrics

Turn-two metrics are paired by `case_id + replication_id`:

- Cached prefix tokens
- Newly computed prefill tokens
- Prefill duration
- Time to first token
- End-to-end latency

The report must include paired medians and pairwise win rates. At least 21 eligible pairs are
required per contrast. Failed, interrupted, fallback, route-mismatched, or telemetry-invalid
trajectories remain in the attempt ledger but are excluded from causal comparisons.

## Abort policy

The notebook must stop immediately when any strict invariant fails:

- Model identity mismatch
- Tokenizer identity mismatch
- Route-realization mismatch
- Invalid or missing required telemetry
- Privacy scan failure
- Non-zero external spend
- Worker port remains open after cleanup

It must also stop after:

- Three total trajectory failures, or
- Two consecutive trajectory failures

There are no hidden retries and no replacement trajectories.

## Required report

The measured notebook must emit:

- Frozen manifest and authorization fingerprints
- Monotonic attempt ledger
- Condition, case, replication, seed, intended route, and realized route
- Worker-scoped telemetry for both turns
- Exact quality scores
- Eligibility and exclusion reasons
- Paired A/B/C comparison report
- Regression notes
- Failure taxonomy counts
- Cleanup and privacy evidence
- Canonical report SHA-256 and downloadable evidence ZIP

## Permitted claims

After a valid run, claims must remain bounded to the pinned Kaggle environment and the frozen
case set. The report may describe observed differences in cache reuse, recomputation, and latency
only when the required pairs and quality checks pass.

## Non-claims

This package does not authorize claims about:

- Production readiness
- Hosted provider behavior
- Universal cache TTL or eviction thresholds
- Customer traffic
- Concurrency, load, or availability
- General model quality
- Dollar savings outside the bounded local experiment

## Commercial translation

This artifact is buyer-facing proof for an AI Reliability Pilot or Agent Harness Hardening Sprint.
It demonstrates that measured execution is governed by predeclared cases, explicit causal
contrasts, deterministic scoring, strict abort conditions, privacy controls, and evidence lineage
rather than by an improvised benchmark notebook.

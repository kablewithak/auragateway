# AuraGateway Benchmark Constitution

| Field | Value |
|---|---|
| **Constitution version** | 1.0.0 |
| **Status** | Frozen |
| **Freeze date** | 2026-07-12 |
| **PRD baseline** | AuraGateway v2 PRD 2.1.0 |
| **Completed proof gate** | Gate 0 — Benchmark Constitution |
| **Measured execution permitted** | No — execution manifest and downstream proof gates are not frozen |
| **Customer data permitted** | No |

## 1. Purpose

This constitution defines the rules under which AuraGateway benchmark evidence may be generated, compared, interpreted, and reported.

It prevents:

- post-result rule changes;
- configuration drift;
- hidden exclusions;
- run-order bias;
- cache namespace contamination;
- quality-blind cost optimisation;
- unsupported provider-cache claims;
- causal overstatement.

This constitution is frozen before benchmark implementation and measured execution.

## 2. Two-layer freeze model

AuraGateway separates experiment rules from execution assets.

### Layer 1 — Benchmark Constitution

Frozen at Gate 0.

It controls:

- benchmark question;
- conditions and causal contrasts;
- run order;
- retry, exclusion, rerun, and denominator policy;
- cold and warm classification;
- review blindness;
- quality non-inferiority;
- statistical reporting;
- evidence and privacy rules;
- invalidation triggers.

### Layer 2 — Execution Manifest

Frozen only after the required downstream assets exist and Gates 1–8 pass.

It pins:

- corpus and retrieval hashes;
- prompt, context-pack, tool, and schema versions;
- provider, model, adapter, TTL, and pricing;
- route policy;
- evaluation manifests and rubric;
- negative controls and fault fixtures;
- implementation, dependency, and Git versions.

Freezing this constitution does not authorize measured execution.

## 3. Benchmark question

> Under a fixed multi-turn retrieval-grounded technical-support workload, do deterministic context construction and cache-affinity routing reduce avoidable uncached input work, prefill or time-to-first-output latency, or versioned estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, citation support, or useful feedback retention?

## 4. Workload boundary

The workload is a synthetic multi-turn API troubleshooting and technical-support assistant for the fictional Nimbus Relay API.

The benchmark requires:

- retrieval over a version-controlled synthetic corpus;
- four-turn episodes;
- structured terminal decisions;
- citations;
- clarification and escalation behaviour;
- provider/model route state;
- feedback retention across turns.

No public, customer, or production data is permitted.

## 5. Conditions

### Condition A — Cache-Hostile Baseline

- no enforced static/volatile context boundary;
- no canonical static-anchor serialization gate;
- route choice is turn-local;
- no warm-session route preservation;
- retrieval and output schemas remain fixed.

Condition A must remain functional and plausible. It must not be artificially sabotaged.

### Condition B — Prefix-Deterministic Runtime

- versioned static anchor;
- deterministic instruction, tool, schema, and example ordering;
- typed volatile append;
- retrieval evidence appears only in volatile context;
- HMAC static-prefix fingerprint;
- prefix mutation and volatile-leak checks;
- same route behaviour as A for the A-versus-B comparison.

### Condition C — Cache-Aware Agent Runtime

- all Condition B controls;
- typed session route state;
- route preservation while plausibly warm and eligible;
- TTL-based route reconsideration;
- explicit route-change reasons;
- provider-failure, capability, safety, and quality reroute controls;
- route-thrash detection.

## 6. Causal contrasts

### A versus B

Question:

> What changes when context construction becomes deterministic while route behaviour remains fixed?

Permitted interpretation:

- context-construction policy effect under the named benchmark.

Prohibited interpretation:

- cache-affinity routing effect.

### B versus C

Question:

> What changes when cache-affinity routing is added to deterministic context construction?

Permitted interpretation:

- route-policy effect under the named benchmark.

Prohibited interpretation:

- context-construction effect.

### A versus C

Question:

> What is the total difference between the realistic weak baseline and the complete runtime policy?

Permitted interpretation:

- total system effect under the named benchmark.

Prohibited interpretation:

- attribution to one mechanism.

## 7. Controlled constants

The execution manifest must pin the following before measured execution:

- corpus manifest;
- chunking strategy;
- retrieval implementation;
- retrieval configuration;
- top-k;
- metadata filters;
- prompt template ID and version;
- static context-pack ID and version;
- tool-contract version;
- output-schema version;
- development and held-out evaluation manifests;
- functional and runtime episode manifests;
- quality rubric and thresholds;
- blinded-adjudication protocol;
- maximum turns;
- input and output budgets;
- provider/model capability tier;
- provider/model aliases;
- provider adapter version;
- runtime condition implementation versions;
- route-policy version;
- benchmark runner version;
- run-order schedule IDs;
- cold/warm classification policy;
- retry, exclusion, rerun, and denominator policy IDs;
- statistical reporting configuration;
- comparison-eligibility contract;
- pricing schedule when cost is reported.

## 8. Run identity

Every measured trajectory includes:

- `run_id`;
- `trace_id`;
- `comparison_pair_id`;
- `episode_id`;
- `replication_id`;
- `condition_id`;
- `cache_namespace_id`;
- `session_id_hash`;
- `provider_model_alias`;
- `benchmark_manifest_hash`;
- `execution_manifest_hash`;
- `configuration_fingerprint`.

Identifiers must not expose direct personal information.

## 9. Counterbalancing

### Functional benchmark schedule

The three repetitions use:

```text
Replication 1: A → B → C
Replication 2: B → C → A
Replication 3: C → A → B
```

Schedule ID:

```text
functional-counterbalance-v1
```

### Runtime microbenchmark schedule

The ten repetitions use:

```text
Replication 01: A → B → C
Replication 02: B → C → A
Replication 03: C → A → B
Replication 04: A → C → B
Replication 05: C → B → A
Replication 06: B → A → C
Replication 07: A → B → C
Replication 08: B → C → A
Replication 09: C → A → B
Replication 10: C → B → A
```

Schedule ID:

```text
runtime-counterbalance-v1
```

No operator may reorder conditions after observing partial results.

## 10. Cache isolation

Each condition, comparison pair, and replication uses a distinct cache namespace.

Cross-condition namespace reuse is a benchmark isolation failure and invalidates affected comparisons.

## 11. Cold and warm classification

### Cold turn

A turn is cold when no prior eligible request exists in the same session, provider/model route, namespace, and declared TTL window.

The first turn of every trajectory is cold.

### Warm-eligible turn

A turn is warm-eligible when:

- a prior eligible request used the same provider/model route;
- the static prefix fingerprint matches;
- the cache namespace matches;
- the request occurs inside the execution manifest's TTL assumption;
- no provider failure, session reset, or benchmark transition invalidated affinity.

Warm eligibility is not proof of a provider cache hit.

### Ambiguous state

When cache state cannot be classified defensibly, evidence is marked unavailable or ambiguous.

Cold and warm results are reported separately.

## 12. Provider and telemetry evidence

Evidence levels are:

- observed provider evidence;
- inferred local evidence;
- unavailable.

Provider cache fields retain provider-specific meaning.

Unknown values remain `None`. They are never converted to zero.

Local prompt-evaluation timing must not populate provider cache-token fields.

Cache, latency, and cost claims require an explicit telemetry-sufficiency decision.

## 13. Timeout and retry policy

Policy ID:

```text
provider-request-policy-v1
```

Exact controls:

```text
Connection timeout: 10 seconds
First-output timeout: 45 seconds
Total request timeout: 120 seconds
Maximum retries after the initial attempt: 1
Retry backoff: fixed 2 seconds
Retry jitter during measured execution: disabled
```

A retry is permitted only when:

- the error is typed as retryable;
- the response state is `no_response` or `definite_failure`;
- the maximum retry count has not been reached;
- the action cannot create an ambiguous duplicate.

Blind retry after an ambiguous response is prohibited.

## 14. Exclusion policy

Policy ID:

```text
exclusion-policy-v1
```

A run may be excluded from a specific metric family only under a predeclared rule.

Allowed exclusion classes:

- confirmed benchmark isolation failure;
- confirmed configuration fingerprint mismatch;
- provider response that cannot be mapped into the frozen telemetry contract;
- benchmark harness defect affecting the run;
- operator interruption recorded before result inspection.

Excluded runs remain in the evidence bundle and failure-accounted reporting.

Poor quality, high latency, high cost, or an unfavourable result are not exclusion reasons.

## 15. Rerun policy

Policy ID:

```text
rerun-policy-v1
```

A rerun may occur only when:

- a retryable provider failure exhausted the per-request retry policy;
- a benchmark harness defect invalidated the original run;
- a configuration mismatch requires a complete affected comparison rerun;
- a predeclared minimum successful-run count was not reached.

Every rerun records:

- original run ID;
- replacement run ID;
- reason code;
- trigger;
- whether the original remains in the denominator.

The original record is never deleted.

## 16. Denominator policy

Policy ID:

```text
denominator-policy-v1
```

Every report includes:

- total scheduled runs;
- completed runs;
- validation failures;
- provider errors;
- budget exhaustion;
- exclusions;
- configuration invalidations;
- safety aborts.

### Primary task-quality denominator

All comparison-eligible scheduled trajectories are included.

The following count as non-success:

- validation failure;
- provider error;
- budget exhaustion;
- safety abort;
- failure to reach the required terminal decision.

Runs excluded under `exclusion-policy-v1` remain visible but are removed from the eligible quality denominator only for the affected metric family.

### Runtime denominator

Runtime metrics are reported in two views:

1. completed-run measurements;
2. failure-accounted completion and failure rates over all scheduled runs.

## 17. Functional benchmark

Planned design:

- 18 multi-turn episodes;
- 4 turns per episode;
- 3 conditions;
- 3 repetitions per condition;
- 162 measured trajectories.

Purpose:

- task success;
- structured-output validity;
- citation validity and support;
- clarification, escalation, and refusal correctness;
- route-policy correctness;
- feedback retention and task sufficiency.

## 18. Runtime microbenchmark

Planned design:

- 6 selected episodes;
- 4 turns per episode;
- 3 conditions;
- 10 repetitions per condition;
- 180 measured trajectories.

Purpose:

- cache evidence;
- uncached input work;
- prefill or prompt-evaluation timing;
- time to first output;
- versioned estimated trajectory cost;
- route preservation and switching.

The runtime subset may not replace the full functional quality benchmark.

## 19. Quality gate

Policy ID:

```text
quality-non-inferiority-v1
```

A runtime improvement is accepted only when:

- task-success regression is no greater than 5 percentage points;
- citation support does not regress;
- structured-output validity remains at or above 95 percent;
- unsupported-answer rate does not increase;
- retrieval configuration remains unchanged;
- no new unsafe route, retry, escalation, or refusal pattern appears;
- compared runs pass execution-manifest and configuration-fingerprint eligibility.

A cheaper or faster run that fails this gate is a quality regression, not an improvement.

## 20. Blinded adjudication

Protocol ID:

```text
blinded-adjudication-v1
```

Controls:

- deterministic checks run on 100 percent of outputs;
- one primary rubric review is completed for 100 percent of rubric-eligible outputs;
- 25 percent are independently double-reviewed;
- the double-review sample is stratified by condition and terminal decision;
- the sample is selected with seed `20260712`;
- reviewers cannot see condition, route policy, cost, latency, or cache telemetry;
- disagreement reasons are retained;
- material disagreements are resolved by an adjudicator who did not provide both initial ratings.

Reviewer identities may be assigned later, but this protocol may not change during measured execution.

## 21. Feedback evidence

The benchmark evaluates feedback at trace level:

- validity;
- novelty;
- retention;
- later action change;
- task sufficiency.

It does not calculate or claim a universal EFC score.

## 22. Statistical reporting

Configuration ID:

```text
paired-bootstrap-v1
```

Runtime and paired comparison reports include:

- run count;
- successful-run count;
- failure count;
- median;
- p25 and p75;
- minimum and maximum;
- p90 where useful;
- paired per-episode differences;
- cold and warm views;
- completed-run and failure-accounted views.

Uncertainty interval:

```text
Method: percentile bootstrap
Resampling unit: comparison pair at episode level
Bootstrap samples: 10,000
Confidence level: 95 percent
Random seed: 20260712
```

The project does not claim universal generalisation, causal validity outside the benchmark, or academic statistical significance.

## 23. Pricing

Cost may be reported only against a frozen, versioned local pricing schedule containing:

- provider/model alias;
- source date;
- currency;
- input price;
- output price;
- cache read/write prices where available;
- estimated versus provider-reported status.

Cost estimates are not invoices.

## 24. Privacy and vendor boundary

AuraGateway uses synthetic data only during the 200-hour project.

Normal logs, sanitized traces, comparison artifacts, and public evidence bundles exclude:

- raw prompts;
- raw user messages;
- raw conversation history;
- raw retrieved document text;
- raw model outputs;
- hidden reasoning;
- raw provider payloads;
- credentials;
- secrets;
- direct personal identifiers;
- unbounded metadata.

Provider adapters are the only components allowed to inspect raw provider SDK objects or payloads.

Protected blinded-review exports:

- remain local under an ignored path;
- use opaque review IDs;
- remain separate from public traces and evidence bundles;
- follow an explicit retention and deletion rule.

Any forbidden trace content is a `PRIVACY_VIOLATION` and blocks affected evidence publication.

## 25. Evidence bundle and immutability

Every completed benchmark execution produces a typed evidence bundle.

Finalized bundles are append-only.

Corrections produce a new bundle that identifies:

- the superseded bundle;
- correction reason;
- affected artifacts;
- affected claims;
- rerun scope.

Raw prompts, provider payloads, protected review exports, credentials, and secrets are forbidden in public evidence bundles.

## 26. Comparison eligibility

The comparison gate returns:

- eligible or ineligible;
- partially eligible metric families where explicitly supported;
- compared run IDs;
- mismatched fields;
- invalidated metrics;
- invalidated claims;
- required reruns.

Human-authored report text may not override an ineligible decision.

Runs with different execution-manifest hashes are ineligible by default.

## 27. Decision precedence

Comparative reporting follows this order:

1. bundle schema and hash verification;
2. run-accountability verification;
3. execution-manifest and configuration-fingerprint eligibility;
4. telemetry-sufficiency decision;
5. quality non-inferiority decision;
6. metric calculation;
7. claim generation.

A failure at an earlier gate blocks dependent claim families.

## 28. Invalidation triggers

Affected measured comparisons require rerun when:

- this constitution changes;
- an execution-manifest controlled field changes;
- held-out or diagnostic cases change after their manifest freeze;
- prompt or static-anchor content changes;
- retrieval configuration changes;
- provider/model alias or capability tier changes;
- adapter changes alter telemetry meaning;
- quality rubric, scorer, instructions, or thresholds change;
- route-policy rules change;
- negative-control or fault definitions change after freeze;
- run order, cold-start, retry, exclusion, rerun, or denominator rules change;
- statistical rules change;
- pricing changes while cost comparison remains in scope;
- a configuration fingerprint mismatch is discovered.

## 29. Claim language

Permitted language remains conditional:

> Under the named workload, provider/model, frozen execution manifest, and Benchmark Constitution 1.0.0, the tested runtime policy produced the reported outcomes.

The benchmark must not claim:

- guaranteed cache hits;
- direct GPU KV-cache visibility;
- guaranteed cache residency, TTL, eviction, or scheduling;
- universal savings;
- broad provider rankings;
- production readiness;
- customer-data readiness;
- Coinbase-scale infrastructure or results.

## 30. Change control

This constitution is frozen.

A substantive rule change requires:

1. a new constitution version;
2. a documented reason;
3. a new Gate 0 review;
4. invalidation of affected measured comparisons;
5. updated execution-manifest compatibility rules.

Downstream asset values are added to the execution manifest and do not reopen the constitution when they conform to these frozen rules.

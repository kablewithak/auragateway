# AuraGateway Benchmark Constitution

| Field | Value |
|---|---|
| **Constitution version** | 0.2.0 |
| **Status** | Draft — under review, not frozen |
| **PRD baseline** | AuraGateway v2 PRD 2.1.0 |
| **Active phase** | Phase 0 — Design Freeze and Benchmark Constitution |
| **Active proof gate** | Gate 0 — Benchmark Constitution |
| **Measured execution permitted** | No |
| **Customer data permitted** | No |

## 1. Purpose

This constitution defines the rules under which AuraGateway benchmark evidence may be generated, compared, interpreted, and reported.

It exists to prevent:

- post-result rule changes;
- configuration drift;
- hidden exclusions;
- run-order bias;
- cache namespace contamination;
- quality-blind cost optimisation;
- unsupported provider-cache claims;
- causal overstatement.

This document must be frozen before measured provider execution begins.

## 2. Benchmark question

> Under a fixed multi-turn retrieval-grounded technical-support workload, do deterministic context construction and cache-affinity routing reduce avoidable uncached input work, prefill or time-to-first-output latency, or versioned estimated trajectory cost without reducing retrieval quality, grounded task success, structured-output validity, citation support, or useful feedback retention?

## 3. Workload boundary

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

## 4. Conditions

### Condition A — Cache-Hostile Baseline

- no enforced static/volatile context boundary;
- no canonical static-anchor serialization gate;
- route choice is turn-local;
- no warm-session route preservation;
- retrieval and output schemas remain fixed.

### Condition B — Prefix-Deterministic Runtime

- versioned static anchor;
- deterministic instruction, tool, schema, and example ordering;
- typed volatile append;
- retrieval evidence appears only in volatile context;
- HMAC static-prefix fingerprint;
- prefix mutation and volatile-leak checks;
- same route behaviour as A for A-versus-B comparison.

### Condition C — Cache-Aware Agent Runtime

- all Condition B controls;
- typed session route state;
- route preservation while plausibly warm and eligible;
- TTL-based route reconsideration;
- explicit route-change reasons;
- provider-failure, capability, safety, and quality reroute controls;
- route-thrash detection.

## 5. Causal contrasts

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

## 6. Controlled constants

The following remain fixed across affected comparisons:

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
- run-order policy;
- cold/warm classification;
- retry, exclusion, and rerun rules;
- statistical reporting configuration;
- comparison-eligibility rules;
- pricing schedule when cost is reported.

## 7. Run identity

Every measured trajectory must include:

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
- `configuration_fingerprint`.

Identifiers must not expose direct personal information.

## 8. Counterbalancing

The initial planned three-replication condition order is:

- replication 1: A, B, C;
- replication 2: B, C, A;
- replication 3: C, A, B.

Runtime microbenchmark repetitions will use a deterministic balanced extension of these permutations.

The exact schedule and seed must be stored in the frozen benchmark manifest.

No operator may reorder conditions after observing partial results.

## 9. Cache isolation

Each condition, comparison pair, and replication must use distinct cache namespaces.

Cross-condition namespace reuse is a benchmark isolation failure and invalidates affected comparisons.

## 10. Cold and warm classification

### Cold turn

A turn is cold when no prior eligible request exists in the same session, provider/model route, namespace, and declared TTL window.

The first turn of every trajectory is classified cold.

### Warm-eligible turn

A turn is warm-eligible when:

- a prior eligible request used the same provider/model route;
- the static prefix fingerprint matches;
- the cache namespace matches;
- the request occurs inside the declared TTL assumption;
- no provider failure, session reset, or benchmark transition invalidated affinity.

Warm eligibility is not proof of a provider cache hit.

### Ambiguous state

When cache state cannot be classified defensibly, the evidence is marked unavailable or ambiguous and excluded only under a predeclared rule.

Cold and warm results are reported separately.

## 11. Provider and telemetry evidence

Evidence levels are:

- observed provider evidence;
- inferred local evidence;
- unavailable.

Provider cache fields retain provider-specific meaning.

Unknown values remain `None`. They are never converted to zero.

Local prompt-evaluation timing must not populate provider cache-token fields.

Cache, latency, and cost claims require an explicit telemetry-sufficiency decision.

## 12. Retry policy

Retries are bounded and provider-error aware.

A retry is permitted only when:

- the error is typed as retryable;
- the response state is `no_response` or `definite_failure`;
- the maximum retry count has not been reached;
- the action will not create an ambiguous duplicate.

Blind retry after an ambiguous response is prohibited.

The frozen version must declare exact timeout, retry count, and backoff values before live execution.

## 13. Exclusion policy

A run may be excluded from a specific analysis only under a predeclared rule.

Planned eligible reasons include:

- confirmed benchmark isolation failure;
- confirmed configuration fingerprint mismatch;
- provider response that cannot be parsed into the declared telemetry contract;
- benchmark harness defect affecting the run;
- operator interruption recorded before result inspection.

Excluded runs remain in the evidence bundle and in failure-accounted reporting.

Poor model quality, high latency, high cost, or an unfavourable result are not exclusion reasons.

## 14. Rerun policy

A rerun may occur only when:

- a retryable provider failure exhausted the per-request retry policy;
- a benchmark harness defect invalidated the original run;
- a configuration mismatch requires a full affected comparison rerun;
- a predeclared minimum successful-run count was not reached.

Every rerun records:

- original run ID;
- reason code;
- operator or automated trigger;
- whether the original remains in denominators;
- replacement run ID.

## 15. Denominator policy

Reports include:

- total scheduled runs;
- completed runs;
- validation failures;
- provider errors;
- budget exhaustion;
- exclusions;
- configuration invalidations;
- safety aborts.

Quality rates use the full predeclared eligible denominator unless the frozen metric definition states otherwise.

Runtime reports provide both:

- successful-run measurements;
- failure-accounted views.

## 16. Functional benchmark

Planned design:

- 18 multi-turn episodes;
- 4 turns per episode;
- 3 conditions;
- 3 repetitions per condition.

Purpose:

- task success;
- structured-output validity;
- citation validity and support;
- clarification, escalation, and refusal correctness;
- route-policy correctness;
- feedback retention and task sufficiency.

## 17. Runtime microbenchmark

Planned design:

- 6 selected episodes;
- 4 turns per episode;
- 3 conditions;
- 10 repetitions per condition.

Purpose:

- cache evidence;
- uncached input work;
- prefill or prompt-evaluation timing;
- time to first output;
- versioned estimated trajectory cost;
- route preservation and switching.

The runtime subset may not replace the full functional quality benchmark.

## 18. Quality gate

A runtime improvement is accepted only when:

- task-success regression is no greater than 5 percentage points;
- citation support does not regress;
- structured-output validity remains at or above 95 percent;
- unsupported-answer rate does not increase;
- retrieval configuration remains unchanged;
- no new unsafe route, retry, escalation, or refusal pattern appears;
- compared runs pass configuration-fingerprint eligibility.

A cheaper or faster run that fails this gate is classified as a quality regression, not an improvement.

## 19. Blinded adjudication

Rubric-reviewed outputs use opaque review IDs.

Reviewers may inspect:

- the task;
- permitted evidence;
- output;
- deterministic validation results needed by the rubric.

Reviewers may not inspect:

- condition identity;
- route-policy identity;
- cost;
- latency;
- cache telemetry.

At least 25 percent of rubric-reviewed outputs are double-reviewed.

Material disagreements require adjudication and retained reasons.

## 20. Feedback evidence

The benchmark evaluates feedback at trace level:

- validity;
- novelty;
- retention;
- later action change;
- task sufficiency.

It does not calculate or claim a universal EFC score.

## 21. Statistical reporting

The frozen configuration must specify exact bootstrap settings.

The intended report includes:

- run count;
- successful-run count;
- failure count;
- median;
- p25 and p75;
- minimum and maximum;
- p90 where useful;
- paired per-episode differences;
- bootstrap confidence intervals;
- cold and warm views;
- success-only and failure-accounted views.

The project does not claim universal generalisation or academic statistical significance.

## 22. Pricing

Cost may be reported only against a versioned local pricing schedule containing:

- provider/model alias;
- source date;
- currency;
- input price;
- output price;
- cache read/write prices where available;
- whether values are provider-reported or estimated.

Cost estimates are not invoices.

## 23. Comparison eligibility

The comparison gate returns:

- eligible or ineligible;
- compared run IDs;
- mismatched fields;
- invalidated claims;
- required reruns.

Human prose may not override an ineligible decision.

## 24. Invalidation triggers

Affected comparisons require rerun when:

- any controlled constant changes;
- held-out or diagnostic cases change after freeze;
- the constitution changes after execution begins;
- prompt or static-anchor content changes;
- retrieval configuration changes;
- provider/model alias or capability tier changes;
- adapter changes alter telemetry meaning;
- quality rubric, scorer, instructions, or thresholds change;
- route-policy rules change;
- negative-control or fault definitions change after closure;
- run order, cold-start, retry, exclusion, or rerun rules change;
- statistical rules change after results are inspected;
- pricing changes while cost comparison remains in scope;
- configuration fingerprint mismatch is discovered.

## 25. Claim language

Permitted language must remain conditional:

> Under the named workload, provider/model, frozen configuration, and benchmark constitution, the tested runtime policy produced the reported outcomes.

The benchmark must not claim:

- guaranteed cache hits;
- direct GPU KV-cache visibility;
- guaranteed cache residency, TTL, eviction, or scheduling;
- universal savings;
- broad provider rankings;
- production readiness;
- customer-data readiness;
- Coinbase-scale infrastructure or results.

## 26. Privacy and vendor boundary

AuraGateway uses synthetic data only during the 200-hour project.

Normal logs, sanitized traces, comparison artifacts, and public evidence bundles must exclude:

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

The governing controls are defined in:

- ADR-0009;
- `docs/privacy/AuraGateway_Privacy_and_Vendor_Boundary.md`.

## 27. Evidence bundle and immutability

Every completed benchmark execution produces a typed evidence bundle.

Finalized bundles are append-only.

Corrections produce a new bundle that identifies:

- the superseded bundle;
- correction reason;
- affected artifacts;
- affected claims;
- rerun scope.

Required bundle evidence includes:

- benchmark and environment manifests;
- configuration fingerprint;
- run results;
- failures;
- exclusions;
- reruns;
- comparison eligibility;
- comparison table;
- benchmark report;
- sanitized trace samples;
- artifact hash manifest;
- bundle manifest.

Raw prompts, provider payloads, protected review exports, credentials, and secrets are forbidden in public evidence bundles.

The governing controls are defined in:

- ADR-0010;
- `docs/benchmark/AuraGateway_Evidence_Bundle_Specification.md`.

## 28. Comparison decision precedence

Comparative reporting follows this order:

1. bundle schema and hash verification;
2. run-accountability verification;
3. configuration-fingerprint eligibility;
4. telemetry-sufficiency decision;
5. quality non-inferiority decision;
6. metric calculation;
7. claim generation.

A failure at an earlier gate blocks dependent downstream claim families.

Human prose may not override a machine-readable blocked decision.

## 29. Freeze procedure

This constitution may be frozen only after:

- all Gate 0 requirements are reviewed;
- unresolved placeholders are eliminated;
- exact retry, timeout, counterbalancing, bootstrap, and denominator rules are specified;
- constitution version is promoted;
- SHA-256 hash is recorded in the benchmark manifest;
- the repository commit is recorded;
- measured execution has not begun.

Until then:

- status remains `Draft — under review`;
- measured benchmark execution is prohibited;
- changes do not require benchmark reruns because no measured benchmark exists.

## 30. Open items before freeze

- exact primary provider and model alias;
- exact provider adapter version;
- exact TTL assumption and evidence source;
- exact timeout and retry count;
- exact backoff schedule;
- exact runtime permutation schedule for ten repetitions;
- exact bootstrap method, sample count, and confidence level;
- exact quality rubric version;
- exact functional and runtime episode manifests;
- exact pricing schedule version;
- exact comparison fingerprint schema version.

These are intentional unresolved design inputs, not permission to begin measured execution.

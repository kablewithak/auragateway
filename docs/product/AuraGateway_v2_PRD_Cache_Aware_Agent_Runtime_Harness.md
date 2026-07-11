# AuraGateway v2
## Product Requirements Document
### Cache-Aware Agent Runtime and Evaluation Harness

| Field | Value |
|---|---|
| **Document version** | 2.1.0 |
| **Status** | Expanded 200-hour design baseline for implementation |
| **Project type** | Standalone advanced AI reliability systems lab |
| **Execution allocation** | 200 hours |
| **Primary relationship to roadmap** | Week 3 companion project only; not part of the roadmap, not a core capstone, and not a dependency for consultancy progress |
| **Primary technical focus** | Retrieval-aware context construction, prompt/KV-cache evidence, cache-affinity routing, telemetry normalization, hard diagnostic evaluation, and EFC-style trajectory evidence |
| **Architecture posture** | Local-first, provider-neutral, typed, eval-driven, privacy-safe, production-shaped but not production-ready |
| **Primary output** | A reproducible, paired A/B/C benchmark report showing whether deterministic context and cache-affinity routing reduce avoidable prefill work, latency, or estimated cost without reducing task quality |
| **Author role** | AI Reliability Lead |

---

# 1. Executive Summary

AuraGateway v2 is a **cache-aware agent runtime and evaluation harness**.

It is not a generic AI gateway, a model-router platform, a billing product, a production proxy, or a dashboard. It is a controlled systems experiment designed to determine whether runtime context and routing policy materially affect prefill work, latency, estimated cost, task quality, and trace behaviour.

The project evaluates one fixed, multi-turn, retrieval-grounded technical-support workflow under three runtime conditions:

1. **Condition A — Cache-Hostile Baseline**  
   Stable and dynamic context are assembled without deterministic static/volatile separation. Routing is turn-local and does not preserve session cache value.

2. **Condition B — Prefix-Deterministic Runtime**  
   Stable instructions, output schema, tool contracts, reusable examples, and approved context packs are serialized deterministically. User state, retrieval evidence, changing conversation state, and runtime metadata are isolated in a typed volatile append.

3. **Condition C — Cache-Aware Agent Runtime**  
   Condition B plus a bounded cache-affinity session policy that preserves an eligible provider/model route while cache reuse remains plausible and re-evaluates the route only for explicit, typed reasons.

The project holds the workload, corpus, retrieval configuration, output schema, task budget, quality rubric, benchmark cases, provider/model capability tier, and pricing schedule constant during comparison. It changes only the intended intervention for each causal contrast:

```text
A versus B: context-construction policy changes; route policy remains fixed.
B versus C: cache-affinity route policy changes; deterministic context remains fixed.
A versus C: total system effect; not a single-mechanism causal claim.
```

The 200-hour version adds the controls needed to make the evidence difficult to dismiss:

- a frozen benchmark constitution;
- paired and counterbalanced execution;
- hard diagnostic cases;
- blinded task-quality adjudication;
- separate functional and runtime benchmarks;
- negative controls and fault injection;
- machine-enforced comparison eligibility;
- telemetry sufficiency gates;
- one-command reproduction;
- immutable evidence bundles with configuration fingerprints and hashes.

AuraGateway succeeds when it produces a reproducible and inspectable conclusion. A positive saving is desirable, but not required. A negative or mixed result is valid when the benchmark remains controlled, all failed runs are accounted for, quality is measured honestly, and the report explains why the expected improvement did or did not appear.

---

# 2. North Star

## 2.1 North Star Statement

> **AuraGateway proves, through a reproducible and controlled multi-turn retrieval-agent benchmark, whether deterministic context construction and cache-affinity routing reduce avoidable prefill work, latency, and estimated cost while preserving retrieval quality, grounded task success, structured-output validity, and useful feedback retention under fixed provider, model, and evaluation conditions.**

## 2.2 Plain-English North Star

> **AuraGateway tests whether an AI assistant can reuse the parts of its context that have not changed and avoid unnecessarily switching models during a conversation, so it spends less time and money repeating work without becoming less accurate, less reliable, or worse at completing the task.**

## 2.3 North Star Outcome Target

Condition C versus Condition A should produce at least one of the following:

```text
≥ 30% reduction in observed avoidable uncached input work
OR
≥ 15% reduction in paired median prefill / time-to-first-output latency
OR
≥ 15% reduction in versioned estimated trajectory cost
```

The improvement is accepted only when all quality guardrails pass:

```text
- task-success regression is no greater than 5 percentage points;
- citation support does not regress;
- structured-output validity remains at or above 95%;
- unsupported-answer rate does not increase;
- retrieval configuration remains unchanged;
- no new route-thrash, redundant-feedback, unsafe-retry, or unsafe-escalation pattern appears;
- all compared runs share an eligible configuration fingerprint.
```

These are project targets, not promised outcomes.

## 2.4 North Star Anti-Claims

AuraGateway must not claim:

- guaranteed provider cache hits;
- direct GPU KV-cache visibility;
- guaranteed provider cache residency, TTL, eviction, or scheduling behaviour;
- universal cost or latency savings;
- broad provider rankings;
- universal EFC measurement;
- production readiness;
- customer-data readiness;
- Coinbase-scale infrastructure or Coinbase-scale results.

---

# 3. Inspiration and Intellectual Lineage

AuraGateway combines four technical inspiration streams and one internal engineering doctrine.

| Source | AuraGateway extraction |
|---|---|
| **Coinbase engineering post by Mark Landgrebe, Senior Staff Software Engineer** | A single gateway control layer, cheaper defaults, exact-prefix caching, long stable prefixes, cache-aware routing, preserving a model while its cache is warm, TTL-based route reconsideration, redaction, logging, failover, and cost controls |
| **Week 3 retrieval mechanics** | Dense and sparse retrieval, chunking comparison, metadata filters, Recall@k, Precision@k, MRR, token budgets, and context assembly |
| **Prompt and KV-cache provider material** | Stable-prefix construction, cache eligibility, provider-reported cache evidence, local timing evidence, prefill-cost awareness, and mutation detection |
| **Effective Feedback Compute research** | Feedback validity, novelty, retention, action change, and task sufficiency rather than rewarding raw token, retry, or tool-call volume |
| **AI reliability harness doctrine** | Typed contracts, fixed evals, explicit failure states, privacy-safe traces, reproducible evidence, regression gates, and maintainable runtime boundaries |

AuraGateway does not reproduce Coinbase’s infrastructure. The Coinbase post supplies an engineering hypothesis. AuraGateway supplies a bounded test harness that can evaluate whether the underlying ideas work under named conditions.

---

# 4. Problem Statement

Many AI applications assemble every request as an isolated concatenation event:

```text
system instructions
+ tool definitions
+ examples
+ retrieved chunks
+ conversation history
+ timestamps
+ user metadata
+ current request
= model call
```

This creates five recurring problems.

## 4.1 Cache-Hostile Context Construction

Stable instructions, tool contracts, schemas, examples, retrieval evidence, timestamps, identifiers, and dynamic state are frequently mixed without a canonical boundary.

Small changes can mutate the stable prefix:

- a timestamp;
- unordered JSON;
- changed whitespace;
- tool-order drift;
- schema-order drift;
- random identifiers;
- provider-specific serialization differences;
- dynamic retrieval inserted before stable content.

The application may believe it has a stable prompt while the actual provider payload changes every turn.

## 4.2 Per-Turn Routing Can Destroy Trajectory Value

A naive router chooses the cheapest adequate model for each turn independently.

That can be locally rational and globally wasteful. If cache state belongs to a specific provider/model route, switching can discard reusable session computation. A marginally cheaper turn can become a more expensive trajectory.

AuraGateway tests a different objective:

> Choose the lowest expected trajectory cost subject to capability, safety, quality, and cache-affinity constraints.

## 4.3 Lower Token Use Can Hide Worse Behaviour

A system can become cheaper by:

- skipping retrieval;
- shortening answers below task sufficiency;
- refusing too often;
- avoiding necessary validation;
- escalating prematurely;
- choosing an incapable economy model;
- failing to retain corrective feedback;
- terminating difficult trajectories early.

Raw token reduction is not a success metric. Runtime savings are accepted only after fixed task-quality guardrails pass.

## 4.4 Provider Telemetry Is Semantically Inconsistent

Providers expose different signals and use different definitions.

| Provider/runtime | Potentially useful evidence | Important limitation |
|---|---|---|
| **Anthropic** | Cache reads, cache creation, uncached suffix input, cache controls | Provider-specific token accounting and cache semantics |
| **OpenAI** | Prompt tokens and cached prompt-token details where available | Provider-managed retention and scheduling behaviour |
| **Ollama/local runtime** | Prompt-evaluation count and duration, load and total duration | Local timing is not provider-style cached-token evidence |

Unknown evidence must remain unknown. Missing values must never become fabricated zeroes.

## 4.5 Weak Benchmark Protocol Can Manufacture Confidence

Even a sound architecture can produce misleading conclusions when:

- run order is not controlled;
- provider load varies across conditions;
- failed runs disappear;
- conditions use different configuration fingerprints;
- review is not blinded;
- easy or ambiguous cases dominate;
- exclusions are decided after seeing results;
- cold and warm turns are mixed;
- timing claims use too few repetitions.

The 200-hour design treats benchmark execution as a first-class product component.

---

# 5. Product Vision

## 5.1 Product Statement

AuraGateway is a local-first, typed, provider-aware runtime and evaluation harness that:

1. constructs and freezes a retrieval-grounded benchmark;
2. compiles stable and volatile context deterministically;
3. fingerprints the exact reusable prefix;
4. detects prefix mutation and volatile-content leakage;
5. preserves eligible session routes while cache value remains plausible;
6. normalizes provider telemetry without erasing provider meaning;
7. evaluates retrieval, task quality, runtime behaviour, and feedback evidence;
8. refuses invalid comparisons automatically;
9. retains failures, outliers, exclusions, and reruns;
10. produces reproducible machine-readable and human-readable evidence.

## 5.2 Product Positioning

AuraGateway is demonstrated as:

> A controlled runtime audit harness for identifying where retrieval agents repeatedly reconstruct stable context, lose cache value through route changes, misinterpret provider telemetry, and mistake lower activity for useful progress.

It is not positioned as a production AI gateway.

## 5.3 Commercial Translation

Potential future offer:

> **Context, Cache, and Agent Runtime Efficiency Audit**

| Buyer problem | AuraGateway proof asset |
|---|---|
| AI spend rises without clear task improvement | Paired runtime and quality comparison |
| Long instructions and tools are repeatedly resent | Static/volatile compiler and mutation audit |
| Per-turn routing discards session value | Cache-affinity route policy and route-decision report |
| Teams cannot trust provider usage fields | Provider-specific telemetry contracts and sufficiency gate |
| Cost reductions may harm answer quality | Fixed non-inferiority guardrails and blinded adjudication |
| Agent traces contain noise rather than progress | Validity, novelty, retention, and task-sufficiency evidence |
| Teams cannot reproduce internal benchmark claims | Immutable evidence bundle and one-command report generation |

The project creates proof that this future offer could be credible. It does not itself constitute a finished consultancy product.

---

# 6. Goals

## 6.1 Primary Goals

1. Build a fixed multi-turn retrieval-grounded technical-support workload.
2. Compare at least two chunking strategies and dense versus sparse retrieval before freeze.
3. Construct a diagnostic development set and a protected held-out set.
4. Freeze a benchmark constitution before measured provider runs.
5. Build deterministic static-prefix and volatile-append context serialization.
6. Prove static-prefix stability across controlled turns.
7. Detect deliberate and accidental prefix mutation.
8. Integrate provider-specific cache telemetry without flattening incompatible semantics.
9. Implement a bounded cache-affinity session-routing policy.
10. Compare Conditions A, B, and C under matching configuration fingerprints.
11. Separate functional quality evaluation from high-repetition runtime measurement.
12. Add negative controls proving the harness detects broken prefixes, telemetry, routing, feedback retention, and privacy violations.
13. Use deterministic checks plus blinded rubric review for task quality.
14. Record useful, redundant, invalid, retained, and unretained feedback evidence.
15. Generate a reproducible evidence bundle and buyer-readable report.
16. Preserve privacy through synthetic data and metadata-safe traces.

## 6.2 Secondary Goals

1. Demonstrate provider-neutral interfaces.
2. Demonstrate Pydantic v2 schema-first boundaries.
3. Demonstrate machine-enforced comparison eligibility.
4. Demonstrate provider-evidence sufficiency decisions.
5. Demonstrate paired benchmark analysis and practical uncertainty reporting.
6. Demonstrate one-command local reproduction.
7. Produce a technical case study, skeptical-reviewer guide, and ten-minute demo.

---

# 7. Non-Goals

## 7.1 Product Non-Goals

- A production multi-tenant gateway.
- General-purpose proxy compatibility.
- API-key management for external users.
- Billing or chargeback.
- Enterprise authentication or authorization.
- Frontend/dashboard development.
- Kubernetes or cloud deployment.
- Queues, serverless infrastructure, or managed databases.
- Production cross-provider failover.
- Autonomous control of real customer spend.
- Universal support for every provider.
- Arbitrary user-submitted prompt templates.
- Open-ended autonomous agents.
- Fine-tuning.
- Long-term memory productization.
- Customer-data ingestion.
- High-throughput production load testing.
- Performance claims outside the frozen benchmark.

## 7.2 Research Non-Goals

- Direct inspection of vendor VRAM.
- Proof of vendor internal KV-cache architecture.
- Reproduction of Coinbase’s internal platform.
- Statistical claims of universal generalization.
- A universal live EFC score.
- A claim that fewer tokens always indicate better behaviour.
- Broad model or provider ranking.

---

# 8. Scope Boundary and Roadmap Separation

AuraGateway remains separate from:

- the AI consultancy roadmap’s core capstones;
- the primary consultancy proof repository;
- the Week 3 retrieval scorecard;
- unrelated reliability projects;
- production infrastructure work.

AuraGateway may borrow learning concepts from Week 3, but it must independently contain its own:

- corpus;
- retrieval benchmark;
- chunking comparison;
- dense/sparse comparison;
- development cases;
- held-out cases;
- runtime episodes;
- quality rubric;
- benchmark constitution;
- evidence report.

It must not become a dependency that blocks consultancy progress.

---

# 9. Target Users and Stakeholders

| Stakeholder | Need |
|---|---|
| **AI reliability engineer** | Inspectable runtime architecture, failure evidence, regression gates |
| **LLM runtime engineer** | Correct provider boundaries, cache evidence, serialization and routing policy |
| **Evaluation scientist** | Frozen cases, causal contrasts, paired execution, blinded review, uncertainty reporting |
| **RAG engineer** | Retrieval scorecard, metadata controls, freeze integrity, citations and grounding |
| **Senior engineer / CTO reviewer** | Reproducible result, maintainable boundaries, honest claims |
| **Future consultancy buyer** | Clear evidence of avoidable runtime waste and quality-preserving remediation |
| **Privacy/security reviewer** | Synthetic data, no raw content in traces, explicit vendor boundaries |
| **Project maintainer** | Typed interfaces, one-command workflow, runbooks, artifact hashes |

---

# 10. Core Terms

| Term | Definition |
|---|---|
| **Prefill** | Processing input context before model output generation begins |
| **KV cache** | Cached key/value attention states that may avoid recomputing previously processed prompt content |
| **Prompt cache** | Provider-level reuse of stable prompt-prefix computation across requests |
| **Static anchor** | Versioned stable context intended to remain identical across comparable turns |
| **Volatile append** | Dynamic request material placed after the static anchor |
| **Prefix fingerprint** | HMAC-SHA256 fingerprint of canonical provider-serialized static content |
| **Cache affinity** | Policy preference to preserve a current route while cache reuse remains plausible |
| **Cache evidence** | Provider-reported or locally inferred signal related to cache behaviour |
| **Functional benchmark** | Full task-quality evaluation across hard multi-turn episodes |
| **Runtime microbenchmark** | Higher-repetition subset used for latency, cache, and cost measurement |
| **Comparison pair** | Matching episode and replication identity across A/B/C conditions |
| **Configuration fingerprint** | Hash/version bundle proving controlled constants match across runs |
| **Comparison eligibility** | Machine decision stating whether two or more runs may be compared |
| **Telemetry sufficiency** | Machine decision stating which cache, latency, or cost claims are permitted |
| **Negative control** | Deliberately broken condition used to prove the harness detects an expected failure |
| **Task-quality guardrail** | Fixed criterion preventing savings from being accepted when behaviour worsens |
| **Feedback evidence** | Trace event showing validity, novelty, retention, action change, and sufficiency |
| **Observed evidence** | Directly returned by a provider/runtime response |
| **Inferred evidence** | Derived from controlled local timing or deterministic instrumentation |
| **Unavailable evidence** | Not present or not defensibly inferable |

---

# 11. Experimental Design

## 11.1 Primary Causal Questions

AuraGateway answers three distinct questions.

### Question 1 — Context Construction

```text
Does deterministic static/volatile context construction change cache evidence,
uncached input work, prefill latency, or cost while holding route policy fixed?
```

Comparison:

```text
Condition A versus Condition B
```

### Question 2 — Cache-Affinity Routing

```text
Does preserving an eligible session route while cache value remains plausible
improve trajectory-level runtime outcomes while holding deterministic context fixed?
```

Comparison:

```text
Condition B versus Condition C
```

### Question 3 — Total Runtime Policy

```text
What is the combined difference between the realistic weak baseline and the
full deterministic, cache-aware runtime?
```

Comparison:

```text
Condition A versus Condition C
```

A versus C is a total-system comparison and must not be described as identifying one causal mechanism.

## 11.2 Benchmark Constitution

Before measured runs, the project must freeze a versioned benchmark constitution containing:

- benchmark question;
- condition definitions;
- intervention definitions;
- controlled constants;
- run-order policy;
- counterbalancing method;
- provider/model aliases;
- generation settings;
- cache namespace rules;
- cold/warm classification;
- turn spacing;
- timeout policy;
- bounded retry policy;
- ambiguous-response handling;
- exclusion rules;
- rerun rules;
- denominator policy;
- blinded review protocol;
- adjudication protocol;
- metric formulas;
- bootstrap configuration;
- quality thresholds;
- reportable claims;
- invalidation triggers.

No benchmark rule may be changed after measured results are inspected without versioning the constitution and rerunning all affected comparisons.

## 11.3 Paired and Counterbalanced Execution

Every measured run must include:

```text
comparison_pair_id
episode_id
replication_id
condition_id
provider_model_alias
benchmark_manifest_hash
configuration_fingerprint
```

Conditions must be executed using a counterbalanced schedule to reduce run-order and provider-load bias.

An example three-replication Latin-style schedule:

```text
Replication 1: A → B → C
Replication 2: B → C → A
Replication 3: C → A → B
```

The exact schedule must be declared in the benchmark constitution.

## 11.4 Run Accountability

Every run must resolve to one of:

```text
completed
completed_with_validation_failure
provider_error
budget_exhausted
excluded_by_predeclared_rule
invalidated_by_configuration_mismatch
aborted_by_safety_control
```

Failed, retried, excluded, and invalidated runs remain in the evidence bundle. They may not be deleted because they are inconvenient.

---

# 12. Benchmark Workload

## 12.1 Workload Type

AuraGateway evaluates one bounded workflow:

> **Multi-turn API troubleshooting and technical-support assistant**

The workflow requires:

- retrieval;
- stable instructions;
- tools and structured outputs;
- dynamic user state;
- evolving conversation context;
- citations;
- ambiguity detection;
- clarification;
- escalation;
- feedback retention;
- route state.

## 12.2 Synthetic Corpus

The local, version-controlled corpus represents a fictional developer platform:

> **Nimbus Relay API**

Corpus topics include:

- authentication;
- API keys;
- OAuth;
- pagination;
- rate limits;
- retries;
- error codes;
- webhooks;
- SDK behaviour;
- API versioning;
- idempotency;
- file uploads;
- event delivery;
- incident statuses;
- permissions;
- sandbox limitations.

## 12.3 Corpus Constraints

| Requirement | Minimum |
|---|---:|
| Documents | 30 |
| Document formats | Markdown and JSON only |
| Intent categories | 10 |
| Required metadata fields | `source_id`, `version`, `topic`, `api_area`, `status`, `updated_at` |
| Deliberately stale documents | 5 |
| Deliberately conflicting documents | 5 |
| Documents with incomplete guidance | 4 |
| Near-duplicate documents | 4 |
| Version-sensitive procedures | 6 |
| Public/customer data | 0 |
| Secrets | 0 |
| Raw production logs | 0 |

## 12.4 Evaluation Assets

| Asset | Count | Purpose |
|---|---:|---|
| Development retrieval cases | 24 | Compare chunking, dense/sparse retrieval, top-k, and metadata filtering |
| Held-out retrieval cases | 16 | Confirm the frozen retrieval choice |
| Functional multi-turn episodes | 18 | Evaluate task quality, grounding, policy, and feedback behaviour |
| Runtime microbenchmark episodes | 6 | Higher-repetition cache, latency, and cost measurement |
| Turns per episode | 4 | Create meaningful trajectory progression |
| Functional repetitions per condition | 3 | Reduce single-run quality noise |
| Runtime repetitions per condition | 10 | Improve practical runtime uncertainty estimates |
| Functional measured trajectories | 162 | 18 × 3 conditions × 3 repetitions |
| Runtime measured trajectories | 180 | 6 × 3 conditions × 10 repetitions |

The first turn of every trajectory is retained and reported separately from eligible warm turns.

## 12.5 Diagnostic Case Requirements

Each accepted evaluation case must identify a concrete failure hypothesis.

Required case fields:

```text
case_id
case_family
failure_hypothesis
required_sources
forbidden_sources
expected_terminal_decision
required_information_gain
acceptable_variants
failure_labels
accept_reason
difficulty_reason
evaluation_split
```

Required case families include:

- version-conflicting sources;
- similar error codes;
- missing required parameters;
- incomplete documentation;
- repeated user information;
- contradictory user correction;
- duplicate retrieval evidence;
- noisy context dilution;
- unsupported requested behaviour;
- model capability edge cases;
- multi-turn evidence correction;
- provider failure mid-session.

Trivial, ambiguous, duplicate, ungrounded, or non-diagnostic cases must be rejected with a stored reject reason.

## 12.6 Task Outcomes

Each episode must end in exactly one of:

```text
answer
clarify
escalate
refuse
```

An answer requires:

- valid structured output;
- valid citation IDs;
- source-supported claims;
- no contradiction with selected evidence;
- no stale or forbidden source use.

A clarification requires:

- explicit missing information;
- no unsupported assumptions;
- a question capable of resolving the missing state.

An escalation requires:

- a typed escalation reason;
- no fabricated technical procedure;
- retained evidence showing why the issue cannot be safely resolved.

A refusal requires:

- a policy or evidence-based reason;
- no hidden substitution with unsupported advice.

---

# 13. Retrieval Design

## 13.1 Retrieval Baselines

AuraGateway must compare:

1. **Sparse retrieval**
   - BM25 or equivalent deterministic lexical retrieval.

2. **Dense retrieval**
   - Embedding similarity behind a provider-neutral interface.

A hybrid may be selected only after development-set evaluation.

## 13.2 Chunking Strategies

At least two strategies are required.

### Strategy One — Fixed Token Window

```text
configurable target size
configurable overlap
source metadata inheritance
```

### Strategy Two — Section-Aware Chunking

```text
semantic heading boundaries
parent-heading preservation
bounded fallback splitting
source metadata preservation
```

## 13.3 Retrieval Metrics

The scorecard must report:

```text
Recall@k
Precision@k
MRR
Correct-source-in-top-k rate
Unsupported-source retrieval rate
Stale-source retrieval rate
Metadata-filter violation rate
Near-duplicate displacement rate
```

## 13.4 Retrieval Freeze Gate

After development cases select:

- chunking strategy;
- retrieval type;
- top-k;
- metadata filtering policy;
- score normalization;

those values are frozen before held-out retrieval validation and runtime comparison.

Any post-freeze change invalidates all affected A/B/C results and requires a complete rerun.

---

# 14. Product Architecture

## 14.1 High-Level Flow

```text
Frozen benchmark manifest
        ↓
Typed episode intake
        ↓
Retrieval core
        ↓
Canonical context planner
        ↓
Static anchor + volatile append compiler
        ↓
Prefix fingerprint and mutation audit
        ↓
Cache-affinity route controller
        ↓
Provider-neutral inference client
        ↓
Provider response and telemetry normalizer
        ↓
Structured-output and citation validator
        ↓
Feedback-evidence evaluator
        ↓
Metadata-safe trace writer
        ↓
Comparison eligibility gate
        ↓
Telemetry sufficiency gate
        ↓
Result bundle and report generator
```

## 14.2 Proposed Repository Shape

```text
auragateway/
  packages/
    config/
    contracts/
    retrieval_core/
    context_compiler/
    cache_policy/
    inference_clients/
      providers/
    telemetry/
    feedback_evidence/
    evaluation/
    privacy_controls/
    comparison_control/
    reporting/
  apps/
    benchmark_runner/
  data/
    corpus/
    prompts/
    evals/
      development/
      held_out/
      runtime_microbenchmark/
    provider_fixtures/
    pricing/
  docs/
    adr/
    runbooks/
    benchmark/
    case_study/
    handover/
  evidence_vault/
    retrieval_reports/
    prefix_reports/
    telemetry_reports/
    runtime_reports/
    quality_reports/
    trace_samples/
    before_after_tables/
  tests/
    unit/
    integration/
    metamorphic/
    fault_injection/
  .local/
```

## 14.3 Dependency Direction

```text
apps
  ↓
evaluation / comparison_control / reporting
  ↓
context_compiler + retrieval_core + cache_policy
  ↓
inference_clients + telemetry + feedback_evidence
  ↓
contracts + config + privacy_controls
```

Rules:

- only `packages/inference_clients/providers/` may import provider SDKs;
- evaluation packages may not inspect provider SDK objects directly;
- trace writers may not receive raw prompts, documents, outputs, or provider payloads;
- reporting consumes immutable typed result bundles, not live provider objects;
- comparison control may reject runs but may not mutate historical results.

---

# 15. Architecture Principles

## 15.1 Schema First

All core boundaries use Pydantic v2.

Forbidden across core interfaces:

```python
dict[str, Any]
list[dict[str, Any]]
```

These forms are allowed only inside isolated raw-provider parsing functions that immediately validate into typed models.

## 15.2 Canonical Serialization

Required canonicalization:

- UTF-8 encoding;
- newline normalization;
- deterministic JSON key ordering;
- deterministic tool ordering;
- deterministic schema ordering;
- stable whitespace rules;
- explicit serialization version;
- explicit template/context-pack versions;
- immutable static segment identifiers;
- no timestamps, request IDs, session IDs, or random values in static content.

## 15.3 Data Minimization

Retain:

- metadata;
- fingerprints;
- versions;
- source references;
- timing;
- labels;
- metric values;
- safe error envelopes.

Do not retain:

- raw prompts;
- raw user messages;
- raw retrieved documents;
- raw model outputs;
- raw provider payloads outside adapters;
- secrets;
- direct personal identifiers.

## 15.4 Evidence Before Claims

No runtime claim is accepted without:

- baseline;
- intervention;
- fixed workload;
- matching configuration fingerprints;
- metric definitions;
- run counts;
- uncertainty summary;
- failed-run accounting;
- task-quality result;
- residual risks;
- explicit non-claims.

## 15.5 Provider Semantics Are Preserved

Normalized contracts must preserve material semantic differences.

Unknown or unsupported derived values remain `None`.

## 15.6 Software-Evolution Constraint

A passing benchmark is not sufficient if the implementation is brittle.

Changes should remain easy after the next three likely requirements:

- a new provider fixture;
- a new runtime condition;
- a revised quality rubric version;
- a new retrieval case family;
- a new report metric.

---

# 16. Core Functional Requirements

## FR-001 — Typed Benchmark Episode

```python
class BenchmarkEpisode(BaseModel):
    episode_id: str
    turns: list["EpisodeTurn"]
    expected_outcome: "ExpectedOutcome"
    source_scope: "SourceScope"
    task_type: str
    difficulty: Literal["low", "medium", "high"]
    evaluation_split: Literal[
        "development",
        "held_out",
        "runtime_microbenchmark",
    ]
    failure_hypothesis: str
    required_source_ids: list[str]
    forbidden_source_ids: list[str]
```

## FR-002 — Typed Conversation Turns

```python
class EpisodeTurn(BaseModel):
    turn_index: int
    user_message: str
    expected_information_gain: list[str]
    expected_decision: Literal[
        "answer",
        "clarify",
        "escalate",
        "refuse",
    ] | None
```

Raw user messages may exist inside benchmark assets but must never be emitted into public traces.

## FR-003 — Static Anchor Registry

```python
class StaticAnchorSpec(BaseModel):
    template_id: str
    template_version: str
    output_schema_version: str
    tool_contract_version: str
    context_pack_id: str | None
    context_pack_version: str | None
    serialization_version: str
```

The client may not inject arbitrary runtime text into the static anchor.

## FR-004 — Volatile Append Contract

```python
class VolatileAppendSpec(BaseModel):
    current_user_message: str
    conversation_delta: list["ConversationTurn"]
    retrieval_evidence: list["RetrievedChunkReference"]
    safe_runtime_metadata: "SafeRuntimeMetadata"
```

## FR-005 — Volatile-Content Isolation

The compiler must block the following from static content:

- timestamps;
- request IDs;
- session IDs;
- direct user identifiers;
- retrieval chunks;
- conversation history;
- runtime token counts;
- provider response data;
- temporary flags;
- random values;
- secrets;
- unstable metadata.

## FR-006 — Prefix Fingerprint

```text
prefix_fingerprint = HMAC-SHA256(
    canonical_provider_serialization(static_anchor)
)
```

Also retain:

- template ID/version;
- tool-contract fingerprint;
- output-schema fingerprint;
- context-pack fingerprint;
- serialization version.

## FR-007 — Prefix Mutation Audit

```text
prefix_mutation_detected = true
mutation_reason =
  template_version_changed
  tool_contract_changed
  output_schema_changed
  context_pack_changed
  serialization_order_changed
  forbidden_volatile_field_detected
  provider_serialization_changed
  unknown
```

## FR-008 — Retrieval Core

The system must:

- support dense retrieval;
- support sparse retrieval;
- support metadata filtering;
- return source and chunk IDs;
- retain retrieval scores;
- block excluded stale sources;
- produce a typed unsupported state when evidence is insufficient.

## FR-009 — Structured Output Contract

```python
class AssistantDecision(BaseModel):
    decision: Literal["answer", "clarify", "escalate", "refuse"]
    answer: str | None
    citations: list[str]
    missing_information: list[str]
    escalation_reason: str | None
    confidence_band: Literal["high", "medium", "low"]
```

Rules:

- `answer` is required only for `decision="answer"`;
- citations are required for every answer;
- unsupported answers may not use high confidence;
- clarification, escalation, and refusal require structured reasons.

## FR-010 — Provider-Neutral Inference Boundary

```python
class InferenceClient(Protocol):
    async def generate(
        self,
        request: "ProviderRequest",
    ) -> "ProviderResponse":
        ...
```

Required implementations:

| Adapter | Requirement |
|---|---|
| **FakeInferenceClient** | Mandatory for deterministic tests and functional fixtures |
| **Primary live provider adapter** | Mandatory for controlled cache-evidence benchmark where credentials permit |
| **Secondary provider fixture normalizer** | Mandatory; live use not required |
| **OllamaInferenceClient** | Optional local timing path |

A third live provider is out of scope.

## FR-011 — Explicit Provider Errors

```python
class ProviderErrorEnvelope(BaseModel):
    provider: str
    model: str
    error_code: str
    retryable: bool
    timeout_seconds: float | None
    response_state: Literal[
        "no_response",
        "definite_failure",
        "ambiguous",
    ]
    safe_message: str
    trace_id: UUID
```

Retries must be bounded. Ambiguous response state must not trigger blind duplicate generation.

## FR-012 — Cache Evidence Contract

```python
class CacheEvidence(BaseModel):
    provider: str
    model: str
    evidence_level: Literal[
        "observed_provider",
        "inferred_local",
        "unavailable",
    ]
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    uncached_input_tokens: int | None
    total_input_tokens: int | None
    cache_read_ratio: float | None
    prompt_eval_duration_ms: float | None
    cache_ttl_hint_seconds: int | None
    evidence_notes: list[str]
```

Rules:

- ratios remain `None` when denominators are not defensible;
- local timing may not populate provider cache-token fields;
- unknown values remain `None`;
- evidence includes provider/model identity.

## FR-013 — Telemetry Sufficiency

```python
class TelemetrySufficiency(BaseModel):
    cache_claim_permitted: bool
    latency_claim_permitted: bool
    cost_claim_permitted: bool
    unavailable_fields: list[str]
    reasons: list[str]
```

The report generator must honour this decision. Prose may not override it.

## FR-014 — Session Route State

```python
class SessionRouteState(BaseModel):
    session_id_hash: str
    active_provider: str | None
    active_model: str | None
    last_cache_evidence_at: datetime | None
    cache_affinity_status: Literal[
        "cold",
        "plausibly_warm",
        "expired",
        "unknown",
    ]
    route_change_count: int
    last_route_reason: str
```

Allowed route reasons:

```text
session_start
warm_cache_affinity
ttl_expired
provider_failure
capability_requirement
safety_requirement
quality_guardrail
session_reset
benchmark_control
```

## FR-015 — Route-Change Guard

No route switch during a plausibly warm session unless:

- provider failure;
- safety requirement;
- hard capability mismatch;
- quality guardrail failure;
- TTL expiry;
- explicit benchmark transition.

## FR-016 — Feedback Evidence Event

```python
class FeedbackEvidenceEvent(BaseModel):
    trace_id: UUID
    turn_index: int
    event_id: str
    subgoal_id: str
    evidence_source: Literal[
        "retrieval",
        "schema_validator",
        "citation_validator",
        "deterministic_rule",
        "provider_error",
        "user_clarification",
    ]
    evidence_fingerprint: str
    validity_status: Literal["valid", "invalid", "unknown"]
    novelty_status: Literal["new", "redundant", "unknown"]
    retained_in_state: bool | None
    retention_location: str | None
    next_action_changed: bool | None
    task_sufficiency_status: Literal[
        "insufficient",
        "sufficient",
        "unknown",
    ]
    evidence_reason_code: str
```

## FR-017 — Comparison Eligibility

```python
class ComparisonEligibility(BaseModel):
    eligible: bool
    compared_run_ids: list[str]
    mismatched_fields: list[str]
    invalidated_claims: list[str]
    required_reruns: list[str]
```

The system must refuse comparison when controlled fingerprints differ.

## FR-018 — Metadata-Safe Trace Logging

Every turn emits safe JSON Lines fields:

```text
trace_id
run_id
comparison_pair_id
episode_id
condition_id
replication_id
turn_index
provider
model
route_reason
template_version
configuration_fingerprint
prefix_fingerprint
cache_evidence
timings
retrieval_metrics
decision
validation_result
failure_labels
feedback_evidence_summary
```

Forbidden trace content:

```text
raw prompt
raw user message
raw retrieved document
raw model output
raw provider payload
API key
access token
email
phone number
full user identifier
unbounded metadata dictionary
```

## FR-019 — Reproducible Result Bundle

Every benchmark run must produce:

```text
benchmark_manifest.json
configuration_fingerprint.json
environment_manifest.json
run_results.jsonl
failures.jsonl
exclusions.jsonl
comparison.csv
benchmark_report.md
sanitized_trace_samples.jsonl
artifact_hashes.json
```

## FR-020 — One-Command Workflow

The project must support commands equivalent to:

```powershell
python -m apps.benchmark_runner validate-config
python -m apps.benchmark_runner run --manifest .\data\evals\benchmark_manifest.json
python -m apps.benchmark_runner report --run-id <run-id>
```

The exact command surface may differ, but validation, execution, and report generation must remain deterministic and documented.

---

# 17. Runtime Conditions

## 17.1 Condition A — Cache-Hostile Baseline

Purpose:

> Represent a realistic weak implementation where context is assembled per turn without deterministic static/volatile separation or session cache-affinity policy.

Characteristics:

```text
- per-turn route selection;
- stable and dynamic content may be mixed;
- runtime metadata may appear before stable instructions;
- no canonical serialization gate;
- no static-anchor fingerprint enforcement;
- no session route preservation;
- retrieval and output schema remain fixed;
- the same task-quality checks still apply.
```

Condition A must remain functional and plausible. It must not be artificially sabotaged.

## 17.2 Condition B — Prefix-Deterministic Runtime

Purpose:

> Isolate the value of stable context construction.

Characteristics:

```text
- versioned static anchor;
- deterministic instruction order;
- deterministic tool and schema order;
- canonical serialization;
- typed volatile append;
- retrieval appears only in volatile append;
- HMAC fingerprint validation;
- same provider/model route behaviour as A for the A-versus-B contrast.
```

## 17.3 Condition C — Cache-Aware Agent Runtime

Purpose:

> Test whether preserving session cache value improves trajectory-level outcomes beyond deterministic context construction alone.

Characteristics:

```text
Everything in B
+
cache-affinity session state
+
bounded route-change policy
+
route retained while plausibly warm
+
re-route only for explicit reason
+
route-decision trace
+
cache evidence consumed by policy
```

## 17.4 Experimental Isolation

Every replication uses distinct:

```text
cache_namespace_id
session_id_hash
run_id
comparison_pair_id
condition_id
```

Condition namespaces must not share accidental cache state.

---

# 18. Cache Strategy

## 18.1 Static Anchor Contents

Allowed static content:

- system behaviour policy;
- task procedure;
- output schema;
- stable tool contracts;
- citation rules;
- immutable few-shot examples;
- approved reusable context pack;
- template/schema/tool/context versions.

## 18.2 Volatile Append Contents

- current user message;
- new conversation turns;
- retrieval evidence;
- dynamic metadata;
- current tool result;
- current validation feedback;
- current runtime-state delta.

## 18.3 Context Pack Rule

A reusable context pack is allowed only when it:

1. is relevant to the task class;
2. remains fixed during comparison;
3. preserves or improves development-set quality;
4. introduces no unsupported claims;
5. is not padding intended only to force caching.

## 18.4 Prefix Negative-Control Calibration

Before the main runtime benchmark, execute matched requests using:

```text
exact stable prefix
versus
one controlled stable-prefix mutation
```

Required mutations include at least:

- timestamp insertion;
- tool-order change;
- schema version change;
- JSON ordering change;
- one-byte stable-example change.

If the runtime cannot distinguish stable and mutated prefixes through trustworthy evidence, the benchmark must label cache evidence unavailable or insufficiently sensitive.

---

# 19. Routing Strategy

## 19.1 Routing Objective

Not:

> Choose the cheapest model for the current turn.

Instead:

> Choose the route with the lowest expected trajectory cost subject to capability, safety, quality, and cache-affinity constraints.

## 19.2 Model Roles

```python
class ModelRoleConfig(BaseModel):
    economy_model: str
    capable_model: str
    primary_provider: str
    secondary_provider: str | None
```

## 19.3 Calibration Gate

Before cache-affinity routing is enabled:

1. each candidate model runs against development cases;
2. each model must meet a fixed quality floor;
3. the capable model is required above the economy model’s accepted capability band;
4. routing remains disabled if calibration is incomplete.

Minimum eligibility:

```text
Structured-output validity: ≥ 95%
Citation-ID validity: ≥ 95%
Task-success rate: ≥ 75%
Unsupported-answer rate: ≤ 5%
```

## 19.4 Decision Logic

```text
IF session is new:
    select route using capability, safety, and estimated trajectory cost.

ELSE IF active route is plausibly warm
AND capability remains sufficient
AND no provider error exists
AND no safety or quality rule requires change:
    preserve active route.

ELSE IF TTL is expired:
    re-evaluate route.

ELSE IF provider error is retryable and response state is definite failure:
    retry within bounded policy.

ELSE IF provider failure, safety requirement, capability mismatch,
or quality guardrail failure occurs:
    reroute with explicit reason.

ELSE:
    preserve current route.
```

## 19.5 Route-Thrash Failure

A route-thrash failure occurs when the provider/model changes two or more times during a plausibly warm session without an allowed reason.

---

# 20. Telemetry and Cost Model

## 20.1 Adapter Boundary

Raw provider responses exist inside provider adapters only and are not persisted outside that boundary.

## 20.2 Normalized Usage Telemetry

```python
class UsageTelemetry(BaseModel):
    provider: str
    model: str
    input_tokens_total: int | None
    uncached_input_tokens: int | None
    cache_read_tokens: int | None
    cache_write_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    request_duration_ms: float | None
    time_to_first_output_ms: float | None
    prompt_eval_duration_ms: float | None
    output_generation_duration_ms: float | None
    cache_evidence_level: Literal[
        "observed_provider",
        "inferred_local",
        "unavailable",
    ]
    provider_usage_complete: bool
    pricing_schedule_version: str | None
```

## 20.3 Derived Metrics

| Metric | Definition |
|---|---|
| **Cache read ratio** | `cache_read_tokens / input_tokens_total`, only when valid |
| **Uncached input share** | `uncached_input_tokens / input_tokens_total`, only when valid |
| **Cache write share** | `cache_write_tokens / input_tokens_total`, only when valid |
| **Median TTFO** | Median dispatch-to-first-output time |
| **Median prefill duration** | Direct provider/local prefill timing where available |
| **Avoidable uncached input work** | Uncached input attributable to content that should have remained stable |
| **Route-switch rate** | Route changes divided by eligible sessions |
| **Warm-session preservation rate** | Eligible sessions retaining the active route |
| **Paired trajectory-cost difference** | Condition cost difference within matching comparison pairs |

## 20.4 Pricing Schedule

Cost may be estimated only from a versioned local pricing schedule.

Every cost report states:

```text
pricing schedule version
pricing source date
provider/model aliases
estimated versus provider-reported status
cache read/write price availability
currency
```

Cost estimates are not vendor invoices.

## 20.5 Statistical Reporting

For runtime metrics, report:

- run count;
- successful-run count;
- failure count;
- median;
- p25 and p75;
- minimum and maximum;
- p90 where useful;
- paired per-episode difference;
- bootstrap confidence interval;
- cold and warm results separately;
- success-only and failure-accounted views where appropriate.

The project does not claim academic statistical significance or universal generalization.

---

# 21. Quality and Evaluation Design

## 21.1 Evaluation Rule

Every meaningful AI change is judged against:

```text
fixed cases
baseline
intervention
scoring
failure labels
trace review
before/after comparison
regression notes
```

## 21.2 Deterministic Scoring

Deterministic checks include:

- schema validity;
- valid decision enum;
- citation IDs exist;
- required fields present;
- required source included;
- forbidden or stale source excluded;
- metadata scope respected;
- forbidden claims absent;
- expected terminal state reached;
- route reasons allowed;
- configuration fingerprints match.

## 21.3 Rubric-Based Scoring

Rubric review covers:

- whether the answer resolves the technical issue;
- whether clarification requests the necessary missing information;
- whether escalation is justified;
- whether cited evidence supports material claims;
- whether contradictions remain;
- whether the trajectory is task-sufficient.

## 21.4 Blinded Adjudication

Quality reviewers must not know whether an output came from Condition A, B, or C.

Required protocol:

- outputs receive opaque review IDs;
- at least 25% of rubric-reviewed outputs are double-reviewed;
- disagreements and reasons are retained;
- an adjudicator resolves material disagreements;
- reviewer identity may be pseudonymous but must be traceable locally;
- rubric changes after held-out review invalidate affected results.

LLM-as-judge may assist only when:

- the rubric is explicit;
- cited evidence is provided;
- deterministic checks remain primary where possible;
- a human spot-check sample is retained;
- model and prompt versions are recorded;
- limitations are documented.

## 21.5 Metrics

### Retrieval

```text
Recall@k
Precision@k
MRR
Correct-source-in-top-k rate
Stale-source retrieval rate
Metadata-filter violation rate
Near-duplicate displacement rate
```

### Task Quality

```text
Task-success rate
Structured-output validity
Citation-ID validity
Citation-support pass rate
Unsupported-answer rate
Correct clarification rate
Correct escalation rate
Correct refusal rate
Blinded rubric pass rate
Reviewer disagreement rate
```

### Runtime

```text
Input tokens
Uncached input tokens
Cache read tokens
Cache write tokens
Median TTFO
Median prefill duration
Estimated trajectory cost
Route switches
Route-thrash failures
Provider errors
Retry count
```

### Feedback Evidence

```text
Valid feedback-event rate
Redundant feedback-event rate
Retained feedback-event rate
Unretained valid feedback-event rate
Feedback-linked action-change rate
Task-sufficiency pass rate
```

## 21.6 Quality Non-Inferiority Gate

Condition C is runtime-improved only when:

```text
Task success is no more than 5 percentage points below A.
Citation support does not decrease.
Structured-output validity remains ≥ 95%.
Unsupported-answer rate does not increase.
Retrieval configuration is unchanged.
No new unsafe route, retry, or escalation pattern appears.
```

The report must show A versus B, B versus C, and A versus C. It may not show only the most favourable comparison.

---

# 22. EFC Evidence Model

## 22.1 Purpose

AuraGateway uses EFC as a trace-level discipline:

> Did feedback provide valid, non-redundant information that was retained, changed a later action, and became sufficient for the task?

It does not calculate a universal real-time EFC score.

## 22.2 Allowed Feedback Sources

```text
retrieval result
schema validation
citation validation
deterministic task rule
provider error
user clarification
```

Disallowed:

```text
hidden chain-of-thought
opaque provider reasoning
unverifiable model confidence
arbitrary self-critique without evidence
```

## 22.3 Required Evidence Classes

The fixture suite must include:

- valid + new + retained;
- valid + redundant;
- invalid;
- valid + unretained;
- action-changing feedback;
- task-sufficient trajectory;
- repeated failure without changed hypothesis.

## 22.4 Task Sufficiency

A trace is task-sufficient only when:

- the expected terminal decision is reached;
- required evidence exists;
- no unsupported claim is made;
- mandatory schema fields validate;
- failures are not ignored;
- required clarification or escalation is not bypassed.

---

# 23. Negative Controls and Fault Injection

AuraGateway must prove that it detects broken behaviour.

| Injection | Required outcome |
|---|---|
| Timestamp in static anchor | `VOLATILE_LEAK` or `PREFIX_MUTATION` |
| Changed tool order | Prefix mutation detected |
| Changed output schema/version | Prefix mutation detected |
| Unknown provider cache field | Unknown remains unknown; no fabricated zero |
| Invalid telemetry denominator | `CACHE_SEMANTICS_MISMATCH` |
| Missing cache evidence | `CACHE_EVIDENCE_UNAVAILABLE` |
| Stale document ranked first | Retrieval or stale-source failure |
| Duplicate retrieval event | `REDUNDANT_FEEDBACK` |
| Valid evidence ignored later | `UNRETAINED_FEEDBACK` |
| Provider timeout | Typed provider error |
| Ambiguous provider response | No blind duplicate generation |
| Two unjustified route changes | `ROUTE_THRASH` |
| Cross-condition namespace reuse | Benchmark isolation failure |
| Raw prompt passed to trace writer | `PRIVACY_VIOLATION` |
| Ineligible cheap model used | `CAPABILITY_MISMATCH` |
| Lower cost with quality regression | Savings claim blocked |
| Changed controlled constant | Comparison ineligible |

## 23.1 Metamorphic Properties

Required metamorphic tests:

```text
Changing volatile user content must not change the static fingerprint.
Changing static schema version must change the fingerprint.
Reordering retrieval chunks may change volatile content but not static fingerprint.
Removing telemetry must not create zero-valued cache metrics.
Replacing an eligible model with an ineligible model must invalidate the route.
Equivalent provider fixtures must normalize to equivalent typed meaning.
Changing only the condition namespace must prevent cross-condition cache sharing.
```

---

# 24. Meta-Harness and Evidence Vault

## 24.1 Configuration Fingerprint

Each run fingerprint includes:

```text
corpus manifest hash
retrieval configuration hash
prompt template ID/version
static context-pack ID/version
tool-contract version
output-schema version
evaluation manifest hash
benchmark constitution version
benchmark runner version
route-policy version
pricing schedule version
provider/model alias
provider adapter version
Python version
dependency lock hash
Git commit hash
```

## 24.2 Comparison Invalidation

The harness must reject comparison when any controlled field differs.

The rejection must state:

- mismatched fields;
- affected comparisons;
- invalidated claims;
- required reruns.

## 24.3 Evidence Bundle Immutability

Completed result bundles are append-only.

Corrections create a new bundle and reference the superseded bundle. Historical evidence is not silently overwritten.

## 24.4 Queryable Evidence

Evidence should support queries such as:

- all route changes by reason;
- all prefix mutations;
- all missing telemetry fields;
- all failed or excluded runs;
- all quality regressions;
- all unretained feedback events;
- all comparisons rejected for fingerprint mismatch;
- all claims blocked by telemetry insufficiency.

---

# 25. Privacy, Security, and Vendor Boundary

## 25.1 Data Classification

| Data class | Allowed in repository? | Allowed in public trace? |
|---|---|---|
| Synthetic corpus | Yes | Source IDs only |
| Prompt templates | Yes | IDs and versions only |
| Provider/model aliases | Yes | Yes |
| Token counts and durations | Yes | Yes |
| Prefix fingerprints | Yes | Yes |
| Raw prompt | Private source asset only | No |
| Raw user message | Benchmark asset only | No |
| Raw model output | Local protected artifact only where required for review | No public trace |
| Raw provider payload | Adapter memory only | No |
| API keys | No | No |
| Personal data | No | No |
| Production customer documents | No | No |

## 25.2 Required Controls

- `.env` ignored by Git;
- `.local/` ignored by Git;
- no secrets in logs;
- no raw provider payload persistence;
- HMAC key from local environment settings;
- least-privilege credentials;
- environment-separated configuration;
- local trace rotation;
- retention/deletion runbook;
- synthetic data only;
- provider boundary note in every benchmark report;
- trace schema rejects forbidden fields;
- sanitized review exports use opaque IDs.

## 25.3 Vendor Boundary Record

Every run report states:

```text
provider
model
whether prompts left local execution
what data categories crossed the boundary
whether cache telemetry was observed
whether local timing was inferred
what metadata was retained
pricing schedule source date
provider documentation check date
```

These are engineering controls, not legal compliance claims.

---

# 26. Failure Taxonomy

| Code | Failure label | Meaning |
|---|---|---|
| `PREFIX_MUTATION` | Unexpected stable-prefix change | Static content changed between comparable turns |
| `VOLATILE_LEAK` | Dynamic content entered static anchor | Timestamp, retrieval, ID, or dynamic state contaminated prefix |
| `CACHE_EVIDENCE_UNAVAILABLE` | No usable cache evidence | Runtime exposed insufficient evidence |
| `CACHE_EVIDENCE_INSUFFICIENTLY_SENSITIVE` | Calibration failed | Stable and deliberately mutated prefixes could not be distinguished |
| `CACHE_COLD_EXPECTED` | Expected first-turn cold state | No previous eligible cache state |
| `CACHE_WARM_EXPECTED_MISS` | Expected warm reuse absent | Prefix, route, TTL, or provider behaviour requires review |
| `CACHE_SEMANTICS_MISMATCH` | Incorrect normalization | Provider fields were interpreted incorrectly |
| `COMPARISON_INELIGIBLE` | Controlled constants differ | Runs may not be compared |
| `BENCHMARK_ISOLATION_FAILURE` | Cache namespace contamination | Conditions may have shared state |
| `ROUTE_THRASH` | Repeated unjustified switching | Route changed without allowed reason |
| `CAPABILITY_MISMATCH` | Model below quality floor | Router chose an ineligible model |
| `RETRIEVAL_MISS` | Correct source absent | Retrieval failure |
| `STALE_SOURCE_SELECTED` | Outdated source used | Metadata/provenance failure |
| `CONTEXT_DILUTION` | Relevant evidence displaced | Context assembly failure |
| `UNSUPPORTED_ANSWER` | Answer exceeds evidence | Grounding failure |
| `INVALID_SCHEMA_OUTPUT` | Output violates contract | Structured-output failure |
| `CITATION_FAILURE` | Citation invalid or unsupported | Attribution failure |
| `REDUNDANT_FEEDBACK` | Repeated evidence without progress | Feedback-quality failure |
| `UNRETAINED_FEEDBACK` | Valid evidence not used later | State/trajectory failure |
| `INVALID_RETRY` | Same failure repeated without new hypothesis | Regulation failure |
| `AMBIGUOUS_DUPLICATE_RISK` | Retry could duplicate uncertain generation | External-call safety failure |
| `BUDGET_EXHAUSTION` | Action or token budget reached | Safe termination required |
| `PROVIDER_TIMEOUT` | Provider exceeded timeout | External I/O failure |
| `PROVIDER_UNAVAILABLE` | Provider unavailable | External I/O failure |
| `QUALITY_REGRESSION` | Runtime saving failed quality gate | Improvement claim blocked |
| `REVIEW_DISAGREEMENT` | Quality reviewers materially disagree | Adjudication required |
| `PRIVACY_VIOLATION` | Forbidden field entered trace/export | Logging boundary failure |

---

# 27. Non-Functional Requirements

## 27.1 Maintainability

- Python 3.11+;
- Pydantic v2;
- pytest;
- Ruff and mypy;
- structured JSON logs;
- explicit error taxonomy;
- no blanket exceptions;
- no notebook-only core logic;
- provider adapters isolated;
- fake clients for deterministic tests;
- full reproducibility through documented commands;
- configuration through typed settings;
- explicit run IDs and trace IDs.

## 27.2 Performance

| Metric | Target |
|---|---|
| Prefix canonicalization | Median under 5 ms locally |
| Prefix fingerprint | Median under 2 ms locally |
| Trace serialization | Must not block model streaming |
| Benchmark validation startup | Under 10 seconds excluding provider calls |
| Report generation | Under 30 seconds for one complete run bundle |
| Comparison eligibility check | Under 2 seconds for a completed bundle |

## 27.3 Reliability

- bounded timeouts;
- bounded retries;
- exponential backoff where appropriate;
- idempotency-aware request handling;
- no automatic duplicate generation after ambiguous response state;
- deterministic provider fixtures;
- explicit failure output;
- append-only completed evidence bundles;
- rollback through configuration, not code surgery.

## 27.4 Reproducibility

Every benchmark report must include:

```text
Git commit hash
Python version
dependency lock hash
provider/model aliases
provider adapter version
prompt template version
corpus manifest hash
retrieval configuration hash
evaluation manifest hash
benchmark constitution version
pricing schedule version
benchmark timestamps
run counts
failed/excluded counts
known external conditions
```

---

# 28. Test Strategy

## 28.1 Unit Tests

| Module | Required tests |
|---|---|
| Context compiler | Canonical ordering, static/volatile separation, forbidden-field rejection |
| Prefix fingerprint | Stable input, changed input, HMAC behaviour, serialization version |
| Retrieval core | Dense/sparse contracts, metadata filters, no-result state |
| Telemetry normalizer | Primary fixture, secondary fixture, Ollama/local timing separation |
| Telemetry sufficiency | Permitted and blocked cache/latency/cost claims |
| Cache policy | Warm retention, TTL expiry, provider failure, no thrash |
| Schema validator | Valid/invalid outputs, enum failures, citation requirements |
| Feedback evidence | Novel/redundant, retained/unretained, sufficient/insufficient |
| Trace redaction | Raw content and secrets rejected |
| Comparison eligibility | Matching and mismatching fingerprints |
| Report generator | JSON/CSV/Markdown consistency |

## 28.2 Integration Tests

1. End-to-end fake-provider functional run.
2. Five-turn prefix-stability audit.
3. Timestamp mutation fails prefix stability.
4. Tool-order mutation fails prefix stability.
5. Output-schema mutation fails prefix stability.
6. Retrieval source selection remains fixed across A/B/C.
7. Condition C preserves an eligible warm route.
8. Condition C reroutes on provider failure with explicit reason.
9. Malformed output produces typed validation failure.
10. Valid retrieval changing next action is marked retained.
11. Duplicate evidence is marked redundant.
12. Mismatched configuration fingerprints block comparison.
13. Missing provider telemetry blocks unsupported claims.
14. Raw prompt passed to trace writer is rejected.
15. Report files derive from the same immutable result bundle.

## 28.3 Metamorphic Tests

Required properties are defined in Section 23.1 and must run as a separate test group.

## 28.4 Fault-Injection Tests

All required injections in Section 23 must have deterministic fixtures.

## 28.5 Live Smoke Tests

When credentials exist:

- use one primary live provider;
- run prefix negative-control calibration;
- optionally run a short Ollama timing sequence;
- record no raw prompts in traces;
- stop at configured cost cap;
- fail safely when telemetry fields differ from documented semantics;
- capture provider/model/date in the result bundle.

---

# 29. Proof Gates

## Gate 0 — Benchmark Constitution

Required:

```text
Benchmark question frozen.
A/B/C causal contrasts frozen.
Controlled constants declared.
Run-order and counterbalancing declared.
Retry, exclusion, and rerun rules declared.
Quality rubric frozen.
Claim and invalidation rules frozen.
```

## Gate 1 — Retrieval Readiness

```text
Two chunking strategies compared.
Dense and sparse retrieval compared.
Recall@k, Precision@k, and MRR reported.
Final retrieval configuration frozen.
Held-out cases not used for tuning.
```

## Gate 2 — Diagnostic Eval Readiness

```text
Development and held-out assets separated.
Every case has a failure hypothesis.
Trivial, ambiguous, and duplicate cases rejected.
Functional and runtime episode sets frozen.
Blinded review protocol prepared.
```

## Gate 3 — Prefix Determinism

```text
Five controlled turns preserve the static fingerprint.
Volatile append changes do not alter it.
Timestamp, tool-order, schema, and JSON-order mutations fail correctly.
Negative-control calibration is reportable.
```

## Gate 4 — Telemetry Integrity

```text
Provider fixtures map into typed contracts.
Unknown values remain None.
Provider-specific semantics remain distinct.
Local timing remains separate from cached-token evidence.
Telemetry sufficiency decisions are enforced.
```

## Gate 5 — Route Policy

```text
Warm sessions retain eligible active routes.
TTL expiry permits re-evaluation.
Provider failure causes typed reroute.
No route thrash occurs in fixed fixtures.
Every route change has an allowed reason.
```

## Gate 6 — Task-Quality Safety

```text
Structured-output validity ≥ 95%.
Citation support does not regress.
Unsupported-answer rate does not increase.
Task success remains within 5 percentage points of baseline.
Blinded review and adjudication complete.
```

## Gate 7 — Feedback Evidence

```text
Valid/new/retained feedback is visible.
Valid/redundant feedback is visible.
Invalid feedback is visible.
Valid/unretained feedback is visible.
At least one feedback event changes a later action.
At least one trajectory is task-sufficient.
```

## Gate 8 — Fault and Privacy Controls

```text
Required negative controls pass.
Fault-injection suite passes.
Trace redaction rejects forbidden content.
Cross-condition namespace contamination is detected.
Comparison mismatch is blocked.
```

## Gate 9 — Benchmark Execution

```text
Functional and runtime benchmarks complete.
Cold and warm turns separated.
Paired differences reported.
Failed, excluded, and retried runs accounted for.
Configuration fingerprints match.
```

## Gate 10 — Final Evidence Report

```text
A/B/C comparisons exist.
Provider-reported and inferred evidence are separated.
Quality guardrails are explicit.
Uncertainty and outliers are reported.
Failure taxonomy and residual risks are documented.
Technical case study and skeptical-reviewer guide exist.
```

---

# 30. 200-Hour Delivery Plan

## Phase 0 — Design Freeze and Benchmark Constitution: 18 Hours

| Hours | Deliverable |
|---:|---|
| 1–4 | PRD review, scope freeze, ADR map |
| 5–9 | Benchmark constitution and causal contrasts |
| 10–13 | Run-order, retry, exclusion, rerun, and invalidation policy |
| 14–16 | Privacy/vendor boundary and evidence-bundle design |
| 17–18 | Gate 0 review and design checkpoint |

Exit criteria:

- benchmark rules frozen;
- A/B/C contrasts unambiguous;
- claim boundaries approved;
- no customer data;
- no generic gateway drift.

## Phase 1 — Corpus, Retrieval, and Eval Asset Construction: 28 Hours

| Hours | Deliverable |
|---:|---|
| 19–23 | Synthetic corpus and manifest |
| 24–27 | Fixed-window chunker |
| 28–31 | Section-aware chunker |
| 32–35 | Sparse retriever |
| 36–39 | Dense retriever |
| 40–42 | Development retrieval cases and scorecard |
| 43–44 | Retrieval freeze decision |
| 45–46 | Held-out retrieval validation |

Cumulative project hours after Phase 1: **46 / 200**.

Exit criteria:

- retrieval configuration frozen;
- held-out boundary protected;
- diagnostic retrieval cases accepted or rejected with reasons.

## Phase 2 — Typed Contracts and Context Compiler: 24 Hours

| Allocation | Deliverable |
|---:|---|
| 4h | Core Pydantic contracts |
| 4h | Static-anchor registry |
| 3h | Volatile-append contract |
| 4h | Canonical serialization |
| 3h | HMAC prefix fingerprint |
| 3h | Mutation audit and negative controls |
| 3h | Prefix-stability report |

Cumulative project hours: **70 / 200**.

Exit criteria:

- Gate 3 passes;
- deliberate mutations fail correctly;
- raw content remains outside traces.

## Phase 3 — Provider Adapters and Telemetry Calibration: 24 Hours

| Allocation | Deliverable |
|---:|---|
| 4h | Fake provider and deterministic fixtures |
| 6h | Primary live-provider adapter |
| 4h | Secondary-provider fixture normalizer |
| 2h | Optional Ollama timing adapter |
| 4h | Unified telemetry and sufficiency contracts |
| 2h | Provider error taxonomy |
| 2h | Provider semantic mapping report |

Cumulative project hours: **94 / 200**.

Exit criteria:

- Gate 4 passes;
- evidence semantics documented;
- unavailable values remain unavailable;
- unsupported claims are machine-blocked.

## Phase 4 — Cache-Affinity Controller and Trajectory Regulation: 20 Hours

| Allocation | Deliverable |
|---:|---|
| 4h | Session route state |
| 5h | Capability and cost-aware route policy |
| 3h | Warm affinity and TTL logic |
| 3h | Provider failure and ambiguous-response handling |
| 3h | Route-thrash and invalid-retry controls |
| 2h | Route-decision report |

Cumulative project hours: **114 / 200**.

Exit criteria:

- Gate 5 passes;
- route reasons always captured;
- warm routes preserved correctly;
- unsafe retries blocked.

## Phase 5 — Quality, Feedback Evidence, and Blinded Adjudication: 24 Hours

| Allocation | Deliverable |
|---:|---|
| 5h | Functional episode construction and review |
| 3h | Runtime microbenchmark episode selection |
| 4h | Deterministic quality scorers |
| 3h | Blinded rubric and review workflow |
| 4h | Feedback validity, novelty, retention, and sufficiency |
| 3h | Synthetic trajectory fixtures |
| 2h | Quality and EFC trace report |

Cumulative project hours: **138 / 200**.

Exit criteria:

- Gates 2, 6, and 7 pass;
- review is condition-blind;
- EFC remains evidence discipline, not fake universal scoring.

## Phase 6 — Fault Injection, Meta-Harness, and Reproducibility: 22 Hours

| Allocation | Deliverable |
|---:|---|
| 6h | Negative-control and fault-injection suite |
| 4h | Configuration fingerprint and comparison eligibility |
| 3h | Immutable evidence-bundle writer |
| 3h | One-command validation/run/report interface |
| 3h | Metamorphic tests |
| 3h | Privacy and trace-redaction enforcement |

Cumulative project hours: **160 / 200**.

Exit criteria:

- Gate 8 passes;
- invalid comparisons are blocked;
- evidence bundles are reproducible and append-only.

## Phase 7 — Benchmark Execution and Statistical Analysis: 26 Hours

| Allocation | Deliverable |
|---:|---|
| 3h | Dry run and constitution validation |
| 4h | Prefix negative-control calibration |
| 7h | Functional A/B/C execution |
| 6h | Runtime microbenchmark execution |
| 3h | Failed-run and exclusion review |
| 3h | Paired analysis and uncertainty tables |

Cumulative project hours: **186 / 200**.

Exit criteria:

- Gate 9 passes;
- no hidden exclusions;
- cold and warm turns separated;
- paired results available.

## Phase 8 — Reporting, Case Study, Demo, and Handover: 14 Hours

| Allocation | Deliverable |
|---:|---|
| 5h | Final benchmark report and machine-readable bundle |
| 3h | Technical case study |
| 2h | Skeptical-reviewer guide |
| 2h | Ten-minute demo script and runbook |
| 2h | Final evidence audit and formal handover |

Cumulative project hours: **200 / 200**.

Exit criteria:

- Gate 10 passes;
- result is reproducible;
- claims match evidence;
- repository is handover-ready.

## 30.1 Authoritative Hours Ledger

| Phase | Hours | Cumulative |
|---|---:|---:|
| Phase 0 | 18 | 18 |
| Phase 1 | 28 | 46 |
| Phase 2 | 24 | 70 |
| Phase 3 | 24 | 94 |
| Phase 4 | 20 | 114 |
| Phase 5 | 24 | 138 |
| Phase 6 | 22 | 160 |
| Phase 7 | 26 | 186 |
| Phase 8 | 14 | 200 |
| **Total** | **200** | **200** |

---

# 31. Required ADRs

## ADR-0001 — AuraGateway Scope and Non-Goals

AuraGateway is a controlled benchmark harness, not a production gateway.

## ADR-0002 — Benchmark Constitution and Causal Contrasts

A/B/C comparisons require predeclared interventions, controlled constants, run rules, and invalidation triggers.

## ADR-0003 — Canonical Context Serialization

Static and volatile content use typed segments and deterministic serialization.

## ADR-0004 — Prefix Fingerprinting

Use HMAC-SHA256 over canonical static provider payloads; never log raw static content.

## ADR-0005 — Provider Telemetry Semantics

Preserve provider-specific fields and derive metrics only when valid.

## ADR-0006 — Cache-Affinity Route Policy

Preserve eligible routes during plausible warm-cache windows unless explicit reasons require change.

## ADR-0007 — Quality Evaluation and Blinded Adjudication

Use deterministic checks first and condition-blind rubric review for residual qualitative judgment.

## ADR-0008 — EFC Evidence Contract

Track feedback validity, novelty, retention, action change, and sufficiency without claiming a universal score.

## ADR-0009 — Privacy-Safe Observability

Record fingerprints, versions, timing, labels, and source references—not raw sensitive content.

## ADR-0010 — Immutable Evidence Bundles and Comparison Eligibility

Completed evidence is append-only, and mismatched configurations cannot be compared.

---

# 32. Risks and Controls

| Risk | Impact | Control |
|---|---|---|
| Provider cache behaviour changes | Results become stale | Pin provider/model/date and rerun calibration |
| Telemetry is incomplete | Cache claim cannot be supported | Telemetry sufficiency blocks claim |
| Runtime evidence is noisy | False latency conclusion | Paired, counterbalanced high-repetition microbenchmark |
| Prefix calibration shows no sensitivity | Benchmark cannot measure cache effect | Label evidence unavailable or insufficiently sensitive |
| Context pack harms quality | Savings hide degradation | Development calibration and non-inferiority gate |
| Router switches too often | Warm value destroyed | Route-thrash guard |
| Economy model is too weak | Quality drops | Capability calibration gate |
| Retrieval changes across conditions | Confounded result | Retrieval freeze and fingerprint check |
| Condition cache contamination | Invalid comparison | Distinct namespaces and isolation test |
| Easy eval cases inflate success | Weak proof | Diagnostic case acceptance policy |
| Review favours optimized condition | Biased quality score | Opaque IDs and blinded adjudication |
| Failed runs disappear | Misleading result | Append-only run accountability |
| API credits are exhausted | Incomplete live benchmark | Cost cap, fake-provider path, accurate maturity label |
| Traces leak content | Privacy breach | Reject forbidden fields and sanitize review exports |
| EFC grows into a second research project | Delivery risk | Fixed evidence classes and no universal score |
| Project expands into gateway product | Delivery failure | Kill criteria and phase gates |

---

# 33. Kill Criteria

Stop, defer, or remove any feature that does not materially improve:

- benchmark validity;
- causal comparison;
- retrieval quality;
- cache evidence;
- route-policy evidence;
- task-quality safety;
- feedback-evidence quality;
- privacy controls;
- reproducibility;
- buyer-readable proof.

Explicitly defer:

```text
third live provider
frontend dashboard
billing
authentication
generic proxy compatibility
production failover
cloud deployment
managed vector database
multi-agent architecture
fine-tuning
arbitrary Jinja execution
universal EFC dashboard
unsupervised memory system
customer-data ingestion
```

---

# 34. Maturity and Claim Boundaries

## 34.1 Target Maturity at Completion

```text
Production-shaped
Locally validated
Synthetic-corpus validated
Fixed-eval validated
Controlled-provider validated where credentials permit
Not customer-data tested
Not deployed
Not production-ready
```

## 34.2 Permitted Claims After Successful Completion

AuraGateway may claim:

- deterministic static-prefix construction;
- typed static/volatile context boundaries;
- prefix mutation and volatile-leak detection;
- provider-aware telemetry normalization;
- machine-enforced telemetry sufficiency;
- fixed retrieval and task-quality evaluation;
- cache-affinity routing under explicit policy;
- blinded quality adjudication;
- paired A/B/C results under named conditions;
- practical uncertainty reporting;
- feedback-evidence trace review;
- privacy-safe metadata traces;
- one-command report reproduction.

## 34.3 Forbidden Claims

AuraGateway may not claim:

- guaranteed provider cache hits;
- direct GPU KV-cache visibility;
- exact provider TTL or eviction behaviour;
- universal cost or latency savings;
- production readiness;
- customer-data validation;
- complete EFC measurement;
- provider billing equivalence;
- broad provider ranking;
- automatic safe routing for arbitrary workloads;
- Coinbase-scale infrastructure or results.

---

# 35. Final Deliverables

## 35.1 Code

```text
Typed contracts
Retrieval core
Context compiler
Prefix fingerprint and mutation audit
Provider adapters
Telemetry normalizer
Telemetry sufficiency gate
Cache-affinity policy
Feedback-evidence evaluator
Comparison eligibility gate
Benchmark runner
Report generator
Tests and fixtures
```

## 35.2 Evaluation Assets

```text
Synthetic corpus and manifest
Development retrieval cases
Held-out retrieval cases
Functional multi-turn episodes
Runtime microbenchmark episodes
Blinded quality rubric
Benchmark constitution
Evaluation manifest
Pricing schedule
Provider fixtures
```

## 35.3 Evidence Vault

```text
Retrieval scorecard
Chunking comparison
Dense versus sparse comparison
Prefix-stability audit
Prefix negative-control calibration
Telemetry fixture report
Route-decision report
Quality and adjudication report
EFC evidence report
Fault-injection report
A/B/C functional benchmark
A/B/C runtime microbenchmark
Cold/warm comparison
Failure taxonomy report
Sanitized trace samples
Before/after tables
Artifact hash manifest
```

## 35.4 Documentation

```text
README
Ten ADRs
Benchmark constitution
Runbook
Privacy and vendor-boundary note
Evaluation manifest
Technical case study
Skeptical-reviewer guide
Ten-minute demo script
Known limitations
Formal handover
```

---

# 36. Demo and Reviewer Experience

The ten-minute demo should show:

1. configuration validation;
2. a stable prefix retaining the same fingerprint;
3. a deliberate mutation being rejected;
4. a warm route being preserved;
5. an unjustified route change being labelled route thrash;
6. missing telemetry blocking a cache claim;
7. a cheaper run failing the quality guardrail;
8. one-command generation of the final report.

The skeptical-reviewer guide must explain:

- where manifests live;
- how configuration fingerprints are built;
- how failed and excluded runs are retained;
- how review blindness works;
- how claims are machine-limited;
- how reports are reproduced;
- what the project does not prove.

---

# 37. Final Acceptance Statement

AuraGateway v2 is complete when a skeptical senior AI engineer can inspect the repository and conclude:

> “This project does not merely claim that prompt caching and cache-aware routing are useful. It fixes a retrieval-agent workload, freezes the benchmark before measured runs, separates stable from volatile context, validates prefix determinism with negative controls, preserves provider telemetry semantics, tests cache-affinity routing through paired A/B/C comparisons, protects task quality with blinded evaluation, retains failed runs, rejects invalid comparisons, and reproduces its conclusions from immutable evidence.”

That is the standard.

---

# 38. Evidence Basis

AuraGateway treats provider cache telemetry as provider-specific and requires implementation-time verification against current provider documentation and fixtures. Cache fields, thresholds, TTLs, pricing, invalidation behaviour, and retention assumptions must remain provider/model-specific.

The project takes direct architectural inspiration from Mark Landgrebe’s description of Coinbase’s internal AI gateway: stable exact-match prefixes, cheaper defaults, cache-aware routing, warm-route preservation, TTL-based rerouting, redaction, logging, failover, and cost controls. AuraGateway does not claim to reproduce Coinbase’s system or results.

Effective Feedback Compute is used as a trace-level evaluation doctrine. Value comes from feedback that is valid, non-redundant, retained, action-changing, and sufficient for the task—not from raw token volume, retries, tool calls, or agent steps.

The benchmark’s strongest claim is conditional and local:

> Under the named workload, provider/model, frozen configuration, and benchmark constitution, the tested runtime policy produced the reported cost, latency, quality, routing, and feedback-evidence outcomes.

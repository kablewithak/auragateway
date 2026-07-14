# AuraGateway — Session Brief
## Current Session Mission Order, Benchmark Integrity, and Evidence Control

> Paste this file into every new AuraGateway working session after the current project handover or continuity checkpoint.
>
> This is a **session-specific** document. Update only the sections relevant to the current session, active proof gate, and frozen experiment state.
>
> This brief is aligned to `AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md` version `2.2.0`, the terminal evidence amendment to the 200-hour design baseline.
>
> AuraGateway is a standalone advanced AI reliability systems lab. It is a Week 3 companion project only. It is **not** part of the AI consultancy roadmap’s core capstones, does not replace Week 3 requirements, and must not become a hidden dependency of the consultancy proof repository.

---

# Terminal Continuity State — PRD 2.2.0

This state is fixed unless a new, separately authorized project phase changes it.

```text
core runtime and evaluation harness: implemented
terminal evidence review: complete
Gate 4 telemetry contract integrity: passed
Gate 4 live numeric evidence sufficiency: closed unavailable
measured A/B/C comparison: not completed
provider cache usage measured: false
provider cache savings measured: false
core scope: closed
maturity: production-shaped, locally validated, synthetic-corpus validated,
          fixed-eval validated, controlled-provider tested
deployed: false
customer-data tested: false
production-ready: false
```

Permitted terminal claim:

```text
For the two authorized raw-wire calls, Groq omitted
usage.prompt_tokens_details.cached_tokens from both raw responses.
```

Permanent blocked claims:

```text
provider cache hit or miss
cached tokens equal zero
measured provider cache usage
measured provider cache savings
completed A/B/C benchmark result
universal cost or latency savings
production readiness
```

No identical provider rerun, resume, additional provider execution, or execution-evidence mutation is
permitted on the closed evidence path.

The next phase is `hugging_face_publication_layer_design`. It is a separate static publication
adapter and must not introduce live inference, credentials, customer data, or protected provider
payloads.

---

# 0. Project Identity and Operating Boundary

## Project

```text
AuraGateway v2 — Cache-Aware Agent Runtime and Evaluation Harness
```

## North Star

> AuraGateway proves, through a reproducible and controlled multi-turn retrieval-agent benchmark, whether deterministic context construction and cache-affinity routing reduce avoidable prefill work, latency, and estimated cost while preserving retrieval quality, grounded task success, structured-output validity, and useful feedback retention under fixed provider, model, and evaluation conditions.

## Plain-English North Star

> AuraGateway tests whether an AI assistant can reuse the parts of its context that have not changed and avoid unnecessarily switching models during a conversation, so it spends less time and money repeating work without becoming less accurate, less reliable, or worse at completing the task.

## Project Classification

```text
Standalone advanced AI reliability systems lab
```

## Roadmap Relationship

```text
Week 3 companion project only.

It may borrow retrieval, token-budget, context-assembly, provider-boundary,
prompt-cache, KV-cache, routing, evaluation, and EFC concepts.

It must not replace roadmap Week 3 gates.
It must not be treated as a consultancy core capstone.
It must not create a dependency on the primary consultancy proof repository.
```

## Direct Inspiration

```text
Mark Landgrebe, Senior Staff Software Engineer at Coinbase:
- exact-prefix caching;
- long stable prefixes across turns;
- cheaper model defaults;
- cache-aware session routing;
- preserving a model while cache state remains warm;
- TTL-based route reconsideration;
- gateway-level redaction, logging, failover, and cost controls.

AuraGateway tests a bounded version of the underlying engineering hypothesis.
It does not reproduce Coinbase infrastructure, scale, or results.
```

## Current Maturity Label

Choose one:

```text
Prototype
Production-shaped
Locally validated
Synthetic-corpus validated
Benchmark-constitution validated
Diagnostic-eval validated
Fixed-eval validated
Controlled-provider validated
Customer-data tested
Deployed
Production-ready
```

Selected label:

```text
Production-shaped
Locally validated
Synthetic-corpus validated
Fixed-eval validated
Controlled-provider tested
Not customer-data tested
Not deployed
Not production-ready
```

## Permanent Claim Boundary

AuraGateway may measure:

```text
- deterministic static-prefix construction;
- prefix mutation and volatile-content leakage;
- provider-reported cache telemetry where available;
- locally inferred prompt-evaluation timing where available;
- cache-affinity route decisions and route preservation;
- retrieval and task-quality outcomes;
- paired A/B/C runtime differences only when comparison eligibility passes;
- terminal negative results when required evidence is unavailable;
- trace-level feedback validity, novelty, retention, action change, and sufficiency;
- comparison eligibility under frozen configuration fingerprints;
- estimated cost only under a named, versioned pricing schedule.
```

For the closed v2 provider path, paired A/B/C measurement and cache-savings claims are not permitted.

AuraGateway must not claim:

```text
- guaranteed provider cache hits;
- direct provider GPU KV-cache visibility;
- guaranteed cache residency, TTL, eviction, or provider scheduling behavior;
- universal cost or latency savings;
- broad provider performance rankings;
- universal or complete EFC scoring;
- production readiness;
- customer-data readiness;
- Coinbase-scale infrastructure or Coinbase-scale results.
```

---

# 1. Session Mode

Choose the main mode for this session:

- Build
- Debug / Refactor
- Eval / Harness
- Agent
- RAG
- Roadmap / Learning
- Business Translation
- Teaching
- Documentation
- Handover

Selected mode:

```text
Documentation
```

Secondary mode, if any:

```text
Handover
```

---

# 2. Current Project Position

## Active Phase

Choose one:

```text
Phase 0 — Design Freeze and Benchmark Constitution
Phase 1 — Corpus, Retrieval, and Eval Asset Construction
Phase 2 — Typed Contracts and Context Compiler
Phase 3 — Provider Adapters and Telemetry Calibration
Phase 4 — Cache-Affinity Controller and Trajectory Regulation
Phase 5 — Quality, Feedback Evidence, and Blinded Adjudication
Phase 6 — Fault Injection, Meta-Harness, and Reproducibility
Phase 7 — Benchmark Execution and Statistical Analysis
Phase 8 — Reporting, Case Study, Demo, and Handover
Post-implementation — Maintenance, Revalidation, or Commercial Translation
```

Selected phase:

```text
Post-implementation — Maintenance, Revalidation, or Commercial Translation
```

## Hours Completed

```text
Historical design allocation: 200 hours
Core evidence scope: closed
Hours are no longer the release gate; evidence and publication acceptance criteria govern next work
```

## Current Active Proof Gate

Choose the one being advanced:

```text
Gate 0 — Benchmark Constitution
Gate 1 — Retrieval Readiness
Gate 2 — Diagnostic Eval Readiness
Gate 3 — Prefix Determinism
Gate 4 — Telemetry Integrity
Gate 5 — Route Policy
Gate 6 — Task-Quality Safety
Gate 7 — Feedback Evidence
Gate 8 — Fault and Privacy Controls
Gate 9 — Benchmark Execution
Gate 10 — Final Evidence Report
```

Selected proof gate:

```text
Gate 10 — Final Evidence Report: closed by terminal evidence review
```

## Current Experiment State

Choose one:

```text
Pre-freeze
Benchmark constitution drafting
Benchmark constitution frozen
Development retrieval tuning
Retrieval frozen
Diagnostic eval authoring
Diagnostic eval review
Evaluation manifest frozen
Prompt/static-anchor still editable
Prompt/static-anchor frozen
Telemetry fixture validation
Telemetry sufficiency validation
Live provider smoke validation
Negative-control calibration
Condition A active
Condition B active
Condition C active
Paired A/B/C execution active
Blinded adjudication active
Fault-injection validation
Comparison eligibility validation
Benchmark complete
Statistical analysis active
Report under review
Handover-ready
```

Selected state:

```text
Handover-ready
```

## Why This Session Matters

```text
Preserve the terminal negative result, prevent future A/B/C or cache-savings overclaims, and keep
the Hugging Face publication layer separate from the closed runtime.
```

## Current Benchmark Objective

```text
No benchmark execution is active. The evidence path is terminal because required numeric provider
cache telemetry was unavailable.
```

## Current Causal Contrast

Choose one:

```text
None — design, retrieval, shared infrastructure, or reporting session
A versus B — deterministic context construction only
B versus C — cache-affinity route policy only
A versus C — total system effect; not a single-mechanism causal claim
Negative control — deliberate stable-prefix mutation
Functional benchmark — task quality and policy correctness
Runtime microbenchmark — cache, prefill, TTFO, and cost evidence
```

Selected contrast:

```text
None — terminal reporting, handover, or static publication work only
```

---

# 3. Session Objective

## Primary Objective

```text
Maintain the closed core evidence state and implement the separate, sanitized Hugging Face
publication layer without changing runtime evidence or claims.
```

## Expected Output From the Assistant

Choose or describe:

```text
- implementation plan
- full replacement files
- repo file tree
- ADR
- benchmark constitution
- paired execution design
- eval design
- diagnostic case set
- retrieval scorecard design
- telemetry contract
- telemetry sufficiency gate
- routing-policy design
- comparison-eligibility contract
- negative-control design
- fault-injection suite
- blinded-adjudication protocol
- debugging diagnosis
- failure analysis
- benchmark report
- trace review
- evidence-bundle design
- one-command reproducibility workflow
- reviewer guide
- case-study draft
- demo script
- handover
- study explanation
- GitOps commands
```

Expected output:

```text

```

## Smallest Safe Slice

State the smallest deliverable that moves the active proof gate forward without changing unrelated frozen assets:

```text

```

## What Evidence Will Exist at the End of This Session?

```text

```

## Definition of Done for This Session

```text

```

---

# 4. Experiment Integrity and Freeze Status

> This section is mandatory for any session that changes retrieval, prompts, context packs, routing, provider behavior, telemetry, metrics, evaluation cases, adjudication rules, benchmark execution, statistical reporting, or comparison eligibility.

## Current Runtime Condition

Choose one:

```text
None — design or shared infrastructure session
A — Cache-Hostile Baseline
B — Prefix-Deterministic Runtime
C — Cache-Aware Agent Runtime
A/B/C comparison runner
Negative-control calibration
Functional benchmark runner
Runtime microbenchmark runner
```

Selected condition:

```text

```

## Intervention Under Test

State exactly one main intervention whenever a benchmark comparison is active:

```text

```

## Controlled Constants

These must remain fixed during the affected comparison unless the benchmark constitution declares a full rerun:

```text
- corpus manifest;
- chunking strategy;
- retrieval implementation;
- retrieval configuration;
- top-k;
- metadata-filter policy;
- prompt template ID and version;
- static context-pack ID and version;
- tool-contract version;
- output-schema version;
- development and held-out evaluation manifests;
- multi-turn episode manifest;
- task-quality rubric and thresholds;
- blinded-adjudication protocol;
- max turns;
- input and output budgets;
- provider/model capability tier;
- provider/model aliases;
- provider adapter version;
- runtime condition implementation version;
- route-policy version;
- benchmark runner version;
- run-order and counterbalancing policy;
- cold-start classification policy;
- retry, exclusion, and rerun rules;
- statistical reporting configuration;
- comparison-eligibility rules;
- pricing schedule version, if cost is reported.
```

Current controlled constants:

```text

```

## Freeze Status

| Asset | Status: Editable / Frozen / Not Applicable | Manifest, Version, or Hash | Evidence |
|---|---|---|---|
| Benchmark constitution |  |  |  |
| Corpus |  |  |  |
| Development retrieval cases |  |  |  |
| Held-out retrieval cases |  |  |  |
| Diagnostic multi-turn episodes |  |  |  |
| Functional benchmark subset |  |  |  |
| Runtime microbenchmark subset |  |  |  |
| Chunking strategy |  |  |  |
| Retrieval configuration |  |  |  |
| Prompt template |  |  |  |
| Static context pack |  |  |  |
| Tool contract |  |  |  |
| Output schema |  |  |  |
| Routing policy |  |  |  |
| Quality rubric |  |  |  |
| Blinded-adjudication protocol |  |  |  |
| Negative-control definitions |  |  |  |
| Fault-injection fixtures |  |  |  |
| Telemetry sufficiency rules |  |  |  |
| Pricing schedule |  |  |  |
| Benchmark runner |  |  |  |
| Statistical reporting configuration |  |  |  |
| Comparison-eligibility contract |  |  |  |
| Evidence-bundle schema |  |  |  |

## Allowed Changes This Session

```text

```

## Prohibited Changes This Session

```text

```

## Full Rerun Required If

```text
- any controlled constant changes;
- a held-out or diagnostic evaluation case changes after freeze;
- the benchmark constitution changes after benchmark execution begins;
- a prompt or static-anchor change alters the configured experiment;
- retrieval configuration changes after freeze;
- the provider/model capability tier or alias changes;
- a provider adapter changes telemetry meaning;
- the quality rubric, scorer, reviewer instructions, or acceptance threshold changes;
- a route-policy rule changes during comparison;
- negative-control or fault-injection definitions change after their gate closes;
- run-order, cold-start, retry, exclusion, or rerun rules change;
- statistical reporting rules change after results are inspected;
- the pricing schedule changes while cost comparison remains in scope;
- a configuration fingerprint mismatch is discovered between compared runs.
```

Additional rerun triggers:

```text

```

## Comparison Eligibility

```text
Eligible for comparison: yes / no / not yet evaluated
Mismatched fingerprint fields:
Invalidated claims:
Required reruns:
```

---

# 5. Benchmark Constitution and Run Control

## Constitution State

```text
Draft / under review / frozen / superseded / verify first
```

Selected state:

```text

```

## Paired Execution Identity

```text
comparison_pair_id strategy:
episode_id strategy:
replication_id strategy:
condition_id:
provider_model_alias:
benchmark_manifest_hash:
```

## Run Order and Counterbalancing

```text
Execution-order policy:
Counterbalancing method:
Provider-load drift control:
Time spacing between runs:
Randomization seed or deterministic schedule:
```

## Cold and Warm Classification

```text
Cold-start definition:
Warm-turn eligibility:
TTL assumption:
TTL source and date checked:
Ambiguous cache-state treatment:
```

## Retry, Exclusion, and Rerun Rules

```text
Retryable failures:
Non-retryable failures:
Maximum retries:
Ambiguous response-state handling:
Predeclared exclusion rules:
Rerun eligibility:
Whether failed runs remain in denominators:
```

## Statistical Reporting Configuration

```text
Primary summary statistics:
Paired-difference reporting:
Range / quartile reporting:
P90 reporting:
Bootstrap interval configuration:
Outlier reporting policy:
Success-only versus failure-inclusive views:
```

---

# 6. Cache Evidence and Provider State

## Primary Provider and Model

```text
Provider:
Model alias:
Exact model identifier:
Adapter path/version:
Documentation date checked:
```

## Secondary Provider or Fixture-Only Adapter

```text
Provider:
Model or fixture version:
Role:
Live or fixture-only:
```

## Local Ollama / Local Runtime State

```text
Installed / not installed:
Model:
Purpose:
Known local limitations:
```

## Cache Evidence Level for This Session

Choose one:

```text
Observed provider evidence
Inferred local evidence
Unavailable
Mixed — specify by provider/runtime
```

Selected level:

```text

```

## Provider Telemetry Fields Available

```text

```

## Provider Telemetry Fields Unavailable or Semantically Uncertain

```text

```

## Telemetry Sufficiency

```text
Cache claim permitted: yes / no / not evaluated
Latency claim permitted: yes / no / not evaluated
Cost claim permitted: yes / no / not evaluated
Unavailable required fields:
Reasons:
```

## Cache TTL Assumptions

```text
Provider TTL or retention assumption:
Source:
Date checked:
Known uncertainty:
```

## Pricing Schedule

```text
Pricing schedule version:
Pricing source date:
Estimated or provider-reported:
Cache read/write pricing available:
```

## Prefix Negative-Control Calibration

```text
Calibration status: not started / passed / failed / inconclusive
Stable-prefix run evidence:
Controlled mutation used:
Mutated-prefix run evidence:
Telemetry sensitivity conclusion:
Claims still permitted:
```

## Required Evidence Language

Use only one of these when reporting cache behavior:

```text
Observed provider cache evidence:
The provider explicitly returned cache-related usage fields.

Inferred local cache evidence:
A controlled local runtime showed timing behavior consistent with warm/cold
prefill reuse. This does not prove provider-style cached-token counts.

Cache evidence unavailable:
The current provider/runtime did not expose enough trustworthy telemetry to
support a cache-efficiency claim.
```

---

# 7. Current Repo / Workspace Context

Repo name:

```text

```

Local repo path:

```text

```

Current branch:

```text

```

Latest known Git status:

```text

```

Latest known commit or PR state:

```text

```

Virtual environment or setup notes:

```text

```

Known commands that already passed:

```text

```

Known commands that failed:

```text

```

Current relevant package or module paths:

```text

```

Current data / evidence paths:

```text

```

Current frozen manifests:

```text

```

Current untracked or local-only artifacts that must be preserved:

```text

```

---

# 8. Benchmark Configuration Fingerprint

> Complete this section once benchmarked evidence exists. Do not invent values.

```text
Benchmark constitution version/hash:
Corpus manifest hash:
Retrieval configuration hash:
Prompt template ID and version:
Static context-pack ID and version:
Tool-contract version:
Output-schema version:
Development-eval manifest hash:
Held-out-eval manifest hash:
Diagnostic-episode manifest hash:
Functional benchmark subset hash:
Runtime microbenchmark subset hash:
Quality rubric version:
Blinded-adjudication protocol version:
Negative-control manifest hash:
Fault-injection fixture hash:
Telemetry-sufficiency rules version:
Route-policy version:
Benchmark runner version:
Statistical reporting configuration version:
Comparison-eligibility contract version:
Evidence-bundle schema version:
Pricing schedule version:
Provider/model alias:
Provider adapter version:
Python version:
Dependency lock hash/version:
Git commit hash:
```

Benchmark namespace controls:

```text
cache_namespace_id strategy:
session_id_hash policy:
run_id format:
comparison_pair_id format:
replication_id format:
condition ID:
```

Cold-start handling:

```text
How cold-start turns are separated from warm-turn reporting:
```

Comparison result:

```text
Comparison eligible: yes / no / not evaluated
Mismatches:
Invalidated metrics or claims:
```

---

# 9. Evaluation, Adjudication, and Evidence State

## Diagnostic Case State

```text
Development cases complete:
Held-out retrieval cases complete:
Diagnostic multi-turn episodes complete:
Cases accepted:
Cases rejected:
Acceptance/rejection reasons stored:
Evaluation manifest state:
```

## Scoring Boundary

Deterministic checks:

```text

```

Rubric-based checks:

```text

```

## Blinded Adjudication

```text
Protocol version:
Opaque review-ID method:
Reviewer count:
Double-review percentage:
Disagreement-resolution rule:
Reviewer condition visibility:
Rubric freeze status:
```

## Functional Benchmark State

```text
Not started / partial / complete / invalidated
Episode count:
Repetitions:
Task-quality result state:
Known failures:
```

## Runtime Microbenchmark State

```text
Not started / partial / complete / invalidated
Episode subset count:
Repetitions:
Cold/warm reporting state:
Known failures:
```

## Negative Controls and Fault Injection

```text
Prefix mutation controls:
Telemetry semantic controls:
Route-thrash controls:
Retrieval/stale-source controls:
Feedback retention controls:
Privacy trace-rejection controls:
Cross-condition isolation controls:
Fault suite status:
```

## Evidence Bundle State

```text
Run bundle path:
Manifest path:
Results JSONL path:
Failures JSONL path:
Comparison CSV path:
Benchmark report path:
Sanitized trace path:
Artifact hash manifest path:
Bundle immutable: yes / no / not yet
```

---

# 10. Files and Evidence Available

Files uploaded or pasted for this session:

```text

```

Files that are source of truth:

```text
1. AuraGateway v2 PRD version 2.2.0
2. Relevant AuraGateway ADRs
3. Frozen benchmark constitution
4. Corpus, retrieval, and evaluation manifests
5. Frozen prompt, context-pack, tool-contract, and output-schema versions
6. Current provider documentation and pricing references
7. Latest validated evidence bundle, benchmark report, and sanitized traces
8. This SESSION_BRIEF.md
9. Terminal output, logs, screenshots, and test evidence provided in this session
```

Current source-of-truth files:

```text

```

Files that may be stale or must not be trusted:

```text

```

Files that must not be inspected for the active task:

```text

```

Terminal output, logs, screenshots, or test evidence already provided:

```text

```

Missing evidence the assistant must request before making a confident claim:

```text

```

---

# 11. Constraints and Workflow Preferences

## Permanent Technical Constraints

```text
- Local-first, repo-first, provider-neutral, and testable.
- Python 3.11+ with type hints and Pydantic v2.
- pytest, Ruff, mypy, structured JSON logs, explicit error taxonomy, and trace IDs/run IDs.
- No vague dict-passing across core boundaries.
- No direct provider SDK objects outside provider adapters.
- No raw prompts, raw documents, raw model outputs, PII, secrets, or unbounded metadata in traces.
- No blanket exceptions.
- Timeouts, bounded retries, and explicit retryability where external I/O exists.
- No ambiguous automatic duplicate generation after uncertain provider response state.
- No cloud infrastructure unless explicitly requested for a later deployment scope.
- No production-readiness claim without proven deployment, monitoring, security,
  incident response, load behavior, and operational ownership.
```

## Permanent Experiment Constraints

```text
- Freeze the benchmark constitution before measured execution.
- Use paired and counterbalanced A/B/C execution.
- Keep A versus B limited to context-construction policy.
- Keep B versus C limited to cache-affinity route policy.
- Treat A versus C as total system effect, not a single-mechanism causal claim.
- Do not use held-out or diagnostic cases to tune retrieval, prompts, routing, metrics, or thresholds.
- Do not change controlled constants during an active comparison.
- Do not compare runs with different configuration fingerprints.
- Do not compare conditions with different corpus, retrieval setup, output schema,
  task budget, quality rubric, provider/model tier, or adjudication protocol.
- Keep functional and runtime benchmark purposes distinct.
- Blind rubric-based task-quality review to runtime condition.
- Retain failed runs, excluded runs, provider errors, outliers, and rerun reasons.
- Apply only predeclared exclusion and rerun rules.
- Separate cold and warm turns.
- Do not present inferred local timing as observed provider cache-token evidence.
- Do not report cache ratios when provider semantics or denominators are unknown.
- Do not optimize cost by allowing lower task quality, unsupported answers, unsafe retry,
  premature escalation, or incapable-model routing.
- Do not claim improvement unless comparison eligibility and quality gates pass.
```

## User Workflow Preferences

```text
- Treat “excellent work,” “what’s next?”, and “take it away” as confirmation that all
  prior instructions have been completed and the next operational response is wanted.
- Prefer one complete operational response for implementation slices:
  branch/current state → one complete source/test ZIP to Downloads → exact PowerShell
  unzip-and-copy commands → Git status → validation/tests → Git add/status/commit/push
  → GitHub-safe PR description → one after-merge sync/delete block.
- Provide full-file replacements rather than patches unless explicitly requested otherwise.
- Use copy-paste-safe Windows PowerShell commands.
- Do not repeat Set-Location when the user is already in the repo root.
- Keep validation before Git add/commit/push.
- Use one pytest command per line.
- After every git add, include git status before git commit.
- Include after-merge sync/delete instructions as one complete PowerShell-only block.
- Use Desktop ZIPs for user-to-assistant multi-file context bundles.
- Do not create formal handovers mid-slice.
- Do not invent branch names, repo state, test results, hashes, provider evidence, or benchmark results.
```

## Session-Specific Constraints

```text

```

## Preferred Output Format

```text

```

---

# 12. What Must Not Be Done

Do not do the following in this session:

```text
- Do not introduce a third live provider unless the active proof gate explicitly requires it.
- Do not add dashboards, billing, authentication, generic proxy compatibility,
  cloud deployment, production failover, vector database migration, multi-agent scope,
  fine-tuning, arbitrary Jinja execution, or a universal EFC scoring dashboard.
- Do not make the API gateway application part of the critical path unless explicitly approved.
- Do not change frozen evaluation assets or controlled constants without declaring reruns.
- Do not tune prompts, context packs, routing, quality thresholds, or statistical rules using held-out results.
- Do not inspect condition identity during blinded rubric review.
- Do not decide exclusions or reruns after seeing whether they improve the result.
- Do not compare runs with mismatched configuration fingerprints.
- Do not call a stable prefix hash proof of provider cache reuse.
- Do not call provider cache evidence proof of direct GPU KV-cache visibility.
- Do not claim universal cost savings, latency improvement, or production behavior.
- Do not log raw prompts, raw user messages, raw retrieved documents, raw model outputs,
  raw provider payloads, secrets, direct user identifiers, or unrestricted metadata.
- Do not use fake telemetry values such as zero when the correct value is unknown.
- Do not proceed from implementation evidence to benchmark claims without fixed evaluation evidence.
- Do not move to the next phase without the active proof gate’s required evidence.
- Do not overwrite or delete failed, anomalous, or excluded run evidence.
```

Additional session-specific prohibitions:

```text

```

---

# 13. Acceptance Criteria

## Session Acceptance Criteria

This session is successful only if:

```text

```

## Active Proof-Gate Requirements

Select the relevant requirements.

### Gate 0 — Benchmark Constitution

```text
- Primary causal contrasts are explicit.
- Controlled constants are enumerated.
- Paired and counterbalanced run order is defined.
- Cold/warm classification is defined.
- Retry, exclusion, and rerun rules are predeclared.
- Failed-run denominator treatment is explicit.
- Statistical reporting is defined before results are inspected.
- Constitution version/hash is frozen before measured execution.
```

### Gate 1 — Retrieval Readiness

```text
- Two chunking strategies are compared.
- Dense and sparse retrieval are compared.
- Recall@k, Precision@k, MRR, stale-source rate, and metadata violations are reported.
- Final retrieval configuration is selected and frozen.
- Held-out retrieval cases are not used for tuning.
```

### Gate 2 — Diagnostic Eval Readiness

```text
- Hard diagnostic multi-turn cases cover named failure hypotheses.
- Each case defines required sources, forbidden sources, expected decision, and failure labels.
- Ambiguous, trivial, duplicate, and non-diagnostic cases are rejected.
- Accept/reject reasons are stored.
- Functional and runtime benchmark subsets are declared.
- Evaluation manifests are frozen.
```

### Gate 3 — Prefix Determinism

```text
- Five controlled turns preserve the same static-anchor fingerprint.
- Volatile append changes do not mutate the static fingerprint.
- Timestamp insertion into static context fails.
- Tool-order mutation fails.
- Output-schema mutation fails.
- Prefix negative-control calibration is executed and interpreted.
```

### Gate 4 — Telemetry Integrity

```text
- Provider telemetry fixtures map into typed contracts.
- Unknown values remain None.
- Provider-specific cache fields remain semantically distinct.
- Local timing evidence remains separate from provider-reported cached tokens.
- Telemetry sufficiency explicitly permits or blocks cache, latency, and cost claims.
- Raw provider payloads remain inside adapter boundaries.
```

### Gate 5 — Route Policy

```text
- Warm session preserves an eligible active route.
- TTL expiry permits route re-evaluation.
- Provider failure produces typed reroute with explicit reason.
- Capability, safety, and quality reasons are enforced.
- No route thrash occurs in fixed fixtures.
- Every route change has an allowed reason code.
```

### Gate 6 — Task-Quality Safety

```text
- Deterministic scoring checks are implemented.
- Rubric-based scoring criteria are explicit and frozen.
- Rubric review is blinded to condition.
- Double-review and disagreement rules are implemented.
- Structured-output validity remains at or above 95%.
- Citation support does not regress.
- Unsupported-answer rate does not increase.
- Task success remains within the non-inferiority boundary.
- Retrieval configuration remains unchanged across conditions.
```

### Gate 7 — Feedback Evidence

```text
- Valid/new/retained feedback is visible.
- Valid/redundant feedback is visible.
- Invalid feedback is visible.
- Valid/unretained feedback is visible.
- At least one feedback event changes a later action.
- At least one trace is task-sufficient.
- No universal EFC score is invented.
```

### Gate 8 — Fault and Privacy Controls

```text
- Prefix mutation and volatile leak injections fail safely.
- Telemetry semantic mismatches are detected.
- Route thrash is detected.
- Stale-source and retrieval failures are surfaced.
- Repeated and unretained feedback is classified.
- Cross-condition cache namespace contamination is detected.
- Trace writer rejects raw prompts, documents, outputs, PII, and secrets.
- Metamorphic invariants pass.
```

### Gate 9 — Benchmark Execution

```text
- Functional and runtime benchmarks are run under the frozen constitution.
- A/B/C runs are paired and counterbalanced.
- Cold and warm turns are separated.
- Per-run results, failures, exclusions, and reruns are retained.
- Compared runs pass configuration-fingerprint eligibility.
- Paired differences, medians, ranges, quartiles, P90, and uncertainty intervals are reported as configured.
- Quality non-inferiority gates are evaluated before savings claims.
```

### Gate 10 — Final Evidence Report

```text
- Machine-readable result bundle exists.
- Markdown and CSV comparison reports exist.
- Failure taxonomy and residual risks are documented.
- Provider-reported and inferred evidence are separated.
- Negative and inconclusive results remain reportable.
- Artifact hashes and immutable evidence bundle exist.
- One-command validation, run, and report workflows are documented.
- Reviewer guide, case study, demo script, claims, and non-claims are complete.
```

## Minimum Verification Required

```text

```

## Current Permitted Claim

```text

```

## Current Evidence Level

```text
Observed provider evidence / inferred local evidence / unavailable / mixed
```

Selected evidence level:

```text

```

## Current Comparison Eligibility

```text
Eligible / ineligible / not yet evaluated
```

Selected:

```text

```

## Non-Claims for This Session

```text

```

---

# 14. Commercial Translation — Optional and Evidence-Subordinate

> Do not force commercial language into a session whose primary work is benchmark integrity, retrieval correctness, telemetry semantics, fault controls, or safety.

Selected offer:

```text
None — standalone proof project
AI System Evaluation Audit
Context, Cache, and Agent Runtime Efficiency Audit
RAG Reliability Improvement Sprint
Agent Harness Hardening Sprint
AI Reliability Pilot
AI Reliability Retainer
Other
```

Selected offer:

```text

```

Buyer pain addressed:

```text

```

Proof asset this session creates or improves:

```text

```

Commercial claim permitted today:

```text

```

How this could become sellable later:

```text

```

Acceptance criteria a future buyer could understand:

```text

```

---

# 15. Open Questions and Known Uncertainty

## Questions the Assistant Should Answer

```text

```

## Questions the Assistant Should Ask Before Proceeding

```text

```

## Known Technical Uncertainty

```text

```

## Provider / Cache Uncertainty

```text

```

## Experiment / Evaluation Uncertainty

```text

```

## Adjudication / Statistical Uncertainty

```text

```

## Decision Needed Before the Next Slice

```text

```

---

# 16. Instruction to Assistant

Use the following source hierarchy.

```text
1. AuraGateway v2 PRD version 2.2.0
2. Relevant AuraGateway ADRs
3. Frozen benchmark constitution
4. Corpus, retrieval, evaluation, negative-control, and fault-injection manifests
5. Frozen prompt, context-pack, tool-contract, output-schema, and route-policy versions
6. Provider documentation and versioned pricing sources
7. Latest validated immutable evidence bundle and reports
8. This SESSION_BRIEF.md
9. Terminal output, logs, screenshots, and test evidence provided in this session
```

The wider AI consultancy roadmap may be used only as background learning context. It is not the architecture, implementation, or evidence source of truth for AuraGateway.

## Assistant Operating Rules

```text
- Respect the selected session mode.
- Treat the active proof gate as the immediate definition of done.
- Preserve benchmark and experiment integrity before optimizing implementation speed.
- Do not infer or invent repo state, branch names, hashes, test outputs, benchmark results,
  provider cache behavior, telemetry semantics, statistical conclusions, or production readiness.
- Ask for the smallest concrete missing input only when it is required for correctness.
- When enough evidence exists, proceed without unnecessary reconfirmation.
- Use schema-first interfaces, typed errors, deterministic contracts, and explicit evidence boundaries.
- Keep raw prompts, raw documents, raw outputs, raw provider payloads, PII, and secrets out of logs and traces.
- Treat local timing as inferred evidence unless the runtime directly exposes valid provider cache telemetry.
- Enforce telemetry sufficiency before allowing cache, latency, or cost claims.
- Refuse comparisons when controlled configuration fingerprints differ.
- Keep A versus B, B versus C, and A versus C interpretations distinct.
- Apply only predeclared retry, exclusion, rerun, and statistical rules.
- Preserve failed runs, anomalies, outliers, exclusions, and rerun reasons.
- Keep rubric review blinded to condition.
- Do not call a cost or latency result successful unless task-quality non-inferiority passes.
- Do not optimize raw token count, retries, tool calls, or agent steps in isolation.
  Evaluate whether feedback was valid, non-redundant, retained, action-changing, and sufficient.
- When code changes are requested, use the user’s required operational workflow:
  branch/current state → one ZIP to Downloads → exact PowerShell copy commands → Git status
  → validation → Git add/status/commit/push → PR description → one after-merge sync/delete block.
- For debugging or refactoring without enough evidence, state exactly:
  “PREMISE FAILURE: Missing context. Please provide: [specific files/functions/stack traces/test output/logs].”
```

---

# 17. Session Completion Record

> Complete this section before handing over or starting a new session.

## What Changed

```text

```

## What Was Verified

```text

```

## What Failed or Remains Risky

```text

```

## Benchmark / Freeze Impact

```text

```

## Comparison Eligibility Impact

```text

```

## Evidence Bundle Impact

```text

```

## Permitted Claim After This Session

```text

```

## Non-Claims That Still Apply

```text

```

## Hours Ledger Update

```text
Hours before session:
Hours spent this session:
Hours completed after session: ___ / 200
Remaining hours:
```

## Next Safest Slice

```text

```

## Handover Trigger

```text
No handover / lightweight continuity checkpoint / formal handover
```

Selected:

```text

```

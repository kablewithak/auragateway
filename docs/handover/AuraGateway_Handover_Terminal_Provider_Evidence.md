# AuraGateway Project Handover
## Terminal Provider Evidence — Groq and OpenRouter/Hy3 Closed Lineages

| Field | Current value |
|---|---|
| Handover status | Formal terminal continuity checkpoint |
| Date | 2026-07-14 |
| Repository | `kablewithak/auragateway` |
| Local repository | `C:\Users\kabom\Documents\Machine Learning\Machine Learning Workspace\auragateway` |
| Source branch state | `main`, clean at terminal-review inspection |
| Source terminal merge | `00d0712` — PR #61 OpenRouter Hy3 capability closeout |
| Governing core PRD | `AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md` 2.3.0 |
| Governing Hy3 mini PRD | `AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md` 1.1.0 |
| Core state | Closed with negative Groq provider telemetry |
| Hy3 extension state | Closed before successful inference after HTTP 401 |
| A/B/C state | Not authorized and not completed |
| Current maturity | Production-shaped, locally validated, synthetic/fixed-eval validated, controlled-provider tested; not deployed or production-ready |
| Next optional phase | Static Hugging Face publication integration |

---

# 1. Executive Summary

AuraGateway v2 is a local-first, typed, provider-aware cache-aware agent runtime and evaluation
harness. Its North Star was to test whether deterministic context construction and cache-affinity
routing could reduce avoidable repeated prompt work, latency, or estimated cost without degrading
retrieval quality, grounded task success, schema validity, routing safety, or useful feedback
retention.

The runtime, contracts, retrieval assets, context compiler, cache-affinity policy, evals, negative
controls, comparison gates, and evidence harness were implemented. The measured A/B/C benchmark was
not executed because the required live provider cache evidence never became eligible.

Two independent provider lineages reached terminal results.

## Groq lineage

```text
authorized raw-wire calls: 2
successful responses: 2
required cached-token field: absent from both raw responses
cache evidence: unavailable
terminal action: close lineage and block A/B/C
```

## OpenRouter/Hy3 lineage

```text
requested model: tencent/hy3:free
metadata-only preflight: passed
live cold attempts: 1
successful completions: 0
HTTP status: 401
safe failure: PROVIDER_AUTHENTICATION_FAILED
generation metadata requested: false
warm call attempted: false
cache telemetry observed: false
authorization consumed: true
resume or rerun: prohibited
terminal action: close capability path and block pilot
```

The combined result is not a measured cache-performance result. It is a reliability result:

> AuraGateway refused to manufacture a cache, savings, routing, or latency conclusion when the
> required provider evidence was absent or never reached.

---

# 2. Project Identity and North Star

```text
project: AuraGateway v2 — Cache-Aware Agent Runtime and Evaluation Harness
classification: standalone advanced AI reliability systems lab
roadmap relationship: Week 3 companion project only
core design allocation: 200 hours
provider extension: separate OpenRouter/Hy3 capability lineage
architecture: local-first, typed, provider-neutral, eval-driven, privacy-safe
```

Formal North Star:

> AuraGateway proves, through a reproducible and controlled multi-turn retrieval-agent benchmark,
> whether deterministic context construction and cache-affinity routing reduce avoidable prefill work,
> latency, and estimated cost while preserving retrieval quality, grounded task success,
> structured-output validity, and useful feedback retention under fixed provider, model, and
> evaluation conditions.

Plain-English North Star:

> AuraGateway tests whether an AI assistant can reuse the parts of its context that have not changed
> and avoid unnecessarily switching models during a conversation, so it spends less time and money
> repeating work without becoming less accurate or reliable.

The North Star remains a design hypothesis. The measured runtime comparison was not evidence-eligible.

---

# 3. Direct Inspiration and Claim Boundary

The architectural inspiration is Mark Landgrebe’s description of Coinbase’s internal AI gateway:

```text
cheaper-model defaults
exact-prefix caching
long stable prefixes
cache-aware session routing
warm-route preservation
TTL-based route reconsideration
redaction, logging, failover, and cost controls
```

AuraGateway does not reproduce Coinbase infrastructure, scale, economics, deployment, or results.

Permanent non-claims:

```text
guaranteed provider cache hits
direct GPU KV-cache visibility
exact provider TTL or eviction behavior
universal cost or latency savings
broad provider rankings
production readiness
customer-data readiness
complete universal EFC scoring
```

---

# 4. Current Repository State

Latest source terminal evidence supplied by the user:

```text
On branch main
Your branch is up to date with 'origin/main'.

nothing to commit, working tree clean

00d0712 (HEAD -> main, origin/main, origin/HEAD)
Merge pull request #61 from kablewithak/feat/openrouter-hy3-capability-probe-closeout
```

This handover is created by a later documentation PR. The next LLM must verify the actual current
`HEAD` and must not assume `00d0712` remains latest.

Orientation:

```powershell
Set-Location "C:\Users\kabom\Documents\Machine Learning\Machine Learning Workspace\auragateway"

git status
git --no-pager log -1 --oneline
python --version
python -m ruff --version
```

Known local lint authority at closeout:

```text
Ruff 0.15.21
```

---

# 5. Core Architecture Status

Implemented production-shaped boundaries include:

```text
Pydantic v2 typed contracts
synthetic Nimbus Relay corpus
sparse and dense retrieval boundaries
chunking and retrieval evaluation assets
deterministic static-anchor and volatile-append compiler
HMAC/static-prefix fingerprinting
prefix mutation and volatile-leak detection
provider-neutral inference contracts
Groq, OpenRouter, fake, and local-runtime adapters
provider-specific telemetry normalization
telemetry sufficiency gate
cache-affinity session route state and policy
structured-output and citation validation
feedback-evidence traces
fault injection and metamorphic tests
configuration fingerprints and comparison eligibility
append-only protected evidence
sanitized terminal closeout generation
```

This is production-shaped, not production-ready.

---

# 6. Gate Status

```text
Gate 0 — Benchmark Constitution: passed
Gate 1 — Retrieval Readiness: passed
Gate 2 — Diagnostic Eval Readiness: passed
Gate 3 — Prefix Determinism: passed
Gate 4A — Telemetry Contract Integrity: passed
Gate 4B — Groq Live Numeric Evidence: closed unavailable
Gate 4C — OpenRouter/Hy3 Capability Evidence: closed before successful inference
Gate 5 — Route Policy: fixed-fixture validated
Gate 6 — Task-Quality Safety: implementation/fixed-eval validated
Gate 7 — Feedback Evidence: implementation/fixed-eval validated
Gate 8 — Fault and Privacy Controls: validated
Gate 9 — Measured A/B/C Benchmark Execution: not authorized
Gate 10 — Terminal Evidence Report: complete
```

Comparison eligibility:

```text
eligible: false
reason: no closed provider lineage produced eligible numeric cache evidence
required reruns: none under current lineages
rerun permitted: false
```

---

# 7. Groq Terminal Evidence

## Path

The Groq path progressed through:

```text
initial telemetry calibration
SDK cache-schema compatibility review
raw-wire reauthorization review
one-time activation
protected raw-wire execution
closeout
core terminal evidence review
```

## Result

Both authorized raw HTTP calls returned successful model responses. The required field:

```text
usage.prompt_tokens_details.cached_tokens
```

was absent from both raw responses.

## Meaning

Permitted:

> The field was absent from the two observed successful responses.

Blocked:

```text
cache miss
cache hit
zero cached tokens
provider cache usage measured
provider cache savings measured
universal omission behavior
```

## Why no more calls

There was no changed contract, route, request structure, provider documentation, or new hypothesis that
gave a concrete reason to expect the missing field to appear. Additional identical calls would have
become evidence fishing.

The Groq lineage is immutable and closed.

---

# 8. OpenRouter/Hy3 Extension Design

The extension selected OpenRouter/Hy3 because:

```text
richer documented cache and generation telemetry: dominant immediate reason
explicit session identity for future affinity identifiability: strategic reason
free long-prefix route: practical enabler
```

The route/model distinction is:

```text
gateway provider and telemetry authority: OpenRouter
requested model configuration: tencent/hy3:free
upstream provider: observable only after successful generation metadata
```

OpenRouter telemetry must never be described as Tencent-direct telemetry.

---

# 9. OpenRouter/Hy3 Governance Path

The extension used four pre-execution governance stages:

```text
identifiability review
adapter dry run
capability authorization review
activation and metadata-only preflight
```

Then:

```text
execution-runner implementation PR
merge to clean main
one live execution
sanitized closeout PR
terminal continuity review
```

General doctrine:

> Irreversible provider actions require a separately reviewable artifact that freezes what the next
> action is allowed to do.

Governance depth scaled with:

```text
irreversibility
evidence value
call scarcity
privacy risk
failure cost
difficulty of rerunning
claim sensitivity
```

---

# 10. OpenRouter Adapter and Evidence Semantics

The generic adapter preserved:

```text
requested and resolved model identity
resolved upstream provider identity when available
generation identity
session identity reconciliation
prompt and completion tokens
cached-token and cache-write states
cache discount when available
raw and parsed hashes
safe error envelopes
```

Cache observation states:

```text
field_absent
field_null
observed_zero
observed_positive
invalid_type
generation_details_mismatch
```

Rules:

```text
absent and null remain unknown
numeric zero proves zero, not cache use
cold positive cache read is contamination evidence only
cold positive cache write or warm positive cache read can support bounded promotion
latency cannot prove caching
```

Fixture validation does not count as live provider evidence.

---

# 11. Bounded Execution Constitution

Frozen execution limits:

```text
logical calls: cold then warm
maximum provider successes: 2
maximum total attempts: 4
maximum transient replacements: 1 per logical call
transient statuses: 429, 502, 524, 529
automatic transport retries: false
retry after success: prohibited
resume: prohibited
rerun: prohibited
```

Exact expected outputs:

```text
COLD-PROBE-ACK
WARM-PROBE-ACK
```

The runner used a recording transport wrapper to preserve the hash-bound OpenRouter adapter. Each
HTTP response was retained separately before typed semantic normalization.

Authorization consumption was recorded in a protected local terminal receipt. The committed grant
remained immutable.

---

# 12. OpenRouter/Hy3 Live Result

Sanitized result:

```text
execution ID: openrouter-hy3-capability-probe-v1
logical call: cold_probe
attempt number: 1
network request count: 1
response kind: completion
HTTP status: 401
provider error code: 401
provider error message: Missing Authentication header
safe error code: PROVIDER_AUTHENTICATION_FAILED
retry permitted: false
provider success count: 0
replacement count: 0
warm call attempted: false
generation metadata requested: false
terminal outcome: closed_terminal_provider_failure
authorization consumed: true
```

The runner behaved correctly:

```text
401
→ non-retryable
→ no second cold attempt
→ no warm call
→ terminal evidence written
→ authorization consumed
→ execution closed
```

---

# 13. Authentication Diagnosis Boundary

Post hoc local diagnostics established:

```text
urllib backend constructs an Authorization header: true
authorization scheme: Bearer
real key used in diagnostic: false
network request made by diagnostic: false
system proxy detected: false
```

These diagnostics clear obvious local regression suspects but do not prove what OpenRouter received
during the live attempt.

Unresolved possibilities:

```text
invalid or revoked key
different key from preflight
mistyped or truncated key
surrounding whitespace
exact live header delivery issue
account-side rejection
another authentication factor
```

Do not claim that OpenRouter removed a header or that AuraGateway definitely omitted it.

---

# 14. Hy3 Capability Decision

Promotion required:

```text
two retained successful responses
numeric cache telemetry
controlled positive cache use
route/model/session reconciliation
no unauthorized retry
verified evidence hashes
```

Observed:

```text
successful responses: 0
numeric telemetry: false
controlled cache use: false
route identity: false
```

Decision:

```text
capability path closed
pilot authorization review prohibited
A/B/C pilot prohibited
retained benchmark prohibited
```

The remaining planned 28 hours of the 48-hour extension were not activated.

---

# 15. Protected and Public Evidence

Protected under `.local`:

```text
prompt bundle
preparation receipt
preflight receipt
attempt journal
raw response record
parsed response sink
terminal receipt
```

Committed sanitized evidence:

```text
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_policy.json
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_result.json
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1/closeout_manifest.json
docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Closeout.md
docs/adr/openrouter-hy3-capability-probe-closeout.md
```

Public evidence includes hashes and safe metadata only. It excludes keys, header values, prompt text,
session identity, and raw provider bodies.

Do not delete `.local` merely to satisfy tests. Tests must isolate filesystem assumptions.

---

# 16. Governing Documents

```text
docs/product/AuraGateway_v2_PRD_Cache_Aware_Agent_Runtime_Harness.md
docs/product/AuraGateway_OpenRouter_Hy3_Free_Tier_Validation_Mini_PRD.md
docs/session/AuraGateway_SESSION_BRIEF.md
docs/benchmark/AuraGateway_v2_Terminal_Evidence_Review.md
docs/benchmark/AuraGateway_OpenRouter_Hy3_Terminal_Evidence_Review.md
docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md
docs/adr/openrouter-hy3-terminal-evidence-review.md
data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/review.json
data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1/manifest.json
```

The historical v2.1.0 design baseline and v2.2.0 Groq terminal amendment remain valid historical
states. Version 2.3.0 governs current continuity.

---

# 17. Important Runtime and Test Files

OpenRouter boundaries:

```text
src/auragateway/contracts/openrouter.py
src/auragateway/providers/openrouter.py
src/auragateway/providers/openrouter_http.py
src/auragateway/providers/openrouter_preflight.py
src/auragateway/providers/openrouter_recording.py
```

Capability governance:

```text
src/auragateway/benchmark/openrouter_hy3_probe_prompt.py
src/auragateway/benchmark/openrouter_hy3_probe_state_model.py
src/auragateway/benchmark/openrouter_hy3_capability_probe_authorization_runner.py
src/auragateway/benchmark/openrouter_hy3_capability_probe_activation_runner.py
src/auragateway/benchmark/openrouter_hy3_capability_probe_execution_runner.py
src/auragateway/benchmark/openrouter_hy3_capability_probe_closeout_runner.py
```

Tests include:

```text
OpenRouter adapter and transport fixtures
header-construction regression test
state-model invariants
activation filesystem isolation
execution terminal outcomes
closeout public/private boundary validation
```

Do not alter historical hash-bound files casually. A change requires a superseding evidence strategy.

---

# 18. Validation

Public terminal validators:

```powershell
python -m auragateway.benchmark.auragateway_v2_terminal_evidence_review_runner `
    validate `
    --repo-root .

python -m auragateway.benchmark.openrouter_hy3_capability_probe_closeout_runner `
    validate-public `
    --repo-root .
```

Release gates:

```powershell
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src tests
git diff --check
git ls-files .local
```

`git ls-files .local` must return no output.

Do not claim CI passed unless current GitHub checks are inspected.

---

# 19. User Workflow Preferences

Confirmation signals:

```text
excellent work
what's next?
take it away
```

Treat them as evidence that all prior instructions were completed and the next bounded operational
slice is wanted.

Implementation workflow:

```text
PowerShell and VS Code
one branch per bounded slice
full-file replacements preferred
one ZIP to Downloads
exact extraction and copy commands
git status after files land
validation before staging
one pytest command per line
git status after git add
exact-path git add
semantic commit and push
clean raw-Markdown PR description
commands-only after-merge sync/delete block
Desktop ZIP for user-to-assistant inspection bundles
```

Ruff policy:

```text
current local authority: 0.15.21
ruff check and ruff format --check are independent gates
historical versions remain historical facts
```

---

# 20. Current Permitted Claims

The project may claim:

```text
deterministic static-prefix construction
typed static/volatile boundaries
prefix mutation and volatile-leak detection
provider-aware telemetry normalization
machine-enforced telemetry sufficiency
cache-affinity policy implementation and fixture validation
bounded one-time execution and terminal closeout
Groq required-field omission in two successful raw responses
OpenRouter/Hy3 first-cold-attempt HTTP 401 terminal closure
no successful Hy3 completion or cache telemetry
A/B/C blocked by evidence gates
```

---

# 21. Current Non-Claims

```text
provider cache hit or miss
cached tokens equal zero
provider cache usage or savings measured
successful Hy3 inference
Hy3 model, route, privacy, cache, cost, or latency conclusion
Condition C benefit
completed A/B/C benchmark
universal savings
production readiness
```

---

# 22. Residual Harness Gaps

```text
credential continuity between preflight and execution was not fingerprinted
exact-live-request header construction was not retained as non-sensitive evidence
surrounding whitespace was not rejected before transport
OpenRouter 401 root cause remains unresolved
no provider lineage produced eligible cache telemetry
```

For any new provider lineage, address these before authorization.

These gaps do not reopen the closed Hy3 execution.

---

# 23. Commercial Proof Angle

## Buyer pain

Teams often assume that a provider’s usage response is sufficient to support cache, latency, and cost
claims. They also run repeated external experiments without a fixed stop rule.

## Failure mode

```text
missing or unreachable telemetry
credential drift between preflight and execution
implicit retries
ambiguous evidence stage
unsupported savings claims
```

## Proof asset

AuraGateway shows:

```text
measurement sufficiency before benchmark spend
provider-specific evidence states
one-time authorization and call ceilings
write-through protected evidence
terminal negative/failure closeout
claims and non-claims linked to exact evidence stage
```

## Offer mapping

```text
AI System Evaluation Audit
Agent Harness Hardening Sprint
AI Reliability Pilot
AI Reliability Retainer
```

## Why a CTO pays

A false efficiency claim can cause architecture decisions, vendor commitments, and budget forecasts to
be based on telemetry that was absent, ambiguous, or never reached. The audit prevents that category
error.

Do not market AuraGateway as proof of measured savings.

---

# 24. Optional Next Phase

The only predesigned next phase is:

```text
Hugging Face static publication integration
```

It must:

```text
use committed sanitized artifacts only
perform no live inference
load no credentials
read no protected provider bodies
publish explicit claims and non-claims
show Groq and OpenRouter/Hy3 as different terminal evidence stages
avoid implying A/B/C completion
```

A new live provider experiment is not the next phase by default. It would require a new PRD and
provider lineage.

---

# 25. Quick Resume Checklist

```text
Confirm repository path.
Run git status and git log -1.
Read PRD 2.3.0 and Hy3 Mini PRD 1.1.0.
Read both terminal evidence reviews.
Read the provider evidence matrix.
Confirm both provider lineages are closed.
Confirm A/B/C remains unauthorized.
Confirm no .local files are tracked.
Do not load a provider key.
Do not rerun preflight or execution.
Do not inspect or publish raw protected evidence.
Use Ruff 0.15.21 unless current local evidence differs.
Treat current terminal output as the authority for branch and commit state.
Proceed only with static publication or a separately authorized new lineage.
```

---

# Final Instruction to the Next LLM

Be strict about evidence stage.

```text
Groq reached successful inference but not sufficient cache telemetry.
OpenRouter/Hy3 reached the provider but not successful inference.
Neither reached eligible A/B/C measurement.
```

Do not merge those results into a generic statement that “provider caching failed.”

The strongest project result is the harness behavior:

> It stopped at the correct boundary, retained the failure, consumed the authorization, and refused to
> convert missing or unreachable evidence into a performance claim.

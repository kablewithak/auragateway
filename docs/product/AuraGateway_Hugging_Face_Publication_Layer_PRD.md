# AuraGateway Hugging Face Publication Layer
## Product Requirements Document

| Field | Value |
|---|---|
| Document version | 1.0.0 |
| Status | Planned publication phase; implementation not started |
| Relationship to AuraGateway core | Separate presentation adapter after core evidence closure |
| Hosting targets | Hugging Face Dataset and static Hugging Face Space |
| Runtime posture | Precomputed artifacts only; no backend and no live inference |
| Data posture | Sanitized public evidence only |
| Architecture posture | Static, provider-neutral, privacy-safe, replaceable |

---

# 1. Purpose

Publish AuraGateway's engineering evidence in a form that a skeptical CTO or staff engineer can
inspect without cloning the repository or running provider calls.

The publication layer must explain both the implemented reliability system and the terminal negative
telemetry result. It must not turn the absence of numeric provider cache evidence into a positive
savings story.

# 2. Product Boundary

The publication layer is not part of the cache-aware runtime.

It consumes sanitized, precomputed artifacts through a one-way export seam:

```text
immutable repository evidence
    -> sanitization and publication validation
    -> versioned public dataset artifacts
    -> static Space visualization
```

It must not write back into runtime evidence, mutate historical artifacts, or influence claim
eligibility.

# 3. Required Outputs

## 3.1 Hugging Face Dataset

Publish a versioned dataset containing:

- terminal evidence review;
- sanitized claim and non-claim matrix;
- evidence manifest and public SHA-256 identities;
- gate status summary;
- selected synthetic eval cases;
- retrieval and routing fixture summaries;
- comparison-eligibility explanation;
- methodology and limitations card;
- machine-readable project maturity record.

Do not publish:

- `.local` files;
- raw or parsed provider response bodies;
- credentials or environment values;
- raw prompts;
- customer data;
- user messages;
- retrieved private documents;
- HMAC secrets or key material;
- provider payload content not already approved for public release.

## 3.2 Static Hugging Face Space

Use a static frontend, preferably Vite, React, TypeScript, and shadcn/ui.

Required views:

1. **Executive result**
   - core scope completed;
   - negative provider telemetry result;
   - A/B/C comparison not completed;
   - exact maturity labels.

2. **Evidence lineage**
   - calibration;
   - SDK compatibility review;
   - raw-wire reauthorization;
   - terminal closeout;
   - project-level terminal review.

3. **Gate explorer**
   - passed gates;
   - blocked gates;
   - Gate 4 contract-integrity versus live-sufficiency distinction.

4. **Claim matrix**
   - permitted claim;
   - blocked claim;
   - reason;
   - evidence pointer.

5. **Case and failure explorer**
   - synthetic cases only;
   - failure hypothesis;
   - expected behavior;
   - observed or fixture outcome;
   - diagnostic value.

6. **Architecture view**
   - context compiler;
   - telemetry boundary;
   - cache-affinity controller;
   - evidence harness;
   - publication adapter.

7. **Methodology and limitations**
   - fixed conditions;
   - evidence thresholds;
   - provider-specific limits;
   - non-claims;
   - reproduction guidance.

# 4. Functional Requirements

The Space must:

- load only checked-in static JSON, CSV, and Markdown-derived content;
- render without a server process;
- require no API token;
- require no model endpoint;
- provide evidence paths and SHA-256 values;
- visually distinguish observed, inferred, unavailable, and blocked states;
- show missing telemetry as `unavailable`, never zero;
- make the negative result visible on the first screen;
- work on desktop and mobile;
- support a deterministic production build.

# 5. Validation Requirements

Before publication:

```text
all exported artifacts pass typed schema validation;
all public files pass a forbidden-field scan;
all hashes reconcile with the approved export manifest;
no .local path is included;
no credential-like value is included;
no raw provider response content is included;
the static build succeeds;
links and evidence pointers resolve;
claim text matches the terminal review;
```

A publication build must fail closed when any check fails.

# 6. Privacy and Security Controls

- Public-export allowlist, not denylist.
- PII and secret scanner on every export.
- No analytics requiring personal identifiers.
- No form collecting user data.
- No cookies required for core use.
- No client-side provider credentials.
- No server-side secret store because no backend is permitted.
- Dataset revisions are immutable and versioned.
- Removal and correction procedure documented.
- POPIA and GDPR principles applied as engineering controls, not legal certification.

# 7. Claims

The publication layer may state:

- AuraGateway is production-shaped and locally validated;
- the runtime and evidence harness were implemented;
- the project preserved unknown telemetry semantics;
- the provider field was absent on two observed raw responses;
- the harness blocked an ineligible benchmark;
- the evidence chain is hash-bound and inspectable.

It may not state:

- provider cache usage was measured;
- cached tokens were zero;
- a cache hit or miss occurred;
- cache savings were measured;
- A/B/C improvement was demonstrated;
- universal provider behavior;
- production readiness;
- customer-data validation.

# 8. Acceptance Criteria

The publication phase is complete when:

```text
Hugging Face Dataset is public and versioned;
static Space is public and builds reproducibly;
all content derives from an approved sanitized export;
terminal negative result is represented accurately;
claim matrix matches machine-readable terminal review;
no protected or sensitive artifact is published;
a fresh reviewer can trace every public conclusion to evidence;
```

# 9. Non-Goals

```text
live inference
chat interface
provider proxy
runtime dashboard
credential management
customer upload
user accounts
backend API
database
managed vector store
production monitoring
benchmark rerun
new provider execution
```

# 10. Commercial Role

The public layer is a buyer-readable proof surface for:

- AI System Evaluation Audit;
- Agent Harness Hardening Sprint;
- AI Reliability Pilot;
- AI Reliability Retainer.

It demonstrates that the consultancy can identify evidence insufficiency, preserve negative results,
and prevent unsupported business claims rather than optimizing only for attractive demos.

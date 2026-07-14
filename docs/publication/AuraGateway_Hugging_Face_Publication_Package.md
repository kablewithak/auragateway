# AuraGateway Hugging Face Publication Package

## Purpose

Package AuraGateway's committed terminal provider evidence as a public-safe Dataset candidate and a
static Space candidate without reopening provider execution.

## Candidate paths

```text
release/hugging-face/dataset/auragateway-provider-evidence
release/hugging-face/space/auragateway-provider-evidence
```

## Source evidence

```text
data/evals/benchmark/openrouter-hy3-capability-probe-closeout-v1
data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1
docs/benchmark/AuraGateway_Provider_Evidence_Matrix.md
```

The publication adapter verifies the frozen terminal state before generating outputs.

## Build

```powershell
python -m auragateway.publication.hugging_face_runner build --repo-root .
```

## Validate

```powershell
python -m auragateway.publication.hugging_face_runner validate --repo-root .
```

Expected boundary:

```text
live_inference_included=false
credential_required=false
remote_publication_authorized=false
next_gate=remote_publication_authorization_review
```

## Dataset candidate

Contains:

```text
README.md
ATTRIBUTION.md
LICENSE.md
candidate_manifest.json
evidence_boundary.md
publication_state.json
data/provider_evidence.jsonl
data/claim_matrix.jsonl
docs/METHODOLOGY.md
```

## Space candidate

Contains:

```text
README.md
index.html
style.css
app.js
evidence.js
evidence_boundary.md
LICENSE.md
candidate_manifest.json
```

The Space uses Hugging Face's static SDK boundary and needs no application server.

## Public claim

> AuraGateway retained two terminal provider results and blocked the measured A/B/C cache benchmark
> because neither provider lineage produced eligible numeric cache evidence.

## Public non-claims

```text
No provider cache hit or miss was measured.
No cached-token value of zero was established.
No provider cache saving or latency improvement was measured.
No Hy3 inference succeeded.
No A/B/C result exists.
The project is not deployed or production-ready.
```

## Privacy and security

The candidate contains no credentials, raw prompts, customer data, protected session identifiers,
raw provider bodies, local journals, parsed response files, prompt bundles, or terminal receipts.

## Remote-publication gate

Do not publish remotely in this slice. Before publication:

1. choose an explicit public license;
2. decide Dataset and Space repository names and visibility;
3. create a controlled credential boundary;
4. inspect the exact candidate file lists and hashes;
5. publish through a separate executor;
6. reconcile anonymous remote contents against the local manifest;
7. retain a publication receipt and rollback instructions.

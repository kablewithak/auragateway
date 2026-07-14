---
pretty_name: AuraGateway Provider Evidence
language:
- en
license: other
size_categories:
- n<1K
tags:
- ai-reliability
- llm-evaluation
- prompt-caching
- observability
- negative-results
configs:
- config_name: provider_evidence
  data_files:
  - split: train
    path: data/provider_evidence.jsonl
- config_name: claim_matrix
  data_files:
  - split: train
    path: data/claim_matrix.jsonl
---

# AuraGateway Provider Evidence

This dataset is a static, sanitized publication package for AuraGateway v2. It contains two
terminal provider-lineage summaries and a claim matrix. It contains no raw prompts, customer data,
credentials, raw provider payloads, or live inference code.

## Headline result

AuraGateway did not force a measured cache benchmark after its provider evidence gates failed.

- Groq returned two successful raw-wire responses, but the required cached-token field was absent.
- OpenRouter returned HTTP 401 on the first Hy3 cold attempt before successful model inference.
- Neither lineage produced eligible numeric cache evidence.
- The A/B/C provider comparison was not authorized or completed.

## Data files

| Config | File | Purpose |
|---|---|---|
| `provider_evidence` | `data/provider_evidence.jsonl` | Sanitized terminal provider records |
| `claim_matrix` | `data/claim_matrix.jsonl` | Explicit permitted and blocked claims |

## Intended use

Use this package to inspect how a production-shaped AI reliability harness records negative and
inconclusive provider evidence without converting unknown telemetry into zero or continuing an
experiment after its measurement gate fails.

## Prohibited interpretation

This dataset does not establish cache performance, cost savings, latency improvements, Hy3 model
quality, provider rankings, customer-data readiness, deployment, or production readiness.

## Evidence maturity

```text
production-shaped
locally validated
synthetic-corpus validated
fixed-eval validated
controlled-provider tested
not customer-data tested
not deployed
not production-ready
```

## License

The local candidate uses Hugging Face metadata value `license: other`. No standalone public reuse
license has been selected yet. Remote publication must remain blocked until the repository owner
chooses and records an explicit publication license.

## Reproducibility

The committed `publication_manifest.json` binds every candidate file to SHA-256 hashes and records
the exact source evidence used to build this package.

# AuraGateway v2 Terminal Review Supersession

## Purpose

Repair a validator/repository-evolution mismatch without rewriting historical evidence.

## Historical state

The core terminal review froze:

```text
review_id=auragateway-v2-terminal-evidence-review-v1
prd_version=2.2.0
source provider lineage=Groq
measured A/B/C comparison=false
```

The later terminal continuity review froze:

```text
review_id=openrouter-hy3-terminal-evidence-review-v1
core PRD version=2.3.0
OpenRouter/Hy3 outcome=closed_terminal_provider_failure
comparison eligible=false
runtime rerun permitted=false
```

## Delegated documents

Exactly three mutable continuity paths are delegated:

| Path | Historical authority | Current authority |
|---|---|---|
| `README.md` | Core terminal manifest | Hy3 terminal-continuity manifest |
| Core PRD | Core terminal manifest | Hy3 terminal-continuity manifest |
| Session brief | Core terminal manifest | Hy3 terminal-continuity manifest |

All evidence files, the original review/report/ADR, and the publication-layer PRD remain validated against the original core manifest.

## Validation properties

The remediation proves:

```text
original manifest unchanged
original source evidence unchanged
superseding manifest hash-bound
exact delegated path set enforced
historical hashes preserved
current hashes verified
missing or tampered overlay rejected
provider execution prohibited
```

## Claims

Permitted:

> AuraGateway supports additive continuity supersession while preserving immutable historical evidence.

Blocked:

```text
historical evidence was rewritten
provider evidence changed
A/B/C became comparison-eligible
provider execution was reopened
publication results changed
```

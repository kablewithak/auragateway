# AuraGateway Gate 6 Deterministic Quality Scorers

## Purpose

This artifact defines the first Task-Quality Safety boundary. It converts frozen diagnostic episode requirements into deterministic, metadata-safe checks before any condition-blind rubric review.

## Inputs

The runner consumes only versioned repository assets:

- the frozen functional episode set;
- the frozen episode manifest and retrieval-configuration fingerprint;
- the synthetic corpus inventory;
- deterministic candidate traces;
- frozen claim-to-source support registries.

Candidate fixtures may contain synthetic output text for schema validation. Persisted scorecards retain only output hashes, source IDs, check outcomes, and failure labels.

## Deterministic checks

The scorer evaluates:

1. structured terminal-output validity;
2. retrieval-configuration fingerprint equality;
3. terminal decision and reason-code correctness;
4. retrieved source-ID validity;
5. required-source presence;
6. forbidden-source absence;
7. unscoped stale-source absence;
8. citation-ID validity;
9. citation retrieval provenance;
10. required citation presence;
11. required semantic claim digests;
12. forbidden semantic claim digests;
13. claim-to-source support;
14. decision-specific expectation details.

There is no weighted aggregate and no universal quality score. A scorecard passes only when no deterministic check fails.

## Claim support

The scorer does not pretend that string matching proves natural-language entailment. Required and forbidden claims are normalized and SHA-256 hashed. A human-authored fixture registry maps claim digests to supporting and contradicting source IDs.

This makes the evidence mapping inspectable and reproducible while leaving residual prose quality for later blinded review.

## Fixed evidence

The fixture set contains 14 cases:

- 4 passing controls;
- 10 negative controls;
- answer, clarify, escalate, and refuse terminal states;
- malformed structured output;
- terminal-decision mismatch;
- incomplete clarification;
- escalation-reason mismatch;
- forbidden and stale source use;
- invalid citations;
- unsupported and forbidden claims;
- retrieval-fingerprint drift;
- missing required source evidence.

## Commands

Build new evidence only when intentionally versioning the fixture or scorer boundary:

```powershell
python -m auragateway.evals.quality_runner build --repo-root .
```

Normal validation must verify the frozen evidence:

```powershell
python -m auragateway.evals.quality_runner verify --repo-root .
```

## Gate status

This slice advances Gate 6 but does not close it.

Still required:

- frozen rubric criteria;
- opaque condition-blind review exports;
- primary and double-review workflow;
- material-disagreement adjudication;
- quality non-inferiority aggregation across A, B, and C;
- held-out execution under a frozen scorer and rubric version.

## Non-claims

The deterministic report does not prove that arbitrary response wording is correct or useful. It does not replace blinded review, establish citation entailment outside the registry, prove task-quality non-inferiority, permit measured A/B/C execution, or support latency or cost claims.

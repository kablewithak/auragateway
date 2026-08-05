# ADR: P4 Output-Contract Diagnostic Execution Authorization V1

## Status

Accepted for repository implementation. This ADR does not issue live runtime authority.

## Context

P4 Output-Contract Diagnostic V1 is merged through a four-stage authority lineage:

- original implementation merge: `3ab50e7a1e2661c5967ba91501c51afe96b58864`;
- evidence-contract remediation feature: `e60b59e40fc756e51a58617d4d47cbb85d37dc7b`;
- evidence-contract remediation merge: `e13882628559ec0f8f3364cc27ce574cbdd92806`;
- terminal-evidence closure feature: `d85cc387344164034e30fe57752e4f04f4d10cdd`;
- terminal-evidence closure merge and current source authority:
  `5c1654c78ce398591043960fb28e5e1f03f3cc34`.

The diagnostic now has one canonical sixteen-artifact contract for ordinary successful and failed
terminal paths. It initializes deterministic `NOT_RUN` reports, preserves partial request evidence,
prevents case selection from partial evidence, tears down failed worker startup, terminalizes
teardown and cleanup failures, and rejects incomplete pre-manifest or pre-archive output sets.

The governed budget remains one T4 session, one offline runtime installation, one import-closure
probe, one model load, one worker start, and exactly eighteen scheduled model requests with no
hidden retries, external network requests, benchmark trajectories, customer data, credentials, or
external spend.

## Decision

Implement a separate transient, single-use execution-authorization issuer.

The issuer must:

- require clean synchronized `main` at the terminal-evidence closure merge;
- bind every implementation artifact by repository path and SHA-256;
- bind the original implementation, both evidence-contract commits, and both terminal-closure
  commits;
- bind the notebook, runtime script, wrapper, request, review, implementation record, model
  snapshot, and governed wheelhouse;
- bind the exact sixteen-artifact terminal-path contract and its executable closure markers;
- require explicit operator confirmation of the source authority, terminal-closure feature,
  notebook and runtime identities, backend, request budget, and terminal-path completeness;
- create authorization and consumption artifacts without overwriting;
- require transient lifecycle artifacts to remain untracked;
- consume authority after one passed, failed, or interrupted attempt;
- prohibit unchanged replay after consumption;
- exclude measured A/B/C execution.

## Consequences

Repository implementation and review of the issuer cannot execute Kaggle or create live authority.
After merge, a separate immediate-readiness review and explicit operator confirmation are required
before issuance. Static terminal-path closure is authorization evidence, not proof that the pinned
Kaggle runtime will complete successfully.

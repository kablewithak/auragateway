# ADR: Preflight V4 semantic-channel reconciliation

Date: 2026-08-09
Status: Proposed for repository acceptance

## Context

Final Offline Verifier V4 saved version `341211001` passed input validation,
target-environment creation, exact hash-locked offline installation, target
distribution inventory, and dependency checking, then reported a failure at
`controlled_python_startup`.

A local, GPU-free reproduction and repository forensic inspection established
that V4 stores sanitized and tail-bounded subprocess output in
`stdout_excerpt` / `stderr_excerpt` and subsequently reuses those evidence
representations as semantic inputs.

The primary violated invariant is:

`PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION`

The failure class is `DIAGNOSTIC_HARNESS_DEFECT`.

Failure code:

`EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT`

## Decision

Preserve V4 and saved version `341211001` as immutable evidence.

Do not patch V4.

Introduce a reconciliation-only repository tranche that:

1. binds the exact V4 notebook/source/test identities;
2. machine-detects the current semantic/evidence channel topology;
3. records the five deterministic path-bearing false-negative roles;
4. binds the historical controlled-startup mechanism as design evidence;
5. freezes executable successor gates;
6. issues no execution authority.

The successor must use:

`raw observation -> typed semantic observation -> decision -> terminal evidence transform`

Evidence transforms include sanitization, redaction, canonicalization, and
truncation. They are prohibited before semantic decision-making.

## Historical design evidence

PR #127 proves the controlled startup mechanism in which child-process semantic
facts such as `prefix_matches_expected` are computed before evidence
sanitization.

PR #197 provides a native-origin pattern in which raw resolved paths are
classified before the persisted origin is sanitized.

Historical implementations remain design evidence only. They are not current
vLLM `0.25.1+cu129` qualification authority and must not be copied wholesale.

## Consequences

No new Kaggle execution is authorized.

No wheelhouse rebuild or dependency resolution is justified.

The next implementation gate is:

`design_semantic_channel_safe_final_offline_verifier_v5_successor`

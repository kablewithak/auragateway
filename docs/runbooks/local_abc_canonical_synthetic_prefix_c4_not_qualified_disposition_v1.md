# Runbook: Canonical Synthetic Prefix C4 NOT_QUALIFIED Disposition V1

## Purpose

Preserve and deterministically validate the governed C4 evidence before any new execution or causal interpretation.

## Commands

Generate:

`python src/auragateway/local_abc/canonical_synthetic_prefix_c4_not_qualified_disposition_v1.py generate --repo-root .`

Validate:

`python src/auragateway/local_abc/canonical_synthetic_prefix_c4_not_qualified_disposition_v1.py validate --repo-root .`

## Required custody

The evidence vault contains exactly eight top-level custody members:

- execution authorization
- execution artifact manifest
- platform observation receipt
- authorization terminal receipt
- executed Kaggle notebook
- Kaggle terminal log
- outer Kaggle results ZIP
- governed inner evidence ZIP

The producer binds each member by SHA-256 and byte length.

## Behavioral acceptance

A valid disposition requires three completed fresh-worker observations, three valid JSON responses, three `finish_reason=stop` responses, zero exact required objects, no hidden retry, no external network request, clean teardown, and clean scratch cleanup.

`NOT_QUALIFIED` is a behavioral result, not an execution failure.

## Prohibited transitions

Do not:

- rerun saved version 343536641;
- reuse the consumed authorization;
- claim C4 qualification;
- claim P5 or P6 requalification;
- claim final A/B/C measurement;
- claim a root cause;
- authorize a new execution from this disposition.

## Next gate

`ANALYZE_C4_NOT_QUALIFIED_OUTPUT_DIVERGENCE_BEFORE_NEW_EXECUTION_V1`

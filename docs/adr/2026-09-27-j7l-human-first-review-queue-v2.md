# ADR — J7L Human-First Development V2 Review Queue

**Date:** 2026-09-27
**Status:** Accepted implementation design
**Protocol:** `auragateway-j7l-human-first-review-v2`

## Context

The J7L human-first V2 foundation has frozen a fresh 48-case development subject,
pre-frozen a `0.80` novelty threshold, validated the sealed authoring population,
and materialized one reviewer-safe export.

The project has one available human reviewer. A second-human review or
adjudication protocol is therefore non-executable and must not be simulated.

## Decision

Use a sequential, append-only, opaque-assignment human-review queue.

The queue:

1. consumes only the already-frozen reviewer-safe export during active review;
2. validates the sealed authoring artifact by SHA-256 without semantically
   reading its hidden contents during active review;
3. derives a deterministic mixed review order from opaque assignment IDs;
4. exposes one opaque assignment at a time;
5. requires all seven criterion scores, failure labels, visible evidence
   references, and concise rationale;
6. derives PASS/FAIL mechanically from the frozen rule;
7. writes each accepted assessment append-only;
8. forbids out-of-order assessment files;
9. keeps provider/model/Jev/J7M/final-A/B/C execution unauthorized;
10. reads hidden authoring targets only after all 48 human assessments are
    complete, solely for aggregate coverage evaluation.

## Human authority

Authority is exactly:

`SINGLE_HUMAN_DEVELOPMENT_REFERENCE`

This is development reference authority, not independent ground truth.

The reviewer attests once that:

- the hidden authoring payload has not been read;
- each human judgment will be made before any AI proposal of scores, labels,
  evidence, verdict, or rationale.

An AI assistant may help with mechanics or schema validation after the human has
already made the judgment. It must not originate the judgment.

## Reviewer-facing identity

Human work items expose:

- queue index;
- opaque assignment ID;
- opaque review-item ID;
- reviewer-safe state and its SHA-256;
- frozen human semantic projection;
- reviewer instruction.

They do not expose case ID or family.

## Sequentiality

Submission must target the next frozen queue assignment. Accepted assessments
form a strict prefix of the deterministic queue order.

This prevents silent retroactive rewriting and makes interruption/resume
observable.

## Human reference coverage

After all 48 assessments are append-only, the queue may read hidden authoring
metadata for coverage only.

Advancement requires:

- PASS >= 16;
- FAIL >= 16;
- each failure label has positive human support >= 2;
- each authoring near-miss label has at least two cases where the human did not
  assign that label;
- every criterion has at least three distinct human score values;
- every criterion has at least four human low observations in `{1,2}`;
- every criterion has at least four human high observations in `{3,4}`;
- terminal material-evidence count >= 8.

Authoring targets are never substituted for human truth.

If coverage fails, human assessments are preserved unchanged and the lineage
stops at `STOP_VERSIONED_SUCCESSOR_REQUIRED`.

## Freeze

On coverage pass, the queue freezes:

- exact 48 assessment digests;
- reviewer pseudonymous identity hash;
- foundation case-freeze identity;
- human-reference coverage-report identity;
- protected reference-freeze identity;
- metadata-only public receipt.

No model/Jev execution is authorized by this freeze. The next gate is a
separate design and authorization step for J7L V2 development evaluator
execution.

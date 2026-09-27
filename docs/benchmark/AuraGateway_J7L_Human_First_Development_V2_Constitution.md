# AuraGateway J7L Human-First Development V2 — Constitution

**Date:** 2026-09-27  
**Status:** Foundation protocol; no model/Jev execution authority  
**Protocol ID:** `auragateway-j7l-human-first-development-v2`

## 1. Purpose

This protocol creates a fresh 48-case development population after the historical
J7L model-derived reference failed human audit and the later human-completion
lineage was contaminated by AI-authored judgments being submitted as human
assessments.

Historical evidence is preserved. It is not rewritten, rescored, deleted, or
converted into a passing lineage.

The new authority boundary is:

`SINGLE_HUMAN_DEVELOPMENT_REFERENCE`

This is development evidence only. It is not independent qualification truth.

## 2. Historical disposition

Before any new population is read:

- the V3 failed audit identity must validate;
- the original 28-case human freeze identity must validate;
- the contaminated V1 successor must remain at eight submitted successor
  assessments, 36 total recorded human assessments, 12 pending, next case
  `j7l-dev-011`;
- the distinct-human remediation V2 code remains preserved but its local review
  lineage must be uninitialized because a genuinely distinct human reviewer is
  unavailable.

No historical protected evidence may be modified.

## 3. Fresh population

The fresh namespace is:

`j7l-v2-dev-001` through `j7l-v2-dev-048`.

The population contains exactly:

- 12 `ordinary_clean`;
- 12 `clear_failure`;
- 12 `terminal_non_substantive`;
- 12 `ontology_near_miss`.

Historical `j7l-dev-*` IDs are forbidden.

The fresh population must be authored in a separate sealed authoring context that
does not inherit this Project's history or prior J7L case content. The human reviewer
must not read the hidden authoring JSON before the reviewer-safe export is frozen.

## 4. Authoring targets

Hidden authoring targets are design controls, not human truth.

The authoring population must target:

- at least 16 PASS cases;
- at least 16 FAIL cases;
- each of the 22 failure labels positively at least twice;
- each of the 22 failure labels as a near-miss negative at least twice;
- at least three intended score values for every rubric criterion;
- at least four intended low scores `{1,2}` for every criterion;
- at least four intended high scores `{3,4}` for every criterion;
- at least eight terminal/non-substantive cases where visible evidence
  materially determines the terminal action.

The seven frozen criteria remain:

- `task_correctness`;
- `evidence_grounding`;
- `source_use`;
- `terminal_decision`;
- `completeness`;
- `clarity`;
- `safety`.

The frozen deterministic verdict rule remains:

- total criterion score >= 21;
- minimum criterion score >= 2;
- zero failure labels;
- then PASS; otherwise FAIL.

Human review is not required to agree with authoring targets.

## 5. Novelty boundary

The old 48-case protected authoring population may be read only by deterministic
local novelty tooling.

Before any new authoring population is imported:

1. lock the historical disposition;
2. calculate and freeze the historical pairwise similarity profile;
3. inspect only that aggregate profile;
4. choose and freeze the novelty threshold;
5. only then import the new sealed population.

Similarity algorithm:

`nfkc-casefold-whitespace-canonical-json__max-sequence-token-jaccard-v1`

Exact historical case reuse is forbidden. Normalized exact reuse is forbidden.
The pre-frozen similarity threshold applies both to new-vs-historical pairs and
within-new pairs.

The threshold may not be weakened after the new population is read.

## 6. Reviewer-safe export

The human reviewer may see only:

- opaque assignment identity;
- opaque review-item identity;
- reviewer-safe state;
- the frozen J7K human semantic projection;
- reviewer instructions.

The reviewer-safe export must not contain:

- case ID;
- case index;
- family metadata;
- intended criterion scores;
- intended verdict;
- intended failure labels;
- near-miss targets;
- authoring notes;
- model-reference judgments;
- historical judgments;
- Jev output;
- baseline/intervention results.

## 7. Human boundary

The single human reviewer independently chooses:

- all seven criterion scores;
- failure labels;
- evidence references;
- concise rationale.

An AI assistant may validate schema and serialize a human decision only after the
human has made that decision. It may not choose or propose the human judgment
first.

The 48 human assessments must freeze before any model-reference or Jev reveal.

## 8. Model and evaluator boundary

This foundation protocol authorizes:

- historical-state validation;
- historical similarity profiling;
- novelty-threshold freeze;
- sealed authoring import;
- deterministic reviewer-safe export.

It does not authorize:

- reference-model requests;
- Jev requests;
- provider execution;
- threshold selection from evaluator outcomes;
- J7M execution;
- final A/B/C quality claims.

Those require later versioned gates after the human reference is frozen.

## 9. Qualification boundary

J7L V2 is development evidence. Procedure selection may occur on it after the
human reference is frozen.

After development:

1. freeze the selected procedure;
2. create a fresh J7M holdout;
3. human-review J7M before evaluator/model reveal;
4. run the frozen procedure once;
5. qualify or fail without tuning J7M.

Only after valid J7M qualification may the final controlled A/B/C quality path
advance.

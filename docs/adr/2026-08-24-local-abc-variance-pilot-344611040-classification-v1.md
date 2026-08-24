# ADR: Classify variance-pilot Kaggle Version 344611040 and block repetition freeze

Date: 2026-08-24

## Status

Accepted classification boundary candidate.

## Context

Governed variance-pilot transaction
`06935eae12e8f996c7046a859ea75525b436a871b086ba4c56470d24871747ab`
executed once as Kaggle Version `344611040` from issuer merge
`bb1e2b46767e7b84ae8bbecab2887759e38e028d`.

The runtime completed without fatal failure, produced the governed evidence ZIP, and
cleanly terminalized the single-use capability as consumed. The execution therefore
provides valid runtime and mechanism observations.

The same evidence also exposed two blockers to repetition freeze:

1. task-output contract failure: all 54 trajectories are task-failed; only 6 of 216
   completed turns are valid JSON and 132 of 216 turns terminate by length;
2. the current turn-2 worker-symmetry estimator is confounded: every worker-1
   projection is condition C while every worker-2 projection is condition A or B.
   The observed worker timing ratio therefore cannot be interpreted as a causal
   worker/GPU effect.

The cache-salt isolation preflight remains separately useful evidence: cold same-salt
reuse is 0 cached tokens, warm same-salt reuse is 944 cached tokens, and the
different-salt request observes 0 cached tokens.

## Decision

Accept the governed execution evidence as a runtime pass without accepting the pilot
for repetition freeze.

The classification is:

- governed execution: `ACCEPTED_GOVERNED_EXECUTION_PASS`;
- cache-salt qualification: `QUALIFIED`;
- task-output contract: `FAILED`;
- worker-symmetry estimator: `CONFOUNDED`;
- repetition freeze:
  `BLOCK_REPETITION_FREEZE_AND_REDESIGN`;
- pilot repository acceptance: false;
- final measured A/B/C authorization: false;
- new execution authorization: false;
- effect claims permitted: false.

The exact evidence is preserved under:

`evidence_vault/local_abc/measured-abc-variance-pilot-344611040-v1/`

and must remain byte-identical.

## Successor redesign boundary

A successor pilot may be implemented only after all of these design requirements are
represented explicitly in code/tests:

1. qualify both workers using identical neutral workload and equal warm-up outside the
   A/B/C treatment;
2. keep cache-salt isolation qualification separate from worker-symmetry qualification;
3. require schema-valid model output before conversation state mutation;
4. prove the output-token budget sufficient, or qualify one identical schema-enforcement
   boundary applied across A/B/C;
5. block final A/B/C authorization until successor pilot acceptance.

These are control-plane requirements. They do not prescribe a new A/B/C treatment and
must not silently change the North Star intervention definitions.

## Non-claims

This classification does not claim that worker 2 is intrinsically slower than worker 1.
It does not claim a final prefix effect, affinity effect, combined effect, quality
non-inferiority, or production readiness. It does not authorize another Kaggle run.

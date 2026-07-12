# AuraGateway Gate 6 Quality Non-Inferiority Dry Run

## Purpose

This artifact documents the final pre-execution Gate 6 comparison boundary. It turns the frozen task-quality requirements into a typed A/B/C decision gate without invoking providers or claiming measured benchmark results.

## Boundary

The comparison accepts aggregate metadata for conditions A, B, and C. Each condition must provide:

- sample count;
- answer count;
- structured-output-valid count;
- citation-evaluable and citation-supported counts;
- unsupported-answer count;
- task-success count;
- the frozen retrieval-configuration fingerprint;
- the frozen episode-manifest digest;
- an evidence-bundle digest.

No raw prompts, conversations, documents, candidate outputs, reviewer notes, or hidden reasoning are retained.

## Frozen thresholds

A comparison is eligible only when all conditions use the same retrieval configuration and frozen episode manifest.

Eligible comparisons must satisfy:

- at least 30 samples per condition;
- at least one answer and one citation-evaluable outcome per condition;
- structured-output validity of at least 95 percent in every condition;
- no citation-support regression against condition A;
- no increase in unsupported-answer rate against condition A;
- task success in conditions B and C no more than five percentage points below condition A.

The five-point task-success margin and the 95 percent structured-output threshold are inclusive boundaries.

## Explicit states

The gate produces one of four states:

- `passed`: eligible and every quality check passes;
- `failed`: eligible but at least one quality check fails;
- `ineligible`: retrieval or episode configuration differs across conditions;
- `insufficient_sample`: sample or rate denominator requirements are not met.

Ineligible and insufficient comparisons are not converted into ordinary quality failures. This prevents configuration drift or weak evidence from being misread as model-quality results.

## Fixed evidence

The frozen dry-run fixture set contains ten cases:

- one exact-boundary passing control;
- five eligible quality failures;
- two configuration-ineligible controls;
- two insufficient-evidence controls.

The negative controls cover:

- structured-output validity below 95 percent;
- citation-support regression;
- unsupported-answer-rate increase;
- task-success loss greater than five percentage points;
- multiple simultaneous regressions;
- retrieval fingerprint drift;
- episode-manifest drift;
- insufficient sample count;
- missing answer and citation denominators.

## Experiment integrity

This slice:

- does not call Groq;
- does not call Ollama;
- does not execute conditions A, B, or C;
- does not change retrieval configuration;
- does not change episodes or held-out labels;
- does not change routing or pricing;
- keeps measured execution prohibited.

## Claim boundary

The evidence proves deterministic eligibility, threshold, non-inferiority, regression, and insufficient-evidence behavior on fixed synthetic aggregates.

It does not prove actual provider-condition quality, completed human review on measured trajectories, task-quality non-inferiority, latency improvement, cost reduction, benchmark readiness, deployment safety, or production readiness.

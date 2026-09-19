# AuraGateway J7L Development Evaluation V1 — Constitution

**Status:** Candidate constitution for implementation  
**Gate:** `J7L_DEVELOPMENT_EVALUATION_V1`  
**Date:** 2026-09-19  
**Repository:** `kablewithak/auragateway`  
**Predecessor:** `J7K_SHARED_SEMANTIC_PROJECTION_V1`  
**Next gate if accepted:** `J7M_HELD_OUT_QUALIFICATION_V1`

## 1. Purpose

J7L measures whether the repaired Quality Semantic Registry v2 and its J7K model projection improve the existing evaluator on fresh development evidence.

J7L is a development/calibration gate. It may select a development threshold for later held-out testing, but it may not establish independent evaluator qualification, autonomous adjudication suitability, deployment readiness, or any AuraGateway A/B/C effect claim.

The experiment compares two evaluator conditions on exactly the same fresh cases:

- **BASELINE_V1_SEMANTICS** — the existing Jev v1 question semantics used in the preserved Final-342 shadow-adjudication experiment.
- **INTERVENTION_V2_SEMANTICS** — the J7K model projection generated from `auragateway-quality-semantic-registry-v2`.

The model pin, reviewer-safe state, case bytes, question inventory, and execution policy must remain fixed except for the semantic instructions under test.

## 2. Frozen semantic authority

J7L binds:

- registry ID: `auragateway-quality-semantic-registry-v2`
- registry schema: `2.0.0`
- semantic registry SHA-256: `0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166`
- registry artifact SHA-256: `0684620f4a21d3fa3fd0bb54fb8caf9d5fab19f3b516cdf0b23de5880a06f74c`
- J7K human projection SHA-256: `177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82`
- J7K model projection SHA-256: `b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e`

Human reviewers and the intervention evaluator must consume deterministic projections of this same registry. Private human semantics, private model semantics, semantic elision, and prompt-only normative additions are prohibited.

The preserved Final-342 v1 rubric, human judgments, Jev requests/responses, and calibration reports remain immutable historical evidence.

## 3. Development population

### 3.1 Size

The frozen J7L development population contains exactly **48 fresh cases**.

The population is deliberately diagnostic rather than representative. J7M, not J7L, owns independent qualification.

### 3.2 Case families

The 48 cases are authored before any J7L model reveal and contain exactly:

- 12 ordinary/clean cases expected to exercise correct answer behaviour;
- 12 clear failure cases with unambiguous evidence;
- 12 terminal-action or non-substantive cases, including clarification, escalation, refusal, and missing-field boundaries;
- 12 ontology near-miss cases designed to distinguish related failure labels without relying on enum names alone.

Case-family membership is metadata for dataset construction and coverage only. It is not visible to human reviewers or the model evaluator.

### 3.3 Freshness

J7L cases must be new.

Prohibited:

- copying a Final-342 review item;
- paraphrasing a Final-342 item so closely that its authoritative outcome is recoverable;
- reusing Final-342 review-item IDs;
- reusing Final-342 human reviews or adjudications as J7L truth;
- selecting cases based on observed J7L model outputs.

Permitted:

- exercising the same general reliability concepts;
- using the same frozen source corpus when appropriate;
- deliberately targeting semantic boundaries discovered during the historical J7 analysis.

### 3.4 Human-truth coverage required before model reveal

Before the development population may be frozen for model execution, authoritative human truth must satisfy all of the following:

- case count = 48;
- PASS count >= 16;
- FAIL count >= 16;
- every one of the 22 failure labels has positive support >= 2;
- every one of the 22 failure labels has explicit near-miss negative support >= 2;
- every rubric criterion has at least 3 distinct authoritative score values represented;
- every rubric criterion has at least 4 low-score observations in `{1, 2}`;
- every rubric criterion has at least 4 high-score observations in `{3, 4}`;
- the terminal/non-substantive family contains at least 8 cases where visible evidence materially determines whether the terminal action is justified.

If these coverage requirements are not met, additional or replacement development cases may be authored **only before any J7L model request is performed**. Once model execution begins, the development population is immutable.

## 4. Human authority

All 48 cases receive a primary human review using the J7K human semantic projection.

A pre-frozen stratified secondary schedule covers exactly **24 of 48 cases**:

- all 12 terminal-action/non-substantive cases;
- all 12 ontology near-miss cases.

Secondary reviewers must not see primary-review scores, verdicts, labels, rationale, or model outputs.

Material disagreement is defined by the existing AuraGateway blinded-quality rules:

- verdict mismatch;
- any criterion score delta >= 2;
- failure-label-set mismatch.

Every material disagreement requires adjudication before human truth is frozen.

The authoritative human result for each case is:

- PRIMARY when no required secondary review exists;
- PRIMARY when a required secondary review exists and there is no material disagreement;
- ADJUDICATION when material disagreement exists.

No model request may occur until:

- all 48 primary reviews are complete;
- all 24 scheduled secondary reviews are complete;
- every required adjudication is complete;
- the authoritative truth artifact is frozen and hash-bound.

## 5. Model experiment

### 5.1 Model

J7L initially binds the existing evaluator model:

`jev-1.13.0`

A model-version change requires a new J7L experiment version.

### 5.2 Paired conditions

Each development case receives exactly two evaluator requests:

1. `BASELINE_V1_SEMANTICS`
2. `INTERVENTION_V2_SEMANTICS`

Both requests must use:

- identical reviewer-safe case state;
- identical case/state bytes;
- identical model pin;
- identical 7 criterion + 22 failure-label question inventory;
- identical provider endpoint and response contract;
- no authoritative human result in model-visible state;
- no Final-342 human adjudication;
- no experiment-family metadata.

The only intended experimental variable is the semantic instruction content.

### 5.3 Balanced request order

To reduce order effects without randomness:

- even case indices execute baseline then intervention;
- odd case indices execute intervention then baseline.

Case order is frozen before model execution.

### 5.4 Execution policy

- 96 planned provider requests total;
- serial execution;
- maximum 1 request in flight;
- no automatic retry;
- no replacement case after model reveal;
- existing valid response + receipt => skip, do not replay;
- provider/validation/persistence failure => retain the failed pair state and stop or resume only under the same frozen population;
- model outputs are append-only evidence.

A missing member of a pair makes that case unavailable for paired intervention analysis. It is not silently excluded from denominator accounting.

## 6. Metrics

### 6.1 Criterion scoring

For each of the 7 criteria and overall:

- exact accuracy;
- mean absolute error;
- within-one accuracy;
- multiclass Brier score;
- mean selected-choice confidence;
- confidence ECE;
- catastrophic disagreement count/rate where absolute score error >= 2;
- maximum disagreement count/rate for `1 <-> 4`.

### 6.2 Failure-label scoring

Using raw probabilities:

- per-label positive support;
- per-label prevalence;
- per-label Brier score;
- pooled failure-probability Brier score;
- pooled failure-probability ECE.

At the fixed diagnostic threshold `0.50`:

- micro precision;
- micro recall;
- micro F1;
- exact failure-label-set accuracy;
- derived verdict accuracy;
- per-label precision/recall/F1 where support permits;
- false-positive rate on explicitly authored near-miss negatives.

### 6.3 Development threshold selection

Only the intervention condition may produce the candidate threshold carried into J7M.

Candidate thresholds are frozen to:

`0.05, 0.10, 0.15, ..., 0.95`

Threshold selection is deterministic and lexicographic:

1. highest micro F1;
2. highest exact failure-label-set accuracy;
3. highest derived verdict accuracy;
4. lowest false-positive count;
5. if still tied, choose the higher threshold.

The selected threshold is a **development-selected candidate only**. It is not independently validated until J7M.

### 6.4 Repaired-boundary slices

J7L must report dedicated slices for:

- `evidence_grounding` on terminal-action/non-substantive cases;
- clarification decisions where visible evidence could determine whether clarification was justified;
- failure-label near misses;
- `CONTRADICTORY_STATE` versus related labels;
- stale-source versus contradictory-state distinctions;
- missing-required-source versus unsupported-claim distinctions.

These slices are diagnostic and must retain case-level traces.

## 7. Advancement gate to J7M

J7L may advance to J7M only when **all** dataset, absolute-performance, non-regression, and repaired-boundary conditions pass.

### 7.1 Dataset integrity

Required:

- all Section 3.4 coverage requirements pass;
- human authority is complete before model reveal;
- all planned cases remain in denominator accounting;
- no case was replaced after observing model output;
- semantic registry and J7K projection identities match Section 2;
- no private evaluator semantics were introduced.

### 7.2 Absolute intervention floors

Required on the 48-case development set:

- overall criterion exact accuracy >= `0.80`;
- overall criterion within-one accuracy >= `0.97`;
- catastrophic criterion disagreement rate <= `0.03`;
- derived verdict accuracy at the selected development threshold >= `0.90`;
- failure-label micro F1 at the selected development threshold >= `0.85`;
- exact failure-label-set accuracy at the selected development threshold >= `0.75`;
- pooled failure-probability ECE <= `0.10`.

These are development advancement floors, not production or deployment thresholds.

### 7.3 Baseline non-regression

The intervention must not:

- reduce overall criterion exact accuracy by more than `0.02` absolute versus baseline;
- reduce any individual criterion exact accuracy by more than `0.05` absolute versus baseline;
- increase catastrophic criterion disagreement rate;
- increase pooled failure-probability Brier score by more than `0.02`;
- increase near-miss false-positive rate by more than `0.05` absolute.

### 7.4 Repaired-boundary requirements

Required:

- `evidence_grounding` exact accuracy on the terminal/non-substantive slice >= `0.85`;
- zero `evidence_grounding` `1 <-> 4` disagreements on that slice;
- near-miss failure-label false-positive rate <= `0.15`;
- no evidence that humans and the intervention consumed different semantic definitions.

### 7.5 Failure state

If any advancement condition fails:

- J7L status is `DEVELOPMENT_EVALUATOR_NOT_READY_FOR_HELD_OUT`;
- no qualification claim is permitted;
- no J7M model execution is permitted;
- the failure taxonomy and traces are reviewed;
- any semantic-contract change requires a new registry version;
- any model/prompt/control change requires a new J7L experiment version and a fresh development comparison.

## 8. Required evidence package

J7L must preserve:

- development constitution and SHA-256;
- case inventory and canonical case hashes;
- human projection identity;
- model projection identity;
- frozen primary/secondary assignment schedule;
- authoritative human truth artifact;
- baseline request inventory;
- intervention request inventory;
- provider responses and receipts under protected local evidence;
- case-comparison artifact;
- aggregate report;
- threshold-selection report;
- failure taxonomy;
- per-case paired trace;
- terminal J7L receipt.

Public repository artifacts must not contain protected reviewer notes, raw secrets, credentials, or unnecessary personal data.

## 9. Explicit non-claims

J7L does not prove:

- Jev is independently qualified;
- Jev may autonomously adjudicate production decisions;
- the selected threshold is independently validated;
- the 48-case development population estimates production prevalence;
- Final-342 should be rescored;
- the historical 35-case Jev calibration is invalid;
- the Final-342 governed execution failure is repaired retroactively;
- the AuraGateway A/B/C effect is established;
- deployment or production readiness.

## 10. Next gate

If and only if Section 7 passes:

`J7M_HELD_OUT_QUALIFICATION_V1`

J7M must freeze fresh held-out cases, human authority, the J7L-selected threshold, acceptance criteria, model pin, and request semantics before any held-out model reveal.

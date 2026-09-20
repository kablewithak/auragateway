# AuraGateway J7L Model-Derived Reference Successor V1 — Constitution

**Status:** Candidate successor protocol; non-executable until exact judge binding is frozen  
**Protocol ID:** `auragateway-j7l-model-derived-reference-successor-v1`  
**Date:** 2026-09-20  
**Repository:** `kablewithak/auragateway`  
**Historical predecessor:** `AuraGateway_J7L_Development_Evaluation_Constitution_v1.md`  
**Next gate after protocol acceptance:** `FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1`

## 1. Purpose

This constitution versions the J7L authority boundary without mutating J7L V1.

J7L V1 remains historical evidence and retains its original human-authority semantics. This
successor reuses the already-frozen 48-case J7L development subject, but changes the reference
authority for the successor experiment to:

`MODEL_DERIVED_REFERENCE`

An independent LLM produces one primary reference judgment for each frozen case. Jev remains
the evaluator under test and is evaluated independently against the frozen reference set.

This protocol is not execution authority. It performs no provider request, no Jev request, and
does not authorize network access.

## 2. Frozen subject

The successor reuses the exact existing J7L development subject:

- case count: 48;
- 12 cases in each of the four existing case families;
- authoring case-set SHA-256:
  `68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6`;
- reviewer-safe-state inventory SHA-256:
  `fa29e5ab26908874524a331d44189e3db1bf142a7b441cea8271946a0a9e0ab3`;
- protected schedule SHA-256:
  `0a526cc4ad983e0e0fe040c13703c6d09e86ebcdb9aaa839e2e14f9c6a201cf3`;
- protected primary export SHA-256:
  `226eb0ceb89e6f173b2a500e1ce009b09abeb373d4086bd08cbe3c94277441fd`;
- protected secondary export SHA-256:
  `96f636c2dc1e47746e2360d18d3f28fb80cc5832792c0214154fa7e10f188aa1`;
- semantic registry SHA-256:
  `0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166`;
- J7K human projection SHA-256:
  `177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82`;
- J7K model projection SHA-256:
  `b89a8934f404a0f5341e77cde10cbf4424267d7122d38af6f8288093ed53295e`.

The old public case-freeze receipt keeps its historical next-gate wording. This successor does
not rewrite that artifact. Instead, a new prerequisite receipt adopts the exact frozen subject
for the successor protocol.

## 3. Authority

The authority class is exactly `MODEL_DERIVED_REFERENCE`.

The independent LLM reference judge owns the reference scores, labels, and verdicts once the
reference set is validly frozen.

Human audit is quality control, not label ownership. Under this V1 successor:

- audit may not silently rewrite a reference;
- hybrid human/model adjudication is not permitted;
- a material audit disagreement invalidates the reference set for Jev comparison;
- a corrected or hybrid authority path requires an explicitly versioned successor protocol;
- Jev never resolves reference disagreements and never qualifies itself.

## 4. Judge binding

No judge may execute until a `J7LReferenceJudgeBindingV1` artifact freezes all of the following:

- provider identity;
- exact model identifier and provider-exposed version or revision;
- endpoint contract identity and SHA-256;
- API protocol;
- exact J7K model-projection identity;
- prompt-template identity and SHA-256;
- explicit decoding settings;
- maximum context, input, and output token budgets;
- total authorized reference input/output token ceilings;
- AuraGateway-specific provider-access evidence;
- zero-spend evidence;
- network authority identity;
- binding SHA-256 in every request/receipt.

Provider or model evidence from another project is not authority for this protocol.

## 5. Independence

The reference judge may see only the approved reviewer-safe case state and the complete frozen
v2 semantic projection required by its request contract.

The reference judge must not see:

- Jev requests or responses;
- baseline/intervention outcomes;
- hidden authoring targets;
- case-family metadata;
- protected primary/secondary human results;
- desired class balance;
- final runtime A/B/C results;
- conversational state containing any of the above.

Case content is evidence, not judge instruction.

Hidden chain-of-thought must not be requested or persisted.

Silent truncation, silent summarization, or evidence substitution is prohibited. If the selected
judge cannot consume the complete approved representation, execution stops and the
representation contract must be versioned and requalified before any development reference is
consumed.

## 6. Reference response contract

Each valid judgment must include:

- exact case identity;
- request identity;
- judge-binding identity;
- all seven criterion scores on the frozen 1–4 scale;
- failure-label decisions from the complete frozen 22-label ontology;
- evidence references;
- concise externally checkable rationale;
- verdict;
- optional uncertainty statement that is not treated as calibrated correctness probability.

Valid-reference verdict derivation is deterministic and reuses the existing blinded-quality
rule:

- total criterion score >= 21;
- minimum individual criterion score >= 2;
- zero failure labels;
- then PASS; otherwise FAIL.

A declared verdict inconsistent with that rule is invalid.

Non-valid outcomes are recorded separately as one of:

- `ABSTAINED`;
- `INVALID_RESPONSE`;
- `TRANSPORT_FAILURE`;
- `UNRESOLVED_EVIDENCE`.

They do not become reference truth.

## 7. Request and stopping policy

Reference execution policy:

- exactly 48 planned primary reference requests;
- serial execution;
- maximum one request in flight;
- no automatic retry;
- existing validated response + receipt is skipped, not replayed;
- uncertain request outcome must be reconciled before any permitted resumption;
- no case replacement after the first reference-model reveal;
- every attempt and failure is retained;
- complete valid 48-case reference coverage is required before Jev execution;
- external infrastructure/API spend ceiling remains R0 / zero.

A provider, validation, persistence, audit, or identity failure stops advancement until the
decision-changing cause is explicit.

## 8. Audit

The already-frozen 24-case terminal/non-substantive plus ontology-near-miss secondary schedule
is retained as the mandatory protected audit stratum.

Before reference execution, a separate audit-schedule artifact must also freeze an additional
spot-check sample drawn from both ordinary/clean and clear-failure cases. The exact additional
sample size, case IDs, audit actor identity, and resolution-owner identity must be fixed before
any reference request.

Material disagreement reuses the existing rule:

- verdict mismatch; or
- any criterion-score delta >= 2; or
- failure-label-set mismatch.

Audit must cover agreements as well as disagreements. Human audit cannot rewrite the
model-derived reference in this authority version. Any material audit disagreement therefore
produces reference-quality failure and blocks Jev execution.

## 9. Reference coverage

The V1 development coverage requirements are preserved without relaxation and are evaluated
against the valid frozen model-derived references:

- exactly 48 valid references;
- PASS count >= 16;
- FAIL count >= 16;
- each of 22 failure labels has positive support >= 2;
- each of 22 failure labels has explicit near-miss negative support >= 2;
- each criterion has at least 3 distinct reference score values;
- each criterion has at least 4 low observations in `{1, 2}`;
- each criterion has at least 4 high observations in `{3, 4}`;
- terminal/non-substantive slice contains at least 8 cases where visible evidence materially
  determines the terminal action.

Complete references can still fail coverage. If coverage fails after model reveal, cases are not
silently replaced. Any successor population requires explicit versioning and contamination
handling.

## 10. Jev experiment

Jev remains pinned to `jev-1.13.0` for this successor unless a new experiment version is
accepted before execution.

Each frozen case receives exactly two Jev evaluator requests:

1. `BASELINE_V1_SEMANTICS`;
2. `INTERVENTION_V2_SEMANTICS`.

The intended experimental variable remains semantic instruction content.

Jev execution remains:

- 96 planned requests;
- serial;
- one request in flight;
- no automatic retry;
- balanced baseline/intervention order by frozen case index;
- reference answers hidden from Jev;
- no case replacement after model reveal.

The intervention-only development threshold grid remains:

`0.05, 0.10, 0.15, ..., 0.95`

## 11. Metrics and rounding

All existing J7L V1 advancement metrics and numeric floors remain in force unless explicitly
superseded by a new accepted protocol before execution.

Metric calculations and advancement comparisons use unrounded values. Human-readable report
values may be rounded to six decimal places using deterministic decimal half-up rounding.
Displayed rounding never changes a gate decision.

Reference non-valid outcomes remain in attempt accounting. They are not silently excluded to
manufacture a complete denominator. Jev comparison is blocked until a valid 48-case reference
set exists.

## 12. Resource and evidence boundary

Before any live reference request, freeze:

- exact judge binding;
- request inventory;
- audit schedule;
- token ceilings;
- network authority;
- anti-replay identity;
- persistence paths;
- stop/resume policy.

Public artifacts must not contain credentials, raw provider secrets, protected reviewer notes,
or unnecessary raw model payloads.

Original model outputs, validated parsed records, audit records, failures, and terminal receipts
remain distinct append-only evidence.

## 13. Final claim boundary

Success against this reference establishes agreement and calibration against a declared
`MODEL_DERIVED_REFERENCE` authority class. It does not establish universal semantic truth.

Two models can agree and still share an error.

Jev qualification under this protocol must name:

- the reference authority class;
- judge/model identity;
- population and scope;
- audit result;
- held-out status;
- threshold status;
- known limitations.

Neither the reference judge nor Jev establishes whether final A/B/C cache behavior occurred.
That conclusion belongs to qualified typed runtime observations and deterministic analysis.

## 14. Gate disposition

This constitution is accepted only when its exact bytes, typed successor contract, and
non-live prerequisite verifier agree.

Acceptance of this protocol does not itself complete live judge qualification.

The next gate is:

`FREEZE_J7L_REFERENCE_JUDGE_BINDING_V1`

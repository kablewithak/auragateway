# ADR: Adopt Typed Deterministic Arithmetic Action Realization for Local A/B/C Evaluation

**ADR ID:** `ADR-2026-07-16-LOCAL-ABC-ARITHMETIC-ACTION-REALIZATION`  
**Status:** Proposed  
**Date:** 2026-07-16  
**Decision owner:** AuraGateway maintainers  
**Target acceptance event:** Merge of the failed-canary audit and governance PR following PR #75  
**Repository target path:** `docs/adr/2026-07-16-local-abc-deterministic-arithmetic-action-realization.md`  
**Maturity:** Production-shaped design decision; not implemented; not runtime validated  
**External spend authorized:** R0 / $0  
**GPU execution authorized:** No  
**Customer data authorized:** No  

---

## 1. Decision

AuraGateway will introduce a **typed deterministic arithmetic action-realization boundary** for arithmetic cases in the controlled Local A/B/C evaluation harness.

For the `payment-reconciliation` capability, the model will no longer be responsible for producing the final arithmetic answer directly. The model will emit a schema-constrained action containing:

- the capability identifier;
- the requested operation;
- the required operands;
- the case and turn identities.

Repository code will then:

1. validate the action strictly;
2. reject malformed, incomplete, unsupported, ambiguous, or out-of-range actions;
3. calculate the result with a deterministic pure function;
4. emit the final response through the existing structured-output contract;
5. retain machine-readable evidence for action validation and realization;
6. fail closed without hidden retries or fallback to an unvalidated model answer.

This ADR selects deterministic action realization over an immediate model upgrade.

This ADR does **not** authorize another Kaggle run, reuse of the consumed v2 canary authorization, or execution of the 72-trajectory measured benchmark.

---

## 2. Context

The controlled Local A/B/C extension exists to determine whether deterministic prefix construction and worker affinity reduce avoidable uncached prefill work without reducing task quality. The design requires machine-enforced eligibility, trustworthy cache telemetry, structured-output validity, complete attempt accounting, and a separate evidence lineage for every experiment.

The corrected schema-constrained quality/cache canary v2.3 executed three of six authorized requests:

- `incident-severity`, turn 1: passed;
- `incident-severity`, turn 2: passed with positive same-worker cache reuse;
- `payment-reconciliation`, turn 1: failed exact-answer matching;
- `payment-reconciliation`, turn 2: not observed;
- `data-sharing-policy`, turn 1: not observed;
- `data-sharing-policy`, turn 2: not observed.

The terminal payment request passed the observed harness boundaries:

- repository and authorization binding;
- prompt construction;
- canonical token normalization;
- HTTP response handling;
- JSON parsing;
- exact key-set validation;
- case identity;
- turn identity;
- confidence value;
- schema validation;
- route realization;
- prompt-token telemetry;
- cold-cache state.

It failed only:

```text
OUTPUT_ANSWER_MISMATCH
```

The zero-failure policy then aborted the run without retry or replacement. Worker cleanup completed successfully.

The execution-grounded semi-formal reasoning certificate classifies the result as:

```text
CERTIFIED_FAILED_DIAGNOSTIC
```

The certificate establishes that the prior token-counting defect was remediated for all observed requests and that the terminal divergence occurred at the model-output semantic answer boundary.

---

## 3. Evidence bindings

This ADR is constrained by the following immutable evidence:

| Evidence | Binding |
|---|---|
| Repository merge commit | `5d8170b5f33f9bff07a3f6c0db3f90b5399a1bae` |
| Failed-canary evidence archive SHA-256 | `38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1` |
| Rerun authorization fingerprint | `7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66` |
| Failed predecessor audit fingerprint | `45712ac7ab42c17bc949dc374dd1e4114ab408657b54d36509c0d241a5f74019` |
| Token-normalization policy fingerprint | `9b16866de747d67f41e4289d6f5fc9e7398da0054ee052dcc9371c5585954830` |
| Preserved scope fingerprint | `d1563d346138f10c4701492a2c1ddc7bd02bb0c5c937221b36c916361e348c64` |
| Semi-formal certificate ID | `auragateway-local-abc-sfrc-0001` |
| Semi-formal certificate JSON SHA-256 | `ed2b7a204b168904dc48ce0b70e49d7a4121750f632fde1f370494f97b782303` |
| Semi-formal certificate status | `CERTIFIED_FAILED_DIAGNOSTIC` |

These bindings must be copied into the failed-canary audit artifact created by the implementation PR.

---

## 4. Problem statement

The mixed canary currently treats deterministic arithmetic as a direct language-model answer-generation responsibility.

That boundary is weak for a reliability harness because:

1. arithmetic execution is deterministic and cheaply realizable in code;
2. a semantically wrong answer can occur despite valid schema, telemetry, routing, and cache behavior;
3. retrying the same model output would add activity without adding reliable information;
4. upgrading the model would increase cost and complexity before testing the simpler harness boundary;
5. weakening the case would reduce diagnostic value and invalidate comparison with the failed evidence.

The system needs a boundary that preserves model responsibility for intent and operand extraction while moving deterministic calculation into inspectable, testable repository code.

---

## 5. Decision drivers

The chosen design must satisfy the following drivers:

1. **Deterministic correctness**  
   Given a validated action, calculation must not depend on sampling or model behavior.

2. **Schema-first boundaries**  
   Software-used model output must become a typed contract before execution.

3. **Failure transparency**  
   Extraction, validation, execution, rendering, and telemetry failures must remain distinguishable.

4. **No hidden recovery**  
   No hidden retry, model fallback, trajectory replacement, or silent coercion.

5. **Evidence continuity**  
   The failed v2.3 evidence remains immutable and non-reusable.

6. **New-lineage comparability**  
   The intervention must have a new baseline, authorization, schedule, hashes, and report.

7. **Cache-study integrity**  
   Changes to prompts, schemas, or token shapes require fresh prefix and cache qualification.

8. **Local-first implementation**  
   No paid APIs, managed services, remote calculators, or production deployment.

9. **Maintainability**  
   The action boundary must support future deterministic capabilities without case-ID conditionals spread through the harness.

10. **Commercial proof quality**  
    The resulting artifact must demonstrate that AuraGateway distinguishes model responsibility from harness responsibility rather than solving failures with retries or larger models by default.

---

## 6. Considered options

### Option A — Typed deterministic arithmetic action realization

The model emits a validated action and operands. Repository code calculates the result.

**Advantages**

- deterministic final arithmetic;
- explicit model/harness responsibility split;
- inspectable validation and execution;
- strong unit and property testing;
- no model upgrade required;
- extensible capability-adapter seam;
- preserves the hard diagnostic case.

**Disadvantages**

- introduces an additional schema and execution boundary;
- action extraction can still fail;
- prompt and schema changes alter tokenization and require cache requalification;
- the intervention is not directly comparable to the previous model-only path without an explicit baseline report.

**Decision:** Selected.

---

### Option B — Bind a larger or different model

Keep direct answer generation but select a model expected to perform arithmetic more reliably.

**Advantages**

- smaller harness change;
- preserves a single model-output boundary;
- may improve other semantic cases.

**Disadvantages**

- increases model capability, cost, latency, memory, or deployment requirements;
- does not fix the architectural mismatch of using probabilistic generation for deterministic calculation;
- requires a new model and tokenizer evidence lineage;
- could mask weak harness design;
- no evidence currently proves that a larger model is required.

**Decision:** Rejected for the next step. Retained as a later option if typed action extraction itself is not reliable enough.

---

### Option C — Prompt-tune the existing direct-answer path

Modify instructions or examples to encourage correct arithmetic.

**Advantages**

- low implementation effort;
- no new executor.

**Disadvantages**

- treats a deterministic operation as prompt-sensitive behavior;
- risks overfitting one case;
- changes prompt identity and invalidates current cache comparability;
- offers no deterministic guarantee;
- encourages repeated prompt adjustment without a stable capability boundary.

**Decision:** Rejected.

---

### Option D — Add retries or self-correction

Retry when exact-answer scoring fails.

**Advantages**

- may improve observed success rate.

**Disadvantages**

- violates the frozen zero-retry canary contract;
- rewards more attempts instead of more informative feedback;
- increases latency and token use;
- obscures first-attempt reliability;
- cannot reuse the consumed authorization.

**Decision:** Rejected.

---

### Option E — Remove or weaken the arithmetic case

Delete the case, change `1450`, or weaken exact-answer scoring.

**Advantages**

- allows the canary to proceed more easily.

**Disadvantages**

- destroys the diagnostic value of the hard case;
- rewrites the acceptance boundary after observing the result;
- invalidates evidence continuity;
- creates an untrustworthy benchmark.

**Decision:** Prohibited.

---

## 7. Architecture decision

### 7.1 Capability boundary

Introduce a capability adapter identified independently from case ID:

```text
arithmetic.reconcile_balance.v1
```

The scheduler or case manifest may select this capability, but core execution logic must dispatch by capability identifier, not by hard-coded `payment-reconciliation` branches distributed across the codebase.

### 7.2 Model output contract

The first implementation should use a strict Pydantic v2 contract equivalent to:

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictInt


class ReconcileBalanceAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    capability: Literal["arithmetic.reconcile_balance.v1"]
    case_id: Literal["payment-reconciliation"]
    turn_index: Literal[1, 2]
    opening_balance: StrictInt
    credits: StrictInt
    debits: StrictInt
```

The exact repository implementation may use shared base contracts, enums, bounded integer types, or discriminated unions. It must preserve:

- strict integers;
- no floats;
- no numeric strings unless the contract explicitly and deterministically canonicalizes them;
- no extra fields;
- immutable validated actions;
- exact case and turn identity;
- explicit schema version;
- explicit capability identity.

### 7.3 Deterministic executor

The executor must be a pure function:

```text
closing_balance = opening_balance + credits - debits
```

It must:

- accept only a validated action;
- perform no network, filesystem, model, or tool calls;
- use explicit overflow or numeric-bound checks;
- return a typed immutable result;
- be deterministic across repeated calls;
- expose no hidden state;
- remain independently unit-testable.

### 7.4 Result contract

The executor should return a typed result equivalent to:

```python
class ReconcileBalanceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    capability: Literal["arithmetic.reconcile_balance.v1"]
    case_id: Literal["payment-reconciliation"]
    turn_index: Literal[1, 2]
    answer: StrictInt
    realization_source: Literal["deterministic_executor"]
```

The final response renderer may convert `answer` to the existing response schema's required string form only through an explicit canonicalization function.

### 7.5 Failure taxonomy

At minimum, the boundary must distinguish:

```text
action_output_missing
action_json_invalid
action_schema_invalid
action_identity_mismatch
action_capability_unsupported
action_operand_invalid
action_operand_out_of_range
action_execution_failed
result_schema_invalid
result_render_failed
quality_answer_mismatch
```

A validation failure must not be relabeled as a model refusal, cache failure, route failure, or generic exception.

### 7.6 Retry and fallback policy

For the first controlled experiment:

```text
hidden retries = 0
repair attempts = 0
fallback to direct model arithmetic = prohibited
replacement trajectory = prohibited
```

A failed action is retained as failed diagnostic evidence.

A later ADR may introduce explicit repair behavior only after first-attempt extraction reliability is measured.

### 7.7 Privacy and logging

Evidence may retain:

- action schema version;
- capability identifier;
- case and turn identity;
- validation outcome;
- canonical action SHA-256;
- operand count and bounded metadata;
- result SHA-256;
- error code;
- trace ID and run ID;
- latency and token telemetry.

Evidence must not retain:

- raw prompts;
- raw rendered prompts;
- raw model output;
- authorization headers;
- secrets;
- customer data;
- PII.

Because the current workload is synthetic, exact synthetic operands may be retained only if the evidence schema explicitly classifies them as synthetic and the privacy scan permits them. Hash-only retention remains the safer default.

---

## 8. Runtime flow

```text
synthetic case
    ↓
stable prompt + volatile turn
    ↓
model emits ReconcileBalanceAction
    ↓
strict schema validation
    ├── invalid → retain typed failure and stop
    ↓
deterministic executor
    ├── execution failure → retain typed failure and stop
    ↓
typed ReconcileBalanceResult
    ↓
canonical final-response renderer
    ↓
existing exact quality rubric
    ↓
cache, route, latency, and eligibility evidence
```

The existing direct structured-output path remains available for non-arithmetic capabilities such as incident severity and data-sharing policy.

---

## 9. Evaluation and authorization plan

This ADR authorizes design and implementation work only.

### Gate A — Contract and executor tests

Required:

- schema acceptance and rejection tests;
- exact calculation tests;
- boundary-value tests;
- wrong case/turn identity tests;
- unsupported capability tests;
- extra-field rejection;
- numeric-string and float rejection;
- deterministic repeatability;
- canonical JSON and fingerprint stability;
- privacy-field allowlist tests.

### Gate B — Diagnostic extraction cases

Create fixed hard cases that test:

- normal operands;
- operand order changes;
- zero values;
- repeated numbers;
- irrelevant distractor numbers;
- retained feedback containing previous operands;
- explicit rule conflicts;
- malformed input;
- unsupported operation;
- ambiguous or missing operands.

Each case must have an accept/reject reason and a failure label.

### Gate C — Baseline versus intervention

**Baseline**

The v2.3 direct-answer evidence remains the frozen baseline:

```text
payment-reconciliation turn 1:
OUTPUT_ANSWER_MISMATCH
```

**Intervention**

Typed action extraction plus deterministic realization.

**Scoring**

Measure separately:

- action JSON validity;
- action schema validity;
- operand extraction accuracy;
- action identity accuracy;
- executor correctness;
- final answer correctness;
- first-attempt task success;
- token counts;
- cache observation state;
- latency;
- failure class.

No aggregate success score may hide action-extraction failures.

### Gate D — Cache requalification

Because the output schema and prompt may change, the implementation must re-freeze and verify:

- rendered prompt hashes;
- normalized token-ID hashes;
- B/C prefix equality;
- eligible shared-prefix token counts;
- same-worker positive reuse;
- different-worker isolation;
- cold reset;
- worker identity;
- telemetry equations.

The v2.3 cache numbers are historical evidence, not direct expectations for the new action schema.

### Gate E — New bounded authorization

A new GPU canary requires:

- merged implementation commit;
- fixed diagnostic cases;
- passed local tests;
- frozen model and tokenizer identities;
- frozen action schema;
- frozen request count;
- zero hidden retries;
- explicit stop conditions;
- separate authorization fingerprint;
- separate notebook hash;
- new evidence filenames.

The consumed v2 authorization cannot be reused.

---

## 10. Acceptance criteria

The implementation is acceptable for a new bounded canary only when:

1. the action contract is strict, versioned, immutable, and extra-forbid;
2. the executor is pure and deterministic;
3. the final renderer is canonical and tested;
4. all failure states are typed and machine-readable;
5. direct model arithmetic is not used as fallback;
6. no hidden retry or replacement path exists;
7. fixed extraction diagnostics pass the frozen threshold;
8. unit, Ruff, formatting, mypy, and full repository tests pass;
9. prompt and schema changes have been requalified for cache comparison;
10. the failed v2.3 evidence and consumed authorization are audited immutably;
11. a new execution authorization is reviewed separately;
12. external spend remains R0 / $0;
13. no customer data, raw prompts, raw outputs, PII, or secrets enter logs;
14. the full 72-trajectory benchmark remains unauthorized.

---

## 11. Consequences

### Positive consequences

- deterministic arithmetic correctness after valid extraction;
- clearer separation between model reasoning and action execution;
- stronger failure localization;
- less incentive to add retries or upgrade models prematurely;
- reusable adapter seam for other deterministic operations;
- better regression and property testing;
- stronger commercial proof of AI reliability engineering.

### Negative consequences

- more contracts and code paths;
- an additional failure boundary at action extraction;
- new prompts and schemas require cache requalification;
- evidence lineage becomes more complex;
- the intervention cannot be presented as a direct continuation of the v2.3 model-only canary;
- the system must maintain both direct-output and action-realization paths.

### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Model extracts the wrong operands | Hard diagnostic cases, exact operand scoring, no hidden repair |
| Adapter is hard-coded to one case | Capability registry and discriminated action contracts |
| Executor hides model weakness | Report extraction accuracy separately from execution correctness |
| Prompt/schema change breaks cache comparability | New token hashes and cache qualification |
| Numeric coercion changes semantics | Strict types and explicit canonicalization |
| Arithmetic scope expands into financial logic | Keep v1 bounded to synthetic integer reconciliation |
| Result is marketed as production-ready | Preserve maturity and non-claim labels |

---

## 12. Implementation boundaries

The first implementation must remain bounded to:

```text
capability=arithmetic.reconcile_balance.v1
operation=opening_balance + credits - debits
input domain=synthetic exact integers
output domain=synthetic exact integer
```

It must not expand into:

- currency conversion;
- floating-point arithmetic;
- tax calculations;
- interest calculations;
- financial advice;
- customer ledger mutation;
- external payment systems;
- autonomous tool selection;
- production traffic.

Future capabilities require separate contracts and, where materially different, separate ADRs.

---

## 13. Rollback

Before any measured execution, rollback is straightforward:

- remove the capability adapter registration;
- retain the direct-output path;
- preserve the failed-canary audit and this ADR;
- do not reuse the v2 authorization;
- record the implementation as rejected or superseded.

After a new bounded experiment executes, its evidence must remain immutable even if the implementation is rolled back.

---

## 14. Supersession conditions

Revisit or supersede this ADR if:

1. action extraction fails the frozen diagnostic threshold;
2. the action schema destroys useful prefix stability beyond an accepted bound;
3. the executor requires domain semantics not representable as a pure deterministic function;
4. a stronger general action-realization architecture is accepted;
5. a new model demonstrably removes the need for deterministic realization while meeting cost, latency, and reliability constraints;
6. the Local A/B/C research question changes materially.

Supersession must not rewrite the v2.3 evidence or certificate.

---

## 15. Non-claims

This ADR does not claim:

- the deterministic action path is implemented;
- the action path has passed any runtime canary;
- operand extraction will be reliable;
- the payment-reconciliation case will pass after intervention;
- a larger model is unnecessary in all future work;
- all arithmetic belongs in deterministic tools;
- the incident-severity cache result generalizes to other cases;
- the 72-trajectory benchmark is authorized;
- AuraGateway is production-ready;
- Kaggle is a production environment.

---

## 16. Commercial translation

This decision strengthens the proof asset for an:

```text
Agent Harness Hardening Sprint
```

Buyer pain:

> A model can produce valid JSON and still make a deterministic operational mistake. Retrying or upgrading the model hides the weak boundary rather than fixing it.

Failure mode:

> Probabilistic answer generation is being used for an operation that should be validated and executed deterministically.

Proof asset:

- failed model-only evidence;
- execution-grounded reasoning certificate;
- typed action schema;
- deterministic executor;
- extraction-versus-execution eval report;
- no-retry failure ledger;
- cache requalification report.

Acceptance statement:

> The harness separates model intent extraction from deterministic execution, rejects invalid actions, preserves first-attempt evidence, and measures whether the intervention improves correctness without invalidating cache and routing claims.

Non-claim:

> This is not an autonomous financial agent or production payment system.

---

## 17. Decision outcome

**Selected:** Typed deterministic arithmetic action realization.

**Deferred:** New model-capability binding.

**Rejected:** Prompt tuning as the primary fix, hidden retries, trajectory replacement, weakened scoring, case removal, authorization reuse, and full measured execution.

**Next repository action:** Create a docs-and-governance PR that:

1. audits the v2.3 failed canary;
2. records the consumed authorization;
3. adds the semi-formal reasoning certificate;
4. adds this ADR;
5. adds tests preventing authorization reuse;
6. keeps GPU execution and the full measured benchmark blocked.

The arithmetic implementation begins only after that governance PR merges.

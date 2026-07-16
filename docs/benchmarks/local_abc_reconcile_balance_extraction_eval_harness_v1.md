# Local A/B/C Reconcile-Balance Action-Extraction Evaluation Harness v1

## Status

Production-shaped, locally validated evaluation harness. No model execution has occurred under this
plan. GPU execution, a new canary, and the full 72-trajectory measured benchmark remain unauthorized.

## Boundary

This harness evaluates one responsibility only:

> Can the model emit the exact typed `arithmetic.reconcile_balance.v1` action on its first attempt?

The model is responsible for extracting:

- capability identity;
- case identity;
- turn identity;
- `opening_balance`;
- `credits`;
- `debits`.

The model is not responsible for calculating or emitting the final balance. Repository code performs
`opening_balance + credits - debits` through the deterministic executor merged in PR #78.

## Evidence lineage

- Deterministic action implementation merge:
  `0e4f761de11c85ccf40d234e93a5b2d974590612`
- Failed v2.3 canary audit:
  `772821da69c7f4bd56f265b64d527ad4a07c460cb8869b62e7080455f0131b62`
- Failed v2.3 evidence archive:
  `38dfb3e727b5234e9db510e0c4735150e5721b479908c69fec4d4c8e004059f1`
- Action schema:
  `923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7`
- Prompt policy:
  `5f5415b907552bad09dfe16f0537dac0834fd42493579d91090d1b416daa2ec9`
- Fixed case manifest:
  `babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5`
- Evaluation plan:
  `53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62`

## Fixed case constitution

The manifest contains 12 accepted synthetic cases and six rejected candidates.

Accepted cases exercise:

- the exact historical payment counterexample;
- turn-two history and feedback distractors;
- reordered operand descriptions;
- explicit zero values;
- repeated operands;
- irrelevant metadata numbers;
- formatted integer amounts;
- multiline key-value layout;
- the same final answer from different operands;
- the maximum operand boundary;
- credits-first operation language;
- separation of current-turn values from prior-turn feedback.

The same-answer/different-operands case is essential. A model can accidentally produce the correct
final answer from incorrect operands. The harness therefore scores operand accuracy independently
from final-answer accuracy.

Rejected candidates retain explicit reasons. They include ambiguous ground truth, missing operands,
unsupported interest calculations, currency conversion, and duplicated cases. Missing or ambiguous
prompts are not executable until a typed refusal contract exists; guessing is not rewarded.

## Baseline

The frozen baseline is payment-reconciliation turn one from schema-canary rerun v2.3:

```text
expected answer = 1450
final answer match = false
first-attempt task success = false
failure code = OUTPUT_ANSWER_MISMATCH
```

The direct-answer baseline did not expose action JSON validity, action-schema validity, identity
accuracy, operand accuracy, or deterministic execution accuracy. Those metrics remain explicitly
`not_measured`; the harness does not invent retrospective values.

## Intervention

```text
typed action extraction
→ strict action-schema validation
→ deterministic repository execution
→ canonical final response
→ exact final-answer comparison
```

No direct model arithmetic fallback exists.

## Separate metrics

Every case produces metadata-only evidence for:

1. action JSON validity;
2. action-schema validity;
3. exact case and turn identity;
4. exact operand extraction;
5. deterministic execution success;
6. final-answer correctness;
7. complete first-attempt task success.

The report cannot hide extraction failures behind execution or answer aggregates. It retains the
model-output hash, prompt hashes, action hash, result hash, completion metadata, typed action-runtime
failure, and evaluation failure codes. Raw prompt and raw model output are excluded from report
contracts.

## Failure taxonomy

Action-runtime failures remain separate from evaluation failures.

Action-runtime examples:

- `ACTION_OUTPUT_MISSING`;
- `ACTION_JSON_INVALID`;
- `ACTION_SCHEMA_INVALID`;
- `ACTION_IDENTITY_MISMATCH`;
- `ACTION_OPERAND_INVALID`;
- `ACTION_OPERAND_OUT_OF_RANGE`;
- `ACTION_RESULT_OUT_OF_RANGE`.

Evaluation failures:

- `OUTPUT_CONTRACT_FAILED`;
- `CASE_ID_MISMATCH`;
- `TURN_INDEX_MISMATCH`;
- `OPERAND_MISMATCH`;
- `DETERMINISTIC_EXECUTION_FAILED`;
- `FINAL_ANSWER_MISMATCH`;
- `FINISH_REASON_UNEXPECTED`.

A malformed output does not receive invented operand or semantic mismatch labels. A valid action with
wrong operands may still execute; execution success is then reported separately from extraction and
final-answer accuracy.

## Regression gate

The first bounded extraction canary requires all 12 fixed cases to achieve:

```text
action JSON valid rate = 1.0
action schema valid rate = 1.0
identity accuracy = 1.0
operand accuracy = 1.0
execution success rate = 1.0
final-answer accuracy = 1.0
first-attempt task success rate = 1.0
```

Also required:

- finish reason `stop` for every request;
- zero hidden retries;
- zero repair attempts;
- zero replacement requests;
- zero direct-model arithmetic fallbacks;
- exact case order and complete score coverage.

The report contract recomputes every metric and failure count from case scores. Drifted aggregate
metrics or a mismatched gate decision fail validation.

## Privacy and safety

- synthetic data only;
- raw prompts may exist transiently for request construction but are not retained in evidence;
- raw model output may exist transiently for validation but is not retained in evidence;
- no customer data, PII, secrets, or authorization headers;
- R0 / $0 external spend;
- no model, network, filesystem, or GPU execution authorized by this slice.

## Next gate

After this harness merges, create a separate bounded action-extraction authorization that binds:

- the merged harness commit;
- exact model and tokenizer revisions;
- exact JSON Schema response format;
- the 12-case manifest and prompt policy;
- deterministic decoding;
- zero-retry and zero-replacement rules;
- evidence filenames and hashes;
- explicit stop conditions.

Only after that authorization merges may a thin Kaggle notebook be generated. Cache
requalification remains a later experiment because the new prompt and output schema alter token
shape.

## Commercial translation

This is an **Agent Harness Hardening Sprint** proof asset.

Buyer failure mode:

> The model produced valid-looking structured output, but the system could not distinguish operand
> extraction accuracy from deterministic execution or final-answer luck.

Proof delivered:

- immutable failed baseline;
- strict action contract;
- deterministic executor;
- hard fixed extraction cases;
- explicit rejected-case constitution;
- separate extraction, execution, and answer metrics;
- hash-bound, no-retry evidence report.

## Non-claims

This harness does not claim:

- that the pinned model can pass the extraction cases;
- that payment reconciliation has passed a new runtime canary;
- that a larger model is unnecessary;
- that ambiguous prompts are safely refused;
- that cache reuse survives the new prompt and schema;
- that GPU execution is authorized;
- that the 72-trajectory benchmark is authorized;
- that AuraGateway is production-ready.

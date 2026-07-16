# Deterministic Reconcile-Balance Action Realization v1

## Decision implemented

This slice implements the boundary selected by
`ADR-2026-07-16-LOCAL-ABC-ARITHMETIC-ACTION-REALIZATION`.

The model emits capability, case, turn, and operand fields. Repository code
calculates `opening_balance + credits - debits`. The model no longer emits the
final answer consumed by the quality scorer.

## Contracts and execution

- `ReconcileBalanceAction`: strict, immutable, extra-forbid action contract.
- `ReconcileBalanceResult`: deterministic executor result.
- `ReconcileBalanceRenderedOutput`: canonical existing payment output shape.
- `ActionRealizationEvidence`: hash-only lineage with no raw operands.
- `ReconcileBalanceRealizationOutcome`: cross-validated result and evidence.

Dispatch uses `arithmetic.reconcile_balance.v1`, not scattered case-ID branches.
The executor performs no network, filesystem, model, or external tool calls.

## Failure taxonomy

The boundary distinguishes missing output, malformed JSON, invalid schema,
identity mismatch, unsupported capability, invalid operands, bounded-domain
failures, executor failures, result-schema failures, rendering failures, and
quality mismatches.

No hidden retry, repair, replacement, or direct-model arithmetic fallback exists.

## Diagnostic corpus

`reconcile_balance_action_diagnostic_cases_v1.json` contains 20 synthetic hard
cases with explicit accept or reject reasons. The cases cover the historical
arithmetic, turn identity, numeric boundaries, repeated operands, key ordering,
missing and extra fields, malformed JSON, wrong identities, wrong capability,
numeric strings, floats, booleans, and unsigned-domain violations.

## Schema fingerprints

- Action schema: `923c7fb8c5abadf80c65e55516330e7ec48bd5147ec24662a8cc5dbeed0b76a7`
- Result schema: `660d8b3bdf6e1eaace8e48419a56d3586f5168d18a3b78e114c7dd143bc4cb46`
- Rendered output schema: `48a6fa77df13c92a11e2d82bbe3a864761927b278eaa9c40e2dfd0241904616c`

## Privacy and authorization

- synthetic data only;
- raw prompt, raw model output, and raw action retention prohibited in evidence;
- R0 / $0 external spend;
- no customer data, PII, secrets, or authorization headers;
- GPU execution unauthorized;
- full measured benchmark unauthorized.

## Next gate

After merge, build a fixed extraction-evaluation harness comparing the frozen
v2.3 direct-answer baseline with typed action extraction plus deterministic
execution. Report extraction accuracy, executor correctness, and final-answer
correctness separately. Cache requalification and a new GPU authorization remain
later gates.

## Non-claims

This slice does not claim that a model can reliably emit the action, that the
payment case passes a runtime canary, that cache behavior remains comparable,
that a Kaggle run is authorized, or that AuraGateway is production-ready.

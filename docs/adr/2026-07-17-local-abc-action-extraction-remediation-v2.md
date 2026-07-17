# ADR: Version the Reconcile-Balance Action-Extraction Remediation

**ADR ID:** `ADR-2026-07-17-LOCAL-ABC-ACTION-EXTRACTION-REMEDIATION-V2`
**Status:** Accepted for local implementation
**Date:** 2026-07-17
**Execution authorization:** Not granted
**GPU execution:** Not permitted
**External spend:** R0 / $0
**Customer data:** Not used

## Context

The governed 12-request action-extraction canary completed with a clean harness but failed the
semantic quality gate:

```text
action JSON validity        12/12
action schema validity      12/12
identity accuracy           12/12
deterministic execution     12/12
exact operand accuracy      10/12
exact final-answer accuracy 10/12
infrastructure failures     0
hidden retries              0
```

PR #85 preserved this result as immutable evidence and closed the consumed authorization. The two
hash-resolved failures are distinct:

```text
FORMATTED_INTEGER_LEADING_COMPONENT_DROPPED
KEY_VALUE_CREDIT_DEBIT_ROLE_REVERSAL
```

The first failure requires a deterministic harness control because losing digits from `R1,200`
cannot be made reliable through schema validity alone. The second failure remains a semantic field
binding problem: the model retained all values but assigned credits and debits to the wrong fields.

The next intervention must preserve the existing deterministic arithmetic action contract, avoid
retry laundering, preserve all 12 historical cases, add hard diagnostic coverage, and remain local
until a separately reviewed authorization exists.

## Decision

Adopt a three-part, versioned remediation candidate:

1. **Deterministic integer lexical normalization**
   - Remove supported currency markers immediately attached to integer amounts.
   - Remove integer grouping commas while preserving every digit.
   - Leave decimal values unchanged rather than silently coercing them.
   - Perform no semantic field assignment, arithmetic, currency conversion, or case-specific repair.

2. **Semantic role-bound instruction v2**
   - Require binding by explicit field label rather than position, line order, or magnitude.
   - State that `opening_balance`, `credits`, and `debits` are not interchangeable.
   - Explicitly prohibit swapping credits and debits.
   - Preserve the direct-answer prohibition and zero-retry policy.

3. **Role-described response schema v2**
   - Preserve the existing `ReconcileBalanceAction` schema and deterministic executor.
   - Add field descriptions to the model-facing JSON Schema response format.
   - Version the response-format identity separately from the unchanged action schema.

The intervention is defined in repository artifacts but does not authorize a model request.

## Why this boundary

The intervention separates deterministic formatting cleanup from probabilistic semantic extraction:

```text
raw synthetic source
    ↓
deterministic integer lexical normalization
    ↓
role-bound v2 extraction prompt and response schema
    ↓
strict existing ReconcileBalanceAction validation
    ↓
existing deterministic arithmetic executor
```

The normalizer is intentionally lexical. It does not parse a complete business action. This keeps
the model responsible for semantic role extraction while preventing avoidable digit loss caused by
currency and grouping notation.

## Alternatives considered

### Prompt-only remediation

Rejected as insufficient. It would leave formatted-integer correctness entirely probabilistic and
would not harden the harness boundary that already has deterministic information available.

### Deterministic semantic parser for the full action

Rejected for this slice. A full parser would replace the extraction task, increase coupling to
prompt phrasing, and make the canary measure parser coverage rather than model extraction quality.

### Post-output repair or semantic swapping heuristic

Prohibited. Swapping fields after observing an incorrect action would create a hidden repair path,
weaken first-attempt evidence, and risk correcting one case while corrupting another.

### Retry or self-correction

Prohibited. The baseline authorization allowed one attempt per case. More requests would increase
activity without preserving a clean first-attempt comparison.

### Larger model

Deferred. No evidence yet shows that a model change is required after the smaller harness controls
are tested. A model change would also create a separate model and tokenizer lineage.

### Remove or weaken failed cases

Prohibited. Both failures are hard diagnostic assets and remain in the complete suite.

## Evaluation constitution

The v2 remediation manifest contains:

```text
12 historical cases preserved exactly and in order
4 new diagnostic cases
16 total cases
```

The new diagnostics cover:

```text
multiple integer grouping separators
spaced currency markers
credits-first key-value ordering
mixed key-value delimiters with debits first
```

The requalification gate remains all-or-nothing:

```text
JSON validity                 100%
schema validity               100%
identity accuracy             100%
operand accuracy              100%
deterministic execution       100%
final-answer accuracy         100%
first-attempt task success    100%
infrastructure failures       0
hidden retries                0
repairs                       0
replacement requests          0
```

The complete 16-case suite must run. Executing only the two historical failures is prohibited.

## Artifact identities

```text
parent case manifest SHA-256:
babfd460048784991041957fc50e29853d6caa29ba195207bd8f2ad1088bbbf5

parent evaluation plan SHA-256:
53a9dc8f3418b4df86151ad9763d44ddd16179ed5d4ca7ac505c3b2f7e401b62

parent evidence audit SHA-256:
8e0294686db03adab55e3341914417bb0dfd630e97adc6fe36a9d671d36744bd

normalization policy SHA-256:
7caa66d8bba36260fb97f822fdeea4f4badc16b1add1b5ed9eb5896be6257ef8

prompt policy SHA-256:
750a6f89c7ada7b9d508eaf143214e3d93e6456bb4b3586afa7dc089f8dcfc4c

response schema SHA-256:
bb81d7bbb98524b748cb91eb3cc0f4083f8d7df430016caa42724396af72687d

remediation case manifest SHA-256:
82037903ab9d944a88e6d1460a001a648308163ed7dae735cbf01359737ae4aa

remediation plan SHA-256:
ebeb86b583eeff4f8b2c3ea973f67d6aaba1368a4386eb53737179ed3fd64a36
```

## Privacy and security

The remediation uses synthetic data only. Runtime evidence may retain hashes, counts, policy IDs,
case IDs, and failure codes. It must not retain raw prompts, raw rendered prompts, raw model output,
raw actions, credentials, secrets, PII, or customer data.

The normalizer returns transient text for execution but excludes both source and normalized text from
its canonical evidence serialization.

## Consequences

### Positive

- Digit preservation for supported integer formatting becomes deterministic.
- Field-role requirements become explicit in both instructions and response-schema descriptions.
- Historical evidence remains immutable.
- The action contract and deterministic executor remain unchanged.
- The intervention is independently testable without a GPU.
- No hidden retry, parser fallback, model upgrade, or direct arithmetic fallback is introduced.

### Negative

- Semantic field binding is still model-dependent and must be measured.
- Prompt and response-format identities change, so old cache and quality results cannot be reused as
  intervention evidence.
- The lexical normalizer deliberately does not support decimals, exchange rates, or arbitrary
  financial notation.
- A new notebook binding and bounded authorization will be required before execution.

## Next gate

```text
bounded_action_extraction_v2_authorization_review
```

That later gate may authorize one attempt for each of the 16 fixed cases. It must not authorize the
full measured A/B/C benchmark or cache-effect claims.

## Non-claims

This ADR does not claim:

- that the two failed cases are fixed in model execution;
- that the v2 intervention improves quality;
- that schema descriptions guarantee semantic correctness;
- that the lexical normalizer is a general financial parser;
- that decimals or currency conversion are supported;
- that another GPU run is authorized;
- that cache savings are measured;
- that the full A/B/C benchmark is eligible;
- that AuraGateway is production-ready.

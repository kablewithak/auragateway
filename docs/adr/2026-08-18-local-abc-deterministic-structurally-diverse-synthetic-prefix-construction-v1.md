# ADR: Deterministic Structurally Diverse Synthetic Prefix Construction V1

Date: 2026-08-18

## Status

Accepted.

This decision governs the controlled local qualification harness only.
The concrete canonical corpus is not yet frozen, C4 is not qualified,
P5/P6 are not requalified, and runtime execution remains unauthorized.

## Context

AuraGateway's North-Star benchmark asks whether deterministic prefix construction
and worker affinity reduce avoidable repeated prefill work while preserving task
quality. Before P5/P6 or the final measured A/B/C benchmark can be interpreted,
the controlled local harness must first establish a request construction that is
both deterministic and behaviorally qualified.

The historical long-context qualification request derived most of its synthetic
context length by repeating one short cache-context body 24 times. The 24
repetitions were experimental stress apparatus rather than 24 genuine business,
conversation, or semantic units.

The governed differential lineage established three relevant observations:

1. A 1x control produced 3/3 exact-object responses while the 24x repeated-context
   condition produced 0/3. This established the long/repeated-context condition as
   necessary relative to the 1x control without isolating length or repetition as
   the sole cause.
2. A token-count-matched 899-token A/B/C differential produced A=0/3, B=0/3,
   and C=3/3. The successful C condition materially reduced exact token-pattern
   repetition while preserving total prompt-token count and broad semantic class.
3. The later cumulative-length-locked B-vs-D differential produced B=0/3 and
   D=3/3. D restored behavior while preserving B's complete cumulative prompt-token
   trajectory and changing the neutral marker nouns across the 24 repeated
   sentence templates.

Together these results make high exact internal repetition an avoidable and
demonstrably risky property of the synthetic qualification construction. They do
not establish exact repetition as the sole or root cause, do not establish an
exact threshold, and do not establish marker lexical or semantic novelty as the
causal mechanism.

The existing 24 repetitions therefore must not be promoted into a false logical
ontology such as 24 numbered records merely because the diagnostic lineage happened
to use 24 repeated bodies.

## Decision

The controlled local qualification harness will represent long reusable synthetic
context as one versioned, deterministic, structurally diverse canonical corpus.

The canonical corpus is a single synthetic context artifact. It is not a runtime
collection of pseudo-records and does not acquire logical sub-unit identities from
the historical 24x repetition design.

The following invariants govern its implementation.

### 1. Canonical and versioned bytes

A corpus version is authored once and then treated as canonical.

Equivalent requests using that corpus version must receive identical corpus bytes.
Any intentional byte-level change creates a new corpus version and requires a new
identity and qualification decision.

Runtime randomization, shuffled wording, stochastic marker selection, timestamp
insertion, and request-specific mutation are prohibited.

### 2. Structural diversity without repetition-derived length

The corpus must use deterministic lexical and structural diversity.

Its long-context workload must not derive primarily from exact repetition of a
short synthetic body. Exact duplication may occur naturally at small scales, but
construction may not use repeated short-body multiplication as the principal
length mechanism.

The corpus must remain synthetic, semantically neutral with respect to the final
probe, and free of customer data or other sensitive payloads.

### 3. Control-plane data stays outside the semantic prefix

Transaction identifiers, authorization state, observation ordinals, timestamps,
worker identity, platform receipts, execution metadata, evidence identifiers, and
other control-plane values must not be injected into the reusable semantic prefix.

A deterministic constructor that inserts unique operational metadata into every
request is not a reusable-prefix constructor for this benchmark.

### 4. Rendered token identity is authoritative

Source-text boundaries are not tokenizer boundaries.

Static qualification must therefore inspect the complete rendered/tokenized request
under the pinned tokenizer and chat template. Source strings, sentence joins, or
Python object boundaries are insufficient authorities for token identity.

Before behavioral C4 execution, the concrete request contract must freeze the
canonical corpus version together with the role topology, fixed system instruction,
assistant acknowledgement, final probe object, chat-template behavior, tokenizer
identity, and relevant generation contract.

### 5. Preserve a meaningful long-context stress regime

The historical 899-token requests were valuable differential controls, but 899 is
not declared a permanent architectural invariant by this ADR.

The first concrete successor must remain in a meaningfully comparable long-context
stress regime. It may not obtain qualification merely by shrinking the request
enough to remove the previously observed stress boundary.

The exact target length or bounded range must be declared and frozen before any
behavioral result is observed.

### 6. Static representation measurements are rejection guardrails, not C4 evidence

Before behavioral execution, the fully rendered candidate must be measured against
the governed historical repeated and diversified constructions using predeclared
representation diagnostics, including repetition-sensitive measurements where
available.

A candidate with representation characteristics materially similar to the known
failing repeated construction must be rejected or explicitly re-reviewed before
behavioral execution.

Passing static representation checks does not qualify C4 and does not establish
model correctness.

### 7. Preserve future causal contrasts

For the final benchmark, deterministic-prefix conditions B and C must share the
same canonical deterministic prefix constructor and corpus identity. Worker
affinity is the intended B-to-C intervention.

Conceptually:

`B_PREFIX_CONSTRUCTOR == C_PREFIX_CONSTRUCTOR`

Changing prefix construction between B and C would contaminate the affinity
estimand and requires redesign before execution.

## Scope

This ADR is normative for the synthetic controlled local qualification harness and
for the deterministic-prefix construction used by its successor C4/P5/P6 path.

It establishes an engineering principle for that harness: reusable prefix content
must be canonical, deterministic, inspectable, and free from gratuitous exact
repetition.

It does not authorize applying the same concrete corpus or construction strategy to
production AuraGateway prompts. Production transfer requires separate evidence and
a separate decision appropriate to the production workload.

This ADR also does not satisfy or supersede the repository's separately planned
general `ADR-0003 Canonical Context Serialization`; its scope is narrower.

## Alternatives rejected

1. **Retain the historical repeated short body.**
   Rejected because exact short-body repetition is an avoidable property already
   associated with governed failure under the current qualification lineage.

2. **Ordinal section corpus such as `section_01` through `section_24`.**
   Rejected because the historical 24 repetitions have no genuine logical
   identities. Numbering them would manufacture structure from experiment lineage
   and could introduce its own periodic token pattern.

3. **Canonical JSON or typed-record sequence.**
   Rejected for this synthetic context because repeated keys, punctuation, and
   record framing may create another artificial recurrence pattern while adding a
   schema that the workload does not semantically require.

4. **Adopt the successful D marker-diversified comparator directly.**
   Rejected because D is a mechanism-discrimination intervention, not a validated
   general prompt architecture. Its success motivates the decision to avoid
   gratuitous exact repetition but does not prove that its 24-marker sentence
   construction is the optimal successor.

5. **Generate random or request-specific long filler.**
   Rejected because it breaks deterministic prefix identity and weakens causal
   interpretability.

## Consequences

The harness gains a stable, hashable reusable-prefix artifact whose identity can be
inspected before execution. Future B/C comparison can isolate worker affinity
without silently changing prefix construction.

The design requires more deliberate corpus authoring and static inspection than
multiplying a short body. That additional work is accepted because it removes an
artificial construction artifact from the qualification path.

The concrete corpus can still fail behavioral C4. Architecture acceptance is not
behavioral qualification.

Any corpus byte change after freeze creates a new version and invalidates prior
identity-based qualification for that changed corpus.

A synthetic corpus remains an approximation of production workloads. Success here
does not establish production prompt reliability, production cache effectiveness,
or production readiness.

## Qualification state

- Architecture decision: `ACCEPTED`
- Concrete canonical corpus: `NOT_YET_FROZEN`
- C4 behavioral qualification: `NOT_QUALIFIED`
- P5: `NOT_REQUALIFIED`
- P6: `NOT_REQUALIFIED`
- Final measured A/B/C: `NOT_MEASURED`
- New runtime execution authorized by this ADR: `false`

## Non-claims

This ADR does not establish:

- exact repetition as the sole or root cause of the historical failure;
- aligned 16-token recurrence as independently causal;
- marker lexical novelty as causal;
- marker semantic novelty as causal;
- an exact repetition or context-length threshold;
- context length alone as causal;
- a prefix-cache defect;
- C4 qualification;
- P5 or P6 requalification;
- a measured North-Star A/B/C effect;
- production readiness;
- textual segment boundaries as tokenizer boundaries.

## Reversal condition

Reconsider or supersede this ADR if any of the following occurs:

1. the frozen concrete corpus retains representation characteristics materially
   similar to the known failing repeated construction;
2. the frozen concrete corpus fails its predeclared C4 behavioral qualification;
3. P5 establishes that this construction prevents or materially degrades the
   intended reusable-prefix behavior; or
4. later evidence establishes that another construction satisfies the same
   invariants with lower complexity.

Reversal must preserve the governed evidence that motivated this decision. A failed
successor is evidence for redesign, not authority to rewrite historical results.

## Next gate

`DESIGN_AND_FREEZE_CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1`

This next gate is static. It does not authorize model execution, a Kaggle run, a new
execution authorization, P5/P6 requalification, or modification of the governed
B-vs-D result.

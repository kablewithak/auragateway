# Nimbus Relay Development Retrieval Set

## Document control

```text
Asset ID: nimbus-relay-development-retrieval-v1
Version: 1.0.0
Split: development
Accepted cases: 24
Rejected proposed cases: 8
Status: accepted development asset
Held-out cases included: 0
```

## Purpose

The development set exposes concrete retrieval weaknesses before the retrieval configuration is
frozen.

It is used to compare:

- chunking candidates;
- sparse retrieval;
- the later dense retrieval candidate;
- top-k behaviour;
- metadata filtering;
- stale-source controls;
- near-duplicate displacement;
- source coverage for later citation support.

It must not be used as held-out confirmation evidence.

## Accepted-case contract

Every accepted case includes:

```text
case_id
case_family
failure_hypothesis
query_text
top_k
filters
relevance_judgments
required_sources
forbidden_sources
near_duplicate_sources
expected_terminal_decision
required_information_gain
acceptable_variants
failure_labels
accept_reason
difficulty_reason
evaluation_split
```

Relevance is labelled at source level:

```text
3 = directly authoritative for the requested answer
2 = materially supporting or conflict-resolving evidence
1 = related evidence that may help but is not sufficient
```

Required sources must have relevance grade two or three.

Forbidden sources are not relevant and represent a concrete failure if retrieved in the top-k
result. They are commonly stale, wrong-language, wrong-version, or unsupported substitutes.

## Case-family coverage

The 24 accepted cases cover:

- version conflicts;
- similar error codes;
- missing retry-safety parameters;
- incomplete documentation;
- near-duplicate displacement;
- multi-source grounding;
- metadata filtering;
- unsupported requested behaviour;
- exact procedures;
- SDK-language variants.

Material diagnostic pressures include:

- 24-hour versus seven-day API-key lifetime;
- 72-hour versus 48-hour webhook retry windows;
- 48-hour versus 24-hour idempotency retention;
- 409 versus 422 resolution boundaries;
- ambiguous non-idempotent write retries;
- raw HTTP versus SDK pagination;
- Markdown versus JSON event catalogues;
- incomplete upload, incident, custom-role, and sandbox guidance;
- Python versus JavaScript SDK contamination.

## Rejected-case policy

Rejected cases are retained rather than silently discarded.

The current rejected set includes examples rejected because they are:

- ambiguous;
- trivial;
- duplicates of accepted cases;
- ungrounded in the corpus;
- non-diagnostic;
- privacy-unsafe.

A rejected case may not re-enter the accepted set without a new version and an explicit resolution of
the stored rejection reason.

## Split protection

The contracts reject a development case labelled as held out.

The development set contains no held-out cases, labels, or expected results. The held-out set will be
created only after the retrieval configuration is frozen and will use separate paths and hashes.

## Privacy and trace boundary

Raw development queries are versioned in the accepted asset because the corpus is fully synthetic.

Persisted candidate result artifacts remove:

- raw query text;
- retrieved chunk content;
- complete document text.

They retain:

- query SHA-256;
- source and chunk IDs;
- rankings;
- metric values;
- missing required sources;
- forbidden sources found;
- metadata-filter violations;
- candidate configuration hashes.

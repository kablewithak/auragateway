# Nimbus Relay Gate 1 Held-Out Retrieval Report

## Decision

```text
Proof gate: Gate 1 — Retrieval Readiness
Decision: BLOCKED
Held-out set: nimbus-relay-held-out-retrieval-v1
Accepted cases: 12
Passing finalists: 0 / 2
Retrieval freeze permitted: no
Measured execution permitted: no
```

## Why the gate is blocked

Both finalists retrieved every required source across all 12 cases, but neither passed the complete reliability contract.

The blocked result is intentional evidence. Gate 1 does not reward recall alone while ignoring forbidden sources, excess unsupported evidence, ranking weakness, or near-duplicate displacement.

## Candidate results

| Metric | Dense section-aware top-5 | BM25 fixed-window top-5 | Gate |
|---|---:|---:|---:|
| Recall@k | 1.000000000000 | 1.000000000000 | >= 0.98 |
| Correct source in top-k | 1.000000000000 | 1.000000000000 | >= 1.00 |
| All required sources in top-k | 1.000000000000 | 1.000000000000 | >= 0.95 |
| Citation-support readiness | 0.833333333333 | 0.833333333333 | >= 0.90 |
| MRR | 0.944444444444 | 0.944444444444 | >= 0.95 |
| nDCG@k | 0.924370716649 | 0.926319958257 | scored |
| Failure-weighted case pass | 0.875000000000 | 0.875000000000 | >= 0.90 |
| Unsupported-source retrieval | 0.266666666667 | 0.266666666667 | <= 0.11 |
| Unwanted stale retrieval | 0.000000000000 | 0.000000000000 | <= 0.00 |
| Metadata-filter violations | 0.000000000000 | 0.000000000000 | <= 0.00 |
| Near-duplicate displacement | 0.500000000000 | 0.000000000000 | <= 0.00 |
| Final score | 72.104818277600 | 82.124310693700 | hard-gate subordinate |

BM25 fixed-window has the stronger held-out score, but it still cannot be selected because it fails four hard gates.

Dense section-aware additionally fails the zero-displacement gate.

## Shared diagnostic failures

### `ho-ret-002` — OAuth grant contamination

Both finalists rank the required client-credentials source first, then also retrieve the forbidden refresh-token error catalogue.

This means the correct source is present, but the support set still contains evidence from an inapplicable OAuth grant path.

### `ho-ret-011` — SDK language contamination

Both finalists rank the required JavaScript SDK source first, then also retrieve the forbidden Python SDK guide.

This confirms that the SDK-language failure observed in development generalizes to held-out wording.

## Additional ranking weaknesses

### Dense section-aware pagination displacement

For `ho-ret-004`, the SDK pagination guide ranks ahead of the requested raw HTTP guide.

This causes:

- reciprocal rank of `0.333333333333` for the first relevant source;
- near-duplicate displacement;
- failure of the zero-displacement hard gate.

### BM25 webhook cross-area ranking

For `ho-ret-005`, BM25 ranks a webhook delivery-schedule source before the required signature and event-catalogue sources.

Every required source remains in top five, but the first relevant source appears at rank three, contributing to the MRR miss.

## Unsupported-source noise

The held-out set deliberately contains narrow and multi-source questions. Both finalists return substantial additional evidence inside top five.

Examples include:

- the incomplete upload procedure beside upload-error and retry sources;
- prose event catalogues beside machine-readable event requirements;
- delivery-schedule guidance beside signature verification;
- parallel OAuth and SDK variants.

The resulting unsupported-source rate of `0.266666666667` is materially above the frozen maximum of `0.11`.

## Gate interpretation

The held-out evidence does not confirm or reverse the development recommendation because neither finalist is promotion eligible.

The correct machine decision is:

```text
Status: gate_1_blocked
Selected retriever: none
Retrieval freeze manifest: prohibited
Required next gate: held_out_retrieval_remediation
```

## Required remediation

The next slice should harden the retrieval contract rather than tune the held-out labels.

The smallest maintainable remediation is:

1. add typed document-variant metadata for language, interface, grant type, and representation format;
2. add deterministic query-intent extraction for those dimensions;
3. apply the resulting filters before ranking;
4. rerun development cases and preserve before/after evidence;
5. create a new held-out set version rather than modifying held-out v1;
6. reopen Gate 1 only after the new policy is frozen.

Do not lower thresholds or remove forbidden-source judgments to manufacture a pass.

## Validation evidence

The Gate 1 harness verifies:

- frozen held-out and rejected-set hashes;
- development-set hash continuity;
- development selection policy and report hashes;
- finalist rank and manifest identity;
- source-reference validity;
- cross-split query separation;
- deterministic case results and scorecards;
- deterministic blocked decision;
- absence of an unauthorized retrieval freeze manifest.

## Evidence boundary

This report supports:

- held-out retrieval evaluation completed;
- Gate 1 correctly blocked;
- the current finalists have complete held-out source recall;
- OAuth grant, SDK language, ranking, and unsupported-evidence weaknesses remain.

It does not support:

- a frozen retrieval configuration;
- Gate 1 completion;
- answer-generation quality;
- runtime benchmark execution;
- production readiness.

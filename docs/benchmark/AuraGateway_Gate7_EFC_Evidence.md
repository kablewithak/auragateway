# AuraGateway Gate 7 — EFC Evidence Contract

## Purpose

This artifact records the first deterministic Gate 7 boundary for practical feedback-evidence trace review.

AuraGateway evaluates feedback as separate evidence properties rather than rewarding raw tokens, retries, retrievals, tool calls, or agent steps.

## Implemented boundary

The slice adds typed metadata-only evidence for:

- validity;
- informativeness;
- novelty and redundancy;
- retention;
- feedback-linked action change;
- required-subgoal coverage;
- task sufficiency.

No universal EFC score is produced.

## Frozen fixture evidence

| Item | Value |
|---|---:|
| Fixture count | 11 |
| Passing controls | 2 |
| Negative controls | 9 |
| Task-sufficient fixture trajectories | 3 |
| Universal EFC score reported | No |
| Measured execution permitted | No |

Task-sufficient fixture count is greater than passing-control count because one deliberately redundant trajectory still reaches the task outcome while correctly failing the EFC evidence-quality boundary.

## Negative controls

The fixed set covers:

- invalid feedback;
- unknown validity;
- irrelevant feedback;
- redundant feedback;
- novelty-status inconsistency;
- valid but unretained feedback;
- unknown retention;
- incomplete task state;
- missing required-subgoal evidence.

## Metamorphic controls

- Adding duplicate evidence cannot improve a passing trajectory.
- Duplicate evidence raises the redundant-event rate.
- Reordering distinct same-turn events does not change aggregate rates or task sufficiency.
- Public report records retain `universal_efc_score: null` and explicitly state that no universal score is reported.

## Artifact hashes

| Artifact | SHA-256 |
|---|---|
| `fixtures.json` | `0551e376099a678b7e139d4f2c197172144e1d413e913a1c44899eafa8b26db4` |
| `report.json` | `e83c1921c10e4aa8d04c17376d96865663fd836172dd62fef101999a993b44a4` |
| `manifest.json` | `7e856227772b38d4b66cd41936e0ad695747544f733942d4165c80dd1f71573e` |
| episode manifest | `3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b` |
| Gate 6 quality manifest | `c35e95240ab8c2a76d8f7e1b4ce0283142ec6363f9d49dd72eeb9b31fa62d60b` |

## Reproduction

Normal verification:

```powershell
python -m auragateway.evals.feedback_runner verify --repo-root .
```

`build` is reserved for intentional versioning of fixtures, contracts, evaluation rules, or upstream evidence bindings.

## Privacy boundary

The public evidence contains IDs, hashes, statuses, counts, rates, and bounded failure codes only.

It does not contain raw prompts, user messages, retrieved documents, candidate outputs, provider payloads, feedback prose, secrets, PII, or hidden reasoning.

## Claim boundary

This slice proves deterministic practical EFC trace checks on frozen synthetic metadata-only trajectories.

It does not prove a universal EFC score, complete feedback-value measurement, measured A/B/C feedback improvement, arbitrary semantic relevance, provider performance, deployment safety, or production readiness.

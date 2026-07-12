# ADR-0008: EFC Evidence Contract

- **Status:** Accepted
- **Date:** 2026-07-12
- **Decision version:** 1.0.0
- **Decision owners:** AuraGateway project maintainers
- **Applies from:** Phase 6
- **Supersedes:** None

## Context

AuraGateway must distinguish useful feedback from raw activity. More tokens, retries, retrieved chunks, tool calls, or agent steps do not prove that a trajectory improved. A feedback event is useful only when the evidence is sufficiently trustworthy, relevant to the active subgoal, non-redundant, retained in state, and sufficient to support later task progress.

The project does not reproduce the complete Effective Feedback Compute research methodology and must not emit a fabricated universal EFC score. It needs a practical, inspectable trace discipline that exposes why feedback helped, failed, repeated existing evidence, disappeared from state, or remained insufficient.

The functional episode set already contains diagnostic failures for redundant feedback, unretained feedback, noisy context, contradictory state, and task insufficiency. Gate 7 converts that doctrine into typed metadata-only evidence and deterministic fixed-case checks.

## Decision

AuraGateway will record one typed `FeedbackEvidenceEvent` per feedback-bearing observation and aggregate those events into a metadata-only trajectory summary.

Each event records:

- trace and turn identity;
- event and subgoal identity;
- bounded evidence-source type;
- a SHA-256 evidence fingerprint;
- validity status and validity-evidence digest;
- informativeness status;
- novelty status;
- explicit retention state and retention location;
- optional before/after action fingerprints;
- task-sufficiency status;
- a bounded reason code.

Raw prompts, user messages, documents, model outputs, hidden reasoning, and free-form feedback text are not part of this contract.

## Validity

Known validity requires an evidence digest tied to a validator, retrieval contract, source-metadata check, deterministic rule, provider error, or user clarification. Unknown validity carries no invented proof.

An invalid or unknown event cannot become useful merely because it triggered more activity.

## Informativeness

Informativeness is evaluated against the event's declared subgoal. The first implementation uses frozen synthetic fixture labels rather than pretending arbitrary semantic relevance can be inferred universally.

An irrelevant or unknown-informativeness event cannot satisfy a required subgoal.

## Novelty and non-redundancy

Novelty is checked against prior evidence fingerprints in the same trajectory.

- `new` is valid only when the fingerprint has not appeared earlier;
- `redundant` is valid only when the fingerprint has appeared earlier;
- inconsistent novelty declarations receive a stable failure code;
- repeated evidence is retained as evidence of redundancy rather than discarded.

Adding duplicate feedback must never improve the trajectory result.

## Retention

A retained event requires an explicit metadata-safe state location. Unretained or unknown-retention events cannot claim a state location.

Valid but unretained feedback receives a stable failure code because evidence that disappears cannot reliably influence later decisions.

## Action change

When action-change evidence is known, before and after action fingerprints are required. The boolean action-change field must agree with whether the fingerprints differ.

Action change is reported separately. It is not required for every useful event and is not treated as a universal reward.

## Task sufficiency

A trajectory is task-sufficient only when:

- the task is marked complete;
- the expected terminal decision was reached;
- every required subgoal is completed;
- every required subgoal has at least one valid, informative, new, retained event;
- at least one event explicitly records sufficient evidence.

Task sufficiency remains a bounded fixture-level decision. It is not inferred from token volume or step count.

## Reported metrics

AuraGateway reports separate evidence rates:

- valid feedback-event rate;
- redundant feedback-event rate;
- retained valid feedback-event rate;
- unretained valid feedback-event rate;
- feedback-linked action-change rate;
- task-sufficiency pass status.

Denominators are explicit in the implementation. No composite universal EFC score is calculated or reported.

## Privacy and evidence handling

Public EFC reports retain only:

- IDs;
- hashes;
- statuses;
- bounded failure codes;
- counts;
- rates;
- task-sufficiency outcomes.

They do not retain raw feedback, prompts, documents, user messages, candidate outputs, secrets, PII, reviewer notes, or hidden reasoning.

## Consequences

### Positive

- Useful feedback is separated from raw agent activity.
- Duplicate and noisy evidence cannot be rewarded as progress.
- Retention failures become inspectable.
- Action-change evidence is explicit rather than inferred from narrative traces.
- Task sufficiency has a deterministic bounded rule.
- Public reports remain metadata-safe.
- Later A/B/C trajectories can use the same event and aggregation contract.

### Negative

- Informativeness still requires frozen fixture judgment or controlled review.
- Evidence fingerprints depend on stable upstream canonicalization.
- The contract does not establish a universal real-time EFC metric.
- Passing synthetic fixtures is necessary but insufficient for measured Gate 7 completion.

## Required verification

The first Gate 7 slice must prove that:

- valid, informative, new, retained feedback can pass;
- useful retained feedback can pass without forcing an action change;
- invalid feedback fails;
- unknown validity fails;
- irrelevant feedback fails;
- duplicate feedback is labelled and cannot improve a trajectory;
- inconsistent novelty declarations fail;
- valid but unretained feedback fails;
- unknown retention fails;
- missing required-subgoal evidence fails;
- incomplete tasks fail sufficiency;
- adding duplicate evidence cannot improve a passing trajectory;
- distinct-event ordering at the same turn does not change aggregate rates;
- public reports contain no raw feedback content;
- fixture and report hashes reproduce;
- no universal EFC score is reported.

## Gate status

This decision establishes the typed and deterministic synthetic EFC evidence boundary.

Gate 7 remains open until feedback evidence is captured and reviewed on measured benchmark trajectories.

## Claim boundary

This ADR and its first implementation slice prove deterministic validity, informativeness, novelty, retention, action-change, and task-sufficiency behavior on fixed synthetic metadata-only trajectories.

They do not prove complete EFC measurement, arbitrary semantic relevance, universal feedback value, measured provider-condition improvement, benchmark readiness, deployment safety, or production readiness.

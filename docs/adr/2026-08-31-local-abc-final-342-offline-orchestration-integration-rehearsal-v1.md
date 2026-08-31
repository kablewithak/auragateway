# ADR: Final-342 Offline Orchestration and Integration Rehearsal V1

Date: 2026-08-31

## Status

Proposed for acceptance.

## Context

The final-342 experiment now has accepted planning, runtime, evidence-production,
protected-review, measured-quality, and analysis boundaries. PR #331 completed the final
analysis engine and removed measured feedback as a North-Star pre-run blocker while preserving
feedback-specific claim restrictions.

The next material risk is not another statistical or runtime architecture question. It is
composition risk: the accepted pieces must be able to hand evidence across their real typed seams
before the final execution manifest is frozen and before any live authorization exists.

A live smoke run would be the wrong proof. It would mix integration validation with GPU/runtime
availability, provider behavior, execution authority, and scientific evidence. The remaining
question can be answered offline with deterministic synthetic evidence.

## Decision

Implement `FINAL_342_OFFLINE_ORCHESTRATION_AND_INTEGRATION_REHEARSAL_V1` as one
non-authorizing integration proof over the exact frozen 342-run denominator.

The rehearsal composes the accepted modules in this order:

1. frozen `PlannedRun` ledger;
2. final execution producer `initial_state` and exact plan/trace bindings;
3. protected review capture, reload, blinded payload construction, and protected export;
4. G11.9 per-run measured-quality reduction for all 162 functional trajectories;
5. synthetic typed runtime measurements for all 180 runtime trajectories;
6. G11.10 final analysis engine over the exact 342-run population.

No production source is modified by the rehearsal. The new module is orchestration and evidence
validation only.

## Exact population

The frozen scientific denominator remains unchanged:

- 342 scheduled trajectories total;
- 162 functional trajectories;
- 180 runtime-microbenchmark trajectories;
- 41 predeclared secondary-review assignments;
- 60 runtime comparison pairs per A/B/C contrast.

The producer's real `initial_state` function must yield exactly 342 `PlanBinding` records and 342
`RuntimeTraceIdentity` records for the same frozen plan. The rehearsal does not fabricate a smaller
shadow plan.

## Synthetic evidence boundary

All evidence produced by this rehearsal is explicitly synthetic. Synthetic identifiers are used for
the rehearsal transaction, final-manifest identity, retrieval configuration, episode-manifest
identity, runtime model identity, outputs, and reviewer identities.

Synthetic evidence is used only to prove that the accepted software boundaries compose. It is not:

- measured A/B/C evidence;
- a benchmark result;
- evidence that any runtime effect exists;
- evidence that quality non-inferiority has been achieved in the final experiment;
- authority to freeze a manifest;
- authority to issue an execution authorization.

The rehearsal intentionally drives a complete/pass synthetic path through the analysis engine. A
`SUPPORTED` analysis decision in that synthetic path means only that the software can realize the
accepted claim logic when given complete qualifying inputs. It has zero scientific authority.

## Producer seam

The rehearsal calls the accepted final execution producer `initial_state` against the real frozen
ledger using deterministic synthetic transaction and final-manifest digests.

This proves that:

- all 342 planned trajectories are realized as producer plan bindings;
- all 342 run/trace identities are bound to one final-manifest identity;
- the planning-manifest identity is not reused as the final-manifest identity;
- accepted producer predecessor checks still pass;
- no live worker or transport operation is needed to prove the composition seam.

The rehearsal then uses the producer's real typed terminal, attempt, transport, measurement, and
bundle-receipt contracts for downstream synthetic evidence.

## Protected-review seam

One predeclared secondary-review case is exercised through the real protected-review storage path:

1. four synthetic transport responses are captured with `capture_transport_response`;
2. all four captures are reloaded from protected storage;
3. reviewer payloads are built against the frozen secondary schedule;
4. both primary and secondary assignments are produced for the selected scheduled case;
5. reviewer-safe field checks are applied;
6. a protected export receipt is produced inside a temporary directory.

The temporary protected tree is deleted automatically after the rehearsal. No public raw prompt or
response artifact is created.

The complete 162-run quality population uses the same typed `ProtectedTurnCapture` contract. The
single storage round trip exists to prove the I/O and blinding seam without performing hundreds of
redundant fsync operations during every focused test.

## Measured-quality seam

Every functional trajectory is passed through the actual G11.9
`reduce_measured_quality_run` function.

For the positive rehearsal path:

- all four turns are represented by typed protected captures;
- deterministic quality contains every frozen deterministic check;
- all checks pass;
- every trajectory receives a primary review;
- exactly the frozen 41 scheduled cases receive a secondary review;
- secondary reviews agree materially with the primary review;
- no adjudication is required;
- route and retry evidence is internally consistent;
- all 162 reducer outputs must be evidence-complete task successes.

This is not a claim that the final measured run will achieve those outcomes. It proves only that the
producer/review/reducer contracts compose over the exact functional denominator.

## Runtime-analysis seam

The 180 runtime trajectories receive deterministic synthetic turn measurements using the real
producer measurement and runtime-core identity contracts.

The rehearsal preserves the frozen endpoint semantics:

- turn 1 is cold descriptive evidence;
- candidate turns are 2, 3, and 4;
- A and B use the frozen turn-local route;
- C uses the frozen affinity route;
- a legitimate non-warm turn 2 in turn-local A/B is excluded rather than treated as missing;
- warm candidate turns retain primary `newly_computed_prefill_tokens` telemetry;
- every measurement is bound to the same synthetic final-manifest identity.

Synthetic token values are deliberately separated by condition so the complete path exercises all
three frozen contrasts and their paired-bootstrap decision logic. The values have no benchmark or
performance meaning.

## Final analysis seam

The rehearsal passes the exact synthetic population into `Final342AnalysisInput` using:

- the real frozen planned runs;
- producer-generated plan bindings;
- producer-generated trace bindings;
- one terminal record per planned trajectory;
- 720 typed runtime measurements;
- 162 outputs from the real measured-quality reducer;
- an explicitly synthetic verified-bundle receipt;
- one synthetic retrieval and episode-manifest identity shared across A/B/C.

Acceptance of the positive rehearsal requires:

- complete 342-run accountability;
- quality gate state `PASSED` for the synthetic fixture;
- exactly 60 eligible pairs for B-A, C-B, and C-A;
- the three synthetic mechanics decisions to traverse the `SUPPORTED` path;
- the returned rehearsal summary to keep all scientific and authorization claims disabled.

Tests also perturb a final-manifest trace binding and require the analysis engine to fail
closed with
`EVIDENCE_INCOMPLETE` and blocked claim decisions.

## Source identity and precedence

The rehearsal record binds the exact accepted identities of the runtime core, execution producer,
review design, review successor, G11.9 quality reducer, G11.10 analysis engine, frozen planned-run
ledger, and blinded-quality rubric.

Repository validation requires the PR #331 merge commit
`0cbb6cea399537345efdbddbb874fecfa6dc5a85` to remain an ancestor of the current branch. A changed
predecessor byte invalidates the rehearsal subject and requires explicit requalification rather than
silent reuse.

## Authorization boundary

The rehearsal performs:

- zero model requests;
- zero GPU execution;
- zero Kaggle execution;
- zero network transport;
- zero authorization issuance;
- zero execution-manifest freeze;
- zero final measured A/B/C execution.

`manifest_freeze_permitted`, `final_measured_abc_execution_authorized`,
`new_execution_authorized`, and `effect_claims_permitted` remain false in the rehearsal result.

The next gate is a separate manifest-freeze transition after this rehearsal is accepted and merged.

## Consequences

A passing rehearsal establishes that the final-run plan, producer, protected-review successor,
measured-quality reducer, and final analysis engine compose through their accepted typed contracts
without requiring live execution.

This removes the final software-integration uncertainty before manifest freeze. It does not remove
platform-readiness, authorization, or measured-evidence requirements.

The rehearsal also gives future regressions a narrow diagnostic boundary: if final integration later
breaks, the same deterministic synthetic path can distinguish software seam drift from live runtime
or platform failures.

## Rejected alternatives

### Run a small live A/B/C smoke experiment

Rejected because the remaining question is deterministic composition. A live smoke would consume
runtime resources and entangle software integration with platform state and authority.

### Rebuild a smaller synthetic plan

Rejected because a reduced shadow plan would not prove 342-run accountability, exact producer
binding coverage, the 41-case secondary schedule, or all 60 runtime comparison pairs.

### Bypass the G11.9 reducer and fabricate `MeasuredQualityRunResult`

Rejected because that would repeat the analysis-engine unit-test boundary rather than prove the
producer/review/reducer seam.

### Write all 162 protected review cases through durable temporary storage

Rejected as redundant I/O. One scheduled secondary case exercises capture, reload, payload
construction, blinding, and export. All 162 quality cases still traverse the same typed capture
contract and the real G11.9 reducer.

### Treat synthetic `SUPPORTED` decisions as experiment evidence

Rejected categorically. Synthetic decisions prove software mechanics only and are explicitly marked
non-scientific and non-authoritative.

## Next gate

`REQUALIFY_AND_FREEZE_FINAL_342_EXECUTION_MANIFEST_V1`

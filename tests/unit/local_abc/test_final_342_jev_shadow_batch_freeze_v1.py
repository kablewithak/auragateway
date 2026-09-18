from __future__ import annotations

from auragateway.contracts.blinded_quality import (
    DisagreementReason,
    RubricCriterion,
)
from auragateway.local_abc import (
    final_342_jev_shadow_batch_freeze_v1 as batch_freeze,
)


def _deltas() -> dict[RubricCriterion, int]:
    return {criterion: 0 for criterion in RubricCriterion}


def _entry(
    index: int,
    *,
    request_sha256: str | None = None,
) -> batch_freeze.FrozenBatchEntry:
    is_canary = index == 0
    return batch_freeze.FrozenBatchEntry(
        batch_index=index,
        review_item_id=f"{index + 1:064x}",
        episode_id=f"ep-func-{index + 1:03d}",
        request_relative_path=(
            f".local/auragateway/jev-shadow-adjudication-v1/batch-v1/requests/{index:02d}.json"
        ),
        request_sha256=(request_sha256 if request_sha256 is not None else f"{index + 101:064x}"),
        disagreement_reasons=(DisagreementReason.FAILURE_LABEL_MISMATCH,),
        criterion_score_deltas=_deltas(),
        lifecycle_state=("EXECUTED_CANARY" if is_canary else "FROZEN_PENDING"),
        provider_request_already_performed=is_canary,
        response_sha256=(batch_freeze.EXPECTED_CANARY_RESPONSE_SHA256 if is_canary else None),
    )


def test_execution_policy_is_serial_fail_stop_and_no_retry() -> None:
    policy = batch_freeze.BatchExecutionPolicy()

    assert policy.model_pin == "jev-1.13.0"
    assert policy.max_in_flight_requests == 1
    assert policy.execution_mode == "SERIAL_ONE_AT_A_TIME"
    assert policy.retry_policy == "NO_AUTOMATIC_RETRY"
    assert policy.stop_policy == "STOP_ON_FIRST_PROVIDER_VALIDATION_OR_PERSISTENCE_FAILURE"
    assert policy.failure_threshold_frozen is False
    assert policy.threshold_selection_deferred_until_calibration is True


def test_manifest_requires_one_executed_canary_and_34_pending() -> None:
    entries = tuple(
        _entry(
            index,
            request_sha256=(batch_freeze.EXPECTED_CANARY_REQUEST_SHA256 if index == 0 else None),
        )
        for index in range(35)
    )

    manifest = batch_freeze.FrozenBatchManifest(
        batch_size=35,
        executed_canary_count=1,
        pending_count=34,
        question_count_per_case=29,
        criterion_question_count_per_case=7,
        failure_question_count_per_case=22,
        request_inventory_sha256="f" * 64,
        policy=batch_freeze.BatchExecutionPolicy(),
        entries=entries,
    )

    assert manifest.entries[0].lifecycle_state == "EXECUTED_CANARY"
    assert sum(item.lifecycle_state == "FROZEN_PENDING" for item in manifest.entries) == 34


def test_inventory_digest_changes_when_request_identity_changes() -> None:
    baseline = tuple(
        _entry(
            index,
            request_sha256=(batch_freeze.EXPECTED_CANARY_REQUEST_SHA256 if index == 0 else None),
        )
        for index in range(35)
    )
    changed = list(baseline)
    changed[10] = changed[10].model_copy(update={"request_sha256": "e" * 64})

    assert batch_freeze._inventory_digest(baseline) != batch_freeze._inventory_digest(
        tuple(changed)
    )

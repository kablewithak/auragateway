from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

import pytest

from auragateway.contracts.blinded_quality import BlindedQualityRubric
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as bridge,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)
from auragateway.local_abc import (
    final_342_secondary_review_work_queue_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]


def _rubric() -> BlindedQualityRubric:
    return BlindedQualityRubric.model_validate_json(
        (ROOT / bridge.RUBRIC_PATH).read_text(encoding="utf-8")
    )


def _turns() -> tuple[review_successor.ReviewerTurn, ...]:
    return tuple(
        review_successor.ReviewerTurn(
            turn_index=index,
            user_message=f"visible user message {index}",
            assistant_output={"answer": f"visible assistant output {index}"},
        )
        for index in range(1, 5)
    )


def _payload(
    *,
    assignment_id: str,
    review_item_id: str,
    episode_id: str,
) -> review_successor.ReviewerPayload:
    return review_successor.ReviewerPayload(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id=episode_id,
        turns=_turns(),
    )


def _assignment(
    *,
    assignment_id: str,
    review_item_id: str,
    episode_id: str,
    role: Literal["primary", "secondary"],
) -> bridge.ExpectedReviewAssignment:
    return bridge.ExpectedReviewAssignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id=episode_id,
        role=role,
    )


def _schedule_entry(
    *,
    index: int,
    review_item_id: str,
    episode_id: str,
    secondary_assignment_id: str,
) -> review_successor.SecondaryScheduleEntry:
    return review_successor.SecondaryScheduleEntry(
        planned_order_index=index,
        run_id=f"run-{index:03d}",
        episode_id=episode_id,
        condition_id="A",
        expected_terminal_decision="answer",
        review_item_id=review_item_id,
        secondary_assignment_id=secondary_assignment_id,
    )


def _write_primary_result(
    root: Path,
    assignment_id: str,
) -> None:
    path = root / bridge.REVIEW_RESULT_ROOT / "reviews" / f"{assignment_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}\n", encoding="utf-8")


def _export(
    payloads: tuple[review_successor.ReviewerPayload, ...],
) -> review_successor.ProtectedExport:
    review_items = {item.review_item_id for item in payloads}
    return review_successor.ProtectedExport(
        review_item_count=len(review_items),
        assignment_count=len(payloads),
        assignments=payloads,
    )


def _schedule(
    entries: tuple[review_successor.SecondaryScheduleEntry, ...],
) -> review_successor.ProtectedSchedule:
    return review_successor.ProtectedSchedule(
        schema_version="1.0.0",
        schedule_id="auragateway-final-342-secondary-review-schedule-v1",
        population=162,
        target=41,
        seed=20260712,
        allocation={"test": 41},
        entries=entries,
    )


def test_select_next_secondary_follows_frozen_schedule_order(
    tmp_path: Path,
) -> None:
    first_item = "1" * 64
    second_item = "2" * 64

    first_primary_id = "review-000000000000000000000001"
    first_secondary_id = "review-000000000000000000000002"
    second_primary_id = "review-000000000000000000000003"
    second_secondary_id = "review-000000000000000000000004"

    assignments = (
        _assignment(
            assignment_id=first_primary_id,
            review_item_id=first_item,
            episode_id="ep-func-001",
            role="primary",
        ),
        _assignment(
            assignment_id=first_secondary_id,
            review_item_id=first_item,
            episode_id="ep-func-001",
            role="secondary",
        ),
        _assignment(
            assignment_id=second_primary_id,
            review_item_id=second_item,
            episode_id="ep-func-002",
            role="primary",
        ),
        _assignment(
            assignment_id=second_secondary_id,
            review_item_id=second_item,
            episode_id="ep-func-002",
            role="secondary",
        ),
    )

    _write_primary_result(tmp_path, first_primary_id)
    _write_primary_result(tmp_path, second_primary_id)

    export = _export(
        (
            _payload(
                assignment_id=second_secondary_id,
                review_item_id=second_item,
                episode_id="ep-func-002",
            ),
            _payload(
                assignment_id=first_secondary_id,
                review_item_id=first_item,
                episode_id="ep-func-001",
            ),
        )
    )

    schedule = _schedule(
        tuple(
            [
                _schedule_entry(
                    index=1,
                    review_item_id=first_item,
                    episode_id="ep-func-001",
                    secondary_assignment_id=first_secondary_id,
                ),
                _schedule_entry(
                    index=2,
                    review_item_id=second_item,
                    episode_id="ep-func-002",
                    secondary_assignment_id=second_secondary_id,
                ),
            ]
            + [
                _schedule_entry(
                    index=index,
                    review_item_id=f"{index:x}".rjust(64, "0"),
                    episode_id=f"ep-func-{index:03d}",
                    secondary_assignment_id=f"review-{1000 + index:024x}",
                )
                for index in range(3, 42)
            ]
        )
    )

    selected = subject.select_next_secondary(
        root=tmp_path,
        export=export,
        schedule=schedule,
        assignments=assignments,
    )

    assert selected is not None
    assert selected[0].assignment_id == first_secondary_id


def test_secondary_requires_corresponding_primary_result(
    tmp_path: Path,
) -> None:
    item = "1" * 64
    primary_id = "review-000000000000000000000001"
    secondary_id = "review-000000000000000000000002"

    assignments = (
        _assignment(
            assignment_id=primary_id,
            review_item_id=item,
            episode_id="ep-func-001",
            role="primary",
        ),
        _assignment(
            assignment_id=secondary_id,
            review_item_id=item,
            episode_id="ep-func-001",
            role="secondary",
        ),
    )

    export = _export(
        (
            _payload(
                assignment_id=secondary_id,
                review_item_id=item,
                episode_id="ep-func-001",
            ),
        )
    )

    schedule = _schedule(
        tuple(
            [
                _schedule_entry(
                    index=1,
                    review_item_id=item,
                    episode_id="ep-func-001",
                    secondary_assignment_id=secondary_id,
                )
            ]
            + [
                _schedule_entry(
                    index=index,
                    review_item_id=f"{index:x}".rjust(64, "0"),
                    episode_id=f"ep-func-{index:03d}",
                    secondary_assignment_id=f"review-{1000 + index:024x}",
                )
                for index in range(2, 42)
            ]
        )
    )

    with pytest.raises(subject.SecondaryWorkQueueError) as caught:
        subject.select_next_secondary(
            root=tmp_path,
            export=export,
            schedule=schedule,
            assignments=assignments,
        )

    assert caught.value.error_code == "FINAL_342_SECONDARY_REVIEW_QUEUE_PRIMARY_REQUIRED"


def test_completed_secondary_advances_to_next_assignment(
    tmp_path: Path,
) -> None:
    first_item = "1" * 64
    second_item = "2" * 64

    first_primary_id = "review-000000000000000000000001"
    first_secondary_id = "review-000000000000000000000002"
    second_primary_id = "review-000000000000000000000003"
    second_secondary_id = "review-000000000000000000000004"

    assignments = (
        _assignment(
            assignment_id=first_primary_id,
            review_item_id=first_item,
            episode_id="ep-func-001",
            role="primary",
        ),
        _assignment(
            assignment_id=first_secondary_id,
            review_item_id=first_item,
            episode_id="ep-func-001",
            role="secondary",
        ),
        _assignment(
            assignment_id=second_primary_id,
            review_item_id=second_item,
            episode_id="ep-func-002",
            role="primary",
        ),
        _assignment(
            assignment_id=second_secondary_id,
            review_item_id=second_item,
            episode_id="ep-func-002",
            role="secondary",
        ),
    )

    _write_primary_result(tmp_path, first_primary_id)
    _write_primary_result(tmp_path, second_primary_id)

    first_secondary_result = (
        tmp_path / bridge.REVIEW_RESULT_ROOT / "reviews" / f"{first_secondary_id}.json"
    )
    first_secondary_result.write_text("{}\n", encoding="utf-8")

    export = _export(
        (
            _payload(
                assignment_id=first_secondary_id,
                review_item_id=first_item,
                episode_id="ep-func-001",
            ),
            _payload(
                assignment_id=second_secondary_id,
                review_item_id=second_item,
                episode_id="ep-func-002",
            ),
        )
    )

    schedule = _schedule(
        tuple(
            [
                _schedule_entry(
                    index=1,
                    review_item_id=first_item,
                    episode_id="ep-func-001",
                    secondary_assignment_id=first_secondary_id,
                ),
                _schedule_entry(
                    index=2,
                    review_item_id=second_item,
                    episode_id="ep-func-002",
                    secondary_assignment_id=second_secondary_id,
                ),
            ]
            + [
                _schedule_entry(
                    index=index,
                    review_item_id=f"{index:x}".rjust(64, "0"),
                    episode_id=f"ep-func-{index:03d}",
                    secondary_assignment_id=f"review-{1000 + index:024x}",
                )
                for index in range(3, 42)
            ]
        )
    )

    selected = subject.select_next_secondary(
        root=tmp_path,
        export=export,
        schedule=schedule,
        assignments=assignments,
    )

    assert selected is not None
    assert selected[0].assignment_id == second_secondary_id


def test_secondary_work_item_is_blinded_and_local(tmp_path: Path) -> None:
    assignment_id = "review-000000000000000000000002"
    review_item_id = "1" * 64

    assignment = _assignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
        role="secondary",
    )

    payload = _payload(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )

    receipt = subject.materialize_secondary_work_item(
        root=tmp_path,
        queue_root=tmp_path / ".local" / "secondary-queue",
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert receipt.status == "SECONDARY_WORK_ITEM_READY"
    assert receipt.work_item_path is not None

    work_item = json.loads((tmp_path / receipt.work_item_path).read_text(encoding="utf-8"))

    review_successor.assert_reviewer_safe(work_item)
    serialized = json.dumps(work_item, sort_keys=True)
    assert "primary_review" not in serialized
    assert "primary_verdict" not in serialized
    assert "reviewer_id_sha256" not in serialized


def test_repeated_materialization_preserves_matching_human_draft(
    tmp_path: Path,
) -> None:
    assignment_id = "review-000000000000000000000002"
    review_item_id = "1" * 64

    assignment = _assignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
        role="secondary",
    )
    payload = _payload(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )
    queue_root = tmp_path / ".local" / "secondary-queue"

    first = subject.materialize_secondary_work_item(
        root=tmp_path,
        queue_root=queue_root,
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert first.submission_path is not None
    submission_path = tmp_path / first.submission_path

    human_draft = json.loads(submission_path.read_text(encoding="utf-8"))
    human_draft["reviewer_key"] = "secondary-reviewer-01"
    human_draft["rationale"] = "human draft preserved"
    submission_path.write_text(
        json.dumps(human_draft, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    second = subject.materialize_secondary_work_item(
        root=tmp_path,
        queue_root=queue_root,
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert second.submission_template_created is False
    assert json.loads(submission_path.read_text(encoding="utf-8")) == human_draft


def test_stale_submission_assignment_identity_fails_closed(
    tmp_path: Path,
) -> None:
    assignment_id = "review-000000000000000000000002"
    review_item_id = "1" * 64

    assignment = _assignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
        role="secondary",
    )
    payload = _payload(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )
    queue_root = tmp_path / ".local" / "secondary-queue"

    first = subject.materialize_secondary_work_item(
        root=tmp_path,
        queue_root=queue_root,
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert first.submission_path is not None
    submission_path = tmp_path / first.submission_path

    stale = json.loads(submission_path.read_text(encoding="utf-8"))
    stale["assignment_id"] = "review-ffffffffffffffffffffffff"
    submission_path.write_text(
        json.dumps(stale, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(subject.SecondaryWorkQueueError) as caught:
        subject.materialize_secondary_work_item(
            root=tmp_path,
            queue_root=queue_root,
            assignment=assignment,
            payload=payload,
            rubric=_rubric(),
        )

    assert (
        caught.value.error_code == "FINAL_342_SECONDARY_REVIEW_QUEUE_SUBMISSION_IDENTITY_MISMATCH"
    )


def test_submission_template_field_names_match_bridge_contract() -> None:
    assert set(subject.ReviewSubmissionTemplate.model_fields) == set(
        bridge.ReviewSubmissionDraft.model_fields
    )

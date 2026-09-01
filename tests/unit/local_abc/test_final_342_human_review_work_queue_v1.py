from __future__ import annotations

import json
from pathlib import Path

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
)
from auragateway.local_abc import (
    final_342_human_review_work_queue_v1 as subject,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as bridge,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)

ROOT = Path(__file__).resolve().parents[3]


def _rubric() -> BlindedQualityRubric:
    return BlindedQualityRubric.model_validate_json(
        (ROOT / bridge.RUBRIC_PATH).read_text(encoding="utf-8")
    )


def _turns() -> tuple[
    review_successor.ReviewerTurn,
    ...,
]:
    return tuple(
        review_successor.ReviewerTurn(
            turn_index=index,
            user_message=(f"visible user message {index}"),
            assistant_output={"answer": (f"visible assistant output {index}")},
        )
        for index in range(
            1,
            5,
        )
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


def _primary_assignment(
    *,
    assignment_id: str,
    review_item_id: str,
    episode_id: str,
) -> bridge.ExpectedReviewAssignment:
    return bridge.ExpectedReviewAssignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id=episode_id,
        role="primary",
    )


def test_select_next_primary_follows_export_order(
    tmp_path: Path,
) -> None:
    first_id = "review-000000000000000000000001"
    second_id = "review-000000000000000000000002"

    first_item = "1" * 64
    second_item = "2" * 64

    first = _primary_assignment(
        assignment_id=first_id,
        review_item_id=first_item,
        episode_id="ep-func-001",
    )

    second = _primary_assignment(
        assignment_id=second_id,
        review_item_id=second_item,
        episode_id="ep-func-002",
    )

    export = review_successor.ProtectedExport(
        review_item_count=2,
        assignment_count=2,
        assignments=(
            _payload(
                assignment_id=first_id,
                review_item_id=first_item,
                episode_id="ep-func-001",
            ),
            _payload(
                assignment_id=second_id,
                review_item_id=second_item,
                episode_id="ep-func-002",
            ),
        ),
    )

    selected = subject.select_next_primary(
        root=tmp_path,
        export=export,
        assignments=(
            first,
            second,
        ),
    )

    assert selected is not None
    assert selected[0].assignment_id == first_id


def test_completed_primary_advances_to_next_assignment(
    tmp_path: Path,
) -> None:
    first_id = "review-000000000000000000000001"
    second_id = "review-000000000000000000000002"

    first_item = "1" * 64
    second_item = "2" * 64

    first = _primary_assignment(
        assignment_id=first_id,
        review_item_id=first_item,
        episode_id="ep-func-001",
    )

    second = _primary_assignment(
        assignment_id=second_id,
        review_item_id=second_item,
        episode_id="ep-func-002",
    )

    export = review_successor.ProtectedExport(
        review_item_count=2,
        assignment_count=2,
        assignments=(
            _payload(
                assignment_id=first_id,
                review_item_id=first_item,
                episode_id="ep-func-001",
            ),
            _payload(
                assignment_id=second_id,
                review_item_id=second_item,
                episode_id="ep-func-002",
            ),
        ),
    )

    result_path = tmp_path / bridge.REVIEW_RESULT_ROOT / "reviews" / f"{first_id}.json"

    result_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result_path.write_text(
        "{}\n",
        encoding="utf-8",
    )

    selected = subject.select_next_primary(
        root=tmp_path,
        export=export,
        assignments=(
            first,
            second,
        ),
    )

    assert selected is not None
    assert selected[0].assignment_id == second_id


def test_primary_work_item_is_reviewer_safe_and_local(
    tmp_path: Path,
) -> None:
    assignment_id = "review-000000000000000000000001"
    review_item_id = "1" * 64

    assignment = _primary_assignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )

    payload = _payload(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )

    queue_root = tmp_path / ".local" / "queue"

    receipt = subject.materialize_primary_work_item(
        root=tmp_path,
        queue_root=queue_root,
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert receipt.status == "PRIMARY_WORK_ITEM_READY"
    assert receipt.work_item_created is True
    assert receipt.submission_template_created is True

    assert receipt.work_item_path is not None

    work_item_path = tmp_path / receipt.work_item_path

    work_item = json.loads(work_item_path.read_text(encoding="utf-8"))

    review_successor.assert_reviewer_safe(work_item)


def test_repeated_materialization_does_not_overwrite_human_draft(
    tmp_path: Path,
) -> None:
    assignment_id = "review-000000000000000000000001"
    review_item_id = "1" * 64

    assignment = _primary_assignment(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )

    payload = _payload(
        assignment_id=assignment_id,
        review_item_id=review_item_id,
        episode_id="ep-func-001",
    )

    queue_root = tmp_path / ".local" / "queue"

    first = subject.materialize_primary_work_item(
        root=tmp_path,
        queue_root=queue_root,
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert first.submission_path is not None

    submission_path = tmp_path / first.submission_path

    human_edited = '{"human_edit_preserved":true}\n'

    submission_path.write_text(
        human_edited,
        encoding="utf-8",
    )

    second = subject.materialize_primary_work_item(
        root=tmp_path,
        queue_root=queue_root,
        assignment=assignment,
        payload=payload,
        rubric=_rubric(),
    )

    assert second.work_item_created is False
    assert second.submission_template_created is False

    assert submission_path.read_text(encoding="utf-8") == human_edited


def test_submission_template_field_names_match_bridge_contract() -> None:
    assert set(subject.ReviewSubmissionTemplate.model_fields) == set(
        bridge.ReviewSubmissionDraft.model_fields
    )

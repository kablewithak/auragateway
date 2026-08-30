"""Tests for the final-342 measured-review successor."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import final_342_measured_review_successor_v1 as successor
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core

ROOT = Path(__file__).resolve().parents[3]


class FakeTransportResult:
    def __init__(
        self,
        response_object: dict[str, object] | None,
        *,
        valid: bool = True,
    ) -> None:
        self.response_object = response_object
        self.response_json_object_valid = valid


def _record_payload() -> dict[str, object]:
    value = json.loads((ROOT / successor.RECORD_PATH).read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise AssertionError("measured-review successor record must be an object")
    return cast(dict[str, object], value)


def test_current_successor_validates_without_execution() -> None:
    result = successor.validate(ROOT)

    assert result["status"] == "FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1_VALID"
    assert result["secondary_schedule_count"] == 41
    assert result["producer_modification_required"] is False
    assert result["protected_capture_implemented"] is True
    assert result["reviewer_export_implemented"] is True
    assert result["manifest_freeze_permitted"] is False
    assert result["final_measured_abc_execution_authorized"] is False
    assert result["effect_claims_permitted"] is False
    assert result["next_gate"] == "AUTHOR_FINAL_342_MEASURED_QUALITY_REDUCERS_V1"


def test_schedule_digest_matches_public_record() -> None:
    schedule = successor.derive_protected_schedule(ROOT)
    payload = successor.protected_schedule_bytes(ROOT)
    record = successor.MeasuredReviewSuccessorRecord.model_validate(_record_payload())

    assert len(schedule.entries) == 41
    assert successor.sha256_bytes(payload) == successor.EXPECTED_SCHEDULE_SHA256
    assert record.secondary_schedule.schedule_sha256 == successor.EXPECTED_SCHEDULE_SHA256


def test_schedule_allocation_and_identity_are_exact() -> None:
    schedule = successor.derive_protected_schedule(ROOT)

    assert schedule.allocation == {
        "A|answer": 7,
        "A|clarify": 2,
        "A|escalate": 2,
        "A|refuse": 2,
        "B|answer": 8,
        "B|clarify": 2,
        "B|escalate": 2,
        "B|refuse": 2,
        "C|answer": 8,
        "C|clarify": 2,
        "C|escalate": 2,
        "C|refuse": 2,
    }
    assert len({item.run_id for item in schedule.entries}) == 41
    assert len({item.secondary_assignment_id for item in schedule.entries}) == 41


def test_protected_schedule_materialization_is_idempotent(tmp_path: Path) -> None:
    target, digest, created = successor.materialize_protected_schedule(
        ROOT,
        protected_root=tmp_path,
    )
    second_target, second_digest, second_created = successor.materialize_protected_schedule(
        ROOT,
        protected_root=tmp_path,
    )

    assert created is True
    assert second_created is False
    assert target == second_target
    assert digest == second_digest == successor.EXPECTED_SCHEDULE_SHA256


def test_capture_uses_transient_response_and_append_only_store(tmp_path: Path) -> None:
    result = FakeTransportResult({"answer": "visible candidate"})
    run_id = "run-functional-ep-func-001-r02-condition-c"

    capture = successor.capture_transport_response(
        store_root=tmp_path,
        transport_result=result,
        run_id=run_id,
        episode_id="ep-func-001",
        turn_index=1,
        user_message="hello",
    )
    repeated = successor.capture_transport_response(
        store_root=tmp_path,
        transport_result=result,
        run_id=run_id,
        episode_id="ep-func-001",
        turn_index=1,
        user_message="hello",
    )

    assert capture == repeated
    assert capture.review_item_id == core.protected_review_id(run_id)

    with pytest.raises(successor.MeasuredReviewError):
        successor.capture_transport_response(
            store_root=tmp_path,
            transport_result=FakeTransportResult({"answer": "different"}),
            run_id=run_id,
            episode_id="ep-func-001",
            turn_index=1,
            user_message="hello",
        )


def test_invalid_transport_response_is_not_captured(tmp_path: Path) -> None:
    with pytest.raises(successor.MeasuredReviewError):
        successor.capture_transport_response(
            store_root=tmp_path,
            transport_result=FakeTransportResult(None, valid=False),
            run_id="run-functional-ep-func-001-r02-condition-c",
            episode_id="ep-func-001",
            turn_index=1,
            user_message="hello",
        )


def test_reviewer_payload_hides_execution_metadata() -> None:
    schedule = successor.derive_protected_schedule(ROOT)
    selected = schedule.entries[0]
    captures = tuple(
        successor.ProtectedTurnCapture(
            run_id=selected.run_id,
            review_item_id=selected.review_item_id,
            episode_id=selected.episode_id,
            turn_index=index,
            user_message=f"user {index}",
            assistant_output={"answer": f"assistant {index}"},
            response_sha256=successor.sha256_bytes(
                successor.canonical_json_bytes({"answer": f"assistant {index}"})
            ),
        )
        for index in range(1, 5)
    )

    payloads = successor.build_reviewer_payloads(
        captures=captures,
        schedule=schedule,
        frozen_source_evidence=({"source_id": "source-1", "text": "evidence"},),
    )

    assert len(payloads) == 2
    assert payloads[0].assignment_id != payloads[1].assignment_id
    serialized = json.dumps(
        [item.model_dump(mode="json") for item in payloads],
        sort_keys=True,
    )
    assert '"run_id"' not in serialized
    assert '"condition_id"' not in serialized
    assert '"route"' not in serialized
    assert '"worker_id"' not in serialized
    assert '"latency"' not in serialized
    assert '"cost"' not in serialized


def test_forbidden_reviewer_field_fails_closed() -> None:
    with pytest.raises(ValueError):
        successor.assert_reviewer_safe({"nested": {"condition_id": "A"}})


def test_public_receipt_contains_digest_not_raw_output(tmp_path: Path) -> None:
    schedule = successor.derive_protected_schedule(ROOT)
    selected = schedule.entries[0]
    captures = tuple(
        successor.ProtectedTurnCapture(
            run_id=selected.run_id,
            review_item_id=selected.review_item_id,
            episode_id=selected.episode_id,
            turn_index=index,
            user_message=f"user {index}",
            assistant_output={"answer": f"assistant {index}"},
            response_sha256=successor.sha256_bytes(
                successor.canonical_json_bytes({"answer": f"assistant {index}"})
            ),
        )
        for index in range(1, 5)
    )
    payloads = successor.build_reviewer_payloads(
        captures=captures,
        schedule=schedule,
    )
    receipt = successor.write_protected_export(
        protected_root=tmp_path,
        assignments=payloads,
    )

    assert receipt.item_count == 1
    assert receipt.raw_outputs_in_public_evidence is False
    assert receipt.public_binding_is_metadata_or_digest_only is True
    assert len(receipt.export_sha256) == 64


def test_deletion_requires_all_retention_gates(tmp_path: Path) -> None:
    protected = tmp_path / "protected"
    protected.mkdir()
    (protected / "raw.json").write_text('{"raw":true}\n', encoding="utf-8")

    with pytest.raises(successor.MeasuredReviewError):
        successor.delete_protected_review_material(
            protected_root=protected,
            authorization=successor.DeletionAuthorization(
                review_complete=True,
                adjudication_complete=True,
                analysis_inputs_materialized=False,
                public_receipt_verified=True,
            ),
            receipt_path=tmp_path / "receipt.json",
        )

    assert protected.is_dir()

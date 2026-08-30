"""Implement the protected final-342 measured-review successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Literal, Never, Protocol, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import final_342_measured_review_design_v1 as review_design
from auragateway.local_abc import final_342_non_authorizing_runtime_core_v1 as core
from auragateway.local_abc import (
    final_342_producer_review_analysis_seam_audit_v1 as seam_audit,
)

RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_measured_review_successor_v1.json")
PRODUCER_PATH = Path("src/auragateway/local_abc/final_342_execution_producer_v1.py")
RUNTIME_CORE_PATH = Path("src/auragateway/local_abc/final_342_non_authorizing_runtime_core_v1.py")
REVIEW_SOURCE_PATH = Path("src/auragateway/local_abc/final_342_measured_review_design_v1.py")
REVIEW_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_measured_review_design_v1.json"
)
SEAM_AUDIT_SOURCE_PATH = Path(
    "src/auragateway/local_abc/final_342_producer_review_analysis_seam_audit_v1.py"
)
SEAM_AUDIT_RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_final_342_producer_review_analysis_seam_audit_v1.json"
)
ANALYSIS_RECORD_PATH = Path("benchmarks/local_abc/auragateway_final_342_analysis_contracts_v1.json")
LEDGER_PATH = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
EPISODES_PATH = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
RUBRIC_PATH = Path("data/evals/quality/blinded-v1/rubric.json")
SOURCE_INVENTORY_PATH = Path("data/corpus/source_inventory.json")
PROTECTED_REVIEW_ROOT = Path(".local/auragateway/final-342-protected-review-v1")
PROTECTED_SCHEDULE_PATH = PROTECTED_REVIEW_ROOT / "review_sample_schedule_v1.json"
PROTECTED_EXPORT_PATH = PROTECTED_REVIEW_ROOT / "reviewer_export_v1.json"

EXPECTED_BASE_MAIN = "6d9f1c5cb54ab89e6e199ba42c676282330410b0"
EXPECTED_SCHEDULE_SHA256 = "9566edb218c2d9c6459e8428bc93676bc1e73484b2fd56a249aed2cc1db6748c"
RUBRIC_ID: Literal["auragateway-quality-rubric-v1"] = "auragateway-quality-rubric-v1"
RUBRIC_SHA256: Literal["7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"] = (
    "7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"
)

EXPECTED_SOURCE_BLOBS: dict[str, str] = {
    PRODUCER_PATH.as_posix(): "9bedae7c7815e80d7c03ccc37b1e5261310056cf",
    RUNTIME_CORE_PATH.as_posix(): "7edeb7cb3f6c2213868d23863c33a9a94669468c",
    REVIEW_SOURCE_PATH.as_posix(): "673091128975b2fc33ba175649c8e82b2670a522",
    REVIEW_RECORD_PATH.as_posix(): "e667cf734e6fdeec1acf4a5b254beebb78754fb7",
    SEAM_AUDIT_SOURCE_PATH.as_posix(): "f271f2746effc77b03147a7c9929e30c8c563e2e",
    SEAM_AUDIT_RECORD_PATH.as_posix(): "605a193bf7873ec1184e7f50a7a1ed410e5b94c3",
    ANALYSIS_RECORD_PATH.as_posix(): "0e7f654a5e8562f93ada988bba51f4e3ed5b5b1f",
    LEDGER_PATH.as_posix(): "553b23e24629bdca81d9fb9fdcbd90cc2081caf0",
    EPISODES_PATH.as_posix(): "b8e6a9c0a0097b0755acf9b47ac332792ffaaeac",
    RUBRIC_PATH.as_posix(): "13fc4dbd77dfd2667dd601c481821f7ac5ce0bd5",
    SOURCE_INVENTORY_PATH.as_posix(): "0ad3aa46086d7ed6955448b7bd01d7c7b08969d7",
}

FORBIDDEN_REVIEWER_KEYS = frozenset(
    {
        "run_id",
        "condition_id",
        "route",
        "route_schedule_id",
        "worker_id",
        "worker_identity",
        "cache_namespace",
        "cache_namespace_id",
        "cache_telemetry",
        "latency",
        "cost",
        "planned_order_index",
        "condition_fingerprint",
        "internal_rendered_prompt",
        "expected_answer",
        "expected_answer_key",
        "required_claims",
        "forbidden_claims",
    }
)


class MeasuredReviewError(RuntimeError):
    """Fail-closed measured-review successor error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise MeasuredReviewError("FINAL_342_REVIEW_SUCCESSOR_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceBinding(FrozenModel):
    role: str = Field(min_length=3)
    path: str = Field(min_length=3)
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")


class SecondarySchedulePolicy(FrozenModel):
    status: Literal["IMPLEMENTED_AS_PROTECTED_DETERMINISTIC_MATERIALIZATION"]
    protected_path: Literal[
        ".local/auragateway/final-342-protected-review-v1/review_sample_schedule_v1.json"
    ]
    population: Literal[162]
    target: Literal[41]
    stratum_count: Literal[12]
    seed: Literal[20260712]
    allocation_method: Literal["hamilton_largest_remainder"]
    schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schedule_bytes_publicly_persisted: Literal[False]
    schedule_digest_publicly_persisted: Literal[True]
    observed_outcomes_used: Literal[False]
    replacement_permitted: Literal[False]
    materialization_required_in_acceptance_gate: Literal[True]
    final_manifest_must_bind_schedule_sha256: Literal[True]


class ProtectedCapturePolicy(FrozenModel):
    status: Literal["IMPLEMENTED_THIN_SUCCESSOR"]
    hook_source: Literal["execute_transport_attempt.return.TransportExecutionResult"]
    producer_modification_required: Literal[False]
    consume_transient_response_object: Literal[True]
    response_json_object_valid_required: Literal[True]
    append_only_turn_capture: Literal[True]
    protected_root: Literal[".local/auragateway/final-342-protected-review-v1"]
    raw_run_id_protected_only: Literal[True]
    internal_rendered_prompt_captured: Literal[False]
    capture_failure_state: Literal["EVIDENCE_INCOMPLETE"]
    capture_failure_is_model_failure: Literal[False]
    capture_failure_may_be_silent: Literal[False]
    replacement_after_capture_failure_permitted: Literal[False]


class ReviewerExportPolicy(FrozenModel):
    status: Literal["IMPLEMENTED_THIN_SUCCESSOR"]
    primary_assignment_required_for_every_reviewable_candidate: Literal[True]
    secondary_assignment_only_for_predeclared_schedule: Literal[True]
    reviewer_payload_forbidden_fields_fail_closed: Literal[True]
    condition_id_visible: Literal[False]
    route_visible: Literal[False]
    worker_identity_visible: Literal[False]
    cache_telemetry_visible: Literal[False]
    latency_visible: Literal[False]
    cost_visible: Literal[False]
    planned_run_order_visible: Literal[False]
    internal_rendered_prompt_visible: Literal[False]
    expected_answer_key_visible: Literal[False]
    public_receipt_digest_only: Literal[True]
    public_receipt_item_count_semantics: Literal["unique_review_item_count"]
    raw_outputs_in_public_evidence: Literal[False]


class RetentionPolicy(FrozenModel):
    event_driven_deletion_only: Literal[True]
    review_complete_required: Literal[True]
    adjudication_complete_required: Literal[True]
    analysis_inputs_materialized_required: Literal[True]
    public_receipt_verified_required: Literal[True]
    deletion_receipt_required: Literal[True]
    deletion_authorized_now: Literal[False]


class ImplementationBoundary(FrozenModel):
    producer_modification_authorized: Literal[False]
    measured_quality_reducers_implemented: Literal[False]
    measured_feedback_successor_implemented: Literal[False]
    analysis_engine_implemented: Literal[False]
    offline_integration_rehearsal_implemented: Literal[False]
    next_missing_boundary: Literal["FINAL_342_MEASURED_QUALITY_REDUCERS_V1"]


class SafetyState(FrozenModel):
    model_requests_performed: Literal[0]
    gpu_execution_performed: Literal[False]
    kaggle_execution_performed: Literal[False]
    execution_manifest_frozen: Literal[False]
    manifest_freeze_permitted: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class MeasuredReviewSuccessorRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    successor_id: Literal["auragateway-final-342-measured-review-successor-v1"]
    status: Literal["PROPOSED_FOR_FINAL_342_MEASURED_REVIEW_SUCCESSOR_ACCEPTANCE"]
    base_main_commit: Literal["6d9f1c5cb54ab89e6e199ba42c676282330410b0"]
    decision: Literal["FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1"]
    source_bindings: tuple[SourceBinding, ...] = Field(min_length=11, max_length=11)
    secondary_schedule: SecondarySchedulePolicy
    protected_capture: ProtectedCapturePolicy
    reviewer_export: ReviewerExportPolicy
    retention: RetentionPolicy
    implementation_boundary: ImplementationBoundary
    safety_state: SafetyState
    next_gate: Literal["AUTHOR_FINAL_342_MEASURED_QUALITY_REDUCERS_V1"]

    @model_validator(mode="after")
    def validate_record(self) -> Self:
        observed = {item.path: item.git_blob_sha for item in self.source_bindings}
        if observed != EXPECTED_SOURCE_BLOBS:
            raise ValueError("measured-review successor source binding set drifted")
        if self.secondary_schedule.schedule_sha256 != EXPECTED_SCHEDULE_SHA256:
            raise ValueError("measured-review schedule digest drifted")
        return self


class SecondaryScheduleEntry(FrozenModel):
    planned_order_index: int = Field(ge=0)
    run_id: str = Field(min_length=3)
    episode_id: str = Field(min_length=3)
    condition_id: Literal["A", "B", "C"]
    expected_terminal_decision: Literal["answer", "clarify", "escalate", "refuse"]
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    secondary_assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")


class ProtectedSchedule(FrozenModel):
    schema_version: Literal["1.0.0"]
    schedule_id: Literal["auragateway-final-342-secondary-review-schedule-v1"]
    population: Literal[162]
    target: Literal[41]
    seed: Literal[20260712]
    allocation: dict[str, int]
    entries: tuple[SecondaryScheduleEntry, ...] = Field(min_length=41, max_length=41)

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        run_ids = tuple(item.run_id for item in self.entries)
        review_ids = tuple(item.review_item_id for item in self.entries)
        assignment_ids = tuple(item.secondary_assignment_id for item in self.entries)
        if len(set(run_ids)) != 41:
            raise ValueError("secondary schedule run IDs must be unique")
        if len(set(review_ids)) != 41:
            raise ValueError("secondary schedule review IDs must be unique")
        if len(set(assignment_ids)) != 41:
            raise ValueError("secondary schedule assignment IDs must be unique")
        expected_order = tuple(sorted(item.planned_order_index for item in self.entries))
        observed_order = tuple(item.planned_order_index for item in self.entries)
        if observed_order != expected_order:
            raise ValueError("secondary schedule must follow planned order")
        return self


class TransportResultView(Protocol):
    response_object: dict[str, object] | None
    response_json_object_valid: bool


class ProtectedTurnCapture(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    run_id: str = Field(min_length=3)
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(min_length=3)
    turn_index: int = Field(ge=1, le=4)
    user_message: str = Field(min_length=1)
    assistant_output: dict[str, object]
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_json_object_valid: Literal[True] = True
    terminal_structured_result: dict[str, object] | None = None
    citation_source_ids: tuple[str, ...] = ()
    deterministic_validation_summary: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_capture(self) -> Self:
        if self.review_item_id != core.protected_review_id(self.run_id):
            raise ValueError("protected capture review identity drifted")
        digest = sha256_bytes(canonical_json_bytes(self.assistant_output))
        if self.response_sha256 != digest:
            raise ValueError("protected capture response digest drifted")
        return self


class ReviewerTurn(FrozenModel):
    turn_index: int = Field(ge=1, le=4)
    user_message: str = Field(min_length=1)
    assistant_output: dict[str, object]
    citation_source_ids: tuple[str, ...] = ()


class ReviewerPayload(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(min_length=3)
    rubric_id: Literal["auragateway-quality-rubric-v1"] = RUBRIC_ID
    rubric_sha256: Literal["7e9ddcc086392a8c571e406257edce0fd8cf962f055746245e3e0219c3844951"] = (
        RUBRIC_SHA256
    )
    turns: tuple[ReviewerTurn, ...] = Field(min_length=4, max_length=4)
    terminal_structured_result: dict[str, object] | None = None
    frozen_source_evidence: tuple[dict[str, object], ...] = ()
    deterministic_validation_summary: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_blinding(self) -> Self:
        assert_reviewer_safe(self.model_dump(mode="python"))
        return self


class ProtectedExport(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    export_id: Literal["auragateway-final-342-protected-review-export-v1"] = (
        "auragateway-final-342-protected-review-export-v1"
    )
    review_item_count: int = Field(ge=1)
    assignment_count: int = Field(ge=1)
    assignments: tuple[ReviewerPayload, ...] = Field(min_length=1)


class DeletionAuthorization(FrozenModel):
    review_complete: bool
    adjudication_complete: bool
    analysis_inputs_materialized: bool
    public_receipt_verified: bool


class DeletionReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal["auragateway-final-342-protected-review-deletion-v1"] = (
        "auragateway-final-342-protected-review-deletion-v1"
    )
    deleted_root: Literal[".local/auragateway/final-342-protected-review-v1"]
    deleted_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_complete: Literal[True]
    adjudication_complete: Literal[True]
    analysis_inputs_materialized: Literal[True]
    public_receipt_verified: Literal[True]


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_JSON_READ_FAILED",
            f"unable to read JSON object: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_JSON_SHAPE_INVALID",
            f"JSON value must be a string-keyed object: {path.as_posix()}",
        )
    return cast(dict[str, object], value)


def _git_blob_sha(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_SOURCE_MISSING",
            f"required source is missing or symlinked: {relative}",
        )
    result = subprocess.run(
        ["git", "hash-object", "--", relative],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_GIT_HASH_FAILED",
            f"unable to hash required source: {relative}",
        )
    return result.stdout.strip()


def _require_base_main_ancestor(root: Path) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_BASE_MAIN, "HEAD"],
        cwd=root,
        capture_output=True,
        check=False,
        text=True,
    )
    if result.returncode != 0:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_BASE_MAIN_INVALID",
            "accepted G11.7 merge must be an ancestor of current HEAD",
        )


def _validate_source_bindings(
    root: Path,
    record: MeasuredReviewSuccessorRecord,
) -> None:
    observed = {item.path: item.git_blob_sha for item in record.source_bindings}
    if observed != EXPECTED_SOURCE_BLOBS:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_SOURCE_SET_DRIFT",
            "measured-review successor source binding set drifted",
        )
    for relative, expected in EXPECTED_SOURCE_BLOBS.items():
        if _git_blob_sha(root, relative) != expected:
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_SOURCE_IDENTITY_DRIFT",
                f"measured-review predecessor identity drifted: {relative}",
            )


def _normalized_allocation() -> dict[str, int]:
    raw = review_design.secondary_review_stratum_allocation()
    return {
        f"{condition}|{decision}": count for (condition, decision), count in sorted(raw.items())
    }


def _functional_planned_order_indexes(root: Path) -> dict[str, int]:
    ledger = _read_json_object(root / LEDGER_PATH)
    runs = ledger.get("runs")
    if not isinstance(runs, list):
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_LEDGER_INVALID",
            "planned-run ledger runs must be an array",
        )

    indexes: dict[str, int] = {}
    for raw in runs:
        if not isinstance(raw, dict):
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_LEDGER_ROW_INVALID",
                "planned-run ledger row must be an object",
            )
        if raw.get("workload") != "functional":
            continue

        run_id = raw.get("run_id")
        planned_order_index = raw.get("planned_order_index")
        if (
            not isinstance(run_id, str)
            or not isinstance(planned_order_index, int)
            or isinstance(planned_order_index, bool)
        ):
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_FUNCTIONAL_IDENTITY_INVALID",
                "functional run requires string run_id and integer planned_order_index",
            )
        if run_id in indexes:
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_FUNCTIONAL_RUN_DUPLICATE",
                "functional run IDs must remain unique",
            )
        indexes[run_id] = planned_order_index

    if len(indexes) != 162:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_FUNCTIONAL_POPULATION_DRIFT",
            "planned ledger must contain exactly 162 functional trajectories",
        )
    return indexes


def derive_protected_schedule(root: Path) -> ProtectedSchedule:
    rows = seam_audit.derive_secondary_schedule(root)
    planned_order_indexes = _functional_planned_order_indexes(root)
    entries: list[SecondaryScheduleEntry] = []

    for row in rows:
        run_id = row.get("run_id")
        if not isinstance(run_id, str):
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_SCHEDULE_RUN_ID_INVALID",
                "derived secondary schedule requires a string run_id",
            )
        planned_order_index = planned_order_indexes.get(run_id)
        if planned_order_index is None:
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_SCHEDULE_LINKAGE_INVALID",
                "derived secondary schedule references an unknown functional run",
            )

        payload = dict(row)
        payload["planned_order_index"] = planned_order_index
        entries.append(SecondaryScheduleEntry.model_validate(payload))

    return ProtectedSchedule(
        schema_version="1.0.0",
        schedule_id="auragateway-final-342-secondary-review-schedule-v1",
        population=162,
        target=41,
        seed=20260712,
        allocation=_normalized_allocation(),
        entries=tuple(entries),
    )


def protected_schedule_bytes(root: Path) -> bytes:
    schedule = derive_protected_schedule(root)
    return canonical_json_bytes(schedule.model_dump(mode="json"))


def _write_once(path: Path, payload: bytes) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_PROTECTED_PATH_UNSAFE",
                f"protected path is not a regular file: {path.as_posix()}",
            )
        if path.read_bytes() != payload:
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_APPEND_ONLY_CONFLICT",
                f"protected append-only bytes conflict: {path.as_posix()}",
            )
        return False

    temp = path.with_name(f".{path.name}.tmp")
    if temp.exists():
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_TEMP_RESIDUE",
            f"protected write temp already exists: {temp.as_posix()}",
        )

    with temp.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    try:
        os.rename(temp, path)
    except OSError:
        if temp.exists():
            temp.unlink()
        if path.is_file() and path.read_bytes() == payload:
            return False
        raise
    return True


def materialize_protected_schedule(
    root: Path,
    protected_root: Path | None = None,
) -> tuple[Path, str, bool]:
    schedule_bytes = protected_schedule_bytes(root)
    digest = sha256_bytes(schedule_bytes)
    if digest != EXPECTED_SCHEDULE_SHA256:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_SCHEDULE_DIGEST_DRIFT",
            "derived secondary-review schedule digest drifted",
        )
    target_root = protected_root if protected_root is not None else root / PROTECTED_REVIEW_ROOT
    target = target_root / PROTECTED_SCHEDULE_PATH.name
    created = _write_once(target, schedule_bytes)
    return target, digest, created


def _walk_reviewer_value(value: object) -> Iterable[tuple[str, object]]:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if isinstance(key, str):
                yield key, item
                yield from _walk_reviewer_value(item)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from _walk_reviewer_value(item)


def assert_reviewer_safe(value: object) -> None:
    forbidden = sorted(
        key for key, _ in _walk_reviewer_value(value) if key in FORBIDDEN_REVIEWER_KEYS
    )
    if forbidden:
        raise ValueError(
            "reviewer payload contains forbidden fields: " + ",".join(sorted(set(forbidden)))
        )


def capture_transport_response(
    *,
    store_root: Path,
    transport_result: TransportResultView,
    run_id: str,
    episode_id: str,
    turn_index: int,
    user_message: str,
    terminal_structured_result: dict[str, object] | None = None,
    citation_source_ids: tuple[str, ...] = (),
    deterministic_validation_summary: dict[str, object] | None = None,
) -> ProtectedTurnCapture:
    if not transport_result.response_json_object_valid:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_RESPONSE_OBJECT_INVALID",
            "protected review capture requires a valid JSON response object",
        )
    response = transport_result.response_object
    if response is None:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_RESPONSE_OBJECT_MISSING",
            "protected review capture requires the transient response object",
        )

    capture = ProtectedTurnCapture(
        run_id=run_id,
        review_item_id=core.protected_review_id(run_id),
        episode_id=episode_id,
        turn_index=turn_index,
        user_message=user_message,
        assistant_output=response,
        response_sha256=sha256_bytes(canonical_json_bytes(response)),
        terminal_structured_result=terminal_structured_result,
        citation_source_ids=citation_source_ids,
        deterministic_validation_summary=(
            deterministic_validation_summary if deterministic_validation_summary is not None else {}
        ),
    )
    path = store_root / capture.review_item_id / f"turn-{capture.turn_index:02d}.json"
    _write_once(path, canonical_json_bytes(capture.model_dump(mode="json")))
    return capture


def load_captures(
    store_root: Path,
    review_item_id: str,
) -> tuple[ProtectedTurnCapture, ...]:
    captures: list[ProtectedTurnCapture] = []
    for turn_index in range(1, 5):
        path = store_root / review_item_id / f"turn-{turn_index:02d}.json"
        if not path.is_file() or path.is_symlink():
            raise MeasuredReviewError(
                "FINAL_342_REVIEW_SUCCESSOR_CAPTURE_INCOMPLETE",
                "reviewable trajectory requires all four protected turn captures",
            )
        captures.append(ProtectedTurnCapture.model_validate(_read_json_object(path)))
    run_ids = {item.run_id for item in captures}
    episode_ids = {item.episode_id for item in captures}
    if len(run_ids) != 1 or len(episode_ids) != 1:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_CAPTURE_IDENTITY_DRIFT",
            "protected turn captures must share one run and episode identity",
        )
    return tuple(captures)


def _secondary_run_ids(schedule: ProtectedSchedule) -> frozenset[str]:
    return frozenset(item.run_id for item in schedule.entries)


def build_reviewer_payloads(
    *,
    captures: Sequence[ProtectedTurnCapture],
    schedule: ProtectedSchedule,
    frozen_source_evidence: tuple[dict[str, object], ...] = (),
    deterministic_validation_summary: dict[str, object] | None = None,
) -> tuple[ReviewerPayload, ...]:
    if len(captures) != 4:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_CAPTURE_COUNT_INVALID",
            "reviewer export requires exactly four protected turn captures",
        )
    ordered = tuple(sorted(captures, key=lambda item: item.turn_index))
    if tuple(item.turn_index for item in ordered) != (1, 2, 3, 4):
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_CAPTURE_TURN_SET_INVALID",
            "reviewer export requires turn indices 1 through 4 exactly once",
        )
    run_ids = {item.run_id for item in ordered}
    episode_ids = {item.episode_id for item in ordered}
    review_ids = {item.review_item_id for item in ordered}
    if len(run_ids) != 1 or len(episode_ids) != 1 or len(review_ids) != 1:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_CAPTURE_IDENTITY_DRIFT",
            "reviewer export captures must share one protected identity",
        )

    run_id = ordered[0].run_id
    review_item_id = ordered[0].review_item_id
    episode_id = ordered[0].episode_id
    summary = (
        deterministic_validation_summary if deterministic_validation_summary is not None else {}
    )
    terminal = ordered[-1].terminal_structured_result
    turns = tuple(
        ReviewerTurn(
            turn_index=item.turn_index,
            user_message=item.user_message,
            assistant_output=item.assistant_output,
            citation_source_ids=item.citation_source_ids,
        )
        for item in ordered
    )

    roles: list[Literal["primary", "secondary"]] = ["primary"]
    if run_id in _secondary_run_ids(schedule):
        roles.append("secondary")

    payloads = tuple(
        ReviewerPayload(
            assignment_id=review_design.role_assignment_id(review_item_id, role),
            review_item_id=review_item_id,
            episode_id=episode_id,
            turns=turns,
            terminal_structured_result=terminal,
            frozen_source_evidence=frozen_source_evidence,
            deterministic_validation_summary=summary,
        )
        for role in roles
    )
    return payloads


def write_protected_export(
    *,
    protected_root: Path,
    assignments: Sequence[ReviewerPayload],
) -> core.ProtectedReviewPublicReceipt:
    if not assignments:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_EXPORT_EMPTY",
            "protected reviewer export requires at least one assignment",
        )
    for assignment in assignments:
        assert_reviewer_safe(assignment.model_dump(mode="python"))

    unique_review_items = {item.review_item_id for item in assignments}
    export = ProtectedExport(
        review_item_count=len(unique_review_items),
        assignment_count=len(assignments),
        assignments=tuple(assignments),
    )
    payload = canonical_json_bytes(export.model_dump(mode="json"))
    target = protected_root / PROTECTED_EXPORT_PATH.name
    _write_once(target, payload)
    return core.ProtectedReviewPublicReceipt(
        export_sha256=sha256_bytes(payload),
        item_count=len(unique_review_items),
        retention_and_deletion_rule_bound=True,
    )


def _protected_tree_digest(root: Path) -> str:
    if not root.is_dir() or root.is_symlink():
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_DELETE_ROOT_INVALID",
            "protected review root must be a real directory before deletion",
        )
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        payload = path.read_bytes()
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def delete_protected_review_material(
    *,
    protected_root: Path,
    authorization: DeletionAuthorization,
    receipt_path: Path,
) -> DeletionReceipt:
    if not (
        authorization.review_complete
        and authorization.adjudication_complete
        and authorization.analysis_inputs_materialized
        and authorization.public_receipt_verified
    ):
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_DELETION_NOT_AUTHORIZED",
            "protected raw review material cannot be deleted before all retention gates",
        )
    digest = _protected_tree_digest(protected_root)
    shutil.rmtree(protected_root)
    receipt = DeletionReceipt(
        deleted_root=".local/auragateway/final-342-protected-review-v1",
        deleted_material_sha256=digest,
        review_complete=True,
        adjudication_complete=True,
        analysis_inputs_materialized=True,
        public_receipt_verified=True,
    )
    _write_once(receipt_path, canonical_json_bytes(receipt.model_dump(mode="json")))
    return receipt


def _validate_record_and_schedule(
    root: Path,
    *,
    require_protected_schedule: bool,
) -> tuple[MeasuredReviewSuccessorRecord, str, bool]:
    record = MeasuredReviewSuccessorRecord.model_validate(_read_json_object(root / RECORD_PATH))
    _require_base_main_ancestor(root)
    _validate_source_bindings(root, record)

    derived_bytes = protected_schedule_bytes(root)
    digest = sha256_bytes(derived_bytes)
    if digest != EXPECTED_SCHEDULE_SHA256:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_SCHEDULE_DIGEST_DRIFT",
            "derived protected schedule digest drifted",
        )
    if record.secondary_schedule.schedule_sha256 != digest:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_RECORD_SCHEDULE_DRIFT",
            "recorded protected schedule digest differs from derived bytes",
        )

    protected_path = root / PROTECTED_SCHEDULE_PATH
    materialized = protected_path.is_file() and not protected_path.is_symlink()
    if materialized and protected_path.read_bytes() != derived_bytes:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_PROTECTED_SCHEDULE_CONFLICT",
            "materialized protected schedule differs from deterministic bytes",
        )
    if require_protected_schedule and not materialized:
        raise MeasuredReviewError(
            "FINAL_342_REVIEW_SUCCESSOR_PROTECTED_SCHEDULE_MISSING",
            "acceptance requires the exact protected schedule to be materialized",
        )
    return record, digest, materialized


def validate(
    repo_root: Path,
    *,
    require_protected_schedule: bool = False,
) -> dict[str, object]:
    root = repo_root.resolve()
    record, digest, materialized = _validate_record_and_schedule(
        root,
        require_protected_schedule=require_protected_schedule,
    )
    schedule = derive_protected_schedule(root)
    return {
        "status": "FINAL_342_MEASURED_REVIEW_SUCCESSOR_V1_VALID",
        "secondary_schedule_count": len(schedule.entries),
        "secondary_schedule_sha256": digest,
        "protected_schedule_materialized": materialized,
        "producer_modification_required": False,
        "protected_capture_implemented": True,
        "reviewer_export_implemented": True,
        "public_receipt_digest_only": True,
        "manifest_freeze_permitted": record.safety_state.manifest_freeze_permitted,
        "final_measured_abc_execution_authorized": (
            record.safety_state.final_measured_abc_execution_authorized
        ),
        "effect_claims_permitted": record.safety_state.effect_claims_permitted,
        "next_gate": record.next_gate,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=("validate", "materialize-schedule"),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument(
        "--require-protected-schedule",
        action="store_true",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root)
    try:
        if args.command == "materialize-schedule":
            path, digest, created = materialize_protected_schedule(root.resolve())
            result: dict[str, object] = {
                "status": "FINAL_342_PROTECTED_REVIEW_SCHEDULE_MATERIALIZED",
                "path": path.relative_to(root.resolve()).as_posix(),
                "schedule_sha256": digest,
                "created": created,
                "secondary_schedule_count": 41,
                "model_requests_performed": 0,
                "gpu_execution_performed": False,
                "kaggle_execution_performed": False,
                "final_measured_abc_execution_authorized": False,
            }
        else:
            result = validate(
                root,
                require_protected_schedule=args.require_protected_schedule,
            )
    except (
        MeasuredReviewError,
        ValidationError,
        OSError,
        UnicodeDecodeError,
        subprocess.SubprocessError,
    ) as error:
        if isinstance(error, MeasuredReviewError):
            code = error.error_code
            message = error.safe_message
        else:
            code = "FINAL_342_REVIEW_SUCCESSOR_VALIDATION_FAILED"
            message = str(error)
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Freeze the complete 35-case Final-342 Jev shadow batch without network I/O."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    DisagreementReason,
    MaterialDisagreement,
    QualityReviewRecord,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_runner_v1 as canary_runner,
)
from auragateway.local_abc import (
    final_342_jev_shadow_canary_v1 as canary,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as review_bridge,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)

EXPECTED_BATCH_SIZE: Literal[35] = 35
EXPECTED_EXECUTED_CANARY_COUNT: Literal[1] = 1
EXPECTED_PENDING_COUNT: Literal[34] = 34

EXPECTED_CANARY_REQUEST_SHA256: Literal[
    "5771e2b850afed39e05f4a31589b73e792a33e75c40bbaeb57cff8ad303f7d52"
] = "5771e2b850afed39e05f4a31589b73e792a33e75c40bbaeb57cff8ad303f7d52"

EXPECTED_CANARY_RESPONSE_SHA256: Literal[
    "abb8b51a37726604af4a7abc2e93d8ded376f9c7233869575fc97dbca9f1da93"
] = "abb8b51a37726604af4a7abc2e93d8ded376f9c7233869575fc97dbca9f1da93"

BATCH_ROOT = Path(".local/auragateway/jev-shadow-adjudication-v1/batch-v1")
BATCH_REQUEST_ROOT = BATCH_ROOT / "requests"
BATCH_MANIFEST_PATH = BATCH_ROOT / "manifest.json"


class JevBatchFreezeError(RuntimeError):
    """Fail-closed 35-case batch-freeze error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BatchExecutionPolicy(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    ordering: Literal["FROZEN_SECONDARY_SCHEDULE_MATERIAL_DISAGREEMENT_ORDER"] = (
        "FROZEN_SECONDARY_SCHEDULE_MATERIAL_DISAGREEMENT_ORDER"
    )
    request_schema: Literal["J4_CANARY_SHAPE_V1"] = "J4_CANARY_SHAPE_V1"
    execution_mode: Literal["SERIAL_ONE_AT_A_TIME"] = "SERIAL_ONE_AT_A_TIME"
    max_in_flight_requests: Literal[1] = 1
    stop_policy: Literal["STOP_ON_FIRST_PROVIDER_VALIDATION_OR_PERSISTENCE_FAILURE"] = (
        "STOP_ON_FIRST_PROVIDER_VALIDATION_OR_PERSISTENCE_FAILURE"
    )
    retry_policy: Literal["NO_AUTOMATIC_RETRY"] = "NO_AUTOMATIC_RETRY"
    anti_replay_policy: Literal["VALIDATED_EXISTING_RESPONSE_AND_RECEIPT_SKIP_PROVIDER_REQUEST"] = (
        "VALIDATED_EXISTING_RESPONSE_AND_RECEIPT_SKIP_PROVIDER_REQUEST"
    )
    model_pin: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    failure_threshold_frozen: Literal[False] = False
    threshold_selection_deferred_until_calibration: Literal[True] = True
    authoritative_human_adjudication_remains_separate: Literal[True] = True


class FrozenBatchEntry(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    batch_index: int = Field(ge=0, le=34)
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    request_relative_path: str = Field(min_length=1)
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    disagreement_reasons: tuple[DisagreementReason, ...] = Field(min_length=1)
    criterion_score_deltas: dict[RubricCriterion, int]
    lifecycle_state: Literal["EXECUTED_CANARY", "FROZEN_PENDING"]
    provider_request_already_performed: bool
    response_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    authoritative_adjudication_present: Literal[False] = False

    @model_validator(mode="after")
    def validate_entry(self) -> FrozenBatchEntry:
        if set(self.criterion_score_deltas) != set(RubricCriterion):
            raise ValueError("batch entry score deltas must cover all criteria")
        is_canary = self.lifecycle_state == "EXECUTED_CANARY"
        if is_canary != self.provider_request_already_performed:
            raise ValueError("batch entry lifecycle/provider state is inconsistent")
        if is_canary != (self.response_sha256 is not None):
            raise ValueError("executed canary must be the only entry with a response digest")
        if self.batch_index == 0 and not is_canary:
            raise ValueError("batch index zero must be the executed J4 canary")
        if self.batch_index > 0 and is_canary:
            raise ValueError("only batch index zero may be the executed J4 canary")
        return self


class FrozenBatchManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_35_CASE_SHADOW_BATCH_FROZEN"] = (
        "FINAL_342_JEV_35_CASE_SHADOW_BATCH_FROZEN"
    )
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    batch_size: Literal[35]
    executed_canary_count: Literal[1]
    pending_count: Literal[34]
    question_count_per_case: Literal[29]
    criterion_question_count_per_case: Literal[7]
    failure_question_count_per_case: Literal[22]
    canary_request_sha256: Literal[
        "5771e2b850afed39e05f4a31589b73e792a33e75c40bbaeb57cff8ad303f7d52"
    ] = EXPECTED_CANARY_REQUEST_SHA256
    canary_response_sha256: Literal[
        "abb8b51a37726604af4a7abc2e93d8ded376f9c7233869575fc97dbca9f1da93"
    ] = EXPECTED_CANARY_RESPONSE_SHA256
    request_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: BatchExecutionPolicy
    entries: tuple[FrozenBatchEntry, ...] = Field(min_length=35, max_length=35)
    authoritative_adjudication_count: Literal[0] = 0
    provider_requests_performed_during_freeze: Literal[0] = 0
    protected_final_342_data_sent_during_freeze: Literal[False] = False
    human_adjudication_seen_by_jev: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal["J5B_VALIDATE_FROZEN_BATCH_AND_AUTHOR_RUNNER"] = (
        "J5B_VALIDATE_FROZEN_BATCH_AND_AUTHOR_RUNNER"
    )

    @model_validator(mode="after")
    def validate_manifest(self) -> FrozenBatchManifest:
        indices = tuple(item.batch_index for item in self.entries)
        if indices != tuple(range(EXPECTED_BATCH_SIZE)):
            raise ValueError("batch indices must be exactly 0..34 in frozen order")
        review_item_ids = tuple(item.review_item_id for item in self.entries)
        if len(set(review_item_ids)) != EXPECTED_BATCH_SIZE:
            raise ValueError("batch review-item IDs must be unique")
        request_hashes = tuple(item.request_sha256 for item in self.entries)
        if len(set(request_hashes)) != EXPECTED_BATCH_SIZE:
            raise ValueError("batch request hashes must be unique")
        executed = tuple(item for item in self.entries if item.lifecycle_state == "EXECUTED_CANARY")
        pending = tuple(item for item in self.entries if item.lifecycle_state == "FROZEN_PENDING")
        if len(executed) != EXPECTED_EXECUTED_CANARY_COUNT:
            raise ValueError("batch must contain exactly one executed canary")
        if len(pending) != EXPECTED_PENDING_COUNT:
            raise ValueError("batch must contain exactly 34 pending requests")
        if self.entries[0].request_sha256 != self.canary_request_sha256:
            raise ValueError("batch index zero request differs from J4 canary")
        if self.entries[0].response_sha256 != self.canary_response_sha256:
            raise ValueError("batch index zero response differs from J4 canary")
        return self


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_FILE_MISSING",
            f"required batch-freeze input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_JSON_INVALID",
            f"batch-freeze input is not valid JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_JSON_SHAPE_INVALID",
            f"batch-freeze JSON root must be an object: {path.as_posix()}",
        )
    return value


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise JevBatchFreezeError(
                "FINAL_342_JEV_BATCH_FREEZE_PATH_UNSAFE",
                f"batch-freeze output path is unsafe: {path.as_posix()}",
            )
        if path.read_bytes() != payload:
            raise JevBatchFreezeError(
                "FINAL_342_JEV_BATCH_FREEZE_APPEND_ONLY_CONFLICT",
                f"existing batch-freeze output differs: {path.as_posix()}",
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_TEMP_RESIDUE",
            f"temporary batch-freeze output already exists: {temporary.as_posix()}",
        )
    temporary.write_bytes(payload)
    temporary.replace(path)


def _authoritative_adjudication_path(root: Path, review_item_id: str) -> Path:
    return root / review_bridge.REVIEW_RESULT_ROOT / "adjudications" / f"{review_item_id}.json"


def _load_live_canary_receipt(root: Path) -> canary_runner.LiveCanaryReceipt:
    receipt_path = root / canary_runner.CANARY_RECEIPT_PATH
    response_path = root / canary_runner.CANARY_RESPONSE_PATH

    try:
        receipt = canary_runner.LiveCanaryReceipt.model_validate(_read_json_object(receipt_path))
    except ValidationError as error:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_RECEIPT_INVALID",
            "J4 live canary receipt failed typed validation",
        ) from error

    if receipt.provider_request_performed is not True:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_NOT_EXECUTED",
            "persisted J4 canary receipt does not record the live provider call",
        )
    if receipt.provider_request_count_this_invocation != 1:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_REQUEST_COUNT_INVALID",
            "persisted J4 canary receipt does not record exactly one provider call",
        )
    if receipt.request_sha256 != EXPECTED_CANARY_REQUEST_SHA256:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_REQUEST_DRIFT",
            "J4 canary request digest differs from the accepted live receipt",
        )
    if receipt.response_sha256 != EXPECTED_CANARY_RESPONSE_SHA256:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_RESPONSE_DRIFT",
            "J4 canary response digest differs from the accepted live receipt",
        )

    response_bytes = response_path.read_bytes()
    if _sha256_bytes(response_bytes) != receipt.response_sha256:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_RESPONSE_BYTES_DRIFT",
            "persisted J4 canary response bytes differ from its receipt",
        )
    return receipt


def _request_for_material_case(
    payload: review_successor.ReviewerPayload,
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
    disagreement: MaterialDisagreement,
    rubric: BlindedQualityRubric,
) -> tuple[jev_contract.JevShadowRequest, bytes, str]:
    packet = canary.build_canary_packet(payload, primary, secondary, disagreement)
    safe_state = jev_contract.ReviewerSafeJevState(payload=packet.model_dump(mode="json"))
    request = jev_contract.build_request(safe_state, rubric)
    request_bytes = _canonical_bytes(request.model_dump(mode="json"))
    return request, request_bytes, _sha256_bytes(request_bytes)


def _inventory_digest(entries: tuple[FrozenBatchEntry, ...]) -> str:
    inventory = [
        {
            "batch_index": entry.batch_index,
            "review_item_id": entry.review_item_id,
            "episode_id": entry.episode_id,
            "request_sha256": entry.request_sha256,
            "lifecycle_state": entry.lifecycle_state,
        }
        for entry in entries
    ]
    return _sha256_bytes(_canonical_bytes(inventory))


def freeze_shadow_batch(repo_root: Path) -> FrozenBatchManifest:
    root = repo_root.resolve()

    live_canary = _load_live_canary_receipt(root)

    export, schedule, rubric, assignments = canary._load_inputs(root)
    material = canary._disagreement_inventory(
        root,
        export,
        schedule,
        rubric,
        assignments,
    )
    canary._validate_frozen_disagreement_shape(material)

    if len(material) != EXPECTED_BATCH_SIZE:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_POPULATION_INVALID",
            f"expected exactly 35 material disagreements; observed={len(material)}",
        )

    entries: list[FrozenBatchEntry] = []

    for batch_index, (payload, primary, secondary, disagreement) in enumerate(material):
        adjudication_path = _authoritative_adjudication_path(
            root,
            payload.review_item_id,
        )
        if adjudication_path.exists():
            raise JevBatchFreezeError(
                "FINAL_342_JEV_BATCH_FREEZE_AUTHORITATIVE_ADJUDICATION_PRESENT",
                (
                    "shadow batch must be frozen before human adjudication; "
                    f"review_item_id={payload.review_item_id}"
                ),
            )

        request, request_bytes, request_sha256 = _request_for_material_case(
            payload,
            primary,
            secondary,
            disagreement,
            rubric,
        )

        if len(request.questions) != 29:
            raise JevBatchFreezeError(
                "FINAL_342_JEV_BATCH_FREEZE_QUESTION_COUNT_DRIFT",
                "Jev request question inventory is not exactly 29",
            )

        request_relative_path = (
            BATCH_REQUEST_ROOT / f"{batch_index:02d}-{payload.review_item_id}.json"
        )
        _write_once(root / request_relative_path, request_bytes)

        is_canary = batch_index == 0
        entries.append(
            FrozenBatchEntry(
                batch_index=batch_index,
                review_item_id=payload.review_item_id,
                episode_id=payload.episode_id,
                request_relative_path=request_relative_path.as_posix(),
                request_sha256=request_sha256,
                disagreement_reasons=disagreement.reasons,
                criterion_score_deltas=disagreement.criterion_score_deltas,
                lifecycle_state=("EXECUTED_CANARY" if is_canary else "FROZEN_PENDING"),
                provider_request_already_performed=is_canary,
                response_sha256=(live_canary.response_sha256 if is_canary else None),
            )
        )

    frozen_entries = tuple(entries)

    canary_request_path = root / canary.CANARY_REQUEST_PATH
    canary_request_bytes = canary_request_path.read_bytes()

    if _sha256_bytes(canary_request_bytes) != EXPECTED_CANARY_REQUEST_SHA256:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_FILE_DRIFT",
            "persisted J4 canary request bytes differ from accepted digest",
        )

    first_request_path = root / frozen_entries[0].request_relative_path
    if first_request_path.read_bytes() != canary_request_bytes:
        raise JevBatchFreezeError(
            "FINAL_342_JEV_BATCH_FREEZE_CANARY_NOT_BYTE_IDENTICAL",
            "batch index zero is not byte-identical to the executed J4 canary",
        )

    manifest = FrozenBatchManifest(
        batch_size=EXPECTED_BATCH_SIZE,
        executed_canary_count=EXPECTED_EXECUTED_CANARY_COUNT,
        pending_count=EXPECTED_PENDING_COUNT,
        question_count_per_case=29,
        criterion_question_count_per_case=len(RubricCriterion),
        failure_question_count_per_case=len(EpisodeFailureLabel),
        request_inventory_sha256=_inventory_digest(frozen_entries),
        policy=BatchExecutionPolicy(),
        entries=frozen_entries,
    )

    _write_once(
        root / BATCH_MANIFEST_PATH,
        _canonical_bytes(manifest.model_dump(mode="json")),
    )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final_342_jev_shadow_batch_freeze_v1")
    parser.add_argument("command", choices=("freeze",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = freeze_shadow_batch(args.repo_root)
    print(manifest.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

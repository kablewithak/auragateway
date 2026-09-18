"""Prepare one real Final-342 Jev shadow-adjudication canary request."""

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
    ReviewRole,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.evals import blinded_quality as blinded_eval
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)
from auragateway.local_abc import (
    final_342_measured_review_execution_bridge_v1 as review_bridge,
)
from auragateway.local_abc import (
    final_342_measured_review_successor_v1 as review_successor,
)

EXPECTED_MATERIAL_DISAGREEMENTS: Literal[35] = 35
EXPECTED_VERDICT_MISMATCHES: Literal[0] = 0
EXPECTED_MATERIAL_SCORE_DELTAS: Literal[4] = 4
EXPECTED_FAILURE_LABEL_MISMATCHES: Literal[35] = 35

CANARY_ROOT = Path(".local/auragateway/jev-shadow-adjudication-v1/real-canary-v1")
CANARY_REQUEST_PATH = CANARY_ROOT / "request.json"
CANARY_MANIFEST_PATH = CANARY_ROOT / "manifest.json"


class JevCanaryError(RuntimeError):
    """Fail-closed real-canary preparation error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class InitialReviewView(FrozenModel):
    """Identity-free initial review shown to the shadow adjudicator."""

    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...]
    verdict: ReviewVerdict

    @model_validator(mode="after")
    def validate_scores(self) -> InitialReviewView:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("initial review must score all rubric criteria")
        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("initial review score must be in [1,4]")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("initial review failure labels must be unique")
        return self


class JevCanaryPacket(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    purpose: Literal["final_342_real_shadow_adjudication_canary"] = (
        "final_342_real_shadow_adjudication_canary"
    )
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    adjudication_instruction: str = Field(min_length=50, max_length=1500)
    visible_case_evidence: dict[str, Any]
    review_a: InitialReviewView
    review_b: InitialReviewView
    disagreement_reasons: tuple[DisagreementReason, ...] = Field(min_length=1)
    criterion_score_deltas: dict[RubricCriterion, int]

    @model_validator(mode="after")
    def validate_packet(self) -> JevCanaryPacket:
        if len(self.disagreement_reasons) != len(set(self.disagreement_reasons)):
            raise ValueError("canary disagreement reasons must be unique")
        if set(self.criterion_score_deltas) != set(RubricCriterion):
            raise ValueError("canary score deltas must cover all rubric criteria")
        return self


class JevCanaryManifest(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_REAL_CANARY_REQUEST_READY"] = (
        "FINAL_342_JEV_REAL_CANARY_REQUEST_READY"
    )
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    question_count: Literal[29]
    criterion_question_count: Literal[7]
    failure_question_count: Literal[22]
    material_disagreement_count: Literal[35]
    verdict_mismatch_count: Literal[0]
    material_score_delta_count: Literal[4]
    failure_label_mismatch_count: Literal[35]
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authoritative_adjudication_present_for_canary: Literal[False] = False
    human_adjudication_seen_by_jev: Literal[False] = False
    protected_final_342_data_sent: Literal[False] = False
    provider_request_performed: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal["J4B_LIVE_ONE_REAL_SHADOW_CANARY"] = "J4B_LIVE_ONE_REAL_SHADOW_CANARY"


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_FILE_MISSING",
            f"required canary input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_JSON_INVALID",
            f"canary input is not valid JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_JSON_SHAPE_INVALID",
            f"canary JSON root must be an object: {path.as_posix()}",
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
            raise JevCanaryError(
                "FINAL_342_JEV_CANARY_PATH_UNSAFE",
                f"canary output path is unsafe: {path.as_posix()}",
            )
        if path.read_bytes() != payload:
            raise JevCanaryError(
                "FINAL_342_JEV_CANARY_APPEND_ONLY_CONFLICT",
                f"existing canary output differs: {path.as_posix()}",
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_TEMP_RESIDUE",
            f"temporary canary path already exists: {temporary.as_posix()}",
        )
    temporary.write_bytes(payload)
    temporary.replace(path)


def _load_rubric(root: Path) -> BlindedQualityRubric:
    try:
        return BlindedQualityRubric.model_validate(
            _read_json_object(root / review_bridge.RUBRIC_PATH)
        )
    except ValidationError as error:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_RUBRIC_INVALID",
            "frozen quality rubric failed typed validation",
        ) from error


def _load_review(
    result_root: Path,
    assignment: review_bridge.ExpectedReviewAssignment,
    rubric: BlindedQualityRubric,
) -> QualityReviewRecord:
    path = result_root / "reviews" / f"{assignment.assignment_id}.json"
    try:
        review = QualityReviewRecord.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_REVIEW_INVALID",
            "persisted review failed typed validation",
        ) from error

    expected_role = ReviewRole.PRIMARY if assignment.role == "primary" else ReviewRole.SECONDARY
    if (
        review.review_id != assignment.assignment_id
        or review.episode_id != assignment.episode_id
        or review.role is not expected_role
    ):
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_REVIEW_IDENTITY_DRIFT",
            "persisted review does not match its frozen assignment",
        )

    expected_verdict = blinded_eval.expected_verdict(
        review.criterion_scores,
        len(review.failure_labels),
        rubric,
    )
    if review.verdict is not expected_verdict:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_REVIEW_VERDICT_INVALID",
            "persisted review verdict differs from the frozen rubric",
        )
    return review


def _find_assignment(
    assignments: tuple[review_bridge.ExpectedReviewAssignment, ...],
    *,
    review_item_id: str,
    role: Literal["primary", "secondary"],
) -> review_bridge.ExpectedReviewAssignment:
    matches = tuple(
        item for item in assignments if item.review_item_id == review_item_id and item.role == role
    )
    if len(matches) != 1:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_ASSIGNMENT_INVALID",
            f"expected exactly one {role} assignment for canary review item",
        )
    return matches[0]


def _score_map(review: QualityReviewRecord) -> dict[RubricCriterion, int]:
    return {item.criterion: item.score for item in review.criterion_scores}


def _review_view(review: QualityReviewRecord) -> InitialReviewView:
    return InitialReviewView(
        criterion_scores=_score_map(review),
        failure_labels=review.failure_labels,
        verdict=review.verdict,
    )


def _anonymized_review_pair(
    review_item_id: str,
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
) -> tuple[InitialReviewView, InitialReviewView]:
    candidates = (
        (
            hashlib.sha256(f"{review_item_id}|primary".encode()).hexdigest(),
            _review_view(primary),
        ),
        (
            hashlib.sha256(f"{review_item_id}|secondary".encode()).hexdigest(),
            _review_view(secondary),
        ),
    )
    ordered = tuple(sorted(candidates, key=lambda item: item[0]))
    return ordered[0][1], ordered[1][1]


def build_canary_packet(
    payload: review_successor.ReviewerPayload,
    primary: QualityReviewRecord,
    secondary: QualityReviewRecord,
    disagreement: MaterialDisagreement,
) -> JevCanaryPacket:
    if (
        payload.episode_id != primary.episode_id
        or payload.episode_id != secondary.episode_id
        or disagreement.episode_id != payload.episode_id
    ):
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_EPISODE_IDENTITY_DRIFT",
            "canary payload and reviews refer to different episodes",
        )

    review_a, review_b = _anonymized_review_pair(
        payload.review_item_id,
        primary,
        secondary,
    )

    visible_case_evidence = {
        "rubric_id": payload.rubric_id,
        "rubric_sha256": payload.rubric_sha256,
        "turns": [item.model_dump(mode="json") for item in payload.turns],
        "terminal_structured_result": payload.terminal_structured_result,
        "frozen_source_evidence": list(payload.frozen_source_evidence),
        "deterministic_validation_summary": payload.deterministic_validation_summary,
    }

    packet = JevCanaryPacket(
        review_item_id=payload.review_item_id,
        episode_id=payload.episode_id,
        adjudication_instruction=(
            "Independently determine the final frozen rubric scores and the "
            "likelihood that each exact failure label applies. Use only the "
            "visible case evidence. The two anonymous initial reviews are "
            "advisory evidence showing the disagreement to resolve; do not "
            "average them mechanically and do not assume either is correct."
        ),
        visible_case_evidence=visible_case_evidence,
        review_a=review_a,
        review_b=review_b,
        disagreement_reasons=disagreement.reasons,
        criterion_score_deltas=disagreement.criterion_score_deltas,
    )

    jev_contract.ReviewerSafeJevState(payload=packet.model_dump(mode="json"))
    return packet


def _load_inputs(
    root: Path,
) -> tuple[
    review_successor.ProtectedExport,
    review_successor.ProtectedSchedule,
    BlindedQualityRubric,
    tuple[review_bridge.ExpectedReviewAssignment, ...],
]:
    review_bridge.validate_inputs(root)

    protected_root = root / review_bridge.PROTECTED_REVIEW_ROOT
    export_path = protected_root / review_successor.PROTECTED_EXPORT_PATH.name
    schedule_path = protected_root / review_successor.PROTECTED_SCHEDULE_PATH.name

    try:
        export = review_successor.ProtectedExport.model_validate(_read_json_object(export_path))
        schedule = review_successor.ProtectedSchedule.model_validate(
            _read_json_object(schedule_path)
        )
    except ValidationError as error:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_PROTECTED_INPUT_INVALID",
            "protected review input failed typed validation",
        ) from error

    rubric = _load_rubric(root)
    assignments = review_bridge.project_expected_assignments(export, schedule)
    return export, schedule, rubric, assignments


def _disagreement_inventory(
    root: Path,
    export: review_successor.ProtectedExport,
    schedule: review_successor.ProtectedSchedule,
    rubric: BlindedQualityRubric,
    assignments: tuple[review_bridge.ExpectedReviewAssignment, ...],
) -> tuple[
    tuple[
        review_successor.ReviewerPayload,
        QualityReviewRecord,
        QualityReviewRecord,
        MaterialDisagreement,
    ],
    ...,
]:
    result_root = root / review_bridge.REVIEW_RESULT_ROOT
    payload_by_assignment = {payload.assignment_id: payload for payload in export.assignments}

    material: list[
        tuple[
            review_successor.ReviewerPayload,
            QualityReviewRecord,
            QualityReviewRecord,
            MaterialDisagreement,
        ]
    ] = []

    for schedule_entry in schedule.entries:
        primary_assignment = _find_assignment(
            assignments,
            review_item_id=schedule_entry.review_item_id,
            role="primary",
        )
        secondary_assignment = _find_assignment(
            assignments,
            review_item_id=schedule_entry.review_item_id,
            role="secondary",
        )

        primary = _load_review(result_root, primary_assignment, rubric)
        secondary = _load_review(result_root, secondary_assignment, rubric)

        disagreement = blinded_eval.detect_material_disagreement(
            primary,
            secondary,
            rubric,
        )
        if disagreement is None:
            continue

        payload = payload_by_assignment.get(primary_assignment.assignment_id)
        if payload is None:
            raise JevCanaryError(
                "FINAL_342_JEV_CANARY_REVIEWER_PAYLOAD_MISSING",
                "primary reviewer payload is missing from protected export",
            )

        material.append((payload, primary, secondary, disagreement))

    return tuple(material)


def _validate_frozen_disagreement_shape(
    material: tuple[
        tuple[
            review_successor.ReviewerPayload,
            QualityReviewRecord,
            QualityReviewRecord,
            MaterialDisagreement,
        ],
        ...,
    ],
) -> None:
    verdict_mismatches = 0
    material_score_deltas = 0
    failure_label_mismatches = 0

    for _payload, _primary, _secondary, disagreement in material:
        reasons = set(disagreement.reasons)
        if DisagreementReason.VERDICT_MISMATCH in reasons:
            verdict_mismatches += 1
        if DisagreementReason.MATERIAL_SCORE_DELTA in reasons:
            material_score_deltas += 1
        if DisagreementReason.FAILURE_LABEL_MISMATCH in reasons:
            failure_label_mismatches += 1

    observed = (
        len(material),
        verdict_mismatches,
        material_score_deltas,
        failure_label_mismatches,
    )
    expected = (
        EXPECTED_MATERIAL_DISAGREEMENTS,
        EXPECTED_VERDICT_MISMATCHES,
        EXPECTED_MATERIAL_SCORE_DELTAS,
        EXPECTED_FAILURE_LABEL_MISMATCHES,
    )
    if observed != expected:
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_DISAGREEMENT_SHAPE_DRIFT",
            (
                "review disagreement shape drifted from the pre-Jev frozen "
                f"state; observed={observed} expected={expected}"
            ),
        )


def prepare_real_canary(repo_root: Path) -> JevCanaryManifest:
    root = repo_root.resolve()

    export, schedule, rubric, assignments = _load_inputs(root)
    material = _disagreement_inventory(
        root,
        export,
        schedule,
        rubric,
        assignments,
    )
    _validate_frozen_disagreement_shape(material)

    payload, primary, secondary, disagreement = material[0]

    adjudication_path = (
        root / review_bridge.REVIEW_RESULT_ROOT / "adjudications" / f"{payload.review_item_id}.json"
    )
    if adjudication_path.exists():
        raise JevCanaryError(
            "FINAL_342_JEV_CANARY_AUTHORITATIVE_ADJUDICATION_PRESENT",
            "real canary must be prepared before authoritative human adjudication",
        )

    packet = build_canary_packet(
        payload,
        primary,
        secondary,
        disagreement,
    )
    safe_state = jev_contract.ReviewerSafeJevState(payload=packet.model_dump(mode="json"))
    request = jev_contract.build_request(safe_state, rubric)

    request_payload = request.model_dump(mode="json")
    request_bytes = _canonical_bytes(request_payload)
    request_sha256 = _sha256_bytes(request_bytes)

    manifest = JevCanaryManifest(
        review_item_id=packet.review_item_id,
        episode_id=packet.episode_id,
        question_count=len(request.questions),
        criterion_question_count=len(RubricCriterion),
        failure_question_count=len(EpisodeFailureLabel),
        material_disagreement_count=EXPECTED_MATERIAL_DISAGREEMENTS,
        verdict_mismatch_count=EXPECTED_VERDICT_MISMATCHES,
        material_score_delta_count=EXPECTED_MATERIAL_SCORE_DELTAS,
        failure_label_mismatch_count=EXPECTED_FAILURE_LABEL_MISMATCHES,
        request_sha256=request_sha256,
    )

    _write_once(root / CANARY_REQUEST_PATH, request_bytes)
    _write_once(
        root / CANARY_MANIFEST_PATH,
        _canonical_bytes(manifest.model_dump(mode="json")),
    )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final_342_jev_shadow_canary_v1")
    parser.add_argument("command", choices=("prepare",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    manifest = prepare_real_canary(args.repo_root)
    print(manifest.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

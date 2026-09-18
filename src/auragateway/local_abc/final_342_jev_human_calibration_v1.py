"""Read-only Final-342 Jev-vs-human calibration.

Requires J6 authoritative human adjudication to be complete. Performs no
provider calls, selects no deployment threshold, and persists only local
comparison/calibration evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.blinded_quality import (
    AdjudicationRecord,
    BlindedQualityRubric,
    CriterionScore,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.evals import blinded_quality as blinded_eval
from auragateway.local_abc import final_342_jev_shadow_adjudication_contract_v1 as jev_contract
from auragateway.local_abc import final_342_jev_shadow_batch_freeze_v1 as batch_freeze
from auragateway.local_abc import final_342_jev_shadow_batch_runner_v1 as batch_runner
from auragateway.local_abc import final_342_jev_shadow_canary_runner_v1 as canary_runner
from auragateway.local_abc import final_342_jev_shadow_canary_v1 as canary
from auragateway.local_abc import final_342_measured_review_execution_bridge_v1 as bridge

EXPECTED_CASE_COUNT: Literal[35] = 35
EXPECTED_JEV_REQUEST_INVENTORY_SHA256: Literal[
    "d009646abff567e35c94da8a61edf57f2cf8ac948bfe915e7941861abd359627"
] = "d009646abff567e35c94da8a61edf57f2cf8ac948bfe915e7941861abd359627"
THRESHOLD_GRID: tuple[float, ...] = (
    0.05,
    0.10,
    0.15,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
    0.90,
    0.95,
)
CALIBRATION_ROOT = Path(".local/auragateway/final-342-jev-human-calibration-v1")
CASE_COMPARISON_PATH = CALIBRATION_ROOT / "case-comparisons.json"
REPORT_PATH = CALIBRATION_ROOT / "report.json"
RECEIPT_PATH = CALIBRATION_ROOT / "receipt.json"


class JevHumanCalibrationError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise JevHumanCalibrationError("FINAL_342_JEV_HUMAN_CALIBRATION_ARGUMENT_ERROR", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CaseComparison(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    batch_index: int = Field(ge=0, le=34)
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(pattern=r"^ep-func-[0-9]{3}$")
    human_criterion_scores: dict[RubricCriterion, int]
    jev_criterion_scores: dict[RubricCriterion, int]
    criterion_probabilities: dict[RubricCriterion, dict[str, float]]
    criterion_confidences: dict[RubricCriterion, float]
    human_failure_labels: tuple[EpisodeFailureLabel, ...]
    jev_failure_probabilities: dict[EpisodeFailureLabel, float]
    human_verdict: ReviewVerdict
    input_tokens: int = Field(ge=1)
    output_tokens: int = Field(ge=1)

    @model_validator(mode="after")
    def validate_case(self) -> CaseComparison:
        required_criteria = set(RubricCriterion)
        if set(self.human_criterion_scores) != required_criteria:
            raise ValueError("human criterion inventory drifted")
        if set(self.jev_criterion_scores) != required_criteria:
            raise ValueError("Jev criterion inventory drifted")
        if set(self.criterion_probabilities) != required_criteria:
            raise ValueError("Jev probability inventory drifted")
        if set(self.criterion_confidences) != required_criteria:
            raise ValueError("Jev confidence inventory drifted")
        if set(self.jev_failure_probabilities) != set(EpisodeFailureLabel):
            raise ValueError("Jev failure-probability inventory drifted")
        if len(self.human_failure_labels) != len(set(self.human_failure_labels)):
            raise ValueError("human failure labels must be unique")
        for probabilities in self.criterion_probabilities.values():
            if set(probabilities) != set(jev_contract.CRITERION_SCORE_KEYS):
                raise ValueError("criterion probability keys must be 1,2,3,4")
        return self


class CalibrationBin(FrozenModel):
    bin_index: int = Field(ge=0, le=9)
    lower_bound: float = Field(ge=0.0, le=1.0)
    upper_bound: float = Field(ge=0.0, le=1.0)
    count: int = Field(ge=0)
    mean_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    empirical_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    absolute_gap: float | None = Field(default=None, ge=0.0, le=1.0)


class CriterionMetric(FrozenModel):
    criterion: RubricCriterion
    count: Literal[35] = 35
    exact_accuracy: float = Field(ge=0.0, le=1.0)
    mean_absolute_error: float = Field(ge=0.0, le=3.0)
    within_one_accuracy: float = Field(ge=0.0, le=1.0)
    multiclass_brier: float = Field(ge=0.0, le=2.0)
    mean_choice_confidence: float = Field(ge=0.0, le=1.0)


class FailureLabelMetric(FrozenModel):
    label: EpisodeFailureLabel
    count: Literal[35] = 35
    positive_support: int = Field(ge=0, le=35)
    prevalence: float = Field(ge=0.0, le=1.0)
    mean_probability: float = Field(ge=0.0, le=1.0)
    brier_score: float = Field(ge=0.0, le=1.0)


class PerLabelThresholdMetric(FrozenModel):
    label: EpisodeFailureLabel
    true_positive: int = Field(ge=0)
    false_positive: int = Field(ge=0)
    false_negative: int = Field(ge=0)
    true_negative: int = Field(ge=0)
    precision: float | None = Field(default=None, ge=0.0, le=1.0)
    recall: float | None = Field(default=None, ge=0.0, le=1.0)
    f1: float | None = Field(default=None, ge=0.0, le=1.0)


class ThresholdMetric(FrozenModel):
    threshold: float = Field(gt=0.0, lt=1.0)
    predicted_positive_count: int = Field(ge=0)
    exact_label_set_accuracy: float = Field(ge=0.0, le=1.0)
    micro_precision: float | None = Field(default=None, ge=0.0, le=1.0)
    micro_recall: float | None = Field(default=None, ge=0.0, le=1.0)
    micro_f1: float | None = Field(default=None, ge=0.0, le=1.0)
    derived_verdict_accuracy: float = Field(ge=0.0, le=1.0)
    per_label: tuple[PerLabelThresholdMetric, ...] = Field(min_length=22, max_length=22)


class CalibrationReport(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_VS_HUMAN_CALIBRATION_COMPLETE"] = (
        "FINAL_342_JEV_VS_HUMAN_CALIBRATION_COMPLETE"
    )
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    case_count: Literal[35] = 35
    criterion_observation_count: Literal[245] = 245
    failure_probability_observation_count: Literal[770] = 770
    request_inventory_sha256: Literal[
        "d009646abff567e35c94da8a61edf57f2cf8ac948bfe915e7941861abd359627"
    ] = EXPECTED_JEV_REQUEST_INVENTORY_SHA256
    case_comparison_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_exact_accuracy: float = Field(ge=0.0, le=1.0)
    criterion_mean_absolute_error: float = Field(ge=0.0, le=3.0)
    criterion_within_one_accuracy: float = Field(ge=0.0, le=1.0)
    criterion_multiclass_brier: float = Field(ge=0.0, le=2.0)
    criterion_confidence_ece: float = Field(ge=0.0, le=1.0)
    failure_probability_brier: float = Field(ge=0.0, le=1.0)
    failure_probability_ece: float = Field(ge=0.0, le=1.0)
    criterion_metrics: tuple[CriterionMetric, ...] = Field(min_length=7, max_length=7)
    failure_label_metrics: tuple[FailureLabelMetric, ...] = Field(min_length=22, max_length=22)
    criterion_confidence_bins: tuple[CalibrationBin, ...] = Field(min_length=10, max_length=10)
    failure_probability_bins: tuple[CalibrationBin, ...] = Field(min_length=10, max_length=10)
    threshold_grid: tuple[float, ...] = THRESHOLD_GRID
    threshold_sweep: tuple[ThresholdMetric, ...] = Field(min_length=19, max_length=19)
    deployment_threshold_selected: Literal[False] = False
    threshold_sweep_is_exploratory: Literal[True] = True
    independently_validated_threshold_available: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    human_adjudication_complete_before_reveal: Literal[True] = True
    effect_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_report(self) -> CalibrationReport:
        if tuple(item.criterion for item in self.criterion_metrics) != tuple(RubricCriterion):
            raise ValueError("criterion metric ordering drifted")
        if tuple(item.label for item in self.failure_label_metrics) != tuple(EpisodeFailureLabel):
            raise ValueError("failure-label metric ordering drifted")
        if tuple(item.threshold for item in self.threshold_sweep) != THRESHOLD_GRID:
            raise ValueError("threshold sweep grid drifted")
        return self


class CalibrationReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_VS_HUMAN_CALIBRATION_PASS"] = (
        "FINAL_342_JEV_VS_HUMAN_CALIBRATION_PASS"
    )
    model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    case_count: Literal[35] = 35
    request_inventory_sha256: Literal[
        "d009646abff567e35c94da8a61edf57f2cf8ac948bfe915e7941861abd359627"
    ] = EXPECTED_JEV_REQUEST_INVENTORY_SHA256
    case_comparison_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    criterion_exact_accuracy: float = Field(ge=0.0, le=1.0)
    criterion_mean_absolute_error: float = Field(ge=0.0, le=3.0)
    criterion_within_one_accuracy: float = Field(ge=0.0, le=1.0)
    criterion_multiclass_brier: float = Field(ge=0.0, le=2.0)
    criterion_confidence_ece: float = Field(ge=0.0, le=1.0)
    failure_probability_brier: float = Field(ge=0.0, le=1.0)
    failure_probability_ece: float = Field(ge=0.0, le=1.0)
    deployment_threshold_selected: Literal[False] = False
    independently_validated_threshold_available: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    human_adjudication_complete_before_reveal: Literal[True] = True
    effect_claims_permitted: Literal[False] = False
    next_gate: Literal["J7B_INTERPRET_CALIBRATION_AND_PLAN_VALIDATION"] = (
        "J7B_INTERPRET_CALIBRATION_AND_PLAN_VALIDATION"
    )


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _provider_canonical_bytes(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_FILE_MISSING",
            f"required calibration input is missing or unsafe: {path.as_posix()}",
        )
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_JSON_INVALID",
            f"calibration input is not valid JSON: {path.as_posix()}",
        ) from error
    if not isinstance(value, dict):
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_JSON_SHAPE_INVALID",
            f"calibration JSON root must be an object: {path.as_posix()}",
        )
    return value


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise JevHumanCalibrationError(
                "FINAL_342_JEV_HUMAN_CALIBRATION_OUTPUT_PATH_UNSAFE",
                f"calibration output path is unsafe: {path.as_posix()}",
            )
        if path.read_bytes() != payload:
            raise JevHumanCalibrationError(
                "FINAL_342_JEV_HUMAN_CALIBRATION_APPEND_ONLY_CONFLICT",
                f"existing calibration evidence differs: {path.as_posix()}",
            )
        return
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_TEMP_RESIDUE",
            f"temporary calibration output already exists: {temporary.as_posix()}",
        )
    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.rename(temporary, path)
    except OSError:
        if temporary.exists():
            temporary.unlink()
        if path.is_file() and not path.is_symlink() and path.read_bytes() == payload:
            return
        raise


def _safe_div(numerator: int | float, denominator: int | float) -> float | None:
    return None if denominator == 0 else float(numerator) / float(denominator)


def _f1(precision: float | None, recall: float | None) -> float | None:
    if precision is None or recall is None:
        return None
    return 0.0 if precision + recall == 0.0 else 2.0 * precision * recall / (precision + recall)


def _binary_counts(truth: list[bool], predicted: list[bool]) -> tuple[int, int, int, int]:
    if len(truth) != len(predicted):
        raise ValueError("binary metric inputs must have equal length")
    tp = sum(t and p for t, p in zip(truth, predicted, strict=True))
    fp = sum((not t) and p for t, p in zip(truth, predicted, strict=True))
    fn = sum(t and (not p) for t, p in zip(truth, predicted, strict=True))
    tn = sum((not t) and (not p) for t, p in zip(truth, predicted, strict=True))
    return tp, fp, fn, tn


def _calibration_bins(
    probabilities: list[float], outcomes: list[bool]
) -> tuple[tuple[CalibrationBin, ...], float]:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("calibration inputs must be non-empty and equal length")
    ps: list[list[float]] = [[] for _ in range(10)]
    ys: list[list[bool]] = [[] for _ in range(10)]
    for probability, outcome in zip(probabilities, outcomes, strict=True):
        if probability < 0.0 or probability > 1.0:
            raise ValueError("calibration probability outside [0,1]")
        index = min(int(probability * 10.0), 9)
        ps[index].append(probability)
        ys[index].append(outcome)
    bins: list[CalibrationBin] = []
    ece = 0.0
    total = len(probabilities)
    for index in range(10):
        count = len(ps[index])
        if count == 0:
            mean_probability: float | None = None
            empirical_rate: float | None = None
            gap: float | None = None
        else:
            observed_mean_probability = sum(ps[index]) / count
            observed_empirical_rate = sum(ys[index]) / count
            observed_gap = abs(observed_mean_probability - observed_empirical_rate)
            mean_probability = observed_mean_probability
            empirical_rate = observed_empirical_rate
            gap = observed_gap
            ece += (count / total) * observed_gap
        bins.append(
            CalibrationBin(
                bin_index=index,
                lower_bound=index / 10.0,
                upper_bound=(index + 1) / 10.0,
                count=count,
                mean_probability=mean_probability,
                empirical_rate=empirical_rate,
                absolute_gap=gap,
            )
        )
    return tuple(bins), ece


def _multiclass_brier(probabilities: dict[str, float], truth_score: int) -> float:
    if set(probabilities) != set(jev_contract.CRITERION_SCORE_KEYS):
        raise ValueError("multiclass probability inventory must be 1,2,3,4")
    if truth_score not in (1, 2, 3, 4):
        raise ValueError("truth score must be in [1,4]")
    return sum(
        (float(probabilities[key]) - (1.0 if int(key) == truth_score else 0.0)) ** 2
        for key in jev_contract.CRITERION_SCORE_KEYS
    )


def _human_score_map(adjudication: AdjudicationRecord) -> dict[RubricCriterion, int]:
    return {item.criterion: item.score for item in adjudication.final_criterion_scores}


def _verdict(
    scores: dict[RubricCriterion, int], label_count: int, rubric: BlindedQualityRubric
) -> ReviewVerdict:
    typed_scores = tuple(
        CriterionScore(
            criterion=criterion,
            score=scores[criterion],
            evidence_note_sha256="0" * 64,
        )
        for criterion in RubricCriterion
    )
    return blinded_eval.expected_verdict(typed_scores, label_count, rubric)


def _load_rubric(root: Path) -> BlindedQualityRubric:
    try:
        return BlindedQualityRubric.model_validate(_read_json_object(root / bridge.RUBRIC_PATH))
    except ValidationError as error:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_RUBRIC_INVALID",
            "frozen rubric failed typed validation",
        ) from error


def _load_manifest(root: Path) -> batch_freeze.FrozenBatchManifest:
    try:
        manifest = batch_freeze.FrozenBatchManifest.model_validate(
            _read_json_object(root / batch_freeze.BATCH_MANIFEST_PATH)
        )
    except ValidationError as error:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_MANIFEST_INVALID",
            "frozen Jev batch manifest failed typed validation",
        ) from error
    if manifest.request_inventory_sha256 != EXPECTED_JEV_REQUEST_INVENTORY_SHA256:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_INVENTORY_DRIFT",
            "Jev request inventory differs from accepted J5 evidence",
        )
    if len(manifest.entries) != 35:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_CASE_COUNT_DRIFT",
            "Jev batch must contain exactly 35 cases",
        )
    return manifest


def _load_request_response(
    root: Path, entry: batch_freeze.FrozenBatchEntry
) -> tuple[jev_contract.JevShadowRequest, jev_contract.JevShadowResponse, int, int]:
    if entry.batch_index == 0:
        request_path = root / canary.CANARY_REQUEST_PATH
        response_path = root / canary_runner.CANARY_RESPONSE_PATH
        try:
            request = jev_contract.JevShadowRequest.model_validate(_read_json_object(request_path))
            response = jev_contract.JevShadowResponse.model_validate(
                _read_json_object(response_path)
            )
            receipt = canary_runner.LiveCanaryReceipt.model_validate(
                _read_json_object(root / canary_runner.CANARY_RECEIPT_PATH)
            )
        except ValidationError as error:
            raise JevHumanCalibrationError(
                "FINAL_342_JEV_HUMAN_CALIBRATION_CANARY_INVALID",
                "J4 Jev canary evidence failed typed validation",
            ) from error
        if _sha256_bytes(request_path.read_bytes()) != entry.request_sha256:
            raise JevHumanCalibrationError(
                "FINAL_342_JEV_HUMAN_CALIBRATION_CANARY_REQUEST_DRIFT",
                "J4 canary request digest drifted",
            )
        response_bytes = _provider_canonical_bytes(response.model_dump(mode="json"))
        if _sha256_bytes(response_bytes) != receipt.response_sha256:
            raise JevHumanCalibrationError(
                "FINAL_342_JEV_HUMAN_CALIBRATION_CANARY_RESPONSE_DRIFT",
                "J4 canary response digest drifted",
            )
        if receipt.review_item_id != entry.review_item_id or receipt.episode_id != entry.episode_id:
            raise JevHumanCalibrationError(
                "FINAL_342_JEV_HUMAN_CALIBRATION_CANARY_IDENTITY_DRIFT",
                "J4 canary identity drifted",
            )
        jev_contract.validate_response_against_request(request, response)
        return request, response, receipt.input_tokens, receipt.output_tokens

    request_path = root / entry.request_relative_path
    execution_path = (
        root / batch_runner.EXECUTION_ROOT / f"{entry.batch_index:02d}-{entry.review_item_id}.json"
    )
    try:
        request = jev_contract.JevShadowRequest.model_validate(_read_json_object(request_path))
        execution = batch_runner.BatchCaseExecutionRecord.model_validate(
            _read_json_object(execution_path)
        )
    except ValidationError as error:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_BATCH_CASE_INVALID",
            f"J5 Jev case failed typed validation at index {entry.batch_index}",
        ) from error
    if _sha256_bytes(request_path.read_bytes()) != entry.request_sha256:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_REQUEST_DRIFT",
            f"J5 request digest drifted at index {entry.batch_index}",
        )
    if (
        execution.batch_index != entry.batch_index
        or execution.review_item_id != entry.review_item_id
        or execution.episode_id != entry.episode_id
        or execution.request_sha256 != entry.request_sha256
    ):
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_EXECUTION_IDENTITY_DRIFT",
            f"J5 execution identity drifted at index {entry.batch_index}",
        )
    jev_contract.validate_response_against_request(request, execution.response)
    response_bytes = _provider_canonical_bytes(execution.response.model_dump(mode="json"))
    if _sha256_bytes(response_bytes) != execution.response_sha256:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_RESPONSE_DRIFT",
            f"J5 response digest drifted at index {entry.batch_index}",
        )
    return request, execution.response, execution.input_tokens, execution.output_tokens


def _load_adjudication(
    root: Path, entry: batch_freeze.FrozenBatchEntry, rubric: BlindedQualityRubric
) -> AdjudicationRecord:
    path = root / bridge.REVIEW_RESULT_ROOT / "adjudications" / f"{entry.review_item_id}.json"
    try:
        adjudication = AdjudicationRecord.model_validate(_read_json_object(path))
    except ValidationError as error:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_ADJUDICATION_INVALID",
            f"human adjudication failed typed validation at index {entry.batch_index}",
        ) from error
    if adjudication.episode_id != entry.episode_id:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_ADJUDICATION_IDENTITY_DRIFT",
            f"human adjudication episode drifted at index {entry.batch_index}",
        )
    expected = blinded_eval.expected_verdict(
        adjudication.final_criterion_scores,
        len(adjudication.final_failure_labels),
        rubric,
    )
    if adjudication.final_verdict is not expected:
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_HUMAN_VERDICT_INVALID",
            f"human adjudication verdict drifted at index {entry.batch_index}",
        )
    return adjudication


def _build_cases(
    root: Path, manifest: batch_freeze.FrozenBatchManifest, rubric: BlindedQualityRubric
) -> tuple[CaseComparison, ...]:
    cases: list[CaseComparison] = []
    for entry in manifest.entries:
        request, response, input_tokens, output_tokens = _load_request_response(root, entry)
        adjudication = _load_adjudication(root, entry, rubric)
        projection = jev_contract.project_response(request, response)
        probabilities: dict[RubricCriterion, dict[str, float]] = {}
        confidences: dict[RubricCriterion, float] = {}
        for criterion in RubricCriterion:
            answer = response.answers[jev_contract.criterion_question_name(criterion)]
            if not isinstance(answer, jev_contract.JevChoiceAnswer):
                raise JevHumanCalibrationError(
                    "FINAL_342_JEV_HUMAN_CALIBRATION_CHOICE_INVALID",
                    f"criterion answer type drifted at index {entry.batch_index}",
                )
            probabilities[criterion] = {
                key: float(value) for key, value in answer.probabilities.items()
            }
            confidences[criterion] = float(answer.confidence)
        cases.append(
            CaseComparison(
                batch_index=entry.batch_index,
                review_item_id=entry.review_item_id,
                episode_id=entry.episode_id,
                human_criterion_scores=_human_score_map(adjudication),
                jev_criterion_scores=projection.criterion_scores,
                criterion_probabilities=probabilities,
                criterion_confidences=confidences,
                human_failure_labels=adjudication.final_failure_labels,
                jev_failure_probabilities=projection.failure_probabilities,
                human_verdict=adjudication.final_verdict,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )
        )
    result = tuple(cases)
    if len(result) != 35 or tuple(case.batch_index for case in result) != tuple(range(35)):
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_ORDER_DRIFT",
            "calibration cases must be exactly 35 in frozen order",
        )
    return result


def _criterion_metrics(
    cases: tuple[CaseComparison, ...],
) -> tuple[
    tuple[CriterionMetric, ...], float, float, float, float, tuple[CalibrationBin, ...], float
]:
    metrics: list[CriterionMetric] = []
    all_errors: list[int] = []
    all_exact: list[bool] = []
    all_within: list[bool] = []
    all_brier: list[float] = []
    all_confidences: list[float] = []
    for criterion in RubricCriterion:
        errors: list[int] = []
        exact: list[bool] = []
        within: list[bool] = []
        briers: list[float] = []
        confidences: list[float] = []
        for case in cases:
            truth = case.human_criterion_scores[criterion]
            predicted = case.jev_criterion_scores[criterion]
            error = abs(predicted - truth)
            errors.append(error)
            exact.append(predicted == truth)
            within.append(error <= 1)
            briers.append(_multiclass_brier(case.criterion_probabilities[criterion], truth))
            confidences.append(case.criterion_confidences[criterion])
        metrics.append(
            CriterionMetric(
                criterion=criterion,
                exact_accuracy=sum(exact) / len(exact),
                mean_absolute_error=sum(errors) / len(errors),
                within_one_accuracy=sum(within) / len(within),
                multiclass_brier=sum(briers) / len(briers),
                mean_choice_confidence=sum(confidences) / len(confidences),
            )
        )
        all_errors.extend(errors)
        all_exact.extend(exact)
        all_within.extend(within)
        all_brier.extend(briers)
        all_confidences.extend(confidences)
    bins, ece = _calibration_bins(all_confidences, all_exact)
    return (
        tuple(metrics),
        sum(all_exact) / len(all_exact),
        sum(all_errors) / len(all_errors),
        sum(all_within) / len(all_within),
        sum(all_brier) / len(all_brier),
        bins,
        ece,
    )


def _failure_metrics(
    cases: tuple[CaseComparison, ...],
) -> tuple[tuple[FailureLabelMetric, ...], float, tuple[CalibrationBin, ...], float]:
    metrics: list[FailureLabelMetric] = []
    all_probabilities: list[float] = []
    all_truth: list[bool] = []
    for label in EpisodeFailureLabel:
        probabilities = [case.jev_failure_probabilities[label] for case in cases]
        truth = [label in set(case.human_failure_labels) for case in cases]
        support = sum(truth)
        briers = [
            (probability - (1.0 if outcome else 0.0)) ** 2
            for probability, outcome in zip(probabilities, truth, strict=True)
        ]
        metrics.append(
            FailureLabelMetric(
                label=label,
                positive_support=support,
                prevalence=support / len(cases),
                mean_probability=sum(probabilities) / len(probabilities),
                brier_score=sum(briers) / len(briers),
            )
        )
        all_probabilities.extend(probabilities)
        all_truth.extend(truth)
    overall_brier = sum(
        (probability - (1.0 if outcome else 0.0)) ** 2
        for probability, outcome in zip(all_probabilities, all_truth, strict=True)
    ) / len(all_probabilities)
    bins, ece = _calibration_bins(all_probabilities, all_truth)
    return tuple(metrics), overall_brier, bins, ece


def _threshold_metrics(
    cases: tuple[CaseComparison, ...], rubric: BlindedQualityRubric
) -> tuple[ThresholdMetric, ...]:
    results: list[ThresholdMetric] = []
    for threshold in THRESHOLD_GRID:
        per_label: list[PerLabelThresholdMetric] = []
        total_tp = total_fp = total_fn = 0
        for label in EpisodeFailureLabel:
            truth = [label in set(case.human_failure_labels) for case in cases]
            predicted = [case.jev_failure_probabilities[label] >= threshold for case in cases]
            tp, fp, fn, tn = _binary_counts(truth, predicted)
            precision = _safe_div(tp, tp + fp)
            recall = _safe_div(tp, tp + fn)
            total_tp += tp
            total_fp += fp
            total_fn += fn
            per_label.append(
                PerLabelThresholdMetric(
                    label=label,
                    true_positive=tp,
                    false_positive=fp,
                    false_negative=fn,
                    true_negative=tn,
                    precision=precision,
                    recall=recall,
                    f1=_f1(precision, recall),
                )
            )
        exact_sets = 0
        verdict_matches = 0
        predicted_positive_count = 0
        for case in cases:
            predicted_labels = tuple(
                label
                for label in EpisodeFailureLabel
                if case.jev_failure_probabilities[label] >= threshold
            )
            predicted_positive_count += len(predicted_labels)
            if set(predicted_labels) == set(case.human_failure_labels):
                exact_sets += 1
            if (
                _verdict(case.jev_criterion_scores, len(predicted_labels), rubric)
                is case.human_verdict
            ):
                verdict_matches += 1
        micro_precision = _safe_div(total_tp, total_tp + total_fp)
        micro_recall = _safe_div(total_tp, total_tp + total_fn)
        results.append(
            ThresholdMetric(
                threshold=threshold,
                predicted_positive_count=predicted_positive_count,
                exact_label_set_accuracy=exact_sets / len(cases),
                micro_precision=micro_precision,
                micro_recall=micro_recall,
                micro_f1=_f1(micro_precision, micro_recall),
                derived_verdict_accuracy=verdict_matches / len(cases),
                per_label=tuple(per_label),
            )
        )
    return tuple(results)


def build_report(
    cases: tuple[CaseComparison, ...], rubric: BlindedQualityRubric, *, case_comparison_sha256: str
) -> CalibrationReport:
    criterion_metrics, exact, mae, within, criterion_brier, criterion_bins, criterion_ece = (
        _criterion_metrics(cases)
    )
    failure_metrics, failure_brier, failure_bins, failure_ece = _failure_metrics(cases)
    return CalibrationReport(
        case_comparison_sha256=case_comparison_sha256,
        criterion_exact_accuracy=exact,
        criterion_mean_absolute_error=mae,
        criterion_within_one_accuracy=within,
        criterion_multiclass_brier=criterion_brier,
        criterion_confidence_ece=criterion_ece,
        failure_probability_brier=failure_brier,
        failure_probability_ece=failure_ece,
        criterion_metrics=criterion_metrics,
        failure_label_metrics=failure_metrics,
        criterion_confidence_bins=criterion_bins,
        failure_probability_bins=failure_bins,
        threshold_sweep=_threshold_metrics(cases, rubric),
    )


def run_calibration(repo_root: Path) -> CalibrationReceipt:
    root = repo_root.resolve()
    completion = bridge.validate_review_completion(root)
    if (
        completion.status != "COMPLETE"
        or completion.valid_adjudication_count != 35
        or completion.missing_required_adjudication_count != 0
        or completion.unresolved_material_disagreement_count != 0
        or not completion.overall_review_evidence_complete
    ):
        raise JevHumanCalibrationError(
            "FINAL_342_JEV_HUMAN_CALIBRATION_HUMAN_TRUTH_INCOMPLETE",
            "J6 authoritative human adjudication must be complete before Jev reveal",
        )
    rubric = _load_rubric(root)
    manifest = _load_manifest(root)
    cases = _build_cases(root, manifest, rubric)
    cases_bytes = _canonical_json_bytes(
        {
            "schema_version": "1.0.0",
            "status": "FINAL_342_JEV_HUMAN_CASE_COMPARISONS_COMPLETE",
            "case_count": 35,
            "cases": [case.model_dump(mode="json") for case in cases],
        }
    )
    cases_sha256 = _sha256_bytes(cases_bytes)
    report = build_report(cases, rubric, case_comparison_sha256=cases_sha256)
    report_bytes = _canonical_json_bytes(report.model_dump(mode="json"))
    report_sha256 = _sha256_bytes(report_bytes)
    receipt = CalibrationReceipt(
        case_comparison_sha256=cases_sha256,
        report_sha256=report_sha256,
        criterion_exact_accuracy=report.criterion_exact_accuracy,
        criterion_mean_absolute_error=report.criterion_mean_absolute_error,
        criterion_within_one_accuracy=report.criterion_within_one_accuracy,
        criterion_multiclass_brier=report.criterion_multiclass_brier,
        criterion_confidence_ece=report.criterion_confidence_ece,
        failure_probability_brier=report.failure_probability_brier,
        failure_probability_ece=report.failure_probability_ece,
    )
    _write_once(root / CASE_COMPARISON_PATH, cases_bytes)
    _write_once(root / REPORT_PATH, report_bytes)
    _write_once(root / RECEIPT_PATH, _canonical_json_bytes(receipt.model_dump(mode="json")))
    return receipt


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="final_342_jev_human_calibration_v1")
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run_calibration(args.repo_root)
    except (
        JevHumanCalibrationError,
        jev_contract.JevContractError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        if isinstance(
            error,
            (
                JevHumanCalibrationError,
                jev_contract.JevContractError,
            ),
        ):
            code, message = error.error_code, error.safe_message
        elif isinstance(error, ValidationError):
            code, message = (
                "FINAL_342_JEV_HUMAN_CALIBRATION_TYPED_VALIDATION_FAILED",
                "Jev-human calibration typed validation failed",
            )
        elif isinstance(error, ValueError):
            code, message = "FINAL_342_JEV_HUMAN_CALIBRATION_METRIC_INPUT_INVALID", str(error)
        else:
            code, message = (
                "FINAL_342_JEV_HUMAN_CALIBRATION_IO_FAILED",
                "Jev-human calibration local I/O failed",
            )
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
    print(result.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

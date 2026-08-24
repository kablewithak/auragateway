"""Schedule and neutral-worker contracts for measured A/B/C variance-pilot successor V2."""

from __future__ import annotations

import hashlib
import json
import statistics
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import Field, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract, WorkerId

V1_PILOT_SCHEDULE_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v1/pilot_schedule.json"
)
V1_PILOT_SCHEDULE_SHA256: Final = (
    "da8964631aa690e55e14b8b0e3cd484dc0f9d7fb90090bfad32241b117aa06b7"
)

EXPECTED_CASE_COUNT: Final = 6
EXPECTED_PAIR_COUNT: Final = 18
EXPECTED_TRAJECTORY_COUNT: Final = 54
EXPECTED_PILOT_TURN_COUNT: Final = 216
TURNS_PER_TRAJECTORY: Final = 4

SCHEMA_CANARY_REQUEST_COUNT: Final = 2
WARMUP_REQUEST_COUNT: Final = 2
NEUTRAL_MEASURED_REQUEST_COUNT: Final = 20
PRETREATMENT_REQUEST_COUNT: Final = 24
MAXIMUM_TOTAL_MODEL_REQUESTS: Final = 240

MAX_OUTPUT_TOKENS: Final = 256
MAXIMUM_WORKER_MEDIAN_TTFT_RATIO: Final = 1.25
MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO: Final = 1.25


class VariancePilotV2ContractError(RuntimeError):
    """Metadata-safe deterministic V2 contract failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class WorkerOrientation(StrEnum):
    """Counterbalanced worker orientation from the controlled local A/B/C design."""

    ORIENTATION_1 = "orientation_1"
    ORIENTATION_2 = "orientation_2"


class PreTreatmentPhase(StrEnum):
    """Pre-treatment phases that are excluded from A/B/C treatment evidence."""

    SCHEMA_CANARY = "schema_canary"
    WARMUP = "warmup"
    NEUTRAL_WORKER_QUALIFICATION = "neutral_worker_qualification"


class PilotCaseV2(LocalABCContract):
    """One V1 pilot case carried into V2 without case reselection."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    episode_id: str


class PilotTrajectoryV2(LocalABCContract):
    """One scheduled V2 condition trajectory."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    schedule_index: int = Field(ge=0, lt=EXPECTED_TRAJECTORY_COUNT)
    comparison_pair_index: int = Field(ge=0, lt=EXPECTED_PAIR_COUNT)
    comparison_pair_id: str
    run_id: str
    episode_id: str
    pilot_replication_id: Literal["pilot-v2-r01", "pilot-v2-r02", "pilot-v2-r03"]
    replication_index: int = Field(ge=1, le=3)
    case_order_position: int = Field(ge=1, le=6)
    condition_id: ConditionId
    condition_order_index: int = Field(ge=0, le=2)
    worker_orientation: WorkerOrientation
    realized_route: tuple[WorkerId, WorkerId, WorkerId, WorkerId]
    starting_state_id: str
    cache_namespace_id: str
    turn_count: Literal[4] = TURNS_PER_TRAJECTORY
    maximum_request_attempt_count: Literal[4] = 4


class PilotScheduleV2(LocalABCContract):
    """Exact V2 schedule with condition, case-order and worker counterbalancing."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    schedule_id: Literal["auragateway-measured-abc-variance-pilot-successor-v2"] = (
        "auragateway-measured-abc-variance-pilot-successor-v2"
    )
    source_v1_schedule_sha256: Literal[
        "da8964631aa690e55e14b8b0e3cd484dc0f9d7fb90090bfad32241b117aa06b7"
    ] = V1_PILOT_SCHEDULE_SHA256
    cases: tuple[PilotCaseV2, ...] = Field(min_length=6, max_length=6)
    trajectories: tuple[PilotTrajectoryV2, ...] = Field(min_length=54, max_length=54)
    case_count: Literal[6] = 6
    comparison_pair_count: Literal[18] = 18
    trajectory_count: Literal[54] = 54
    pilot_turn_count: Literal[216] = 216
    hidden_retries_permitted: Literal[False] = False
    replacement_cases_permitted: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        if tuple(item.schedule_index for item in self.trajectories) != tuple(
            range(EXPECTED_TRAJECTORY_COUNT)
        ):
            raise ValueError("V2 schedule indexes must be contiguous")
        if sorted({item.comparison_pair_index for item in self.trajectories}) != list(
            range(EXPECTED_PAIR_COUNT)
        ):
            raise ValueError("V2 comparison-pair indexes must be contiguous")

        case_ids = tuple(item.episode_id for item in self.cases)
        if case_ids != tuple(sorted(case_ids)) or len(case_ids) != len(set(case_ids)):
            raise ValueError("V2 pilot cases must be unique and sorted")
        if len({item.run_id for item in self.trajectories}) != EXPECTED_TRAJECTORY_COUNT:
            raise ValueError("V2 run IDs must be unique")
        if (
            len({item.cache_namespace_id for item in self.trajectories})
            != EXPECTED_TRAJECTORY_COUNT
        ):
            raise ValueError("V2 pilot cache namespaces must be unique")

        rows_by_pair: dict[int, list[PilotTrajectoryV2]] = {}
        for row in self.trajectories:
            rows_by_pair.setdefault(row.comparison_pair_index, []).append(row)

        expected_orders = {
            1: (ConditionId.A, ConditionId.B, ConditionId.C),
            2: (ConditionId.B, ConditionId.C, ConditionId.A),
            3: (ConditionId.C, ConditionId.A, ConditionId.B),
        }
        pair_representatives: list[PilotTrajectoryV2] = []
        for rows in rows_by_pair.values():
            if len(rows) != 3:
                raise ValueError("each V2 comparison pair must contain three conditions")
            rows = sorted(rows, key=lambda item: item.condition_order_index)
            first = rows[0]
            if tuple(item.condition_id for item in rows) != expected_orders[
                first.replication_index
            ]:
                raise ValueError("V2 condition order drifted")
            if len({item.episode_id for item in rows}) != 1:
                raise ValueError("V2 comparison pair episode identity drifted")
            if len({item.worker_orientation for item in rows}) != 1:
                raise ValueError("V2 comparison pair orientation drifted")
            if len({item.starting_state_id for item in rows}) != 1:
                raise ValueError("V2 comparison pair starting state drifted")
            for item in rows:
                if item.realized_route != route_for(item.condition_id, item.worker_orientation):
                    raise ValueError("V2 realized route violates worker orientation")
            pair_representatives.append(first)

        if {
            orientation: sum(
                row.worker_orientation is orientation for row in pair_representatives
            )
            for orientation in WorkerOrientation
        } != {
            WorkerOrientation.ORIENTATION_1: 9,
            WorkerOrientation.ORIENTATION_2: 9,
        }:
            raise ValueError("V2 global worker orientation must be balanced 9/9")

        for replication_index in (1, 2, 3):
            rows = [
                row
                for row in pair_representatives
                if row.replication_index == replication_index
            ]
            if len(rows) != EXPECTED_CASE_COUNT:
                raise ValueError("each V2 replication must contain six comparison pairs")
            counts = {
                orientation: sum(row.worker_orientation is orientation for row in rows)
                for orientation in WorkerOrientation
            }
            if counts != {
                WorkerOrientation.ORIENTATION_1: 3,
                WorkerOrientation.ORIENTATION_2: 3,
            }:
                raise ValueError("each V2 replication must balance orientation 3/3")

        for case_id in case_ids:
            rows = [row for row in pair_representatives if row.episode_id == case_id]
            if len(rows) != 3:
                raise ValueError("each V2 case must appear once in each replication")
            if {row.worker_orientation for row in rows} != set(WorkerOrientation):
                raise ValueError("each V2 case must observe both worker orientations")
            if {(row.case_order_position - 1) // 2 for row in rows} != {0, 1, 2}:
                raise ValueError("each V2 case must occupy early, middle and late order bands")
        return self


class PreTreatmentRequest(LocalABCContract):
    """One symmetric request before A/B/C treatment begins."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    sequence_index: int = Field(ge=0, lt=PRETREATMENT_REQUEST_COUNT)
    request_id: str
    phase: PreTreatmentPhase
    worker_id: WorkerId
    measurement_pair_index: int | None = Field(default=None, ge=1, le=10)
    pair_order_index: int | None = Field(default=None, ge=0, le=1)
    measured_for_worker_symmetry: bool
    cache_namespace_id: str
    common_request_contract_id: Literal["neutral-worker-qualification-request-v1"] = (
        "neutral-worker-qualification-request-v1"
    )
    max_output_tokens: Literal[256] = MAX_OUTPUT_TOKENS


class NeutralWorkerQualificationPlan(LocalABCContract):
    """Exact symmetric pre-treatment plan outside A/B/C treatment."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    plan_id: Literal["auragateway-neutral-worker-qualification-v2"] = (
        "auragateway-neutral-worker-qualification-v2"
    )
    requests: tuple[PreTreatmentRequest, ...] = Field(min_length=24, max_length=24)
    schema_canary_request_count: Literal[2] = SCHEMA_CANARY_REQUEST_COUNT
    warmup_request_count: Literal[2] = WARMUP_REQUEST_COUNT
    measured_request_count: Literal[20] = NEUTRAL_MEASURED_REQUEST_COUNT
    pre_treatment_request_count: Literal[24] = PRETREATMENT_REQUEST_COUNT
    maximum_worker_median_ttft_ratio: float = MAXIMUM_WORKER_MEDIAN_TTFT_RATIO
    maximum_worker_median_prefill_ratio: float = MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO
    hidden_retries_permitted: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if tuple(item.sequence_index for item in self.requests) != tuple(
            range(PRETREATMENT_REQUEST_COUNT)
        ):
            raise ValueError("pre-treatment sequence indexes must be contiguous")
        if len({item.request_id for item in self.requests}) != PRETREATMENT_REQUEST_COUNT:
            raise ValueError("pre-treatment request IDs must be unique")
        if len({item.cache_namespace_id for item in self.requests}) != PRETREATMENT_REQUEST_COUNT:
            raise ValueError("pre-treatment namespaces must be unique")
        if self.maximum_worker_median_ttft_ratio != MAXIMUM_WORKER_MEDIAN_TTFT_RATIO:
            raise ValueError("neutral TTFT threshold drifted")
        if self.maximum_worker_median_prefill_ratio != MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO:
            raise ValueError("neutral prefill threshold drifted")

        canary = [item for item in self.requests if item.phase is PreTreatmentPhase.SCHEMA_CANARY]
        warmup = [item for item in self.requests if item.phase is PreTreatmentPhase.WARMUP]
        measured = [item for item in self.requests if item.measured_for_worker_symmetry]
        if [item.worker_id for item in canary] != [WorkerId.WORKER_1, WorkerId.WORKER_2]:
            raise ValueError("schema canary must execute worker_1 then worker_2")
        if [item.worker_id for item in warmup] != [WorkerId.WORKER_2, WorkerId.WORKER_1]:
            raise ValueError("warm-up must execute worker_2 then worker_1")
        if any(item.measured_for_worker_symmetry for item in (*canary, *warmup)):
            raise ValueError("canary and warm-up cannot enter worker-symmetry evidence")
        if len(measured) != NEUTRAL_MEASURED_REQUEST_COUNT:
            raise ValueError("neutral qualification requires exactly twenty measurements")

        first_counts = {worker: 0 for worker in WorkerId}
        for pair_index in range(1, 11):
            rows = [item for item in measured if item.measurement_pair_index == pair_index]
            rows = sorted(rows, key=lambda item: cast(int, item.pair_order_index))
            if len(rows) != 2:
                raise ValueError("each neutral pair requires two worker requests")
            first = WorkerId.WORKER_1 if pair_index % 2 == 1 else WorkerId.WORKER_2
            second = WorkerId.WORKER_2 if first is WorkerId.WORKER_1 else WorkerId.WORKER_1
            if [item.worker_id for item in rows] != [first, second]:
                raise ValueError("neutral qualification ordering drifted")
            first_counts[rows[0].worker_id] += 1
        if first_counts != {WorkerId.WORKER_1: 5, WorkerId.WORKER_2: 5}:
            raise ValueError("neutral first-worker support must balance 5/5")
        return self


class NeutralWorkerSample(LocalABCContract):
    """One measured neutral worker observation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    measurement_pair_index: int = Field(ge=1, le=10)
    pair_order_index: int = Field(ge=0, le=1)
    worker_id: WorkerId
    admitted: bool
    telemetry_valid: bool
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    prefill_duration_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_metrics(self) -> Self:
        if self.telemetry_valid and (
            self.time_to_first_token_ms is None or self.prefill_duration_ms is None
        ):
            raise ValueError("valid neutral telemetry requires TTFT and prefill duration")
        return self


class NeutralWorkerQualificationAssessment(LocalABCContract):
    """Gross pre-treatment worker-asymmetry decision."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    decision: Literal["PASS", "FAIL"]
    observed_sample_count: int = Field(ge=0, le=20)
    worker_1_sample_count: int = Field(ge=0, le=10)
    worker_2_sample_count: int = Field(ge=0, le=10)
    worker_median_ttft_ratio: float | None = Field(default=None, ge=1)
    worker_median_prefill_ratio: float | None = Field(default=None, ge=1)
    blocking_reasons: tuple[str, ...] = ()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _read_v1_case_ids(repo_root: Path) -> tuple[str, ...]:
    path = repo_root / V1_PILOT_SCHEDULE_PATH
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise VariancePilotV2ContractError(
            "V2_SOURCE_SCHEDULE_MISSING",
            "accepted V1 pilot schedule is missing",
        ) from exc
    if _sha256_bytes(raw) != V1_PILOT_SCHEDULE_SHA256:
        raise VariancePilotV2ContractError(
            "V2_SOURCE_SCHEDULE_DRIFT",
            "accepted V1 pilot schedule identity drifted",
        )
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VariancePilotV2ContractError(
            "V2_SOURCE_SCHEDULE_INVALID",
            "accepted V1 pilot schedule is invalid JSON",
        ) from exc
    if not isinstance(payload, dict):
        raise VariancePilotV2ContractError(
            "V2_SOURCE_SCHEDULE_INVALID",
            "accepted V1 pilot schedule root is invalid",
        )
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASE_COUNT:
        raise VariancePilotV2ContractError(
            "V2_SOURCE_SCHEDULE_INVALID",
            "accepted V1 pilot schedule must contain exactly six cases",
        )
    case_ids: list[str] = []
    for row in cases:
        if not isinstance(row, dict) or not isinstance(row.get("episode_id"), str):
            raise VariancePilotV2ContractError(
                "V2_SOURCE_SCHEDULE_INVALID",
                "accepted V1 pilot case identity is invalid",
            )
        case_ids.append(cast(str, row["episode_id"]))
    result = tuple(case_ids)
    if result != tuple(sorted(result)) or len(set(result)) != EXPECTED_CASE_COUNT:
        raise VariancePilotV2ContractError(
            "V2_SOURCE_SCHEDULE_INVALID",
            "accepted V1 pilot cases must be unique and sorted",
        )
    return result


def route_for(
    condition_id: ConditionId,
    orientation: WorkerOrientation,
) -> tuple[WorkerId, WorkerId, WorkerId, WorkerId]:
    """Return the exact four-turn route for one condition and orientation."""

    if orientation is WorkerOrientation.ORIENTATION_1:
        if condition_id in {ConditionId.A, ConditionId.B}:
            return (
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
                WorkerId.WORKER_1,
                WorkerId.WORKER_2,
            )
        return (
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
            WorkerId.WORKER_1,
        )
    if condition_id in {ConditionId.A, ConditionId.B}:
        return (
            WorkerId.WORKER_2,
            WorkerId.WORKER_1,
            WorkerId.WORKER_2,
            WorkerId.WORKER_1,
        )
    return (
        WorkerId.WORKER_2,
        WorkerId.WORKER_2,
        WorkerId.WORKER_2,
        WorkerId.WORKER_2,
    )


def build_schedule(repo_root: Path) -> PilotScheduleV2:
    """Build the frozen case/order/orientation schedule."""

    case_ids = _read_v1_case_ids(repo_root)
    cases = tuple(PilotCaseV2(episode_id=item) for item in case_ids)
    condition_orders = (
        (ConditionId.A, ConditionId.B, ConditionId.C),
        (ConditionId.B, ConditionId.C, ConditionId.A),
        (ConditionId.C, ConditionId.A, ConditionId.B),
    )
    orientation_pattern = (
        WorkerOrientation.ORIENTATION_1,
        WorkerOrientation.ORIENTATION_2,
        WorkerOrientation.ORIENTATION_2,
        WorkerOrientation.ORIENTATION_1,
        WorkerOrientation.ORIENTATION_1,
        WorkerOrientation.ORIENTATION_2,
    )
    rotations = (0, 2, 4)

    trajectories: list[PilotTrajectoryV2] = []
    schedule_index = 0
    pair_index = 0
    for replication_index, (condition_order, rotation) in enumerate(
        zip(condition_orders, rotations, strict=True),
        start=1,
    ):
        rotated_cases = case_ids[rotation:] + case_ids[:rotation]
        replication_id = cast(
            Literal["pilot-v2-r01", "pilot-v2-r02", "pilot-v2-r03"],
            f"pilot-v2-r{replication_index:02d}",
        )
        for position, (episode_id, orientation) in enumerate(
            zip(rotated_cases, orientation_pattern, strict=True),
            start=1,
        ):
            pair_id = f"pilot-v2-pair-{episode_id}-{replication_id}"
            starting_state_id = f"pilot-v2-start-{episode_id}-{replication_id}-{orientation.value}"
            for order_index, condition_id in enumerate(condition_order):
                slug = condition_id.value.lower()
                trajectories.append(
                    PilotTrajectoryV2(
                        schedule_index=schedule_index,
                        comparison_pair_index=pair_index,
                        comparison_pair_id=pair_id,
                        run_id=f"pilot-v2-run-{episode_id}-{replication_id}-{slug}",
                        episode_id=episode_id,
                        pilot_replication_id=replication_id,
                        replication_index=replication_index,
                        case_order_position=position,
                        condition_id=condition_id,
                        condition_order_index=order_index,
                        worker_orientation=orientation,
                        realized_route=route_for(condition_id, orientation),
                        starting_state_id=starting_state_id,
                        cache_namespace_id=f"pilot-v2-ns-{episode_id}-{replication_id}-{slug}",
                    )
                )
                schedule_index += 1
            pair_index += 1
    return PilotScheduleV2(cases=cases, trajectories=tuple(trajectories))


def build_neutral_worker_plan() -> NeutralWorkerQualificationPlan:
    """Build the exact symmetric pre-treatment request sequence."""

    requests: list[PreTreatmentRequest] = []

    def add(
        phase: PreTreatmentPhase,
        worker_id: WorkerId,
        measured: bool,
        pair_index: int | None = None,
        pair_order_index: int | None = None,
    ) -> None:
        index = len(requests)
        suffix = (
            f"-p{pair_index:02d}-o{pair_order_index}"
            if pair_index is not None and pair_order_index is not None
            else ""
        )
        requests.append(
            PreTreatmentRequest(
                sequence_index=index,
                request_id=f"pretreatment-v2-{phase.value}-{worker_id.value}{suffix}",
                phase=phase,
                worker_id=worker_id,
                measurement_pair_index=pair_index,
                pair_order_index=pair_order_index,
                measured_for_worker_symmetry=measured,
                cache_namespace_id=f"pretreatment-v2-ns-{phase.value}-{worker_id.value}{suffix}",
            )
        )

    add(PreTreatmentPhase.SCHEMA_CANARY, WorkerId.WORKER_1, False)
    add(PreTreatmentPhase.SCHEMA_CANARY, WorkerId.WORKER_2, False)
    add(PreTreatmentPhase.WARMUP, WorkerId.WORKER_2, False)
    add(PreTreatmentPhase.WARMUP, WorkerId.WORKER_1, False)
    for pair_index in range(1, 11):
        first = WorkerId.WORKER_1 if pair_index % 2 == 1 else WorkerId.WORKER_2
        second = WorkerId.WORKER_2 if first is WorkerId.WORKER_1 else WorkerId.WORKER_1
        add(
            PreTreatmentPhase.NEUTRAL_WORKER_QUALIFICATION,
            first,
            True,
            pair_index,
            0,
        )
        add(
            PreTreatmentPhase.NEUTRAL_WORKER_QUALIFICATION,
            second,
            True,
            pair_index,
            1,
        )
    return NeutralWorkerQualificationPlan(requests=tuple(requests))


def _median_ratio(left: list[float], right: list[float]) -> float | None:
    if not left or not right:
        return None
    left_median = statistics.median(left)
    right_median = statistics.median(right)
    low = min(left_median, right_median)
    high = max(left_median, right_median)
    if low == 0:
        return 1.0 if high == 0 else None
    return high / low


def assess_neutral_worker_qualification(
    plan: NeutralWorkerQualificationPlan,
    samples: tuple[NeutralWorkerSample, ...],
) -> NeutralWorkerQualificationAssessment:
    """Assess only neutral pre-treatment measurements, never A/B/C telemetry."""

    measured_plan = [item for item in plan.requests if item.measured_for_worker_symmetry]
    expected = {
        (
            cast(int, item.measurement_pair_index),
            cast(int, item.pair_order_index),
            item.worker_id,
        )
        for item in measured_plan
    }
    observed = {
        (item.measurement_pair_index, item.pair_order_index, item.worker_id)
        for item in samples
    }
    if len(observed) != len(samples):
        raise VariancePilotV2ContractError(
            "V2_NEUTRAL_SAMPLE_DUPLICATE",
            "neutral worker evidence contains duplicate sample identities",
        )
    if observed - expected:
        raise VariancePilotV2ContractError(
            "V2_NEUTRAL_SAMPLE_UNEXPECTED",
            "neutral worker evidence contains unexpected sample identities",
        )

    blocking: list[str] = []
    if observed != expected:
        blocking.append("NEUTRAL_SAMPLE_SET_INCOMPLETE")
    if any(not item.admitted for item in samples):
        blocking.append("NEUTRAL_OUTPUT_ADMISSION_FAILED")
    if any(not item.telemetry_valid for item in samples):
        blocking.append("NEUTRAL_TELEMETRY_INVALID")

    usable = [
        item
        for item in samples
        if item.admitted
        and item.telemetry_valid
        and item.time_to_first_token_ms is not None
        and item.prefill_duration_ms is not None
    ]
    worker_1 = [item for item in usable if item.worker_id is WorkerId.WORKER_1]
    worker_2 = [item for item in usable if item.worker_id is WorkerId.WORKER_2]
    ttft_ratio = _median_ratio(
        [cast(float, item.time_to_first_token_ms) for item in worker_1],
        [cast(float, item.time_to_first_token_ms) for item in worker_2],
    )
    prefill_ratio = _median_ratio(
        [cast(float, item.prefill_duration_ms) for item in worker_1],
        [cast(float, item.prefill_duration_ms) for item in worker_2],
    )
    if ttft_ratio is None:
        blocking.append("NEUTRAL_TTFT_RATIO_UNAVAILABLE")
    elif ttft_ratio > MAXIMUM_WORKER_MEDIAN_TTFT_RATIO:
        blocking.append("NEUTRAL_TTFT_ASYMMETRY_EXCEEDED")
    if prefill_ratio is None:
        blocking.append("NEUTRAL_PREFILL_RATIO_UNAVAILABLE")
    elif prefill_ratio > MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO:
        blocking.append("NEUTRAL_PREFILL_ASYMMETRY_EXCEEDED")

    blocking = sorted(set(blocking))
    return NeutralWorkerQualificationAssessment(
        decision="PASS" if not blocking else "FAIL",
        observed_sample_count=len(samples),
        worker_1_sample_count=sum(item.worker_id is WorkerId.WORKER_1 for item in samples),
        worker_2_sample_count=sum(item.worker_id is WorkerId.WORKER_2 for item in samples),
        worker_median_ttft_ratio=ttft_ratio,
        worker_median_prefill_ratio=prefill_ratio,
        blocking_reasons=tuple(blocking),
    )

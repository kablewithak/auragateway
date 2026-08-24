"""Generate and validate non-authorizing variance-pilot runtime-contract readiness V2."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import Field, ValidationError

from auragateway.local_abc import (
    measured_abc_variance_pilot_current_line_reconciliation_v1 as reconciliation,
)
from auragateway.local_abc import measured_abc_variance_pilot_runtime_v1 as runtime
from auragateway.local_abc.contracts import ConditionId, LocalABCContract

BASE_MAIN_COMMIT: Final = "9d59d417c92f79a4540b01b7292f5bf6e655e0d2"

PILOT_MANIFEST_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_manifest.json")
PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_schedule.json")
CONDITION_FINGERPRINTS_PATH: Final = Path(
    "data/evals/benchmark/preflight-v3/condition_fingerprints.json"
)
COMPILER_SPEC_PATH: Final = Path("data/context/compiler_spec.json")
CURRENT_ACCEPTANCE_PATH: Final = reconciliation.CURRENT_P5_P6_ACCEPTANCE_PATH
RECONCILIATION_RECORD_PATH: Final = reconciliation.RECORD_PATH
RECONCILIATION_REVIEW_PATH: Final = reconciliation.REVIEW_PATH

RUNTIME_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_runtime_v1.py"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_runtime_launcher_readiness_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_runtime_launcher_readiness_v1.py"
)
RUNTIME_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_runtime_v1.py"
)

RUNTIME_REQUEST_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/runtime_request_v1.json")
RUNTIME_REALIZATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_runtime_realization_v1.json"
)
READINESS_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_runtime_launcher_readiness_v2.json"
)

NEXT_GATE: Final = (
    "IMPLEMENT_VARIANCE_PILOT_TRANSACTION_BOUND_EXECUTABLE_AND_AUTHORIZATION_SUCCESSOR_V1"
)


class ReadinessError(RuntimeError):
    """Metadata-safe runtime readiness error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class ArtifactReceipt(LocalABCContract):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class RuntimeModelContract(LocalABCContract):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    required_native_module: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    attention_backend: Literal["TRITON_ATTN"] = "TRITON_ATTN"
    gpu_topology: Literal["T4_X2"] = "T4_X2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_snapshot_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class PilotBudget(LocalABCContract):
    pilot_case_count: Literal[6] = 6
    pilot_trajectory_count: Literal[54] = 54
    pilot_turn_count: Literal[216] = 216
    maximum_request_attempt_count: Literal[432] = 432
    maximum_attempts_per_turn: Literal[2] = 2
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0
    replacement_cases_permitted: Literal[False] = False


class RouteContract(LocalABCContract):
    realization_id: Literal["four-turn-route-realization-v1"] = "four-turn-route-realization-v1"
    condition_a_workers: tuple[
        Literal["worker_1"],
        Literal["worker_2"],
        Literal["worker_1"],
        Literal["worker_2"],
    ] = ("worker_1", "worker_2", "worker_1", "worker_2")
    condition_b_workers: tuple[
        Literal["worker_1"],
        Literal["worker_2"],
        Literal["worker_1"],
        Literal["worker_2"],
    ] = ("worker_1", "worker_2", "worker_1", "worker_2")
    condition_c_workers: tuple[
        Literal["worker_1"],
        Literal["worker_1"],
        Literal["worker_1"],
        Literal["worker_1"],
    ] = ("worker_1", "worker_1", "worker_1", "worker_1")
    operational_telemetry_turn: Literal[2] = 2
    effect_estimation_permitted_from_pilot: Literal[False] = False


class TelemetryAdmissionContract(LocalABCContract):
    preflight_required_before_pilot_requests: Literal[True] = True
    current_timing_metric_names_prequalified: Literal[False] = False
    missing_metric_becomes_zero: Literal[False] = False
    ambiguous_metric_permitted: Literal[False] = False
    required_roles: tuple[
        Literal["prefill_duration_ms"],
        Literal["time_to_first_token_ms"],
        Literal["end_to_end_latency_ms"],
    ] = (
        "prefill_duration_ms",
        "time_to_first_token_ms",
        "end_to_end_latency_ms",
    )
    pilot_requests_blocked_until_all_roles_qualified: Literal[True] = True


class RuntimeRequest(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    request_id: Literal["auragateway-measured-abc-variance-pilot-runtime-request-v1"]
    base_main_commit: Literal["9d59d417c92f79a4540b01b7292f5bf6e655e0d2"] = BASE_MAIN_COMMIT
    runtime: RuntimeModelContract = RuntimeModelContract()
    budget: PilotBudget = PilotBudget()
    route_contract: RouteContract = RouteContract()
    telemetry_admission: TelemetryAdmissionContract = TelemetryAdmissionContract()
    worker_bindings: tuple[
        Literal["worker_1=gpu0:8001"],
        Literal["worker_2=gpu1:8002"],
    ] = ("worker_1=gpu0:8001", "worker_2=gpu1:8002")
    internet_enabled: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    raw_prompt_public: Literal[False] = False
    raw_user_message_public: Literal[False] = False
    raw_retrieved_document_public: Literal[False] = False
    raw_model_output_public: Literal[False] = False
    transaction_bound_authorization_required: Literal[True] = True
    authorization_specific_kaggle_inputs: Literal[0] = 0
    preissuance_platform_observation_required: Literal[False] = False
    post_artifact_platform_observation_required: Literal[True] = True
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False


class RuntimeRealizationRecord(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-measured-abc-variance-pilot-runtime-realization-v1"]
    runtime_request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    condition_fingerprints_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    compiler_spec_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_acceptance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reconciliation_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reconciliation_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_core: ArtifactReceipt
    route_realization_basis: Literal["FROZEN_TWO_WORKER_ROUTE_PAIR_REPEATED_ACROSS_FOUR_TURNS"] = (
        "FROZEN_TWO_WORKER_ROUTE_PAIR_REPEATED_ACROSS_FOUR_TURNS"
    )
    operational_telemetry_projection: Literal["TURN_TWO_PRIMARY_RUNTIME_TELEMETRY"] = (
        "TURN_TWO_PRIMARY_RUNTIME_TELEMETRY"
    )
    prompt_semantics_reused_from_controlled_live_execution: Literal[True] = True
    timing_telemetry_preflight_required: Literal[True] = True
    current_timing_telemetry_qualification_established: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    non_claims: tuple[str, ...]
    next_gate: str


class RuntimeLauncherReadinessV2(LocalABCContract):
    schema_version: Literal["2.0.0"] = "2.0.0"
    readiness_id: Literal["auragateway-measured-abc-variance-pilot-runtime-launcher-readiness-v2"]
    status: Literal["READY_FOR_TRANSACTION_BOUND_EXECUTABLE_IMPLEMENTATION"] = (
        "READY_FOR_TRANSACTION_BOUND_EXECUTABLE_IMPLEMENTATION"
    )
    base_main_commit: Literal["9d59d417c92f79a4540b01b7292f5bf6e655e0d2"] = BASE_MAIN_COMMIT
    runtime_request: ArtifactReceipt
    runtime_realization: ArtifactReceipt
    runtime_core: ArtifactReceipt
    producer_source: ArtifactReceipt
    producer_test: ArtifactReceipt
    runtime_test: ArtifactReceipt
    old_runtime_launcher_readiness_v1_superseded: Literal[True] = True
    old_variance_pilot_authorization_v1_superseded: Literal[True] = True
    transaction_bound_successor_required: Literal[True] = True
    transaction_bound_executable_generated: Literal[False] = False
    platform_observation_persisted: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: str


def _canonical(payload: object) -> str:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_FILE_MISSING",
            "required runtime-readiness file is missing or unsafe",
            relative.as_posix(),
        )
    return ArtifactReceipt(
        repository_path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_FILE_MISSING",
            "required runtime-readiness JSON is missing",
            path.as_posix(),
        ) from error
    except json.JSONDecodeError as error:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_JSON_INVALID",
            "required runtime-readiness JSON is invalid",
            path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_JSON_ROOT_INVALID",
            "required runtime-readiness JSON root must be one object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _validate_schedule(repo_root: Path) -> tuple[str, str]:
    schedule_path = repo_root / PILOT_SCHEDULE_PATH
    manifest_path = repo_root / PILOT_MANIFEST_PATH
    schedule = _load_json_object(schedule_path)
    manifest = _load_json_object(manifest_path)
    required = {
        "case_count": 6,
        "trajectory_count": 54,
        "turn_count": 216,
        "maximum_request_attempt_count": 432,
        "hidden_retries_permitted": False,
        "replacement_cases_permitted": False,
        "final_benchmark_effect_claims_permitted": False,
    }
    for key, expected in required.items():
        if schedule.get(key) != expected:
            raise ReadinessError(
                "VARIANCE_PILOT_RUNTIME_READINESS_SCHEDULE_DRIFT",
                f"pilot schedule field drifted: {key}",
                PILOT_SCHEDULE_PATH.as_posix(),
            )
    trajectories = schedule.get("trajectories")
    if not isinstance(trajectories, list) or len(trajectories) != 54:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_SCHEDULE_DRIFT",
            "pilot schedule must preserve exactly 54 trajectories",
            PILOT_SCHEDULE_PATH.as_posix(),
        )
    schedule_sha = _sha256_file(schedule_path)
    if manifest.get("pilot_schedule_sha256") != schedule_sha:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_MANIFEST_DRIFT",
            "pilot manifest no longer binds the schedule bytes",
            PILOT_MANIFEST_PATH.as_posix(),
        )
    return schedule_sha, _sha256_file(manifest_path)


def _validate_condition_contract(repo_root: Path) -> str:
    path = repo_root / CONDITION_FINGERPRINTS_PATH
    payload = _load_json_object(path)
    records = payload.get("records")
    if not isinstance(records, list) or len(records) != 3:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_CONDITION_DRIFT",
            "condition fingerprint manifest must contain A, B, and C",
            CONDITION_FINGERPRINTS_PATH.as_posix(),
        )
    expected_routes = {
        "A": ["worker_1", "worker_2"],
        "B": ["worker_1", "worker_2"],
        "C": ["worker_1", "worker_1"],
    }
    expected_prefix = {
        "A": "cache_hostile",
        "B": "deterministic_exact",
        "C": "deterministic_exact",
    }
    observed_ids: list[str] = []
    for raw in records:
        if not isinstance(raw, dict):
            raise ReadinessError(
                "VARIANCE_PILOT_RUNTIME_READINESS_CONDITION_DRIFT",
                "condition fingerprint record is invalid",
                CONDITION_FINGERPRINTS_PATH.as_posix(),
            )
        record = cast(dict[str, object], raw)
        raw_payload = record.get("payload")
        if not isinstance(raw_payload, dict):
            raise ReadinessError(
                "VARIANCE_PILOT_RUNTIME_READINESS_CONDITION_DRIFT",
                "condition fingerprint payload is invalid",
                CONDITION_FINGERPRINTS_PATH.as_posix(),
            )
        condition = cast(dict[str, object], raw_payload)
        condition_id = condition.get("condition_id")
        if not isinstance(condition_id, str) or condition_id not in expected_routes:
            raise ReadinessError(
                "VARIANCE_PILOT_RUNTIME_READINESS_CONDITION_DRIFT",
                "condition fingerprint ID is invalid",
                CONDITION_FINGERPRINTS_PATH.as_posix(),
            )
        observed_ids.append(condition_id)
        if condition.get("route_schedule") != expected_routes[condition_id]:
            raise ReadinessError(
                "VARIANCE_PILOT_RUNTIME_READINESS_ROUTE_DRIFT",
                f"condition route schedule drifted: {condition_id}",
                CONDITION_FINGERPRINTS_PATH.as_posix(),
            )
        if condition.get("prefix_policy") != expected_prefix[condition_id]:
            raise ReadinessError(
                "VARIANCE_PILOT_RUNTIME_READINESS_PREFIX_DRIFT",
                f"condition prefix policy drifted: {condition_id}",
                CONDITION_FINGERPRINTS_PATH.as_posix(),
            )
    if observed_ids != ["A", "B", "C"]:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_CONDITION_ORDER_DRIFT",
            "condition fingerprints must preserve A, B, C order",
            CONDITION_FINGERPRINTS_PATH.as_posix(),
        )
    return _sha256_file(path)


def _validate_reconciliation(repo_root: Path) -> tuple[str, str]:
    reconciliation.validate_implementation(repo_root)
    return (
        _sha256_file(repo_root / RECONCILIATION_RECORD_PATH),
        _sha256_file(repo_root / RECONCILIATION_REVIEW_PATH),
    )


def build_request() -> RuntimeRequest:
    return RuntimeRequest(request_id="auragateway-measured-abc-variance-pilot-runtime-request-v1")


def build_realization(repo_root: Path, request: RuntimeRequest) -> RuntimeRealizationRecord:
    schedule_sha, manifest_sha = _validate_schedule(repo_root)
    condition_sha = _validate_condition_contract(repo_root)
    reconciliation_sha, reconciliation_review_sha = _validate_reconciliation(repo_root)
    compiler_spec = _load_json_object(repo_root / COMPILER_SPEC_PATH)
    runtime.build_static_system_prompt(compiler_spec)
    for condition in ConditionId:
        runtime.route_realization(condition)
        runtime.prompt_realization(condition)
    return RuntimeRealizationRecord(
        record_id="auragateway-measured-abc-variance-pilot-runtime-realization-v1",
        runtime_request_sha256=hashlib.sha256(
            _canonical(request.model_dump(mode="json")).encode("utf-8")
        ).hexdigest(),
        pilot_schedule_sha256=schedule_sha,
        pilot_manifest_sha256=manifest_sha,
        condition_fingerprints_sha256=condition_sha,
        compiler_spec_sha256=_sha256_file(repo_root / COMPILER_SPEC_PATH),
        current_acceptance_sha256=_sha256_file(repo_root / CURRENT_ACCEPTANCE_PATH),
        reconciliation_record_sha256=reconciliation_sha,
        reconciliation_review_sha256=reconciliation_review_sha,
        runtime_core=_receipt(repo_root, RUNTIME_SOURCE_PATH),
        non_claims=(
            "This record does not authorize or execute the variance pilot.",
            "This record does not qualify current timing metric names.",
            "This record does not generate a transaction-bound executable.",
            "This record does not persist a Kaggle platform observation.",
            "This record does not freeze final repetition counts.",
            "This record does not estimate any final A/B/C effect.",
            "This record does not authorize final measured A/B/C execution.",
        ),
        next_gate=NEXT_GATE,
    )


def build_readiness(
    repo_root: Path,
    realization: RuntimeRealizationRecord,
) -> RuntimeLauncherReadinessV2:
    _ = realization
    return RuntimeLauncherReadinessV2(
        readiness_id=("auragateway-measured-abc-variance-pilot-runtime-launcher-readiness-v2"),
        runtime_request=_receipt(repo_root, RUNTIME_REQUEST_PATH),
        runtime_realization=_receipt(repo_root, RUNTIME_REALIZATION_PATH),
        runtime_core=_receipt(repo_root, RUNTIME_SOURCE_PATH),
        producer_source=_receipt(repo_root, SOURCE_PATH),
        producer_test=_receipt(repo_root, TEST_PATH),
        runtime_test=_receipt(repo_root, RUNTIME_TEST_PATH),
        next_gate=NEXT_GATE,
    )


def _write_json(path: Path, model: LocalABCContract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _canonical(model.model_dump(mode="json")),
        encoding="utf-8",
        newline="\n",
    )


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    request = build_request()
    _write_json(root / RUNTIME_REQUEST_PATH, request)
    realization = build_realization(root, request)
    _write_json(root / RUNTIME_REALIZATION_PATH, realization)
    readiness = build_readiness(root, realization)
    _write_json(root / READINESS_PATH, readiness)
    return {
        "status": "VARIANCE_PILOT_RUNTIME_CONTRACT_READINESS_V2_GENERATED",
        "route_realization_id": "four-turn-route-realization-v1",
        "operational_telemetry_turn": 2,
        "timing_telemetry_preflight_required": True,
        "transaction_bound_executable_generated": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_request = build_request()
    expected_realization = build_realization(root, expected_request)
    try:
        observed_request = RuntimeRequest.model_validate_json(
            (root / RUNTIME_REQUEST_PATH).read_text(encoding="utf-8")
        )
        observed_realization = RuntimeRealizationRecord.model_validate_json(
            (root / RUNTIME_REALIZATION_PATH).read_text(encoding="utf-8")
        )
        observed_readiness = RuntimeLauncherReadinessV2.model_validate_json(
            (root / READINESS_PATH).read_text(encoding="utf-8")
        )
    except FileNotFoundError as error:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_OUTPUT_MISSING",
            "generated runtime-readiness output is missing",
        ) from error
    except ValidationError as error:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_OUTPUT_INVALID",
            "generated runtime-readiness output failed typed validation",
        ) from error
    if observed_request != expected_request:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_REQUEST_DRIFT",
            "runtime request is not deterministic",
            RUNTIME_REQUEST_PATH.as_posix(),
        )
    if observed_realization != expected_realization:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_REALIZATION_DRIFT",
            "runtime realization is not deterministic",
            RUNTIME_REALIZATION_PATH.as_posix(),
        )
    expected_readiness = build_readiness(root, expected_realization)
    if observed_readiness != expected_readiness:
        raise ReadinessError(
            "VARIANCE_PILOT_RUNTIME_READINESS_RECORD_DRIFT",
            "runtime readiness is not deterministic",
            READINESS_PATH.as_posix(),
        )
    return {
        "status": "VARIANCE_PILOT_RUNTIME_CONTRACT_READINESS_V2_VALID",
        "transaction_bound_executable_generated": False,
        "timing_telemetry_preflight_required": True,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "candidate_introduced_execution_authority": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-runtime-launcher-readiness-v1"
    )
    parser.add_argument(
        "command",
        choices=("generate", "validate-implementation"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        root = args.repo_root.resolve()
        result = generate(root) if args.command == "generate" else validate_implementation(root)
        print(_canonical(result), end="")
        return 0
    except ReadinessError as error:
        print(_canonical(error.envelope()), file=sys.stderr, end="")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

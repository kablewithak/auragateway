"""Deterministic planning and evidence contracts for measured A/B/C variance pilot V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self, TypeVar, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import ConditionId, LocalABCContract, WorkerId

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "ef57daa9da4ae1ee608146e50a162fb647e32e14"
POLICY_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/variance_pilot_v1_policy.json")
POLICY_SHA256: Final = "dcd7d7b709563728886d6adbc355374e2dee3c5d4c1e63ac9e0cccdc4654c303"

DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_v1_design.json"
)
DESIGN_GIT_BLOB_SHA: Final = "80a543ce73e2fc1405531b231afc58ab12b4e949"
DESIGN_SHA256: Final = "f1dcd141f7447515bf3b68007fe2e7336f53b792fa69ffbfbe55d1dc02c17f5c"

EPISODE_MANIFEST_PATH: Final = Path("data/evals/episodes/manifest.json")
EPISODE_MANIFEST_GIT_BLOB_SHA: Final = "9a702e6ea9ee0673d7142ade77937bdd5aafee13"
EPISODE_MANIFEST_SHA256: Final = "3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b"

ACCEPTED_EPISODES_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
ACCEPTED_EPISODES_GIT_BLOB_SHA: Final = "b8e6a9c0a0097b0755acf9b47ac332792ffaaeac"
ACCEPTED_EPISODES_SHA256: Final = "6229df94a6a426f815a2050172a79e115d9554031239043b397140ce13894285"
RUNTIME_SELECTION_PATH: Final = Path("data/evals/episodes/runtime-v1/selection.json")
RUNTIME_SELECTION_GIT_BLOB_SHA: Final = "3340765b2a2ad9f59bec69f0dbc3ba22944aaf81"
RUNTIME_SELECTION_SHA256: Final = "5ff912ad317fe09d97518e5b03178ebe3bb565dcf09719182bfffc80b67034e1"

PREFLIGHT_MANIFEST_PATH: Final = Path("data/evals/benchmark/preflight-v3/manifest.json")
PREFLIGHT_MANIFEST_GIT_BLOB_SHA: Final = "9d25301b23a77c5bfc0ed14383e9cfe16ca9e842"
PLANNED_LEDGER_PATH: Final = Path("data/evals/benchmark/preflight-v3/planned_run_ledger.json")
PLANNED_LEDGER_SHA256: Final = "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
CONDITION_FINGERPRINTS_PATH: Final = Path(
    "data/evals/benchmark/preflight-v3/condition_fingerprints.json"
)
CONDITION_FINGERPRINTS_SHA256: Final = (
    "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
)

P5_P6_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
)
P5_P6_ACCEPTANCE_GIT_BLOB_SHA: Final = "2cac406ed4e8f2d5c50795d104d2db425abfcbac"

FINAL_AUTHORIZATION_IMPLEMENTATION_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_execution_authorization_v1.py"
)
FINAL_AUTHORIZATION_IMPLEMENTATION_GIT_BLOB_SHA: Final = "c26713d99ac3afcdbab2c89b1c2888e1c7a7db51"

PILOT_MANIFEST_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_manifest.json")
PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_schedule.json")
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_v1_implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_v1_implementation_record.json"
)
SOURCE_PATH: Final = Path("src/auragateway/local_abc/measured_abc_variance_pilot_v1.py")
AUTHORIZATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_execution_authorization_v1.py"
)
TEST_PATH: Final = Path("tests/unit/local_abc/test_measured_abc_variance_pilot_v1.py")
AUTHORIZATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_execution_authorization_v1.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-08-local-abc-measured-abc-variance-pilot-v1-implementation.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Measured_ABC_Variance_Pilot_V1_Implementation.md"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_measured_abc_variance_pilot_v1.md")

EXPECTED_PILOT_CASE_COUNT: Final = 6
EXPECTED_TRAJECTORY_COUNT: Final = 54
EXPECTED_TURN_COUNT: Final = 216
MAXIMUM_REQUEST_ATTEMPTS: Final = 432
TURNS_PER_TRAJECTORY: Final = 4
MAXIMUM_ATTEMPTS_PER_TURN: Final = 2

MAXIMUM_INTERRUPTION_RATE: Final = 0.05
MINIMUM_NUMERIC_TELEMETRY_FRACTION: Final = 0.95
MAXIMUM_WORKER_MEDIAN_TTFT_RATIO: Final = 1.25
MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO: Final = 1.25

_ModelT = TypeVar("_ModelT", bound=LocalABCContract)


class VariancePilotError(RuntimeError):
    """Metadata-safe variance-pilot implementation failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class ErrorEnvelope(LocalABCContract):
    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class RepetitionFreezeDecision(StrEnum):
    ACCEPT_PLANNED_REPETITION_COUNTS = "ACCEPT_PLANNED_REPETITION_COUNTS"
    BLOCK_REPETITION_FREEZE_AND_REDESIGN = "BLOCK_REPETITION_FREEZE_AND_REDESIGN"


class PilotTaskStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class PilotComparisonStatus(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    NOT_EVALUATED = "not_evaluated"


class PilotCase(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    episode_id: str
    evaluation_split: Literal["development"] = "development"
    excluded_from_final_runtime_selection: Literal[True] = True


class PilotTrajectory(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    schedule_index: int = Field(ge=0, lt=EXPECTED_TRAJECTORY_COUNT)
    run_id: str
    comparison_pair_id: str
    episode_id: str
    pilot_replication_id: str
    condition_id: ConditionId
    condition_order_index: int = Field(ge=0, le=2)
    cache_namespace_id: str
    turn_count: Literal[4] = TURNS_PER_TRAJECTORY
    maximum_request_attempt_count: Literal[8] = 8

    @field_validator(
        "run_id",
        "comparison_pair_id",
        "episode_id",
        "pilot_replication_id",
        "cache_namespace_id",
    )
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("pilot identifiers must be non-empty and contain no whitespace")
        return value


class PilotSchedule(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    schedule_id: Literal["auragateway-measured-abc-variance-pilot-v1"] = (
        "auragateway-measured-abc-variance-pilot-v1"
    )
    selector_id: Literal["development-minus-final-runtime-selection-v1"] = (
        "development-minus-final-runtime-selection-v1"
    )
    cases: tuple[PilotCase, ...] = Field(min_length=6, max_length=6)
    trajectories: tuple[PilotTrajectory, ...] = Field(min_length=54, max_length=54)
    case_count: Literal[6] = 6
    trajectory_count: Literal[54] = 54
    turn_count: Literal[216] = 216
    maximum_request_attempt_count: Literal[432] = 432
    hidden_retries_permitted: Literal[False] = False
    replacement_cases_permitted: Literal[False] = False
    final_benchmark_effect_claims_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        indexes = tuple(item.schedule_index for item in self.trajectories)
        if indexes != tuple(range(EXPECTED_TRAJECTORY_COUNT)):
            raise ValueError("pilot schedule indexes must be contiguous")
        case_ids = tuple(item.episode_id for item in self.cases)
        if tuple(sorted(case_ids)) != case_ids:
            raise ValueError("pilot cases must be sorted")
        if len(case_ids) != len(set(case_ids)):
            raise ValueError("pilot cases must be unique")
        run_ids = tuple(item.run_id for item in self.trajectories)
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("pilot run IDs must be unique")
        namespaces = tuple(item.cache_namespace_id for item in self.trajectories)
        if len(namespaces) != len(set(namespaces)):
            raise ValueError("pilot cache namespaces must be unique")
        attempts = sum(int(item.maximum_request_attempt_count) for item in self.trajectories)
        if attempts != MAXIMUM_REQUEST_ATTEMPTS:
            raise ValueError("pilot request-attempt budget does not reconcile")
        return self


class PilotManifest(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    manifest_id: Literal["auragateway-measured-abc-variance-pilot-v1"] = (
        "auragateway-measured-abc-variance-pilot-v1"
    )
    implementation_base_main_commit: Literal["ef57daa9da4ae1ee608146e50a162fb647e32e14"] = (
        IMPLEMENTATION_BASE_MAIN_COMMIT
    )
    design_git_blob_sha: Literal["80a543ce73e2fc1405531b231afc58ab12b4e949"] = DESIGN_GIT_BLOB_SHA
    design_sha256: Literal["f1dcd141f7447515bf3b68007fe2e7336f53b792fa69ffbfbe55d1dc02c17f5c"] = (
        DESIGN_SHA256
    )
    diagnostic_episode_manifest_sha256: Literal[
        "3a77c6fa037c62a1a548c2e5dc13e9668ebd3114cb58903df538bf7fa239ea6b"
    ] = EPISODE_MANIFEST_SHA256
    runtime_selection_sha256: Literal[
        "5ff912ad317fe09d97518e5b03178ebe3bb565dcf09719182bfffc80b67034e1"
    ] = RUNTIME_SELECTION_SHA256
    planned_run_ledger_sha256: Literal[
        "c6ea56cd0be059101f9984e2cbdfab05e7a676e4c451b1bbf99120ae25a8472c"
    ] = PLANNED_LEDGER_SHA256
    condition_fingerprints_sha256: Literal[
        "e67e7b7de6ef903ea0b43aca397eddd57eb8231f0830cb10f62e190b8a6f6955"
    ] = CONDITION_FINGERPRINTS_SHA256
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_case_count: Literal[6] = 6
    pilot_trajectory_count: Literal[54] = 54
    pilot_turn_count: Literal[216] = 216
    maximum_request_attempt_count: Literal[432] = 432
    final_functional_repetitions: Literal[3] = 3
    final_runtime_repetitions: Literal[10] = 10
    variance_pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "merge_then_build_variance_pilot_runtime_launcher_and_issue_separate_authorization_v1"
    ] = "merge_then_build_variance_pilot_runtime_launcher_and_issue_separate_authorization_v1"


class PilotTelemetry(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    run_id: str
    episode_id: str
    pilot_replication_id: str
    condition_id: ConditionId
    worker_id: WorkerId
    task_status: PilotTaskStatus
    comparison_status: PilotComparisonStatus
    interrupted: bool
    cached_prefix_tokens: int | None = Field(default=None, ge=0)
    newly_computed_prefill_tokens: int | None = Field(default=None, ge=0)
    prefill_duration_ms: float | None = Field(default=None, ge=0)
    time_to_first_token_ms: float | None = Field(default=None, ge=0)
    end_to_end_latency_ms: float | None = Field(default=None, ge=0)
    session_duration_ms: float | None = Field(default=None, ge=0)
    cache_consistent: bool | None = None
    raw_prompt_retained: Literal[False] = False
    raw_user_message_retained: Literal[False] = False
    raw_retrieved_document_text_retained: Literal[False] = False
    raw_model_output_retained: Literal[False] = False
    credentials_retained: Literal[False] = False
    customer_data_used: Literal[False] = False


class PilotEvidenceBundle(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    bundle_id: Literal["auragateway-measured-abc-variance-pilot-v1-evidence"] = (
        "auragateway-measured-abc-variance-pilot-v1-evidence"
    )
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    trajectories: tuple[PilotTelemetry, ...] = Field(min_length=54, max_length=54)
    external_spend: Literal[0] = 0
    external_network_requests: Literal[0] = 0
    hidden_retries: Literal[0] = 0
    replacement_cases_used: Literal[False] = False

    @model_validator(mode="after")
    def validate_trajectory_identity(self) -> Self:
        run_ids = tuple(item.run_id for item in self.trajectories)
        if len(run_ids) != len(set(run_ids)):
            raise ValueError("pilot evidence run IDs must be unique")
        return self


class PilotOperationalAssessment(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    total_trajectories: Literal[54] = 54
    interruption_count: int = Field(ge=0, le=54)
    interruption_rate: float = Field(ge=0, le=1)
    numeric_telemetry_complete_count: int = Field(ge=0, le=54)
    numeric_telemetry_fraction: float = Field(ge=0, le=1)
    worker_1_numeric_sample_count: int = Field(ge=0)
    worker_2_numeric_sample_count: int = Field(ge=0)
    worker_median_ttft_ratio: float | None = Field(default=None, ge=1)
    worker_median_prefill_ratio: float | None = Field(default=None, ge=1)
    cache_consistency_failure_count: int = Field(ge=0)
    decision: RepetitionFreezeDecision
    blocking_reasons: tuple[str, ...]
    final_functional_repetitions: Literal[3] = 3
    final_runtime_repetitions: Literal[10] = 10
    final_effect_size_used: Literal[False] = False
    final_runtime_selected_cases_used: Literal[False] = False


class ImplementationReview(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-measured-abc-variance-pilot-v1-review"] = (
        "auragateway-measured-abc-variance-pilot-v1-review"
    )
    implementation_base_main_commit: Literal["ef57daa9da4ae1ee608146e50a162fb647e32e14"] = (
        IMPLEMENTATION_BASE_MAIN_COMMIT
    )
    design_git_blob_sha: Literal["80a543ce73e2fc1405531b231afc58ab12b4e949"] = DESIGN_GIT_BLOB_SHA
    selector_id: Literal["development-minus-final-runtime-selection-v1"] = (
        "development-minus-final-runtime-selection-v1"
    )
    case_count: Literal[6] = 6
    trajectory_count: Literal[54] = 54
    turn_count: Literal[216] = 216
    maximum_request_attempt_count: Literal[432] = 432
    pilot_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    implementation_status: Literal["IMPLEMENTED_NOT_AUTHORIZED"] = "IMPLEMENTED_NOT_AUTHORIZED"
    next_gate: Literal[
        "merge_then_build_variance_pilot_runtime_launcher_and_issue_separate_authorization_v1"
    ] = "merge_then_build_variance_pilot_runtime_launcher_and_issue_separate_authorization_v1"


class ArtifactReceipt(LocalABCContract):
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ImplementationRecord(LocalABCContract):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-measured-abc-variance-pilot-v1-record"] = (
        "auragateway-measured-abc-variance-pilot-v1-record"
    )
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    policy: ArtifactReceipt
    source: ArtifactReceipt
    authorization_source: ArtifactReceipt
    tests: ArtifactReceipt
    authorization_tests: ArtifactReceipt
    adr: ArtifactReceipt
    report: ArtifactReceipt
    runbook: ArtifactReceipt
    pilot_manifest: ArtifactReceipt
    pilot_schedule: ArtifactReceipt
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    implementation_status: Literal["IMPLEMENTED_NOT_AUTHORIZED"] = "IMPLEMENTED_NOT_AUTHORIZED"


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


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _error(
    code: str,
    message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise VariancePilotError(
        code,
        message,
        path.as_posix() if path is not None else None,
        details,
    )


def _read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        _error("VARIANCE_PILOT_ARTIFACT_MISSING", "Required pilot artifact is missing", path)
    except json.JSONDecodeError:
        _error("VARIANCE_PILOT_JSON_INVALID", "Pilot artifact is invalid JSON", path)


def _load_model(model: type[_ModelT], path: Path) -> _ModelT:
    try:
        return model.model_validate(_read_json(path))
    except ValidationError as exc:
        _error(
            "VARIANCE_PILOT_SCHEMA_INVALID",
            "Pilot artifact failed typed validation",
            path,
            tuple(item["msg"] for item in exc.errors(include_url=False, include_input=False)),
        )


def _run_git(repo_root: Path, *args: str, binary: bool = False) -> str | bytes:
    if binary:
        completed_bytes = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if completed_bytes.returncode != 0:
            _error(
                "VARIANCE_PILOT_GIT_FAILED",
                "Required Git operation failed",
                details=(
                    " ".join(args),
                    completed_bytes.stderr.decode(errors="replace").strip(),
                ),
            )
        return completed_bytes.stdout
    completed_text = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed_text.returncode != 0:
        _error(
            "VARIANCE_PILOT_GIT_FAILED",
            "Required Git operation failed",
            details=(" ".join(args), completed_text.stderr.strip()),
        )
    return completed_text.stdout


def _git_blob_sha(repo_root: Path, relative: Path) -> str:
    return cast(
        str,
        _run_git(repo_root, "rev-parse", f"HEAD:{relative.as_posix()}"),
    ).strip()


def _git_blob_bytes(repo_root: Path, relative: Path) -> bytes:
    return cast(
        bytes,
        _run_git(repo_root, "show", f"HEAD:{relative.as_posix()}", binary=True),
    )


def _git_sha256(repo_root: Path, relative: Path) -> str:
    return _sha256_bytes(_git_blob_bytes(repo_root, relative))


def _artifact_receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file():
        _error(
            "VARIANCE_PILOT_IMPLEMENTATION_ARTIFACT_MISSING",
            "Implementation artifact is missing",
            relative,
        )
    return ArtifactReceipt(
        repository_path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _validate_authorities(repo_root: Path) -> None:
    policy_path = repo_root / POLICY_PATH
    if not policy_path.is_file() or _sha256_file(policy_path) != POLICY_SHA256:
        _error(
            "VARIANCE_PILOT_POLICY_DRIFT",
            "Variance-pilot policy identity drifted",
            POLICY_PATH,
        )
    expected_blobs: dict[Path, str] = {
        DESIGN_PATH: DESIGN_GIT_BLOB_SHA,
        EPISODE_MANIFEST_PATH: EPISODE_MANIFEST_GIT_BLOB_SHA,
        ACCEPTED_EPISODES_PATH: ACCEPTED_EPISODES_GIT_BLOB_SHA,
        RUNTIME_SELECTION_PATH: RUNTIME_SELECTION_GIT_BLOB_SHA,
        PREFLIGHT_MANIFEST_PATH: PREFLIGHT_MANIFEST_GIT_BLOB_SHA,
        P5_P6_ACCEPTANCE_PATH: P5_P6_ACCEPTANCE_GIT_BLOB_SHA,
        FINAL_AUTHORIZATION_IMPLEMENTATION_PATH: FINAL_AUTHORIZATION_IMPLEMENTATION_GIT_BLOB_SHA,
    }
    for path, expected_blob in expected_blobs.items():
        observed_blob = _git_blob_sha(repo_root, path)
        if observed_blob != expected_blob:
            _error(
                "VARIANCE_PILOT_AUTHORITY_DRIFT",
                "Variance-pilot authority identity drifted",
                path,
                (f"expected={expected_blob}", f"observed={observed_blob}"),
            )
    expected_hashes: dict[Path, str] = {
        DESIGN_PATH: DESIGN_SHA256,
        EPISODE_MANIFEST_PATH: EPISODE_MANIFEST_SHA256,
        ACCEPTED_EPISODES_PATH: ACCEPTED_EPISODES_SHA256,
        RUNTIME_SELECTION_PATH: RUNTIME_SELECTION_SHA256,
        PLANNED_LEDGER_PATH: PLANNED_LEDGER_SHA256,
        CONDITION_FINGERPRINTS_PATH: CONDITION_FINGERPRINTS_SHA256,
    }
    for path, expected_hash in expected_hashes.items():
        observed_hash = _git_sha256(repo_root, path)
        if observed_hash != expected_hash:
            _error(
                "VARIANCE_PILOT_AUTHORITY_HASH_DRIFT",
                "Variance-pilot authority content identity drifted",
                path,
                (f"expected={expected_hash}", f"observed={observed_hash}"),
            )


def _episode_rows(repo_root: Path) -> list[dict[str, object]]:
    payload = _read_json(repo_root / ACCEPTED_EPISODES_PATH)
    if not isinstance(payload, dict):
        _error(
            "VARIANCE_PILOT_EPISODES_INVALID",
            "Accepted episode set root is invalid",
            ACCEPTED_EPISODES_PATH,
        )
    rows = payload.get("episodes")
    if not isinstance(rows, list):
        _error(
            "VARIANCE_PILOT_EPISODES_INVALID",
            "Accepted episode set is missing episodes",
            ACCEPTED_EPISODES_PATH,
        )
    result: list[dict[str, object]] = []
    for row in rows:
        if not isinstance(row, dict):
            _error(
                "VARIANCE_PILOT_EPISODES_INVALID",
                "Accepted episode row is invalid",
                ACCEPTED_EPISODES_PATH,
            )
        result.append(cast(dict[str, object], row))
    return result


def _runtime_ids(repo_root: Path) -> set[str]:
    payload = _read_json(repo_root / RUNTIME_SELECTION_PATH)
    if not isinstance(payload, dict):
        _error(
            "VARIANCE_PILOT_RUNTIME_SELECTION_INVALID",
            "Runtime selection root is invalid",
            RUNTIME_SELECTION_PATH,
        )
    rows = payload.get("entries")
    if not isinstance(rows, list):
        _error(
            "VARIANCE_PILOT_RUNTIME_SELECTION_INVALID",
            "Runtime selection is missing entries",
            RUNTIME_SELECTION_PATH,
        )
    ids: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("episode_id"), str):
            _error(
                "VARIANCE_PILOT_RUNTIME_SELECTION_INVALID",
                "Runtime selection row is invalid",
                RUNTIME_SELECTION_PATH,
            )
        ids.add(cast(str, row["episode_id"]))
    if len(ids) != 6:
        _error(
            "VARIANCE_PILOT_RUNTIME_SELECTION_INVALID",
            "Runtime selection must contain exactly six unique episodes",
            RUNTIME_SELECTION_PATH,
        )
    return ids


def select_pilot_cases(repo_root: Path) -> tuple[PilotCase, ...]:
    runtime_ids = _runtime_ids(repo_root)
    selected: list[PilotCase] = []
    held_out_seen = 0
    development_seen = 0
    for row in _episode_rows(repo_root):
        episode_id = row.get("episode_id")
        split = row.get("evaluation_split")
        if not isinstance(episode_id, str) or not isinstance(split, str):
            _error(
                "VARIANCE_PILOT_EPISODE_IDENTITY_INVALID",
                "Episode identity or split is invalid",
                ACCEPTED_EPISODES_PATH,
            )
        if split == "held_out":
            held_out_seen += 1
            continue
        if split != "development":
            _error(
                "VARIANCE_PILOT_EPISODE_SPLIT_INVALID",
                "Episode split must be development or held_out",
                ACCEPTED_EPISODES_PATH,
                (episode_id, split),
            )
        development_seen += 1
        if episode_id in runtime_ids:
            continue
        selected.append(PilotCase(episode_id=episode_id))
    if development_seen != 12 or held_out_seen != 6:
        _error(
            "VARIANCE_PILOT_EPISODE_COUNTS_DRIFT",
            "Episode split counts drifted",
            ACCEPTED_EPISODES_PATH,
            (
                f"development={development_seen}",
                f"held_out={held_out_seen}",
            ),
        )
    selected = sorted(selected, key=lambda item: item.episode_id)
    if len(selected) != EXPECTED_PILOT_CASE_COUNT:
        _error(
            "VARIANCE_PILOT_CASE_SELECTION_DRIFT",
            "Pilot selector did not produce exactly six cases",
            ACCEPTED_EPISODES_PATH,
            (f"selected={len(selected)}",),
        )
    return tuple(selected)


def build_schedule(repo_root: Path) -> PilotSchedule:
    cases = select_pilot_cases(repo_root)
    orders: tuple[tuple[ConditionId, ConditionId, ConditionId], ...] = (
        (ConditionId.A, ConditionId.B, ConditionId.C),
        (ConditionId.B, ConditionId.C, ConditionId.A),
        (ConditionId.C, ConditionId.A, ConditionId.B),
    )
    trajectories: list[PilotTrajectory] = []
    schedule_index = 0
    for case in cases:
        for repetition_index, order in enumerate(orders, start=1):
            replication_id = f"pilot-r{repetition_index:02d}"
            pair_id = f"pilot-pair-{case.episode_id}-{replication_id}"
            for order_index, condition in enumerate(order):
                condition_slug = condition.value.lower()
                trajectories.append(
                    PilotTrajectory(
                        schedule_index=schedule_index,
                        run_id=(f"pilot-run-{case.episode_id}-{replication_id}-{condition_slug}"),
                        comparison_pair_id=pair_id,
                        episode_id=case.episode_id,
                        pilot_replication_id=replication_id,
                        condition_id=condition,
                        condition_order_index=order_index,
                        cache_namespace_id=(
                            f"pilot-ns-{case.episode_id}-{replication_id}-{condition_slug}"
                        ),
                    )
                )
                schedule_index += 1
    return PilotSchedule(cases=cases, trajectories=tuple(trajectories))


def build_manifest(schedule: PilotSchedule) -> PilotManifest:
    schedule_sha = _sha256_bytes(_canonical(schedule.model_dump(mode="json")).encode("utf-8"))
    return PilotManifest(pilot_schedule_sha256=schedule_sha)


def _ratio(values_a: list[float], values_b: list[float]) -> float | None:
    if not values_a or not values_b:
        return None
    median_a = statistics.median(values_a)
    median_b = statistics.median(values_b)
    low = min(median_a, median_b)
    high = max(median_a, median_b)
    if low == 0:
        return None if high == 0 else float("inf")
    return high / low


def assess_operational_variance(
    evidence: PilotEvidenceBundle,
    schedule: PilotSchedule,
) -> PilotOperationalAssessment:
    expected_ids = {item.run_id for item in schedule.trajectories}
    observed_ids = {item.run_id for item in evidence.trajectories}
    if observed_ids != expected_ids:
        _error(
            "VARIANCE_PILOT_EVIDENCE_RUN_SET_DRIFT",
            "Pilot evidence run set differs from the frozen pilot schedule",
        )
    interruption_count = sum(item.interrupted for item in evidence.trajectories)
    interruption_rate = interruption_count / EXPECTED_TRAJECTORY_COUNT

    def numeric_complete(item: PilotTelemetry) -> bool:
        return all(
            value is not None
            for value in (
                item.prefill_duration_ms,
                item.time_to_first_token_ms,
                item.end_to_end_latency_ms,
                item.session_duration_ms,
            )
        )

    complete = [item for item in evidence.trajectories if numeric_complete(item)]
    telemetry_fraction = len(complete) / EXPECTED_TRAJECTORY_COUNT
    worker_1 = [item for item in complete if item.worker_id is WorkerId.WORKER_1]
    worker_2 = [item for item in complete if item.worker_id is WorkerId.WORKER_2]
    ttft_ratio = _ratio(
        [cast(float, item.time_to_first_token_ms) for item in worker_1],
        [cast(float, item.time_to_first_token_ms) for item in worker_2],
    )
    prefill_ratio = _ratio(
        [cast(float, item.prefill_duration_ms) for item in worker_1],
        [cast(float, item.prefill_duration_ms) for item in worker_2],
    )
    cache_failures = sum(item.cache_consistent is False for item in evidence.trajectories)
    blocking: list[str] = []
    if interruption_rate > MAXIMUM_INTERRUPTION_RATE:
        blocking.append("INTERRUPTION_RATE_EXCEEDED")
    if telemetry_fraction < MINIMUM_NUMERIC_TELEMETRY_FRACTION:
        blocking.append("NUMERIC_TELEMETRY_INSUFFICIENT")
    if ttft_ratio is None:
        blocking.append("WORKER_TTFT_RATIO_UNAVAILABLE")
    elif ttft_ratio > MAXIMUM_WORKER_MEDIAN_TTFT_RATIO:
        blocking.append("WORKER_TTFT_ASYMMETRY_EXCEEDED")
    if prefill_ratio is None:
        blocking.append("WORKER_PREFILL_RATIO_UNAVAILABLE")
    elif prefill_ratio > MAXIMUM_WORKER_MEDIAN_PREFILL_RATIO:
        blocking.append("WORKER_PREFILL_ASYMMETRY_EXCEEDED")
    if cache_failures:
        blocking.append("CACHE_CONSISTENCY_FAILURE")
    decision = (
        RepetitionFreezeDecision.ACCEPT_PLANNED_REPETITION_COUNTS
        if not blocking
        else RepetitionFreezeDecision.BLOCK_REPETITION_FREEZE_AND_REDESIGN
    )
    return PilotOperationalAssessment(
        interruption_count=interruption_count,
        interruption_rate=interruption_rate,
        numeric_telemetry_complete_count=len(complete),
        numeric_telemetry_fraction=telemetry_fraction,
        worker_1_numeric_sample_count=len(worker_1),
        worker_2_numeric_sample_count=len(worker_2),
        worker_median_ttft_ratio=ttft_ratio,
        worker_median_prefill_ratio=prefill_ratio,
        cache_consistency_failure_count=cache_failures,
        decision=decision,
        blocking_reasons=tuple(blocking),
    )


def _write_canonical(path: Path, model: LocalABCContract) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _canonical(model.model_dump(mode="json")),
        encoding="utf-8",
        newline="\n",
    )


def build_review(manifest: PilotManifest, schedule: PilotSchedule) -> ImplementationReview:
    return ImplementationReview(
        pilot_manifest_sha256=_sha256_bytes(
            _canonical(manifest.model_dump(mode="json")).encode("utf-8")
        ),
        pilot_schedule_sha256=_sha256_bytes(
            _canonical(schedule.model_dump(mode="json")).encode("utf-8")
        ),
    )


def build_record(repo_root: Path, review: ImplementationReview) -> ImplementationRecord:
    review_sha = _sha256_bytes(_canonical(review.model_dump(mode="json")).encode("utf-8"))
    return ImplementationRecord(
        review_sha256=review_sha,
        policy=_artifact_receipt(repo_root, POLICY_PATH),
        source=_artifact_receipt(repo_root, SOURCE_PATH),
        authorization_source=_artifact_receipt(repo_root, AUTHORIZATION_SOURCE_PATH),
        tests=_artifact_receipt(repo_root, TEST_PATH),
        authorization_tests=_artifact_receipt(repo_root, AUTHORIZATION_TEST_PATH),
        adr=_artifact_receipt(repo_root, ADR_PATH),
        report=_artifact_receipt(repo_root, REPORT_PATH),
        runbook=_artifact_receipt(repo_root, RUNBOOK_PATH),
        pilot_manifest=_artifact_receipt(repo_root, PILOT_MANIFEST_PATH),
        pilot_schedule=_artifact_receipt(repo_root, PILOT_SCHEDULE_PATH),
    )


def generate(repo_root: Path) -> dict[str, object]:
    _validate_authorities(repo_root)
    schedule = build_schedule(repo_root)
    manifest = build_manifest(schedule)
    _write_canonical(repo_root / PILOT_SCHEDULE_PATH, schedule)
    _write_canonical(repo_root / PILOT_MANIFEST_PATH, manifest)
    review = build_review(manifest, schedule)
    _write_canonical(repo_root / REVIEW_PATH, review)
    record = build_record(repo_root, review)
    _write_canonical(repo_root / RECORD_PATH, record)
    return {
        "status": "MEASURED_ABC_VARIANCE_PILOT_V1_GENERATED",
        "pilot_case_count": 6,
        "pilot_trajectory_count": 54,
        "pilot_turn_count": 216,
        "maximum_request_attempt_count": 432,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": (
            "merge_then_build_variance_pilot_runtime_launcher_and_issue_separate_authorization_v1"
        ),
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    _validate_authorities(repo_root)
    schedule = build_schedule(repo_root)
    manifest = build_manifest(schedule)
    observed_schedule = _load_model(PilotSchedule, repo_root / PILOT_SCHEDULE_PATH)
    observed_manifest = _load_model(PilotManifest, repo_root / PILOT_MANIFEST_PATH)
    if observed_schedule != schedule:
        _error(
            "VARIANCE_PILOT_SCHEDULE_DRIFT",
            "Generated pilot schedule is not deterministic",
            PILOT_SCHEDULE_PATH,
        )
    if observed_manifest != manifest:
        _error(
            "VARIANCE_PILOT_MANIFEST_DRIFT",
            "Generated pilot manifest is not deterministic",
            PILOT_MANIFEST_PATH,
        )
    review = build_review(manifest, schedule)
    observed_review = _load_model(ImplementationReview, repo_root / REVIEW_PATH)
    if observed_review != review:
        _error(
            "VARIANCE_PILOT_REVIEW_DRIFT",
            "Variance-pilot implementation review drifted",
            REVIEW_PATH,
        )
    record = build_record(repo_root, review)
    observed_record = _load_model(ImplementationRecord, repo_root / RECORD_PATH)
    if observed_record != record:
        _error(
            "VARIANCE_PILOT_RECORD_DRIFT",
            "Variance-pilot implementation record drifted",
            RECORD_PATH,
        )
    return {
        "status": "MEASURED_ABC_VARIANCE_PILOT_V1_VALID",
        "implementation_status": "IMPLEMENTED_NOT_AUTHORIZED",
        "pilot_case_count": 6,
        "pilot_trajectory_count": 54,
        "pilot_turn_count": 216,
        "maximum_request_attempt_count": 432,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": (
            "merge_then_build_variance_pilot_runtime_launcher_and_issue_separate_authorization_v1"
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="measured-abc-variance-pilot-v1")
    parser.add_argument("command", choices=("generate", "validate-implementation"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main() -> int:
    try:
        args = _parser().parse_args()
        repo_root = args.repo_root.resolve()
        result = (
            generate(repo_root)
            if args.command == "generate"
            else validate_implementation(repo_root)
        )
        print(_canonical(result), end="")
        return 0
    except VariancePilotError as exc:
        envelope = ErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(_canonical(envelope.model_dump(mode="json")), end="", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

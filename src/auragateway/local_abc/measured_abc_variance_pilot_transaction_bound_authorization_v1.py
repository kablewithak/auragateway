"""Transaction-bound authorization successor for variance-pilot execution V1.

Static generation and validation are inert. Live issuance is permitted only from a clean,
synchronized main after merge and an exact operator retype of a fresh dynamic SHA-256 challenge.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import secrets
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import (
    measured_abc_variance_pilot_current_line_reconciliation_v1 as reconciliation,
)
from auragateway.local_abc import (
    measured_abc_variance_pilot_runtime_launcher_readiness_v1 as readiness,
)

BASE_MAIN_COMMIT: Final = "9d59d417c92f79a4540b01b7292f5bf6e655e0d2"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_transaction_bound_authorization_v1.py"
)
RUNTIME_PAYLOAD_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_transaction_bound_runtime_v1.py"
)
WRAPPER_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "measured_abc_variance_pilot_transaction_bound_wrapper_v1.py.tmpl"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_transaction_bound_authorization_v1.py"
)
RUNTIME_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_measured_abc_variance_pilot_transaction_bound_runtime_v1.py"
)

R2_RUNTIME_LIBRARY_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
R2_RUNTIME_LIBRARY_SHA256: Final = (
    "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
)

PILOT_SCHEDULE_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_schedule.json")
PILOT_MANIFEST_PATH: Final = Path("data/evals/benchmark/variance-pilot-v1/pilot_manifest.json")
ACCEPTED_EPISODES_PATH: Final = Path("data/evals/episodes/functional-v1/accepted_episodes.json")
RUNTIME_SELECTION_PATH: Final = Path("data/evals/episodes/runtime-v1/selection.json")
SOURCE_MANIFEST_PATH: Final = Path("data/corpus/source_manifest.json")
COMPILER_SPEC_PATH: Final = Path("data/context/compiler_spec.json")
READINESS_PATH: Final = readiness.READINESS_PATH
CURRENT_ACCEPTANCE_PATH: Final = reconciliation.CURRENT_P5_P6_ACCEPTANCE_PATH

REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_transaction_bound_"
    "authorization_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_transaction_bound_"
    "authorization_v1_record.json"
)

LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_transaction_bound_"
    "authorization_v1_live.json"
)
LIVE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_transaction_bound_"
    "artifact_v1_live_manifest.json"
)
PLATFORM_OBSERVATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_transaction_bound_"
    "platform_observation_v1_live.json"
)
TERMINAL_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_transaction_bound_"
    "authorization_v1_terminal.json"
)

AUTHORIZATION_SCOPE: Final = "MEASURED_ABC_VARIANCE_PILOT_TRANSACTION_BOUND_V1"
NOTEBOOK_NAME: Final = "ag-variance-pilot-transaction-bound-v1"
EVIDENCE_ZIP_NAME: Final = "ag-variance-pilot-tx-v1-evidence.zip"
DEFAULT_WINDOW_MINUTES: Final = 180
MAX_WINDOW_MINUTES: Final = 240

NEXT_GATE: Final = (
    "MERGE_THEN_VERIFY_PRESERVED_TRANSIENT_LIFECYCLE_COPIES_AND_"
    "ISSUE_FRESH_VARIANCE_PILOT_TRANSACTION_BOUND_AUTHORIZATION_V1"
)
NEXT_GATE_AFTER_ISSUE: Final = "PERSIST_VARIANCE_PILOT_PLATFORM_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
NEXT_GATE_AFTER_OBSERVATION: Final = "ONE_SAVE_AND_RUN_ALL_VARIANCE_PILOT_TRANSACTION_BOUND_V1"
NEXT_GATE_AFTER_TERMINAL: Final = (
    "PRESERVE_AND_ACCEPT_OR_CLASSIFY_VARIANCE_PILOT_TRANSACTION_BOUND_V1"
)


class AuthorizationError(RuntimeError):
    """Metadata-safe transaction-bound authorization error."""

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


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeModelContract(FrozenModel):
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


class ExecutionBudget(FrozenModel):
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_save_and_run_all_actions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_runtime_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[2] = 2
    maximum_worker_starts: Literal[2] = 2
    maximum_worker_teardowns: Literal[2] = 2
    maximum_timing_preflight_requests: Literal[2] = 2
    maximum_cache_salt_preflight_requests: Literal[3] = 3
    maximum_preflight_requests: Literal[5] = 5
    maximum_pilot_trajectory_count: Literal[54] = 54
    maximum_pilot_turn_count: Literal[216] = 216
    maximum_pilot_request_attempts: Literal[432] = 432
    maximum_total_model_requests: Literal[437] = 437
    maximum_output_tokens_per_request: Literal[64] = 64
    maximum_hidden_retries: Literal[0] = 0
    maximum_replacement_cases: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class CacheIsolationContract(FrozenModel):
    mechanism: Literal["VLLM_CACHE_SALT"] = "VLLM_CACHE_SALT"
    per_trajectory_cache_salt_required: Literal[True] = True
    salt_derivation: Literal["SHA256_CACHE_NAMESPACE_ID"] = "SHA256_CACHE_NAMESPACE_ID"
    same_trajectory_cache_reuse_permitted: Literal[True] = True
    cross_trajectory_cache_reuse_permitted: Literal[False] = False
    cache_salt_security_secret_claimed: Literal[False] = False


class RequiredPlatform(FrozenModel):
    accelerator: Literal["T4_X2"] = "T4_X2"
    allocated_gpu_count: Literal[2] = 2
    internet_enabled: Literal[False] = False
    external_network_access_permitted: Literal[False] = False
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    preissuance_platform_observation_required: Literal[False] = False
    fresh_post_artifact_observation_required: Literal[True] = True
    observation_precedes_save_and_run_all: Literal[True] = True
    observation_mounted_as_runtime_input: Literal[False] = False


class StaticReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-measured-abc-variance-pilot-transaction-bound-auth-v1-review"]
    base_main_commit: Literal["9d59d417c92f79a4540b01b7292f5bf6e655e0d2"] = BASE_MAIN_COMMIT
    status: Literal["IMPLEMENTED_NOT_ISSUED"] = "IMPLEMENTED_NOT_ISSUED"
    runtime: RuntimeModelContract = RuntimeModelContract()
    budget: ExecutionBudget = ExecutionBudget()
    cache_isolation: CacheIsolationContract = CacheIsolationContract()
    required_platform: RequiredPlatform = RequiredPlatform()
    r2_runtime_library_sha256: Literal[
        "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
    ] = R2_RUNTIME_LIBRARY_SHA256
    pilot_case_count: Literal[6] = 6
    pilot_trajectory_count: Literal[54] = 54
    pilot_turn_count: Literal[216] = 216
    timing_preflight_requires_live_model_requests: Literal[True] = True
    timing_preflight_request_count: Literal[2] = 2
    cache_salt_preflight_request_count: Literal[3] = 3
    total_preflight_request_count: Literal[5] = 5
    timing_preflight_precedes_pilot_requests: Literal[True] = True
    cache_salt_runtime_preflight_required: Literal[True] = True
    authorization_specific_kaggle_inputs: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    transaction_bound_executable_generated: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    non_claims: tuple[str, ...]
    next_gate: str


class ArtifactReceipt(FrozenModel):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=1)


class StaticRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-measured-abc-variance-pilot-transaction-bound-auth-v1-record"]
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source: ArtifactReceipt
    runtime_payload: ArtifactReceipt
    wrapper_template: ArtifactReceipt
    test: ArtifactReceipt
    runtime_test: ArtifactReceipt
    readiness: ArtifactReceipt
    reconciliation_record: ArtifactReceipt
    current_p5_p6_acceptance: ArtifactReceipt
    pilot_schedule: ArtifactReceipt
    pilot_manifest: ArtifactReceipt
    static_material_case_count: Literal[6] = 6
    static_material_trajectory_count: Literal[54] = 54
    live_authorization_issued: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: str


class LiveAuthorization(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str
    decision: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle: Literal["ISSUED"] = "ISSUED"
    scope: Literal["MEASURED_ABC_VARIANCE_PILOT_TRANSACTION_BOUND_V1"] = AUTHORIZATION_SCOPE
    issued_at: datetime
    expires_at: datetime
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    issuer_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    r2_runtime_library_sha256: Literal[
        "7f820f1b1195dd2877d4cd197fdc10b79c4e86490e98597aab8bae09cd4a3afc"
    ] = R2_RUNTIME_LIBRARY_SHA256
    pilot_runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pilot_material_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_launcher_readiness_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_p5_p6_acceptance_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    budget: ExecutionBudget = ExecutionBudget()
    cache_isolation: CacheIsolationContract = CacheIsolationContract()
    required_platform: RequiredPlatform = RequiredPlatform()
    pilot_execution_authorized: Literal[True] = True
    final_measured_abc_execution_authorized: Literal[False] = False
    single_use: Literal[True] = True
    authorization_reusable: Literal[False] = False
    unchanged_replay_authorized: Literal[False] = False
    runtime_anti_replay_established: Literal[False] = False
    authorization_specific_kaggle_inputs: Literal[0] = 0
    manual_confirmation_json_files: Literal[0] = 0
    preissuance_platform_observation_required: Literal[False] = False
    fresh_post_artifact_platform_observation_required: Literal[True] = True
    platform_observation_runtime_input: Literal[False] = False

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.issued_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("authorization timestamps must be timezone-aware")
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        return self


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _artifact_bytes(value: object) -> bytes:
    return _canonical_bytes(value) + b"\n"


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha256(path.read_bytes())


def _receipt(repo_root: Path, relative: Path) -> ArtifactReceipt:
    path = repo_root / relative
    if not path.is_file() or path.is_symlink():
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_REQUIRED_FILE_MISSING",
            "required authorization file is missing or unsafe",
            relative.as_posix(),
        )
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha_file(path),
        size_bytes=path.stat().st_size,
    )


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_REQUIRED_FILE_MISSING",
            "required JSON file is missing",
            path.as_posix(),
        ) from error
    except json.JSONDecodeError as error:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_JSON_INVALID",
            "required JSON file is invalid",
            path.as_posix(),
        ) from error
    if not isinstance(value, dict):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_JSON_ROOT_INVALID",
            "required JSON root must be one object",
            path.as_posix(),
        )
    return cast(dict[str, object], value)


def _git(repo_root: Path, *args: str, binary: bool = False) -> str | bytes:
    if binary:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=False,
            capture_output=True,
            timeout=30,
        )
        if completed.returncode != 0:
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_GIT_FAILED",
                "required Git operation failed",
            )
        return completed.stdout
    completed_text = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed_text.returncode != 0:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_GIT_FAILED",
            "required Git operation failed",
        )
    return completed_text.stdout.strip()


def _head_bytes(repo_root: Path, relative: Path) -> bytes:
    return cast(
        bytes,
        _git(
            repo_root,
            "show",
            f"HEAD:{relative.as_posix()}",
            binary=True,
        ),
    )


def _validate_r2_identity(repo_root: Path, *, committed: bool) -> None:
    payload = (
        _head_bytes(repo_root, R2_RUNTIME_LIBRARY_PATH)
        if committed
        else (repo_root / R2_RUNTIME_LIBRARY_PATH).read_bytes()
    )
    if _sha256(payload) != R2_RUNTIME_LIBRARY_SHA256:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_R2_RUNTIME_IDENTITY_DRIFT",
            "accepted current-runtime library identity drifted",
            R2_RUNTIME_LIBRARY_PATH.as_posix(),
        )


def _schedule_state(repo_root: Path) -> tuple[list[str], int]:
    schedule = _read_json(repo_root / PILOT_SCHEDULE_PATH)
    cases = schedule.get("cases")
    trajectories = schedule.get("trajectories")
    if not isinstance(cases, list) or len(cases) != 6:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_SCHEDULE_DRIFT",
            "pilot schedule must contain exactly six cases",
            PILOT_SCHEDULE_PATH.as_posix(),
        )
    if not isinstance(trajectories, list) or len(trajectories) != 54:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_SCHEDULE_DRIFT",
            "pilot schedule must contain exactly 54 trajectories",
            PILOT_SCHEDULE_PATH.as_posix(),
        )
    ids: list[str] = []
    for raw in cases:
        if not isinstance(raw, dict) or not isinstance(raw.get("episode_id"), str):
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_SCHEDULE_DRIFT",
                "pilot case identity is invalid",
                PILOT_SCHEDULE_PATH.as_posix(),
            )
        ids.append(cast(str, raw["episode_id"]))
    if len(ids) != len(set(ids)):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_SCHEDULE_DRIFT",
            "pilot case identities must be unique",
            PILOT_SCHEDULE_PATH.as_posix(),
        )
    return ids, len(trajectories)


def _validate_current_state(repo_root: Path) -> None:
    reconciliation.validate_implementation(repo_root)
    readiness.validate_implementation(repo_root)
    case_ids, trajectories = _schedule_state(repo_root)
    if len(case_ids) != 6 or trajectories != 54:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_CURRENT_STATE_INVALID",
            "variance-pilot schedule state is invalid",
        )
    _validate_r2_identity(repo_root, committed=True)


def build_review(repo_root: Path) -> StaticReview:
    _validate_current_state(repo_root)
    return StaticReview(
        review_id=("auragateway-measured-abc-variance-pilot-transaction-bound-auth-v1-review"),
        non_claims=(
            "This implementation does not issue live pilot authorization.",
            "This implementation does not execute Kaggle or GPU work.",
            "This implementation does not establish timing telemetry qualification.",
            "This implementation does not accept the variance pilot.",
            "This implementation does not freeze final repetition counts.",
            "This implementation does not establish an A/B/C effect.",
            "This implementation does not authorize final measured A/B/C execution.",
        ),
        next_gate=NEXT_GATE,
    )


def build_record(repo_root: Path, review: StaticReview) -> StaticRecord:
    return StaticRecord(
        record_id=("auragateway-measured-abc-variance-pilot-transaction-bound-auth-v1-record"),
        review_sha256=_sha256(_canonical_bytes(review)),
        source=_receipt(repo_root, SOURCE_PATH),
        runtime_payload=_receipt(repo_root, RUNTIME_PAYLOAD_PATH),
        wrapper_template=_receipt(repo_root, WRAPPER_TEMPLATE_PATH),
        test=_receipt(repo_root, TEST_PATH),
        runtime_test=_receipt(repo_root, RUNTIME_TEST_PATH),
        readiness=_receipt(repo_root, READINESS_PATH),
        reconciliation_record=_receipt(
            repo_root,
            reconciliation.RECORD_PATH,
        ),
        current_p5_p6_acceptance=_receipt(
            repo_root,
            CURRENT_ACCEPTANCE_PATH,
        ),
        pilot_schedule=_receipt(repo_root, PILOT_SCHEDULE_PATH),
        pilot_manifest=_receipt(repo_root, PILOT_MANIFEST_PATH),
        next_gate=NEXT_GATE,
    )


def _write_json(path: Path, value: BaseModel | dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_artifact_bytes(value))


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    review = build_review(root)
    _write_json(root / REVIEW_PATH, review)
    record = build_record(root, review)
    _write_json(root / RECORD_PATH, record)
    return {
        "status": "VARIANCE_PILOT_TRANSACTION_BOUND_AUTHORIZATION_V1_GENERATED",
        "live_authorization_issued": False,
        "transaction_bound_executable_generated": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_review = build_review(root)
    expected_record = build_record(root, expected_review)
    try:
        observed_review = StaticReview.model_validate_json((root / REVIEW_PATH).read_bytes())
        observed_record = StaticRecord.model_validate_json((root / RECORD_PATH).read_bytes())
    except (FileNotFoundError, ValidationError) as error:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_GENERATED_OUTPUT_INVALID",
            "generated transaction-bound authorization output is invalid",
        ) from error
    if observed_review != expected_review:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_REVIEW_DRIFT",
            "transaction-bound authorization review is not deterministic",
            REVIEW_PATH.as_posix(),
        )
    if observed_record != expected_record:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_RECORD_DRIFT",
            "transaction-bound authorization record is not deterministic",
            RECORD_PATH.as_posix(),
        )
    return {
        "status": "VARIANCE_PILOT_TRANSACTION_BOUND_AUTHORIZATION_V1_VALID",
        "candidate_introduced_execution_authority": False,
        "live_authorization_issued": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _require_clean_synchronized_main(repo_root: Path) -> str:
    branch = cast(str, _git(repo_root, "branch", "--show-current"))
    if branch != "main":
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_LIVE_ISSUE_REQUIRES_MAIN",
            "live authorization may only be issued from main",
        )
    _git(repo_root, "fetch", "origin", "main")
    head = cast(str, _git(repo_root, "rev-parse", "HEAD"))
    origin = cast(str, _git(repo_root, "rev-parse", "origin/main"))
    if head != origin:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_MAIN_NOT_SYNCHRONIZED",
            "local main must exactly match origin/main before live issuance",
        )
    status = cast(str, _git(repo_root, "status", "--porcelain"))
    if status:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_WORKTREE_NOT_CLEAN",
            "live issuance requires a clean synchronized main worktree",
        )
    return head


def _head_json(repo_root: Path, relative: Path) -> dict[str, object]:
    payload = _head_bytes(repo_root, relative)
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_COMMITTED_JSON_INVALID",
            "committed JSON authority root is invalid",
            relative.as_posix(),
        )
    return cast(dict[str, object], value)


def _build_live_material(repo_root: Path) -> bytes:
    schedule = _head_json(repo_root, PILOT_SCHEDULE_PATH)
    case_rows = schedule.get("cases")
    if not isinstance(case_rows, list) or len(case_rows) != 6:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_MATERIAL_SCHEDULE_INVALID",
            "committed pilot schedule case set is invalid",
        )
    case_ids = []
    for raw in case_rows:
        if not isinstance(raw, dict) or not isinstance(raw.get("episode_id"), str):
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_MATERIAL_SCHEDULE_INVALID",
                "committed pilot case identity is invalid",
            )
        case_ids.append(cast(str, raw["episode_id"]))

    runtime_selection = _head_json(repo_root, RUNTIME_SELECTION_PATH)
    runtime_entries = runtime_selection.get("entries")
    if not isinstance(runtime_entries, list):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_RUNTIME_SELECTION_INVALID",
            "committed final runtime selection is invalid",
        )
    final_runtime_ids = {
        item.get("episode_id")
        for item in runtime_entries
        if isinstance(item, dict) and isinstance(item.get("episode_id"), str)
    }
    if set(case_ids) & final_runtime_ids:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_FINAL_RUNTIME_EPISODE_LEAKAGE",
            "variance-pilot material overlaps final runtime-selected episodes",
        )

    episodes_payload = _head_json(repo_root, ACCEPTED_EPISODES_PATH)
    raw_episodes = episodes_payload.get("episodes")
    if not isinstance(raw_episodes, list):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_MATERIAL_EPISODES_INVALID",
            "committed accepted episode set is invalid",
        )
    episodes: list[dict[str, object]] = []
    required_source_ids: set[str] = set()
    for raw in raw_episodes:
        if not isinstance(raw, dict):
            continue
        episode_id = raw.get("episode_id")
        if episode_id not in case_ids:
            continue
        if raw.get("evaluation_split") != "development":
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_MATERIAL_SPLIT_INVALID",
                "pilot material may contain development episodes only",
            )
        scope = raw.get("source_scope")
        if not isinstance(scope, dict):
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_MATERIAL_EPISODES_INVALID",
                "pilot episode source scope is invalid",
            )
        ids = scope.get("required_source_ids")
        if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_MATERIAL_EPISODES_INVALID",
                "pilot episode source IDs are invalid",
            )
        required_source_ids.update(cast(list[str], ids))
        episodes.append(cast(dict[str, object], raw))
    if len(episodes) != 6:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_MATERIAL_EPISODES_INVALID",
            "pilot material must contain exactly six selected episodes",
        )

    source_manifest = _head_json(repo_root, SOURCE_MANIFEST_PATH)
    raw_artifacts = source_manifest.get("artifacts")
    if not isinstance(raw_artifacts, list):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_SOURCE_MANIFEST_INVALID",
            "committed source manifest artifacts are invalid",
        )
    sources: dict[str, dict[str, object]] = {}
    for raw in raw_artifacts:
        if not isinstance(raw, dict):
            continue
        source_id = raw.get("source_id")
        if source_id not in required_source_ids:
            continue
        path = raw.get("document_path")
        expected_sha = raw.get("sha256")
        expected_bytes = raw.get("byte_count")
        if not (
            isinstance(source_id, str)
            and isinstance(path, str)
            and isinstance(expected_sha, str)
            and isinstance(expected_bytes, int)
        ):
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_SOURCE_MANIFEST_INVALID",
                "required source manifest row is invalid",
            )
        source_bytes = _head_bytes(repo_root, Path(path))
        if _sha256(source_bytes) != expected_sha or len(source_bytes) != expected_bytes:
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_SOURCE_IDENTITY_DRIFT",
                "required source identity drifted",
                path,
            )
        text = source_bytes.decode("utf-8")
        sources[source_id] = {
            "sha256": _sha256(source_bytes),
            "byte_count": len(source_bytes),
            "text": text,
        }
    if set(sources) != required_source_ids:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_SOURCE_SET_INCOMPLETE",
            "transaction-bound pilot material source set is incomplete",
        )

    compiler_spec = _head_json(repo_root, COMPILER_SPEC_PATH)
    material = {
        "schema_version": "1.0.0",
        "material_id": "auragateway-variance-pilot-transaction-bound-material-v1",
        "pilot_schedule": schedule,
        "pilot_schedule_sha256": _sha256(_head_bytes(repo_root, PILOT_SCHEDULE_PATH)),
        "pilot_manifest_sha256": _sha256(_head_bytes(repo_root, PILOT_MANIFEST_PATH)),
        "accepted_episode_set_sha256": _sha256(_head_bytes(repo_root, ACCEPTED_EPISODES_PATH)),
        "source_manifest_sha256": _sha256(_head_bytes(repo_root, SOURCE_MANIFEST_PATH)),
        "compiler_spec_sha256": _sha256(_head_bytes(repo_root, COMPILER_SPEC_PATH)),
        "episodes": episodes,
        "sources": sources,
        "compiler_spec": compiler_spec,
        "customer_data_used": False,
        "held_out_episode_count": 0,
        "final_runtime_selected_episode_count": 0,
    }
    return _canonical_bytes(material)


def _render_wrapper(
    template: str,
    *,
    envelope: bytes,
    r2_runtime: bytes,
    pilot_runtime: bytes,
    material: bytes,
    transaction_id: str,
    issuer_commit: str,
    issuer_sha: str,
    readiness_sha: str,
) -> bytes:
    replacements = {
        "__AUTHORIZATION_B64__": base64.b64encode(envelope).decode("ascii"),
        "__R2_RUNTIME_B64__": base64.b64encode(r2_runtime).decode("ascii"),
        "__PILOT_RUNTIME_B64__": base64.b64encode(pilot_runtime).decode("ascii"),
        "__PILOT_MATERIAL_B64__": base64.b64encode(material).decode("ascii"),
        "__TRANSACTION_ID__": transaction_id,
        "__ISSUER_MERGE_COMMIT__": issuer_commit,
        "__ISSUER_SOURCE_SHA256__": issuer_sha,
        "__R2_RUNTIME_SHA256__": _sha256(r2_runtime),
        "__PILOT_RUNTIME_SHA256__": _sha256(pilot_runtime),
        "__PILOT_MATERIAL_SHA256__": _sha256(material),
        "__READINESS_SHA256__": readiness_sha,
    }
    rendered = template
    for token, value in replacements.items():
        if token not in rendered:
            raise AuthorizationError(
                "VARIANCE_PILOT_TX_AUTH_TEMPLATE_TOKEN_MISSING",
                "wrapper template token is missing",
            )
        rendered = rendered.replace(token, value)
    if "__" in rendered and any(token in rendered for token in replacements):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_TEMPLATE_RENDER_FAILED",
            "wrapper template retained an unresolved required token",
        )
    return rendered.encode("utf-8")


def issue_live(
    repo_root: Path,
    artifact_dir: Path,
    window_minutes: int,
) -> dict[str, object]:
    root = repo_root.resolve()
    if window_minutes < 1 or window_minutes > MAX_WINDOW_MINUTES:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_WINDOW_INVALID",
            "authorization window is outside permitted bounds",
        )
    issuer_commit = _require_clean_synchronized_main(root)
    _validate_r2_identity(root, committed=True)

    issuer_source = _head_bytes(root, SOURCE_PATH)
    pilot_runtime = _head_bytes(root, RUNTIME_PAYLOAD_PATH)
    r2_runtime = _head_bytes(root, R2_RUNTIME_LIBRARY_PATH)
    template_bytes = _head_bytes(root, WRAPPER_TEMPLATE_PATH)
    readiness_bytes = _head_bytes(root, READINESS_PATH)
    acceptance_bytes = _head_bytes(root, CURRENT_ACCEPTANCE_PATH)
    material = _build_live_material(root)

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=window_minutes)
    challenge = _sha256(
        secrets.token_bytes(32)
        + issuer_commit.encode("ascii")
        + issued_at.isoformat().encode("ascii")
        + _sha256(readiness_bytes).encode("ascii")
    )
    print("RETYPE_DYNAMIC_SHA256_CHALLENGE=" + challenge)
    confirmed = input("Retype the exact challenge to issue live authority: ").strip()
    if confirmed != challenge:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_OPERATOR_CONFIRMATION_FAILED",
            "dynamic SHA-256 challenge confirmation failed",
        )

    authorization = LiveAuthorization(
        authorization_id="variance-pilot-tx-" + secrets.token_hex(16),
        issued_at=issued_at,
        expires_at=expires_at,
        issuer_merge_commit=issuer_commit,
        issuer_source_sha256=_sha256(issuer_source),
        pilot_runtime_payload_sha256=_sha256(pilot_runtime),
        pilot_material_sha256=_sha256(material),
        runtime_launcher_readiness_sha256=_sha256(readiness_bytes),
        current_p5_p6_acceptance_sha256=_sha256(acceptance_bytes),
    )
    authorization_bytes = _canonical_bytes(authorization)
    transaction_id = _sha256(authorization_bytes)
    envelope = _canonical_bytes(
        {
            "transaction_id": transaction_id,
            "authorization": authorization.model_dump(mode="json"),
        }
    )

    wrapper = _render_wrapper(
        template_bytes.decode("utf-8"),
        envelope=envelope,
        r2_runtime=r2_runtime,
        pilot_runtime=pilot_runtime,
        material=material,
        transaction_id=transaction_id,
        issuer_commit=issuer_commit,
        issuer_sha=_sha256(issuer_source),
        readiness_sha=_sha256(readiness_bytes),
    )
    artifact_dir.mkdir(parents=True, exist_ok=True)
    executable_path = artifact_dir / f"{NOTEBOOK_NAME}.py"
    notebook_path = artifact_dir / f"{NOTEBOOK_NAME}.ipynb"
    executable_path.write_bytes(wrapper)
    notebook = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": wrapper.decode("utf-8").splitlines(keepends=True),
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    notebook_bytes = _artifact_bytes(notebook)
    notebook_path.write_bytes(notebook_bytes)

    _write_json(
        root / LIVE_AUTHORIZATION_PATH,
        {
            "transaction_id": transaction_id,
            "authorization": authorization.model_dump(mode="json"),
        },
    )
    manifest = {
        "schema_version": "1.0.0",
        "status": "TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        "transaction_id": transaction_id,
        "issuer_merge_commit": issuer_commit,
        "issuer_source_sha256": _sha256(issuer_source),
        "r2_runtime_library_sha256": _sha256(r2_runtime),
        "pilot_runtime_payload_sha256": _sha256(pilot_runtime),
        "pilot_material_sha256": _sha256(material),
        "executable_sha256": _sha256(wrapper),
        "notebook_container_sha256": _sha256(notebook_bytes),
        "notebook_container_is_semantic_payload_identity": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "permitted_kaggle_input_roles": [
            "durable_runtime",
            "model_snapshot",
        ],
        "platform_observation_required_before_save_and_run_all": True,
        "platform_observation_persisted": False,
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "single_use_governance": True,
        "runtime_anti_replay_established": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }
    _write_json(root / LIVE_MANIFEST_PATH, manifest)
    return manifest


def record_platform_observation(
    repo_root: Path,
    transaction_id: str,
    observed_at: datetime,
) -> dict[str, object]:
    root = repo_root.resolve()
    live = _read_json(root / LIVE_AUTHORIZATION_PATH)
    manifest = _read_json(root / LIVE_MANIFEST_PATH)
    if live.get("transaction_id") != transaction_id:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_TRANSACTION_MISMATCH",
            "live authorization transaction identity mismatch",
        )
    if manifest.get("transaction_id") != transaction_id:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_TRANSACTION_MISMATCH",
            "live artifact manifest transaction identity mismatch",
        )
    receipt = {
        "schema_version": "1.0.0",
        "control_id": "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL",
        "transaction_id": transaction_id,
        "authorization_sha256": _sha_file(root / LIVE_AUTHORIZATION_PATH),
        "manifest_sha256": _sha_file(root / LIVE_MANIFEST_PATH),
        "platform_observed_at": observed_at.astimezone(UTC).isoformat(),
        "accelerator": "T4_X2",
        "allocated_gpu_count": 2,
        "internet_enabled": False,
        "wheelhouse_input_count": 1,
        "model_snapshot_input_count": 1,
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "persisted_before_save_and_run_all": True,
        "receipt_runtime_input": False,
    }
    _write_json(root / PLATFORM_OBSERVATION_PATH, receipt)
    return {
        "status": "VARIANCE_PILOT_PLATFORM_OBSERVATION_PERSISTED",
        "transaction_id": transaction_id,
        "next_gate": NEXT_GATE_AFTER_OBSERVATION,
    }


def terminalize(
    repo_root: Path,
    transaction_id: str,
    outcome: str,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    terminal_log_sha256: str | None,
) -> dict[str, object]:
    root = repo_root.resolve()
    live = _read_json(root / LIVE_AUTHORIZATION_PATH)
    if live.get("transaction_id") != transaction_id:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_TRANSACTION_MISMATCH",
            "terminalization transaction identity mismatch",
        )
    permitted = {"PASSED", "FAILED", "INTERRUPTED", "AMBIGUOUS"}
    if outcome not in permitted:
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_TERMINAL_OUTCOME_INVALID",
            "terminal execution outcome is invalid",
        )
    if outcome == "PASSED" and (
        saved_version_id is None or evidence_zip_sha256 is None or terminal_log_sha256 is None
    ):
        raise AuthorizationError(
            "VARIANCE_PILOT_TX_AUTH_PASS_EVIDENCE_REQUIRED",
            "PASSED terminalization requires saved version and evidence identities",
        )
    record = {
        "schema_version": "1.0.0",
        "transaction_id": transaction_id,
        "authorization_sha256": _sha_file(root / LIVE_AUTHORIZATION_PATH),
        "disposition": "CONSUMED",
        "execution_attempted": True,
        "execution_outcome": outcome,
        "terminalized_at": datetime.now(UTC).isoformat(),
        "saved_version_id": saved_version_id,
        "evidence_zip_sha256": evidence_zip_sha256,
        "terminal_log_sha256": terminal_log_sha256,
        "authorization_reusable": False,
        "pilot_execution_authorized": False,
        "pilot_repository_acceptance_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_TERMINAL,
    }
    _write_json(root / TERMINAL_PATH, record)
    return record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measured-abc-variance-pilot-transaction-bound-authorization-v1"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for command in ("generate", "validate-implementation"):
        item = sub.add_parser(command)
        item.add_argument("--repo-root", type=Path, default=Path("."))

    issue = sub.add_parser("issue-live")
    issue.add_argument("--repo-root", type=Path, default=Path("."))
    issue.add_argument("--artifact-dir", type=Path, required=True)
    issue.add_argument(
        "--window-minutes",
        type=int,
        default=DEFAULT_WINDOW_MINUTES,
    )

    observe = sub.add_parser("record-platform-observation")
    observe.add_argument("--repo-root", type=Path, default=Path("."))
    observe.add_argument("--transaction-id", required=True)
    observe.add_argument("--observed-at", required=True)

    terminal = sub.add_parser("terminalize")
    terminal.add_argument("--repo-root", type=Path, default=Path("."))
    terminal.add_argument("--transaction-id", required=True)
    terminal.add_argument("--outcome", required=True)
    terminal.add_argument("--saved-version-id", type=int)
    terminal.add_argument("--evidence-zip-sha256")
    terminal.add_argument("--terminal-log-sha256")
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        root = args.repo_root.resolve()
        if args.command == "generate":
            result = generate(root)
        elif args.command == "validate-implementation":
            result = validate_implementation(root)
        elif args.command == "issue-live":
            result = issue_live(
                root,
                args.artifact_dir.resolve(),
                args.window_minutes,
            )
        elif args.command == "record-platform-observation":
            observed = datetime.fromisoformat(args.observed_at)
            if observed.tzinfo is None or observed.utcoffset() is None:
                raise AuthorizationError(
                    "VARIANCE_PILOT_TX_AUTH_OBSERVATION_TIME_INVALID",
                    "platform observation time must be timezone-aware",
                )
            result = record_platform_observation(
                root,
                args.transaction_id,
                observed,
            )
        else:
            result = terminalize(
                root,
                args.transaction_id,
                args.outcome,
                args.saved_version_id,
                args.evidence_zip_sha256,
                args.terminal_log_sha256,
            )
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except AuthorizationError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

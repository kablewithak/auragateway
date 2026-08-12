"""Reconcile P4/P5 differential execution with a terminalization provenance gap."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "14c4249a5663cf7f94674fab924d5fc334c835f44836347ce13634eb505cc22e"
SAVED_VERSION_ID: Final = 341807938
BASE_COMMIT: Final = "5fa152542cff2a1bf47602451802f239fe754b02"
EXPECTED_EVIDENCE_SHA256: Final = "128d9e0d76c1d55608b862bb4604ed654667cbeda821c8de8ec103445803cd3c"
EXPECTED_NOTEBOOK_SHA256: Final = "a3ec983ac7d49b5ecbb15d0ca2921710cc60d25515fd7ad8cb0cc2e8fab65685"
EXPECTED_TERMINAL_LOG_SHA256: Final = (
    "9ea37ed7747f756d48a957afcef91149c834b8d7c080990232f93ebc415eb421"
)
EXPECTED_RECONCILIATION_INPUT_SHA256: Final = (
    "10433e527f0901299b4a94cfd915e1f8b257826b569eb797d3a70bf00dad0d2f"
)
EXPECTED_RUNTIME_SHA256: Final = "4711f94031bc65ae159dab14412d99cfbd9ecee01b5a2d7d2fd7a2c2b09d7db7"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_differential_terminalization_reconciliation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_composition_differential_terminalization_reconciliation_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_P5_Composition_Differential_Terminalization_Reconciliation_V1.md"
)
VAULT_ROOT: Final = Path("evidence_vault/local_abc/p4-p5-composition-differential-v1")
EVIDENCE_ZIP_PATH: Final = VAULT_ROOT / "ag-p4-p5-composition-differential-evidence-v1.zip"
EXECUTED_NOTEBOOK_PATH: Final = VAULT_ROOT / "ag-p4-p5-composition-differential-v1.ipynb"
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "ag-p4-p5-composition-differential-v1.log"
RECONCILIATION_INPUT_PATH: Final = (
    VAULT_ROOT
    / "auragateway-p4-p5-composition-differential-terminalization-reconciliation-input-v1.zip"
)
PRESERVED_AUTHORIZATION_PATH: Final = VAULT_ROOT / "live_authorization_v1.json"
PRESERVED_MANIFEST_PATH: Final = VAULT_ROOT / "live_execution_artifact_manifest_v1.json"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_differential_terminalization_reconciliation_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_differential_terminalization_reconciliation_v1_review.json"
)

NEXT_GATE: Final = "DESIGN_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"


class ReconciliationError(RuntimeError):
    """Fail-closed reconciliation error."""

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


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class ReconciliationInput(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal[
        "auragateway-p4-p5-composition-differential-terminalization-reconciliation-input-v1"
    ]
    status: Literal["OBSERVED_EXECUTION_TERMINALIZATION_BLOCKED"]
    transaction_id: Literal["14c4249a5663cf7f94674fab924d5fc334c835f44836347ce13634eb505cc22e"]
    saved_version_id: Literal[341807938]
    kaggle_script_version_id: Literal[341807938]
    execution_attempted: Literal[True]
    diagnostic_execution_status: Literal["DIAGNOSTIC_COMPLETE"]
    diagnostic_decision: Literal["COMPOSITION_REGRESSION_SUPPORTED"]
    scheduled_request_count: Literal[6]
    completed_request_count: Literal[6]
    case_a_exact_successes: Literal[3]
    case_b_exact_successes: Literal[0]
    platform_observation_performed: Literal[True]
    platform_observation_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    observed_accelerator: Literal["T4_X2"]
    observed_gpu_count: Literal[2]
    observed_internet_enabled: Literal[False]
    platform_observed_at: None
    platform_observation_timestamp_recoverable: Literal[False]
    terminal_receipt_created: Literal[False]
    terminalization_blocker: Literal["EXACT_PLATFORM_OBSERVATION_TIMESTAMP_NOT_RECOVERABLE"]
    terminalization_timestamp_fabricated: Literal[False]
    authorization_reuse_permitted: Literal[False]
    rerun_permitted: Literal[False]
    case_c_authorized: Literal[False]
    runtime_remediation_authorized: Literal[False]
    diagnostic_result_invalidated: Literal[False]
    repository_acceptance_claimed: Literal[False]
    evidence_zip_sha256: Literal["128d9e0d76c1d55608b862bb4604ed654667cbeda821c8de8ec103445803cd3c"]
    terminal_log_sha256: Literal["9ea37ed7747f756d48a957afcef91149c834b8d7c080990232f93ebc415eb421"]
    executed_notebook_sha256: Literal[
        "a3ec983ac7d49b5ecbb15d0ca2921710cc60d25515fd7ad8cb0cc2e8fab65685"
    ]
    proposed_next_gate: Literal["PRESERVE_AND_RECONCILE_P4_P5_TERMINALIZATION_PROVENANCE_V1"]
    captured_at: str = Field(min_length=1)
    kaggle_notebook: Literal["ag-p4-p5-composition-differential-v1"]


class ReconciliationRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal[
        "auragateway-p4-p5-composition-differential-terminalization-reconciliation-v1"
    ]
    status: Literal["RECONCILED_EXECUTED_SINGLE_USE_AUTHORITY_WITH_TERMINALIZATION_PROVENANCE_GAP"]
    transaction_id: Literal["14c4249a5663cf7f94674fab924d5fc334c835f44836347ce13634eb505cc22e"]
    saved_version_id: Literal[341807938]
    kaggle_script_version_id: Literal[341807938]
    diagnostic_execution_status: Literal["DIAGNOSTIC_COMPLETE"]
    diagnostic_decision: Literal["COMPOSITION_REGRESSION_SUPPORTED"]
    variable_under_test: Literal["MESSAGE_COMPOSITION_ONLY"]
    case_a_exact_successes: Literal[3]
    case_b_exact_successes: Literal[0]
    case_a_valid_json_count: Literal[3]
    case_b_valid_json_count: Literal[0]
    controlled_differential_evidence_established: Literal[True]
    scientific_result_valid: Literal[True]
    diagnostic_result_invalidated: Literal[False]
    execution_attempted: Literal[True]
    authorization_single_use: Literal[True]
    authorization_reuse_permitted: Literal[False]
    rerun_permitted: Literal[False]
    original_issuer_lifecycle_observed: Literal["ISSUED"]
    original_issuer_terminal_receipt_created: Literal[False]
    original_issuer_terminalization_completed: Literal[False]
    original_issuer_lifecycle_closed: Literal[False]
    operational_authority_closed_by_reconciliation: Literal[True]
    terminalization_blocker: Literal["EXACT_PLATFORM_OBSERVATION_TIMESTAMP_NOT_RECOVERABLE"]
    platform_observation_performed: Literal[True]
    platform_observation_source: Literal["KAGGLE_NOTEBOOK_SETTINGS_UI"]
    observed_accelerator: Literal["T4_X2"]
    observed_gpu_count: Literal[2]
    observed_internet_enabled: Literal[False]
    platform_observed_at: None
    platform_observation_timestamp_recoverable: Literal[False]
    terminalization_timestamp_fabricated: Literal[False]
    repository_evidence_disposition: Literal[
        "ACCEPTED_DIAGNOSTIC_EVIDENCE_WITH_TERMINALIZATION_PROVENANCE_GAP"
    ]
    runtime_source_identity_verified: Literal[True]
    runtime_source_metadata_debt_present: Literal[True]
    stale_runtime_notebook_name: Literal["ag-p5-p6-transaction-bound-v1"]
    stale_runtime_source_main_commit: Literal["4afdcf9d840bc90ceb34af8dae098998f78de572"]
    future_platform_observation_control: Literal[
        "PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"
    ]
    case_c_authorized: Literal[False]
    runtime_remediation_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...]
    next_gate: Literal["DESIGN_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"]

    @model_validator(mode="after")
    def validate_boundaries(self) -> Self:
        if len(self.authorities) != 7:
            raise ValueError("reconciliation authority count drifted")
        if len(self.non_claims) < 8:
            raise ValueError("reconciliation non-claim boundary is incomplete")
        return self


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_ARTIFACT_MISSING",
            "required reconciliation artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _require_hash(root: Path, relative: Path, expected: str) -> Path:
    path = _require_file(root, relative)
    if _sha256_file(path) != expected:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_IDENTITY_DRIFT",
            "reconciliation artifact byte identity drifted",
            relative.as_posix(),
        )
    return path


def _load_json_file(root: Path, relative: Path) -> dict[str, object]:
    path = _require_file(root, relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_JSON_INVALID",
            "reconciliation JSON is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_JSON_INVALID",
            "reconciliation JSON root must be an object",
            relative.as_posix(),
        )
    return cast(dict[str, object], payload)


def _zip_member_bytes(path: Path, member: str) -> bytes:
    try:
        with zipfile.ZipFile(path) as archive:
            matches = tuple(info for info in archive.infolist() if info.filename == member)
            if len(matches) != 1 or matches[0].is_dir():
                raise ReconciliationError(
                    "P4_P5_TERMINALIZATION_RECONCILIATION_ZIP_MEMBER_INVALID",
                    "required ZIP member cardinality drifted",
                    member,
                )
            return archive.read(matches[0])
    except (OSError, zipfile.BadZipFile) as error:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_ZIP_INVALID",
            "required reconciliation ZIP is invalid",
            path.name,
        ) from error


def _zip_json(path: Path, member: str) -> dict[str, object]:
    try:
        payload = json.loads(_zip_member_bytes(path, member).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_ZIP_JSON_INVALID",
            "required ZIP JSON member is invalid",
            member,
        ) from error
    if not isinstance(payload, dict):
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_ZIP_JSON_INVALID",
            "required ZIP JSON member root must be an object",
            member,
        )
    return cast(dict[str, object], payload)


def _receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = _require_file(root, relative)
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _canonical_json_bytes(payload: BaseModel | dict[str, object]) -> bytes:
    value: object = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_evidence_bundle(root: Path) -> tuple[dict[str, object], dict[str, object]]:
    evidence_path = _require_hash(root, EVIDENCE_ZIP_PATH, EXPECTED_EVIDENCE_SHA256)
    decision = _zip_json(
        evidence_path,
        "p4_p5_composition_differential_decision_v1.json",
    )
    summary = _zip_json(
        evidence_path,
        "p4_p5_composition_differential_summary_v1.json",
    )
    manifest = _zip_json(evidence_path, "bundle_manifest_v1.json")
    runtime_identity = _zip_json(evidence_path, "runtime_source_identity_report_v1.json")

    required_decision = {
        "decision_state": "COMPOSITION_REGRESSION_SUPPORTED",
        "variable_under_test": "MESSAGE_COMPOSITION_ONLY",
        "case_a_exact_object_count": 3,
        "case_b_exact_object_count": 0,
        "case_a_valid_json_count": 3,
        "case_b_valid_json_count": 0,
        "raw_output_retained": False,
        "raw_prompt_retained": False,
    }
    for key, expected in required_decision.items():
        if decision.get(key) != expected:
            raise ReconciliationError(
                "P4_P5_TERMINALIZATION_RECONCILIATION_DECISION_DRIFT",
                f"diagnostic decision field drifted: {key}",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

    if summary.get("status") != "DIAGNOSTIC_COMPLETE":
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_SUMMARY_DRIFT",
            "diagnostic execution status drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if summary.get("completed_request_count") != 6:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_SUMMARY_DRIFT",
            "completed request count drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if summary.get("request_order") != ["A", "B", "B", "A", "A", "B"]:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_SUMMARY_DRIFT",
            "request order drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    counters = summary.get("counters")
    if not isinstance(counters, dict):
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_SUMMARY_DRIFT",
            "action counters are missing",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    required_counters = {
        "model_requests": 6,
        "model_loads": 1,
        "worker_starts": 1,
        "hidden_retries": 0,
        "network_requests": 0,
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
    }
    for key, expected in required_counters.items():
        if counters.get(key) != expected:
            raise ReconciliationError(
                "P4_P5_TERMINALIZATION_RECONCILIATION_BUDGET_DRIFT",
                f"diagnostic action counter drifted: {key}",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

    if manifest.get("member_count") != 14:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_MANIFEST_DRIFT",
            "evidence bundle member count drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if manifest.get("raw_model_output_included") is not False:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_PRIVACY_DRIFT",
            "raw model output retention boundary drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if manifest.get("raw_prompt_included") is not False:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_PRIVACY_DRIFT",
            "raw prompt retention boundary drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    if runtime_identity.get("executed_runtime_script_sha256") != EXPECTED_RUNTIME_SHA256:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_RUNTIME_IDENTITY_DRIFT",
            "executed runtime identity drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if runtime_identity.get("wrapper_hash_verification_passed") is not True:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_RUNTIME_IDENTITY_DRIFT",
            "runtime wrapper verification did not pass",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if runtime_identity.get("notebook_name") != "ag-p5-p6-transaction-bound-v1":
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_METADATA_DEBT_DRIFT",
            "known stale notebook metadata changed",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if runtime_identity.get("source_main_commit") != ("4afdcf9d840bc90ceb34af8dae098998f78de572"):
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_METADATA_DEBT_DRIFT",
            "known stale source-main metadata changed",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    return decision, summary


def _validate_reconciliation_input(root: Path) -> ReconciliationInput:
    path = _require_hash(
        root,
        RECONCILIATION_INPUT_PATH,
        EXPECTED_RECONCILIATION_INPUT_SHA256,
    )
    payload = _zip_json(
        path,
        "reconciliation/terminalization_reconciliation_input_v1.json",
    )
    reconciliation = ReconciliationInput.model_validate(payload)

    preserved_authorization = _require_file(root, PRESERVED_AUTHORIZATION_PATH).read_bytes()
    preserved_manifest = _require_file(root, PRESERVED_MANIFEST_PATH).read_bytes()

    archived_authorization = _zip_member_bytes(
        path,
        "benchmarks/local_abc/"
        "auragateway_p4_p5_composition_differential_"
        "execution_authorization_v1_live.json",
    )
    archived_manifest = _zip_member_bytes(
        path,
        "benchmarks/local_abc/"
        "auragateway_p4_p5_composition_differential_"
        "execution_artifact_v1_live_manifest.json",
    )
    if preserved_authorization != archived_authorization:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_AUTHORIZATION_DRIFT",
            "preserved live authorization differs from captured input",
            PRESERVED_AUTHORIZATION_PATH.as_posix(),
        )
    if preserved_manifest != archived_manifest:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_MANIFEST_DRIFT",
            "preserved live manifest differs from captured input",
            PRESERVED_MANIFEST_PATH.as_posix(),
        )

    authorization = _load_json_file(root, PRESERVED_AUTHORIZATION_PATH)
    body = authorization.get("authorization")
    if not isinstance(body, dict):
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_AUTHORIZATION_INVALID",
            "preserved authorization body is missing",
            PRESERVED_AUTHORIZATION_PATH.as_posix(),
        )
    required_authorization = {
        "lifecycle": "ISSUED",
        "decision": "AUTHORIZED",
        "runtime_execution_authorized": True,
        "single_use": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "case_c_authorized": False,
        "runtime_remediation_authorized": False,
    }
    for key, expected in required_authorization.items():
        if body.get(key) != expected:
            raise ReconciliationError(
                "P4_P5_TERMINALIZATION_RECONCILIATION_AUTHORIZATION_DRIFT",
                f"preserved authorization field drifted: {key}",
                PRESERVED_AUTHORIZATION_PATH.as_posix(),
            )
    if authorization.get("transaction_id") != TRANSACTION_ID:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_TRANSACTION_DRIFT",
            "preserved authorization transaction drifted",
            PRESERVED_AUTHORIZATION_PATH.as_posix(),
        )

    manifest = _load_json_file(root, PRESERVED_MANIFEST_PATH)
    if manifest.get("transaction_id") != TRANSACTION_ID:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_TRANSACTION_DRIFT",
            "preserved manifest transaction drifted",
            PRESERVED_MANIFEST_PATH.as_posix(),
        )
    if manifest.get("single_use_governance") is not True:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_MANIFEST_DRIFT",
            "single-use manifest governance drifted",
            PRESERVED_MANIFEST_PATH.as_posix(),
        )

    return reconciliation


def build_record(repo_root: Path) -> ReconciliationRecord:
    root = repo_root.resolve()

    _require_hash(root, EXECUTED_NOTEBOOK_PATH, EXPECTED_NOTEBOOK_SHA256)
    terminal_log = _require_hash(root, TERMINAL_LOG_PATH, EXPECTED_TERMINAL_LOG_SHA256)
    _validate_evidence_bundle(root)
    _validate_reconciliation_input(root)

    log_text = terminal_log.read_text(encoding="utf-8", errors="replace")
    required_log_markers = (
        '"decision_state":"COMPOSITION_REGRESSION_SUPPORTED"',
        '"completed_request_count":6',
        f'"transaction_id":"{TRANSACTION_ID}"',
    )
    for marker in required_log_markers:
        if marker not in log_text:
            raise ReconciliationError(
                "P4_P5_TERMINALIZATION_RECONCILIATION_LOG_DRIFT",
                "terminal log no longer contains required governed result marker",
                TERMINAL_LOG_PATH.as_posix(),
            )

    authorities = (
        _receipt(root, EVIDENCE_ZIP_PATH),
        _receipt(root, EXECUTED_NOTEBOOK_PATH),
        _receipt(root, TERMINAL_LOG_PATH),
        _receipt(root, RECONCILIATION_INPUT_PATH),
        _receipt(root, PRESERVED_AUTHORIZATION_PATH),
        _receipt(root, PRESERVED_MANIFEST_PATH),
        _receipt(root, REPORT_PATH),
    )

    return ReconciliationRecord(
        schema_version="1.0.0",
        record_id=("auragateway-p4-p5-composition-differential-terminalization-reconciliation-v1"),
        status=("RECONCILED_EXECUTED_SINGLE_USE_AUTHORITY_WITH_TERMINALIZATION_PROVENANCE_GAP"),
        transaction_id=TRANSACTION_ID,
        saved_version_id=SAVED_VERSION_ID,
        kaggle_script_version_id=SAVED_VERSION_ID,
        diagnostic_execution_status="DIAGNOSTIC_COMPLETE",
        diagnostic_decision="COMPOSITION_REGRESSION_SUPPORTED",
        variable_under_test="MESSAGE_COMPOSITION_ONLY",
        case_a_exact_successes=3,
        case_b_exact_successes=0,
        case_a_valid_json_count=3,
        case_b_valid_json_count=0,
        controlled_differential_evidence_established=True,
        scientific_result_valid=True,
        diagnostic_result_invalidated=False,
        execution_attempted=True,
        authorization_single_use=True,
        authorization_reuse_permitted=False,
        rerun_permitted=False,
        original_issuer_lifecycle_observed="ISSUED",
        original_issuer_terminal_receipt_created=False,
        original_issuer_terminalization_completed=False,
        original_issuer_lifecycle_closed=False,
        operational_authority_closed_by_reconciliation=True,
        terminalization_blocker="EXACT_PLATFORM_OBSERVATION_TIMESTAMP_NOT_RECOVERABLE",
        platform_observation_performed=True,
        platform_observation_source="KAGGLE_NOTEBOOK_SETTINGS_UI",
        observed_accelerator="T4_X2",
        observed_gpu_count=2,
        observed_internet_enabled=False,
        platform_observed_at=None,
        platform_observation_timestamp_recoverable=False,
        terminalization_timestamp_fabricated=False,
        repository_evidence_disposition=(
            "ACCEPTED_DIAGNOSTIC_EVIDENCE_WITH_TERMINALIZATION_PROVENANCE_GAP"
        ),
        runtime_source_identity_verified=True,
        runtime_source_metadata_debt_present=True,
        stale_runtime_notebook_name="ag-p5-p6-transaction-bound-v1",
        stale_runtime_source_main_commit="4afdcf9d840bc90ceb34af8dae098998f78de572",
        future_platform_observation_control=("PERSIST_DURABLE_OBSERVATION_BEFORE_SAVE_AND_RUN_ALL"),
        case_c_authorized=False,
        runtime_remediation_authorized=False,
        new_execution_authorized=False,
        authorities=authorities,
        non_claims=(
            "The original issuer terminal receipt was not created.",
            "The missing platform observation timestamp is not reconstructed or fabricated.",
            "The original issuer lifecycle is not claimed closed by its terminalize command.",
            "No second execution or unchanged replay is authorized.",
            "Case C is not authorized by this reconciliation.",
            "Runtime remediation is not authorized by this reconciliation.",
            "The result does not establish generic Qwen unreliability.",
            (
                "The result is scoped to the frozen runtime, model, "
                "and message-composition differential."
            ),
            "Known stale runtime-source metadata does not replace executed runtime byte identity.",
        ),
        next_gate=NEXT_GATE,
    )


def expected_outputs(repo_root: Path) -> tuple[bytes, bytes]:
    root = repo_root.resolve()
    record = build_record(root)
    record_bytes = _canonical_json_bytes(record)
    source_receipt = _receipt(root, SOURCE_PATH)
    test_receipt = _receipt(root, TEST_PATH)
    report_receipt = _receipt(root, REPORT_PATH)

    review: dict[str, object] = {
        "schema_version": "1.0.0",
        "review_id": (
            "auragateway-p4-p5-composition-differential-terminalization-reconciliation-v1-review"
        ),
        "decision": "APPROVED_RECONCILIATION_WITH_EXPLICIT_PROVENANCE_GAP",
        "base_commit": BASE_COMMIT,
        "transaction_id": TRANSACTION_ID,
        "saved_version_id": SAVED_VERSION_ID,
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "source": source_receipt.model_dump(mode="json"),
        "tests": test_receipt.model_dump(mode="json"),
        "report": report_receipt.model_dump(mode="json"),
        "diagnostic_decision": "COMPOSITION_REGRESSION_SUPPORTED",
        "case_a_exact_successes": 3,
        "case_b_exact_successes": 0,
        "platform_observation_timestamp_recoverable": False,
        "terminalization_timestamp_fabricated": False,
        "authorization_reuse_permitted": False,
        "new_execution_authorized": False,
        "runtime_remediation_authorized": False,
        "next_gate": NEXT_GATE,
    }
    return record_bytes, _canonical_json_bytes(review)


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record_bytes, review_bytes = expected_outputs(root)
    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)
    review_path.write_bytes(review_bytes)
    return {
        "status": "P4_P5_TERMINALIZATION_RECONCILIATION_GENERATED",
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "review_sha256": hashlib.sha256(review_bytes).hexdigest(),
        "authorization_reuse_permitted": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_record, expected_review = expected_outputs(root)
    record_path = _require_file(root, RECORD_PATH)
    review_path = _require_file(root, REVIEW_PATH)
    if record_path.read_bytes() != expected_record:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_RECORD_DRIFT",
            "generated reconciliation record drifted",
            RECORD_PATH.as_posix(),
        )
    if review_path.read_bytes() != expected_review:
        raise ReconciliationError(
            "P4_P5_TERMINALIZATION_RECONCILIATION_REVIEW_DRIFT",
            "generated reconciliation review drifted",
            REVIEW_PATH.as_posix(),
        )
    ReconciliationRecord.model_validate(json.loads(record_path.read_text(encoding="utf-8")))
    return {
        "status": "P4_P5_TERMINALIZATION_RECONCILIATION_VALID",
        "record_sha256": _sha256_file(record_path),
        "review_sha256": _sha256_file(review_path),
        "diagnostic_decision": "COMPOSITION_REGRESSION_SUPPORTED",
        "authorization_reuse_permitted": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = Path(args.repo_root)
    try:
        result: dict[str, object] | None = None
        if args.command == "generate":
            result = generate(root)
        if args.command == "validate":
            result = validate(root)
        if result is None:
            raise ReconciliationError(
                "P4_P5_TERMINALIZATION_RECONCILIATION_COMMAND_INVALID",
                "reconciliation command was not handled",
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
    except (ReconciliationError, ValidationError) as error:
        if isinstance(error, ReconciliationError):
            payload = error.envelope()
        if isinstance(error, ValidationError):
            payload = {
                "error_code": "P4_P5_TERMINALIZATION_RECONCILIATION_SCHEMA_INVALID",
                "safe_message": "reconciliation schema validation failed",
                "path": None,
            }
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

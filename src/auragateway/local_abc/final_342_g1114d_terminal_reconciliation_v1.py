"""Reconcile the G11.14D Final-342 terminal-classification conflict."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "16136113b163494ddd366e33a4a7553eafef9c42bd7c57e4e2f3be651fb1c8ab"
SAVED_VERSION_ID: Final = 346383612

TERMINAL_RECEIPT_SHA256: Final = "0db7fd65c153439bc286c074436366c0a785e7d6fb95611a7501c6f1ef91f39e"
LIVE_AUTHORIZATION_SHA256: Final = (
    "2e0b28ec3d2d0e539ca7fd6bf86fce7fb0fe3c596cf702c95669956cd51a3284"
)
LIVE_MANIFEST_SHA256: Final = "33807408204960a6dd51bd2fae6a2b607d983c18244c4b2cec71b71a836d1f74"
PLATFORM_OBSERVATION_SHA256: Final = (
    "d93b453900cc7aa084644ec9ed19c923c98b2b36de769e05df1ff138f213e7f6"
)
EVIDENCE_ZIP_SHA256: Final = "4a218279024b6413b4ddba40cf8f647176360af75381478d26aed6bded29fd57"
TERMINAL_LOG_SHA256: Final = "a772c86f207701f0da9b3e07bc3735f13259bc617e060ef4484c6d054b460211"
SUCCESSOR_QUALIFICATION_SHA256: Final = (
    "5a5690c2240200948d98b37a7be60805bb4ddbe33314805d0febc76e7e965023"
)

TERMINAL_RECEIPT_BYTES: Final = 670
LIVE_AUTHORIZATION_BYTES: Final = 1943
LIVE_MANIFEST_BYTES: Final = 1589
PLATFORM_OBSERVATION_BYTES: Final = 462
EVIDENCE_ZIP_BYTES: Final = 306544
TERMINAL_LOG_BYTES: Final = 2194

VAULT_ROOT: Final = Path("evidence_vault/local_abc/final-342-g1114d-terminal-reconciliation-v1")

TERMINAL_PATH: Final = VAULT_ROOT / "lifecycle/authorization_terminal_v1-346383612.json"
LIVE_AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/live_authorization_v1-346383612.json"
LIVE_MANIFEST_PATH: Final = VAULT_ROOT / "lifecycle/live_manifest_v1-346383612.json"
PLATFORM_OBSERVATION_PATH: Final = VAULT_ROOT / "lifecycle/platform_observation_v1-346383612.json"
EVIDENCE_ZIP_PATH: Final = VAULT_ROOT / "runtime/final_342_measured_evidence_v1-346383612.zip"
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "runtime/kaggle_terminal_v1-346383612.log"

QUALIFICATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_single_use_live_issuer_qualification_v1.json"
)
REPAIR_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/final_342_transaction_bound_live_execution_v1.py.tmpl"
)
REPAIR_TEST_PATH: Final = Path("tests/unit/local_abc/test_final_342_single_use_live_issuer_v1.py")
P5_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)
PRODUCER_PATH: Final = Path("src/auragateway/local_abc/final_342_execution_producer_v1.py")

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/final_342_g1114d_terminal_reconciliation_v1.py"
)
TEST_PATH: Final = Path("tests/unit/local_abc/test_final_342_g1114d_terminal_reconciliation_v1.py")

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_g1114d_terminal_reconciliation_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_final_342_g1114d_terminal_reconciliation_v1_review.json"
)

NEXT_GATE: Final = "VALIDATE_G1114D_FULL_REPAIR_AND_RECONCILIATION_PACKAGE"


class ReconciliationError(RuntimeError):
    """Fail-closed G11.14D reconciliation error."""

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


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError(
            "FINAL_342_G1114D_RECONCILIATION_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExternalModel(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class ArtifactReceipt(FrozenModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class HistoricalTerminalReceipt(ExternalModel):
    transaction_id: Literal["16136113b163494ddd366e33a4a7553eafef9c42bd7c57e4e2f3be651fb1c8ab"]
    disposition: Literal["CONSUMED"]
    execution_attempted: Literal[True]
    execution_outcome: Literal["PASSED"]
    saved_version_id: Literal[346383612]
    authorization_reusable: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]


class EvidenceSummary(FrozenModel):
    primary_failure_present: Literal[False]
    secondary_failure_count: Literal[1]
    secondary_failure_phase: Literal["teardown"]
    secondary_failure_code: Literal["FINAL_342_TEARDOWN_FAILURE"]
    secondary_failure_safe_message: Literal["ValidationError"]
    worker_teardown_record_count: Literal[0]
    scratch_cleanup_status: Literal["PASSED"]
    scratch_absent: Literal[True]
    scheduled_request_count: Literal[1368]
    attempted_request_count: Literal[1368]
    http_completed_request_count: Literal[1368]
    admitted_request_count: Literal[1368]
    committed_request_count: Literal[1368]
    request_reconciliation_passed: Literal[True]
    scheduled_trajectory_count: Literal[342]
    trajectory_terminal_count: Literal[342]
    completed_trajectory_count: Literal[342]
    failed_trajectory_count: Literal[0]


class ReconciliationRecord(FrozenModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-final-342-g1114d-terminal-reconciliation-v1"]
    status: Literal["FINAL_342_G1114D_TERMINAL_CLASSIFICATION_RECONCILED"]

    transaction_id: Literal["16136113b163494ddd366e33a4a7553eafef9c42bd7c57e4e2f3be651fb1c8ab"]
    saved_version_id: Literal[346383612]

    historical_terminal_disposition: Literal["CONSUMED"]
    historical_terminal_execution_outcome: Literal["PASSED"]
    historical_terminal_receipt_sha256: Literal[
        "0db7fd65c153439bc286c074436366c0a785e7d6fb95611a7501c6f1ef91f39e"
    ]
    historical_terminal_receipt_preserved: Literal[True]

    functional_execution_outcome: Literal["PASSED"]
    request_reconciliation_passed: Literal[True]
    trajectory_terminal_count: Literal[342]
    completed_trajectory_count: Literal[342]

    primary_failure_present: Literal[False]
    secondary_failure_count: Literal[1]
    secondary_failure_phase: Literal["teardown"]
    secondary_failure_code: Literal["FINAL_342_TEARDOWN_FAILURE"]
    secondary_failure_safe_message: Literal["ValidationError"]
    worker_teardown_record_count: Literal[0]

    scratch_cleanup_status: Literal["PASSED"]
    scratch_absent: Literal[True]

    governed_teardown_outcome: Literal["FAILED"]
    overall_governed_execution_outcome: Literal["FAILED"]
    terminal_receipt_classification_conflict: Literal[True]
    historical_terminal_outcome_superseded_for_governed_acceptance: Literal[True]

    technical_evidence_disposition: Literal[
        "ACCEPTED_PARTIAL_FUNCTIONAL_EVIDENCE_GOVERNED_LIFECYCLE_FAILURE"
    ]

    remediation_effect_class: Literal["LATENT_DOWNSTREAM_DEFECT_REVEALED"]
    root_cause_classification: Literal["P5_P6_TEARDOWN_REPORT_TO_PRODUCER_FIELD_MAPPING_MISMATCH"]
    root_cause_confidence: Literal["HIGH_ARCHITECTURAL_INFERENCE_NOT_RUNTIME_TEARDOWN_PROOF"]

    repair_implemented: Literal[True]
    scientific_contract_changed: Literal[False]

    actual_worker_teardown_pass_established: Literal[False]
    effect_claims_permitted: Literal[False]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    new_execution_authorized: Literal[False]

    authorities: tuple[ArtifactReceipt, ...]
    next_gate: Literal["VALIDATE_G1114D_FULL_REPAIR_AND_RECONCILIATION_PACKAGE"]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_boundary(self) -> Self:
        if len(self.authorities) != 9:
            raise ValueError("G11.14D authority count drifted")

        if len(self.non_claims) < 6:
            raise ValueError("G11.14D non-claim boundary is incomplete")

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
            "FINAL_342_G1114D_ARTIFACT_MISSING",
            "required reconciliation artifact is missing or unsafe",
            relative.as_posix(),
        )

    return path


def _require_exact_file(
    root: Path,
    relative: Path,
    expected_sha256: str,
    expected_size: int,
) -> Path:
    path = _require_file(root, relative)

    if path.stat().st_size != expected_size:
        raise ReconciliationError(
            "FINAL_342_G1114D_ARTIFACT_SIZE_DRIFT",
            "preserved artifact byte count drifted",
            relative.as_posix(),
        )

    if _sha256_file(path) != expected_sha256:
        raise ReconciliationError(
            "FINAL_342_G1114D_ARTIFACT_SHA256_DRIFT",
            "preserved artifact SHA-256 drifted",
            relative.as_posix(),
        )

    return path


def _load_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "FINAL_342_G1114D_JSON_INVALID",
            "reconciliation JSON is invalid",
            path.as_posix(),
        ) from error

    if not isinstance(value, dict):
        raise ReconciliationError(
            "FINAL_342_G1114D_JSON_INVALID",
            "reconciliation JSON root must be an object",
            path.as_posix(),
        )

    return cast(dict[str, object], value)


def _receipt(root: Path, relative: Path) -> ArtifactReceipt:
    path = _require_file(root, relative)

    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _canonical_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload: object = value

    if isinstance(value, BaseModel):
        payload = value.model_dump(mode="json")

    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _validate_preserved_identity(root: Path) -> None:
    _require_exact_file(
        root,
        TERMINAL_PATH,
        TERMINAL_RECEIPT_SHA256,
        TERMINAL_RECEIPT_BYTES,
    )
    _require_exact_file(
        root,
        LIVE_AUTHORIZATION_PATH,
        LIVE_AUTHORIZATION_SHA256,
        LIVE_AUTHORIZATION_BYTES,
    )
    _require_exact_file(
        root,
        LIVE_MANIFEST_PATH,
        LIVE_MANIFEST_SHA256,
        LIVE_MANIFEST_BYTES,
    )
    _require_exact_file(
        root,
        PLATFORM_OBSERVATION_PATH,
        PLATFORM_OBSERVATION_SHA256,
        PLATFORM_OBSERVATION_BYTES,
    )
    _require_exact_file(
        root,
        EVIDENCE_ZIP_PATH,
        EVIDENCE_ZIP_SHA256,
        EVIDENCE_ZIP_BYTES,
    )
    _require_exact_file(
        root,
        TERMINAL_LOG_PATH,
        TERMINAL_LOG_SHA256,
        TERMINAL_LOG_BYTES,
    )

    qualification = _require_file(root, QUALIFICATION_PATH)

    if _sha256_file(qualification) != SUCCESSOR_QUALIFICATION_SHA256:
        raise ReconciliationError(
            "FINAL_342_G1114D_SUCCESSOR_QUALIFICATION_DRIFT",
            "G11.14D successor qualification identity drifted",
            QUALIFICATION_PATH.as_posix(),
        )


def _validate_historical_terminal(root: Path) -> HistoricalTerminalReceipt:
    payload = _load_json(_require_file(root, TERMINAL_PATH))

    try:
        return HistoricalTerminalReceipt.model_validate(payload)
    except ValidationError as error:
        raise ReconciliationError(
            "FINAL_342_G1114D_TERMINAL_RECEIPT_DRIFT",
            "historical terminal receipt semantics drifted",
            TERMINAL_PATH.as_posix(),
        ) from error


def _validate_evidence_zip(root: Path) -> EvidenceSummary:
    path = _require_file(root, EVIDENCE_ZIP_PATH)

    try:
        with zipfile.ZipFile(path) as archive:
            failure = json.loads(archive.read("failure_report_v1.json"))
            teardown = json.loads(archive.read("worker_teardown_report_v1.json"))
            cleanup = json.loads(archive.read("scratch_cleanup_report_v1.json"))
            reconciliation = json.loads(archive.read("request_reconciliation_v1.json"))
            trajectory = json.loads(archive.read("trajectory_terminal_ledger_v1.json"))
            manifest = json.loads(archive.read("bundle_manifest_v1.json"))
    except (
        KeyError,
        OSError,
        ValueError,
        zipfile.BadZipFile,
        json.JSONDecodeError,
    ) as error:
        raise ReconciliationError(
            "FINAL_342_G1114D_EVIDENCE_ZIP_INVALID",
            "preserved Final-342 evidence ZIP is invalid",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error

    if failure.get("primary_failure") is not None:
        raise ReconciliationError(
            "FINAL_342_G1114D_PRIMARY_FAILURE_DRIFT",
            "preserved evidence unexpectedly contains primary failure",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    secondary = failure.get("secondary_failures")

    if not isinstance(secondary, list) or len(secondary) != 1:
        raise ReconciliationError(
            "FINAL_342_G1114D_SECONDARY_FAILURE_DRIFT",
            "preserved secondary failure cardinality drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    secondary_failure = secondary[0]

    if not isinstance(secondary_failure, dict):
        raise ReconciliationError(
            "FINAL_342_G1114D_SECONDARY_FAILURE_DRIFT",
            "preserved secondary failure shape drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    expected_secondary = {
        "phase": "teardown",
        "error_code": "FINAL_342_TEARDOWN_FAILURE",
        "safe_message": "ValidationError",
    }

    for key, value in expected_secondary.items():
        if secondary_failure.get(key) != value:
            raise ReconciliationError(
                "FINAL_342_G1114D_SECONDARY_FAILURE_DRIFT",
                f"preserved secondary failure field drifted: {key}",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

    workers = teardown.get("workers")

    if not isinstance(workers, list) or len(workers) != 0:
        raise ReconciliationError(
            "FINAL_342_G1114D_TEARDOWN_RECORD_DRIFT",
            "preserved worker teardown record cardinality drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    if cleanup.get("status") != "PASSED":
        raise ReconciliationError(
            "FINAL_342_G1114D_CLEANUP_DRIFT",
            "preserved scratch cleanup status drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    if cleanup.get("scratch_absent") is not True:
        raise ReconciliationError(
            "FINAL_342_G1114D_CLEANUP_DRIFT",
            "preserved evidence no longer proves scratch absent",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    expected_counts = {
        "scheduled_request_count": 1368,
        "attempted_request_count": 1368,
        "http_completed_request_count": 1368,
        "admitted_request_count": 1368,
        "committed_request_count": 1368,
        "attempted_minus_http_completed": 0,
        "http_completed_minus_admitted": 0,
        "admitted_minus_committed": 0,
    }

    for count_key, count_value in expected_counts.items():
        if reconciliation.get(count_key) != count_value:
            raise ReconciliationError(
                "FINAL_342_G1114D_REQUEST_RECONCILIATION_DRIFT",
                f"preserved request reconciliation field drifted: {count_key}",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

    if trajectory.get("scheduled_trajectory_count") != 342:
        raise ReconciliationError(
            "FINAL_342_G1114D_TRAJECTORY_DRIFT",
            "scheduled trajectory count drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    if trajectory.get("observed_terminal_count") != 342:
        raise ReconciliationError(
            "FINAL_342_G1114D_TRAJECTORY_DRIFT",
            "terminal trajectory count drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    trajectories = trajectory.get("trajectories")

    if not isinstance(trajectories, list) or len(trajectories) != 342:
        raise ReconciliationError(
            "FINAL_342_G1114D_TRAJECTORY_DRIFT",
            "terminal trajectory ledger cardinality drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    completed = [
        item
        for item in trajectories
        if isinstance(item, dict) and item.get("terminal_state") == "completed"
    ]
    failed = [
        item
        for item in trajectories
        if isinstance(item, dict) and item.get("terminal_state") == "failed"
    ]

    if len(completed) != 342 or len(failed) != 0:
        raise ReconciliationError(
            "FINAL_342_G1114D_TRAJECTORY_DRIFT",
            "terminal trajectory classifications drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    if manifest.get("transaction_id") != TRANSACTION_ID:
        raise ReconciliationError(
            "FINAL_342_G1114D_MANIFEST_IDENTITY_DRIFT",
            "evidence manifest transaction identity drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    if manifest.get("member_count") != 9:
        raise ReconciliationError(
            "FINAL_342_G1114D_MANIFEST_IDENTITY_DRIFT",
            "evidence manifest member count drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )

    for key in (
        "raw_prompts_included",
        "raw_outputs_included",
        "raw_provider_payloads_included",
        "credentials_included",
    ):
        if manifest.get(key) is not False:
            raise ReconciliationError(
                "FINAL_342_G1114D_PUBLIC_EVIDENCE_PRIVACY_DRIFT",
                f"public evidence privacy field drifted: {key}",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

    return EvidenceSummary(
        primary_failure_present=False,
        secondary_failure_count=1,
        secondary_failure_phase="teardown",
        secondary_failure_code="FINAL_342_TEARDOWN_FAILURE",
        secondary_failure_safe_message="ValidationError",
        worker_teardown_record_count=0,
        scratch_cleanup_status="PASSED",
        scratch_absent=True,
        scheduled_request_count=1368,
        attempted_request_count=1368,
        http_completed_request_count=1368,
        admitted_request_count=1368,
        committed_request_count=1368,
        request_reconciliation_passed=True,
        scheduled_trajectory_count=342,
        trajectory_terminal_count=342,
        completed_trajectory_count=342,
        failed_trajectory_count=0,
    )


def _validate_root_cause_and_repair(root: Path) -> None:
    runtime_source = _require_file(root, P5_RUNTIME_PATH).read_text(encoding="utf-8")
    producer_source = _require_file(root, PRODUCER_PATH).read_text(encoding="utf-8")
    repair_template = _require_file(root, REPAIR_TEMPLATE_PATH).read_text(encoding="utf-8")
    repair_test = _require_file(root, REPAIR_TEST_PATH).read_text(encoding="utf-8")

    runtime_markers = (
        '"process_tree_absent_after": process_tree_absent',
        '"gpu_processes_absent_after": gpu_processes_absent',
        '"port_closed_after": port_closed',
        '"memory_returned_within_tolerance": memory_returned',
    )

    producer_markers = (
        'report.get("process_tree_absent")',
        'report.get("gpu_processes_absent")',
        'report.get("port_closed")',
        'report.get("memory_returned")',
    )

    repair_markers = (
        "class _TeardownReportAdapter:",
        '"process_tree_absent_after"',
        '"gpu_processes_absent_after"',
        '"port_closed_after"',
        '"memory_returned_within_tolerance"',
        "_teardown_workers_view(workers)",
    )

    test_markers = (
        "test_live_teardown_adapter_maps_actual_p5_p6_report_schema",
        '"process_tree_absent_after": True',
        '"gpu_processes_absent_after": True',
        '"port_closed_after": True',
        '"memory_returned_within_tolerance": True',
    )

    for marker in runtime_markers:
        if marker not in runtime_source:
            raise ReconciliationError(
                "FINAL_342_G1114D_RUNTIME_SCHEMA_DRIFT",
                "P5/P6 teardown runtime schema marker drifted",
                P5_RUNTIME_PATH.as_posix(),
            )

    for marker in producer_markers:
        if marker not in producer_source:
            raise ReconciliationError(
                "FINAL_342_G1114D_PRODUCER_SCHEMA_DRIFT",
                "Final-342 producer teardown schema marker drifted",
                PRODUCER_PATH.as_posix(),
            )

    for marker in repair_markers:
        if marker not in repair_template:
            raise ReconciliationError(
                "FINAL_342_G1114D_REPAIR_DRIFT",
                "G11.14D teardown adapter repair marker is missing",
                REPAIR_TEMPLATE_PATH.as_posix(),
            )

    for marker in test_markers:
        if marker not in repair_test:
            raise ReconciliationError(
                "FINAL_342_G1114D_REPAIR_TEST_DRIFT",
                "G11.14D teardown regression marker is missing",
                REPAIR_TEST_PATH.as_posix(),
            )


def build_record(repo_root: Path) -> ReconciliationRecord:
    root = repo_root.resolve()

    _validate_preserved_identity(root)
    terminal = _validate_historical_terminal(root)
    evidence = _validate_evidence_zip(root)
    _validate_root_cause_and_repair(root)

    authorities = (
        _receipt(root, TERMINAL_PATH),
        _receipt(root, LIVE_AUTHORIZATION_PATH),
        _receipt(root, LIVE_MANIFEST_PATH),
        _receipt(root, PLATFORM_OBSERVATION_PATH),
        _receipt(root, EVIDENCE_ZIP_PATH),
        _receipt(root, TERMINAL_LOG_PATH),
        _receipt(root, QUALIFICATION_PATH),
        _receipt(root, REPAIR_TEMPLATE_PATH),
        _receipt(root, REPAIR_TEST_PATH),
    )

    return ReconciliationRecord(
        schema_version="1.0.0",
        record_id="auragateway-final-342-g1114d-terminal-reconciliation-v1",
        status="FINAL_342_G1114D_TERMINAL_CLASSIFICATION_RECONCILED",
        transaction_id=TRANSACTION_ID,
        saved_version_id=SAVED_VERSION_ID,
        historical_terminal_disposition=terminal.disposition,
        historical_terminal_execution_outcome=terminal.execution_outcome,
        historical_terminal_receipt_sha256=TERMINAL_RECEIPT_SHA256,
        historical_terminal_receipt_preserved=True,
        functional_execution_outcome="PASSED",
        request_reconciliation_passed=evidence.request_reconciliation_passed,
        trajectory_terminal_count=evidence.trajectory_terminal_count,
        completed_trajectory_count=evidence.completed_trajectory_count,
        primary_failure_present=evidence.primary_failure_present,
        secondary_failure_count=evidence.secondary_failure_count,
        secondary_failure_phase=evidence.secondary_failure_phase,
        secondary_failure_code=evidence.secondary_failure_code,
        secondary_failure_safe_message=evidence.secondary_failure_safe_message,
        worker_teardown_record_count=evidence.worker_teardown_record_count,
        scratch_cleanup_status=evidence.scratch_cleanup_status,
        scratch_absent=evidence.scratch_absent,
        governed_teardown_outcome="FAILED",
        overall_governed_execution_outcome="FAILED",
        terminal_receipt_classification_conflict=True,
        historical_terminal_outcome_superseded_for_governed_acceptance=True,
        technical_evidence_disposition=(
            "ACCEPTED_PARTIAL_FUNCTIONAL_EVIDENCE_GOVERNED_LIFECYCLE_FAILURE"
        ),
        remediation_effect_class="LATENT_DOWNSTREAM_DEFECT_REVEALED",
        root_cause_classification=("P5_P6_TEARDOWN_REPORT_TO_PRODUCER_FIELD_MAPPING_MISMATCH"),
        root_cause_confidence=("HIGH_ARCHITECTURAL_INFERENCE_NOT_RUNTIME_TEARDOWN_PROOF"),
        repair_implemented=True,
        scientific_contract_changed=False,
        actual_worker_teardown_pass_established=False,
        effect_claims_permitted=False,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        new_execution_authorized=False,
        authorities=authorities,
        next_gate=NEXT_GATE,
        non_claims=(
            "The historical PASSED terminal receipt is not deleted or rewritten.",
            "The saved execution is not accepted as a complete governed Final-342 pass.",
            "Actual physical worker teardown success is not established.",
            "The zero teardown-record count is not evidence that zero workers required teardown.",
            "No A/B/C effect claim is authorized by this reconciliation.",
            "The consumed authorization is not reusable.",
            "No unchanged replay is authorized.",
            "No new Kaggle execution is authorized.",
        ),
    )


def expected_outputs(repo_root: Path) -> tuple[bytes, bytes]:
    root = repo_root.resolve()
    record = build_record(root)
    record_bytes = _canonical_bytes(record)

    review: dict[str, object] = {
        "schema_version": "1.0.0",
        "review_id": ("auragateway-final-342-g1114d-terminal-reconciliation-v1-review"),
        "decision": "APPROVED_TERMINAL_CLASSIFICATION_RECONCILIATION",
        "transaction_id": TRANSACTION_ID,
        "saved_version_id": SAVED_VERSION_ID,
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "source": _receipt(root, SOURCE_PATH).model_dump(mode="json"),
        "tests": _receipt(root, TEST_PATH).model_dump(mode="json"),
        "historical_terminal_receipt_sha256": TERMINAL_RECEIPT_SHA256,
        "evidence_zip_sha256": EVIDENCE_ZIP_SHA256,
        "successor_qualification_sha256": SUCCESSOR_QUALIFICATION_SHA256,
        "historical_terminal_execution_outcome": "PASSED",
        "corrected_governed_execution_outcome": "FAILED",
        "effect_claims_permitted": False,
        "authorization_reusable": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }

    return record_bytes, _canonical_bytes(review)


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record_bytes, review_bytes = expected_outputs(root)

    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH

    record_path.parent.mkdir(parents=True, exist_ok=True)

    record_path.write_bytes(record_bytes)
    review_path.write_bytes(review_bytes)

    return {
        "status": "FINAL_342_G1114D_TERMINAL_RECONCILIATION_GENERATED",
        "record_sha256": hashlib.sha256(record_bytes).hexdigest(),
        "review_sha256": hashlib.sha256(review_bytes).hexdigest(),
        "historical_terminal_receipt_preserved": True,
        "corrected_governed_execution_outcome": "FAILED",
        "effect_claims_permitted": False,
        "authorization_reusable": False,
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
            "FINAL_342_G1114D_RECORD_DRIFT",
            "generated G11.14D reconciliation record drifted",
            RECORD_PATH.as_posix(),
        )

    if review_path.read_bytes() != expected_review:
        raise ReconciliationError(
            "FINAL_342_G1114D_REVIEW_DRIFT",
            "generated G11.14D reconciliation review drifted",
            REVIEW_PATH.as_posix(),
        )

    ReconciliationRecord.model_validate_json(record_path.read_bytes())

    return {
        "status": "FINAL_342_G1114D_TERMINAL_RECONCILIATION_VALID",
        "record_sha256": _sha256_file(record_path),
        "review_sha256": _sha256_file(review_path),
        "historical_terminal_receipt_preserved": True,
        "corrected_governed_execution_outcome": "FAILED",
        "effect_claims_permitted": False,
        "authorization_reusable": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _Parser:
    parser = _Parser(prog="final-342-g1114d-terminal-reconciliation-v1")
    parser.add_argument(
        "command",
        choices=("generate", "validate"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)

        result: dict[str, object] | None = None

        if args.command == "generate":
            result = generate(args.repo_root)

        if args.command == "validate":
            result = validate(args.repo_root)

        if result is None:
            raise ReconciliationError(
                "FINAL_342_G1114D_COMMAND_INVALID",
                "G11.14D reconciliation command was not handled",
            )

    except (
        ReconciliationError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        payload: dict[str, object] = {
            "error_code": "FINAL_342_G1114D_RECONCILIATION_FAILED",
            "safe_message": "G11.14D terminal reconciliation failed",
            "path": None,
        }

        if isinstance(error, ReconciliationError):
            payload = error.envelope()

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

"""Validate Exact-Runtime P5/P6 V2 outcome-unknown governance V1."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Never, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SAVED_VERSION_ID: Final = 341548056
BASE_MAIN_COMMIT: Final = "0ee9e5b8fe8fb8fbf5268f2c270748e1a4c9b8e2"

AUTHORIZATION_SHA256: Final = "f2ba0df653f09651bbb61904e63d2b54e6a45e74fd3910e88a82fd93b7cbb720"
AUTHORIZATION_SIZE_BYTES: Final = 2116
TERMINAL_RECEIPT_SHA256: Final = "b2b644971de644d335f8955188f30896a0cd4354d21e92c5295dbedc13adb9ba"
TERMINAL_RECEIPT_SIZE_BYTES: Final = 954
TERMINAL_LOG_SHA256: Final = "fba590846fa1a82a448f6dee96ea2bfd7a7e0b22bafcccdfb5e499fb8d6c4d0a"
TERMINAL_LOG_SIZE_BYTES: Final = 2791
PARTIAL_RESULTS_SHA256: Final = "804174adc457d5cfbcd4b2df19a9fb83c5306dd014640f83bedf6313cab3c790"
PARTIAL_RESULTS_SIZE_BYTES: Final = 15370
RUNTIME_SCRIPT_SHA256: Final = "599b0395952abb0666e48890d4f25ad9050260837134a4c53716943a3d391df0"

NEXT_GATE: Final = "DESIGN_AND_MERGE_TRANSACTION_BOUND_EXECUTION_AUTHORIZATION_ARCHITECTURE_V1"

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_execution_authorization.json"
)
OPERATIONAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_authorization_consumption.json"
)

VAULT_ROOT: Final = Path("evidence_vault/local_abc/p5-p6-exact-runtime-v2-outcome-unknown-v1")
VAULT_AUTHORIZATION_PATH: Final = VAULT_ROOT / (
    "lifecycle/execution_authorization_v2-341548056.json"
)
VAULT_RECEIPT_PATH: Final = VAULT_ROOT / (
    "lifecycle/authorization_terminal_receipt_v2-341548056.json"
)
TERMINAL_LOG_PATH: Final = VAULT_ROOT / ("kaggle/ag-exact-runtime-p5-p6-requal-v2-341548056.log")
PARTIAL_RESULTS_PATH: Final = VAULT_ROOT / "kaggle/results-341548056.zip"

SFR_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_v2_outcome_unknown_sfr_v1.json"
)
ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_v2_outcome_unknown_acceptance_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_v2_outcome_unknown_acceptance_v1_review.json"
)
EVIDENCE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_v2_outcome_unknown_evidence_manifest_v1.json"
)
EVIDENCE_MANIFEST_SHA256: Final = "7213e46d17c0c7b106b793621e3f8017891afdd62fef2dd9ec691088264cb89c"
SFR_SHA256: Final = "9e41ff31d20df98309d5952eb3f4bc4be1a94fca1d545be74514c63c20553cf8"
ACCEPTANCE_SHA256: Final = "66603d034a229b8ee623a6f5c93e3a7f5045da474443c9693c2f7629acf2fc07"
REVIEW_SHA256: Final = "53555f6636d5efb2ec7d4ab8173a1847ee50a9486f6d093b221dd3a95eb0a1f3"

EXPECTED_PARTIAL_MEMBERS: Final = (
    "p5_p6_exact_runtime_requalification_v2/c1_model_construction_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/c2_worker_startup_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/c3_single_request_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/c4_output_contract_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/p5_cache_behavior_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/p5_post_restart_native_origin_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/p6_native_origin_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/p6_stage_checkpoint_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/p6_worker_state_isolation_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/runtime_environment_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/runtime_import_closure_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/runtime_install_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/runtime_source_identity_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2/worker_teardown_report_v1.json",
    "p5_p6_exact_runtime_requalification_v2_scratch/target_runtime/bin/Activate.ps1",
    "p5_p6_exact_runtime_requalification_v2_scratch/target_runtime/bin/activate",
    "p5_p6_exact_runtime_requalification_v2_scratch/target_runtime/bin/activate.csh",
    "p5_p6_exact_runtime_requalification_v2_scratch/target_runtime/bin/activate.fish",
    "p5_p6_exact_runtime_requalification_v2_scratch/target_runtime/pyvenv.cfg",
)


class GovernanceError(RuntimeError):
    """Metadata-safe governance validation error."""

    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.code,
            "safe_message": self.message,
            "path": self.path,
        }


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class OutcomeUnknownAcceptance(FrozenModel):
    schema_version: str
    record_id: str
    status: str
    saved_version_id: int
    kaggle_execution_status: str
    authorization_terminal_disposition: str
    governed_execution_outcome: str
    failure_class: str
    diagnostic_masking_established: bool
    earliest_precleanup_exception_recovered: bool
    expected_governed_evidence_zip_produced: bool
    partial_kaggle_results_preserved: bool
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_log_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    partial_results_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_source_identity_verified: bool
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_install_report_status: str
    runtime_installation_completed: bool
    target_runtime_materialization_observed: bool
    model_requests_performed: int
    p5_status: str
    p6_status: str
    p6_current_stage: str
    runtime_incompatibility_established: bool
    model_failure_established: bool
    p5_failure_established: bool
    p6_failure_established: bool
    accepted_v5_exact_runtime_capability_invalidated: bool
    authorization_transport_v1_failure_recurred: bool
    authorization_reusable: bool
    runtime_execution_authorized: bool
    pilot_execution_authorized: bool
    final_measured_abc_execution_authorized: bool
    symbolic_link_regression_case_required_for_successor: bool
    architecture_reconciliation_required: bool
    sfr_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    next_gate: str

    @model_validator(mode="after")
    def validate_boundary(self) -> OutcomeUnknownAcceptance:
        expected: dict[str, object] = {
            "status": "ACCEPTED_DIAGNOSTIC_OUTCOME_UNKNOWN",
            "saved_version_id": SAVED_VERSION_ID,
            "kaggle_execution_status": "FAILED",
            "authorization_terminal_disposition": "OUTCOME_UNKNOWN",
            "governed_execution_outcome": "OUTCOME_UNKNOWN",
            "failure_class": "HARNESS_SEMANTIC_FAILURE",
            "diagnostic_masking_established": True,
            "earliest_precleanup_exception_recovered": False,
            "expected_governed_evidence_zip_produced": False,
            "partial_kaggle_results_preserved": True,
            "authorization_sha256": AUTHORIZATION_SHA256,
            "terminal_receipt_sha256": TERMINAL_RECEIPT_SHA256,
            "terminal_log_sha256": TERMINAL_LOG_SHA256,
            "partial_results_zip_sha256": PARTIAL_RESULTS_SHA256,
            "runtime_source_identity_verified": True,
            "runtime_script_sha256": RUNTIME_SCRIPT_SHA256,
            "runtime_install_report_status": "NOT_RUN",
            "runtime_installation_completed": False,
            "target_runtime_materialization_observed": True,
            "model_requests_performed": 0,
            "p5_status": "NOT_RUN",
            "p6_status": "NOT_RUN",
            "p6_current_stage": "P6_NOT_STARTED",
            "runtime_incompatibility_established": False,
            "model_failure_established": False,
            "p5_failure_established": False,
            "p6_failure_established": False,
            "accepted_v5_exact_runtime_capability_invalidated": False,
            "authorization_transport_v1_failure_recurred": False,
            "authorization_reusable": False,
            "runtime_execution_authorized": False,
            "pilot_execution_authorized": False,
            "final_measured_abc_execution_authorized": False,
            "symbolic_link_regression_case_required_for_successor": True,
            "architecture_reconciliation_required": True,
            "sfr_sha256": SFR_SHA256,
            "evidence_manifest_sha256": EVIDENCE_MANIFEST_SHA256,
            "next_gate": NEXT_GATE,
        }
        for key, value in expected.items():
            if getattr(self, key) != value:
                raise ValueError(f"outcome-unknown acceptance drifted: {key}")
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
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_ARTIFACT_MISSING",
            "required governance artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_JSON_INVALID",
            "governance JSON is invalid",
            path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_JSON_INVALID",
            "governance JSON root must be an object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def preserve_lifecycle(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    pairs = (
        (
            OPERATIONAL_AUTHORIZATION_PATH,
            VAULT_AUTHORIZATION_PATH,
            AUTHORIZATION_SHA256,
            AUTHORIZATION_SIZE_BYTES,
        ),
        (
            OPERATIONAL_RECEIPT_PATH,
            VAULT_RECEIPT_PATH,
            TERMINAL_RECEIPT_SHA256,
            TERMINAL_RECEIPT_SIZE_BYTES,
        ),
    )
    copied: list[str] = []
    for source_rel, target_rel, expected_sha, expected_size in pairs:
        source = _require_file(root, source_rel)
        if source.stat().st_size != expected_size or _sha256_file(source) != expected_sha:
            raise GovernanceError(
                "P5_P6_V2_OUTCOME_UNKNOWN_LIFECYCLE_IDENTITY_DRIFT",
                "operational lifecycle artifact identity drifted",
                source_rel.as_posix(),
            )
        target = root / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if not target.is_file() or target.is_symlink():
                raise GovernanceError(
                    "P5_P6_V2_OUTCOME_UNKNOWN_NON_OVERWRITE_VIOLATION",
                    "preserved lifecycle target exists unsafely",
                    target_rel.as_posix(),
                )
            if target.read_bytes() != source.read_bytes():
                raise GovernanceError(
                    "P5_P6_V2_OUTCOME_UNKNOWN_NON_OVERWRITE_VIOLATION",
                    "preserved lifecycle target has different bytes",
                    target_rel.as_posix(),
                )
        if not target.exists():
            shutil.copyfile(source, target)
        copied.append(target_rel.as_posix())
    return {
        "status": "P5_P6_V2_OUTCOME_UNKNOWN_LIFECYCLE_PRESERVED",
        "copied_paths": copied,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
    }


def _validate_identity(path: Path, expected_sha: str, expected_size: int) -> None:
    if path.stat().st_size != expected_size or _sha256_file(path) != expected_sha:
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_IDENTITY_DRIFT",
            "preserved evidence identity drifted",
            path.as_posix(),
        )


def _validate_manifest(root: Path) -> None:
    path = _require_file(root, EVIDENCE_MANIFEST_PATH)
    if _sha256_file(path) != EVIDENCE_MANIFEST_SHA256:
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_MANIFEST_DRIFT",
            "evidence manifest identity drifted",
            EVIDENCE_MANIFEST_PATH.as_posix(),
        )
    payload = _load_json(path)
    members = payload.get("members")
    count = payload.get("member_count")
    if not isinstance(members, list) or count != len(members):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_MANIFEST_INVALID",
            "evidence manifest members are invalid",
            EVIDENCE_MANIFEST_PATH.as_posix(),
        )
    for item in members:
        if not isinstance(item, dict):
            raise GovernanceError(
                "P5_P6_V2_OUTCOME_UNKNOWN_MANIFEST_INVALID",
                "evidence manifest member is invalid",
                EVIDENCE_MANIFEST_PATH.as_posix(),
            )
        raw_path = item.get("path")
        raw_sha = item.get("sha256")
        raw_size = item.get("size_bytes")
        if (
            not isinstance(raw_path, str)
            or not isinstance(raw_sha, str)
            or not isinstance(raw_size, int)
        ):
            raise GovernanceError(
                "P5_P6_V2_OUTCOME_UNKNOWN_MANIFEST_INVALID",
                "evidence manifest member fields are invalid",
                EVIDENCE_MANIFEST_PATH.as_posix(),
            )
        member = _require_file(root, Path(raw_path))
        _validate_identity(member, raw_sha, raw_size)


def _validate_terminal_receipt(path: Path) -> None:
    payload = _load_json(path)
    expected: dict[str, object] = {
        "authorization_sha256": AUTHORIZATION_SHA256,
        "disposition": "OUTCOME_UNKNOWN",
        "execution_attempted": True,
        "execution_outcome": None,
        "saved_version_id": SAVED_VERSION_ID,
        "evidence_zip_sha256": None,
        "terminal_log_sha256": TERMINAL_LOG_SHA256,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise GovernanceError(
                "P5_P6_V2_OUTCOME_UNKNOWN_TERMINAL_RECEIPT_DRIFT",
                f"terminal receipt field drifted: {key}",
                VAULT_RECEIPT_PATH.as_posix(),
            )


def _validate_partial_results(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = tuple(archive.namelist())
        if set(names) != set(EXPECTED_PARTIAL_MEMBERS):
            raise GovernanceError(
                "P5_P6_V2_OUTCOME_UNKNOWN_PARTIAL_RESULTS_DRIFT",
                "partial-results member inventory drifted",
                PARTIAL_RESULTS_PATH.as_posix(),
            )
        prohibited = (
            "ag-exact-runtime-p5-p6-requal-evidence-v2.zip",
            "failure_report_v1.json",
            "p5_p6_exact_runtime_requalification_summary_v1.json",
            "bundle_manifest_v1.json",
            "scratch_cleanup_report_v1.json",
        )
        basenames = {Path(name).name for name in names}
        if any(name in basenames for name in prohibited):
            raise GovernanceError(
                "P5_P6_V2_OUTCOME_UNKNOWN_TERMINAL_EVIDENCE_DRIFT",
                "partial results unexpectedly contain terminal governed evidence",
                PARTIAL_RESULTS_PATH.as_posix(),
            )

        source = json.loads(
            archive.read(
                "p5_p6_exact_runtime_requalification_v2/runtime_source_identity_report_v1.json"
            )
        )
        install = json.loads(
            archive.read("p5_p6_exact_runtime_requalification_v2/runtime_install_report_v1.json")
        )
        p5 = json.loads(
            archive.read("p5_p6_exact_runtime_requalification_v2/p5_cache_behavior_report_v1.json")
        )
        p6 = json.loads(
            archive.read(
                "p5_p6_exact_runtime_requalification_v2/p6_stage_checkpoint_report_v1.json"
            )
        )

    if (
        source.get("status") != "PASSED"
        or source.get("executed_runtime_script_sha256") != RUNTIME_SCRIPT_SHA256
    ):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_RUNTIME_SOURCE_DRIFT",
            "runtime-source identity evidence drifted",
            PARTIAL_RESULTS_PATH.as_posix(),
        )
    if install.get("status") != "NOT_RUN":
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_INSTALL_REPORT_DRIFT",
            "runtime-install fallback status drifted",
            PARTIAL_RESULTS_PATH.as_posix(),
        )
    if p5.get("status") != "NOT_RUN":
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_P5_DEPTH_DRIFT",
            "P5 execution depth drifted",
            PARTIAL_RESULTS_PATH.as_posix(),
        )
    if (
        p6.get("status") != "NOT_RUN"
        or p6.get("current_stage") != "P6_NOT_STARTED"
        or p6.get("global_model_requests") != 0
    ):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_P6_DEPTH_DRIFT",
            "P6 execution depth drifted",
            PARTIAL_RESULTS_PATH.as_posix(),
        )


def _validate_log(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    required = (
        "cleanup_scratch()",
        "directory_snapshot(path)",
        "RuntimeError: target runtime contains a symbolic link",
    )
    if any(fragment not in text for fragment in required):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_LOG_DRIFT",
            "terminal log no longer preserves the observed cleanup failure",
            TERMINAL_LOG_PATH.as_posix(),
        )


def validate_governance(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    _validate_manifest(root)

    auth = _require_file(root, VAULT_AUTHORIZATION_PATH)
    receipt = _require_file(root, VAULT_RECEIPT_PATH)
    log = _require_file(root, TERMINAL_LOG_PATH)
    results = _require_file(root, PARTIAL_RESULTS_PATH)

    _validate_identity(auth, AUTHORIZATION_SHA256, AUTHORIZATION_SIZE_BYTES)
    _validate_identity(
        receipt,
        TERMINAL_RECEIPT_SHA256,
        TERMINAL_RECEIPT_SIZE_BYTES,
    )
    _validate_identity(log, TERMINAL_LOG_SHA256, TERMINAL_LOG_SIZE_BYTES)
    _validate_identity(
        results,
        PARTIAL_RESULTS_SHA256,
        PARTIAL_RESULTS_SIZE_BYTES,
    )

    _validate_terminal_receipt(receipt)
    _validate_log(log)
    _validate_partial_results(results)

    acceptance_payload = _load_json(_require_file(root, ACCEPTANCE_PATH))
    try:
        acceptance = OutcomeUnknownAcceptance.model_validate(acceptance_payload)
    except ValidationError as error:
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_ACCEPTANCE_INVALID",
            "outcome-unknown acceptance record is invalid",
            ACCEPTANCE_PATH.as_posix(),
        ) from error

    sfr = _load_json(_require_file(root, SFR_PATH))
    if (
        _sha256_file(root / SFR_PATH) != SFR_SHA256
        or sfr.get("status") != "CERTIFIED_DIAGNOSTIC_OUTCOME_UNKNOWN"
        or sfr.get("next_safe_action") != NEXT_GATE
    ):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_SFR_DRIFT",
            "semi-formal reasoning certificate drifted",
            SFR_PATH.as_posix(),
        )

    review = _load_json(_require_file(root, REVIEW_PATH))
    if (
        _sha256_file(root / REVIEW_PATH) != REVIEW_SHA256
        or review.get("status") != "APPROVED_FOR_DIAGNOSTIC_OUTCOME_UNKNOWN_PRESERVATION"
        or review.get("classification") != acceptance.failure_class
        or review.get("next_gate") != NEXT_GATE
    ):
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_REVIEW_DRIFT",
            "outcome-unknown governance review drifted",
            REVIEW_PATH.as_posix(),
        )

    if _sha256_file(root / ACCEPTANCE_PATH) != ACCEPTANCE_SHA256:
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_ACCEPTANCE_DRIFT",
            "outcome-unknown acceptance identity drifted",
            ACCEPTANCE_PATH.as_posix(),
        )

    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_OUTCOME_UNKNOWN_GOVERNANCE_VALID",
        "saved_version_id": SAVED_VERSION_ID,
        "failure_class": acceptance.failure_class,
        "governed_execution_outcome": acceptance.governed_execution_outcome,
        "diagnostic_masking_established": True,
        "runtime_incompatibility_established": False,
        "p5_p6_exact_runtime_requalified": False,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def reject_authorization_reuse(authorization_sha256: str) -> Never:
    if authorization_sha256 != AUTHORIZATION_SHA256:
        raise GovernanceError(
            "P5_P6_V2_OUTCOME_UNKNOWN_AUTHORIZATION_IDENTITY_UNKNOWN",
            "authorization identity is not governed by this record",
        )
    raise GovernanceError(
        "P5_P6_V2_OUTCOME_UNKNOWN_AUTHORIZATION_TERMINAL",
        "terminal V2 authorization cannot be reused",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("preserve-lifecycle", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.repo_root).resolve()
    try:
        if args.command == "preserve-lifecycle":
            result = preserve_lifecycle(root)
        else:
            result = validate_governance(root)
    except GovernanceError as error:
        print(json.dumps(error.envelope(), sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

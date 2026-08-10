"""Validate and preserve Exact-Runtime P5/P6 authority-failure governance V1."""

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

FAILED_SAVED_VERSION_ID: Final = 341454766
INSPECTION_SAVED_VERSION_ID: Final = 341466979

AUTHORIZATION_SHA256: Final = "e9c1b58aedfccee3f36349bf063d5f1267721b8f395699a6c325304d32c20a2c"
AUTHORIZATION_SIZE_BYTES: Final = 3414
TERMINAL_RECEIPT_SHA256: Final = "e3a3c0519fff010576f1674adf09c5dafa13b013b04e670b2510204c81f7e4b5"
TERMINAL_RECEIPT_SIZE_BYTES: Final = 951

FAILED_EVIDENCE_ZIP_SHA256: Final = (
    "ca1cfada6a4c0ab7d8ed8fe446d3d6c281f246c4731ce20441884a998f82e6b6"
)
INSPECTION_EVIDENCE_ZIP_SHA256: Final = (
    "387935b89f327945811900365eba69c4278919e49750337aef8d6daf93e7a5dc"
)

OPERATIONAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_"
    "execution_authorization.json"
)
OPERATIONAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_"
    "authorization_consumption.json"
)
VAULT_ROOT: Final = Path("evidence_vault/local_abc/p5-p6-exact-runtime-authority-failure-v1")
VAULT_AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/execution_authorization_v1-341454766.json"
VAULT_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/authorization_consumption_v1-341454766.json"

SFR_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_authority_failure_sfr_v1.json"
)
ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_authority_failure_acceptance_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_authority_failure_acceptance_v1_review.json"
)
EVIDENCE_MANIFEST_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_authority_failure_evidence_manifest_v1.json"
)
EVIDENCE_MANIFEST_SHA256: Final = "9e7994d33416fe0abf81893c299c21f85c878d4b022838a7b601660eb8cda4c4"

FAILED_ZIP_PATH: Final = VAULT_ROOT / (
    "failed_run/ag-exact-runtime-p5-p6-requal-evidence-v1-341454766.zip"
)
INSPECTION_ZIP_PATH: Final = VAULT_ROOT / (
    "inspection/ag-p5-p6-authorization-input-inspection-v1-341466979.zip"
)

EXPECTED_AUTHORIZATION_RELATIVE_PATH: Final = (
    "datasets/kabomolefe/ag-p5-p6-execution-authorization-v1/execution_authorization_v1.json"
)
EXPECTED_NEXT_GATE: Final = "DESIGN_AND_MERGE_AUTHORIZATION_TRANSPORT_DISCOVERY_REMEDIATION_V1"


class GovernanceError(RuntimeError):
    """Metadata-safe failure-governance validation error."""

    def __init__(
        self,
        code: str,
        message: str,
        path: str | None = None,
    ) -> None:
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


class FailureAcceptance(FrozenModel):
    schema_version: str
    record_id: str
    status: str
    failure_depth: str
    saved_version_id: int
    inspection_saved_version_id: int
    failure_class: str
    reported_runtime_failure_class: str
    direct_cause: str
    runtime_incompatibility_established: bool
    authorization_transport_discovery_contract_invalidated: bool
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    terminal_receipt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    failed_evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    inspection_evidence_zip_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    current_consumer_candidate_count: int
    recursive_diagnostic_candidate_count: int
    candidate_metadata_parity_count: int
    observed_authorization_relative_path: str
    observed_authorization_path_depth: int
    runtime_installation_performed: bool
    model_loaded: bool
    worker_started: bool
    model_requests_performed: int
    p5_p6_exact_runtime_requalified: bool
    authorization_reusable: bool
    runtime_execution_authorized: bool
    pilot_execution_authorized: bool
    final_measured_abc_execution_authorized: bool
    fresh_authorization_required_for_future_execution: bool
    next_gate: str

    @model_validator(mode="after")
    def validate_boundary(self) -> FailureAcceptance:
        expected: dict[str, object] = {
            "status": "ACCEPTED_DIAGNOSTIC_FAILURE",
            "failure_depth": "EARLY_CONTROL_PLANE",
            "saved_version_id": FAILED_SAVED_VERSION_ID,
            "inspection_saved_version_id": INSPECTION_SAVED_VERSION_ID,
            "failure_class": ("AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE"),
            "reported_runtime_failure_class": "AUTHORITY_FAILURE",
            "runtime_incompatibility_established": False,
            "authorization_transport_discovery_contract_invalidated": True,
            "authorization_sha256": AUTHORIZATION_SHA256,
            "terminal_receipt_sha256": TERMINAL_RECEIPT_SHA256,
            "failed_evidence_zip_sha256": FAILED_EVIDENCE_ZIP_SHA256,
            "inspection_evidence_zip_sha256": INSPECTION_EVIDENCE_ZIP_SHA256,
            "current_consumer_candidate_count": 0,
            "recursive_diagnostic_candidate_count": 1,
            "candidate_metadata_parity_count": 1,
            "observed_authorization_relative_path": (EXPECTED_AUTHORIZATION_RELATIVE_PATH),
            "observed_authorization_path_depth": 4,
            "runtime_installation_performed": False,
            "model_loaded": False,
            "worker_started": False,
            "model_requests_performed": 0,
            "p5_p6_exact_runtime_requalified": False,
            "authorization_reusable": False,
            "runtime_execution_authorized": False,
            "pilot_execution_authorized": False,
            "final_measured_abc_execution_authorized": False,
            "fresh_authorization_required_for_future_execution": True,
            "next_gate": EXPECTED_NEXT_GATE,
        }
        for key, value in expected.items():
            if getattr(self, key) != value:
                raise ValueError(f"failure-acceptance field drifted: {key}")
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
            "P5_P6_FAILURE_GOVERNANCE_ARTIFACT_MISSING",
            "required failure-governance artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_JSON_INVALID",
            "failure-governance JSON is invalid",
            path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_JSON_INVALID",
            "failure-governance JSON root must be an object",
            path.as_posix(),
        )
    return cast(dict[str, object], payload)


def preserve_lifecycle(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    source_pairs = (
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

    for source_rel, target_rel, expected_sha, expected_size in source_pairs:
        source = _require_file(root, source_rel)
        if source.stat().st_size != expected_size or _sha256_file(source) != expected_sha:
            raise GovernanceError(
                "P5_P6_FAILURE_GOVERNANCE_LIFECYCLE_IDENTITY_DRIFT",
                "operational lifecycle artifact identity drifted",
                source_rel.as_posix(),
            )

        target = root / target_rel
        target.parent.mkdir(parents=True, exist_ok=True)

        if target.exists():
            if not target.is_file() or target.is_symlink():
                raise GovernanceError(
                    "P5_P6_FAILURE_GOVERNANCE_NON_OVERWRITE_VIOLATION",
                    "lifecycle evidence target already exists unsafely",
                    target_rel.as_posix(),
                )
            if target.read_bytes() != source.read_bytes():
                raise GovernanceError(
                    "P5_P6_FAILURE_GOVERNANCE_NON_OVERWRITE_VIOLATION",
                    "lifecycle evidence target has different bytes",
                    target_rel.as_posix(),
                )

        if not target.exists():
            shutil.copyfile(source, target)

        copied.append(target_rel.as_posix())

    return {
        "status": "P5_P6_FAILURE_GOVERNANCE_LIFECYCLE_PRESERVED",
        "copied_paths": copied,
        "authorization_sha256": AUTHORIZATION_SHA256,
        "terminal_receipt_sha256": TERMINAL_RECEIPT_SHA256,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
    }


def _validate_static_evidence(root: Path) -> None:
    manifest_path = _require_file(root, EVIDENCE_MANIFEST_PATH)
    if _sha256_file(manifest_path) != EVIDENCE_MANIFEST_SHA256:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_MANIFEST_DRIFT",
            "static evidence manifest identity drifted",
            EVIDENCE_MANIFEST_PATH.as_posix(),
        )

    payload = _load_json(manifest_path)
    members = payload.get("members")
    member_count = payload.get("member_count")
    if not isinstance(members, list) or member_count != len(members):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_MANIFEST_INVALID",
            "static evidence manifest members are invalid",
            EVIDENCE_MANIFEST_PATH.as_posix(),
        )

    for raw_member in members:
        if not isinstance(raw_member, dict):
            raise GovernanceError(
                "P5_P6_FAILURE_GOVERNANCE_MANIFEST_INVALID",
                "static evidence manifest member is invalid",
                EVIDENCE_MANIFEST_PATH.as_posix(),
            )

        relative_value = raw_member.get("path")
        expected_sha = raw_member.get("sha256")
        expected_size = raw_member.get("size_bytes")
        if (
            not isinstance(relative_value, str)
            or not isinstance(expected_sha, str)
            or not isinstance(expected_size, int)
        ):
            raise GovernanceError(
                "P5_P6_FAILURE_GOVERNANCE_MANIFEST_INVALID",
                "static evidence manifest member fields are invalid",
                EVIDENCE_MANIFEST_PATH.as_posix(),
            )

        relative = Path(relative_value)
        path = _require_file(root, relative)
        if path.stat().st_size != expected_size or _sha256_file(path) != expected_sha:
            raise GovernanceError(
                "P5_P6_FAILURE_GOVERNANCE_STATIC_EVIDENCE_DRIFT",
                "preserved static evidence identity drifted",
                relative.as_posix(),
            )


def _validate_failed_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        failure = json.loads(archive.read("failure_report_v1.json"))
        summary = json.loads(archive.read("p5_p6_exact_runtime_requalification_summary_v1.json"))

    if failure.get("failure_class") != "AUTHORITY_FAILURE":
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_FAILED_EVIDENCE_DRIFT",
            "failed evidence no longer reports AUTHORITY_FAILURE",
            FAILED_ZIP_PATH.as_posix(),
        )

    expected_message = "exactly one live P5/P6 execution authorization is required"
    if failure.get("safe_message") != expected_message:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_FAILED_EVIDENCE_DRIFT",
            "failed evidence authorization message drifted",
            FAILED_ZIP_PATH.as_posix(),
        )

    counters = summary.get("counters")
    if not isinstance(counters, dict):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_FAILED_EVIDENCE_DRIFT",
            "failed evidence counters are missing",
            FAILED_ZIP_PATH.as_posix(),
        )

    for key in (
        "runtime_install_attempts",
        "runtime_import_closure_probes",
        "model_loads",
        "worker_starts",
        "model_requests",
        "network_requests",
        "benchmark_trajectory_requests",
    ):
        if counters.get(key) != 0:
            raise GovernanceError(
                "P5_P6_FAILURE_GOVERNANCE_EXECUTION_DEPTH_DRIFT",
                "failed evidence crossed the early control-plane boundary",
                FAILED_ZIP_PATH.as_posix(),
            )


def _validate_inspection_zip(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        report = json.loads(archive.read("inspection_report.json"))
        inventory = json.loads(archive.read("candidate_inventory.json"))

    if report.get("finding_code") != "OBSERVED_SHALLOW_DISCOVERY_FALSE_NEGATIVE":
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_INSPECTION_DRIFT",
            "inspection no longer proves shallow-discovery false negative",
            INSPECTION_ZIP_PATH.as_posix(),
        )

    current = report.get("current_consumer_discovery")
    recursive = report.get("recursive_diagnostic_discovery")
    if not isinstance(current, dict) or not isinstance(recursive, dict):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_INSPECTION_DRIFT",
            "inspection discovery records are missing",
            INSPECTION_ZIP_PATH.as_posix(),
        )

    if current.get("candidate_count") != 0 or recursive.get("candidate_count") != 1:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_INSPECTION_DRIFT",
            "inspection candidate cardinality drifted",
            INSPECTION_ZIP_PATH.as_posix(),
        )

    candidates = inventory.get("candidates")
    if not isinstance(candidates, list) or len(candidates) != 1:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_INSPECTION_DRIFT",
            "inspection authorization inventory drifted",
            INSPECTION_ZIP_PATH.as_posix(),
        )

    candidate = candidates[0]
    if not isinstance(candidate, dict):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_INSPECTION_DRIFT",
            "inspection authorization candidate is invalid",
            INSPECTION_ZIP_PATH.as_posix(),
        )

    if (
        candidate.get("sha256") != AUTHORIZATION_SHA256
        or candidate.get("relative_path") != EXPECTED_AUTHORIZATION_RELATIVE_PATH
        or candidate.get("expected_metadata_all_match") is not True
    ):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_INSPECTION_DRIFT",
            "inspection authorization identity or parity drifted",
            INSPECTION_ZIP_PATH.as_posix(),
        )


def _validate_terminal_receipt(path: Path) -> None:
    payload = _load_json(path)
    expected: dict[str, object] = {
        "authorization_sha256": AUTHORIZATION_SHA256,
        "disposition": "CONSUMED",
        "execution_attempted": True,
        "execution_outcome": "FAILED",
        "saved_version_id": FAILED_SAVED_VERSION_ID,
        "evidence_zip_sha256": FAILED_EVIDENCE_ZIP_SHA256,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise GovernanceError(
                "P5_P6_FAILURE_GOVERNANCE_TERMINAL_RECEIPT_DRIFT",
                f"terminal receipt field drifted: {key}",
                VAULT_RECEIPT_PATH.as_posix(),
            )


def validate_governance(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()

    _validate_static_evidence(root)

    auth = _require_file(root, VAULT_AUTHORIZATION_PATH)
    receipt = _require_file(root, VAULT_RECEIPT_PATH)

    if (
        auth.stat().st_size != AUTHORIZATION_SIZE_BYTES
        or _sha256_file(auth) != AUTHORIZATION_SHA256
    ):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_AUTHORIZATION_DRIFT",
            "preserved authorization identity drifted",
            VAULT_AUTHORIZATION_PATH.as_posix(),
        )

    if (
        receipt.stat().st_size != TERMINAL_RECEIPT_SIZE_BYTES
        or _sha256_file(receipt) != TERMINAL_RECEIPT_SHA256
    ):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_RECEIPT_DRIFT",
            "preserved terminal receipt identity drifted",
            VAULT_RECEIPT_PATH.as_posix(),
        )

    _validate_failed_zip(_require_file(root, FAILED_ZIP_PATH))
    _validate_inspection_zip(_require_file(root, INSPECTION_ZIP_PATH))
    _validate_terminal_receipt(receipt)

    acceptance_payload = _load_json(_require_file(root, ACCEPTANCE_PATH))
    try:
        acceptance = FailureAcceptance.model_validate(acceptance_payload)
    except ValidationError as error:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_ACCEPTANCE_INVALID",
            "failure-acceptance record is invalid",
            ACCEPTANCE_PATH.as_posix(),
        ) from error

    sfr = _load_json(_require_file(root, SFR_PATH))
    if (
        sfr.get("status") != "CERTIFIED_FAILED_DIAGNOSTIC"
        or sfr.get("direct_cause") != acceptance.direct_cause
        or sfr.get("next_safe_action") != EXPECTED_NEXT_GATE
    ):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_SFR_DRIFT",
            "semi-formal reasoning certificate drifted",
            SFR_PATH.as_posix(),
        )

    review = _load_json(_require_file(root, REVIEW_PATH))
    if (
        review.get("status") != "APPROVED_FOR_FAILURE_GOVERNANCE_PRESERVATION"
        or review.get("classification") != acceptance.failure_class
        or review.get("next_gate") != EXPECTED_NEXT_GATE
    ):
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_REVIEW_DRIFT",
            "failure-governance review drifted",
            REVIEW_PATH.as_posix(),
        )

    return {
        "status": ("EXACT_RUNTIME_P5_P6_AUTHORITY_FAILURE_GOVERNANCE_V1_VALID"),
        "saved_version_id": FAILED_SAVED_VERSION_ID,
        "inspection_saved_version_id": INSPECTION_SAVED_VERSION_ID,
        "failure_class": acceptance.failure_class,
        "failure_depth": acceptance.failure_depth,
        "runtime_incompatibility_established": False,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": EXPECTED_NEXT_GATE,
    }


def reject_authorization_reuse(authorization_sha256: str) -> Never:
    if authorization_sha256 != AUTHORIZATION_SHA256:
        raise GovernanceError(
            "P5_P6_FAILURE_GOVERNANCE_AUTHORIZATION_IDENTITY_UNKNOWN",
            "authorization identity is not governed by this failure record",
        )
    raise GovernanceError(
        "P5_P6_FAILURE_GOVERNANCE_AUTHORIZATION_CONSUMED",
        "consumed P5/P6 execution authorization cannot be reused",
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("preserve-lifecycle", "validate"),
    )
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
        print(
            json.dumps(error.envelope(), sort_keys=True),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

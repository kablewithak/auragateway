"""Validate current CUDA 12.9 authorities and historical supersession boundaries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final, Never, cast

from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_harness_evidence_integration,
    full_abc_local_environment_qualification_execution_authorization_issuance_review,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_runtime_integration_review as integration_review,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization as authorization,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_contracts as contracts,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_issuance as issuance,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_harness_rematerialization as rematerialization,
)

harness_integration = full_abc_local_environment_qualification_cu129_harness_evidence_integration
issuance_review = full_abc_local_environment_qualification_execution_authorization_issuance_review

INTEGRATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_v1.json"
)
RUNTIME_MANIFEST_PATH: Final = contracts.MATERIALIZED_DATASET_MANIFEST_PATH
MATERIALIZATION_RECORD_PATH: Final = contracts.MATERIALIZATION_RECORD_PATH
DATASET_REQUEST_PATH: Final = contracts.DATASET_MANIFEST_REQUEST_PATH
AUTHORIZATION_REQUEST_PATH: Final = contracts.AUTHORIZATION_REQUEST_PATH
EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_request.json"
)
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
FINAL_AUTHORIZATION_PATH: Final = contracts.FINAL_AUTHORIZATION_PATH

REVIEW_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_runtime_integration_review.py"
)
EXECUTION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution.py"
)
ISSUANCE_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_execution_authorization_issuance.py"
)
ISSUANCE_REVIEW_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_execution_authorization_issuance_review.py"
)
REMATERIALIZATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_harness_rematerialization.py"
)
ISSUANCE_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_authorization_issuance_v1.md"
)

CANONICAL_JSON_PATHS: Final = (
    INTEGRATION_PATH,
    RUNTIME_MANIFEST_PATH,
    MATERIALIZATION_RECORD_PATH,
    DATASET_REQUEST_PATH,
    AUTHORIZATION_REQUEST_PATH,
    EXECUTION_REQUEST_PATH,
    QUALIFICATION_REQUEST_PATH,
    WORKER_PLAN_PATH,
    harness_integration.INTEGRATION_RECORD_PATH,
    harness_integration.READINESS_REVIEW_PATH,
    harness_integration.EVIDENCE_IDENTITY_PATH,
)

LIVE_RUNTIME_PATHS: Final = (
    Path("src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"),
    Path(
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
    ),
    Path(
        "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
    ),
    RUNTIME_MANIFEST_PATH,
    MATERIALIZATION_RECORD_PATH,
    DATASET_REQUEST_PATH,
    AUTHORIZATION_REQUEST_PATH,
    WORKER_PLAN_PATH,
)

RETIRED_RUNTIME_MARKERS: Final = (
    '"vllm_wheel"',
    '"python_wheel"',
    "vllm-0.25.1+cu129",
)


class AuthorityGraphError(RuntimeError):
    """Fail-closed current or historical authority-graph defect."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise AuthorityGraphError(message)


def _load_json_object(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorityGraphError(f"authority JSON is unreadable: {path.as_posix()}") from exc
    if not isinstance(payload, dict):
        raise AuthorityGraphError(f"authority JSON must contain one object: {path.as_posix()}")
    return cast(dict[str, object], payload)


def _require_canonical_json(path: Path) -> None:
    payload = _load_json_object(path)
    expected = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    observed = path.read_text(encoding="utf-8")
    if observed != expected:
        raise AuthorityGraphError(
            f"authority JSON is not canonical single-line JSON: {path.as_posix()}"
        )


def _require_source_markers(path: Path, markers: tuple[str, ...]) -> None:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuthorityGraphError(f"authority source is unreadable: {path.as_posix()}") from exc
    missing = tuple(marker for marker in markers if marker not in source)
    if missing:
        raise AuthorityGraphError(
            f"authority source is missing required controls: {path.as_posix()}: "
            + ", ".join(missing)
        )


def _require_live_runtime_has_no_retired_markers(repo_root: Path) -> None:
    drift: list[str] = []
    for relative_path in LIVE_RUNTIME_PATHS:
        text = (repo_root / relative_path).read_text(encoding="utf-8")
        observed = tuple(marker for marker in RETIRED_RUNTIME_MARKERS if marker in text)
        if observed:
            drift.append(f"{relative_path.as_posix()}:{','.join(observed)}")
    if drift:
        raise AuthorityGraphError(
            "current runtime authorities retain retired single-wheel markers: " + "; ".join(drift)
        )


def validate_repository_authority_graph(repo_root: str | Path) -> dict[str, object]:
    """Validate current wheelhouse authorities and revision-bound historical evidence."""

    root = Path(repo_root).resolve()
    for relative_path in CANONICAL_JSON_PATHS:
        _require_canonical_json(root / relative_path)

    integration = _load_json_object(root / INTEGRATION_PATH)
    if integration.get("decision") != "INTEGRATED_REPOSITORY_ONLY_AUTHORIZATION_BLOCKED":
        raise AuthorityGraphError("CUDA 12.9 integration disposition drifted")
    if integration.get("next_gate") != (
        "review_fresh_qualification_authorization_and_control_output_regeneration"
    ):
        raise AuthorityGraphError("CUDA 12.9 integration next gate drifted")
    safety = integration.get("safety")
    if not isinstance(safety, dict):
        raise AuthorityGraphError("CUDA 12.9 integration safety envelope is invalid")
    prohibited = (
        "authorization_issued",
        "credentials_present",
        "customer_data_present",
        "kaggle_execution_performed",
        "measured_execution_authorized",
        "model_loaded",
        "worker_started",
    )
    if any(safety.get(field) is not False for field in prohibited):
        raise AuthorityGraphError("CUDA 12.9 integration crossed a prohibited boundary")
    if safety.get("model_requests_performed") != 0:
        raise AuthorityGraphError("CUDA 12.9 integration performed model requests")

    record = contracts.MaterializedOfflineDatasetRecord.model_validate_json(
        (root / MATERIALIZATION_RECORD_PATH).read_text(encoding="utf-8")
    )
    manifest = contracts.PortableQualificationDatasetManifest.model_validate_json(
        (root / RUNTIME_MANIFEST_PATH).read_text(encoding="utf-8")
    )
    projected_manifest = authorization.build_portable_runtime_manifest(record)
    if projected_manifest.canonical_json() != manifest.canonical_json():
        raise AuthorityGraphError("materialization projection does not equal runtime manifest")
    if record.runtime_manifest_sha256 != manifest.fingerprint():
        raise AuthorityGraphError("materialization record does not bind runtime manifest")

    runtime = manifest.entries[2]
    if (
        runtime.role != "vllm_runtime"
        or runtime.artifact_format != "python_wheelhouse_directory"
        or runtime.runtime_output_directory != "auragateway_vllm_cu129_wheelhouse_v1"
        or runtime.package_count != 176
    ):
        raise AuthorityGraphError("current runtime manifest does not bind the wheelhouse")

    observed_dataset_request = contracts.OfflineDatasetManifestRequest.model_validate_json(
        (root / DATASET_REQUEST_PATH).read_text(encoding="utf-8")
    )
    expected_dataset_request = authorization.build_offline_dataset_manifest_request()
    if observed_dataset_request != expected_dataset_request:
        raise AuthorityGraphError("offline dataset request does not match its builder")

    observed_authorization_request = (
        contracts.QualificationAuthorizationRequest.model_validate_json(
            (root / AUTHORIZATION_REQUEST_PATH).read_text(encoding="utf-8")
        )
    )
    expected_authorization_request = authorization.build_qualification_authorization_request()
    if observed_authorization_request != expected_authorization_request:
        raise AuthorityGraphError("authorization request does not match its builder")
    if observed_authorization_request.final_authorization_generated is not False:
        raise AuthorityGraphError("authorization request claims final authorization")

    _require_live_runtime_has_no_retired_markers(root)
    _require_source_markers(
        root / REVIEW_SOURCE_PATH,
        (
            "EXPECTED_HISTORICAL_GIT_BLOBS",
            "_git_blob_at_revision",
            "HISTORICAL_PREINTEGRATION_AUTHORITY",
        ),
    )
    _require_source_markers(
        root / EXECUTION_SOURCE_PATH,
        ("hash-object", "--path"),
    )
    _require_source_markers(
        root / ISSUANCE_REVIEW_SOURCE_PATH,
        (
            "HistoricalQualificationAuthorizationRequest",
            "HistoricalDatasetRole",
            "HistoricalMaterializationRecord",
            "_load_json_object_at_revision",
        ),
    )
    _require_source_markers(
        root / REMATERIALIZATION_SOURCE_PATH,
        (
            "HistoricalPortableManifest",
            "HistoricalMaterializationRecord",
            "HISTORICAL_AUTHORITY_COMMIT",
            "_git_file_bytes_at_revision",
        ),
    )
    _require_source_markers(
        root / ISSUANCE_SOURCE_PATH,
        (
            "CURRENT_AUTHORIZATION_BASE_COMMIT",
            "CURRENT_HARNESS_SOURCE_COMMIT",
            "READINESS_REVIEW_SHA256",
            "validate_implementation_package",
            "CURRENT_ISSUANCE_FROZEN_LOADER_PARITY_FAILED",
            "AUTHORIZATION_ALREADY_EXISTS",
        ),
    )
    _require_source_markers(
        root / ISSUANCE_RUNBOOK_PATH,
        (
            "CURRENT STATUS: ISSUER IMPLEMENTED; AUTHORIZATION ABSENT",
            "explicit operator confirmation",
            "CONTROL_PACKAGE_AUTHORIZATION_PARITY",
        ),
    )

    issuer_summary = issuance.validate_implementation_package(root)
    if issuer_summary.get("status") != "FRESH_CU129_AUTHORIZATION_ISSUER_READY":
        raise AuthorityGraphError("fresh CUDA 12.9 issuer readiness drifted")
    if issuer_summary.get("authorization_issued") is not False:
        raise AuthorityGraphError("fresh CUDA 12.9 issuer created authorization")
    if issuer_summary.get("model_requests_performed") != 0:
        raise AuthorityGraphError("fresh CUDA 12.9 issuer performed model requests")

    historical_review = integration_review.validate_repository_package(root)
    if historical_review.get("review_disposition") != "HISTORICAL_PREINTEGRATION_AUTHORITY":
        raise AuthorityGraphError("pre-integration review supersession disposition drifted")

    historical_issuance = issuance_review.validate_repository_review_package(root)
    if (
        historical_issuance.get("authorization_issuance_performed") is not False
        or historical_issuance.get("final_authorization_generated") is not False
        or historical_issuance.get("kaggle_session_started") is not False
    ):
        raise AuthorityGraphError("historical PR 109 review crossed an operational boundary")

    historical_rematerialization = rematerialization.validate_repository_package(root)
    if (
        historical_rematerialization.get("authorization_issued") is not False
        or historical_rematerialization.get("gpu_execution_performed") is not False
        or historical_rematerialization.get("model_requests_performed") != 0
    ):
        raise AuthorityGraphError("historical rematerialization crossed an operational boundary")

    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise AuthorityGraphError("final qualification authorization must remain absent")

    return {
        "status": "CURRENT_CU129_AUTHORIZATION_ISSUER_IMPLEMENTED_AUTHORIZATION_ABSENT",
        "current_runtime_role": runtime.role,
        "current_runtime_format": runtime.artifact_format,
        "runtime_package_count": runtime.package_count,
        "canonical_json_authorities_verified": len(CANONICAL_JSON_PATHS),
        "current_harness_evidence_integrated": True,
        "operational_input_closure": "PASSED",
        "authorization_source_binding_policy": (
            harness_integration.AUTHORIZATION_SOURCE_BINDING_POLICY
        ),
        "current_authorization_base_commit": (issuer_summary["current_authorization_base_commit"]),
        "current_harness_source_commit": issuer_summary["current_harness_source_commit"],
        "historical_preintegration_review_revision_bound": True,
        "historical_pr109_issuance_review_revision_bound": True,
        "historical_rematerialization_revision_bound": True,
        "fresh_cu129_authorization_review_required": False,
        "fresh_cu129_authorization_issuer_implemented": True,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": issuer_summary["next_gate"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-authority-graph")
    parser.add_argument("--repo-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    summary = validate_repository_authority_graph(args.repo_root)
    for key, value in summary.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Validate the bounded CUDA 12.9 worker-startup observability implementation."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc import (
    cu129_worker_observability_harness_integration as integration,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_cu129_worker_startup_observability_review as review,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_execution_authorization_issuance as issuance,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_kaggle_launcher as launcher,
)
from auragateway.local_abc import (
    full_abc_local_environment_qualification_worker_startup_diagnostics as diagnostics,
)
from auragateway.local_abc.contracts import LocalABCContract

BASE_COMMIT: Final = "997efb4aacf998567a3d92e7202a0054bf473ca4"
IMPLEMENTATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_worker_startup_observability_implementation_v1.json"
)
DIAGNOSTICS_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_worker_startup_diagnostics.py"
)
RUNTIME_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
LAUNCHER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
LAUNCHER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_launcher_v1.ipynb"
)
HARNESS_TOOLCHAIN_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "full_abc_local_environment_qualification_cu129_"
    "worker_observability_harness_toolchain.py"
)
ACTIVE_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
ACTIVE_MATERIALIZATION_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_"
    "environment_qualification_execution_"
    "authorization_v1.json"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-07-22-local-abc-cu129-worker-startup-diagnostics-implementation.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Worker_Startup_Observability_Implementation_Report.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_cu129_worker_startup_observability_implementation_v1.md"
)
ISSUANCE_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_authorization_issuance_v1.md"
)

EXPECTED_IMPLEMENTATION_SHA256: Final = (
    "ba4263eacc8252811b7f708f2a1fa491bf6a02ebc120f2e0c4ad2a10c4e3555a"
)
EXPECTED_ARTIFACT_SHA256: Final = {
    DIAGNOSTICS_PATH: "58d39a67c9d82d1b2f5938328dfa9362ee922ced2e089f8b5d529c0139cc2b91",
    RUNTIME_ADAPTER_PATH: "f83452b6fbfd583f4236c2edbaf0e4bd3a6ece331494fdff891bf50d022ba617",
    LAUNCHER_SOURCE_PATH: "454d5e6fe7f7ff5711710d140f0bece3ee84f3a863a7c33316f784af13724bd0",
    LAUNCHER_NOTEBOOK_PATH: "8477a8f389fe21a925d87c6c4e5b7a71e9de1b1c09910d5d293eadbf6b73db26",
    HARNESS_TOOLCHAIN_PATH: "a8796339caa74229def3af2ab146247707b039e180b2f6898682be6fd80ddbcb",
}
EXPECTED_DOCUMENT_SHA256: Final = {
    ADR_PATH: "95da4d30081eaecad0155782e498ec93fd5b38511e11af7907c5c3153eac9826",
    REPORT_PATH: "ddc609749e63642a7d280c7bda51f2c04fe49a08861101d8d8e8bb7807332ff2",
    RUNBOOK_PATH: "94360a965552a0a2dc7cb4e6047e268124790a8bee22e33aaee76bd863a46dc0",
}
CURRENT_UNCHANGED_ARTIFACT_SHA256: Final = {
    DIAGNOSTICS_PATH: EXPECTED_ARTIFACT_SHA256[DIAGNOSTICS_PATH],
    RUNTIME_ADAPTER_PATH: EXPECTED_ARTIFACT_SHA256[RUNTIME_ADAPTER_PATH],
    HARNESS_TOOLCHAIN_PATH: EXPECTED_ARTIFACT_SHA256[HARNESS_TOOLCHAIN_PATH],
}
HISTORICAL_HARNESS_SOURCE_COMMIT: Final = "426f57dd11dddc2fb8e5a703721c2189abc7a0ff"


class ImplementationError(RuntimeError):
    """Fail-closed worker-observability implementation validation error."""


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ImplementationError(message)


class ImplementationArtifact(LocalABCContract):
    """One exact implementation artifact identity."""

    role: Literal[
        "diagnostics",
        "runtime_adapter",
        "launcher_source",
        "launcher_notebook",
        "post_merge_harness_toolchain",
    ]
    path: str
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("implementation artifact digest must be lowercase SHA-256")
        return value


class HistoricalActiveAuthority(LocalABCContract):
    """Consumed active harness identities that remain historical until rematerialization."""

    harness_source_commit: Literal["426f57dd11dddc2fb8e5a703721c2189abc7a0ff"]
    runtime_adapter_sha256: Literal[
        "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
    ]
    launcher_source_sha256: Literal[
        "7c0f7f1d466fd68a56d6b77c6e16cf69343491710052818743327b51f1d57f16"
    ]
    launcher_notebook_sha256: Literal[
        "7ec60fd0a162f50961f8ff66a6e3dec3c68a15617109fdc7530b2ec380294de9"
    ]
    manifest_sha256: Literal["f7289cee9414d03d88ceb4775198e15ff9446fd99771a58c187de0d4264ef94a"]
    materialization_record_sha256: Literal[
        "284b488dece09e6b17dcf72e4dea69bbdadd440356ce353622b100c38a02100a"
    ]


class DiagnosticControls(LocalABCContract):
    """Bounded diagnostic controls implemented at the worker boundary."""

    maximum_stream_capture_bytes: Literal[32768]
    maximum_diagnostic_bytes: Literal[262144]
    maximum_readiness_polls: Literal[90]
    worker_count: Literal[2]
    hidden_retries_performed: Literal[0]
    workers_replaced: Literal[0]
    raw_environment_included: Literal[False]
    authorization_payload_included: Literal[False]
    model_content_included: Literal[False]


class AuthorityTransition(LocalABCContract):
    """Required authority migration after executable harness changes."""

    active_manifest_promoted: Literal[False]
    historical_harness_reused_as_remediated_lineage: Literal[False]
    existing_authorization_issuer_usable: Literal[False]
    post_merge_harness_source_package_required: Literal[True]
    cpu_only_materialization_required: Literal[True]
    metadata_only_inspection_required: Literal[True]
    fresh_authorization_required_before_retry: Literal[True]


class ImplementationSafety(LocalABCContract):
    """Operational actions prohibited in the implementation PR."""

    authorization_issued: Literal[False]
    kaggle_execution_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    external_spend: Literal[0]
    measured_execution_authorized: Literal[False]


class WorkerStartupObservabilityImplementation(LocalABCContract):
    """Typed implementation decision and blocked post-merge transition."""

    schema_version: Literal["1.0.0"]
    implementation_id: Literal["auragateway-cu129-worker-startup-observability-implementation-v1"]
    repository_base_commit: Literal["997efb4aacf998567a3d92e7202a0054bf473ca4"]
    review_id: Literal["auragateway-cu129-worker-startup-observability-review-v1"]
    decision: Literal["IMPLEMENTED_AWAITING_POST_MERGE_HARNESS_SOURCE_PACKAGE"]
    historical_active_authority: HistoricalActiveAuthority
    implemented_artifacts: tuple[ImplementationArtifact, ...] = Field(min_length=5, max_length=5)
    diagnostic_controls: DiagnosticControls
    authority_transition: AuthorityTransition
    safety: ImplementationSafety
    non_claims: tuple[str, ...] = Field(min_length=8)
    next_gate: Literal["merge_then_build_post_merge_worker_observability_harness_source_package"]

    @model_validator(mode="after")
    def validate_artifact_roles(self) -> Self:
        roles = tuple(artifact.role for artifact in self.implemented_artifacts)
        expected = (
            "diagnostics",
            "runtime_adapter",
            "launcher_source",
            "launcher_notebook",
            "post_merge_harness_toolchain",
        )
        if roles != expected:
            raise ValueError("implementation artifact order or role set drifted")
        return self


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ImplementationError(f"{path.as_posix()} must contain one JSON object")
    return cast(dict[str, object], payload)


def _require_base_ancestor(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        return
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            BASE_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise ImplementationError("worker-observability base commit is not an ancestor")


def _require_exact_identities(
    repo_root: Path,
    expected: dict[Path, str],
    *,
    label: str,
) -> None:
    drift = tuple(
        path.as_posix()
        for path, expected_sha256 in expected.items()
        if not (repo_root / path).is_file() or _sha256(repo_root / path) != expected_sha256
    )
    if drift:
        raise ImplementationError(f"{label} identities drifted: " + ", ".join(drift))


def _require_source_controls(repo_root: Path) -> None:
    diagnostic_source = (repo_root / DIAGNOSTICS_PATH).read_text(encoding="utf-8")
    adapter_source = (repo_root / RUNTIME_ADAPTER_PATH).read_text(encoding="utf-8")
    launcher_source = (repo_root / LAUNCHER_SOURCE_PATH).read_text(encoding="utf-8")
    toolchain_source = (repo_root / HARNESS_TOOLCHAIN_PATH).read_text(encoding="utf-8")
    required = {
        "diagnostics": (
            "MAXIMUM_STREAM_CAPTURE_BYTES: Final = 32 * 1024",
            "MAXIMUM_DIAGNOSTIC_BYTES: Final = 256 * 1024",
            "hidden_retries_performed: Literal[0]",
            "write_diagnostic_atomic",
            "raw_environment_included: Literal[False]",
        ),
        "adapter": (
            "spawn_captured",
            "_CapturedWorkerProcess",
            "readiness_history",
            "failed bounded readiness polling",
            "write_diagnostic_atomic",
        ),
        "launcher": (
            "worker_startup_diagnostic.json",
            "worker_startup_diagnostic_included",
            "load_worker_startup_diagnostic",
            "MAXIMUM_DIAGNOSTIC_BYTES",
        ),
        "toolchain": (
            "REVIEW_MERGE_COMMIT",
            "_require_clean_synchronized_main",
            'accelerator": "none',
            "active_manifest_promoted",
            "FINAL_AUTHORIZATION_PATH",
        ),
    }
    sources = {
        "diagnostics": diagnostic_source,
        "adapter": adapter_source,
        "launcher": launcher_source,
        "toolchain": toolchain_source,
    }
    missing = tuple(
        f"{role}:{marker}"
        for role, markers in required.items()
        for marker in markers
        if marker not in sources[role]
    )
    if missing:
        raise ImplementationError("worker-observability controls drifted: " + ", ".join(missing))
    prohibited = (
        "hidden_retry_count=1",
        "replacement_count=1",
        "authorization_payload_included=True",
        "raw_environment_included=True",
    )
    if any(marker in "\n".join(sources.values()) for marker in prohibited):
        raise ImplementationError("worker-observability source crossed a prohibited boundary")


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    """Validate implementation, historical lineage, and the fresh issuer transition."""

    root = Path(repo_root).resolve()
    _require_base_ancestor(root)
    implementation_path = root / IMPLEMENTATION_PATH
    if _sha256(implementation_path) != EXPECTED_IMPLEMENTATION_SHA256:
        raise ImplementationError("worker-observability implementation record identity drifted")
    payload = _load_json(implementation_path)
    observed = implementation_path.read_text(encoding="utf-8")
    canonical = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    if observed != canonical:
        raise ImplementationError("worker-observability implementation record is not canonical")
    record = WorkerStartupObservabilityImplementation.model_validate(payload)

    _require_exact_identities(
        root,
        CURRENT_UNCHANGED_ARTIFACT_SHA256,
        label="worker-observability implementation artifact",
    )
    _require_exact_identities(root, EXPECTED_DOCUMENT_SHA256, label="implementation document")
    if _sha256(root / ACTIVE_MANIFEST_PATH) != integration.CURRENT_MANIFEST_SHA256:
        raise ImplementationError(
            "active manifest does not bind the inspected worker-observability harness"
        )
    if _sha256(root / ACTIVE_MATERIALIZATION_PATH) != (
        integration.CURRENT_MATERIALIZATION_RECORD_SHA256
    ):
        raise ImplementationError("active materialization record does not bind inspected evidence")
    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise ImplementationError(
            "authorization exists before explicit operator-confirmed issuance"
        )

    expected_by_path = {artifact.path: artifact.sha256 for artifact in record.implemented_artifacts}
    if expected_by_path != {
        path.as_posix(): sha256 for path, sha256 in EXPECTED_ARTIFACT_SHA256.items()
    }:
        raise ImplementationError("implementation record artifact identities drifted")

    _require_source_controls(root)
    if diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES != 32 * 1024:
        raise ImplementationError("worker stream capture budget drifted")
    if diagnostics.MAXIMUM_DIAGNOSTIC_BYTES != 256 * 1024:
        raise ImplementationError("worker diagnostic byte budget drifted")
    if diagnostics.MAXIMUM_READINESS_POLLS != 90:
        raise ImplementationError("worker readiness poll budget drifted")

    review_summary = review.validate_repository_package(root)
    if review_summary.get("observability_implementation_present") is not True:
        raise ImplementationError("worker-observability review does not recognize implementation")
    integration_summary = integration.validate_repository_package(root)
    if integration_summary.get("status") != ("WORKER_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED"):
        raise ImplementationError("worker-observability harness integration drifted")
    if integration_summary.get("source_commit") != integration.SOURCE_COMMIT:
        raise ImplementationError("integrated worker-observability harness source drifted")

    verification = launcher.verify_launcher_notebook(
        repo_root=root,
        notebook_path=root / LAUNCHER_NOTEBOOK_PATH,
    )
    if verification.notebook_sha256 != integration.CURRENT_LAUNCHER_NOTEBOOK_SHA256:
        raise ImplementationError("integrated generated launcher parity drifted")
    if _sha256(root / LAUNCHER_SOURCE_PATH) != integration.CURRENT_LAUNCHER_SOURCE_SHA256:
        raise ImplementationError("integrated launcher source identity drifted")

    issuer_summary = issuance.validate_implementation_package(root)
    if issuer_summary.get("status") != "FRESH_CU129_AUTHORIZATION_ISSUER_READY":
        raise ImplementationError("fresh authorization issuer validation failed")
    if issuer_summary.get("current_authorization_base_commit") != (
        "fba5d25ec831f0ec28a1bcd3d63e9c6d8c4b985b"
    ):
        raise ImplementationError("fresh authorization issuer base commit drifted")
    if issuer_summary.get("current_harness_source_commit") != integration.SOURCE_COMMIT:
        raise ImplementationError("fresh authorization issuer harness binding drifted")
    if issuer_summary.get("runtime_adapter_sha256") != (integration.CURRENT_RUNTIME_ADAPTER_SHA256):
        raise ImplementationError("fresh authorization issuer runtime adapter drifted")
    if issuer_summary.get("worker_startup_diagnostics_sha256") != (
        integration.CURRENT_WORKER_DIAGNOSTICS_SHA256
    ):
        raise ImplementationError("fresh authorization issuer diagnostics binding drifted")
    if issuer_summary.get("launcher_source_sha256") != (integration.CURRENT_LAUNCHER_SOURCE_SHA256):
        raise ImplementationError("fresh authorization issuer launcher source drifted")
    if issuer_summary.get("launcher_notebook_sha256") != verification.notebook_sha256:
        raise ImplementationError("fresh authorization issuer launcher notebook drifted")

    return {
        "status": "WORKER_STARTUP_OBSERVABILITY_HARNESS_EVIDENCE_INTEGRATED",
        "implementation_id": record.implementation_id,
        "review_merge_commit": BASE_COMMIT,
        "historical_harness_source_commit": HISTORICAL_HARNESS_SOURCE_COMMIT,
        "current_harness_source_commit": integration.SOURCE_COMMIT,
        "implemented_runtime_adapter_sha256": (EXPECTED_ARTIFACT_SHA256[RUNTIME_ADAPTER_PATH]),
        "materialized_harness_launcher_source_sha256": (
            EXPECTED_ARTIFACT_SHA256[LAUNCHER_SOURCE_PATH]
        ),
        "active_launcher_source_sha256": integration.CURRENT_LAUNCHER_SOURCE_SHA256,
        "active_launcher_notebook_sha256": verification.notebook_sha256,
        "maximum_stream_capture_bytes": diagnostics.MAXIMUM_STREAM_CAPTURE_BYTES,
        "maximum_diagnostic_bytes": diagnostics.MAXIMUM_DIAGNOSTIC_BYTES,
        "maximum_readiness_polls": diagnostics.MAXIMUM_READINESS_POLLS,
        "fresh_issuer_implemented": True,
        "fresh_authorization_base_commit": issuer_summary["current_authorization_base_commit"],
        "historical_issuer_usable": False,
        "active_manifest_promoted": True,
        "operational_input_closure": "PASSED",
        "authorization_issued": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": issuer_summary["next_gate"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-worker-startup-observability-implementation")
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _build_parser().parse_args(argv)
    result = validate_repository_package(arguments.repo_root)
    for key, value in result.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

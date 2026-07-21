"""Validate repository-only CUDA 12.9 qualification runtime integration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Final, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.local_abc.full_abc_local_environment_qualification import (
    build_qualification_request,
    build_worker_startup_plan,
)
from auragateway.local_abc.full_abc_local_environment_qualification_cu129_runtime import (
    DEPENDENCY_VALIDATION,
    EXPECTED_CONTROL_HASHES,
    EXPECTED_PACKAGE_COUNT,
    INSTALLATION_EXECUTOR,
    LOADER_POLICY,
    PYTHON_STARTUP_POLICY,
    RUNTIME_OUTPUT_DIRECTORY,
    canonical_command_sha256,
    worker_command_template,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution import (
    build_execution_request,
    build_notebook_payload,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution_authorization import (
    build_offline_dataset_manifest_request,
    build_qualification_authorization_request,
)
from auragateway.local_abc.full_abc_local_environment_qualification_execution_contracts import (
    QualificationDatasetManifest,
)
from auragateway.local_abc.full_abc_local_environment_qualification_kaggle_launcher import (
    LAUNCHER_NOTEBOOK_PATH,
    verify_launcher_notebook,
)

INTEGRATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_v1.json"
)
QUALIFICATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_request.json"
)
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
DATASET_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
DATASET_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest_request.json"
)
AUTHORIZATION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_authorization_request.json"
)
REVIEWED_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_full_abc_environment_qualification_v1.ipynb"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
LAUNCHER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeAuthority(_StrictModel):
    runtime_output_directory: str
    resolution_lock_sha256: str
    runtime_manifest_sha256: str
    sha256_manifest_sha256: str
    package_count: int
    installation_executor: str
    dependency_validation: str
    python_startup_policy: str
    loader_policy: str
    vllm_distribution: str
    torch_distribution: str
    transformers_distribution: str


class RuntimeIntegrationDecision(_StrictModel):
    schema_version: str
    integration_id: str
    repository_base_commit: str
    decision: str
    runtime_authority: RuntimeAuthority
    validated_boundaries: list[str] = Field(min_length=9)
    safety: dict[str, object]
    next_gate: str

    @model_validator(mode="after")
    def validate_decision(self) -> RuntimeIntegrationDecision:
        expected_runtime = {
            "runtime_output_directory": RUNTIME_OUTPUT_DIRECTORY,
            "resolution_lock_sha256": EXPECTED_CONTROL_HASHES["resolution_lock.json"],
            "runtime_manifest_sha256": EXPECTED_CONTROL_HASHES["runtime_manifest.json"],
            "sha256_manifest_sha256": EXPECTED_CONTROL_HASHES["sha256_manifest.json"],
            "package_count": EXPECTED_PACKAGE_COUNT,
            "installation_executor": INSTALLATION_EXECUTOR,
            "dependency_validation": DEPENDENCY_VALIDATION,
            "python_startup_policy": PYTHON_STARTUP_POLICY,
            "loader_policy": LOADER_POLICY,
            "vllm_distribution": "0.19.1",
            "torch_distribution": "2.10.0+cu129",
            "transformers_distribution": "5.5.3",
        }
        if self.runtime_authority.model_dump() != expected_runtime:
            raise ValueError("CUDA 12.9 qualification runtime authority drifted")
        if self.repository_base_commit != "e6659de":
            raise ValueError("runtime integration base commit drifted")
        if self.decision != "INTEGRATED_REPOSITORY_ONLY_AUTHORIZATION_BLOCKED":
            raise ValueError("runtime integration decision drifted")
        if self.next_gate != (
            "review_fresh_qualification_authorization_and_control_output_regeneration"
        ):
            raise ValueError("runtime integration next gate drifted")
        prohibited = (
            "authorization_issued",
            "credentials_present",
            "customer_data_present",
            "kaggle_execution_performed",
            "measured_execution_authorized",
            "model_loaded",
            "worker_started",
        )
        if any(self.safety.get(field) is not False for field in prohibited):
            raise ValueError("runtime integration safety boundary drifted")
        if self.safety.get("model_requests_performed") != 0:
            raise ValueError("runtime integration performed model requests")
        if self.safety.get("external_spend") != 0:
            raise ValueError("runtime integration incurred external spend")
        return self


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise RuntimeError(message)


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.as_posix()} must contain one JSON object")
    return cast(dict[str, object], payload)


def _require_canonical_json(path: Path, expected: str) -> None:
    if path.read_text(encoding="utf-8") != expected:
        raise RuntimeError(f"generated artifact drifted: {path.as_posix()}")


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    decision = RuntimeIntegrationDecision.model_validate(_load_json_object(root / INTEGRATION_PATH))

    qualification_request = build_qualification_request()
    worker_plan = build_worker_startup_plan()
    execution_request = build_execution_request()
    dataset_request = build_offline_dataset_manifest_request()
    authorization_request = build_qualification_authorization_request()

    _require_canonical_json(
        root / QUALIFICATION_REQUEST_PATH,
        qualification_request.canonical_json(),
    )
    _require_canonical_json(root / WORKER_PLAN_PATH, worker_plan.canonical_json())
    _require_canonical_json(
        root / EXECUTION_REQUEST_PATH,
        execution_request.canonical_json(),
    )
    _require_canonical_json(root / DATASET_REQUEST_PATH, dataset_request.canonical_json())
    _require_canonical_json(
        root / AUTHORIZATION_REQUEST_PATH,
        authorization_request.canonical_json(),
    )

    manifest = QualificationDatasetManifest.model_validate(
        _load_json_object(root / DATASET_MANIFEST_PATH)
    )
    runtime_entries = tuple(entry for entry in manifest.entries if entry.role == "vllm_runtime")
    if len(runtime_entries) != 1:
        raise RuntimeError("offline manifest must contain one CUDA 12.9 runtime authority")
    runtime_entry = runtime_entries[0]
    if runtime_entry.runtime_output_directory != RUNTIME_OUTPUT_DIRECTORY:
        raise RuntimeError("offline manifest runtime output identity drifted")
    if runtime_entry.package_count != EXPECTED_PACKAGE_COUNT:
        raise RuntimeError("offline manifest runtime package count drifted")

    expected_hashes = {
        "worker_1": canonical_command_sha256(worker_command_template(8001)),
        "worker_2": canonical_command_sha256(worker_command_template(8002)),
    }
    if {worker.worker_id: worker.command_sha256 for worker in worker_plan.workers} != (
        expected_hashes
    ):
        raise RuntimeError("target-runtime worker command identities drifted")

    observed_notebook = _load_json_object(root / REVIEWED_NOTEBOOK_PATH)
    if observed_notebook != build_notebook_payload():
        raise RuntimeError("reviewed qualification notebook drifted")
    verify_launcher_notebook(
        repo_root=root,
        notebook_path=root / LAUNCHER_NOTEBOOK_PATH,
    )

    adapter_source = (root / ADAPTER_PATH).read_text(encoding="utf-8")
    launcher_source = (root / LAUNCHER_SOURCE_PATH).read_text(encoding="utf-8")
    prohibited_active_fragments = (
        'entries["vllm_wheel"]',
        '_EXPECTED_VLLM_VERSION: Final = "0.25.1"',
        "VLLM_WHEEL_PATH",
        "vllm-0.25.1+cu129",
    )
    if any(fragment in adapter_source for fragment in prohibited_active_fragments):
        raise RuntimeError("runtime adapter retains the historical single-wheel path")
    if any(fragment in launcher_source for fragment in prohibited_active_fragments):
        raise RuntimeError("qualification launcher retains the historical single-wheel path")
    if (root / FINAL_AUTHORIZATION_PATH).exists():
        raise RuntimeError("qualification authorization must remain absent")

    return {
        "integration_id": decision.integration_id,
        "integration_status": decision.decision,
        "runtime_output_directory": runtime_entry.runtime_output_directory,
        "runtime_package_count": runtime_entry.package_count,
        "worker_1_command_sha256": expected_hashes["worker_1"],
        "worker_2_command_sha256": expected_hashes["worker_2"],
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": decision.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-qualification-runtime-integration")
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = validate_repository_package(args.repo_root)
    for key, value in result.items():
        rendered = str(value).lower() if isinstance(value, bool) else str(value)
        print(f"{key}={rendered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

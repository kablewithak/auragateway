"""Validate the historical CUDA 12.9 runtime-integration review and its supersession."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Final, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_COMMIT: Final = "daa8df9"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_review_v1.json"
)
INTEGRATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_v1.json"
)
LAUNCHER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
)
MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)

EXPECTED_HISTORICAL_GIT_BLOBS: Final = {
    LAUNCHER_PATH: "c8021c9a0688f689c49a4828110dd1c96911cb5c",
    ADAPTER_PATH: "2f832c487e338d6233fa774dc6a4069f31cfcc30",
    CONTRACTS_PATH: "8f6219793e33096fe02fa7340a7e85fd484c297d",
    MANIFEST_PATH: "a28229afb04b745a901f99d1c04172feed7752f2",
    WORKER_PLAN_PATH: "4729f9668e3c331185fd7c4f191d2e171f5ecad8",
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RuntimeIntegrationReview(_StrictModel):
    schema_version: str
    review_id: str
    repository_base_commit: str
    decision: str
    current_boundary: dict[str, object]
    required_replacement: dict[str, object]
    required_atomic_change_set: list[str] = Field(min_length=8)
    regression_requirements: list[str] = Field(min_length=8)
    next_gate: str
    safety: dict[str, object]

    @model_validator(mode="after")
    def validate_boundary(self) -> RuntimeIntegrationReview:
        if self.repository_base_commit != BASE_COMMIT:
            raise ValueError("runtime integration review base commit drifted")
        if self.decision != "APPROVED_FOR_BOUNDED_CU129_QUALIFICATION_RUNTIME_INTEGRATION":
            raise ValueError("runtime integration review decision drifted")
        if self.next_gate != "implement_atomic_cu129_qualification_runtime_integration":
            raise ValueError("runtime integration review next gate drifted")
        if self.safety.get("model_requests_performed") != 0:
            raise ValueError("runtime integration review performed model requests")
        prohibited = (
            "kaggle_execution_performed",
            "authorization_issued",
            "model_loaded",
            "worker_started",
            "measured_execution_authorized",
            "customer_data_present",
            "credentials_present",
        )
        if any(self.safety.get(field) is not False for field in prohibited):
            raise ValueError("runtime integration review safety boundary drifted")
        return self


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise RuntimeError(message)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.as_posix()} must contain one JSON object")
    return cast(dict[str, object], payload)


def _git_blob_at_revision(repo_root: Path, relative_path: Path, revision: str) -> str:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "rev-parse",
            f"{revision}:{relative_path.as_posix()}",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError(f"historical authority is unavailable: {relative_path.as_posix()}")
    identity = result.stdout.strip()
    if len(identity) != 40 or any(character not in "0123456789abcdef" for character in identity):
        raise RuntimeError(
            f"historical authority returned an invalid Git blob: {relative_path.as_posix()}"
        )
    return identity


def _require_base_ancestor(repo_root: Path) -> None:
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
        text=True,
        timeout=5,
    )
    if result.returncode != 0:
        raise RuntimeError("runtime integration review base commit is not an ancestor")


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    review = RuntimeIntegrationReview.model_validate(_load_json(root / REVIEW_PATH))
    _require_base_ancestor(root)

    historical_drift = tuple(
        sorted(
            relative_path.as_posix()
            for relative_path, expected_blob in EXPECTED_HISTORICAL_GIT_BLOBS.items()
            if _git_blob_at_revision(root, relative_path, BASE_COMMIT) != expected_blob
        )
    )
    if historical_drift:
        raise RuntimeError(
            "one or more pre-integration Git authorities drifted: " + ", ".join(historical_drift)
        )

    integration = _load_json(root / INTEGRATION_PATH)
    required_integration = {
        "decision": "INTEGRATED_REPOSITORY_ONLY_AUTHORIZATION_BLOCKED",
        "repository_base_commit": "e6659de",
        "next_gate": "review_fresh_qualification_authorization_and_control_output_regeneration",
    }
    if any(integration.get(field) != expected for field, expected in required_integration.items()):
        raise RuntimeError("current CUDA 12.9 runtime integration disposition drifted")

    safety = integration.get("safety")
    if not isinstance(safety, dict):
        raise RuntimeError("current runtime integration safety record is invalid")
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
        raise RuntimeError("current runtime integration crossed a prohibited boundary")
    if safety.get("model_requests_performed") != 0:
        raise RuntimeError("current runtime integration performed model requests")

    manifest = _load_json(root / MANIFEST_PATH)
    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 3:
        raise RuntimeError("current offline dataset manifest entry set drifted")
    runtime_entry = entries[2]
    if not isinstance(runtime_entry, dict):
        raise RuntimeError("current runtime dataset entry is invalid")
    if (
        runtime_entry.get("role") != "vllm_runtime"
        or runtime_entry.get("artifact_format") != "python_wheelhouse_directory"
        or runtime_entry.get("package_count") != 176
    ):
        raise RuntimeError("current wheelhouse runtime authority drifted")

    workers = _load_json(root / WORKER_PLAN_PATH).get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise RuntimeError("current worker startup plan drifted")
    for worker in workers:
        if not isinstance(worker, dict):
            raise RuntimeError("current worker startup plan entry is invalid")
        argv = worker.get("command_argv")
        if (
            not isinstance(argv, list)
            or len(argv) < 3
            or argv[0] != "${AURAGATEWAY_TARGET_PYTHON}"
            or argv[1] != "-S"
        ):
            raise RuntimeError("current worker command is not target-runtime controlled")

    return {
        "review_id": review.review_id,
        "review_decision": review.decision,
        "review_disposition": "HISTORICAL_PREINTEGRATION_AUTHORITY",
        "historical_runtime_input": "single_vllm_0_25_1_cu129_wheel",
        "current_runtime_input": "exact_176_package_cu129_wheelhouse",
        "current_integration_status": integration["decision"],
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": integration["next_gate"],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-qualification-runtime-integration-review")
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

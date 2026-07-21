"""Validate the bounded CUDA 12.9 qualification runtime integration review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Final, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_COMMIT: Final = "daa8df9"
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_qualification_runtime_integration_review_v1.json"
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

EXPECTED_CURRENT_SHA256: Final = {
    LAUNCHER_PATH: "523868330501721513f5ea1317d162e408da89486d2ea03ef8cd2a451a94e638",
    ADAPTER_PATH: "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8",
    CONTRACTS_PATH: "69c0412b6bf89ad5eed2bb174f55c1fb621d126767c48147bbc2287a323adcd0",
    MANIFEST_PATH: "9ffd335fad6ac660782be7881625a1fb99a39f5d4a1446f31504154634c91eb7",
    WORKER_PLAN_PATH: "e0385a61f877be2913c4be87813e52ccff50378e65c95160d425a4abce1b3fde",
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


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.as_posix()} must contain one JSON object")
    return cast(dict[str, object], payload)


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    root = Path(repo_root).resolve()
    review = RuntimeIntegrationReview.model_validate(_load_json(root / REVIEW_PATH))

    for relative_path, expected_sha256 in EXPECTED_CURRENT_SHA256.items():
        observed = _sha256(root / relative_path)
        if observed != expected_sha256:
            raise RuntimeError(
                f"captured pre-integration authority drifted: {relative_path.as_posix()}"
            )

    launcher = (root / LAUNCHER_PATH).read_text(encoding="utf-8")
    adapter = (root / ADAPTER_PATH).read_text(encoding="utf-8")
    contracts = (root / CONTRACTS_PATH).read_text(encoding="utf-8")
    manifest = _load_json(root / MANIFEST_PATH)
    worker_plan = _load_json(root / WORKER_PLAN_PATH)

    required_stale_launcher = (
        "VLLM_WHEEL_PATH",
        "vllm-0.25.1+cu129",
        '"vllm_wheel": EXPECTED_VLLM_WHEEL.as_posix()',
    )
    if any(fragment not in launcher for fragment in required_stale_launcher):
        raise RuntimeError("launcher no longer matches the reviewed pre-integration state")

    required_stale_adapter = (
        '_EXPECTED_VLLM_VERSION: Final = "0.25.1"',
        'entries["vllm_wheel"]',
        '"pip",',
        '"--no-deps",',
        '[sys.executable, "-c", script]',
    )
    if any(fragment not in adapter for fragment in required_stale_adapter):
        raise RuntimeError("adapter no longer matches the reviewed pre-integration state")

    if 'Literal["harness_source", "model_artifacts", "vllm_wheel"]' not in contracts:
        raise RuntimeError("dataset role contract no longer matches the reviewed state")
    if '"python_wheel",' not in contracts:
        raise RuntimeError("dataset format contract no longer matches the reviewed state")

    entries = manifest.get("entries")
    if not isinstance(entries, list) or len(entries) != 3:
        raise RuntimeError("offline dataset manifest entry set drifted")
    runtime_entry = entries[2]
    if not isinstance(runtime_entry, dict):
        raise RuntimeError("offline runtime dataset entry is invalid")
    if (
        runtime_entry.get("role") != "vllm_wheel"
        or runtime_entry.get("artifact_format") != "python_wheel"
        or runtime_entry.get("sha256")
        != "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
    ):
        raise RuntimeError("historical single-wheel manifest authority drifted")

    workers = worker_plan.get("workers")
    if not isinstance(workers, list) or len(workers) != 2:
        raise RuntimeError("worker startup plan drifted")
    for worker in workers:
        if not isinstance(worker, dict):
            raise RuntimeError("worker startup plan entry is invalid")
        argv = worker.get("command_argv")
        if not isinstance(argv, list) or not argv or argv[0] != "python":
            raise RuntimeError("historical generic worker interpreter drifted")

    return {
        "review_id": review.review_id,
        "decision": review.decision,
        "current_runtime_input": "single_vllm_0_25_1_cu129_wheel",
        "required_runtime_input": "exact_176_package_cu129_wheelhouse",
        "required_installation_executor": "BASE_PIP_TARGET_DIRECTORY",
        "required_python_startup": "NO_SITE_WITH_CONTROLLED_SITE_BOOTSTRAP",
        "required_loader_policy": "TARGET_NVIDIA_LIBRARIES_PREPENDED",
        "next_gate": review.next_gate,
        "authorization_issued": False,
        "runtime_execution_performed": False,
        "model_requests_performed": 0,
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

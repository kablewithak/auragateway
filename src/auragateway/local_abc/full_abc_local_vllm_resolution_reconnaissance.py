"""Validate the CUDA 12.9 resolution-reconnaissance package and replay reports."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.parse
from collections import Counter, defaultdict
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Self, cast

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,119}$")

PLAN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_resolution_reconnaissance_plan_v1.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_vllm_cu129_resolution_reconnaissance_v1.ipynb")
MATERIALIZER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb"
)
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-resolution-reconnaissance.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_resolution_reconnaissance_v1.md")
RUNTIME_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_runtime_compatibility_remediation_v1.json"
)

NOTEBOOK_NAME: Final = "auragateway-cu129-resolution-reconnaissance-v1"
OUTPUT_DIRECTORY_NAME: Final = "auragateway_vllm_cu129_resolution_reconnaissance_v1"
EXPECTED_NOTEBOOK_SHA256: Final = "541e92aa0b509d0966911904d1c6bb951819aa98abb69f4f7964b724c55afd6a"
EXPECTED_MATERIALIZER_SHA256: Final = (
    "a3e043ba6c2caf982a0ebe14ddd1d102e0b5066a46ff17f6fdbf7e0bf876cf79"
)
EXPECTED_NVIDIA_FAILURE_LOG_SHA256: Final = (
    "f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4"
)
EXPECTED_VLLM_ASSET_SHA256: Final = (
    "71a87f46cafab4489c69a5c5c83b870d0235e5694d8222303d460576293dc719"
)

APPROVED_HOST_AUTHORITIES: Final = {
    "download.pytorch.org": "pytorch",
    "download-r2.pytorch.org": "pytorch",
    "files.pythonhosted.org": "pypi",
    "github.com": "github_release",
    "objects.githubusercontent.com": "github_release",
    "release-assets.githubusercontent.com": "github_release",
}
CANDIDATE_HOST_AUTHORITIES: Final = {"pypi.nvidia.com": "nvidia"}


class AuthorityName(StrEnum):
    """Artifact source authorities used during reconnaissance."""

    GITHUB_RELEASE = "github_release"
    NVIDIA = "nvidia"
    PYPI = "pypi"
    PYTORCH = "pytorch"
    UNKNOWN = "unknown"


class AuthorityState(StrEnum):
    """Review state for one observed exact hostname."""

    APPROVED = "approved"
    REVIEW_REQUIRED = "review_required"


class HistoricalFailureV1(LocalABCContract):
    """One preserved materializer failure."""

    attempt: int
    classification: str
    code: str
    execution_log_sha256: str
    historical_kaggle_title: str
    first_divergence: str
    dependency_resolution_completed: bool
    wheel_downloads_performed: Literal[0]
    observed_distribution: str | None = None
    observed_host: str | None = None

    @field_validator("execution_log_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("historical failure log identity must be lowercase SHA-256")
        return value


class ReconnaissanceArtifactsV1(LocalABCContract):
    """Bound repository and Kaggle identities."""

    notebook: Literal["notebooks/auragateway_vllm_cu129_resolution_reconnaissance_v1.ipynb"]
    notebook_sha256: Literal["541e92aa0b509d0966911904d1c6bb951819aa98abb69f4f7964b724c55afd6a"]
    kaggle_title: Literal["auragateway-cu129-resolution-reconnaissance-v1"]
    output_directory: Literal["auragateway_vllm_cu129_resolution_reconnaissance_v1"]
    runbook: Literal["docs/runbooks/local_abc_vllm_cu129_resolution_reconnaissance_v1.md"]
    adr: Literal["docs/adr/2026-07-20-local-abc-vllm-resolution-reconnaissance.md"]


class ReconnaissanceContractV1(LocalABCContract):
    """Non-execution reconnaissance boundary."""

    run_mode: Literal["RESOLUTION_ONLY"]
    accelerator: Literal["none"]
    internet_required: Literal[True]
    inputs_required: Literal[0]
    package_installation_performed: Literal[False]
    pip_download_command_performed: Literal[False]
    wheel_files_written: Literal[0]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]
    authorization_issued: Literal[False]
    collect_all_policy_violations: Literal[True]
    retain_sanitized_resolution_report: Literal[True]
    retain_host_inventory: Literal[True]
    retain_authority_inventory: Literal[True]
    retain_historical_context: Literal[True]


class ReconnaissancePlanV1(LocalABCContract):
    """Typed plan for the resolution-only diagnostic gate."""

    schema_version: Literal["1.0.0"]
    plan_id: Literal["auragateway-vllm-cu129-resolution-reconnaissance-v1"]
    decision: Literal["RUN_RESOLUTION_RECONNAISSANCE_BEFORE_MATERIALIZATION"]
    source_commit: Literal["ebf892bc9e5b38aaee9d7a32e754a165b1c77d81"]
    selected_runtime: dict[str, str]
    artifacts: ReconnaissanceArtifactsV1
    historical_failures: tuple[HistoricalFailureV1, HistoricalFailureV1, HistoricalFailureV1]
    historical_runtime_context: dict[str, object]
    static_materializer_findings: tuple[dict[str, object], ...]
    reconnaissance_contract: ReconnaissanceContractV1
    initial_authority_policy: dict[str, object]
    required_outputs: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    next_gate: Literal["review_complete_source_authority_inventory"]
    safety: dict[str, object]

    @model_validator(mode="after")
    def validate_plan(self) -> Self:
        if tuple(item.attempt for item in self.historical_failures) != (1, 2, 3):
            raise ValueError("historical failures must preserve attempts 1 through 3")
        if self.historical_failures[2].execution_log_sha256 != (EXPECTED_NVIDIA_FAILURE_LOG_SHA256):
            raise ValueError("NVIDIA host failure identity drifted")
        expected_runtime = {
            "python": "3.12",
            "cuda_variant": "cu129",
            "vllm": "0.19.1",
            "torch": "2.10.0+cu129",
            "torchaudio": "2.10.0+cu129",
            "torchvision": "0.25.0+cu129",
            "transformers": "5.5.3",
        }
        if self.selected_runtime != expected_runtime:
            raise ValueError("selected runtime drifted")
        return self


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected one JSON object: {path.as_posix()}")
    return cast(dict[str, object], payload)


def normalize_distribution_name(value: str) -> str:
    """Normalize one distribution name for deterministic policy evaluation."""

    return value.lower().replace("_", "-")[:120]


def expected_authority(distribution_name: str) -> AuthorityName:
    """Return the required package authority for one distribution family."""

    normalized = normalize_distribution_name(distribution_name)
    if normalized == "vllm":
        return AuthorityName.GITHUB_RELEASE
    if normalized in {"torch", "torchaudio", "torchvision"}:
        return AuthorityName.PYTORCH
    if normalized.startswith("nvidia-"):
        return AuthorityName.NVIDIA
    return AuthorityName.PYPI


def observed_authority(hostname: str) -> tuple[AuthorityName, AuthorityState]:
    """Classify an exact host without wildcard trust."""

    approved = APPROVED_HOST_AUTHORITIES.get(hostname)
    if approved is not None:
        return AuthorityName(approved), AuthorityState.APPROVED
    candidate = CANDIDATE_HOST_AUTHORITIES.get(hostname)
    if candidate is not None:
        return AuthorityName(candidate), AuthorityState.REVIEW_REQUIRED
    return AuthorityName.UNKNOWN, AuthorityState.REVIEW_REQUIRED


def _archive_sha256(archive_info: object) -> str | None:
    if not isinstance(archive_info, dict):
        return None
    hash_value = archive_info.get("hash")
    if isinstance(hash_value, str) and hash_value.startswith("sha256="):
        digest = hash_value.removeprefix("sha256=")
        if _SHA256_PATTERN.fullmatch(digest) is not None:
            return digest
    hashes = archive_info.get("hashes")
    if isinstance(hashes, dict):
        sha256_value = hashes.get("sha256")
        if isinstance(sha256_value, str) and _SHA256_PATTERN.fullmatch(sha256_value) is not None:
            return sha256_value
    return None


def evaluate_resolution_report(payload: dict[str, object]) -> dict[str, object]:
    """Evaluate every pip install record and aggregate all policy violations."""

    install = payload.get("install")
    if not isinstance(install, list):
        raise ValueError("pip resolution report must contain an install list")

    records: list[dict[str, object]] = []
    violations: list[dict[str, object]] = []

    for index, item in enumerate(install):
        if not isinstance(item, dict):
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": f"invalid-record-{index}",
                    "hostname": "missing",
                    "failure_code": "RESOLUTION_RECORD_INVALID",
                }
            )
            continue

        metadata = item.get("metadata")
        download_info = item.get("download_info")
        if not isinstance(metadata, dict) or not isinstance(download_info, dict):
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": f"unknown-record-{index}",
                    "hostname": "missing",
                    "failure_code": "RESOLUTION_RECORD_INCOMPLETE",
                }
            )
            continue

        name = str(metadata.get("name", f"unknown-record-{index}"))
        version = str(metadata.get("version", "missing"))
        raw_url = download_info.get("url")
        if not isinstance(raw_url, str):
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalize_distribution_name(name),
                    "hostname": "missing",
                    "failure_code": "RESOLVED_ARTIFACT_URL_MISSING",
                }
            )
            continue

        parsed = urllib.parse.urlsplit(raw_url)
        hostname = parsed.hostname or "missing"
        normalized = normalize_distribution_name(name)
        expected = expected_authority(name)
        observed, state = observed_authority(hostname)
        digest = _archive_sha256(download_info.get("archive_info"))

        records.append(
            {
                "record_index": index,
                "distribution_name": name[:120],
                "normalized_name": normalized,
                "version": version[:120],
                "expected_authority": expected.value,
                "observed_authority": observed.value,
                "authority_state": state.value,
                "scheme": parsed.scheme or "missing",
                "hostname": hostname,
                "artifact_filename": PurePosixPath(parsed.path).name or "missing",
                "sha256": digest,
            }
        )

        if parsed.scheme != "https":
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalized,
                    "hostname": hostname,
                    "failure_code": "ARTIFACT_URL_SCHEME_UNSAFE",
                }
            )
        if parsed.username is not None or parsed.password is not None:
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalized,
                    "hostname": hostname,
                    "failure_code": "ARTIFACT_URL_CREDENTIALS_PRESENT",
                }
            )
        if parsed.fragment:
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalized,
                    "hostname": hostname,
                    "failure_code": "ARTIFACT_URL_FRAGMENT_PRESENT",
                }
            )
        if digest is None:
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalized,
                    "hostname": hostname,
                    "failure_code": "ARTIFACT_SHA256_MISSING",
                }
            )
        if state is AuthorityState.REVIEW_REQUIRED:
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalized,
                    "hostname": hostname,
                    "failure_code": "ARTIFACT_HOST_REVIEW_REQUIRED",
                }
            )
        elif observed is not expected:
            violations.append(
                {
                    "record_index": index,
                    "distribution_name": normalized,
                    "hostname": hostname,
                    "failure_code": "PACKAGE_AUTHORITY_MISMATCH",
                }
            )

    normalized_names = [str(record["normalized_name"]) for record in records]
    for name, count in Counter(normalized_names).items():
        if count > 1:
            violations.append(
                {
                    "record_index": -1,
                    "distribution_name": name,
                    "hostname": "multiple",
                    "failure_code": "DUPLICATE_DISTRIBUTION_IDENTITY",
                }
            )

    host_distributions: dict[str, set[str]] = defaultdict(set)
    for record in records:
        host_distributions[str(record["hostname"])].add(str(record["normalized_name"]))

    records.sort(key=lambda item: (str(item["normalized_name"]), str(item["version"])))
    violations.sort(
        key=lambda item: (
            str(item["failure_code"]),
            str(item["distribution_name"]),
            str(item["hostname"]),
            cast(int, item["record_index"]),
        )
    )
    hosts = [
        {
            "hostname": hostname,
            "distribution_count": len(distributions),
            "distributions": sorted(distributions),
        }
        for hostname, distributions in sorted(host_distributions.items())
    ]
    return {
        "status": (
            "RESOLUTION_RECONNAISSANCE_POLICY_COMPLETE"
            if not violations
            else "RESOLUTION_RECONNAISSANCE_REVIEW_REQUIRED"
        ),
        "resolved_artifacts": records,
        "host_inventory": hosts,
        "violations": violations,
    }


def _notebook_source(payload: dict[str, object]) -> str:
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("reconnaissance notebook cells are missing")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise RuntimeError("reconnaissance notebook must contain exactly one code cell")
    source = code_cells[0].get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    if isinstance(source, str):
        return source
    raise RuntimeError("reconnaissance notebook source is invalid")


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate the plan, unexecuted notebook, historical evidence, and pause gate."""

    root = repo_root.resolve()
    plan = ReconnaissancePlanV1.model_validate(_load_json_object(root / PLAN_PATH))

    notebook_payload = _load_json_object(root / NOTEBOOK_PATH)
    metadata = notebook_payload.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("reconnaissance notebook metadata is missing")
    auragateway = metadata.get("auragateway")
    expected_metadata = {
        "notebook_name": NOTEBOOK_NAME,
        "diagnostic_only": True,
        "internet_required": True,
        "accelerator": "none",
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_requests_permitted": 0,
        "qualification_claimed": False,
    }
    if not isinstance(auragateway, dict) or any(
        auragateway.get(key) != value for key, value in expected_metadata.items()
    ):
        raise RuntimeError("reconnaissance notebook metadata drifted")

    for cell in cast(list[object], notebook_payload.get("cells", [])):
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None or cell.get("outputs") != []:
            raise RuntimeError("reconnaissance notebook contains execution state")

    source = _notebook_source(notebook_payload)
    compile(source, NOTEBOOK_PATH.as_posix(), "exec")
    required_fragments = (
        f'NOTEBOOK_NAME = "{NOTEBOOK_NAME}"',
        'OUTPUT_DIRECTORY_NAME = "auragateway_vllm_cu129_resolution_reconnaissance_v1"',
        '"--dry-run"',
        '"--report"',
        '"pypi.nvidia.com": "nvidia"',
        '"ARTIFACT_HOST_REVIEW_REQUIRED"',
        '"MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT"',
        '"wheel_files_written": len(tuple(OUTPUT_ROOT.rglob("*.whl")))',
        '"package_installation_performed": False',
        '"model_requests_performed": 0',
        '"qualification_claimed": False',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError(
            "reconnaissance notebook lacks reviewed fragments: " + ", ".join(missing)
        )
    if _file_sha256(root / NOTEBOOK_PATH) != EXPECTED_NOTEBOOK_SHA256:
        raise RuntimeError("reconnaissance notebook raw identity drifted")

    materializer_source = _notebook_source(_load_json_object(root / MATERIALIZER_PATH))
    materializer_findings = (
        '"vllm-0.19.1+cu128-"',
        '"torch-2.10.0+cu128-"',
        '"torchaudio-2.10.0+cu128-"',
        '"torchvision-0.25.0+cu128-"',
    )
    if _file_sha256(root / MATERIALIZER_PATH) != EXPECTED_MATERIALIZER_SHA256:
        raise RuntimeError("paused materializer identity drifted")
    if any(fragment not in materializer_source for fragment in materializer_findings):
        raise RuntimeError("known materializer prefix drift is no longer represented by the plan")

    runtime_record = _load_json_object(root / RUNTIME_RECORD_PATH)
    if runtime_record.get("schema_version") != "1.5.0":
        raise RuntimeError("runtime remediation schema version drifted")
    if runtime_record.get("decision") != "PAUSED_FOR_CU129_RESOLUTION_RECONNAISSANCE":
        raise RuntimeError("runtime materialization pause decision drifted")
    if runtime_record.get("next_gate") != "run_cu129_resolution_reconnaissance":
        raise RuntimeError("runtime next gate drifted")

    nvidia_failure = runtime_record.get("materializer_nvidia_failure")
    if not isinstance(nvidia_failure, dict):
        raise RuntimeError("NVIDIA host failure is missing")
    if nvidia_failure.get("execution_log_sha256") != EXPECTED_NVIDIA_FAILURE_LOG_SHA256:
        raise RuntimeError("NVIDIA host failure-log identity drifted")
    if nvidia_failure.get("observed_host") != "pypi.nvidia.com":
        raise RuntimeError("NVIDIA host failure evidence drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_doc_fragments = (
        NOTEBOOK_NAME,
        OUTPUT_DIRECTORY_NAME,
        EXPECTED_NVIDIA_FAILURE_LOG_SHA256,
        "MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT",
        "collect all policy violations",
    )
    if any(fragment not in adr for fragment in required_doc_fragments):
        raise RuntimeError("reconnaissance ADR drifted")
    if any(fragment not in runbook for fragment in required_doc_fragments):
        raise RuntimeError("reconnaissance runbook drifted")

    return {
        "status": "VLLM_RESOLUTION_RECONNAISSANCE_PACKAGE_VALID",
        "plan_sha256": _file_sha256(root / PLAN_PATH),
        "notebook_sha256": _file_sha256(root / NOTEBOOK_PATH),
        "historical_failure_count": len(plan.historical_failures),
        "nvidia_failure_log_sha256": EXPECTED_NVIDIA_FAILURE_LOG_SHA256,
        "candidate_host_count": len(CANDIDATE_HOST_AUTHORITIES),
        "approved_host_count": len(APPROVED_HOST_AUTHORITIES),
        "materializer_paused": True,
        "package_installation_performed": False,
        "model_requests_performed": 0,
        "qualification_claimed": False,
        "authorization_issued": False,
        "next_gate": plan.next_gate,
    }


def main() -> int:
    """Validate the repository reconnaissance package and print canonical JSON."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(_canonical_json(validate_repository_package(args.repo_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

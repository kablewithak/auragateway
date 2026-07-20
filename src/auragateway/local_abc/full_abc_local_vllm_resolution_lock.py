"""Validate the reviewed CUDA 12.9 resolution lock and materializer binding."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Self, cast

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

LOCK_PATH: Final = Path("benchmarks/local_abc/auragateway_vllm_cu129_resolution_lock_v1.json")
RESULT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_resolution_reconnaissance_result_v1.json"
)
MATERIALIZER_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb"
)
EVIDENCE_DIRECTORY: Final = Path("evidence_vault/local_abc/vllm-cu129-resolution-reconnaissance-v1")
SOURCE_IDENTITY_PATH: Final = EVIDENCE_DIRECTORY / "source_evidence_identity.json"
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu129-exact-resolution-lock.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_wheelhouse_materialization_v1.md")

EXPECTED_LOCK_SHA256: Final = "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
EXPECTED_MATERIALIZER_SHA256: Final = (
    "d836a61bc7ed7a0d6c26eca68a28ed22e685e5a6705bf16ce4f6dbb8168f7ba2"
)
EXPECTED_RESULTS_ZIP_SHA256: Final = (
    "a035b21fe5795816e888886003c3dd6c73dbda162370805be687b28f8cef4399"
)
EXPECTED_EXECUTION_LOG_SHA256: Final = (
    "3455a8e631157a0c4e4c66e3e5e23c0e4cb41236e6b7d1016811b357488a2269"
)
EXPECTED_PACKAGE_COUNT: Final = 176
EXPECTED_HOST_COUNT: Final = 5
EXPECTED_HOST_COUNTS: Final = {
    "download-r2.pytorch.org": 4,
    "download.pytorch.org": 3,
    "files.pythonhosted.org": 153,
    "github.com": 1,
    "pypi.nvidia.com": 15,
}


class LockedArtifactV1(LocalABCContract):
    """One exact reviewed artifact identity."""

    normalized_name: str
    version: str
    hostname: str
    source_authority: str
    artifact_filename: str
    sanitized_url: str
    url_sha256: str
    sha256: str

    @field_validator("normalized_name", "version", "hostname", "artifact_filename")
    @classmethod
    def validate_bounded_text(cls, value: str) -> str:
        if not value or len(value) > 240:
            raise ValueError("locked artifact text fields must be non-empty and bounded")
        return value

    @field_validator("url_sha256", "sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact identities must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_url(self) -> Self:
        from urllib.parse import urlsplit

        parsed = urlsplit(self.sanitized_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != self.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("sanitized URL violates the exact source contract")
        if PurePosixPath(parsed.path).name != self.artifact_filename:
            raise ValueError("artifact filename and sanitized URL disagree")
        return self


class HostDecisionV1(LocalABCContract):
    """Exact-host decision for the reviewed closure."""

    hostname: str
    source_authority: str
    distribution_count: int
    decision: Literal["approved_only_for_exact_locked_artifacts"]


class ResolutionLockV1(LocalABCContract):
    """The complete reviewed CUDA 12.9 closure."""

    schema_version: Literal["1.0.0"]
    lock_id: Literal["auragateway-vllm-cu129-resolution-lock-v1"]
    source_commit: Literal["28def78afd5fcfe84d219efac9a0317dedad73b5"]
    source_evidence: dict[str, str]
    selected_runtime: dict[str, str]
    review_decision: Literal["APPROVED_AS_EXACT_LOCKED_CLOSURE"]
    package_count: Literal[176]
    host_count: Literal[5]
    exact_host_policy: tuple[
        HostDecisionV1,
        HostDecisionV1,
        HostDecisionV1,
        HostDecisionV1,
        HostDecisionV1,
    ]
    wildcard_domains_permitted: Literal[False]
    records: tuple[LockedArtifactV1, ...]
    non_claims: tuple[str, ...]

    @model_validator(mode="after")
    def validate_lock(self) -> Self:
        if len(self.records) != self.package_count:
            raise ValueError("resolution lock package count drifted")
        names = tuple(record.normalized_name for record in self.records)
        if len(names) != len(set(names)) or names != tuple(sorted(names)):
            raise ValueError("locked distribution identities must be unique and sorted")
        digests = tuple(record.sha256 for record in self.records)
        if len(digests) != len(set(digests)):
            raise ValueError("locked artifact SHA-256 identities must be unique")
        host_counts: dict[str, int] = {}
        for record in self.records:
            host_counts[record.hostname] = host_counts.get(record.hostname, 0) + 1
        if host_counts != EXPECTED_HOST_COUNTS:
            raise ValueError("locked exact-host inventory drifted")
        policy_counts = {item.hostname: item.distribution_count for item in self.exact_host_policy}
        if policy_counts != EXPECTED_HOST_COUNTS:
            raise ValueError("host policy counts disagree with locked records")
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


def _notebook_source(path: Path) -> str:
    payload = _load_json_object(path)
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("materializer notebook cells are missing")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise RuntimeError("materializer notebook must contain exactly one code cell")
    cell = code_cells[0]
    if cell.get("execution_count") is not None or cell.get("outputs") != []:
        raise RuntimeError("materializer notebook contains execution state")
    source = cell.get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    raise RuntimeError("materializer notebook source is invalid")


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate evidence, exact lock, materializer binding, and next-gate safety."""

    root = repo_root.resolve()
    lock = ResolutionLockV1.model_validate(_load_json_object(root / LOCK_PATH))

    if _file_sha256(root / LOCK_PATH) != EXPECTED_LOCK_SHA256:
        raise RuntimeError("resolution lock raw identity drifted")
    if lock.source_evidence.get("results_zip_sha256") != EXPECTED_RESULTS_ZIP_SHA256:
        raise RuntimeError("reconnaissance ZIP identity drifted")
    if lock.source_evidence.get("execution_log_sha256") != EXPECTED_EXECUTION_LOG_SHA256:
        raise RuntimeError("reconnaissance log identity drifted")

    result = _load_json_object(root / RESULT_PATH)
    if result.get("decision") != "RECONNAISSANCE_ACCEPTED_AND_LOCKED":
        raise RuntimeError("reconnaissance review decision drifted")
    review = result.get("review_resolution")
    if not isinstance(review, dict) or review.get("resolution_lock_sha256") != EXPECTED_LOCK_SHA256:
        raise RuntimeError("reconnaissance result does not bind the exact lock")
    if review.get("artifact_transfer_observed_during_pip_dry_run") is not True:
        raise RuntimeError("artifact-transfer semantics were not preserved")

    identity = _load_json_object(root / SOURCE_IDENTITY_PATH)
    if identity.get("results_zip_sha256") != EXPECTED_RESULTS_ZIP_SHA256:
        raise RuntimeError("evidence-vault ZIP identity drifted")
    if identity.get("execution_log_sha256") != EXPECTED_EXECUTION_LOG_SHA256:
        raise RuntimeError("evidence-vault log identity drifted")
    files = identity.get("source_files")
    if not isinstance(files, list) or len(files) != 11:
        raise RuntimeError("reconnaissance evidence manifest must contain 11 source files")
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("reconnaissance evidence entry is invalid")
        relative_raw = entry.get("path")
        if not isinstance(relative_raw, str):
            raise RuntimeError("reconnaissance evidence path is invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("reconnaissance evidence path is unsafe")
        path = root / EVIDENCE_DIRECTORY / Path(*relative.parts)
        if (
            not path.is_file()
            or path.is_symlink()
            or entry.get("sha256") != _file_sha256(path)
            or entry.get("size_bytes") != path.stat().st_size
        ):
            raise RuntimeError("reconnaissance evidence identity drifted")

    source = _notebook_source(root / MATERIALIZER_PATH)
    compile(source, MATERIALIZER_PATH.as_posix(), "exec")
    required_fragments = (
        f'RESOLUTION_LOCK_SHA256 = "{EXPECTED_LOCK_SHA256}"',
        "EXPECTED_PACKAGE_COUNT = 176",
        '"pypi.nvidia.com"',
        '"RESOLUTION_LOCK_MISMATCH"',
        '"UNEXPECTED_RESOLVED_DISTRIBUTION"',
        '"LOCKED_DISTRIBUTION_MISSING"',
        '"torch-2.10.0+cu129-"',
        '"torchaudio-2.10.0+cu129-"',
        '"torchvision-0.25.0+cu129-"',
        '"pip_resolution_artifact_transfer_observed"',
        '"pip_download_subcommand_performed": True',
        '"package_installation_performed": False',
    )
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError("materializer lacks exact-lock fragments: " + ", ".join(missing))
    prohibited_fragments = (
        '"torch-2.10.0+cu128-"',
        '"torchaudio-2.10.0+cu128-"',
        '"torchvision-0.25.0+cu128-"',
        '"vllm-0.19.1+cu128-"',
    )
    if any(fragment in source for fragment in prohibited_fragments):
        raise RuntimeError("stale cu128 materializer prefix remains")
    if _file_sha256(root / MATERIALIZER_PATH) != EXPECTED_MATERIALIZER_SHA256:
        raise RuntimeError("exact-lock materializer raw identity drifted")

    adr = (root / ADR_PATH).read_text(encoding="utf-8")
    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    for fragment in (
        EXPECTED_LOCK_SHA256,
        "176",
        "approved only for the exact locked artifacts",
    ):
        if fragment not in adr:
            raise RuntimeError("exact-lock ADR drifted")
    for fragment in (EXPECTED_LOCK_SHA256, "package_count=176", "zero downloads"):
        if fragment not in runbook:
            raise RuntimeError("exact-lock runbook drifted")

    return {
        "status": "VLLM_CU129_EXACT_RESOLUTION_LOCK_PACKAGE_VALID",
        "resolution_lock_sha256": EXPECTED_LOCK_SHA256,
        "materializer_notebook_sha256": EXPECTED_MATERIALIZER_SHA256,
        "package_count": lock.package_count,
        "host_count": lock.host_count,
        "results_zip_sha256": EXPECTED_RESULTS_ZIP_SHA256,
        "execution_log_sha256": EXPECTED_EXECUTION_LOG_SHA256,
        "artifact_transfer_observed_during_reconnaissance": True,
        "package_installation_performed": False,
        "model_requests_performed": 0,
        "qualification_claimed": False,
        "authorization_issued": False,
        "next_gate": "materialize_exact_locked_cu129_wheelhouse",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(_canonical_json(validate_repository_package(args.repo_root)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

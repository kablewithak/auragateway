"""Validate the current CUDA 12.9 harness-rematerialization review boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, model_validator

from auragateway.local_abc.contracts import LocalABCContract

BASE_COMMIT: Final = "16decd4e0d91c4baa18129b0d7afc69bb2630aa1"
HISTORICAL_HARNESS_SOURCE_COMMIT: Final = "be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"

REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_current_harness_rematerialization_review_v1.json"
)
HISTORICAL_NOTEBOOK_PATH: Final = Path(
    "evidence_vault/local_abc/harness-materializer-input-v3/ag-harness-materializer-input-v3.ipynb"
)
HISTORICAL_IDENTITY_PATH: Final = Path(
    "evidence_vault/local_abc/harness-materializer-input-v3/source_evidence_identity.json"
)

EXECUTION_CONTRACTS_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_execution_contracts.py"
)
RUNTIME_ADAPTER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_runtime_adapter.py"
)
CU129_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_cu129_runtime.py"
)
LAUNCHER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_manifest.json"
)
MATERIALIZATION_RECORD_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/offline_dataset_materialization_record.json"
)
EXECUTION_REQUEST_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/qualification_execution_request.json"
)
WORKER_PLAN_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/worker_startup_plan.json"
)
LAUNCHER_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_full_run_environment_qualification_kaggle_launcher_v1.md"
)
FINAL_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)
ADR_PATH: Final = Path("docs/adr/2026-07-21-local-abc-cu129-current-harness-rematerialization.md")
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_CU129_Current_Harness_Rematerialization_Review.md"
)

EXPECTED_CURRENT_SHA256: Final = {
    EXECUTION_CONTRACTS_PATH: ("644e4013a753010bb1204e4bcc73e4e133a071ccc70213bca27dd24b74f8c0a0"),
    RUNTIME_ADAPTER_PATH: ("aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"),
    CU129_RUNTIME_PATH: ("9230a4f06238b87c3b537f383aceda0de44c41c8c6b21c1d6b35666440a5445c"),
    LAUNCHER_PATH: ("0c9b10bef8cb58c8139d4c0de5f299d75f1bc0a70b733742d1876fe4c3e30cdb"),
    MANIFEST_PATH: ("0382604c6b673d832a1bf93031a4f5db79029be7e2d564354115dab9244c14e4"),
    MATERIALIZATION_RECORD_PATH: (
        "faa842a9c94d41b51b44a56277df56d3c7d2cfccd0c0c2ad33d85161dedebd9a"
    ),
    EXECUTION_REQUEST_PATH: ("7b0080429246f6def3c1ac28b8a677a2ed7e29ccf318690d9309ed98ff179ba0"),
    WORKER_PLAN_PATH: ("45bd37e50e663e514a3bac7b3ca22a678015dc5d5472f84bab3381123244262c"),
    LAUNCHER_RUNBOOK_PATH: ("0f309a6fd2bb72579386581f565dfb70105e31c7a795e274067cc3d0c38160d4"),
}

EXPECTED_HISTORICAL_SHA256: Final = {
    EXECUTION_CONTRACTS_PATH: ("69c0412b6bf89ad5eed2bb174f55c1fb621d126767c48147bbc2287a323adcd0"),
    RUNTIME_ADAPTER_PATH: ("78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"),
    LAUNCHER_PATH: ("040d6d47a07cba68fd0852ea175a4d2b92e6d5819775ce3152fd99f61d4a2066"),
    MANIFEST_PATH: ("ddc1e1fc9e5ba61212dafad8d7196eb17699b6103083b6f9678dce83ca0a74c2"),
    MATERIALIZATION_RECORD_PATH: (
        "705881978f5a612a4bc1d131fdc96508fd8fb4a78c73e384df6968eb54bbb7a3"
    ),
    EXECUTION_REQUEST_PATH: ("dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"),
    WORKER_PLAN_PATH: ("e0385a61f877be2913c4be87813e52ccff50378e65c95160d425a4abce1b3fde"),
}

HISTORICAL_NOTEBOOK_SHA256: Final = (
    "91f9ccc30883341af4cfd24d11c780ee136b9f7ccf9316b77b9d72ba559312c2"
)
HISTORICAL_DIRECTORY_SHA256: Final = (
    "4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e"
)
CURRENT_RUNTIME_RESOLUTION_LOCK_SHA256: Final = (
    "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
)
HISTORICAL_HARNESS_OUTPUT_DIRECTORY: Final = "auragateway_qualification_harness_be1bfad_v1"
HISTORICAL_HARNESS_MOUNTED_PATH: Final = (
    "/kaggle/input/notebooks/kabomolefe/ag-harness-materializer-input-v3/"
    f"{HISTORICAL_HARNESS_OUTPUT_DIRECTORY}"
)


class HistoricalMaterializerEvidence(LocalABCContract):
    """Exact historical source evidence recovered from Kaggle."""

    notebook_raw_sha256: Literal["91f9ccc30883341af4cfd24d11c780ee136b9f7ccf9316b77b9d72ba559312c2"]
    notebook_name: Literal["ag-harness-materializer-input-v3"]
    source_commit: Literal["be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"]
    output_directory: Literal["auragateway_qualification_harness_be1bfad_v1"]
    directory_sha256: Literal["4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e"]
    file_count: Literal[953]
    total_bytes: Literal[8879194]
    classification: Literal["CONSUMED_HISTORICAL_MATERIALIZER_SOURCE"]


class ObservedCurrentBoundary(LocalABCContract):
    """Current repository state that makes rematerialization mandatory."""

    launcher_harness_source_commit: Literal["be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"]
    launcher_harness_output_directory: Literal["auragateway_qualification_harness_be1bfad_v1"]
    current_runtime_role: Literal["vllm_runtime"]
    current_runtime_artifact_format: Literal["python_wheelhouse_directory"]
    current_runtime_package_count: Literal[176]
    current_runtime_resolution_lock_sha256: Literal[
        "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
    ]
    historical_runtime_adapter_sha256: Literal[
        "78870b1a7e27de9931f0f58e11613110dc642ba0d4a934ca149576e4e86412d8"
    ]
    current_runtime_adapter_sha256: Literal[
        "aec461dcd595bfa3af286d88832ec7ef1ca2b416adca6a548f102d9543fb8dba"
    ]
    historical_execution_contracts_sha256: Literal[
        "69c0412b6bf89ad5eed2bb174f55c1fb621d126767c48147bbc2287a323adcd0"
    ]
    current_execution_contracts_sha256: Literal[
        "644e4013a753010bb1204e4bcc73e4e133a071ccc70213bca27dd24b74f8c0a0"
    ]
    historical_execution_request_sha256: Literal[
        "dcef7e7243f4de16955bccdfc36dbd0194b51a602d1fc67f5c6fa375ca529e28"
    ]
    current_execution_request_sha256: Literal[
        "7b0080429246f6def3c1ac28b8a677a2ed7e29ccf318690d9309ed98ff179ba0"
    ]
    historical_worker_plan_sha256: Literal[
        "e0385a61f877be2913c4be87813e52ccff50378e65c95160d425a4abce1b3fde"
    ]
    current_worker_plan_sha256: Literal[
        "45bd37e50e663e514a3bac7b3ca22a678015dc5d5472f84bab3381123244262c"
    ]
    current_cu129_runtime_module_present: Literal[True]
    final_authorization_present: Literal[False]
    launcher_runbook_runtime_input_instruction: Literal["STALE_SINGLE_WHEEL_RESOURCE"]


class ReviewSafety(LocalABCContract):
    """Prohibited activity remains absent during the review."""

    authorization_issued: Literal[False]
    kaggle_execution_performed: Literal[False]
    package_installation_performed: Literal[False]
    model_loaded: Literal[False]
    worker_started: Literal[False]
    model_requests_performed: Literal[0]
    measured_execution_authorized: Literal[False]
    credentials_present: Literal[False]
    customer_data_present: Literal[False]
    external_spend: Literal[0]


class CurrentHarnessRematerializationReview(LocalABCContract):
    """Decision contract for the next repository implementation slice."""

    schema_version: Literal["1.0.0"]
    review_id: Literal["auragateway-cu129-current-harness-rematerialization-review-v1"]
    repository_base_commit: Literal["16decd4e0d91c4baa18129b0d7afc69bb2630aa1"]
    decision: Literal["APPROVED_FOR_CURRENT_CU129_HARNESS_REMATERIALIZATION_IMPLEMENTATION"]
    failure_class: Literal["FROZEN_HARNESS_CANNOT_REALIZE_CURRENT_CU129_RUNTIME"]
    historical_materializer_evidence: HistoricalMaterializerEvidence
    observed_current_boundary: ObservedCurrentBoundary
    required_implementation: tuple[str, ...] = Field(min_length=10)
    required_negative_regressions: tuple[str, ...] = Field(min_length=10)
    next_gate: Literal["implement_current_cu129_harness_rematerializer"]
    safety: ReviewSafety
    non_claims: tuple[str, ...] = Field(min_length=6)

    @model_validator(mode="after")
    def validate_required_scope(self) -> Self:
        implementation_text = "\n".join(self.required_implementation)
        regression_text = "\n".join(self.required_negative_regressions)
        required_fragments = (
            "new immutable source commit",
            "metadata-only Kaggle input-realization inspection",
            "update the launcher harness source binding",
            "authorization issuance blocked",
        )
        if any(fragment not in implementation_text for fragment in required_fragments):
            raise ValueError("required rematerialization implementation scope drifted")
        required_regressions = (
            "historical be1bfadd harness",
            "historical vllm_wheel role",
            "path traversal",
            "stale launcher",
            "model requests",
        )
        if any(fragment not in regression_text for fragment in required_regressions):
            raise ValueError("required rematerialization regressions drifted")
        return self


class HistoricalMaterializerIdentity(LocalABCContract):
    """Repository evidence binding for the recovered notebook."""

    schema_version: Literal["1.0.0"]
    evidence_id: Literal["auragateway-historical-harness-materializer-input-v3-source-v1"]
    notebook_path: Literal[
        "evidence_vault/local_abc/harness-materializer-input-v3/"
        "ag-harness-materializer-input-v3.ipynb"
    ]
    notebook_raw_sha256: Literal["91f9ccc30883341af4cfd24d11c780ee136b9f7ccf9316b77b9d72ba559312c2"]
    notebook_name: Literal["ag-harness-materializer-input-v3"]
    input_dataset_name: Literal["ag-harness-be1bfad-v1-input"]
    source_commit: Literal["be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"]
    expected_archive_name: Literal["ag-harness-be1bfad-v1.zip"]
    expected_archive_sha256: Literal[
        "741629c9c1e39b02b14c16001ac3c7f96ebe6fb72670c47bfc22af31b4182c37"
    ]
    output_directory: Literal["auragateway_qualification_harness_be1bfad_v1"]
    directory_sha256: Literal["4a371c80aef605c4f1ab5617c21ce43bd0939ad449ffcbcadab656878d785a2e"]
    file_count: Literal[953]
    total_bytes: Literal[8879194]
    saved_output_status: Literal["HARNESS_MATERIALIZED"]
    nested_archives_present: Literal[False]
    symlinks_present: Literal[False]
    network_access_performed: Literal[False]
    gpu_execution_performed: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    classification: Literal["CONSUMED_HISTORICAL_MATERIALIZER_SOURCE"]


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise RuntimeError(message)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.as_posix()} must contain one JSON object")
    return cast(dict[str, object], payload)


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
        raise RuntimeError("review base commit is not an ancestor of HEAD")


def _git_file_bytes(repo_root: Path, revision: str, path: Path) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{revision}:{path.as_posix()}"],
        check=False,
        capture_output=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"historical authority is unavailable: {path.as_posix()}")
    return result.stdout


def _git_file_sha256(repo_root: Path, revision: str, path: Path) -> str:
    return hashlib.sha256(_git_file_bytes(repo_root, revision, path)).hexdigest()


def _git_json(repo_root: Path, revision: str, path: Path) -> dict[str, object]:
    payload = json.loads(_git_file_bytes(repo_root, revision, path).decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"historical JSON root is invalid: {path.as_posix()}")
    return cast(dict[str, object], payload)


def _git_text(repo_root: Path, revision: str, path: Path) -> str:
    return _git_file_bytes(repo_root, revision, path).decode("utf-8")


def _notebook_source(path: Path) -> str:
    notebook = _load_json(path)
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("historical materializer notebook cells are invalid")
    sources: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        source = cell.get("source")
        if isinstance(source, list) and all(isinstance(line, str) for line in source):
            sources.append("".join(source))
        elif isinstance(source, str):
            sources.append(source)
    if not sources:
        raise RuntimeError("historical materializer notebook has no code source")
    return "\n".join(sources)


def _validate_historical_evidence(repo_root: Path) -> HistoricalMaterializerIdentity:
    notebook_path = repo_root / HISTORICAL_NOTEBOOK_PATH
    if _file_sha256(notebook_path) != HISTORICAL_NOTEBOOK_SHA256:
        raise RuntimeError("historical materializer notebook identity drifted")
    identity = HistoricalMaterializerIdentity.model_validate(
        _load_json(repo_root / HISTORICAL_IDENTITY_PATH)
    )
    source = _notebook_source(notebook_path)
    required_fragments = (
        'NOTEBOOK_NAME = "ag-harness-materializer-input-v3"',
        'EXPECTED_SOURCE_COMMIT = "be1bfadd8a8aa3f0a2f6143d6a73f082f1090c50"',
        'OUTPUT_DIRECTORY_NAME = "auragateway_qualification_harness_be1bfad_v1"',
        "def validated_member_path",
        "def extract_archive",
        "def copy_expanded_tree",
        "nested_archives_present",
        "model_requests_performed",
    )
    if any(fragment not in source for fragment in required_fragments):
        raise RuntimeError("historical materializer source contract drifted")
    return identity


def _validate_current_file_identities(repo_root: Path) -> None:
    drift = tuple(
        path.as_posix()
        for path, expected_sha256 in EXPECTED_CURRENT_SHA256.items()
        if _git_file_sha256(repo_root, BASE_COMMIT, path) != expected_sha256
    )
    if drift:
        raise RuntimeError("current rematerialization authorities drifted: " + ", ".join(drift))


def _validate_historical_file_identities(repo_root: Path) -> None:
    drift = tuple(
        path.as_posix()
        for path, expected_sha256 in EXPECTED_HISTORICAL_SHA256.items()
        if _git_file_sha256(repo_root, HISTORICAL_HARNESS_SOURCE_COMMIT, path) != expected_sha256
    )
    if drift:
        raise RuntimeError("historical harness authorities drifted: " + ", ".join(drift))


def _manifest_entries_by_role(entries: object) -> dict[str, dict[str, object]]:
    if not isinstance(entries, list) or len(entries) != 3:
        raise RuntimeError("current offline dataset manifest entry set drifted")

    by_role: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("current offline dataset manifest entry shape drifted")
        role = entry.get("role")
        if not isinstance(role, str) or role in by_role:
            raise RuntimeError("current offline dataset manifest roles drifted")
        by_role[role] = cast(dict[str, object], entry)

    expected_roles = {"harness_source", "model_artifacts", "vllm_runtime"}
    if set(by_role) != expected_roles:
        raise RuntimeError("current offline dataset manifest roles drifted")
    return by_role


def _validate_runtime_boundary(repo_root: Path) -> None:
    """Validate the exact reviewed boundary at its immutable base commit."""

    manifest = _git_json(repo_root, BASE_COMMIT, MANIFEST_PATH)
    entries_by_role = _manifest_entries_by_role(manifest.get("entries"))
    harness_entry = entries_by_role["harness_source"]
    runtime_entry = entries_by_role["vllm_runtime"]

    if harness_entry.get("artifact_format") != "source_tree_directory":
        raise RuntimeError("reviewed frozen harness artifact format drifted")
    if harness_entry.get("sha256") != HISTORICAL_DIRECTORY_SHA256:
        raise RuntimeError("reviewed frozen harness directory identity drifted")
    if harness_entry.get("mounted_path") != HISTORICAL_HARNESS_MOUNTED_PATH:
        raise RuntimeError("reviewed frozen harness mounted path drifted")

    if runtime_entry.get("artifact_format") != "python_wheelhouse_directory":
        raise RuntimeError("reviewed CUDA 12.9 runtime artifact format drifted")
    if runtime_entry.get("package_count") != 176:
        raise RuntimeError("reviewed CUDA 12.9 runtime package count drifted")
    if runtime_entry.get("resolution_lock_sha256") != CURRENT_RUNTIME_RESOLUTION_LOCK_SHA256:
        raise RuntimeError("reviewed CUDA 12.9 runtime resolution lock drifted")

    record = _git_json(repo_root, BASE_COMMIT, MATERIALIZATION_RECORD_PATH)
    if record.get("harness_source_commit") != HISTORICAL_HARNESS_SOURCE_COMMIT:
        raise RuntimeError("reviewed materialization record lost the frozen harness")

    launcher = _git_text(repo_root, BASE_COMMIT, LAUNCHER_PATH)
    launcher_fragments = (
        HISTORICAL_HARNESS_SOURCE_COMMIT,
        "ag-harness-materializer-input-v3/",
        "auragateway_qualification_harness_be1bfad_v1",
        "auragateway_vllm_cu129_wheelhouse_v1",
    )
    if any(fragment not in launcher for fragment in launcher_fragments):
        raise RuntimeError("reviewed launcher boundary drifted")

    runbook = _git_text(repo_root, BASE_COMMIT, LAUNCHER_RUNBOOK_PATH)
    if "auragateway-vllm-wheel-recovery-v1" not in runbook:
        raise RuntimeError("reviewed stale launcher instruction is absent")

    if (repo_root / FINAL_AUTHORIZATION_PATH).exists():
        raise RuntimeError("final authorization exists before fresh issuance implementation")


def _validate_documentation(repo_root: Path) -> None:
    required = {
        ADR_PATH: (
            "CURRENT_HARNESS_REMATERIALIZATION_REQUIRED",
            "FROZEN_HARNESS_CANNOT_REALIZE_CURRENT_CU129_RUNTIME",
        ),
        REPORT_PATH: (
            "APPROVED_FOR_CURRENT_CU129_HARNESS_REMATERIALIZATION_IMPLEMENTATION",
            "STALE_LAUNCHER_RUNTIME_INPUT_INSTRUCTION",
        ),
    }
    for path, fragments in required.items():
        text = (repo_root / path).read_text(encoding="utf-8")
        if any(fragment not in text for fragment in fragments):
            raise RuntimeError(f"review documentation drifted: {path.as_posix()}")


def validate_repository_package(repo_root: str | Path) -> dict[str, object]:
    """Validate the review and prove the current frozen-harness incompatibility."""

    root = Path(repo_root).resolve()
    review = CurrentHarnessRematerializationReview.model_validate(_load_json(root / REVIEW_PATH))
    _require_base_ancestor(root)
    identity = _validate_historical_evidence(root)
    _validate_current_file_identities(root)
    _validate_historical_file_identities(root)
    _validate_runtime_boundary(root)
    _validate_documentation(root)

    return {
        "review_id": review.review_id,
        "decision": review.decision,
        "failure_class": review.failure_class,
        "historical_materializer_notebook_sha256": identity.notebook_raw_sha256,
        "historical_harness_source_commit": identity.source_commit,
        "current_runtime_role": review.observed_current_boundary.current_runtime_role,
        "current_runtime_package_count": (
            review.observed_current_boundary.current_runtime_package_count
        ),
        "current_harness_rematerialization_required": True,
        "authorization_issued": False,
        "kaggle_execution_performed": False,
        "model_requests_performed": 0,
        "next_gate": review.next_gate,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-cu129-current-harness-rematerialization-review")
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

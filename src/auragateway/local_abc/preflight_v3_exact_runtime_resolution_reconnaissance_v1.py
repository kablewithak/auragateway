"""Validate and freeze the repository boundary for preflight-v3 exact-runtime reconnaissance."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Final, Literal, Self

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "15d8c4db122eb50c2f639748bc06f98bae70b167"

DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_materialization_v1_design.json"
)
EXECUTION_MANIFEST_PATH: Final = Path(
    "data/evals/benchmark/preflight-v3/execution_manifest_draft.json"
)
DEVELOPER_DEPENDENCY_LOCK_PATH: Final = Path(
    "data/evals/benchmark/preflight-v3/developer_dependency_lock.json"
)
CONDITION_FINGERPRINTS_PATH: Final = Path(
    "data/evals/benchmark/preflight-v3/condition_fingerprints.json"
)
NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_v1.ipynb"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_resolution_reconnaissance_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_resolution_reconnaissance_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V3_Exact_Runtime_Resolution_Reconnaissance_V1_Implementation.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_exact_runtime_resolution_reconnaissance_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_v1_implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_v1_implementation_record.json"
)

EXPECTED_DESIGN_SHA256: Final = "6cfb96a5c665e0865ab22f471e7f5dd2ca38c9139b4d7ec84d5c9416373d965a"
EXPECTED_DESIGN_BLOB_SHA: Final = "108bd29320997ab598faa1ad16baae0c25e0eb2a"
EXPECTED_EXECUTION_MANIFEST_BLOB_SHA: Final = "02538a9f796b3be202c63d2ff6a741c00fe56c91"
EXPECTED_DEVELOPER_DEPENDENCY_LOCK_BLOB_SHA: Final = "794adc1de41e1514644744e9ec5b7df02646f978"
EXPECTED_CONDITION_FINGERPRINTS_BLOB_SHA: Final = "35be4e1f611ba58ea356eef4c2b6477dee95c73f"

NOTEBOOK_NAME: Final = "auragateway-preflight-v3-exact-runtime-resolution-reconnaissance-v1"
REQUESTED_KAGGLE_TITLE: Final = "ag-preflight-v3-runtime-resolution-recon-v1"
OUTPUT_DIRECTORY_NAME: Final = "auragateway_preflight_v3_exact_runtime_resolution_reconnaissance_v1"
EXPECTED_VLLM_DISTRIBUTION: Final = "0.25.1+cu129"
EXPECTED_VLLM_WHEEL_SHA256: Final = (
    "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
)
EXPECTED_TORCH_VERSION: Final = "2.11.0+cu129"
EXPECTED_CUDA_VERSION: Final = "12.9"

NEXT_GATE: Final = "merge_then_execute_preflight_v3_exact_runtime_resolution_reconnaissance_v1"

RequiredOutputV1 = Literal[
    "resolved_artifacts.json",
    "resolver_report.json",
    "host_policy.json",
    "resolution_receipt.json",
    "output_manifest.json",
]
REQUIRED_OUTPUTS: Final[tuple[RequiredOutputV1, ...]] = (
    "resolved_artifacts.json",
    "resolver_report.json",
    "host_policy.json",
    "resolution_receipt.json",
    "output_manifest.json",
)


class ArtifactIdentityV1(LocalABCContract):
    """Immutable repository artifact identity."""

    path: str
    sha256: str

    @field_validator("sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("artifact identity must use lowercase SHA-256")
        return value


class RuntimePlanV1(LocalABCContract):
    """Exact runtime identity inherited from preflight-v3."""

    python: Literal["3.12"] = "3.12"
    cuda: Literal["12.9"] = "12.9"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_wheel_sha256: Literal[
        "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
    ] = "9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"


class ReconnaissanceBudgetV1(LocalABCContract):
    """Fail-closed external execution budget."""

    accelerator: Literal["none"] = "none"
    internet_enabled: Literal[True] = True
    dependency_resolution_permitted: Literal[True] = True
    package_installation_permitted: Literal[False] = False
    artifact_download_retention_permitted: Literal[False] = False
    model_loads: Literal[0] = 0
    model_requests: Literal[0] = 0
    benchmark_trajectories: Literal[0] = 0
    credentials_permitted: Literal[False] = False
    customer_data_permitted: Literal[False] = False
    external_spend: Literal[0] = 0


class ImplementationReviewV1(LocalABCContract):
    """Deterministic review produced after source formatting."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-preflight-v3-exact-runtime-resolution-reconnaissance-v1-implementation-review"
    ] = "auragateway-preflight-v3-exact-runtime-resolution-reconnaissance-v1-implementation-review"
    implementation_base_main_commit: Literal["15d8c4db122eb50c2f639748bc06f98bae70b167"] = (
        IMPLEMENTATION_BASE_MAIN_COMMIT
    )
    design: ArtifactIdentityV1
    notebook: ArtifactIdentityV1
    source: ArtifactIdentityV1
    tests: ArtifactIdentityV1
    report: ArtifactIdentityV1
    runbook: ArtifactIdentityV1
    authored_artifact_count: Literal[5] = 5
    generated_artifact_count: Literal[2] = 2
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "merge_then_execute_preflight_v3_exact_runtime_resolution_reconnaissance_v1"
    ] = NEXT_GATE


class ImplementationRecordV1(LocalABCContract):
    """Repository record binding the executable reconnaissance implementation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-preflight-v3-exact-runtime-resolution-reconnaissance-v1-implementation-record"
    ] = "auragateway-preflight-v3-exact-runtime-resolution-reconnaissance-v1-implementation-record"
    implementation_base_main_commit: Literal["15d8c4db122eb50c2f639748bc06f98bae70b167"] = (
        IMPLEMENTATION_BASE_MAIN_COMMIT
    )
    design_sha256: Literal["6cfb96a5c665e0865ab22f471e7f5dd2ca38c9139b4d7ec84d5c9416373d965a"] = (
        EXPECTED_DESIGN_SHA256
    )
    implementation_review_sha256: str
    notebook_sha256: str
    source_sha256: str
    tests_sha256: str
    runtime_plan: RuntimePlanV1
    budget: ReconnaissanceBudgetV1
    required_outputs: tuple[RequiredOutputV1, ...] = REQUIRED_OUTPUTS
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    exact_runtime_resolution_lock_frozen: Literal[False] = False
    exact_runtime_materialized: Literal[False] = False
    exact_runtime_offline_verified: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "merge_then_execute_preflight_v3_exact_runtime_resolution_reconnaissance_v1"
    ] = NEXT_GATE

    @field_validator(
        "implementation_review_sha256",
        "notebook_sha256",
        "source_sha256",
        "tests_sha256",
    )
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("implementation record hashes must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_required_outputs(self) -> Self:
        if self.required_outputs != REQUIRED_OUTPUTS:
            raise ValueError("required reconnaissance outputs drifted")
        return self


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _read_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _git_blob_sha(repo_root: Path, relative_path: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", f"HEAD:{relative_path.as_posix()}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise ValueError(
            f"could not resolve committed authority blob for {relative_path.as_posix()}"
        )
    return completed.stdout.strip()


def _require_authority_blob(
    repo_root: Path,
    relative_path: Path,
    expected_blob_sha: str,
) -> None:
    observed = _git_blob_sha(repo_root, relative_path)
    if observed != expected_blob_sha:
        raise ValueError(f"authority blob drifted for {relative_path.as_posix()}: {observed}")


def validate_authority(repo_root: Path) -> None:
    """Validate the merged design and preflight-v3 runtime authority."""

    design_path = repo_root / DESIGN_PATH
    if _sha256_file(design_path) != EXPECTED_DESIGN_SHA256:
        raise ValueError("exact-runtime materialization design SHA-256 drifted")

    _require_authority_blob(
        repo_root,
        DESIGN_PATH,
        EXPECTED_DESIGN_BLOB_SHA,
    )
    _require_authority_blob(
        repo_root,
        EXECUTION_MANIFEST_PATH,
        EXPECTED_EXECUTION_MANIFEST_BLOB_SHA,
    )
    _require_authority_blob(
        repo_root,
        DEVELOPER_DEPENDENCY_LOCK_PATH,
        EXPECTED_DEVELOPER_DEPENDENCY_LOCK_BLOB_SHA,
    )
    _require_authority_blob(
        repo_root,
        CONDITION_FINGERPRINTS_PATH,
        EXPECTED_CONDITION_FINGERPRINTS_BLOB_SHA,
    )

    design = _read_json_object(design_path)
    if design.get("decision") != "EXTEND_EXISTING_CU129_MATERIALIZER_WITH_NEW_EXACT_RUNTIME_LOCK":
        raise ValueError("exact-runtime design decision drifted")
    if design.get("direct_reuse_permitted") is not False:
        raise ValueError("historical resolution lock must not become direct authority")
    if (
        design.get("next_gate")
        != "implement_preflight_v3_exact_runtime_resolution_reconnaissance_v1"
    ):
        raise ValueError("exact-runtime design next gate drifted")

    planned_runtime = design.get("planned_runtime")
    if not isinstance(planned_runtime, dict):
        raise ValueError("planned runtime missing from design")
    if planned_runtime.get("vllm_distribution_version") != EXPECTED_VLLM_DISTRIBUTION:
        raise ValueError("planned vLLM distribution drifted")
    if planned_runtime.get("vllm_wheel_sha256") != EXPECTED_VLLM_WHEEL_SHA256:
        raise ValueError("planned vLLM wheel SHA-256 drifted")
    if planned_runtime.get("torch_version") != EXPECTED_TORCH_VERSION:
        raise ValueError("planned torch version drifted")

    manifest = _read_json_object(repo_root / EXECUTION_MANIFEST_PATH)
    runtime_direction = manifest.get("runtime_direction")
    if not isinstance(runtime_direction, dict):
        raise ValueError("preflight-v3 runtime direction is missing")
    if runtime_direction.get("vllm_distribution_version") != EXPECTED_VLLM_DISTRIBUTION:
        raise ValueError("execution manifest vLLM runtime drifted")
    if runtime_direction.get("vllm_wheel_sha256") != EXPECTED_VLLM_WHEEL_SHA256:
        raise ValueError("execution manifest vLLM SHA-256 drifted")
    if runtime_direction.get("torch_version") != EXPECTED_TORCH_VERSION:
        raise ValueError("execution manifest torch runtime drifted")
    if runtime_direction.get("torch_cuda_version") != EXPECTED_CUDA_VERSION:
        raise ValueError("execution manifest CUDA runtime drifted")
    if runtime_direction.get("current_full_run_environment_requalification_required") is not True:
        raise ValueError("environment requalification must remain required")
    if manifest.get("gpu_execution_authorized") is not False:
        raise ValueError("GPU execution unexpectedly became authorized")
    if manifest.get("measured_execution_authorized") is not False:
        raise ValueError("measured execution unexpectedly became authorized")

    dependency_lock = _read_json_object(repo_root / DEVELOPER_DEPENDENCY_LOCK_PATH)
    if dependency_lock.get("kaggle_runtime_lock_generated") is not False:
        raise ValueError("Kaggle runtime lock unexpectedly became generated")
    if dependency_lock.get("execution_authorized") is not False:
        raise ValueError("developer dependency lock unexpectedly authorizes execution")


def _notebook_source(payload: dict[str, object]) -> str:
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        raise ValueError("reconnaissance notebook must contain exactly two cells")
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        raise ValueError("reconnaissance code cell is invalid")
    source = code_cell.get("source")
    if not isinstance(source, list) or not all(isinstance(item, str) for item in source):
        raise ValueError("reconnaissance code source must be a list of strings")
    return "".join(source)


def validate_notebook(repo_root: Path) -> None:
    """Validate the non-executed notebook and its fail-closed budget."""

    payload = _read_json_object(repo_root / NOTEBOOK_PATH)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("notebook metadata is missing")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise ValueError("AuraGateway notebook metadata is missing")

    expected_metadata = {
        "schema_version": "1.0.0",
        "notebook_name": NOTEBOOK_NAME,
        "requested_kaggle_title": REQUESTED_KAGGLE_TITLE,
        "accelerator": "none",
        "internet_required": True,
        "package_installation_permitted": False,
        "artifact_download_retention_permitted": False,
        "model_loads_permitted": 0,
        "model_requests_permitted": 0,
        "benchmark_trajectories_permitted": 0,
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "external_spend": 0,
        "expected_vllm_distribution": EXPECTED_VLLM_DISTRIBUTION,
        "expected_vllm_wheel_sha256": EXPECTED_VLLM_WHEEL_SHA256,
        "expected_torch_version": EXPECTED_TORCH_VERSION,
    }
    for key, expected in expected_metadata.items():
        if auragateway.get(key) != expected:
            raise ValueError(f"notebook metadata drifted: {key}")

    cells = payload.get("cells")
    assert isinstance(cells, list)
    code_cell = cells[1]
    assert isinstance(code_cell, dict)
    if code_cell.get("execution_count") is not None:
        raise ValueError("repository notebook must remain unexecuted")
    if code_cell.get("outputs") != []:
        raise ValueError("repository notebook must not contain execution outputs")

    source = _notebook_source(payload)
    required_fragments = (
        f'NOTEBOOK_NAME = "{NOTEBOOK_NAME}"',
        f'EXPECTED_VLLM_DISTRIBUTION = "{EXPECTED_VLLM_DISTRIBUTION}"',
        EXPECTED_VLLM_WHEEL_SHA256,
        f'EXPECTED_TORCH_VERSION = "{EXPECTED_TORCH_VERSION}"',
        '"--dry-run"',
        '"--ignore-installed"',
        '"--only-binary=:all:"',
        '"--report"',
        "TemporaryDirectory",
        "installed_snapshot",
        "KAGGLE_INPUTS_PRESENT",
        "CREDENTIAL_ENV_PRESENT",
        "PIP_RESOLUTION_FAILED",
        "stable_url_sha256",
        "query_present",
        "fragment_present",
        "VLLM_SHA256_MISMATCH",
        "VLLM_VERSION_MISMATCH",
        "TORCH_VERSION_MISMATCH",
        "PACKAGE_ENVIRONMENT_MUTATED",
        "artifact_download_retention_permitted",
        '"package_installation_performed": False',
        '"model_loads_performed": 0',
        '"model_requests_performed": 0',
        '"benchmark_trajectories_performed": 0',
        '"credentials_used": False',
        '"customer_data_used": False',
        '"external_spend": 0',
        "resolved_artifacts.json",
        "resolver_report.json",
        "host_policy.json",
        "resolution_receipt.json",
        "output_manifest.json",
    )
    missing = [fragment for fragment in required_fragments if fragment not in source]
    if missing:
        raise ValueError(f"notebook contract fragments missing: {missing}")

    forbidden_fragments = (
        "torch.cuda",
        "vllm.LLM",
        "AsyncLLMEngine",
        "/v1/chat/completions",
        "OPENAI_API_KEY]",
        "HF_TOKEN]",
        "pip download",
    )
    present = [fragment for fragment in forbidden_fragments if fragment in source]
    if present:
        raise ValueError(f"notebook contains forbidden execution surface: {present}")


def _artifact_identity(repo_root: Path, path: Path) -> ArtifactIdentityV1:
    return ArtifactIdentityV1(
        path=path.as_posix(),
        sha256=_sha256_file(repo_root / path),
    )


def build_review(repo_root: Path) -> ImplementationReviewV1:
    """Build the deterministic post-format implementation review."""

    validate_authority(repo_root)
    validate_notebook(repo_root)
    return ImplementationReviewV1(
        design=_artifact_identity(repo_root, DESIGN_PATH),
        notebook=_artifact_identity(repo_root, NOTEBOOK_PATH),
        source=_artifact_identity(repo_root, SOURCE_PATH),
        tests=_artifact_identity(repo_root, TEST_PATH),
        report=_artifact_identity(repo_root, REPORT_PATH),
        runbook=_artifact_identity(repo_root, RUNBOOK_PATH),
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
    )


def build_record(
    repo_root: Path,
    review_sha256: str,
) -> ImplementationRecordV1:
    """Build the deterministic implementation record."""

    return ImplementationRecordV1(
        implementation_review_sha256=review_sha256,
        notebook_sha256=_sha256_file(repo_root / NOTEBOOK_PATH),
        source_sha256=_sha256_file(repo_root / SOURCE_PATH),
        tests_sha256=_sha256_file(repo_root / TEST_PATH),
        runtime_plan=RuntimePlanV1(),
        budget=ReconnaissanceBudgetV1(),
        exact_runtime_resolution_lock_frozen=False,
        exact_runtime_materialized=False,
        exact_runtime_offline_verified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
    )


def generate(repo_root: Path) -> dict[str, object]:
    """Generate deterministic implementation review and record files."""

    review = build_review(repo_root)
    review_text = review.canonical_json() + "\n"
    review_path = repo_root / REVIEW_PATH
    review_path.write_text(review_text, encoding="utf-8", newline="\n")
    review_sha256 = _sha256_bytes(review_text.encode("utf-8"))

    record = build_record(repo_root, review_sha256)
    record_text = record.canonical_json() + "\n"
    record_path = repo_root / RECORD_PATH
    record_path.write_text(record_text, encoding="utf-8", newline="\n")

    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_V1_GENERATED",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "review_sha256": review_sha256,
        "record_sha256": _sha256_bytes(record_text.encode("utf-8")),
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> tuple[str, str]:
    """Require generated artifacts to equal deterministic recomputation."""

    expected_review = build_review(repo_root)
    expected_review_text = expected_review.canonical_json() + "\n"
    review_path = repo_root / REVIEW_PATH
    if not review_path.is_file():
        raise ValueError("implementation review has not been generated")
    observed_review_text = review_path.read_text(encoding="utf-8")
    if observed_review_text != expected_review_text:
        raise ValueError("implementation review is stale or nondeterministic")
    review_sha256 = _sha256_bytes(expected_review_text.encode("utf-8"))

    expected_record = build_record(repo_root, review_sha256)
    expected_record_text = expected_record.canonical_json() + "\n"
    record_path = repo_root / RECORD_PATH
    if not record_path.is_file():
        raise ValueError("implementation record has not been generated")
    observed_record_text = record_path.read_text(encoding="utf-8")
    if observed_record_text != expected_record_text:
        raise ValueError("implementation record is stale or nondeterministic")

    return (
        review_sha256,
        _sha256_bytes(expected_record_text.encode("utf-8")),
    )


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate the complete non-executed implementation package."""

    validate_authority(repo_root)
    validate_notebook(repo_root)
    review_sha256, record_sha256 = validate_generated(repo_root)
    return {
        "status": "PREFLIGHT_V3_EXACT_RUNTIME_RESOLUTION_RECONNAISSANCE_V1_VALID",
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "notebook_name": NOTEBOOK_NAME,
        "notebook_sha256": _sha256_file(repo_root / NOTEBOOK_PATH),
        "review_sha256": review_sha256,
        "record_sha256": record_sha256,
        "exact_runtime_resolution_lock_frozen": False,
        "exact_runtime_materialized": False,
        "exact_runtime_offline_verified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _print_summary(payload: dict[str, object]) -> None:
    print(_canonical_json(payload))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("generate", "validate-implementation"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if args.command == "generate":
        _print_summary(generate(repo_root))
        return 0

    _print_summary(validate_implementation(repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

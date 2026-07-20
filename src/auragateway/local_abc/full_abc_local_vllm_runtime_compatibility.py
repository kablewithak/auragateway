"""Validate the vLLM runtime compatibility diagnosis and wheelhouse notebooks."""

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
_VERSION_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+-]{0,79}$")

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_vllm_runtime_compatibility_remediation_v1.json"
)
SUPERSEDED_ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu128-offline-wheelhouse.md")
ADR_PATH: Final = Path("docs/adr/2026-07-20-local-abc-vllm-cu129-isolated-wheelhouse.md")
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_vllm_cu129_wheelhouse_materialization_v1.md")
EVIDENCE_DIRECTORY: Final = Path(
    "evidence_vault/local_abc/environment-qualification-vllm-runtime-compatibility-v1"
)
EVIDENCE_SHA256_PATH: Final = EVIDENCE_DIRECTORY / "evidence_sha256.json"
SOURCE_IDENTITY_PATH: Final = EVIDENCE_DIRECTORY / "source_evidence_identity.json"
MATERIALIZER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb"
)
VERIFIER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v1.ipynb"
)
RECONNAISSANCE_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_vllm_cu129_resolution_reconnaissance_v1.ipynb"
)
LEGACY_NOTEBOOK_PATHS: Final = (
    Path("notebooks/ag-vllm-cu128-wheelhouse-materializer-v1.ipynb"),
    Path("notebooks/ag-vllm-cu128-offline-compatibility-v1.ipynb"),
    Path("notebooks/auragateway_vllm_cu128_wheelhouse_materialization_v1.ipynb"),
    Path("notebooks/auragateway_vllm_cu128_offline_runtime_compatibility_v1.ipynb"),
)
LEGACY_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_vllm_cu128_wheelhouse_materialization_v1.md"
)

EXPECTED_QUALIFICATION_EVIDENCE_ZIP_SHA256: Final = (
    "82a97b9bb66f4411acf9d6a893d969d9919777a1d7ad586519cd8cd3837efca4"
)
EXPECTED_QUALIFICATION_LOG_SHA256: Final = (
    "d56cd42b7d1cb3898360c773e7b83a06028310803f03ba102ac4a3dc1d741c2a"
)
EXPECTED_DIAGNOSTIC_EVIDENCE_ZIP_SHA256: Final = (
    "e13eb8051798dd79b96900e69e9d5a657a80b884b9e5a0a5eba3cf6904103aee"
)
EXPECTED_MATERIALIZER_FAILURE_LOG_SHA256: Final = (
    "b45bee3fd286f35d367ee25639100eb33b9244251d5a921dedd84c998e785a2d"
)
EXPECTED_MATERIALIZER_CDN_FAILURE_LOG_SHA256: Final = (
    "69c7656374fc5313becb44684f1b11eac950db7c79eed5b62572eaefec3640a3"
)
EXPECTED_MATERIALIZER_NVIDIA_FAILURE_LOG_SHA256: Final = (
    "f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4"
)
EXPECTED_VLLM_ASSET_SHA256: Final = (
    "71a87f46cafab4489c69a5c5c83b870d0235e5694d8222303d460576293dc719"
)
EXPECTED_MATERIALIZER_NOTEBOOK_SHA256: Final = (
    "d836a61bc7ed7a0d6c26eca68a28ed22e685e5a6705bf16ce4f6dbb8168f7ba2"
)
EXPECTED_RESOLUTION_LOCK_SHA256: Final = (
    "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
)
EXPECTED_VERIFIER_NOTEBOOK_SHA256: Final = (
    "692f83fd8a6fa7398ee9fabb0ecbf62640c82d6582a96a552f47e4f8b3b1b189"
)
EXPECTED_RECONNAISSANCE_NOTEBOOK_SHA256: Final = (
    "541e92aa0b509d0966911904d1c6bb951819aa98abb69f4f7964b724c55afd6a"
)

MATERIALIZER_NOTEBOOK_NAME: Final = "auragateway-cu129-wheelhouse-materializer-v1"
VERIFIER_NOTEBOOK_NAME: Final = "auragateway-cu129-offline-verifier-v1"
RECONNAISSANCE_NOTEBOOK_NAME: Final = "auragateway-cu129-resolution-reconnaissance-v1"
OUTPUT_DIRECTORY_NAME: Final = "auragateway_vllm_cu129_wheelhouse_v1"
VERIFIER_EVIDENCE_DIRECTORY_NAME: Final = "auragateway_vllm_cu129_offline_compatibility_evidence_v1"
RECONNAISSANCE_OUTPUT_DIRECTORY_NAME: Final = "auragateway_vllm_cu129_resolution_reconnaissance_v1"


class VllmRuntimeStackV1(LocalABCContract):
    """Exact isolated target stack for the CUDA 12.9 compatibility campaign."""

    python: Literal["3.12"]
    cuda_variant: Literal["cu129"]
    vllm_binary_cuda: Literal["12.9"]
    vllm_release: Literal["0.19.1"]
    vllm: Literal["0.19.1"]
    vllm_asset_name: Literal["vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl"]
    vllm_asset_sha256: Literal["71a87f46cafab4489c69a5c5c83b870d0235e5694d8222303d460576293dc719"]
    torch: Literal["2.10.0+cu129"]
    torchaudio: Literal["2.10.0+cu129"]
    torchvision: Literal["0.25.0+cu129"]
    transformers: Literal["5.5.3"]
    installation_mode: Literal["isolated_virtual_environment"]
    base_environment_torch_is_runtime_authority: Literal[False]
    network_installation_permitted_during_materialization: Literal[True]
    network_installation_permitted_during_verification: Literal[False]

    @field_validator(
        "python",
        "vllm_binary_cuda",
        "vllm_release",
        "vllm",
        "torch",
        "torchaudio",
        "torchvision",
        "transformers",
    )
    @classmethod
    def validate_version(cls, value: str) -> str:
        if _VERSION_PATTERN.fullmatch(value) is None:
            raise ValueError("runtime versions must use stable bounded identifiers")
        return value

    @field_validator("vllm_asset_sha256")
    @classmethod
    def validate_asset_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("vLLM asset SHA-256 must be lowercase hexadecimal")
        return value


class VllmRuntimeFailureV1(LocalABCContract):
    """Observed incompatibility established by the diagnostic evidence."""

    primary_class: Literal["RUNTIME_BINARY_COMPATIBILITY_FAILURE"]
    primary_code: Literal["VLLM_TORCH_ABI_MISMATCH"]
    secondary_class: Literal["OFFLINE_DEPENDENCY_CLOSURE_FAILURE"]
    secondary_code: Literal["INCOMPLETE_VLLM_WHEELHOUSE"]
    qualification_stage: Literal["dependency_lock_capture"]
    diagnostic_error: Literal["undefined symbol: torch_from_blob"]
    observed_vllm: Literal["0.25.1+cu129"]
    observed_torch: Literal["2.10.0+cu128"]
    observed_torchaudio: Literal["2.10.0+cu128"]
    observed_torchvision: Literal["0.25.0+cu128"]
    observed_transformers: Literal["5.0.0"]
    gpu_count: Literal[2]
    gpu_model: Literal["Tesla T4"]
    compute_capability: Literal["7.5"]


class VllmMaterializerFailureV1(LocalABCContract):
    """Preserved first divergence from the failed cu128 materializer."""

    classification: Literal["MATERIALIZER_RELEASE_ASSET_CONTRACT_FAILURE"]
    code: Literal["VLLM_CU128_RELEASE_ASSET_ABSENT"]
    failed_requested_kaggle_title: Literal["auragateway-cu128-wheelhouse-materializer-v1"]
    historical_kaggle_title: Literal["auragateway-cu128-wheelhouse-asset-mismatch-v1"]
    execution_log_sha256: Literal[
        "b45bee3fd286f35d367ee25639100eb33b9244251d5a921dedd84c998e785a2d"
    ]
    first_divergence: Literal["official_v0.19.1_release_has_no_explicit_cu128_x86_64_wheel"]
    output_generated: Literal[False]
    wheel_downloads_performed: Literal[0]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class VllmMaterializerCdnFailureV1(LocalABCContract):
    # Preserved first divergence from the failed cu129 CDN allowlist run.

    classification: Literal["MATERIALIZER_DOWNLOAD_HOST_ALLOWLIST_FAILURE"]
    code: Literal["PYTORCH_CDN_HOST_NOT_ALLOWED"]
    failed_requested_kaggle_title: Literal["auragateway-cu129-wheelhouse-materializer-v1"]
    historical_kaggle_title: Literal["auragateway-cu129-wheelhouse-cdn-mismatch-v1"]
    execution_log_sha256: Literal[
        "69c7656374fc5313becb44684f1b11eac950db7c79eed5b62572eaefec3640a3"
    ]
    first_divergence: Literal["resolved_torch_wheel_uses_download-r2.pytorch.org"]
    observed_host: Literal["download-r2.pytorch.org"]
    dependency_resolution_completed: Literal[True]
    output_generated: Literal[False]
    wheel_downloads_performed: Literal[0]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class VllmMaterializerNvidiaFailureV1(LocalABCContract):
    """Preserved first divergence from the third materializer attempt."""

    classification: Literal["MATERIALIZER_ACQUISITION_POLICY_FAILURE"]
    code: Literal["NVIDIA_PACKAGE_HOST_NOT_ALLOWED"]
    failed_requested_kaggle_title: Literal["auragateway-cu129-wheelhouse-materializer-v1"]
    historical_kaggle_title: Literal["auragateway-cu129-wheelhouse-nvidia-host-mismatch-v1"]
    execution_log_sha256: Literal[
        "f6e6f844ebfb7ede0aab428e4766af4123622fb2f3092933e4070e26d6831fa4"
    ]
    first_divergence: Literal["resolved_nvidia_cublas_wheel_uses_pypi.nvidia.com"]
    observed_distribution: Literal["nvidia-cublas-cu12"]
    observed_host: Literal["pypi.nvidia.com"]
    dependency_resolution_completed: Literal[True]
    output_generated: Literal[False]
    wheel_downloads_performed: Literal[0]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class VllmRuntimeArtifactsV1(LocalABCContract):
    """Repository and Kaggle artifact identities for the next two gates."""

    materializer_notebook: Literal[
        "notebooks/auragateway_vllm_cu129_wheelhouse_materialization_v1.ipynb"
    ]
    verifier_notebook: Literal[
        "notebooks/auragateway_vllm_cu129_offline_runtime_compatibility_v1.ipynb"
    ]
    output_directory: Literal["auragateway_vllm_cu129_wheelhouse_v1"]
    verifier_evidence_directory: Literal["auragateway_vllm_cu129_offline_compatibility_evidence_v1"]
    materializer_kaggle_name: Literal["auragateway-cu129-wheelhouse-materializer-v1"]
    verifier_kaggle_name: Literal["auragateway-cu129-offline-verifier-v1"]
    reconnaissance_notebook: Literal[
        "notebooks/auragateway_vllm_cu129_resolution_reconnaissance_v1.ipynb"
    ]
    reconnaissance_kaggle_name: Literal["auragateway-cu129-resolution-reconnaissance-v1"]
    reconnaissance_output_directory: Literal["auragateway_vllm_cu129_resolution_reconnaissance_v1"]
    resolution_lock: Literal["benchmarks/local_abc/auragateway_vllm_cu129_resolution_lock_v1.json"]
    resolution_lock_sha256: Literal[
        "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
    ]
    reconnaissance_result: Literal[
        "benchmarks/local_abc/auragateway_vllm_resolution_reconnaissance_result_v1.json"
    ]

    @field_validator(
        "materializer_notebook",
        "verifier_notebook",
        "reconnaissance_notebook",
    )
    @classmethod
    def validate_repository_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if path.is_absolute() or ".." in path.parts or len(value) > 220:
            raise ValueError("notebook paths must be bounded repository-relative paths")
        return value


class VllmReconnaissanceResultV1(LocalABCContract):
    """Reviewed resolution-only evidence used to construct the exact lock."""

    results_zip_sha256: Literal["a035b21fe5795816e888886003c3dd6c73dbda162370805be687b28f8cef4399"]
    execution_log_sha256: Literal[
        "3455a8e631157a0c4e4c66e3e5e23c0e4cb41236e6b7d1016811b357488a2269"
    ]
    resolved_distribution_count: Literal[176]
    host_count: Literal[5]
    policy_violation_count: Literal[26]
    review_resolution: Literal["exact_artifact_lock_replaces_family_authority_heuristics"]
    artifact_transfer_observed_during_pip_dry_run: Literal[True]
    package_installation_performed: Literal[False]
    wheel_files_retained_in_output: Literal[0]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class VllmMaterializerContractV1(LocalABCContract):
    """Exact-lock materializer contract after reconnaissance review."""

    notebook_sha256: Literal["d836a61bc7ed7a0d6c26eca68a28ed22e685e5a6705bf16ce4f6dbb8168f7ba2"]
    resolution_lock_sha256: Literal[
        "1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"
    ]
    expected_package_count: Literal[176]
    exact_host_count: Literal[5]
    prefix_variant_drift_repaired: Literal[True]
    wildcard_domains_permitted: Literal[False]
    package_installation_performed: Literal[False]
    model_requests_performed: Literal[0]
    qualification_claimed: Literal[False]


class VllmRuntimeSafetyV1(LocalABCContract):
    """Non-negotiable safety state for the materialization slice."""

    authorization_issued: Literal[False]
    qualification_claimed: Literal[False]
    model_loaded: Literal[False]
    model_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    customer_data_used: Literal[False]
    credentials_used: Literal[False]
    external_spend: Literal[0]


class VllmRuntimeCompatibilityRemediationV1(LocalABCContract):
    """Typed decision record for the complete isolated wheelhouse approach."""

    schema_version: Literal["1.6.0"]
    record_id: Literal["auragateway-vllm-runtime-compatibility-remediation-v1"]
    decision: Literal["APPROVED_FOR_EXACT_LOCKED_CU129_WHEELHOUSE_MATERIALIZATION"]
    failure: VllmRuntimeFailureV1
    materializer_failure: VllmMaterializerFailureV1
    materializer_cdn_failure: VllmMaterializerCdnFailureV1
    materializer_nvidia_failure: VllmMaterializerNvidiaFailureV1
    selected_runtime: VllmRuntimeStackV1
    artifacts: VllmRuntimeArtifactsV1
    reconnaissance_result: VllmReconnaissanceResultV1
    materializer_contract: VllmMaterializerContractV1
    gates: tuple[str, ...]
    safety: VllmRuntimeSafetyV1
    next_gate: Literal["materialize_exact_locked_cu129_wheelhouse"]

    @model_validator(mode="after")
    def validate_gates(self) -> Self:
        expected = (
            "exact_resolution_lock_verified",
            "exact_vllm_release_asset_identity_verified",
            "wheelhouse_materialization_successful",
            "wheelhouse_hash_manifest_valid",
            "offline_isolated_install_successful",
            "offline_pip_check_successful",
            "torch_cuda_runtime_matches_cu129",
            "two_t4_gpus_visible",
            "vllm_distribution_matches_0.19.1",
            "vllm_module_import_successful",
            "vllm_native_extension_import_successful",
            "zero_model_requests",
        )
        if self.gates != expected:
            raise ValueError("compatibility gates must preserve the reviewed order")
        return self


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected one JSON object: {path.as_posix()}")
    return cast(dict[str, object], payload)


def _notebook_source(payload: dict[str, object]) -> str:
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("notebook cells are missing")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise RuntimeError("compatibility notebooks must contain exactly one code cell")
    source = code_cells[0].get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    if isinstance(source, str):
        return source
    raise RuntimeError("notebook code source is invalid")


def _validate_notebook(
    path: Path,
    *,
    expected_name: str,
    expected_sha256: str,
    expected_internet: bool,
    expected_accelerator: str,
    required_fragments: tuple[str, ...],
) -> dict[str, object]:
    payload = _load_json_object(path)
    if payload.get("nbformat") != 4:
        raise RuntimeError("notebook must use nbformat 4")
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        raise RuntimeError("notebook metadata is missing")
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        raise RuntimeError("AuraGateway notebook metadata is missing")
    expected_metadata = {
        "notebook_name": expected_name,
        "diagnostic_only": True,
        "internet_required": expected_internet,
        "accelerator": expected_accelerator,
        "credentials_permitted": False,
        "customer_data_permitted": False,
        "model_requests_permitted": 0,
        "qualification_claimed": False,
    }
    drift = tuple(
        sorted(
            key
            for key, expected_value in expected_metadata.items()
            if auragateway.get(key) != expected_value
        )
    )
    if drift:
        raise RuntimeError("notebook metadata drifted: " + ", ".join(drift))

    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise RuntimeError("notebook cells are invalid")
    for cell in cells:
        if not isinstance(cell, dict) or cell.get("cell_type") != "code":
            continue
        if cell.get("execution_count") is not None:
            raise RuntimeError("notebook contains execution state")
        outputs = cell.get("outputs")
        if outputs != []:
            raise RuntimeError("notebook contains saved output")

    source = _notebook_source(payload)
    compile(source, path.as_posix(), "exec")
    missing = tuple(fragment for fragment in required_fragments if fragment not in source)
    if missing:
        raise RuntimeError("notebook source lacks reviewed fragments: " + ", ".join(missing))
    notebook_sha256 = _file_sha256(path)
    if notebook_sha256 != expected_sha256:
        raise RuntimeError("notebook raw identity drifted")
    return {
        "notebook_name": expected_name,
        "notebook_sha256": notebook_sha256,
        "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "output_cells_present": False,
        "execution_counts_present": False,
    }


def validate_repository_package(repo_root: Path) -> dict[str, object]:
    """Validate preserved evidence, typed decision, and both unexecuted notebooks."""

    root = repo_root.resolve()
    if any((root / path).exists() for path in LEGACY_NOTEBOOK_PATHS):
        raise RuntimeError("legacy cu128 notebook identity remains in the repository")
    if (root / LEGACY_RUNBOOK_PATH).exists():
        raise RuntimeError("legacy cu128 runbook remains in the repository")

    superseded_adr = (root / SUPERSEDED_ADR_PATH).read_text(encoding="utf-8")
    if "Status: Superseded after failed materialization" not in superseded_adr:
        raise RuntimeError("superseded cu128 ADR lacks its correction state")
    if EXPECTED_MATERIALIZER_FAILURE_LOG_SHA256 not in superseded_adr:
        raise RuntimeError("superseded cu128 ADR lacks the failed-run identity")

    active_adr = (root / ADR_PATH).read_text(encoding="utf-8")
    required_adr_fragments = (
        "vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl",
        EXPECTED_VLLM_ASSET_SHA256,
        "torch 2.10.0+cu129",
        "CUDA 12.9",
        EXPECTED_MATERIALIZER_CDN_FAILURE_LOG_SHA256,
        EXPECTED_MATERIALIZER_NVIDIA_FAILURE_LOG_SHA256,
        "download-r2.pytorch.org",
        "pypi.nvidia.com",
        RECONNAISSANCE_NOTEBOOK_NAME,
    )
    if any(fragment not in active_adr for fragment in required_adr_fragments):
        raise RuntimeError("active cu129 ADR drifted")

    runbook = (root / RUNBOOK_PATH).read_text(encoding="utf-8")
    required_runbook_fragments = (
        MATERIALIZER_NOTEBOOK_NAME,
        VERIFIER_NOTEBOOK_NAME,
        OUTPUT_DIRECTORY_NAME,
        VERIFIER_EVIDENCE_DIRECTORY_NAME,
        EXPECTED_MATERIALIZER_FAILURE_LOG_SHA256,
        EXPECTED_MATERIALIZER_CDN_FAILURE_LOG_SHA256,
        EXPECTED_MATERIALIZER_NVIDIA_FAILURE_LOG_SHA256,
        "download-r2.pytorch.org",
        "pypi.nvidia.com",
        RECONNAISSANCE_NOTEBOOK_NAME,
    )
    if any(fragment not in runbook for fragment in required_runbook_fragments):
        raise RuntimeError("cu129 materialization runbook drifted")

    record = VllmRuntimeCompatibilityRemediationV1.model_validate(
        _load_json_object(root / RECORD_PATH)
    )
    if record.artifacts.materializer_notebook != MATERIALIZER_NOTEBOOK_PATH.as_posix():
        raise RuntimeError("materializer repository path drifted")
    if record.artifacts.verifier_notebook != VERIFIER_NOTEBOOK_PATH.as_posix():
        raise RuntimeError("verifier repository path drifted")
    if record.artifacts.reconnaissance_notebook != RECONNAISSANCE_NOTEBOOK_PATH.as_posix():
        raise RuntimeError("reconnaissance repository path drifted")
    if record.artifacts.materializer_kaggle_name != MATERIALIZER_NOTEBOOK_NAME:
        raise RuntimeError("materializer Kaggle title drifted")
    if record.artifacts.verifier_kaggle_name != VERIFIER_NOTEBOOK_NAME:
        raise RuntimeError("verifier Kaggle title drifted")
    if record.artifacts.reconnaissance_kaggle_name != RECONNAISSANCE_NOTEBOOK_NAME:
        raise RuntimeError("reconnaissance Kaggle title drifted")
    if record.artifacts.reconnaissance_output_directory != RECONNAISSANCE_OUTPUT_DIRECTORY_NAME:
        raise RuntimeError("reconnaissance output identity drifted")
    if record.artifacts.resolution_lock_sha256 != EXPECTED_RESOLUTION_LOCK_SHA256:
        raise RuntimeError("resolution lock identity drifted")
    if record.materializer_contract.notebook_sha256 != EXPECTED_MATERIALIZER_NOTEBOOK_SHA256:
        raise RuntimeError("materializer contract identity drifted")
    if record.materializer_contract.expected_package_count != 176:
        raise RuntimeError("materializer package count drifted")
    if record.artifacts.output_directory != OUTPUT_DIRECTORY_NAME:
        raise RuntimeError("wheelhouse output identity drifted")
    if record.artifacts.verifier_evidence_directory != VERIFIER_EVIDENCE_DIRECTORY_NAME:
        raise RuntimeError("verifier evidence output identity drifted")
    if record.materializer_failure.execution_log_sha256 != EXPECTED_MATERIALIZER_FAILURE_LOG_SHA256:
        raise RuntimeError("materializer failure-log identity drifted")
    if (
        record.materializer_cdn_failure.execution_log_sha256
        != EXPECTED_MATERIALIZER_CDN_FAILURE_LOG_SHA256
    ):
        raise RuntimeError("materializer CDN failure-log identity drifted")
    if record.materializer_cdn_failure.observed_host != "download-r2.pytorch.org":
        raise RuntimeError("materializer CDN failure host drifted")
    if (
        record.materializer_nvidia_failure.execution_log_sha256
        != EXPECTED_MATERIALIZER_NVIDIA_FAILURE_LOG_SHA256
    ):
        raise RuntimeError("materializer NVIDIA failure-log identity drifted")
    if record.materializer_nvidia_failure.observed_host != "pypi.nvidia.com":
        raise RuntimeError("materializer NVIDIA failure host drifted")
    if record.selected_runtime.vllm_asset_sha256 != EXPECTED_VLLM_ASSET_SHA256:
        raise RuntimeError("selected vLLM release-asset identity drifted")

    source_identity = _load_json_object(root / SOURCE_IDENTITY_PATH)
    expected_source = {
        "qualification_evidence_zip_sha256": EXPECTED_QUALIFICATION_EVIDENCE_ZIP_SHA256,
        "qualification_log_sha256": EXPECTED_QUALIFICATION_LOG_SHA256,
        "diagnostic_evidence_zip_sha256": EXPECTED_DIAGNOSTIC_EVIDENCE_ZIP_SHA256,
    }
    for key, expected_value in expected_source.items():
        if source_identity.get(key) != expected_value:
            raise RuntimeError(f"source evidence identity drifted at {key}")

    evidence_manifest = _load_json_object(root / EVIDENCE_SHA256_PATH)
    files = evidence_manifest.get("files")
    if not isinstance(files, list) or len(files) != 18:
        raise RuntimeError("preserved evidence manifest must contain exactly 18 files")
    for entry in files:
        if not isinstance(entry, dict):
            raise RuntimeError("preserved evidence entry is invalid")
        relative_raw = entry.get("path")
        digest = entry.get("sha256")
        size_bytes = entry.get("size_bytes")
        if not isinstance(relative_raw, str):
            raise RuntimeError("preserved evidence path is invalid")
        relative = PurePosixPath(relative_raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("preserved evidence path is unsafe")
        path = root / EVIDENCE_DIRECTORY / Path(*relative.parts)
        if not path.is_file() or path.is_symlink():
            raise RuntimeError("preserved evidence file is missing or unsafe")
        if digest != _file_sha256(path) or size_bytes != path.stat().st_size:
            raise RuntimeError("preserved evidence identity drifted")

    torch_probe = _load_json_object(
        root / EVIDENCE_DIRECTORY / "diagnostic/10_probe_torch_runtime.json"
    )
    torch_payload = torch_probe.get("payload")
    if not isinstance(torch_payload, dict):
        raise RuntimeError("torch diagnostic payload is missing")
    expected_torch = {
        "torch": "2.10.0+cu128",
        "cuda_version": "12.8",
        "cuda_available": True,
        "cuda_device_count": 2,
        "cuda_device_names": ["Tesla T4", "Tesla T4"],
    }
    if torch_payload != expected_torch:
        raise RuntimeError("torch diagnostic payload drifted")

    vllm_probe = _load_json_object(
        root / EVIDENCE_DIRECTORY / "diagnostic/10_probe_vllm_module.json"
    )
    stderr_excerpt = vllm_probe.get("stderr_excerpt")
    if not isinstance(stderr_excerpt, str) or "undefined symbol: torch_from_blob" not in (
        stderr_excerpt
    ):
        raise RuntimeError("vLLM ABI failure evidence drifted")

    pip_check = _load_json_object(root / EVIDENCE_DIRECTORY / "diagnostic/10_pip_check.json")
    stdout_excerpt = pip_check.get("stdout_excerpt")
    if not isinstance(stdout_excerpt, str):
        raise RuntimeError("pip-check diagnostic output is missing")
    required_pip_fragments = (
        "vllm 0.25.1+cu129 has requirement torch==2.11.0",
        "vllm 0.25.1+cu129 has requirement transformers>=5.5.3",
    )
    if any(fragment not in stdout_excerpt for fragment in required_pip_fragments):
        raise RuntimeError("dependency-closure diagnostic evidence drifted")

    materializer = _validate_notebook(
        root / MATERIALIZER_NOTEBOOK_PATH,
        expected_name=MATERIALIZER_NOTEBOOK_NAME,
        expected_sha256=EXPECTED_MATERIALIZER_NOTEBOOK_SHA256,
        expected_internet=True,
        expected_accelerator="none",
        required_fragments=(
            'NOTEBOOK_NAME = "auragateway-cu129-wheelhouse-materializer-v1"',
            'OUTPUT_DIRECTORY_NAME = "auragateway_vllm_cu129_wheelhouse_v1"',
            'VLLM_RELEASE = "0.19.1"',
            'VLLM_DISTRIBUTION = "0.19.1"',
            'VLLM_ASSET_NAME = "vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl"',
            EXPECTED_VLLM_ASSET_SHA256,
            '"torch==2.10.0+cu129"',
            '"transformers==5.5.3"',
            '"download-r2.pytorch.org"',
            '"pypi.nvidia.com"',
            (
                "RESOLUTION_LOCK_SHA256 = "
                '"1575538b0a412c9b030fc95ccada0f0527553b76f06ef6b2b72904e61c84870c"'
            ),
            '"RESOLUTION_LOCK_MISMATCH"',
            '"torch-2.10.0+cu129-"',
            '"pip_resolution_artifact_transfer_observed"',
            '"--require-hashes"',
            '"materialization_status=PASSED"',
        ),
    )
    verifier = _validate_notebook(
        root / VERIFIER_NOTEBOOK_PATH,
        expected_name=VERIFIER_NOTEBOOK_NAME,
        expected_sha256=EXPECTED_VERIFIER_NOTEBOOK_SHA256,
        expected_internet=False,
        expected_accelerator="T4 x2",
        required_fragments=(
            'NOTEBOOK_NAME = "auragateway-cu129-offline-verifier-v1"',
            (
                'OUTPUT_ZIP = Path("/kaggle/working/'
                'auragateway_vllm_cu129_offline_compatibility_evidence_v1.zip")'
            ),
            (
                'EVIDENCE_ROOT = Path("/kaggle/working/'
                'auragateway_vllm_cu129_offline_compatibility_evidence_v1")'
            ),
            '"diagnostic_id": "auragateway-cu129-offline-verifier-v1"',
            '"torch": "2.10.0+cu129"',
            '"cuda": "12.9"',
            '"vllm_distribution": "0.19.1"',
            '"--no-index"',
            '"offline_isolated_install"',
            '"vllm_native_extension"',
            '"model_requests_performed=0"',
            '"qualification_claimed=false"',
        ),
    )
    reconnaissance = _validate_notebook(
        root / RECONNAISSANCE_NOTEBOOK_PATH,
        expected_name=RECONNAISSANCE_NOTEBOOK_NAME,
        expected_sha256=EXPECTED_RECONNAISSANCE_NOTEBOOK_SHA256,
        expected_internet=True,
        expected_accelerator="none",
        required_fragments=(
            'NOTEBOOK_NAME = "auragateway-cu129-resolution-reconnaissance-v1"',
            ('OUTPUT_DIRECTORY_NAME = "auragateway_vllm_cu129_resolution_reconnaissance_v1"'),
            '"--dry-run"',
            '"--report"',
            '"pypi.nvidia.com": "nvidia"',
            '"ARTIFACT_HOST_REVIEW_REQUIRED"',
            '"wheel_files_written": len(tuple(OUTPUT_ROOT.rglob("*.whl")))',
            '"model_requests_performed": 0',
            '"qualification_claimed": False',
        ),
    )

    return {
        "status": "VLLM_RUNTIME_COMPATIBILITY_PACKAGE_VALID",
        "record_sha256": _file_sha256(root / RECORD_PATH),
        "evidence_files_verified": len(files) + 1,
        "qualification_evidence_zip_sha256": EXPECTED_QUALIFICATION_EVIDENCE_ZIP_SHA256,
        "diagnostic_evidence_zip_sha256": EXPECTED_DIAGNOSTIC_EVIDENCE_ZIP_SHA256,
        "failure_code": record.failure.primary_code,
        "materializer_failure_code": record.materializer_failure.code,
        "materializer_cdn_failure_code": record.materializer_cdn_failure.code,
        "materializer_nvidia_failure_code": record.materializer_nvidia_failure.code,
        "selected_vllm": record.selected_runtime.vllm,
        "selected_torch": record.selected_runtime.torch,
        "selected_cuda_variant": record.selected_runtime.cuda_variant,
        "materializer_notebook_sha256": materializer["notebook_sha256"],
        "resolution_lock_sha256": EXPECTED_RESOLUTION_LOCK_SHA256,
        "approved_package_count": 176,
        "verifier_notebook_sha256": verifier["notebook_sha256"],
        "reconnaissance_notebook_sha256": reconnaissance["notebook_sha256"],
        "materializer_paused": False,
        "authorization_issued": record.safety.authorization_issued,
        "model_requests_performed": record.safety.model_requests_performed,
        "qualification_claimed": record.safety.qualification_claimed,
        "next_gate": record.next_gate,
    }


def main() -> int:
    """Validate the repository package and print canonical JSON."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args()
    print(json.dumps(validate_repository_package(args.repo_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

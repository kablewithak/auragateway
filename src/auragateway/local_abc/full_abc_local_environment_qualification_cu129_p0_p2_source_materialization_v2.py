"""Build and validate the P0-P2 source materialization V2 toolchain."""

from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import os
import re
import sys
import zipfile
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import Field, ValidationError, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

SOURCE_MAIN_BASE_COMMIT: Final = "24914d79ef4b4d33285f111c8920d16c36244614"
OPTION_C_DECISION_MERGE_COMMIT: Final = "f4f08eda4b4d4747514b4646fe53664d8a78ca6d"
ARCHITECTURE_ORIGIN_BRANCH: Final = "fix/local-abc-cu129-p1-probe-taxonomy-v1"

REVIEW_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_source_materialization_review_v2.json"
)
TOOLCHAIN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_source_materialization_toolchain_v2.json"
)
MATERIALIZER_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_p0_p2_source_materializer_v2.ipynb"
)
INSPECTION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_cu129_p0_p2_source_input_inspection_v2.ipynb"
)
MATERIALIZER_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p0_p2_source_materializer_v2.py.tmpl"
)
INSPECTION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p0_p2_source_input_inspection_v2.py.tmpl"
)
LINEAGE_REMEDIATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_cu129_p0_p2_lineage_semantics_remediation_v1.json"
)

AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_full_run_environment_qualification_"
    "execution_authorization_v1.json"
)

MATERIALIZER_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-materializer-v2"
INSPECTION_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-inspection-v2"
MATERIALIZER_FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-mat-failed-v2"
INSPECTION_FAILED_NOTEBOOK_NAME: Final = "ag-cu129-p0-p2-source-insp-failed-v2"
OUTPUT_DATASET_NAME: Final = "ag-cu129-p0-p2-source-v2"
OUTPUT_DIRECTORY_NAME: Final = "ag_cu129_p0_p2_source_materializer_v2_output"
INSPECTION_EVIDENCE_ZIP_NAME: Final = "ag-cu129-p0-p2-source-inspection-v2.zip"
SOURCE_BUNDLE_NAME: Final = "ag-cu129-p0-p2-source-bundle-v2.zip"
BUNDLE_MANIFEST_NAME: Final = "bundle_manifest.json"

ZIP_TIMESTAMP: Final = (1980, 1, 1, 0, 0, 0)
BASE64_CHUNK_WIDTH: Final = 72
MAXIMUM_KAGGLE_NAME_CHARACTERS: Final = 50
MAXIMUM_GENERATED_LINE_LENGTH: Final = 100
EXPECTED_SOURCE_ARTIFACT_COUNT: Final = 3

LEGACY_V1_PATHS: Final = (
    Path("benchmarks/local_abc/auragateway_cu129_p0_p2_source_materialization_review_v1.json"),
    Path("benchmarks/local_abc/auragateway_cu129_p0_p2_source_materialization_toolchain_v1.json"),
    Path("docs/adr/2026-07-29-local-abc-cu129-p0-p2-source-materialization.md"),
    Path("docs/reports/AuraGateway_CU129_P0_P2_Source_Materialization_Review.md"),
    Path("docs/runbooks/local_abc_cu129_p0_p2_source_materialization_v1.md"),
    Path("notebooks/auragateway_cu129_p0_p2_source_input_inspection_v1.ipynb"),
    Path("notebooks/auragateway_cu129_p0_p2_source_materializer_v1.ipynb"),
    Path(
        "src/auragateway/local_abc/"
        "full_abc_local_environment_qualification_"
        "cu129_p0_p2_source_materialization.py"
    ),
    Path(
        "tests/unit/local_abc/"
        "test_full_abc_local_environment_qualification_"
        "cu129_p0_p2_source_materialization.py"
    ),
)


class P0P2SourceMaterializationV2Error(RuntimeError):
    """Fail-closed V2 source-materialization error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        """Return a machine-readable error envelope."""

        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class SourceArtifactBinding(LocalABCContract):
    """Exact repository source artifact included in the deterministic bundle."""

    role: Literal[
        "diagnostic_notebook",
        "diagnostic_request",
        "implementation_record",
    ]
    repository_path: str = Field(min_length=3, max_length=240)
    output_name: str = Field(min_length=3, max_length=160)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)

    @field_validator("repository_path")
    @classmethod
    def validate_repository_path(cls, value: str) -> str:
        """Reject unsafe or non-canonical repository paths."""

        path = PurePosixPath(value)
        if (
            path.is_absolute()
            or ".." in path.parts
            or "\\" in value
            or value.startswith("./")
            or path.as_posix() != value
        ):
            raise ValueError("repository path is unsafe or non-canonical")
        return value

    @field_validator("output_name")
    @classmethod
    def validate_output_name(cls, value: str) -> str:
        """Require one safe basename for Kaggle materialization."""

        path = PurePosixPath(value)
        if path.is_absolute() or len(path.parts) != 1 or value in {".", ".."} or "\\" in value:
            raise ValueError("output name must be one safe basename")
        return value


SOURCE_BINDINGS: Final = (
    SourceArtifactBinding(
        role="diagnostic_notebook",
        repository_path=("notebooks/auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb"),
        output_name=("auragateway_cu129_p0_p2_platform_diagnostic_v1.ipynb"),
        sha256=("2f62c6ebfebba148db6f5f9192a474f22ec7599099c397a4169f811849db8603"),
        size_bytes=51853,
    ),
    SourceArtifactBinding(
        role="diagnostic_request",
        repository_path=(
            "data/evals/benchmark/environment-qualification-v1/"
            "option_c_p0_p2_platform_diagnostic_request.json"
        ),
        output_name="option_c_p0_p2_platform_diagnostic_request.json",
        sha256=("ae70648c21ddd4899bc5e2c3c8cb8346387949e4320d5e9858352bf11e774eae"),
        size_bytes=2113,
    ),
    SourceArtifactBinding(
        role="implementation_record",
        repository_path=(
            "benchmarks/local_abc/"
            "auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json"
        ),
        output_name=("auragateway_cu129_p0_p2_platform_diagnostic_implementation_v1.json"),
        sha256=("27316b176bda4bf24d293213fe5ff34326b2c27c0ac015359fcdd4858d5765ba"),
        size_bytes=2544,
    ),
)


class SourceBundleManifest(LocalABCContract):
    """Manifest embedded in the deterministic source bundle."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    bundle_id: Literal["auragateway-cu129-p0-p2-source-bundle-v2"] = (
        "auragateway-cu129-p0-p2-source-bundle-v2"
    )
    source_main_base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    option_c_decision_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    artifacts: tuple[SourceArtifactBinding, ...]

    @model_validator(mode="after")
    def validate_artifacts(self) -> Self:
        """Require the exact role set and canonical artifact ordering."""

        if len(self.artifacts) != EXPECTED_SOURCE_ARTIFACT_COUNT:
            raise ValueError("source bundle must contain exactly three artifacts")
        roles = tuple(item.role for item in self.artifacts)
        if roles != (
            "diagnostic_notebook",
            "diagnostic_request",
            "implementation_record",
        ):
            raise ValueError("source artifact roles or ordering drifted")
        output_names = tuple(item.output_name for item in self.artifacts)
        if len(output_names) != len(set(output_names)):
            raise ValueError("source output names must be unique")
        return self


class SafetyRecord(LocalABCContract):
    """Static safety proof for the V2 materialization tranche."""

    authorization_issued: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    package_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_spend: Literal[0] = 0


class SourceMaterializationReviewRecord(LocalABCContract):
    """Approved global redesign contract."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-source-materialization-review-v2"]
    decision: Literal["CLEAN_GLOBAL_REBUILD"]
    rejected_architecture: Literal["NESTED_STRING_FRAGMENT_CODE_GENERATION"]
    source_main_base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    architecture_origin_branch: Literal["fix/local-abc-cu129-p1-probe-taxonomy-v1"]
    source_artifacts: tuple[SourceArtifactBinding, ...]
    source_bundle_name: Literal["ag-cu129-p0-p2-source-bundle-v2.zip"]
    materializer_notebook_name: str
    inspection_notebook_name: str
    output_dataset_name: str
    architecture_requirements: tuple[str, ...]
    prohibited_techniques: tuple[str, ...]
    safety: SafetyRecord
    next_gate: Literal["execute_cpu_only_p0_p2_source_materializer_v2"]

    @model_validator(mode="after")
    def validate_review(self) -> Self:
        """Validate the exact approved V2 redesign."""

        if self.source_main_base_commit != SOURCE_MAIN_BASE_COMMIT:
            raise ValueError("review source main base commit drifted")
        if self.source_artifacts != SOURCE_BINDINGS:
            raise ValueError("review source artifact bindings drifted")
        if self.materializer_notebook_name != MATERIALIZER_NOTEBOOK_NAME:
            raise ValueError("materializer notebook name drifted")
        if self.inspection_notebook_name != INSPECTION_NOTEBOOK_NAME:
            raise ValueError("inspection notebook name drifted")
        if self.output_dataset_name != OUTPUT_DATASET_NAME:
            raise ValueError("output dataset name drifted")
        required_architecture = {
            "deterministic_source_bundle",
            "fixed_width_base64_chunks",
            "ordinary_multiline_notebook_templates",
            "safe_bundle_member_validation",
            "two_build_byte_determinism",
            "generated_source_compile_and_line_length_gates",
        }
        if set(self.architecture_requirements) != required_architecture:
            raise ValueError("architecture requirement set drifted")
        required_prohibitions = {
            "manual_generated_notebook_edits",
            "nested_lines_extend_program_construction",
            "whitespace_sensitive_source_surgery",
            "broad_ruff_format",
            "runtime_or_kaggle_execution",
        }
        if set(self.prohibited_techniques) != required_prohibitions:
            raise ValueError("prohibited technique set drifted")
        return self


class GeneratedNotebookReceipt(LocalABCContract):
    """Identity receipt for one generated unexecuted notebook."""

    notebook_name: str
    repository_path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cell_count: Literal[2] = 2
    outputs_present: Literal[False] = False
    execution_counts_present: Literal[False] = False
    maximum_code_line_length: int = Field(ge=1, le=100)


class SourceMaterializationToolchainRecord(LocalABCContract):
    """Complete generated V2 toolchain identity."""

    schema_version: Literal["2.0.0"] = "2.0.0"
    record_id: Literal["auragateway-cu129-p0-p2-source-materialization-toolchain-v2"]
    status: Literal["P0_P2_SOURCE_MATERIALIZATION_TOOLCHAIN_V2_VALID"]
    source_main_base_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    source_bundle_name: str
    source_bundle_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    bundle_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_artifact_count: Literal[3] = 3
    materializer: GeneratedNotebookReceipt
    inspection: GeneratedNotebookReceipt
    output_dataset_name: str
    output_directory_name: str
    inspection_evidence_zip_name: str
    generation_deterministic: Literal[True] = True
    nested_string_fragment_generation_present: Literal[False] = False
    safety: SafetyRecord
    next_gate: Literal["execute_cpu_only_p0_p2_source_materializer_v2"]


class GeneratedToolchain:
    """In-memory deterministic generation result."""

    def __init__(
        self,
        *,
        bundle_bytes: bytes,
        bundle_manifest_bytes: bytes,
        source_inventory_bytes: bytes,
        materializer_notebook_bytes: bytes,
        inspection_notebook_bytes: bytes,
        record: SourceMaterializationToolchainRecord,
    ) -> None:
        self.bundle_bytes = bundle_bytes
        self.bundle_manifest_bytes = bundle_manifest_bytes
        self.source_inventory_bytes = source_inventory_bytes
        self.materializer_notebook_bytes = materializer_notebook_bytes
        self.inspection_notebook_bytes = inspection_notebook_bytes
        self.record = record


def _canonical_json(payload: object) -> str:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _canonical_json_bytes(payload: object) -> bytes:
    return _canonical_json(payload).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    if temporary.exists():
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TEMPORARY_PATH_EXISTS",
            "temporary output path already exists",
            temporary.as_posix(),
        )
    temporary.write_bytes(payload)
    temporary.replace(path)


def _validate_safe_bundle_name(value: str) -> str:
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or len(path.parts) != 1
        or ".." in path.parts
        or "\\" in value
        or value in {".", ".."}
    ):
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_UNSAFE_BUNDLE_MEMBER",
            "source bundle member name is unsafe",
            value,
        )
    return value


def _read_bound_source_artifacts(
    repo_root: Path,
    bindings: Sequence[SourceArtifactBinding],
) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    for binding in bindings:
        source_path = repo_root / binding.repository_path
        if not source_path.is_file() or source_path.is_symlink():
            raise P0P2SourceMaterializationV2Error(
                "P0_P2_V2_SOURCE_ARTIFACT_MISSING",
                "bound source artifact is missing or unsafe",
                binding.repository_path,
            )
        payload = source_path.read_bytes()
        if len(payload) != binding.size_bytes:
            raise P0P2SourceMaterializationV2Error(
                "P0_P2_V2_SOURCE_SIZE_DRIFT",
                "bound source artifact size drifted",
                binding.repository_path,
            )
        if _sha256_bytes(payload) != binding.sha256:
            raise P0P2SourceMaterializationV2Error(
                "P0_P2_V2_SOURCE_IDENTITY_DRIFT",
                "bound source artifact identity drifted",
                binding.repository_path,
            )
        payloads[binding.output_name] = payload
    return payloads


def _source_inventory_payload(
    bindings: Sequence[SourceArtifactBinding],
) -> list[dict[str, object]]:
    return [
        {
            "role": binding.role,
            "path": binding.output_name,
            "sha256": binding.sha256,
            "size_bytes": binding.size_bytes,
        }
        for binding in bindings
    ]


def _build_bundle_once(
    manifest_bytes: bytes,
    source_payloads: Mapping[str, bytes],
) -> bytes:
    output = io.BytesIO()
    members = {
        BUNDLE_MANIFEST_NAME: manifest_bytes,
        **dict(source_payloads),
    }
    with zipfile.ZipFile(
        output,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(members):
            safe_name = _validate_safe_bundle_name(name)
            info = zipfile.ZipInfo(safe_name, date_time=ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info,
                members[name],
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=9,
            )
    return output.getvalue()


def build_source_bundle(
    repo_root: Path,
    bindings: Sequence[SourceArtifactBinding] | None = None,
    *,
    source_main_base_commit: str = SOURCE_MAIN_BASE_COMMIT,
) -> tuple[bytes, bytes, bytes]:
    """Build the deterministic source bundle and canonical control payloads."""

    artifacts = SOURCE_BINDINGS if bindings is None else tuple(bindings)
    manifest = SourceBundleManifest(
        source_main_base_commit=source_main_base_commit,
        option_c_decision_merge_commit=(OPTION_C_DECISION_MERGE_COMMIT),
        artifacts=artifacts,
    )
    manifest_bytes = manifest.canonical_json().encode("utf-8")
    source_payloads = _read_bound_source_artifacts(repo_root, artifacts)
    first = _build_bundle_once(manifest_bytes, source_payloads)
    second = _build_bundle_once(manifest_bytes, source_payloads)
    if first != second:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_BUNDLE_NONDETERMINISTIC",
            "two source bundle builds from identical inputs differed",
        )
    inventory_bytes = _canonical_json_bytes(_source_inventory_payload(artifacts))
    return first, manifest_bytes, inventory_bytes


def _base64_expression(payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    chunks = [
        encoded[index : index + BASE64_CHUNK_WIDTH]
        for index in range(0, len(encoded), BASE64_CHUNK_WIDTH)
    ]
    lines = ["SOURCE_BUNDLE_B64 = ("]
    lines.extend(f'    "{chunk}"' for chunk in chunks)
    lines.append(")")
    expression = "\n".join(lines)
    if max(len(line) for line in expression.splitlines()) > 100:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_BASE64_LINE_TOO_LONG",
            "fixed-width base64 expression exceeded line policy",
        )
    return expression


def _load_template(repo_root: Path, relative_path: Path) -> str:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TEMPLATE_MISSING",
            "ordinary notebook template is missing or unsafe",
            relative_path.as_posix(),
        )
    return path.read_text(encoding="utf-8")


def _render_template(
    template: str,
    replacements: Mapping[str, str],
) -> str:
    rendered = template.strip()
    for token, value in replacements.items():
        marker = f"__{token}__"
        if rendered.count(marker) != 1:
            raise P0P2SourceMaterializationV2Error(
                "P0_P2_V2_TEMPLATE_TOKEN_DRIFT",
                "template token count drifted",
                marker,
            )
        rendered = rendered.replace(marker, value)
    unresolved = sorted(set(re.findall(r"__[A-Z][A-Z0-9_]+__", rendered)))
    if unresolved:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TEMPLATE_TOKEN_UNRESOLVED",
            "generated notebook template contains unresolved tokens",
            ",".join(unresolved),
        )
    return rendered


def _maximum_line_length(source: str) -> int:
    return max(len(line) for line in source.splitlines())


def _validate_generated_source(
    source: str,
    *,
    label: str,
) -> int:
    try:
        compile(source, label, "exec")
    except SyntaxError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_GENERATED_SOURCE_INVALID",
            "generated notebook source failed Python compilation",
            label,
        ) from exc
    maximum = _maximum_line_length(source)
    if maximum > MAXIMUM_GENERATED_LINE_LENGTH:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_GENERATED_LINE_TOO_LONG",
            "generated notebook source exceeded line-length policy",
            f"{label}:{maximum}",
        )
    prohibited = (
        "lines.extend([",
        "subprocess",
        "torch.cuda",
        "AutoModel",
        "AutoTokenizer",
        "execute_from_environment",
    )
    observed = tuple(token for token in prohibited if token in source)
    if observed:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_GENERATED_ACTIVITY_PROHIBITED",
            "generated notebook contains prohibited source patterns",
            f"{label}:{observed!r}",
        )
    return maximum


def _notebook_payload(
    *,
    title: str,
    instructions: str,
    source: str,
) -> dict[str, object]:
    return {
        "cells": [
            {
                "cell_type": "markdown",
                "metadata": {},
                "source": (f"# {title}\n\n{instructions}\n").splitlines(keepends=True),
            },
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def _notebook_bytes(payload: dict[str, object]) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=1,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def build_generated_toolchain(
    repo_root: Path,
    bindings: Sequence[SourceArtifactBinding] | None = None,
    *,
    source_main_base_commit: str = SOURCE_MAIN_BASE_COMMIT,
) -> GeneratedToolchain:
    """Build all generated V2 artifacts in memory."""

    bundle_bytes, manifest_bytes, inventory_bytes = build_source_bundle(
        repo_root,
        bindings,
        source_main_base_commit=source_main_base_commit,
    )
    bundle_sha256 = _sha256_bytes(bundle_bytes)
    manifest_sha256 = _sha256_bytes(manifest_bytes)
    inventory_sha256 = _sha256_bytes(inventory_bytes)
    common_replacements = {
        "OUTPUT_DATASET_NAME": OUTPUT_DATASET_NAME,
        "OUTPUT_DIRECTORY_NAME": OUTPUT_DIRECTORY_NAME,
        "SOURCE_BUNDLE_NAME": SOURCE_BUNDLE_NAME,
        "SOURCE_BUNDLE_SHA256": bundle_sha256,
        "BUNDLE_MANIFEST_SHA256": manifest_sha256,
        "SOURCE_INVENTORY_SHA256": inventory_sha256,
        "SOURCE_MAIN_BASE_COMMIT": source_main_base_commit,
    }
    materializer_source = _render_template(
        _load_template(repo_root, MATERIALIZER_TEMPLATE_PATH),
        {
            **common_replacements,
            "MATERIALIZER_NOTEBOOK_NAME": MATERIALIZER_NOTEBOOK_NAME,
            "SOURCE_BUNDLE_B64": _base64_expression(bundle_bytes),
        },
    )
    inspection_source = _render_template(
        _load_template(repo_root, INSPECTION_TEMPLATE_PATH),
        {
            "OUTPUT_DATASET_NAME": OUTPUT_DATASET_NAME,
            "OUTPUT_DIRECTORY_NAME": OUTPUT_DIRECTORY_NAME,
            "SOURCE_BUNDLE_SHA256": bundle_sha256,
            "BUNDLE_MANIFEST_SHA256": manifest_sha256,
            "SOURCE_INVENTORY_SHA256": inventory_sha256,
            "SOURCE_MAIN_BASE_COMMIT": source_main_base_commit,
            "INSPECTION_NOTEBOOK_NAME": INSPECTION_NOTEBOOK_NAME,
            "INSPECTION_REPORT_NAME": ("p0_p2_source_input_inspection_report.json"),
            "INSPECTION_EVIDENCE_ZIP_NAME": (INSPECTION_EVIDENCE_ZIP_NAME),
        },
    )
    materializer_maximum = _validate_generated_source(
        materializer_source,
        label=MATERIALIZER_NOTEBOOK_PATH.as_posix(),
    )
    inspection_maximum = _validate_generated_source(
        inspection_source,
        label=INSPECTION_NOTEBOOK_PATH.as_posix(),
    )
    materializer_bytes = _notebook_bytes(
        _notebook_payload(
            title="AuraGateway P0-P2 source materializer V2",
            instructions=(
                "CPU-only publisher. Use Accelerator None, Internet Off, "
                "no secrets, and Save & Run All exactly once."
            ),
            source=materializer_source,
        )
    )
    inspection_bytes = _notebook_bytes(
        _notebook_payload(
            title="AuraGateway P0-P2 source input inspection V2",
            instructions=(
                "Metadata-only inspection. Attach exactly one successful "
                "materializer output, use Accelerator None and Internet Off."
            ),
            source=inspection_source,
        )
    )
    record = SourceMaterializationToolchainRecord(
        record_id=("auragateway-cu129-p0-p2-source-materialization-toolchain-v2"),
        status="P0_P2_SOURCE_MATERIALIZATION_TOOLCHAIN_V2_VALID",
        source_main_base_commit=source_main_base_commit,
        source_bundle_name=SOURCE_BUNDLE_NAME,
        source_bundle_sha256=bundle_sha256,
        bundle_manifest_sha256=manifest_sha256,
        source_inventory_sha256=inventory_sha256,
        materializer=GeneratedNotebookReceipt(
            notebook_name=MATERIALIZER_NOTEBOOK_NAME,
            repository_path=MATERIALIZER_NOTEBOOK_PATH.as_posix(),
            sha256=_sha256_bytes(materializer_bytes),
            maximum_code_line_length=materializer_maximum,
        ),
        inspection=GeneratedNotebookReceipt(
            notebook_name=INSPECTION_NOTEBOOK_NAME,
            repository_path=INSPECTION_NOTEBOOK_PATH.as_posix(),
            sha256=_sha256_bytes(inspection_bytes),
            maximum_code_line_length=inspection_maximum,
        ),
        output_dataset_name=OUTPUT_DATASET_NAME,
        output_directory_name=OUTPUT_DIRECTORY_NAME,
        inspection_evidence_zip_name=INSPECTION_EVIDENCE_ZIP_NAME,
        safety=SafetyRecord(),
        next_gate="execute_cpu_only_p0_p2_source_materializer_v2",
    )
    return GeneratedToolchain(
        bundle_bytes=bundle_bytes,
        bundle_manifest_bytes=manifest_bytes,
        source_inventory_bytes=inventory_bytes,
        materializer_notebook_bytes=materializer_bytes,
        inspection_notebook_bytes=inspection_bytes,
        record=record,
    )


def generate(repo_root: Path) -> SourceMaterializationToolchainRecord:
    """Generate the two notebooks and their exact toolchain record."""

    toolchain = build_generated_toolchain(repo_root)
    _write_bytes_atomic(
        repo_root / MATERIALIZER_NOTEBOOK_PATH,
        toolchain.materializer_notebook_bytes,
    )
    _write_bytes_atomic(
        repo_root / INSPECTION_NOTEBOOK_PATH,
        toolchain.inspection_notebook_bytes,
    )
    _write_bytes_atomic(
        repo_root / TOOLCHAIN_RECORD_PATH,
        toolchain.record.canonical_json().encode("utf-8"),
    )
    return toolchain.record


def _load_review_record(
    path: Path,
) -> SourceMaterializationReviewRecord:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_REVIEW_RECORD_MISSING",
            "V2 source-materialization review record is missing",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_REVIEW_RECORD_JSON_INVALID",
            "V2 source-materialization review record is invalid JSON",
            path.as_posix(),
        ) from exc
    try:
        return SourceMaterializationReviewRecord.model_validate(payload)
    except ValidationError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_REVIEW_RECORD_CONTRACT_INVALID",
            "V2 source-materialization review record violates its contract",
            path.as_posix(),
        ) from exc


def _load_toolchain_record(
    path: Path,
) -> SourceMaterializationToolchainRecord:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TOOLCHAIN_RECORD_MISSING",
            "V2 source-materialization toolchain record is missing",
            path.as_posix(),
        ) from exc
    except json.JSONDecodeError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TOOLCHAIN_RECORD_JSON_INVALID",
            "V2 source-materialization toolchain record is invalid JSON",
            path.as_posix(),
        ) from exc
    try:
        return SourceMaterializationToolchainRecord.model_validate(payload)
    except ValidationError as exc:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TOOLCHAIN_RECORD_CONTRACT_INVALID",
            "V2 source-materialization toolchain record violates its contract",
            path.as_posix(),
        ) from exc


def validate(repo_root: Path) -> SourceMaterializationToolchainRecord:
    """Validate exact source bindings and byte-identical generated outputs."""

    _load_review_record(repo_root / REVIEW_RECORD_PATH)
    if (repo_root / AUTHORIZATION_PATH).exists():
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_AUTHORIZATION_PRESENT",
            "transient authorization must be absent",
            AUTHORIZATION_PATH.as_posix(),
        )
    present_legacy = [path.as_posix() for path in LEGACY_V1_PATHS if (repo_root / path).exists()]
    if present_legacy:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_LEGACY_CANDIDATE_PRESENT",
            "rejected V1 candidate paths remain in the repository",
            ",".join(present_legacy),
        )
    expected = build_generated_toolchain(repo_root)
    observed_record = _load_toolchain_record(repo_root / TOOLCHAIN_RECORD_PATH)
    if observed_record != expected.record:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_TOOLCHAIN_RECORD_DRIFT",
            "generated V2 toolchain record drifted",
            TOOLCHAIN_RECORD_PATH.as_posix(),
        )
    expected_outputs = {
        MATERIALIZER_NOTEBOOK_PATH: (expected.materializer_notebook_bytes),
        INSPECTION_NOTEBOOK_PATH: (expected.inspection_notebook_bytes),
        TOOLCHAIN_RECORD_PATH: (expected.record.canonical_json().encode("utf-8")),
    }
    for relative_path, expected_bytes in expected_outputs.items():
        path = repo_root / relative_path
        if not path.is_file() or path.is_symlink():
            raise P0P2SourceMaterializationV2Error(
                "P0_P2_V2_GENERATED_OUTPUT_MISSING",
                "generated V2 output is missing or unsafe",
                relative_path.as_posix(),
            )
        if path.read_bytes() != expected_bytes:
            raise P0P2SourceMaterializationV2Error(
                "P0_P2_V2_GENERATED_OUTPUT_DRIFT",
                "generated V2 output differs from deterministic rebuild",
                relative_path.as_posix(),
            )
    return expected.record


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise P0P2SourceMaterializationV2Error(
            "P0_P2_V2_ARGUMENT_INVALID",
            message,
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--repo-root",
            type=Path,
            required=True,
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""

    try:
        arguments = _parser().parse_args(argv)
        repo_root = cast(Path, arguments.repo_root).resolve()
        if arguments.command == "generate":
            record = generate(repo_root)
            status = "P0_P2_SOURCE_MATERIALIZATION_V2_GENERATED"
        else:
            record = validate(repo_root)
            status = record.status
        print(
            _canonical_json(
                {
                    "status": status,
                    "source_bundle_sha256": record.source_bundle_sha256,
                    "materializer_notebook_name": (record.materializer.notebook_name),
                    "materializer_notebook_sha256": (record.materializer.sha256),
                    "inspection_notebook_name": (record.inspection.notebook_name),
                    "inspection_notebook_sha256": (record.inspection.sha256),
                    "source_artifact_count": (record.source_artifact_count),
                    "nested_string_fragment_generation_present": (
                        record.nested_string_fragment_generation_present
                    ),
                    "next_gate": record.next_gate,
                }
            )
        )
        return 0
    except P0P2SourceMaterializationV2Error as error:
        print(
            _canonical_json(error.envelope()),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

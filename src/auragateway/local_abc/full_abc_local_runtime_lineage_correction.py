"""Supersede the hosted-provider-contaminated full A/B/C preflight-v2 lineage."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, Self

from pydantic import field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,159}$")

SOURCE_MERGE_COMMIT = "eb86611670f6163a91343e76d79ff94f8fbfd88c"
SUPERSEDED_SOURCE_MERGE_COMMIT = "d6531fdc0b27892dcc299598f9f251fa157434dc"
SUPERSEDED_MANIFEST_GIT_BLOB_SHA = "2ed78faefbfa8cf8a464c8cc96349b808dd5c855"
NEXT_GATE = "full_abc_local_preflight_v3_rebuild_review"

CORRECTION_PATH = Path(
    "benchmarks/local_abc/auragateway_full_abc_local_runtime_lineage_correction_v1.json"
)
SUPERSESSION_PATH = Path(
    "data/evals/benchmark/preflight-v2/hosted_provider_lineage_supersession_v1.json"
)

_EXPECTED_INVALIDATED_FIELDS = (
    "dependency_lock.packages.groq",
    "condition_fingerprints.records[*].payload.pricing_schedule_id",
    "condition_fingerprints.records[*].payload.provider_adapter_version",
    "condition_fingerprints.records[*].payload.provider_model_alias",
    "execution_manifest_draft.assets.currency",
    "execution_manifest_draft.assets.pricing_schedule_id",
    "execution_manifest_draft.assets.pricing_schedule_sha256",
    "execution_manifest_draft.assets.pricing_source_date",
    "execution_manifest_draft.assets.provider_adapter_version",
    "execution_manifest_draft.assets.provider_model_alias",
    "execution_manifest_draft.unresolved_freeze_assets.cost_budget_approval",
    "execution_manifest_draft.unresolved_freeze_assets.provider_readiness_record",
    "preflight_report.checks.cost_approval_pending",
    "preflight_report.checks.provider_readiness_pending",
    "preflight_report.next_gate",
)

_EXPECTED_SUPERSEDED_HASHES = {
    "condition_fingerprints_sha256": (
        "6af3b45b8495ad41ef93b71db156305b78f9b72bf0de0ce04637f013c09ef6d0"
    ),
    "dependency_lock_sha256": ("44c69022985216f88fff5186a563724d8cb9b715577d47bfe1629a8ea19edd88"),
    "execution_manifest_sha256": (
        "ae0a70c4c0a00ebc5b11dad757b6f101d756e39d7d563b21d5a973dea451f9d9"
    ),
    "input_sha256": "fcfec50011e9851c9b904aa8155076997967057ef977ad53c28b59f1e570a0f7",
    "plan_sha256": "cf22d4dbb78a7b9bd9d77c90a1d2b5b20ebf1f27102ca919562d5ffd81f2c16a",
    "report_sha256": "1681a1964c6857e3824b0c834057dd8a3f84d886dfbe8206a189bdc1a1ace351",
    "spec_sha256": "e7bd972fe11f055b21fe66ae1d5deb362db37ad35b7c593327ef103afbda5678",
}


class FullABCLocalRuntimeLineageCorrectionError(RuntimeError):
    """Expected metadata-safe correction validation failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class FullABCLocalRuntimeLineageCorrectionErrorEnvelope(LocalABCContract):
    """Machine-readable error without prompt, output, credential, or payload content."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class FullABCWorkerBinding(LocalABCContract):
    """One worker in the fixed two-GPU local vLLM topology."""

    worker_id: Literal["worker_1", "worker_2"]
    gpu_index: Literal[0, 1]
    port: Literal[8001, 8002]

    @model_validator(mode="after")
    def validate_topology(self) -> Self:
        expected = {
            "worker_1": (0, 8001),
            "worker_2": (1, 8002),
        }
        if (self.gpu_index, self.port) != expected[self.worker_id]:
            raise ValueError("worker identity must match the fixed local A/B/C topology")
        return self


class FullABCLocalModelIdentity(LocalABCContract):
    """Exact open-weight model and tokenizer identity already qualified on T4."""

    model_alias: Literal["local-qwen2.5-0.5b-instruct"]
    repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"]
    revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    model_manifest_sha256: Literal[
        "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
    ]
    config_sha256: Literal["18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"]
    generation_config_sha256: Literal[
        "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"
    ]
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"]
    tokenizer_json_sha256: Literal[
        "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
    ]
    tokenizer_config_sha256: Literal[
        "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"
    ]


class FullABCLocalRuntimeIdentity(LocalABCContract):
    """North-star runtime identity for the zero-spend local A/B/C benchmark."""

    execution_backend: Literal["local_vllm"]
    environment: Literal["kaggle_t4_x2"]
    transport_endpoint: Literal["/v1/chat/completions"]
    worker_client_contract: Literal["auragateway.local_abc.worker_client.WorkerClient"]
    worker_registry_contract: Literal["auragateway.local_abc.worker_registry.WorkerRegistry"]
    model: FullABCLocalModelIdentity
    workers: tuple[FullABCWorkerBinding, FullABCWorkerBinding]
    gpu_count: Literal[2] = 2
    gpu_model: Literal["Tesla T4"] = "Tesla T4"
    compute_capability: Literal["7.5"] = "7.5"
    torch_version: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    vllm_module_version: Literal["0.25.1"] = "0.25.1"
    vllm_distribution_version: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_wheel_sha256: Literal["9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"]
    hosted_provider_required: Literal[False] = False
    provider_credentials_required: Literal[False] = False
    pricing_in_scope: Literal[False] = False
    paid_fallback_permitted: Literal[False] = False
    external_spend: Literal[0] = 0
    customer_data_used: Literal[False] = False
    current_full_run_environment_requalification_required: Literal[True] = True

    @model_validator(mode="after")
    def validate_workers(self) -> Self:
        if tuple(worker.worker_id for worker in self.workers) != (
            "worker_1",
            "worker_2",
        ):
            raise ValueError("local runtime workers must preserve worker_1, worker_2 order")
        if len({worker.gpu_index for worker in self.workers}) != 2:
            raise ValueError("local runtime workers must use independent GPUs")
        return self


class FullABCEvidenceBinding(LocalABCContract):
    """Canonical repository evidence supporting the local model/runtime identity."""

    evidence_id: str
    path: str
    canonical_sha256: str
    evidence_role: Literal[
        "two_worker_environment",
        "model_runtime_authorization",
        "successful_model_execution_audit",
        "authorization_consumption",
    ]

    @field_validator("evidence_id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence IDs must use stable lowercase characters")
        return value

    @field_validator("canonical_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("evidence bindings require lowercase SHA-256")
        return value

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("evidence paths must remain repository-relative")
        return path.as_posix()


class FullABCLocalRuntimeDirectionCorrection(LocalABCContract):
    """Authoritative decision superseding the hosted-provider-contaminated v2 draft."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    correction_id: Literal["auragateway-full-abc-local-runtime-lineage-correction-v1"]
    source_merge_commit: Literal["eb86611670f6163a91343e76d79ff94f8fbfd88c"]
    superseded_source_merge_commit: Literal["d6531fdc0b27892dcc299598f9f251fa157434dc"]
    superseded_manifest_path: Literal["data/evals/benchmark/preflight-v2/manifest.json"]
    superseded_manifest_git_blob_sha: Literal["2ed78faefbfa8cf8a464c8cc96349b808dd5c855"]
    superseded_artifact_hashes: dict[str, str]
    invalidated_fields: tuple[str, ...]
    failure_code: Literal["HOSTED_PROVIDER_LINEAGE_IMPORTED_INTO_LOCAL_BENCHMARK"]
    disposition: Literal["PREFLIGHT_V2_INVALIDATED_NON_EXECUTABLE"]
    local_runtime: FullABCLocalRuntimeIdentity
    evidence_bindings: tuple[
        FullABCEvidenceBinding,
        FullABCEvidenceBinding,
        FullABCEvidenceBinding,
        FullABCEvidenceBinding,
    ]
    preflight_v2_planning_authoritative: Literal[False] = False
    preflight_v2_execution_eligible: Literal[False] = False
    preflight_v2_comparison_eligible: Literal[False] = False
    groq_in_full_abc_scope: Literal[False] = False
    openrouter_in_full_abc_scope: Literal[False] = False
    hosted_provider_probe_required: Literal[False] = False
    cost_budget_required: Literal[False] = False
    pricing_schedule_required: Literal[False] = False
    model_execution_performed: Literal[False] = False
    provider_call_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    credential_accessed: Literal[False] = False
    measured_execution_authorized: Literal[False] = False
    claim_generation_permitted: Literal[False] = False
    next_gate: Literal["full_abc_local_preflight_v3_rebuild_review"]

    @field_validator("superseded_artifact_hashes")
    @classmethod
    def validate_superseded_hashes(cls, value: dict[str, str]) -> dict[str, str]:
        if value != _EXPECTED_SUPERSEDED_HASHES:
            raise ValueError("superseded artifact hashes drifted from merged PR 97")
        return dict(sorted(value.items()))

    @field_validator("invalidated_fields")
    @classmethod
    def validate_invalidated_fields(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if value != _EXPECTED_INVALIDATED_FIELDS:
            raise ValueError("invalidated hosted-provider field set drifted")
        return value

    @field_validator("evidence_bindings")
    @classmethod
    def validate_evidence_order(
        cls,
        value: tuple[
            FullABCEvidenceBinding,
            FullABCEvidenceBinding,
            FullABCEvidenceBinding,
            FullABCEvidenceBinding,
        ],
    ) -> tuple[
        FullABCEvidenceBinding,
        FullABCEvidenceBinding,
        FullABCEvidenceBinding,
        FullABCEvidenceBinding,
    ]:
        expected_roles = (
            "two_worker_environment",
            "model_runtime_authorization",
            "successful_model_execution_audit",
            "authorization_consumption",
        )
        if tuple(item.evidence_role for item in value) != expected_roles:
            raise ValueError("local runtime evidence bindings must preserve canonical order")
        return value


class FullABCPreflightV2SupersessionRecord(LocalABCContract):
    """Overlay that makes the erroneous preflight-v2 lineage fail closed."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    supersession_id: Literal["auragateway-full-abc-preflight-v2-supersession-v1"]
    source_merge_commit: Literal["eb86611670f6163a91343e76d79ff94f8fbfd88c"]
    correction_path: Literal[
        "benchmarks/local_abc/auragateway_full_abc_local_runtime_lineage_correction_v1.json"
    ]
    correction_sha256: str
    superseded_manifest_path: Literal["data/evals/benchmark/preflight-v2/manifest.json"]
    superseded_manifest_git_blob_sha: Literal["2ed78faefbfa8cf8a464c8cc96349b808dd5c855"]
    status: Literal["superseded_invalid_non_executable"]
    reason_code: Literal["HOSTED_PROVIDER_LINEAGE_IMPORTED_INTO_LOCAL_BENCHMARK"]
    provider_budget_review_permitted: Literal[False] = False
    provider_probe_permitted: Literal[False] = False
    preflight_v2_reuse_permitted: Literal[False] = False
    execution_authorized: Literal[False] = False
    next_gate: Literal["full_abc_local_preflight_v3_rebuild_review"]

    @field_validator("correction_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("supersession correction binding must be lowercase SHA-256")
        return value


class FullABCLocalRuntimeCorrectionPackage(LocalABCContract):
    """Validated correction and supersession pair."""

    correction: FullABCLocalRuntimeDirectionCorrection
    supersession: FullABCPreflightV2SupersessionRecord

    @model_validator(mode="after")
    def validate_cross_binding(self) -> Self:
        if self.supersession.correction_sha256 != self.correction.fingerprint():
            raise ValueError("supersession must bind the exact correction fingerprint")
        if (
            self.supersession.superseded_manifest_git_blob_sha
            != self.correction.superseded_manifest_git_blob_sha
        ):
            raise ValueError("correction and supersession must bind one v2 manifest")
        return self


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FullABCLocalRuntimeLineageCorrectionError(
            "LOCAL_RUNTIME_CORRECTION_ASSET_NOT_FOUND",
            "A required local-runtime correction artifact was not found.",
            str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise FullABCLocalRuntimeLineageCorrectionError(
            "LOCAL_RUNTIME_CORRECTION_ASSET_INVALID_JSON",
            "A local-runtime correction artifact is not valid JSON.",
            str(path),
        ) from exc


def load_full_abc_local_runtime_direction_correction(
    path: Path,
) -> FullABCLocalRuntimeDirectionCorrection:
    """Load and validate the authoritative correction decision."""

    try:
        return FullABCLocalRuntimeDirectionCorrection.model_validate(_load_json(path))
    except ValueError as exc:
        raise FullABCLocalRuntimeLineageCorrectionError(
            "LOCAL_RUNTIME_CORRECTION_VALIDATION_FAILED",
            "The local-runtime correction artifact failed typed validation.",
            str(path),
            (str(exc),),
        ) from exc


def load_full_abc_preflight_v2_supersession(
    path: Path,
) -> FullABCPreflightV2SupersessionRecord:
    """Load and validate the preflight-v2 supersession overlay."""

    try:
        return FullABCPreflightV2SupersessionRecord.model_validate(_load_json(path))
    except ValueError as exc:
        raise FullABCLocalRuntimeLineageCorrectionError(
            "PREFLIGHT_V2_SUPERSESSION_VALIDATION_FAILED",
            "The preflight-v2 supersession artifact failed typed validation.",
            str(path),
            (str(exc),),
        ) from exc


def load_full_abc_local_runtime_correction_package(
    repo_root: Path,
) -> FullABCLocalRuntimeCorrectionPackage:
    """Load the correction package and verify its cross-file binding."""

    correction = load_full_abc_local_runtime_direction_correction(repo_root / CORRECTION_PATH)
    supersession = load_full_abc_preflight_v2_supersession(repo_root / SUPERSESSION_PATH)
    try:
        return FullABCLocalRuntimeCorrectionPackage(
            correction=correction,
            supersession=supersession,
        )
    except ValueError as exc:
        raise FullABCLocalRuntimeLineageCorrectionError(
            "LOCAL_RUNTIME_CORRECTION_PACKAGE_MISMATCH",
            "The correction and supersession artifacts do not match.",
            details=(str(exc),),
        ) from exc


def assert_preflight_v2_not_execution_eligible(repo_root: Path) -> None:
    """Fail unless the supersession overlay blocks every v2 execution path."""

    package = load_full_abc_local_runtime_correction_package(repo_root)
    correction = package.correction
    supersession = package.supersession
    if any(
        (
            correction.preflight_v2_planning_authoritative,
            correction.preflight_v2_execution_eligible,
            correction.preflight_v2_comparison_eligible,
            correction.hosted_provider_probe_required,
            correction.cost_budget_required,
            supersession.provider_budget_review_permitted,
            supersession.provider_probe_permitted,
            supersession.preflight_v2_reuse_permitted,
            supersession.execution_authorized,
        )
    ):
        raise FullABCLocalRuntimeLineageCorrectionError(
            "PREFLIGHT_V2_SUPERSESSION_UNSAFE",
            "The superseded preflight-v2 lineage exposes an unsafe permission.",
        )


def build_default_correction() -> FullABCLocalRuntimeDirectionCorrection:
    """Build the immutable correction payload used by repository artifacts and tests."""

    return FullABCLocalRuntimeDirectionCorrection(
        correction_id="auragateway-full-abc-local-runtime-lineage-correction-v1",
        source_merge_commit=SOURCE_MERGE_COMMIT,
        superseded_source_merge_commit=SUPERSEDED_SOURCE_MERGE_COMMIT,
        superseded_manifest_path="data/evals/benchmark/preflight-v2/manifest.json",
        superseded_manifest_git_blob_sha=SUPERSEDED_MANIFEST_GIT_BLOB_SHA,
        superseded_artifact_hashes=_EXPECTED_SUPERSEDED_HASHES,
        invalidated_fields=_EXPECTED_INVALIDATED_FIELDS,
        failure_code="HOSTED_PROVIDER_LINEAGE_IMPORTED_INTO_LOCAL_BENCHMARK",
        disposition="PREFLIGHT_V2_INVALIDATED_NON_EXECUTABLE",
        local_runtime=FullABCLocalRuntimeIdentity(
            execution_backend="local_vllm",
            environment="kaggle_t4_x2",
            transport_endpoint="/v1/chat/completions",
            worker_client_contract=("auragateway.local_abc.worker_client.WorkerClient"),
            worker_registry_contract=("auragateway.local_abc.worker_registry.WorkerRegistry"),
            model=FullABCLocalModelIdentity(
                model_alias="local-qwen2.5-0.5b-instruct",
                repository="Qwen/Qwen2.5-0.5B-Instruct",
                revision="7ae557604adf67be50417f59c2c2f167def9a775",
                model_manifest_sha256=(
                    "b5c53c05aa258cf85b8ac7c1f41ec81aaa6d9d66a656d32f7271bf5d4c9b8daa"
                ),
                config_sha256=("18e18afcaccafade98daf13a54092927904649e1dd4eba8299ab717d5d94ff45"),
                generation_config_sha256=(
                    "e558847a8b4402616f1273797b015104dc266fe4b520056fca88823ba8f8ebe6"
                ),
                tokenizer_revision="7ae557604adf67be50417f59c2c2f167def9a775",
                tokenizer_json_sha256=(
                    "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
                ),
                tokenizer_config_sha256=(
                    "5b5d4f65d0acd3b2d56a35b56d374a36cbc1c8fa5cf3b3febbbfabf22f359583"
                ),
            ),
            workers=(
                FullABCWorkerBinding(worker_id="worker_1", gpu_index=0, port=8001),
                FullABCWorkerBinding(worker_id="worker_2", gpu_index=1, port=8002),
            ),
            vllm_wheel_sha256=("9e206f370c934a2d4b6b1f05d3d09708d344e05d80260189ef19f60755709431"),
        ),
        evidence_bindings=(
            FullABCEvidenceBinding(
                evidence_id="local-abc-measured-execution-authorization-v1",
                path="benchmarks/local_abc/measured_execution_authorization_v1.json",
                canonical_sha256=(
                    "64565dd6d34d7d9f9e55a4522b594ef95c458b0ff1af7994dfe81b39a8ba4e74"
                ),
                evidence_role="two_worker_environment",
            ),
            FullABCEvidenceBinding(
                evidence_id="reconcile-balance-requalification-authorization-v2",
                path=(
                    "benchmarks/local_abc/"
                    "reconcile_balance_extraction_requalification_authorization_v2.json"
                ),
                canonical_sha256=(
                    "a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899"
                ),
                evidence_role="model_runtime_authorization",
            ),
            FullABCEvidenceBinding(
                evidence_id="reconcile-balance-requalification-evidence-audit-v2",
                path=(
                    "benchmarks/local_abc/"
                    "reconcile_balance_extraction_requalification_evidence_audit_v2.json"
                ),
                canonical_sha256=(
                    "a6a1031d85997d8b13b521866d580ce468579cfbb8d731180820fdcc5dd0be79"
                ),
                evidence_role="successful_model_execution_audit",
            ),
            FullABCEvidenceBinding(
                evidence_id="reconcile-balance-requalification-consumption-v2",
                path=(
                    "benchmarks/local_abc/"
                    "reconcile_balance_extraction_requalification_authorization_consumption_v2.json"
                ),
                canonical_sha256=(
                    "51b36a3ac4e6122c2cf9fa9e5132d26e57af101a19714cb4cd60c4c71afdff4f"
                ),
                evidence_role="authorization_consumption",
            ),
        ),
        next_gate=NEXT_GATE,
    )


def build_default_supersession(
    correction: FullABCLocalRuntimeDirectionCorrection,
) -> FullABCPreflightV2SupersessionRecord:
    """Build the fail-closed overlay for the merged preflight-v2 lineage."""

    return FullABCPreflightV2SupersessionRecord(
        supersession_id="auragateway-full-abc-preflight-v2-supersession-v1",
        source_merge_commit=SOURCE_MERGE_COMMIT,
        correction_path=CORRECTION_PATH.as_posix(),
        correction_sha256=correction.fingerprint(),
        superseded_manifest_path="data/evals/benchmark/preflight-v2/manifest.json",
        superseded_manifest_git_blob_sha=SUPERSEDED_MANIFEST_GIT_BLOB_SHA,
        status="superseded_invalid_non_executable",
        reason_code="HOSTED_PROVIDER_LINEAGE_IMPORTED_INTO_LOCAL_BENCHMARK",
        next_gate=NEXT_GATE,
    )


def validate_repository_correction_package(repo_root: Path) -> dict[str, object]:
    """Return a compact, safe validation summary for release gates."""

    assert_preflight_v2_not_execution_eligible(repo_root)
    package = load_full_abc_local_runtime_correction_package(repo_root)
    return {
        "correction_sha256": package.correction.fingerprint(),
        "supersession_sha256": package.supersession.fingerprint(),
        "preflight_v2_execution_eligible": False,
        "execution_backend": package.correction.local_runtime.execution_backend,
        "model_alias": package.correction.local_runtime.model.model_alias,
        "hosted_provider_required": False,
        "pricing_in_scope": False,
        "external_spend": 0,
        "next_gate": package.correction.next_gate,
    }


__all__ = [
    "CORRECTION_PATH",
    "NEXT_GATE",
    "SOURCE_MERGE_COMMIT",
    "SUPERSESSION_PATH",
    "FullABCLocalRuntimeCorrectionPackage",
    "FullABCLocalRuntimeDirectionCorrection",
    "FullABCLocalRuntimeIdentity",
    "FullABCLocalRuntimeLineageCorrectionError",
    "FullABCLocalRuntimeLineageCorrectionErrorEnvelope",
    "FullABCPreflightV2SupersessionRecord",
    "assert_preflight_v2_not_execution_eligible",
    "build_default_correction",
    "build_default_supersession",
    "load_full_abc_local_runtime_correction_package",
    "load_full_abc_local_runtime_direction_correction",
    "load_full_abc_preflight_v2_supersession",
    "validate_repository_correction_package",
]

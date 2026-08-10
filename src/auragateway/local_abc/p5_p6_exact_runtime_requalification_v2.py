"""Generate and validate Exact-Runtime P5/P6 Requalification V2 assets."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import re
import subprocess
import sys
import types
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

SOURCE_MAIN_COMMIT: Final = "e7e9dea0ebfac320ea480e003e46fd0346c40a56"

DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_authorization_transport_"
    "remediation_design_v1.json"
)
DESIGN_RECORD_SHA256: Final = "679c11a020e7381417f9f2fe0087f72ee10e9a454703609a1ab48c70da57d3bb"
V5_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_evidence_acceptance_v1_record.json"
)
V5_ACCEPTANCE_SHA256: Final = "b86314bd8c9a71766884ac7143b7fff3198e986dd99c6065814b45c8d1095eb1"
RESOLUTION_LOCK_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v3_exact_runtime_resolution_lock_v1.json"
)
RESOLUTION_LOCK_SHA256: Final = "1294394ac476336b103b036d8654a49e4ae78c25c912ca5729cd94f982384f3c"
SEMANTIC_BOUNDARY_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_semantic_boundary_design_v1.json"
)
SEMANTIC_BOUNDARY_SHA256: Final = "1d248baa983edebeda4f0fa95aa5a70c870d18dcba374249c40125cc81e48c75"
HISTORICAL_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1.json"
)
HISTORICAL_ACCEPTANCE_SHA256: Final = (
    "d0268386d8d934257d035c2f720276d39e94a9eb0daa7da51175cc2cda3c1539"
)
HISTORICAL_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_successor_execution_acceptance_v1_review.json"
)
HISTORICAL_REVIEW_SHA256: Final = "8cbd4b94b47d7f167fee5523f660244acb54adfe6a2826da46fa85c38e8ba762"
HISTORICAL_HARNESS_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_successor_runtime_qualification_v1.py"
)
HISTORICAL_HARNESS_SHA256: Final = (
    "a8c5741b6385a5f9393679a77b2c55b9d8bfbfeb32351c3d3708b21d6f4ebd82"
)
HISTORICAL_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_successor_runtime_qualification_v1.py.tmpl"
)
HISTORICAL_TEMPLATE_SHA256: Final = (
    "fd67c6377835b097be3b9b68a6c8abe4685a391250dc532fcdfa393bcc04f672"
)

PREDECESSOR_BEHAVIORAL_DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_requalification_design_v1.json"
)
PREDECESSOR_BEHAVIORAL_DESIGN_SHA256: Final = (
    "4781d9d3dda0c69cdc629a78dbaa94c39e73374914e40d1b48486b7d0e0033a2"
)
PREDECESSOR_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v1.py"
)
PREDECESSOR_SOURCE_SHA256: Final = (
    "e41c0c327eab743c01dad961d07204a041e64e0579936145b79a1c23a675d126"
)
PREDECESSOR_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v1.py.tmpl"
)
PREDECESSOR_TEMPLATE_SHA256: Final = (
    "bc512e45e7ac646045dda3f598ca2aa961a0c69c86b73117d66bb457710d0dfa"
)
PREDECESSOR_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v1.py"
)
PREDECESSOR_TEST_SHA256: Final = "9d6151e387cd7b972696ffe982016831271288209a8a18cd6db1335343c137eb"
PREDECESSOR_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_exact_runtime_requalification_v1.ipynb"
)
PREDECESSOR_NOTEBOOK_SHA256: Final = (
    "cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"
)
PREDECESSOR_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_review.json"
)
PREDECESSOR_REVIEW_SHA256: Final = (
    "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
)
PREDECESSOR_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_record.json"
)
PREDECESSOR_RECORD_SHA256: Final = (
    "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
)

FAILURE_ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_authority_failure_acceptance_v1.json"
)
FAILURE_ACCEPTANCE_SHA256: Final = (
    "d919ef6e788ae9b5e311bae2166484c3d7d33093a88e355fb79851b9c2568226"
)
FAILURE_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_authority_failure_acceptance_v1_review.json"
)
FAILURE_REVIEW_SHA256: Final = "48f55790fb19b145fa24c69c9a2186513783704377a2cfd291a8f52255d2f4c5"
FAILURE_SFR_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_exact_runtime_authority_failure_sfr_v1.json"
)
FAILURE_SFR_SHA256: Final = "8f94af5e1ca8abe9d430e914b3b8ed2ce6a89eb03e770cf1109162452b7c8583"

HISTORICAL_CONTROL_DISCOVERY_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_full_abc_local_environment_qualification_"
    "control_output_discovery_remediation_v1.json"
)
HISTORICAL_CONTROL_DISCOVERY_RECORD_SHA256: Final = (
    "88a47cbcc8be001182be824d88d341e77e9089934cb547018d3adcfc9f7a53ea"
)
HISTORICAL_LAUNCHER_PATH: Final = Path(
    "src/auragateway/local_abc/full_abc_local_environment_qualification_kaggle_launcher.py"
)
HISTORICAL_LAUNCHER_SHA256: Final = (
    "cf5ec98d24fae4f926ad9ecf5c4764f17a4e6f994cbebf26f58f701e26df1f03"
)

TRANSPORT_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_authorization_transport_v1.py"
)
TRANSPORT_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_authorization_transport_v1.py"
)

SOURCE_PATH: Final = Path("src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v2.py")
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v2.py.tmpl"
)
TEST_PATH: Final = Path("tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v2.py")
ADR_PATH: Final = Path(
    "docs/adr/2026-08-10-local-abc-exact-runtime-p5-p6-authorization-transport-remediation-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Exact_Runtime_P5_P6_Authorization_Transport_Remediation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_exact_runtime_p5_p6_authorization_transport_remediation_v1.md"
)

REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_implementation_record.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_p5_p6_exact_runtime_requalification_v2.ipynb")

LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_execution_authorization.json"
)
LIVE_CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v2_authorization_consumption.json"
)

NOTEBOOK_NAME: Final = "ag-exact-runtime-p5-p6-requal-v2"
FAILED_NOTEBOOK_NAME: Final = "ag-exact-runtime-p5-p6-requal-failed-v2"
EVIDENCE_ZIP_NAME: Final = "ag-exact-runtime-p5-p6-requal-evidence-v2.zip"

NEXT_GATE: Final = (
    "DESIGN_AND_MERGE_EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_EXECUTION_AUTHORIZATION_ISSUER"
)

STATIC_PATHS: Final = (
    SOURCE_PATH,
    TEMPLATE_PATH,
    TEST_PATH,
    TRANSPORT_SOURCE_PATH,
    TRANSPORT_TEST_PATH,
    ADR_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
)
GENERATED_PATHS: Final = (
    REVIEW_PATH,
    RECORD_PATH,
    NOTEBOOK_PATH,
)
CANDIDATE_PATHS: Final = tuple(sorted((*STATIC_PATHS, DESIGN_RECORD_PATH, *GENERATED_PATHS)))

EXPECTED_AUTHORITIES: Final = (
    (
        "accepted_exact_runtime_capability",
        V5_ACCEPTANCE_PATH,
        V5_ACCEPTANCE_SHA256,
        "CURRENT",
    ),
    (
        "accepted_exact_runtime_resolution",
        RESOLUTION_LOCK_PATH,
        RESOLUTION_LOCK_SHA256,
        "CURRENT",
    ),
    (
        "accepted_semantic_boundary",
        SEMANTIC_BOUNDARY_PATH,
        SEMANTIC_BOUNDARY_SHA256,
        "CURRENT",
    ),
    (
        "historical_governed_p5_p6_acceptance",
        HISTORICAL_ACCEPTANCE_PATH,
        HISTORICAL_ACCEPTANCE_SHA256,
        "DESIGN_PRECEDENT_ONLY",
    ),
    (
        "historical_governed_p5_p6_review",
        HISTORICAL_REVIEW_PATH,
        HISTORICAL_REVIEW_SHA256,
        "DESIGN_PRECEDENT_ONLY",
    ),
    (
        "historical_p5_p6_harness",
        HISTORICAL_HARNESS_PATH,
        HISTORICAL_HARNESS_SHA256,
        "DESIGN_PRECEDENT_ONLY",
    ),
    (
        "historical_p5_p6_runtime_template",
        HISTORICAL_TEMPLATE_PATH,
        HISTORICAL_TEMPLATE_SHA256,
        "DESIGN_PRECEDENT_ONLY",
    ),
)

RUNTIME_OUTPUTS: Final = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "c1_model_construction_report_v1.json",
    "c2_worker_startup_report_v1.json",
    "c3_single_request_report_v1.json",
    "c4_output_contract_report_v1.json",
    "p5_cache_behavior_report_v1.json",
    "p5_post_restart_native_origin_report_v1.json",
    "p6_stage_checkpoint_report_v1.json",
    "p6_native_origin_report_v1.json",
    "p6_worker_state_isolation_report_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "p5_p6_exact_runtime_requalification_summary_v1.json",
    "failure_report_v1.json",
    "bundle_manifest_v1.json",
    "human_report_v1.md",
)


class ImplementationError(RuntimeError):
    """Fail-closed implementation-generation error."""

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
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_IMPLEMENTATION_ARGUMENT_ERROR",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_bytes(self) -> bytes:
        return _canonical_json_bytes(self.model_dump(mode="json"))


class ArtifactIdentity(_StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class AuthorityIdentity(ArtifactIdentity):
    role: str = Field(min_length=1)
    authority_scope: Literal["CURRENT", "DESIGN_PRECEDENT_ONLY"]


class RuntimeContract(_StrictModel):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    required_native_module: Literal["vllm._C_stable_libtorch"] = "vllm._C_stable_libtorch"
    gpu_topology: Literal["T4_x2"] = "T4_x2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    tokenizer_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_directory_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"


class ExecutionBudget(_StrictModel):
    maximum_model_requests: Literal[6] = 6
    maximum_worker_starts: Literal[3] = 3
    maximum_model_loads: Literal[3] = 3
    hidden_retries_permitted: Literal[0] = 0
    replacement_workers_permitted: Literal[0] = 0
    benchmark_trajectory_requests_permitted: Literal[0] = 0
    network_requests_permitted: Literal[0] = 0
    external_spend: Literal[0] = 0


class SemanticBoundary(_StrictModel):
    raw_observation_type: Literal["RawRuntimeObservation"] = "RawRuntimeObservation"
    typed_observation_type: Literal["TypedSemanticObservation"] = "TypedSemanticObservation"
    decision_type: Literal["BehaviorDecision"] = "BehaviorDecision"
    evidence_projection_type: Literal["EvidenceProjection"] = "EvidenceProjection"
    public_evidence_used_as_semantic_input: Literal[False] = False
    evidence_projection_terminal: Literal[True] = True
    lossy_transformations_before_semantic_decision: Literal[0] = 0
    truncation_before_semantic_decision: Literal[0] = 0
    evidence_format_metamorphic_invariance_required: Literal[True] = True
    excerpt_length_metamorphic_invariance_required: Literal[True] = True


class AuthorizationConsumerContract(_StrictModel):
    authorization_filename: Literal["execution_authorization_v1.json"] = (
        "execution_authorization_v1.json"
    )
    authorization_scope: Literal["EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"] = (
        "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
    )
    transport_contract: Literal["GOVERNED_ROOT_EXACT_FLAT_V1"] = "GOVERNED_ROOT_EXACT_FLAT_V1"
    producer_notebook_name: Literal["ag-p5-p6-auth-control-v1"] = "ag-p5-p6-auth-control-v1"
    producer_output_directory: Literal["ag_p5_p6_auth_control_v1"] = "ag_p5_p6_auth_control_v1"
    exact_flat_control_file_count: Literal[3] = 3
    governed_root_resolved_before_filename: Literal[True] = True
    global_filename_uniqueness_required: Literal[False] = False
    unscoped_recursive_authorization_search_permitted: Literal[False] = False
    decision_required: Literal["AUTHORIZED"] = "AUTHORIZED"
    lifecycle_required: Literal["ISSUED"] = "ISSUED"
    runtime_script_sha256_binding_required: Literal[True] = True
    implementation_review_sha256_binding_required: Literal[True] = True
    design_record_sha256_binding_required: Literal[True] = True
    v5_acceptance_sha256_binding_required: Literal[True] = True
    live_time_window_required: Literal[True] = True
    single_use_required: Literal[True] = True
    every_terminal_attempt_consumes_authorization: Literal[True] = True
    unchanged_replay_authorized: Literal[False] = False


class ImplementationSafety(_StrictModel):
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    runtime_execution_authorized: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    benchmark_trajectory_requests_performed: Literal[0] = 0
    network_requests_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_present: Literal[False] = False
    external_spend: Literal[0] = 0


class ImplementationReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-exact-runtime-p5-p6-requalification-v2-implementation-review"]
    status: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"]
    implementation_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    design_record: AuthorityIdentity
    accepted_authorities: tuple[AuthorityIdentity, ...] = Field(
        min_length=7,
        max_length=7,
    )
    runtime: RuntimeContract
    request_roles: tuple[
        Literal["BASE_COLD"],
        Literal["BASE_WARM"],
        Literal["NEGATIVE_PREFIX"],
        Literal["POST_RESET_COLD"],
        Literal["CROSS_WORKER_COLD"],
        Literal["WORKER1_RETENTION"],
    ]
    execution_budget: ExecutionBudget
    semantic_boundary: SemanticBoundary
    authorization_consumer: AuthorizationConsumerContract
    predecessor_lineage_validated: Literal[True] = True
    behavioral_core_preserved: Literal[True] = True
    authorization_transport_remediated: Literal[True] = True
    expected_runtime_outputs: tuple[str, ...] = Field(min_length=19, max_length=19)
    failure_taxonomy: tuple[str, ...] = Field(min_length=26)
    static_artifacts: tuple[ArtifactIdentity, ...] = Field(min_length=8, max_length=8)
    safety: ImplementationSafety
    next_gate: str = Field(min_length=20)
    non_claims: tuple[str, ...] = Field(min_length=8)

    @model_validator(mode="after")
    def validate_request_roles(self) -> Self:
        expected = (
            "BASE_COLD",
            "BASE_WARM",
            "NEGATIVE_PREFIX",
            "POST_RESET_COLD",
            "CROSS_WORKER_COLD",
            "WORKER1_RETENTION",
        )
        if self.request_roles != expected:
            raise ValueError("exact-runtime P5/P6 request order drifted")
        return self


class NotebookIdentity(ArtifactIdentity):
    notebook_name: Literal["ag-exact-runtime-p5-p6-requal-v2"]
    failed_notebook_name: Literal["ag-exact-runtime-p5-p6-requal-failed-v2"]
    code_cell_count: Literal[1]
    execution_count_present: Literal[False] = False
    output_present: Literal[False] = False
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ImplementationRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-exact-runtime-p5-p6-requalification-v2-implementation"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    implementation_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    review: ArtifactIdentity
    notebook: NotebookIdentity
    static_artifacts: tuple[ArtifactIdentity, ...] = Field(min_length=8, max_length=8)
    runtime: RuntimeContract
    execution_budget: ExecutionBudget
    semantic_boundary: SemanticBoundary
    authorization_consumer: AuthorizationConsumerContract
    predecessor_lineage_validated: Literal[True] = True
    behavioral_core_preserved: Literal[True] = True
    authorization_transport_remediated: Literal[True] = True
    expected_runtime_outputs: tuple[str, ...] = Field(min_length=19, max_length=19)
    safety: ImplementationSafety
    next_gate: str = Field(min_length=20)


def _canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_file(repo_root: Path, relative_path: Path) -> bytes:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_ARTIFACT_MISSING_OR_UNSAFE",
            "required implementation artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    return path.read_bytes()


def _identity(repo_root: Path, relative_path: Path) -> ArtifactIdentity:
    payload = _read_file(repo_root, relative_path)
    return ArtifactIdentity(
        path=relative_path.as_posix(),
        sha256=_sha256_bytes(payload),
        size_bytes=len(payload),
    )


def _authority(
    repo_root: Path,
    role: str,
    path: Path,
    expected_sha256: str,
    authority_scope: Literal["CURRENT", "DESIGN_PRECEDENT_ONLY"],
) -> AuthorityIdentity:
    payload = _read_file(repo_root, path)
    observed_sha = _sha256_bytes(payload)
    if observed_sha != expected_sha256:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_AUTHORITY_IDENTITY_DRIFT",
            "required authority identity drifted",
            path.as_posix(),
        )
    return AuthorityIdentity(
        role=role,
        path=path.as_posix(),
        sha256=observed_sha,
        size_bytes=len(payload),
        authority_scope=authority_scope,
    )


def _accepted_authorities(repo_root: Path) -> tuple[AuthorityIdentity, ...]:
    predecessor_review = _read_json_object(repo_root, PREDECESSOR_REVIEW_PATH)
    raw = predecessor_review.get("accepted_authorities")
    if not isinstance(raw, list) or len(raw) != len(EXPECTED_AUTHORITIES):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_AUTHORITY_INVENTORY_DRIFT",
            "predecessor accepted-authority inventory drifted",
            PREDECESSOR_REVIEW_PATH.as_posix(),
        )

    observed: list[AuthorityIdentity] = []
    for expected, item in zip(EXPECTED_AUTHORITIES, raw, strict=True):
        if not isinstance(item, dict):
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_AUTHORITY_INVENTORY_DRIFT",
                "predecessor authority entry is invalid",
                PREDECESSOR_REVIEW_PATH.as_posix(),
            )
        role, path, sha256, scope = expected
        expected_fields = {
            "role": role,
            "path": path.as_posix(),
            "sha256": sha256,
            "authority_scope": scope,
        }
        for key, value in expected_fields.items():
            if item.get(key) != value:
                raise ImplementationError(
                    "P5_P6_EXACT_RUNTIME_V2_AUTHORITY_INVENTORY_DRIFT",
                    f"predecessor authority field drifted: {role}.{key}",
                    PREDECESSOR_REVIEW_PATH.as_posix(),
                )
        size_bytes = item.get("size_bytes")
        if not isinstance(size_bytes, int) or size_bytes <= 0:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_AUTHORITY_INVENTORY_DRIFT",
                f"predecessor authority size is invalid: {role}",
                PREDECESSOR_REVIEW_PATH.as_posix(),
            )
        observed.append(
            AuthorityIdentity(
                role=role,
                path=path.as_posix(),
                sha256=sha256,
                size_bytes=size_bytes,
                authority_scope=cast(
                    Literal["CURRENT", "DESIGN_PRECEDENT_ONLY"],
                    scope,
                ),
            )
        )
    return tuple(observed)


def _read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    payload = _read_file(repo_root, relative_path)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_JSON_INVALID",
            "required implementation authority is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(parsed, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_JSON_INVALID",
            "required implementation authority is not a JSON object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], parsed)


def validate_design_authority(repo_root: Path) -> dict[str, object]:
    design_bytes = _read_file(repo_root, DESIGN_RECORD_PATH)
    if _sha256_bytes(design_bytes) != DESIGN_RECORD_SHA256:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_DESIGN_IDENTITY_DRIFT",
            "authorization transport remediation design identity drifted",
            DESIGN_RECORD_PATH.as_posix(),
        )
    design = _read_json_object(repo_root, DESIGN_RECORD_PATH)
    expected = {
        "design_status": "DESIGN_FROZEN_FOR_SUCCESSOR_IMPLEMENTATION",
        "implementation_base_main_commit": SOURCE_MAIN_COMMIT,
        "next_gate": NEXT_GATE,
    }
    for key, value in expected.items():
        if design.get(key) != value:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_DESIGN_SEMANTIC_DRIFT",
                f"authorization transport remediation design drifted: {key}",
                DESIGN_RECORD_PATH.as_posix(),
            )

    predecessor = design.get("predecessor")
    if not isinstance(predecessor, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_DESIGN_SEMANTIC_DRIFT",
            "authorization transport predecessor record is missing",
            DESIGN_RECORD_PATH.as_posix(),
        )
    predecessor_expected = {
        "failed_saved_version_id": 341454766,
        "inspection_saved_version_id": 341466979,
        "failure_class": "AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE",
        "failure_depth": "EARLY_CONTROL_PLANE",
        "current_consumer_candidate_count": 0,
        "recursive_diagnostic_candidate_count": 1,
    }
    for predecessor_key, predecessor_value in predecessor_expected.items():
        if predecessor.get(predecessor_key) != predecessor_value:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_DESIGN_PREDECESSOR_DRIFT",
                (f"authorization transport predecessor field drifted: {predecessor_key}"),
                DESIGN_RECORD_PATH.as_posix(),
            )

    transport = design.get("transport_contract")
    if not isinstance(transport, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_TRANSPORT_CONTRACT_MISSING",
            "authorization transport contract is missing",
            DESIGN_RECORD_PATH.as_posix(),
        )
    transport_expected = {
        "producer_notebook_name": "ag-p5-p6-auth-control-v1",
        "producer_output_directory": "ag_p5_p6_auth_control_v1",
        "authorization_filename": "execution_authorization_v1.json",
        "discovery_scope": "GOVERNED_PRODUCER_ROOT",
        "root_name_and_producer_token_required": True,
        "global_authorization_filename_uniqueness_required": False,
        "unscoped_recursive_authorization_search_permitted": False,
        "unrelated_authorization_filename_collisions_ignored": True,
        "multiple_governed_roots_rejected": True,
        "extra_members_rejected": True,
        "missing_members_rejected": True,
        "canonical_json_required": True,
        "authorization_hash_and_size_bound": True,
        "manifest_receipt_cross_binding_required": True,
    }
    for transport_key, transport_value in transport_expected.items():
        if transport.get(transport_key) != transport_value:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_TRANSPORT_CONTRACT_DRIFT",
                (f"authorization transport field drifted: {transport_key}"),
                DESIGN_RECORD_PATH.as_posix(),
            )

    safety = design.get("safety")
    if not isinstance(safety, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_DESIGN_SAFETY_MISSING",
            "authorization transport safety record is missing",
            DESIGN_RECORD_PATH.as_posix(),
        )
    if any(
        safety.get(key) is not False
        for key in (
            "v1_executed_artifacts_mutated",
            "live_authorization_issued",
            "runtime_execution_authorized",
            "p5_p6_exact_runtime_requalified",
            "pilot_execution_authorized",
            "final_measured_abc_execution_authorized",
            "kaggle_execution_performed",
        )
    ):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_DESIGN_SAFETY_DRIFT",
            "authorization transport design promoted execution authority",
            DESIGN_RECORD_PATH.as_posix(),
        )
    return {
        "status": "EXACT_RUNTIME_P5_P6_TRANSPORT_REMEDIATION_DESIGN_VALID",
        "design_record_sha256": DESIGN_RECORD_SHA256,
        "predecessor_saved_version_id": 341454766,
        "inspection_saved_version_id": 341466979,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _require_base_main_ancestor(repo_root: Path) -> None:
    process = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            SOURCE_MAIN_COMMIT,
            "HEAD",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_BASE_MAIN_NOT_ANCESTOR",
            "implementation base main is not an ancestor of HEAD",
        )


def _failure_taxonomy(repo_root: Path) -> tuple[str, ...]:
    _ = repo_root
    return (
        "INPUT_IDENTITY_FAILURE",
        "MODEL_ARTIFACT_FAILURE",
        "TOKENIZER_ARTIFACT_FAILURE",
        "MODEL_CONSTRUCTION_FAILURE",
        "WORKER_STARTUP_FAILURE",
        "WORKER_IDENTITY_FAILURE",
        "DEVICE_REALIZATION_FAILURE",
        "REQUEST_EXECUTION_FAILURE",
        "OUTPUT_CONTRACT_FAILURE",
        "P5_CACHE_ENABLEMENT_FAILURE",
        "P5_STARTING_STATE_FAILURE",
        "P5_CACHE_OBSERVATION_FAILURE",
        "P5_BEHAVIOR_FAILURE",
        "P6_ROUTE_REALIZATION_FAILURE",
        "P6_WORKER_GENERATION_FAILURE",
        "P6_STATE_ISOLATION_FAILURE",
        "P6_BEHAVIOR_FAILURE",
        "METRIC_SEMANTIC_FAILURE",
        "METRIC_ATTRIBUTION_AMBIGUOUS",
        "REQUEST_RECONCILIATION_FAILURE",
        "TEARDOWN_FAILURE",
        "HARNESS_SEMANTIC_FAILURE",
        "EVIDENCE_PROJECTION_FAILURE",
        "AUTHORITY_FAILURE",
        "NON_DETERMINISTIC_FAILURE",
        "DIAGNOSTIC_INVALID",
    )


def _runtime_contract() -> RuntimeContract:
    return RuntimeContract()


def _budget() -> ExecutionBudget:
    return ExecutionBudget()


def _boundary() -> SemanticBoundary:
    return SemanticBoundary()


def _authorization_consumer() -> AuthorizationConsumerContract:
    return AuthorizationConsumerContract()


def _safety() -> ImplementationSafety:
    return ImplementationSafety(
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
    )


def _non_claims() -> tuple[str, ...]:
    return (
        "successor_v2_has_not_been_executed",
        "current_exact_runtime_model_construction_not_reobserved",
        "current_exact_runtime_worker_startup_not_reobserved",
        "current_exact_runtime_single_request_not_reobserved",
        "current_exact_runtime_output_contract_not_reobserved",
        "current_exact_runtime_p5_not_requalified",
        "current_exact_runtime_p6_not_requalified",
        "fresh_execution_authorization_issuer_not_implemented",
        "fresh_execution_authorization_not_issued",
        "runtime_execution_not_authorized",
        "pilot_execution_not_authorized",
        "final_measured_abc_execution_not_authorized",
        "production_readiness_not_claimed",
    )


def _static_artifacts(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    return tuple(_identity(repo_root, path) for path in STATIC_PATHS)


def validate_predecessor_lineage(repo_root: Path) -> dict[str, object]:
    expected = (
        (PREDECESSOR_SOURCE_PATH, PREDECESSOR_SOURCE_SHA256),
        (PREDECESSOR_TEMPLATE_PATH, PREDECESSOR_TEMPLATE_SHA256),
        (PREDECESSOR_TEST_PATH, PREDECESSOR_TEST_SHA256),
        (PREDECESSOR_NOTEBOOK_PATH, PREDECESSOR_NOTEBOOK_SHA256),
        (PREDECESSOR_REVIEW_PATH, PREDECESSOR_REVIEW_SHA256),
        (PREDECESSOR_RECORD_PATH, PREDECESSOR_RECORD_SHA256),
        (FAILURE_ACCEPTANCE_PATH, FAILURE_ACCEPTANCE_SHA256),
        (FAILURE_REVIEW_PATH, FAILURE_REVIEW_SHA256),
        (FAILURE_SFR_PATH, FAILURE_SFR_SHA256),
        (
            HISTORICAL_CONTROL_DISCOVERY_RECORD_PATH,
            HISTORICAL_CONTROL_DISCOVERY_RECORD_SHA256,
        ),
        (HISTORICAL_LAUNCHER_PATH, HISTORICAL_LAUNCHER_SHA256),
    )
    for path, expected_sha in expected:
        observed = _sha256_bytes(_read_file(repo_root, path))
        if observed != expected_sha:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_PREDECESSOR_IDENTITY_DRIFT",
                "required predecessor or historical precedent identity drifted",
                path.as_posix(),
            )

    acceptance = _read_json_object(repo_root, FAILURE_ACCEPTANCE_PATH)
    required_acceptance = {
        "status": "ACCEPTED_DIAGNOSTIC_FAILURE",
        "failure_class": "AUTHORIZATION_DISCOVERY_CONTRACT_FALSE_NEGATIVE",
        "failure_depth": "EARLY_CONTROL_PLANE",
        "saved_version_id": 341454766,
        "inspection_saved_version_id": 341466979,
        "current_consumer_candidate_count": 0,
        "recursive_diagnostic_candidate_count": 1,
        "authorization_transport_discovery_contract_invalidated": True,
        "runtime_incompatibility_established": False,
        "authorization_reusable": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
    }
    for key, value in required_acceptance.items():
        if acceptance.get(key) != value:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_FAILURE_GOVERNANCE_DRIFT",
                f"failure governance field drifted: {key}",
                FAILURE_ACCEPTANCE_PATH.as_posix(),
            )

    historical = _read_json_object(
        repo_root,
        HISTORICAL_CONTROL_DISCOVERY_RECORD_PATH,
    )
    remediation = historical.get("remediation")
    if not isinstance(remediation, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_HISTORICAL_PRECEDENT_DRIFT",
            "historical root-scoped discovery remediation is missing",
            HISTORICAL_CONTROL_DISCOVERY_RECORD_PATH.as_posix(),
        )
    required_historical = {
        "discovery_scope": "governed_control_output_root",
        "global_filename_uniqueness_required": False,
        "multiple_governed_roots_rejected": True,
        "unrelated_input_filename_collisions_ignored": True,
        "symbolic_links_accepted": False,
    }
    for key, value in required_historical.items():
        if remediation.get(key) != value:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_HISTORICAL_PRECEDENT_DRIFT",
                f"historical root-scoped discovery field drifted: {key}",
                HISTORICAL_CONTROL_DISCOVERY_RECORD_PATH.as_posix(),
            )

    return {
        "status": "EXACT_RUNTIME_P5_P6_V1_AND_FAILURE_LINEAGE_VALID",
        "predecessor_source_sha256": PREDECESSOR_SOURCE_SHA256,
        "predecessor_template_sha256": PREDECESSOR_TEMPLATE_SHA256,
        "predecessor_notebook_sha256": PREDECESSOR_NOTEBOOK_SHA256,
        "failed_saved_version_id": 341454766,
        "inspection_saved_version_id": 341466979,
        "historical_root_scoped_discovery_bound": True,
        "runtime_execution_authorized": False,
    }


def _parse_template_for_behavior(source: str) -> ast.Module:
    replacements = {
        "__NOTEBOOK_NAME__": "ag-static",
        "__SOURCE_MAIN_COMMIT__": "0" * 40,
        "__IMPLEMENTATION_REVIEW_SHA256__": "1" * 64,
        "__DESIGN_RECORD_SHA256__": "2" * 64,
        "__V5_ACCEPTANCE_SHA256__": "3" * 64,
        "__MODEL_SNAPSHOT_SHA256__": "4" * 64,
        "__EVIDENCE_ZIP_NAME__": "static.zip",
    }
    for marker, value in replacements.items():
        source = source.replace(marker, value)
    return ast.parse(source)


def audit_behavioral_core_preservation(repo_root: Path) -> dict[str, object]:
    predecessor = _read_file(
        repo_root,
        PREDECESSOR_TEMPLATE_PATH,
    ).decode("utf-8")
    successor = _read_file(
        repo_root,
        TEMPLATE_PATH,
    ).decode("utf-8")
    predecessor_tree = _parse_template_for_behavior(predecessor)
    successor_tree = _parse_template_for_behavior(successor)

    predecessor_functions = {
        node.name: node for node in predecessor_tree.body if isinstance(node, ast.FunctionDef)
    }
    successor_functions = {
        node.name: node for node in successor_tree.body if isinstance(node, ast.FunctionDef)
    }
    allowed_changed = {
        "_load_canonical_control_json",
        "resolve_authorization_control_output",
        "require_execution_authorization",
        "runtime_source_identity",
        "main",
    }
    predecessor_names = set(predecessor_functions)
    successor_names = set(successor_functions)
    unexpected_removed = predecessor_names - successor_names
    unexpected_added = successor_names - predecessor_names - allowed_changed
    if unexpected_removed or unexpected_added:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_BEHAVIORAL_FUNCTION_SET_DRIFT",
            "successor runtime behavioral function inventory drifted",
            TEMPLATE_PATH.as_posix(),
        )

    compared = 0
    for name in sorted(predecessor_names - allowed_changed):
        before = ast.dump(
            predecessor_functions[name],
            annotate_fields=True,
            include_attributes=False,
        )
        after = ast.dump(
            successor_functions[name],
            annotate_fields=True,
            include_attributes=False,
        )
        if before != after:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_BEHAVIORAL_CORE_DRIFT",
                f"successor changed an unapproved behavioral function: {name}",
                TEMPLATE_PATH.as_posix(),
            )
        compared += 1

    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_BEHAVIORAL_CORE_PRESERVED",
        "unchanged_top_level_function_count": compared,
        "approved_changed_functions": tuple(sorted(allowed_changed)),
        "behavioral_semantics_changed": False,
    }


def audit_authorization_transport_runtime(
    runtime_source: bytes,
) -> dict[str, object]:
    source = runtime_source.decode("utf-8")
    if 'INPUT_ROOT.glob(f"*/{AUTHORIZATION_FILENAME}")' in source:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_SHALLOW_DISCOVERY_RETAINED",
            "successor retained the disproved shallow authorization discovery",
            TEMPLATE_PATH.as_posix(),
        )
    if "INPUT_ROOT.rglob(AUTHORIZATION_FILENAME)" in source:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_UNSCOPED_RGLOBAL_DISCOVERY",
            "successor introduced unscoped recursive authorization discovery",
            TEMPLATE_PATH.as_posix(),
        )

    tree = ast.parse(source)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    required = {
        "resolve_authorization_control_output",
        "require_execution_authorization",
        "main",
    }
    if not required.issubset(functions):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_TRANSPORT_FUNCTION_MISSING",
            "successor authorization transport function set is incomplete",
            TEMPLATE_PATH.as_posix(),
        )

    resolver_dump = ast.dump(
        functions["resolve_authorization_control_output"],
        annotate_fields=True,
        include_attributes=False,
    )
    required_resolver_tokens = (
        "AUTHORIZATION_CONTROL_OUTPUT_DIRECTORY",
        "AUTHORIZATION_CONTROL_NOTEBOOK_NAME",
        "AUTHORIZATION_CONTROL_MANIFEST_FILENAME",
        "AUTHORIZATION_CONTROL_RECEIPT_FILENAME",
    )
    for token in required_resolver_tokens:
        if token not in resolver_dump:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_TRANSPORT_RESOLVER_DRIFT",
                f"successor transport resolver lost binding: {token}",
                TEMPLATE_PATH.as_posix(),
            )

    main = functions["main"]
    calls = [
        node.func.id
        for node in ast.walk(main)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    required_order = (
        "write_runtime_source_identity_report",
        "require_private_environment",
        "require_execution_authorization",
        "discover_one_directory",
        "discover_model_snapshot",
        "install_runtime",
    )
    positions: list[int] = []
    for name in required_order:
        if name not in calls:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_V2_EXECUTION_ORDER_DRIFT",
                f"successor runtime call is missing: {name}",
                TEMPLATE_PATH.as_posix(),
            )
        positions.append(calls.index(name))
    if positions != sorted(positions):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_EXECUTION_ORDER_DRIFT",
            "authorization transport no longer precedes runtime installation",
            TEMPLATE_PATH.as_posix(),
        )

    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_AUTHORIZATION_TRANSPORT_VALID",
        "governed_root_resolved_before_filename": True,
        "global_filename_uniqueness_required": False,
        "unscoped_recursive_authorization_search_permitted": False,
        "authorization_before_runtime_installation": True,
        "runtime_execution_authorized": False,
    }


def _review(repo_root: Path) -> ImplementationReview:
    validate_design_authority(repo_root)
    validate_predecessor_lineage(repo_root)
    audit_behavioral_core_preservation(repo_root)
    authorities = _accepted_authorities(repo_root)
    design_authority = _authority(
        repo_root,
        "frozen_exact_runtime_p5_p6_transport_remediation_design",
        DESIGN_RECORD_PATH,
        DESIGN_RECORD_SHA256,
        "CURRENT",
    )
    return ImplementationReview(
        review_id=("auragateway-exact-runtime-p5-p6-requalification-v2-implementation-review"),
        status="APPROVED_FOR_REPOSITORY_IMPLEMENTATION",
        implementation_base_main_commit=SOURCE_MAIN_COMMIT,
        design_record=design_authority,
        accepted_authorities=authorities,
        runtime=_runtime_contract(),
        request_roles=(
            "BASE_COLD",
            "BASE_WARM",
            "NEGATIVE_PREFIX",
            "POST_RESET_COLD",
            "CROSS_WORKER_COLD",
            "WORKER1_RETENTION",
        ),
        execution_budget=_budget(),
        semantic_boundary=_boundary(),
        authorization_consumer=_authorization_consumer(),
        predecessor_lineage_validated=True,
        behavioral_core_preserved=True,
        authorization_transport_remediated=True,
        expected_runtime_outputs=RUNTIME_OUTPUTS,
        failure_taxonomy=_failure_taxonomy(repo_root),
        static_artifacts=_static_artifacts(repo_root),
        safety=_safety(),
        next_gate=NEXT_GATE,
        non_claims=_non_claims(),
    )


def _render_runtime_template(
    repo_root: Path,
    implementation_review_sha256: str,
) -> bytes:
    template = _read_file(repo_root, TEMPLATE_PATH).decode("utf-8")
    replacements = {
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__SOURCE_MAIN_COMMIT__": SOURCE_MAIN_COMMIT,
        "__IMPLEMENTATION_REVIEW_SHA256__": implementation_review_sha256,
        "__DESIGN_RECORD_SHA256__": DESIGN_RECORD_SHA256,
        "__V5_ACCEPTANCE_SHA256__": V5_ACCEPTANCE_SHA256,
        "__MODEL_SNAPSHOT_SHA256__": (
            "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
        ),
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
    }
    for token, value in replacements.items():
        if template.count(token) != 1:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_TEMPLATE_PLACEHOLDER_DRIFT",
                f"runtime template placeholder count drifted: {token}",
                TEMPLATE_PATH.as_posix(),
            )
        template = template.replace(token, value)
    if re.search(r"__[A-Z0-9_]+__", template) is not None:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_TEMPLATE_PLACEHOLDER_DRIFT",
            "unresolved runtime-template placeholder remains",
            TEMPLATE_PATH.as_posix(),
        )
    compile(template, TEMPLATE_PATH.as_posix(), "exec")
    return template.encode("utf-8")


def _function_node(module: ast.Module, function_name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            return node
    raise ImplementationError(
        "P5_P6_EXACT_RUNTIME_SEMANTIC_FUNCTION_MISSING",
        f"required runtime semantic function is missing: {function_name}",
        TEMPLATE_PATH.as_posix(),
    )


def audit_runtime_semantic_boundary(runtime_source: bytes) -> dict[str, object]:
    source = runtime_source.decode("utf-8")
    module = ast.parse(source)
    semantic_functions = (
        "metric_snapshot",
        "metric_delta",
        "decide_p5",
        "decide_p6",
    )
    prohibited_names = {
        "sanitize_excerpt",
        "evidence_projection",
        "EvidenceProjection",
    }
    prohibited_attributes = {
        "stdout",
        "stderr",
        "stdout_tail",
        "stderr_tail",
        "public_summary",
    }
    violations: list[str] = []
    for function_name in semantic_functions:
        function = _function_node(module, function_name)
        for node in ast.walk(function):
            if isinstance(node, ast.Name) and node.id in prohibited_names:
                violations.append(f"{function_name}:name:{node.id}")
            if isinstance(node, ast.Attribute) and node.attr in prohibited_attributes:
                violations.append(f"{function_name}:attribute:{node.attr}")
    if violations:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_SEMANTIC_CHANNEL_VIOLATION",
            "public evidence flows into a semantic decision function",
            TEMPLATE_PATH.as_posix(),
        )

    required_order = (
        "metric_snapshot",
        "metric_delta",
        "decide_p5",
        "decide_p6",
        "evidence_projection",
    )
    offsets = tuple(source.find(f"def {name}(") for name in required_order)
    if any(offset < 0 for offset in offsets) or offsets != tuple(sorted(offsets)):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_SEMANTIC_DATAFLOW_ORDER_DRIFT",
            "runtime semantic/evidence function order drifted",
            TEMPLATE_PATH.as_posix(),
        )

    main_node = _function_node(module, "main")
    calls = [
        node.func.id
        for node in ast.walk(main_node)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    if "require_execution_authorization" not in calls:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_AUTHORIZATION_CONSUMER_MISSING",
            "runtime main does not require a live authorization",
            TEMPLATE_PATH.as_posix(),
        )
    if "install_runtime" not in calls:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_INSTALL_BOUNDARY_MISSING",
            "runtime main does not contain the governed install boundary",
            TEMPLATE_PATH.as_posix(),
        )
    auth_offset = source.find("authorization = require_execution_authorization()")
    install_offset = source.find("install_runtime(wheelhouse, counters)")
    if auth_offset < 0 or install_offset < 0 or auth_offset >= install_offset:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_AUTHORIZATION_ORDER_DRIFT",
            "authorization is not validated before runtime installation",
            TEMPLATE_PATH.as_posix(),
        )

    return {
        "semantic_function_count": len(semantic_functions),
        "semantic_channel_violation_count": 0,
        "public_evidence_used_as_semantic_input": False,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "authorization_precedes_runtime_installation": True,
    }


def _wrapper_code(runtime_source: bytes) -> tuple[bytes, str, str]:
    runtime_sha256 = _sha256_bytes(runtime_source)
    encoded = base64.b64encode(runtime_source).decode("ascii")
    chunks = tuple(encoded[index : index + 76] for index in range(0, len(encoded), 76))
    lines = [
        "import base64 as _ag_base64",
        "import hashlib as _ag_hashlib",
        "",
        "_AG_RUNTIME_B64 = (",
        *[f'    "{chunk}"' for chunk in chunks],
        ")",
        ('_AG_RUNTIME_SOURCE = _ag_base64.b64decode("".join(_AG_RUNTIME_B64)).decode("utf-8")'),
        f'_AG_EXPECTED_RUNTIME_SHA256 = "{runtime_sha256}"',
        (
            "_AG_OBSERVED_RUNTIME_SHA256 = "
            '_ag_hashlib.sha256(_AG_RUNTIME_SOURCE.encode("utf-8")).hexdigest()'
        ),
        "if _AG_OBSERVED_RUNTIME_SHA256 != _AG_EXPECTED_RUNTIME_SHA256:",
        '    raise RuntimeError("runtime script identity mismatch")',
        "EXECUTED_RUNTIME_SCRIPT_SHA256 = _AG_OBSERVED_RUNTIME_SHA256",
        "exec(",
        ('    compile(_AG_RUNTIME_SOURCE, "<auragateway-exact-runtime-p5-p6-v2>", "exec"),'),
        "    globals(),",
        "    globals(),",
        ")",
    ]
    wrapper = ("\n".join(lines) + "\n").encode("utf-8")
    if max(len(line) for line in wrapper.decode("utf-8").splitlines()) > 100:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_NOTEBOOK_LINE_LENGTH_DRIFT",
            "generated notebook wrapper exceeds 100 characters",
            NOTEBOOK_PATH.as_posix(),
        )
    compile(wrapper.decode("utf-8"), NOTEBOOK_PATH.as_posix(), "exec")
    return wrapper, runtime_sha256, _sha256_bytes(wrapper)


def _notebook_bytes(runtime_source: bytes) -> tuple[bytes, str, str]:
    wrapper, runtime_sha256, wrapper_sha256 = _wrapper_code(runtime_source)
    lines = wrapper.decode("utf-8").splitlines()
    code_source = [
        line + "\n" if index < len(lines) - 1 else line for index, line in enumerate(lines)
    ]
    payload = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "e26ad337eec342d5a1599a12f6dbcf1a",
                "metadata": {},
                "outputs": [],
                "source": code_source,
            }
        ],
        "metadata": {
            "accelerator": "GPU",
            "internet": False,
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
                "dockerImageVersionId": None,
                "isGpuEnabled": True,
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
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
    notebook = (json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    return notebook, runtime_sha256, wrapper_sha256


def _notebook_identity(
    notebook_bytes: bytes,
    runtime_script_sha256: str,
    wrapper_code_sha256: str,
) -> NotebookIdentity:
    return NotebookIdentity(
        path=NOTEBOOK_PATH.as_posix(),
        sha256=_sha256_bytes(notebook_bytes),
        size_bytes=len(notebook_bytes),
        notebook_name=NOTEBOOK_NAME,
        failed_notebook_name=FAILED_NOTEBOOK_NAME,
        code_cell_count=1,
        runtime_script_sha256=runtime_script_sha256,
        wrapper_code_sha256=wrapper_code_sha256,
    )


def build_generated(
    repo_root: Path,
) -> tuple[ImplementationReview, ImplementationRecord, bytes]:
    if (repo_root / LIVE_AUTHORIZATION_PATH).exists():
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_LIVE_AUTHORIZATION_PRESENT",
            "live V2 runtime authorization must be absent during implementation",
            LIVE_AUTHORIZATION_PATH.as_posix(),
        )
    if (repo_root / LIVE_CONSUMPTION_PATH).exists():
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_CONSUMPTION_PRESENT",
            "V2 authorization consumption must be absent during implementation",
            LIVE_CONSUMPTION_PATH.as_posix(),
        )

    review = _review(repo_root)
    review_bytes = review.canonical_bytes()
    review_sha = _sha256_bytes(review_bytes)
    runtime_source = _render_runtime_template(repo_root, review_sha)
    audit_runtime_semantic_boundary(runtime_source)
    audit_authorization_transport_runtime(runtime_source)
    notebook_bytes, runtime_sha, wrapper_sha = _notebook_bytes(runtime_source)

    record = ImplementationRecord(
        record_id=("auragateway-exact-runtime-p5-p6-requalification-v2-implementation"),
        status="IMPLEMENTED_NOT_EXECUTED",
        implementation_base_main_commit=SOURCE_MAIN_COMMIT,
        review=ArtifactIdentity(
            path=REVIEW_PATH.as_posix(),
            sha256=review_sha,
            size_bytes=len(review_bytes),
        ),
        notebook=_notebook_identity(
            notebook_bytes,
            runtime_sha,
            wrapper_sha,
        ),
        static_artifacts=_static_artifacts(repo_root),
        runtime=_runtime_contract(),
        execution_budget=_budget(),
        semantic_boundary=_boundary(),
        authorization_consumer=_authorization_consumer(),
        predecessor_lineage_validated=True,
        behavioral_core_preserved=True,
        authorization_transport_remediated=True,
        expected_runtime_outputs=RUNTIME_OUTPUTS,
        safety=_safety(),
        next_gate=NEXT_GATE,
    )
    return review, record, notebook_bytes


def _write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(payload)
    temporary.replace(path)


def generate(repo_root: Path) -> dict[str, object]:
    review, record, notebook = build_generated(repo_root)
    outputs = {
        REVIEW_PATH: review.canonical_bytes(),
        RECORD_PATH: record.canonical_bytes(),
        NOTEBOOK_PATH: notebook,
    }
    for relative_path, payload in outputs.items():
        _write_atomic(repo_root / relative_path, payload)
    return {
        "status": "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_GENERATED",
        "review_sha256": _sha256_bytes(outputs[REVIEW_PATH]),
        "record_sha256": _sha256_bytes(outputs[RECORD_PATH]),
        "notebook_sha256": _sha256_bytes(outputs[NOTEBOOK_PATH]),
        "runtime_script_sha256": record.notebook.runtime_script_sha256,
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> dict[str, object]:
    review, record, notebook = build_generated(repo_root)
    expected = {
        REVIEW_PATH: review.canonical_bytes(),
        RECORD_PATH: record.canonical_bytes(),
        NOTEBOOK_PATH: notebook,
    }
    identities: dict[str, str] = {}
    for relative_path, expected_bytes in expected.items():
        observed = _read_file(repo_root, relative_path)
        if observed != expected_bytes:
            raise ImplementationError(
                "P5_P6_EXACT_RUNTIME_GENERATED_ARTIFACT_DRIFT",
                "generated implementation artifact is non-canonical",
                relative_path.as_posix(),
            )
        identities[relative_path.as_posix()] = _sha256_bytes(observed)
    return {
        "status": "EXACT_RUNTIME_P5_P6_GENERATED_ARTIFACTS_VALID",
        "identities": identities,
        "runtime_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_notebook(repo_root: Path) -> dict[str, object]:
    review = _review(repo_root)
    runtime_source = _render_runtime_template(
        repo_root,
        _sha256_bytes(review.canonical_bytes()),
    )
    semantic_audit = audit_runtime_semantic_boundary(runtime_source)
    transport_audit = audit_authorization_transport_runtime(runtime_source)
    expected_notebook, runtime_sha, wrapper_sha = _notebook_bytes(runtime_source)
    observed = _read_file(repo_root, NOTEBOOK_PATH)
    if observed != expected_notebook:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_NOTEBOOK_DRIFT",
            "generated V2 notebook is not canonical",
            NOTEBOOK_PATH.as_posix(),
        )
    payload = json.loads(observed)
    if not isinstance(payload, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_NOTEBOOK_INVALID",
            "generated V2 notebook is not a JSON object",
            NOTEBOOK_PATH.as_posix(),
        )
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 1:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_NOTEBOOK_INVALID",
            "generated V2 notebook must contain exactly one code cell",
            NOTEBOOK_PATH.as_posix(),
        )
    cell = cells[0]
    if not isinstance(cell, dict):
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_NOTEBOOK_INVALID",
            "generated V2 notebook code cell is invalid",
            NOTEBOOK_PATH.as_posix(),
        )
    if cell.get("execution_count") is not None or cell.get("outputs") != []:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_NOTEBOOK_EXECUTION_STATE_PRESENT",
            "V2 implementation notebook must remain unexecuted",
            NOTEBOOK_PATH.as_posix(),
        )
    return {
        "status": "EXACT_RUNTIME_P5_P6_V2_NOTEBOOK_VALID",
        "notebook_sha256": _sha256_bytes(observed),
        "runtime_script_sha256": runtime_sha,
        "wrapper_code_sha256": wrapper_sha,
        "semantic_boundary": semantic_audit,
        "authorization_transport": transport_audit,
        "runtime_execution_authorized": False,
    }


def runtime_namespace(repo_root: Path) -> dict[str, object]:
    review = _review(repo_root)
    runtime_source = _render_runtime_template(
        repo_root,
        _sha256_bytes(review.canonical_bytes()),
    )
    module_name = "auragateway_static_runtime_validation"
    module = types.ModuleType(module_name)
    module.__dict__["EXECUTED_RUNTIME_SCRIPT_SHA256"] = _sha256_bytes(runtime_source)
    sys.modules[module_name] = module
    exec(
        compile(
            runtime_source,
            "<auragateway-exact-runtime-p5-p6-v2-static>",
            "exec",
        ),
        module.__dict__,
        module.__dict__,
    )
    return cast(dict[str, object], module.__dict__)


def validate_implementation(repo_root: Path) -> dict[str, object]:
    _require_base_main_ancestor(repo_root)
    design = validate_design_authority(repo_root)
    predecessor = validate_predecessor_lineage(repo_root)
    behavioral = audit_behavioral_core_preservation(repo_root)
    authorities = _accepted_authorities(repo_root)
    generated = validate_generated(repo_root)
    notebook = validate_notebook(repo_root)
    if len(authorities) != 7:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_AUTHORITY_COUNT_DRIFT",
            "accepted authority inventory no longer contains seven entries",
        )
    if len(CANDIDATE_PATHS) != 12:
        raise ImplementationError(
            "P5_P6_EXACT_RUNTIME_V2_CANDIDATE_BOUNDARY_DRIFT",
            "V2 remediation candidate must contain exactly twelve paths",
        )
    return {
        "status": "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2_IMPLEMENTATION_VALID",
        "implementation_base_main_commit": SOURCE_MAIN_COMMIT,
        "design": design,
        "predecessor": predecessor,
        "behavioral_core": behavioral,
        "accepted_authority_count": len(authorities),
        "candidate_path_count": len(CANDIDATE_PATHS),
        "generated": generated,
        "notebook": notebook,
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "fresh_authorization_issuer_implemented": False,
        "fresh_authorization_issued": False,
        "next_gate": NEXT_GATE,
    }


def _print_error(error: ImplementationError) -> None:
    print(
        _canonical_json_bytes(error.envelope()).decode("utf-8"),
        file=sys.stderr,
    )


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "generate",
            "validate",
            "validate-generated",
            "validate-notebook",
            "validate-design",
        ),
    )
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        if args.command == "generate":
            result = generate(repo_root)
        elif args.command == "validate-generated":
            result = validate_generated(repo_root)
        elif args.command == "validate-notebook":
            result = validate_notebook(repo_root)
        elif args.command == "validate-design":
            result = validate_design_authority(repo_root)
        else:
            result = validate_implementation(repo_root)
    except ImplementationError as error:
        _print_error(error)
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

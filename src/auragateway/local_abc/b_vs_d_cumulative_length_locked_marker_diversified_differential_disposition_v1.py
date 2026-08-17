"""Preserve and disposition the governed B-vs-D marker-diversified differential."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "75860f22287511bafba2bcf42be16214ef8b41a6260857fe258596aaab5d69d1"
SAVED_VERSION_ID: Final = 343074095
ISSUER_MERGE_COMMIT: Final = "f142fe3e94984ced197b836c7fae477b0d71eecb"

CUSTODY_MANIFEST_SHA256: Final = "d9e263ada8b03f5e77c87d91d44a28c463f68368d0cf4ca90e30df6b61f57ab2"
EVIDENCE_ZIP_SHA256: Final = "4661552364736621338249e6a21d0cacfbd355ba04e57432943cf721fc40e0f0"
OUTER_RESULTS_ZIP_SHA256: Final = "6d6313e87f3ffc1df803b4507f94fbc53d1628e83c0e8b42d074c3bf38a4f71c"
TERMINAL_LOG_SHA256: Final = "fa88a9c4de4476e4a3daf359d8d4fb2b24b874a96ea9e2daeb9417513f1a0e32"
NOTEBOOK_SHA256: Final = "1913d9ed109db8360924dc1f3343aaae076259a5b071466ced134fc29b8e3eb7"
AUTHORIZATION_SHA256: Final = "df538079793052bf4af9e569c9209df79ab9e0a7d36e169d68ffaee33bce912c"
EXECUTION_MANIFEST_SHA256: Final = (
    "4ffee8262a8b6687cc34169f9d80a7a20bed0768542b88bb9cf6e4e2d6871838"
)
PLATFORM_RECEIPT_SHA256: Final = "eada301361f9623e7af0d5dadd20c40087c14c3e8ffa672568aedae00fcddcd7"
TERMINAL_RECEIPT_SHA256: Final = "30ddc5b08bc304a6ea9463e06c6c2afd26e5a4e9a9e0eb8a0a97576692c2b946"

RUNTIME_SHA256: Final = "fe5bf3cc731d42ead44451cea4298ba1507cbcba28b65fcdbae0a31237868d39"
IMPLEMENTATION_RECORD_SHA256: Final = (
    "795a7cdf5285ba49e5dcc57a76cd46e03f07121359a5f66101692cee41bb2074"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "7278fdf91cef5fd2a19e39f4bc34421c2dce823a42e09aacc7c44ccce7fb53dc"
)
AUTHORIZATION_DESIGN_RECORD_SHA256: Final = (
    "77a8140ad6a95da54bc1b21a5844edbbcbc52f53e75d0ba2eaf8de4b55a0d848"
)
ISSUER_SOURCE_SHA256: Final = "b4b515ec494f943808fa0157a367bd7ede3b304f39acb287520baf83293d73cd"
GENERATOR_CONTRACT_SHA256: Final = (
    "b30c890e359c0745d5e759758065d0a8a4d6619060a658c6a04f71ca76642432"
)

DECISION_STATE: Final = "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
NEXT_GATE: Final = "REPAIR_TRANSACTION_BOUND_WRAPPER_ZERO_EXIT_REPORTING_BEFORE_NEW_EXECUTION_V1"

VAULT_ROOT: Final = Path("evidence_vault/local_abc/b-vs-d-marker-diversified-diff-v1")
CUSTODY_MANIFEST_PATH: Final = VAULT_ROOT / "custody_manifest_v1.json"
AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/execution_authorization_v1.json"
EXECUTION_MANIFEST_PATH: Final = VAULT_ROOT / "lifecycle/execution_artifact_manifest_v1.json"
PLATFORM_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/platform_observation_receipt_v1.json"
TERMINAL_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/authorization_terminal_receipt_v1.json"
EVIDENCE_ZIP_PATH: Final = VAULT_ROOT / "kaggle/evidence-v1-343074095.zip"
OUTER_RESULTS_ZIP_PATH: Final = VAULT_ROOT / "kaggle/results-343074095.zip"
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "kaggle/kaggle-terminal-343074095.log"
NOTEBOOK_PATH: Final = VAULT_ROOT / "kaggle/ag-b-vs-d-marker-diversified-diff-v1-343074095.ipynb"

RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_runtime_v1.py"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1.json"
)
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1_review.json"
)
AUTHORIZATION_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_execution_authorization_design_v1.json"
)
ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_"
    "execution_authorization_v1.py"
)
GENERATOR_CONTRACT_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_"
    "transaction_bound_wrapper_v1.py.tmpl"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_disposition_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_disposition_v1_review.json"
)

REQUEST_ORDER: Final = (
    "B_NEUTRAL_REPEATED_24X",
    "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
    "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
    "B_NEUTRAL_REPEATED_24X",
    "B_NEUTRAL_REPEATED_24X",
    "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED",
)


class DispositionError(RuntimeError):
    """Fail-closed evidence-disposition error."""

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


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise DispositionError(
            "B_VS_D_DISPOSITION_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(StrictModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int | None = Field(default=None, gt=0)


class CustodyManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    manifest_id: Literal["auragateway-b-vs-d-marker-diversified-differential-evidence-custody-v1"]
    transaction_id: Literal["75860f22287511bafba2bcf42be16214ef8b41a6260857fe258596aaab5d69d1"]
    saved_version_id: Literal[343074095]
    execution_status: Literal["DIAGNOSTIC_COMPLETE"]
    decision_state: Literal["MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"]
    condition_b_exact_object_count: Literal[0]
    condition_d_exact_object_count: Literal[3]
    terminal_disposition: Literal["CONSUMED"]
    terminal_execution_outcome: Literal["PASSED"]
    authorization_reusable: Literal[False]
    wrapper_reporting_defect_observed: Literal[True]
    member_count: Literal[8]
    members: tuple[ArtifactReceipt, ...]

    @model_validator(mode="after")
    def validate_members(self) -> Self:
        if len(self.members) != self.member_count:
            raise ValueError("custody member count drifted")
        if any(item.size_bytes is None for item in self.members):
            raise ValueError("custody member size is missing")
        return self


class DispositionRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-b-vs-d-marker-diversified-differential-disposition-v1"]
    status: Literal["DISPOSITIONED_VALID_GOVERNED_B_VS_D_DIFFERENTIAL"]
    transaction_id: Literal["75860f22287511bafba2bcf42be16214ef8b41a6260857fe258596aaab5d69d1"]
    saved_version_id: Literal[343074095]
    terminal_disposition: Literal["CONSUMED"]
    execution_outcome: Literal["PASSED"]
    diagnostic_status: Literal["DIAGNOSTIC_COMPLETE"]
    decision_state: Literal["MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"]
    variable_under_test: Literal["MARKER_DIVERSIFICATION_UNDER_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"]
    prompt_token_count_per_condition: Literal[899]
    observations_per_condition: Literal[3]
    condition_b_exact_object_count: Literal[0]
    condition_d_exact_object_count: Literal[3]
    condition_b_valid_json_count: Literal[0]
    condition_d_valid_json_count: Literal[3]
    b_anchor_reproduced: Literal[True]
    mechanistic_inference_permitted: Literal[True]
    all_condition_token_identities_matched: Literal[True]
    all_condition_payload_identities_matched: Literal[True]
    complete_cumulative_prompt_token_profile_locked: Literal[True]
    fresh_worker_process_per_observation: Literal[True]
    worker_identity_cardinality: Literal[6]
    runtime_source_identity_verified: Literal[True]
    runtime_installation_passed: Literal[True]
    runtime_import_closure_passed: Literal[True]
    model_requests_performed: Literal[6]
    model_loads_performed: Literal[6]
    worker_starts_performed: Literal[6]
    hidden_retries_performed: Literal[0]
    external_network_requests_performed: Literal[0]
    benchmark_trajectory_requests_performed: Literal[0]
    external_spend: Literal[0]
    teardown_passed: Literal[True]
    scratch_cleanup_passed: Literal[True]
    raw_prompt_retained: Literal[False]
    raw_model_output_retained: Literal[False]
    p5_requalified: Literal[False]
    p6_requalified: Literal[False]
    measured_abc_execution_performed: Literal[False]
    pilot_execution_performed: Literal[False]
    marker_diversification_restores_behavior_under_length_lock: Literal[True]
    exact_repetition_sole_or_root_cause_established: Literal[False]
    exact_ngram_and_periodicity_effects_individually_isolated: Literal[False]
    marker_lexical_semantic_novelty_eliminated: Literal[False]
    text_boundary_token_boundary_assumption_used: Literal[False]
    exact_repetition_threshold_established: Literal[False]
    context_length_alone_established_causal: Literal[False]
    exact_root_cause_established: Literal[False]
    prefix_cache_defect_established: Literal[False]
    wrapper_reporting_defect_observed: Literal[True]
    wrapper_reporting_defect_classification: Literal[
        "CONTROL_PLANE_ZERO_EXIT_SYSTEMEXIT_FALSE_POSITIVE"
    ]
    scientific_result_invalidated_by_wrapper_reporting_defect: Literal[False]
    new_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    mechanistic_classification: Literal[
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
    ]
    evidence_confidence: Literal[
        "PREDECLARED_B_VS_D_DIFFERENTIAL_WITH_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"
    ]
    custody_manifest_sha256: Literal[
        "d9e263ada8b03f5e77c87d91d44a28c463f68368d0cf4ca90e30df6b61f57ab2"
    ]
    governed_evidence_zip_sha256: Literal[
        "4661552364736621338249e6a21d0cacfbd355ba04e57432943cf721fc40e0f0"
    ]
    outer_kaggle_results_zip_sha256: Literal[
        "6d6313e87f3ffc1df803b4507f94fbc53d1628e83c0e8b42d074c3bf38a4f71c"
    ]
    authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...]
    next_gate: Literal[
        "REPAIR_TRANSACTION_BOUND_WRAPPER_ZERO_EXIT_REPORTING_BEFORE_NEW_EXECUTION_V1"
    ]

    @model_validator(mode="after")
    def validate_boundary(self) -> Self:
        if len(self.authorities) != 15:
            raise ValueError("disposition authority count drifted")
        if len(self.non_claims) < 14:
            raise ValueError("disposition non-claim boundary is incomplete")
        return self


class DispositionReview(StrictModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal["auragateway-b-vs-d-marker-diversified-differential-disposition-v1-review"]
    status: Literal["APPROVED_GOVERNED_B_VS_D_DIFFERENTIAL_DISPOSITION"]
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: Literal[
        "d9e263ada8b03f5e77c87d91d44a28c463f68368d0cf4ca90e30df6b61f57ab2"
    ]
    marker_diversification_result_accepted: Literal[True]
    wrapper_reporting_defect_accepted_as_control_plane_only: Literal[True]
    scientific_result_invalidated_by_wrapper_defect: Literal[False]
    exact_repetition_root_cause_claimed: Literal[False]
    exact_ngram_or_periodicity_effect_claimed: Literal[False]
    exact_threshold_claimed: Literal[False]
    p5_requalification_claimed: Literal[False]
    p6_requalification_claimed: Literal[False]
    measured_abc_claimed: Literal[False]
    new_execution_authorized: Literal[False]
    next_gate: Literal[
        "REPAIR_TRANSACTION_BOUND_WRAPPER_ZERO_EXIT_REPORTING_BEFORE_NEW_EXECUTION_V1"
    ]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )


def _require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise DispositionError(
            "B_VS_D_DISPOSITION_ARTIFACT_MISSING",
            "required disposition artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _require_hash(root: Path, relative: Path, expected: str) -> Path:
    path = _require_file(root, relative)
    if _sha256_file(path) != expected:
        raise DispositionError(
            "B_VS_D_DISPOSITION_IDENTITY_DRIFT",
            "disposition artifact byte identity drifted",
            relative.as_posix(),
        )
    return path


def _load_json(root: Path, relative: Path) -> dict[str, object]:
    path = _require_file(root, relative)
    try:
        payload: object = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DispositionError(
            "B_VS_D_DISPOSITION_JSON_INVALID",
            "disposition JSON is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise DispositionError(
            "B_VS_D_DISPOSITION_JSON_INVALID",
            "disposition JSON root must be one object",
            relative.as_posix(),
        )
    return payload


def _artifact(
    root: Path,
    relative: Path,
    role: str,
    expected_sha256: str,
    *,
    include_size: bool = True,
) -> ArtifactReceipt:
    path = _require_hash(root, relative, expected_sha256)
    return ArtifactReceipt(
        role=role,
        path=relative.as_posix(),
        sha256=expected_sha256,
        size_bytes=path.stat().st_size if include_size else None,
    )


def validate_custody(root: Path) -> CustodyManifest:
    _require_hash(root, CUSTODY_MANIFEST_PATH, CUSTODY_MANIFEST_SHA256)
    payload = _load_json(root, CUSTODY_MANIFEST_PATH)
    manifest = CustodyManifest.model_validate(payload)
    for item in manifest.members:
        relative = Path(item.path)
        path = _require_hash(root, relative, item.sha256)
        if path.stat().st_size != item.size_bytes:
            raise DispositionError(
                "B_VS_D_DISPOSITION_SIZE_DRIFT",
                "custody member size drifted",
                item.path,
            )
    return manifest


def _load_zip_json(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    try:
        payload: object = json.loads(archive.read(name))
    except (KeyError, UnicodeError, json.JSONDecodeError) as error:
        raise DispositionError(
            "B_VS_D_DISPOSITION_EVIDENCE_JSON_INVALID",
            "governed evidence JSON is missing or invalid",
            name,
        ) from error
    if not isinstance(payload, dict):
        raise DispositionError(
            "B_VS_D_DISPOSITION_EVIDENCE_JSON_INVALID",
            "governed evidence JSON root must be one object",
            name,
        )
    return payload


def validate_evidence_bundle(root: Path) -> None:
    path = _require_hash(root, EVIDENCE_ZIP_PATH, EVIDENCE_ZIP_SHA256)
    with zipfile.ZipFile(path) as archive:
        required = {
            "bundle_manifest_v1.json",
            "b_vs_d_marker_diversified_decision_v1.json",
            "b_vs_d_marker_diversified_request_results_v1.json",
            "b_vs_d_marker_diversified_runtime_ready_v1.json",
            "b_vs_d_marker_diversified_summary_v1.json",
            "worker_teardown_report_v1.json",
            "scratch_cleanup_report_v1.json",
            "failure_report_v1.json",
            "runtime_source_identity_report_v1.json",
            "runtime_import_closure_report_v1.json",
        }
        if not required.issubset(set(archive.namelist())):
            raise DispositionError(
                "B_VS_D_DISPOSITION_EVIDENCE_INCOMPLETE",
                "governed evidence ZIP is missing required members",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

        bundle = _load_zip_json(archive, "bundle_manifest_v1.json")
        members = bundle.get("members")
        if not isinstance(members, list) or len(members) != 13:
            raise ValueError("bundle manifest member cardinality drifted")
        for raw in members:
            if not isinstance(raw, dict):
                raise ValueError("bundle member is invalid")
            member_path = raw.get("path")
            expected_sha = raw.get("sha256")
            expected_size = raw.get("size_bytes")
            if (
                not isinstance(member_path, str)
                or not isinstance(expected_sha, str)
                or not isinstance(expected_size, int)
            ):
                raise ValueError("bundle member identity is invalid")
            observed = archive.read(member_path)
            if _sha256_bytes(observed) != expected_sha:
                raise ValueError("bundle member SHA-256 drifted")
            if len(observed) != expected_size:
                raise ValueError("bundle member size drifted")

        decision = _load_zip_json(
            archive,
            "b_vs_d_marker_diversified_decision_v1.json",
        )
        if decision.get("decision_state") != DECISION_STATE:
            raise ValueError("B-vs-D decision state drifted")
        if decision.get("condition_exact_object_counts") != {
            "B_NEUTRAL_REPEATED_24X": 0,
            "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED": 3,
        }:
            raise ValueError("B-vs-D exact-object counts drifted")
        if decision.get("condition_valid_json_counts") != {
            "B_NEUTRAL_REPEATED_24X": 0,
            "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED": 3,
        }:
            raise ValueError("B-vs-D valid-JSON counts drifted")
        if decision.get("b_anchor_reproduced") is not True:
            raise ValueError("B historical anchor was not reproduced")
        if decision.get("mechanistic_inference_permitted") is not True:
            raise ValueError("mechanistic inference gate is not satisfied")
        if decision.get("complete_cumulative_prompt_token_profile_locked") is not True:
            raise ValueError("cumulative prompt token profile lock drifted")
        if decision.get("worker_identity_cardinality") != 6:
            raise ValueError("fresh-worker identity cardinality drifted")
        if decision.get("marker_lexical_semantic_novelty_bounded_not_eliminated") is not True:
            raise ValueError("marker novelty boundary drifted")
        if (
            decision.get("exact_ngram_block_and_periodicity_effects_not_individually_isolated")
            is not True
        ):
            raise ValueError("n-gram and periodicity non-claim drifted")
        if decision.get("text_boundary_token_boundary_assumption_used") is not False:
            raise ValueError("text/token boundary non-assumption drifted")

        summary = _load_zip_json(
            archive,
            "b_vs_d_marker_diversified_summary_v1.json",
        )
        expected_summary = {
            "status": "DIAGNOSTIC_COMPLETE",
            "decision_state": DECISION_STATE,
            "completed_requests": 6,
            "scheduled_requests": 6,
            "model_requests": 6,
            "model_loads": 6,
            "worker_starts": 6,
            "hidden_retries": 0,
            "external_network_requests": 0,
            "external_spend": 0,
            "teardown_status": "PASSED",
            "scratch_cleanup_status": "PASSED",
            "measured_abc_execution_performed": False,
            "p5_requalified": False,
            "p6_requalified": False,
        }
        for key, value in expected_summary.items():
            if summary.get(key) != value:
                raise ValueError(f"summary field drifted: {key}")
        raw_request_order = summary.get("request_order")
        if not isinstance(raw_request_order, list):
            raise ValueError("request order is not a list")

        observed_request_order: list[str] = []
        for item in raw_request_order:
            if not isinstance(item, str):
                raise ValueError("request order member is not a string")
            observed_request_order.append(item)

        if tuple(observed_request_order) != REQUEST_ORDER:
            raise ValueError("request order drifted")

        results = _load_zip_json(
            archive,
            "b_vs_d_marker_diversified_request_results_v1.json",
        )
        if results.get("status") != "COMPLETE":
            raise ValueError("request-results status drifted")
        if results.get("scheduled_request_count") != 6:
            raise ValueError("scheduled request count drifted")
        observations = results.get("results")
        if not isinstance(observations, list) or len(observations) != 6:
            raise ValueError("request observation cardinality drifted")
        observed_order = tuple(
            item.get("condition_id") for item in observations if isinstance(item, dict)
        )
        if observed_order != REQUEST_ORDER:
            raise ValueError("request observation order drifted")
        if not all(
            isinstance(item, dict) and item.get("zero_cache_baseline") is True
            for item in observations
        ):
            raise ValueError("zero-cache baseline drifted")

        runtime_ready = _load_zip_json(
            archive,
            "b_vs_d_marker_diversified_runtime_ready_v1.json",
        )
        if runtime_ready.get("status") != "PASSED":
            raise ValueError("runtime-ready status drifted")
        if runtime_ready.get("backend") != "TRITON_ATTN":
            raise ValueError("runtime backend drifted")
        if runtime_ready.get("model_repository") != "Qwen/Qwen2.5-0.5B-Instruct":
            raise ValueError("model repository drifted")
        if runtime_ready.get("model_revision") != ("7ae557604adf67be50417f59c2c2f167def9a775"):
            raise ValueError("model revision drifted")
        if runtime_ready.get("model_snapshot_sha256") != (
            "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
        ):
            raise ValueError("model snapshot identity drifted")

        source_identity = _load_zip_json(
            archive,
            "runtime_source_identity_report_v1.json",
        )
        if source_identity.get("executed_runtime_script_sha256") != RUNTIME_SHA256:
            raise ValueError("executed runtime source identity drifted")
        if source_identity.get("wrapper_hash_verification_passed") is not True:
            raise ValueError("wrapper runtime hash verification drifted")

        import_closure = _load_zip_json(
            archive,
            "runtime_import_closure_report_v1.json",
        )
        if import_closure.get("status") != "PASSED":
            raise ValueError("runtime import-closure status drifted")
        if import_closure.get("hidden_retry_count") != 0:
            raise ValueError("runtime import-closure hidden retry drifted")
        if import_closure.get("network_access_requested") is not False:
            raise ValueError("runtime import-closure network boundary drifted")

        teardown = _load_zip_json(archive, "worker_teardown_report_v1.json")
        if teardown.get("status") != "PASSED":
            raise ValueError("worker teardown status drifted")
        if teardown.get("observed_teardown_count") != 6:
            raise ValueError("worker teardown cardinality drifted")

        scratch = _load_zip_json(archive, "scratch_cleanup_report_v1.json")
        if scratch.get("status") != "PASSED":
            raise ValueError("scratch cleanup status drifted")
        if scratch.get("scratch_exists_after") is not False:
            raise ValueError("scratch cleanup terminal state drifted")

        failure = _load_zip_json(archive, "failure_report_v1.json")
        if failure.get("status") != "NOT_APPLICABLE":
            raise ValueError("runtime failure report drifted")


def validate_outer_results(root: Path) -> None:
    path = _require_hash(
        root,
        OUTER_RESULTS_ZIP_PATH,
        OUTER_RESULTS_ZIP_SHA256,
    )
    with zipfile.ZipFile(path) as archive:
        inner_name = (
            "ag-b-vs-d-cumulative-length-locked-marker-diversified-differential-evidence-v1.zip"
        )
        failure_name = (
            "b_vs_d_cumulative_length_locked_marker_diversified_"
            "differential_primary_failure_v1.json"
        )
        admission_name = (
            "b_vs_d_cumulative_length_locked_marker_diversified_"
            "differential_transaction_bound_admission_v1.json"
        )
        required = {inner_name, failure_name, admission_name}
        if not required.issubset(set(archive.namelist())):
            raise ValueError("outer Kaggle results ZIP boundary drifted")
        if _sha256_bytes(archive.read(inner_name)) != EVIDENCE_ZIP_SHA256:
            raise ValueError("outer results nested evidence identity drifted")

        failure = _load_zip_json(archive, failure_name)
        if failure.get("status") != "PRIMARY_FAILURE_CAPTURED":
            raise ValueError("wrapper primary-failure capture status drifted")
        if failure.get("exception_type") != "SystemExit":
            raise ValueError("wrapper primary-failure type drifted")
        if failure.get("safe_message") != "0":
            raise ValueError("wrapper zero-exit signal drifted")
        if failure.get("transaction_id") != TRANSACTION_ID:
            raise ValueError("wrapper primary-failure transaction drifted")

        admission = _load_zip_json(archive, admission_name)
        if admission.get("status") != (
            "B_VS_D_MARKER_DIVERSIFIED_TRANSACTION_BOUND_RUNTIME_ADMISSION_VALID"
        ):
            raise ValueError("transaction-bound admission status drifted")
        if admission.get("transaction_id") != TRANSACTION_ID:
            raise ValueError("transaction-bound admission identity drifted")
        if admission.get("issuer_merge_commit") != ISSUER_MERGE_COMMIT:
            raise ValueError("transaction-bound issuer binding drifted")
        if admission.get("runtime_payload_sha256") != RUNTIME_SHA256:
            raise ValueError("transaction-bound runtime binding drifted")


def validate_notebook_reporting_defect(root: Path) -> None:
    path = _require_hash(root, NOTEBOOK_PATH, NOTEBOOK_SHA256)
    try:
        notebook: object = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise DispositionError(
            "B_VS_D_DISPOSITION_NOTEBOOK_INVALID",
            "saved notebook JSON is invalid",
            NOTEBOOK_PATH.as_posix(),
        ) from error
    if not isinstance(notebook, dict):
        raise ValueError("saved notebook root is invalid")
    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("saved notebook has no cells")
    first_cell = cells[0]
    if not isinstance(first_cell, dict):
        raise ValueError("saved notebook first cell is invalid")
    outputs = first_cell.get("outputs")
    if not isinstance(outputs, list):
        raise ValueError("saved notebook first-cell outputs are invalid")

    system_exit_zero = False
    successful_summary = False
    for output in outputs:
        if not isinstance(output, dict):
            continue
        if (
            output.get("output_type") == "error"
            and output.get("ename") == "SystemExit"
            and output.get("evalue") == "0"
        ):
            system_exit_zero = True
        if output.get("output_type") != "stream":
            continue
        text = output.get("text")
        if isinstance(text, list):
            rendered = "".join(item for item in text if isinstance(item, str))
        elif isinstance(text, str):
            rendered = text
        else:
            continue
        if DECISION_STATE in rendered and TRANSACTION_ID in rendered:
            successful_summary = True

    if not system_exit_zero:
        raise ValueError("zero-exit SystemExit notebook artifact was not preserved")
    if not successful_summary:
        raise ValueError("successful diagnostic summary was not preserved")


def validate_lifecycle(root: Path) -> None:
    _require_hash(root, AUTHORIZATION_PATH, AUTHORIZATION_SHA256)
    _require_hash(root, EXECUTION_MANIFEST_PATH, EXECUTION_MANIFEST_SHA256)
    _require_hash(root, PLATFORM_RECEIPT_PATH, PLATFORM_RECEIPT_SHA256)
    _require_hash(root, TERMINAL_RECEIPT_PATH, TERMINAL_RECEIPT_SHA256)

    authorization = _load_json(root, AUTHORIZATION_PATH)
    execution_manifest = _load_json(root, EXECUTION_MANIFEST_PATH)
    platform = _load_json(root, PLATFORM_RECEIPT_PATH)
    terminal = _load_json(root, TERMINAL_RECEIPT_PATH)

    for payload in (
        authorization,
        execution_manifest,
        platform,
        terminal,
    ):
        if payload.get("transaction_id") != TRANSACTION_ID:
            raise ValueError("transaction identity drifted")

    auth = authorization.get("authorization")
    if not isinstance(auth, dict):
        raise ValueError("authorization payload is invalid")
    if auth.get("decision") != "AUTHORIZED":
        raise ValueError("authorization decision drifted")
    if auth.get("single_use") is not True:
        raise ValueError("single-use authorization boundary drifted")
    if auth.get("authorization_reusable") is not False:
        raise ValueError("authorization reuse boundary drifted")
    if auth.get("issuer_merge_commit") != ISSUER_MERGE_COMMIT:
        raise ValueError("authorization issuer merge binding drifted")
    if auth.get("runtime_payload_sha256") != RUNTIME_SHA256:
        raise ValueError("authorization runtime binding drifted")

    if execution_manifest.get("status") != "TRANSACTION_BOUND_EXECUTABLE_GENERATED":
        raise ValueError("execution artifact manifest status drifted")
    if execution_manifest.get("issuer_merge_commit") != ISSUER_MERGE_COMMIT:
        raise ValueError("execution manifest issuer binding drifted")
    if execution_manifest.get("runtime_payload_sha256") != RUNTIME_SHA256:
        raise ValueError("execution manifest runtime binding drifted")

    if platform.get("accelerator") != "T4_X2":
        raise ValueError("platform accelerator drifted")
    if platform.get("allocated_gpu_count") != 2:
        raise ValueError("platform GPU count drifted")
    if platform.get("internet_enabled") is not False:
        raise ValueError("platform Internet-Off binding drifted")
    if platform.get("persisted_before_save_and_run_all") is not True:
        raise ValueError("durable platform observation ordering drifted")

    if terminal.get("disposition") != "CONSUMED":
        raise ValueError("terminal disposition drifted")
    if terminal.get("execution_attempted") is not True:
        raise ValueError("terminal execution-attempt state drifted")
    if terminal.get("execution_outcome") != "PASSED":
        raise ValueError("terminal execution outcome drifted")
    if terminal.get("saved_version_id") != SAVED_VERSION_ID:
        raise ValueError("saved version identity drifted")
    if terminal.get("authorization_reusable") is not False:
        raise ValueError("terminal authorization remains reusable")
    if terminal.get("runtime_execution_authorized") is not False:
        raise ValueError("terminal runtime authority remains live")
    if terminal.get("evidence_zip_sha256") != EVIDENCE_ZIP_SHA256:
        raise ValueError("terminal evidence binding drifted")
    if terminal.get("terminal_log_sha256") != TERMINAL_LOG_SHA256:
        raise ValueError("terminal log binding drifted")
    if terminal.get("platform_observation_receipt_sha256") != PLATFORM_RECEIPT_SHA256:
        raise ValueError("terminal platform binding drifted")


def validate_repo_authorities(root: Path) -> None:
    expected = (
        (RUNTIME_PATH, RUNTIME_SHA256),
        (IMPLEMENTATION_RECORD_PATH, IMPLEMENTATION_RECORD_SHA256),
        (IMPLEMENTATION_REVIEW_PATH, IMPLEMENTATION_REVIEW_SHA256),
        (
            AUTHORIZATION_DESIGN_RECORD_PATH,
            AUTHORIZATION_DESIGN_RECORD_SHA256,
        ),
        (ISSUER_SOURCE_PATH, ISSUER_SOURCE_SHA256),
        (GENERATOR_CONTRACT_PATH, GENERATOR_CONTRACT_SHA256),
    )
    for path, digest in expected:
        _require_hash(root, path, digest)


def build_record(root: Path) -> DispositionRecord:
    root = root.resolve()
    custody = validate_custody(root)
    validate_evidence_bundle(root)
    validate_outer_results(root)
    validate_notebook_reporting_defect(root)
    validate_lifecycle(root)
    validate_repo_authorities(root)

    custody_authority = ArtifactReceipt(
        role="custody_manifest",
        path=CUSTODY_MANIFEST_PATH.as_posix(),
        sha256=CUSTODY_MANIFEST_SHA256,
        size_bytes=(root / CUSTODY_MANIFEST_PATH).stat().st_size,
    )
    repo_authorities = (
        _artifact(root, RUNTIME_PATH, "runtime_payload", RUNTIME_SHA256),
        _artifact(
            root,
            IMPLEMENTATION_RECORD_PATH,
            "implementation_record",
            IMPLEMENTATION_RECORD_SHA256,
        ),
        _artifact(
            root,
            IMPLEMENTATION_REVIEW_PATH,
            "implementation_review",
            IMPLEMENTATION_REVIEW_SHA256,
        ),
        _artifact(
            root,
            AUTHORIZATION_DESIGN_RECORD_PATH,
            "authorization_design_record",
            AUTHORIZATION_DESIGN_RECORD_SHA256,
        ),
        _artifact(
            root,
            ISSUER_SOURCE_PATH,
            "issuer_source",
            ISSUER_SOURCE_SHA256,
            include_size=False,
        ),
        _artifact(
            root,
            GENERATOR_CONTRACT_PATH,
            "generator_contract",
            GENERATOR_CONTRACT_SHA256,
        ),
    )
    authorities = (
        custody_authority,
        *custody.members,
        *repo_authorities,
    )

    return DispositionRecord(
        schema_version="1.0.0",
        record_id=("auragateway-b-vs-d-marker-diversified-differential-disposition-v1"),
        status="DISPOSITIONED_VALID_GOVERNED_B_VS_D_DIFFERENTIAL",
        transaction_id=TRANSACTION_ID,
        saved_version_id=SAVED_VERSION_ID,
        terminal_disposition="CONSUMED",
        execution_outcome="PASSED",
        diagnostic_status="DIAGNOSTIC_COMPLETE",
        decision_state=DECISION_STATE,
        variable_under_test=("MARKER_DIVERSIFICATION_UNDER_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"),
        prompt_token_count_per_condition=899,
        observations_per_condition=3,
        condition_b_exact_object_count=0,
        condition_d_exact_object_count=3,
        condition_b_valid_json_count=0,
        condition_d_valid_json_count=3,
        b_anchor_reproduced=True,
        mechanistic_inference_permitted=True,
        all_condition_token_identities_matched=True,
        all_condition_payload_identities_matched=True,
        complete_cumulative_prompt_token_profile_locked=True,
        fresh_worker_process_per_observation=True,
        worker_identity_cardinality=6,
        runtime_source_identity_verified=True,
        runtime_installation_passed=True,
        runtime_import_closure_passed=True,
        model_requests_performed=6,
        model_loads_performed=6,
        worker_starts_performed=6,
        hidden_retries_performed=0,
        external_network_requests_performed=0,
        benchmark_trajectory_requests_performed=0,
        external_spend=0,
        teardown_passed=True,
        scratch_cleanup_passed=True,
        raw_prompt_retained=False,
        raw_model_output_retained=False,
        p5_requalified=False,
        p6_requalified=False,
        measured_abc_execution_performed=False,
        pilot_execution_performed=False,
        marker_diversification_restores_behavior_under_length_lock=True,
        exact_repetition_sole_or_root_cause_established=False,
        exact_ngram_and_periodicity_effects_individually_isolated=False,
        marker_lexical_semantic_novelty_eliminated=False,
        text_boundary_token_boundary_assumption_used=False,
        exact_repetition_threshold_established=False,
        context_length_alone_established_causal=False,
        exact_root_cause_established=False,
        prefix_cache_defect_established=False,
        wrapper_reporting_defect_observed=True,
        wrapper_reporting_defect_classification=(
            "CONTROL_PLANE_ZERO_EXIT_SYSTEMEXIT_FALSE_POSITIVE"
        ),
        scientific_result_invalidated_by_wrapper_reporting_defect=False,
        new_execution_authorized=False,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        mechanistic_classification=DECISION_STATE,
        evidence_confidence=(
            "PREDECLARED_B_VS_D_DIFFERENTIAL_WITH_CUMULATIVE_PROMPT_TOKEN_LENGTH_LOCK"
        ),
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        governed_evidence_zip_sha256=EVIDENCE_ZIP_SHA256,
        outer_kaggle_results_zip_sha256=OUTER_RESULTS_ZIP_SHA256,
        authorities=authorities,
        non_claims=(
            "The result does not establish exact repetition as the sole or root cause.",
            "Exact n-gram block effects are not individually isolated.",
            "Aligned periodicity effects are not individually isolated.",
            "Marker lexical novelty was not eliminated.",
            "Marker semantic novelty was not eliminated.",
            "The exact repetition threshold is not established.",
            "Context length alone is not established as causal.",
            "The exact root cause of the historical regression is not established.",
            "A prefix-cache defect is not established.",
            "P5 is not requalified by this diagnostic.",
            "P6 is not requalified by this diagnostic.",
            "Measured North-Star A/B/C execution was not performed.",
            "The zero-exit wrapper reporting defect does not invalidate the science.",
            "No new execution is authorized and unchanged replay is unauthorized.",
        ),
        next_gate=NEXT_GATE,
    )


def build_review(record: DispositionRecord) -> DispositionReview:
    record_sha256 = _sha256_bytes(_canonical_bytes(record))
    return DispositionReview(
        schema_version="1.0.0",
        review_id=("auragateway-b-vs-d-marker-diversified-differential-disposition-v1-review"),
        status="APPROVED_GOVERNED_B_VS_D_DIFFERENTIAL_DISPOSITION",
        record_sha256=record_sha256,
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        marker_diversification_result_accepted=True,
        wrapper_reporting_defect_accepted_as_control_plane_only=True,
        scientific_result_invalidated_by_wrapper_defect=False,
        exact_repetition_root_cause_claimed=False,
        exact_ngram_or_periodicity_effect_claimed=False,
        exact_threshold_claimed=False,
        p5_requalification_claimed=False,
        p6_requalification_claimed=False,
        measured_abc_claimed=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def generate(root: Path) -> tuple[bytes, bytes]:
    root = root.resolve()
    record = build_record(root)
    record_bytes = _canonical_bytes(record)
    review = build_review(record)
    review_bytes = _canonical_bytes(review)

    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)
    review_path.write_bytes(review_bytes)
    return record_bytes, review_bytes


def validate(root: Path) -> tuple[DispositionRecord, DispositionReview]:
    root = root.resolve()
    record = build_record(root)
    expected_record = _canonical_bytes(record)
    record_path = _require_file(root, RECORD_PATH)
    if record_path.read_bytes() != expected_record:
        raise DispositionError(
            "B_VS_D_DISPOSITION_RECORD_DRIFT",
            "disposition record bytes drifted",
            RECORD_PATH.as_posix(),
        )

    review = build_review(record)
    expected_review = _canonical_bytes(review)
    review_path = _require_file(root, REVIEW_PATH)
    if review_path.read_bytes() != expected_review:
        raise DispositionError(
            "B_VS_D_DISPOSITION_REVIEW_DRIFT",
            "disposition review bytes drifted",
            REVIEW_PATH.as_posix(),
        )
    return record, review


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="b-vs-d-disposition-v1")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        child = subparsers.add_parser(command)
        child.add_argument("--repo-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload: dict[str, object]
    try:
        if args.command == "generate":
            record_bytes, review_bytes = generate(args.repo_root)
            payload = {
                "status": "GENERATED",
                "record_sha256": _sha256_bytes(record_bytes),
                "review_sha256": _sha256_bytes(review_bytes),
                "next_gate": NEXT_GATE,
            }
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            return 0
        if args.command == "validate":
            record, review = validate(args.repo_root)
            payload = {
                "status": "VALID",
                "decision_state": record.decision_state,
                "review_status": review.status,
                "wrapper_reporting_defect_observed": (record.wrapper_reporting_defect_observed),
                "new_execution_authorized": record.new_execution_authorized,
                "next_gate": record.next_gate,
            }
            print(json.dumps(payload, separators=(",", ":"), sort_keys=True))
            return 0
        raise AssertionError("unreachable disposition command")
    except (DispositionError, ValidationError, ValueError, zipfile.BadZipFile) as error:
        if isinstance(error, DispositionError):
            payload = {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            }
        else:
            payload = {
                "error_code": "B_VS_D_DISPOSITION_VALIDATION_FAILED",
                "safe_message": str(error),
            }
        print(json.dumps(payload, separators=(",", ":"), sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

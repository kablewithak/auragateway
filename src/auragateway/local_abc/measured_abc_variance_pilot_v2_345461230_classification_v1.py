"""Classify governed successor V2 variance-pilot Kaggle Version 345461230 evidence.

The classifier is repository-only and non-authorizing. It validates immutable
lifecycle and Kaggle evidence against one frozen policy, independently derives
pilot-acceptance findings, and may open only the repetition/statistical-freeze
design gate. It never issues execution authority or promotes pilot observations
into final A/B/C effect claims.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v2/"
    "variance_pilot_v2_345461230_classification_v1_policy.json"
)
POLICY_SHA256: Final = "540ae24a00e9af522c816f20e7d7d5dc93c487a7e31523ccfd640af459cb2b33"

RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_v2_transaction_bound_runtime_v1.py"
)
CLASSIFICATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_measured_abc_variance_pilot_v2_345461230_classification_v1.json"
)
ACCEPTANCE_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_v2_345461230_acceptance_v1.json"
)

NEXT_GATE: Final = (
    "MERGE_V2_345461230_PILOT_ACCEPTANCE_THEN_IMPLEMENT_REPETITION_STATISTICAL_FREEZE_V1"
)


class ClassificationError(RuntimeError):
    """Metadata-safe governed pilot classification failure."""

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

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
            "details": list(self.details),
        }


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExpectedSemantics(StrictModel):
    zip_member_count: Literal[32]
    bundle_manifest_member_count: Literal[31]
    scheduled_trajectory_count: Literal[54]
    scheduled_turn_count: Literal[216]
    pretreatment_request_count: Literal[24]
    pilot_model_request_count: Literal[216]
    total_model_request_count: Literal[240]
    attempted_request_count: Literal[240]
    http_completed_request_count: Literal[240]
    admitted_request_count: Literal[240]
    committed_request_count: Literal[240]
    failed_trajectory_count: Literal[0]
    finish_reason_stop_count: Literal[216]
    hidden_retry_count: Literal[0]
    replacement_case_count: Literal[0]
    output_admission_failure_count: Literal[0]
    prospective_reachable_budget_rejection_count: Literal[0]
    neutral_worker_qualification_decision: Literal["PASS"]
    neutral_worker_1_sample_count: Literal[10]
    neutral_worker_2_sample_count: Literal[10]
    maximum_worker_median_ttft_ratio: float = Field(ge=1.25, le=1.25)
    maximum_worker_median_prefill_ratio: float = Field(ge=1.25, le=1.25)
    observed_worker_median_ttft_ratio: float = Field(ge=1.0, le=1.25)
    observed_worker_median_prefill_ratio: float = Field(ge=1.0, le=1.25)
    bc_output_hash_comparison_count: Literal[72]
    bc_output_hash_match_count: Literal[72]
    affinity_pair_count: Literal[18]
    affinity_new_prefill_favorable_pair_count: Literal[18]
    affinity_prefill_duration_favorable_pair_count: Literal[18]
    affinity_ttft_favorable_pair_count: Literal[18]
    affinity_end_to_end_favorable_pair_count: Literal[18]
    worker_teardown_report_count: Literal[2]
    scratch_cleanup_status: Literal["PASSED"]
    primary_runtime_failure: Literal[False]
    external_network_requests: Literal[0]
    external_spend: Literal[0]
    customer_data_used: Literal[False]
    raw_prompts_retained: Literal[False]
    raw_outputs_retained: Literal[False]
    executed_notebook_papermill_exception: Literal[True]
    runtime_execution_outcome: Literal["PASSED"]


class ExpectedClassification(StrictModel):
    governed_execution_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    task_output_contract: Literal["PASSED"]
    worker_nuisance_control: Literal["QUALIFIED"]
    estimator_and_nuisance_controls_interpretable: Literal[True]
    pilot_acceptance_decision: Literal["ACCEPT"]
    pilot_repository_acceptance_established: Literal[True]
    repetition_freeze_permitted: Literal[True]
    repetition_freeze_established: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class ClassificationPolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal[
        "auragateway-measured-abc-variance-pilot-v2-345461230-classification-v1-policy"
    ]
    saved_version_id: Literal[345461230]
    transaction_id: Literal["4341cafac81245d433a680db0bc9c62ecabdbf1d279c0ddc0a19741eb44c7d8b"]
    issuer_merge_commit: Literal["563aa99958d75d3cf09eb83dc6ea3062e8308a90"]
    runtime_payload_sha256: Literal[
        "796c6cfc2fa615a5b28b4de013e3b2bea45c758cd96c039fe6464fce637b89ce"
    ]
    vault_path: str
    expected_hashes: dict[str, str]
    expected_zip_members: dict[str, str]
    expected_semantics: ExpectedSemantics
    expected_classification: ExpectedClassification

    @model_validator(mode="after")
    def validate_identity_sets(self) -> Self:
        if len(self.expected_hashes) != 7:
            raise ValueError("V2 preserved vault receipt count must be exactly seven")
        if len(self.expected_zip_members) != 32:
            raise ValueError("V2 governed evidence ZIP must contain exactly 32 members")
        expected_vault = "evidence_vault/local_abc/measured-abc-variance-pilot-v2-345461230-v1"
        if self.vault_path != expected_vault:
            raise ValueError("V2 evidence vault path drifted")
        return self


class ExecutionFinding(StrictModel):
    governed_execution_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"] = (
        "ACCEPTED_GOVERNED_EXECUTION_PASS"
    )
    scheduled_request_count: Literal[240] = 240
    attempted_request_count: Literal[240] = 240
    http_completed_request_count: Literal[240] = 240
    admitted_request_count: Literal[240] = 240
    committed_request_count: Literal[240] = 240
    hidden_retry_count: Literal[0] = 0
    replacement_case_count: Literal[0] = 0
    output_admission_failure_count: Literal[0] = 0
    primary_runtime_failure: Literal[False] = False
    worker_teardown_passed: Literal[True] = True
    scratch_cleanup_passed: Literal[True] = True


class TaskOutputFinding(StrictModel):
    scheduled_trajectory_count: Literal[54] = 54
    observed_trajectory_count: Literal[54] = 54
    failed_trajectory_count: Literal[0] = 0
    scheduled_turn_count: Literal[216] = 216
    completed_turn_count: Literal[216] = 216
    finish_reason_stop_count: Literal[216] = 216
    admitted_turn_count: Literal[216] = 216
    committed_turn_count: Literal[216] = 216
    task_output_contract: Literal["PASSED"] = "PASSED"


class WorkerNuisanceFinding(StrictModel):
    decision: Literal["PASS"] = "PASS"
    observed_sample_count: Literal[20] = 20
    worker_1_sample_count: Literal[10] = 10
    worker_2_sample_count: Literal[10] = 10
    worker_median_ttft_ratio: float = Field(ge=1.0, le=1.25)
    worker_median_prefill_ratio: float = Field(ge=1.0, le=1.25)
    maximum_worker_median_ttft_ratio: float = Field(default=1.25, ge=1.25, le=1.25)
    maximum_worker_median_prefill_ratio: float = Field(default=1.25, ge=1.25, le=1.25)
    global_orientation_1_pair_count: Literal[9] = 9
    global_orientation_2_pair_count: Literal[9] = 9
    each_replication_orientation_1_pair_count: Literal[3] = 3
    each_replication_orientation_2_pair_count: Literal[3] = 3
    each_case_observed_under_both_orientations: Literal[True] = True
    worker_nuisance_control: Literal["QUALIFIED"] = "QUALIFIED"
    estimator_and_nuisance_controls_interpretable: Literal[True] = True


class AffinityPilotFinding(StrictModel):
    matched_pair_count: Literal[18] = 18
    output_hash_comparison_count: Literal[72] = 72
    output_hash_match_count: Literal[72] = 72
    newly_computed_prefill_favorable_pair_count: Literal[18] = 18
    prefill_duration_favorable_pair_count: Literal[18] = 18
    ttft_favorable_pair_count: Literal[18] = 18
    end_to_end_favorable_pair_count: Literal[18] = 18
    mean_newly_computed_prefill_delta_c_minus_b: float
    mean_prefill_duration_ms_delta_c_minus_b: float
    mean_ttft_ms_delta_c_minus_b: float
    mean_end_to_end_latency_ms_delta_c_minus_b: float
    pilot_directional_signal_observed: Literal[True] = True
    final_affinity_effect_established: Literal[False] = False


class NotebookFinding(StrictModel):
    papermill_exception_metadata_observed: Literal[True] = True
    runtime_execution_outcome: Literal["PASSED"] = "PASSED"
    papermill_metadata_promoted_to_runtime_failure: Literal[False] = False


class PilotClassification(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    classification_id: Literal[
        "auragateway-measured-abc-variance-pilot-v2-345461230-classification-v1"
    ] = "auragateway-measured-abc-variance-pilot-v2-345461230-classification-v1"
    saved_version_id: Literal[345461230] = 345461230
    transaction_id: str
    issuer_merge_commit: str
    policy_sha256: Literal["540ae24a00e9af522c816f20e7d7d5dc93c487a7e31523ccfd640af459cb2b33"] = (
        POLICY_SHA256
    )
    evidence_zip_sha256: str
    terminal_log_sha256: str
    executed_notebook_sha256: str
    execution: ExecutionFinding
    task_output: TaskOutputFinding
    worker_nuisance: WorkerNuisanceFinding
    affinity_pilot: AffinityPilotFinding
    notebook: NotebookFinding
    pilot_acceptance_decision: Literal["ACCEPT"] = "ACCEPT"
    pilot_repository_acceptance_established: Literal[True] = True
    repetition_freeze_permitted: Literal[True] = True
    repetition_freeze_established: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    prefix_effect_established: Literal[False] = False
    affinity_effect_established: Literal[False] = False
    combined_effect_established: Literal[False] = False
    quality_noninferiority_established: Literal[False] = False
    production_readiness_established: Literal[False] = False
    raw_prompts_retained: Literal[False] = False
    raw_outputs_retained: Literal[False] = False
    customer_data_used: Literal[False] = False
    external_network_requests: Literal[0] = 0
    external_spend: Literal[0] = 0
    next_gate: str = NEXT_GATE


class PilotAcceptanceBoundary(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    boundary_id: Literal["auragateway-measured-abc-variance-pilot-v2-345461230-acceptance-v1"] = (
        "auragateway-measured-abc-variance-pilot-v2-345461230-acceptance-v1"
    )
    source_saved_version_id: Literal[345461230] = 345461230
    source_transaction_id: str
    source_classification_sha256: str
    governed_execution_evidence_accepted: Literal[True] = True
    task_output_contract_satisfied: Literal[True] = True
    worker_nuisance_control_qualified: Literal[True] = True
    estimator_and_nuisance_controls_interpretable: Literal[True] = True
    pilot_repository_acceptance_established: Literal[True] = True
    repetition_freeze_permitted: Literal[True] = True
    repetition_freeze_established: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    effect_claims_permitted: Literal[False] = False
    next_gate: str = NEXT_GATE


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ClassificationError(
            "V2_PILOT_CLASSIFICATION_ARGUMENT_INVALID",
            "V2 pilot classification arguments are invalid",
            details=(message,),
        )


def _error(
    code: str,
    message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise ClassificationError(
        code,
        message,
        None if path is None else path.as_posix(),
        details,
    )


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _canonical_bytes(value: BaseModel | dict[str, object]) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _read_json(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_bytes())
    except (FileNotFoundError, json.JSONDecodeError) as error:
        _error(
            "V2_PILOT_CLASSIFICATION_JSON_INVALID",
            "required governed JSON evidence is missing or invalid",
            path,
            (type(error).__name__,),
        )
    if not isinstance(value, dict):
        _error(
            "V2_PILOT_CLASSIFICATION_JSON_INVALID",
            "required governed JSON evidence root is invalid",
            path,
        )
    return cast(dict[str, object], value)


def _require_equal(
    observed: object,
    expected: object,
    code: str,
    message: str,
) -> None:
    if observed != expected:
        _error(
            code,
            message,
            details=(f"expected={expected!r}", f"observed={observed!r}"),
        )


def _require_close(observed: object, expected: float, message: str) -> float:
    if not isinstance(observed, (int, float)) or isinstance(observed, bool):
        _error("V2_PILOT_CLASSIFICATION_METRIC_INVALID", message)
    value = float(observed)
    if not math.isclose(value, expected, rel_tol=0.0, abs_tol=1e-12):
        _error(
            "V2_PILOT_CLASSIFICATION_METRIC_DRIFT",
            message,
            details=(f"expected={expected!r}", f"observed={value!r}"),
        )
    return value


def _load_policy(repo_root: Path) -> ClassificationPolicy:
    path = repo_root / POLICY_PATH
    if not path.is_file() or _sha256_file(path) != POLICY_SHA256:
        _error(
            "V2_PILOT_CLASSIFICATION_POLICY_DRIFT",
            "V2 pilot classification policy identity drifted",
            POLICY_PATH,
        )
    try:
        return ClassificationPolicy.model_validate_json(path.read_bytes())
    except ValidationError as error:
        _error(
            "V2_PILOT_CLASSIFICATION_POLICY_INVALID",
            "V2 pilot classification policy failed typed validation",
            POLICY_PATH,
            tuple(item["msg"] for item in error.errors(include_url=False)),
        )


def _validate_runtime_identity(repo_root: Path, policy: ClassificationPolicy) -> None:
    runtime = repo_root / RUNTIME_PATH
    if not runtime.is_file() or runtime.is_symlink():
        _error(
            "V2_PILOT_CLASSIFICATION_RUNTIME_MISSING",
            "bound V2 transaction runtime source is missing or unsafe",
            RUNTIME_PATH,
        )
    if _sha256_file(runtime) != policy.runtime_payload_sha256:
        _error(
            "V2_PILOT_CLASSIFICATION_RUNTIME_DRIFT",
            "bound V2 transaction runtime source identity drifted",
            RUNTIME_PATH,
        )


def _validate_vault(repo_root: Path, policy: ClassificationPolicy) -> Path:
    vault = repo_root / policy.vault_path
    for relative, expected_sha in policy.expected_hashes.items():
        path = vault / relative
        if not path.is_file() or path.is_symlink():
            _error(
                "V2_PILOT_CLASSIFICATION_EVIDENCE_MISSING",
                "governed V2 pilot evidence file is missing or unsafe",
                path,
            )
        observed_sha = _sha256_file(path)
        if observed_sha != expected_sha:
            _error(
                "V2_PILOT_CLASSIFICATION_EVIDENCE_DRIFT",
                "governed V2 pilot evidence identity drifted",
                path,
                (f"expected={expected_sha}", f"observed={observed_sha}"),
            )
    return vault


def _validate_lifecycle(vault: Path, policy: ClassificationPolicy) -> None:
    live = _read_json(vault / "lifecycle/authorization_live.json")
    manifest = _read_json(vault / "lifecycle/artifact_live_manifest.json")
    observation = _read_json(vault / "lifecycle/platform_observation_live.json")
    terminal = _read_json(vault / "lifecycle/authorization_terminal.json")

    for payload in (live, manifest, observation, terminal):
        _require_equal(
            payload.get("transaction_id"),
            policy.transaction_id,
            "V2_PILOT_CLASSIFICATION_TRANSACTION_DRIFT",
            "V2 lifecycle transaction identity drifted",
        )

    authorization = live.get("authorization")
    if not isinstance(authorization, dict):
        _error(
            "V2_PILOT_CLASSIFICATION_AUTHORIZATION_INVALID",
            "preserved V2 live authorization payload is invalid",
        )
    required_authorization = {
        "decision": "AUTHORIZED",
        "lifecycle": "ISSUED",
        "issuer_merge_commit": policy.issuer_merge_commit,
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "single_use": True,
        "authorization_reusable": False,
        "unchanged_replay_authorized": False,
        "runtime_anti_replay_established": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
    }
    for key, expected in required_authorization.items():
        _require_equal(
            authorization.get(key),
            expected,
            "V2_PILOT_CLASSIFICATION_AUTHORIZATION_INVALID",
            f"V2 authorization field {key} drifted",
        )

    required_manifest = {
        "status": "V2_TRANSACTION_BOUND_EXECUTABLE_GENERATED",
        "issuer_merge_commit": policy.issuer_merge_commit,
        "pilot_execution_authorized": True,
        "final_measured_abc_execution_authorized": False,
        "single_use_governance": True,
        "runtime_anti_replay_established": False,
        "authorization_specific_kaggle_inputs": 0,
        "authorization_producer_notebooks": 0,
        "manual_confirmation_json_files": 0,
        "platform_observation_required_before_save_and_run_all": True,
        "platform_observation_persisted": False,
    }
    for key, expected in required_manifest.items():
        _require_equal(
            manifest.get(key),
            expected,
            "V2_PILOT_CLASSIFICATION_MANIFEST_INVALID",
            f"V2 live manifest field {key} drifted",
        )

    required_observation = {
        "accelerator": "T4_X2",
        "allocated_gpu_count": 2,
        "internet_enabled": False,
        "wheelhouse_input_count": 1,
        "model_snapshot_input_count": 1,
        "authorization_specific_kaggle_input_count": 0,
        "capability_source": "KAGGLE_NOTEBOOK_SETTINGS_UI",
        "persisted_before_save_and_run_all": True,
        "receipt_runtime_input": False,
    }
    for key, expected in required_observation.items():
        _require_equal(
            observation.get(key),
            expected,
            "V2_PILOT_CLASSIFICATION_PLATFORM_INVALID",
            f"V2 platform observation field {key} drifted",
        )

    expected_evidence_sha = policy.expected_hashes[
        "raw_kaggle/ag-variance-pilot-v2-tx-v1-evidence.zip"
    ]
    expected_log_sha = policy.expected_hashes["raw_kaggle/ag-v2-variance-pilot-tx-bound-v1.log"]
    required_terminal = {
        "saved_version_id": policy.saved_version_id,
        "disposition": "CONSUMED",
        "execution_attempted": True,
        "execution_outcome": "PASSED",
        "evidence_zip_sha256": expected_evidence_sha,
        "terminal_log_sha256": expected_log_sha,
        "authorization_reusable": False,
        "pilot_execution_authorized": False,
        "pilot_repository_acceptance_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
    }
    for key, expected in required_terminal.items():
        _require_equal(
            terminal.get(key),
            expected,
            "V2_PILOT_CLASSIFICATION_TERMINAL_INVALID",
            f"V2 terminal lifecycle field {key} drifted",
        )


def _safe_zip_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def _read_evidence_zip(
    zip_path: Path,
    policy: ClassificationPolicy,
) -> dict[str, dict[str, object]]:
    expected_names = set(policy.expected_zip_members)
    payloads: dict[str, dict[str, object]] = {}
    try:
        with zipfile.ZipFile(zip_path) as archive:
            infos = archive.infolist()
            names = [item.filename for item in infos]
            if len(names) != len(set(names)):
                _error(
                    "V2_PILOT_CLASSIFICATION_ZIP_DUPLICATE_MEMBER",
                    "V2 evidence ZIP contains duplicate member names",
                    zip_path,
                )
            if len(names) != policy.expected_semantics.zip_member_count:
                _error(
                    "V2_PILOT_CLASSIFICATION_ZIP_MEMBER_COUNT",
                    "V2 evidence ZIP member count drifted",
                    zip_path,
                )
            if set(names) != expected_names:
                _error(
                    "V2_PILOT_CLASSIFICATION_ZIP_MEMBER_SET",
                    "V2 evidence ZIP member set drifted",
                    zip_path,
                    tuple(sorted(set(names) ^ expected_names)),
                )
            for info in infos:
                if info.is_dir() or not _safe_zip_name(info.filename):
                    _error(
                        "V2_PILOT_CLASSIFICATION_ZIP_PATH_INVALID",
                        "V2 evidence ZIP member path is invalid",
                        zip_path,
                        (info.filename,),
                    )
                raw = archive.read(info)
                expected_sha = policy.expected_zip_members[info.filename]
                observed_sha = _sha256_bytes(raw)
                if observed_sha != expected_sha:
                    _error(
                        "V2_PILOT_CLASSIFICATION_ZIP_MEMBER_DRIFT",
                        "V2 evidence ZIP member identity drifted",
                        zip_path,
                        (
                            info.filename,
                            f"expected={expected_sha}",
                            f"observed={observed_sha}",
                        ),
                    )
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError as error:
                    _error(
                        "V2_PILOT_CLASSIFICATION_ZIP_JSON_INVALID",
                        "V2 evidence ZIP member is not valid JSON",
                        zip_path,
                        (info.filename, type(error).__name__),
                    )
                if not isinstance(value, dict):
                    _error(
                        "V2_PILOT_CLASSIFICATION_ZIP_JSON_INVALID",
                        "V2 evidence ZIP member root is invalid",
                        zip_path,
                        (info.filename,),
                    )
                payloads[info.filename] = cast(dict[str, object], value)
    except zipfile.BadZipFile as error:
        _error(
            "V2_PILOT_CLASSIFICATION_ZIP_INVALID",
            "V2 evidence ZIP is invalid",
            zip_path,
            (type(error).__name__,),
        )
    return payloads


def _validate_bundle(
    payloads: dict[str, dict[str, object]],
    policy: ClassificationPolicy,
) -> None:
    bundle = payloads["bundle_manifest_v1.json"]
    _require_equal(
        bundle.get("member_count"),
        policy.expected_semantics.bundle_manifest_member_count,
        "V2_PILOT_CLASSIFICATION_BUNDLE_INVALID",
        "V2 bundle manifest member count drifted",
    )
    _require_equal(
        bundle.get("transaction_id"),
        policy.transaction_id,
        "V2_PILOT_CLASSIFICATION_BUNDLE_INVALID",
        "V2 bundle transaction identity drifted",
    )
    _require_equal(
        bundle.get("runtime_payload_sha256"),
        policy.runtime_payload_sha256,
        "V2_PILOT_CLASSIFICATION_RUNTIME_DRIFT",
        "V2 bundle runtime payload identity drifted",
    )
    for key in (
        "raw_prompts_included",
        "raw_outputs_included",
        "raw_source_documents_included",
        "credentials_included",
    ):
        _require_equal(
            bundle.get(key),
            False,
            "V2_PILOT_CLASSIFICATION_BUNDLE_INVALID",
            f"V2 bundle privacy field {key} drifted",
        )
    members = bundle.get("members")
    if not isinstance(members, list):
        _error(
            "V2_PILOT_CLASSIFICATION_BUNDLE_INVALID",
            "V2 bundle member receipt set is invalid",
        )
    observed: dict[str, str] = {}
    for raw in members:
        if not isinstance(raw, dict):
            _error(
                "V2_PILOT_CLASSIFICATION_BUNDLE_INVALID",
                "V2 bundle member receipt is invalid",
            )
        path = raw.get("path")
        sha = raw.get("sha256")
        if not isinstance(path, str) or not isinstance(sha, str):
            _error(
                "V2_PILOT_CLASSIFICATION_BUNDLE_INVALID",
                "V2 bundle member identity is invalid",
            )
        observed[path] = sha
    expected = {
        name: sha
        for name, sha in policy.expected_zip_members.items()
        if name != "bundle_manifest_v1.json"
    }
    if observed != expected:
        _error(
            "V2_PILOT_CLASSIFICATION_BUNDLE_DRIFT",
            "V2 bundle member manifest does not match frozen ZIP member identities",
        )


def _validate_terminal_log(vault: Path, policy: ClassificationPolicy) -> None:
    path = vault / "raw_kaggle/ag-v2-variance-pilot-tx-bound-v1.log"
    text = path.read_text(encoding="utf-8")
    required = (
        "EVIDENCE_ZIP_SHA256="
        + policy.expected_hashes["raw_kaggle/ag-variance-pilot-v2-tx-v1-evidence.zip"],
        f"TRANSACTION_ID={policy.transaction_id}",
        "EXECUTION_OUTCOME=PASSED",
    )
    for marker in required:
        if marker not in text:
            _error(
                "V2_PILOT_CLASSIFICATION_TERMINAL_LOG_INVALID",
                "required V2 terminal marker is absent",
                path,
                (marker,),
            )


def _validate_notebook(vault: Path, policy: ClassificationPolicy) -> NotebookFinding:
    notebook = _read_json(vault / "raw_kaggle/ag-v2-variance-pilot-tx-bound-v1.ipynb")
    metadata = notebook.get("metadata")
    if not isinstance(metadata, dict):
        _error(
            "V2_PILOT_CLASSIFICATION_NOTEBOOK_INVALID",
            "executed notebook metadata is invalid",
        )
    papermill = metadata.get("papermill")
    if not isinstance(papermill, dict):
        _error(
            "V2_PILOT_CLASSIFICATION_NOTEBOOK_INVALID",
            "executed notebook Papermill metadata is missing",
        )
    _require_equal(
        papermill.get("exception"),
        policy.expected_semantics.executed_notebook_papermill_exception,
        "V2_PILOT_CLASSIFICATION_NOTEBOOK_METADATA_DRIFT",
        "executed notebook Papermill exception metadata drifted",
    )
    return NotebookFinding()


def _execution_finding(
    payloads: dict[str, dict[str, object]],
    policy: ClassificationPolicy,
) -> ExecutionFinding:
    expected = policy.expected_semantics
    runtime_binding = payloads["runtime_binding_report_v1.json"]
    reconciliation = payloads["request_reconciliation_v1.json"]
    summary = payloads["runtime_summary_v1.json"]
    failure = payloads["failure_report_v1.json"]
    teardown = payloads["worker_teardown_report_v1.json"]
    cleanup = payloads["scratch_cleanup_report_v1.json"]

    _require_equal(
        runtime_binding.get("transaction_id"),
        policy.transaction_id,
        "V2_PILOT_CLASSIFICATION_RUNTIME_BINDING_INVALID",
        "V2 runtime-binding transaction identity drifted",
    )
    _require_equal(
        runtime_binding.get("runtime_payload_sha256"),
        policy.runtime_payload_sha256,
        "V2_PILOT_CLASSIFICATION_RUNTIME_DRIFT",
        "V2 runtime-binding payload identity drifted",
    )
    _require_equal(
        runtime_binding.get("request_budget"),
        expected.total_model_request_count,
        "V2_PILOT_CLASSIFICATION_BUDGET_INVALID",
        "V2 request budget drifted",
    )
    _require_equal(
        runtime_binding.get("max_output_tokens"),
        256,
        "V2_PILOT_CLASSIFICATION_BUDGET_INVALID",
        "V2 max-output-token budget drifted",
    )
    _require_equal(
        runtime_binding.get("hidden_retry_count"),
        0,
        "V2_PILOT_CLASSIFICATION_RETRY_INVALID",
        "V2 runtime binding reports hidden retries",
    )
    _require_equal(
        runtime_binding.get("replacement_case_count"),
        0,
        "V2_PILOT_CLASSIFICATION_REPLACEMENT_INVALID",
        "V2 runtime binding reports replacement cases",
    )

    reconciliation_fields: dict[str, object] = {
        "scheduled_request_count": expected.total_model_request_count,
        "attempted_request_count": expected.attempted_request_count,
        "http_completed_request_count": expected.http_completed_request_count,
        "admitted_request_count": expected.admitted_request_count,
        "committed_request_count": expected.committed_request_count,
        "hidden_retry_count": expected.hidden_retry_count,
        "replacement_case_count": expected.replacement_case_count,
        "output_admission_failure_count": expected.output_admission_failure_count,
        "prospective_reachable_budget_rejection_count": (
            expected.prospective_reachable_budget_rejection_count
        ),
        "monotonic_invariant_satisfied": True,
    }
    for key, value in reconciliation_fields.items():
        _require_equal(
            reconciliation.get(key),
            value,
            "V2_PILOT_CLASSIFICATION_RECONCILIATION_INVALID",
            f"V2 request reconciliation field {key} drifted",
        )

    summary_fields: dict[str, object] = {
        "status": "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
        "transaction_id": policy.transaction_id,
        "pretreatment_qualification": "PASS",
        "scheduled_trajectory_count": expected.scheduled_trajectory_count,
        "observed_trajectory_count": expected.scheduled_trajectory_count,
        "failed_trajectory_count": expected.failed_trajectory_count,
        "pilot_execution_authorized_at_runtime": True,
        "pilot_repository_acceptance_established": False,
        "final_measured_abc_execution_authorized": False,
        "effect_claims_permitted": False,
        "raw_prompts_retained": False,
        "raw_outputs_retained": False,
        "customer_data_used": expected.customer_data_used,
        "external_network_requests": expected.external_network_requests,
        "external_spend": expected.external_spend,
    }
    for key, value in summary_fields.items():
        _require_equal(
            summary.get(key),
            value,
            "V2_PILOT_CLASSIFICATION_RUNTIME_SUMMARY_INVALID",
            f"V2 runtime-summary field {key} drifted",
        )

    _require_equal(
        failure.get("status"),
        "NO_PRIMARY_RUNTIME_FAILURE",
        "V2_PILOT_CLASSIFICATION_RUNTIME_FAILURE",
        "V2 runtime reported a primary or cleanup failure",
    )
    _require_equal(
        failure.get("primary_failure"),
        expected.primary_runtime_failure,
        "V2_PILOT_CLASSIFICATION_RUNTIME_FAILURE",
        "V2 primary runtime failure state drifted",
    )
    _require_equal(
        failure.get("cleanup_failure"),
        False,
        "V2_PILOT_CLASSIFICATION_CLEANUP_FAILURE",
        "V2 cleanup failure state drifted",
    )

    _require_equal(
        teardown.get("worker_report_count"),
        expected.worker_teardown_report_count,
        "V2_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
        "V2 worker teardown report count drifted",
    )
    _require_equal(
        teardown.get("teardown_errors"),
        [],
        "V2_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
        "V2 worker teardown errors were observed",
    )
    reports = teardown.get("reports")
    if not isinstance(reports, list) or len(reports) != 2:
        _error(
            "V2_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
            "V2 worker teardown report set is invalid",
        )
    if any(not isinstance(item, dict) or item.get("status") != "PASSED" for item in reports):
        _error(
            "V2_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
            "V2 worker teardown did not pass for every worker",
        )

    _require_equal(
        cleanup.get("status"),
        expected.scratch_cleanup_status,
        "V2_PILOT_CLASSIFICATION_CLEANUP_INVALID",
        "V2 scratch cleanup status drifted",
    )
    _require_equal(
        cleanup.get("scratch_exists_after"),
        False,
        "V2_PILOT_CLASSIFICATION_CLEANUP_INVALID",
        "V2 scratch workspace remained after cleanup",
    )
    return ExecutionFinding()


def _task_and_worker_findings(
    payloads: dict[str, dict[str, object]],
    policy: ClassificationPolicy,
) -> tuple[TaskOutputFinding, WorkerNuisanceFinding]:
    expected = policy.expected_semantics
    pretreatment = payloads["pretreatment_ledger_v1.json"]
    neutral = payloads["neutral_worker_qualification_v1.json"]
    pilot = payloads["pilot_trajectory_ledger_v1.json"]

    _require_equal(
        pretreatment.get("attempted_request_count"),
        expected.pretreatment_request_count,
        "V2_PILOT_CLASSIFICATION_PRETREATMENT_INVALID",
        "V2 pretreatment attempt count drifted",
    )
    _require_equal(
        pretreatment.get("admitted_request_count"),
        expected.pretreatment_request_count,
        "V2_PILOT_CLASSIFICATION_PRETREATMENT_INVALID",
        "V2 pretreatment admission count drifted",
    )
    _require_equal(
        pretreatment.get("qualification_decision"),
        "PASS",
        "V2_PILOT_CLASSIFICATION_PRETREATMENT_INVALID",
        "V2 pretreatment qualification did not pass",
    )

    neutral_fields = {
        "decision": expected.neutral_worker_qualification_decision,
        "observed_sample_count": 20,
        "worker_1_sample_count": expected.neutral_worker_1_sample_count,
        "worker_2_sample_count": expected.neutral_worker_2_sample_count,
        "blocking_reasons": [],
    }
    for key, value in neutral_fields.items():
        _require_equal(
            neutral.get(key),
            value,
            "V2_PILOT_CLASSIFICATION_NEUTRAL_WORKER_INVALID",
            f"V2 neutral worker field {key} drifted",
        )
    ttft_ratio = _require_close(
        neutral.get("worker_median_ttft_ratio"),
        expected.observed_worker_median_ttft_ratio,
        "V2 neutral worker median TTFT ratio drifted",
    )
    prefill_ratio = _require_close(
        neutral.get("worker_median_prefill_ratio"),
        expected.observed_worker_median_prefill_ratio,
        "V2 neutral worker median prefill ratio drifted",
    )
    if ttft_ratio > expected.maximum_worker_median_ttft_ratio:
        _error(
            "V2_PILOT_CLASSIFICATION_NEUTRAL_WORKER_ASYMMETRY",
            "V2 neutral TTFT asymmetry exceeded the frozen threshold",
        )
    if prefill_ratio > expected.maximum_worker_median_prefill_ratio:
        _error(
            "V2_PILOT_CLASSIFICATION_NEUTRAL_WORKER_ASYMMETRY",
            "V2 neutral prefill asymmetry exceeded the frozen threshold",
        )

    trajectories_raw = pilot.get("trajectories")
    if not isinstance(trajectories_raw, list):
        _error(
            "V2_PILOT_CLASSIFICATION_LEDGER_INVALID",
            "V2 pilot trajectory set is invalid",
        )
    trajectories = [
        cast(dict[str, object], item) for item in trajectories_raw if isinstance(item, dict)
    ]
    if len(trajectories) != len(trajectories_raw):
        _error(
            "V2_PILOT_CLASSIFICATION_LEDGER_INVALID",
            "V2 pilot trajectory row is invalid",
        )
    _require_equal(
        len(trajectories),
        expected.scheduled_trajectory_count,
        "V2_PILOT_CLASSIFICATION_LEDGER_INVALID",
        "V2 pilot trajectory count drifted",
    )

    total_turns = 0
    admitted_turns = 0
    committed_turns = 0
    finish_stop = 0
    failed_trajectories = 0
    attempt_sequences: list[int] = []
    pair_rows: dict[int, list[dict[str, object]]] = defaultdict(list)

    for trajectory in trajectories:
        _require_equal(
            trajectory.get("scheduled_turn_count"),
            4,
            "V2_PILOT_CLASSIFICATION_TRAJECTORY_INVALID",
            "V2 trajectory scheduled-turn count drifted",
        )
        for key in (
            "attempted_request_count",
            "http_completed_request_count",
            "admitted_request_count",
            "committed_turn_count",
        ):
            _require_equal(
                trajectory.get(key),
                4,
                "V2_PILOT_CLASSIFICATION_TRAJECTORY_INVALID",
                f"V2 trajectory field {key} drifted",
            )
        if trajectory.get("trajectory_failed") is True:
            failed_trajectories += 1
        _require_equal(
            trajectory.get("failure_code"),
            None,
            "V2_PILOT_CLASSIFICATION_TRAJECTORY_INVALID",
            "V2 trajectory failure code was observed",
        )
        _require_equal(
            trajectory.get("raw_prompts_retained"),
            False,
            "V2_PILOT_CLASSIFICATION_PRIVACY_INVALID",
            "V2 trajectory retained raw prompts",
        )
        _require_equal(
            trajectory.get("raw_outputs_retained"),
            False,
            "V2_PILOT_CLASSIFICATION_PRIVACY_INVALID",
            "V2 trajectory retained raw outputs",
        )
        pair_index = trajectory.get("comparison_pair_index")
        if not isinstance(pair_index, int) or isinstance(pair_index, bool):
            _error(
                "V2_PILOT_CLASSIFICATION_PAIR_INVALID",
                "V2 comparison pair index is invalid",
            )
        pair_rows[pair_index].append(trajectory)
        turns = trajectory.get("turns")
        if not isinstance(turns, list) or len(turns) != 4:
            _error(
                "V2_PILOT_CLASSIFICATION_TRAJECTORY_INVALID",
                "V2 trajectory turn set is invalid",
            )
        for turn in turns:
            if not isinstance(turn, dict):
                _error(
                    "V2_PILOT_CLASSIFICATION_TURN_INVALID",
                    "V2 pilot turn row is invalid",
                )
            total_turns += 1
            if turn.get("admitted") is True:
                admitted_turns += 1
            if turn.get("committed") is True:
                committed_turns += 1
            if turn.get("finish_reason") == "stop":
                finish_stop += 1
            _require_equal(
                turn.get("http_completed"),
                True,
                "V2_PILOT_CLASSIFICATION_TURN_INVALID",
                "V2 pilot turn did not complete HTTP transport",
            )
            _require_equal(
                turn.get("failure_code"),
                None,
                "V2_PILOT_CLASSIFICATION_TURN_INVALID",
                "V2 pilot turn failure code was observed",
            )
            _require_equal(
                turn.get("raw_prompt_retained"),
                False,
                "V2_PILOT_CLASSIFICATION_PRIVACY_INVALID",
                "V2 pilot turn retained a raw prompt",
            )
            _require_equal(
                turn.get("raw_output_retained"),
                False,
                "V2_PILOT_CLASSIFICATION_PRIVACY_INVALID",
                "V2 pilot turn retained a raw output",
            )
            sequence = turn.get("attempt_sequence")
            if not isinstance(sequence, int) or isinstance(sequence, bool):
                _error(
                    "V2_PILOT_CLASSIFICATION_SEQUENCE_INVALID",
                    "V2 pilot attempt sequence is invalid",
                )
            attempt_sequences.append(sequence)

    _require_equal(
        failed_trajectories,
        expected.failed_trajectory_count,
        "V2_PILOT_CLASSIFICATION_TASK_CONTRACT_FAILED",
        "V2 pilot contains failed trajectories",
    )
    _require_equal(
        total_turns,
        expected.scheduled_turn_count,
        "V2_PILOT_CLASSIFICATION_TASK_CONTRACT_FAILED",
        "V2 pilot turn count drifted",
    )
    _require_equal(
        admitted_turns,
        expected.scheduled_turn_count,
        "V2_PILOT_CLASSIFICATION_TASK_CONTRACT_FAILED",
        "V2 pilot did not admit every turn",
    )
    _require_equal(
        committed_turns,
        expected.scheduled_turn_count,
        "V2_PILOT_CLASSIFICATION_TASK_CONTRACT_FAILED",
        "V2 pilot did not commit every turn",
    )
    _require_equal(
        finish_stop,
        expected.finish_reason_stop_count,
        "V2_PILOT_CLASSIFICATION_TASK_CONTRACT_FAILED",
        "V2 pilot finish-reason contract drifted",
    )
    _require_equal(
        sorted(attempt_sequences),
        list(range(25, 241)),
        "V2_PILOT_CLASSIFICATION_SEQUENCE_INVALID",
        "V2 pilot request attempt sequence is incomplete or duplicated",
    )

    orientation_counts: Counter[str] = Counter()
    replication_orientation: dict[str, Counter[str]] = defaultdict(Counter)
    case_orientations: dict[str, set[str]] = defaultdict(set)
    expected_orders = {
        "pilot-v2-r01": ["A", "B", "C"],
        "pilot-v2-r02": ["B", "C", "A"],
        "pilot-v2-r03": ["C", "A", "B"],
    }
    if set(pair_rows) != set(range(18)):
        _error(
            "V2_PILOT_CLASSIFICATION_PAIR_INVALID",
            "V2 comparison pair index set drifted",
        )
    for rows in pair_rows.values():
        if len(rows) != 3:
            _error(
                "V2_PILOT_CLASSIFICATION_PAIR_INVALID",
                "V2 comparison pair does not contain exactly three conditions",
            )
        rows = sorted(rows, key=lambda item: cast(int, item["schedule_index"]))
        conditions = [cast(str, item.get("condition_id")) for item in rows]
        replications = {item.get("pilot_replication_id") for item in rows}
        orientations = {item.get("worker_orientation") for item in rows}
        episodes = {item.get("episode_id") for item in rows}
        pair_ids = {item.get("comparison_pair_id") for item in rows}
        if len(replications) != 1 or len(orientations) != 1 or len(episodes) != 1:
            _error(
                "V2_PILOT_CLASSIFICATION_PAIR_INVALID",
                "V2 matched-pair nuisance identities drifted",
            )
        if len(pair_ids) != 1:
            _error(
                "V2_PILOT_CLASSIFICATION_PAIR_INVALID",
                "V2 comparison-pair identity drifted",
            )
        replication = cast(str, next(iter(replications)))
        orientation = cast(str, next(iter(orientations)))
        episode = cast(str, next(iter(episodes)))
        if conditions != expected_orders.get(replication):
            _error(
                "V2_PILOT_CLASSIFICATION_ORDER_INVALID",
                "V2 condition-order counterbalancing drifted",
            )
        if orientation not in {"orientation_1", "orientation_2"}:
            _error(
                "V2_PILOT_CLASSIFICATION_ORIENTATION_INVALID",
                "V2 worker orientation is invalid",
            )
        orientation_counts[orientation] += 1
        replication_orientation[replication][orientation] += 1
        case_orientations[episode].add(orientation)

    _require_equal(
        orientation_counts,
        Counter({"orientation_1": 9, "orientation_2": 9}),
        "V2_PILOT_CLASSIFICATION_ORIENTATION_INVALID",
        "V2 global worker-orientation balance drifted",
    )
    for replication in expected_orders:
        _require_equal(
            replication_orientation[replication],
            Counter({"orientation_1": 3, "orientation_2": 3}),
            "V2_PILOT_CLASSIFICATION_ORIENTATION_INVALID",
            "V2 per-replication worker-orientation balance drifted",
        )
    if len(case_orientations) != 6 or any(
        values != {"orientation_1", "orientation_2"} for values in case_orientations.values()
    ):
        _error(
            "V2_PILOT_CLASSIFICATION_ORIENTATION_INVALID",
            "V2 cases do not each observe both worker orientations",
        )

    return (
        TaskOutputFinding(
            completed_turn_count=total_turns,
            admitted_turn_count=admitted_turns,
            committed_turn_count=committed_turns,
        ),
        WorkerNuisanceFinding(
            worker_median_ttft_ratio=ttft_ratio,
            worker_median_prefill_ratio=prefill_ratio,
        ),
    )


def _metric_sum(row: dict[str, object], field: str) -> float:
    turns = row.get("turns")
    if not isinstance(turns, list):
        _error(
            "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
            "V2 affinity comparison turn set is invalid",
        )
    total = 0.0
    for turn in turns:
        if not isinstance(turn, dict):
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 affinity comparison turn row is invalid",
            )
        value = turn.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                f"V2 affinity metric is invalid: {field}",
            )
        total += float(value)
    return total


def _affinity_finding(
    payloads: dict[str, dict[str, object]],
    policy: ClassificationPolicy,
) -> AffinityPilotFinding:
    expected = policy.expected_semantics
    pilot = payloads["pilot_trajectory_ledger_v1.json"]
    rows_raw = pilot.get("trajectories")
    if not isinstance(rows_raw, list):
        _error(
            "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
            "V2 affinity trajectory set is invalid",
        )
    pairs: dict[int, dict[str, dict[str, object]]] = defaultdict(dict)
    for raw in rows_raw:
        if not isinstance(raw, dict):
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 affinity trajectory row is invalid",
            )
        pair_index = raw.get("comparison_pair_index")
        condition = raw.get("condition_id")
        if not isinstance(pair_index, int) or isinstance(pair_index, bool):
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 affinity comparison-pair index is invalid",
            )
        if condition not in {"A", "B", "C"}:
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 affinity condition identity is invalid",
            )
        pairs[pair_index][cast(str, condition)] = cast(dict[str, object], raw)

    output_comparisons = 0
    output_matches = 0
    favorable_new_prefill = 0
    favorable_prefill = 0
    favorable_ttft = 0
    favorable_e2e = 0
    new_prefill_deltas: list[float] = []
    prefill_deltas: list[float] = []
    ttft_deltas: list[float] = []
    e2e_deltas: list[float] = []

    for pair_index in range(expected.affinity_pair_count):
        conditions = pairs.get(pair_index)
        if conditions is None or set(conditions) != {"A", "B", "C"}:
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 affinity comparison pair is incomplete",
            )
        b_row = conditions["B"]
        c_row = conditions["C"]
        b_turns = b_row.get("turns")
        c_turns = c_row.get("turns")
        if not isinstance(b_turns, list) or not isinstance(c_turns, list):
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 B/C turn set is invalid",
            )
        if len(b_turns) != 4 or len(c_turns) != 4:
            _error(
                "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                "V2 B/C turn set must contain four turns per condition",
            )
        for b_turn, c_turn in zip(b_turns, c_turns, strict=True):
            if not isinstance(b_turn, dict) or not isinstance(c_turn, dict):
                _error(
                    "V2_PILOT_CLASSIFICATION_AFFINITY_INVALID",
                    "V2 B/C turn row is invalid",
                )
            output_comparisons += 1
            if b_turn.get("output_sha256") == c_turn.get("output_sha256"):
                output_matches += 1

        metric_fields = (
            "newly_computed_prefill_tokens",
            "prefill_duration_ms",
            "time_to_first_token_ms",
            "end_to_end_latency_ms",
        )
        deltas = {
            field: _metric_sum(c_row, field) - _metric_sum(b_row, field) for field in metric_fields
        }
        new_prefill_deltas.append(deltas["newly_computed_prefill_tokens"])
        prefill_deltas.append(deltas["prefill_duration_ms"])
        ttft_deltas.append(deltas["time_to_first_token_ms"])
        e2e_deltas.append(deltas["end_to_end_latency_ms"])
        favorable_new_prefill += deltas["newly_computed_prefill_tokens"] < 0
        favorable_prefill += deltas["prefill_duration_ms"] < 0
        favorable_ttft += deltas["time_to_first_token_ms"] < 0
        favorable_e2e += deltas["end_to_end_latency_ms"] < 0

    observed = {
        "bc_output_hash_comparison_count": output_comparisons,
        "bc_output_hash_match_count": output_matches,
        "affinity_new_prefill_favorable_pair_count": favorable_new_prefill,
        "affinity_prefill_duration_favorable_pair_count": favorable_prefill,
        "affinity_ttft_favorable_pair_count": favorable_ttft,
        "affinity_end_to_end_favorable_pair_count": favorable_e2e,
    }
    for key, value in observed.items():
        _require_equal(
            value,
            getattr(expected, key),
            "V2_PILOT_CLASSIFICATION_AFFINITY_DRIFT",
            f"V2 pilot affinity finding {key} drifted",
        )

    return AffinityPilotFinding(
        mean_newly_computed_prefill_delta_c_minus_b=(
            sum(new_prefill_deltas) / len(new_prefill_deltas)
        ),
        mean_prefill_duration_ms_delta_c_minus_b=sum(prefill_deltas) / len(prefill_deltas),
        mean_ttft_ms_delta_c_minus_b=sum(ttft_deltas) / len(ttft_deltas),
        mean_end_to_end_latency_ms_delta_c_minus_b=sum(e2e_deltas) / len(e2e_deltas),
    )


def build_classification(repo_root: Path) -> PilotClassification:
    root = repo_root.resolve()
    policy = _load_policy(root)
    _validate_runtime_identity(root, policy)
    vault = _validate_vault(root, policy)
    _validate_lifecycle(vault, policy)
    _validate_terminal_log(vault, policy)
    notebook = _validate_notebook(vault, policy)
    zip_path = vault / "raw_kaggle/ag-variance-pilot-v2-tx-v1-evidence.zip"
    payloads = _read_evidence_zip(zip_path, policy)
    _validate_bundle(payloads, policy)
    execution = _execution_finding(payloads, policy)
    task, worker = _task_and_worker_findings(payloads, policy)
    affinity = _affinity_finding(payloads, policy)

    expected = policy.expected_classification
    observed_contract = {
        "governed_execution_disposition": execution.governed_execution_disposition,
        "task_output_contract": task.task_output_contract,
        "worker_nuisance_control": worker.worker_nuisance_control,
        "estimator_and_nuisance_controls_interpretable": (
            worker.estimator_and_nuisance_controls_interpretable
        ),
        "pilot_acceptance_decision": "ACCEPT",
        "pilot_repository_acceptance_established": True,
        "repetition_freeze_permitted": True,
        "repetition_freeze_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
    }
    if observed_contract != expected.model_dump(mode="python"):
        _error(
            "V2_PILOT_CLASSIFICATION_DECISION_DRIFT",
            "independently derived V2 pilot classification does not match frozen policy",
        )

    return PilotClassification(
        transaction_id=policy.transaction_id,
        issuer_merge_commit=policy.issuer_merge_commit,
        evidence_zip_sha256=policy.expected_hashes[
            "raw_kaggle/ag-variance-pilot-v2-tx-v1-evidence.zip"
        ],
        terminal_log_sha256=policy.expected_hashes[
            "raw_kaggle/ag-v2-variance-pilot-tx-bound-v1.log"
        ],
        executed_notebook_sha256=policy.expected_hashes[
            "raw_kaggle/ag-v2-variance-pilot-tx-bound-v1.ipynb"
        ],
        execution=execution,
        task_output=task,
        worker_nuisance=worker,
        affinity_pilot=affinity,
        notebook=notebook,
    )


def build_acceptance_boundary(classification: PilotClassification) -> PilotAcceptanceBoundary:
    return PilotAcceptanceBoundary(
        source_transaction_id=classification.transaction_id,
        source_classification_sha256=_sha256_bytes(_canonical_bytes(classification)),
    )


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    classification = build_classification(root)
    boundary = build_acceptance_boundary(classification)
    (root / CLASSIFICATION_PATH).write_bytes(_canonical_bytes(classification))
    (root / ACCEPTANCE_PATH).write_bytes(_canonical_bytes(boundary))
    return {
        "status": "VARIANCE_PILOT_V2_345461230_CLASSIFICATION_V1_GENERATED",
        "governed_execution_evidence_accepted": True,
        "task_output_contract": "PASSED",
        "worker_nuisance_control": "QUALIFIED",
        "pilot_repository_acceptance_established": True,
        "repetition_freeze_permitted": True,
        "repetition_freeze_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_classification = build_classification(root)
    expected_boundary = build_acceptance_boundary(expected_classification)
    try:
        observed_classification = PilotClassification.model_validate_json(
            (root / CLASSIFICATION_PATH).read_bytes()
        )
        observed_boundary = PilotAcceptanceBoundary.model_validate_json(
            (root / ACCEPTANCE_PATH).read_bytes()
        )
    except (FileNotFoundError, ValidationError) as error:
        _error(
            "V2_PILOT_CLASSIFICATION_GENERATED_OUTPUT_INVALID",
            "generated V2 pilot classification output is missing or invalid",
            details=(type(error).__name__,),
        )
    if observed_classification != expected_classification:
        _error(
            "V2_PILOT_CLASSIFICATION_OUTPUT_DRIFT",
            "generated V2 pilot classification is not deterministic",
            CLASSIFICATION_PATH,
        )
    if observed_boundary != expected_boundary:
        _error(
            "V2_PILOT_ACCEPTANCE_OUTPUT_DRIFT",
            "generated V2 pilot acceptance boundary is not deterministic",
            ACCEPTANCE_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_V2_345461230_CLASSIFICATION_V1_VALID",
        "governed_execution_evidence_accepted": True,
        "pilot_repository_acceptance_established": True,
        "repetition_freeze_permitted": True,
        "repetition_freeze_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "effect_claims_permitted": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser(prog="measured-abc-variance-pilot-v2-345461230-classification-v1")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        item = sub.add_parser(command)
        item.add_argument("--repo-root", type=Path, default=Path("."))
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        root = args.repo_root.resolve()
        result = generate(root) if args.command == "generate" else validate(root)
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except ClassificationError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

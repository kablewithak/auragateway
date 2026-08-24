"""Classify governed variance-pilot Kaggle Version 344611040 evidence.

This producer accepts the execution evidence as a governed runtime pass while
blocking repetition freeze and final A/B/C authority. It does not issue any
execution capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path(
    "data/evals/benchmark/variance-pilot-v1/variance_pilot_344611040_classification_v1_policy.json"
)
POLICY_SHA256: Final = "a0451e52e3f370bbac9a48ed938f8f07436bdcc718ec262937d429f4a782f220"

RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/measured_abc_variance_pilot_transaction_bound_runtime_v1.py"
)
CLASSIFICATION_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_344611040_classification_v1.json"
)
REDESIGN_BOUNDARY_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_measured_abc_variance_pilot_redesign_boundary_v1.json"
)

NEXT_GATE: Final = "MERGE_CLASSIFICATION_THEN_IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_DESIGN_V2"


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
    zip_member_count: Literal[8]
    bundle_manifest_member_count: Literal[7]
    scheduled_trajectory_count: Literal[54]
    scheduled_turn_count: Literal[216]
    pilot_model_request_count: Literal[216]
    preflight_model_request_count: Literal[5]
    total_model_request_count: Literal[221]
    interrupted_trajectory_count: Literal[0]
    comparison_eligible_trajectory_count: Literal[54]
    task_failed_trajectory_count: Literal[54]
    request_completed_turn_count: Literal[216]
    finish_reason_length_count: Literal[132]
    finish_reason_stop_count: Literal[84]
    json_valid_turn_count: Literal[6]
    json_invalid_turn_count: Literal[210]
    unique_output_sha256_count: Literal[21]
    same_salt_cold_cached_prefix_tokens: Literal[0]
    same_salt_warm_cached_prefix_tokens: Literal[944]
    different_salt_cached_prefix_tokens: Literal[0]
    worker_1_projection_count: Literal[18]
    worker_2_projection_count: Literal[36]
    worker_1_conditions: tuple[Literal["C"], ...]
    worker_2_conditions: tuple[Literal["A", "B"], ...]

    @model_validator(mode="after")
    def validate_worker_conditions(self) -> Self:
        if self.worker_1_conditions != ("C",):
            raise ValueError("worker 1 condition set drifted")
        if self.worker_2_conditions != ("A", "B"):
            raise ValueError("worker 2 condition set drifted")
        return self


class ClassificationContract(StrictModel):
    governed_execution_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    cache_salt_qualification: Literal["QUALIFIED"]
    task_output_contract: Literal["FAILED"]
    worker_symmetry_estimator: Literal["CONFOUNDED"]
    repetition_freeze_decision: Literal["BLOCK_REPETITION_FREEZE_AND_REDESIGN"]
    pilot_repository_acceptance_established: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]


class ClassificationPolicy(StrictModel):
    schema_version: Literal["1.0.0"]
    policy_id: Literal["auragateway-measured-abc-variance-pilot-344611040-classification-v1-policy"]
    saved_version_id: Literal[344611040]
    transaction_id: Literal["06935eae12e8f996c7046a859ea75525b436a871b086ba4c56470d24871747ab"]
    issuer_merge_commit: Literal["bb1e2b46767e7b84ae8bbecab2887759e38e028d"]
    runtime_payload_sha256: Literal[
        "a3c832ba7b8233efccdcd035d408fbd7508ade1dabd5b929adcb148d35b28c5b"
    ]
    vault_path: str
    expected_hashes: dict[str, str]
    expected_zip_members: dict[str, str]
    expected_semantics: ExpectedSemantics
    classification: ClassificationContract
    redesign_requirements: tuple[str, ...]

    @model_validator(mode="after")
    def validate_identity_sets(self) -> Self:
        if len(self.expected_hashes) != 7:
            raise ValueError("vault receipt count drifted")
        if len(self.expected_zip_members) != 8:
            raise ValueError("evidence ZIP member identity count drifted")
        if len(self.redesign_requirements) != 5:
            raise ValueError("redesign requirement count drifted")
        return self


class WorkerProjectionFinding(StrictModel):
    worker_1_projection_count: Literal[18]
    worker_2_projection_count: Literal[36]
    worker_1_conditions: tuple[Literal["C"], ...]
    worker_2_conditions: tuple[Literal["A", "B"], ...]
    worker_1_median_ttft_ms: float = Field(ge=0)
    worker_2_median_ttft_ms: float = Field(ge=0)
    observed_ttft_ratio: float = Field(ge=1)
    worker_1_median_prefill_ms: float = Field(ge=0)
    worker_2_median_prefill_ms: float = Field(ge=0)
    observed_prefill_ratio: float = Field(ge=1)
    causal_worker_effect_interpretable: Literal[False] = False
    confound: Literal["TURN_2_WORKER_ID_IS_ALIASED_WITH_ABC_CONDITION_AND_CACHE_STATE"] = (
        "TURN_2_WORKER_ID_IS_ALIASED_WITH_ABC_CONDITION_AND_CACHE_STATE"
    )


class TaskOutputFinding(StrictModel):
    failed_trajectory_count: Literal[54]
    request_completed_turn_count: Literal[216]
    finish_reason_length_count: Literal[132]
    finish_reason_stop_count: Literal[84]
    json_valid_turn_count: Literal[6]
    json_invalid_turn_count: Literal[210]
    unique_output_sha256_count: Literal[21]
    task_output_contract: Literal["FAILED"] = "FAILED"


class CacheSaltFinding(StrictModel):
    status: Literal["QUALIFIED"]
    same_salt_cold_cached_prefix_tokens: Literal[0]
    same_salt_warm_cached_prefix_tokens: Literal[944]
    different_salt_cached_prefix_tokens: Literal[0]
    cross_salt_reuse_observed: Literal[False]


class PilotClassification(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    classification_id: Literal[
        "auragateway-measured-abc-variance-pilot-344611040-classification-v1"
    ] = "auragateway-measured-abc-variance-pilot-344611040-classification-v1"
    saved_version_id: Literal[344611040]
    transaction_id: str
    issuer_merge_commit: str
    evidence_zip_sha256: str
    terminal_log_sha256: str
    executed_notebook_sha256: str
    governed_execution_disposition: Literal["ACCEPTED_GOVERNED_EXECUTION_PASS"]
    runtime_fatal_failure: Literal[False]
    scheduled_trajectory_count: Literal[54]
    scheduled_turn_count: Literal[216]
    total_model_request_count: Literal[221]
    interrupted_trajectory_count: Literal[0]
    hidden_retry_count: Literal[0]
    replacement_case_count: Literal[0]
    comparison_eligible_trajectory_count: Literal[54]
    cache_salt: CacheSaltFinding
    task_output: TaskOutputFinding
    worker_projection: WorkerProjectionFinding
    repetition_freeze_decision: Literal["BLOCK_REPETITION_FREEZE_AND_REDESIGN"]
    pilot_repository_acceptance_established: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    effect_claims_permitted: Literal[False]
    raw_prompts_retained: Literal[False]
    raw_outputs_retained: Literal[False]
    customer_data_used: Literal[False]
    external_network_requests: Literal[0]
    external_spend: Literal[0]
    next_gate: Literal["MERGE_CLASSIFICATION_THEN_IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_DESIGN_V2"] = (
        NEXT_GATE
    )


class RedesignBoundary(StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    boundary_id: Literal["auragateway-measured-abc-variance-pilot-redesign-boundary-v1"] = (
        "auragateway-measured-abc-variance-pilot-redesign-boundary-v1"
    )
    source_saved_version_id: Literal[344611040]
    source_transaction_id: str
    source_classification_sha256: str
    accepted_execution_evidence: Literal[True] = True
    accepted_cache_salt_mechanism_evidence: Literal[True] = True
    task_output_contract_satisfied: Literal[False] = False
    worker_symmetry_established: Literal[False] = False
    repetition_freeze_permitted: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    redesign_requirements: tuple[str, ...]
    next_gate: Literal["IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_DESIGN_V2_WITHOUT_REUSING_344611040"] = (
        "IMPLEMENT_VARIANCE_PILOT_SUCCESSOR_DESIGN_V2_WITHOUT_REUSING_344611040"
    )


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ClassificationError(
            "VARIANCE_PILOT_CLASSIFICATION_ARGUMENT_INVALID",
            "classification arguments are invalid",
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
            "VARIANCE_PILOT_CLASSIFICATION_JSON_INVALID",
            "required governed JSON evidence is missing or invalid",
            path,
            (type(error).__name__,),
        )
    if not isinstance(value, dict):
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_JSON_INVALID",
            "required governed JSON evidence root is invalid",
            path,
        )
    return cast(dict[str, object], value)


def _load_policy(repo_root: Path) -> ClassificationPolicy:
    path = repo_root / POLICY_PATH
    if not path.is_file() or _sha256_file(path) != POLICY_SHA256:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_POLICY_DRIFT",
            "classification policy identity drifted",
            POLICY_PATH,
        )
    try:
        return ClassificationPolicy.model_validate_json(path.read_bytes())
    except ValidationError as error:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_POLICY_INVALID",
            "classification policy failed typed validation",
            POLICY_PATH,
            tuple(item["msg"] for item in error.errors(include_url=False)),
        )


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


def _validate_vault(repo_root: Path, policy: ClassificationPolicy) -> Path:
    vault = repo_root / policy.vault_path
    for relative, expected_sha in policy.expected_hashes.items():
        path = vault / relative
        if not path.is_file():
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_EVIDENCE_MISSING",
                "governed pilot evidence file is missing",
                path,
            )
        observed_sha = _sha256_file(path)
        if observed_sha != expected_sha:
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_EVIDENCE_DRIFT",
                "governed pilot evidence identity drifted",
                path,
                (f"expected={expected_sha}", f"observed={observed_sha}"),
            )
    runtime_path = repo_root / RUNTIME_PATH
    if _sha256_file(runtime_path) != policy.runtime_payload_sha256:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_RUNTIME_DRIFT",
            "bound pilot runtime payload identity drifted",
            RUNTIME_PATH,
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
            "VARIANCE_PILOT_CLASSIFICATION_TRANSACTION_DRIFT",
            "lifecycle transaction identity drifted",
        )

    authorization = live.get("authorization")
    if not isinstance(authorization, dict):
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_AUTHORIZATION_INVALID",
            "live authorization payload is invalid",
        )
    _require_equal(
        authorization.get("issuer_merge_commit"),
        policy.issuer_merge_commit,
        "VARIANCE_PILOT_CLASSIFICATION_ISSUER_DRIFT",
        "issuer merge commit drifted",
    )
    _require_equal(
        authorization.get("pilot_execution_authorized"),
        True,
        "VARIANCE_PILOT_CLASSIFICATION_AUTHORIZATION_INVALID",
        "pilot was not authorized by the preserved capability",
    )
    _require_equal(
        authorization.get("final_measured_abc_execution_authorized"),
        False,
        "VARIANCE_PILOT_CLASSIFICATION_FINAL_AUTHORITY_INVALID",
        "preserved pilot authority enabled final measured A/B/C",
    )

    _require_equal(
        manifest.get("issuer_merge_commit"),
        policy.issuer_merge_commit,
        "VARIANCE_PILOT_CLASSIFICATION_ISSUER_DRIFT",
        "artifact manifest issuer drifted",
    )
    _require_equal(
        observation.get("accelerator"),
        "T4_X2",
        "VARIANCE_PILOT_CLASSIFICATION_PLATFORM_INVALID",
        "platform accelerator observation drifted",
    )
    _require_equal(
        observation.get("allocated_gpu_count"),
        2,
        "VARIANCE_PILOT_CLASSIFICATION_PLATFORM_INVALID",
        "platform GPU count drifted",
    )
    _require_equal(
        observation.get("internet_enabled"),
        False,
        "VARIANCE_PILOT_CLASSIFICATION_PLATFORM_INVALID",
        "platform internet observation drifted",
    )
    _require_equal(
        observation.get("wheelhouse_input_count"),
        1,
        "VARIANCE_PILOT_CLASSIFICATION_PLATFORM_INVALID",
        "wheelhouse input count drifted",
    )
    _require_equal(
        observation.get("model_snapshot_input_count"),
        1,
        "VARIANCE_PILOT_CLASSIFICATION_PLATFORM_INVALID",
        "model snapshot input count drifted",
    )
    _require_equal(
        observation.get("persisted_before_save_and_run_all"),
        True,
        "VARIANCE_PILOT_CLASSIFICATION_PLATFORM_INVALID",
        "platform observation was not persisted before execution",
    )

    terminal_expectations = {
        "saved_version_id": policy.saved_version_id,
        "disposition": "CONSUMED",
        "execution_attempted": True,
        "execution_outcome": "PASSED",
        "authorization_reusable": False,
        "pilot_repository_acceptance_established": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "evidence_zip_sha256": policy.expected_hashes[
            "raw_kaggle/ag-variance-pilot-tx-v1-evidence.zip"
        ],
        "terminal_log_sha256": policy.expected_hashes[
            "raw_kaggle/ag-variance-pilot-transaction-bound-v1.log"
        ],
    }
    for key, expected in terminal_expectations.items():
        _require_equal(
            terminal.get(key),
            expected,
            "VARIANCE_PILOT_CLASSIFICATION_TERMINAL_INVALID",
            f"terminal lifecycle field {key} drifted",
        )


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
                    "VARIANCE_PILOT_CLASSIFICATION_ZIP_DUPLICATE_MEMBER",
                    "evidence ZIP contains duplicate member names",
                    zip_path,
                )
            if len(names) != policy.expected_semantics.zip_member_count:
                _error(
                    "VARIANCE_PILOT_CLASSIFICATION_ZIP_MEMBER_COUNT",
                    "evidence ZIP member count drifted",
                    zip_path,
                )
            if set(names) != expected_names:
                _error(
                    "VARIANCE_PILOT_CLASSIFICATION_ZIP_MEMBER_SET",
                    "evidence ZIP member set drifted",
                    zip_path,
                    tuple(sorted(set(names) ^ expected_names)),
                )
            for info in infos:
                if info.is_dir() or "/" in info.filename or "\\" in info.filename:
                    _error(
                        "VARIANCE_PILOT_CLASSIFICATION_ZIP_PATH_INVALID",
                        "evidence ZIP member path is invalid",
                        zip_path,
                        (info.filename,),
                    )
                raw = archive.read(info)
                expected_sha = policy.expected_zip_members[info.filename]
                observed_sha = _sha256_bytes(raw)
                if observed_sha != expected_sha:
                    _error(
                        "VARIANCE_PILOT_CLASSIFICATION_ZIP_MEMBER_DRIFT",
                        "evidence ZIP member identity drifted",
                        zip_path,
                        (
                            info.filename,
                            f"expected={expected_sha}",
                            f"observed={observed_sha}",
                        ),
                    )
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError:
                    _error(
                        "VARIANCE_PILOT_CLASSIFICATION_ZIP_JSON_INVALID",
                        "evidence ZIP JSON member is invalid",
                        zip_path,
                        (info.filename,),
                    )
                if not isinstance(value, dict):
                    _error(
                        "VARIANCE_PILOT_CLASSIFICATION_ZIP_JSON_INVALID",
                        "evidence ZIP JSON root is invalid",
                        zip_path,
                        (info.filename,),
                    )
                payloads[info.filename] = cast(dict[str, object], value)
    except zipfile.BadZipFile as error:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_ZIP_INVALID",
            "governed pilot evidence ZIP is invalid",
            zip_path,
            (type(error).__name__,),
        )
    return payloads


def _median(values: list[float]) -> float:
    if not values:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_TELEMETRY_EMPTY",
            "required worker telemetry population is empty",
        )
    return float(statistics.median(values))


def _ratio(first: float, second: float) -> float:
    low = min(first, second)
    high = max(first, second)
    if low <= 0:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_TELEMETRY_INVALID",
            "worker timing median is non-positive",
        )
    return high / low


def _build_findings(
    payloads: dict[str, dict[str, object]],
    policy: ClassificationPolicy,
) -> tuple[
    CacheSaltFinding,
    TaskOutputFinding,
    WorkerProjectionFinding,
    dict[str, int],
]:
    expected = policy.expected_semantics
    preflight = payloads["timing_telemetry_preflight_v1.json"]
    ledger = payloads["pilot_trajectory_ledger_v1.json"]
    operational = payloads["pilot_operational_evidence_v1.json"]
    summary = payloads["pilot_runtime_summary_v1.json"]
    failure = payloads["failure_report_v1.json"]
    teardown = payloads["worker_teardown_report_v1.json"]
    cleanup = payloads["scratch_cleanup_report_v1.json"]
    manifest = payloads["bundle_manifest_v1.json"]

    for evidence_name, evidence_payload in (
        ("timing_telemetry_preflight_v1.json", preflight),
        ("pilot_trajectory_ledger_v1.json", ledger),
        ("pilot_operational_evidence_v1.json", operational),
        ("pilot_runtime_summary_v1.json", summary),
        ("worker_teardown_report_v1.json", teardown),
        ("failure_report_v1.json", failure),
        ("bundle_manifest_v1.json", manifest),
    ):
        _require_equal(
            evidence_payload.get("transaction_id"),
            policy.transaction_id,
            "VARIANCE_PILOT_CLASSIFICATION_TRANSACTION_DRIFT",
            f"evidence ZIP transaction identity drifted in {evidence_name}",
        )

    _require_equal(
        manifest.get("member_count"),
        expected.bundle_manifest_member_count,
        "VARIANCE_PILOT_CLASSIFICATION_BUNDLE_INVALID",
        "bundle manifest member count drifted",
    )
    manifest_members = manifest.get("members")
    if not isinstance(manifest_members, list):
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_BUNDLE_INVALID",
            "bundle manifest member list is invalid",
        )
    expected_manifest_names = set(policy.expected_zip_members) - {"bundle_manifest_v1.json"}
    observed_manifest_names: set[str] = set()
    for raw in manifest_members:
        if not isinstance(raw, dict):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_BUNDLE_INVALID",
                "bundle manifest member row is invalid",
            )
        member_name = raw.get("name")
        member_sha = raw.get("sha256")
        if not isinstance(member_name, str) or not isinstance(member_sha, str):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_BUNDLE_INVALID",
                "bundle manifest member identity is invalid",
            )
        observed_manifest_names.add(member_name)
        _require_equal(
            member_sha,
            policy.expected_zip_members.get(member_name),
            "VARIANCE_PILOT_CLASSIFICATION_BUNDLE_INVALID",
            "bundle manifest member SHA drifted",
        )
    _require_equal(
        observed_manifest_names,
        expected_manifest_names,
        "VARIANCE_PILOT_CLASSIFICATION_BUNDLE_INVALID",
        "bundle manifest member set drifted",
    )

    for key in (
        "raw_prompts_included",
        "raw_outputs_included",
        "raw_source_documents_included",
        "credentials_included",
    ):
        _require_equal(
            manifest.get(key),
            False,
            "VARIANCE_PILOT_CLASSIFICATION_PRIVACY_INVALID",
            f"bundle privacy field {key} drifted",
        )

    cache_raw = preflight.get("cache_salt_isolation")
    if not isinstance(cache_raw, dict):
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_CACHE_PREFLIGHT_INVALID",
            "cache-salt preflight evidence is invalid",
        )
    cache = CacheSaltFinding(
        status=cast(str, cache_raw.get("status")),
        same_salt_cold_cached_prefix_tokens=cast(
            int, cache_raw.get("same_salt_cold_cached_prefix_tokens")
        ),
        same_salt_warm_cached_prefix_tokens=cast(
            int, cache_raw.get("same_salt_warm_cached_prefix_tokens")
        ),
        different_salt_cached_prefix_tokens=cast(
            int, cache_raw.get("different_salt_cached_prefix_tokens")
        ),
        cross_salt_reuse_observed=cast(bool, cache_raw.get("cross_salt_reuse_observed")),
    )
    _require_equal(
        cache.same_salt_cold_cached_prefix_tokens,
        expected.same_salt_cold_cached_prefix_tokens,
        "VARIANCE_PILOT_CLASSIFICATION_CACHE_PREFLIGHT_INVALID",
        "same-salt cold cache observation drifted",
    )
    _require_equal(
        cache.same_salt_warm_cached_prefix_tokens,
        expected.same_salt_warm_cached_prefix_tokens,
        "VARIANCE_PILOT_CLASSIFICATION_CACHE_PREFLIGHT_INVALID",
        "same-salt warm cache observation drifted",
    )
    _require_equal(
        cache.different_salt_cached_prefix_tokens,
        expected.different_salt_cached_prefix_tokens,
        "VARIANCE_PILOT_CLASSIFICATION_CACHE_PREFLIGHT_INVALID",
        "different-salt cache observation drifted",
    )

    _require_equal(
        summary.get("status"),
        "PASSED_PENDING_REPOSITORY_ACCEPTANCE",
        "VARIANCE_PILOT_CLASSIFICATION_RUNTIME_SUMMARY_INVALID",
        "runtime summary status drifted",
    )
    for key, expected_value in (
        ("raw_prompts_retained", False),
        ("raw_outputs_retained", False),
        ("customer_data_used", False),
        ("external_spend", 0),
        ("final_measured_abc_execution_authorized", False),
        ("effect_claims_permitted", False),
    ):
        _require_equal(
            summary.get(key),
            expected_value,
            "VARIANCE_PILOT_CLASSIFICATION_RUNTIME_SUMMARY_INVALID",
            f"runtime summary field {key} drifted",
        )
    for key, expected_value in (
        ("external_network_requests", 0),
        ("external_spend", 0),
        ("hidden_retries", 0),
        ("replacement_cases_used", False),
    ):
        _require_equal(
            operational.get(key),
            expected_value,
            "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
            f"operational evidence field {key} drifted",
        )
    _require_equal(
        failure.get("fatal_failure"),
        False,
        "VARIANCE_PILOT_CLASSIFICATION_RUNTIME_FAILURE",
        "governed pilot reported a fatal runtime failure",
    )
    _require_equal(
        teardown.get("worker_report_count"),
        2,
        "VARIANCE_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
        "worker teardown report count drifted",
    )
    reports = teardown.get("reports")
    if not isinstance(reports, list) or len(reports) != 2:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
            "worker teardown reports are invalid",
        )
    for report in reports:
        if not isinstance(report, dict):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
                "worker teardown row is invalid",
            )
        for key in (
            "capture_threads_finalized",
            "gpu_processes_absent_after",
            "memory_returned_within_tolerance",
            "port_closed_after",
            "process_tree_absent_after",
        ):
            _require_equal(
                report.get(key),
                True,
                "VARIANCE_PILOT_CLASSIFICATION_TEARDOWN_INVALID",
                f"worker teardown field {key} failed",
            )
    _require_equal(
        cleanup.get("status"),
        "PASSED",
        "VARIANCE_PILOT_CLASSIFICATION_CLEANUP_INVALID",
        "scratch cleanup did not pass",
    )
    _require_equal(
        cleanup.get("scratch_exists_after"),
        False,
        "VARIANCE_PILOT_CLASSIFICATION_CLEANUP_INVALID",
        "scratch remained after pilot cleanup",
    )

    trajectories_raw = ledger.get("trajectories")
    if not isinstance(trajectories_raw, list):
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_LEDGER_INVALID",
            "pilot trajectory ledger is invalid",
        )
    _require_equal(
        len(trajectories_raw),
        expected.scheduled_trajectory_count,
        "VARIANCE_PILOT_CLASSIFICATION_LEDGER_INVALID",
        "pilot trajectory count drifted",
    )

    task_counts: Counter[str] = Counter()
    finish_counts: Counter[str] = Counter()
    json_counts: Counter[bool] = Counter()
    output_hashes: set[str] = set()
    request_completed = 0
    total_turns = 0
    interrupted = 0
    hidden_retries = cast(int, ledger.get("hidden_retry_count"))
    replacements = cast(int, ledger.get("replacement_case_count"))

    for raw_trajectory in trajectories_raw:
        if not isinstance(raw_trajectory, dict):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_LEDGER_INVALID",
                "pilot trajectory row is invalid",
            )
        task_status = raw_trajectory.get("task_status")
        if isinstance(task_status, str):
            task_counts[task_status] += 1
        if raw_trajectory.get("interrupted") is True:
            interrupted += 1
        turns_raw = raw_trajectory.get("turns")
        if not isinstance(turns_raw, list):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_LEDGER_INVALID",
                "pilot turn list is invalid",
            )
        total_turns += len(turns_raw)
        for raw_turn in turns_raw:
            if not isinstance(raw_turn, dict):
                _error(
                    "VARIANCE_PILOT_CLASSIFICATION_LEDGER_INVALID",
                    "pilot turn row is invalid",
                )
            if raw_turn.get("request_completed") is True:
                request_completed += 1
            finish = raw_turn.get("finish_reason")
            if isinstance(finish, str):
                finish_counts[finish] += 1
            valid = raw_turn.get("json_object_valid")
            if isinstance(valid, bool):
                json_counts[valid] += 1
            output_sha = raw_turn.get("output_sha256")
            if isinstance(output_sha, str):
                output_hashes.add(output_sha)

    _require_equal(
        total_turns,
        expected.scheduled_turn_count,
        "VARIANCE_PILOT_CLASSIFICATION_LEDGER_INVALID",
        "pilot turn count drifted",
    )
    _require_equal(
        task_counts["failed"],
        expected.task_failed_trajectory_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "task-failed trajectory count drifted",
    )
    _require_equal(
        request_completed,
        expected.request_completed_turn_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "completed request count drifted",
    )
    _require_equal(
        finish_counts["length"],
        expected.finish_reason_length_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "length termination count drifted",
    )
    _require_equal(
        finish_counts["stop"],
        expected.finish_reason_stop_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "stop termination count drifted",
    )
    _require_equal(
        json_counts[True],
        expected.json_valid_turn_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "valid JSON turn count drifted",
    )
    _require_equal(
        json_counts[False],
        expected.json_invalid_turn_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "invalid JSON turn count drifted",
    )
    _require_equal(
        len(output_hashes),
        expected.unique_output_sha256_count,
        "VARIANCE_PILOT_CLASSIFICATION_TASK_FINDING_DRIFT",
        "unique output identity count drifted",
    )

    task = TaskOutputFinding(
        failed_trajectory_count=task_counts["failed"],
        request_completed_turn_count=request_completed,
        finish_reason_length_count=finish_counts["length"],
        finish_reason_stop_count=finish_counts["stop"],
        json_valid_turn_count=json_counts[True],
        json_invalid_turn_count=json_counts[False],
        unique_output_sha256_count=len(output_hashes),
    )

    projections_raw = operational.get("trajectories")
    if not isinstance(projections_raw, list):
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
            "pilot operational projection is invalid",
        )
    comparison_counts: Counter[str] = Counter()
    worker_conditions: dict[str, set[str]] = {"worker_1": set(), "worker_2": set()}
    ttft: dict[str, list[float]] = {"worker_1": [], "worker_2": []}
    prefill: dict[str, list[float]] = {"worker_1": [], "worker_2": []}

    for raw in projections_raw:
        if not isinstance(raw, dict):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
                "pilot operational row is invalid",
            )
        comparison = raw.get("comparison_status")
        if isinstance(comparison, str):
            comparison_counts[comparison] += 1
        worker = raw.get("worker_id")
        condition = raw.get("condition_id")
        if worker not in worker_conditions or not isinstance(condition, str):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_WORKER_PROJECTION_INVALID",
                "worker projection identity is invalid",
            )
        worker_key = cast(str, worker)
        worker_conditions[worker_key].add(condition)
        ttft_value = raw.get("time_to_first_token_ms")
        prefill_value = raw.get("prefill_duration_ms")
        if not isinstance(ttft_value, (int, float)) or not isinstance(prefill_value, (int, float)):
            _error(
                "VARIANCE_PILOT_CLASSIFICATION_WORKER_PROJECTION_INVALID",
                "worker timing projection is incomplete",
            )
        ttft[worker_key].append(float(ttft_value))
        prefill[worker_key].append(float(prefill_value))

    _require_equal(
        comparison_counts["eligible"],
        expected.comparison_eligible_trajectory_count,
        "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
        "comparison-eligible trajectory count drifted",
    )
    _require_equal(
        len(ttft["worker_1"]),
        expected.worker_1_projection_count,
        "VARIANCE_PILOT_CLASSIFICATION_WORKER_PROJECTION_INVALID",
        "worker 1 projection count drifted",
    )
    _require_equal(
        len(ttft["worker_2"]),
        expected.worker_2_projection_count,
        "VARIANCE_PILOT_CLASSIFICATION_WORKER_PROJECTION_INVALID",
        "worker 2 projection count drifted",
    )
    _require_equal(
        tuple(sorted(worker_conditions["worker_1"])),
        expected.worker_1_conditions,
        "VARIANCE_PILOT_CLASSIFICATION_WORKER_CONFOUND_DRIFT",
        "worker 1 condition population drifted",
    )
    _require_equal(
        tuple(sorted(worker_conditions["worker_2"])),
        expected.worker_2_conditions,
        "VARIANCE_PILOT_CLASSIFICATION_WORKER_CONFOUND_DRIFT",
        "worker 2 condition population drifted",
    )

    worker_1_ttft = _median(ttft["worker_1"])
    worker_2_ttft = _median(ttft["worker_2"])
    worker_1_prefill = _median(prefill["worker_1"])
    worker_2_prefill = _median(prefill["worker_2"])
    worker_projection = WorkerProjectionFinding(
        worker_1_projection_count=len(ttft["worker_1"]),
        worker_2_projection_count=len(ttft["worker_2"]),
        worker_1_conditions=tuple(sorted(worker_conditions["worker_1"])),
        worker_2_conditions=tuple(sorted(worker_conditions["worker_2"])),
        worker_1_median_ttft_ms=round(worker_1_ttft, 6),
        worker_2_median_ttft_ms=round(worker_2_ttft, 6),
        observed_ttft_ratio=round(_ratio(worker_1_ttft, worker_2_ttft), 6),
        worker_1_median_prefill_ms=round(worker_1_prefill, 6),
        worker_2_median_prefill_ms=round(worker_2_prefill, 6),
        observed_prefill_ratio=round(
            _ratio(worker_1_prefill, worker_2_prefill),
            6,
        ),
    )

    counts = {
        "interrupted": interrupted,
        "hidden_retries": hidden_retries,
        "replacements": replacements,
        "comparison_eligible": comparison_counts["eligible"],
    }
    _require_equal(
        counts["interrupted"],
        expected.interrupted_trajectory_count,
        "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
        "interrupted trajectory count drifted",
    )
    _require_equal(
        hidden_retries,
        0,
        "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
        "hidden retries were observed",
    )
    _require_equal(
        replacements,
        0,
        "VARIANCE_PILOT_CLASSIFICATION_OPERATIONAL_INVALID",
        "replacement cases were observed",
    )
    return cache, task, worker_projection, counts


def build_classification(repo_root: Path) -> PilotClassification:
    root = repo_root.resolve()
    policy = _load_policy(root)
    vault = _validate_vault(root, policy)
    _validate_lifecycle(vault, policy)
    zip_path = vault / "raw_kaggle/ag-variance-pilot-tx-v1-evidence.zip"
    payloads = _read_evidence_zip(zip_path, policy)
    cache, task, worker_projection, counts = _build_findings(payloads, policy)

    summary = payloads["pilot_runtime_summary_v1.json"]
    bundle = payloads["bundle_manifest_v1.json"]
    _require_equal(
        summary.get("model_request_count"),
        policy.expected_semantics.total_model_request_count,
        "VARIANCE_PILOT_CLASSIFICATION_REQUEST_COUNT_DRIFT",
        "total model request count drifted",
    )
    _require_equal(
        bundle.get("runtime_payload_sha256"),
        policy.runtime_payload_sha256,
        "VARIANCE_PILOT_CLASSIFICATION_RUNTIME_DRIFT",
        "evidence bundle runtime identity drifted",
    )

    return PilotClassification(
        saved_version_id=policy.saved_version_id,
        transaction_id=policy.transaction_id,
        issuer_merge_commit=policy.issuer_merge_commit,
        evidence_zip_sha256=policy.expected_hashes[
            "raw_kaggle/ag-variance-pilot-tx-v1-evidence.zip"
        ],
        terminal_log_sha256=policy.expected_hashes[
            "raw_kaggle/ag-variance-pilot-transaction-bound-v1.log"
        ],
        executed_notebook_sha256=policy.expected_hashes[
            "raw_kaggle/ag-variance-pilot-transaction-bound-v1.ipynb"
        ],
        governed_execution_disposition=(policy.classification.governed_execution_disposition),
        runtime_fatal_failure=False,
        scheduled_trajectory_count=policy.expected_semantics.scheduled_trajectory_count,
        scheduled_turn_count=policy.expected_semantics.scheduled_turn_count,
        total_model_request_count=policy.expected_semantics.total_model_request_count,
        interrupted_trajectory_count=counts["interrupted"],
        hidden_retry_count=counts["hidden_retries"],
        replacement_case_count=counts["replacements"],
        comparison_eligible_trajectory_count=counts["comparison_eligible"],
        cache_salt=cache,
        task_output=task,
        worker_projection=worker_projection,
        repetition_freeze_decision=(policy.classification.repetition_freeze_decision),
        pilot_repository_acceptance_established=False,
        final_measured_abc_execution_authorized=False,
        new_execution_authorized=False,
        effect_claims_permitted=False,
        raw_prompts_retained=False,
        raw_outputs_retained=False,
        customer_data_used=False,
        external_network_requests=0,
        external_spend=0,
    )


def build_redesign_boundary(
    classification: PilotClassification,
    policy: ClassificationPolicy,
) -> RedesignBoundary:
    return RedesignBoundary(
        source_saved_version_id=classification.saved_version_id,
        source_transaction_id=classification.transaction_id,
        source_classification_sha256=_sha256_bytes(_canonical_bytes(classification)),
        redesign_requirements=policy.redesign_requirements,
    )


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    policy = _load_policy(root)
    classification = build_classification(root)
    boundary = build_redesign_boundary(classification, policy)
    (root / CLASSIFICATION_PATH).write_bytes(_canonical_bytes(classification))
    (root / REDESIGN_BOUNDARY_PATH).write_bytes(_canonical_bytes(boundary))
    return {
        "status": "VARIANCE_PILOT_344611040_CLASSIFICATION_V1_GENERATED",
        "governed_execution_disposition": (classification.governed_execution_disposition),
        "cache_salt_qualification": classification.cache_salt.status,
        "task_output_contract": classification.task_output.task_output_contract,
        "worker_symmetry_estimator": "CONFOUNDED",
        "repetition_freeze_decision": classification.repetition_freeze_decision,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    policy = _load_policy(root)
    expected_classification = build_classification(root)
    expected_boundary = build_redesign_boundary(expected_classification, policy)
    try:
        observed_classification = PilotClassification.model_validate_json(
            (root / CLASSIFICATION_PATH).read_bytes()
        )
        observed_boundary = RedesignBoundary.model_validate_json(
            (root / REDESIGN_BOUNDARY_PATH).read_bytes()
        )
    except (FileNotFoundError, ValidationError) as error:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_GENERATED_OUTPUT_INVALID",
            "generated classification output is missing or invalid",
            details=(type(error).__name__,),
        )
    if observed_classification != expected_classification:
        _error(
            "VARIANCE_PILOT_CLASSIFICATION_OUTPUT_DRIFT",
            "generated pilot classification is not deterministic",
            CLASSIFICATION_PATH,
        )
    if observed_boundary != expected_boundary:
        _error(
            "VARIANCE_PILOT_REDESIGN_BOUNDARY_OUTPUT_DRIFT",
            "generated pilot redesign boundary is not deterministic",
            REDESIGN_BOUNDARY_PATH,
        )
    return {
        "status": "VARIANCE_PILOT_344611040_CLASSIFICATION_V1_VALID",
        "governed_execution_evidence_accepted": True,
        "repetition_freeze_permitted": False,
        "final_measured_abc_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="measured-abc-variance-pilot-344611040-classification-v1")
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

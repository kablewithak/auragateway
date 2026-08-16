"""Preserve and disposition the governed P4/P5 token-matched differential."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "43ab735de5477d0d05c6eba1fc95b5966d4a06d37a5d5f28875ed5c2c423122a"
SAVED_VERSION_ID: Final = 342834146
ISSUER_MERGE_COMMIT: Final = "417c7457dce0fafe16c4fbbd21d8344251f609d0"

CUSTODY_MANIFEST_SHA256: Final = "ef31e51e6c2da4634a1a5c7ad946cbf4814f8263916c8dfddbbc1d0e08123ec1"
EVIDENCE_ZIP_SHA256: Final = "4f44f378e309e49195e9bef1aa3122f9850d84f705c113782133febc96ce9654"
TERMINAL_LOG_SHA256: Final = "377013ccb4e46df2ea6e3e0c5af4e527cfe51868b2714639671f98c841a18094"
NOTEBOOK_SHA256: Final = "b89a6158560a9a58ea8607b75b1e4125bab595b95cc9a841a0b9bb7b34d09a75"
PLATFORM_RECEIPT_SHA256: Final = "2c95fc3d107de8b568bdef73159464389aa8d13b0bef3dd00d9d88fa9f4c2244"
TERMINAL_RECEIPT_SHA256: Final = "d10967a7a87bbe69a9e205d44260bdfe83d35a2b5e6493a5584f567d45014d4b"

RUNTIME_SHA256: Final = "9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834"
IMPLEMENTATION_RECORD_SHA256: Final = (
    "6815a8d3b6a7eb5e88212fd0e280cbfc686f378ab0c98f18e1a05e0de0681b27"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "fe7bd30cc8afdaa318d09a65748f2ae2d214d7c42f83416b666f1da9d8580a1a"
)
AUTHORIZATION_DESIGN_RECORD_SHA256: Final = (
    "6ba28cdb0f2d489c5de9171ab08edad6403d9adb058fb6b84caa61e03d1b69a4"
)
ISSUER_SOURCE_SHA256: Final = "ca80a9580b5d23d4cb81833746c73867f4761baeba564d5748b05c08bd7c6ec0"
GENERATOR_CONTRACT_SHA256: Final = (
    "61bd23ca78e803005bd9a7e7c3b7062dbca096e329508f5a5c9751e66227428c"
)

NEXT_GATE: Final = (
    "STATIC_HIGH_EXACT_TOKEN_PATTERN_REPETITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"
)

VAULT_ROOT: Final = Path(
    "evidence_vault/local_abc/p4-p5-token-count-matched-context-structure-differential-v1"
)
CUSTODY_MANIFEST_PATH: Final = VAULT_ROOT / "custody_manifest_v1.json"
AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/execution_authorization_v1.json"
EXECUTION_MANIFEST_PATH: Final = VAULT_ROOT / "lifecycle/execution_artifact_manifest_v1.json"
PLATFORM_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/platform_observation_receipt_v1.json"
TERMINAL_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/authorization_terminal_receipt_v1.json"
EVIDENCE_ZIP_PATH: Final = VAULT_ROOT / "kaggle/" / "evidence-v1-342834146.zip"
NOTEBOOK_PATH: Final = (
    VAULT_ROOT / "kaggle/" / "ag-p4-p5-token-matched-structure-diff-v1-342834146.ipynb"
)
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "kaggle/kaggle-terminal-342834146.log"

RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "p4_p5_token_count_matched_context_structure_differential_runtime_v1.py"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_implementation_v1.json"
)
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_implementation_v1_review.json"
)
AUTHORIZATION_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_execution_authorization_design_v1.json"
)
ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "p4_p5_token_count_matched_context_structure_differential_"
    "execution_authorization_v1.py"
)
GENERATOR_CONTRACT_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "p4_p5_token_count_matched_context_structure_differential_"
    "transaction_bound_wrapper_v1.py.tmpl"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_disposition_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_token_count_matched_context_structure_"
    "differential_disposition_v1_review.json"
)

REQUEST_ORDER: Final = (
    "A_ORIGINAL_24X_ANCHOR",
    "B_NEUTRAL_REPEATED_24X",
    "C_NEUTRAL_DIVERSE_24_SEGMENT",
    "B_NEUTRAL_REPEATED_24X",
    "C_NEUTRAL_DIVERSE_24_SEGMENT",
    "A_ORIGINAL_24X_ANCHOR",
    "C_NEUTRAL_DIVERSE_24_SEGMENT",
    "A_ORIGINAL_24X_ANCHOR",
    "B_NEUTRAL_REPEATED_24X",
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
            "P4_P5_TOKEN_MATCHED_DISPOSITION_ARGUMENT_INVALID",
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
    manifest_id: Literal[
        "auragateway-p4-p5-token-count-matched-context-structure-differential-evidence-custody-v1"
    ]
    transaction_id: Literal["43ab735de5477d0d05c6eba1fc95b5966d4a06d37a5d5f28875ed5c2c423122a"]
    saved_version_id: Literal[342834146]
    execution_status: Literal["DIAGNOSTIC_COMPLETE"]
    decision_state: Literal["HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"]
    condition_a_exact_object_count: Literal[0]
    condition_b_exact_object_count: Literal[0]
    condition_c_exact_object_count: Literal[3]
    terminal_disposition: Literal["CONSUMED"]
    terminal_execution_outcome: Literal["PASSED"]
    authorization_reusable: Literal[False]
    member_count: Literal[7]
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
    record_id: Literal[
        "auragateway-p4-p5-token-count-matched-context-structure-differential-disposition-v1"
    ]
    status: Literal["DISPOSITIONED_VALID_GOVERNED_TOKEN_MATCHED_DIFFERENTIAL"]
    transaction_id: Literal["43ab735de5477d0d05c6eba1fc95b5966d4a06d37a5d5f28875ed5c2c423122a"]
    saved_version_id: Literal[342834146]
    terminal_disposition: Literal["CONSUMED"]
    execution_outcome: Literal["PASSED"]
    diagnostic_status: Literal["DIAGNOSTIC_COMPLETE"]
    decision_state: Literal["HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"]
    variable_under_test: Literal["TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE"]
    prompt_token_count_per_condition: Literal[899]
    observations_per_condition: Literal[3]
    condition_a_exact_object_count: Literal[0]
    condition_b_exact_object_count: Literal[0]
    condition_c_exact_object_count: Literal[3]
    condition_a_valid_json_count: Literal[0]
    condition_b_valid_json_count: Literal[0]
    condition_c_valid_json_count: Literal[3]
    anchor_reproduced: Literal[True]
    mechanistic_inference_permitted: Literal[True]
    all_condition_token_identities_matched: Literal[True]
    all_condition_payload_identities_matched: Literal[True]
    b_to_c_residual_lexical_novelty_bounded: Literal[True]
    fresh_worker_process_per_observation: Literal[True]
    worker_identity_cardinality: Literal[9]
    runtime_source_identity_verified: Literal[True]
    runtime_installation_passed: Literal[True]
    runtime_import_closure_passed: Literal[True]
    model_requests_performed: Literal[9]
    model_loads_performed: Literal[9]
    worker_starts_performed: Literal[9]
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
    high_exact_token_pattern_repetition_strongly_implicated: Literal[True]
    exact_repetition_sole_cause_established: Literal[False]
    semantic_amplification_sole_cause_established: Literal[False]
    exact_repetition_threshold_established: Literal[False]
    context_length_alone_established_causal: Literal[False]
    exact_root_cause_established: Literal[False]
    prefix_cache_defect_established: Literal[False]
    new_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    mechanistic_classification: Literal["HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"]
    specific_classification: Literal[
        "FROZEN_899_TOKEN_A0_B0_C3_PATTERN_STRONGLY_IMPLICATES_HIGH_"
        "EXACT_TOKEN_PATTERN_REPETITION_WITH_BOUNDED_LEXICAL_NOVELTY"
    ]
    evidence_confidence: Literal[
        "PREDECLARED_TOKEN_MATCHED_THREE_CONDITION_DIFFERENTIAL_WITHIN_FROZEN_RUNTIME"
    ]
    custody_manifest_sha256: Literal[
        "ef31e51e6c2da4634a1a5c7ad946cbf4814f8263916c8dfddbbc1d0e08123ec1"
    ]
    governed_evidence_zip_sha256: Literal[
        "4f44f378e309e49195e9bef1aa3122f9850d84f705c113782133febc96ce9654"
    ]
    authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...]
    next_gate: Literal[
        "STATIC_HIGH_EXACT_TOKEN_PATTERN_REPETITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"
    ]

    @model_validator(mode="after")
    def validate_boundary(self) -> Self:
        if len(self.authorities) != 14:
            raise ValueError("disposition authority count drifted")
        if len(self.non_claims) < 12:
            raise ValueError("disposition non-claim boundary is incomplete")
        return self


class DispositionReview(StrictModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal[
        "auragateway-p4-p5-token-count-matched-context-structure-differential-disposition-v1-review"
    ]
    status: Literal["APPROVED_GOVERNED_TOKEN_MATCHED_DIFFERENTIAL_DISPOSITION"]
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: Literal[
        "ef31e51e6c2da4634a1a5c7ad946cbf4814f8263916c8dfddbbc1d0e08123ec1"
    ]
    high_exact_token_pattern_repetition_result_accepted: Literal[True]
    exact_repetition_sole_cause_claimed: Literal[False]
    semantic_amplification_sole_cause_claimed: Literal[False]
    exact_threshold_claimed: Literal[False]
    exact_root_cause_claimed: Literal[False]
    p5_requalification_claimed: Literal[False]
    p6_requalification_claimed: Literal[False]
    measured_abc_claimed: Literal[False]
    new_execution_authorized: Literal[False]
    next_gate: Literal[
        "STATIC_HIGH_EXACT_TOKEN_PATTERN_REPETITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"
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
            "P4_P5_TOKEN_MATCHED_DISPOSITION_ARTIFACT_MISSING",
            "required disposition artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _require_hash(root: Path, relative: Path, expected: str) -> Path:
    path = _require_file(root, relative)
    if _sha256_file(path) != expected:
        raise DispositionError(
            "P4_P5_TOKEN_MATCHED_DISPOSITION_IDENTITY_DRIFT",
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
            "P4_P5_TOKEN_MATCHED_DISPOSITION_JSON_INVALID",
            "disposition JSON is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise DispositionError(
            "P4_P5_TOKEN_MATCHED_DISPOSITION_JSON_INVALID",
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
                "P4_P5_TOKEN_MATCHED_DISPOSITION_SIZE_DRIFT",
                "custody member size drifted",
                item.path,
            )
    return manifest


def validate_evidence_bundle(root: Path) -> None:
    path = _require_hash(root, EVIDENCE_ZIP_PATH, EVIDENCE_ZIP_SHA256)
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        required = {
            "bundle_manifest_v1.json",
            "p4_p5_token_matched_decision_v1.json",
            "p4_p5_token_matched_request_results_v1.json",
            "p4_p5_token_matched_summary_v1.json",
            "worker_teardown_report_v1.json",
            "scratch_cleanup_report_v1.json",
            "failure_report_v1.json",
            "runtime_source_identity_report_v1.json",
            "runtime_import_closure_report_v1.json",
        }
        if not required.issubset(names):
            raise DispositionError(
                "P4_P5_TOKEN_MATCHED_DISPOSITION_EVIDENCE_INCOMPLETE",
                "governed evidence ZIP is missing required members",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

        bundle = json.loads(archive.read("bundle_manifest_v1.json"))
        if not isinstance(bundle, dict):
            raise ValueError("bundle manifest root is invalid")
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

        decision = json.loads(archive.read("p4_p5_token_matched_decision_v1.json"))
        if decision.get("decision_state") != (
            "HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"
        ):
            raise ValueError("token-matched decision state drifted")
        if decision.get("condition_exact_object_counts") != {
            "A_ORIGINAL_24X_ANCHOR": 0,
            "B_NEUTRAL_REPEATED_24X": 0,
            "C_NEUTRAL_DIVERSE_24_SEGMENT": 3,
        }:
            raise ValueError("token-matched condition result drifted")
        if decision.get("anchor_reproduced") is not True:
            raise ValueError("historical A anchor was not reproduced")
        if decision.get("mechanistic_inference_permitted") is not True:
            raise ValueError("mechanistic inference gate is not satisfied")
        if decision.get("b_to_c_residual_lexical_novelty_bounded") is not True:
            raise ValueError("B-to-C lexical novelty boundary drifted")
        if decision.get("worker_identity_cardinality") != 9:
            raise ValueError("fresh-worker identity cardinality drifted")

        summary = json.loads(archive.read("p4_p5_token_matched_summary_v1.json"))
        expected = {
            "status": "DIAGNOSTIC_COMPLETE",
            "decision_state": ("HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"),
            "model_requests": 9,
            "model_loads": 9,
            "worker_starts": 9,
            "hidden_retries": 0,
            "external_network_requests": 0,
            "external_spend": 0,
            "teardown_status": "PASSED",
            "scratch_cleanup_status": "PASSED",
            "measured_abc_execution_performed": False,
        }
        for key, value in expected.items():
            if summary.get(key) != value:
                raise ValueError(f"summary field drifted: {key}")


def validate_lifecycle(root: Path) -> None:
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

    if terminal.get("disposition") != "CONSUMED":
        raise ValueError("terminal disposition drifted")
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

    if platform.get("accelerator") != "T4_X2":
        raise ValueError("platform accelerator drifted")
    if platform.get("allocated_gpu_count") != 2:
        raise ValueError("platform GPU count drifted")
    if platform.get("internet_enabled") is not False:
        raise ValueError("platform Internet-Off binding drifted")


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
        record_id=(
            "auragateway-p4-p5-token-count-matched-context-structure-differential-disposition-v1"
        ),
        status="DISPOSITIONED_VALID_GOVERNED_TOKEN_MATCHED_DIFFERENTIAL",
        transaction_id=TRANSACTION_ID,
        saved_version_id=SAVED_VERSION_ID,
        terminal_disposition="CONSUMED",
        execution_outcome="PASSED",
        diagnostic_status="DIAGNOSTIC_COMPLETE",
        decision_state=("HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"),
        variable_under_test="TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE",
        prompt_token_count_per_condition=899,
        observations_per_condition=3,
        condition_a_exact_object_count=0,
        condition_b_exact_object_count=0,
        condition_c_exact_object_count=3,
        condition_a_valid_json_count=0,
        condition_b_valid_json_count=0,
        condition_c_valid_json_count=3,
        anchor_reproduced=True,
        mechanistic_inference_permitted=True,
        all_condition_token_identities_matched=True,
        all_condition_payload_identities_matched=True,
        b_to_c_residual_lexical_novelty_bounded=True,
        fresh_worker_process_per_observation=True,
        worker_identity_cardinality=9,
        runtime_source_identity_verified=True,
        runtime_installation_passed=True,
        runtime_import_closure_passed=True,
        model_requests_performed=9,
        model_loads_performed=9,
        worker_starts_performed=9,
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
        high_exact_token_pattern_repetition_strongly_implicated=True,
        exact_repetition_sole_cause_established=False,
        semantic_amplification_sole_cause_established=False,
        exact_repetition_threshold_established=False,
        context_length_alone_established_causal=False,
        exact_root_cause_established=False,
        prefix_cache_defect_established=False,
        new_execution_authorized=False,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        mechanistic_classification=("HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"),
        specific_classification=(
            "FROZEN_899_TOKEN_A0_B0_C3_PATTERN_STRONGLY_IMPLICATES_HIGH_"
            "EXACT_TOKEN_PATTERN_REPETITION_WITH_BOUNDED_LEXICAL_NOVELTY"
        ),
        evidence_confidence=(
            "PREDECLARED_TOKEN_MATCHED_THREE_CONDITION_DIFFERENTIAL_WITHIN_FROZEN_RUNTIME"
        ),
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        governed_evidence_zip_sha256=EVIDENCE_ZIP_SHA256,
        authorities=authorities,
        non_claims=(
            "High exact token-pattern repetition is strongly implicated, "
            "not established as the sole cause.",
            "Repeated instruction-like semantic amplification is not "
            "established as the sole cause.",
            "The exact repetition threshold is not established.",
            "Context length alone is not established as causal.",
            "Residual lexical novelty remains bounded in the B-to-C contrast.",
            "The exact root cause of the historical regression is not established.",
            "A prefix-cache defect is not established.",
            "P5 is not requalified by this diagnostic.",
            "P6 is not requalified by this diagnostic.",
            "Measured North-Star A/B/C execution was not performed.",
            "No new runtime or Kaggle execution is authorized by this disposition.",
            "The consumed authorization is not reusable and unchanged replay is unauthorized.",
        ),
        next_gate=NEXT_GATE,
    )


def expected_outputs(root: Path) -> tuple[bytes, bytes]:
    record = build_record(root)
    record_bytes = _canonical_bytes(record)
    review = DispositionReview(
        schema_version="1.0.0",
        review_id=(
            "auragateway-p4-p5-token-count-matched-context-structure-"
            "differential-disposition-v1-review"
        ),
        status=("APPROVED_GOVERNED_TOKEN_MATCHED_DIFFERENTIAL_DISPOSITION"),
        record_sha256=_sha256_bytes(record_bytes),
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        high_exact_token_pattern_repetition_result_accepted=True,
        exact_repetition_sole_cause_claimed=False,
        semantic_amplification_sole_cause_claimed=False,
        exact_threshold_claimed=False,
        exact_root_cause_claimed=False,
        p5_requalification_claimed=False,
        p6_requalification_claimed=False,
        measured_abc_claimed=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    return record_bytes, _canonical_bytes(review)


def generate(root: Path) -> dict[str, object]:
    root = root.resolve()
    record_bytes, review_bytes = expected_outputs(root)
    (root / RECORD_PATH).write_bytes(record_bytes)
    (root / REVIEW_PATH).write_bytes(review_bytes)
    return {
        "status": "P4_P5_TOKEN_MATCHED_DIFFERENTIAL_DISPOSITION_GENERATED",
        "record_sha256": _sha256_bytes(record_bytes),
        "review_sha256": _sha256_bytes(review_bytes),
        "decision_state": ("HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"),
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    record_bytes, review_bytes = expected_outputs(root)
    if _require_file(root, RECORD_PATH).read_bytes() != record_bytes:
        raise DispositionError(
            "P4_P5_TOKEN_MATCHED_DISPOSITION_RECORD_DRIFT",
            "checked-in disposition record differs from deterministic output",
            RECORD_PATH.as_posix(),
        )
    if _require_file(root, REVIEW_PATH).read_bytes() != review_bytes:
        raise DispositionError(
            "P4_P5_TOKEN_MATCHED_DISPOSITION_REVIEW_DRIFT",
            "checked-in disposition review differs from deterministic output",
            REVIEW_PATH.as_posix(),
        )
    return {
        "status": "P4_P5_TOKEN_MATCHED_DIFFERENTIAL_DISPOSITION_VALID",
        "decision_state": ("HIGH_EXACT_TOKEN_PATTERN_REPETITION_STRONGLY_IMPLICATED"),
        "condition_a_exact_object_count": 0,
        "condition_b_exact_object_count": 0,
        "condition_c_exact_object_count": 3,
        "authorization_reusable": False,
        "new_execution_authorized": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "measured_abc_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def _print_error(error: DispositionError) -> None:
    print(
        json.dumps(
            {
                "error_code": error.error_code,
                "safe_message": error.safe_message,
                "path": error.path,
            },
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result: dict[str, object] | None = None
    try:
        if args.command == "generate":
            result = generate(Path(args.repo_root))
        if args.command == "validate":
            result = validate(Path(args.repo_root))
        if result is None:
            raise DispositionError(
                "P4_P5_TOKEN_MATCHED_DISPOSITION_ARGUMENT_INVALID",
                "unsupported disposition command",
            )
    except (
        DispositionError,
        ValidationError,
        ValueError,
        OSError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
        KeyError,
    ) as error:
        if isinstance(error, DispositionError):
            _print_error(error)
        if not isinstance(error, DispositionError):
            _print_error(
                DispositionError(
                    "P4_P5_TOKEN_MATCHED_DISPOSITION_VALIDATION_FAILED",
                    str(error),
                )
            )
        return 2
    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

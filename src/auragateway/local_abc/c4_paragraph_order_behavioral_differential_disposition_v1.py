"""Preserve and disposition governed C4 paragraph-order differential evidence V1.

This module is execution-inert. It validates immutable lifecycle/evidence bytes,
reconciles the frozen paragraph-order diagnostic, and emits deterministic
repository disposition record/review artifacts.

It does not authorize or perform model, GPU, Kaggle, P5, P6, or final A/B/C
execution.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "19fc03a6b4ca74a025f8d9b8cd21be7e1cb14a4e776995760c679a581340f122"
SAVED_VERSION_ID: Final = 343909652
DIAGNOSTIC_ID: Final = "C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
DECISION_STATE: Final = "ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE"
NEXT_GATE: Final = "ANALYZE_C4_PARAGRAPH_ORDER_NO_CHANGE_BEFORE_NEW_EXECUTION_V1"

CONTROL_CONDITION: Final = "CONTROL_ORIGINAL_C4"
TREATMENT_CONDITION: Final = "TREATMENT_REVERSED_MIDDLE_EIGHT"
REQUEST_ORDER: Final = (
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
    TREATMENT_CONDITION,
    CONTROL_CONDITION,
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
)

CONTROL_TOKEN_SHA256: Final = "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
TREATMENT_TOKEN_SHA256: Final = "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
CONTROL_PAYLOAD_SHA256: Final = "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
TREATMENT_PAYLOAD_SHA256: Final = "47c519c24efd40e3bab4bfa2eaec1cf3d62c91a648870e631721625567f20b5e"
HISTORICAL_CONTROL_PARSED_OBJECT_SHA256: Final = (
    "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
)
CONTROL_REUSABLE_PREFIX_SHA256: Final = (
    "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
)
TREATMENT_REUSABLE_PREFIX_SHA256: Final = (
    "28e53ebbf741ef12dbdbc8e29a1515c05d09dc3dc71f1e768339064b7517194b"
)

RUNTIME_SHA256: Final = "1d055dfab9f83a2706f5335b4529df98d45e45de5210a8c6c21c2b91e6a72df0"
ISSUER_MERGE_COMMIT: Final = "aaa86888df2b8a9c3d01680e1a1e4b8ebba1ecc7"
AUTHORIZATION_CANONICAL_SHA256: Final = (
    "36e6533e8e86f8dcbd097101d98c52efa3bf83a1885b82c8c94fbb8db17d1f4b"
)
MANIFEST_CANONICAL_SHA256: Final = (
    "1bd9e5a31355de9e64a661fe2f94d3c3afad6779ecea20e5c2440beb587aebe1"
)
PLATFORM_RECEIPT_CANONICAL_SHA256: Final = (
    "3edd2c83c1acf050822eb30681fff32a0a9d55568f8c3a8ad6939792c63b9763"
)
EVIDENCE_ZIP_SHA256: Final = "20e209c0a73f817b774065081ebed3e142405db1dca4e96847f5cc802650ca18"
OUTER_RESULTS_ZIP_SHA256: Final = "dfdfc7dbaed1e0387e4022505424a34ee806ae146e5d73167d813a650720c5c3"
TERMINAL_LOG_SHA256: Final = "86ae10e12ba80be2e9d3df31589d7508fdf4184829c1369631ed5078cd5a392b"
NOTEBOOK_SHA256: Final = "ab3126c55a0539287d3fe1577a173980ffbbdef8df7ea834624b86b5ab1a454e"

VAULT_ROOT: Final = Path("evidence_vault/local_abc/c4-paragraph-order-behavioral-differential-v1")
CUSTODY_MANIFEST_PATH: Final = VAULT_ROOT / "custody_manifest_v1.json"
AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/execution_authorization_v1.json"
EXECUTION_MANIFEST_PATH: Final = VAULT_ROOT / "lifecycle/execution_artifact_manifest_v1.json"
PLATFORM_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/platform_observation_receipt_v1.json"
TERMINAL_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/authorization_terminal_receipt_v1.json"
EVIDENCE_ZIP_PATH: Final = VAULT_ROOT / "kaggle/evidence-v1-343909652.zip"
OUTER_RESULTS_ZIP_PATH: Final = VAULT_ROOT / "kaggle/results-343909652.zip"
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "kaggle/kaggle-terminal-343909652.log"
NOTEBOOK_PATH: Final = VAULT_ROOT / "kaggle/ag-c4-paragraph-order-diff-v1-343909652.ipynb"

RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/c4_paragraph_order_behavioral_differential_runtime_v1.py"
)
IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1.json"
)
IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1_review.json"
)
AUTHORIZATION_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_"
    "execution_authorization_design_v1.json"
)
ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "c4_paragraph_order_behavioral_differential_execution_authorization_v1.py"
)
GENERATOR_CONTRACT_PATH: Final = Path(
    "src/auragateway/local_abc/templates/"
    "c4_paragraph_order_behavioral_differential_transaction_bound_wrapper_v1.py.tmpl"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/c4_paragraph_order_behavioral_differential_disposition_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_c4_paragraph_order_behavioral_differential_disposition_v1.py"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_disposition_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_disposition_v1_review.json"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_C4_Paragraph_Order_Behavioral_Differential_Disposition_V1.md"
)

CUSTODY_MANIFEST_SHA256: Final = "5de191716f788ab0345b74a1446252e95bf3793a3685c4fb4d498ead794aa549"

CUSTODY_SPECS: Final = (
    (
        "execution_authorization",
        AUTHORIZATION_PATH,
        "e004716303381a657e2ce7856f413b9096b3e1858d5a162c77bd1a05903127e7",
        7149,
    ),
    (
        "execution_artifact_manifest",
        EXECUTION_MANIFEST_PATH,
        "41bd6ee45de9888dffd2da992587bf53d68743215e98140255f632629a15e572",
        1704,
    ),
    (
        "platform_observation_receipt",
        PLATFORM_RECEIPT_PATH,
        "46bbbac62ef43a11a760a30c8729c8811759d747c395b08eb0adf5066810c2a9",
        598,
    ),
    (
        "authorization_terminal_receipt",
        TERMINAL_RECEIPT_PATH,
        "3a1f9c1791a0ccf0e6d94375946a16adc60d163d5c29ec24430435cbb7b57039",
        835,
    ),
    (
        "governed_evidence_zip",
        EVIDENCE_ZIP_PATH,
        EVIDENCE_ZIP_SHA256,
        15588,
    ),
    (
        "outer_kaggle_results_zip",
        OUTER_RESULTS_ZIP_PATH,
        OUTER_RESULTS_ZIP_SHA256,
        82291,
    ),
    (
        "terminal_log",
        TERMINAL_LOG_PATH,
        TERMINAL_LOG_SHA256,
        3181,
    ),
    (
        "saved_notebook",
        NOTEBOOK_PATH,
        NOTEBOOK_SHA256,
        518975,
    ),
)

REPO_AUTHORITIES: Final = (
    (
        "runtime_payload",
        RUNTIME_PATH,
        RUNTIME_SHA256,
    ),
    (
        "implementation_record",
        IMPLEMENTATION_RECORD_PATH,
        "c563bf012c7ec587089b7b28af5074207a389c5fb7381b9c1213299d3b489386",
    ),
    (
        "implementation_review",
        IMPLEMENTATION_REVIEW_PATH,
        "355a6b7f7871e648d8bfaf4c7841e9e6346f9b59eba65ac98c00b55d940d2595",
    ),
    (
        "authorization_design_record",
        AUTHORIZATION_DESIGN_RECORD_PATH,
        "8305ebb153f962015c28de98bd6fcf6feeb202482163c6cce3f0caf08cc3d143",
    ),
    (
        "issuer_source",
        ISSUER_SOURCE_PATH,
        "ecaccc674478cf5b8d379b456b462b6431e071f3567cfb5e98c245ca1fd3f030",
    ),
    (
        "generator_contract",
        GENERATOR_CONTRACT_PATH,
        "7a62445e48a51f32c49aa76d378127a8339a91e22e0c22e4de0150f7571b9f23",
    ),
)

INNER_MEMBERS: Final = frozenset(
    {
        "runtime_source_identity_report_v1.json",
        "runtime_install_report_v1.json",
        "runtime_environment_report_v1.json",
        "runtime_import_closure_report_v1.json",
        "c4_paragraph_order_runtime_ready_v1.json",
        "pre_request_token_identity_journal_v1.json",
        "c4_paragraph_order_request_results_v1.json",
        "c4_paragraph_order_decision_v1.json",
        "worker_teardown_report_v1.json",
        "scratch_cleanup_report_v1.json",
        "failure_report_v1.json",
        "c4_paragraph_order_summary_v1.json",
        "human_report_v1.md",
        "bundle_manifest_v1.json",
    }
)

NON_CLAIMS: Final = (
    "Global paragraph order is not established as the sole or root cause.",
    "The observed no-change result does not qualify C4.",
    "The result does not establish an exact repetition threshold.",
    "The result does not establish a prefix-cache defect.",
    "P5 is not requalified by this diagnostic.",
    "P6 is not requalified by this diagnostic.",
    "Final North-Star A/B/C execution was not performed.",
    "Production readiness is not established.",
    "No new execution is authorized and unchanged replay is unauthorized.",
)


class DispositionError(RuntimeError):
    """Structured fail-closed disposition error."""

    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.path = path


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise DispositionError("C4_ORDER_DISPOSITION_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(FrozenModel):
    role: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int | None = Field(default=None, gt=0)


class CustodyManifest(FrozenModel):
    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-c4-paragraph-order-behavioral-differential-evidence-custody-v1"
    transaction_id: str = TRANSACTION_ID
    saved_version_id: int = SAVED_VERSION_ID
    terminal_disposition: str = "CONSUMED"
    execution_outcome: str = "PASSED"
    decision_state: str = DECISION_STATE
    authorization_reusable: bool = False
    member_count: int = 8
    members: tuple[ArtifactReceipt, ...]

    @model_validator(mode="after")
    def validate_boundary(self) -> CustodyManifest:
        if self.member_count != 8 or len(self.members) != 8:
            raise ValueError("custody manifest must contain exactly eight members")
        roles = {item.role for item in self.members}
        paths = {item.path for item in self.members}
        if len(roles) != 8 or len(paths) != 8:
            raise ValueError("custody roles and paths must be unique")
        if self.authorization_reusable:
            raise ValueError("terminal authorization must not be reusable")
        return self


class DispositionRecord(FrozenModel):
    schema_version: str = "1.0.0"
    record_id: str = "auragateway-c4-paragraph-order-behavioral-differential-disposition-v1"
    status: str = "DISPOSITIONED_VALID_GOVERNED_C4_PARAGRAPH_ORDER_DIFFERENTIAL"
    transaction_id: str = TRANSACTION_ID
    saved_version_id: int = SAVED_VERSION_ID
    diagnostic_id: str = DIAGNOSTIC_ID
    decision_state: str = DECISION_STATE
    execution_valid: bool = True
    observations_per_condition: int = 3
    prompt_token_count_per_condition: int = 899
    final_user_boundary_per_condition: int = 880
    control_exact_object_count: int = 0
    treatment_exact_object_count: int = 0
    control_valid_json_count: int = 3
    treatment_valid_json_count: int = 3
    control_anchor_reproduced: bool = True
    control_historical_parsed_identity_matched: bool = True
    treatment_parsed_identity_matches_historical_control: bool = True
    same_deterministic_failure_phenotype_observed: bool = True
    all_condition_payload_identities_matched: bool = True
    all_condition_token_identities_matched: bool = True
    token_id_multiset_identical_static_premise: bool = True
    static_token_multiset_premise_reexecuted: bool = False
    fresh_worker_process_per_observation: bool = True
    worker_identity_cardinality: int = 6
    model_requests_performed: int = 6
    model_loads_performed: int = 6
    worker_starts_performed: int = 6
    hidden_retries_performed: int = 0
    replacement_observations_performed: int = 0
    external_network_requests_performed: int = 0
    benchmark_trajectory_requests_performed: int = 0
    external_spend: int = 0
    teardown_passed: bool = True
    scratch_cleanup_passed: bool = True
    failure_report_not_applicable: bool = True
    raw_prompt_retained: bool = False
    raw_output_retained: bool = False
    wrapper_reporting_defect_observed: bool = False
    paragraph_order_root_cause_established: bool = False
    c4_qualification_accepted_by_repository: bool = False
    paragraph_order_repository_state_advanced: bool = False
    p5_requalified: bool = False
    p6_requalified: bool = False
    final_abc_measured: bool = False
    production_readiness_established: bool = False
    terminal_disposition: str = "CONSUMED"
    execution_outcome: str = "PASSED"
    authorization_reusable: bool = False
    unchanged_replay_authorized: bool = False
    new_execution_authorized: bool = False
    custody_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    governed_evidence_zip_sha256: str = EVIDENCE_ZIP_SHA256
    outer_kaggle_results_zip_sha256: str = OUTER_RESULTS_ZIP_SHA256
    authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...] = NON_CLAIMS
    next_gate: str = NEXT_GATE


class DispositionReview(FrozenModel):
    schema_version: str = "1.0.0"
    review_id: str = "auragateway-c4-paragraph-order-behavioral-differential-disposition-v1-review"
    status: str = "APPROVED_GOVERNED_C4_PARAGRAPH_ORDER_DIFFERENTIAL_DISPOSITION"
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    decision_state: str = DECISION_STATE
    execution_valid: bool = True
    control_anchor_reproduced: bool = True
    same_failure_phenotype_accepted: bool = True
    c4_qualified_claimed: bool = False
    paragraph_order_root_cause_claimed: bool = False
    p5_requalified_claimed: bool = False
    p6_requalified_claimed: bool = False
    measured_abc_claimed: bool = False
    new_execution_authorized: bool = False
    next_gate: str = NEXT_GATE


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json_bytes(value: object, *, newline: bool = True) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    if newline:
        return encoded + b"\n"
    return encoded


def _require_file(root: Path, path: Path) -> bytes:
    target = root / path
    if not target.is_file():
        raise DispositionError(
            "C4_ORDER_DISPOSITION_REQUIRED_ARTIFACT_MISSING",
            "required artifact missing",
            path.as_posix(),
        )
    return target.read_bytes()


def _require_hash(root: Path, path: Path, expected: str) -> bytes:
    payload = _require_file(root, path)
    actual = _sha256_bytes(payload)
    if actual != expected:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_IDENTITY_MISMATCH",
            f"expected {expected}; observed {actual}",
            path.as_posix(),
        )
    return payload


def _load_json_bytes(payload: bytes, label: str) -> dict[str, object]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as error:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_JSON_INVALID",
            f"invalid JSON: {error.msg}",
            label,
        ) from error
    if not isinstance(value, dict):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_JSON_ROOT_INVALID",
            "JSON root must be an object",
            label,
        )
    return value


def _load_json(root: Path, path: Path, expected_sha256: str | None = None) -> dict[str, object]:
    payload = (
        _require_hash(root, path, expected_sha256)
        if expected_sha256 is not None
        else _require_file(root, path)
    )
    return _load_json_bytes(payload, path.as_posix())


def _expect(
    value: dict[str, object],
    expected: dict[str, object],
    label: str,
) -> None:
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_SEMANTIC_DRIFT",
                f"{label}.{key} drifted",
            )


def _zip_object(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    try:
        payload = archive.read(name)
    except KeyError as error:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_EVIDENCE_MEMBER_MISSING",
            "evidence member missing",
            name,
        ) from error
    return _load_json_bytes(payload, name)


def validate_custody(root: Path) -> CustodyManifest:
    payload = _require_hash(root, CUSTODY_MANIFEST_PATH, CUSTODY_MANIFEST_SHA256)
    try:
        manifest = CustodyManifest.model_validate_json(payload)
    except ValidationError as error:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_CUSTODY_MANIFEST_INVALID",
            str(error),
            CUSTODY_MANIFEST_PATH.as_posix(),
        ) from error

    expected = {
        (role, path.as_posix(), sha256, size_bytes)
        for role, path, sha256, size_bytes in CUSTODY_SPECS
    }
    observed = {(item.role, item.path, item.sha256, item.size_bytes) for item in manifest.members}
    if observed != expected:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_CUSTODY_MEMBER_SET_DRIFT",
            "custody member identity set drifted",
            CUSTODY_MANIFEST_PATH.as_posix(),
        )

    for role, path, sha256, size_bytes in CUSTODY_SPECS:
        member = _require_hash(root, path, sha256)
        if len(member) != size_bytes:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_CUSTODY_SIZE_DRIFT",
                f"custody size drifted for {role}",
                path.as_posix(),
            )
    return manifest


def _validate_request_results(payload: dict[str, object]) -> None:
    _expect(
        payload,
        {
            "status": "COMPLETE",
            "diagnostic_id": DIAGNOSTIC_ID,
            "scheduled_request_count": 6,
            "observed_request_count": 6,
            "request_order": list(REQUEST_ORDER),
            "raw_output_retained": False,
            "raw_prompt_retained": False,
        },
        "request_results",
    )
    results = payload.get("results")
    if not isinstance(results, list) or len(results) != 6:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_REQUEST_COUNT_INVALID",
            "expected six request results",
        )

    workers: set[str] = set()
    parsed_identities: set[str] = set()
    for ordinal, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            raise DispositionError(
                "C4_ORDER_DISPOSITION_REQUEST_RESULT_INVALID",
                "request result must be an object",
            )
        condition = REQUEST_ORDER[ordinal - 1]
        token_sha = (
            CONTROL_TOKEN_SHA256 if condition == CONTROL_CONDITION else TREATMENT_TOKEN_SHA256
        )
        payload_sha = (
            CONTROL_PAYLOAD_SHA256 if condition == CONTROL_CONDITION else TREATMENT_PAYLOAD_SHA256
        )
        _expect(
            item,
            {
                "request_ordinal": ordinal,
                "sequence_index": ordinal,
                "condition_id": condition,
                "http_status": 200,
                "finish_reason": "stop",
                "response_complete": True,
                "valid_json": True,
                "json_root_type": "object",
                "duplicate_key_detected": False,
                "markdown_fence_detected": False,
                "leading_non_whitespace_content_detected": False,
                "trailing_non_whitespace_content_detected": False,
                "exact_object": False,
                "probe_exact": False,
                "value_exact": False,
                "request_error": None,
                "transport_error": None,
                "zero_cache_baseline": True,
                "teardown_status": "PASSED",
                "raw_output_retained": False,
                "raw_prompt_retained": False,
                "prompt_tokens": 899,
                "token_count": 899,
                "token_sha256": token_sha,
                "payload_sha256": payload_sha,
                "canonical_parsed_object_sha256": (HISTORICAL_CONTROL_PARSED_OBJECT_SHA256),
                "response_sha256": HISTORICAL_CONTROL_PARSED_OBJECT_SHA256,
            },
            f"request[{ordinal}]",
        )
        worker = item.get("worker_instance_id")
        parsed = item.get("canonical_parsed_object_sha256")
        if not isinstance(worker, str) or not isinstance(parsed, str):
            raise DispositionError(
                "C4_ORDER_DISPOSITION_REQUEST_IDENTITY_INVALID",
                "worker or parsed-object identity is invalid",
            )
        workers.add(worker)
        parsed_identities.add(parsed)

    if len(workers) != 6:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_WORKER_CARDINALITY_DRIFT",
            "expected six distinct worker identities",
        )
    if parsed_identities != {HISTORICAL_CONTROL_PARSED_OBJECT_SHA256}:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_FAILURE_PHENOTYPE_DRIFT",
            "parsed-object failure phenotype drifted",
        )


def _validate_token_journal(payload: dict[str, object]) -> None:
    _expect(
        payload,
        {
            "schema_version": "1.0.0",
            "diagnostic_id": DIAGNOSTIC_ID,
            "raw_model_output_retained": False,
            "raw_prompt_retained": False,
        },
        "token_journal",
    )
    entries = payload.get("entries")
    if not isinstance(entries, list) or len(entries) != 6:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_TOKEN_JOURNAL_COUNT_INVALID",
            "expected six pre-request identity entries",
        )
    for ordinal, item in enumerate(entries, start=1):
        if not isinstance(item, dict):
            raise DispositionError(
                "C4_ORDER_DISPOSITION_TOKEN_JOURNAL_ENTRY_INVALID",
                "token journal entry must be an object",
            )
        condition = REQUEST_ORDER[ordinal - 1]
        control = condition == CONTROL_CONDITION
        _expect(
            item,
            {
                "request_ordinal": ordinal,
                "condition_id": condition,
                "persisted_before_model_request": True,
                "token_count": 899,
                "token_sha256": (CONTROL_TOKEN_SHA256 if control else TREATMENT_TOKEN_SHA256),
                "payload_sha256": (CONTROL_PAYLOAD_SHA256 if control else TREATMENT_PAYLOAD_SHA256),
                "reusable_prefix_token_count": 880,
                "reusable_prefix_token_sha256": (
                    CONTROL_REUSABLE_PREFIX_SHA256 if control else TREATMENT_REUSABLE_PREFIX_SHA256
                ),
            },
            f"token_journal[{ordinal}]",
        )


def validate_evidence_bundle(root: Path) -> None:
    _require_hash(root, EVIDENCE_ZIP_PATH, EVIDENCE_ZIP_SHA256)
    with zipfile.ZipFile(root / EVIDENCE_ZIP_PATH) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or frozenset(names) != INNER_MEMBERS:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_EVIDENCE_MEMBER_SET_DRIFT",
                "governed evidence member set drifted",
                EVIDENCE_ZIP_PATH.as_posix(),
            )

        manifest = _zip_object(archive, "bundle_manifest_v1.json")
        members = manifest.get("members")
        if not isinstance(members, list) or len(members) != 13:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_BUNDLE_MANIFEST_INVALID",
                "bundle manifest must contain exactly thirteen members",
            )
        for item in members:
            if not isinstance(item, dict):
                raise DispositionError(
                    "C4_ORDER_DISPOSITION_BUNDLE_MEMBER_INVALID",
                    "bundle manifest member must be an object",
                )
            name = item.get("path")
            if not isinstance(name, str):
                raise DispositionError(
                    "C4_ORDER_DISPOSITION_BUNDLE_MEMBER_INVALID",
                    "bundle member path must be a string",
                )
            member = archive.read(name)
            if _sha256_bytes(member) != item.get("sha256"):
                raise DispositionError(
                    "C4_ORDER_DISPOSITION_BUNDLE_MEMBER_DRIFT",
                    f"bundle member hash drifted: {name}",
                )
            if len(member) != item.get("size_bytes"):
                raise DispositionError(
                    "C4_ORDER_DISPOSITION_BUNDLE_MEMBER_DRIFT",
                    f"bundle member size drifted: {name}",
                )

        decision = _zip_object(archive, "c4_paragraph_order_decision_v1.json")
        _expect(
            decision,
            {
                "status": "DECIDED",
                "diagnostic_id": DIAGNOSTIC_ID,
                "primary_endpoint": "exact_object",
                "control_anchor_reproduced": True,
                "control_historical_parsed_identity_required": True,
                "condition_exact_object_counts": {
                    CONTROL_CONDITION: 0,
                    TREATMENT_CONDITION: 0,
                },
                "condition_valid_json_counts": {
                    CONTROL_CONDITION: 3,
                    TREATMENT_CONDITION: 3,
                },
                "observed_terminal_state": DECISION_STATE,
                "all_condition_payload_identities_matched": True,
                "all_condition_token_identities_matched": True,
                "static_token_multiset_premise_reexecuted": False,
                "fresh_worker_process_per_observation": True,
                "worker_identity_cardinality": 6,
                "paragraph_order_root_cause_established": False,
                "p5_requalified": False,
                "p6_requalified": False,
                "final_abc_measured": False,
                "raw_output_retained": False,
                "raw_prompt_retained": False,
            },
            "decision",
        )

        _validate_request_results(
            _zip_object(archive, "c4_paragraph_order_request_results_v1.json")
        )
        _validate_token_journal(_zip_object(archive, "pre_request_token_identity_journal_v1.json"))

        _expect(
            _zip_object(archive, "c4_paragraph_order_summary_v1.json"),
            {
                "status": "QUALIFICATION_EXECUTION_COMPLETE",
                "diagnostic_id": DIAGNOSTIC_ID,
                "scheduled_requests": 6,
                "completed_requests": 6,
                "model_loads": 6,
                "worker_starts": 6,
                "model_requests": 6,
                "hidden_retries": 0,
                "external_network_requests": 0,
                "external_spend": 0,
                "observed_terminal_state": DECISION_STATE,
                "teardown_status": "PASSED",
                "scratch_cleanup_status": "PASSED",
                "qualification_accepted_by_repository": False,
                "paragraph_order_repository_state_advanced": False,
                "p5_requalified": False,
                "p6_requalified": False,
                "final_abc_measured": False,
                "production_readiness_established": False,
                "raw_output_retained": False,
                "raw_prompt_retained": False,
            },
            "summary",
        )

        _expect(
            _zip_object(archive, "runtime_source_identity_report_v1.json"),
            {
                "status": "PASSED",
                "decision": "EXECUTED_RUNTIME_SCRIPT_IDENTITY_VERIFIED",
                "executed_runtime_script_sha256": RUNTIME_SHA256,
                "wrapper_hash_verification_passed": True,
            },
            "runtime_source_identity",
        )
        _expect(
            _zip_object(archive, "c4_paragraph_order_runtime_ready_v1.json"),
            {
                "status": "PASSED",
                "decision": "STATIC_RUNTIME_PREREQUISITES_REALIZED",
                "diagnostic_id": DIAGNOSTIC_ID,
                "backend": "TRITON_ATTN",
                "prompt_token_count_per_condition": 899,
                "final_user_boundary_per_condition": 880,
                "control_prompt_token_sha256": CONTROL_TOKEN_SHA256,
                "treatment_prompt_token_sha256": TREATMENT_TOKEN_SHA256,
                "scheduled_model_loads": 6,
                "scheduled_model_requests": 6,
                "scheduled_worker_starts": 6,
                "fresh_worker_process_per_observation": True,
                "raw_output_retained": False,
                "raw_prompt_retained": False,
            },
            "runtime_ready",
        )
        _expect(
            _zip_object(archive, "runtime_import_closure_report_v1.json"),
            {
                "status": "PASSED",
                "decision": "PROCESS_TREE_IMPORT_CLOSURE_PASSED",
                "hidden_retry_count": 0,
                "network_access_requested": False,
                "model_loads_consumed": 0,
                "worker_starts_consumed": 0,
                "process_outcome": "ZERO_EXIT",
                "returncode": 0,
                "timed_out": False,
                "pythonpath_exact_target_site": True,
                "inherited_pythonpath_replaced": True,
                "nested_interpreter_depth": 2,
                "failure_signals": [],
            },
            "runtime_import_closure",
        )
        _expect(
            _zip_object(archive, "worker_teardown_report_v1.json"),
            {
                "status": "PASSED",
                "scheduled_worker_count": 6,
                "observed_teardown_count": 6,
                "all_completed_observations_torn_down": True,
                "fresh_worker_process_per_observation": True,
                "raw_output_retained": False,
                "raw_prompt_retained": False,
            },
            "teardown",
        )
        _expect(
            _zip_object(archive, "scratch_cleanup_report_v1.json"),
            {
                "status": "PASSED",
                "scratch_exists_after": False,
                "secondary_failure_only": True,
            },
            "scratch_cleanup",
        )
        _expect(
            _zip_object(archive, "failure_report_v1.json"),
            {
                "status": "NOT_APPLICABLE",
                "completed_requests": 6,
                "failure_class": None,
                "error_type": None,
                "detail_code": None,
                "teardown_status": "PASSED",
            },
            "failure_report",
        )


def validate_outer_results(root: Path) -> None:
    _require_hash(root, OUTER_RESULTS_ZIP_PATH, OUTER_RESULTS_ZIP_SHA256)
    with zipfile.ZipFile(root / OUTER_RESULTS_ZIP_PATH) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise DispositionError(
                "C4_ORDER_DISPOSITION_DUPLICATE_OUTER_MEMBER",
                "outer results ZIP contains duplicate member names",
            )
        inner = "ag-c4-paragraph-order-diff-evidence-v1.zip"
        if inner not in names:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_INNER_EVIDENCE_MISSING",
                "outer results ZIP does not contain governed evidence ZIP",
            )
        if _sha256_bytes(archive.read(inner)) != EVIDENCE_ZIP_SHA256:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_INNER_EVIDENCE_DRIFT",
                "outer results ZIP does not bind the governed evidence ZIP",
            )
        admission_name = (
            "c4_paragraph_order_behavioral_differential_transaction_bound_admission_v1.json"
        )
        admission = _zip_object(archive, admission_name)
        _expect(
            admission,
            {
                "status": "C4_PARAGRAPH_ORDER_TRANSACTION_BOUND_RUNTIME_ADMISSION_VALID",
                "transaction_id": TRANSACTION_ID,
                "issuer_merge_commit": ISSUER_MERGE_COMMIT,
                "runtime_payload_sha256": RUNTIME_SHA256,
                "authorization_live_at_admission": True,
                "internet_policy_bound": True,
                "network_probe_performed": False,
                "observed_gpu_count": 2,
                "platform_observation_receipt_runtime_input": False,
            },
            "outer_admission",
        )
        primary_failures = [name for name in names if "primary_failure" in name]
        if primary_failures:
            raise DispositionError(
                "C4_ORDER_DISPOSITION_UNEXPECTED_WRAPPER_PRIMARY_FAILURE",
                "current wrapper line emitted an unexpected primary-failure artifact",
            )


def validate_notebook(root: Path) -> None:
    payload = _require_hash(root, NOTEBOOK_PATH, NOTEBOOK_SHA256)
    notebook = _load_json_bytes(payload, NOTEBOOK_PATH.as_posix())
    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_NOTEBOOK_INVALID",
            "saved notebook has no cells",
            NOTEBOOK_PATH.as_posix(),
        )
    output_text: list[str] = []
    for cell in cells:
        if not isinstance(cell, dict):
            raise DispositionError(
                "C4_ORDER_DISPOSITION_NOTEBOOK_INVALID",
                "saved notebook cell is invalid",
            )
        outputs = cell.get("outputs", [])
        if not isinstance(outputs, list):
            raise DispositionError(
                "C4_ORDER_DISPOSITION_NOTEBOOK_INVALID",
                "saved notebook outputs are invalid",
            )
        for output in outputs:
            if not isinstance(output, dict):
                raise DispositionError(
                    "C4_ORDER_DISPOSITION_NOTEBOOK_INVALID",
                    "saved notebook output is invalid",
                )
            if output.get("output_type") == "error":
                raise DispositionError(
                    "C4_ORDER_DISPOSITION_NOTEBOOK_ERROR_OUTPUT",
                    "saved notebook contains an error output",
                )
            text = output.get("text")
            if isinstance(text, list):
                output_text.append("".join(str(part) for part in text))
            if isinstance(text, str):
                output_text.append(text)
    rendered = "\n".join(output_text)
    required = (TRANSACTION_ID, DECISION_STATE, EVIDENCE_ZIP_SHA256)
    if any(marker not in rendered for marker in required):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_NOTEBOOK_SUMMARY_DRIFT",
            "saved notebook output does not bind the accepted transaction/result",
        )
    if "PRIMARY_FAILURE_CAPTURED" in rendered:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_NOTEBOOK_WRAPPER_FAILURE",
            "saved notebook output contains a wrapper primary-failure report",
        )


def validate_lifecycle(root: Path) -> None:
    authorization = _load_json(root, AUTHORIZATION_PATH, CUSTODY_SPECS[0][2])
    if _sha256_bytes(_canonical_json_bytes(authorization, newline=False)) != (
        AUTHORIZATION_CANONICAL_SHA256
    ):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_AUTHORIZATION_CANONICAL_IDENTITY_DRIFT",
            "authorization canonical identity drifted",
        )
    nested = authorization.get("authorization")
    if not isinstance(nested, dict):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_AUTHORIZATION_INVALID",
            "authorization payload is missing",
        )
    if _sha256_bytes(_canonical_json_bytes(nested, newline=False)) != TRANSACTION_ID:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_TRANSACTION_IDENTITY_DRIFT",
            "transaction identity is not the canonical authorization payload identity",
        )
    _expect(
        authorization,
        {
            "schema_version": "1.0.0",
            "transaction_id": TRANSACTION_ID,
        },
        "authorization_envelope",
    )
    _expect(
        nested,
        {
            "decision": "AUTHORIZED",
            "scope": DIAGNOSTIC_ID,
            "single_use": True,
            "authorization_reusable": False,
            "runtime_execution_authorized": True,
            "unchanged_replay_authorized": False,
            "runtime_remediation_authorized": False,
            "threshold_search_authorized": False,
            "p5_p6_requalification_authorized": False,
            "north_star_abc_effect_claim_authorized": False,
            "paragraph_order_root_cause_claim_authorized": False,
            "operator_confirmation_method": "RETYPE_DYNAMIC_SHA256_CHALLENGE",
            "operator_confirmation_recorded": True,
            "issuer_merge_commit": ISSUER_MERGE_COMMIT,
            "issuer_source_sha256": REPO_AUTHORITIES[4][2],
            "generator_contract_sha256": REPO_AUTHORITIES[5][2],
            "runtime_payload_sha256": RUNTIME_SHA256,
        },
        "authorization",
    )

    manifest = _load_json(root, EXECUTION_MANIFEST_PATH, CUSTODY_SPECS[1][2])
    if _sha256_bytes(_canonical_json_bytes(manifest, newline=False)) != (MANIFEST_CANONICAL_SHA256):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_MANIFEST_CANONICAL_IDENTITY_DRIFT",
            "execution artifact manifest canonical identity drifted",
        )
    _expect(
        manifest,
        {
            "status": "TRANSACTION_BOUND_EXECUTABLE_GENERATED",
            "transaction_id": TRANSACTION_ID,
            "authorization_sha256": AUTHORIZATION_CANONICAL_SHA256,
            "issuer_merge_commit": ISSUER_MERGE_COMMIT,
            "runtime_payload_sha256": RUNTIME_SHA256,
            "single_use_governance": True,
            "runtime_execution_authorized": True,
            "runtime_anti_replay_established": False,
            "platform_observation_required_before_save_and_run_all": True,
        },
        "execution_manifest",
    )

    platform = _load_json(root, PLATFORM_RECEIPT_PATH, CUSTODY_SPECS[2][2])
    if _sha256_bytes(_canonical_json_bytes(platform, newline=False)) != (
        PLATFORM_RECEIPT_CANONICAL_SHA256
    ):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_PLATFORM_RECEIPT_CANONICAL_IDENTITY_DRIFT",
            "platform receipt canonical identity drifted",
        )
    _expect(
        platform,
        {
            "transaction_id": TRANSACTION_ID,
            "authorization_sha256": AUTHORIZATION_CANONICAL_SHA256,
            "manifest_sha256": MANIFEST_CANONICAL_SHA256,
            "accelerator": "T4_X2",
            "allocated_gpu_count": 2,
            "internet_enabled": False,
            "persisted_before_save_and_run_all": True,
            "receipt_runtime_input": False,
        },
        "platform_receipt",
    )

    terminal = _load_json(root, TERMINAL_RECEIPT_PATH, CUSTODY_SPECS[3][2])
    _expect(
        terminal,
        {
            "transaction_id": TRANSACTION_ID,
            "authorization_sha256": AUTHORIZATION_CANONICAL_SHA256,
            "manifest_sha256": MANIFEST_CANONICAL_SHA256,
            "platform_observation_receipt_sha256": (PLATFORM_RECEIPT_CANONICAL_SHA256),
            "disposition": "CONSUMED",
            "execution_attempted": True,
            "execution_outcome": "PASSED",
            "runtime_execution_authorized": False,
            "authorization_reusable": False,
            "runtime_anti_replay_established": False,
            "saved_version_id": SAVED_VERSION_ID,
            "evidence_zip_sha256": EVIDENCE_ZIP_SHA256,
            "terminal_log_sha256": TERMINAL_LOG_SHA256,
        },
        "terminal_receipt",
    )


def validate_repo_authorities(root: Path) -> tuple[ArtifactReceipt, ...]:
    receipts: list[ArtifactReceipt] = []
    for role, path, expected in REPO_AUTHORITIES:
        _require_hash(root, path, expected)
        receipts.append(
            ArtifactReceipt(
                role=role,
                path=path.as_posix(),
                sha256=expected,
                size_bytes=None,
            )
        )
    return tuple(receipts)


def build_record(root: Path) -> DispositionRecord:
    manifest = validate_custody(root)
    validate_evidence_bundle(root)
    validate_outer_results(root)
    validate_notebook(root)
    validate_lifecycle(root)
    repo_receipts = validate_repo_authorities(root)

    custody_manifest_receipt = ArtifactReceipt(
        role="custody_manifest",
        path=CUSTODY_MANIFEST_PATH.as_posix(),
        sha256=CUSTODY_MANIFEST_SHA256,
        size_bytes=len(_require_file(root, CUSTODY_MANIFEST_PATH)),
    )
    authorities = (
        custody_manifest_receipt,
        *manifest.members,
        *repo_receipts,
    )
    if len(authorities) != 15:
        raise DispositionError(
            "C4_ORDER_DISPOSITION_AUTHORITY_CARDINALITY_DRIFT",
            "expected exactly fifteen disposition authorities",
        )

    return DispositionRecord(
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        authorities=authorities,
    )


def build_review(record: DispositionRecord) -> DispositionReview:
    return DispositionReview(
        record_sha256=_sha256_bytes(_canonical_json_bytes(record)),
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
    )


def generate(root: Path) -> tuple[DispositionRecord, DispositionReview]:
    record = build_record(root)
    review = build_review(record)
    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(_canonical_json_bytes(record))
    review_path.write_bytes(_canonical_json_bytes(review))
    return record, review


def validate(root: Path) -> tuple[DispositionRecord, DispositionReview]:
    record = build_record(root)
    review = build_review(record)
    observed_record = _require_file(root, RECORD_PATH)
    observed_review = _require_file(root, REVIEW_PATH)
    if observed_record != _canonical_json_bytes(record):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_RECORD_DRIFT",
            "generated disposition record drifted",
            RECORD_PATH.as_posix(),
        )
    if observed_review != _canonical_json_bytes(review):
        raise DispositionError(
            "C4_ORDER_DISPOSITION_REVIEW_DRIFT",
            "generated disposition review drifted",
            REVIEW_PATH.as_posix(),
        )
    return record, review


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("generate", "validate"):
        child = subparsers.add_parser(command)
        child.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _build_parser().parse_args(argv)
        root = args.repo_root.resolve()
        if args.command == "generate":
            record, review = generate(root)
        else:
            record, review = validate(root)
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "command": args.command,
                    "decision_state": record.decision_state,
                    "record_sha256": _sha256_bytes(_canonical_json_bytes(record)),
                    "review_sha256": _sha256_bytes(_canonical_json_bytes(review)),
                    "custody_manifest_sha256": record.custody_manifest_sha256,
                    "new_execution_authorized": record.new_execution_authorized,
                    "next_gate": record.next_gate,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except (DispositionError, ValidationError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        if isinstance(error, DispositionError):
            code = error.code
            message = error.message
            path = error.path
        else:
            code = "C4_ORDER_DISPOSITION_VALIDATION_FAILED"
            message = str(error)
            path = None
        print(
            json.dumps(
                {
                    "status": "FAIL",
                    "error_code": code,
                    "message": message,
                    "path": path,
                },
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Reconcile the failed governed P4/P5 composition remediation confirmation."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

TRANSACTION_ID: Final = "c984a77f3de24f986a9d9f255c25d83e375f552951b256c6e8f44c79c96e3542"
SAVED_VERSION_ID: Final = 341956898
BASE_MAIN_COMMIT: Final = "7ca6e7e43c2992cbe8525f0b56d40a9c6c6f7ea7"

CUSTODY_MANIFEST_SHA256: Final = "9338d50ea9b2f83084edc3322f481d07fe92373ac77bcafd61f3b82e319f063a"
EVIDENCE_ZIP_SHA256: Final = "784b7c4a7f0ac03afec018b24f40cb19d3db0e8ecb0ada2f930b0fd1c66e5397"
TERMINAL_LOG_SHA256: Final = "39cd32a1914262530823f73ba5197ed425befe85606a42344d8c70f6c1edef80"
NOTEBOOK_SHA256: Final = "1ae90a9ae7708346a15ad001af61f6a8b3a2cdb0ddb25d90c33deefca29a472a"
REMEDIATED_RUNTIME_SHA256: Final = (
    "aa0631ef5bc7b13c6d0f4a00078b6b35bc274147fc0847965dc000f732adc7ff"
)
PRE_REQUEST_TOKEN_SHA256: Final = "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
PRE_REQUEST_PAYLOAD_SHA256: Final = (
    "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediation_c3_failure_reconciliation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_composition_remediation_c3_failure_reconciliation_v1.py"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_P5_Composition_Remediation_C3_Failure_Reconciliation_V1.md"
)
REMEDIATED_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py"
)

VAULT_ROOT: Final = Path("evidence_vault/local_abc/p4-p5-composition-remediation-c3-failure-v1")
CUSTODY_MANIFEST_PATH: Final = VAULT_ROOT / "custody_manifest_v1.json"
EVIDENCE_ZIP_PATH: Final = (
    VAULT_ROOT / "kaggle/ag-p5-p6-transaction-bound-evidence-v1-341956898.zip"
)
TERMINAL_LOG_PATH: Final = VAULT_ROOT / "kaggle/kaggle-terminal-341956898.log"
NOTEBOOK_PATH: Final = (
    VAULT_ROOT / "kaggle/ag-p4-p5-remediation-p5-p6-confirmation-v1-341956898.ipynb"
)
AUTHORIZATION_PATH: Final = VAULT_ROOT / "lifecycle/execution_authorization_v1.json"
EXECUTION_MANIFEST_PATH: Final = VAULT_ROOT / "lifecycle/execution_artifact_manifest_v1.json"
PLATFORM_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/platform_observation_receipt_v1.json"
TERMINAL_RECEIPT_PATH: Final = VAULT_ROOT / "lifecycle/authorization_terminal_receipt_v1.json"

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_remediation_c3_failure_reconciliation_v1.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p4_p5_composition_remediation_c3_failure_reconciliation_v1_review.json"
)

NEXT_GATE: Final = "STATIC_REMAINING_COMPOSITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"

OLD_V5_TAIL: Final = (
    "For structured probes, return only the exact JSON object supplied in the final user message."
)
ACCEPTED_V4_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)


class ReconciliationError(RuntimeError):
    """Fail-closed reconciliation error."""

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
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_ARGUMENT_INVALID",
            message,
        )


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactReceipt(StrictModel):
    role: str = Field(min_length=1)
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class CustodyManifest(StrictModel):
    schema_version: Literal["1.0.0"]
    manifest_id: Literal["auragateway-p4-p5-composition-remediation-c3-failure-evidence-custody-v1"]
    transaction_id: Literal["c984a77f3de24f986a9d9f255c25d83e375f552951b256c6e8f44c79c96e3542"]
    saved_version_id: Literal[341956898]
    execution_status: Literal["FAILED"]
    completed_capabilities: tuple[str, ...]
    technical_first_divergence: Literal["C3"]
    failure_class: Literal["REQUEST_EXECUTION_FAILURE"]
    safe_failure_message: Literal["model response is not valid JSON"]
    model_requests_performed: Literal[1]
    model_loads_performed: Literal[1]
    worker_starts_performed: Literal[1]
    hidden_retries_performed: Literal[0]
    external_network_requests_performed: Literal[0]
    p5_reached: Literal[False]
    p6_reached: Literal[False]
    terminal_disposition: Literal["CONSUMED"]
    terminal_execution_outcome: Literal["FAILED"]
    authorization_reusable: Literal[False]
    matching_terminal_log_copy_count: int = Field(ge=1)
    duplicate_terminal_logs_byte_identical: bool
    member_count: Literal[7]
    members: tuple[ArtifactReceipt, ...]

    @model_validator(mode="after")
    def validate_boundary(self) -> Self:
        if self.completed_capabilities != ("C1", "C2"):
            raise ValueError("completed capability sequence drifted")
        if len(self.members) != self.member_count:
            raise ValueError("custody member count drifted")
        if (
            self.matching_terminal_log_copy_count > 1
            and not self.duplicate_terminal_logs_byte_identical
        ):
            raise ValueError("duplicate terminal-log custody is not byte-identical")
        return self


class ReconciliationRecord(StrictModel):
    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-p4-p5-composition-remediation-c3-failure-reconciliation-v1"]
    status: Literal["RECONCILED_VALID_GOVERNED_REMEDIATION_FAILURE"]
    transaction_id: Literal["c984a77f3de24f986a9d9f255c25d83e375f552951b256c6e8f44c79c96e3542"]
    saved_version_id: Literal[341956898]
    terminal_disposition: Literal["CONSUMED"]
    execution_outcome: Literal["FAILED"]
    technical_first_divergence: Literal["C3"]
    technical_failure_class: Literal["REQUEST_EXECUTION_FAILURE"]
    safe_failure_message: Literal["model response is not valid JSON"]
    completed_capabilities: tuple[str, ...]
    runtime_installation_passed: Literal[True]
    runtime_import_closure_passed: Literal[True]
    model_construction_passed: Literal[True]
    worker_startup_passed: Literal[True]
    remediated_runtime_identity_verified: Literal[True]
    remediation_instruction_replacement_present: Literal[True]
    historical_v5_tail_absent: Literal[True]
    first_request_role: Literal["BASE_COLD"]
    first_request_prefix_variant: Literal["A"]
    first_request_token_count: Literal[899]
    first_request_token_sha256: Literal[
        "6b34448d083e68826cae84c0675876c18d7a70fab53299860b78f2a5a18922b0"
    ]
    first_request_payload_sha256: Literal[
        "b038763a5a2cb09f0a565dd7d11ac959c42c9c9a53f0f2d5e384edb6531c3a8e"
    ]
    pre_request_identity_persisted_before_model_request: Literal[True]
    raw_prompt_retained: Literal[False]
    raw_model_output_retained: Literal[False]
    model_requests_performed: Literal[1]
    model_loads_performed: Literal[1]
    worker_starts_performed: Literal[1]
    hidden_retries_performed: Literal[0]
    external_network_requests_performed: Literal[0]
    teardown_passed: Literal[True]
    scratch_cleanup_passed: Literal[True]
    p5_reached: Literal[False]
    p6_reached: Literal[False]
    p5_failure_established: Literal[False]
    p6_failure_established: Literal[False]
    full_remediation_confirmation_established: Literal[False]
    v5_tail_replacement_sufficient_remediation: Literal[False]
    composition_regression_family_remains_unresolved: Literal[True]
    remaining_composition_subfactor_identified: Literal[False]
    exact_failed_model_output_known: Literal[False]
    runtime_incompatibility_established: Literal[False]
    general_model_unreliability_established: Literal[False]
    guided_decoding_fix_authorized: Literal[False]
    new_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    unchanged_replay_authorized: Literal[False]
    causal_classification: Literal["REMEDIATION_INTERVENTION_INSUFFICIENT"]
    specific_classification: Literal[
        "V5_TAIL_REPLACEMENT_NOT_SUFFICIENT_FOR_COMPOSED_C3_OUTPUT_CONTRACT"
    ]
    causal_confidence: Literal[
        "COUNTERFACTUAL_REMEDIATION_EVIDENCE_WITH_REMAINING_FACTOR_AMBIGUITY"
    ]
    runtime_predecessor_metadata_preserved: Literal[True]
    predecessor_metadata_used_as_current_authority: Literal[False]
    custody_manifest_sha256: Literal[
        "9338d50ea9b2f83084edc3322f481d07fe92373ac77bcafd61f3b82e319f063a"
    ]
    governed_evidence_zip_sha256: Literal[
        "784b7c4a7f0ac03afec018b24f40cb19d3db0e8ecb0ada2f930b0fd1c66e5397"
    ]
    authorities: tuple[ArtifactReceipt, ...]
    non_claims: tuple[str, ...]
    next_gate: Literal["STATIC_REMAINING_COMPOSITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"]

    @model_validator(mode="after")
    def validate_record_boundary(self) -> Self:
        if self.completed_capabilities != ("C1", "C2"):
            raise ValueError("record completed capability sequence drifted")
        if len(self.authorities) != 9:
            raise ValueError("reconciliation authority count drifted")
        if len(self.non_claims) < 10:
            raise ValueError("reconciliation non-claim boundary is incomplete")
        return self


class ReconciliationReview(StrictModel):
    schema_version: Literal["1.0.0"]
    review_id: Literal[
        "auragateway-p4-p5-composition-remediation-c3-failure-reconciliation-v1-review"
    ]
    status: Literal["APPROVED_VALID_GOVERNED_REMEDIATION_FAILURE_RECONCILIATION"]
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: Literal[
        "9338d50ea9b2f83084edc3322f481d07fe92373ac77bcafd61f3b82e319f063a"
    ]
    remediation_success_claimed: Literal[False]
    p5_failure_claimed: Literal[False]
    p6_failure_claimed: Literal[False]
    exact_failed_output_claimed: Literal[False]
    new_execution_authorized: Literal[False]
    next_gate: Literal["STATIC_REMAINING_COMPOSITION_FACTOR_INSPECTION_BEFORE_NEW_EXECUTION_V1"]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_file(root: Path, relative: Path) -> Path:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_ARTIFACT_MISSING",
            "required reconciliation artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path


def _require_hash(root: Path, relative: Path, expected: str) -> Path:
    path = _require_file(root, relative)
    observed = _sha256_file(path)
    if observed != expected:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_IDENTITY_DRIFT",
            "reconciliation artifact byte identity drifted",
            relative.as_posix(),
        )
    return path


def _load_json_file(root: Path, relative: Path) -> dict[str, object]:
    path = _require_file(root, relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_JSON_INVALID",
            "reconciliation JSON is invalid",
            relative.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_JSON_INVALID",
            "reconciliation JSON root must be an object",
            relative.as_posix(),
        )
    return cast(dict[str, object], payload)


def _canonical_json_bytes(payload: BaseModel | dict[str, object]) -> bytes:
    value: object = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _receipt(root: Path, role: str, relative: Path) -> ArtifactReceipt:
    path = _require_file(root, relative)
    return ArtifactReceipt(
        role=role,
        path=relative.as_posix(),
        sha256=_sha256_file(path),
        size_bytes=path.stat().st_size,
    )


def _member_name_is_safe(name: str) -> bool:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute():
        return False
    if not path.parts:
        return False
    return all(part not in {"", ".", ".."} for part in path.parts)


def _open_validated_evidence_zip(root: Path) -> zipfile.ZipFile:
    path = _require_hash(root, EVIDENCE_ZIP_PATH, EVIDENCE_ZIP_SHA256)
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_ZIP_INVALID",
            "governed evidence ZIP is invalid",
            EVIDENCE_ZIP_PATH.as_posix(),
        ) from error

    normalized_names: set[str] = set()
    for info in archive.infolist():
        normalized = info.filename.replace("\\", "/")
        if not _member_name_is_safe(normalized):
            archive.close()
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_ZIP_UNSAFE",
                "governed evidence ZIP contains an unsafe member",
                normalized,
            )
        if normalized in normalized_names:
            archive.close()
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_ZIP_DUPLICATE",
                "governed evidence ZIP contains duplicate normalized members",
                normalized,
            )
        normalized_names.add(normalized)
    return archive


def _zip_json(archive: zipfile.ZipFile, member: str) -> dict[str, object]:
    matches = tuple(
        info for info in archive.infolist() if info.filename.replace("\\", "/") == member
    )
    if len(matches) != 1 or matches[0].is_dir():
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_ZIP_MEMBER_INVALID",
            "required evidence member cardinality drifted",
            member,
        )
    try:
        payload = json.loads(archive.read(matches[0]).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_ZIP_JSON_INVALID",
            "required evidence JSON member is invalid",
            member,
        ) from error
    if not isinstance(payload, dict):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_ZIP_JSON_INVALID",
            "required evidence JSON member root must be an object",
            member,
        )
    return cast(dict[str, object], payload)


def _validate_custody(root: Path) -> CustodyManifest:
    _require_hash(root, CUSTODY_MANIFEST_PATH, CUSTODY_MANIFEST_SHA256)
    custody = CustodyManifest.model_validate(_load_json_file(root, CUSTODY_MANIFEST_PATH))

    expected_roles = {
        "governed_evidence_zip": EVIDENCE_ZIP_PATH,
        "terminal_log": TERMINAL_LOG_PATH,
        "saved_notebook": NOTEBOOK_PATH,
        "execution_authorization": AUTHORIZATION_PATH,
        "execution_artifact_manifest": EXECUTION_MANIFEST_PATH,
        "platform_observation_receipt": PLATFORM_RECEIPT_PATH,
        "authorization_terminal_receipt": TERMINAL_RECEIPT_PATH,
    }
    by_role = {receipt.role: receipt for receipt in custody.members}
    if set(by_role) != set(expected_roles):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_CUSTODY_ROLE_DRIFT",
            "custody role inventory drifted",
            CUSTODY_MANIFEST_PATH.as_posix(),
        )

    for role, relative in expected_roles.items():
        receipt = by_role[role]
        if receipt.path != relative.as_posix():
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_CUSTODY_PATH_DRIFT",
                "custody member path drifted",
                relative.as_posix(),
            )
        path = _require_file(root, relative)
        if path.stat().st_size != receipt.size_bytes:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_CUSTODY_SIZE_DRIFT",
                "custody member size drifted",
                relative.as_posix(),
            )
        if _sha256_file(path) != receipt.sha256:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_CUSTODY_HASH_DRIFT",
                "custody member hash drifted",
                relative.as_posix(),
            )

    if by_role["governed_evidence_zip"].sha256 != EVIDENCE_ZIP_SHA256:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_EVIDENCE_IDENTITY_DRIFT",
            "governed evidence ZIP identity drifted",
            EVIDENCE_ZIP_PATH.as_posix(),
        )
    if by_role["terminal_log"].sha256 != TERMINAL_LOG_SHA256:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_LOG_IDENTITY_DRIFT",
            "terminal log identity drifted",
            TERMINAL_LOG_PATH.as_posix(),
        )
    if by_role["saved_notebook"].sha256 != NOTEBOOK_SHA256:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_NOTEBOOK_IDENTITY_DRIFT",
            "saved notebook identity drifted",
            NOTEBOOK_PATH.as_posix(),
        )
    return custody


def _validate_lifecycle(root: Path) -> None:
    authorization = _load_json_file(root, AUTHORIZATION_PATH)
    execution_manifest = _load_json_file(root, EXECUTION_MANIFEST_PATH)
    platform = _load_json_file(root, PLATFORM_RECEIPT_PATH)
    terminal = _load_json_file(root, TERMINAL_RECEIPT_PATH)

    for name, payload in (
        ("authorization", authorization),
        ("execution manifest", execution_manifest),
        ("platform receipt", platform),
        ("terminal receipt", terminal),
    ):
        if payload.get("transaction_id") != TRANSACTION_ID:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_TRANSACTION_DRIFT",
                f"{name} transaction identity drifted",
            )

    if platform.get("accelerator") != "T4_X2":
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_PLATFORM_DRIFT",
            "platform accelerator drifted",
            PLATFORM_RECEIPT_PATH.as_posix(),
        )
    if platform.get("allocated_gpu_count") != 2:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_PLATFORM_DRIFT",
            "platform GPU count drifted",
            PLATFORM_RECEIPT_PATH.as_posix(),
        )
    if platform.get("internet_enabled") is not False:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_PLATFORM_DRIFT",
            "platform Internet state drifted",
            PLATFORM_RECEIPT_PATH.as_posix(),
        )
    if platform.get("capability_source") != "KAGGLE_NOTEBOOK_SETTINGS_UI":
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_PLATFORM_DRIFT",
            "platform capability source drifted",
            PLATFORM_RECEIPT_PATH.as_posix(),
        )

    if terminal.get("disposition") != "CONSUMED":
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_TERMINAL_DRIFT",
            "terminal disposition drifted",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    if terminal.get("execution_outcome") != "FAILED":
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_TERMINAL_DRIFT",
            "terminal execution outcome drifted",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    if terminal.get("execution_attempted") is not True:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_TERMINAL_DRIFT",
            "terminal receipt no longer records attempted execution",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    if terminal.get("saved_version_id") != SAVED_VERSION_ID:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_TERMINAL_DRIFT",
            "terminal saved-version identity drifted",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    if terminal.get("evidence_zip_sha256") != EVIDENCE_ZIP_SHA256:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_TERMINAL_DRIFT",
            "terminal evidence identity drifted",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )
    if terminal.get("terminal_log_sha256") != TERMINAL_LOG_SHA256:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_TERMINAL_DRIFT",
            "terminal log binding drifted",
            TERMINAL_RECEIPT_PATH.as_posix(),
        )


def _evaluate_runtime_string_expression(node: ast.expr) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Constant):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_EXPRESSION_UNSAFE",
            "runtime instruction expression contains a non-string constant",
            REMEDIATED_RUNTIME_PATH.as_posix(),
        )
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _evaluate_runtime_string_expression(node.left) + _evaluate_runtime_string_expression(
            node.right
        )
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mult)
        and isinstance(node.left, ast.Constant)
        and isinstance(node.left.value, str)
        and isinstance(node.right, ast.Constant)
        and isinstance(node.right.value, int)
        and not isinstance(node.right.value, bool)
    ):
        return node.left.value * node.right.value
    raise ReconciliationError(
        "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_EXPRESSION_UNSAFE",
        "runtime instruction expression is outside the allowed static subset",
        REMEDIATED_RUNTIME_PATH.as_posix(),
    )


def _runtime_instruction_constants(text: str) -> dict[str, str]:
    try:
        tree = ast.parse(text)
    except SyntaxError as error:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_AST_INVALID",
            "remediated runtime source cannot be parsed",
            REMEDIATED_RUNTIME_PATH.as_posix(),
        ) from error

    target_names = {
        "SYSTEM_PROMPT",
        "SYNTHETIC_CACHE_CONTEXT_A",
        "SYNTHETIC_CACHE_CONTEXT_B",
    }
    values: dict[str, str] = {}

    for statement in tree.body:
        if not isinstance(statement, ast.Assign):
            continue
        if len(statement.targets) != 1:
            continue

        target = statement.targets[0]

        if not isinstance(target, ast.Name):
            continue
        if target.id not in target_names:
            continue
        if target.id in values:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_CONSTANT_DUPLICATE",
                "runtime instruction constant is assigned more than once",
                target.id,
            )

        values[target.id] = _evaluate_runtime_string_expression(statement.value)

    missing = target_names.difference(values)

    if missing:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_CONSTANT_MISSING",
            "one or more runtime instruction constants are unavailable",
            ",".join(sorted(missing)),
        )

    return values


def _validate_remediated_runtime(root: Path) -> None:
    runtime = _require_hash(
        root,
        REMEDIATED_RUNTIME_PATH,
        REMEDIATED_RUNTIME_SHA256,
    )
    text = runtime.read_text(encoding="utf-8")
    values = _runtime_instruction_constants(text)

    system_prompt = values["SYSTEM_PROMPT"]
    context_a = values["SYNTHETIC_CACHE_CONTEXT_A"]
    context_b = values["SYNTHETIC_CACHE_CONTEXT_B"]

    if system_prompt != ACCEPTED_V4_INSTRUCTION:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_REMEDIATION_DRIFT",
            "system prompt no longer equals the accepted V4 instruction",
            REMEDIATED_RUNTIME_PATH.as_posix(),
        )

    if not context_a.endswith(ACCEPTED_V4_INSTRUCTION):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_REMEDIATION_DRIFT",
            "cache-context A no longer ends with the accepted V4 instruction",
            REMEDIATED_RUNTIME_PATH.as_posix(),
        )

    if not context_b.endswith(ACCEPTED_V4_INSTRUCTION):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_REMEDIATION_DRIFT",
            "cache-context B no longer ends with the accepted V4 instruction",
            REMEDIATED_RUNTIME_PATH.as_posix(),
        )

    for name in (
        "SYSTEM_PROMPT",
        "SYNTHETIC_CACHE_CONTEXT_A",
        "SYNTHETIC_CACHE_CONTEXT_B",
    ):
        if OLD_V5_TAIL in values[name]:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_RUNTIME_REMEDIATION_DRIFT",
                "historical V5 cache-context tail reappeared",
                name,
            )


def _validate_bundle_manifest(
    archive: zipfile.ZipFile,
    bundle_manifest: dict[str, object],
) -> None:
    members = bundle_manifest.get("members")
    if not isinstance(members, list):
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_BUNDLE_MANIFEST_DRIFT",
            "evidence bundle manifest members are unavailable",
            "bundle_manifest_v1.json",
        )

    archive_by_name = {
        info.filename.replace("\\", "/"): info for info in archive.infolist() if not info.is_dir()
    }
    for raw in members:
        if not isinstance(raw, dict):
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_BUNDLE_MANIFEST_DRIFT",
                "evidence bundle manifest member is invalid",
                "bundle_manifest_v1.json",
            )
        path = raw.get("path")
        expected_sha = raw.get("sha256")
        expected_size = raw.get("size_bytes")
        if not isinstance(path, str) or path not in archive_by_name:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_BUNDLE_MANIFEST_DRIFT",
                "evidence bundle member path drifted",
                str(path),
            )
        info = archive_by_name[path]
        payload = archive.read(info)
        if expected_sha != _sha256_bytes(payload):
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_BUNDLE_HASH_DRIFT",
                "evidence bundle member hash drifted",
                path,
            )
        if expected_size != len(payload):
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_BUNDLE_SIZE_DRIFT",
                "evidence bundle member size drifted",
                path,
            )


def _validate_execution_evidence(root: Path) -> None:
    archive = _open_validated_evidence_zip(root)
    try:
        summary = _zip_json(
            archive,
            "p5_p6_exact_runtime_requalification_summary_v1.json",
        )
        failure = _zip_json(archive, "failure_report_v1.json")
        c3 = _zip_json(archive, "c3_single_request_report_v1.json")
        c4 = _zip_json(archive, "c4_output_contract_report_v1.json")
        journal = _zip_json(
            archive,
            "pre_request_token_identity_journal_v1.json",
        )
        p5 = _zip_json(archive, "p5_cache_behavior_report_v1.json")
        p6 = _zip_json(archive, "p6_worker_state_isolation_report_v1.json")
        teardown = _zip_json(archive, "worker_teardown_report_v1.json")
        cleanup = _zip_json(archive, "scratch_cleanup_report_v1.json")
        bundle = _zip_json(archive, "bundle_manifest_v1.json")
        _validate_bundle_manifest(archive, bundle)

        required_summary: dict[str, object] = {
            "status": "FAILED",
            "failed_capability": "C3",
            "failure_class": "REQUEST_EXECUTION_FAILURE",
            "completed_capabilities": ["C1", "C2"],
            "p5_decision": None,
            "p6_decision": None,
            "worker_teardown_status": "PASSED",
            "scratch_cleanup_status": "PASSED",
            "scratch_exists_after_cleanup": False,
            "executed_runtime_script_sha256": REMEDIATED_RUNTIME_SHA256,
            "network_access_permitted": False,
            "credentials_used": False,
            "customer_data_present": False,
        }
        for key, expected in required_summary.items():
            if summary.get(key) != expected:
                raise ReconciliationError(
                    "P4_P5_REMEDIATION_C3_RECONCILIATION_SUMMARY_DRIFT",
                    f"execution summary field drifted: {key}",
                    "p5_p6_exact_runtime_requalification_summary_v1.json",
                )

        counters = summary.get("counters")
        if not isinstance(counters, dict):
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_COUNTER_DRIFT",
                "execution counters are unavailable",
            )
        required_counters: dict[str, object] = {
            "model_requests": 1,
            "model_loads": 1,
            "worker_starts": 1,
            "hidden_retries": 0,
            "network_requests": 0,
            "runtime_install_attempts": 1,
            "runtime_import_closure_probes": 1,
            "kaggle_sessions": 1,
        }
        for key, expected in required_counters.items():
            if counters.get(key) != expected:
                raise ReconciliationError(
                    "P4_P5_REMEDIATION_C3_RECONCILIATION_COUNTER_DRIFT",
                    f"execution counter drifted: {key}",
                )

        required_failure: dict[str, object] = {
            "status": "FAILED",
            "failed_capability": "C3",
            "failure_class": "REQUEST_EXECUTION_FAILURE",
            "safe_message": "model response is not valid JSON",
            "failed_after": ["C1", "C2"],
            "teardown_status": "PASSED",
        }
        for key, expected in required_failure.items():
            if failure.get(key) != expected:
                raise ReconciliationError(
                    "P4_P5_REMEDIATION_C3_RECONCILIATION_FAILURE_DRIFT",
                    f"failure report field drifted: {key}",
                    "failure_report_v1.json",
                )

        if c3.get("status") != "FAILED" or c3.get("decision_state") != "FAIL":
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_C3_DRIFT",
                "C3 failure state drifted",
                "c3_single_request_report_v1.json",
            )
        if c4.get("status") != "NOT_RUN" or c4.get("blocked_by") != "C3":
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_C4_DRIFT",
                "C4 not-run boundary drifted",
                "c4_output_contract_report_v1.json",
            )
        if p5.get("status") != "NOT_RUN" or p5.get("decision_state") is not None:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_P5_DRIFT",
                "P5 not-reached boundary drifted",
                "p5_cache_behavior_report_v1.json",
            )
        if p6.get("status") != "NOT_RUN" or p6.get("decision_state") is not None:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_P6_DRIFT",
                "P6 not-reached boundary drifted",
                "p6_worker_state_isolation_report_v1.json",
            )
        if teardown.get("status") != "PASSED":
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_TEARDOWN_DRIFT",
                "worker teardown no longer passes",
                "worker_teardown_report_v1.json",
            )
        if cleanup.get("status") != "PASSED":
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_CLEANUP_DRIFT",
                "scratch cleanup no longer passes",
                "scratch_cleanup_report_v1.json",
            )

        entries = journal.get("entries")
        if not isinstance(entries, list) or len(entries) != 1:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_JOURNAL_DRIFT",
                "pre-request token journal cardinality drifted",
                "pre_request_token_identity_journal_v1.json",
            )
        entry = entries[0]
        if not isinstance(entry, dict):
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_JOURNAL_DRIFT",
                "pre-request token journal entry is invalid",
            )
        required_entry: dict[str, object] = {
            "request_ordinal": 1,
            "request_role": "BASE_COLD",
            "prefix_variant": "A",
            "token_count": 899,
            "token_sha256": PRE_REQUEST_TOKEN_SHA256,
            "payload_sha256": PRE_REQUEST_PAYLOAD_SHA256,
            "persisted_before_model_request": True,
        }
        for key, expected in required_entry.items():
            if entry.get(key) != expected:
                raise ReconciliationError(
                    "P4_P5_REMEDIATION_C3_RECONCILIATION_JOURNAL_DRIFT",
                    f"pre-request journal field drifted: {key}",
                )
        token_ids = entry.get("token_ids")
        if not isinstance(token_ids, list) or len(token_ids) != 899:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_JOURNAL_DRIFT",
                "pre-request token-id evidence drifted",
            )
        if any(isinstance(token, bool) or not isinstance(token, int) for token in token_ids):
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_JOURNAL_DRIFT",
                "pre-request token-id type drifted",
            )
        token_bytes = json.dumps(
            token_ids,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        if _sha256_bytes(token_bytes) != PRE_REQUEST_TOKEN_SHA256:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_JOURNAL_HASH_DRIFT",
                "pre-request token identity no longer recomputes",
            )
        if journal.get("raw_prompt_retained") is not False:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_PRIVACY_DRIFT",
                "raw prompt retention boundary drifted",
            )
        if journal.get("raw_model_output_retained") is not False:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_PRIVACY_DRIFT",
                "raw model-output retention boundary drifted",
            )
    finally:
        archive.close()


def _validate_terminal_log(root: Path) -> None:
    log = _require_hash(root, TERMINAL_LOG_PATH, TERMINAL_LOG_SHA256)
    text = log.read_text(encoding="utf-8", errors="replace")
    required_markers = (
        f'"transaction_id":"{TRANSACTION_ID}"',
        '"failed_capability":"C3"',
        '"failure_class":"REQUEST_EXECUTION_FAILURE"',
        '"model_requests":1',
        '"model_loads":1',
        '"worker_starts":1',
        '"p5_decision":null',
        '"p6_decision":null',
        '"status":"FAILED"',
    )
    for marker in required_markers:
        if marker not in text:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_LOG_DRIFT",
                "terminal log no longer contains required governed marker",
                TERMINAL_LOG_PATH.as_posix(),
            )


def _validate_all(root: Path) -> CustodyManifest:
    custody = _validate_custody(root)
    _validate_lifecycle(root)
    _validate_remediated_runtime(root)
    _validate_execution_evidence(root)
    _validate_terminal_log(root)
    _require_hash(root, NOTEBOOK_PATH, NOTEBOOK_SHA256)
    return custody


def build_record(repo_root: Path) -> ReconciliationRecord:
    root = repo_root.resolve()
    _validate_all(root)

    authorities = (
        _receipt(root, "custody_manifest", CUSTODY_MANIFEST_PATH),
        _receipt(root, "governed_evidence_zip", EVIDENCE_ZIP_PATH),
        _receipt(root, "terminal_log", TERMINAL_LOG_PATH),
        _receipt(root, "saved_notebook", NOTEBOOK_PATH),
        _receipt(root, "execution_authorization", AUTHORIZATION_PATH),
        _receipt(root, "execution_artifact_manifest", EXECUTION_MANIFEST_PATH),
        _receipt(root, "platform_observation_receipt", PLATFORM_RECEIPT_PATH),
        _receipt(root, "authorization_terminal_receipt", TERMINAL_RECEIPT_PATH),
        _receipt(root, "remediated_runtime", REMEDIATED_RUNTIME_PATH),
    )

    return ReconciliationRecord(
        schema_version="1.0.0",
        record_id=("auragateway-p4-p5-composition-remediation-c3-failure-reconciliation-v1"),
        status="RECONCILED_VALID_GOVERNED_REMEDIATION_FAILURE",
        transaction_id=TRANSACTION_ID,
        saved_version_id=SAVED_VERSION_ID,
        terminal_disposition="CONSUMED",
        execution_outcome="FAILED",
        technical_first_divergence="C3",
        technical_failure_class="REQUEST_EXECUTION_FAILURE",
        safe_failure_message="model response is not valid JSON",
        completed_capabilities=("C1", "C2"),
        runtime_installation_passed=True,
        runtime_import_closure_passed=True,
        model_construction_passed=True,
        worker_startup_passed=True,
        remediated_runtime_identity_verified=True,
        remediation_instruction_replacement_present=True,
        historical_v5_tail_absent=True,
        first_request_role="BASE_COLD",
        first_request_prefix_variant="A",
        first_request_token_count=899,
        first_request_token_sha256=PRE_REQUEST_TOKEN_SHA256,
        first_request_payload_sha256=PRE_REQUEST_PAYLOAD_SHA256,
        pre_request_identity_persisted_before_model_request=True,
        raw_prompt_retained=False,
        raw_model_output_retained=False,
        model_requests_performed=1,
        model_loads_performed=1,
        worker_starts_performed=1,
        hidden_retries_performed=0,
        external_network_requests_performed=0,
        teardown_passed=True,
        scratch_cleanup_passed=True,
        p5_reached=False,
        p6_reached=False,
        p5_failure_established=False,
        p6_failure_established=False,
        full_remediation_confirmation_established=False,
        v5_tail_replacement_sufficient_remediation=False,
        composition_regression_family_remains_unresolved=True,
        remaining_composition_subfactor_identified=False,
        exact_failed_model_output_known=False,
        runtime_incompatibility_established=False,
        general_model_unreliability_established=False,
        guided_decoding_fix_authorized=False,
        new_execution_authorized=False,
        authorization_reusable=False,
        unchanged_replay_authorized=False,
        causal_classification="REMEDIATION_INTERVENTION_INSUFFICIENT",
        specific_classification=(
            "V5_TAIL_REPLACEMENT_NOT_SUFFICIENT_FOR_COMPOSED_C3_OUTPUT_CONTRACT"
        ),
        causal_confidence=("COUNTERFACTUAL_REMEDIATION_EVIDENCE_WITH_REMAINING_FACTOR_AMBIGUITY"),
        runtime_predecessor_metadata_preserved=True,
        predecessor_metadata_used_as_current_authority=False,
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        governed_evidence_zip_sha256=EVIDENCE_ZIP_SHA256,
        authorities=authorities,
        non_claims=(
            "P5 did not run and no P5 failure is established.",
            "P6 did not run and no P6 failure is established.",
            "The exact malformed model output is not known.",
            "Generic Qwen unreliability is not established.",
            "Runtime incompatibility is not established.",
            "Model construction failure is not established.",
            "Worker startup failure is not established.",
            "V4 prompting in general is not disproven.",
            "The remaining causal composition subfactor is not identified.",
            "Guided decoding or JSON schema is not automatically authorized.",
            "No rerun or new execution is authorized.",
            "The consumed authorization is not reusable.",
        ),
        next_gate=NEXT_GATE,
    )


def expected_outputs(repo_root: Path) -> tuple[bytes, bytes]:
    record = build_record(repo_root)
    record_bytes = _canonical_json_bytes(record)
    review = ReconciliationReview(
        schema_version="1.0.0",
        review_id=("auragateway-p4-p5-composition-remediation-c3-failure-reconciliation-v1-review"),
        status="APPROVED_VALID_GOVERNED_REMEDIATION_FAILURE_RECONCILIATION",
        record_sha256=_sha256_bytes(record_bytes),
        custody_manifest_sha256=CUSTODY_MANIFEST_SHA256,
        remediation_success_claimed=False,
        p5_failure_claimed=False,
        p6_failure_claimed=False,
        exact_failed_output_claimed=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    return record_bytes, _canonical_json_bytes(review)


def generate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    record_bytes, review_bytes = expected_outputs(root)
    record_path = root / RECORD_PATH
    review_path = root / REVIEW_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)
    review_path.write_bytes(review_bytes)
    return {
        "status": "P4_P5_REMEDIATION_C3_FAILURE_RECONCILIATION_GENERATED",
        "record_path": RECORD_PATH.as_posix(),
        "record_sha256": _sha256_bytes(record_bytes),
        "review_path": REVIEW_PATH.as_posix(),
        "review_sha256": _sha256_bytes(review_bytes),
        "transaction_id": TRANSACTION_ID,
        "saved_version_id": SAVED_VERSION_ID,
        "p5_reached": False,
        "p6_reached": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    expected_record, expected_review = expected_outputs(root)
    record_path = _require_file(root, RECORD_PATH)
    review_path = _require_file(root, REVIEW_PATH)
    if record_path.read_bytes() != expected_record:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_RECORD_DRIFT",
            "checked-in reconciliation record drifted",
            RECORD_PATH.as_posix(),
        )
    if review_path.read_bytes() != expected_review:
        raise ReconciliationError(
            "P4_P5_REMEDIATION_C3_RECONCILIATION_REVIEW_DRIFT",
            "checked-in reconciliation review drifted",
            REVIEW_PATH.as_posix(),
        )
    record = ReconciliationRecord.model_validate_json(expected_record)
    review = ReconciliationReview.model_validate_json(expected_review)
    return {
        "status": "P4_P5_REMEDIATION_C3_FAILURE_RECONCILIATION_VALID",
        "record_sha256": _sha256_bytes(expected_record),
        "review_sha256": _sha256_bytes(expected_review),
        "transaction_id": record.transaction_id,
        "saved_version_id": record.saved_version_id,
        "technical_first_divergence": record.technical_first_divergence,
        "causal_classification": record.causal_classification,
        "v5_tail_replacement_sufficient_remediation": (
            record.v5_tail_replacement_sufficient_remediation
        ),
        "p5_failure_established": record.p5_failure_established,
        "p6_failure_established": record.p6_failure_established,
        "new_execution_authorized": review.new_execution_authorized,
        "next_gate": record.next_gate,
    }


def _build_parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.repo_root)
    try:
        result: dict[str, object] | None = None
        if args.command == "generate":
            result = generate(root)
        if args.command == "validate":
            result = validate(root)
        if result is None:
            raise ReconciliationError(
                "P4_P5_REMEDIATION_C3_RECONCILIATION_COMMAND_INVALID",
                "reconciliation command was not handled",
            )
        print(
            json.dumps(
                result,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
        return 0
    except (ReconciliationError, ValidationError) as error:
        payload: dict[str, object]
        if isinstance(error, ReconciliationError):
            payload = error.envelope()
        else:
            payload = {
                "error_code": "P4_P5_REMEDIATION_C3_RECONCILIATION_SCHEMA_INVALID",
                "safe_message": "reconciliation schema validation failed",
                "path": None,
            }
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

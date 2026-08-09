"""Single-use execution authorization for final offline verifier V4."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import Field, model_validator

from auragateway.local_abc.contracts import LocalABCContract
from auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4 import (
    VerifierImplementationError,
)
from auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4 import (
    validate_implementation as validate_v4_implementation,
)
from auragateway.local_abc.preflight_v3_exact_runtime_offline_compatibility_v4 import (
    validate_preexecution_contract as validate_v4_preexecution_contract,
)

IMPLEMENTATION_FEATURE_COMMIT: Final = "ed155dc32716041b333dd05d7244b4e19e23f9dd"
IMPLEMENTATION_MERGE_COMMIT: Final = "0fbc2430751502b46cdf5494a483e91713e059be"

ISSUER_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "preflight_v3_exact_runtime_offline_compatibility_v4_execution_authorization_v1.py"
)
ISSUER_TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_preflight_v3_exact_runtime_offline_compatibility_v4_execution_authorization_v1.py"
)
ISSUER_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_final_offline_verifier_v4_execution_authorization_v1.md"
)
ISSUER_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_"
    "execution_authorization_v1_record.json"
)

AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_"
    "execution_authorization_v1.json"
)
CONSUMPTION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_"
    "execution_authorization_consumption_v1.json"
)
ABANDONMENT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_"
    "execution_authorization_abandonment_v1.json"
)

V4_ARTIFACT_IDENTITIES: Final[dict[str, tuple[str, int]]] = {
    "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v4.ipynb": (
        "db4725b508322948ca4a9c29a48283f83ab047873a3eadb530e9f32e6a5490e9",
        93231,
    ),
    "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v4.py": (
        "354f66baebf1cc599f31ff179421fb78597d65581ac661b432964ce1a7967ccf",
        39241,
    ),
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v4.py": (
        "f594233d800c7c0b6e74dade939a4975aa0c0b4858f2e8203163a1ef5e3c6507",
        10179,
    ),
    (
        "docs/adr/2026-08-09-local-abc-preflight-v3-input-validation-"
        "reconciliation-and-final-offline-verifier-v4.md"
    ): (
        "49de6964e810a817a6d6d3ed0722975c13ab3d85070fea0b3239ffe56d2cc5a1",
        3419,
    ),
    (
        "docs/reports/AuraGateway_Preflight_V3_Input_Validation_Reconciliation_"
        "and_Final_Offline_Verifier_V4.md"
    ): (
        "92db2dfd8a175164c02c5b1b5d489a0e58e8cff849a428ade168ce6fdc6e3e46",
        2337,
    ),
    "docs/runbooks/local_abc_preflight_v3_final_exact_runtime_offline_verifier_v4.md": (
        "9f363be52a09a30d227f966179e6ffaf9d6284c73ace718222a12279558ea4aa",
        1699,
    ),
    (
        "benchmarks/local_abc/"
        "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_"
        "implementation_review.json"
    ): (
        "9e758985fc6310505ffcbc185524c0d1df0dc923f60974b9caeb10aa3250d735",
        7069,
    ),
    (
        "benchmarks/local_abc/"
        "auragateway_preflight_v3_exact_runtime_offline_compatibility_v4_"
        "implementation_record.json"
    ): (
        "86387aef3f486ba670784478fcbd54e0aec6d61a52726898d66f024c185f7ed6",
        4824,
    ),
}

AUTHORIZATION_ID: Final = (
    "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-execution-authorization-v1"
)
CONSUMPTION_ID: Final = (
    "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-"
    "execution-authorization-consumption-v1"
)
ABANDONMENT_ID: Final = (
    "auragateway-preflight-v3-exact-runtime-offline-compatibility-v4-"
    "execution-authorization-abandonment-v1"
)
CONFIRMATION_PHRASE: Final = (
    "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
    "FINAL_OFFLINE_VERIFIER_V4_EXECUTION"
)
MAXIMUM_AUTHORIZATION_WINDOW_MINUTES: Final = 240
DEFAULT_AUTHORIZATION_WINDOW_MINUTES: Final = 180
EXPECTED_OUTPUT_MEMBERS: Final = (
    "input_validation.json",
    "probe_records.json",
    "verification_summary.json",
    "evidence_manifest.json",
)
EXPECTED_EVIDENCE_ZIP: Final = (
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_evidence_v4.zip"
)
NEXT_GATE_AFTER_ISSUE: Final = "execute_one_governed_final_offline_verifier_v4_saved_version"
NEXT_GATE_AFTER_CONSUMPTION: Final = (
    "preserve_and_accept_or_classify_final_offline_verifier_v4_evidence"
)
NEXT_GATE_AFTER_ABANDONMENT: Final = (
    "reconcile_then_issue_fresh_final_offline_verifier_v4_authorization"
)


class AuthorizationIssuerError(RuntimeError):
    """Fail-closed authorization issuer error."""

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


class ErrorEnvelope(LocalABCContract):
    """Machine-readable CLI error."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ArtifactIdentity(LocalABCContract):
    """Identity of one bound artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class ExecutionLimits(LocalABCContract):
    """Hard ceiling for the one authorized verifier attempt."""

    maximum_authorization_window_minutes: Literal[240] = 240
    maximum_kaggle_sessions: Literal[1] = 1
    maximum_runtime_install_attempts: Literal[1] = 1
    maximum_native_import_closure_probes: Literal[1] = 1
    maximum_model_loads: Literal[0] = 0
    maximum_worker_starts: Literal[0] = 0
    maximum_model_requests: Literal[0] = 0
    maximum_benchmark_trajectory_requests: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_spend: Literal[0] = 0


class IssuerRecord(LocalABCContract):
    """Deterministic repository receipt for the authorization issuer."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-preflight-v3-final-offline-verifier-v4-execution-authorization-issuer-v1"
    ]
    status: Literal["FINAL_OFFLINE_VERIFIER_V4_EXECUTION_AUTHORIZATION_ISSUER_VALID"]
    bound_implementation_feature_commit: Literal["ed155dc32716041b333dd05d7244b4e19e23f9dd"]
    bound_implementation_merge_commit: Literal["0fbc2430751502b46cdf5494a483e91713e059be"]
    implementation_artifacts: tuple[ArtifactIdentity, ...]
    issuer_source: ArtifactIdentity
    issuer_tests: ArtifactIdentity
    issuer_runbook: ArtifactIdentity
    authorization_path: str
    consumption_path: str
    abandonment_path: str
    execution_limits: ExecutionLimits
    runtime_loader_enforcement_claimed: Literal[False]
    operator_procedure_required: Literal[True]
    pre_execution_compatibility_gate_required: Literal[True]
    pre_execution_compatibility_gate_validated_at_issue: Literal[False]
    historical_receipt_backprojection_permitted: Literal[False]
    live_authorization_issued: Literal[False]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]


class ExecutionAuthorization(LocalABCContract):
    """Short-lived single-use operator authorization."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    authorization_id: str
    lifecycle: Literal["ISSUED"]
    issued_at: datetime
    expires_at: datetime
    authorization_window_minutes: int = Field(ge=1, le=240)
    issuer_merge_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    implementation_feature_commit: Literal["ed155dc32716041b333dd05d7244b4e19e23f9dd"]
    implementation_merge_commit: Literal["0fbc2430751502b46cdf5494a483e91713e059be"]
    notebook_sha256: Literal["db4725b508322948ca4a9c29a48283f83ab047873a3eadb530e9f32e6a5490e9"]
    operator_confirmation: Literal[
        "I_CONFIRM_FRESH_KAGGLE_T4_X2_INTERNET_OFF_AND_AUTHORIZE_ONE_"
        "FINAL_OFFLINE_VERIFIER_V4_EXECUTION"
    ]
    observed_platform: Literal["T4_X2"]
    observed_gpu_count: Literal[2]
    observed_internet_enabled: Literal[False]
    execution_limits: ExecutionLimits
    expected_evidence_members: tuple[str, ...]
    expected_evidence_zip: Literal[
        "auragateway_preflight_v3_exact_runtime_offline_compatibility_evidence_v4.zip"
    ]
    preserve_saved_version: Literal[True]
    pre_execution_compatibility_gate_validated: Literal[True]
    historical_receipt_backprojection_permitted: Literal[False]
    offline_verifier_v4_execution_authorized: Literal[True]
    model_execution_authorized: Literal[False]
    p5_p6_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    authorization_reusable: Literal[False]
    next_gate: Literal["execute_one_governed_final_offline_verifier_v4_saved_version"]

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.expires_at <= self.issued_at:
            raise ValueError("authorization expiry must follow issuance")
        expected = self.issued_at + timedelta(minutes=self.authorization_window_minutes)
        if self.expires_at != expected:
            raise ValueError("authorization expiry does not match window")
        if self.expected_evidence_members != EXPECTED_OUTPUT_MEMBERS:
            raise ValueError("expected evidence member contract drifted")
        return self


class TerminalOutcome(StrEnum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class AuthorizationConsumption(LocalABCContract):
    """Terminal receipt after one execution attempt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    consumption_id: str
    authorization_id: str
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["CONSUMED"]
    outcome: TerminalOutcome
    consumed_at: datetime
    saved_version_id: int | None = Field(default=None, ge=1)
    evidence_zip_sha256: str | None = None
    authorization_reusable: Literal[False]
    offline_verifier_v4_execution_authorized: Literal[False]
    model_execution_authorized: Literal[False]
    p5_p6_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["preserve_and_accept_or_classify_final_offline_verifier_v4_evidence"]

    @model_validator(mode="after")
    def require_terminal_evidence(self) -> Self:
        if self.outcome in {TerminalOutcome.PASSED, TerminalOutcome.FAILED}:
            if self.saved_version_id is None:
                raise ValueError("terminal executed outcome requires saved version id")
            if self.evidence_zip_sha256 is None:
                raise ValueError("terminal executed outcome requires evidence ZIP SHA-256")
        if (
            self.evidence_zip_sha256 is not None
            and re_full_sha256(self.evidence_zip_sha256) is False
        ):
            raise ValueError("evidence ZIP SHA-256 is invalid")
        return self


class AuthorizationAbandonment(LocalABCContract):
    """Terminal receipt for unused authority."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    abandonment_id: str
    authorization_id: str
    authorization_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    lifecycle: Literal["ABANDONED"]
    abandoned_at: datetime
    reason: str = Field(min_length=1, max_length=500)
    authorization_reusable: Literal[False]
    offline_verifier_v4_execution_authorized: Literal[False]
    model_execution_authorized: Literal[False]
    p5_p6_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["reconcile_then_issue_fresh_final_offline_verifier_v4_authorization"]


def re_full_sha256(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(character in "0123456789abcdef" for character in value)


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _raise(
    error_code: str,
    safe_message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise AuthorizationIssuerError(
        error_code,
        safe_message,
        None if path is None else path.as_posix(),
        details,
    )


def _identity(repo_root: Path, path: Path) -> ArtifactIdentity:
    target = repo_root / path
    if not target.is_file():
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTH_ISSUER_ARTIFACT_MISSING",
            "required artifact is missing",
            path,
        )
    return ArtifactIdentity(
        path=path.as_posix(),
        sha256=_sha256_file(target),
        size_bytes=target.stat().st_size,
    )


def _git(repo_root: Path, *args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _require_git_success(
    repo_root: Path,
    error_code: str,
    safe_message: str,
    *args: str,
) -> str:
    returncode, stdout, stderr = _git(repo_root, *args)
    if returncode != 0:
        details = () if not stderr else (stderr,)
        _raise(error_code, safe_message, details=details)
    return stdout


def _require_bound_implementation(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    returncode, _, _ = _git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        IMPLEMENTATION_MERGE_COMMIT,
        "HEAD",
    )
    if returncode != 0:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTH_ISSUER_IMPLEMENTATION_NOT_ANCESTOR",
            "bound V4 implementation merge commit is not an ancestor of HEAD",
        )

    identities: list[ArtifactIdentity] = []
    for path_text, (expected_sha, expected_size) in V4_ARTIFACT_IDENTITIES.items():
        path = Path(path_text)
        identity = _identity(repo_root, path)
        if identity.sha256 != expected_sha or identity.size_bytes != expected_size:
            _raise(
                "FINAL_OFFLINE_VERIFIER_V4_AUTH_ISSUER_IMPLEMENTATION_DRIFT",
                "bound V4 implementation artifact identity drifted",
                path,
                (
                    f"expected_sha256={expected_sha}",
                    f"observed_sha256={identity.sha256}",
                    f"expected_size_bytes={expected_size}",
                    f"observed_size_bytes={identity.size_bytes}",
                ),
            )
        identities.append(identity)
    return tuple(identities)


def build_record(repo_root: Path) -> IssuerRecord:
    implementation = _require_bound_implementation(repo_root)
    return IssuerRecord(
        record_id=(
            "auragateway-preflight-v3-final-offline-verifier-v4-execution-authorization-issuer-v1"
        ),
        status="FINAL_OFFLINE_VERIFIER_V4_EXECUTION_AUTHORIZATION_ISSUER_VALID",
        bound_implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        bound_implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        implementation_artifacts=implementation,
        issuer_source=_identity(repo_root, ISSUER_SOURCE_PATH),
        issuer_tests=_identity(repo_root, ISSUER_TEST_PATH),
        issuer_runbook=_identity(repo_root, ISSUER_RUNBOOK_PATH),
        authorization_path=AUTHORIZATION_PATH.as_posix(),
        consumption_path=CONSUMPTION_PATH.as_posix(),
        abandonment_path=ABANDONMENT_PATH.as_posix(),
        execution_limits=ExecutionLimits(),
        runtime_loader_enforcement_claimed=False,
        operator_procedure_required=True,
        pre_execution_compatibility_gate_required=True,
        pre_execution_compatibility_gate_validated_at_issue=False,
        historical_receipt_backprojection_permitted=False,
        live_authorization_issued=False,
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
    )


def generate_record(repo_root: Path) -> dict[str, object]:
    record = build_record(repo_root)
    payload = _canonical_json_bytes(record.model_dump(mode="json"))
    target = repo_root / ISSUER_RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return {
        "status": record.status,
        "issuer_record_sha256": _sha256_bytes(payload),
        "live_authorization_issued": False,
        "next_gate": "merge_authorization_issuer_then_observe_and_issue",
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    expected = build_record(repo_root)
    expected_bytes = _canonical_json_bytes(expected.model_dump(mode="json"))
    target = repo_root / ISSUER_RECORD_PATH
    if not target.is_file():
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTH_ISSUER_RECORD_MISSING",
            "issuer record is missing",
            ISSUER_RECORD_PATH,
        )
    if target.read_bytes() != expected_bytes:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTH_ISSUER_RECORD_DRIFT",
            "issuer record is not canonical for current source/test/runbook bytes",
            ISSUER_RECORD_PATH,
        )
    return {
        "status": expected.status,
        "issuer_record_sha256": _sha256_bytes(expected_bytes),
        "bound_implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "next_expensive_execution_permitted": False,
        "next_gate": "merge_authorization_issuer_then_observe_and_issue",
    }


def _require_no_terminal_or_live_artifact(repo_root: Path) -> None:
    present = tuple(
        path.as_posix()
        for path in (AUTHORIZATION_PATH, CONSUMPTION_PATH, ABANDONMENT_PATH)
        if (repo_root / path).exists()
    )
    if present:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_LIFECYCLE_ALREADY_STARTED",
            "a live or terminal authorization artifact already exists",
            details=present,
        )


def _require_issue_repo_state(repo_root: Path, issuer_merge_commit: str) -> None:
    branch = _require_git_success(
        repo_root,
        "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect current branch",
        "branch",
        "--show-current",
    )
    if branch != "main":
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_NOT_ON_MAIN",
            "authorization issuance requires main",
        )

    head = _require_git_success(
        repo_root,
        "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect HEAD",
        "rev-parse",
        "HEAD",
    )
    origin_main = _require_git_success(
        repo_root,
        "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect origin/main",
        "rev-parse",
        "origin/main",
    )
    if head != issuer_merge_commit:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ISSUER_COMMIT_MISMATCH",
            "confirmed issuer merge commit does not equal HEAD",
        )
    if head != origin_main:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_MAIN_NOT_SYNCHRONIZED",
            "HEAD does not equal origin/main",
        )

    status = _require_git_success(
        repo_root,
        "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_GIT_STATE_FAILED",
        "unable to inspect repository status",
        "status",
        "--porcelain=v1",
        "-uall",
    )
    if status:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_REPOSITORY_NOT_CLEAN",
            "repository must be clean before authorization issuance",
        )

    returncode, _, _ = _git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        IMPLEMENTATION_MERGE_COMMIT,
        head,
    )
    if returncode != 0:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_IMPLEMENTATION_NOT_ANCESTOR",
            "bound V4 implementation is not contained by issuer main",
        )


def _require_v4_preexecution_contract(repo_root: Path) -> None:
    try:
        implementation = validate_v4_implementation(repo_root)
        contract = validate_v4_preexecution_contract(repo_root)
    except VerifierImplementationError as error:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_PREEXECUTION_CONTRACT_FAILED",
            "V4 implementation or pre-execution compatibility contract failed",
            details=(error.error_code, error.safe_message),
        )

    if implementation.get("status") != (
        "PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V4_IMPLEMENTATION_VALID"
    ):
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_PREEXECUTION_CONTRACT_FAILED",
            "V4 implementation validation status drifted",
        )
    if contract.get("status") != "PREFLIGHT_V3_V4_PREEXECUTION_CONTRACT_VALID":
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_PREEXECUTION_CONTRACT_FAILED",
            "V4 pre-execution compatibility status drifted",
        )
    if contract.get("historical_receipt_backprojection_permitted") is not False:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_PREEXECUTION_CONTRACT_FAILED",
            "historical receipt back-projection policy drifted",
        )
    if contract.get("runtime_execution_authorized") is not False:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_PREEXECUTION_CONTRACT_FAILED",
            "pre-execution contract unexpectedly authorizes runtime execution",
        )
    if contract.get("next_expensive_execution_permitted") is not False:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_PREEXECUTION_CONTRACT_FAILED",
            "pre-execution contract unexpectedly permits expensive execution",
        )


def issue_authorization(
    repo_root: Path,
    *,
    issuer_merge_commit: str,
    operator_confirmation: str,
    authorization_window_minutes: int,
    now: datetime | None = None,
) -> ExecutionAuthorization:
    validate_implementation(repo_root)
    _require_v4_preexecution_contract(repo_root)
    _require_no_terminal_or_live_artifact(repo_root)
    _require_issue_repo_state(repo_root, issuer_merge_commit)

    if operator_confirmation != CONFIRMATION_PHRASE:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_CONFIRMATION_INVALID",
            "exact operator confirmation phrase is required",
        )
    if not 1 <= authorization_window_minutes <= MAXIMUM_AUTHORIZATION_WINDOW_MINUTES:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_WINDOW_INVALID",
            "authorization window must be within the governed ceiling",
        )

    issued_at = (now or datetime.now(UTC)).replace(microsecond=0)
    expires_at = issued_at + timedelta(minutes=authorization_window_minutes)
    authorization = ExecutionAuthorization(
        authorization_id=AUTHORIZATION_ID,
        lifecycle="ISSUED",
        issued_at=issued_at,
        expires_at=expires_at,
        authorization_window_minutes=authorization_window_minutes,
        issuer_merge_commit=issuer_merge_commit,
        implementation_feature_commit=IMPLEMENTATION_FEATURE_COMMIT,
        implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        notebook_sha256=V4_ARTIFACT_IDENTITIES[
            "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v4.ipynb"
        ][0],
        operator_confirmation=CONFIRMATION_PHRASE,
        observed_platform="T4_X2",
        observed_gpu_count=2,
        observed_internet_enabled=False,
        execution_limits=ExecutionLimits(),
        expected_evidence_members=EXPECTED_OUTPUT_MEMBERS,
        expected_evidence_zip=EXPECTED_EVIDENCE_ZIP,
        preserve_saved_version=True,
        pre_execution_compatibility_gate_validated=True,
        historical_receipt_backprojection_permitted=False,
        offline_verifier_v4_execution_authorized=True,
        model_execution_authorized=False,
        p5_p6_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        authorization_reusable=False,
        next_gate=NEXT_GATE_AFTER_ISSUE,
    )
    payload = _canonical_json_bytes(authorization.model_dump(mode="json"))
    target = repo_root / AUTHORIZATION_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return authorization


def _read_authorization(repo_root: Path) -> tuple[ExecutionAuthorization, bytes]:
    target = repo_root / AUTHORIZATION_PATH
    if not target.is_file():
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_MISSING",
            "live authorization file is missing",
            AUTHORIZATION_PATH,
        )
    payload = target.read_bytes()
    try:
        parsed = json.loads(payload)
        authorization = ExecutionAuthorization.model_validate(parsed)
    except (json.JSONDecodeError, ValueError) as error:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_INVALID",
            "live authorization file is invalid",
            AUTHORIZATION_PATH,
            (str(error),),
        )
    canonical = _canonical_json_bytes(authorization.model_dump(mode="json"))
    if payload != canonical:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_NONCANONICAL",
            "live authorization bytes are not canonical",
            AUTHORIZATION_PATH,
        )
    return authorization, payload


def validate_live_authorization(
    repo_root: Path,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    authorization, payload = _read_authorization(repo_root)
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
        )
    observed_now = (now or datetime.now(UTC)).replace(microsecond=0)
    if observed_now >= authorization.expires_at:
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_EXPIRED",
            "live authorization has expired",
        )
    return {
        "authorization_id": authorization.authorization_id,
        "authorization_sha256": _sha256_bytes(payload),
        "issued_at": authorization.issued_at.isoformat(),
        "expires_at": authorization.expires_at.isoformat(),
        "pre_execution_compatibility_gate_validated": True,
        "offline_verifier_v4_execution_authorized": True,
        "model_execution_authorized": False,
        "p5_p6_execution_authorized": False,
        "next_gate": NEXT_GATE_AFTER_ISSUE,
    }


def consume_authorization(
    repo_root: Path,
    *,
    outcome: TerminalOutcome,
    saved_version_id: int | None,
    evidence_zip_sha256: str | None,
    now: datetime | None = None,
) -> AuthorizationConsumption:
    authorization, payload = _read_authorization(repo_root)
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
        )
    consumed_at = (now or datetime.now(UTC)).replace(microsecond=0)
    receipt = AuthorizationConsumption(
        consumption_id=CONSUMPTION_ID,
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_bytes(payload),
        lifecycle="CONSUMED",
        outcome=outcome,
        consumed_at=consumed_at,
        saved_version_id=saved_version_id,
        evidence_zip_sha256=evidence_zip_sha256,
        authorization_reusable=False,
        offline_verifier_v4_execution_authorized=False,
        model_execution_authorized=False,
        p5_p6_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_gate=NEXT_GATE_AFTER_CONSUMPTION,
    )
    receipt_payload = _canonical_json_bytes(receipt.model_dump(mode="json"))
    target = repo_root / CONSUMPTION_PATH
    target.write_bytes(receipt_payload)
    return receipt


def abandon_authorization(
    repo_root: Path,
    *,
    reason: str,
    now: datetime | None = None,
) -> AuthorizationAbandonment:
    authorization, payload = _read_authorization(repo_root)
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / ABANDONMENT_PATH).exists():
        _raise(
            "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ALREADY_TERMINAL",
            "authorization already has a terminal receipt",
        )
    abandoned_at = (now or datetime.now(UTC)).replace(microsecond=0)
    receipt = AuthorizationAbandonment(
        abandonment_id=ABANDONMENT_ID,
        authorization_id=authorization.authorization_id,
        authorization_sha256=_sha256_bytes(payload),
        lifecycle="ABANDONED",
        abandoned_at=abandoned_at,
        reason=reason,
        authorization_reusable=False,
        offline_verifier_v4_execution_authorized=False,
        model_execution_authorized=False,
        p5_p6_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_gate=NEXT_GATE_AFTER_ABANDONMENT,
    )
    receipt_payload = _canonical_json_bytes(receipt.model_dump(mode="json"))
    target = repo_root / ABANDONMENT_PATH
    target.write_bytes(receipt_payload)
    return receipt


def _print_error(error: AuthorizationIssuerError) -> None:
    envelope = ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    )
    print(
        _canonical_json_bytes(envelope.model_dump(mode="json")).decode("utf-8"),
        file=sys.stderr,
        end="",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "generate-record",
            "validate-implementation",
            "issue",
            "validate-live",
            "consume",
            "abandon",
        ),
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--issuer-merge-commit")
    parser.add_argument("--operator-confirm")
    parser.add_argument(
        "--window-minutes",
        type=int,
        default=DEFAULT_AUTHORIZATION_WINDOW_MINUTES,
    )
    parser.add_argument(
        "--outcome",
        choices=tuple(outcome.value for outcome in TerminalOutcome),
    )
    parser.add_argument("--saved-version-id", type=int)
    parser.add_argument("--evidence-zip-sha256")
    parser.add_argument("--reason")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    try:
        if args.command == "generate-record":
            result: object = generate_record(repo_root)
        elif args.command == "validate-implementation":
            result = validate_implementation(repo_root)
        elif args.command == "issue":
            if args.issuer_merge_commit is None:
                _raise(
                    "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ARGUMENT_MISSING",
                    "--issuer-merge-commit is required",
                )
            if args.operator_confirm is None:
                _raise(
                    "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ARGUMENT_MISSING",
                    "--operator-confirm is required",
                )
            result = issue_authorization(
                repo_root,
                issuer_merge_commit=args.issuer_merge_commit,
                operator_confirmation=args.operator_confirm,
                authorization_window_minutes=args.window_minutes,
            ).model_dump(mode="json")
        elif args.command == "validate-live":
            result = validate_live_authorization(repo_root)
        elif args.command == "consume":
            if args.outcome is None:
                _raise(
                    "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ARGUMENT_MISSING",
                    "--outcome is required",
                )
            result = consume_authorization(
                repo_root,
                outcome=TerminalOutcome(args.outcome),
                saved_version_id=args.saved_version_id,
                evidence_zip_sha256=args.evidence_zip_sha256,
            ).model_dump(mode="json")
        else:
            if args.reason is None:
                _raise(
                    "FINAL_OFFLINE_VERIFIER_V4_AUTHORIZATION_ARGUMENT_MISSING",
                    "--reason is required",
                )
            result = abandon_authorization(
                repo_root,
                reason=args.reason,
            ).model_dump(mode="json")
    except AuthorizationIssuerError as error:
        _print_error(error)
        return 2
    print(_canonical_json_bytes(result).decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Single-use activation machinery for Huawei credential readiness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Final, Literal, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.local_abc import j7l_huawei_credential_readiness_v1 as readiness

READINESS_PLAN_PATH = Path(
    "data/evals/quality/j7l-huawei-credential-readiness-v1/readiness_plan.json"
)
AUTHORIZATION_PATH = Path(
    "data/evals/quality/j7l-huawei-credential-readiness-authorization-v1/authorization.json"
)
CONSUMPTION_PATH = Path(
    ".local/auragateway/j7l-huawei-credential-readiness-v1/authorization_consumed.json"
)
RESULT_PATH = Path("data/evals/quality/j7l-huawei-credential-readiness-v1/readiness_result.json")
ACTIVATION_SOURCE_PATH = Path(
    "src/auragateway/local_abc/j7l_huawei_credential_readiness_activation_v1.py"
)
ACTIVATION_TEST_PATH = Path(
    "tests/unit/local_abc/test_j7l_huawei_credential_readiness_activation_v1.py"
)

_TIMEOUT_SECONDS: Final[Literal[60]] = 60
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ActivationError(RuntimeError):
    """Fail-closed readiness activation error."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class RemediationContextV1(FrozenModel):
    prior_boundary: Literal["j7l-glm52-named-tool-qualification-v1"]
    observed_failure_class: Literal["PROVIDER_AUTHENTICATION_FAILURE"]
    observed_failure_depth: Literal["MODEL_CATALOG_AUTHENTICATION_BOUNDARY"]
    observed_http_status: Literal[401]
    prior_authorization_reusable: Literal[False]
    prior_qualification_rerun_permitted: Literal[False]
    glm52_failure_established: Literal[False]
    named_tool_failure_established: Literal[False]


class ImplementationBindingV1(FrozenModel):
    source_base_commit: Literal["98d46c0396de94b99b3c2ceb93b9809474d9e2cc"]
    source_path: Literal["src/auragateway/local_abc/j7l_huawei_credential_readiness_v1.py"]
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    test_path: Literal["tests/unit/local_abc/test_j7l_huawei_credential_readiness_v1.py"]
    test_sha256: str = Field(pattern=_SHA256_PATTERN)
    activation_source_base_commit: Literal["2f84509d112c05156fe992bee9ebd355205ebb43"]
    activation_source_path: Literal[
        "src/auragateway/local_abc/j7l_huawei_credential_readiness_activation_v1.py"
    ]
    activation_source_sha256: str = Field(pattern=_SHA256_PATTERN)
    activation_test_path: Literal[
        "tests/unit/local_abc/test_j7l_huawei_credential_readiness_activation_v1.py"
    ]
    activation_test_sha256: str = Field(pattern=_SHA256_PATTERN)
    classification_core_implemented: Literal[True]
    real_network_adapter_implemented: Literal[True]
    live_activation_implemented: Literal[True]


class RequestBoundaryV1(FrozenModel):
    permitted_request_role: Literal["MODEL_CATALOG_READINESS_ONLY"]
    maximum_provider_http_requests: Literal[1]
    maximum_catalog_requests: Literal[1]
    maximum_model_inference_requests: Literal[0]
    automatic_retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    rerun_under_same_future_authorization_permitted: Literal[False]
    external_spend_ceiling_zar: Literal[0]
    request_body_present: Literal[False]
    j7l_case_content_permitted: Literal[False]
    jev_content_permitted: Literal[False]
    frozen_reference_answer_content_permitted: Literal[False]


class ClassificationContractV1(FrozenModel):
    http_200_exact_model_present: Literal["READY"]
    http_401: Literal["AUTHENTICATION_FAILED"]
    http_403: Literal["ENTITLEMENT_DENIED"]
    http_429: Literal["RATE_LIMITED"]
    http_5xx: Literal["PROVIDER_UNAVAILABLE"]
    transport_failure: Literal["TRANSPORT_FAILED"]
    malformed_http_200_catalog: Literal["CATALOG_INVALID"]
    http_200_exact_model_absent: Literal["MODEL_NOT_PRESENT"]


class PrivacyAndEvidenceV1(FrozenModel):
    credential_value_persistence_permitted: Literal[False]
    authorization_header_persistence_permitted: Literal[False]
    raw_provider_error_body_persistence_permitted: Literal[False]
    metadata_safe_result_required: Literal[True]
    raw_j7l_prompt_persistence_permitted: Literal[False]
    raw_jev_content_persistence_permitted: Literal[False]


class ClaimBoundaryV1(FrozenModel):
    ready_may_establish_catalog_authentication_at_observed_time: Literal[True]
    ready_may_establish_exact_model_catalog_visibility: Literal[True]
    proves_chat_inference_entitlement: Literal[False]
    proves_glm52_inference_success: Literal[False]
    proves_named_tool_transport: Literal[False]
    proves_thinking_disabled_behavior: Literal[False]
    proves_usage_accounting: Literal[False]
    proves_reference_judgment_quality: Literal[False]
    authorizes_named_tool_qualification: Literal[False]
    authorizes_j7l_reference_execution: Literal[False]
    authorizes_jev_execution: Literal[False]
    authorizes_binding_freeze: Literal[False]
    independently_proves_zero_spend: Literal[False]


class ReadinessPlanV1(FrozenModel):
    schema_version: Literal["1.0.0"]
    plan_id: Literal["j7l-huawei-credential-readiness-v1"]
    status: Literal["REVIEW_READY_INACTIVE"]
    remediation_context: RemediationContextV1
    provider: Literal["huawei_modelarts_maas"]
    region_label: Literal["ap-southeast-1"]
    exact_model_identifier: Literal["glm-5.2"]
    catalog_endpoint_url: Literal["https://api-ap-southeast-1.modelarts-maas.com/v2/models"]
    credential_env_name: Literal["HUAWEI_MAAS_API_KEY"]
    implementation_binding: ImplementationBindingV1
    request_boundary: RequestBoundaryV1
    classification_contract: ClassificationContractV1
    privacy_and_evidence: PrivacyAndEvidenceV1
    claim_boundary: ClaimBoundaryV1
    provider_call_authorized: Literal[False]
    credential_access_authorized: Literal[False]
    network_access_authorized: Literal[False]
    execution_command_available: Literal[False]
    activation_required: Literal[True]
    next_gate: Literal["AUTHORIZE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE_V1"]


class AuthorizationV1(FrozenModel):
    """Single-use future authority for exactly one readiness catalog request."""

    schema_version: Literal["1.0.0"]
    authorization_id: Literal["j7l-huawei-credential-readiness-authorization-v1"]
    status: Literal["active"]
    readiness_plan_path: Literal[
        "data/evals/quality/j7l-huawei-credential-readiness-v1/readiness_plan.json"
    ]
    readiness_plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    activation_source_path: Literal[
        "src/auragateway/local_abc/j7l_huawei_credential_readiness_activation_v1.py"
    ]
    activation_source_sha256: str = Field(pattern=_SHA256_PATTERN)
    confirmation_phrase: Literal["EXECUTE_J7L_HUAWEI_CREDENTIAL_READINESS_ONCE"]
    provider: Literal["huawei_modelarts_maas"]
    exact_model_identifier: Literal["glm-5.2"]
    credential_env_name: Literal["HUAWEI_MAAS_API_KEY"]
    provider_call_authorized: Literal[True]
    credential_access_authorized: Literal[True]
    network_access_authorized: Literal[True]
    execution_command_available: Literal[True]
    maximum_provider_http_requests: Literal[1]
    maximum_catalog_requests: Literal[1]
    maximum_model_inference_requests: Literal[0]
    zero_spend_confirmation_required: Literal[True]
    external_spend_ceiling_zar: Literal[0]
    automatic_retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    rerun_permitted: Literal[False]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    binding_freeze_permitted: Literal[False]
    authorization_consumed_on_first_network_attempt: Literal[True]
    clean_main_required: Literal[True]

    @model_validator(mode="after")
    def validate_request_budget(self) -> Self:
        expected = self.maximum_catalog_requests + self.maximum_model_inference_requests
        if self.maximum_provider_http_requests != expected:
            raise ValueError("provider HTTP ceiling must equal catalog plus inference ceiling")
        return self


class ReadinessExecutionResultV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    execution_status: Literal["J7L_HUAWEI_CREDENTIAL_READINESS_OBSERVED"] = (
        "J7L_HUAWEI_CREDENTIAL_READINESS_OBSERVED"
    )
    authorization_id: Literal["j7l-huawei-credential-readiness-authorization-v1"]
    authorization_sha256: str = Field(pattern=_SHA256_PATTERN)
    readiness_plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    readiness: readiness.CredentialReadinessResultV1
    zero_spend_operator_confirmed_before_execution: Literal[True] = True
    zero_spend_independently_proven: Literal[False] = False
    rerun_permitted: Literal[False] = False
    resume_permitted: Literal[False] = False
    next_gate: Literal["REVIEW_J7L_HUAWEI_CREDENTIAL_READINESS_RESULT_V1"] = (
        "REVIEW_J7L_HUAWEI_CREDENTIAL_READINESS_RESULT_V1"
    )


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> None:
        del req, fp, code, msg, headers, newurl
        return None


class UrllibHuaweiCatalogClient:
    """One-shot Huawei catalog adapter with default TLS and no retry behavior."""

    def __init__(self, *, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        self._timeout_seconds = timeout_seconds
        self._opener = urllib.request.build_opener(_NoRedirect())

    @staticmethod
    def _read_bounded(response: object) -> bytes:
        reader = getattr(response, "read", None)
        if reader is None:
            raise readiness.CredentialReadinessError("provider response is unreadable")
        body = cast(bytes, reader(_MAX_RESPONSE_BYTES + 1))
        if len(body) > _MAX_RESPONSE_BYTES:
            return b""
        return body

    def get_catalog(
        self,
        *,
        url: str,
        api_key: str,
    ) -> readiness.HttpResult:
        request = urllib.request.Request(
            url=url,
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        try:
            with self._opener.open(request, timeout=self._timeout_seconds) as response:
                return readiness.HttpResult(
                    status_code=int(response.status),
                    body=self._read_bounded(response),
                )
        except urllib.error.HTTPError as error:
            status_code = int(error.code)
            error.close()
            return readiness.HttpResult(status_code=status_code, body=b"")
        except (urllib.error.URLError, TimeoutError) as error:
            raise readiness.CredentialReadinessError("provider transport failed") from error


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _assert_hash(path: Path, expected_sha256: str, *, code: str) -> None:
    if _sha256_file(path) != expected_sha256:
        raise ActivationError(code, f"artifact identity drifted: {path.as_posix()}")


def _write_once(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _load_plan(repo_root: Path) -> ReadinessPlanV1:
    root = repo_root.resolve()
    plan = ReadinessPlanV1.model_validate(_load_json(root / READINESS_PLAN_PATH))
    binding = plan.implementation_binding
    identities = (
        (root / binding.source_path, binding.source_sha256, "CLASSIFIER_SOURCE_HASH_MISMATCH"),
        (root / binding.test_path, binding.test_sha256, "CLASSIFIER_TEST_HASH_MISMATCH"),
        (
            root / binding.activation_source_path,
            binding.activation_source_sha256,
            "ACTIVATION_SOURCE_HASH_MISMATCH",
        ),
        (
            root / binding.activation_test_path,
            binding.activation_test_sha256,
            "ACTIVATION_TEST_HASH_MISMATCH",
        ),
    )
    for path, expected_sha256, code in identities:
        _assert_hash(path, expected_sha256, code=code)
    return plan


def _load_authorization(
    repo_root: Path,
    plan: ReadinessPlanV1,
) -> AuthorizationV1:
    root = repo_root.resolve()
    auth = AuthorizationV1.model_validate(_load_json(root / AUTHORIZATION_PATH))
    plan_path = root / auth.readiness_plan_path
    _assert_hash(
        plan_path,
        auth.readiness_plan_sha256,
        code="READINESS_PLAN_HASH_MISMATCH",
    )
    _assert_hash(
        root / auth.activation_source_path,
        auth.activation_source_sha256,
        code="AUTHORIZED_ACTIVATION_SOURCE_HASH_MISMATCH",
    )
    if auth.provider != plan.provider:
        raise ActivationError("PROVIDER_IDENTITY_DRIFT", "authorized provider drifted")
    if auth.exact_model_identifier != plan.exact_model_identifier:
        raise ActivationError("MODEL_IDENTITY_DRIFT", "authorized model drifted")
    if auth.credential_env_name != plan.credential_env_name:
        raise ActivationError("CREDENTIAL_IDENTITY_DRIFT", "credential environment drifted")

    boundary = plan.request_boundary
    expected = (
        (auth.maximum_provider_http_requests, boundary.maximum_provider_http_requests),
        (auth.maximum_catalog_requests, boundary.maximum_catalog_requests),
        (auth.maximum_model_inference_requests, boundary.maximum_model_inference_requests),
        (auth.external_spend_ceiling_zar, boundary.external_spend_ceiling_zar),
    )
    if any(observed != planned for observed, planned in expected):
        raise ActivationError("AUTHORIZATION_BUDGET_DRIFT", "authorization budget drifted")
    return auth


def _git_text(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    if completed.returncode != 0:
        raise ActivationError("GIT_INSPECTION_FAILED", "required Git inspection failed")
    return completed.stdout.strip()


def _assert_live_git_boundary(repo_root: Path) -> None:
    if _git_text(repo_root, "branch", "--show-current") != "main":
        raise ActivationError("LIVE_BRANCH_INVALID", "live readiness requires branch main")
    tracked = _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked:
        raise ActivationError(
            "TRACKED_WORKTREE_DIRTY",
            "live readiness requires a clean tracked working tree",
        )


def _assert_fresh_execution(repo_root: Path) -> None:
    if (repo_root / CONSUMPTION_PATH).exists() or (repo_root / RESULT_PATH).exists():
        raise ActivationError(
            "EXECUTION_ALREADY_EXISTS",
            "readiness authorization is consumed or result evidence exists",
        )


def validate_activation(repo_root: Path) -> dict[str, object]:
    """Validate inactive machinery without reading credentials or using the network."""

    root = repo_root.resolve()
    plan = _load_plan(root)
    authorization_present = (root / AUTHORIZATION_PATH).is_file()
    authorization_id: str | None = None
    if authorization_present:
        authorization_id = _load_authorization(root, plan).authorization_id

    return {
        "schema_version": "1.0.0",
        "status": "J7L_HUAWEI_CREDENTIAL_READINESS_ACTIVATION_V1_PASS",
        "plan_id": plan.plan_id,
        "authorization_present": authorization_present,
        "authorization_id": authorization_id,
        "maximum_provider_http_requests": plan.request_boundary.maximum_provider_http_requests,
        "maximum_model_inference_requests": plan.request_boundary.maximum_model_inference_requests,
        "provider_call_performed": False,
        "credential_accessed": False,
        "network_access_performed": False,
        "consumption_evidence_exists": (root / CONSUMPTION_PATH).exists(),
        "readiness_result_exists": (root / RESULT_PATH).exists(),
    }


def _read_api_key(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise ActivationError("HUAWEI_MAAS_API_KEY_MISSING", "Huawei MaaS API key is unavailable")
    return value


def execute_readiness(
    repo_root: Path,
    *,
    confirmation: str,
    zero_spend_confirmed: bool,
    client: readiness.CatalogClient | None = None,
    live_boundary: Callable[[Path], None] = _assert_live_git_boundary,
) -> dict[str, object]:
    """Consume one authorization and perform exactly one catalog readiness request."""

    root = repo_root.resolve()
    plan = _load_plan(root)
    auth = _load_authorization(root, plan)

    if confirmation != auth.confirmation_phrase:
        raise ActivationError("CONFIRMATION_MISMATCH", "execution confirmation phrase is invalid")
    if not zero_spend_confirmed:
        raise ActivationError(
            "ZERO_SPEND_NOT_CONFIRMED",
            "R0 external-spend status must be confirmed before provider execution",
        )

    live_boundary(root)
    _assert_fresh_execution(root)
    api_key = _read_api_key(auth.credential_env_name)

    active_client = UrllibHuaweiCatalogClient() if client is None else client
    authorization_sha256 = _sha256_file(root / AUTHORIZATION_PATH)
    plan_sha256 = _sha256_file(root / READINESS_PLAN_PATH)
    _write_once(
        root / CONSUMPTION_PATH,
        {
            "schema_version": "1.0.0",
            "status": "AUTHORIZATION_CONSUMED",
            "authorization_id": auth.authorization_id,
            "authorization_sha256": authorization_sha256,
            "readiness_plan_sha256": plan_sha256,
            "consumed_at_utc": datetime.now(UTC).isoformat(),
            "provider_http_attempts_permitted_after_consumption": 1,
            "rerun_permitted": False,
            "resume_permitted": False,
        },
    )

    observed = readiness.probe_credential_readiness(api_key=api_key, client=active_client)
    public_result = ReadinessExecutionResultV1(
        authorization_id=auth.authorization_id,
        authorization_sha256=authorization_sha256,
        readiness_plan_sha256=plan_sha256,
        readiness=observed,
    )
    payload = cast(dict[str, object], public_result.model_dump(mode="json"))
    _write_once(root / RESULT_PATH, payload)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--repo-root", type=Path, required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", type=Path, required=True)
    run.add_argument("--confirmation", required=True)
    run.add_argument("--zero-spend-confirmed", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "validate":
            result = validate_activation(args.repo_root)
        else:
            result = execute_readiness(
                args.repo_root,
                confirmation=args.confirmation,
                zero_spend_confirmed=args.zero_spend_confirmed,
            )
    except (ActivationError, ValidationError, OSError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, ActivationError) else "ACTIVATION_FAILED"
        safe_message = (
            error.safe_message
            if isinstance(error, ActivationError)
            else "Huawei credential-readiness activation failed"
        )
        print(
            json.dumps(
                {"error_code": code, "safe_message": safe_message},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, ensure_ascii=True, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

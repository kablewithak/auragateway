"""Fresh single-use execution lineage for GLM-5.2 named-tool requalification."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.j7l_glm52_named_tool_qualification_v1 import (
    J7LGLM52NamedToolQualificationPlanV1,
)
from auragateway.local_abc import j7l_glm52_named_tool_qualification_activation_v1 as v1_activation
from auragateway.local_abc import j7l_glm52_named_tool_qualification_v1 as v1_design

REQUALIFICATION_PLAN_PATH = Path(
    "data/evals/quality/j7l-glm52-named-tool-requalification-v2/requalification_plan.json"
)
AUTHORIZATION_PATH = Path(
    "data/evals/quality/j7l-glm52-named-tool-requalification-authorization-v2/authorization.json"
)
ACTIVATION_SOURCE_PATH = Path(
    "src/auragateway/local_abc/j7l_glm52_named_tool_requalification_v2.py"
)

_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class ActivationError(RuntimeError):
    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ExecutionBudgetV2(FrozenModel):
    maximum_provider_http_requests: Literal[2]
    maximum_catalog_requests: Literal[1]
    maximum_model_inference_requests: Literal[1]
    qualification_token_allowance: Literal[20000]
    automatic_retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    rerun_permitted: Literal[False]
    external_spend_ceiling_zar: Literal[0]
    paid_fallback_permitted: Literal[False]


class EvidencePathsV2(FrozenModel):
    consumption_path: str
    catalog_raw_path: str
    chat_raw_path: str
    protected_raw_response_path: str
    protected_parsed_response_path: str
    public_result_path: str


class FrozenScienceV2(FrozenModel):
    source_request_contract_reused_unchanged: Literal[True]
    source_synthetic_prompt_recipe_reused_unchanged: Literal[True]
    source_named_tool_contract_reused_unchanged: Literal[True]
    source_model_projection_reused_unchanged: Literal[True]
    source_acceptance_requirements_reused_unchanged: Literal[True]


class RequalificationPlanV2(FrozenModel):
    schema_version: Literal["1.0.0"]
    plan_id: Literal["j7l-glm52-named-tool-requalification-v2"]
    status: Literal["REVIEW_READY_INACTIVE"]
    purpose: Literal["fresh_execution_lineage_after_successful_huawei_credential_readiness"]
    source_qualification_plan_path: str
    source_qualification_plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    readiness_result_path: str
    readiness_result_sha256: str = Field(pattern=_SHA256_PATTERN)
    required_readiness_status: Literal["READY"]
    prior_authorization_id: Literal["j7l-glm52-named-tool-qualification-authorization-v1"]
    prior_authorization_reusable: Literal[False]
    prior_execution_lineage_reusable: Literal[False]
    fresh_authorization_id: Literal["j7l-glm52-named-tool-requalification-authorization-v2"]
    provider: Literal["huawei_modelarts_maas"]
    exact_model_identifier: Literal["glm-5.2"]
    credential_env_name: Literal["HUAWEI_MAAS_API_KEY"]
    execution_budget: ExecutionBudgetV2
    evidence_paths: EvidencePathsV2
    frozen_science: FrozenScienceV2
    provider_call_authorized: Literal[False]
    credential_access_authorized: Literal[False]
    network_access_authorized: Literal[False]
    execution_command_available_under_current_authority: Literal[False]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    binding_freeze_permitted: Literal[False]
    activation_required: Literal[True]
    next_gate: Literal["AUTHORIZE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE_V2"]


class AuthorizationV2(FrozenModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal["j7l-glm52-named-tool-requalification-authorization-v2"]
    status: Literal["active"]
    requalification_plan_path: str
    requalification_plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    source_qualification_plan_path: str
    source_qualification_plan_sha256: str = Field(pattern=_SHA256_PATTERN)
    readiness_result_path: str
    readiness_result_sha256: str = Field(pattern=_SHA256_PATTERN)
    activation_source_path: str
    activation_source_sha256: str = Field(pattern=_SHA256_PATTERN)
    confirmation_phrase: Literal["EXECUTE_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_ONCE"]
    provider: Literal["huawei_modelarts_maas"]
    exact_model_identifier: Literal["glm-5.2"]
    credential_env_name: Literal["HUAWEI_MAAS_API_KEY"]
    provider_call_authorized: Literal[True]
    credential_access_authorized: Literal[True]
    network_access_authorized: Literal[True]
    execution_command_available: Literal[True]
    maximum_provider_http_requests: Literal[2]
    maximum_catalog_requests: Literal[1]
    maximum_model_inference_requests: Literal[1]
    qualification_token_allowance: Literal[20000]
    zero_spend_confirmation_required: Literal[True]
    external_spend_ceiling_zar: Literal[0]
    paid_fallback_permitted: Literal[False]
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
        if self.maximum_provider_http_requests != (
            self.maximum_catalog_requests + self.maximum_model_inference_requests
        ):
            raise ValueError("provider HTTP ceiling must equal catalog plus inference ceiling")
        return self


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
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _validate_ready_result(payload: object) -> None:
    if not isinstance(payload, Mapping):
        raise ActivationError("READINESS_RESULT_SHAPE_INVALID", "readiness result root is invalid")
    readiness = payload.get("readiness")
    if not isinstance(readiness, Mapping):
        raise ActivationError("READINESS_RESULT_SHAPE_INVALID", "readiness observation is missing")
    required = {
        "status": "READY",
        "exact_model_identifier": "glm-5.2",
        "catalog_model_present": True,
        "provider_http_requests_attempted": 1,
        "catalog_requests_attempted": 1,
        "model_inference_requests_attempted": 0,
        "automatic_retries_performed": 0,
    }
    for key, expected in required.items():
        if readiness.get(key) != expected:
            raise ActivationError(
                "READINESS_RESULT_NOT_QUALIFIED",
                f"readiness field {key} is not qualified",
            )
    if payload.get("rerun_permitted") is not False:
        raise ActivationError("READINESS_RESULT_NOT_TERMINAL", "readiness rerun boundary drifted")
    if payload.get("resume_permitted") is not False:
        raise ActivationError("READINESS_RESULT_NOT_TERMINAL", "readiness resume boundary drifted")


def _load_plan(
    repo_root: Path,
) -> tuple[RequalificationPlanV2, J7LGLM52NamedToolQualificationPlanV1]:
    root = repo_root.resolve()
    plan = RequalificationPlanV2.model_validate(_load_json(root / REQUALIFICATION_PLAN_PATH))
    source_plan_path = root / plan.source_qualification_plan_path
    _assert_hash(
        source_plan_path,
        plan.source_qualification_plan_sha256,
        code="SOURCE_QUALIFICATION_PLAN_HASH_MISMATCH",
    )
    readiness_path = root / plan.readiness_result_path
    _assert_hash(
        readiness_path,
        plan.readiness_result_sha256,
        code="READINESS_RESULT_HASH_MISMATCH",
    )
    _validate_ready_result(_load_json(readiness_path))
    source_plan = v1_design.load_plan(root)
    if source_plan.provider != plan.provider:
        raise ActivationError("PROVIDER_IDENTITY_DRIFT", "provider identity drifted")
    if source_plan.exact_model_identifier != plan.exact_model_identifier:
        raise ActivationError("MODEL_IDENTITY_DRIFT", "model identity drifted")
    return plan, source_plan


def _load_authorization(repo_root: Path, plan: RequalificationPlanV2) -> AuthorizationV2:
    root = repo_root.resolve()
    auth = AuthorizationV2.model_validate(_load_json(root / AUTHORIZATION_PATH))
    identities = (
        (root / auth.requalification_plan_path, auth.requalification_plan_sha256),
        (root / auth.source_qualification_plan_path, auth.source_qualification_plan_sha256),
        (root / auth.readiness_result_path, auth.readiness_result_sha256),
        (root / auth.activation_source_path, auth.activation_source_sha256),
    )
    for path, expected_sha256 in identities:
        _assert_hash(path, expected_sha256, code="AUTHORIZED_ARTIFACT_HASH_MISMATCH")
    if auth.authorization_id != plan.fresh_authorization_id:
        raise ActivationError("AUTHORIZATION_IDENTITY_DRIFT", "authorization identity drifted")
    if auth.provider != plan.provider:
        raise ActivationError("PROVIDER_IDENTITY_DRIFT", "provider identity drifted")
    if auth.exact_model_identifier != plan.exact_model_identifier:
        raise ActivationError("MODEL_IDENTITY_DRIFT", "model identity drifted")
    budget = plan.execution_budget
    expected = (
        (auth.maximum_provider_http_requests, budget.maximum_provider_http_requests),
        (auth.maximum_catalog_requests, budget.maximum_catalog_requests),
        (auth.maximum_model_inference_requests, budget.maximum_model_inference_requests),
        (auth.qualification_token_allowance, budget.qualification_token_allowance),
        (auth.external_spend_ceiling_zar, budget.external_spend_ceiling_zar),
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
        raise ActivationError("LIVE_BRANCH_INVALID", "live requalification requires main")
    tracked = _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked:
        raise ActivationError(
            "TRACKED_WORKTREE_DIRTY",
            "live requalification requires a clean tracked working tree",
        )


def _evidence_paths(repo_root: Path, plan: RequalificationPlanV2) -> tuple[Path, ...]:
    p = plan.evidence_paths
    return (
        repo_root / p.consumption_path,
        repo_root / p.catalog_raw_path,
        repo_root / p.chat_raw_path,
        repo_root / p.protected_raw_response_path,
        repo_root / p.protected_parsed_response_path,
        repo_root / p.public_result_path,
    )


def _assert_fresh_execution(repo_root: Path, plan: RequalificationPlanV2) -> None:
    if any(path.exists() for path in _evidence_paths(repo_root, plan)):
        raise ActivationError(
            "EXECUTION_ALREADY_EXISTS",
            "v2 authority is consumed or v2 evidence exists",
        )


def validate_activation(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    plan, source_plan = _load_plan(root)
    authorization_present = (root / AUTHORIZATION_PATH).is_file()
    authorization_id = None
    if authorization_present:
        authorization_id = _load_authorization(root, plan).authorization_id
    design_result = v1_design.dry_run(root)
    return {
        "schema_version": "1.0.0",
        "status": "J7L_GLM52_NAMED_TOOL_REQUALIFICATION_V2_PASS",
        "plan_id": plan.plan_id,
        "source_plan_id": source_plan.plan_id,
        "authorization_present": authorization_present,
        "authorization_id": authorization_id,
        "design_status": design_result["status"],
        "readiness_status": "READY",
        "provider_call_performed": False,
        "credential_accessed": False,
        "network_access_performed": False,
    }


def execute_requalification(
    repo_root: Path,
    *,
    confirmation: str,
    zero_spend_confirmed: bool,
    client: v1_activation.HttpClient | None = None,
    live_boundary: Callable[[Path], None] = _assert_live_git_boundary,
) -> dict[str, object]:
    root = repo_root.resolve()
    plan, source_plan = _load_plan(root)
    auth = _load_authorization(root, plan)

    if confirmation != auth.confirmation_phrase:
        raise ActivationError("CONFIRMATION_MISMATCH", "execution confirmation phrase is invalid")
    if not zero_spend_confirmed:
        raise ActivationError(
            "ZERO_SPEND_NOT_CONFIRMED",
            "R0 external-spend status must be confirmed before provider execution",
        )

    live_boundary(root)
    _assert_fresh_execution(root, plan)
    v1_design.load_assets(root)
    request_body = v1_design.build_chat_request_body(root)

    api_key = os.environ.get(auth.credential_env_name)
    if api_key is None or not api_key.strip():
        raise ActivationError("HUAWEI_MAAS_API_KEY_MISSING", "Huawei MaaS API key is unavailable")

    auth_sha = _sha256_file(root / AUTHORIZATION_PATH)
    p = plan.evidence_paths
    _write_once(
        root / p.consumption_path,
        {
            "schema_version": "1.0.0",
            "status": "AUTHORIZATION_CONSUMED",
            "authorization_id": auth.authorization_id,
            "authorization_sha256": auth_sha,
            "consumed_at_utc": datetime.now(UTC).isoformat(),
            "provider_http_attempts_permitted_after_consumption": 2,
            "rerun_permitted": False,
            "resume_permitted": False,
        },
    )

    active_client = v1_activation.UrllibHuaweiClient() if client is None else client
    catalog = active_client.get(source_plan.catalog_endpoint_url, api_key, 60)
    if catalog.status_code != 200:
        raise ActivationError(
            "CATALOG_HTTP_STATUS_INVALID",
            f"catalog returned HTTP {catalog.status_code}",
        )
    _write_once(
        root / p.catalog_raw_path,
        v1_activation._protected_response(catalog, request_role="model_catalog"),
    )
    catalog_payload = v1_activation._json_mapping(catalog.body, role="catalog")
    entry = v1_activation._catalog_entry(
        catalog_payload,
        model_id=source_plan.exact_model_identifier,
    )
    version_field, version_value = v1_activation._version_or_revision(entry)

    chat = active_client.post_json(source_plan.chat_endpoint_url, api_key, request_body, 60)
    if chat.status_code != 200:
        raise ActivationError(
            "CHAT_HTTP_STATUS_INVALID",
            f"chat completion returned HTTP {chat.status_code}",
        )
    _write_once(
        root / p.chat_raw_path,
        v1_activation._protected_response(chat, request_role="synthetic_named_tool"),
    )
    chat_payload = v1_activation._json_mapping(chat.body, role="chat")
    observation = v1_activation._validate_chat_response(chat_payload, plan=source_plan)

    _write_once(
        root / p.protected_raw_response_path,
        {
            "schema_version": "1.0.0",
            "authorization_sha256": auth_sha,
            "source_qualification_plan_sha256": plan.source_qualification_plan_sha256,
            "readiness_result_sha256": plan.readiness_result_sha256,
            "catalog": v1_activation._protected_response(
                catalog,
                request_role="model_catalog",
            ),
            "chat": v1_activation._protected_response(
                chat,
                request_role="synthetic_named_tool",
            ),
        },
    )
    _write_once(
        root / p.protected_parsed_response_path,
        {
            "schema_version": "1.0.0",
            "catalog_model_entry": dict(entry),
            "provider_version_or_revision_field": version_field,
            "provider_version_or_revision_value": version_value,
            "chat_observation": observation,
        },
    )

    result = {
        "schema_version": "1.0.0",
        "status": "J7L_GLM52_NAMED_TOOL_REQUALIFICATION_V2_PASS",
        "authorization_id": auth.authorization_id,
        "authorization_sha256": auth_sha,
        "source_qualification_plan_sha256": plan.source_qualification_plan_sha256,
        "readiness_result_sha256": plan.readiness_result_sha256,
        "provider": source_plan.provider,
        "requested_model": source_plan.exact_model_identifier,
        "catalog_contains_exact_model_id": True,
        "provider_version_or_revision_exposed": version_value is not None,
        "provider_version_or_revision_field": version_field,
        "provider_version_or_revision_value": version_value,
        "returned_model": observation["returned_model"],
        "returned_model_matches_requested": observation["returned_model_matches_requested"],
        "provider_http_request_count": 2,
        "catalog_request_count": 1,
        "model_inference_request_count": 1,
        "named_tool_transport_qualified": True,
        "thinking_disabled_observed": True,
        "usage_accounting_observed": True,
        "prompt_tokens": observation["prompt_tokens"],
        "completion_tokens": observation["completion_tokens"],
        "total_tokens": observation["total_tokens"],
        "reasoning_tokens": observation["reasoning_tokens"],
        "qualification_token_allowance": auth.qualification_token_allowance,
        "zero_spend_operator_confirmed_before_execution": True,
        "zero_spend_independently_proven": False,
        "j7l_reference_request_performed": False,
        "jev_request_performed": False,
        "binding_freeze_performed": False,
        "rerun_permitted": False,
        "resume_permitted": False,
        "next_gate": "REVIEW_J7L_GLM52_NAMED_TOOL_REQUALIFICATION_RESULT_V2",
    }
    _write_once(root / p.public_result_path, result)
    return result


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
        result = (
            validate_activation(args.repo_root)
            if args.command == "validate"
            else execute_requalification(
                args.repo_root,
                confirmation=args.confirmation,
                zero_spend_confirmed=args.zero_spend_confirmed,
            )
        )
    except (
        ActivationError,
        v1_activation.ActivationError,
        ValidationError,
        OSError,
        json.JSONDecodeError,
    ) as error:
        code = error.code if hasattr(error, "code") else "ACTIVATION_FAILED"
        safe_message = (
            error.safe_message
            if hasattr(error, "safe_message")
            else "GLM-5.2 named-tool requalification activation failed"
        )
        print(
            json.dumps(
                {"error_code": code, "safe_message": safe_message},
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

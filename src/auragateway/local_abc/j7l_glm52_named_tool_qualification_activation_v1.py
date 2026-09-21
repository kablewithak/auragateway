"""Single-use live activation for the GLM-5.2 named-tool qualification."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol, Self, cast

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from auragateway.contracts.j7l_glm52_named_tool_qualification_v1 import (
    J7LGLM52NamedToolQualificationPlanV1,
)
from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceToolArgumentsV1,
)
from auragateway.local_abc import j7l_glm52_named_tool_qualification_v1 as design

AUTHORIZATION_PATH = Path(
    "data/evals/quality/j7l-glm52-named-tool-qualification-authorization-v1/authorization.json"
)
CONSUMPTION_PATH = Path(
    ".local/auragateway/j7l-glm52-named-tool-qualification-v1/authorization_consumed.json"
)
CATALOG_RAW_PATH = Path(
    ".local/auragateway/j7l-glm52-named-tool-qualification-v1/catalog_raw_response.json"
)
CHAT_RAW_PATH = Path(
    ".local/auragateway/j7l-glm52-named-tool-qualification-v1/chat_raw_response.json"
)

_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
_TIMEOUT_SECONDS = 60


class ActivationError(RuntimeError):
    """Fail-closed activation or live qualification error."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class AuthorizationV1(BaseModel):
    """Single-use execution authority for the frozen qualification plan."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    authorization_id: Literal["j7l-glm52-named-tool-qualification-authorization-v1"]
    status: Literal["active"]
    qualification_plan_path: Literal[
        "data/evals/quality/j7l-glm52-named-tool-qualification-v1/qualification_plan.json"
    ]
    qualification_plan_sha256: str
    qualification_design_merge_commit: Literal["2d457cb99f6ec62300f9e807f134dc7000a7670c"]
    confirmation_phrase: Literal["EXECUTE_J7L_GLM52_NAMED_TOOL_QUALIFICATION_ONCE"]
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

    @field_validator("qualification_plan_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("qualification_plan_sha256 must be lowercase SHA-256")
        return value

    @model_validator(mode="after")
    def validate_bounds(self) -> Self:
        if self.maximum_provider_http_requests != (
            self.maximum_catalog_requests + self.maximum_model_inference_requests
        ):
            raise ValueError("provider HTTP ceiling must equal catalog plus inference ceiling")
        return self


@dataclass(frozen=True)
class HttpResult:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class HttpClient(Protocol):
    def get(self, url: str, api_key: str, timeout_seconds: int) -> HttpResult:
        """Perform one GET without retries."""

    def post_json(
        self,
        url: str,
        api_key: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> HttpResult:
        """Perform one JSON POST without retries."""


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


class UrllibHuaweiClient:
    """Minimal Huawei MaaS HTTP client with default TLS verification and no retry."""

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener(_NoRedirect())

    @staticmethod
    def _read_bounded(response: object) -> bytes:
        reader = getattr(response, "read", None)
        if reader is None:
            raise ActivationError("HTTP_RESPONSE_INVALID", "HTTP response is unreadable")
        body = cast(bytes, reader(_MAX_RESPONSE_BYTES + 1))
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ActivationError(
                "HTTP_RESPONSE_TOO_LARGE",
                "provider response exceeded the protected response byte ceiling",
            )
        return body

    def _send(self, request: urllib.request.Request, timeout_seconds: int) -> HttpResult:
        try:
            with self._opener.open(request, timeout=timeout_seconds) as response:
                body = self._read_bounded(response)
                headers = {str(key).lower(): str(value) for key, value in response.headers.items()}
                return HttpResult(
                    status_code=int(response.status),
                    headers=headers,
                    body=body,
                )
        except urllib.error.HTTPError as error:
            raise ActivationError(
                "PROVIDER_HTTP_ERROR",
                f"provider returned HTTP {error.code}",
            ) from error
        except urllib.error.URLError as error:
            raise ActivationError(
                "PROVIDER_TRANSPORT_ERROR",
                "provider transport failed",
            ) from error

    def get(self, url: str, api_key: str, timeout_seconds: int) -> HttpResult:
        request = urllib.request.Request(
            url=url,
            headers={"Authorization": f"Bearer {api_key}"},
            method="GET",
        )
        return self._send(request, timeout_seconds)

    def post_json(
        self,
        url: str,
        api_key: str,
        payload: Mapping[str, object],
        timeout_seconds: int,
    ) -> HttpResult:
        encoded = design.canonical_json(dict(payload)).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        return self._send(request, timeout_seconds)


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_once(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    allowed = ("x-request-id", "trace-id")
    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower() in allowed or str(key).lower().startswith("x-ratelimit-")
    }


def _protected_response(
    result: HttpResult,
    *,
    request_role: str,
) -> dict[str, object]:
    return {
        "request_role": request_role,
        "http_status_code": result.status_code,
        "raw_body_sha256": hashlib.sha256(result.body).hexdigest(),
        "raw_body_base64": base64.b64encode(result.body).decode("ascii"),
        "safe_response_headers": _safe_headers(result.headers),
    }


def _load_assets(
    repo_root: Path,
) -> tuple[AuthorizationV1, J7LGLM52NamedToolQualificationPlanV1]:
    root = repo_root.resolve()
    auth = AuthorizationV1.model_validate(_load_json(root / AUTHORIZATION_PATH))
    plan_path = root / auth.qualification_plan_path
    if _sha256_file(plan_path) != auth.qualification_plan_sha256:
        raise ActivationError(
            "QUALIFICATION_PLAN_HASH_MISMATCH",
            "authorized qualification plan bytes drifted",
        )
    plan = design.load_plan(root)

    if auth.provider != plan.provider:
        raise ActivationError("PROVIDER_IDENTITY_DRIFT", "authorized provider drifted")
    if auth.exact_model_identifier != plan.exact_model_identifier:
        raise ActivationError("MODEL_IDENTITY_DRIFT", "authorized model drifted")

    budget = plan.execution_budget
    expected = {
        "maximum_provider_http_requests": auth.maximum_provider_http_requests,
        "maximum_catalog_requests": auth.maximum_catalog_requests,
        "maximum_model_inference_requests": auth.maximum_model_inference_requests,
        "qualification_token_allowance": auth.qualification_token_allowance,
        "external_spend_ceiling_zar": auth.external_spend_ceiling_zar,
    }
    for key, expected_value in expected.items():
        if budget.get(key) != expected_value:
            raise ActivationError(
                "AUTHORIZATION_BUDGET_DRIFT",
                f"qualification budget field {key} drifted",
            )

    if budget.get("automatic_retry_permitted") is not False:
        raise ActivationError("AUTHORIZATION_RETRY_DRIFT", "automatic retry policy drifted")
    if budget.get("resume_permitted") is not False:
        raise ActivationError("AUTHORIZATION_RESUME_DRIFT", "resume policy drifted")
    if budget.get("rerun_permitted") is not False:
        raise ActivationError("AUTHORIZATION_RERUN_DRIFT", "rerun policy drifted")
    if budget.get("paid_fallback_permitted") is not False:
        raise ActivationError(
            "AUTHORIZATION_PAID_FALLBACK_DRIFT",
            "paid fallback policy drifted",
        )

    return auth, plan


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
        raise ActivationError("LIVE_BRANCH_INVALID", "live qualification requires branch main")
    tracked = _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked:
        raise ActivationError(
            "TRACKED_WORKTREE_DIRTY",
            "live qualification requires a clean tracked working tree",
        )


def _evidence_paths(
    repo_root: Path,
    plan: J7LGLM52NamedToolQualificationPlanV1,
) -> tuple[Path, ...]:
    return (
        repo_root / CONSUMPTION_PATH,
        repo_root / CATALOG_RAW_PATH,
        repo_root / CHAT_RAW_PATH,
        repo_root / plan.protected_raw_response_path,
        repo_root / plan.protected_parsed_response_path,
        repo_root / plan.public_result_path,
    )


def _assert_fresh_execution(
    repo_root: Path,
    plan: J7LGLM52NamedToolQualificationPlanV1,
) -> None:
    if any(path.exists() for path in _evidence_paths(repo_root, plan)):
        raise ActivationError(
            "EXECUTION_ALREADY_EXISTS",
            "qualification authorization is consumed or execution evidence exists",
        )


def validate_activation(repo_root: Path) -> dict[str, object]:
    """Validate merged authorization without reading credentials or using the network."""

    root = repo_root.resolve()
    auth, plan = _load_assets(root)
    design_result = design.dry_run(root)
    evidence_exists = {
        path.relative_to(root).as_posix(): path.exists() for path in _evidence_paths(root, plan)
    }
    return {
        "schema_version": "1.0.0",
        "status": "J7L_GLM52_NAMED_TOOL_AUTHORIZATION_V1_PASS",
        "authorization_id": auth.authorization_id,
        "authorization_sha256": _sha256_file(root / AUTHORIZATION_PATH),
        "qualification_plan_sha256": auth.qualification_plan_sha256,
        "design_status": design_result["status"],
        "maximum_provider_http_requests": auth.maximum_provider_http_requests,
        "maximum_model_inference_requests": auth.maximum_model_inference_requests,
        "qualification_token_allowance": auth.qualification_token_allowance,
        "external_spend_ceiling_zar": auth.external_spend_ceiling_zar,
        "provider_call_performed": False,
        "credential_accessed": False,
        "network_access_performed": False,
        "evidence_exists": evidence_exists,
    }


def _json_mapping(body: bytes, *, role: str) -> Mapping[str, object]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ActivationError(
            "PROVIDER_JSON_INVALID",
            f"{role} response was not valid UTF-8 JSON",
        ) from error
    if not isinstance(payload, Mapping):
        raise ActivationError(
            "PROVIDER_JSON_SHAPE_INVALID",
            f"{role} response root was not an object",
        )
    return cast(Mapping[str, object], payload)


def _catalog_entry(
    payload: Mapping[str, object],
    *,
    model_id: str,
) -> Mapping[str, object]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ActivationError("CATALOG_SHAPE_INVALID", "catalog data field is not a list")
    matches = [item for item in data if isinstance(item, Mapping) and item.get("id") == model_id]
    if len(matches) != 1:
        raise ActivationError(
            "CATALOG_MODEL_ID_INVALID",
            "catalog did not contain exactly one authorized model ID",
        )
    return cast(Mapping[str, object], matches[0])


def _version_or_revision(entry: Mapping[str, object]) -> tuple[str | None, str | None]:
    for name in ("version", "revision", "model_version", "model_revision"):
        value = entry.get(name)
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            rendered = str(value).strip()
            if rendered:
                return name, rendered
    return None, None


def _required_nonnegative_int(mapping: Mapping[str, object], name: str) -> int:
    value = mapping.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ActivationError("USAGE_INVALID", f"usage.{name} is invalid")
    return value


def _validate_chat_response(
    payload: Mapping[str, object],
    *,
    plan: J7LGLM52NamedToolQualificationPlanV1,
) -> dict[str, object]:
    returned_model = payload.get("model")
    if not isinstance(returned_model, str) or not returned_model.strip():
        raise ActivationError("RETURNED_MODEL_MISSING", "provider response model is missing")

    choices = payload.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ActivationError(
            "CHOICE_COUNT_INVALID",
            "qualification requires exactly one provider choice",
        )
    choice = choices[0]
    if not isinstance(choice, Mapping):
        raise ActivationError("CHOICE_SHAPE_INVALID", "provider choice is invalid")
    message = choice.get("message")
    if not isinstance(message, Mapping):
        raise ActivationError("MESSAGE_SHAPE_INVALID", "provider message is invalid")

    reasoning_content = message.get("reasoning_content")
    if reasoning_content not in (None, ""):
        raise ActivationError(
            "THINKING_DISABLE_FAILED",
            "provider returned non-empty reasoning_content",
        )

    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        raise ActivationError(
            "TOOL_CALL_COUNT_INVALID",
            "qualification requires exactly one returned tool call",
        )
    tool_call = tool_calls[0]
    if not isinstance(tool_call, Mapping):
        raise ActivationError("TOOL_CALL_SHAPE_INVALID", "returned tool call is invalid")
    function = tool_call.get("function")
    if not isinstance(function, Mapping):
        raise ActivationError("TOOL_FUNCTION_INVALID", "returned tool function is invalid")
    if function.get("name") != "submit_reference_judgment":
        raise ActivationError("TOOL_NAME_INVALID", "returned tool name drifted")

    arguments_text = function.get("arguments")
    if not isinstance(arguments_text, str):
        raise ActivationError("TOOL_ARGUMENTS_INVALID", "tool arguments are not a JSON string")
    try:
        arguments_payload = json.loads(arguments_text)
    except json.JSONDecodeError as error:
        raise ActivationError(
            "TOOL_ARGUMENTS_JSON_INVALID",
            "tool arguments were not valid JSON",
        ) from error
    if not isinstance(arguments_payload, Mapping):
        raise ActivationError(
            "TOOL_ARGUMENTS_SHAPE_INVALID",
            "tool arguments root was not an object",
        )
    arguments = J7LReferenceToolArgumentsV1.model_validate(arguments_payload)

    usage_value = payload.get("usage")
    if not isinstance(usage_value, Mapping):
        raise ActivationError("USAGE_MISSING", "provider usage object is missing")
    usage = cast(Mapping[str, object], usage_value)
    prompt_tokens = _required_nonnegative_int(usage, "prompt_tokens")
    completion_tokens = _required_nonnegative_int(usage, "completion_tokens")
    total_tokens = _required_nonnegative_int(usage, "total_tokens")

    details_value = usage.get("completion_tokens_details")
    if not isinstance(details_value, Mapping):
        raise ActivationError(
            "REASONING_USAGE_MISSING",
            "completion token details are missing",
        )
    reasoning_tokens = _required_nonnegative_int(
        cast(Mapping[str, object], details_value),
        "reasoning_tokens",
    )
    if reasoning_tokens != 0:
        raise ActivationError(
            "THINKING_USAGE_NONZERO",
            "provider reported non-zero reasoning tokens",
        )
    allowance_value = plan.execution_budget.get("qualification_token_allowance")
    if (
        isinstance(allowance_value, bool)
        or not isinstance(allowance_value, int)
        or allowance_value < 1
    ):
        raise ActivationError(
            "QUALIFICATION_TOKEN_BUDGET_INVALID",
            "qualification token allowance is invalid",
        )
    if total_tokens > allowance_value:
        raise ActivationError(
            "QUALIFICATION_TOKEN_BUDGET_EXCEEDED",
            "qualification exceeded the frozen token allowance",
        )

    return {
        "returned_model": returned_model,
        "returned_model_matches_requested": returned_model == plan.exact_model_identifier,
        "finish_reason": choice.get("finish_reason"),
        "tool_call_id_present": isinstance(tool_call.get("id"), str),
        "tool_arguments_sha256": hashlib.sha256(
            design.canonical_json(arguments.model_dump(mode="json")).encode("utf-8")
        ).hexdigest(),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "reasoning_tokens": reasoning_tokens,
        "reasoning_content_empty": True,
        "tool_name": "submit_reference_judgment",
        "tool_arguments_valid": True,
    }


def execute_qualification(
    repo_root: Path,
    *,
    confirmation: str,
    zero_spend_confirmed: bool,
    client: HttpClient | None = None,
    live_boundary: Callable[[Path], None] = _assert_live_git_boundary,
) -> dict[str, object]:
    """Consume the single-use authorization and run one bounded live qualification."""

    root = repo_root.resolve()
    auth, plan = _load_assets(root)

    if confirmation != auth.confirmation_phrase:
        raise ActivationError("CONFIRMATION_MISMATCH", "execution confirmation phrase is invalid")
    if not zero_spend_confirmed:
        raise ActivationError(
            "ZERO_SPEND_NOT_CONFIRMED",
            "R0 external-spend status must be confirmed before provider execution",
        )

    live_boundary(root)
    _assert_fresh_execution(root, plan)

    design.load_assets(root)
    request_body = design.build_chat_request_body(root)

    api_key = os.environ.get(auth.credential_env_name)
    if api_key is None or not api_key.strip():
        raise ActivationError(
            "HUAWEI_MAAS_API_KEY_MISSING",
            "HUAWEI_MAAS_API_KEY is unavailable",
        )

    authorization_sha256 = _sha256_file(root / AUTHORIZATION_PATH)
    _write_once(
        root / CONSUMPTION_PATH,
        {
            "schema_version": "1.0.0",
            "status": "AUTHORIZATION_CONSUMED",
            "authorization_id": auth.authorization_id,
            "authorization_sha256": authorization_sha256,
            "qualification_plan_sha256": auth.qualification_plan_sha256,
            "consumed_at_utc": datetime.now(UTC).isoformat(),
            "provider_http_attempts_permitted_after_consumption": 2,
            "rerun_permitted": False,
            "resume_permitted": False,
        },
    )

    active_client = UrllibHuaweiClient() if client is None else client

    catalog_result = active_client.get(
        plan.catalog_endpoint_url,
        api_key,
        _TIMEOUT_SECONDS,
    )
    if catalog_result.status_code != 200:
        raise ActivationError(
            "CATALOG_HTTP_STATUS_INVALID",
            f"catalog returned HTTP {catalog_result.status_code}",
        )
    _write_once(
        root / CATALOG_RAW_PATH,
        _protected_response(catalog_result, request_role="model_catalog"),
    )
    catalog_payload = _json_mapping(catalog_result.body, role="catalog")
    entry = _catalog_entry(catalog_payload, model_id=plan.exact_model_identifier)
    version_field, version_value = _version_or_revision(entry)

    chat_result = active_client.post_json(
        plan.chat_endpoint_url,
        api_key,
        request_body,
        _TIMEOUT_SECONDS,
    )
    if chat_result.status_code != 200:
        raise ActivationError(
            "CHAT_HTTP_STATUS_INVALID",
            f"chat completion returned HTTP {chat_result.status_code}",
        )
    _write_once(
        root / CHAT_RAW_PATH,
        _protected_response(chat_result, request_role="synthetic_named_tool"),
    )
    chat_payload = _json_mapping(chat_result.body, role="chat")
    chat_observation = _validate_chat_response(chat_payload, plan=plan)

    combined_raw = {
        "schema_version": "1.0.0",
        "authorization_sha256": authorization_sha256,
        "qualification_plan_sha256": auth.qualification_plan_sha256,
        "catalog": _protected_response(catalog_result, request_role="model_catalog"),
        "chat": _protected_response(chat_result, request_role="synthetic_named_tool"),
    }
    _write_once(root / plan.protected_raw_response_path, combined_raw)

    parsed = {
        "schema_version": "1.0.0",
        "catalog_model_entry": dict(entry),
        "provider_version_or_revision_field": version_field,
        "provider_version_or_revision_value": version_value,
        "chat_observation": chat_observation,
    }
    _write_once(root / plan.protected_parsed_response_path, parsed)

    public_result: dict[str, object] = {
        "schema_version": "1.0.0",
        "status": "J7L_GLM52_NAMED_TOOL_QUALIFICATION_PASS",
        "authorization_id": auth.authorization_id,
        "authorization_sha256": authorization_sha256,
        "qualification_plan_sha256": auth.qualification_plan_sha256,
        "provider": plan.provider,
        "requested_model": plan.exact_model_identifier,
        "catalog_contains_exact_model_id": True,
        "provider_version_or_revision_exposed": version_value is not None,
        "provider_version_or_revision_field": version_field,
        "provider_version_or_revision_value": version_value,
        "returned_model": chat_observation["returned_model"],
        "returned_model_matches_requested": chat_observation["returned_model_matches_requested"],
        "provider_http_request_count": 2,
        "catalog_request_count": 1,
        "model_inference_request_count": 1,
        "named_tool_transport_qualified": True,
        "thinking_disabled_observed": True,
        "usage_accounting_observed": True,
        "prompt_tokens": chat_observation["prompt_tokens"],
        "completion_tokens": chat_observation["completion_tokens"],
        "total_tokens": chat_observation["total_tokens"],
        "reasoning_tokens": chat_observation["reasoning_tokens"],
        "qualification_token_allowance": auth.qualification_token_allowance,
        "zero_spend_operator_confirmed_before_execution": True,
        "zero_spend_independently_proven": False,
        "j7l_reference_request_performed": False,
        "jev_request_performed": False,
        "binding_freeze_performed": False,
        "rerun_permitted": False,
        "resume_permitted": False,
        "next_gate": "REVIEW_J7L_GLM52_NAMED_TOOL_QUALIFICATION_RESULT_V1",
    }
    _write_once(root / plan.public_result_path, public_result)
    return public_result


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
            else execute_qualification(
                args.repo_root,
                confirmation=args.confirmation,
                zero_spend_confirmed=args.zero_spend_confirmed,
            )
        )
    except (ActivationError, ValidationError, OSError, json.JSONDecodeError) as error:
        code = error.code if isinstance(error, ActivationError) else "ACTIVATION_FAILED"
        safe_message = (
            error.safe_message
            if isinstance(error, ActivationError)
            else "GLM-5.2 named-tool qualification activation failed"
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

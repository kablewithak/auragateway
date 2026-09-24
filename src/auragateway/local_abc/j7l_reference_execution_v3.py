"""Governed J7L V3 model-derived reference execution over Huawei GLM-5.2."""

from __future__ import annotations

import argparse
import base64
import binascii
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceAuditScheduleV1,
    J7LReferenceJudgmentV1,
    J7LReferenceToolArgumentsV1,
)

BINDING_PATH = Path("data/evals/quality/j7l-reference-judge-binding-v2/binding.json")
PLAN_PATH = Path(
    "data/evals/quality/j7l-reference-execution-protocol-v3/reference_execution_plan.json"
)
AUTHORIZATION_PATH = Path(
    "data/evals/quality/j7l-reference-execution-authorization-v3/authorization.json"
)

EXPECTED_BINDING_SHA256 = "7c87832c697b66414921fef76f80466ef3b0c89421969d53acc6d35aa3906b1f"
EXPECTED_PLAN_SHA256 = "09ed20aa41df2a495f36affb47fe94c6344fcf0d667d67f9b5f9eaa8be5097ec"
OPERATOR_ID_SHA256 = "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"

CONSUMPTION_PATH = Path(".local/auragateway/j7l-reference-execution-v3/authorization_consumed.json")
AUDIT_SCHEDULE_PATH = Path(
    ".local/auragateway/j7l-reference-execution-v3/reference_audit_schedule.json"
)
ATTEMPTS_DIR = Path(".local/auragateway/j7l-reference-execution-v3/attempts")
RAW_RESPONSES_DIR = Path(".local/auragateway/j7l-reference-execution-v3/raw-responses")
JUDGMENTS_DIR = Path(".local/auragateway/j7l-reference-execution-v3/judgments")
PUBLIC_RESULT_PATH = Path(
    "data/evals/quality/j7l-reference-execution-protocol-v3/reference_execution_result.json"
)

PHASE_TOTAL_TOKEN_CEILING = 960000
PER_REQUEST_TOTAL_TOKEN_CEILING = 20000
PLANNED_REFERENCE_REQUEST_COUNT = 48

_TIMEOUT_SECONDS = 90
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024

_USAGE_KEYS = (
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "reasoning_tokens",
)


class ReferenceExecutionError(RuntimeError):
    """Fail-closed J7L V3 reference execution error."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorizationV3(FrozenModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal["j7l-reference-execution-authorization-v3"]
    status: Literal["active"]
    binding_path: Literal["data/evals/quality/j7l-reference-judge-binding-v2/binding.json"]
    binding_sha256: Literal["7c87832c697b66414921fef76f80466ef3b0c89421969d53acc6d35aa3906b1f"]
    execution_plan_path: Literal[
        "data/evals/quality/j7l-reference-execution-protocol-v3/reference_execution_plan.json"
    ]
    execution_plan_sha256: Literal[
        "09ed20aa41df2a495f36affb47fe94c6344fcf0d667d67f9b5f9eaa8be5097ec"
    ]
    reference_audit_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    audit_actor_id_sha256: Literal[
        "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
    ]
    resolution_owner_id_sha256: Literal[
        "a37370417f5c7d7f387a954fc51fb718a3e5fcf8d1b55ca74c89ef35fd1b5c82"
    ]
    confirmation_phrase: Literal["EXECUTE_J7L_REFERENCE_SET_V3"]
    provider: Literal["huawei_modelarts_maas"]
    exact_model_identifier: Literal["glm-5.2"]
    credential_env_name: Literal["HUAWEI_MAAS_API_KEY"]
    provider_call_authorized: Literal[True]
    credential_access_authorized: Literal[True]
    network_access_authorized: Literal[True]
    reference_execution_authorized: Literal[True]
    maximum_model_inference_requests: Literal[48]
    max_in_flight_requests: Literal[1]
    automatic_retry_permitted: Literal[False]
    completed_case_replay_permitted: Literal[False]
    ambiguous_attempt_retry_permitted: Literal[False]
    resume_after_completed_cases_permitted: Literal[True]
    cumulative_phase_total_token_ceiling: Literal[960000]
    external_spend_ceiling_zar: Literal[0]
    paid_fallback_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    zero_spend_confirmation_required: Literal[True]
    clean_main_required: Literal[True]

    @model_validator(mode="after")
    def validate_policy(self) -> AuthorizationV3:
        if self.maximum_model_inference_requests != PLANNED_REFERENCE_REQUEST_COUNT:
            raise ValueError("reference authorization must remain exactly 48 requests")
        if self.cumulative_phase_total_token_ceiling != PHASE_TOTAL_TOKEN_CEILING:
            raise ValueError("reference authorization token ceiling drifted")
        return self


class HttpResult(FrozenModel):
    status_code: int
    headers: dict[str, str]
    body: bytes


class UrllibHuaweiClient:
    """Minimal no-retry Huawei client."""

    def __init__(self) -> None:
        self._opener = urllib.request.build_opener()

    def post_json(
        self,
        url: str,
        api_key: str,
        payload: Mapping[str, object],
    ) -> HttpResult:
        encoded = canonical_json(payload).encode("utf-8")
        request = urllib.request.Request(
            url=url,
            data=encoded,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._opener.open(request, timeout=_TIMEOUT_SECONDS) as response:
                body = cast(bytes, response.read(_MAX_RESPONSE_BYTES + 1))
                if len(body) > _MAX_RESPONSE_BYTES:
                    raise ReferenceExecutionError(
                        "HTTP_RESPONSE_TOO_LARGE",
                        "provider response exceeded protected byte ceiling",
                    )
                return HttpResult(
                    status_code=int(response.status),
                    headers={
                        str(key).lower(): str(value) for key, value in response.headers.items()
                    },
                    body=body,
                )
        except urllib.error.HTTPError as error:
            raise ReferenceExecutionError(
                "PROVIDER_HTTP_ERROR",
                f"provider returned HTTP {error.code}",
            ) from error
        except urllib.error.URLError as error:
            raise ReferenceExecutionError(
                "PROVIDER_TRANSPORT_ERROR",
                "provider transport failed",
            ) from error


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping(value: object, *, role: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ReferenceExecutionError(
            "JSON_SHAPE_INVALID",
            f"{role} root is not an object",
        )
    return cast(Mapping[str, object], value)


def _required_str(mapping: Mapping[str, object], name: str, *, role: str) -> str:
    value = mapping.get(name)
    if not isinstance(value, str) or not value:
        raise ReferenceExecutionError(
            "JSON_FIELD_INVALID",
            f"{role}.{name} is missing or invalid",
        )
    return value


def _assert_hash(path: Path, expected: str, *, role: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ReferenceExecutionError(f"{role}_MISSING", f"{role} is missing or unsafe")
    if sha256_file(path) != expected:
        raise ReferenceExecutionError(f"{role}_HASH_MISMATCH", f"{role} hash drifted")


def _validate_plan_policy(plan: Mapping[str, object]) -> None:
    if plan.get("schema_version") != "3.0.0":
        raise ReferenceExecutionError("PLAN_SCHEMA_DRIFT", "execution plan schema drifted")
    if plan.get("plan_id") != "j7l-reference-execution-v3":
        raise ReferenceExecutionError("PLAN_ID_DRIFT", "execution plan identity drifted")
    if plan.get("binding_sha256") != EXPECTED_BINDING_SHA256:
        raise ReferenceExecutionError("PLAN_BINDING_DRIFT", "execution plan binding drifted")
    if plan.get("status") != "REVIEW_READY_INACTIVE":
        raise ReferenceExecutionError("PLAN_STATUS_DRIFT", "execution plan status drifted")

    inactive_fields = (
        "credential_access_authorized",
        "network_access_authorized",
        "provider_call_authorized",
        "reference_execution_authorized",
        "jev_request_permitted",
    )
    for field_name in inactive_fields:
        if plan.get(field_name) is not False:
            raise ReferenceExecutionError(
                "PLAN_AUTHORITY_DRIFT",
                f"execution plan unexpectedly authorizes {field_name}",
            )

    if plan.get("future_authorization_path") != AUTHORIZATION_PATH.as_posix():
        raise ReferenceExecutionError(
            "PLAN_AUTHORIZATION_PATH_DRIFT",
            "future authorization path drifted",
        )
    if plan.get("public_result_path") != PUBLIC_RESULT_PATH.as_posix():
        raise ReferenceExecutionError(
            "PLAN_PUBLIC_RESULT_PATH_DRIFT",
            "public result path drifted",
        )

    audit = _mapping(plan.get("audit_authority"), role="audit authority")
    if audit.get("audit_actor_id_sha256") != OPERATOR_ID_SHA256:
        raise ReferenceExecutionError("AUDIT_ACTOR_DRIFT", "audit actor identity drifted")
    if audit.get("resolution_owner_id_sha256") != OPERATOR_ID_SHA256:
        raise ReferenceExecutionError(
            "RESOLUTION_OWNER_DRIFT",
            "resolution owner identity drifted",
        )
    if audit.get("audit_schedule_contract") != "J7LReferenceAuditScheduleV1":
        raise ReferenceExecutionError(
            "AUDIT_CONTRACT_DRIFT",
            "audit schedule contract drifted",
        )
    if audit.get("audit_schedule_must_validate_before_credential_access") is not True:
        raise ReferenceExecutionError(
            "AUDIT_VALIDATION_ORDER_DRIFT",
            "audit schedule validation order drifted",
        )
    if audit.get("schedule_frozen_before_reference_execution") is not True:
        raise ReferenceExecutionError(
            "AUDIT_FREEZE_POLICY_DRIFT",
            "audit schedule freeze policy drifted",
        )
    if audit.get("audit_may_rewrite_reference") is not False:
        raise ReferenceExecutionError(
            "AUDIT_REWRITE_POLICY_DRIFT",
            "audit rewrite policy drifted",
        )
    if audit.get("material_disagreement_invalidates_reference_set") is not True:
        raise ReferenceExecutionError(
            "AUDIT_INVALIDATION_POLICY_DRIFT",
            "audit invalidation policy drifted",
        )

    request_policy = _mapping(plan.get("request_policy"), role="request policy")
    exact_policy: dict[str, object] = {
        "planned_reference_request_count": PLANNED_REFERENCE_REQUEST_COUNT,
        "max_in_flight_requests": 1,
        "automatic_retry_permitted": False,
        "completed_case_replay_permitted": False,
        "ambiguous_attempt_retry_permitted": False,
        "resume_after_completed_cases_permitted": True,
        "per_request_total_token_ceiling": PER_REQUEST_TOTAL_TOKEN_CEILING,
        "hard_reference_phase_total_token_ceiling": PHASE_TOTAL_TOKEN_CEILING,
        "completed_usage_reconstructed_on_resume": True,
        "cumulative_phase_total_token_ceiling_enforced_across_resumes": True,
        "per_invocation_and_cumulative_usage_reported_separately": True,
        "serial_execution": True,
        "paid_fallback_permitted": False,
        "external_spend_ceiling_zar": 0,
    }
    for key, expected_policy_value in exact_policy.items():
        if request_policy.get(key) != expected_policy_value:
            raise ReferenceExecutionError(
                "REQUEST_POLICY_DRIFT",
                f"request policy field drifted: {key}",
            )

    protected = _mapping(plan.get("protected_evidence"), role="protected evidence")
    exact_paths: dict[str, str] = {
        "root": ".local/auragateway/j7l-reference-execution-v3",
        "attempts_dir": ATTEMPTS_DIR.as_posix(),
        "audit_schedule_path": AUDIT_SCHEDULE_PATH.as_posix(),
        "consumption_path": CONSUMPTION_PATH.as_posix(),
        "judgments_dir": JUDGMENTS_DIR.as_posix(),
        "raw_responses_dir": RAW_RESPONSES_DIR.as_posix(),
    }
    for key, expected_path in exact_paths.items():
        if protected.get(key) != expected_path:
            raise ReferenceExecutionError(
                "PROTECTED_EVIDENCE_PATH_DRIFT",
                f"protected evidence path drifted: {key}",
            )


def _load_bound_assets(repo_root: Path) -> tuple[Mapping[str, object], Mapping[str, object]]:
    binding_path = repo_root / BINDING_PATH
    plan_path = repo_root / PLAN_PATH

    if sha256_file(binding_path) != EXPECTED_BINDING_SHA256:
        raise ReferenceExecutionError("BINDING_HASH_MISMATCH", "binding bytes drifted")
    if sha256_file(plan_path) != EXPECTED_PLAN_SHA256:
        raise ReferenceExecutionError("PLAN_HASH_MISMATCH", "execution plan bytes drifted")

    binding = _mapping(_load_json(binding_path), role="binding")
    plan = _mapping(_load_json(plan_path), role="execution plan")

    if binding.get("binding_frozen") is not True:
        raise ReferenceExecutionError("BINDING_NOT_FROZEN", "binding is not frozen")
    if binding.get("reference_execution_authorized") is not False:
        raise ReferenceExecutionError(
            "BINDING_AUTHORITY_DRIFT",
            "binding artifact must not itself authorize execution",
        )

    _validate_plan_policy(plan)
    return binding, plan


def _load_reference_inputs(
    repo_root: Path,
    plan: Mapping[str, object],
) -> tuple[tuple[dict[str, object], ...], object, Mapping[str, object]]:
    schedule_path = repo_root / _required_str(
        plan,
        "protected_case_schedule_path",
        role="execution plan",
    )
    primary_path = repo_root / _required_str(
        plan,
        "protected_primary_export_path",
        role="execution plan",
    )
    projection_path = repo_root / _required_str(
        plan,
        "model_projection_path",
        role="execution plan",
    )
    tool_path = repo_root / _required_str(
        plan,
        "named_tool_contract_path",
        role="execution plan",
    )
    qualification_path = repo_root / _required_str(
        plan,
        "qualification_result_path",
        role="execution plan",
    )

    _assert_hash(
        schedule_path,
        _required_str(plan, "protected_case_schedule_sha256", role="execution plan"),
        role="PROTECTED_CASE_SCHEDULE",
    )
    _assert_hash(
        primary_path,
        _required_str(plan, "protected_primary_export_sha256", role="execution plan"),
        role="PROTECTED_PRIMARY_EXPORT",
    )
    _assert_hash(
        projection_path,
        _required_str(plan, "model_projection_sha256", role="execution plan"),
        role="MODEL_PROJECTION",
    )
    _assert_hash(
        tool_path,
        _required_str(plan, "named_tool_contract_sha256", role="execution plan"),
        role="NAMED_TOOL_CONTRACT",
    )
    _assert_hash(
        qualification_path,
        _required_str(plan, "qualification_result_sha256", role="execution plan"),
        role="QUALIFICATION_RESULT",
    )

    schedule = _mapping(_load_json(schedule_path), role="protected schedule")
    primary = _mapping(_load_json(primary_path), role="primary reviewer export")
    tool_contract = _mapping(_load_json(tool_path), role="named tool contract")
    model_projection = _load_json(projection_path)

    entries_value = schedule.get("entries")
    items_value = primary.get("items")
    if not isinstance(entries_value, list) or len(entries_value) != 48:
        raise ReferenceExecutionError("SCHEDULE_COUNT_INVALID", "schedule must contain 48 cases")
    if not isinstance(items_value, list) or len(items_value) != 48:
        raise ReferenceExecutionError(
            "PRIMARY_EXPORT_COUNT_INVALID",
            "primary export must contain 48 cases",
        )

    by_review_item: dict[str, Mapping[str, object]] = {}
    for item in items_value:
        mapped = _mapping(item, role="primary export item")
        review_item_id = mapped.get("review_item_id")
        if not isinstance(review_item_id, str):
            raise ReferenceExecutionError(
                "REVIEW_ITEM_ID_INVALID",
                "primary review item id invalid",
            )
        by_review_item[review_item_id] = mapped

    cases: list[dict[str, object]] = []
    for index, entry_value in enumerate(entries_value, start=1):
        entry = _mapping(entry_value, role="schedule entry")
        case_id = entry.get("case_id")
        review_item_id = entry.get("review_item_id")
        expected_case_id = f"j7l-dev-{index:03d}"
        if case_id != expected_case_id:
            raise ReferenceExecutionError("CASE_ORDER_INVALID", "frozen J7L case order drifted")
        if not isinstance(review_item_id, str) or review_item_id not in by_review_item:
            raise ReferenceExecutionError("CASE_EXPORT_JOIN_INVALID", "schedule/export join failed")
        item = by_review_item[review_item_id]
        state = item.get("reviewer_safe_state")
        if not isinstance(state, Mapping):
            raise ReferenceExecutionError(
                "REVIEWER_SAFE_STATE_INVALID",
                "reviewer-safe state is not an object",
            )
        cases.append(
            {
                "case_id": case_id,
                "family": entry.get("family"),
                "review_item_id": review_item_id,
                "reviewer_safe_state": dict(state),
            }
        )

    return tuple(cases), model_projection, tool_contract


def _audit_schedule(
    cases: tuple[dict[str, object], ...],
    plan: Mapping[str, object],
) -> J7LReferenceAuditScheduleV1:
    protected = tuple(
        str(case["case_id"])
        for case in cases
        if case.get("family") in {"terminal_non_substantive", "ontology_near_miss"}
    )
    ordinary = tuple(
        str(case["case_id"]) for case in cases if case.get("family") == "ordinary_clean"
    )
    clear_failure = tuple(
        str(case["case_id"]) for case in cases if case.get("family") == "clear_failure"
    )

    if len(protected) != 24 or len(ordinary) != 12 or len(clear_failure) != 12:
        raise ReferenceExecutionError(
            "AUDIT_STRATUM_INVALID",
            "protected case-family counts drifted",
        )

    audit = _mapping(plan.get("audit_authority"), role="audit authority")
    return J7LReferenceAuditScheduleV1(
        schedule_id="j7l-reference-audit-schedule-v3",
        audit_actor_id_sha256=_required_str(
            audit,
            "audit_actor_id_sha256",
            role="audit authority",
        ),
        resolution_owner_id_sha256=_required_str(
            audit,
            "resolution_owner_id_sha256",
            role="audit authority",
        ),
        protected_secondary_case_ids=protected,
        additional_spot_check_case_ids=ordinary[:2] + clear_failure[:2],
    )


def _audit_schedule_bytes(
    cases: tuple[dict[str, object], ...],
    plan: Mapping[str, object],
) -> bytes:
    schedule = _audit_schedule(cases, plan)
    payload = schedule.model_dump(mode="json")
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _freeze_audit_schedule(
    repo_root: Path,
    cases: tuple[dict[str, object], ...],
    plan: Mapping[str, object],
) -> str:
    expected_bytes = _audit_schedule_bytes(cases, plan)
    _write_once_or_match(repo_root / AUDIT_SCHEDULE_PATH, expected_bytes)
    return sha256_bytes(expected_bytes)


def _write_once(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_once_or_match(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise ReferenceExecutionError(
                "APPEND_ONLY_CONFLICT",
                "existing protected artifact differs from expected bytes",
            )
        return
    with path.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())


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
        raise ReferenceExecutionError("GIT_INSPECTION_FAILED", "required Git inspection failed")
    return completed.stdout.strip()


def _assert_live_git_boundary(repo_root: Path) -> None:
    if _git_text(repo_root, "branch", "--show-current") != "main":
        raise ReferenceExecutionError("LIVE_BRANCH_INVALID", "reference execution requires main")
    tracked = _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked:
        raise ReferenceExecutionError(
            "TRACKED_WORKTREE_DIRTY",
            "reference execution requires a clean tracked worktree",
        )


def _safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower() in {"x-request-id", "trace-id"}
        or str(key).lower().startswith("x-ratelimit-")
    }


def _build_request(
    *,
    model_projection: object,
    reviewer_safe_state: Mapping[str, object],
    tool_contract: Mapping[str, object],
) -> dict[str, object]:
    wire = _mapping(tool_contract.get("wire"), role="named tool wire")
    tools = wire.get("tools")
    tool_choice = wire.get("tool_choice")
    if not isinstance(tools, list) or len(tools) != 1 or not isinstance(tool_choice, Mapping):
        raise ReferenceExecutionError("NAMED_TOOL_WIRE_INVALID", "named tool wire drifted")

    visible_payload = {
        "semantic_projection": model_projection,
        "reviewer_safe_state": dict(reviewer_safe_state),
    }
    return {
        "model": "glm-5.2",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the independent AuraGateway J7L model-derived reference judge. "
                    "Use only the supplied semantic projection and reviewer-safe visible evidence. "
                    "Do not reveal hidden chain-of-thought. "
                    "Call submit_reference_judgment exactly once. "
                    "Do not emit any additional tool call."
                ),
            },
            {
                "role": "user",
                "content": canonical_json(visible_payload),
            },
        ],
        "stream": False,
        "max_completion_tokens": 768,
        "chat_template_kwargs": {"thinking": False},
        "tools": tools,
        "tool_choice": dict(tool_choice),
    }


def _required_nonnegative_int(mapping: Mapping[str, object], name: str) -> int:
    value = mapping.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReferenceExecutionError("USAGE_INVALID", f"usage.{name} is invalid")
    return value


def _validate_response(
    body: bytes,
    *,
    case_id: str,
    request_id_sha256: str,
    judge_binding_sha256: str,
) -> tuple[J7LReferenceJudgmentV1, dict[str, int], str]:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ReferenceExecutionError(
            "PROVIDER_JSON_INVALID",
            "provider response is not valid UTF-8 JSON",
        ) from error
    response = _mapping(payload, role="chat response")

    returned_model = response.get("model")
    if returned_model != "glm-5.2":
        raise ReferenceExecutionError("RETURNED_MODEL_DRIFT", "returned model drifted")

    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ReferenceExecutionError("CHOICE_COUNT_INVALID", "expected exactly one choice")
    choice = _mapping(choices[0], role="choice")
    message = _mapping(choice.get("message"), role="message")

    if message.get("reasoning_content") not in (None, ""):
        raise ReferenceExecutionError(
            "THINKING_DISABLE_FAILED",
            "provider returned non-empty reasoning_content",
        )

    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list) or len(tool_calls) != 1:
        raise ReferenceExecutionError("TOOL_CALL_COUNT_INVALID", "expected exactly one tool call")
    call = _mapping(tool_calls[0], role="tool call")
    function = _mapping(call.get("function"), role="tool function")
    if function.get("name") != "submit_reference_judgment":
        raise ReferenceExecutionError("TOOL_NAME_INVALID", "returned tool name drifted")

    arguments_text = function.get("arguments")
    if not isinstance(arguments_text, str):
        raise ReferenceExecutionError("TOOL_ARGUMENTS_INVALID", "tool arguments are not JSON text")
    try:
        arguments_payload = json.loads(arguments_text)
    except json.JSONDecodeError as error:
        raise ReferenceExecutionError(
            "TOOL_ARGUMENTS_JSON_INVALID",
            "tool arguments are not valid JSON",
        ) from error

    arguments = J7LReferenceToolArgumentsV1.model_validate(arguments_payload)
    judgment = J7LReferenceJudgmentV1(
        case_id=case_id,
        request_id_sha256=request_id_sha256,
        judge_binding_sha256=judge_binding_sha256,
        **arguments.model_dump(),
    )

    usage = _mapping(response.get("usage"), role="usage")
    prompt_tokens = _required_nonnegative_int(usage, "prompt_tokens")
    completion_tokens = _required_nonnegative_int(usage, "completion_tokens")
    total_tokens = _required_nonnegative_int(usage, "total_tokens")
    details = _mapping(usage.get("completion_tokens_details"), role="completion token details")
    reasoning_tokens = _required_nonnegative_int(details, "reasoning_tokens")

    if reasoning_tokens != 0:
        raise ReferenceExecutionError(
            "THINKING_USAGE_NONZERO",
            "provider reported non-zero reasoning tokens",
        )
    if total_tokens > PER_REQUEST_TOTAL_TOKEN_CEILING:
        raise ReferenceExecutionError(
            "PER_REQUEST_TOKEN_CEILING_EXCEEDED",
            "reference request exceeded the 20,000-token operational ceiling",
        )

    return (
        judgment,
        {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "reasoning_tokens": reasoning_tokens,
        },
        returned_model,
    )


def _authorization(repo_root: Path) -> tuple[AuthorizationV3, str]:
    path = repo_root / AUTHORIZATION_PATH
    if not path.is_file() or path.is_symlink():
        raise ReferenceExecutionError(
            "AUTHORIZATION_MISSING",
            "reference execution authorization is missing",
        )
    auth = AuthorizationV3.model_validate(_load_json(path))
    return auth, sha256_file(path)


def _zero_usage() -> dict[str, int]:
    return {key: 0 for key in _USAGE_KEYS}


def _add_usage(target: dict[str, int], usage: Mapping[str, int]) -> None:
    for key in _USAGE_KEYS:
        target[key] += usage[key]


def _safe_json_file(path: Path, *, role: str) -> object:
    if not path.is_file() or path.is_symlink():
        raise ReferenceExecutionError(
            "PROTECTED_EVIDENCE_UNSAFE",
            f"{role} is missing or unsafe",
        )
    return _load_json(path)


def _completed_case_evidence(
    repo_root: Path,
    *,
    case_id: str,
    expected_request_sha256: str,
) -> tuple[J7LReferenceJudgmentV1, dict[str, int]] | None:
    attempt_path = repo_root / ATTEMPTS_DIR / f"{case_id}.json"
    raw_path = repo_root / RAW_RESPONSES_DIR / f"{case_id}.json"
    judgment_path = repo_root / JUDGMENTS_DIR / f"{case_id}.json"

    presence = (attempt_path.exists(), raw_path.exists(), judgment_path.exists())
    if presence == (False, False, False):
        return None
    if presence != (True, True, True):
        raise ReferenceExecutionError(
            "INCOMPLETE_PRIOR_CASE_EVIDENCE",
            f"{case_id} has incomplete prior execution evidence; do not retry",
        )

    attempt = _mapping(
        _safe_json_file(attempt_path, role=f"{case_id} attempt"),
        role=f"{case_id} attempt",
    )
    if attempt.get("status") != "REFERENCE_REQUEST_ATTEMPT_STARTED":
        raise ReferenceExecutionError("ATTEMPT_STATUS_DRIFT", f"{case_id} attempt status drifted")
    if attempt.get("case_id") != case_id:
        raise ReferenceExecutionError("ATTEMPT_CASE_DRIFT", f"{case_id} attempt case drifted")
    if attempt.get("request_id_sha256") != expected_request_sha256:
        raise ReferenceExecutionError(
            "ATTEMPT_REQUEST_ID_DRIFT",
            f"{case_id} attempt request identity drifted",
        )
    if attempt.get("judge_binding_sha256") != EXPECTED_BINDING_SHA256:
        raise ReferenceExecutionError(
            "ATTEMPT_BINDING_DRIFT",
            f"{case_id} attempt binding identity drifted",
        )
    if attempt.get("retry_permitted") is not False:
        raise ReferenceExecutionError(
            "ATTEMPT_RETRY_POLICY_DRIFT",
            f"{case_id} attempt retry policy drifted",
        )

    raw = _mapping(
        _safe_json_file(raw_path, role=f"{case_id} raw response"),
        role=f"{case_id} raw response",
    )
    if raw.get("case_id") != case_id:
        raise ReferenceExecutionError("RAW_CASE_DRIFT", f"{case_id} raw response case drifted")
    if raw.get("request_id_sha256") != expected_request_sha256:
        raise ReferenceExecutionError(
            "RAW_REQUEST_ID_DRIFT",
            f"{case_id} raw response request identity drifted",
        )
    if raw.get("http_status_code") != 200:
        raise ReferenceExecutionError(
            "RAW_HTTP_STATUS_INVALID",
            f"{case_id} raw response HTTP status is invalid",
        )

    raw_body_base64 = raw.get("raw_body_base64")
    if not isinstance(raw_body_base64, str):
        raise ReferenceExecutionError(
            "RAW_BODY_ENCODING_INVALID",
            f"{case_id} raw response body encoding is invalid",
        )
    try:
        raw_body = base64.b64decode(raw_body_base64, validate=True)
    except binascii.Error as error:
        raise ReferenceExecutionError(
            "RAW_BODY_BASE64_INVALID",
            f"{case_id} raw response body is not valid base64",
        ) from error

    if raw.get("raw_body_sha256") != sha256_bytes(raw_body):
        raise ReferenceExecutionError(
            "RAW_BODY_HASH_MISMATCH",
            f"{case_id} raw response body hash drifted",
        )

    persisted_judgment = J7LReferenceJudgmentV1.model_validate(
        _safe_json_file(judgment_path, role=f"{case_id} judgment")
    )
    if persisted_judgment.case_id != case_id:
        raise ReferenceExecutionError(
            "JUDGMENT_CASE_DRIFT",
            f"{case_id} judgment case drifted",
        )
    if persisted_judgment.request_id_sha256 != expected_request_sha256:
        raise ReferenceExecutionError(
            "JUDGMENT_REQUEST_ID_DRIFT",
            f"{case_id} judgment request identity drifted",
        )
    if persisted_judgment.judge_binding_sha256 != EXPECTED_BINDING_SHA256:
        raise ReferenceExecutionError(
            "JUDGMENT_BINDING_DRIFT",
            f"{case_id} judgment binding identity drifted",
        )

    reconstructed_judgment, usage, _ = _validate_response(
        raw_body,
        case_id=case_id,
        request_id_sha256=expected_request_sha256,
        judge_binding_sha256=EXPECTED_BINDING_SHA256,
    )
    if persisted_judgment != reconstructed_judgment:
        raise ReferenceExecutionError(
            "JUDGMENT_RAW_RESPONSE_MISMATCH",
            f"{case_id} judgment does not match the preserved raw response",
        )
    return persisted_judgment, usage


def _validate_consumption_marker(
    repo_root: Path,
    *,
    authorization_sha256: str,
) -> None:
    path = repo_root / CONSUMPTION_PATH
    marker = _mapping(
        _safe_json_file(path, role="authorization consumption marker"),
        role="authorization consumption marker",
    )
    if marker.get("authorization_sha256") != authorization_sha256:
        raise ReferenceExecutionError(
            "CONSUMPTION_AUTHORIZATION_DRIFT",
            "consumption marker belongs to a different authorization",
        )
    if marker.get("binding_sha256") != EXPECTED_BINDING_SHA256:
        raise ReferenceExecutionError(
            "CONSUMPTION_BINDING_DRIFT",
            "consumption marker binding identity drifted",
        )
    if marker.get("execution_plan_sha256") != EXPECTED_PLAN_SHA256:
        raise ReferenceExecutionError(
            "CONSUMPTION_PLAN_DRIFT",
            "consumption marker execution-plan identity drifted",
        )


def _create_consumption_marker(
    repo_root: Path,
    *,
    auth: AuthorizationV3,
    authorization_sha256: str,
    audit_schedule_sha256: str,
) -> None:
    _write_once(
        repo_root / CONSUMPTION_PATH,
        {
            "schema_version": "1.0.0",
            "status": "REFERENCE_EXECUTION_AUTHORIZATION_CONSUMED",
            "authorization_id": auth.authorization_id,
            "authorization_sha256": authorization_sha256,
            "binding_sha256": EXPECTED_BINDING_SHA256,
            "execution_plan_sha256": EXPECTED_PLAN_SHA256,
            "reference_audit_schedule_sha256": audit_schedule_sha256,
            "audit_actor_id_sha256": OPERATOR_ID_SHA256,
            "resolution_owner_id_sha256": OPERATOR_ID_SHA256,
            "consumed_at_utc": datetime.now(UTC).isoformat(),
            "logical_session_resume_after_completed_cases_permitted": True,
            "automatic_retry_permitted": False,
            "ambiguous_attempt_retry_permitted": False,
            "cumulative_phase_total_token_ceiling": PHASE_TOTAL_TOKEN_CEILING,
        },
    )


def validate(repo_root: Path) -> dict[str, object]:
    root = repo_root.resolve()
    binding, plan = _load_bound_assets(root)
    cases, model_projection, tool_contract = _load_reference_inputs(root, plan)
    first = cases[0]
    request = _build_request(
        model_projection=model_projection,
        reviewer_safe_state=cast(Mapping[str, object], first["reviewer_safe_state"]),
        tool_contract=tool_contract,
    )
    audit_schedule = _audit_schedule(cases, plan)
    audit_schedule_bytes = _audit_schedule_bytes(cases, plan)
    authorization_present = (root / AUTHORIZATION_PATH).is_file()

    return {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_EXECUTION_V3_NONLIVE_READY",
        "binding_id": binding["binding_id"],
        "binding_sha256": EXPECTED_BINDING_SHA256,
        "execution_plan_sha256": EXPECTED_PLAN_SHA256,
        "case_count": len(cases),
        "first_request_body_sha256": sha256_bytes(canonical_json(request).encode("utf-8")),
        "reference_audit_schedule_sha256": sha256_bytes(audit_schedule_bytes),
        "audit_actor_id_sha256": audit_schedule.audit_actor_id_sha256,
        "resolution_owner_id_sha256": audit_schedule.resolution_owner_id_sha256,
        "authorization_present": authorization_present,
        "cumulative_phase_total_token_ceiling": PHASE_TOTAL_TOKEN_CEILING,
        "completed_usage_reconstructed_on_resume": True,
        "provider_call_performed": False,
        "credential_accessed": False,
        "network_access_performed": False,
        "reference_execution_performed": False,
        "jev_request_performed": False,
        "next_gate": "AUTHORIZE_J7L_REFERENCE_EXECUTION_V3",
    }


def execute(
    repo_root: Path,
    *,
    confirmation: str,
    zero_spend_confirmed: bool,
    client: UrllibHuaweiClient | None = None,
) -> dict[str, object]:
    root = repo_root.resolve()
    _binding, plan = _load_bound_assets(root)
    auth, auth_sha256 = _authorization(root)

    if confirmation != auth.confirmation_phrase:
        raise ReferenceExecutionError("CONFIRMATION_MISMATCH", "execution confirmation mismatch")
    if not zero_spend_confirmed:
        raise ReferenceExecutionError(
            "ZERO_SPEND_NOT_CONFIRMED",
            "R0 external-spend status must be confirmed before execution",
        )

    _assert_live_git_boundary(root)
    if (root / PUBLIC_RESULT_PATH).exists():
        raise ReferenceExecutionError(
            "REFERENCE_EXECUTION_ALREADY_COMPLETE",
            "public reference execution result already exists",
        )

    cases, model_projection, tool_contract = _load_reference_inputs(root, plan)
    audit_schedule_sha256 = _freeze_audit_schedule(root, cases, plan)

    if auth.reference_audit_schedule_sha256 != audit_schedule_sha256:
        raise ReferenceExecutionError(
            "AUTHORIZATION_AUDIT_SCHEDULE_DRIFT",
            "authorization does not bind the validated audit schedule",
        )
    if auth.audit_actor_id_sha256 != OPERATOR_ID_SHA256:
        raise ReferenceExecutionError(
            "AUTHORIZATION_AUDIT_ACTOR_DRIFT",
            "authorization audit actor identity drifted",
        )
    if auth.resolution_owner_id_sha256 != OPERATOR_ID_SHA256:
        raise ReferenceExecutionError(
            "AUTHORIZATION_RESOLUTION_OWNER_DRIFT",
            "authorization resolution owner identity drifted",
        )

    completed: list[J7LReferenceJudgmentV1] = []
    pending: list[tuple[dict[str, object], dict[str, object], str]] = []
    cumulative_usage = _zero_usage()
    invocation_usage = _zero_usage()

    for case in cases:
        case_id = str(case["case_id"])
        request = _build_request(
            model_projection=model_projection,
            reviewer_safe_state=cast(Mapping[str, object], case["reviewer_safe_state"]),
            tool_contract=tool_contract,
        )
        request_sha256 = sha256_bytes(canonical_json(request).encode("utf-8"))
        prior = _completed_case_evidence(
            root,
            case_id=case_id,
            expected_request_sha256=request_sha256,
        )
        if prior is not None:
            judgment, usage = prior
            completed.append(judgment)
            _add_usage(cumulative_usage, usage)
            continue
        pending.append((case, request, request_sha256))

    if cumulative_usage["total_tokens"] > PHASE_TOTAL_TOKEN_CEILING:
        raise ReferenceExecutionError(
            "REFERENCE_PHASE_TOKEN_CEILING_EXCEEDED",
            "preserved reference usage already exceeds the cumulative phase ceiling",
        )

    consumption_path = root / CONSUMPTION_PATH
    if completed and not consumption_path.exists():
        raise ReferenceExecutionError(
            "COMPLETED_EVIDENCE_WITHOUT_CONSUMPTION",
            "completed reference evidence exists without an authorization consumption marker",
        )
    if consumption_path.exists():
        _validate_consumption_marker(
            root,
            authorization_sha256=auth_sha256,
        )

    api_key: str | None = None
    credential_accessed = False
    if pending:
        if (
            cumulative_usage["total_tokens"] + PER_REQUEST_TOTAL_TOKEN_CEILING
            > PHASE_TOTAL_TOKEN_CEILING
        ):
            raise ReferenceExecutionError(
                "REFERENCE_PHASE_TOKEN_RESERVATION_EXCEEDED",
                "another request could exceed the cumulative reference-phase token ceiling",
            )
        api_key = os.environ.get(auth.credential_env_name)
        credential_accessed = True
        if api_key is None or not api_key.strip():
            raise ReferenceExecutionError(
                "HUAWEI_MAAS_API_KEY_MISSING",
                "HUAWEI_MAAS_API_KEY is unavailable",
            )

        if not consumption_path.exists():
            _create_consumption_marker(
                root,
                auth=auth,
                authorization_sha256=auth_sha256,
                audit_schedule_sha256=audit_schedule_sha256,
            )

    if not pending and not consumption_path.exists():
        raise ReferenceExecutionError(
            "CONSUMPTION_MARKER_MISSING",
            "completed reference set is missing the authorization consumption marker",
        )

    active_client = UrllibHuaweiClient() if client is None else client
    provider_requests = 0

    for case, request, request_sha256 in pending:
        case_id = str(case["case_id"])
        if (
            cumulative_usage["total_tokens"] + PER_REQUEST_TOTAL_TOKEN_CEILING
            > PHASE_TOTAL_TOKEN_CEILING
        ):
            raise ReferenceExecutionError(
                "REFERENCE_PHASE_TOKEN_RESERVATION_EXCEEDED",
                "another request could exceed the cumulative reference-phase token ceiling",
            )

        _write_once(
            root / ATTEMPTS_DIR / f"{case_id}.json",
            {
                "schema_version": "1.0.0",
                "status": "REFERENCE_REQUEST_ATTEMPT_STARTED",
                "case_id": case_id,
                "request_id_sha256": request_sha256,
                "judge_binding_sha256": EXPECTED_BINDING_SHA256,
                "started_at_utc": datetime.now(UTC).isoformat(),
                "retry_permitted": False,
            },
        )

        if api_key is None:
            raise ReferenceExecutionError(
                "CREDENTIAL_STATE_INVALID",
                "provider credential state is unavailable for a pending request",
            )

        result = active_client.post_json(
            _required_str(plan, "chat_endpoint_url", role="execution plan"),
            api_key,
            request,
        )
        provider_requests += 1
        if result.status_code != 200:
            raise ReferenceExecutionError(
                "CHAT_HTTP_STATUS_INVALID",
                f"{case_id} returned HTTP {result.status_code}",
            )

        raw_payload = {
            "schema_version": "1.0.0",
            "case_id": case_id,
            "request_id_sha256": request_sha256,
            "http_status_code": result.status_code,
            "raw_body_sha256": sha256_bytes(result.body),
            "raw_body_base64": base64.b64encode(result.body).decode("ascii"),
            "safe_response_headers": _safe_headers(result.headers),
        }
        _write_once(root / RAW_RESPONSES_DIR / f"{case_id}.json", raw_payload)

        judgment, usage, _ = _validate_response(
            result.body,
            case_id=case_id,
            request_id_sha256=request_sha256,
            judge_binding_sha256=EXPECTED_BINDING_SHA256,
        )
        _write_once(
            root / JUDGMENTS_DIR / f"{case_id}.json",
            judgment.model_dump(mode="json"),
        )

        completed.append(judgment)
        _add_usage(invocation_usage, usage)
        _add_usage(cumulative_usage, usage)

        if cumulative_usage["total_tokens"] > PHASE_TOTAL_TOKEN_CEILING:
            raise ReferenceExecutionError(
                "REFERENCE_PHASE_TOKEN_CEILING_EXCEEDED",
                "reference phase exceeded the cumulative 960,000-token ceiling",
            )

    if len(completed) != PLANNED_REFERENCE_REQUEST_COUNT:
        raise ReferenceExecutionError(
            "REFERENCE_SET_INCOMPLETE",
            "reference execution did not produce 48 valid judgments",
        )

    public_result = {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_EXECUTION_V3_COMPLETE",
        "binding_sha256": EXPECTED_BINDING_SHA256,
        "execution_plan_sha256": EXPECTED_PLAN_SHA256,
        "authorization_sha256": auth_sha256,
        "provider": "huawei_modelarts_maas",
        "model": "glm-5.2",
        "provider_revision_state": "NOT_EXPOSED_BY_PROVIDER",
        "case_count": PLANNED_REFERENCE_REQUEST_COUNT,
        "valid_judgment_count": len(completed),
        "provider_requests_in_this_invocation": provider_requests,
        "provider_requests_in_logical_execution": PLANNED_REFERENCE_REQUEST_COUNT,
        "completed_cases_reused_on_resume": len(completed) - provider_requests,
        "protected_reference_audit_schedule_sha256": audit_schedule_sha256,
        "audit_actor_id_sha256": OPERATOR_ID_SHA256,
        "resolution_owner_id_sha256": OPERATOR_ID_SHA256,
        "observed_prompt_tokens_in_this_invocation": invocation_usage["prompt_tokens"],
        "observed_completion_tokens_in_this_invocation": invocation_usage["completion_tokens"],
        "observed_total_tokens_in_this_invocation": invocation_usage["total_tokens"],
        "observed_reasoning_tokens_in_this_invocation": invocation_usage["reasoning_tokens"],
        "cumulative_observed_prompt_tokens": cumulative_usage["prompt_tokens"],
        "cumulative_observed_completion_tokens": cumulative_usage["completion_tokens"],
        "cumulative_observed_total_tokens": cumulative_usage["total_tokens"],
        "cumulative_observed_reasoning_tokens": cumulative_usage["reasoning_tokens"],
        "cumulative_phase_total_token_ceiling": PHASE_TOTAL_TOKEN_CEILING,
        "completed_usage_reconstructed_on_resume": True,
        "credential_accessed_in_this_invocation": credential_accessed,
        "network_access_performed_in_this_invocation": provider_requests > 0,
        "automatic_retries_performed": 0,
        "completed_case_replays_performed": 0,
        "jev_requests_performed": 0,
        "zero_spend_operator_confirmed_before_execution": True,
        "zero_spend_independently_proven": False,
        "reference_audit_complete": False,
        "reference_coverage_pass": False,
        "next_gate": "AUDIT_J7L_MODEL_DERIVED_REFERENCES_V1",
    }
    _write_once(root / PUBLIC_RESULT_PATH, public_result)
    return public_result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    validate_parser = commands.add_parser("validate")
    validate_parser.add_argument("--repo-root", type=Path, required=True)

    run_parser = commands.add_parser("run")
    run_parser.add_argument("--repo-root", type=Path, required=True)
    run_parser.add_argument("--confirmation", required=True)
    run_parser.add_argument("--zero-spend-confirmed", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = (
            validate(args.repo_root)
            if args.command == "validate"
            else execute(
                args.repo_root,
                confirmation=args.confirmation,
                zero_spend_confirmed=args.zero_spend_confirmed,
            )
        )
    except (ReferenceExecutionError, ValidationError, OSError, json.JSONDecodeError) as error:
        code = (
            error.code
            if isinstance(error, ReferenceExecutionError)
            else "REFERENCE_EXECUTION_FAILED"
        )
        message = (
            error.safe_message
            if isinstance(error, ReferenceExecutionError)
            else "J7L reference execution failed closed"
        )
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
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

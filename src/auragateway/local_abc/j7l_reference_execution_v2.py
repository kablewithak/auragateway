"""Governed J7L model-derived reference execution over Huawei GLM-5.2."""

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
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from auragateway.contracts.quality_development_evaluation_v2 import (
    J7LReferenceJudgmentV1,
    J7LReferenceToolArgumentsV1,
)

BINDING_PATH = Path("data/evals/quality/j7l-reference-judge-binding-v2/binding.json")
PLAN_PATH = Path("data/evals/quality/j7l-reference-judge-binding-v2/reference_execution_plan.json")
AUTHORIZATION_PATH = Path(
    "data/evals/quality/j7l-reference-execution-authorization-v2/authorization.json"
)

EXPECTED_BINDING_SHA256 = "7c87832c697b66414921fef76f80466ef3b0c89421969d53acc6d35aa3906b1f"
EXPECTED_PLAN_SHA256 = "b1984893fb5549cadb75de16d2cb9901d37a08bd23ff1b3257749143d501d490"

CONSUMPTION_PATH = Path(".local/auragateway/j7l-reference-execution-v2/authorization_consumed.json")
AUDIT_SCHEDULE_PATH = Path(
    ".local/auragateway/j7l-reference-execution-v2/reference_audit_schedule.json"
)
ATTEMPTS_DIR = Path(".local/auragateway/j7l-reference-execution-v2/attempts")
RAW_RESPONSES_DIR = Path(".local/auragateway/j7l-reference-execution-v2/raw-responses")
JUDGMENTS_DIR = Path(".local/auragateway/j7l-reference-execution-v2/judgments")
PUBLIC_RESULT_PATH = Path(
    "data/evals/quality/j7l-reference-judge-binding-v2/reference_execution_result.json"
)

_TIMEOUT_SECONDS = 90
_MAX_RESPONSE_BYTES = 2 * 1024 * 1024


class ReferenceExecutionError(RuntimeError):
    """Fail-closed J7L reference execution error."""

    def __init__(self, code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.code = code
        self.safe_message = safe_message


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorizationV2(FrozenModel):
    schema_version: Literal["1.0.0"]
    authorization_id: Literal["j7l-reference-execution-authorization-v2"]
    status: Literal["active"]
    binding_path: Literal["data/evals/quality/j7l-reference-judge-binding-v2/binding.json"]
    binding_sha256: Literal["7c87832c697b66414921fef76f80466ef3b0c89421969d53acc6d35aa3906b1f"]
    execution_plan_path: Literal[
        "data/evals/quality/j7l-reference-judge-binding-v2/reference_execution_plan.json"
    ]
    execution_plan_sha256: Literal[
        "b1984893fb5549cadb75de16d2cb9901d37a08bd23ff1b3257749143d501d490"
    ]
    confirmation_phrase: Literal["EXECUTE_J7L_REFERENCE_SET_V2"]
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
    external_spend_ceiling_zar: Literal[0]
    paid_fallback_permitted: Literal[False]
    jev_request_permitted: Literal[False]
    zero_spend_confirmation_required: Literal[True]
    clean_main_required: Literal[True]

    @model_validator(mode="after")
    def validate_policy(self) -> AuthorizationV2:
        if self.maximum_model_inference_requests != 48:
            raise ValueError("reference authorization must remain exactly 48 requests")
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
                    headers={str(k).lower(): str(v) for k, v in response.headers.items()},
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
    if plan.get("binding_sha256") != EXPECTED_BINDING_SHA256:
        raise ReferenceExecutionError("PLAN_BINDING_DRIFT", "plan binding identity drifted")
    return binding, plan


def _assert_hash(path: Path, expected: str, *, role: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise ReferenceExecutionError(f"{role}_MISSING", f"{role} is missing or unsafe")
    if sha256_file(path) != expected:
        raise ReferenceExecutionError(f"{role}_HASH_MISMATCH", f"{role} hash drifted")


def _load_reference_inputs(
    repo_root: Path,
    plan: Mapping[str, object],
) -> tuple[tuple[dict[str, object], ...], object, Mapping[str, object]]:
    schedule_path = repo_root / str(plan["protected_case_schedule_path"])
    primary_path = repo_root / str(plan["protected_primary_export_path"])
    projection_path = repo_root / str(plan["model_projection_path"])
    tool_path = repo_root / str(plan["named_tool_contract_path"])
    qualification_path = repo_root / str(plan["qualification_result_path"])

    _assert_hash(
        schedule_path,
        str(plan["protected_case_schedule_sha256"]),
        role="PROTECTED_CASE_SCHEDULE",
    )
    _assert_hash(
        primary_path,
        str(plan["protected_primary_export_sha256"]),
        role="PROTECTED_PRIMARY_EXPORT",
    )
    _assert_hash(
        projection_path,
        str(plan["model_projection_sha256"]),
        role="MODEL_PROJECTION",
    )
    _assert_hash(
        tool_path,
        str(plan["named_tool_contract_sha256"]),
        role="NAMED_TOOL_CONTRACT",
    )
    _assert_hash(
        qualification_path,
        str(plan["qualification_result_sha256"]),
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


def _audit_schedule_bytes(cases: tuple[dict[str, object], ...]) -> bytes:
    protected = [
        str(case["case_id"])
        for case in cases
        if case.get("family") in {"terminal_non_substantive", "ontology_near_miss"}
    ]
    ordinary = [str(case["case_id"]) for case in cases if case.get("family") == "ordinary_clean"]
    clear_failure = [
        str(case["case_id"]) for case in cases if case.get("family") == "clear_failure"
    ]

    if len(protected) != 24 or len(ordinary) != 12 or len(clear_failure) != 12:
        raise ReferenceExecutionError(
            "AUDIT_STRATUM_INVALID",
            "protected case-family counts drifted",
        )

    payload = {
        "schema_version": "1.0.0",
        "schedule_id": "j7l-reference-audit-schedule-v1",
        "protected_secondary_case_ids": protected,
        "additional_spot_check_case_ids": ordinary[:2] + clear_failure[:2],
        "selection_rule": (
            "first two ordinary_clean and first two clear_failure cases in frozen case order"
        ),
        "schedule_frozen_before_reference_execution": True,
        "audit_may_rewrite_reference": False,
        "material_disagreement_invalidates_reference_set": True,
    }
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _freeze_audit_schedule(repo_root: Path, cases: tuple[dict[str, object], ...]) -> str:
    expected_bytes = _audit_schedule_bytes(cases)
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

    usage_value = response.get("usage")
    usage = _mapping(usage_value, role="usage")
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
    if total_tokens > 20000:
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


def _authorization(repo_root: Path) -> tuple[AuthorizationV2, str]:
    path = repo_root / AUTHORIZATION_PATH
    if not path.is_file() or path.is_symlink():
        raise ReferenceExecutionError(
            "AUTHORIZATION_MISSING",
            "reference execution authorization is missing",
        )
    auth = AuthorizationV2.model_validate(_load_json(path))
    return auth, sha256_file(path)


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
    audit_schedule_sha = sha256_bytes(_audit_schedule_bytes(cases))
    auth_present = (root / AUTHORIZATION_PATH).is_file()

    return {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_EXECUTION_V2_NONLIVE_READY",
        "binding_id": binding["binding_id"],
        "binding_sha256": EXPECTED_BINDING_SHA256,
        "execution_plan_sha256": EXPECTED_PLAN_SHA256,
        "case_count": len(cases),
        "first_request_body_sha256": sha256_bytes(canonical_json(request).encode("utf-8")),
        "reference_audit_schedule_sha256": audit_schedule_sha,
        "authorization_present": auth_present,
        "provider_call_performed": False,
        "credential_accessed": False,
        "network_access_performed": False,
        "reference_execution_performed": False,
        "next_gate": "AUTHORIZE_J7L_REFERENCE_EXECUTION_V2",
    }


def _completed_judgment(repo_root: Path, case_id: str) -> J7LReferenceJudgmentV1 | None:
    attempt = repo_root / ATTEMPTS_DIR / f"{case_id}.json"
    judgment_path = repo_root / JUDGMENTS_DIR / f"{case_id}.json"

    if not attempt.exists() and not judgment_path.exists():
        return None
    if attempt.exists() and not judgment_path.exists():
        raise ReferenceExecutionError(
            "UNRESOLVED_PRIOR_ATTEMPT",
            f"{case_id} has an attempted request without a valid judgment; do not retry",
        )
    if not attempt.exists() and judgment_path.exists():
        raise ReferenceExecutionError(
            "JUDGMENT_WITHOUT_ATTEMPT",
            f"{case_id} has a judgment without an attempt marker",
        )
    return J7LReferenceJudgmentV1.model_validate(_load_json(judgment_path))


def execute(
    repo_root: Path,
    *,
    confirmation: str,
    zero_spend_confirmed: bool,
    client: UrllibHuaweiClient | None = None,
) -> dict[str, object]:
    root = repo_root.resolve()
    _binding, plan = _load_bound_assets(root)
    auth, auth_sha = _authorization(root)

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
    audit_schedule_sha = _freeze_audit_schedule(root, cases)

    api_key = os.environ.get(auth.credential_env_name)
    if api_key is None or not api_key.strip():
        raise ReferenceExecutionError(
            "HUAWEI_MAAS_API_KEY_MISSING",
            "HUAWEI_MAAS_API_KEY is unavailable",
        )

    consumption = root / CONSUMPTION_PATH
    if not consumption.exists():
        _write_once(
            consumption,
            {
                "schema_version": "1.0.0",
                "status": "REFERENCE_EXECUTION_AUTHORIZATION_CONSUMED",
                "authorization_id": auth.authorization_id,
                "authorization_sha256": auth_sha,
                "binding_sha256": EXPECTED_BINDING_SHA256,
                "execution_plan_sha256": EXPECTED_PLAN_SHA256,
                "consumed_at_utc": datetime.now(UTC).isoformat(),
                "logical_session_resume_after_completed_cases_permitted": True,
                "automatic_retry_permitted": False,
                "ambiguous_attempt_retry_permitted": False,
            },
        )
    if consumption.exists():
        consumed_payload = _mapping(_load_json(consumption), role="consumption marker")
        if consumed_payload.get("authorization_sha256") != auth_sha:
            raise ReferenceExecutionError(
                "CONSUMPTION_AUTHORIZATION_DRIFT",
                "consumption marker belongs to a different authorization",
            )

    active_client = UrllibHuaweiClient() if client is None else client
    completed: list[J7LReferenceJudgmentV1] = []
    total_prompt = 0
    total_completion = 0
    total_tokens = 0
    total_reasoning = 0
    provider_requests = 0

    for case in cases:
        case_id = str(case["case_id"])
        existing = _completed_judgment(root, case_id)
        if existing is not None:
            completed.append(existing)
            continue

        request = _build_request(
            model_projection=model_projection,
            reviewer_safe_state=cast(Mapping[str, object], case["reviewer_safe_state"]),
            tool_contract=tool_contract,
        )
        request_bytes = canonical_json(request).encode("utf-8")
        request_sha = sha256_bytes(request_bytes)

        _write_once(
            root / ATTEMPTS_DIR / f"{case_id}.json",
            {
                "schema_version": "1.0.0",
                "status": "REFERENCE_REQUEST_ATTEMPT_STARTED",
                "case_id": case_id,
                "request_id_sha256": request_sha,
                "judge_binding_sha256": EXPECTED_BINDING_SHA256,
                "started_at_utc": datetime.now(UTC).isoformat(),
                "retry_permitted": False,
            },
        )

        result = active_client.post_json(
            str(plan["chat_endpoint_url"]),
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
            "request_id_sha256": request_sha,
            "http_status_code": result.status_code,
            "raw_body_sha256": sha256_bytes(result.body),
            "raw_body_base64": base64.b64encode(result.body).decode("ascii"),
            "safe_response_headers": _safe_headers(result.headers),
        }
        _write_once(root / RAW_RESPONSES_DIR / f"{case_id}.json", raw_payload)

        judgment, usage, _ = _validate_response(
            result.body,
            case_id=case_id,
            request_id_sha256=request_sha,
            judge_binding_sha256=EXPECTED_BINDING_SHA256,
        )

        _write_once(
            root / JUDGMENTS_DIR / f"{case_id}.json",
            judgment.model_dump(mode="json"),
        )
        completed.append(judgment)
        total_prompt += usage["prompt_tokens"]
        total_completion += usage["completion_tokens"]
        total_tokens += usage["total_tokens"]
        total_reasoning += usage["reasoning_tokens"]

        if total_tokens > 960000:
            raise ReferenceExecutionError(
                "REFERENCE_PHASE_TOKEN_CEILING_EXCEEDED",
                "reference phase exceeded the 960,000-token operational ceiling",
            )

    if len(completed) != 48:
        raise ReferenceExecutionError(
            "REFERENCE_SET_INCOMPLETE",
            "reference execution did not produce 48 valid judgments",
        )

    public_result = {
        "schema_version": "1.0.0",
        "status": "J7L_REFERENCE_EXECUTION_V2_COMPLETE",
        "binding_sha256": EXPECTED_BINDING_SHA256,
        "execution_plan_sha256": EXPECTED_PLAN_SHA256,
        "authorization_sha256": auth_sha,
        "provider": "huawei_modelarts_maas",
        "model": "glm-5.2",
        "provider_revision_state": "NOT_EXPOSED_BY_PROVIDER",
        "case_count": 48,
        "valid_judgment_count": 48,
        "provider_requests_in_this_invocation": provider_requests,
        "protected_reference_audit_schedule_sha256": audit_schedule_sha,
        "observed_prompt_tokens_in_this_invocation": total_prompt,
        "observed_completion_tokens_in_this_invocation": total_completion,
        "observed_total_tokens_in_this_invocation": total_tokens,
        "observed_reasoning_tokens_in_this_invocation": total_reasoning,
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

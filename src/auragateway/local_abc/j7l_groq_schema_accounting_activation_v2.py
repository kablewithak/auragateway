"""Execute one activated J7L Groq strict-schema accounting observation."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable, Mapping
from importlib import metadata
from pathlib import Path
from typing import Any, Literal, Protocol, TypeVar, cast

from groq import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator, model_validator

from auragateway.contracts.j7l_groq_schema_accounting_probe_v2 import (
    SchemaAccountingProbePlanV2,
)

AUTHORIZATION_PATH = Path(
    "data/evals/quality/j7l-groq-schema-accounting-activation-v2/authorization.json"
)
RESULT_PATH = Path(
    "data/evals/quality/j7l-groq-schema-accounting-activation-v2/observation_result.json"
)
_SCHEMA_NAME = "j7l_schema_accounting_probe"
_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)

_PROVIDER_ERRORS = (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    ConflictError,
    InternalServerError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
    UnprocessableEntityError,
)


class ActivationError(RuntimeError):
    """Fail-closed activation or live-execution error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ActivationV2(BaseModel):
    """Human-authorized execution boundary for the frozen V2 probe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    authorization_id: Literal["j7l-groq-schema-accounting-activation-v2"]
    status: Literal["active"]
    plan_path: Literal["data/evals/quality/j7l-groq-schema-accounting-review-v1/probe_plan_v2.json"]
    plan_canonical_sha256: str
    confirmation_phrase: Literal["EXECUTE_J7L_GROQ_SCHEMA_ACCOUNTING_PROBE_ONCE"]
    provider_call_authorized: Literal[True]
    execution_command_available: Literal[True]
    maximum_provider_calls: Literal[2]
    free_tier_required: Literal[True]
    paid_fallback_permitted: Literal[False]
    external_spend_ceiling_zar: Literal[0]
    retry_permitted: Literal[False]
    resume_permitted: Literal[False]
    rerun_permitted: Literal[False]
    j7l_reference_request_permitted: Literal[False]
    jev_request_permitted: Literal[False]

    @field_validator("plan_canonical_sha256")
    @classmethod
    def validate_hash(cls, value: str) -> str:
        if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
            raise ValueError("plan_canonical_sha256 must be lowercase SHA-256")
        return value


class PromptMessage(BaseModel):
    """One frozen synthetic probe message."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    role: Literal["system", "user"]
    content: str


class PromptRecipe(BaseModel):
    """Frozen synthetic-only prompt recipe."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    recipe_id: Literal["j7l-groq-schema-accounting-synthetic-prompt-v1"]
    messages: tuple[PromptMessage, PromptMessage]
    synthetic_only: Literal[True]
    contains_j7l_case_content: Literal[False]
    contains_jev_content: Literal[False]
    contains_reference_answers: Literal[False]

    @model_validator(mode="after")
    def validate_roles(self) -> PromptRecipe:
        if tuple(message.role for message in self.messages) != ("system", "user"):
            raise ValueError("prompt roles must remain system then user")
        return self


class HttpResponse(Protocol):
    """Minimal raw HTTP response boundary used by the probe."""

    content: bytes
    status_code: int
    headers: Mapping[str, str]


class ParsedCompletion(Protocol):
    """Minimal parsed completion boundary used for protected evidence."""

    def model_dump(
        self,
        *,
        mode: str = "python",
        exclude_none: bool = False,
        exclude_unset: bool = False,
    ) -> dict[str, object]:
        """Return a serializable response mapping."""


class RawResponse(Protocol):
    """Minimal raw-response SDK boundary."""

    http_response: HttpResponse

    def parse(self) -> ParsedCompletion:
        """Parse this exact raw response."""

    def close(self) -> None:
        """Release response resources."""


class RawClient(Protocol):
    """Narrow client seam for the two governed calls."""

    def create(self, request: dict[str, object]) -> RawResponse:
        """Create one raw-response chat completion."""

    def close(self) -> None:
        """Close provider resources."""


class SdkRawClient:
    """Groq SDK implementation with retries disabled."""

    def __init__(self, api_key: str, timeout_seconds: int) -> None:
        from groq import Groq

        self._client = Groq(
            api_key=api_key,
            max_retries=0,
            timeout=timeout_seconds,
        )

    def create(self, request: dict[str, object]) -> RawResponse:
        resource = cast(Any, self._client.chat.completions.with_raw_response)
        return cast(RawResponse, resource.create(**request))

    def close(self) -> None:
        self._client.close()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_model(path: Path, model_type: type[_MODEL_T]) -> _MODEL_T:
    return model_type.model_validate(_load_json(path))


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _json_object(path: Path) -> Mapping[str, object]:
    value = _load_json(path)
    if not isinstance(value, Mapping):
        raise ActivationError("JSON_SHAPE_INVALID", f"{path} is not a JSON object")
    return cast(Mapping[str, object], value)


def _load_assets(
    repo_root: Path,
) -> tuple[ActivationV2, SchemaAccountingProbePlanV2, PromptRecipe, Mapping[str, object]]:
    root = repo_root.resolve()
    auth = _load_model(root / AUTHORIZATION_PATH, ActivationV2)

    plan_path = root / auth.plan_path
    raw_plan = _load_json(plan_path)
    if _canonical_sha256(raw_plan) != auth.plan_canonical_sha256:
        raise ActivationError(
            "PLAN_HASH_MISMATCH",
            "Activated V2 plan canonical identity drifted.",
        )
    plan = SchemaAccountingProbePlanV2.model_validate(raw_plan)

    if not plan.activation_required:
        raise ActivationError("PLAN_STATE_INVALID", "V2 plan no longer requires activation.")
    if plan.provider_call_authorized or plan.execution_command_available:
        raise ActivationError(
            "PLAN_STATE_INVALID",
            "Frozen V2 plan authority was mutated instead of activated externally.",
        )

    prompt_path = root / plan.prompt_recipe_path
    schema_path = root / plan.strict_response_schema_path
    if _sha256_file(prompt_path) != plan.prompt_recipe_sha256:
        raise ActivationError("PROMPT_HASH_MISMATCH", "Synthetic prompt recipe hash drifted.")
    if _sha256_file(schema_path) != plan.strict_response_schema_sha256:
        raise ActivationError("SCHEMA_HASH_MISMATCH", "Strict response schema hash drifted.")

    recipe = _load_model(prompt_path, PromptRecipe)
    schema = _json_object(schema_path)
    return auth, plan, recipe, schema


def _protected_evidence_paths(
    repo_root: Path,
    plan: SchemaAccountingProbePlanV2,
) -> tuple[Path, Path]:
    return (
        repo_root / plan.protected_raw_responses_path,
        repo_root / plan.protected_parsed_responses_path,
    )


def _assert_fresh_execution(repo_root: Path, plan: SchemaAccountingProbePlanV2) -> None:
    candidates = (*_protected_evidence_paths(repo_root, plan), repo_root / RESULT_PATH)
    if any(path.exists() for path in candidates):
        raise ActivationError(
            "EXECUTION_ALREADY_EXISTS",
            "Probe evidence already exists; rerun and resume are forbidden.",
        )


def _assert_sdk(plan: SchemaAccountingProbePlanV2) -> str:
    observed = metadata.version("groq")
    if observed != plan.installed_sdk_version_required:
        raise ActivationError(
            "SDK_VERSION_MISMATCH",
            f"Expected Groq SDK {plan.installed_sdk_version_required}; observed {observed}.",
        )
    return observed


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
        raise ActivationError("GIT_INSPECTION_FAILED", "Required Git inspection failed.")
    return completed.stdout.strip()


def _assert_live_git_boundary(repo_root: Path) -> None:
    if _git_text(repo_root, "branch", "--show-current") != "main":
        raise ActivationError("LIVE_BRANCH_INVALID", "Live execution requires branch main.")
    tracked = _git_text(repo_root, "status", "--porcelain=v1", "--untracked-files=no")
    if tracked:
        raise ActivationError(
            "TRACKED_WORKTREE_DIRTY",
            "Live execution requires a clean tracked working tree.",
        )


def validate_activation(repo_root: Path) -> dict[str, object]:
    """Validate merged activation without reading credentials or calling Groq."""

    auth, plan, _, _ = _load_assets(repo_root)
    sdk = _assert_sdk(plan)
    raw_path, parsed_path = _protected_evidence_paths(repo_root, plan)
    return {
        "status": "J7L_GROQ_SCHEMA_ACCOUNTING_ACTIVATION_V2_PASS",
        "authorization_id": auth.authorization_id,
        "installed_groq_sdk_version": sdk,
        "maximum_provider_calls": plan.maximum_provider_calls,
        "maximum_completion_tokens": plan.maximum_completion_tokens,
        "provider_call_performed": False,
        "credential_accessed": False,
        "raw_evidence_exists": raw_path.exists(),
        "parsed_evidence_exists": parsed_path.exists(),
        "result_exists": (repo_root / RESULT_PATH).exists(),
    }


def _append_jsonl(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _usage(payload: Mapping[str, object]) -> tuple[int, int, int | None]:
    value = payload.get("usage")
    if not isinstance(value, Mapping):
        raise ActivationError("USAGE_MISSING", "Provider response usage is missing.")
    usage = cast(Mapping[str, object], value)

    def required(name: str) -> int:
        item = usage.get(name)
        if isinstance(item, bool) or not isinstance(item, int) or item < 0:
            raise ActivationError("USAGE_INVALID", f"usage.{name} is invalid.")
        return item

    total_value = usage.get("total_tokens")
    total = required("total_tokens") if total_value is not None else None
    return required("prompt_tokens"), required("completion_tokens"), total


def _rate_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
        if str(key).lower().startswith("x-ratelimit-")
    }


def _execute_attempt(
    client: RawClient,
    request: dict[str, object],
    *,
    index: int,
    role: str,
    raw_path: Path,
    parsed_path: Path,
) -> tuple[int, int, int | None]:
    try:
        raw = client.create(request)
    except _PROVIDER_ERRORS as error:
        raise ActivationError(
            "PROVIDER_CALL_FAILED",
            f"Groq provider call failed with {type(error).__name__}.",
        ) from error

    try:
        body = bytes(raw.http_response.content)
        _append_jsonl(
            raw_path,
            {
                "attempt_index": index,
                "request_role": role,
                "http_status_code": raw.http_response.status_code,
                "raw_body_sha256": hashlib.sha256(body).hexdigest(),
                "raw_body_base64": base64.b64encode(body).decode("ascii"),
                "rate_limit_headers": _rate_headers(raw.http_response.headers),
            },
        )

        raw_payload = json.loads(body)
        if not isinstance(raw_payload, Mapping):
            raise ActivationError(
                "RAW_RESPONSE_INVALID",
                "Raw provider response is not a JSON object.",
            )
        observed_usage = _usage(cast(Mapping[str, object], raw_payload))

        parsed_payload = raw.parse().model_dump(
            mode="json",
            exclude_none=False,
            exclude_unset=False,
        )
        _append_jsonl(
            parsed_path,
            {
                "attempt_index": index,
                "request_role": role,
                "parsed_response": parsed_payload,
            },
        )
        return observed_usage
    finally:
        raw.close()


def _build_requests(
    plan: SchemaAccountingProbePlanV2,
    recipe: PromptRecipe,
    schema: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    control: dict[str, object] = {
        "messages": [message.model_dump(mode="json") for message in recipe.messages],
        "model": plan.exact_model_identifier,
        "max_completion_tokens": plan.maximum_completion_tokens,
        "temperature": plan.temperature_milli / 1000,
        "stream": plan.streaming,
        "store": plan.storage,
        "reasoning_effort": plan.reasoning_effort,
    }

    strict = dict(control)
    strict["response_format"] = {
        "type": "json_schema",
        "json_schema": {
            "name": _SCHEMA_NAME,
            "strict": True,
            "schema": dict(schema),
        },
    }

    if set(strict) != set(control) | {"response_format"}:
        raise ActivationError(
            "REQUEST_SHAPE_DRIFT",
            "Strict request changed more than response_format.",
        )
    for key, value in control.items():
        if strict[key] != value:
            raise ActivationError("REQUEST_VALUE_DRIFT", f"Request field {key} drifted.")

    return control, strict


def execute_probe(
    repo_root: Path,
    *,
    confirmation: str,
    free_tier_confirmed: bool,
    client: RawClient | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    live_boundary: Callable[[Path], None] = _assert_live_git_boundary,
) -> dict[str, object]:
    """Consume the authorization once and perform exactly two provider calls."""

    root = repo_root.resolve()
    auth, plan, recipe, schema = _load_assets(root)
    _assert_sdk(plan)

    if confirmation != auth.confirmation_phrase:
        raise ActivationError(
            "CONFIRMATION_MISMATCH",
            "Execution confirmation phrase is invalid.",
        )
    if not free_tier_confirmed:
        raise ActivationError(
            "FREE_TIER_NOT_CONFIRMED",
            "Free-tier status must be confirmed before provider execution.",
        )

    live_boundary(root)
    _assert_fresh_execution(root, plan)

    control, strict = _build_requests(plan, recipe, schema)
    raw_path, parsed_path = _protected_evidence_paths(root, plan)

    active_client = client
    if active_client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if api_key is None or not api_key.strip():
            raise ActivationError("GROQ_API_KEY_MISSING", "GROQ_API_KEY is unavailable.")
        active_client = SdkRawClient(api_key, plan.timeout_seconds)

    start = monotonic()
    observations: list[tuple[int, int, int | None]] = []
    try:
        for index, (role, offset, request) in enumerate(
            zip(
                plan.request_roles,
                plan.attempt_offsets_seconds,
                (control, strict),
                strict=True,
            )
        ):
            remaining = start + offset - monotonic()
            if remaining > 0:
                sleep(remaining)

            observations.append(
                _execute_attempt(
                    active_client,
                    request,
                    index=index,
                    role=role,
                    raw_path=raw_path,
                    parsed_path=parsed_path,
                )
            )
    finally:
        active_client.close()

    control_prompt_tokens = observations[0][0]
    strict_prompt_tokens = observations[1][0]
    delta = strict_prompt_tokens - control_prompt_tokens

    outcome = "no_prompt_token_delta_observed"
    if delta > 0:
        outcome = "strict_schema_prompt_tokens_higher"
    if delta < 0:
        outcome = "negative_delta_invalid"

    result: dict[str, object] = {
        "schema_version": "1.0.0",
        "status": "J7L_GROQ_SCHEMA_ACCOUNTING_OBSERVATION_COMPLETE",
        "authorization_id": auth.authorization_id,
        "provider_call_count": 2,
        "control_prompt_tokens": control_prompt_tokens,
        "strict_prompt_tokens": strict_prompt_tokens,
        "prompt_token_delta": delta,
        "outcome": outcome,
        "rerun_permitted": False,
        "resume_permitted": False,
        "j7l_reference_request_performed": False,
        "jev_request_performed": False,
    }
    _write_json(root / RESULT_PATH, result)
    return result


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate")
    validate.add_argument("--repo-root", type=Path, required=True)

    run = subparsers.add_parser("run")
    run.add_argument("--repo-root", type=Path, required=True)
    run.add_argument("--confirmation", required=True)
    run.add_argument("--free-tier-confirmed", action="store_true")

    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = (
            validate_activation(args.repo_root)
            if args.command == "validate"
            else execute_probe(
                args.repo_root,
                confirmation=args.confirmation,
                free_tier_confirmed=args.free_tier_confirmed,
            )
        )
    except (
        ActivationError,
        ValidationError,
        OSError,
        json.JSONDecodeError,
        metadata.PackageNotFoundError,
    ) as error:
        code = error.code if isinstance(error, ActivationError) else "ACTIVATION_FAILED"
        message = (
            error.message
            if isinstance(error, ActivationError)
            else "J7L Groq schema-accounting activation failed."
        )
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                sort_keys=True,
                separators=(",", ":"),
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

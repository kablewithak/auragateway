"""Standalone V2 runtime with exact current-request and prospective next-request budget guards."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, TypeAlias

from auragateway.local_abc.measured_abc_variance_pilot_v2_output_admission_runtime import (
    RuntimeOutputAdmissionError,
    admit_response,
)

JsonHistory: TypeAlias = list[dict[str, str]]
MessageList: TypeAlias = list[dict[str, str]]
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256


class StandaloneRuntimeV2Error(RuntimeError):
    """Metadata-safe fail-closed V2 runtime failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


@dataclass(frozen=True)
class RuntimeTurnRequest:
    request_id: str
    user_content: str
    worker_id: str


@dataclass(frozen=True)
class TokenBudgetObservation:
    request_id: str
    prompt_token_count: int
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    max_model_len: int = MAX_MODEL_LEN


@dataclass(frozen=True)
class TrajectoryExecutionResult:
    completed_turn_count: int
    request_attempt_count: int
    failed: bool
    failure_code: str | None


TokenCounter: TypeAlias = Callable[[MessageList], int]
MessageRenderer: TypeAlias = Callable[[RuntimeTurnRequest, JsonHistory], MessageList]
ResponseSender: TypeAlias = Callable[[RuntimeTurnRequest, MessageList], object]


def _validate_messages(messages: MessageList) -> None:
    if not isinstance(messages, list) or not messages:
        raise StandaloneRuntimeV2Error(
            "V2_RUNTIME_MESSAGES_INVALID",
            "rendered request messages must be a non-empty list",
        )
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise StandaloneRuntimeV2Error(
                "V2_RUNTIME_MESSAGES_INVALID",
                "rendered request message shape is invalid",
            )
        if not isinstance(message.get("role"), str) or not message["role"]:
            raise StandaloneRuntimeV2Error(
                "V2_RUNTIME_MESSAGES_INVALID",
                "rendered request role is invalid",
            )
        if not isinstance(message.get("content"), str):
            raise StandaloneRuntimeV2Error(
                "V2_RUNTIME_MESSAGES_INVALID",
                "rendered request content is invalid",
            )


def check_token_budget(
    request_id: str,
    messages: MessageList,
    token_counter: TokenCounter,
) -> TokenBudgetObservation:
    if not isinstance(request_id, str) or not request_id:
        raise StandaloneRuntimeV2Error(
            "V2_RUNTIME_REQUEST_ID_INVALID",
            "request identity must be a non-empty string",
        )
    _validate_messages(messages)
    prompt_tokens = token_counter(messages)
    if not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool) or prompt_tokens < 0:
        raise StandaloneRuntimeV2Error(
            "V2_RUNTIME_TOKEN_COUNT_INVALID",
            "accepted tokenizer returned an invalid prompt-token count",
        )
    if prompt_tokens + MAX_OUTPUT_TOKENS > MAX_MODEL_LEN:
        raise StandaloneRuntimeV2Error(
            "V2_RUNTIME_TOKEN_BUDGET_EXCEEDED",
            "prompt plus frozen output budget exceeds max_model_len",
        )
    return TokenBudgetObservation(request_id=request_id, prompt_token_count=prompt_tokens)


def _candidate_history(
    history: JsonHistory,
    user_content: str,
    assistant_content: str,
) -> JsonHistory:
    return [
        *({"role": item["role"], "content": item["content"]} for item in history),
        {"role": "user", "content": user_content},
        {"role": "assistant", "content": assistant_content},
    ]


def _prospective_next_turn_check(
    *,
    next_request: RuntimeTurnRequest,
    candidate_history: JsonHistory,
    render_messages: MessageRenderer,
    token_counter: TokenCounter,
) -> None:
    next_messages = render_messages(next_request, candidate_history)
    try:
        check_token_budget(next_request.request_id, next_messages, token_counter)
    except StandaloneRuntimeV2Error as exc:
        if exc.error_code == "V2_RUNTIME_TOKEN_BUDGET_EXCEEDED":
            raise StandaloneRuntimeV2Error(
                "V2_RUNTIME_REACHABLE_PROMPT_BUDGET_REJECTED",
                "admitted output would make the next reachable prompt exceed budget",
            ) from exc
        raise


def execute_turn(
    *,
    request: RuntimeTurnRequest,
    history: JsonHistory,
    admission_spec: object,
    render_messages: MessageRenderer,
    token_counter: TokenCounter,
    send_response: ResponseSender,
    next_request: RuntimeTurnRequest | None = None,
) -> TokenBudgetObservation:
    if not request.user_content:
        raise StandaloneRuntimeV2Error(
            "V2_RUNTIME_USER_CONTENT_INVALID",
            "runtime turn user content must be non-empty",
        )
    messages = render_messages(request, history)
    observation = check_token_budget(request.request_id, messages, token_counter)
    response = send_response(request, messages)
    admitted = admit_response(response, admission_spec)
    candidate = _candidate_history(history, request.user_content, admitted.canonical_json)
    if next_request is not None:
        _prospective_next_turn_check(
            next_request=next_request,
            candidate_history=candidate,
            render_messages=render_messages,
            token_counter=token_counter,
        )
    history.extend(candidate[len(history) :])
    return observation


def execute_trajectory(
    *,
    requests: tuple[RuntimeTurnRequest, RuntimeTurnRequest, RuntimeTurnRequest, RuntimeTurnRequest],
    history: JsonHistory,
    admission_spec: object,
    render_messages: MessageRenderer,
    token_counter: TokenCounter,
    send_response: ResponseSender,
) -> TrajectoryExecutionResult:
    completed = 0
    attempts = 0
    for index, request in enumerate(requests):
        try:
            messages = render_messages(request, history)
            check_token_budget(request.request_id, messages, token_counter)
            attempts += 1
            response = send_response(request, messages)
            admitted = admit_response(response, admission_spec)
            candidate = _candidate_history(history, request.user_content, admitted.canonical_json)
            if index < len(requests) - 1:
                _prospective_next_turn_check(
                    next_request=requests[index + 1],
                    candidate_history=candidate,
                    render_messages=render_messages,
                    token_counter=token_counter,
                )
            history.extend(candidate[len(history) :])
        except StandaloneRuntimeV2Error as exc:
            return TrajectoryExecutionResult(
                completed_turn_count=completed,
                request_attempt_count=attempts,
                failed=True,
                failure_code=exc.error_code,
            )
        except RuntimeOutputAdmissionError as exc:
            return TrajectoryExecutionResult(
                completed_turn_count=completed,
                request_attempt_count=attempts,
                failed=True,
                failure_code=exc.error_code,
            )
        completed += 1
    return TrajectoryExecutionResult(
        completed_turn_count=completed,
        request_attempt_count=attempts,
        failed=False,
        failure_code=None,
    )

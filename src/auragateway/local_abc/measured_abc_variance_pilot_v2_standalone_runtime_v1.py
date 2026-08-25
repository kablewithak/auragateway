"""Stdlib-only token admission and atomic trajectory execution for variance-pilot V2."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final, TypeAlias

from auragateway.local_abc.measured_abc_variance_pilot_v2_output_admission_runtime import (
    RuntimeOutputAdmissionError,
    admit_and_commit_turn,
)

JsonHistory: TypeAlias = list[dict[str, str]]
MessageList: TypeAlias = list[dict[str, str]]
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256


class StandaloneRuntimeError(RuntimeError):
    """Metadata-safe fail-closed standalone runtime failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


@dataclass(frozen=True)
class RuntimeTurnRequest:
    """One already-realized V2 request position."""

    request_id: str
    user_content: str
    worker_id: str


@dataclass(frozen=True)
class TokenBudgetObservation:
    """Exact accepted-tokenizer observation made immediately before request send."""

    request_id: str
    prompt_token_count: int
    max_output_tokens: int = MAX_OUTPUT_TOKENS
    max_model_len: int = MAX_MODEL_LEN


@dataclass(frozen=True)
class TrajectoryExecutionResult:
    """Terminal trajectory state without raw prompt or raw response retention."""

    completed_turn_count: int
    request_attempt_count: int
    failed: bool
    failure_code: str | None


TokenCounter: TypeAlias = Callable[[MessageList], int]
MessageRenderer: TypeAlias = Callable[[RuntimeTurnRequest, JsonHistory], MessageList]
ResponseSender: TypeAlias = Callable[[RuntimeTurnRequest, MessageList], object]


def _validate_messages(messages: MessageList) -> None:
    if not isinstance(messages, list) or not messages:
        raise StandaloneRuntimeError(
            "V2_RUNTIME_MESSAGES_INVALID",
            "rendered request messages must be a non-empty list",
        )
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise StandaloneRuntimeError(
                "V2_RUNTIME_MESSAGES_INVALID",
                "rendered request message shape is invalid",
            )
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or not role:
            raise StandaloneRuntimeError(
                "V2_RUNTIME_MESSAGES_INVALID",
                "rendered request role is invalid",
            )
        if not isinstance(content, str):
            raise StandaloneRuntimeError(
                "V2_RUNTIME_MESSAGES_INVALID",
                "rendered request content is invalid",
            )


def check_token_budget(
    request_id: str,
    messages: MessageList,
    token_counter: TokenCounter,
) -> TokenBudgetObservation:
    """Require exact accepted-tokenizer admission before a request can be sent."""

    if not isinstance(request_id, str) or not request_id:
        raise StandaloneRuntimeError(
            "V2_RUNTIME_REQUEST_ID_INVALID",
            "request identity must be a non-empty string",
        )
    _validate_messages(messages)
    prompt_token_count = token_counter(messages)
    if (
        not isinstance(prompt_token_count, int)
        or isinstance(prompt_token_count, bool)
        or prompt_token_count < 0
    ):
        raise StandaloneRuntimeError(
            "V2_RUNTIME_TOKEN_COUNT_INVALID",
            "accepted tokenizer returned an invalid prompt-token count",
        )
    if prompt_token_count + MAX_OUTPUT_TOKENS > MAX_MODEL_LEN:
        raise StandaloneRuntimeError(
            "V2_RUNTIME_TOKEN_BUDGET_EXCEEDED",
            "prompt plus frozen output budget exceeds max_model_len",
        )
    return TokenBudgetObservation(
        request_id=request_id,
        prompt_token_count=prompt_token_count,
    )


def execute_turn(
    *,
    request: RuntimeTurnRequest,
    history: JsonHistory,
    admission_spec: object,
    render_messages: MessageRenderer,
    token_counter: TokenCounter,
    send_response: ResponseSender,
) -> TokenBudgetObservation:
    """Execute exactly one attempt after token admission and commit history atomically."""

    if not request.user_content:
        raise StandaloneRuntimeError(
            "V2_RUNTIME_USER_CONTENT_INVALID",
            "runtime turn user content must be non-empty",
        )
    messages = render_messages(request, history)
    observation = check_token_budget(request.request_id, messages, token_counter)
    response = send_response(request, messages)
    admit_and_commit_turn(
        history,
        request.user_content,
        response,
        admission_spec,
    )
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
    """Execute four turns with zero retry and stop permanently on the first failed turn."""

    completed = 0
    attempts = 0
    for request in requests:
        try:
            messages = render_messages(request, history)
            check_token_budget(request.request_id, messages, token_counter)
            attempts += 1
            response = send_response(request, messages)
            admit_and_commit_turn(
                history,
                request.user_content,
                response,
                admission_spec,
            )
        except StandaloneRuntimeError as exc:
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

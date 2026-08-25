"""Accepted-runtime request adapter for variance-pilot successor V2.

This module closes the live composition seam between the already-tested V2 deterministic
execution core and the accepted vLLM runtime. It performs no model work on import.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol, TypeAlias, cast

MessageList: TypeAlias = list[dict[str, str]]
JsonObject: TypeAlias = dict[str, object]
PostJson: TypeAlias = Callable[[str, JsonObject], JsonObject]
ProcessFactory: TypeAlias = Callable[..., subprocess.Popen[str]]

EXPECTED_TRANSFORMERS_VERSION: Final = "5.14.1"
EXPECTED_TOKENIZER_CLASS: Final = "Qwen2Tokenizer"
EXPECTED_CHAT_TEMPLATE_SHA256: Final = (
    "cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f"
)
MAX_MODEL_LEN: Final = 4096
MAX_OUTPUT_TOKENS: Final = 256
MAXIMUM_TOTAL_MODEL_REQUESTS: Final = 240
_SHA256_PATTERN: Final = re.compile(r"^[0-9a-f]{64}$")

_TOKENIZER_SIDECAR = r"""
from __future__ import annotations

import hashlib
import json
import sys

from transformers import AutoTokenizer, __version__ as transformers_version


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def normalize_ids(value: object) -> list[int]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and len(value) == 1 and isinstance(value[0], list):
        value = value[0]
    if not isinstance(value, list) or any(not isinstance(item, int) for item in value):
        raise TypeError("token IDs have an unsupported shape")
    return value


snapshot = sys.argv[1]
tokenizer = AutoTokenizer.from_pretrained(snapshot, local_files_only=True)
chat_template = tokenizer.chat_template
if not isinstance(chat_template, str):
    raise RuntimeError("tokenizer chat template is unavailable")
print(
    canonical_json(
        {
            "status": "READY",
            "transformers": transformers_version,
            "tokenizer_class": tokenizer.__class__.__name__,
            "chat_template_sha256": hashlib.sha256(chat_template.encode("utf-8")).hexdigest(),
        }
    ),
    flush=True,
)
for raw in sys.stdin:
    request = json.loads(raw)
    messages = request.get("messages")
    if not isinstance(messages, list):
        raise TypeError("tokenizer sidecar messages must be a list")
    rendered = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    direct = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
    )
    if not hasattr(direct, "keys") or "input_ids" not in direct:
        raise TypeError("direct chat-template result has no input_ids")
    direct_ids = normalize_ids(direct["input_ids"])
    rendered_ids = normalize_ids(
        tokenizer(rendered, add_special_tokens=False)["input_ids"]
    )
    if direct_ids != rendered_ids:
        raise RuntimeError("direct and rendered tokenizer paths disagree")
    messages_json = canonical_json(messages)
    print(
        canonical_json(
            {
                "status": "COUNTED",
                "prompt_token_count": len(direct_ids),
                "messages_sha256": hashlib.sha256(messages_json.encode("utf-8")).hexdigest(),
                "rendered_prompt_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                "token_id_parity": True,
            }
        ),
        flush=True,
    )
"""


class AcceptedRuntimeRequestAdapterError(RuntimeError):
    """Metadata-safe accepted-runtime request-adapter failure."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


@dataclass(frozen=True)
class TokenizerObservation:
    """Exact accepted-tokenizer observation for one rendered message list."""

    messages_sha256: str
    rendered_prompt_sha256: str
    prompt_token_count: int
    token_id_parity: bool = True


class TokenizerCounter(Protocol):
    """Minimal exact-tokenizer surface consumed by the one-shot request adapter."""

    def count(self, messages: MessageList) -> int: ...

    def observation_for(self, messages: MessageList) -> TokenizerObservation: ...


@dataclass
class RequestBudget:
    """Single-use request-attempt budget; reservation happens before transport."""

    maximum_total_model_requests: int = MAXIMUM_TOTAL_MODEL_REQUESTS
    attempted_model_requests: int = 0

    def reserve_attempt(self) -> int:
        if self.maximum_total_model_requests != MAXIMUM_TOTAL_MODEL_REQUESTS:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_BUDGET_DRIFT",
                "accepted-runtime request budget must remain exactly 240",
            )
        if self.attempted_model_requests >= self.maximum_total_model_requests:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_BUDGET_EXCEEDED",
                "accepted-runtime request budget would be exceeded",
            )
        self.attempted_model_requests += 1
        return self.attempted_model_requests


@dataclass(frozen=True)
class RequestReceipt:
    """Metadata-safe receipt proving pre-send and server token-count parity."""

    request_id: str
    attempt_sequence: int
    messages_sha256: str
    rendered_prompt_sha256: str
    prompt_token_count: int
    server_usage_prompt_tokens: int
    finish_reason: str | None
    output_sha256: str
    raw_prompt_retained: bool = False
    raw_output_retained: bool = False


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def message_identity(messages: MessageList) -> str:
    _validate_messages(messages)
    return sha256_text(canonical_json(messages))


def _validate_messages(messages: MessageList) -> None:
    if not isinstance(messages, list) or not messages:
        raise AcceptedRuntimeRequestAdapterError(
            "V2_REQUEST_MESSAGES_INVALID",
            "request messages must be a non-empty list",
        )
    for message in messages:
        if not isinstance(message, dict) or set(message) != {"role", "content"}:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_MESSAGES_INVALID",
                "request message shape is invalid",
            )
        if not isinstance(message.get("role"), str) or not message["role"]:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_MESSAGES_INVALID",
                "request message role is invalid",
            )
        if not isinstance(message.get("content"), str):
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_MESSAGES_INVALID",
                "request message content is invalid",
            )


def _json_object(raw: str, error_code: str) -> JsonObject:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise AcceptedRuntimeRequestAdapterError(
            error_code,
            "accepted-runtime adapter JSON record is invalid",
        ) from exc
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise AcceptedRuntimeRequestAdapterError(
            error_code,
            "accepted-runtime adapter JSON root must be one object",
        )
    return cast(JsonObject, value)


def _require_sha256(value: object, error_code: str, message: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise AcceptedRuntimeRequestAdapterError(error_code, message)
    return value


def _validate_loopback_chat_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    if (
        parsed.scheme != "http"
        or parsed.hostname != "127.0.0.1"
        or parsed.port not in {8001, 8002}
        or parsed.path != "/v1/chat/completions"
        or parsed.query
        or parsed.fragment
    ):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_REQUEST_DESTINATION_INVALID",
            "accepted-runtime requests are restricted to the frozen loopback worker endpoints",
        )


class AcceptedTokenizerSidecar:
    """Persistent exact-tokenizer process using the installed accepted target Python."""

    def __init__(
        self,
        target_python: Path,
        snapshot: Path,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
    ) -> None:
        if not target_python.is_file():
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_TARGET_PYTHON_MISSING",
                "accepted target Python executable is missing",
            )
        if not snapshot.is_dir():
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SNAPSHOT_MISSING",
                "accepted tokenizer snapshot is missing",
            )
        env = dict(os.environ)
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
        env["PYTHONNOUSERSITE"] = "1"
        self._process = process_factory(
            [str(target_python), "-u", "-c", _TOKENIZER_SIDECAR, str(snapshot)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env=env,
        )
        stdout = self._process.stdout
        if stdout is None:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SIDECAR_START_FAILED",
                "accepted tokenizer sidecar stdout is unavailable",
            )
        ready_line = stdout.readline()
        if not ready_line:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SIDECAR_START_FAILED",
                "accepted tokenizer sidecar did not emit readiness evidence",
            )
        ready = _json_object(ready_line, "V2_TOKENIZER_SIDECAR_READY_INVALID")
        expected = {
            "status": "READY",
            "transformers": EXPECTED_TRANSFORMERS_VERSION,
            "tokenizer_class": EXPECTED_TOKENIZER_CLASS,
            "chat_template_sha256": EXPECTED_CHAT_TEMPLATE_SHA256,
        }
        if ready != expected:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_ACCEPTED_TOKENIZER_IDENTITY_DRIFT",
                "accepted tokenizer sidecar identity drifted",
            )
        self._observations: dict[str, TokenizerObservation] = {}

    def count(self, messages: MessageList) -> int:
        _validate_messages(messages)
        if self._process.poll() is not None:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SIDECAR_EXITED",
                "accepted tokenizer sidecar exited before counting completed",
            )
        stdin = self._process.stdin
        stdout = self._process.stdout
        if stdin is None or stdout is None:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SIDECAR_IO_INVALID",
                "accepted tokenizer sidecar pipes are unavailable",
            )
        stdin.write(canonical_json({"messages": messages}) + "\n")
        stdin.flush()
        raw = stdout.readline()
        if not raw:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SIDECAR_COUNT_FAILED",
                "accepted tokenizer sidecar returned no count record",
            )
        observed = _json_object(raw, "V2_TOKENIZER_SIDECAR_COUNT_INVALID")
        count = observed.get("prompt_token_count")
        messages_sha = _require_sha256(
            observed.get("messages_sha256"),
            "V2_TOKENIZER_SIDECAR_COUNT_INVALID",
            "accepted tokenizer message identity is invalid",
        )
        rendered_sha = _require_sha256(
            observed.get("rendered_prompt_sha256"),
            "V2_TOKENIZER_SIDECAR_COUNT_INVALID",
            "accepted tokenizer rendered-prompt identity is invalid",
        )
        if (
            observed.get("status") != "COUNTED"
            or observed.get("token_id_parity") is not True
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_SIDECAR_COUNT_INVALID",
                "accepted tokenizer sidecar returned an invalid count record",
            )
        expected_messages_sha = message_identity(messages)
        if messages_sha != expected_messages_sha:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_MESSAGE_IDENTITY_DRIFT",
                "accepted tokenizer counted a different message identity",
            )
        observation = TokenizerObservation(
            messages_sha256=messages_sha,
            rendered_prompt_sha256=rendered_sha,
            prompt_token_count=count,
        )
        self._observations[messages_sha] = observation
        return count

    def observation_for(self, messages: MessageList) -> TokenizerObservation:
        identity = message_identity(messages)
        observation = self._observations.get(identity)
        if observation is None:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_TOKENIZER_PRE_SEND_OBSERVATION_MISSING",
                "request messages were not counted by the accepted tokenizer before send",
            )
        return observation

    def close(self) -> int:
        stdin = self._process.stdin
        if stdin is not None:
            stdin.close()
        try:
            return self._process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                return self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                return self._process.wait(timeout=5)


def build_request_payload(
    *,
    messages: MessageList,
    cache_salt: str,
    generation_contract: JsonObject,
    response_format: JsonObject,
) -> JsonObject:
    """Build exactly one V2 vLLM request from frozen generation material."""

    _validate_messages(messages)
    _require_sha256(
        cache_salt,
        "V2_CACHE_SALT_INVALID",
        "V2 cache salt must be a lowercase SHA-256 value",
    )
    required_generation = {
        "max_tokens": MAX_OUTPUT_TOKENS,
        "n": 1,
        "seed": 7,
        "stream": False,
        "temperature": 0,
        "top_p": 1,
        "hidden_retries_permitted": False,
    }
    for key, expected in required_generation.items():
        if generation_contract.get(key) != expected:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_GENERATION_CONTRACT_DRIFT",
                "V2 generation contract drifted",
            )
    response_format_sha = _require_sha256(
        generation_contract.get("response_format_sha256"),
        "V2_GENERATION_CONTRACT_DRIFT",
        "V2 response-format identity is invalid",
    )
    if response_format_sha != sha256_text(canonical_json(response_format)):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_FORMAT_IDENTITY_DRIFT",
            "V2 strict response-format identity drifted",
        )
    served_model = generation_contract.get("served_model_name")
    if not isinstance(served_model, str) or not served_model:
        raise AcceptedRuntimeRequestAdapterError(
            "V2_GENERATION_CONTRACT_DRIFT",
            "V2 served-model identity is invalid",
        )
    return {
        "model": served_model,
        "messages": [dict(message) for message in messages],
        "temperature": 0,
        "top_p": 1,
        "seed": 7,
        "max_tokens": MAX_OUTPUT_TOKENS,
        "n": 1,
        "stream": False,
        "cache_salt": cache_salt,
        "response_format": response_format,
    }


def _response_prompt_tokens(response: JsonObject) -> int:
    usage = response.get("usage")
    if not isinstance(usage, dict):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_USAGE_MISSING",
            "vLLM response usage is missing",
        )
    prompt_tokens = usage.get("prompt_tokens")
    if not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool) or prompt_tokens < 0:
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_USAGE_INVALID",
            "vLLM response prompt-token usage is invalid",
        )
    return prompt_tokens


def _response_metadata(response: JsonObject) -> tuple[str | None, str]:
    choices = response.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_ENVELOPE_INVALID",
            "vLLM response must contain exactly one choice",
        )
    choice = choices[0]
    if not isinstance(choice, dict):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_ENVELOPE_INVALID",
            "vLLM response choice is invalid",
        )
    message = choice.get("message")
    if not isinstance(message, dict):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_ENVELOPE_INVALID",
            "vLLM response message is invalid",
        )
    content = message.get("content")
    if not isinstance(content, str):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_ENVELOPE_INVALID",
            "vLLM response content is invalid",
        )
    finish_reason = choice.get("finish_reason")
    if finish_reason is not None and not isinstance(finish_reason, str):
        raise AcceptedRuntimeRequestAdapterError(
            "V2_RESPONSE_ENVELOPE_INVALID",
            "vLLM finish reason is invalid",
        )
    return finish_reason, sha256_text(content)


class OneShotVllmRequestAdapter:
    """Bridge counted V2 messages to one loopback vLLM request with no retry path."""

    def __init__(
        self,
        *,
        tokenizer: TokenizerCounter,
        post_json: PostJson,
        generation_contract: JsonObject,
        response_format: JsonObject,
        budget: RequestBudget,
    ) -> None:
        self.tokenizer = tokenizer
        self.post_json = post_json
        self.generation_contract = generation_contract
        self.response_format = response_format
        self.budget = budget

    def send(
        self,
        *,
        request_id: str,
        url: str,
        messages: MessageList,
        cache_salt: str,
    ) -> tuple[JsonObject, RequestReceipt]:
        if not isinstance(request_id, str) or not request_id:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_ID_INVALID",
                "V2 request identity must be non-empty",
            )
        _validate_loopback_chat_url(url)
        observation = self.tokenizer.observation_for(messages)
        if observation.prompt_token_count + MAX_OUTPUT_TOKENS > MAX_MODEL_LEN:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_REQUEST_TOKEN_BUDGET_EXCEEDED",
                "V2 request exceeds the frozen model-length budget",
            )
        payload = build_request_payload(
            messages=messages,
            cache_salt=cache_salt,
            generation_contract=self.generation_contract,
            response_format=self.response_format,
        )

        # Reservation happens immediately before the one transport call. A transport failure keeps
        # the attempt consumed, so this adapter has no retry ambiguity.
        attempt_sequence = self.budget.reserve_attempt()
        response = self.post_json(url, payload)
        server_prompt_tokens = _response_prompt_tokens(response)
        if server_prompt_tokens != observation.prompt_token_count:
            raise AcceptedRuntimeRequestAdapterError(
                "V2_SERVER_TOKEN_COUNT_MISMATCH",
                "vLLM prompt-token usage differs from the accepted-tokenizer pre-send count",
            )
        finish_reason, output_sha = _response_metadata(response)
        receipt = RequestReceipt(
            request_id=request_id,
            attempt_sequence=attempt_sequence,
            messages_sha256=observation.messages_sha256,
            rendered_prompt_sha256=observation.rendered_prompt_sha256,
            prompt_token_count=observation.prompt_token_count,
            server_usage_prompt_tokens=server_prompt_tokens,
            finish_reason=finish_reason,
            output_sha256=output_sha,
        )
        return response, receipt


def tokenizer_sidecar_source_sha256() -> str:
    """Expose deterministic sidecar source identity for authorization/evidence binding."""

    return sha256_text(_TOKENIZER_SIDECAR)


def tokenizer_sidecar_contains_required_guards() -> bool:
    """Mechanical regression hook for the exact offline tokenizer semantics."""

    required = (
        "local_files_only=True",
        "add_generation_prompt=True",
        'direct["input_ids"]',
        "direct_ids != rendered_ids",
        'tokenizer(rendered, add_special_tokens=False)["input_ids"]',
    )
    return all(item in _TOKENIZER_SIDECAR for item in required)

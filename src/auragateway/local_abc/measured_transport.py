"""Transport boundary for rendering instruct-model measured prompts."""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from typing import Literal, Protocol, Self

from pydantic import Field, field_validator, model_validator

from auragateway.local_abc.contracts import LocalABCContract

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,95}$")


class ChatTemplateRenderer(Protocol):
    """Minimum Hugging Face tokenizer surface required by the transport."""

    def apply_chat_template(
        self,
        conversation: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        """Render one chat conversation into a model-ready prompt."""


class MeasuredPromptTransportPolicy(LocalABCContract):
    """Frozen canary transport for Qwen instruct-model generation."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    transport_id: Literal["qwen-chat-template-single-user-v1"] = "qwen-chat-template-single-user-v1"
    message_role: Literal["user"] = "user"
    tokenize: Literal[False] = False
    add_generation_prompt: Literal[True] = True
    temperature: Decimal = Decimal("0")
    top_p: Decimal = Decimal("1")
    seed: Literal[7] = 7
    max_output_tokens: Literal[128] = 128
    stream: Literal[False] = False
    raw_prompt_logging_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_deterministic_transport(self) -> Self:
        if self.temperature != Decimal("0"):
            raise ValueError("measured canary transport requires temperature=0")
        if self.top_p != Decimal("1"):
            raise ValueError("measured canary transport requires top_p=1")
        return self


class RenderedPromptMetadata(LocalABCContract):
    """Metadata-only lineage for one transient rendered prompt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    transport_id: str
    compiled_prompt_sha256: str
    rendered_prompt_sha256: str
    compiled_character_count: int = Field(gt=0)
    rendered_character_count: int = Field(gt=0)
    raw_prompt_retained: Literal[False] = False

    @field_validator("transport_id")
    @classmethod
    def validate_transport_id(cls, value: str) -> str:
        if _ID_PATTERN.fullmatch(value) is None:
            raise ValueError("transport_id must use stable lowercase characters")
        return value

    @field_validator("compiled_prompt_sha256", "rendered_prompt_sha256")
    @classmethod
    def validate_digest(cls, value: str) -> str:
        if _SHA256_PATTERN.fullmatch(value) is None:
            raise ValueError("rendered prompt lineage requires lowercase SHA-256")
        return value


def render_measured_prompt(
    *,
    compiled_prompt: str,
    renderer: ChatTemplateRenderer,
    policy: MeasuredPromptTransportPolicy,
) -> tuple[str, RenderedPromptMetadata]:
    """Render transient model input while returning only metadata for evidence."""

    if not compiled_prompt.strip():
        raise ValueError("compiled prompt must not be blank")

    rendered = renderer.apply_chat_template(
        [{"role": policy.message_role, "content": compiled_prompt}],
        tokenize=policy.tokenize,
        add_generation_prompt=policy.add_generation_prompt,
    )
    if not isinstance(rendered, str) or not rendered.strip():
        raise ValueError("chat template renderer must return non-empty text")
    if rendered == compiled_prompt:
        raise ValueError("chat template transport must transform the raw prompt")
    if rendered.count(compiled_prompt) != 1:
        raise ValueError("rendered prompt must contain compiled prompt exactly once")

    metadata = RenderedPromptMetadata(
        transport_id=policy.transport_id,
        compiled_prompt_sha256=hashlib.sha256(compiled_prompt.encode("utf-8")).hexdigest(),
        rendered_prompt_sha256=hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        compiled_character_count=len(compiled_prompt),
        rendered_character_count=len(rendered),
    )
    return rendered, metadata

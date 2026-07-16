from __future__ import annotations

import pytest

from auragateway.local_abc.measured_transport import (
    MeasuredPromptTransportPolicy,
    render_measured_prompt,
)


class FakeQwenRenderer:
    def apply_chat_template(
        self,
        conversation: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        assert tokenize is False
        assert add_generation_prompt is True
        content = conversation[0]["content"]
        return f"<|im_start|>user\n{content}<|im_end|>\n<|im_start|>assistant\n"


class PassthroughRenderer:
    def apply_chat_template(
        self,
        conversation: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        del tokenize, add_generation_prompt
        return conversation[0]["content"]


class DuplicateRenderer:
    def apply_chat_template(
        self,
        conversation: list[dict[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        del tokenize, add_generation_prompt
        content = conversation[0]["content"]
        return f"{content}\n{content}"


def test_qwen_transport_renders_and_retains_metadata_only() -> None:
    rendered, metadata = render_measured_prompt(
        compiled_prompt="synthetic measured prompt",
        renderer=FakeQwenRenderer(),
        policy=MeasuredPromptTransportPolicy(),
    )

    assert rendered.startswith("<|im_start|>user")
    assert metadata.compiled_character_count == 25
    assert metadata.rendered_character_count > metadata.compiled_character_count
    assert metadata.raw_prompt_retained is False
    assert "synthetic measured prompt" not in metadata.canonical_json()


def test_transport_policy_is_deterministic_and_canary_bounded() -> None:
    policy = MeasuredPromptTransportPolicy()

    assert policy.temperature == 0
    assert policy.top_p == 1
    assert policy.seed == 7
    assert policy.max_output_tokens == 128
    assert policy.stream is False
    assert policy.raw_prompt_logging_permitted is False


def test_blank_prompt_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        render_measured_prompt(
            compiled_prompt=" ",
            renderer=FakeQwenRenderer(),
            policy=MeasuredPromptTransportPolicy(),
        )


def test_passthrough_transport_is_rejected() -> None:
    with pytest.raises(ValueError, match="must transform"):
        render_measured_prompt(
            compiled_prompt="synthetic measured prompt",
            renderer=PassthroughRenderer(),
            policy=MeasuredPromptTransportPolicy(),
        )


def test_duplicate_compiled_prompt_is_rejected() -> None:
    with pytest.raises(ValueError, match="exactly once"):
        render_measured_prompt(
            compiled_prompt="synthetic measured prompt",
            renderer=DuplicateRenderer(),
            policy=MeasuredPromptTransportPolicy(),
        )

"""Deterministic synthetic prompt construction for the OpenRouter Hy3 probe."""

from __future__ import annotations

import hashlib

from auragateway.contracts.openrouter_hy3_capability_probe_authorization import (
    OpenRouterProbePromptRecipe,
)


def build_stable_prefix(recipe: OpenRouterProbePromptRecipe) -> str:
    """Build the exact synthetic stable prefix described by a frozen recipe."""

    blocks = "\n".join(
        recipe.block_template.format(index=index) for index in range(recipe.block_count)
    )
    return f"{recipe.system_preamble}\n{blocks}"


def validate_stable_prefix(recipe: OpenRouterProbePromptRecipe) -> str:
    """Build and reconcile the prefix against its frozen byte and hash identities."""

    prefix = build_stable_prefix(recipe)
    encoded = prefix.encode("utf-8")
    observed_sha256 = hashlib.sha256(encoded).hexdigest()
    if observed_sha256 != recipe.generated_prefix_sha256:
        raise ValueError("generated stable prefix does not match its frozen SHA-256")
    if len(encoded) != recipe.generated_prefix_bytes:
        raise ValueError("generated stable prefix does not match its frozen byte count")
    return prefix


def derive_session_id(recipe: OpenRouterProbePromptRecipe) -> str:
    """Derive a stable, content-free session identity from the prefix digest."""

    return f"auragateway-hy3-probe-{recipe.generated_prefix_sha256[:32]}"


__all__ = ["build_stable_prefix", "derive_session_id", "validate_stable_prefix"]

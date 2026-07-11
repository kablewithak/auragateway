from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.chunking import (
    ChunkingConfiguration,
    ChunkingStrategy,
)


def test_fixed_window_configuration_requires_overlap_below_target() -> None:
    with pytest.raises(ValidationError, match="overlap_tokens"):
        ChunkingConfiguration(
            config_id="fixed-invalid",
            strategy=ChunkingStrategy.FIXED_WINDOW,
            target_tokens=32,
            overlap_tokens=32,
            minimum_fallback_tokens=8,
            preserve_parent_headings=False,
        )


def test_minimum_chunk_must_not_exceed_target() -> None:
    with pytest.raises(ValidationError, match="minimum_fallback_tokens"):
        ChunkingConfiguration(
            config_id="fixed-invalid",
            strategy=ChunkingStrategy.FIXED_WINDOW,
            target_tokens=32,
            overlap_tokens=4,
            minimum_fallback_tokens=40,
            preserve_parent_headings=False,
        )


def test_section_aware_configuration_requires_heading_preservation() -> None:
    with pytest.raises(ValidationError, match="preserve parent headings"):
        ChunkingConfiguration(
            config_id="section-invalid",
            strategy=ChunkingStrategy.SECTION_AWARE,
            target_tokens=32,
            overlap_tokens=4,
            minimum_fallback_tokens=8,
            preserve_parent_headings=False,
        )


def test_fixed_window_configuration_rejects_heading_preservation() -> None:
    with pytest.raises(ValidationError, match="does not preserve parent headings"):
        ChunkingConfiguration(
            config_id="fixed-invalid",
            strategy=ChunkingStrategy.FIXED_WINDOW,
            target_tokens=32,
            overlap_tokens=4,
            minimum_fallback_tokens=8,
            preserve_parent_headings=True,
        )

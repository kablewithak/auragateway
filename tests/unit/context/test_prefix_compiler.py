from __future__ import annotations

import json
from pathlib import Path

from auragateway.context.compiler import (
    canonical_json_bytes,
    fingerprint_static_context,
    normalize_text,
)
from auragateway.contracts.context import StaticAnchorRegistry
from auragateway.contracts.prefix import StaticCompilerSpec

KEY = b"auragateway-synthetic-prefix-fixture-key-v1-20260712"
KEY_ID = "synthetic-prefix-fixture-key-v1"


def _load_inputs() -> tuple[StaticCompilerSpec, StaticAnchorRegistry]:
    spec = StaticCompilerSpec.model_validate(
        json.loads(Path("data/context/compiler_spec.json").read_text(encoding="utf-8"))
    )
    registry = StaticAnchorRegistry.model_validate(
        json.loads(Path("data/context/static_anchor_registry.json").read_text(encoding="utf-8"))
    )
    return spec, registry


def test_normalize_text_collapses_newline_and_trailing_space_variation() -> None:
    first = "alpha  \r\nbeta\r\n"
    second = "alpha\nbeta\n"
    assert normalize_text(first) == normalize_text(second)


def test_canonical_json_key_order_is_semantically_stable() -> None:
    first = {"beta": 2, "alpha": {"delta": 4, "gamma": 3}}
    second = {"alpha": {"gamma": 3, "delta": 4}, "beta": 2}
    assert canonical_json_bytes(first) == canonical_json_bytes(second)


def test_static_fingerprint_is_stable_for_same_input() -> None:
    spec, registry = _load_inputs()
    first = fingerprint_static_context(Path("."), spec, registry, KEY, KEY_ID)
    second = fingerprint_static_context(Path("."), spec, registry, KEY, KEY_ID)
    assert first == second
    assert first.raw_content_retained is False


def test_static_fingerprint_changes_with_hmac_key() -> None:
    spec, registry = _load_inputs()
    first = fingerprint_static_context(Path("."), spec, registry, KEY, KEY_ID)
    second = fingerprint_static_context(
        Path("."), spec, registry, b"z" * 48, "alternate-fixture-key-v1"
    )
    assert first.canonical_sha256 == second.canonical_sha256
    assert first.prefix_fingerprint != second.prefix_fingerprint

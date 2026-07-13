from __future__ import annotations

import hashlib

from auragateway.providers.base import ProtectedProviderOutput, ProviderCall


def test_protected_output_hides_raw_content_from_repr() -> None:
    raw = '{"decision":"clarify"}'
    output = ProtectedProviderOutput(raw)

    assert raw not in repr(output)
    assert output.sha256 == hashlib.sha256(raw.encode("utf-8")).hexdigest()
    assert output.byte_count == len(raw.encode("utf-8"))


def test_provider_call_default_remains_backward_compatible() -> None:
    assert "protected_output" in ProviderCall.__dataclass_fields__
    assert ProviderCall.__dataclass_fields__["protected_output"].default is None

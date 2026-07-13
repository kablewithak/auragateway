from __future__ import annotations

from auragateway.benchmark.execution import _prefix_fingerprint


def test_same_static_prompt_and_key_preserve_fingerprint() -> None:
    key = b"fixture-live-development-hmac-key-material-0001"
    prompt = "stable-system-prompt\n"

    assert _prefix_fingerprint(prompt, key) == _prefix_fingerprint(prompt, key)


def test_volatile_mutation_changes_cache_hostile_system_fingerprint() -> None:
    key = b"fixture-live-development-hmac-key-material-0001"

    assert _prefix_fingerprint("static\nturn-one", key) != _prefix_fingerprint(
        "static\nturn-two",
        key,
    )

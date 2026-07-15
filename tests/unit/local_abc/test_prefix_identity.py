from __future__ import annotations

import hashlib

import pytest

from auragateway.local_abc.contracts import TokenizerIdentity
from auragateway.local_abc.prefix_identity import (
    PrefixIdentityBuildError,
    PrefixIdentityErrorCode,
    build_prefix_identity,
    canonical_token_id_bytes,
    hash_token_ids,
    tokenizer_fingerprint,
)


class Utf8TokenEncoder:
    def encode(self, text: str) -> tuple[int, ...]:
        return tuple(text.encode("utf-8"))


class EmptyTokenEncoder:
    def encode(self, text: str) -> tuple[int, ...]:
        del text
        return ()


def tokenizer() -> TokenizerIdentity:
    return TokenizerIdentity(
        repository="synthetic/tokenizer",
        revision="abcdef1234567",
        config_sha256="1" * 64,
    )


def test_canonical_token_id_bytes_are_compact_and_order_preserving() -> None:
    assert canonical_token_id_bytes((10, 2, 300)) == b"[10,2,300]"


def test_token_hash_matches_sha256_of_canonical_token_sequence() -> None:
    expected = hashlib.sha256(b"[10,2,300]").hexdigest()
    assert hash_token_ids((10, 2, 300)) == expected


@pytest.mark.parametrize("token_ids", [(), (True,), (-1,), (1, "2")])
def test_invalid_token_sequences_fail_closed(token_ids: tuple[object, ...]) -> None:
    with pytest.raises(PrefixIdentityBuildError):
        canonical_token_id_bytes(token_ids)  # type: ignore[arg-type]


def test_invalid_token_id_exposes_machine_readable_code() -> None:
    with pytest.raises(PrefixIdentityBuildError) as exc_info:
        canonical_token_id_bytes((1, -1))

    assert exc_info.value.code is PrefixIdentityErrorCode.INVALID_TOKEN_ID


def test_tokenizer_fingerprint_binds_full_tokenizer_contract() -> None:
    first = tokenizer()
    second = first.model_copy(update={"revision": "abcdef7654321"})

    assert tokenizer_fingerprint(first) == first.fingerprint()
    assert tokenizer_fingerprint(first) != tokenizer_fingerprint(second)


def test_build_prefix_identity_is_deterministic() -> None:
    first = build_prefix_identity(
        prefix_text="stable-prefix",
        tokenizer=tokenizer(),
        encoder=Utf8TokenEncoder(),
    )
    second = build_prefix_identity(
        prefix_text="stable-prefix",
        tokenizer=tokenizer(),
        encoder=Utf8TokenEncoder(),
    )

    assert first == second
    assert first.token_count == len(b"stable-prefix")


def test_exact_prefix_change_changes_token_hash() -> None:
    first = build_prefix_identity(
        prefix_text="stable-prefix-a",
        tokenizer=tokenizer(),
        encoder=Utf8TokenEncoder(),
    )
    second = build_prefix_identity(
        prefix_text="stable-prefix-b",
        tokenizer=tokenizer(),
        encoder=Utf8TokenEncoder(),
    )

    assert first.token_hash != second.token_hash


def test_empty_prefix_is_rejected_before_encoding() -> None:
    with pytest.raises(PrefixIdentityBuildError) as exc_info:
        build_prefix_identity(
            prefix_text="",
            tokenizer=tokenizer(),
            encoder=Utf8TokenEncoder(),
        )

    assert exc_info.value.code is PrefixIdentityErrorCode.EMPTY_PREFIX


def test_empty_encoder_output_is_rejected() -> None:
    with pytest.raises(PrefixIdentityBuildError) as exc_info:
        build_prefix_identity(
            prefix_text="not-empty",
            tokenizer=tokenizer(),
            encoder=EmptyTokenEncoder(),
        )

    assert exc_info.value.code is PrefixIdentityErrorCode.EMPTY_TOKEN_SEQUENCE

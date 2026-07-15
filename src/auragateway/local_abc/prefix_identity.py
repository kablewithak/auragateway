"""Deterministic token-level prefix identity construction."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from auragateway.local_abc.contracts import PrefixIdentity, TokenizerIdentity

DEFAULT_PREFIX_SERIALIZER_VERSION = "local-abc-prefix-v1"


class TokenEncoder(Protocol):
    """Minimal tokenizer seam required by the local A/B/C compiler."""

    def encode(self, text: str) -> Sequence[int]:
        """Encode exact text into deterministic token IDs."""
        ...


class PrefixIdentityErrorCode(StrEnum):
    """Machine-readable prefix identity construction failures."""

    EMPTY_PREFIX = "EMPTY_PREFIX"
    EMPTY_TOKEN_SEQUENCE = "EMPTY_TOKEN_SEQUENCE"
    INVALID_TOKEN_ID = "INVALID_TOKEN_ID"


class PrefixIdentityBuildError(ValueError):
    """Bounded construction error that retains a stable machine-readable code."""

    def __init__(self, code: PrefixIdentityErrorCode, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def canonical_token_id_bytes(token_ids: Sequence[int]) -> bytes:
    """Serialize non-negative token IDs into canonical UTF-8 JSON bytes."""

    normalized: list[int] = []
    for index, token_id in enumerate(token_ids):
        if isinstance(token_id, bool) or not isinstance(token_id, int) or token_id < 0:
            raise PrefixIdentityBuildError(
                PrefixIdentityErrorCode.INVALID_TOKEN_ID,
                f"token_ids[{index}] must be a non-negative integer",
            )
        normalized.append(token_id)

    if not normalized:
        raise PrefixIdentityBuildError(
            PrefixIdentityErrorCode.EMPTY_TOKEN_SEQUENCE,
            "the tokenizer returned no token IDs",
        )

    payload = json.dumps(
        normalized,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return payload.encode("utf-8")


def hash_token_ids(token_ids: Sequence[int]) -> str:
    """Return the lowercase SHA-256 digest of canonical token-ID bytes."""

    return hashlib.sha256(canonical_token_id_bytes(token_ids)).hexdigest()


def tokenizer_fingerprint(tokenizer: TokenizerIdentity) -> str:
    """Bind prefix identity to the complete qualified tokenizer contract."""

    return tokenizer.fingerprint()


def build_prefix_identity(
    *,
    prefix_text: str,
    tokenizer: TokenizerIdentity,
    encoder: TokenEncoder,
    serializer_version: str = DEFAULT_PREFIX_SERIALIZER_VERSION,
) -> PrefixIdentity:
    """Build a metadata-only identity for the exact tokenized prefix text."""

    if not prefix_text:
        raise PrefixIdentityBuildError(
            PrefixIdentityErrorCode.EMPTY_PREFIX,
            "prefix_text must not be empty",
        )

    token_ids = tuple(encoder.encode(prefix_text))
    return PrefixIdentity(
        serializer_version=serializer_version,
        token_hash=hash_token_ids(token_ids),
        token_count=len(token_ids),
        tokenizer_fingerprint=tokenizer_fingerprint(tokenizer),
    )

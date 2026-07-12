"""Canonical static-context serialization and HMAC-SHA256 prefix fingerprinting."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from pydantic import BaseModel

from auragateway.contracts.context import StaticAnchorRegistry
from auragateway.contracts.prefix import (
    CanonicalAnchorContent,
    CanonicalStaticPayload,
    PrefixFingerprintRecord,
    PrefixMutationReason,
    StaticCompilerSpec,
)

_FORBIDDEN_STATIC_KEYS = {
    "timestamp",
    "request_id",
    "session_id",
    "user_id",
    "direct_user_identifier",
    "retrieval_chunks",
    "retrieval_evidence",
    "conversation_history",
    "current_user_message",
    "runtime_token_count",
    "provider_response",
    "provider_payload",
    "temporary_flag",
    "random_value",
    "secret",
    "api_key",
}
_FORBIDDEN_KEY_PATTERN = re.compile(
    r"(^|_)(timestamp|request|session|user_id|retrieval|conversation|runtime|provider_"
    r"response|provider_payload|temporary|random|secret|api_key)($|_)",
    re.IGNORECASE,
)


class PrefixCompileError(Exception):
    """Expected context-compiler failure with a safe mutation reason."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        mutation_reason: PrefixMutationReason,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.mutation_reason = mutation_reason
        self.details = details


def normalize_text(value: str) -> str:
    """Normalize newlines and trailing horizontal whitespace deterministically."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in normalized.split("\n")]
    return "\n".join(lines).rstrip("\n") + "\n"


def _normalize_json_value(value: object) -> object:
    if isinstance(value, str):
        return normalize_text(value).removesuffix("\n")
    if isinstance(value, Mapping):
        normalized: dict[str, object] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise TypeError("canonical JSON object keys must be strings")
            normalized[key] = _normalize_json_value(item)
        return normalized
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_normalize_json_value(item) for item in value]
    if value is None or isinstance(value, bool | int | float):
        return value
    raise TypeError(f"unsupported canonical JSON value: {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    """Serialize JSON-compatible content with stable key and whitespace rules."""

    normalized = _normalize_json_value(value)
    text = json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (text + "\n").encode("utf-8")


def canonical_model_bytes(model: BaseModel) -> bytes:
    """Serialize a Pydantic model into canonical UTF-8 JSON bytes."""

    return canonical_json_bytes(model.model_dump(mode="json"))


def sha256_bytes(value: bytes) -> str:
    """Return lowercase SHA-256 for bytes."""

    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    """Return lowercase SHA-256 for a file."""

    return sha256_bytes(path.read_bytes())


def ensure_no_forbidden_volatile_fields(value: object, path: str = "artifact") -> None:
    """Reject volatile or secret-bearing keys before typed static validation."""

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise PrefixCompileError(
                    "STATIC_CONTENT_INVALID_KEY",
                    "Static compiler content contains a non-string key.",
                    PrefixMutationReason.UNKNOWN,
                    (path,),
                )
            normalized_key = key.strip().lower()
            if normalized_key in _FORBIDDEN_STATIC_KEYS or _FORBIDDEN_KEY_PATTERN.search(
                normalized_key
            ):
                raise PrefixCompileError(
                    "FORBIDDEN_VOLATILE_FIELD_DETECTED",
                    "Volatile or secret-bearing data was detected in static content.",
                    PrefixMutationReason.FORBIDDEN_VOLATILE_FIELD_DETECTED,
                    (f"{path}.{key}",),
                )
            ensure_no_forbidden_volatile_fields(item, f"{path}.{key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, item in enumerate(value):
            ensure_no_forbidden_volatile_fields(item, f"{path}[{index}]")


def _canonical_artifact_content(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        parsed = json.loads(text)
        return canonical_json_bytes(parsed).decode("utf-8")
    return normalize_text(text)


def build_canonical_static_payload(
    repo_root: Path,
    spec: StaticCompilerSpec,
    registry: StaticAnchorRegistry,
) -> CanonicalStaticPayload:
    """Load hash-bound anchors and construct the typed canonical static payload."""

    registry_path = repo_root / spec.static_registry_path
    if sha256_path(registry_path) != spec.static_registry_sha256:
        raise PrefixCompileError(
            "STATIC_REGISTRY_HASH_MISMATCH",
            "Static compiler specification does not match the registered anchor bytes.",
            PrefixMutationReason.CONTEXT_PACK_CHANGED,
            (spec.static_registry_path,),
        )

    anchors: list[CanonicalAnchorContent] = []
    for anchor in registry.anchors:
        artifact_path = repo_root / anchor.artifact_path
        try:
            actual_hash = sha256_path(artifact_path)
        except FileNotFoundError as exc:
            raise PrefixCompileError(
                "STATIC_ANCHOR_ARTIFACT_NOT_FOUND",
                "A required static anchor artifact was not found.",
                PrefixMutationReason.CONTEXT_PACK_CHANGED,
                (anchor.anchor_id,),
            ) from exc
        if actual_hash != anchor.artifact_sha256:
            raise PrefixCompileError(
                "STATIC_ANCHOR_ARTIFACT_HASH_MISMATCH",
                "A static anchor artifact no longer matches its registered hash.",
                PrefixMutationReason.CONTEXT_PACK_CHANGED,
                (anchor.anchor_id,),
            )
        anchors.append(
            CanonicalAnchorContent(
                anchor_id=anchor.anchor_id,
                order=anchor.order,
                kind=anchor.kind,
                artifact_sha256=anchor.artifact_sha256,
                normalized_content=_canonical_artifact_content(artifact_path),
            )
        )

    return CanonicalStaticPayload(
        serialization_version=spec.serialization_version,
        template_id=spec.template_id,
        template_version=spec.template_version,
        tool_contract_version=spec.tool_contract_version,
        segments=spec.segments,
        tools=spec.tools,
        output_schema=spec.output_schema,
        context_pack=spec.context_pack,
        anchors=tuple(anchors),
    )


def serialize_static_payload(payload: CanonicalStaticPayload) -> bytes:
    """Return provider-neutral canonical bytes for the complete static payload."""

    return canonical_model_bytes(payload)


def fingerprint_static_context(
    repo_root: Path,
    spec: StaticCompilerSpec,
    registry: StaticAnchorRegistry,
    hmac_key: bytes,
    key_id: str,
) -> PrefixFingerprintRecord:
    """Compile canonical static bytes and return safe HMAC fingerprint evidence."""

    if len(hmac_key) < 32:
        raise PrefixCompileError(
            "PREFIX_HMAC_KEY_TOO_SHORT",
            "Prefix HMAC key must contain at least 32 bytes.",
            PrefixMutationReason.UNKNOWN,
        )
    payload = build_canonical_static_payload(repo_root, spec, registry)
    canonical_bytes = serialize_static_payload(payload)
    tool_bytes = canonical_json_bytes([tool.model_dump(mode="json") for tool in spec.tools])
    schema_bytes = canonical_model_bytes(spec.output_schema)
    context_pack_bytes = canonical_model_bytes(spec.context_pack)
    return PrefixFingerprintRecord(
        key_id=key_id,
        prefix_fingerprint=hmac.new(hmac_key, canonical_bytes, hashlib.sha256).hexdigest(),
        canonical_sha256=sha256_bytes(canonical_bytes),
        canonical_bytes=len(canonical_bytes),
        serialization_version=spec.serialization_version,
        template_id=spec.template_id,
        template_version=spec.template_version,
        tool_contract_fingerprint=sha256_bytes(tool_bytes),
        output_schema_fingerprint=sha256_bytes(schema_bytes),
        context_pack_fingerprint=sha256_bytes(context_pack_bytes),
        static_registry_sha256=spec.static_registry_sha256,
    )

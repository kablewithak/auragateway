from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.contracts.retrieval_metadata import (
    InterfaceKind,
    OAuthGrantKind,
    RetrievalMetadataFilter,
    SourceLanguage,
    SourceRetrievalMetadata,
    SourceRetrievalMetadataRegistry,
)

REGISTRY_PATH = Path("data/retrieval/remediation-v1/source_metadata.json")


def test_registry_covers_all_frozen_sources() -> None:
    registry = SourceRetrievalMetadataRegistry.model_validate_json(
        REGISTRY_PATH.read_text(encoding="utf-8")
    )

    assert len(registry.entries) == 30
    assert len(registry.by_source_id()) == 30
    assert registry.by_source_id()["NR-SDK-016"].language is SourceLanguage.PYTHON
    assert registry.by_source_id()["NR-OAUTH-004"].oauth_grant is OAuthGrantKind.REFRESH_TOKEN


def test_language_specific_source_requires_sdk_interface() -> None:
    with pytest.raises(ValidationError):
        SourceRetrievalMetadata(
            source_id="NR-TEST-001",
            language=SourceLanguage.PYTHON,
            interface_kind=InterfaceKind.RAW_HTTP,
            representation="human_guide",
        )


def test_oauth_grant_source_requires_raw_http_interface() -> None:
    with pytest.raises(ValidationError):
        SourceRetrievalMetadata(
            source_id="NR-TEST-001",
            interface_kind=InterfaceKind.SDK,
            oauth_grant=OAuthGrantKind.CLIENT_CREDENTIALS,
            representation="human_guide",
        )


def test_registry_rejects_duplicate_source_ids() -> None:
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    payload["entries"][1]["source_id"] = payload["entries"][0]["source_id"]

    with pytest.raises(ValidationError):
        SourceRetrievalMetadataRegistry.model_validate(payload)


def test_metadata_filter_rejects_duplicate_values() -> None:
    with pytest.raises(ValidationError):
        RetrievalMetadataFilter(languages=(SourceLanguage.PYTHON, SourceLanguage.PYTHON))

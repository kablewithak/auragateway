from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.corpus import CorpusInventory

INVENTORY_PATH = Path("data/corpus/source_inventory.json")


def load_payload() -> dict[str, object]:
    return cast(dict[str, object], json.loads(INVENTORY_PATH.read_text(encoding="utf-8")))


def test_planned_inventory_validates_and_meets_diagnostic_minimums() -> None:
    inventory = CorpusInventory.model_validate(load_payload())

    summary = inventory.validation_summary()

    assert summary.validation_status == "valid"
    assert summary.document_count == 30
    assert summary.distinct_intent_categories >= 10
    assert summary.stale_document_count >= 5
    assert summary.conflicting_document_count >= 5
    assert summary.incomplete_document_count >= 4
    assert summary.near_duplicate_document_count >= 4
    assert summary.version_sensitive_document_count >= 6


def test_duplicate_source_id_is_rejected() -> None:
    payload = copy.deepcopy(load_payload())
    sources = payload["sources"]
    assert isinstance(sources, list)
    first = sources[0]
    second = sources[1]
    assert isinstance(first, dict)
    assert isinstance(second, dict)
    second["source_id"] = first["source_id"]

    with pytest.raises(ValidationError, match="duplicate source_id"):
        CorpusInventory.model_validate(payload)


def test_singleton_conflict_group_is_rejected() -> None:
    payload = copy.deepcopy(load_payload())
    sources = payload["sources"]
    assert isinstance(sources, list)
    for source in sources:
        assert isinstance(source, dict)
        if source.get("source_id") == "NR-AUTH-002":
            source["conflict_group_id"] = None

    with pytest.raises(ValidationError, match="conflict_group_id groups"):
        CorpusInventory.model_validate(payload)


def test_personal_data_flag_is_rejected() -> None:
    payload = copy.deepcopy(load_payload())
    sources = payload["sources"]
    assert isinstance(sources, list)
    source = sources[0]
    assert isinstance(source, dict)
    source["contains_personal_data"] = True

    with pytest.raises(ValidationError, match="personal data is prohibited"):
        CorpusInventory.model_validate(payload)


def test_stale_source_requires_stale_lifecycle_status() -> None:
    payload = copy.deepcopy(load_payload())
    sources = payload["sources"]
    assert isinstance(sources, list)
    source = sources[0]
    assert isinstance(source, dict)
    source["is_stale"] = True
    source["status"] = "current"

    with pytest.raises(ValidationError, match="stale sources must be deprecated or superseded"):
        CorpusInventory.model_validate(payload)

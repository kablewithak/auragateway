from __future__ import annotations

import json
from pathlib import Path

from auragateway.chunking.runner import (
    FIXED_WINDOW_CONFIG,
    LoadedDocument,
    chunk_fixed_window,
    chunk_section_aware,
    lexical_token_count,
)
from auragateway.contracts.corpus import CorpusInventory, CorpusSource

INVENTORY_PATH = Path("data/corpus/source_inventory.json")


def _source(source_id: str) -> CorpusSource:
    inventory = CorpusInventory.model_validate_json(INVENTORY_PATH.read_text(encoding="utf-8"))
    return next(source for source in inventory.sources if source.source_id == source_id)


def test_lexical_token_count_is_provider_neutral_and_deterministic() -> None:
    assert lexical_token_count("alpha  beta\ngamma") == 3
    assert lexical_token_count("  ") == 0


def test_fixed_window_chunks_are_bounded_and_deterministic() -> None:
    source = _source("NR-AUTH-001")
    body = " ".join(f"token-{index}" for index in range(220))
    document = LoadedDocument(source=source, body=body)

    first = chunk_fixed_window(document)
    second = chunk_fixed_window(document)

    assert first == second
    assert len(first) == 3
    assert all(chunk.token_count <= FIXED_WINDOW_CONFIG.target_tokens for chunk in first)
    assert all(not chunk.parent_headings for chunk in first)
    assert len({chunk.chunk_id for chunk in first}) == len(first)


def test_section_aware_preserves_markdown_heading_path(tmp_path: Path) -> None:
    source = _source("NR-AUTH-001")
    repo_root = tmp_path
    path = repo_root / source.document_path
    path.parent.mkdir(parents=True)
    path.write_text(
        """---
source_id: NR-AUTH-001
---
# Authentication

Intro text.

## Rotation

Rotate the key safely.
""",
        encoding="utf-8",
    )
    document = LoadedDocument(
        source=source,
        body="# Authentication\n\nIntro text.\n\n## Rotation\n\nRotate the key safely.",
    )

    chunks = chunk_section_aware(repo_root, document)

    assert [chunk.parent_headings for chunk in chunks] == [
        ("Authentication",),
        ("Authentication", "Rotation"),
    ]
    assert chunks[1].content.startswith("## Rotation")


def test_section_aware_uses_top_level_json_keys_as_headings(tmp_path: Path) -> None:
    source = _source("NR-OAUTH-004")
    repo_root = tmp_path
    path = repo_root / source.document_path
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "metadata": {"source_id": source.source_id},
                "content": {
                    "rules": {"retry": False},
                    "errors": [f"error-{index}" for index in range(30)],
                },
            }
        ),
        encoding="utf-8",
    )
    document = LoadedDocument(source=source, body="unused")

    chunks = chunk_section_aware(repo_root, document)

    assert [chunk.parent_headings for chunk in chunks] == [("errors",), ("document_fields",)]
    assert all("metadata" not in chunk.content for chunk in chunks)

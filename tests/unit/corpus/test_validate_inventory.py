from __future__ import annotations

import json
from pathlib import Path

from auragateway.corpus.validate import main, validate_inventory_file

INVENTORY_PATH = Path("data/corpus/source_inventory.json")


def test_validate_inventory_file_returns_safe_summary() -> None:
    summary = validate_inventory_file(INVENTORY_PATH)

    assert summary.corpus_id == "nimbus-relay"
    assert summary.document_count == 30
    assert summary.validation_status == "valid"


def test_cli_prints_json_summary(capsys: object) -> None:
    exit_code = main([str(INVENTORY_PATH)])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["validation_status"] == "valid"
    assert payload["document_count"] == 30


def test_cli_missing_file_returns_typed_error(capsys: object) -> None:
    exit_code = main(["data/corpus/missing.json"])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.err)

    assert exit_code == 2
    assert payload["error_code"] == "CORPUS_INVENTORY_NOT_FOUND"

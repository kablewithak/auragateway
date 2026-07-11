"""Validate the planned Nimbus Relay corpus inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.corpus import CorpusInventory, CorpusValidationSummary


class CorpusValidationErrorEnvelope(BaseModel):
    """Safe machine-readable CLI failure output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str
    validation_errors: tuple[str, ...] = ()


def validate_inventory_file(path: Path) -> CorpusValidationSummary:
    """Load and validate a raw JSON inventory at the boundary."""

    payload: object = json.loads(path.read_text(encoding="utf-8"))
    inventory = CorpusInventory.model_validate(payload)
    return inventory.validation_summary()


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inventory_path", type=Path)
    return parser.parse_args(argv)


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "inventory"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv)
    path: Path = args.inventory_path

    try:
        summary = validate_inventory_file(path)
    except FileNotFoundError:
        error = CorpusValidationErrorEnvelope(
            error_code="CORPUS_INVENTORY_NOT_FOUND",
            safe_message="Corpus inventory file was not found.",
            path=str(path),
        )
        print(error.model_dump_json(indent=2), file=sys.stderr)
        return 2
    except json.JSONDecodeError:
        error = CorpusValidationErrorEnvelope(
            error_code="CORPUS_INVENTORY_INVALID_JSON",
            safe_message="Corpus inventory is not valid JSON.",
            path=str(path),
        )
        print(error.model_dump_json(indent=2), file=sys.stderr)
        return 3
    except ValidationError as exc:
        error = CorpusValidationErrorEnvelope(
            error_code="CORPUS_INVENTORY_VALIDATION_FAILED",
            safe_message="Corpus inventory failed typed validation.",
            path=str(path),
            validation_errors=_validation_messages(exc),
        )
        print(error.model_dump_json(indent=2), file=sys.stderr)
        return 4

    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

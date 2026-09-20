"""Non-live prerequisite verification for the J7L model-reference successor."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Never

from pydantic import ValidationError

from auragateway.contracts.quality_development_evaluation_v2 import (
    EXPECTED_AUTHORING_CASE_SET_SHA256,
    EXPECTED_CONSTITUTION_SHA256,
    EXPECTED_HUMAN_PROJECTION_SHA256,
    EXPECTED_MODEL_PROJECTION_SHA256,
    EXPECTED_PROTECTED_SCHEDULE_SHA256,
    EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256,
    J7LReferenceSuccessorPrerequisiteReceiptV1,
)
from auragateway.local_abc import quality_development_case_freeze_v1 as case_freeze
from auragateway.local_abc import quality_semantic_projection_v1 as semantic_projection

CONSTITUTION_PATH = Path(
    "docs/benchmark/AuraGateway_J7L_Model_Derived_Reference_Successor_Constitution_v1.md"
)


class J7LReferenceSuccessorError(RuntimeError):
    """Fail-closed successor prerequisite error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_ARGUMENT_ERROR",
            message,
        )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def verify_prerequisites(repo_root: Path) -> J7LReferenceSuccessorPrerequisiteReceiptV1:
    """Verify exact historical subject adoption without provider execution."""

    root = repo_root.resolve()
    constitution_path = root / CONSTITUTION_PATH

    if not constitution_path.is_file() or constitution_path.is_symlink():
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_CONSTITUTION_MISSING",
            "model-derived reference successor constitution is missing or unsafe",
        )

    constitution_sha256 = sha256_bytes(constitution_path.read_bytes())
    if constitution_sha256 != EXPECTED_CONSTITUTION_SHA256:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_CONSTITUTION_DRIFT",
            "model-derived reference successor constitution bytes drifted",
        )

    case_receipt = case_freeze.verify_artifacts(root)

    if case_receipt.authoring_case_set_sha256 != EXPECTED_AUTHORING_CASE_SET_SHA256:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_CASE_SET_DRIFT",
            "J7L authoring case-set identity drifted",
        )

    if (
        case_receipt.reviewer_safe_state_inventory_sha256
        != EXPECTED_REVIEWER_SAFE_STATE_INVENTORY_SHA256
    ):
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_SAFE_STATE_DRIFT",
            "J7L reviewer-safe-state inventory identity drifted",
        )

    if case_receipt.protected_schedule_sha256 != EXPECTED_PROTECTED_SCHEDULE_SHA256:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_SCHEDULE_DRIFT",
            "J7L protected schedule identity drifted",
        )

    parity = semantic_projection.verify_materialized_projections(root)

    if parity.human_projection_sha256 != EXPECTED_HUMAN_PROJECTION_SHA256:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_HUMAN_PROJECTION_DRIFT",
            "J7K human semantic projection identity drifted",
        )

    if parity.model_projection_sha256 != EXPECTED_MODEL_PROJECTION_SHA256:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_MODEL_PROJECTION_DRIFT",
            "J7K model semantic projection identity drifted",
        )

    if not parity.canonical_semantic_parity:
        raise J7LReferenceSuccessorError(
            "J7L_REFERENCE_SUCCESSOR_SEMANTIC_PARITY_MISSING",
            "J7K canonical semantic parity is not established",
        )

    return J7LReferenceSuccessorPrerequisiteReceiptV1()


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    verify = subparsers.add_parser("verify-prerequisites")
    verify.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    args = _build_parser().parse_args()

    try:
        result = verify_prerequisites(args.repo_root)
    except (J7LReferenceSuccessorError, ValidationError, OSError) as error:
        if isinstance(error, J7LReferenceSuccessorError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "J7L_REFERENCE_SUCCESSOR_TYPED_VALIDATION_FAILED"
            message = "J7L model-reference successor typed validation failed"
        else:
            code = "J7L_REFERENCE_SUCCESSOR_LOCAL_IO_FAILED"
            message = "J7L model-reference successor local I/O failed"

        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

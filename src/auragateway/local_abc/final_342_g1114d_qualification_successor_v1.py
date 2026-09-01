"""Materialize the G11.14D Final-342 successor qualification."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Never

from pydantic import ValidationError

from auragateway.local_abc import final_342_single_use_live_issuer_v1 as issuer

BASE_MAIN_COMMIT = "81a3c2f38d0e157d21d280bd27e4deaea6e17014"

PREDECESSOR_TEMPLATE_SHA256 = "37e5adbe6987ebf22d08f562a26bf51591bdbcd826803cbe5d73c039a992d9e7"
PREDECESSOR_TEST_SHA256 = "697b348506a9170d0dced8af8b3d213de2991b9663dee9aac790068bc59dfd15"
PREDECESSOR_SOURCE_SHA256 = "673c54814847795a712b85e82bd65f971c61bbabbd17ed05993924e45ffa771a"
PREDECESSOR_TRANSACTION_MATERIAL_SHA256 = (
    "ef3582a7f9cb9a05a5737de2d04d842bfdf462f2688482d1ddedd68aedb80af7"
)

ALLOWED_CHANGED_FIELDS = {
    "live_execution_template",
    "test",
    "qualification_rendered_wrapper_sha256",
    "qualification_notebook_launcher_source_bytes",
}


class SuccessorError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SuccessorError(
            "FINAL_342_G1114D_SUCCESSOR_ARGUMENT_INVALID",
            message,
        )


def _require_base_ancestor(root: Path) -> None:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "merge-base",
            "--is-ancestor",
            BASE_MAIN_COMMIT,
            "HEAD",
        ],
        check=False,
        capture_output=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise SuccessorError(
            "FINAL_342_G1114D_BASE_MISSING",
            "accepted G11.14C merge is not an ancestor of HEAD",
        )


def _load_predecessor(root: Path) -> issuer.QualificationRecord:
    revision_path = f"{BASE_MAIN_COMMIT}:{issuer.QUALIFICATION_RECORD_PATH.as_posix()}"

    completed = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "show",
            revision_path,
        ],
        check=False,
        capture_output=True,
        timeout=30,
    )

    if completed.returncode != 0:
        raise SuccessorError(
            "FINAL_342_G1114D_PREDECESSOR_MISSING",
            "accepted predecessor qualification could not be read",
        )

    try:
        return issuer.QualificationRecord.model_validate_json(completed.stdout)
    except ValidationError as error:
        raise SuccessorError(
            "FINAL_342_G1114D_PREDECESSOR_INVALID",
            "accepted predecessor qualification failed typed validation",
        ) from error


def _require_predecessor_identity(
    predecessor: issuer.QualificationRecord,
) -> None:
    if predecessor.live_execution_template.sha256 != PREDECESSOR_TEMPLATE_SHA256:
        raise SuccessorError(
            "FINAL_342_G1114D_PREDECESSOR_DRIFT",
            "predecessor template identity drifted",
        )

    if predecessor.test.sha256 != PREDECESSOR_TEST_SHA256:
        raise SuccessorError(
            "FINAL_342_G1114D_PREDECESSOR_DRIFT",
            "predecessor test identity drifted",
        )

    if predecessor.source.sha256 != PREDECESSOR_SOURCE_SHA256:
        raise SuccessorError(
            "FINAL_342_G1114D_PREDECESSOR_DRIFT",
            "issuer source identity drifted",
        )

    if predecessor.transaction_material_sha256 != PREDECESSOR_TRANSACTION_MATERIAL_SHA256:
        raise SuccessorError(
            "FINAL_342_G1114D_PREDECESSOR_DRIFT",
            "transaction material identity drifted",
        )


def _changed_fields(
    predecessor: issuer.QualificationRecord,
    successor: issuer.QualificationRecord,
) -> set[str]:
    before = predecessor.model_dump(mode="json")
    after = successor.model_dump(mode="json")

    return {key for key in before if before[key] != after[key]}


def _require_successor_boundary(
    predecessor: issuer.QualificationRecord,
    successor: issuer.QualificationRecord,
) -> None:
    changed = _changed_fields(predecessor, successor)

    if changed != ALLOWED_CHANGED_FIELDS:
        raise SuccessorError(
            "FINAL_342_G1114D_SUCCESSOR_SCOPE_DRIFT",
            "qualification changed outside the G11.14D repair boundary",
        )

    if successor.source != predecessor.source:
        raise SuccessorError(
            "FINAL_342_G1114D_ISSUER_SOURCE_DRIFT",
            "G11.14D must not mutate issuer source identity",
        )

    if successor.transaction_material_sha256 != predecessor.transaction_material_sha256:
        raise SuccessorError(
            "FINAL_342_G1114D_TRANSACTION_MATERIAL_DRIFT",
            "G11.14D changed transaction material",
        )

    if successor.bootstrap_state_sha256 != predecessor.bootstrap_state_sha256:
        raise SuccessorError(
            "FINAL_342_G1114D_BOOTSTRAP_DRIFT",
            "G11.14D changed bootstrap state",
        )

    if successor.canonical_static_payload_sha256 != predecessor.canonical_static_payload_sha256:
        raise SuccessorError(
            "FINAL_342_G1114D_STATIC_PAYLOAD_DRIFT",
            "G11.14D changed canonical static payload",
        )

    if successor.protected_review_schedule_sha256 != predecessor.protected_review_schedule_sha256:
        raise SuccessorError(
            "FINAL_342_G1114D_REVIEW_SCHEDULE_DRIFT",
            "G11.14D changed protected review schedule",
        )

    if successor.safety_state.effect_claims_permitted is not False:
        raise SuccessorError(
            "FINAL_342_G1114D_AUTHORITY_DRIFT",
            "G11.14D cannot permit effect claims",
        )

    if successor.safety_state.new_execution_authorized is not False:
        raise SuccessorError(
            "FINAL_342_G1114D_AUTHORITY_DRIFT",
            "G11.14D cannot authorize execution",
        )


def build_successor(
    root: Path,
) -> tuple[issuer.QualificationRecord, issuer.QualificationRecord]:
    resolved = root.resolve()
    _require_base_ancestor(resolved)

    predecessor = _load_predecessor(resolved)
    _require_predecessor_identity(predecessor)

    successor = issuer.build_qualification_record(resolved)
    _require_successor_boundary(predecessor, successor)

    return predecessor, successor


def generate(root: Path) -> dict[str, object]:
    resolved = root.resolve()
    predecessor, successor = build_successor(resolved)

    path = resolved / issuer.QUALIFICATION_RECORD_PATH
    path.write_bytes(issuer.canonical_bytes(successor))

    return {
        "status": "FINAL_342_G1114D_SUCCESSOR_QUALIFICATION_GENERATED",
        "predecessor_template_sha256": predecessor.live_execution_template.sha256,
        "successor_template_sha256": successor.live_execution_template.sha256,
        "predecessor_test_sha256": predecessor.test.sha256,
        "successor_test_sha256": successor.test.sha256,
        "issuer_source_unchanged": True,
        "transaction_material_unchanged": True,
        "effect_claims_permitted": False,
        "new_execution_authorized": False,
        "next_gate": "RECONCILE_G1114D_TERMINAL_CLASSIFICATION",
    }


def validate(root: Path) -> dict[str, object]:
    resolved = root.resolve()
    expected = issuer.build_qualification_record(resolved)

    path = resolved / issuer.QUALIFICATION_RECORD_PATH

    if not path.is_file() or path.is_symlink():
        raise SuccessorError(
            "FINAL_342_G1114D_SUCCESSOR_MISSING",
            "successor qualification is missing or unsafe",
        )

    observed = issuer.QualificationRecord.model_validate_json(path.read_bytes())

    if observed != expected:
        raise SuccessorError(
            "FINAL_342_G1114D_SUCCESSOR_DRIFT",
            "successor qualification differs from deterministic reconstruction",
        )

    if path.read_bytes() != issuer.canonical_bytes(observed):
        raise SuccessorError(
            "FINAL_342_G1114D_SUCCESSOR_BYTES_DRIFT",
            "successor qualification bytes are not canonical",
        )

    return {
        "status": "FINAL_342_G1114D_SUCCESSOR_QUALIFICATION_VALID",
        "issuer_source_unchanged": True,
        "transaction_material_unchanged": True,
        "effect_claims_permitted": False,
        "new_execution_authorized": False,
        "next_gate": "RECONCILE_G1114D_TERMINAL_CLASSIFICATION",
    }


def _parser() -> _Parser:
    parser = _Parser(prog="final-342-g1114d-qualification-successor-v1")
    parser.add_argument(
        "command",
        choices=("generate", "validate"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)

        result: dict[str, object] | None = None

        if args.command == "generate":
            result = generate(args.repo_root)

        if args.command == "validate":
            result = validate(args.repo_root)

        if result is None:
            raise SuccessorError(
                "FINAL_342_G1114D_SUCCESSOR_COMMAND_INVALID",
                "successor command was not handled",
            )

    except (
        SuccessorError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        error_code = "FINAL_342_G1114D_SUCCESSOR_FAILED"
        safe_message = "G11.14D successor qualification failed"

        if isinstance(error, SuccessorError):
            error_code = error.error_code
            safe_message = error.safe_message

        print(
            json.dumps(
                {
                    "error_code": error_code,
                    "safe_message": safe_message,
                },
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

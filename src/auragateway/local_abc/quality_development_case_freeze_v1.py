"""Freeze J7L development cases and materialize blinded human-review exports."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError, model_validator

from auragateway.contracts.quality_development_evaluation_v1 import (
    EXPECTED_HUMAN_PROJECTION_SHA256,
    EXPECTED_REGISTRY_SHA256,
    J7LCaseFamily,
    J7LDevelopmentCaseSetV1,
)
from auragateway.contracts.quality_semantic_projection_v1 import HumanSemanticProjectionV1
from auragateway.local_abc import quality_semantic_projection_v1 as semantic_projection

PROTECTED_AUTHORING_CASE_SET_PATH = Path(
    ".local/auragateway/j7l-development-v1/authoring/case-set-v1.json"
)
PROTECTED_REVIEW_ROOT = Path(".local/auragateway/j7l-development-v1/review")
PROTECTED_SCHEDULE_PATH = PROTECTED_REVIEW_ROOT / "review-schedule-v1.json"
PROTECTED_PRIMARY_EXPORT_PATH = PROTECTED_REVIEW_ROOT / "primary-reviewer-export-v1.json"
PROTECTED_SECONDARY_EXPORT_PATH = PROTECTED_REVIEW_ROOT / "secondary-reviewer-export-v1.json"

PUBLIC_FREEZE_PATH = Path("data/evals/quality/j7l-development-v1/case-set-freeze-v1.json")

EXPECTED_AUTHORING_CASE_SET_SHA256: Literal[
    "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
] = "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"

PRIMARY_COUNT: Literal[48] = 48
SECONDARY_COUNT: Literal[24] = 24

AUTHORING_ONLY_KEYS = frozenset(
    {
        "case_id",
        "case_index",
        "family",
        "positive_label_targets",
        "near_miss_label_targets",
        "terminal_action_evidence_material",
        "model_reveal_performed",
        "provider_requests_performed",
        "final_342_case_reuse_permitted",
    }
)


class J7LCaseFreezeError(RuntimeError):
    """Fail-closed J7L case-freeze error."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise J7LCaseFreezeError(
            "J7L_CASE_FREEZE_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class J7LReviewScheduleEntryV1(FrozenModel):
    case_id: str = Field(pattern=r"^j7l-dev-[0-9]{3}$")
    case_index: int = Field(ge=0, le=47)
    family: J7LCaseFamily
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    primary_assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    secondary_assignment_id: str | None = Field(
        default=None,
        pattern=r"^review-[0-9a-f]{24}$",
    )


class J7LReviewScheduleV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    schedule_id: Literal["auragateway-j7l-human-review-schedule-v1"] = (
        "auragateway-j7l-human-review-schedule-v1"
    )
    authoring_case_set_sha256: Literal[
        "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
    ] = EXPECTED_AUTHORING_CASE_SET_SHA256
    primary_assignment_count: Literal[48] = PRIMARY_COUNT
    secondary_assignment_count: Literal[24] = SECONDARY_COUNT
    entries: tuple[J7LReviewScheduleEntryV1, ...] = Field(
        min_length=48,
        max_length=48,
    )

    @model_validator(mode="after")
    def validate_schedule(self) -> Self:
        if tuple(item.case_index for item in self.entries) != tuple(range(48)):
            raise ValueError("J7L review schedule must preserve frozen case order")

        review_item_ids = tuple(item.review_item_id for item in self.entries)
        if len(review_item_ids) != len(set(review_item_ids)):
            raise ValueError("J7L review item IDs must be unique")

        primary_ids = tuple(item.primary_assignment_id for item in self.entries)
        if len(primary_ids) != len(set(primary_ids)):
            raise ValueError("J7L primary assignment IDs must be unique")

        secondary_entries = tuple(
            item for item in self.entries if item.secondary_assignment_id is not None
        )
        if len(secondary_entries) != SECONDARY_COUNT:
            raise ValueError("J7L secondary assignment count must be exactly 24")

        secondary_ids = tuple(item.secondary_assignment_id for item in secondary_entries)
        if len(secondary_ids) != len(set(secondary_ids)):
            raise ValueError("J7L secondary assignment IDs must be unique")

        all_ids = set(primary_ids) | set(secondary_ids)
        if len(all_ids) != PRIMARY_COUNT + SECONDARY_COUNT:
            raise ValueError("J7L primary and secondary assignment IDs must be disjoint")

        for item in self.entries:
            expected_secondary = item.family in {
                J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE,
                J7LCaseFamily.ONTOLOGY_NEAR_MISS,
            }
            if expected_secondary != (item.secondary_assignment_id is not None):
                raise ValueError("J7L protected secondary schedule drifted")

        return self


class J7LVisibleReviewItemV1(FrozenModel):
    assignment_id: str = Field(pattern=r"^review-[0-9a-f]{24}$")
    review_item_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    reviewer_safe_state: dict[str, JsonValue]


class J7LReviewerExportV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    export_id: str = Field(min_length=20, max_length=120)
    review_stream: Literal["primary", "secondary"]
    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    semantic_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    semantic_projection: HumanSemanticProjectionV1
    reviewer_instruction: str = Field(min_length=100, max_length=1200)
    item_count: int = Field(ge=1, le=48)
    items: tuple[J7LVisibleReviewItemV1, ...] = Field(min_length=1, max_length=48)

    @model_validator(mode="after")
    def validate_export(self) -> Self:
        if self.item_count != len(self.items):
            raise ValueError("J7L reviewer export item_count does not reconcile")

        assignment_ids = tuple(item.assignment_id for item in self.items)
        if len(assignment_ids) != len(set(assignment_ids)):
            raise ValueError("J7L reviewer export assignment IDs must be unique")

        review_item_ids = tuple(item.review_item_id for item in self.items)
        if len(review_item_ids) != len(set(review_item_ids)):
            raise ValueError("J7L reviewer export review item IDs must be unique")

        for item in self.items:
            observed = sha256_bytes(canonical_json_bytes(item.reviewer_safe_state))
            if observed != item.reviewer_safe_state_sha256:
                raise ValueError("J7L reviewer-safe state SHA-256 drifted")
            assert_reviewer_export_safe(item.model_dump(mode="json"))

        return self


class J7LCaseSetFreezeReceiptV1(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    receipt_id: Literal["auragateway-j7l-case-set-freeze-v1"] = "auragateway-j7l-case-set-freeze-v1"
    status: Literal["J7L_CASE_SET_FROZEN_FOR_HUMAN_REVIEW"] = "J7L_CASE_SET_FROZEN_FOR_HUMAN_REVIEW"

    authoring_case_set_sha256: Literal[
        "68a87a0a90b9c3df1e78de7461b5f6b22093bef52f9cd4b1854a26eb083e96c6"
    ] = EXPECTED_AUTHORING_CASE_SET_SHA256
    case_count: Literal[48] = PRIMARY_COUNT
    family_counts: dict[J7LCaseFamily, int]
    terminal_material_evidence_case_count: int = Field(ge=8, le=12)

    human_projection_sha256: Literal[
        "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    ] = "177fa6eff0af7f4677c8bf7a011e9f10e03270fc5853f749966c5fc3b7058f82"
    semantic_registry_sha256: Literal[
        "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"
    ] = "0ac2c66786a4f2713d314b2870954446ac3dfefef4c45e990faf769061944166"

    reviewer_safe_state_inventory_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_schedule_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_primary_export_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_secondary_export_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    primary_assignment_count: Literal[48] = PRIMARY_COUNT
    secondary_assignment_count: Literal[24] = SECONDARY_COUNT

    authoring_targets_publicly_persisted: Literal[False] = False
    reviewer_export_contains_authoring_metadata: Literal[False] = False
    model_reveal_performed: Literal[False] = False
    provider_requests_performed: Literal[0] = 0
    jev_requests_performed: Literal[0] = 0
    human_truth_frozen: Literal[False] = False
    threshold_selected: Literal[False] = False

    next_gate: Literal["COMPLETE_J7L_PRIMARY_HUMAN_REVIEW"] = "COMPLETE_J7L_PRIMARY_HUMAN_REVIEW"

    @model_validator(mode="after")
    def validate_family_counts(self) -> Self:
        expected = {family: 12 for family in J7LCaseFamily}
        if self.family_counts != expected:
            raise ValueError("J7L freeze receipt family counts drifted")
        return self


class J7LCaseFreezeBundle(FrozenModel):
    schedule: J7LReviewScheduleV1
    primary_export: J7LReviewerExportV1
    secondary_export: J7LReviewerExportV1
    public_receipt: J7LCaseSetFreezeReceiptV1


def canonical_json_bytes(value: object) -> bytes:
    """Return deterministic JSON bytes without a trailing newline."""

    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def artifact_bytes(model: BaseModel) -> bytes:
    """Return deterministic artifact bytes with one trailing newline."""

    return canonical_json_bytes(model.model_dump(mode="json")) + b"\n"


def sha256_bytes(value: bytes) -> str:
    """Return a lowercase SHA-256 digest."""

    return hashlib.sha256(value).hexdigest()


def _walk_keys(value: object) -> tuple[str, ...]:
    keys: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            keys.append(str(key))
            keys.extend(_walk_keys(child))

    if isinstance(value, list):
        for child in value:
            keys.extend(_walk_keys(child))

    return tuple(keys)


def assert_reviewer_export_safe(value: object) -> None:
    """Reject authoring-only metadata from reviewer-visible payloads."""

    leaked = sorted(set(_walk_keys(value)) & AUTHORING_ONLY_KEYS)
    if leaked:
        raise J7LCaseFreezeError(
            "J7L_REVIEWER_EXPORT_AUTHORING_METADATA_LEAK",
            "reviewer export contains authoring-only keys: " + ",".join(leaked),
        )


def _load_case_set(
    path: Path,
    *,
    expected_sha256: str,
) -> J7LDevelopmentCaseSetV1:
    if not path.is_file() or path.is_symlink():
        raise J7LCaseFreezeError(
            "J7L_AUTHORING_CASE_SET_MISSING",
            "protected J7L authoring case set is missing or unsafe",
        )

    raw = path.read_bytes()
    observed_sha256 = sha256_bytes(raw)
    if observed_sha256 != expected_sha256:
        raise J7LCaseFreezeError(
            "J7L_AUTHORING_CASE_SET_IDENTITY_DRIFT",
            "protected J7L authoring case-set SHA-256 drifted",
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise J7LCaseFreezeError(
            "J7L_AUTHORING_CASE_SET_JSON_INVALID",
            "protected J7L authoring case set is not valid UTF-8 JSON",
        ) from error

    try:
        return J7LDevelopmentCaseSetV1.model_validate(payload)
    except ValidationError as error:
        raise J7LCaseFreezeError(
            "J7L_AUTHORING_CASE_SET_TYPED_INVALID",
            "protected J7L authoring case set failed typed validation",
        ) from error


def _review_item_id(state: dict[str, JsonValue]) -> str:
    return sha256_bytes(canonical_json_bytes(state))


def _assignment_id(
    *,
    stream: Literal["primary", "secondary"],
    review_item_id: str,
) -> str:
    subject = f"auragateway-j7l-v1|{stream}|{review_item_id}".encode()
    return "review-" + sha256_bytes(subject)[:24]


def _schedule_for_case_set(
    case_set: J7LDevelopmentCaseSetV1,
) -> J7LReviewScheduleV1:
    entries: list[J7LReviewScheduleEntryV1] = []

    for case in case_set.cases:
        state_sha256 = sha256_bytes(canonical_json_bytes(case.reviewer_safe_state))
        review_item_id = _review_item_id(case.reviewer_safe_state)

        secondary_required = case.family in {
            J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE,
            J7LCaseFamily.ONTOLOGY_NEAR_MISS,
        }
        secondary_assignment_id: str | None = None
        if secondary_required:
            secondary_assignment_id = _assignment_id(
                stream="secondary",
                review_item_id=review_item_id,
            )

        entries.append(
            J7LReviewScheduleEntryV1(
                case_id=case.case_id,
                case_index=case.case_index,
                family=case.family,
                review_item_id=review_item_id,
                reviewer_safe_state_sha256=state_sha256,
                primary_assignment_id=_assignment_id(
                    stream="primary",
                    review_item_id=review_item_id,
                ),
                secondary_assignment_id=secondary_assignment_id,
            )
        )

    return J7LReviewScheduleV1(entries=tuple(entries))


def _reviewer_instruction(
    stream: Literal["primary", "secondary"],
) -> str:
    independence = (
        "Do not inspect any primary-review result while completing this secondary stream."
        if stream == "secondary"
        else "Complete each item without consulting any other human review result."
    )
    return (
        "Use only the visible reviewer-safe state and the included J7K human semantic "
        "projection. Score all seven criteria and evaluate all failure labels from those "
        "semantics. Do not inspect the protected authoring case set, authoring targets, "
        "case-family metadata, model outputs, or evaluator results. " + independence
    )


def _visible_item(
    *,
    assignment_id: str,
    schedule_entry: J7LReviewScheduleEntryV1,
    state: dict[str, JsonValue],
) -> J7LVisibleReviewItemV1:
    return J7LVisibleReviewItemV1(
        assignment_id=assignment_id,
        review_item_id=schedule_entry.review_item_id,
        reviewer_safe_state_sha256=schedule_entry.reviewer_safe_state_sha256,
        reviewer_safe_state=state,
    )


def build_bundle(
    case_set: J7LDevelopmentCaseSetV1,
    *,
    human_projection: HumanSemanticProjectionV1,
    human_projection_sha256: str,
    semantic_registry_sha256: str,
) -> J7LCaseFreezeBundle:
    """Build deterministic protected review material and a metadata-only public receipt."""

    if human_projection_sha256 != EXPECTED_HUMAN_PROJECTION_SHA256:
        raise J7LCaseFreezeError(
            "J7L_HUMAN_PROJECTION_IDENTITY_DRIFT",
            "J7L human semantic projection identity drifted",
        )

    if semantic_registry_sha256 != EXPECTED_REGISTRY_SHA256:
        raise J7LCaseFreezeError(
            "J7L_SEMANTIC_REGISTRY_IDENTITY_DRIFT",
            "J7L semantic registry identity drifted",
        )

    schedule = _schedule_for_case_set(case_set)
    schedule_by_case_id = {entry.case_id: entry for entry in schedule.entries}

    primary_items: list[J7LVisibleReviewItemV1] = []
    secondary_items: list[J7LVisibleReviewItemV1] = []
    safe_state_inventory: list[dict[str, str]] = []

    for case in case_set.cases:
        schedule_entry = schedule_by_case_id[case.case_id]

        safe_state_inventory.append(
            {
                "review_item_id": schedule_entry.review_item_id,
                "reviewer_safe_state_sha256": schedule_entry.reviewer_safe_state_sha256,
            }
        )

        primary_items.append(
            _visible_item(
                assignment_id=schedule_entry.primary_assignment_id,
                schedule_entry=schedule_entry,
                state=case.reviewer_safe_state,
            )
        )

        if schedule_entry.secondary_assignment_id is not None:
            secondary_items.append(
                _visible_item(
                    assignment_id=schedule_entry.secondary_assignment_id,
                    schedule_entry=schedule_entry,
                    state=case.reviewer_safe_state,
                )
            )

    primary_export = J7LReviewerExportV1(
        export_id="auragateway-j7l-primary-reviewer-export-v1",
        review_stream="primary",
        semantic_projection=human_projection,
        reviewer_instruction=_reviewer_instruction("primary"),
        item_count=len(primary_items),
        items=tuple(primary_items),
    )

    secondary_export = J7LReviewerExportV1(
        export_id="auragateway-j7l-secondary-reviewer-export-v1",
        review_stream="secondary",
        semantic_projection=human_projection,
        reviewer_instruction=_reviewer_instruction("secondary"),
        item_count=len(secondary_items),
        items=tuple(secondary_items),
    )

    assert_reviewer_export_safe(primary_export.model_dump(mode="json"))
    assert_reviewer_export_safe(secondary_export.model_dump(mode="json"))

    family_counts = Counter(case.family for case in case_set.cases)
    terminal_material_count = sum(
        case.family is J7LCaseFamily.TERMINAL_NON_SUBSTANTIVE
        and case.terminal_action_evidence_material
        for case in case_set.cases
    )

    public_receipt = J7LCaseSetFreezeReceiptV1(
        family_counts={family: family_counts[family] for family in J7LCaseFamily},
        terminal_material_evidence_case_count=terminal_material_count,
        reviewer_safe_state_inventory_sha256=sha256_bytes(
            canonical_json_bytes(safe_state_inventory)
        ),
        protected_schedule_sha256=sha256_bytes(artifact_bytes(schedule)),
        protected_primary_export_sha256=sha256_bytes(artifact_bytes(primary_export)),
        protected_secondary_export_sha256=sha256_bytes(artifact_bytes(secondary_export)),
    )

    return J7LCaseFreezeBundle(
        schedule=schedule,
        primary_export=primary_export,
        secondary_export=secondary_export,
        public_receipt=public_receipt,
    )


def build_bundle_from_repo(
    repo_root: Path,
    *,
    case_set_path: Path | None = None,
    expected_case_set_sha256: str = EXPECTED_AUTHORING_CASE_SET_SHA256,
) -> J7LCaseFreezeBundle:
    """Build the exact J7L review bundle from protected authoring evidence."""

    root = repo_root.resolve()
    path = (
        root / PROTECTED_AUTHORING_CASE_SET_PATH
        if case_set_path is None
        else case_set_path.resolve()
    )
    case_set = _load_case_set(
        path,
        expected_sha256=expected_case_set_sha256,
    )

    human_projection, _, parity = semantic_projection.build_projection_bundle(root)

    if not parity.canonical_semantic_parity:
        raise J7LCaseFreezeError(
            "J7L_J7K_SEMANTIC_PARITY_MISSING",
            "J7K semantic parity is not established",
        )

    return build_bundle(
        case_set,
        human_projection=human_projection,
        human_projection_sha256=parity.human_projection_sha256,
        semantic_registry_sha256=parity.source_registry_sha256,
    )


def _write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise J7LCaseFreezeError(
                "J7L_CASE_FREEZE_OUTPUT_UNSAFE",
                "J7L case-freeze output path is unsafe",
            )

        if path.read_bytes() != payload:
            raise J7LCaseFreezeError(
                "J7L_CASE_FREEZE_APPEND_ONLY_CONFLICT",
                "existing J7L case-freeze artifact differs from expected bytes",
            )
        return

    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise J7LCaseFreezeError(
            "J7L_CASE_FREEZE_TEMP_RESIDUE",
            "J7L case-freeze temporary output already exists",
        )

    with temporary.open("xb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(temporary, path)


def write_artifacts(repo_root: Path) -> J7LCaseSetFreezeReceiptV1:
    """Materialize protected reviewer exports and the public metadata-only freeze."""

    root = repo_root.resolve()
    bundle = build_bundle_from_repo(root)

    _write_once(
        root / PROTECTED_SCHEDULE_PATH,
        artifact_bytes(bundle.schedule),
    )
    _write_once(
        root / PROTECTED_PRIMARY_EXPORT_PATH,
        artifact_bytes(bundle.primary_export),
    )
    _write_once(
        root / PROTECTED_SECONDARY_EXPORT_PATH,
        artifact_bytes(bundle.secondary_export),
    )
    _write_once(
        root / PUBLIC_FREEZE_PATH,
        artifact_bytes(bundle.public_receipt),
    )

    return verify_artifacts(root)


def _verify_exact_artifact(
    path: Path,
    *,
    expected: BaseModel,
) -> None:
    if not path.is_file() or path.is_symlink():
        raise J7LCaseFreezeError(
            "J7L_CASE_FREEZE_ARTIFACT_MISSING",
            "required J7L case-freeze artifact is missing or unsafe",
        )

    if path.read_bytes() != artifact_bytes(expected):
        raise J7LCaseFreezeError(
            "J7L_CASE_FREEZE_ARTIFACT_BYTES_DRIFT",
            "materialized J7L case-freeze artifact bytes drifted",
        )


def verify_artifacts(repo_root: Path) -> J7LCaseSetFreezeReceiptV1:
    """Rebuild and verify every protected/public case-freeze artifact."""

    root = repo_root.resolve()
    bundle = build_bundle_from_repo(root)

    _verify_exact_artifact(
        root / PROTECTED_SCHEDULE_PATH,
        expected=bundle.schedule,
    )
    _verify_exact_artifact(
        root / PROTECTED_PRIMARY_EXPORT_PATH,
        expected=bundle.primary_export,
    )
    _verify_exact_artifact(
        root / PROTECTED_SECONDARY_EXPORT_PATH,
        expected=bundle.secondary_export,
    )
    _verify_exact_artifact(
        root / PUBLIC_FREEZE_PATH,
        expected=bundle.public_receipt,
    )

    return bundle.public_receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    for command in ("write", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument(
            "--repo-root",
            type=Path,
            required=True,
        )

    return parser


def main() -> int:
    args = _build_parser().parse_args()

    try:
        receipt = (
            write_artifacts(args.repo_root)
            if args.command == "write"
            else verify_artifacts(args.repo_root)
        )
    except (J7LCaseFreezeError, ValidationError, OSError) as error:
        if isinstance(error, J7LCaseFreezeError):
            code = error.error_code
            message = error.safe_message
        elif isinstance(error, ValidationError):
            code = "J7L_CASE_FREEZE_TYPED_VALIDATION_FAILED"
            message = "J7L case-freeze typed validation failed"
        else:
            code = "J7L_CASE_FREEZE_LOCAL_IO_FAILED"
            message = "J7L case-freeze local I/O failed"

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
            receipt.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

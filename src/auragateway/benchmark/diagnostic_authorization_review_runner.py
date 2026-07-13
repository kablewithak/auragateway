"""Validate inactive diagnostic execution review and reproduce its dry run."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal, TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.benchmark.diagnostic_fixture_runner import (
    DiagnosticFixtureError,
    verify_diagnostic_fixtures,
)
from auragateway.benchmark.diagnostic_plan_runner import (
    DiagnosticDesignError,
    validate_diagnostic_design,
)
from auragateway.contracts.diagnostic_authorization_review import (
    DiagnosticAuthorizationReviewManifest,
    DiagnosticAuthorizationReviewPackage,
    DiagnosticAuthorizationReviewSummary,
    DiagnosticDryRunAttempt,
    DiagnosticDryRunReport,
)
from auragateway.contracts.diagnostic_experiment import DiagnosticExperimentPlan
from auragateway.contracts.diagnostic_fixtures import DiagnosticFixtureManifest

_DEFAULT_REVIEW_ROOT = Path("data/evals/benchmark/diagnostic-authorization-review-v1")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class DiagnosticAuthorizationReviewError(Exception):
    """Expected metadata-safe authorization review failure."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_ASSET_MISSING",
            "A required diagnostic authorization review asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_ASSET_MISSING",
            "A required diagnostic authorization review asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_INVALID_JSON",
            "A diagnostic authorization review asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(include_url=False, include_input=False)
        )
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_VALIDATION_FAILED",
            "A diagnostic authorization review asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _binding_map(
    review: DiagnosticAuthorizationReviewPackage,
) -> dict[str, str]:
    return {item.path: item.sha256 for item in review.bindings}


def _verify_review_bindings(
    repo_root: Path,
    review: DiagnosticAuthorizationReviewPackage,
) -> None:
    for binding in review.bindings:
        path = repo_root / binding.path
        observed = _sha256_file(path)
        if observed != binding.sha256:
            raise DiagnosticAuthorizationReviewError(
                "DIAGNOSTIC_AUTHORIZATION_REVIEW_BINDING_MISMATCH",
                "A frozen diagnostic review dependency no longer matches.",
                path=str(path),
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed}",
                ),
            )


def _attempt_request_hash(
    fixture: DiagnosticFixtureManifest,
    cohort_id: str,
    condition_value: str,
    turn_index: int,
) -> str:
    cohort = next(
        (item for item in fixture.cohorts if item.cohort_id == cohort_id),
        None,
    )
    if cohort is None:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_COHORT_MISSING",
            "A designed cohort is absent from the frozen fixture manifest.",
            details=(cohort_id,),
        )
    if condition_value == "condition_b":
        return cohort.condition_b_request_sha256_by_turn[turn_index - 1]
    if condition_value == "condition_c":
        return cohort.condition_c_request_sha256_by_turn[turn_index - 1]
    raise DiagnosticAuthorizationReviewError(
        "DIAGNOSTIC_AUTHORIZATION_REVIEW_CONDITION_INVALID",
        "The diagnostic review contains a condition outside B and C.",
        details=(condition_value,),
    )


def _build_dry_run_report(
    design: DiagnosticExperimentPlan,
    fixture: DiagnosticFixtureManifest,
    review: DiagnosticAuthorizationReviewPackage,
) -> DiagnosticDryRunReport:
    fixture_by_cohort = {item.cohort_id: item for item in fixture.cohorts}
    sequence_ids = tuple(item.sequence_id for item in design.sequences)
    if sequence_ids != review.sequence_ids_in_order:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_SEQUENCE_ORDER_MISMATCH",
            "The authorization review sequence order differs from the frozen design.",
        )

    attempts: list[DiagnosticDryRunAttempt] = []
    previous_attempt_offset = 0
    previous_sequence_terminal_offset = 0

    for sequence_position, sequence in enumerate(design.sequences):
        cohort = fixture_by_cohort.get(sequence.cohort_id)
        if cohort is None:
            raise DiagnosticAuthorizationReviewError(
                "DIAGNOSTIC_AUTHORIZATION_REVIEW_COHORT_MISSING",
                "A designed cohort is absent from the frozen fixture manifest.",
                details=(sequence.cohort_id,),
            )

        if sequence_position == 0:
            sequence_start_offset = 0
        else:
            sequence_start_offset = (
                previous_sequence_terminal_offset
                + sequence.minimum_delay_after_previous_sequence_seconds
            )

        for turn_index in range(1, sequence.turn_count + 1):
            planned_offset = sequence_start_offset + (
                (turn_index - 1) * sequence.inter_turn_delay_seconds
            )
            delay_from_previous = 0 if not attempts else planned_offset - previous_attempt_offset
            request_hash = _attempt_request_hash(
                fixture,
                sequence.cohort_id,
                sequence.condition_label.value,
                turn_index,
            )
            attempts.append(
                DiagnosticDryRunAttempt(
                    attempt_index=len(attempts),
                    sequence_id=sequence.sequence_id,
                    sequence_schedule_index=sequence.schedule_index,
                    stage=sequence.stage,
                    cohort_id=sequence.cohort_id,
                    condition_label=sequence.condition_label,
                    turn_index=turn_index,
                    planned_offset_seconds=planned_offset,
                    planned_delay_from_previous_attempt_seconds=(delay_from_previous),
                    system_prompt_sha256=cohort.system_prompt_sha256,
                    user_prompt_sha256=cohort.user_prompt_sha256_by_turn[turn_index - 1],
                    provider_request_sha256=request_hash,
                    prompt_byte_count=cohort.total_prompt_byte_counts_by_turn[turn_index - 1],
                    input_token_estimate=cohort.input_token_estimates_by_turn[turn_index - 1],
                )
            )
            previous_attempt_offset = planned_offset

        previous_sequence_terminal_offset = attempts[-1].planned_offset_seconds

    return DiagnosticDryRunReport(
        report_id="batch-06-diagnostic-execution-dry-run-v1",
        review_id=review.review_id,
        attempts=tuple(attempts),
        maximum_total_cost_microusd=review.maximum_total_cost_microusd,
    )


def _assert_report_matches(
    observed: DiagnosticDryRunReport,
    expected: DiagnosticDryRunReport,
) -> None:
    if observed.model_dump(mode="json") != expected.model_dump(mode="json"):
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_DRY_RUN_DRIFT",
            "The committed dry-run report no longer reproduces from frozen inputs.",
        )


def validate_authorization_review(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
    command: Literal["validate", "dry-run"] = "validate",
) -> DiagnosticAuthorizationReviewSummary:
    """Validate inactive authorization review without credentials or provider calls."""

    validate_diagnostic_design(repo_root)
    fixture_summary = verify_diagnostic_fixtures(repo_root)
    if fixture_summary.provider_calls_permitted:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_FIXTURE_STATE_UNSAFE",
            "The fixture verification unexpectedly permits provider calls.",
        )

    resolved_root = repo_root / review_root
    review_path = resolved_root / "review_package.json"
    report_path = resolved_root / "dry_run_report.json"
    manifest_path = resolved_root / "manifest.json"
    active_authorization_path = resolved_root / "authorization.json"
    live_batch_path = repo_root / "data/evals/benchmark/live-development-v7"

    if active_authorization_path.exists():
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_ACTIVE_FILE_FORBIDDEN",
            "An active authorization file is forbidden in the review-only slice.",
            path=str(active_authorization_path),
        )
    if live_batch_path.exists():
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_BATCH07_FORBIDDEN",
            "Batch 07 assets are forbidden before active authorization review.",
            path=str(live_batch_path),
        )

    review = _load_model(
        review_path,
        DiagnosticAuthorizationReviewPackage,
    )
    observed_report = _load_model(
        report_path,
        DiagnosticDryRunReport,
    )
    manifest = _load_model(
        manifest_path,
        DiagnosticAuthorizationReviewManifest,
    )

    if manifest.review_id != review.review_id:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_ID_MISMATCH",
            "The review package and manifest identify different reviews.",
        )
    if _sha256_file(review_path) != manifest.review_package_sha256:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_PACKAGE_HASH_MISMATCH",
            "The review package no longer matches its manifest.",
            path=str(review_path),
        )
    if _sha256_file(report_path) != manifest.dry_run_report_sha256:
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_REPORT_HASH_MISMATCH",
            "The dry-run report no longer matches its manifest.",
            path=str(report_path),
        )

    expected_review_path = (repo_root / manifest.review_package_path).resolve()
    expected_report_path = (repo_root / manifest.dry_run_report_path).resolve()
    if expected_review_path != review_path.resolve():
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_PACKAGE_PATH_MISMATCH",
            "The review manifest points to a different package path.",
        )
    if expected_report_path != report_path.resolve():
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_REPORT_PATH_MISMATCH",
            "The review manifest points to a different report path.",
        )

    _verify_review_bindings(repo_root, review)
    bindings = _binding_map(review)
    design_path = Path("data/evals/benchmark/diagnostic-design-v1/experiment_plan.json")
    fixture_path = Path("data/evals/benchmark/diagnostic-fixtures-v1/fixture_manifest.json")
    design = _load_model(
        repo_root / design_path,
        DiagnosticExperimentPlan,
    )
    fixture = _load_model(
        repo_root / fixture_path,
        DiagnosticFixtureManifest,
    )
    if bindings[design_path.as_posix()] != _sha256_file(repo_root / design_path):
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_DESIGN_BINDING_INVALID",
            "The design binding does not match the validated design bytes.",
        )
    if bindings[fixture_path.as_posix()] != _sha256_file(repo_root / fixture_path):
        raise DiagnosticAuthorizationReviewError(
            "DIAGNOSTIC_AUTHORIZATION_REVIEW_FIXTURE_BINDING_INVALID",
            "The fixture binding does not match the validated fixture bytes.",
        )

    expected_report = _build_dry_run_report(design, fixture, review)
    _assert_report_matches(observed_report, expected_report)

    return DiagnosticAuthorizationReviewSummary(
        command=command,
        review_id=review.review_id,
        status=review.status,
        activation_state=review.activation_state,
    )


def _error_envelope(
    exc: (DiagnosticAuthorizationReviewError | DiagnosticDesignError | DiagnosticFixtureError),
) -> str:
    return json.dumps(
        {
            "error_code": exc.error_code,
            "safe_message": exc.safe_message,
            "path": exc.path,
            "details": exc.details,
        },
        indent=2,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=("Validate or dry-run the inactive Batch 06 diagnostic execution review.")
    )
    parser.add_argument(
        "command",
        choices=("validate", "dry-run"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    parser.add_argument(
        "--review-root",
        type=Path,
        default=_DEFAULT_REVIEW_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        summary = validate_authorization_review(
            args.repo_root.resolve(),
            review_root=args.review_root,
            command=args.command,
        )
    except (
        DiagnosticAuthorizationReviewError,
        DiagnosticDesignError,
        DiagnosticFixtureError,
    ) as exc:
        print(_error_envelope(exc), file=sys.stderr)
        return 1

    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

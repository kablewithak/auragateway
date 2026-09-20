"""Validate the inactive J7L Groq strict-schema accounting probe review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from importlib import metadata
from pathlib import Path
from typing import Never, TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.contracts.j7l_groq_schema_accounting_probe_v1 import (
    PreActivationMeasurementsV1,
    SchemaAccountingDryRunReportV1,
    SchemaAccountingProbePlanV1,
    SchemaAccountingProbeReviewV1,
    SchemaAccountingReviewManifestV1,
)

REVIEW_ROOT = Path("data/evals/quality/j7l-groq-schema-accounting-review-v1")
SUCCESSOR_CONSTITUTION_PATH = Path(
    "docs/benchmark/AuraGateway_J7L_Model_Derived_Reference_Successor_Constitution_v1.md"
)
EXPECTED_SUCCESSOR_CONSTITUTION_SHA256 = (
    "aef0d6a3edbaa63c1e5b46c278b019aeed613d8b8f941f98ee45eaee0a2d6ad2"
)
_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)


class SchemaAccountingReviewError(RuntimeError):
    """Fail-closed error for non-live schema-accounting review validation."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_ARGUMENT_ERROR",
            message,
        )


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_model(path: Path, model_type: type[_MODEL_T]) -> _MODEL_T:
    return model_type.model_validate(_load_json(path))


def _validate_manifest(
    repo_root: Path,
    manifest: SchemaAccountingReviewManifestV1,
) -> None:
    bindings = (
        (manifest.probe_plan_path, manifest.probe_plan_sha256),
        (manifest.review_path, manifest.review_sha256),
        (manifest.dry_run_report_path, manifest.dry_run_report_sha256),
        (
            manifest.strict_response_schema_path,
            manifest.strict_response_schema_sha256,
        ),
        (
            manifest.synthetic_prompt_recipe_path,
            manifest.synthetic_prompt_recipe_sha256,
        ),
        (
            manifest.preactivation_measurements_path,
            manifest.preactivation_measurements_sha256,
        ),
        (manifest.adr_path, manifest.adr_sha256),
        (manifest.report_path, manifest.report_sha256),
    )
    for relative, expected in bindings:
        path = repo_root / relative
        if not path.is_file() or path.is_symlink():
            raise SchemaAccountingReviewError(
                "J7L_GROQ_SCHEMA_ACCOUNTING_ASSET_MISSING",
                "A frozen schema-accounting review asset is missing or unsafe.",
            )
        if _sha256_file(path) != expected:
            raise SchemaAccountingReviewError(
                "J7L_GROQ_SCHEMA_ACCOUNTING_ASSET_DRIFT",
                "A frozen schema-accounting review asset no longer matches its manifest.",
            )


def validate_review(repo_root: Path) -> dict[str, object]:
    """Validate the inactive review without reading credentials or making network calls."""

    root = repo_root.resolve()
    manifest = _load_model(
        root / REVIEW_ROOT / "manifest.json",
        SchemaAccountingReviewManifestV1,
    )
    _validate_manifest(root, manifest)

    plan = _load_model(
        root / manifest.probe_plan_path,
        SchemaAccountingProbePlanV1,
    )
    review = _load_model(
        root / manifest.review_path,
        SchemaAccountingProbeReviewV1,
    )
    measurements = _load_model(
        root / manifest.preactivation_measurements_path,
        PreActivationMeasurementsV1,
    )
    _load_model(
        root / manifest.dry_run_report_path,
        SchemaAccountingDryRunReportV1,
    )

    if plan.prompt_recipe_sha256 != manifest.synthetic_prompt_recipe_sha256:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_PROMPT_BINDING_DRIFT",
            "The probe plan no longer binds the frozen synthetic prompt.",
        )
    if plan.strict_response_schema_sha256 != manifest.strict_response_schema_sha256:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_SCHEMA_BINDING_DRIFT",
            "The probe plan no longer binds the frozen strict response schema.",
        )
    if review.probe_plan_sha256 != manifest.probe_plan_sha256:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_REVIEW_PLAN_DRIFT",
            "The review no longer binds the frozen probe plan.",
        )
    if review.preactivation_measurements_sha256 != (manifest.preactivation_measurements_sha256):
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_MEASUREMENT_BINDING_DRIFT",
            "The review no longer binds the frozen preactivation measurements.",
        )
    if review.strict_response_schema_sha256 != manifest.strict_response_schema_sha256:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_REVIEW_SCHEMA_DRIFT",
            "The review no longer binds the frozen strict schema.",
        )
    if review.synthetic_prompt_recipe_sha256 != (manifest.synthetic_prompt_recipe_sha256):
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_REVIEW_PROMPT_DRIFT",
            "The review no longer binds the frozen synthetic prompt.",
        )

    successor_path = root / SUCCESSOR_CONSTITUTION_PATH
    if not successor_path.is_file() or successor_path.is_symlink():
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_SUCCESSOR_MISSING",
            "The J7L model-derived successor constitution is missing or unsafe.",
        )
    if _sha256_file(successor_path) != EXPECTED_SUCCESSOR_CONSTITUTION_SHA256:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_SUCCESSOR_DRIFT",
            "The J7L model-derived successor constitution identity drifted.",
        )
    if review.successor_constitution_sha256 != EXPECTED_SUCCESSOR_CONSTITUTION_SHA256:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_SUCCESSOR_BINDING_DRIFT",
            "The schema-accounting review binds the wrong successor constitution.",
        )

    installed_sdk = metadata.version("groq")
    if installed_sdk != plan.installed_sdk_version_required:
        raise SchemaAccountingReviewError(
            "J7L_GROQ_SCHEMA_ACCOUNTING_SDK_VERSION_MISMATCH",
            "The installed Groq SDK does not match the frozen review boundary.",
        )

    return {
        "status": "J7L_GROQ_SCHEMA_ACCOUNTING_REVIEW_PASS",
        "next_gate": manifest.next_gate,
        "installed_groq_sdk_version": installed_sdk,
        "planned_attempt_count": plan.planned_attempt_count,
        "maximum_provider_calls": plan.maximum_provider_calls,
        "organization_tpm_observed": measurements.organization_tpm_observed,
        "maximum_exact_message_tokens": measurements.maximum_exact_message_tokens,
        "maximum_conservative_plus_output_budget_tokens": (
            measurements.maximum_conservative_plus_output_budget_tokens
        ),
        "provider_call_performed": False,
        "credential_accessed": False,
        "execution_command_available": False,
        "j7l_reference_request_permitted": False,
        "jev_request_permitted": False,
    }


def dry_run(repo_root: Path) -> dict[str, object]:
    """Return the frozen two-attempt schedule without executing it."""

    root = repo_root.resolve()
    manifest = _load_model(
        root / REVIEW_ROOT / "manifest.json",
        SchemaAccountingReviewManifestV1,
    )
    _validate_manifest(root, manifest)
    report = _load_model(
        root / manifest.dry_run_report_path,
        SchemaAccountingDryRunReportV1,
    )

    return {
        "status": "J7L_GROQ_SCHEMA_ACCOUNTING_DRY_RUN_PASS",
        "attempt_roles": tuple(attempt.role for attempt in report.attempts),
        "attempt_offsets_seconds": tuple(
            attempt.planned_offset_seconds for attempt in report.attempts
        ),
        "provider_call_performed": False,
        "credential_accessed": False,
        "execution_command_available": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate")
    validate.add_argument("--repo-root", type=Path, required=True)
    dry = subparsers.add_parser("dry-run")
    dry.add_argument("--repo-root", type=Path, required=True)
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        result = (
            validate_review(args.repo_root)
            if args.command == "validate"
            else dry_run(args.repo_root)
        )
    except (
        SchemaAccountingReviewError,
        ValidationError,
        OSError,
        json.JSONDecodeError,
        metadata.PackageNotFoundError,
    ) as error:
        code = (
            error.error_code
            if isinstance(error, SchemaAccountingReviewError)
            else "J7L_GROQ_SCHEMA_ACCOUNTING_REVIEW_VALIDATION_FAILED"
        )
        message = (
            error.safe_message
            if isinstance(error, SchemaAccountingReviewError)
            else "J7L Groq schema-accounting review validation failed."
        )
        print(
            json.dumps(
                {"error_code": code, "safe_message": message},
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

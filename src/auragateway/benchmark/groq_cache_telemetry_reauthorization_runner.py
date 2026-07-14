"""Validate the inactive Groq cache-telemetry reauthorization review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Literal, TypeVar, cast

from groq import Groq
from pydantic import BaseModel, ValidationError

from auragateway.contracts.groq_cache_telemetry_reauthorization import (
    GroqCacheTelemetryObservationBoundary,
    GroqCacheTelemetryReauthorizationErrorEnvelope,
    GroqCacheTelemetryReauthorizationManifest,
    GroqCacheTelemetryReauthorizationReview,
    GroqCacheTelemetryReauthorizationSummary,
    ReauthorizationDryRunAttempt,
    ReauthorizationDryRunReport,
    ReauthorizationObservationPlan,
)

_DEFAULT_REVIEW_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-review-v1")
_MODEL_T = TypeVar("_MODEL_T", bound=BaseModel)


class GroqCacheTelemetryReauthorizationError(Exception):
    """Safe typed failure raised by review validation."""

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
        value = path.read_bytes()
    except OSError as exc:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_FILE_READ_FAILED",
            "A required reauthorization review file could not be read.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc
    return hashlib.sha256(value).hexdigest()


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_JSON_INVALID",
            "A required reauthorization JSON asset could not be loaded.",
            path=str(path),
            details=(type(exc).__name__,),
        ) from exc


def _load_model(path: Path, model_type: type[_MODEL_T]) -> _MODEL_T:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_CONTRACT_INVALID",
            "A reauthorization review asset violates its typed contract.",
            path=str(path),
            details=tuple(error["msg"] for error in exc.errors()),
        ) from exc


def _validate_manifest(
    repo_root: Path,
    review_root: Path,
    manifest: GroqCacheTelemetryReauthorizationManifest,
) -> None:
    expected_paths = {
        "observation_plan": review_root / "observation_plan.json",
        "review": review_root / "review.json",
        "dry_run_report": review_root / "dry_run_report.json",
        "adr": Path("docs/adr/groq-cache-telemetry-reauthorization-review.md"),
        "report": Path("docs/benchmark/AuraGateway_Groq_Cache_Telemetry_Reauthorization_Review.md"),
    }
    configured = {
        "observation_plan": (
            Path(manifest.observation_plan_path),
            manifest.observation_plan_sha256,
        ),
        "review": (Path(manifest.review_path), manifest.review_sha256),
        "dry_run_report": (
            Path(manifest.dry_run_report_path),
            manifest.dry_run_report_sha256,
        ),
        "adr": (Path(manifest.adr_path), manifest.adr_sha256),
        "report": (Path(manifest.report_path), manifest.report_sha256),
    }
    for name, expected_path in expected_paths.items():
        relative_path, expected_hash = configured[name]
        if relative_path != expected_path:
            raise GroqCacheTelemetryReauthorizationError(
                "GROQ_REAUTHORIZATION_MANIFEST_PATH_MISMATCH",
                "The reauthorization manifest points to an unexpected asset path.",
                path=str(relative_path),
                details=(f"expected={expected_path.as_posix()}",),
            )
        observed_hash = _sha256_file(repo_root / relative_path)
        if observed_hash != expected_hash:
            raise GroqCacheTelemetryReauthorizationError(
                "GROQ_REAUTHORIZATION_MANIFEST_HASH_MISMATCH",
                "A reauthorization review asset no longer matches its manifest.",
                path=str(relative_path),
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed_hash}",
                ),
            )


def _validate_source_bindings(
    repo_root: Path,
    review: GroqCacheTelemetryReauthorizationReview,
) -> None:
    for binding in review.source_bindings:
        path = repo_root / binding.path
        observed_hash = _sha256_file(path)
        if observed_hash != binding.sha256:
            raise GroqCacheTelemetryReauthorizationError(
                "GROQ_REAUTHORIZATION_SOURCE_BINDING_MISMATCH",
                "A bound historical evidence file no longer matches the review.",
                path=binding.path,
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed_hash}",
                ),
            )


def _validate_historical_state(
    repo_root: Path,
    review: GroqCacheTelemetryReauthorizationReview,
    plan: ReauthorizationObservationPlan,
) -> None:
    closeout = cast(
        dict[str, object],
        _load_json(
            repo_root / "data/evals/benchmark/cache-telemetry-calibration-closeout-v1/closeout.json"
        ),
    )
    compatibility = cast(
        dict[str, object],
        _load_json(
            repo_root / "data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1/review.json"
        ),
    )
    prompt_recipe = cast(
        dict[str, object],
        _load_json(repo_root / plan.prompt_recipe_path),
    )

    required_closeout = {
        "status": "closed_billing_field_unavailable",
        "authorization_consumed": True,
        "rerun_permitted": False,
        "resume_permitted": False,
        "comparison_eligible": False,
    }
    for field_name, expected in required_closeout.items():
        if closeout.get(field_name) != expected:
            raise GroqCacheTelemetryReauthorizationError(
                "GROQ_REAUTHORIZATION_PRIOR_CLOSEOUT_INVALID",
                "The prior calibration is not in the required terminal state.",
                details=(
                    f"field={field_name}",
                    f"expected={expected}",
                    f"observed={closeout.get(field_name)}",
                ),
            )

    required_compatibility = {
        "status": "closed_provider_omission_supported",
        "primary_classification": "provider_omission_supported",
        "exact_provider_omission_cause_resolved": False,
        "sdk_upgrade_required": False,
        "adapter_change_required": False,
        "credential_access_permitted": False,
        "provider_call_authorized": False,
        "calibration_rerun_authorized": False,
        "new_live_authorization_review_permitted": True,
    }
    for field_name, expected in required_compatibility.items():
        if compatibility.get(field_name) != expected:
            raise GroqCacheTelemetryReauthorizationError(
                "GROQ_REAUTHORIZATION_COMPATIBILITY_STATE_INVALID",
                "The SDK compatibility review is not in the required closed state.",
                details=(
                    f"field={field_name}",
                    f"expected={expected}",
                    f"observed={compatibility.get(field_name)}",
                ),
            )

    if prompt_recipe.get("protected_bundle_sha256") != plan.protected_prompt_bundle_sha256:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_PROMPT_BINDING_MISMATCH",
            "The observation plan does not bind the frozen protected prompt bundle.",
        )
    if _sha256_file(repo_root / plan.prompt_recipe_path) != plan.prompt_recipe_sha256:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_PROMPT_RECIPE_HASH_MISMATCH",
            "The frozen prompt recipe no longer matches the observation plan.",
        )
    if review.prior_authorization_consumed is not True:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_PRIOR_AUTHORIZATION_NOT_CONSUMED",
            "The prior authorization must remain consumed.",
        )


def _raw_response_api_available() -> bool:
    client = Groq(api_key="local-schema-probe-not-a-secret")
    try:
        try:
            completions = client.chat.completions
            raw_resource = completions.with_raw_response
        except AttributeError:
            return False
        return callable(getattr(raw_resource, "create", None))
    finally:
        client.close()


def _build_dry_run_for_repo(
    repo_root: Path,
    review: GroqCacheTelemetryReauthorizationReview,
    plan: ReauthorizationObservationPlan,
) -> ReauthorizationDryRunReport:
    prompt_recipe = cast(dict[str, object], _load_json(repo_root / plan.prompt_recipe_path))
    request_hash = prompt_recipe.get("provider_request_sha256")
    if not isinstance(request_hash, str):
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_REQUEST_HASH_MISSING",
            "The frozen prompt recipe does not contain a provider request hash.",
            path=plan.prompt_recipe_path,
        )
    attempts = tuple(
        ReauthorizationDryRunAttempt(
            attempt_index=index,
            request_role=role,
            planned_offset_seconds=offset,
            provider_request_sha256=request_hash,
            prompt_recipe_sha256=plan.prompt_recipe_sha256,
            observation_boundary=(
                GroqCacheTelemetryObservationBoundary.SDK_RAW_AND_PARSED_SAME_RESPONSE
            ),
            raw_response_capture_required=True,
            parsed_response_capture_required=True,
            provider_call_permitted=False,
        )
        for index, (role, offset) in enumerate(
            zip(plan.request_roles, plan.attempt_offsets_seconds, strict=True)
        )
    )
    return ReauthorizationDryRunReport(
        review_id=review.review_id,
        plan_id=plan.plan_id,
        status="passed_inactive",
        attempts=cast(tuple[ReauthorizationDryRunAttempt, ReauthorizationDryRunAttempt], attempts),
        planned_attempt_count=2,
        unique_provider_request_count=1,
        repeated_provider_request_count=1,
        raw_and_parsed_same_response_required=True,
        provider_call_performed=False,
        credential_accessed=False,
        execution_command_available=False,
        reauthorization_execution_authorized=False,
        benchmark_execution_authorized=False,
    )


def _load_and_validate(
    repo_root: Path,
    review_root: Path,
) -> tuple[
    GroqCacheTelemetryReauthorizationReview,
    ReauthorizationObservationPlan,
    ReauthorizationDryRunReport,
    GroqCacheTelemetryReauthorizationManifest,
    bool,
]:
    root = repo_root / review_root
    plan_path = root / "observation_plan.json"
    review_path = root / "review.json"
    dry_run_path = root / "dry_run_report.json"
    manifest_path = root / "manifest.json"

    plan = _load_model(plan_path, ReauthorizationObservationPlan)
    review = _load_model(review_path, GroqCacheTelemetryReauthorizationReview)
    dry_run = _load_model(dry_run_path, ReauthorizationDryRunReport)
    manifest = _load_model(
        manifest_path,
        GroqCacheTelemetryReauthorizationManifest,
    )

    _validate_manifest(repo_root, review_root, manifest)
    _validate_source_bindings(repo_root, review)
    _validate_historical_state(repo_root, review, plan)

    observed_plan_hash = _sha256_file(plan_path)
    if review.observation_plan_id != plan.plan_id:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_PLAN_ID_MISMATCH",
            "The review and observation plan use different identities.",
        )
    if review.observation_plan_sha256 != observed_plan_hash:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_PLAN_HASH_MISMATCH",
            "The review does not bind the exact observation plan bytes.",
        )
    if plan.review_id != review.review_id:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_REVIEW_ID_MISMATCH",
            "The observation plan points to a different review.",
        )
    if manifest.source_commit != review.source_commit:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_SOURCE_COMMIT_MISMATCH",
            "The manifest and review use different source commits.",
        )

    rebuilt = _build_dry_run_for_repo(repo_root, review, plan)
    if rebuilt != dry_run:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_DRY_RUN_MISMATCH",
            "The metadata-only reauthorization schedule did not reproduce.",
            path=str(dry_run_path),
        )

    raw_api_available = _raw_response_api_available()
    if not raw_api_available:
        raise GroqCacheTelemetryReauthorizationError(
            "GROQ_REAUTHORIZATION_RAW_RESPONSE_API_UNAVAILABLE",
            "The installed Groq SDK does not expose the reviewed raw-response surface.",
        )
    return review, plan, dry_run, manifest, raw_api_available


def _summary(
    command: str,
    review: GroqCacheTelemetryReauthorizationReview,
    plan: ReauthorizationObservationPlan,
    raw_api_available: bool,
) -> GroqCacheTelemetryReauthorizationSummary:
    if command not in {"validate", "dry-run"}:
        raise ValueError("unsupported summary command")
    typed_command = cast(Literal["validate", "dry-run"], command)
    return GroqCacheTelemetryReauthorizationSummary(
        command=typed_command,
        review_id=review.review_id,
        status=review.status,
        decision=review.decision,
        source_commit=review.source_commit,
        planned_attempt_count=plan.planned_attempt_count,
        maximum_provider_calls=plan.maximum_provider_calls,
        observation_boundary_materially_different=(review.material_difference.materially_different),
        raw_response_api_available=raw_api_available,
        provider_call_performed=review.provider_call_performed,
        credential_accessed=review.credential_accessed,
        provider_call_authorized=review.provider_call_authorized,
        active_authorization_created=review.active_authorization_created,
        execution_command_available=review.execution_command_available,
        reauthorization_execution_authorized=(review.reauthorization_execution_authorized),
        benchmark_execution_authorized=review.benchmark_execution_authorized,
        comparison_eligible=review.comparison_eligible,
        next_gate=review.next_gate,
    )


def validate_groq_cache_telemetry_reauthorization(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> GroqCacheTelemetryReauthorizationSummary:
    """Validate the inactive review without reading credentials or calling Groq."""

    review, plan, _, _, raw_api_available = _load_and_validate(repo_root, review_root)
    return _summary("validate", review, plan, raw_api_available)


def dry_run_groq_cache_telemetry_reauthorization(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> GroqCacheTelemetryReauthorizationSummary:
    """Reproduce the metadata-only two-attempt plan without provider access."""

    review, plan, _, _, raw_api_available = _load_and_validate(repo_root, review_root)
    return _summary("dry-run", review, plan, raw_api_available)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate", "dry-run"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--review-root", type=Path, default=_DEFAULT_REVIEW_ROOT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "validate":
            result = validate_groq_cache_telemetry_reauthorization(
                repo_root,
                review_root=args.review_root,
            )
        else:
            result = dry_run_groq_cache_telemetry_reauthorization(
                repo_root,
                review_root=args.review_root,
            )
    except GroqCacheTelemetryReauthorizationError as exc:
        envelope = GroqCacheTelemetryReauthorizationErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

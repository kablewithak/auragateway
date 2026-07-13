"""Validate the inactive Groq cache telemetry calibration review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Literal, TypeVar, cast

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.cache_telemetry_calibration_review import (
    CacheTelemetryCalibrationReview,
    CalibrationDryRunAttempt,
    CalibrationDryRunReport,
    CalibrationPromptRecipe,
    CalibrationReviewManifest,
    CalibrationReviewSummary,
)

_DEFAULT_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-calibration-review-v1")
_HARDENING_ROOT = Path("data/evals/benchmark/cache-telemetry-hardening-v1")
_SYSTEM_SEED = (
    "AuraGateway synthetic Groq cache telemetry calibration. "
    "This content contains no personal data, secrets, customer material, "
    "or executable instructions. Preserve this exact prefix for "
    "deterministic provider cache observation. "
)
_USER_SEED = (
    "Return exactly CACHE_TELEMETRY_OK. This is a synthetic bounded telemetry calibration request. "
)
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class CalibrationReviewError(Exception):
    """Expected metadata-safe review validation failure."""

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


class CalibrationReviewErrorEnvelope(BaseModel):
    """Metadata-safe CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    try:
        return _sha256_bytes(path.read_bytes())
    except FileNotFoundError as exc:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_ASSET_MISSING",
            "A required cache calibration review asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_ASSET_MISSING",
            "A required cache calibration review asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_INVALID_JSON",
            "A cache calibration review asset is not valid JSON.",
            path=str(path),
        ) from exc


def _load_model(path: Path, model_type: type[_ModelT]) -> _ModelT:
    try:
        return model_type.model_validate(_load_json(path))
    except ValidationError as exc:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in exc.errors(
                include_url=False,
                include_input=False,
            )
        )
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_VALIDATION_FAILED",
            "A cache calibration review asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _repeat_ascii(seed: str, byte_count: int) -> str:
    encoded = seed.encode("ascii")
    repeats = (byte_count // len(encoded)) + 2
    return (seed * repeats).encode("ascii")[:byte_count].decode("ascii")


def _provider_request(
    system_prompt: str,
    user_prompt: str,
) -> dict[str, object]:
    return {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "model": "openai/gpt-oss-20b",
        "max_completion_tokens": 32,
        "temperature": 0.0,
        "stream": False,
        "store": False,
        "reasoning_effort": "low",
    }


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _build_protected_bundle() -> dict[str, object]:
    system_prompt = _repeat_ascii(_SYSTEM_SEED, 8192)
    user_prompt = _repeat_ascii(_USER_SEED, 256)
    return {
        "schema_version": "1.0.0",
        "calibration_id": "groq-cache-telemetry-calibration-v1",
        "review_id": "groq-cache-telemetry-calibration-review-v1",
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "provider_request": _provider_request(
            system_prompt,
            user_prompt,
        ),
    }


def _protected_bundle_bytes() -> bytes:
    return (json.dumps(_build_protected_bundle(), indent=2) + "\n").encode("utf-8")


def _git_blob_sha1(
    repo_root: Path,
    commit: str,
    path: str,
) -> str:
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "rev-parse",
                f"{commit}:{path}",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_GIT_BINDING_UNAVAILABLE",
            "A frozen Git source binding could not be resolved.",
            path=path,
            details=(commit,),
        ) from exc
    return result.stdout.strip()


def _validate_source_bindings(
    repo_root: Path,
    review: CacheTelemetryCalibrationReview,
) -> None:
    for binding in review.source_bindings:
        observed = _git_blob_sha1(
            repo_root,
            review.source_commit,
            binding.path,
        )
        if observed != binding.git_blob_sha1:
            raise CalibrationReviewError(
                "CACHE_CALIBRATION_REVIEW_SOURCE_BINDING_MISMATCH",
                "A frozen calibration review source no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.git_blob_sha1}",
                    f"observed={observed}",
                ),
            )


def _validate_hardening_state(repo_root: Path) -> None:
    acceptance_raw = _load_json(repo_root / _HARDENING_ROOT / "acceptance.json")
    draft_raw = _load_json(repo_root / _HARDENING_ROOT / "calibration_draft.json")
    manifest_raw = _load_json(repo_root / _HARDENING_ROOT / "manifest.json")
    if not all(isinstance(item, dict) for item in (acceptance_raw, draft_raw, manifest_raw)):
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_SOURCE_SHAPE_INVALID",
            "Hardening source evidence must be JSON objects.",
        )

    acceptance = cast(dict[str, object], acceptance_raw)
    draft = cast(dict[str, object], draft_raw)
    manifest = cast(dict[str, object], manifest_raw)

    acceptance_expected = {
        "hardening_id": "groq-cache-telemetry-hardening-v1",
        "status": "implementation_ready",
        "provider_call_performed": False,
        "credential_accessed": False,
        "calibration_authorized": False,
        "benchmark_execution_authorized": False,
        "next_gate": "cache_telemetry_calibration_authorization_review",
    }
    acceptance_mismatches = tuple(
        f"{key}={acceptance.get(key)!r}"
        for key, expected in acceptance_expected.items()
        if acceptance.get(key) != expected
    )
    if acceptance_mismatches:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_HARDENING_STATE_MISMATCH",
            "The hardening acceptance state differs from the review.",
            details=acceptance_mismatches,
        )

    draft_expected = {
        "calibration_id": "groq-cache-telemetry-calibration-v1",
        "status": "draft_inactive",
        "maximum_provider_calls": 3,
        "retry_permitted": False,
        "resume_permitted": False,
        "provider_call_authorized": False,
        "calibration_authorized": False,
        "benchmark_execution_authorized": False,
        "next_gate": "cache_telemetry_calibration_authorization_review",
    }
    draft_mismatches = tuple(
        f"{key}={draft.get(key)!r}"
        for key, expected in draft_expected.items()
        if draft.get(key) != expected
    )
    if draft_mismatches:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_DRAFT_STATE_MISMATCH",
            "The calibration draft differs from the reviewed boundary.",
            details=draft_mismatches,
        )

    steps_raw = draft.get("steps")
    roles: list[object] = []
    if isinstance(steps_raw, list):
        for item in steps_raw:
            if isinstance(item, dict):
                roles.append(cast(dict[str, object], item).get("request_role"))
    if roles != [
        "cold",
        "warm_repeat_one",
        "warm_repeat_two",
    ]:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_DRAFT_SEQUENCE_MISMATCH",
            "The calibration draft sequence is not cold/warm/warm.",
        )

    manifest_checks = (
        ("acceptance_path", "acceptance_sha256"),
        ("calibration_draft_path", "calibration_draft_sha256"),
        ("synthetic_cases_path", "synthetic_cases_sha256"),
        ("report_path", "report_sha256"),
    )
    for path_key, hash_key in manifest_checks:
        relative_path = manifest.get(path_key)
        expected_hash = manifest.get(hash_key)
        if not isinstance(relative_path, str) or not isinstance(
            expected_hash,
            str,
        ):
            raise CalibrationReviewError(
                "CACHE_CALIBRATION_REVIEW_HARDENING_MANIFEST_INVALID",
                "The hardening manifest is missing a required binding.",
                details=(path_key, hash_key),
            )
        observed_hash = _sha256_file(repo_root / relative_path)
        if observed_hash != expected_hash:
            raise CalibrationReviewError(
                "CACHE_CALIBRATION_REVIEW_HARDENING_HASH_MISMATCH",
                "A hardening source no longer matches its manifest.",
                path=str(repo_root / relative_path),
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed_hash}",
                ),
            )


def _validate_prompt_recipe(
    recipe: CalibrationPromptRecipe,
    review: CacheTelemetryCalibrationReview,
) -> None:
    bundle = _build_protected_bundle()
    system_prompt = bundle["system_prompt"]
    user_prompt = bundle["user_prompt"]
    provider_request = bundle["provider_request"]
    assert isinstance(system_prompt, str)
    assert isinstance(user_prompt, str)

    checks = {
        "system_prompt_sha256": _sha256_bytes(system_prompt.encode("utf-8")),
        "user_prompt_sha256": _sha256_bytes(user_prompt.encode("utf-8")),
        "provider_request_sha256": _sha256_bytes(_canonical_json_bytes(provider_request)),
        "protected_bundle_sha256": _sha256_bytes(_protected_bundle_bytes()),
    }
    mismatches = tuple(
        f"{field}: expected={getattr(recipe, field)} observed={observed}"
        for field, observed in checks.items()
        if getattr(recipe, field) != observed
    )
    if mismatches:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_PROMPT_REPRODUCTION_MISMATCH",
            "The deterministic protected prompt bundle did not reproduce.",
            details=mismatches,
        )

    if review.prompt_binding.model_dump() != {
        key: value
        for key, value in recipe.model_dump().items()
        if key
        not in {
            "schema_version",
            "calibration_id",
            "content_class",
            "provider_request_repetition_count",
            "raw_prompt_committed",
            "provider_call_authorized",
        }
    }:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_PROMPT_BINDING_MISMATCH",
            "The review prompt binding differs from the public recipe.",
        )


def _build_dry_run(
    review: CacheTelemetryCalibrationReview,
) -> CalibrationDryRunReport:
    attempts = tuple(
        CalibrationDryRunAttempt(
            attempt_index=index,
            request_role=cast(
                Literal[
                    "cold",
                    "warm_repeat_one",
                    "warm_repeat_two",
                ],
                role,
            ),
            planned_offset_seconds=offset,
            provider_request_sha256=(review.prompt_binding.provider_request_sha256),
            system_prompt_sha256=(review.prompt_binding.system_prompt_sha256),
            user_prompt_sha256=(review.prompt_binding.user_prompt_sha256),
        )
        for index, (role, offset) in enumerate(
            zip(
                review.schedule.request_roles,
                review.schedule.attempt_offsets_seconds,
                strict=True,
            )
        )
    )
    return CalibrationDryRunReport(
        review_id=review.review_id,
        calibration_id=review.calibration_id,
        attempts=attempts,
    )


def _validate_public_review(
    repo_root: Path,
    review_root: Path,
) -> tuple[
    CacheTelemetryCalibrationReview,
    CalibrationPromptRecipe,
    CalibrationDryRunReport,
    CalibrationReviewManifest,
]:
    root = repo_root / review_root
    recipe_path = root / "prompt_recipe.json"
    review_path = root / "review.json"
    dry_run_path = root / "dry_run_report.json"
    manifest_path = root / "manifest.json"

    recipe = _load_model(recipe_path, CalibrationPromptRecipe)
    review = _load_model(review_path, CacheTelemetryCalibrationReview)
    dry_run = _load_model(dry_run_path, CalibrationDryRunReport)
    manifest = _load_model(manifest_path, CalibrationReviewManifest)

    checks = (
        (manifest.prompt_recipe_path, manifest.prompt_recipe_sha256),
        (manifest.review_path, manifest.review_sha256),
        (
            manifest.dry_run_report_path,
            manifest.dry_run_report_sha256,
        ),
        (manifest.report_path, manifest.report_sha256),
    )
    for relative_path, expected_hash in checks:
        observed_hash = _sha256_file(repo_root / relative_path)
        if observed_hash != expected_hash:
            raise CalibrationReviewError(
                "CACHE_CALIBRATION_REVIEW_HASH_MISMATCH",
                "A calibration review asset no longer matches.",
                path=str(repo_root / relative_path),
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed_hash}",
                ),
            )

    if manifest.protected_bundle_sha256 != (review.prompt_binding.protected_bundle_sha256):
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_PROTECTED_HASH_MISMATCH",
            "The manifest and review bind different prompt bundles.",
        )

    _validate_source_bindings(repo_root, review)
    _validate_hardening_state(repo_root)
    _validate_prompt_recipe(recipe, review)

    rebuilt = _build_dry_run(review)
    if rebuilt != dry_run:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_DRY_RUN_MISMATCH",
            "The dry-run report did not reproduce deterministically.",
            path=str(dry_run_path),
        )
    return review, recipe, dry_run, manifest


def materialize_protected_prompt_bundle(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> CalibrationReviewSummary:
    """Materialize the synthetic prompt bundle without provider access."""

    review, _, _, _ = _validate_public_review(
        repo_root,
        review_root,
    )
    path = repo_root / review.prompt_binding.protected_bundle_path
    expected = _protected_bundle_bytes()
    if path.exists() and path.read_bytes() != expected:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_PROTECTED_BUNDLE_CONFLICT",
            "An existing protected prompt bundle has different bytes.",
            path=str(path),
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(expected)
    return CalibrationReviewSummary(
        command="materialize",
        review_id=review.review_id,
        status=review.status,
        protected_bundle_verified=True,
    )


def validate_calibration_review(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> CalibrationReviewSummary:
    """Validate public review assets without credential access."""

    review, _, _, _ = _validate_public_review(
        repo_root,
        review_root,
    )
    return CalibrationReviewSummary(
        command="validate",
        review_id=review.review_id,
        status=review.status,
        protected_bundle_verified=False,
    )


def dry_run_calibration_review(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> CalibrationReviewSummary:
    """Reproduce the metadata-only three-attempt schedule."""

    review, _, _, _ = _validate_public_review(
        repo_root,
        review_root,
    )
    return CalibrationReviewSummary(
        command="dry-run",
        review_id=review.review_id,
        status=review.status,
        protected_bundle_verified=False,
    )


def verify_calibration_review(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> CalibrationReviewSummary:
    """Verify public assets and the protected prompt bundle."""

    review, _, _, _ = _validate_public_review(
        repo_root,
        review_root,
    )
    protected_path = repo_root / review.prompt_binding.protected_bundle_path
    observed_hash = _sha256_file(protected_path)
    expected_hash = review.prompt_binding.protected_bundle_sha256
    if observed_hash != expected_hash:
        raise CalibrationReviewError(
            "CACHE_CALIBRATION_REVIEW_PROTECTED_BUNDLE_MISMATCH",
            "The protected prompt bundle no longer matches the review.",
            path=str(protected_path),
            details=(
                f"expected={expected_hash}",
                f"observed={observed_hash}",
            ),
        )
    return CalibrationReviewSummary(
        command="verify",
        review_id=review.review_id,
        status=review.status,
        protected_bundle_verified=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("materialize", "validate", "dry-run", "verify"),
    )
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--review-root",
        type=Path,
        default=_DEFAULT_REVIEW_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "materialize":
            result = materialize_protected_prompt_bundle(
                repo_root,
                review_root=args.review_root,
            )
        elif args.command == "validate":
            result = validate_calibration_review(
                repo_root,
                review_root=args.review_root,
            )
        elif args.command == "dry-run":
            result = dry_run_calibration_review(
                repo_root,
                review_root=args.review_root,
            )
        else:
            result = verify_calibration_review(
                repo_root,
                review_root=args.review_root,
            )
    except CalibrationReviewError as exc:
        envelope = CalibrationReviewErrorEnvelope(
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

"""Validate the frozen cache telemetry sufficiency review."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from auragateway.contracts.cache_telemetry_review import (
    CacheTelemetryReviewManifest,
    CacheTelemetryReviewSummary,
    CacheTelemetrySufficiencyReview,
)

_DEFAULT_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-review-v1")
_CLOSEOUT_PATH = Path("data/evals/benchmark/diagnostic-closeout-v1/closeout.json")
_CLOSEOUT_MANIFEST_PATH = Path("data/evals/benchmark/diagnostic-closeout-v1/manifest.json")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class CacheTelemetryReviewError(Exception):
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


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_ASSET_MISSING",
            "A required cache telemetry review asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_ASSET_MISSING",
            "A required cache telemetry review asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_INVALID_JSON",
            "A cache telemetry review asset is not valid JSON.",
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
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_VALIDATION_FAILED",
            "A cache telemetry review asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


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
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_GIT_BINDING_UNAVAILABLE",
            "A frozen Git source binding could not be resolved.",
            path=path,
            details=(commit,),
        ) from exc
    return result.stdout.strip()


def _validate_source_bindings(
    repo_root: Path,
    review: CacheTelemetrySufficiencyReview,
) -> None:
    for binding in review.source_bindings:
        observed = _git_blob_sha1(
            repo_root,
            review.source_commit,
            binding.path,
        )
        if observed != binding.git_blob_sha1:
            raise CacheTelemetryReviewError(
                "CACHE_TELEMETRY_REVIEW_SOURCE_BINDING_MISMATCH",
                "A frozen cache telemetry review source no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.git_blob_sha1}",
                    f"observed={observed}",
                ),
            )


def _validate_closeout_evidence(repo_root: Path) -> None:
    closeout = _load_json(repo_root / _CLOSEOUT_PATH)
    manifest = _load_json(repo_root / _CLOSEOUT_MANIFEST_PATH)
    if not isinstance(closeout, dict) or not isinstance(manifest, dict):
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_CLOSEOUT_SHAPE_INVALID",
            "The diagnostic closeout evidence must be JSON objects.",
        )

    expected = {
        "closeout_id": "batch-06-diagnostic-closeout-v1",
        "status": "closed_nonreproduced",
        "authorization_consumed": True,
        "rerun_permitted": False,
        "resume_permitted": False,
        "execution_evidence_mutation_permitted": False,
        "benchmark_claims_permitted": False,
        "comparison_eligible": False,
        "next_gate": "cache_telemetry_sufficiency_review",
    }
    mismatches = tuple(
        f"{key}={closeout.get(key)!r}"
        for key, value in expected.items()
        if closeout.get(key) != value
    )
    if mismatches:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_CLOSEOUT_STATE_MISMATCH",
            "The diagnostic closeout state differs from the reviewed boundary.",
            details=mismatches,
        )

    execution_outcome = closeout.get("execution_outcome")
    cache_telemetry = closeout.get("cache_telemetry")
    if not isinstance(execution_outcome, dict) or not isinstance(
        cache_telemetry,
        dict,
    ):
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_CLOSEOUT_SECTION_MISSING",
            "Required closeout evidence sections are absent.",
        )

    outcome_expected = {
        "provider_call_count": 24,
        "successful_call_count": 24,
        "provider_error_count": 0,
    }
    outcome_mismatches = tuple(
        f"{key}={execution_outcome.get(key)!r}"
        for key, value in outcome_expected.items()
        if execution_outcome.get(key) != value
    )
    if outcome_mismatches:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_EXECUTION_OUTCOME_MISMATCH",
            "The reviewed execution outcome no longer matches.",
            details=outcome_mismatches,
        )

    cache_expected = {
        "cached_input_token_sample_count": 0,
        "total_cached_input_tokens": None,
        "cache_evidence_available": False,
        "unknown_interpreted_as_zero": False,
        "reason": "CACHE_EVIDENCE_UNAVAILABLE",
    }
    cache_mismatches = tuple(
        f"{key}={cache_telemetry.get(key)!r}"
        for key, value in cache_expected.items()
        if cache_telemetry.get(key) != value
    )
    if cache_mismatches:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_CACHE_EVIDENCE_MISMATCH",
            "The cache telemetry closeout evidence no longer matches.",
            details=cache_mismatches,
        )

    expected_closeout_sha256 = manifest.get("closeout_sha256")
    observed_closeout_sha256 = _sha256_file(repo_root / _CLOSEOUT_PATH)
    if expected_closeout_sha256 != observed_closeout_sha256:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_CLOSEOUT_HASH_MISMATCH",
            "The diagnostic closeout no longer matches its manifest.",
            path=str(repo_root / _CLOSEOUT_PATH),
            details=(
                f"expected={expected_closeout_sha256}",
                f"observed={observed_closeout_sha256}",
            ),
        )


def validate_cache_telemetry_review(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
) -> CacheTelemetryReviewSummary:
    """Validate the review without credentials or provider calls."""

    resolved_root = repo_root / review_root
    review_path = resolved_root / "review.json"
    manifest_path = resolved_root / "manifest.json"

    review = _load_model(
        review_path,
        CacheTelemetrySufficiencyReview,
    )
    manifest = _load_model(
        manifest_path,
        CacheTelemetryReviewManifest,
    )

    if manifest.review_id != review.review_id:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_ID_MISMATCH",
            "The review and manifest identify different reviews.",
        )
    if _sha256_file(review_path) != manifest.review_sha256:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_HASH_MISMATCH",
            "The cache telemetry review no longer matches its manifest.",
            path=str(review_path),
        )
    report_path = repo_root / manifest.report_path
    if _sha256_file(report_path) != manifest.report_sha256:
        raise CacheTelemetryReviewError(
            "CACHE_TELEMETRY_REVIEW_REPORT_HASH_MISMATCH",
            "The cache telemetry report no longer matches its manifest.",
            path=str(report_path),
        )

    _validate_source_bindings(repo_root, review)
    _validate_closeout_evidence(repo_root)

    return CacheTelemetryReviewSummary(
        review_id=review.review_id,
        status=review.status,
        next_gate=review.next_gate,
    )


def _error_envelope(exc: CacheTelemetryReviewError) -> str:
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("validate",),
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
        result = validate_cache_telemetry_review(
            args.repo_root.resolve(),
            review_root=args.review_root,
        )
    except CacheTelemetryReviewError as exc:
        print(_error_envelope(exc), file=sys.stderr)
        return 1

    print(result.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

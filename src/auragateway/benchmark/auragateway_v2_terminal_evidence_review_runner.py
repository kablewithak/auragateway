"""Validate the immutable AuraGateway v2 terminal evidence review."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.auragateway_v2_terminal_evidence_review import (
    AuraGatewayV2TerminalEvidenceReview,
    AuraGatewayV2TerminalEvidenceReviewManifest,
    AuraGatewayV2TerminalEvidenceReviewSummary,
)
from auragateway.contracts.groq_cache_telemetry_reauthorization_closeout import (
    GroqCacheTelemetryReauthorizationCloseout,
)
from auragateway.contracts.groq_cache_telemetry_reauthorization_execution import (
    ReauthorizationExecutionReport,
)
from auragateway.contracts.groq_sdk_cache_schema_compatibility import (
    GroqSdkCacheSchemaCompatibilityReview,
)

_DEFAULT_REVIEW_ROOT = Path("data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1")
_DEFAULT_EXECUTION_ROOT = Path("data/evals/benchmark/groq-cache-telemetry-reauthorization-v1")
_DEFAULT_CLOSEOUT_ROOT = Path(
    "data/evals/benchmark/groq-cache-telemetry-reauthorization-closeout-v1"
)
_DEFAULT_SDK_REVIEW_ROOT = Path("data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class TerminalEvidenceReviewError(Exception):
    """Expected metadata-safe terminal review validation failure."""

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


class TerminalEvidenceReviewErrorEnvelope(BaseModel):
    """Metadata-safe CLI error envelope."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _sha256_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as exc:
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_ASSET_MISSING",
            "A required terminal review asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_ASSET_MISSING",
            "A required terminal review asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_INVALID_JSON",
            "A terminal review asset is not valid JSON.",
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
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_VALIDATION_FAILED",
            "A terminal review asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _validate_source_bindings(
    repo_root: Path,
    review: AuraGatewayV2TerminalEvidenceReview,
) -> None:
    for binding in review.source_bindings:
        observed = _sha256_file(repo_root / binding.path)
        if observed != binding.sha256:
            raise TerminalEvidenceReviewError(
                "AURAGATEWAY_TERMINAL_REVIEW_BINDING_MISMATCH",
                "A bound terminal evidence asset no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.sha256}",
                    f"observed={observed}",
                ),
            )


def _validate_sdk_boundary(repo_root: Path, sdk_review_root: Path) -> None:
    review = _load_model(
        repo_root / sdk_review_root / "review.json",
        GroqSdkCacheSchemaCompatibilityReview,
    )
    if (
        review.status.value != "closed_provider_omission_supported"
        or review.installed_sdk_version != "1.5.0"
        or review.sdk_upgrade_required
        or review.adapter_change_required
        or review.provider_call_authorized
    ):
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_SDK_BOUNDARY_MISMATCH",
            "The SDK compatibility conclusion no longer matches the terminal review.",
        )


def _validate_execution_boundary(repo_root: Path, execution_root: Path) -> None:
    report = _load_model(
        repo_root / execution_root / "report.json",
        ReauthorizationExecutionReport,
    )
    if (
        report.status.value != "completed"
        or report.outcome.value != "wire_field_absent"
        or report.provider_call_count != 2
        or report.successful_call_count != 2
        or report.provider_error_count != 0
        or report.observation_invalid_count != 0
        or report.raw_numeric_sample_count != 0
        or report.parsed_numeric_sample_count != 0
        or report.raw_absent_sample_count != 2
        or not report.authorization_consumed
        or report.rerun_permitted
        or report.resume_permitted
        or report.benchmark_execution_permitted
        or report.benchmark_claims_permitted
        or report.comparison_eligible
    ):
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_EXECUTION_MISMATCH",
            "The raw-wire execution conclusion no longer matches the terminal review.",
        )


def _validate_closeout_boundary(repo_root: Path, closeout_root: Path) -> None:
    closeout = _load_model(
        repo_root / closeout_root / "closeout.json",
        GroqCacheTelemetryReauthorizationCloseout,
    )
    if (
        closeout.status.value != "closed_provider_wire_field_unavailable"
        or closeout.gate_4_resolution.gate_4_passed
        or not closeout.gate_4_resolution.negative_result_accepted
        or closeout.gate_4_resolution.required_provider_cache_evidence_available
        or closeout.provider_calls_permitted
        or closeout.rerun_permitted
        or closeout.resume_permitted
        or closeout.benchmark_execution_permitted
        or closeout.benchmark_claims_permitted
        or closeout.comparison_eligible
    ):
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_CLOSEOUT_MISMATCH",
            "The raw-wire closeout no longer matches the terminal review.",
        )


def _validate_manifest_assets(
    repo_root: Path,
    review_root: Path,
    manifest: AuraGatewayV2TerminalEvidenceReviewManifest,
) -> None:
    expected = {
        manifest.review_path: manifest.review_sha256,
        manifest.report_path: manifest.report_sha256,
        manifest.adr_path: manifest.adr_sha256,
        manifest.prd_path: manifest.prd_sha256,
        manifest.session_brief_path: manifest.session_brief_sha256,
        manifest.readme_path: manifest.readme_sha256,
        manifest.publication_prd_path: manifest.publication_prd_sha256,
    }
    for relative_path, expected_hash in expected.items():
        observed = _sha256_file(repo_root / relative_path)
        if observed != expected_hash:
            raise TerminalEvidenceReviewError(
                "AURAGATEWAY_TERMINAL_REVIEW_HASH_MISMATCH",
                "A terminal review or governing document no longer matches its manifest.",
                path=relative_path,
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed}",
                ),
            )

    if repo_root / review_root / "manifest.json" != repo_root / (
        "data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1/manifest.json"
    ):
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_ROOT_MISMATCH",
            "The terminal review root does not match the frozen manifest path.",
        )


def validate_terminal_evidence_review(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
    execution_root: Path = _DEFAULT_EXECUTION_ROOT,
    closeout_root: Path = _DEFAULT_CLOSEOUT_ROOT,
    sdk_review_root: Path = _DEFAULT_SDK_REVIEW_ROOT,
) -> AuraGatewayV2TerminalEvidenceReviewSummary:
    """Validate terminal review, source lineage, and governing-document hashes."""

    root = repo_root / review_root
    review = _load_model(
        root / "review.json",
        AuraGatewayV2TerminalEvidenceReview,
    )
    manifest = _load_model(
        root / "manifest.json",
        AuraGatewayV2TerminalEvidenceReviewManifest,
    )

    if manifest.source_commit != review.source_commit:
        raise TerminalEvidenceReviewError(
            "AURAGATEWAY_TERMINAL_REVIEW_SOURCE_COMMIT_MISMATCH",
            "The terminal review and manifest source commits do not match.",
        )

    _validate_source_bindings(repo_root, review)
    _validate_sdk_boundary(repo_root, sdk_review_root)
    _validate_execution_boundary(repo_root, execution_root)
    _validate_closeout_boundary(repo_root, closeout_root)
    _validate_manifest_assets(repo_root, review_root, manifest)

    return AuraGatewayV2TerminalEvidenceReviewSummary(
        review_id=review.review_id,
        status=review.status,
        next_phase=review.next_phase,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--review-root",
        type=Path,
        default=_DEFAULT_REVIEW_ROOT,
    )
    parser.add_argument(
        "--execution-root",
        type=Path,
        default=_DEFAULT_EXECUTION_ROOT,
    )
    parser.add_argument(
        "--closeout-root",
        type=Path,
        default=_DEFAULT_CLOSEOUT_ROOT,
    )
    parser.add_argument(
        "--sdk-review-root",
        type=Path,
        default=_DEFAULT_SDK_REVIEW_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = validate_terminal_evidence_review(
            args.repo_root.resolve(),
            review_root=args.review_root,
            execution_root=args.execution_root,
            closeout_root=args.closeout_root,
            sdk_review_root=args.sdk_review_root,
        )
    except TerminalEvidenceReviewError as exc:
        envelope = TerminalEvidenceReviewErrorEnvelope(
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

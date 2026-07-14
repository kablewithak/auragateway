"""Validate the non-live OpenRouter Hy3 identifiability review."""

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
    OpenRouterHy3TerminalEvidenceReviewManifest,
)
from auragateway.contracts.openrouter_hy3_identifiability import (
    OpenRouterHy3IdentifiabilityManifest,
    OpenRouterHy3IdentifiabilityReview,
    OpenRouterHy3IdentifiabilitySummary,
)
from auragateway.contracts.openrouter_hy3_review_supersession import (
    OpenRouterHy3HistoricalReviewSupersession,
    OpenRouterHy3SupersessionScope,
    superseding_hash,
)

_DEFAULT_REVIEW_ROOT = Path(
    "data/evals/benchmark/openrouter-hy3-identifiability-review-v1"
)
_DEFAULT_TERMINAL_REVIEW_ROOT = Path(
    "data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1"
)
_DEFAULT_SUPERSESSION_ROOT = Path(
    "data/evals/benchmark/openrouter-hy3-historical-review-supersession-v1"
)
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class OpenRouterHy3IdentifiabilityError(Exception):
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


class OpenRouterHy3IdentifiabilityErrorEnvelope(BaseModel):
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
        raise OpenRouterHy3IdentifiabilityError(
            "OPENROUTER_HY3_REVIEW_ASSET_MISSING",
            "A required OpenRouter Hy3 review asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OpenRouterHy3IdentifiabilityError(
            "OPENROUTER_HY3_REVIEW_ASSET_MISSING",
            "A required OpenRouter Hy3 review asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise OpenRouterHy3IdentifiabilityError(
            "OPENROUTER_HY3_REVIEW_INVALID_JSON",
            "An OpenRouter Hy3 review asset is not valid JSON.",
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
        raise OpenRouterHy3IdentifiabilityError(
            "OPENROUTER_HY3_REVIEW_VALIDATION_FAILED",
            "An OpenRouter Hy3 review asset failed typed validation.",
            path=str(path),
            details=details,
        ) from exc


def _load_supersession(
    repo_root: Path,
    supersession_root: Path,
) -> tuple[
    OpenRouterHy3HistoricalReviewSupersession,
    OpenRouterHy3TerminalEvidenceReviewManifest,
]:
    supersession = _load_model(
        repo_root / supersession_root / "supersession.json",
        OpenRouterHy3HistoricalReviewSupersession,
    )
    historical_assets = {
        supersession.identifiability_review_path: supersession.identifiability_review_sha256,
        supersession.identifiability_manifest_path: (
            supersession.identifiability_manifest_sha256
        ),
        supersession.superseding_manifest_path: supersession.superseding_manifest_sha256,
    }
    for relative_path, expected_hash in historical_assets.items():
        observed = _sha256_file(repo_root / relative_path)
        if observed != expected_hash:
            raise OpenRouterHy3IdentifiabilityError(
                "OPENROUTER_HY3_REVIEW_SUPERSESSION_LINEAGE_MISMATCH",
                "A historical or superseding review asset no longer matches its supersession.",
                path=relative_path,
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed}",
                ),
            )
    superseding_manifest = _load_model(
        repo_root / supersession.superseding_manifest_path,
        OpenRouterHy3TerminalEvidenceReviewManifest,
    )
    return supersession, superseding_manifest


def _delegated_hash(
    *,
    supersession: OpenRouterHy3HistoricalReviewSupersession,
    superseding_manifest: OpenRouterHy3TerminalEvidenceReviewManifest,
    scope: OpenRouterHy3SupersessionScope,
    path: str,
    historical_hash: str,
) -> str | None:
    for binding in supersession.bindings:
        if binding.scope is scope and binding.path.value == path:
            if binding.historical_sha256 != historical_hash:
                raise OpenRouterHy3IdentifiabilityError(
                    "OPENROUTER_HY3_REVIEW_SUPERSESSION_HISTORICAL_HASH_MISMATCH",
                    "A delegated historical hash no longer matches the frozen review.",
                    path=path,
                )
            return superseding_hash(
                superseding_manifest,
                binding.superseding_hash_field,
            )
    return None


def _validate_source_bindings(
    repo_root: Path,
    review: OpenRouterHy3IdentifiabilityReview,
    supersession: OpenRouterHy3HistoricalReviewSupersession,
    superseding_manifest: OpenRouterHy3TerminalEvidenceReviewManifest,
) -> None:
    for binding in review.source_bindings:
        expected = _delegated_hash(
            supersession=supersession,
            superseding_manifest=superseding_manifest,
            scope=OpenRouterHy3SupersessionScope.IDENTIFIABILITY_REVIEW_SOURCE,
            path=binding.path,
            historical_hash=binding.sha256,
        )
        if expected is None:
            expected = binding.sha256
        observed = _sha256_file(repo_root / binding.path)
        if observed != expected:
            raise OpenRouterHy3IdentifiabilityError(
                "OPENROUTER_HY3_REVIEW_BINDING_MISMATCH",
                "A bound OpenRouter Hy3 review source no longer matches.",
                path=binding.path,
                details=(
                    f"expected={expected}",
                    f"observed={observed}",
                ),
            )


def _validate_terminal_core_boundary(
    repo_root: Path,
    terminal_review_root: Path,
) -> None:
    terminal_review = _load_model(
        repo_root / terminal_review_root / "review.json",
        AuraGatewayV2TerminalEvidenceReview,
    )
    if (
        not terminal_review.core_scope_closed
        or terminal_review.gate_4_resolution.gate_4_passed_for_measured_benchmark
        or terminal_review.gate_4_resolution.benchmark_execution_permitted
        or terminal_review.gate_4_resolution.comparison_eligible
        or terminal_review.additional_provider_execution_permitted
    ):
        raise OpenRouterHy3IdentifiabilityError(
            "OPENROUTER_HY3_REVIEW_CORE_BOUNDARY_MISMATCH",
            "The closed AuraGateway v2 core boundary no longer matches the extension review.",
        )


def _validate_manifest_assets(
    repo_root: Path,
    manifest: OpenRouterHy3IdentifiabilityManifest,
    supersession: OpenRouterHy3HistoricalReviewSupersession,
    superseding_manifest: OpenRouterHy3TerminalEvidenceReviewManifest,
) -> None:
    expected = {
        manifest.review_path: manifest.review_sha256,
        manifest.adr_path: manifest.adr_sha256,
        manifest.report_path: manifest.report_sha256,
        manifest.mini_prd_path: manifest.mini_prd_sha256,
    }
    for relative_path, historical_hash in expected.items():
        delegated = _delegated_hash(
            supersession=supersession,
            superseding_manifest=superseding_manifest,
            scope=OpenRouterHy3SupersessionScope.IDENTIFIABILITY_MANIFEST_ASSET,
            path=relative_path,
            historical_hash=historical_hash,
        )
        expected_hash = historical_hash if delegated is None else delegated
        observed = _sha256_file(repo_root / relative_path)
        if observed != expected_hash:
            raise OpenRouterHy3IdentifiabilityError(
                "OPENROUTER_HY3_REVIEW_HASH_MISMATCH",
                "An OpenRouter Hy3 review artifact no longer matches its manifest.",
                path=relative_path,
                details=(
                    f"expected={expected_hash}",
                    f"observed={observed}",
                ),
            )


def validate_openrouter_hy3_identifiability(
    repo_root: Path,
    *,
    review_root: Path = _DEFAULT_REVIEW_ROOT,
    terminal_review_root: Path = _DEFAULT_TERMINAL_REVIEW_ROOT,
    supersession_root: Path = _DEFAULT_SUPERSESSION_ROOT,
) -> OpenRouterHy3IdentifiabilitySummary:
    """Validate source lineage, frozen controls, and non-live claim boundaries."""

    root = repo_root / review_root
    review = _load_model(
        root / "review.json",
        OpenRouterHy3IdentifiabilityReview,
    )
    manifest = _load_model(
        root / "manifest.json",
        OpenRouterHy3IdentifiabilityManifest,
    )
    if manifest.source_commit != review.source_commit:
        raise OpenRouterHy3IdentifiabilityError(
            "OPENROUTER_HY3_REVIEW_SOURCE_COMMIT_MISMATCH",
            "The review and manifest source commits do not match.",
        )

    supersession, superseding_manifest = _load_supersession(
        repo_root,
        supersession_root,
    )
    _validate_source_bindings(
        repo_root,
        review,
        supersession,
        superseding_manifest,
    )
    _validate_terminal_core_boundary(repo_root, terminal_review_root)
    _validate_manifest_assets(
        repo_root,
        manifest,
        supersession,
        superseding_manifest,
    )

    return OpenRouterHy3IdentifiabilitySummary(
        review_id=review.review_id,
        status=review.status,
        next_gate=review.next_gate,
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
        "--terminal-review-root",
        type=Path,
        default=_DEFAULT_TERMINAL_REVIEW_ROOT,
    )
    parser.add_argument(
        "--supersession-root",
        type=Path,
        default=_DEFAULT_SUPERSESSION_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = validate_openrouter_hy3_identifiability(
            args.repo_root.resolve(),
            review_root=args.review_root,
            terminal_review_root=args.terminal_review_root,
            supersession_root=args.supersession_root,
        )
    except OpenRouterHy3IdentifiabilityError as exc:
        envelope = OpenRouterHy3IdentifiabilityErrorEnvelope(
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

"""Validate non-live Groq cache telemetry capture hardening evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.contracts.cache_telemetry_capture import (
    CacheMeasurementClaimKind,
    CacheTelemetryCalibrationDraft,
    CacheTelemetryHardeningAcceptance,
    CacheTelemetryHardeningManifest,
    CacheTelemetryHardeningSummary,
    CacheTelemetrySyntheticCaseSet,
)
from auragateway.telemetry.cache_capture_sufficiency import (
    assess_groq_cache_telemetry_sufficiency,
)

_DEFAULT_ROOT = Path("data/evals/benchmark/cache-telemetry-hardening-v1")
_ModelT = TypeVar("_ModelT", bound=BaseModel)


class CacheTelemetryHardeningError(Exception):
    """Expected metadata-safe hardening validation failure."""

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


class CacheTelemetryHardeningErrorEnvelope(BaseModel):
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
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_ASSET_MISSING",
            "A required cache telemetry hardening asset was not found.",
            path=str(path),
        ) from exc


def _load_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_ASSET_MISSING",
            "A required cache telemetry hardening asset was not found.",
            path=str(path),
        ) from exc
    except json.JSONDecodeError as exc:
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_INVALID_JSON",
            "A cache telemetry hardening asset is not valid JSON.",
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
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_VALIDATION_FAILED",
            "A cache telemetry hardening asset failed typed validation.",
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
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_SOURCE_BINDING_UNAVAILABLE",
            "A frozen cache telemetry review source could not be resolved.",
            path=path,
            details=(commit,),
        ) from exc
    return result.stdout.strip()


def _validate_source_bindings(
    repo_root: Path,
    acceptance: CacheTelemetryHardeningAcceptance,
) -> None:
    for binding in acceptance.source_bindings:
        observed = _git_blob_sha1(
            repo_root,
            acceptance.source_commit,
            binding.path,
        )
        if observed != binding.git_blob_sha1:
            raise CacheTelemetryHardeningError(
                "CACHE_TELEMETRY_HARDENING_SOURCE_BINDING_MISMATCH",
                "A frozen cache telemetry review source no longer matches.",
                path=binding.path,
                details=(
                    f"expected={binding.git_blob_sha1}",
                    f"observed={observed}",
                ),
            )


def _validate_manifest_hashes(
    repo_root: Path,
    manifest: CacheTelemetryHardeningManifest,
) -> None:
    checks = (
        (manifest.acceptance_path, manifest.acceptance_sha256),
        (
            manifest.calibration_draft_path,
            manifest.calibration_draft_sha256,
        ),
        (
            manifest.synthetic_cases_path,
            manifest.synthetic_cases_sha256,
        ),
        (manifest.report_path, manifest.report_sha256),
    )
    for relative_path, expected in checks:
        path = repo_root / relative_path
        observed = _sha256_file(path)
        if observed != expected:
            raise CacheTelemetryHardeningError(
                "CACHE_TELEMETRY_HARDENING_HASH_MISMATCH",
                "A cache telemetry hardening asset no longer matches.",
                path=str(path),
                details=(
                    f"expected={expected}",
                    f"observed={observed}",
                ),
            )


def _validate_synthetic_cases(
    cases: CacheTelemetrySyntheticCaseSet,
) -> None:
    failures: list[str] = []
    for case in cases.cases:
        report = assess_groq_cache_telemetry_sufficiency(
            case.capture,
            case.telemetry,
            pricing_evidence_available=case.pricing_evidence_available,
        )
        usage = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_USAGE)
        savings = report.decision_for(CacheMeasurementClaimKind.PROVIDER_CACHE_SAVINGS)
        if (
            usage.decision is not case.expected_usage_decision
            or usage.reason_code is not case.expected_usage_reason
            or savings.decision is not case.expected_savings_decision
            or savings.reason_code is not case.expected_savings_reason
        ):
            failures.append(case.case_id)

    if failures:
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_CASE_MISMATCH",
            "Synthetic cache telemetry cases did not match expectations.",
            details=tuple(failures),
        )


def validate_cache_telemetry_hardening(
    repo_root: Path,
    *,
    hardening_root: Path = _DEFAULT_ROOT,
) -> CacheTelemetryHardeningSummary:
    """Validate the hardening slice without credentials or provider calls."""

    root = repo_root / hardening_root
    acceptance = _load_model(
        root / "acceptance.json",
        CacheTelemetryHardeningAcceptance,
    )
    draft = _load_model(
        root / "calibration_draft.json",
        CacheTelemetryCalibrationDraft,
    )
    cases = _load_model(
        root / "synthetic_cases.json",
        CacheTelemetrySyntheticCaseSet,
    )
    manifest = _load_model(
        root / "manifest.json",
        CacheTelemetryHardeningManifest,
    )

    if manifest.hardening_id != acceptance.hardening_id:
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_HARDENING_ID_MISMATCH",
            "The acceptance record and manifest identify different hardening.",
        )
    if draft.provider_call_authorized or draft.calibration_authorized:
        raise CacheTelemetryHardeningError(
            "CACHE_TELEMETRY_CALIBRATION_UNEXPECTEDLY_ACTIVE",
            "The prepared calibration draft must remain inactive.",
        )

    _validate_source_bindings(repo_root, acceptance)
    _validate_manifest_hashes(repo_root, manifest)
    _validate_synthetic_cases(cases)

    return CacheTelemetryHardeningSummary(
        hardening_id=acceptance.hardening_id,
        status=acceptance.status,
        synthetic_case_count=len(cases.cases),
        synthetic_cases_passed=True,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("validate",))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--hardening-root",
        type=Path,
        default=_DEFAULT_ROOT,
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        result = validate_cache_telemetry_hardening(
            args.repo_root.resolve(),
            hardening_root=args.hardening_root,
        )
    except CacheTelemetryHardeningError as exc:
        envelope = CacheTelemetryHardeningErrorEnvelope(
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

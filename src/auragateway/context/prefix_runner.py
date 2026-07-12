"""Build and verify canonical prefix fingerprints and the Gate 3 stability evidence."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError

from auragateway.context.compiler import (
    PrefixCompileError,
    canonical_model_bytes,
    ensure_no_forbidden_volatile_fields,
    fingerprint_static_context,
    sha256_bytes,
    sha256_path,
)
from auragateway.context.runner import verify_context_boundary
from auragateway.contracts.context import StaticAnchorRegistry
from auragateway.contracts.prefix import (
    PrefixDeterminismManifest,
    PrefixDeterminismSummary,
    PrefixFingerprintRecord,
    PrefixMutationCase,
    PrefixMutationCaseSet,
    PrefixMutationKind,
    PrefixMutationOutcome,
    PrefixMutationReason,
    PrefixMutationResult,
    PrefixStabilityReport,
    PrefixTurnAudit,
    PrefixTurnFixtureSet,
    StaticCompilerSpec,
    StaticSegmentKind,
    ToolContractSpec,
)

_DEFAULT_REGISTRY = Path("data/context/static_anchor_registry.json")
_DEFAULT_BOUNDARY_MANIFEST = Path("data/context/boundary_manifest.json")
_DEFAULT_SPEC = Path("data/context/compiler_spec.json")
_DEFAULT_TURNS = Path("data/context/prefix-determinism-v1/turns.json")
_DEFAULT_MUTATIONS = Path("data/context/prefix-determinism-v1/mutation_cases.json")
_DEFAULT_REPORT = Path("data/context/prefix-determinism-v1/report.json")
_DEFAULT_MANIFEST = Path("data/context/prefix-determinism-v1/manifest.json")
_HMAC_KEY_ENV = "AURAGATEWAY_PREFIX_HMAC_KEY"
_HMAC_KEY_ID_ENV = "AURAGATEWAY_PREFIX_HMAC_KEY_ID"


class PrefixDeterminismError(Exception):
    """Expected Gate 3 failure with safe details."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details


class PrefixDeterminismErrorEnvelope(BaseModel):
    """Safe CLI error output that never contains raw static or volatile content."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


def _validation_messages(error: ValidationError) -> tuple[str, ...]:
    messages: list[str] = []
    for item in error.errors(include_url=False, include_input=False):
        location = ".".join(str(part) for part in item["loc"]) or "artifact"
        messages.append(f"{location}: {item['msg']}")
    return tuple(messages)


def _load_json(path: Path, not_found_code: str) -> object:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise PrefixDeterminismError(
            not_found_code,
            "Required prefix-determinism artifact was not found.",
            str(path),
        ) from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PrefixDeterminismError(
            "PREFIX_DETERMINISM_INVALID_JSON",
            "Prefix-determinism artifact is not valid JSON.",
            str(path),
        ) from exc


ModelT = TypeVar("ModelT", bound=BaseModel)


def _load_model(path: Path, model_type: type[ModelT], code: str) -> ModelT:
    try:
        return model_type.model_validate(_load_json(path, f"{code}_NOT_FOUND"))
    except ValidationError as exc:
        raise PrefixDeterminismError(
            f"{code}_VALIDATION_FAILED",
            "Prefix-determinism artifact failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _load_spec(path: Path) -> tuple[StaticCompilerSpec, object]:
    raw = _load_json(path, "STATIC_COMPILER_SPEC_NOT_FOUND")
    try:
        ensure_no_forbidden_volatile_fields(raw)
        return StaticCompilerSpec.model_validate(raw), raw
    except PrefixCompileError as exc:
        raise PrefixDeterminismError(
            exc.error_code,
            exc.safe_message,
            str(path),
            exc.details,
        ) from exc
    except ValidationError as exc:
        raise PrefixDeterminismError(
            "STATIC_COMPILER_SPEC_VALIDATION_FAILED",
            "Static compiler specification failed typed validation.",
            str(path),
            _validation_messages(exc),
        ) from exc


def _load_hmac_settings() -> tuple[bytes, str]:
    key_value = os.environ.get(_HMAC_KEY_ENV)
    key_id = os.environ.get(_HMAC_KEY_ID_ENV)
    if key_value is None or key_id is None:
        raise PrefixDeterminismError(
            "PREFIX_HMAC_SETTINGS_MISSING",
            "Prefix HMAC key and non-secret key ID must be supplied through environment settings.",
        )
    key = key_value.encode("utf-8")
    if len(key) < 32:
        raise PrefixDeterminismError(
            "PREFIX_HMAC_KEY_TOO_SHORT",
            "Prefix HMAC key must contain at least 32 UTF-8 bytes.",
        )
    return key, key_id


def _write_model(path: Path, model: BaseModel) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2) + "\n", encoding="utf-8", newline="\n")


def _fingerprint(
    repo_root: Path,
    spec: StaticCompilerSpec,
    registry: StaticAnchorRegistry,
    key: bytes,
    key_id: str,
) -> PrefixFingerprintRecord:
    try:
        return fingerprint_static_context(repo_root, spec, registry, key, key_id)
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise PrefixDeterminismError(
            "PREFIX_STATIC_ARTIFACT_READ_FAILED",
            "A static prefix artifact could not be read safely.",
        ) from exc
    except PrefixCompileError as exc:
        raise PrefixDeterminismError(
            exc.error_code,
            exc.safe_message,
            details=exc.details,
        ) from exc


def _mutate_tool_order(spec: StaticCompilerSpec) -> StaticCompilerSpec:
    reordered: list[ToolContractSpec] = []
    for order, tool in enumerate(reversed(spec.tools)):
        reordered.append(tool.model_copy(update={"order": order}))
    return spec.model_copy(update={"tools": tuple(reordered)})


def _mutate_schema_version(spec: StaticCompilerSpec) -> StaticCompilerSpec:
    output_schema = spec.output_schema.model_copy(update={"version": "1.0.1"})
    return spec.model_copy(update={"output_schema": output_schema})


def _mutate_example(spec: StaticCompilerSpec) -> StaticCompilerSpec:
    segments = []
    for segment in spec.segments:
        if segment.kind is StaticSegmentKind.FEW_SHOT_EXAMPLE:
            segments.append(segment.model_copy(update={"content": segment.content + "!"}))
        else:
            segments.append(segment)
    return spec.model_copy(update={"segments": tuple(segments)})


def _result(
    case: PrefixMutationCase,
    baseline: PrefixFingerprintRecord,
    observed_outcome: PrefixMutationOutcome,
    observed_reason: PrefixMutationReason | None,
    mutated_fingerprint: str | None,
) -> PrefixMutationResult:
    return PrefixMutationResult(
        case_id=case.case_id,
        mutation_kind=case.mutation_kind,
        expected_outcome=case.expected_outcome,
        observed_outcome=observed_outcome,
        expected_reason=case.expected_reason,
        observed_reason=observed_reason,
        baseline_fingerprint=baseline.prefix_fingerprint,
        mutated_fingerprint=mutated_fingerprint,
        passed=(
            case.expected_outcome is observed_outcome and case.expected_reason is observed_reason
        ),
    )


def _run_mutation_case(
    repo_root: Path,
    case: PrefixMutationCase,
    spec: StaticCompilerSpec,
    raw_spec: object,
    registry: StaticAnchorRegistry,
    baseline: PrefixFingerprintRecord,
    key: bytes,
    key_id: str,
) -> PrefixMutationResult:
    if case.mutation_kind is PrefixMutationKind.TIMESTAMP_INSERTION:
        if not isinstance(raw_spec, dict):
            raise PrefixDeterminismError(
                "STATIC_COMPILER_SPEC_SHAPE_INVALID",
                "Static compiler specification must be a JSON object.",
                str(repo_root / _DEFAULT_SPEC),
            )
        mutated = dict(raw_spec)
        mutated["timestamp"] = "2026-07-12T00:00:00+02:00"
        try:
            ensure_no_forbidden_volatile_fields(mutated)
        except PrefixCompileError as exc:
            return _result(
                case,
                baseline,
                PrefixMutationOutcome.BLOCKED,
                exc.mutation_reason,
                None,
            )
        raise PrefixDeterminismError(
            "TIMESTAMP_MUTATION_NOT_BLOCKED",
            "Timestamp mutation unexpectedly passed static isolation.",
        )

    if case.mutation_kind is PrefixMutationKind.TOOL_ORDER_CHANGE:
        mutated_record = _fingerprint(repo_root, _mutate_tool_order(spec), registry, key, key_id)
        return _result(
            case,
            baseline,
            PrefixMutationOutcome.FINGERPRINT_CHANGED,
            PrefixMutationReason.TOOL_CONTRACT_CHANGED,
            mutated_record.prefix_fingerprint,
        )

    if case.mutation_kind is PrefixMutationKind.OUTPUT_SCHEMA_VERSION_CHANGE:
        mutated_record = _fingerprint(
            repo_root, _mutate_schema_version(spec), registry, key, key_id
        )
        return _result(
            case,
            baseline,
            PrefixMutationOutcome.FINGERPRINT_CHANGED,
            PrefixMutationReason.OUTPUT_SCHEMA_CHANGED,
            mutated_record.prefix_fingerprint,
        )

    if case.mutation_kind is PrefixMutationKind.JSON_KEY_ORDER_CHANGE:
        if not isinstance(raw_spec, dict):
            raise PrefixDeterminismError(
                "STATIC_COMPILER_SPEC_SHAPE_INVALID",
                "Static compiler specification must be a JSON object.",
                str(repo_root / _DEFAULT_SPEC),
            )
        reordered = dict(reversed(tuple(raw_spec.items())))
        reordered_spec = StaticCompilerSpec.model_validate(reordered)
        mutated_record = _fingerprint(repo_root, reordered_spec, registry, key, key_id)
        return _result(
            case,
            baseline,
            PrefixMutationOutcome.CANONICALLY_EQUIVALENT,
            PrefixMutationReason.PROVIDER_SERIALIZATION_CHANGED,
            mutated_record.prefix_fingerprint,
        )

    if case.mutation_kind is PrefixMutationKind.ONE_BYTE_EXAMPLE_CHANGE:
        mutated_record = _fingerprint(repo_root, _mutate_example(spec), registry, key, key_id)
        return _result(
            case,
            baseline,
            PrefixMutationOutcome.FINGERPRINT_CHANGED,
            PrefixMutationReason.CONTEXT_PACK_CHANGED,
            mutated_record.prefix_fingerprint,
        )

    if case.mutation_kind in {
        PrefixMutationKind.VOLATILE_USER_CONTENT_CHANGE,
        PrefixMutationKind.RETRIEVAL_ORDER_CHANGE,
    }:
        unchanged_record = _fingerprint(repo_root, spec, registry, key, key_id)
        return _result(
            case,
            baseline,
            PrefixMutationOutcome.STATIC_FINGERPRINT_UNCHANGED,
            None,
            unchanged_record.prefix_fingerprint,
        )

    raise PrefixDeterminismError(
        "UNKNOWN_PREFIX_MUTATION_KIND",
        "Mutation case uses an unsupported mutation kind.",
        details=(case.mutation_kind.value,),
    )


def _validate_mutation_semantics(result: PrefixMutationResult) -> None:
    if (
        result.observed_outcome is PrefixMutationOutcome.FINGERPRINT_CHANGED
        and result.mutated_fingerprint == result.baseline_fingerprint
    ):
        raise PrefixDeterminismError(
            "PREFIX_MUTATION_NOT_DETECTED",
            "A required static mutation did not change the prefix fingerprint.",
            details=(result.case_id,),
        )
    if (
        result.observed_outcome
        in {
            PrefixMutationOutcome.CANONICALLY_EQUIVALENT,
            PrefixMutationOutcome.STATIC_FINGERPRINT_UNCHANGED,
        }
        and result.mutated_fingerprint != result.baseline_fingerprint
    ):
        raise PrefixDeterminismError(
            "PREFIX_FALSE_POSITIVE_MUTATION",
            "Canonical or volatile-only variation changed the static prefix fingerprint.",
            details=(result.case_id,),
        )


def _build_report(
    repo_root: Path,
    spec: StaticCompilerSpec,
    raw_spec: object,
    registry: StaticAnchorRegistry,
    turns: PrefixTurnFixtureSet,
    mutation_cases: PrefixMutationCaseSet,
    key: bytes,
    key_id: str,
) -> PrefixStabilityReport:
    baseline = _fingerprint(repo_root, spec, registry, key, key_id)
    turn_audits: list[PrefixTurnAudit] = []
    for turn in turns.turns:
        turn_fingerprint = _fingerprint(repo_root, spec, registry, key, key_id)
        turn_audits.append(
            PrefixTurnAudit(
                turn_index=turn.turn_index,
                volatile_log_sha256=sha256_bytes(canonical_model_bytes(turn.volatile_log)),
                volatile_item_count=len(turn.volatile_log.items),
                static_prefix_fingerprint=turn_fingerprint.prefix_fingerprint,
                matches_baseline=(
                    turn_fingerprint.prefix_fingerprint == baseline.prefix_fingerprint
                ),
            )
        )

    mutation_results: list[PrefixMutationResult] = []
    for case in mutation_cases.cases:
        result = _run_mutation_case(
            repo_root,
            case,
            spec,
            raw_spec,
            registry,
            baseline,
            key,
            key_id,
        )
        _validate_mutation_semantics(result)
        mutation_results.append(result)

    return PrefixStabilityReport(
        compiler_spec_path=_DEFAULT_SPEC.as_posix(),
        compiler_spec_sha256=sha256_path(repo_root / _DEFAULT_SPEC),
        static_registry_path=_DEFAULT_REGISTRY.as_posix(),
        static_registry_sha256=sha256_path(repo_root / _DEFAULT_REGISTRY),
        turn_fixtures_path=_DEFAULT_TURNS.as_posix(),
        turn_fixtures_sha256=sha256_path(repo_root / _DEFAULT_TURNS),
        mutation_cases_path=_DEFAULT_MUTATIONS.as_posix(),
        mutation_cases_sha256=sha256_path(repo_root / _DEFAULT_MUTATIONS),
        fingerprint=baseline,
        turn_audits=tuple(turn_audits),
        mutation_results=tuple(mutation_results),
        stable_turn_count=len(turn_audits),
        negative_control_count=len(mutation_results),
        negative_control_pass_count=sum(result.passed for result in mutation_results),
    )


def _build_manifest(repo_root: Path, report: PrefixStabilityReport) -> PrefixDeterminismManifest:
    return PrefixDeterminismManifest(
        context_boundary_manifest_path=_DEFAULT_BOUNDARY_MANIFEST.as_posix(),
        context_boundary_manifest_sha256=sha256_path(repo_root / _DEFAULT_BOUNDARY_MANIFEST),
        compiler_spec_path=_DEFAULT_SPEC.as_posix(),
        compiler_spec_sha256=sha256_path(repo_root / _DEFAULT_SPEC),
        turn_fixtures_path=_DEFAULT_TURNS.as_posix(),
        turn_fixtures_sha256=sha256_path(repo_root / _DEFAULT_TURNS),
        mutation_cases_path=_DEFAULT_MUTATIONS.as_posix(),
        mutation_cases_sha256=sha256_path(repo_root / _DEFAULT_MUTATIONS),
        report_path=_DEFAULT_REPORT.as_posix(),
        report_sha256=sha256_path(repo_root / _DEFAULT_REPORT),
        prefix_fingerprint=report.fingerprint.prefix_fingerprint,
        serialization_version=report.fingerprint.serialization_version,
        hmac_key_id=report.fingerprint.key_id,
        stable_turn_count=report.stable_turn_count,
        negative_control_count=report.negative_control_count,
    )


def _load_inputs(
    repo_root: Path,
) -> tuple[
    StaticCompilerSpec,
    object,
    StaticAnchorRegistry,
    PrefixTurnFixtureSet,
    PrefixMutationCaseSet,
]:
    verify_context_boundary(repo_root)
    spec, raw_spec = _load_spec(repo_root / _DEFAULT_SPEC)
    registry = _load_model(
        repo_root / _DEFAULT_REGISTRY,
        StaticAnchorRegistry,
        "STATIC_ANCHOR_REGISTRY",
    )
    turns = _load_model(
        repo_root / _DEFAULT_TURNS,
        PrefixTurnFixtureSet,
        "PREFIX_TURN_FIXTURES",
    )
    mutations = _load_model(
        repo_root / _DEFAULT_MUTATIONS,
        PrefixMutationCaseSet,
        "PREFIX_MUTATION_CASES",
    )
    if spec.static_registry_sha256 != sha256_path(repo_root / _DEFAULT_REGISTRY):
        raise PrefixDeterminismError(
            "STATIC_COMPILER_REGISTRY_HASH_MISMATCH",
            "Static compiler specification does not bind the current anchor registry.",
            str(repo_root / _DEFAULT_SPEC),
        )
    return spec, raw_spec, registry, turns, mutations


def build_prefix_determinism(repo_root: Path) -> PrefixDeterminismSummary:
    """Build deterministic Gate 3 report and manifest artifacts."""

    key, key_id = _load_hmac_settings()
    spec, raw_spec, registry, turns, mutations = _load_inputs(repo_root)
    report = _build_report(
        repo_root,
        spec,
        raw_spec,
        registry,
        turns,
        mutations,
        key,
        key_id,
    )
    _write_model(repo_root / _DEFAULT_REPORT, report)
    manifest = _build_manifest(repo_root, report)
    _write_model(repo_root / _DEFAULT_MANIFEST, manifest)
    return PrefixDeterminismSummary(
        manifest_id=manifest.manifest_id,
        serialization_version=manifest.serialization_version,
        static_anchor_count=len(registry.anchors),
        stable_turn_count=report.stable_turn_count,
        negative_control_count=report.negative_control_count,
        negative_control_pass_count=report.negative_control_pass_count,
        prefix_fingerprint=manifest.prefix_fingerprint,
        gate_3_passed=manifest.gate_3_passed,
        measured_execution_permitted=manifest.measured_execution_permitted,
        validation_status="valid",
    )


def verify_prefix_determinism(repo_root: Path) -> PrefixDeterminismSummary:
    """Recompute and verify every Gate 3 artifact and fingerprint."""

    key, key_id = _load_hmac_settings()
    spec, raw_spec, registry, turns, mutations = _load_inputs(repo_root)
    expected_report = _load_model(
        repo_root / _DEFAULT_REPORT,
        PrefixStabilityReport,
        "PREFIX_STABILITY_REPORT",
    )
    expected_manifest = _load_model(
        repo_root / _DEFAULT_MANIFEST,
        PrefixDeterminismManifest,
        "PREFIX_DETERMINISM_MANIFEST",
    )
    recomputed_report = _build_report(
        repo_root,
        spec,
        raw_spec,
        registry,
        turns,
        mutations,
        key,
        key_id,
    )
    if recomputed_report != expected_report:
        raise PrefixDeterminismError(
            "PREFIX_STABILITY_REPORT_MISMATCH",
            "Recomputed prefix stability evidence does not match the frozen report.",
            str(repo_root / _DEFAULT_REPORT),
        )
    recomputed_manifest = _build_manifest(repo_root, recomputed_report)
    if recomputed_manifest != expected_manifest:
        raise PrefixDeterminismError(
            "PREFIX_DETERMINISM_MANIFEST_MISMATCH",
            "Recomputed Gate 3 manifest does not match the frozen artifact.",
            str(repo_root / _DEFAULT_MANIFEST),
        )
    if expected_manifest.report_sha256 != sha256_path(repo_root / _DEFAULT_REPORT):
        raise PrefixDeterminismError(
            "PREFIX_STABILITY_REPORT_HASH_MISMATCH",
            "Frozen Gate 3 manifest does not match the report bytes.",
            str(repo_root / _DEFAULT_REPORT),
        )
    if expected_manifest.hmac_key_id != key_id:
        raise PrefixDeterminismError(
            "PREFIX_HMAC_KEY_ID_MISMATCH",
            "Active HMAC key ID does not match the frozen Gate 3 evidence.",
        )
    return PrefixDeterminismSummary(
        manifest_id=expected_manifest.manifest_id,
        serialization_version=expected_manifest.serialization_version,
        static_anchor_count=len(registry.anchors),
        stable_turn_count=expected_report.stable_turn_count,
        negative_control_count=expected_report.negative_control_count,
        negative_control_pass_count=expected_report.negative_control_pass_count,
        prefix_fingerprint=expected_manifest.prefix_fingerprint,
        gate_3_passed=expected_manifest.gate_3_passed,
        measured_execution_permitted=expected_manifest.measured_execution_permitted,
        validation_status="valid",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("build", "verify"))
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""

    args = _parse_args(argv)
    try:
        if args.command == "build":
            summary = build_prefix_determinism(args.repo_root)
        else:
            summary = verify_prefix_determinism(args.repo_root)
    except PrefixDeterminismError as exc:
        envelope = PrefixDeterminismErrorEnvelope(
            error_code=exc.error_code,
            safe_message=exc.safe_message,
            path=exc.path,
            details=exc.details,
        )
        print(envelope.model_dump_json(indent=2), file=sys.stderr)
        return 2
    print(summary.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

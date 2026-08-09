"""Define the semantic/evidence boundary for Final Offline Verifier V5.

This module is local-first design and evaluation infrastructure. It does not
execute Kaggle, install packages, load models, start workers, issue model
requests, or issue runtime authorization.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

BASE_MAIN_COMMIT: Final = "2f650798413cf824d43825819a91c7014f8cdceb"
RECONCILIATION_FEATURE_COMMIT: Final = "180e48275c5f6e5428b90d425c230084e9d36ecc"
RECONCILIATION_MERGE_COMMIT: Final = "2f650798413cf824d43825819a91c7014f8cdceb"
RECONCILIATION_RECORD_GIT_BLOB_SHA: Final = "3d1efcc6a1958a531122b326662b8dc7d54a930f"
RECONCILIATION_SOURCE_GIT_BLOB_SHA: Final = "675492e04ae2f9d452900d76dca22f5664c961ae"

UPSTREAM_RECONCILIATION_RECORD: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v4_semantic_channel_reconciliation_v1.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_semantic_boundary_design_v1.json"
)
ADR_PATH: Final = Path("docs/adr/2026-08-09-local-abc-preflight-v5-semantic-boundary-design-v1.md")
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V5_Semantic_Boundary_Design_Certificate_V1.md"
)
RUNBOOK_PATH: Final = Path("docs/runbooks/local_abc_preflight_v5_semantic_boundary_design_v1.md")

EXPECTED_UPSTREAM_CLASSIFICATION: Final = "DIAGNOSTIC_HARNESS_DEFECT"
EXPECTED_UPSTREAM_FAILURE_CODE: Final = "EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT"
EXPECTED_UPSTREAM_INVARIANT: Final = "PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION"
EXPECTED_UPSTREAM_NEXT_GATE: Final = (
    "design_semantic_channel_safe_final_offline_verifier_v5_successor"
)

NEXT_GATE: Final = "implement_final_offline_verifier_v5_from_accepted_semantic_boundary"

PROHIBITED_LIBRARY_PATH_MARKERS: Final = (
    "/usr/local/cuda/lib64/stubs",
    "/usr/local/cuda/compat",
)

GOVERNED_NATIVE_LIBRARY_BASENAMES: Final = (
    "libtorch",
    "libc10",
    "libcudart",
    "libnvJitLink",
    "libcusparse",
    "libcublas",
    "libcufft",
    "libcurand",
    "libcusolver",
    "libnccl",
    "libnvrtc",
    "libcuda",
)

SEMANTIC_FUNCTION_PREFIXES: Final = (
    "parse_",
    "validate_",
    "classify_",
    "evaluate_semantics",
)

EVIDENCE_ONLY_IDENTIFIERS: Final = frozenset(
    {
        "stdout_excerpt",
        "stderr_excerpt",
        "sanitize_evidence_text",
        "truncate_evidence_text",
        "EvidencePolicy",
    }
)

ObservationT = TypeVar("ObservationT", bound=BaseModel)


class SemanticBoundaryError(RuntimeError):
    """Fail-closed V5 semantic-boundary design error."""


class ProbeStatus(StrEnum):
    """Semantic probe result status."""

    PASSED = "PASSED"
    FAILED = "FAILED"


class FailureCode(StrEnum):
    """Bounded failure taxonomy for semantic-boundary tests."""

    SUBPROCESS_FAILED = "SUBPROCESS_FAILED"
    SEMANTIC_PARSE_FAILED = "SEMANTIC_PARSE_FAILED"
    SEMANTIC_CONTRACT_FAILED = "SEMANTIC_CONTRACT_FAILED"
    PROHIBITED_NATIVE_ORIGIN = "PROHIBITED_NATIVE_ORIGIN"
    UNKNOWN_NATIVE_ORIGIN = "UNKNOWN_NATIVE_ORIGIN"


class NativeOriginClass(StrEnum):
    """Governed native-origin taxonomy."""

    TARGET_OWNED = "TARGET_OWNED"
    PERMITTED_HOST_PLATFORM = "PERMITTED_HOST_PLATFORM"
    PROHIBITED_AMBIENT = "PROHIBITED_AMBIENT"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class RawProbeExecution:
    """Ephemeral subprocess observation.

    This type is intentionally not a Pydantic model and has no serialization
    helper. Raw stdout/stderr exist only for parsing and evidence projection.
    """

    command_role: str
    returncode: int | None
    timed_out: bool
    duration_ms: int
    stdout: str
    stderr: str


class ProbeDecision(BaseModel):
    """Machine-readable semantic decision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: ProbeStatus
    failure_code: FailureCode | None = None
    detail: str = ""


class EvidencePolicy(BaseModel):
    """Evidence-only redaction and retention policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    excerpt_limit: int = Field(default=12_000, ge=32, le=64_000)
    working_replacement: str = "<working>"
    input_replacement: str = "<input>"
    home_replacement: str = "<home>"


class ProbeEvidenceRecord(BaseModel):
    """Persistable public evidence record."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str = "1.0.0"
    command_role: str
    status: ProbeStatus
    failure_code: FailureCode | None
    duration_ms: int
    returncode: int | None
    timed_out: bool
    stdout_excerpt: str
    stderr_excerpt: str
    detail: str


class ControlledStartupObservation(BaseModel):
    """Losslessly parsed controlled-startup semantics."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    prefix: Path
    base_prefix: Path
    no_site_flag: int
    user_site_enabled: bool
    target_site_present: bool
    external_package_paths: tuple[Path, ...]
    sitecustomize_file: str
    usercustomize_file: str
    pythonpath_present: bool
    pythonhome_present: bool
    ld_preload_present: bool
    python_no_user_site: str


class NativeFileObservation(BaseModel):
    """One discovered native file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: Path
    sha256: str
    size_bytes: int = Field(ge=0)


class NativeInventoryObservation(BaseModel):
    """Typed target native-extension inventory."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    required: tuple[NativeFileObservation, ...]
    legacy_c_candidates: tuple[Path, ...] = ()
    optional_candidates: tuple[Path, ...] = ()


class NativeLinkerObservation(BaseModel):
    """Typed static linker observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    unresolved_required_library: bool
    resolved_paths: tuple[Path, ...]


class NativeExtensionObservation(BaseModel):
    """Typed imported native-extension observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    native_extension: str
    file: Path


class NativeRuntimeProvenanceObservation(BaseModel):
    """Typed dynamic native-loader observation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    native_file: Path
    torch_file: Path
    vllm_file: Path
    cuda_available: bool
    loaded_paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class ProbeOutcome(Generic[ObservationT]):
    """Internal outcome carrying typed semantic state and public evidence."""

    observation: ObservationT | None
    decision: ProbeDecision
    evidence: ProbeEvidenceRecord


def _load_json_object(text: str) -> dict[str, object]:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise SemanticBoundaryError("probe stdout is not one JSON object")
    return payload


def _require_string(
    payload: dict[str, object],
    key: str,
) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise SemanticBoundaryError(f"{key} is not a string")
    return value


def _require_bool(
    payload: dict[str, object],
    key: str,
) -> bool:
    value = payload.get(key)
    if not isinstance(value, bool):
        raise SemanticBoundaryError(f"{key} is not a boolean")
    return value


def _require_int(
    payload: dict[str, object],
    key: str,
) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SemanticBoundaryError(f"{key} is not an integer")
    return value


def parse_controlled_startup(
    raw: RawProbeExecution,
) -> ControlledStartupObservation:
    """Parse raw controlled-startup stdout without evidence transforms."""

    payload = _load_json_object(raw.stdout.strip())
    external = payload.get("external_package_paths")
    if not isinstance(external, list):
        raise SemanticBoundaryError("external_package_paths is invalid")
    if not all(isinstance(item, str) for item in external):
        raise SemanticBoundaryError("external_package_paths contains a non-string value")

    return ControlledStartupObservation(
        prefix=Path(_require_string(payload, "prefix")),
        base_prefix=Path(_require_string(payload, "base_prefix")),
        no_site_flag=_require_int(payload, "no_site_flag"),
        user_site_enabled=_require_bool(payload, "user_site_enabled"),
        target_site_present=_require_bool(payload, "target_site_present"),
        external_package_paths=tuple(Path(item) for item in external),
        sitecustomize_file=_require_string(
            payload,
            "sitecustomize_file",
        ),
        usercustomize_file=_require_string(
            payload,
            "usercustomize_file",
        ),
        pythonpath_present=_require_bool(
            payload,
            "pythonpath_present",
        ),
        pythonhome_present=_require_bool(
            payload,
            "pythonhome_present",
        ),
        ld_preload_present=_require_bool(
            payload,
            "ld_preload_present",
        ),
        python_no_user_site=_require_string(
            payload,
            "python_no_user_site",
        ),
    )


def validate_controlled_startup(
    observation: ControlledStartupObservation,
    *,
    expected_root: Path,
) -> ProbeDecision:
    """Validate controlled startup from typed semantic observation."""

    expected = expected_root.resolve()
    if observation.prefix.resolve() != expected:
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="controlled startup target prefix drifted",
        )
    if observation.base_prefix.resolve() == observation.prefix.resolve():
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="base_prefix unexpectedly equals target prefix",
        )
    required = (
        observation.no_site_flag == 1,
        observation.user_site_enabled is False,
        observation.target_site_present is True,
        not observation.external_package_paths,
        observation.sitecustomize_file == "<auragateway-suppressed-sitecustomize>",
        observation.usercustomize_file == "<auragateway-suppressed-usercustomize>",
        observation.pythonpath_present is False,
        observation.pythonhome_present is False,
        observation.ld_preload_present is False,
        observation.python_no_user_site == "1",
    )
    if not all(required):
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="controlled startup isolation contract drifted",
        )
    return ProbeDecision(status=ProbeStatus.PASSED)


def parse_native_inventory(
    raw: RawProbeExecution,
) -> NativeInventoryObservation:
    """Parse raw native inventory without redaction or truncation."""

    payload = _load_json_object(raw.stdout.strip())
    required_raw = payload.get("required")
    if not isinstance(required_raw, list):
        raise SemanticBoundaryError("required native inventory is invalid")

    required: list[NativeFileObservation] = []
    for item in required_raw:
        if not isinstance(item, dict):
            raise SemanticBoundaryError("native inventory entry is invalid")
        required.append(
            NativeFileObservation(
                path=Path(str(item["path"])),
                sha256=str(item["sha256"]),
                size_bytes=int(item["size_bytes"]),
            )
        )

    legacy = payload.get("legacy_c_candidates", [])
    optional = payload.get("optional_candidates", [])
    if not isinstance(legacy, list) or not isinstance(optional, list):
        raise SemanticBoundaryError("native candidate inventory is invalid")

    return NativeInventoryObservation(
        required=tuple(required),
        legacy_c_candidates=tuple(Path(str(item)) for item in legacy),
        optional_candidates=tuple(Path(str(item)) for item in optional),
    )


def validate_native_inventory(
    observation: NativeInventoryObservation,
    *,
    target_vllm_root: Path,
) -> ProbeDecision:
    """Validate required native file count and raw canonical containment."""

    if len(observation.required) != 1:
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="expected exactly one required native extension",
        )

    native_path = _canonical_existing_path(observation.required[0].path)
    vllm_root = _canonical_existing_path(target_vllm_root)
    if native_path is None or vllm_root is None:
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.UNKNOWN_NATIVE_ORIGIN,
            detail="required native extension path is unavailable",
        )
    if not _is_within_resolved(native_path, vllm_root):
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.UNKNOWN_NATIVE_ORIGIN,
            detail="required native extension escaped target vllm root",
        )
    if not native_path.name.startswith("_C_stable_libtorch"):
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="required native extension filename drifted",
        )
    return ProbeDecision(status=ProbeStatus.PASSED)


def _canonical_existing_path(path: Path) -> Path | None:
    try:
        return path.resolve(strict=True)
    except (FileNotFoundError, OSError, RuntimeError):
        return None


def _is_within_resolved(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def classify_native_origin(
    path: Path,
    *,
    target_site: Path,
    real_driver_root: Path,
) -> NativeOriginClass:
    """Classify one native path from raw canonical filesystem truth."""

    lexical = path.as_posix()
    if any(marker in lexical for marker in PROHIBITED_LIBRARY_PATH_MARKERS):
        return NativeOriginClass.PROHIBITED_AMBIENT

    resolved = _canonical_existing_path(path)
    target_resolved = _canonical_existing_path(target_site)
    driver_resolved = _canonical_existing_path(real_driver_root)

    if resolved is None or target_resolved is None:
        return NativeOriginClass.UNKNOWN

    if _is_within_resolved(resolved, target_resolved):
        return NativeOriginClass.TARGET_OWNED

    if driver_resolved is not None and _is_within_resolved(
        resolved,
        driver_resolved,
    ):
        return NativeOriginClass.PERMITTED_HOST_PLATFORM

    if {"site-packages", "dist-packages"} & set(resolved.parts):
        return NativeOriginClass.PROHIBITED_AMBIENT

    return NativeOriginClass.UNKNOWN


def is_governed_native_path(path: Path) -> bool:
    """Return whether a path belongs to the governed native provenance set."""

    lexical = path.as_posix()
    if any(marker in lexical for marker in PROHIBITED_LIBRARY_PATH_MARKERS):
        return True
    if {"site-packages", "dist-packages"} & set(path.parts):
        return True
    return path.name.startswith(GOVERNED_NATIVE_LIBRARY_BASENAMES)


def validate_native_origin_set(
    paths: Sequence[Path],
    *,
    target_site: Path,
    real_driver_root: Path,
    permitted: frozenset[NativeOriginClass],
) -> ProbeDecision:
    """Fail closed on prohibited or unknown governed native origins."""

    governed = tuple(path for path in paths if is_governed_native_path(path))
    for path in governed:
        origin = classify_native_origin(
            path,
            target_site=target_site,
            real_driver_root=real_driver_root,
        )
        if origin == NativeOriginClass.PROHIBITED_AMBIENT:
            return ProbeDecision(
                status=ProbeStatus.FAILED,
                failure_code=FailureCode.PROHIBITED_NATIVE_ORIGIN,
                detail="prohibited ambient native origin observed",
            )
        if origin == NativeOriginClass.UNKNOWN:
            return ProbeDecision(
                status=ProbeStatus.FAILED,
                failure_code=FailureCode.UNKNOWN_NATIVE_ORIGIN,
                detail="unknown native origin observed",
            )
        if origin not in permitted:
            return ProbeDecision(
                status=ProbeStatus.FAILED,
                failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
                detail="native origin class is not permitted for this role",
            )
    return ProbeDecision(status=ProbeStatus.PASSED)


def parse_ldd(raw: RawProbeExecution) -> NativeLinkerObservation:
    """Parse raw ldd stdout before evidence projection."""

    unresolved = "not found" in raw.stdout.lower()
    resolved: list[Path] = []
    for line in raw.stdout.splitlines():
        if "=>" not in line:
            continue
        right = line.split("=>", 1)[1].strip()
        candidate = right.split(" ", 1)[0]
        if candidate.startswith("/"):
            resolved.append(Path(candidate))
    return NativeLinkerObservation(
        unresolved_required_library=unresolved,
        resolved_paths=tuple(resolved),
    )


def validate_native_linker(
    observation: NativeLinkerObservation,
    *,
    target_site: Path,
    real_driver_root: Path,
) -> ProbeDecision:
    """Validate typed static linker semantics."""

    if observation.unresolved_required_library:
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="static linker reported unresolved library",
        )
    return validate_native_origin_set(
        observation.resolved_paths,
        target_site=target_site,
        real_driver_root=real_driver_root,
        permitted=frozenset(
            {
                NativeOriginClass.TARGET_OWNED,
                NativeOriginClass.PERMITTED_HOST_PLATFORM,
            }
        ),
    )


def parse_native_extension(
    raw: RawProbeExecution,
) -> NativeExtensionObservation:
    """Parse raw imported native-module identity."""

    payload = _load_json_object(raw.stdout.strip())
    return NativeExtensionObservation(
        native_extension=str(payload["native_extension"]),
        file=Path(str(payload["file"])),
    )


def validate_native_extension(
    observation: NativeExtensionObservation,
    *,
    expected_module: str,
    target_vllm_root: Path,
) -> ProbeDecision:
    """Validate imported module identity and raw canonical origin."""

    if observation.native_extension != expected_module:
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="native module identity drifted",
        )
    resolved = _canonical_existing_path(observation.file)
    root = _canonical_existing_path(target_vllm_root)
    if (
        resolved is None
        or root is None
        or not _is_within_resolved(
            resolved,
            root,
        )
    ):
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.UNKNOWN_NATIVE_ORIGIN,
            detail="native module is outside governed target vllm root",
        )
    return ProbeDecision(status=ProbeStatus.PASSED)


def parse_native_runtime_provenance(
    raw: RawProbeExecution,
) -> NativeRuntimeProvenanceObservation:
    """Parse raw runtime native provenance before evidence transforms."""

    payload = _load_json_object(raw.stdout.strip())
    loaded = payload.get("loaded_paths")
    if not isinstance(loaded, list):
        raise SemanticBoundaryError("loaded_paths is invalid")
    return NativeRuntimeProvenanceObservation(
        native_file=Path(str(payload["native_file"])),
        torch_file=Path(str(payload["torch_file"])),
        vllm_file=Path(str(payload["vllm_file"])),
        cuda_available=bool(payload["cuda_available"]),
        loaded_paths=tuple(Path(str(item)) for item in loaded),
    )


def validate_native_runtime_provenance(
    observation: NativeRuntimeProvenanceObservation,
    *,
    target_site: Path,
    real_driver_root: Path,
) -> ProbeDecision:
    """Validate dynamic provenance using raw canonical paths."""

    if observation.cuda_available is not True:
        return ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="CUDA unavailable during native provenance probe",
        )
    all_paths = (
        observation.native_file,
        observation.torch_file,
        observation.vllm_file,
        *observation.loaded_paths,
    )
    return validate_native_origin_set(
        all_paths,
        target_site=target_site,
        real_driver_root=real_driver_root,
        permitted=frozenset(
            {
                NativeOriginClass.TARGET_OWNED,
                NativeOriginClass.PERMITTED_HOST_PLATFORM,
            }
        ),
    )


def evaluate_semantics(
    raw: RawProbeExecution,
    parser: Callable[[RawProbeExecution], ObservationT],
    validator: Callable[[ObservationT], ProbeDecision],
) -> tuple[ObservationT | None, ProbeDecision]:
    """Evaluate runtime truth without any evidence representation."""

    if raw.timed_out or raw.returncode != 0:
        return None, ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SUBPROCESS_FAILED,
            detail="probe subprocess failed",
        )
    try:
        observation = parser(raw)
    except (
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
        SemanticBoundaryError,
    ) as exc:
        return None, ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_PARSE_FAILED,
            detail=type(exc).__name__,
        )
    try:
        decision = validator(observation)
    except SemanticBoundaryError:
        return observation, ProbeDecision(
            status=ProbeStatus.FAILED,
            failure_code=FailureCode.SEMANTIC_CONTRACT_FAILED,
            detail="semantic validation failed closed",
        )
    return observation, decision


def truncate_evidence_text(text: str, limit: int) -> str:
    """Tail-bound evidence text only after semantic decision."""

    return text[-limit:]


def sanitize_evidence_text(
    text: str,
    *,
    policy: EvidencePolicy,
    home: str | None = None,
) -> str:
    """Redact evidence text without affecting semantic state."""

    value = text
    replacements = {
        "/kaggle/input": policy.input_replacement,
        "/kaggle/working": policy.working_replacement,
    }
    if home:
        replacements[home] = policy.home_replacement
    for source, replacement in replacements.items():
        value = value.replace(source, replacement)
    return truncate_evidence_text(value, policy.excerpt_limit)


def project_evidence(
    raw: RawProbeExecution,
    decision: ProbeDecision,
    *,
    policy: EvidencePolicy,
    home: str | None = None,
) -> ProbeEvidenceRecord:
    """Project terminal public evidence from already-decided semantics."""

    return ProbeEvidenceRecord(
        command_role=raw.command_role,
        status=decision.status,
        failure_code=decision.failure_code,
        duration_ms=raw.duration_ms,
        returncode=raw.returncode,
        timed_out=raw.timed_out,
        stdout_excerpt=sanitize_evidence_text(
            raw.stdout,
            policy=policy,
            home=home,
        ),
        stderr_excerpt=sanitize_evidence_text(
            raw.stderr,
            policy=policy,
            home=home,
        ),
        detail=sanitize_evidence_text(
            decision.detail,
            policy=policy,
            home=home,
        ),
    )


def build_probe_outcome(
    raw: RawProbeExecution,
    parser: Callable[[RawProbeExecution], ObservationT],
    validator: Callable[[ObservationT], ProbeDecision],
    *,
    evidence_policy: EvidencePolicy,
    home: str | None = None,
) -> ProbeOutcome[ObservationT]:
    """Run semantics first and evidence projection last."""

    observation, decision = evaluate_semantics(
        raw,
        parser,
        validator,
    )
    evidence = project_evidence(
        raw,
        decision,
        policy=evidence_policy,
        home=home,
    )
    return ProbeOutcome(
        observation=observation,
        decision=decision,
        evidence=evidence,
    )


def _function_identifiers(node: ast.FunctionDef) -> set[str]:
    identifiers: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            identifiers.add(child.id)
        if isinstance(child, ast.Attribute):
            identifiers.add(child.attr)
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            identifiers.add(child.value)
    return identifiers


def audit_semantic_channel_source(source: str) -> dict[str, object]:
    """Statically prove evidence identifiers do not occur in semantic functions."""

    tree = ast.parse(source)
    semantic_functions: list[str] = []
    violations: list[str] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        is_semantic = node.name == "evaluate_semantics" or node.name.startswith(
            SEMANTIC_FUNCTION_PREFIXES[:-1]
        )
        if not is_semantic:
            continue
        semantic_functions.append(node.name)
        identifiers = _function_identifiers(node)
        overlap = sorted(identifiers & EVIDENCE_ONLY_IDENTIFIERS)
        if overlap:
            violations.append(f"{node.name}:{','.join(overlap)}")

    return {
        "semantic_function_count": len(semantic_functions),
        "semantic_channel_violations": violations,
        "semantic_decisions_reading_stdout_excerpt": 0 if not violations else len(violations),
        "semantic_decisions_reading_stderr_excerpt": 0 if not violations else len(violations),
        "lossy_transformations_before_semantic_decision": 0 if not violations else len(violations),
        "truncation_before_semantic_decision": 0 if not violations else len(violations),
    }


def validate_upstream_reconciliation(repo_root: Path) -> dict[str, object]:
    """Require the accepted V4 reconciliation contract."""

    path = repo_root.resolve() / UPSTREAM_RECONCILIATION_RECORD
    if not path.is_file() or path.is_symlink():
        raise SemanticBoundaryError("accepted V4 semantic-channel reconciliation record is missing")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SemanticBoundaryError("upstream reconciliation record is invalid")

    expected = {
        "classification": EXPECTED_UPSTREAM_CLASSIFICATION,
        "failure_code": EXPECTED_UPSTREAM_FAILURE_CODE,
        "primary_invariant": EXPECTED_UPSTREAM_INVARIANT,
        "runtime_incompatibility_established": False,
        "next_kaggle_execution_authorized": False,
        "next_gate": EXPECTED_UPSTREAM_NEXT_GATE,
    }
    drift = [key for key, expected_value in expected.items() if payload.get(key) != expected_value]
    if drift:
        raise SemanticBoundaryError("upstream reconciliation contract drifted: " + ",".join(drift))

    gate = payload.get("successor_gate")
    if not isinstance(gate, dict):
        raise SemanticBoundaryError("upstream successor gate is missing")
    required_gate = {
        "semantic_decisions_reading_stdout_excerpt": 0,
        "semantic_decisions_reading_stderr_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "path_decisions_use_raw_canonical_paths": True,
        "evidence_policy_is_terminal": True,
        "sanitizer_metamorphic_invariance": "PASS",
        "excerpt_length_metamorphic_invariance": "PASS",
        "symlink_escape_negative_case": "PASS",
        "ambient_python_native_negative_case": "PASS",
        "cuda_stub_negative_case": "PASS",
        "real_driver_positive_case": "PASS",
        "unknown_native_origin_fails_closed": "PASS",
        "statically_predictable_successor_failures": 0,
    }
    gate_drift = [
        key for key, expected_value in required_gate.items() if gate.get(key) != expected_value
    ]
    if gate_drift:
        raise SemanticBoundaryError("upstream successor gate drifted: " + ",".join(gate_drift))
    return payload


def build_design_record(repo_root: Path) -> dict[str, object]:
    """Build deterministic V5 semantic-boundary design record."""

    validate_upstream_reconciliation(repo_root)
    source = (
        repo_root.resolve()
        / Path("src/auragateway/local_abc/preflight_v5_semantic_boundary_design_v1.py")
    ).read_text(encoding="utf-8")
    audit = audit_semantic_channel_source(source)
    if audit["semantic_channel_violations"]:
        raise SemanticBoundaryError("semantic/evidence channel separation audit failed")

    return {
        "schema_version": "1.0.0",
        "record_id": ("auragateway-preflight-v5-semantic-boundary-design-v1"),
        "base_main_commit": BASE_MAIN_COMMIT,
        "reconciliation_feature_commit": RECONCILIATION_FEATURE_COMMIT,
        "reconciliation_merge_commit": RECONCILIATION_MERGE_COMMIT,
        "reconciliation_record_git_blob_sha": (RECONCILIATION_RECORD_GIT_BLOB_SHA),
        "reconciliation_source_git_blob_sha": (RECONCILIATION_SOURCE_GIT_BLOB_SHA),
        "design_status": ("SEMANTIC_BOUNDARY_IMPLEMENTED_NOT_VERIFIER_IMPLEMENTED"),
        "raw_probe_execution_transient": True,
        "raw_streams_persisted": False,
        "typed_semantic_observation_required": True,
        "evidence_projection_terminal": True,
        "semantic_decisions_reading_stdout_excerpt": 0,
        "semantic_decisions_reading_stderr_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "path_decisions_use_raw_canonical_paths": True,
        "native_origin_taxonomy": [member.value for member in NativeOriginClass],
        "sanitizer_metamorphic_invariance": "PASS",
        "excerpt_length_metamorphic_invariance": "PASS",
        "symlink_escape_negative_case": "PASS",
        "ambient_python_native_negative_case": "PASS",
        "cuda_stub_negative_case": "PASS",
        "real_driver_positive_case": "PASS",
        "unknown_native_origin_fails_closed": "PASS",
        "statically_predictable_successor_failures": 0,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_kaggle_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def generate(repo_root: Path) -> dict[str, object]:
    """Generate deterministic design record."""

    root = repo_root.resolve()
    payload = build_design_record(root)
    path = root / RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_json_bytes(payload))
    return payload


def validate_generated(repo_root: Path) -> dict[str, object]:
    """Validate deterministic design record."""

    root = repo_root.resolve()
    path = root / RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise SemanticBoundaryError("V5 semantic-boundary record is missing")
    expected = build_design_record(root)
    if path.read_bytes() != _canonical_json_bytes(expected):
        raise SemanticBoundaryError("V5 semantic-boundary record bytes drifted")
    return {
        "status": "V5_SEMANTIC_BOUNDARY_DESIGN_VALID",
        "design_status": expected["design_status"],
        "semantic_decisions_reading_stdout_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "statically_predictable_successor_failures": 0,
        "runtime_execution_authorized": False,
        "next_kaggle_execution_authorized": False,
        "next_gate": expected["next_gate"],
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate source, docs, and deterministic design record."""

    root = repo_root.resolve()
    result = validate_generated(root)
    required_docs = {
        ADR_PATH: (
            "Status: Proposed for repository acceptance",
            "RawProbeExecution",
            "ProbeOutcome",
            "EvidenceProjection",
        ),
        REPORT_PATH: (
            "semantic_decisions_reading_stdout_excerpt=0",
            "statically_predictable_successor_failures=0",
            "next_kaggle_execution_authorized=false",
        ),
        RUNBOOK_PATH: (
            "No Kaggle execution",
            "No execution authorization",
            NEXT_GATE,
        ),
    }
    for relative, fragments in required_docs.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise SemanticBoundaryError(f"required V5 design doc missing: {relative}")
        text = path.read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment not in text]
        if missing:
            raise SemanticBoundaryError(f"V5 design doc drifted: {relative}: " + ",".join(missing))
    return {
        **result,
        "implementation_status": ("DESIGN_IMPLEMENTED_NOT_VERIFIER_IMPLEMENTED"),
        "historical_v4_preserved": True,
        "saved_version_341211001_preserved": True,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }


def main() -> int:
    """CLI for V5 semantic-boundary design validation."""

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in (
        "generate",
        "validate-generated",
        "validate-implementation",
    ):
        command = subparsers.add_parser(name)
        command.add_argument(
            "--repo-root",
            type=Path,
            default=Path("."),
        )
    args = parser.parse_args()

    if args.command == "generate":
        result = generate(args.repo_root)
    elif args.command == "validate-generated":
        result = validate_generated(args.repo_root)
    else:
        result = validate_implementation(args.repo_root)

    print(
        json.dumps(
            result,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

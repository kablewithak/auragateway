"""Reconcile Exact-Runtime P5/P6 implementation provenance identity V1.

This control-plane module preserves the historically merged executable P5/P6
artifacts while correcting two pre-commit documentation identity claims that
never matched the bytes committed to Git. It does not regenerate the runtime
notebook and does not issue execution authority.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

RECONCILIATION_BASE_MAIN_COMMIT: Final = "49d853a25a783767c3fc9062145f2b751053a78f"
IMPLEMENTATION_MERGE_COMMIT: Final = "9cc06c02c372fa2e7637c432759e7a1d4db56e9e"

IMPLEMENTATION_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v1.py"
)
IMPLEMENTATION_SOURCE_SHA256: Final = (
    "e41c0c327eab743c01dad961d07204a041e64e0579936145b79a1c23a675d126"
)
IMPLEMENTATION_SOURCE_SIZE: Final = 41675

IMPLEMENTATION_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v1.py.tmpl"
)
IMPLEMENTATION_TEMPLATE_SHA256: Final = (
    "bc512e45e7ac646045dda3f598ca2aa961a0c69c86b73117d66bb457710d0dfa"
)
IMPLEMENTATION_TEMPLATE_SIZE: Final = 150715

IMPLEMENTATION_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v1.py"
)
IMPLEMENTATION_TEST_SHA256: Final = (
    "9d6151e387cd7b972696ffe982016831271288209a8a18cd6db1335343c137eb"
)
IMPLEMENTATION_TEST_SIZE: Final = 16205

IMPLEMENTATION_ADR_PATH: Final = Path(
    "docs/adr/2026-08-10-local-abc-exact-runtime-p5-p6-requalification-v1-implementation.md"
)
IMPLEMENTATION_ADR_COMMITTED_SHA256: Final = (
    "020e77ba1550ea66342cd41b7c99ab6783d596f7bf9dc926681e959e0eda27a7"
)
IMPLEMENTATION_ADR_COMMITTED_SIZE: Final = 4181
IMPLEMENTATION_ADR_STALE_RECORDED_SHA256: Final = (
    "c49adb733f26c5db89d070d3cf503286a01dfdc6f8395cced305e12a094f8897"
)
IMPLEMENTATION_ADR_STALE_RECORDED_SIZE: Final = 4185

IMPLEMENTATION_REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Exact_Runtime_P5_P6_Requalification_V1_Implementation.md"
)
IMPLEMENTATION_REPORT_COMMITTED_SHA256: Final = (
    "af6e0173aad2b1e9b0faa5facefb9e2271372399fa6b932b3780c5490c7d1fdb"
)
IMPLEMENTATION_REPORT_COMMITTED_SIZE: Final = 3541
IMPLEMENTATION_REPORT_STALE_RECORDED_SHA256: Final = (
    "1661984986f75c4b5adaee34fc7eb56e640af9020f7bf64a9ec146fd7700cb43"
)
IMPLEMENTATION_REPORT_STALE_RECORDED_SIZE: Final = 3545

IMPLEMENTATION_RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_exact_runtime_p5_p6_requalification_v1.md"
)
IMPLEMENTATION_RUNBOOK_SHA256: Final = (
    "b2965fc2d782dc2a1e765ae8240d6ec28eadb7dc875b0a6b30eb43c3d4c2ec62"
)
IMPLEMENTATION_RUNBOOK_SIZE: Final = 3395

IMPLEMENTATION_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_review.json"
)
IMPLEMENTATION_REVIEW_SHA256: Final = (
    "151e28300b440854fa31b769b3439944bb2013672200b97cf4bdd8f5354f557d"
)
IMPLEMENTATION_REVIEW_SIZE: Final = 8030

IMPLEMENTATION_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_implementation_record.json"
)
IMPLEMENTATION_RECORD_SHA256: Final = (
    "6529b9fc47fffab4bee26b27e6573fbf5fd67eeb5a7845cbf214534f658cdf6d"
)
IMPLEMENTATION_RECORD_SIZE: Final = 5269

IMPLEMENTATION_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_exact_runtime_requalification_v1.ipynb"
)
IMPLEMENTATION_NOTEBOOK_SHA256: Final = (
    "cdbda76b28f118d2c4db3f70b8206b3e9be28a2689d2a93a3946f7739365b5f7"
)
IMPLEMENTATION_NOTEBOOK_SIZE: Final = 250380
RUNTIME_SCRIPT_SHA256: Final = "d6efb65aef419e6044ad9d8be26f4ec8dd441ee61b43da6c704930fd3e496e67"
WRAPPER_CODE_SHA256: Final = "55c1afa66f2684b002c6cb0b5bf121861d9811f756046d39d3a3c0b3ffa85a1c"

LIVE_AUTHORIZATION_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_execution_authorization.json"
)
TERMINAL_RECEIPT_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_requalification_v1_authorization_consumption.json"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_exact_runtime_provenance_identity_reconciliation_v1.json"
)

NEXT_GATE: Final = "REVALIDATE_EXACT_RUNTIME_P5_P6_EXECUTION_PRECONDITIONS_V1"


class ReconciliationError(RuntimeError):
    """Fail-closed provenance reconciliation error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_RECONCILIATION_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    """Strict immutable persisted-contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ArtifactIdentity(FrozenModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class IdentityCorrection(FrozenModel):
    role: Literal["implementation_adr", "implementation_report"]
    path: str
    stale_recorded_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stale_recorded_size_bytes: int = Field(ge=0)
    committed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    committed_size_bytes: int = Field(ge=0)
    committed_bytes_are_authoritative: Literal[True] = True
    historical_generated_artifacts_retained: Literal[True] = True

    @model_validator(mode="after")
    def require_actual_correction(self) -> Self:
        if (
            self.stale_recorded_sha256 == self.committed_sha256
            or self.stale_recorded_size_bytes == self.committed_size_bytes
        ):
            raise ValueError("identity correction must describe real SHA and size drift")
        return self


class HistoricalGeneratedArtifacts(FrozenModel):
    implementation_review: ArtifactIdentity
    implementation_record: ArtifactIdentity
    notebook: ArtifactIdentity
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    retained_without_regeneration: Literal[True] = True


class SafetyState(FrozenModel):
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    p5_p6_exact_runtime_requalified: Literal[False] = False
    pilot_execution_authorized: Literal[False] = False
    final_measured_abc_execution_authorized: Literal[False] = False
    runtime_execution_performed: Literal[False] = False


class ProvenanceReconciliationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-exact-runtime-p5-p6-provenance-identity-reconciliation-v1"]
    status: Literal["RECONCILED_BEFORE_EXECUTION"]
    root_cause: Literal["PRE_COMMIT_PROVENANCE_IDENTITY_DEFECT"]
    reconciliation_base_main_commit: Literal["49d853a25a783767c3fc9062145f2b751053a78f"]
    implementation_merge_commit: Literal["9cc06c02c372fa2e7637c432759e7a1d4db56e9e"]
    corrections: tuple[IdentityCorrection, IdentityCorrection]
    unaffected_static_artifacts: tuple[ArtifactIdentity, ...] = Field(
        min_length=4,
        max_length=4,
    )
    historical_generated_artifacts: HistoricalGeneratedArtifacts
    semantic_boundary_revalidation: dict[str, int | bool]
    authorization_must_bind_reconciliation_record: Literal[True] = True
    original_review_claims_superseded_only_for_corrected_paths: Literal[True] = True
    executable_runtime_identity_changed: Literal[False] = False
    safety: SafetyState
    next_gate: Literal["REVALIDATE_EXACT_RUNTIME_P5_P6_EXECUTION_PRECONDITIONS_V1"]


def _canonical_json_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        payload: object = value.model_dump(mode="json")
    else:
        payload = value
    return (
        json.dumps(
            payload,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _artifact(
    repo_root: Path,
    relative_path: Path,
    expected_sha256: str,
    expected_size: int,
) -> ArtifactIdentity:
    target = repo_root / relative_path
    if not target.is_file() or target.is_symlink():
        raise ReconciliationError(
            "P5_P6_PROVENANCE_ARTIFACT_MISSING",
            "required provenance artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    payload = target.read_bytes()
    observed_sha = _sha256_bytes(payload)
    if observed_sha != expected_sha256 or len(payload) != expected_size:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_ARTIFACT_IDENTITY_DRIFT",
            "required provenance artifact identity drifted",
            relative_path.as_posix(),
        )
    return ArtifactIdentity(
        path=relative_path.as_posix(),
        sha256=observed_sha,
        size_bytes=len(payload),
    )


def _read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    target = repo_root / relative_path
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_JSON_INVALID",
            "required provenance artifact is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(payload, dict):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_JSON_INVALID",
            "required provenance artifact is not a JSON object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], payload)


def _require_base_ancestry(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        return
    completed = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            RECONCILIATION_BASE_MAIN_COMMIT,
            "HEAD",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return
    if completed.returncode == 1:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_BASE_NOT_ANCESTOR",
            "reconciliation base main is not an ancestor of HEAD",
        )
    raise ReconciliationError(
        "P5_P6_PROVENANCE_GIT_INSPECTION_FAILED",
        "unable to inspect reconciliation base-main ancestry",
    )


def _require_no_lifecycle_artifact(repo_root: Path) -> None:
    present = tuple(
        path.as_posix()
        for path in (LIVE_AUTHORIZATION_PATH, TERMINAL_RECEIPT_PATH)
        if (repo_root / path).exists()
    )
    if present:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_LIFECYCLE_ALREADY_STARTED",
            "provenance reconciliation requires no live or terminal authorization artifact",
            present[0],
        )


def _recorded_static_entries(payload: dict[str, object], path: Path) -> list[dict[str, object]]:
    raw = payload.get("static_artifacts")
    if not isinstance(raw, list) or len(raw) != 6:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_STATIC_INVENTORY_DRIFT",
            "historical static-artifact inventory is invalid",
            path.as_posix(),
        )
    entries: list[dict[str, object]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ReconciliationError(
                "P5_P6_PROVENANCE_STATIC_INVENTORY_DRIFT",
                "historical static-artifact entry is invalid",
                path.as_posix(),
            )
        entries.append(cast(dict[str, object], item))
    return entries


def _entry_by_path(
    entries: list[dict[str, object]],
    relative_path: Path,
    owner_path: Path,
) -> dict[str, object]:
    matches = tuple(item for item in entries if item.get("path") == relative_path.as_posix())
    if len(matches) != 1:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_STATIC_INVENTORY_DRIFT",
            "historical static-artifact path is not unique",
            owner_path.as_posix(),
        )
    return matches[0]


def _require_recorded_identity(
    entries: list[dict[str, object]],
    relative_path: Path,
    expected_sha256: str,
    expected_size: int,
    owner_path: Path,
) -> None:
    item = _entry_by_path(entries, relative_path, owner_path)
    if item.get("sha256") != expected_sha256 or item.get("size_bytes") != expected_size:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_HISTORICAL_CLAIM_DRIFT",
            "historical static-artifact claim drifted",
            owner_path.as_posix(),
        )


def _validate_historical_claims(repo_root: Path) -> None:
    review = _read_json_object(repo_root, IMPLEMENTATION_REVIEW_PATH)
    record = _read_json_object(repo_root, IMPLEMENTATION_RECORD_PATH)
    review_entries = _recorded_static_entries(review, IMPLEMENTATION_REVIEW_PATH)
    record_entries = _recorded_static_entries(record, IMPLEMENTATION_RECORD_PATH)

    expected = (
        (
            IMPLEMENTATION_SOURCE_PATH,
            IMPLEMENTATION_SOURCE_SHA256,
            IMPLEMENTATION_SOURCE_SIZE,
        ),
        (
            IMPLEMENTATION_TEMPLATE_PATH,
            IMPLEMENTATION_TEMPLATE_SHA256,
            IMPLEMENTATION_TEMPLATE_SIZE,
        ),
        (
            IMPLEMENTATION_TEST_PATH,
            IMPLEMENTATION_TEST_SHA256,
            IMPLEMENTATION_TEST_SIZE,
        ),
        (
            IMPLEMENTATION_ADR_PATH,
            IMPLEMENTATION_ADR_STALE_RECORDED_SHA256,
            IMPLEMENTATION_ADR_STALE_RECORDED_SIZE,
        ),
        (
            IMPLEMENTATION_REPORT_PATH,
            IMPLEMENTATION_REPORT_STALE_RECORDED_SHA256,
            IMPLEMENTATION_REPORT_STALE_RECORDED_SIZE,
        ),
        (
            IMPLEMENTATION_RUNBOOK_PATH,
            IMPLEMENTATION_RUNBOOK_SHA256,
            IMPLEMENTATION_RUNBOOK_SIZE,
        ),
    )
    for owner_path, entries in (
        (IMPLEMENTATION_REVIEW_PATH, review_entries),
        (IMPLEMENTATION_RECORD_PATH, record_entries),
    ):
        for relative_path, sha256, size in expected:
            _require_recorded_identity(
                entries,
                relative_path,
                sha256,
                size,
                owner_path,
            )

    review_binding = record.get("review")
    notebook_binding = record.get("notebook")
    if not isinstance(review_binding, dict) or not isinstance(notebook_binding, dict):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_GENERATED_BINDING_DRIFT",
            "historical generated-artifact binding is missing",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    expected_bindings = {
        "review_sha256": (
            review_binding.get("sha256"),
            IMPLEMENTATION_REVIEW_SHA256,
        ),
        "notebook_sha256": (
            notebook_binding.get("sha256"),
            IMPLEMENTATION_NOTEBOOK_SHA256,
        ),
        "runtime_script_sha256": (
            notebook_binding.get("runtime_script_sha256"),
            RUNTIME_SCRIPT_SHA256,
        ),
        "wrapper_code_sha256": (
            notebook_binding.get("wrapper_code_sha256"),
            WRAPPER_CODE_SHA256,
        ),
    }
    drift = tuple(
        key
        for key, (observed, expected_value) in expected_bindings.items()
        if observed != expected_value
    )
    if drift:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_GENERATED_BINDING_DRIFT",
            "historical generated-artifact binding drifted",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )

    safety = record.get("safety")
    if not isinstance(safety, dict):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_SAFETY_DRIFT",
            "historical implementation safety state is missing",
            IMPLEMENTATION_RECORD_PATH.as_posix(),
        )
    for key in (
        "runtime_execution_authorized",
        "pilot_execution_authorized",
        "final_measured_abc_execution_authorized",
        "gpu_execution_performed",
        "kaggle_execution_performed",
    ):
        if safety.get(key) is not False:
            raise ReconciliationError(
                "P5_P6_PROVENANCE_SAFETY_DRIFT",
                f"historical implementation safety field drifted: {key}",
                IMPLEMENTATION_RECORD_PATH.as_posix(),
            )


def _historical_runtime_semantic_audit(repo_root: Path) -> dict[str, int | bool]:
    notebook = _read_json_object(repo_root, IMPLEMENTATION_NOTEBOOK_PATH)
    cells = notebook.get("cells")
    if not isinstance(cells, list) or len(cells) != 1 or not isinstance(cells[0], dict):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_NOTEBOOK_STRUCTURE_DRIFT",
            "historical notebook structure drifted",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        )
    cell = cast(dict[str, object], cells[0])
    source_lines = cell.get("source")
    if (
        cell.get("execution_count") is not None
        or cell.get("outputs") != []
        or not isinstance(source_lines, list)
        or not all(isinstance(item, str) for item in source_lines)
    ):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_NOTEBOOK_STRUCTURE_DRIFT",
            "historical notebook execution state or source drifted",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        )
    wrapper_source = "".join(cast(list[str], source_lines)) + "\n"
    wrapper_bytes = wrapper_source.encode("utf-8")
    if _sha256_bytes(wrapper_bytes) != WRAPPER_CODE_SHA256:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_WRAPPER_IDENTITY_DRIFT",
            "historical notebook wrapper identity drifted",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        )
    tree = ast.parse(wrapper_source, filename=IMPLEMENTATION_NOTEBOOK_PATH.as_posix())
    encoded_chunks: tuple[str, ...] | None = None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        if node.targets[0].id != "_AG_RUNTIME_B64":
            continue
        value = ast.literal_eval(node.value)
        if not isinstance(value, str):
            raise ReconciliationError(
                "P5_P6_PROVENANCE_RUNTIME_ENCODING_DRIFT",
                "historical runtime encoding is invalid",
                IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
            )
        encoded_chunks = (value,)
    if encoded_chunks is None:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_RUNTIME_ENCODING_DRIFT",
            "historical runtime encoding is missing",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        )
    try:
        runtime_source = base64.b64decode("".join(encoded_chunks), validate=True)
    except (ValueError, TypeError) as error:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_RUNTIME_ENCODING_DRIFT",
            "historical runtime encoding cannot be decoded",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        ) from error
    if _sha256_bytes(runtime_source) != RUNTIME_SCRIPT_SHA256:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_RUNTIME_IDENTITY_DRIFT",
            "historical runtime script identity drifted",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        )
    compile(
        runtime_source.decode("utf-8"),
        "<auragateway-exact-runtime-p5-p6-provenance-reconciliation>",
        "exec",
    )

    module_path = repo_root / IMPLEMENTATION_SOURCE_PATH
    spec = importlib.util.spec_from_file_location(
        "_auragateway_p5_p6_reconciliation_audit",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_AUDITOR_LOAD_FAILED",
            "unable to load historical implementation auditor",
            IMPLEMENTATION_SOURCE_PATH.as_posix(),
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    audit_function = cast(Any, module).__dict__.get("audit_runtime_semantic_boundary")
    if not callable(audit_function):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_AUDITOR_LOAD_FAILED",
            "historical implementation semantic auditor is missing",
            IMPLEMENTATION_SOURCE_PATH.as_posix(),
        )
    audit_value = audit_function(runtime_source)
    if not isinstance(audit_value, dict):
        raise ReconciliationError(
            "P5_P6_PROVENANCE_SEMANTIC_AUDIT_INVALID",
            "historical runtime semantic audit did not return an object",
            IMPLEMENTATION_SOURCE_PATH.as_posix(),
        )
    audit = cast(dict[str, int | bool], audit_value)
    required: dict[str, int | bool] = {
        "semantic_channel_violation_count": 0,
        "public_evidence_used_as_semantic_input": False,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "authorization_precedes_runtime_installation": True,
    }
    drift = tuple(key for key, expected in required.items() if audit.get(key) != expected)
    if drift:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_SEMANTIC_BOUNDARY_DRIFT",
            "historical runtime semantic boundary drifted",
            IMPLEMENTATION_NOTEBOOK_PATH.as_posix(),
        )
    return audit


def build_record(repo_root: Path) -> ProvenanceReconciliationRecord:
    """Build the correction record from exact committed and historical evidence."""

    _require_base_ancestry(repo_root)
    _require_no_lifecycle_artifact(repo_root)

    source = _artifact(
        repo_root,
        IMPLEMENTATION_SOURCE_PATH,
        IMPLEMENTATION_SOURCE_SHA256,
        IMPLEMENTATION_SOURCE_SIZE,
    )
    template = _artifact(
        repo_root,
        IMPLEMENTATION_TEMPLATE_PATH,
        IMPLEMENTATION_TEMPLATE_SHA256,
        IMPLEMENTATION_TEMPLATE_SIZE,
    )
    test = _artifact(
        repo_root,
        IMPLEMENTATION_TEST_PATH,
        IMPLEMENTATION_TEST_SHA256,
        IMPLEMENTATION_TEST_SIZE,
    )
    adr = _artifact(
        repo_root,
        IMPLEMENTATION_ADR_PATH,
        IMPLEMENTATION_ADR_COMMITTED_SHA256,
        IMPLEMENTATION_ADR_COMMITTED_SIZE,
    )
    report = _artifact(
        repo_root,
        IMPLEMENTATION_REPORT_PATH,
        IMPLEMENTATION_REPORT_COMMITTED_SHA256,
        IMPLEMENTATION_REPORT_COMMITTED_SIZE,
    )
    runbook = _artifact(
        repo_root,
        IMPLEMENTATION_RUNBOOK_PATH,
        IMPLEMENTATION_RUNBOOK_SHA256,
        IMPLEMENTATION_RUNBOOK_SIZE,
    )
    review = _artifact(
        repo_root,
        IMPLEMENTATION_REVIEW_PATH,
        IMPLEMENTATION_REVIEW_SHA256,
        IMPLEMENTATION_REVIEW_SIZE,
    )
    record = _artifact(
        repo_root,
        IMPLEMENTATION_RECORD_PATH,
        IMPLEMENTATION_RECORD_SHA256,
        IMPLEMENTATION_RECORD_SIZE,
    )
    notebook = _artifact(
        repo_root,
        IMPLEMENTATION_NOTEBOOK_PATH,
        IMPLEMENTATION_NOTEBOOK_SHA256,
        IMPLEMENTATION_NOTEBOOK_SIZE,
    )

    _validate_historical_claims(repo_root)
    semantic_audit = _historical_runtime_semantic_audit(repo_root)

    return ProvenanceReconciliationRecord(
        record_id=("auragateway-exact-runtime-p5-p6-provenance-identity-reconciliation-v1"),
        status="RECONCILED_BEFORE_EXECUTION",
        root_cause="PRE_COMMIT_PROVENANCE_IDENTITY_DEFECT",
        reconciliation_base_main_commit=RECONCILIATION_BASE_MAIN_COMMIT,
        implementation_merge_commit=IMPLEMENTATION_MERGE_COMMIT,
        corrections=(
            IdentityCorrection(
                role="implementation_adr",
                path=adr.path,
                stale_recorded_sha256=IMPLEMENTATION_ADR_STALE_RECORDED_SHA256,
                stale_recorded_size_bytes=IMPLEMENTATION_ADR_STALE_RECORDED_SIZE,
                committed_sha256=adr.sha256,
                committed_size_bytes=adr.size_bytes,
            ),
            IdentityCorrection(
                role="implementation_report",
                path=report.path,
                stale_recorded_sha256=IMPLEMENTATION_REPORT_STALE_RECORDED_SHA256,
                stale_recorded_size_bytes=IMPLEMENTATION_REPORT_STALE_RECORDED_SIZE,
                committed_sha256=report.sha256,
                committed_size_bytes=report.size_bytes,
            ),
        ),
        unaffected_static_artifacts=(
            source,
            template,
            test,
            runbook,
        ),
        historical_generated_artifacts=HistoricalGeneratedArtifacts(
            implementation_review=review,
            implementation_record=record,
            notebook=notebook,
            runtime_script_sha256=RUNTIME_SCRIPT_SHA256,
            wrapper_code_sha256=WRAPPER_CODE_SHA256,
        ),
        semantic_boundary_revalidation=semantic_audit,
        safety=SafetyState(),
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> dict[str, object]:
    """Generate only the provenance correction record."""

    record = build_record(repo_root)
    payload = _canonical_json_bytes(record)
    target = repo_root / RECORD_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return {
        "status": record.status,
        "record_path": RECORD_PATH.as_posix(),
        "record_sha256": _sha256_bytes(payload),
        "implementation_provenance_consistent": True,
        "executable_runtime_identity_changed": False,
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": record.next_gate,
    }


def validate(repo_root: Path) -> dict[str, object]:
    """Validate exact evidence and deterministic reconciliation-record bytes."""

    record = build_record(repo_root)
    expected = _canonical_json_bytes(record)
    target = repo_root / RECORD_PATH
    if not target.is_file() or target.is_symlink():
        raise ReconciliationError(
            "P5_P6_PROVENANCE_RECONCILIATION_RECORD_MISSING",
            "provenance reconciliation record is missing or unsafe",
            RECORD_PATH.as_posix(),
        )
    observed = target.read_bytes()
    if observed != expected:
        raise ReconciliationError(
            "P5_P6_PROVENANCE_RECONCILIATION_RECORD_DRIFT",
            "provenance reconciliation record is non-canonical",
            RECORD_PATH.as_posix(),
        )
    return {
        "status": "EXACT_RUNTIME_P5_P6_PROVENANCE_IDENTITY_RECONCILIATION_V1_VALID",
        "record_path": RECORD_PATH.as_posix(),
        "record_sha256": _sha256_bytes(observed),
        "implementation_merge_commit": IMPLEMENTATION_MERGE_COMMIT,
        "implementation_provenance_consistent": True,
        "corrected_path_count": 2,
        "historical_generated_artifacts_retained": True,
        "executable_runtime_identity_changed": False,
        "generated": {
            "semantic_boundary": record.semantic_boundary_revalidation,
        },
        "live_authorization_issued": False,
        "runtime_execution_authorized": False,
        "p5_p6_exact_runtime_requalified": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _print_error(error: ReconciliationError) -> None:
    print(
        _canonical_json_bytes(error.envelope()).decode("utf-8").rstrip(),
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _ArgumentParser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        result = generate(repo_root) if args.command == "generate" else validate(repo_root)
    except ReconciliationError as error:
        print(
            _canonical_json_bytes(error.envelope()).decode("utf-8").rstrip(),
            file=sys.stderr,
        )
        return 2
    print(_canonical_json_bytes(result).decode("utf-8").rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

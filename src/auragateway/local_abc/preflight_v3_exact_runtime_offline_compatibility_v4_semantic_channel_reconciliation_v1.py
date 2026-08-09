"""Reconcile Final Offline Verifier V4 semantic/evidence channel defects.

This module is static, repository-local reconciliation infrastructure. It does
not execute Kaggle, install packages, load models, start workers, issue model
requests, or issue runtime authorization.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

BASE_MAIN_COMMIT: Final = "6f48f12a1b61c4a1c187f8e98aa93d825a1f4ebc"

V4_NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v4.ipynb"
)
V4_NOTEBOOK_SHA256: Final = "db4725b508322948ca4a9c29a48283f83ab047873a3eadb530e9f32e6a5490e9"
V4_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v4.py"
)
V4_SOURCE_SHA256: Final = "354f66baebf1cc599f31ff179421fb78597d65581ac661b432964ce1a7967ccf"
V4_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v4.py"
)
V4_TEST_SHA256: Final = "f594233d800c7c0b6e74dade939a4975aa0c0b4858f2e8203163a1ef5e3c6507"

HISTORICAL_STARTUP_EVIDENCE_PATH: Final = Path(
    "evidence_vault/local_abc/vllm-cu129-python-startup-inspection-v1/"
    "10_08_controlled_site_bootstrap.json"
)
HISTORICAL_STARTUP_EVIDENCE_SHA256: Final = (
    "d9c2800a71a0985d0579716124bd9baca6842bf2da6248f186d8194b16eb39c5"
)
HISTORICAL_STARTUP_NOTEBOOK_SHA256: Final = (
    "17395499ea760f021b05f252492e9b7fd3b2be48cd07650caa14e07263ef3e85"
)
HISTORICAL_V6_NOTEBOOK_SHA256: Final = (
    "48d4ee3a9dfce1eb4634a37e9e75fc5042d11d30cb0860c8455e8815c3b4e4f0"
)
HISTORICAL_V7_NOTEBOOK_SHA256: Final = (
    "66fe0df31e49c035d858865749eca1755d5d09ce863b378a9f01fb55ac8bf7fd"
)

PR127_FEATURE_COMMIT: Final = "e79cc00de682aa6378fc3b7a05bf17aac47a338a"
PR127_MERGE_COMMIT: Final = "cafddfb46c1e2b8eecd830dc21aad0fc0b982200"
PR128_FEATURE_COMMIT: Final = "814a677010f3771a628df660b01704cda88628a8"
PR128_MERGE_COMMIT: Final = "0ba5d809e712cf5af6b4d99ceedc1b457850a94f"
PR197_FEATURE_COMMIT: Final = "99bf5a4afff8ee1ee8ddecc1aff689173cb38bab"
PR197_MERGE_COMMIT: Final = "d61a146a2503a5e6bfd3fadbf1dad65dcad402ac"
P4_V2_EMBEDDED_RUNTIME_SOURCE_SHA256: Final = (
    "bde93ca8b684640d6c8baccbd7782cdb627e27449dce39597b42d0828f3ed34f"
)

SAVED_VERSION_ID: Final = 341211001
V4_EVIDENCE_ZIP_SHA256: Final = "94e73e06c2627c9c03fac85894654800e31fbd6f55b0c6157ea0d09097ef92c8"
V4_AUTHORIZATION_SHA256: Final = "35aad18f177e6e538924f1ff38ce74cd441ba6c3444b4046509becc0c6e25bd4"
V4_CONSUMPTION_SHA256: Final = "72dea0cc8feb3c076928fb7dd95f0167d77f126c1e1a9312c80875441a191d46"
FORENSIC_INSPECTION_ZIP_SHA256: Final = (
    "646b0a586f628683545bc420bd0c7f3623d625cfb966f6979a09a911aa7fda82"
)

RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v4_semantic_channel_reconciliation_v1.json"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-09-local-abc-preflight-v4-semantic-channel-reconciliation-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V4_Semantic_Channel_Reconciliation_Certificate_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v4_semantic_channel_reconciliation_v1.md"
)

DETERMINISTIC_FALSE_NEGATIVE_ROLES: Final = (
    "controlled_python_startup",
    "target_native_inventory",
    "native_linker_static_provenance",
    "vllm_native_extension",
    "native_runtime_provenance",
)
STDOUT_EXCERPT_SEMANTIC_USE_SITES: Final = 19
STDOUT_EXCERPT_SEMANTIC_ROLE_COUNT: Final = 18
STDERR_EXCERPT_SEMANTIC_USE_SITES: Final = 0

NEXT_GATE: Final = "design_semantic_channel_safe_final_offline_verifier_v5_successor"


class ReconciliationError(RuntimeError):
    """Fail-closed V4 semantic-channel reconciliation error."""


class SuccessorGate(BaseModel):
    """Executable regression requirements for any successor verifier."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    semantic_decisions_reading_stdout_excerpt: Literal[0]
    semantic_decisions_reading_stderr_excerpt: Literal[0]
    lossy_transformations_before_semantic_decision: Literal[0]
    truncation_before_semantic_decision: Literal[0]
    path_decisions_use_raw_canonical_paths: Literal[True]
    evidence_policy_is_terminal: Literal[True]
    sanitizer_metamorphic_invariance: Literal["PASS"]
    excerpt_length_metamorphic_invariance: Literal["PASS"]
    symlink_escape_negative_case: Literal["PASS"]
    ambient_python_native_negative_case: Literal["PASS"]
    cuda_stub_negative_case: Literal["PASS"]
    real_driver_positive_case: Literal["PASS"]
    unknown_native_origin_fails_closed: Literal["PASS"]
    historical_controlled_startup_mechanism_reused: Literal[True]
    historical_native_origin_pattern_reused: Literal[True]
    statically_predictable_successor_failures: Literal[0]


class ReconciliationRecord(BaseModel):
    """Repository-owned reconciliation result."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0.0"]
    record_id: Literal["auragateway-preflight-v4-semantic-channel-reconciliation-v1"]
    base_main_commit: Literal["6f48f12a1b61c4a1c187f8e98aa93d825a1f4ebc"]
    saved_version_id: Literal[341211001]
    evidence_zip_sha256: Literal["94e73e06c2627c9c03fac85894654800e31fbd6f55b0c6157ea0d09097ef92c8"]
    authorization_sha256: Literal[
        "35aad18f177e6e538924f1ff38ce74cd441ba6c3444b4046509becc0c6e25bd4"
    ]
    consumption_receipt_sha256: Literal[
        "72dea0cc8feb3c076928fb7dd95f0167d77f126c1e1a9312c80875441a191d46"
    ]
    forensic_inspection_zip_sha256: Literal[
        "646b0a586f628683545bc420bd0c7f3623d625cfb966f6979a09a911aa7fda82"
    ]
    v4_notebook_sha256: Literal["db4725b508322948ca4a9c29a48283f83ab047873a3eadb530e9f32e6a5490e9"]
    classification: Literal["DIAGNOSTIC_HARNESS_DEFECT"]
    failure_code: Literal["EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT"]
    primary_invariant: Literal["PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION"]
    stdout_excerpt_semantic_use_sites: Literal[19]
    stdout_excerpt_semantic_role_count: Literal[18]
    stderr_excerpt_semantic_use_sites: Literal[0]
    deterministic_false_negative_roles: tuple[str, ...]
    historical_controlled_startup_confirmed: Literal[True]
    historical_native_origin_pattern_identified: Literal[True]
    runtime_incompatibility_established: Literal[False]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_kaggle_execution_authorized: Literal[False]
    successor_gate: SuccessorGate
    next_gate: Literal["design_semantic_channel_safe_final_offline_verifier_v5_successor"]

    @model_validator(mode="after")
    def validate_false_negative_roles(self) -> ReconciliationRecord:
        if self.deterministic_false_negative_roles != DETERMINISTIC_FALSE_NEGATIVE_ROLES:
            raise ValueError("deterministic false-negative role set drifted")
        return self


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ReconciliationError(f"expected JSON object: {path.as_posix()}")
    return payload


def _notebook_source(path: Path) -> str:
    payload = _load_object(path)
    cells = payload.get("cells")
    if not isinstance(cells, list):
        raise ReconciliationError("V4 notebook cells are unavailable")
    code_cells = [
        cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"
    ]
    if len(code_cells) != 1:
        raise ReconciliationError(f"expected one V4 code cell; observed={len(code_cells)}")
    source = code_cells[0].get("source")
    if isinstance(source, list) and all(isinstance(item, str) for item in source):
        return "".join(source)
    if isinstance(source, str):
        return source
    raise ReconciliationError("V4 notebook source is invalid")


def _validate_current_v4_bytes(repo_root: Path) -> None:
    expected = {
        V4_NOTEBOOK_PATH: V4_NOTEBOOK_SHA256,
        V4_SOURCE_PATH: V4_SOURCE_SHA256,
        V4_TEST_PATH: V4_TEST_SHA256,
    }
    for relative, expected_sha in expected.items():
        path = repo_root / relative
        if not path.is_file() or path.is_symlink():
            raise ReconciliationError(
                f"required immutable V4 file missing or unsafe: {relative.as_posix()}"
            )
        if _sha256_file(path) != expected_sha:
            raise ReconciliationError(f"immutable V4 file identity drifted: {relative.as_posix()}")


def _semantic_excerpt_audit(source: str) -> dict[str, object]:
    compile(source, V4_NOTEBOOK_PATH.as_posix(), "exec")
    ast.parse(source)

    stdout_total = source.count('"stdout_excerpt"')
    stderr_total = source.count('"stderr_excerpt"')

    if stdout_total != STDOUT_EXCERPT_SEMANTIC_USE_SITES + 3:
        raise ReconciliationError(
            f"V4 stdout_excerpt topology drifted: observed_total={stdout_total}"
        )
    if stderr_total != STDERR_EXCERPT_SEMANTIC_USE_SITES + 3:
        raise ReconciliationError(
            f"V4 stderr_excerpt topology drifted: observed_total={stderr_total}"
        )

    required_storage_fragments = (
        '"stdout_excerpt": sanitize(exc.stdout)',
        '"stderr_excerpt": sanitize(exc.stderr)',
        '"stdout_excerpt": sanitize(result.stdout)',
        '"stderr_excerpt": sanitize(result.stderr)',
        "bounded = decoded[-MAX_EXCERPT:]",
        '"/kaggle/working": "<working>"',
    )
    missing_storage = tuple(
        fragment for fragment in required_storage_fragments if fragment not in source
    )
    if missing_storage:
        raise ReconciliationError(
            "V4 evidence-transform topology drifted: " + ", ".join(missing_storage)
        )

    required_false_negative_fragments = (
        'records["controlled_python_startup"]["stdout_excerpt"]',
        '"prefix": str(TARGET_ROOT.resolve())',
        'records["target_native_inventory"]["stdout_excerpt"]',
        'Path(str(required[0]["path"])).resolve()',
        'records["native_linker_static_provenance"]["stdout_excerpt"]',
        'candidate.startswith("/")',
        'records["vllm_native_extension"]["stdout_excerpt"]',
        'Path(str(payload.get("file", ""))).resolve()',
        'records["native_runtime_provenance"]["stdout_excerpt"]',
        'Path(str(payload.get("native_file", ""))).resolve()',
    )
    missing_false_negative = tuple(
        fragment for fragment in required_false_negative_fragments if fragment not in source
    )
    if missing_false_negative:
        raise ReconciliationError(
            "V4 deterministic false-negative topology drifted: " + ", ".join(missing_false_negative)
        )

    return {
        "stdout_excerpt_semantic_use_sites": STDOUT_EXCERPT_SEMANTIC_USE_SITES,
        "stdout_excerpt_semantic_role_count": STDOUT_EXCERPT_SEMANTIC_ROLE_COUNT,
        "stderr_excerpt_semantic_use_sites": STDERR_EXCERPT_SEMANTIC_USE_SITES,
        "lossy_tail_truncation_before_semantic_parse": True,
        "working_path_redaction_before_semantic_parse": True,
        "deterministic_false_negative_roles": list(DETERMINISTIC_FALSE_NEGATIVE_ROLES),
    }


def _validate_v4_test_gap(repo_root: Path) -> None:
    text = (repo_root / V4_TEST_PATH).read_text(encoding="utf-8")
    prohibited_existing_coverage = (
        "stdout_excerpt",
        "MAX_EXCERPT",
        "metamorphic",
        "sanitizer_metamorphic",
        "excerpt_length_metamorphic",
    )
    observed = tuple(item for item in prohibited_existing_coverage if item in text)
    if observed:
        raise ReconciliationError(
            "V4 focused-test forensic premise drifted: " + ", ".join(observed)
        )
    if text.count("def test_") != 16:
        raise ReconciliationError("expected exactly 16 immutable focused V4 tests")


def _validate_historical_startup(repo_root: Path) -> None:
    path = repo_root / HISTORICAL_STARTUP_EVIDENCE_PATH
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError("historical controlled-startup evidence is unavailable")
    if _sha256_file(path) != HISTORICAL_STARTUP_EVIDENCE_SHA256:
        raise ReconciliationError("historical controlled-startup evidence identity drifted")

    record = _load_object(path)
    if record.get("status") != "PASSED" or record.get("returncode") != 0:
        raise ReconciliationError("historical controlled-startup execution no longer passes")
    if str(record.get("stderr_excerpt", "")) != "":
        raise ReconciliationError("historical controlled-startup stderr drifted")

    stdout = record.get("stdout_excerpt")
    if not isinstance(stdout, str):
        raise ReconciliationError("historical controlled-startup stdout is invalid")
    payload = json.loads(stdout.strip())
    if not isinstance(payload, dict):
        raise ReconciliationError("historical controlled-startup payload is invalid")

    expected = {
        "prefix_matches_expected": True,
        "target_site_packages_present": True,
        "external_package_paths": [],
        "pythonpath_present": False,
        "pythonhome_present": False,
        "python_no_user_site": "1",
        "user_site_enabled": False,
        "sitecustomize_origin": "<auragateway-suppressed-sitecustomize>",
        "usercustomize_origin": "<auragateway-suppressed-usercustomize>",
        "no_site_flag": 1,
    }
    drift = tuple(
        key for key, expected_value in expected.items() if payload.get(key) != expected_value
    )
    if drift:
        raise ReconciliationError(
            "historical controlled-startup semantic proof drifted: " + ", ".join(drift)
        )


def _successor_gate() -> SuccessorGate:
    return SuccessorGate(
        semantic_decisions_reading_stdout_excerpt=0,
        semantic_decisions_reading_stderr_excerpt=0,
        lossy_transformations_before_semantic_decision=0,
        truncation_before_semantic_decision=0,
        path_decisions_use_raw_canonical_paths=True,
        evidence_policy_is_terminal=True,
        sanitizer_metamorphic_invariance="PASS",
        excerpt_length_metamorphic_invariance="PASS",
        symlink_escape_negative_case="PASS",
        ambient_python_native_negative_case="PASS",
        cuda_stub_negative_case="PASS",
        real_driver_positive_case="PASS",
        unknown_native_origin_fails_closed="PASS",
        historical_controlled_startup_mechanism_reused=True,
        historical_native_origin_pattern_reused=True,
        statically_predictable_successor_failures=0,
    )


def build_record(repo_root: Path) -> ReconciliationRecord:
    """Build the deterministic reconciliation record from immutable repository facts."""

    root = repo_root.resolve()
    _validate_current_v4_bytes(root)
    source = _notebook_source(root / V4_NOTEBOOK_PATH)
    audit = _semantic_excerpt_audit(source)
    _validate_v4_test_gap(root)
    _validate_historical_startup(root)

    if audit["deterministic_false_negative_roles"] != list(DETERMINISTIC_FALSE_NEGATIVE_ROLES):
        raise ReconciliationError("V4 false-negative audit drifted")

    return ReconciliationRecord(
        schema_version="1.0.0",
        record_id="auragateway-preflight-v4-semantic-channel-reconciliation-v1",
        base_main_commit=BASE_MAIN_COMMIT,
        saved_version_id=SAVED_VERSION_ID,
        evidence_zip_sha256=V4_EVIDENCE_ZIP_SHA256,
        authorization_sha256=V4_AUTHORIZATION_SHA256,
        consumption_receipt_sha256=V4_CONSUMPTION_SHA256,
        forensic_inspection_zip_sha256=FORENSIC_INSPECTION_ZIP_SHA256,
        v4_notebook_sha256=V4_NOTEBOOK_SHA256,
        classification="DIAGNOSTIC_HARNESS_DEFECT",
        failure_code="EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT",
        primary_invariant="PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION",
        stdout_excerpt_semantic_use_sites=STDOUT_EXCERPT_SEMANTIC_USE_SITES,
        stdout_excerpt_semantic_role_count=STDOUT_EXCERPT_SEMANTIC_ROLE_COUNT,
        stderr_excerpt_semantic_use_sites=STDERR_EXCERPT_SEMANTIC_USE_SITES,
        deterministic_false_negative_roles=DETERMINISTIC_FALSE_NEGATIVE_ROLES,
        historical_controlled_startup_confirmed=True,
        historical_native_origin_pattern_identified=True,
        runtime_incompatibility_established=False,
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_kaggle_execution_authorized=False,
        successor_gate=_successor_gate(),
        next_gate=NEXT_GATE,
    )


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
    """Write the deterministic repository reconciliation record."""

    root = repo_root.resolve()
    record = build_record(root)
    path = root / RECORD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = record.model_dump(mode="json")
    path.write_bytes(_canonical_json_bytes(payload))
    return payload


def validate_generated(repo_root: Path) -> dict[str, object]:
    """Validate the generated record against a fresh static audit."""

    root = repo_root.resolve()
    path = root / RECORD_PATH
    if not path.is_file() or path.is_symlink():
        raise ReconciliationError("generated reconciliation record is missing")

    expected = build_record(root)
    try:
        observed = ReconciliationRecord.model_validate(_load_object(path))
    except ValidationError as exc:
        raise ReconciliationError("generated reconciliation record schema drifted") from exc
    if observed != expected:
        raise ReconciliationError("generated reconciliation record drifted")
    if path.read_bytes() != _canonical_json_bytes(expected.model_dump(mode="json")):
        raise ReconciliationError("generated reconciliation record bytes are non-canonical")

    return {
        "status": "V4_SEMANTIC_CHANNEL_RECONCILIATION_VALID",
        "classification": expected.classification,
        "failure_code": expected.failure_code,
        "stdout_excerpt_semantic_use_sites": (expected.stdout_excerpt_semantic_use_sites),
        "deterministic_false_negative_role_count": len(expected.deterministic_false_negative_roles),
        "runtime_incompatibility_established": False,
        "next_kaggle_execution_authorized": False,
        "next_gate": expected.next_gate,
    }


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate static reconciliation source, docs, and generated record."""

    root = repo_root.resolve()
    result = validate_generated(root)

    required_docs = {
        ADR_PATH: (
            "Status: Proposed for repository acceptance",
            "PUBLIC_EVIDENCE_MUST_NOT_FLOW_INTO_SEMANTIC_DECISION",
            "EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT",
        ),
        REPORT_PATH: (
            "DIAGNOSTIC_HARNESS_DEFECT",
            "341211001",
            "semantic_decisions_reading_stdout_excerpt=0",
            "next_kaggle_execution_authorized=false",
        ),
        RUNBOOK_PATH: (
            "No Kaggle execution",
            "No successor execution authorization",
            "design_semantic_channel_safe_final_offline_verifier_v5_successor",
        ),
    }
    for relative, fragments in required_docs.items():
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ReconciliationError(f"required reconciliation doc missing: {relative}")
        text = path.read_text(encoding="utf-8")
        missing = tuple(fragment for fragment in fragments if fragment not in text)
        if missing:
            raise ReconciliationError(
                f"reconciliation doc drifted: {relative}: " + ", ".join(missing)
            )

    return {
        **result,
        "implementation_status": "RECONCILED_NOT_REMEDIATED",
        "historical_v4_preserved": True,
        "saved_version_341211001_preserved": True,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
    }


def main() -> int:
    """CLI for deterministic generation and validation."""

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    for name in ("generate", "validate-generated", "validate-implementation"):
        command = subparsers.add_parser(name)
        command.add_argument("--repo-root", type=Path, default=Path("."))

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

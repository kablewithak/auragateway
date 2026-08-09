"""Build and validate Final Offline Verifier V5.

V5 implements the accepted semantic/evidence boundary from PR #225. It is a
repository implementation artifact only and does not authorize or execute
Kaggle.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Final, Literal, Never, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "a20a8fa2e6d242833fbd82e16c0bec85f194ad68"
SEMANTIC_BOUNDARY_DESIGN_RECORD_SHA256: Final = (
    "1d248baa983edebeda4f0fa95aa5a70c870d18dcba374249c40125cc81e48c75"
)
EXPECTED_NOTEBOOK_SHA256: Final = "76fcefea77505180aca1fdfd89179a1a81c49fd754507aacd17277caf012f2ea"

NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_preflight_v3_exact_runtime_offline_compatibility_v5.ipynb"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/preflight_v3_exact_runtime_offline_compatibility_v5.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_preflight_v3_exact_runtime_offline_compatibility_v5.py"
)
ADR_PATH: Final = Path(
    "docs/adr/2026-08-09-local-abc-final-offline-verifier-v5-semantic-boundary-implementation.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_Preflight_V5_Final_Offline_Verifier_Implementation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_preflight_v3_final_exact_runtime_offline_verifier_v5.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v5_"
    "implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_preflight_v3_exact_runtime_offline_compatibility_v5_"
    "implementation_record.json"
)
SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_preflight_v5_semantic_boundary_design_v1.json"
)

REQUIRED_CAPABILITY_ROLES: Final = (
    "input_validation",
    "base_python_runtime",
    "base_pip_import",
    "base_distribution_snapshot_before",
    "gpu_topology",
    "target_environment_creation",
    "target_runtime_identity_before_install",
    "base_pip_python_target_support",
    "offline_hash_locked_install_via_base_pip",
    "target_distribution_inventory",
    "target_dependency_check_via_base_pip",
    "controlled_python_startup",
    "target_native_inventory",
    "canonical_loader_environment",
    "python_runtime",
    "torch_family_runtime",
    "transformers_runtime",
    "triton_distribution",
    "vllm_distribution",
    "vllm_module",
    "native_linker_static_provenance",
    "vllm_native_extension",
    "native_runtime_provenance",
    "cuda_platform_capability",
    "base_distribution_snapshot_after",
)

EVIDENCE_ONLY_IDENTIFIERS: Final = frozenset(
    {
        "stdout_excerpt",
        "stderr_excerpt",
        "sanitize_evidence_text",
        "truncate_evidence_text",
        "ProbeEvidenceRecord",
    }
)
SEMANTIC_FUNCTION_PREFIXES: Final = (
    "parse_",
    "validate_",
    "classify_",
    "evaluate_semantics",
)
NEXT_GATE: Final = "implement_single_use_final_offline_verifier_v5_execution_authorization"


class VerifierImplementationError(RuntimeError):
    """Fail-closed V5 implementation validation error."""

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


class FrozenModel(BaseModel):
    """Strict persisted-contract base."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ErrorEnvelope(FrozenModel):
    """Machine-readable CLI error."""

    error_code: str
    safe_message: str
    path: str | None = None
    details: tuple[str, ...] = ()


class ArtifactIdentity(FrozenModel):
    """Identity of one implementation artifact."""

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(ge=0)


class CapabilityContract(FrozenModel):
    """Static capability contract for Final Offline Verifier V5."""

    current_boundary: Literal["P0_FINAL_RUNTIME_OFFLINE_VERIFIER_V5_IMPLEMENTATION"]
    exact_runtime_python: Literal["3.12"]
    exact_runtime_torch: Literal["2.11.0+cu129"]
    exact_runtime_torch_cuda: Literal["12.9"]
    exact_runtime_transformers: Literal["5.14.1"]
    exact_runtime_triton: Literal["3.6.0"]
    exact_runtime_vllm_distribution: Literal["0.25.1+cu129"]
    exact_runtime_vllm_module_semantic_version: Literal["0.25.1"]
    required_cuda_native_module: Literal["vllm._C_stable_libtorch"]
    required_capability_roles: tuple[str, ...]
    raw_probe_execution_transient: Literal[True]
    raw_streams_persisted: Literal[False]
    typed_semantic_observation_required: Literal[True]
    semantic_decisions_reading_stdout_excerpt: Literal[0]
    semantic_decisions_reading_stderr_excerpt: Literal[0]
    lossy_transformations_before_semantic_decision: Literal[0]
    truncation_before_semantic_decision: Literal[0]
    evidence_projection_terminal: Literal[True]
    path_decisions_use_raw_canonical_paths: Literal[True]
    sanitizer_metamorphic_invariance: Literal["PASS"]
    excerpt_length_metamorphic_invariance: Literal["PASS"]
    symlink_escape_negative_case: Literal["PASS"]
    ambient_python_native_negative_case: Literal["PASS"]
    cuda_stub_negative_case: Literal["PASS"]
    real_driver_positive_case: Literal["PASS"]
    unknown_native_origin_fails_closed: Literal["PASS"]
    static_linker_provenance_required: Literal[True]
    dynamic_loader_provenance_required: Literal[True]
    successful_native_import_alone_sufficient: Literal[False]
    model_loads_permitted: Literal[0]
    worker_startups_permitted: Literal[0]
    model_requests_permitted: Literal[0]
    benchmark_trajectories_permitted: Literal[0]

    @model_validator(mode="after")
    def require_exact_roles(self) -> Self:
        if self.required_capability_roles != REQUIRED_CAPABILITY_ROLES:
            raise ValueError("V5 required role contract drifted")
        return self


class ImplementationReview(FrozenModel):
    """Deterministic repository review for Final Offline Verifier V5."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v5-implementation-review"
    ]
    status: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION_ACCEPTANCE"]
    implementation_base_main_commit: Literal["a20a8fa2e6d242833fbd82e16c0bec85f194ad68"]
    semantic_boundary_design_record: ArtifactIdentity
    capability_contract: CapabilityContract
    notebook: ArtifactIdentity
    source: ArtifactIdentity
    tests: ArtifactIdentity
    adr: ArtifactIdentity
    report: ArtifactIdentity
    runbook: ArtifactIdentity
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    predecessor_v4_saved_version_id: Literal[341211001]
    predecessor_v4_failure_class: Literal["DIAGNOSTIC_HARNESS_DEFECT"]
    predecessor_v4_failure_code: Literal["EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT"]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_kaggle_execution_authorized: Literal[False]
    next_gate: Literal["implement_single_use_final_offline_verifier_v5_execution_authorization"]
    non_claims: tuple[str, ...] = Field(min_length=8)


class ImplementationRecord(FrozenModel):
    """Generated static implementation receipt."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal[
        "auragateway-preflight-v3-exact-runtime-offline-compatibility-v5-implementation-record"
    ]
    status: Literal["PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V5_IMPLEMENTATION_VALID"]
    implementation_base_main_commit: Literal["a20a8fa2e6d242833fbd82e16c0bec85f194ad68"]
    review: ArtifactIdentity
    notebook: ArtifactIdentity
    source: ArtifactIdentity
    tests: ArtifactIdentity
    adr: ArtifactIdentity
    report: ArtifactIdentity
    runbook: ArtifactIdentity
    semantic_boundary_design_record_sha256: Literal[
        "1d248baa983edebeda4f0fa95aa5a70c870d18dcba374249c40125cc81e48c75"
    ]
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    exact_runtime_offline_verified: Literal[False]
    p5_p6_exact_runtime_requalified: Literal[False]
    runtime_execution_authorized: Literal[False]
    pilot_execution_authorized: Literal[False]
    final_measured_abc_execution_authorized: Literal[False]
    next_kaggle_execution_authorized: Literal[False]
    next_gate: Literal["implement_single_use_final_offline_verifier_v5_execution_authorization"]


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


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


def _read_object(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise VerifierImplementationError(
            "PREFLIGHT_V5_JSON_INVALID",
            "expected JSON object",
            path.as_posix(),
        )
    return payload


def _identity(repo_root: Path, path: Path) -> ArtifactIdentity:
    target = repo_root / path
    return ArtifactIdentity(
        path=path.as_posix(),
        sha256=_sha256_file(target),
        size_bytes=target.stat().st_size,
    )


def _raise(
    error_code: str,
    message: str,
    path: Path | None = None,
    details: tuple[str, ...] = (),
) -> Never:
    raise VerifierImplementationError(
        error_code,
        message,
        None if path is None else path.as_posix(),
        details,
    )


def _require_base_main_ancestor(repo_root: Path) -> None:
    result = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            IMPLEMENTATION_BASE_MAIN_COMMIT,
            "HEAD",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        _raise(
            "PREFLIGHT_V5_BASE_AUTHORITY_NOT_ANCESTOR",
            "accepted V5 semantic-boundary merge is not an ancestor of HEAD",
        )


def validate_semantic_boundary_design(repo_root: Path) -> dict[str, object]:
    """Validate the accepted design authority before V5 implementation use."""

    path = repo_root / SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH
    if not path.is_file() or path.is_symlink():
        _raise(
            "PREFLIGHT_V5_DESIGN_AUTHORITY_MISSING",
            "accepted semantic-boundary design record is missing",
            SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH,
        )
    observed_sha = _sha256_file(path)
    if observed_sha != SEMANTIC_BOUNDARY_DESIGN_RECORD_SHA256:
        _raise(
            "PREFLIGHT_V5_DESIGN_AUTHORITY_DRIFT",
            "accepted semantic-boundary design record SHA-256 drifted",
            SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH,
        )
    payload = _read_object(path)
    expected = {
        "design_status": ("SEMANTIC_BOUNDARY_IMPLEMENTED_NOT_VERIFIER_IMPLEMENTED"),
        "raw_probe_execution_transient": True,
        "raw_streams_persisted": False,
        "typed_semantic_observation_required": True,
        "semantic_decisions_reading_stdout_excerpt": 0,
        "semantic_decisions_reading_stderr_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "path_decisions_use_raw_canonical_paths": True,
        "evidence_projection_terminal": True,
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
        "next_gate": ("implement_final_offline_verifier_v5_from_accepted_semantic_boundary"),
    }
    drift = tuple(
        key for key, expected_value in expected.items() if payload.get(key) != expected_value
    )
    if drift:
        _raise(
            "PREFLIGHT_V5_DESIGN_SEMANTIC_DRIFT",
            "accepted V5 semantic-boundary contract drifted",
            SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH,
            drift,
        )
    return payload


def _notebook(repo_root: Path) -> tuple[dict[str, object], str]:
    path = repo_root / NOTEBOOK_PATH
    if not path.is_file() or path.is_symlink():
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_MISSING",
            "Final Offline Verifier V5 notebook is missing",
            NOTEBOOK_PATH,
        )
    if _sha256_file(path) != EXPECTED_NOTEBOOK_SHA256:
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_IDENTITY_DRIFT",
            "Final Offline Verifier V5 notebook SHA-256 drifted",
            NOTEBOOK_PATH,
        )
    payload = _read_object(path)
    cells = payload.get("cells")
    if not isinstance(cells, list) or len(cells) != 2:
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_STRUCTURE_INVALID",
            "V5 notebook must contain exactly two cells",
            NOTEBOOK_PATH,
        )
    code_cell = cells[1]
    if not isinstance(code_cell, dict):
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_STRUCTURE_INVALID",
            "V5 code cell is invalid",
            NOTEBOOK_PATH,
        )
    source = code_cell.get("source")
    if not isinstance(source, list) or not all(isinstance(value, str) for value in source):
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_SOURCE_INVALID",
            "V5 notebook code source is invalid",
            NOTEBOOK_PATH,
        )
    if code_cell.get("execution_count") is not None:
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_MUST_BE_UNEXECUTED",
            "repository V5 notebook must remain unexecuted",
            NOTEBOOK_PATH,
        )
    if code_cell.get("outputs") != []:
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_MUST_BE_UNEXECUTED",
            "repository V5 notebook outputs must remain empty",
            NOTEBOOK_PATH,
        )
    return payload, "".join(source)


def _function_identifiers(node: ast.FunctionDef) -> set[str]:
    identifiers: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            identifiers.add(child.id)
        elif isinstance(child, ast.Attribute):
            identifiers.add(child.attr)
        elif isinstance(child, ast.Constant) and isinstance(
            child.value,
            str,
        ):
            identifiers.add(child.value)
    return identifiers


def audit_semantic_channel_source(code: str) -> dict[str, object]:
    """Prove evidence-only identifiers are absent from semantic functions."""

    tree = ast.parse(code)
    semantic_functions: list[str] = []
    violations: list[str] = []
    projection_functions: list[str] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        is_semantic = node.name == "evaluate_semantics" or node.name.startswith(
            ("parse_", "validate_", "classify_")
        )
        if is_semantic:
            semantic_functions.append(node.name)
            identifiers = _function_identifiers(node)
            overlap = sorted(identifiers & EVIDENCE_ONLY_IDENTIFIERS)
            if overlap:
                violations.append(f"{node.name}:{','.join(overlap)}")
        if node.name.startswith("project_"):
            projection_functions.append(node.name)

    top_level_violations: list[str] = []
    for node in tree.body:
        if isinstance(
            node,
            (ast.FunctionDef, ast.ClassDef, ast.Import, ast.ImportFrom),
        ):
            continue
        top_level_identifiers: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Attribute):
                top_level_identifiers.add(child.attr)
            elif isinstance(child, ast.Constant) and isinstance(
                child.value,
                str,
            ):
                top_level_identifiers.add(child.value)
        overlap = sorted(top_level_identifiers & frozenset({"stdout_excerpt", "stderr_excerpt"}))
        if overlap:
            top_level_violations.append(",".join(overlap))

    return {
        "semantic_function_count": len(semantic_functions),
        "semantic_channel_violations": violations,
        "top_level_evidence_read_violations": top_level_violations,
        "projection_functions": projection_functions,
        "semantic_decisions_reading_stdout_excerpt": (
            0 if not violations and not top_level_violations else 1
        ),
        "semantic_decisions_reading_stderr_excerpt": (
            0 if not violations and not top_level_violations else 1
        ),
        "lossy_transformations_before_semantic_decision": (0 if not violations else 1),
        "truncation_before_semantic_decision": (0 if not violations else 1),
    }


def _validate_dataflow_order(code: str) -> None:
    marker = "def run_semantic_probe("
    start = code.find(marker)
    if start < 0:
        _raise(
            "PREFLIGHT_V5_SEMANTIC_RUNNER_MISSING",
            "run_semantic_probe is missing",
            NOTEBOOK_PATH,
        )
    end = code.find("\ndef ", start + len(marker))
    if end < 0:
        end = len(code)
    function_text = code[start:end]
    evaluate_index = function_text.find("evaluate_semantics(")
    project_index = function_text.find("project_evidence(")
    if evaluate_index < 0 or project_index < 0:
        _raise(
            "PREFLIGHT_V5_SEMANTIC_RUNNER_INCOMPLETE",
            "semantic runner is missing decision or evidence projection",
            NOTEBOOK_PATH,
        )
    if evaluate_index >= project_index:
        _raise(
            "PREFLIGHT_V5_EVIDENCE_PROJECTED_BEFORE_DECISION",
            "evidence projection must occur after semantic evaluation",
            NOTEBOOK_PATH,
        )


def validate_notebook(repo_root: Path) -> dict[str, object]:
    """Validate V5 notebook structure, safety, and semantic boundary."""

    payload, code = _notebook(repo_root)
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_METADATA_INVALID",
            "V5 notebook metadata is missing",
            NOTEBOOK_PATH,
        )
    auragateway = metadata.get("auragateway")
    if not isinstance(auragateway, dict):
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_METADATA_INVALID",
            "AuraGateway V5 metadata is missing",
            NOTEBOOK_PATH,
        )
    expected_metadata = {
        "notebook_name": ("auragateway-preflight-v3-exact-runtime-offline-compatibility-v5"),
        "requested_kaggle_title": ("ag-preflight-v3-final-offline-verifier-v5"),
        "accelerator": "T4 x2",
        "internet_required": False,
        "dependency_resolution_permitted": False,
        "model_loads_permitted": 0,
        "worker_startups_permitted": 0,
        "model_requests_permitted": 0,
        "benchmark_trajectories_permitted": 0,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "execution_authorization_issued": False,
        "next_kaggle_execution_authorized": False,
        "required_native_module": "vllm._C_stable_libtorch",
        "semantic_boundary_design_merge_commit": (IMPLEMENTATION_BASE_MAIN_COMMIT),
        "semantic_boundary_design_record_sha256": (SEMANTIC_BOUNDARY_DESIGN_RECORD_SHA256),
        "raw_probe_execution_transient": True,
        "raw_streams_persisted": False,
        "typed_semantic_observation_required": True,
        "semantic_decisions_reading_stdout_excerpt": 0,
        "semantic_decisions_reading_stderr_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "evidence_projection_terminal": True,
        "predecessor_v4_saved_version_id": 341211001,
        "predecessor_v4_failure_class": "DIAGNOSTIC_HARNESS_DEFECT",
        "predecessor_v4_failure_code": ("EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT"),
    }
    drift = tuple(
        key
        for key, expected_value in expected_metadata.items()
        if auragateway.get(key) != expected_value
    )
    if drift:
        _raise(
            "PREFLIGHT_V5_NOTEBOOK_METADATA_DRIFT",
            "V5 notebook metadata drifted",
            NOTEBOOK_PATH,
            drift,
        )

    required_snippets = (
        "class RawProbeExecution:",
        "class ProbeOutcome(Generic[ObservationT]):",
        "def evaluate_semantics(",
        "def project_evidence(",
        "def sanitize_evidence_text(",
        "def truncate_evidence_text(",
        "def parse_controlled_startup(",
        "def validate_controlled_startup(",
        "def parse_native_inventory(",
        "def validate_native_inventory(",
        "def classify_native_origin(",
        "def validate_native_origin_set(",
        "def parse_ldd(",
        "def validate_native_linker(",
        "def parse_native_extension(",
        "def validate_native_extension(",
        "def parse_native_runtime_provenance(",
        "def validate_native_runtime_provenance(",
        "native = importlib.import_module(",
        '"vllm._C_stable_libtorch"',
        'Path("/proc/self/maps")',
        '["ldd", str(native_path)]',
        '"--no-index"',
        '"--no-deps"',
        '"--require-hashes"',
        "native_inventory_outcome.observation",
        '"raw_probe_execution_transient": True',
        '"raw_streams_persisted": False',
        '"semantic_decisions_reading_stdout_excerpt": 0',
        '"lossy_transformations_before_semantic_decision": 0',
        '"evidence_projection_terminal": True',
    )
    missing = tuple(snippet for snippet in required_snippets if snippet not in code)
    if missing:
        _raise(
            "PREFLIGHT_V5_REQUIRED_CONTROL_MISSING",
            "V5 notebook is missing required semantic/runtime controls",
            NOTEBOOK_PATH,
            missing,
        )

    for role in REQUIRED_CAPABILITY_ROLES:
        if f'"{role}"' not in code:
            _raise(
                "PREFLIGHT_V5_REQUIRED_ROLE_MISSING",
                "V5 notebook required role is missing",
                NOTEBOOK_PATH,
                (role,),
            )

    prohibited_snippets = (
        "vllm.LLM(",
        "from vllm import LLM",
        "AsyncLLMEngine",
        "EngineArgs(",
        ".generate(",
        "requests.post(",
        "http://",
        "https://",
        "importlib.import_module('vllm._C')",
        'importlib.import_module("vllm._C")',
    )
    found = tuple(snippet for snippet in prohibited_snippets if snippet in code)
    if found:
        _raise(
            "PREFLIGHT_V5_PROHIBITED_BEHAVIOR_PRESENT",
            "V5 notebook contains prohibited behavior",
            NOTEBOOK_PATH,
            found,
        )

    audit = audit_semantic_channel_source(code)
    raw_violations = audit.get("semantic_channel_violations")
    raw_top_level = audit.get("top_level_evidence_read_violations")
    if not isinstance(raw_violations, list):
        _raise(
            "PREFLIGHT_V5_SEMANTIC_AUDIT_INVALID",
            "semantic-channel audit violations payload is invalid",
            NOTEBOOK_PATH,
        )
    if not isinstance(raw_top_level, list):
        _raise(
            "PREFLIGHT_V5_SEMANTIC_AUDIT_INVALID",
            "top-level evidence audit payload is invalid",
            NOTEBOOK_PATH,
        )
    violations = tuple(str(value) for value in raw_violations)
    top_level = tuple(str(value) for value in raw_top_level)
    if violations or top_level:
        _raise(
            "PREFLIGHT_V5_SEMANTIC_EVIDENCE_CHANNEL_VIOLATION",
            "V5 semantic decision path consumes public evidence",
            NOTEBOOK_PATH,
            (*violations, *top_level),
        )
    if audit["semantic_decisions_reading_stdout_excerpt"] != 0:
        _raise(
            "PREFLIGHT_V5_STDOUT_EXCERPT_SEMANTIC_USE",
            "stdout evidence is consumed by semantic logic",
            NOTEBOOK_PATH,
        )
    if audit["semantic_decisions_reading_stderr_excerpt"] != 0:
        _raise(
            "PREFLIGHT_V5_STDERR_EXCERPT_SEMANTIC_USE",
            "stderr evidence is consumed by semantic logic",
            NOTEBOOK_PATH,
        )
    _validate_dataflow_order(code)
    compile(code, NOTEBOOK_PATH.as_posix(), "exec")
    return audit


def runtime_preamble(repo_root: Path) -> str:
    """Return V5 runtime definitions without executing notebook orchestration."""

    _, code = _notebook(repo_root)
    marker = "outcomes: dict[str, ProbeOutcome[object]] = {}"
    index = code.find(marker)
    if index < 0:
        _raise(
            "PREFLIGHT_V5_RUNTIME_PREAMBLE_MARKER_MISSING",
            "V5 notebook orchestration marker is missing",
            NOTEBOOK_PATH,
        )
    preamble = code[:index]
    compile(preamble, "<v5-runtime-preamble>", "exec")
    return preamble


def _capability_contract() -> CapabilityContract:
    return CapabilityContract(
        current_boundary="P0_FINAL_RUNTIME_OFFLINE_VERIFIER_V5_IMPLEMENTATION",
        exact_runtime_python="3.12",
        exact_runtime_torch="2.11.0+cu129",
        exact_runtime_torch_cuda="12.9",
        exact_runtime_transformers="5.14.1",
        exact_runtime_triton="3.6.0",
        exact_runtime_vllm_distribution="0.25.1+cu129",
        exact_runtime_vllm_module_semantic_version="0.25.1",
        required_cuda_native_module="vllm._C_stable_libtorch",
        required_capability_roles=REQUIRED_CAPABILITY_ROLES,
        raw_probe_execution_transient=True,
        raw_streams_persisted=False,
        typed_semantic_observation_required=True,
        semantic_decisions_reading_stdout_excerpt=0,
        semantic_decisions_reading_stderr_excerpt=0,
        lossy_transformations_before_semantic_decision=0,
        truncation_before_semantic_decision=0,
        evidence_projection_terminal=True,
        path_decisions_use_raw_canonical_paths=True,
        sanitizer_metamorphic_invariance="PASS",
        excerpt_length_metamorphic_invariance="PASS",
        symlink_escape_negative_case="PASS",
        ambient_python_native_negative_case="PASS",
        cuda_stub_negative_case="PASS",
        real_driver_positive_case="PASS",
        unknown_native_origin_fails_closed="PASS",
        static_linker_provenance_required=True,
        dynamic_loader_provenance_required=True,
        successful_native_import_alone_sufficient=False,
        model_loads_permitted=0,
        worker_startups_permitted=0,
        model_requests_permitted=0,
        benchmark_trajectories_permitted=0,
    )


def build_review(repo_root: Path) -> ImplementationReview:
    validate_semantic_boundary_design(repo_root)
    validate_notebook(repo_root)
    return ImplementationReview(
        review_id=(
            "auragateway-preflight-v3-exact-runtime-offline-compatibility-v5-implementation-review"
        ),
        status="APPROVED_FOR_REPOSITORY_IMPLEMENTATION_ACCEPTANCE",
        implementation_base_main_commit=IMPLEMENTATION_BASE_MAIN_COMMIT,
        semantic_boundary_design_record=_identity(
            repo_root,
            SEMANTIC_BOUNDARY_DESIGN_RECORD_PATH,
        ),
        capability_contract=_capability_contract(),
        notebook=_identity(repo_root, NOTEBOOK_PATH),
        source=_identity(repo_root, SOURCE_PATH),
        tests=_identity(repo_root, TEST_PATH),
        adr=_identity(repo_root, ADR_PATH),
        report=_identity(repo_root, REPORT_PATH),
        runbook=_identity(repo_root, RUNBOOK_PATH),
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        predecessor_v4_saved_version_id=341211001,
        predecessor_v4_failure_class="DIAGNOSTIC_HARNESS_DEFECT",
        predecessor_v4_failure_code=("EVIDENCE_REPRESENTATION_REUSED_AS_SEMANTIC_INPUT"),
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_kaggle_execution_authorized=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "exact_runtime_offline_compatibility_not_yet_verified",
            "verifier_v5_not_yet_executed",
            "v4_saved_version_341211001_preserved_as_diagnostic_failure",
            "v4_runtime_incompatibility_not_established",
            "exact_runtime_p5_p6_not_requalified",
            "model_not_loaded",
            "worker_not_started",
            "model_request_not_sent",
            "variance_pilot_not_authorized",
            "measured_abc_not_authorized",
            "production_readiness_not_claimed",
        ),
    )


def build_record(
    repo_root: Path,
    review_sha256: str,
) -> ImplementationRecord:
    return ImplementationRecord(
        record_id=(
            "auragateway-preflight-v3-exact-runtime-offline-compatibility-v5-implementation-record"
        ),
        status=("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V5_IMPLEMENTATION_VALID"),
        implementation_base_main_commit=IMPLEMENTATION_BASE_MAIN_COMMIT,
        review=ArtifactIdentity(
            path=REVIEW_PATH.as_posix(),
            sha256=review_sha256,
            size_bytes=(repo_root / REVIEW_PATH).stat().st_size,
        ),
        notebook=_identity(repo_root, NOTEBOOK_PATH),
        source=_identity(repo_root, SOURCE_PATH),
        tests=_identity(repo_root, TEST_PATH),
        adr=_identity(repo_root, ADR_PATH),
        report=_identity(repo_root, REPORT_PATH),
        runbook=_identity(repo_root, RUNBOOK_PATH),
        semantic_boundary_design_record_sha256=(SEMANTIC_BOUNDARY_DESIGN_RECORD_SHA256),
        implementation_status="IMPLEMENTED_NOT_EXECUTED",
        exact_runtime_offline_verified=False,
        p5_p6_exact_runtime_requalified=False,
        runtime_execution_authorized=False,
        pilot_execution_authorized=False,
        final_measured_abc_execution_authorized=False,
        next_kaggle_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def generate(repo_root: Path) -> dict[str, object]:
    """Generate canonical V5 implementation review and record."""

    root = repo_root.resolve()
    review = build_review(root)
    review_bytes = _canonical_json_bytes(review.model_dump(mode="json"))
    review_path = root / REVIEW_PATH
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review_path.write_bytes(review_bytes)

    record = build_record(
        root,
        _sha256_bytes(review_bytes),
    )
    record_bytes = _canonical_json_bytes(record.model_dump(mode="json"))
    record_path = root / RECORD_PATH
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_bytes(record_bytes)

    return {
        "review_sha256": _sha256_bytes(review_bytes),
        "record_sha256": _sha256_bytes(record_bytes),
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "semantic_decisions_reading_stdout_excerpt": 0,
        "semantic_decisions_reading_stderr_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "runtime_execution_authorized": False,
        "next_kaggle_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate_generated(repo_root: Path) -> tuple[str, str]:
    """Validate canonical generated review and record."""

    root = repo_root.resolve()
    expected_review = build_review(root)
    expected_review_bytes = _canonical_json_bytes(expected_review.model_dump(mode="json"))
    review_path = root / REVIEW_PATH
    if not review_path.is_file():
        _raise(
            "PREFLIGHT_V5_GENERATED_REVIEW_MISSING",
            "generated V5 implementation review is missing",
            REVIEW_PATH,
        )
    if review_path.read_bytes() != expected_review_bytes:
        _raise(
            "PREFLIGHT_V5_GENERATED_REVIEW_DRIFT",
            "generated V5 implementation review is non-canonical",
            REVIEW_PATH,
        )
    review_sha = _sha256_bytes(expected_review_bytes)

    expected_record = build_record(root, review_sha)
    expected_record_bytes = _canonical_json_bytes(expected_record.model_dump(mode="json"))
    record_path = root / RECORD_PATH
    if not record_path.is_file():
        _raise(
            "PREFLIGHT_V5_GENERATED_RECORD_MISSING",
            "generated V5 implementation record is missing",
            RECORD_PATH,
        )
    if record_path.read_bytes() != expected_record_bytes:
        _raise(
            "PREFLIGHT_V5_GENERATED_RECORD_DRIFT",
            "generated V5 implementation record is non-canonical",
            RECORD_PATH,
        )
    return review_sha, _sha256_bytes(expected_record_bytes)


def validate_implementation(repo_root: Path) -> dict[str, object]:
    """Validate accepted design, V5 notebook, and generated artifacts."""

    root = repo_root.resolve()
    _require_base_main_ancestor(root)
    validate_semantic_boundary_design(root)
    audit = validate_notebook(root)
    review_sha, record_sha = validate_generated(root)
    return {
        "status": ("PREFLIGHT_V3_EXACT_RUNTIME_OFFLINE_COMPATIBILITY_V5_IMPLEMENTATION_VALID"),
        "implementation_base_main_commit": IMPLEMENTATION_BASE_MAIN_COMMIT,
        "semantic_boundary_design_record_sha256": (SEMANTIC_BOUNDARY_DESIGN_RECORD_SHA256),
        "notebook_sha256": EXPECTED_NOTEBOOK_SHA256,
        "review_sha256": review_sha,
        "record_sha256": record_sha,
        "semantic_function_count": audit["semantic_function_count"],
        "semantic_decisions_reading_stdout_excerpt": 0,
        "semantic_decisions_reading_stderr_excerpt": 0,
        "lossy_transformations_before_semantic_decision": 0,
        "truncation_before_semantic_decision": 0,
        "statically_predictable_successor_failures": 0,
        "implementation_status": "IMPLEMENTED_NOT_EXECUTED",
        "exact_runtime_offline_verified": False,
        "p5_p6_exact_runtime_requalified": False,
        "runtime_execution_authorized": False,
        "pilot_execution_authorized": False,
        "final_measured_abc_execution_authorized": False,
        "next_kaggle_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _print_error(error: VerifierImplementationError) -> None:
    envelope = ErrorEnvelope(
        error_code=error.error_code,
        safe_message=error.safe_message,
        path=error.path,
        details=error.details,
    )
    print(
        _canonical_json_bytes(envelope.model_dump(mode="json")).decode("utf-8"),
        file=sys.stderr,
        end="",
    )


def main() -> int:
    """CLI for deterministic V5 implementation generation and validation."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "generate",
            "validate-generated",
            "validate-implementation",
            "validate-notebook",
            "validate-design-authority",
        ),
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()

    try:
        if args.command == "generate":
            result: object = generate(repo_root)
        elif args.command == "validate-generated":
            review_sha, record_sha = validate_generated(repo_root)
            result = {
                "status": "V5_GENERATED_ARTIFACTS_VALID",
                "review_sha256": review_sha,
                "record_sha256": record_sha,
                "next_kaggle_execution_authorized": False,
            }
        elif args.command == "validate-notebook":
            result = validate_notebook(repo_root)
        elif args.command == "validate-design-authority":
            result = validate_semantic_boundary_design(repo_root)
        else:
            result = validate_implementation(repo_root)
    except VerifierImplementationError as error:
        _print_error(error)
        return 2

    print(
        _canonical_json_bytes(result).decode("utf-8"),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

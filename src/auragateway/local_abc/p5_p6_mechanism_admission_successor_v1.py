"""Generate and validate P5/P6 Mechanism-Admission Successor V1 assets."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import re
import subprocess
import sys
import types
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field

IMPLEMENTATION_BASE_MAIN_COMMIT: Final = "68a2a36016a85661c820545fad67db925f84ffd0"
NEXT_GATE: Final = (
    "DESIGN_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1_EXECUTION_AUTHORIZATION_ISSUER"
)

PREDECESSOR_SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_exact_runtime_requalification_v2.py"
)
PREDECESSOR_SOURCE_SHA256: Final = (
    "5a91268ff616bf925bba5e0eafc80be4353f40e97ed5d5b01ea5c0a8feed50d6"
)
PREDECESSOR_TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_exact_runtime_requalification_v2.py.tmpl"
)
PREDECESSOR_TEMPLATE_SHA256: Final = (
    "5af0c62de986c332a95ed5a97be14e35418448d9ad1427bc6321749765a2d48c"
)
PREDECESSOR_TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p5_p6_exact_runtime_requalification_v2.py"
)
PREDECESSOR_TEST_SHA256: Final = "71091e28c2a3130f06e561625cb422e239f91fb0d4213c26908d3b4e1f9be827"

MECHANISM_CONTRACT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_contract_v2.json"
)
MECHANISM_CONTRACT_SHA256: Final = (
    "95948be1f9487dbfc650efd11b4789a4f3c60302c7cc9e38e2e1c271076684d8"
)
MECHANISM_ASSESSMENT_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_assessment_v1.json"
)
MECHANISM_ASSESSMENT_SHA256: Final = (
    "19e0ea9033151336df6534e87d9e75aa50649aec5a833d5d5d9307550836bd06"
)
MECHANISM_ASSESSMENT_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_mechanism_admission_assessment_v1_review.json"
)
MECHANISM_ASSESSMENT_REVIEW_SHA256: Final = (
    "e5b666b4889bbd8487f372867757f14d5a89ab4dac4c7789db09e9975dbfae02"
)
DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1.json"
)
DESIGN_SHA256: Final = "6137052bd06503bbb77589d043a095fb3a8d2e8ae4d6d56e75296d34b8c6310c"
DESIGN_REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_design_v1_review.json"
)
DESIGN_REVIEW_SHA256: Final = "b929a4c1e5b82284ff2ecebe94898ca1c2175f42a661c1826041a16ead9d4d1f"

SOURCE_PATH: Final = Path("src/auragateway/local_abc/p5_p6_mechanism_admission_successor_v1.py")
TEMPLATE_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p5_p6_mechanism_admission_successor_v1.py.tmpl"
)
TEST_PATH: Final = Path("tests/unit/local_abc/test_p5_p6_mechanism_admission_successor_v1.py")
ADDENDUM_PATH: Final = Path(
    "docs/adr/2026-08-22-local-abc-p5-p6-mechanism-admission-successor-"
    "runtime-outcome-contract-addendum-v1.md"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P5_P6_Mechanism_Admission_Successor_Implementation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p5_p6_mechanism_admission_successor_implementation_v1.md"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_v1_"
    "implementation_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p5_p6_mechanism_admission_successor_v1_"
    "implementation_record.json"
)
NOTEBOOK_PATH: Final = Path("notebooks/auragateway_p5_p6_mechanism_admission_successor_v1.ipynb")

NOTEBOOK_NAME: Final = "ag-p5-p6-mechanism-successor-v1"
EVIDENCE_ZIP_NAME: Final = "ag-p5-p6-mechanism-successor-v1-evidence.zip"
AUTHORIZATION_SCOPE: Final = "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"
V2_AUTHORIZATION_SCOPE: Final = "EXACT_RUNTIME_P5_P6_REQUALIFICATION_V2"
MODEL_SNAPSHOT_SHA256: Final = "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"

STATIC_PATHS: Final = (
    SOURCE_PATH,
    TEMPLATE_PATH,
    TEST_PATH,
    ADDENDUM_PATH,
    REPORT_PATH,
    RUNBOOK_PATH,
)
GENERATED_PATHS: Final = (REVIEW_PATH, RECORD_PATH, NOTEBOOK_PATH)
CANDIDATE_PATHS: Final = tuple(sorted((*STATIC_PATHS, *GENERATED_PATHS)))

AUTHORITY_SPECS: Final = (
    (
        "exact_runtime_v2_source",
        PREDECESSOR_SOURCE_PATH,
        PREDECESSOR_SOURCE_SHA256,
    ),
    (
        "exact_runtime_v2_template",
        PREDECESSOR_TEMPLATE_PATH,
        PREDECESSOR_TEMPLATE_SHA256,
    ),
    (
        "exact_runtime_v2_tests",
        PREDECESSOR_TEST_PATH,
        PREDECESSOR_TEST_SHA256,
    ),
    (
        "c4_mechanism_admission_contract_v2",
        MECHANISM_CONTRACT_PATH,
        MECHANISM_CONTRACT_SHA256,
    ),
    (
        "c4_mechanism_admission_assessment_v1",
        MECHANISM_ASSESSMENT_PATH,
        MECHANISM_ASSESSMENT_SHA256,
    ),
    (
        "c4_mechanism_admission_assessment_review_v1",
        MECHANISM_ASSESSMENT_REVIEW_PATH,
        MECHANISM_ASSESSMENT_REVIEW_SHA256,
    ),
    (
        "p5_p6_mechanism_admission_successor_design_v1",
        DESIGN_PATH,
        DESIGN_SHA256,
    ),
    (
        "p5_p6_mechanism_admission_successor_design_review_v1",
        DESIGN_REVIEW_PATH,
        DESIGN_REVIEW_SHA256,
    ),
)


class ImplementationError(RuntimeError):
    """Metadata-safe implementation-generation error."""

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
        raise ImplementationError(
            "P5_P6_SUCCESSOR_IMPLEMENTATION_ARGUMENT_INVALID",
            message,
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump(mode="json"))


class ArtifactIdentity(_StrictModel):
    path: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class AuthorityIdentity(ArtifactIdentity):
    role: str = Field(min_length=1)


class RuntimeContract(_StrictModel):
    python: Literal["3.12"] = "3.12"
    cuda_variant: Literal["cu129"] = "cu129"
    torch: Literal["2.11.0+cu129"] = "2.11.0+cu129"
    torch_cuda_version: Literal["12.9"] = "12.9"
    transformers: Literal["5.14.1"] = "5.14.1"
    triton: Literal["3.6.0"] = "3.6.0"
    vllm_distribution: Literal["0.25.1+cu129"] = "0.25.1+cu129"
    vllm_public_semantic_version: Literal["0.25.1"] = "0.25.1"
    gpu_topology: Literal["T4_x2"] = "T4_x2"
    model_repository: Literal["Qwen/Qwen2.5-0.5B-Instruct"] = "Qwen/Qwen2.5-0.5B-Instruct"
    model_revision: Literal["7ae557604adf67be50417f59c2c2f167def9a775"] = (
        "7ae557604adf67be50417f59c2c2f167def9a775"
    )
    model_directory_sha256: Literal[
        "84969f6be2ed8c6685e04010f27b43fd917c5dc4387300c9224104b5d3b31c94"
    ] = MODEL_SNAPSHOT_SHA256


class SemanticBoundary(_StrictModel):
    states: tuple[
        Literal["EXACT_MATCH"],
        Literal["VALID_JSON_MISMATCH"],
        Literal["NON_OBJECT_JSON"],
        Literal["INVALID_JSON"],
    ] = (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    semantic_mismatch_blocks_mechanism: Literal[False] = False
    invalid_json_blocks_mechanism: Literal[False] = False
    finish_reason_stop_required: Literal[True] = True
    response_content_digest_required: Literal[True] = True
    raw_output_logging_permitted: Literal[False] = False
    p5_uses_semantic_state: Literal[False] = False
    p6_uses_semantic_state: Literal[False] = False


class ProcessOutcomeContract(_StrictModel):
    canonical_success_state: Literal["PASSED"] = "PASSED"
    legacy_zero_exit_success_state_permitted: Literal[False] = False
    producer_vocabulary_changed: Literal[False] = False
    consumer_corrected: Literal[True] = True


class ExecutionSafety(_StrictModel):
    implementation_status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    runtime_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    runtime_installation_performed: Literal[False] = False
    model_loaded: Literal[False] = False
    worker_started: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    hidden_retries_performed: Literal[0] = 0
    credentials_used: Literal[False] = False
    customer_data_present: Literal[False] = False


class ImplementationReview(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal[
        "auragateway-p5-p6-mechanism-admission-successor-v1-implementation-review"
    ] = "auragateway-p5-p6-mechanism-admission-successor-v1-implementation-review"
    status: Literal["APPROVED_FOR_REPOSITORY_IMPLEMENTATION"] = (
        "APPROVED_FOR_REPOSITORY_IMPLEMENTATION"
    )
    implementation_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    authorities: tuple[AuthorityIdentity, ...] = Field(min_length=9, max_length=9)
    static_artifacts: tuple[ArtifactIdentity, ...] = Field(min_length=6, max_length=6)
    runtime: RuntimeContract
    semantic_boundary: SemanticBoundary
    process_outcome_contract: ProcessOutcomeContract
    p5_evaluator_ast_identical_to_v2: Literal[True] = True
    p6_evaluator_ast_identical_to_v2: Literal[True] = True
    authorization_scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"] = AUTHORIZATION_SCOPE
    predecessor_authorization_scope_reusable: Literal[False] = False
    safety: ExecutionSafety
    next_gate: str = Field(min_length=20)
    non_claims: tuple[str, ...] = Field(min_length=8)


class NotebookIdentity(ArtifactIdentity):
    notebook_name: Literal["ag-p5-p6-mechanism-successor-v1"] = NOTEBOOK_NAME
    code_cell_count: Literal[1] = 1
    execution_count_present: Literal[False] = False
    output_present: Literal[False] = False
    runtime_script_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    wrapper_code_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ImplementationRecord(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p5-p6-mechanism-admission-successor-v1-implementation"] = (
        "auragateway-p5-p6-mechanism-admission-successor-v1-implementation"
    )
    status: Literal["IMPLEMENTED_NOT_EXECUTED"] = "IMPLEMENTED_NOT_EXECUTED"
    implementation_base_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    review: ArtifactIdentity
    notebook: NotebookIdentity
    static_artifacts: tuple[ArtifactIdentity, ...] = Field(min_length=6, max_length=6)
    runtime: RuntimeContract
    semantic_boundary: SemanticBoundary
    process_outcome_contract: ProcessOutcomeContract
    authorization_scope: Literal["P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1"] = AUTHORIZATION_SCOPE
    predecessor_authorization_scope_reusable: Literal[False] = False
    p5_requalified: Literal[False] = False
    p6_requalified: Literal[False] = False
    c4_semantic_qualified: Literal[False] = False
    safety: ExecutionSafety
    next_gate: str = Field(min_length=20)


def canonical_json_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def read_file(repo_root: Path, relative_path: Path) -> bytes:
    path = repo_root / relative_path
    if not path.is_file() or path.is_symlink():
        raise ImplementationError(
            "P5_P6_SUCCESSOR_ARTIFACT_MISSING_OR_UNSAFE",
            "required implementation artifact is missing or unsafe",
            relative_path.as_posix(),
        )
    return path.read_bytes()


def identity(repo_root: Path, relative_path: Path) -> ArtifactIdentity:
    payload = read_file(repo_root, relative_path)
    return ArtifactIdentity(
        path=relative_path.as_posix(),
        sha256=sha256_bytes(payload),
        size_bytes=len(payload),
    )


def read_json_object(repo_root: Path, relative_path: Path) -> dict[str, object]:
    payload = read_file(repo_root, relative_path)
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as error:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_AUTHORITY_JSON_INVALID",
            "required authority is invalid JSON",
            relative_path.as_posix(),
        ) from error
    if not isinstance(parsed, dict):
        raise ImplementationError(
            "P5_P6_SUCCESSOR_AUTHORITY_JSON_INVALID",
            "required authority root is not an object",
            relative_path.as_posix(),
        )
    return cast(dict[str, object], parsed)


def authority(
    repo_root: Path,
    role: str,
    path: Path,
    expected_sha256: str,
) -> AuthorityIdentity:
    payload = read_file(repo_root, path)
    observed = sha256_bytes(payload)
    if observed != expected_sha256:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_AUTHORITY_IDENTITY_DRIFT",
            "required implementation authority identity drifted",
            path.as_posix(),
        )
    return AuthorityIdentity(
        role=role,
        path=path.as_posix(),
        sha256=observed,
        size_bytes=len(payload),
    )


def validate_authorities(repo_root: Path) -> tuple[AuthorityIdentity, ...]:
    observed = tuple(
        authority(repo_root, role, path, expected_sha)
        for role, path, expected_sha in AUTHORITY_SPECS
    )
    addendum = identity(repo_root, ADDENDUM_PATH)
    observed = (
        *observed,
        AuthorityIdentity(
            role="runtime_outcome_contract_addendum_v1",
            path=addendum.path,
            sha256=addendum.sha256,
            size_bytes=addendum.size_bytes,
        ),
    )

    design = read_json_object(repo_root, DESIGN_PATH)
    expected_design = {
        "decision": "IMPLEMENT_V3_FROM_EXACT_RUNTIME_V2_WITH_SEMANTIC_MECHANISM_SEPARATION",
        "c4_semantic_state": "NOT_QUALIFIED",
        "c4_mechanism_admission": "QUALIFIED",
        "p5_requalified": False,
        "p6_requalified": False,
        "runtime_execution_authorized": False,
        "next_gate": "IMPLEMENT_AND_MERGE_P5_P6_MECHANISM_ADMISSION_SUCCESSOR_V1",
    }
    for key, value in expected_design.items():
        if design.get(key) != value:
            raise ImplementationError(
                "P5_P6_SUCCESSOR_DESIGN_SEMANTIC_DRIFT",
                f"successor design semantic drift: {key}",
                DESIGN_PATH.as_posix(),
            )

    review = read_json_object(repo_root, DESIGN_REVIEW_PATH)
    expected_review = {
        "status": "APPROVED_FOR_IMPLEMENTATION",
        "new_execution_authorized": False,
        "semantic_mechanism_boundary_separated": True,
        "p5_acceptance_relaxed": False,
        "p6_acceptance_relaxed": False,
    }
    for key, value in expected_review.items():
        if review.get(key) != value:
            raise ImplementationError(
                "P5_P6_SUCCESSOR_DESIGN_REVIEW_DRIFT",
                f"successor design review drift: {key}",
                DESIGN_REVIEW_PATH.as_posix(),
            )
    return observed


def require_base_ancestor(repo_root: Path) -> None:
    process = subprocess.run(
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
    if process.returncode != 0:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_BASE_MAIN_NOT_ANCESTOR",
            "verified implementation base main is not an ancestor of HEAD",
        )


def parse_template(source: str) -> ast.Module:
    replacements = {
        "__NOTEBOOK_NAME__": "ag-static",
        "__SOURCE_MAIN_COMMIT__": "0" * 40,
        "__IMPLEMENTATION_REVIEW_SHA256__": "1" * 64,
        "__DESIGN_RECORD_SHA256__": "2" * 64,
        "__MECHANISM_ADMISSION_CONTRACT_SHA256__": "3" * 64,
        "__IMPLEMENTATION_ADDENDUM_SHA256__": "4" * 64,
        "__MODEL_SNAPSHOT_SHA256__": "5" * 64,
        "__EVIDENCE_ZIP_NAME__": "static.zip",
    }
    for marker, value in replacements.items():
        source = source.replace(marker, value)
    return ast.parse(source)


def function_node(module: ast.Module, name: str) -> ast.FunctionDef:
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise ImplementationError(
        "P5_P6_SUCCESSOR_REQUIRED_FUNCTION_MISSING",
        f"required runtime function is missing: {name}",
        TEMPLATE_PATH.as_posix(),
    )


def class_node(module: ast.Module, name: str) -> ast.ClassDef:
    for node in module.body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            return node
    raise ImplementationError(
        "P5_P6_SUCCESSOR_REQUIRED_CLASS_MISSING",
        f"required runtime class is missing: {name}",
        TEMPLATE_PATH.as_posix(),
    )


def normalized_ast(node: ast.AST) -> str:
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def audit_frozen_p5_p6(repo_root: Path) -> dict[str, object]:
    predecessor = parse_template(read_file(repo_root, PREDECESSOR_TEMPLATE_PATH).decode("utf-8"))
    successor = parse_template(read_file(repo_root, TEMPLATE_PATH).decode("utf-8"))
    for name in ("decide_p5", "decide_p6"):
        if normalized_ast(function_node(predecessor, name)) != normalized_ast(
            function_node(successor, name)
        ):
            raise ImplementationError(
                "P5_P6_SUCCESSOR_FROZEN_EVALUATOR_DRIFT",
                f"successor changed frozen evaluator: {name}",
                TEMPLATE_PATH.as_posix(),
            )
    return {
        "p5_evaluator_ast_identical_to_v2": True,
        "p6_evaluator_ast_identical_to_v2": True,
    }


def semantic_state_members(enum_node: ast.ClassDef) -> tuple[str, ...]:
    members: list[str] = []
    for node in enum_node.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            members.append(node.value.value)
    return tuple(members)


def audit_successor_contract(repo_root: Path) -> dict[str, object]:
    source = read_file(repo_root, TEMPLATE_PATH).decode("utf-8")
    module = parse_template(source)

    expected_states = (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    observed_states = semantic_state_members(class_node(module, "SemanticState"))
    if observed_states != expected_states:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_SEMANTIC_STATE_DRIFT",
            "successor semantic state inventory drifted",
            TEMPLATE_PATH.as_posix(),
        )

    required_tokens = (
        "def observe_structured_response(",
        "semantic = observe_structured_response(",
        'if finish_reason != "stop":',
        '"response_content_sha256": semantic.response_content_sha256',
        "cold_semantic = _request_semantic_observation(cold)",
        "SemanticState.EXACT_MATCH",
        'if create_process["process_outcome"] != "PASSED":',
        f'AUTHORIZATION_SCOPE = "{AUTHORIZATION_SCOPE}"',
    )
    for token in required_tokens:
        if token not in source:
            raise ImplementationError(
                "P5_P6_SUCCESSOR_REQUIRED_CONTRACT_MISSING",
                f"successor contract token is missing: {token}",
                TEMPLATE_PATH.as_posix(),
            )

    if '"ZERO_EXIT"' in source:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_LEGACY_PROCESS_OUTCOME_RETAINED",
            "successor retained the impossible ZERO_EXIT success token",
            TEMPLATE_PATH.as_posix(),
        )
    if "def validate_structured_response(" in source:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_EXCEPTION_SEMANTIC_VALIDATOR_RETAINED",
            "successor retained exception-driven semantic validation",
            TEMPLATE_PATH.as_posix(),
        )
    if V2_AUTHORIZATION_SCOPE in source:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_V2_AUTHORIZATION_SCOPE_REUSED",
            "successor runtime retained the V2 authorization scope",
            TEMPLATE_PATH.as_posix(),
        )

    run_request = function_node(module, "run_structured_request")
    run_request_dump = normalized_ast(run_request)
    if "observe_structured_response" not in run_request_dump:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_SEMANTIC_OBSERVER_NOT_WIRED",
            "run_structured_request does not use the typed semantic observer",
            TEMPLATE_PATH.as_posix(),
        )

    install_runtime = function_node(module, "install_runtime")
    install_strings = {
        node.value
        for node in ast.walk(install_runtime)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    if "ZERO_EXIT" in install_strings or "PASSED" not in install_strings:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_PROCESS_OUTCOME_CONTRACT_DRIFT",
            "install_runtime does not consume canonical PASSED success state",
            TEMPLATE_PATH.as_posix(),
        )

    return {
        "semantic_states": expected_states,
        "semantic_mismatch_blocks_mechanism": False,
        "finish_reason_stop_required": True,
        "response_content_digest_required": True,
        "canonical_process_success_state": "PASSED",
        "legacy_zero_exit_success_state_present": False,
        "authorization_scope": AUTHORIZATION_SCOPE,
        "predecessor_authorization_scope_reusable": False,
    }


def runtime_contract() -> RuntimeContract:
    return RuntimeContract()


def semantic_boundary() -> SemanticBoundary:
    return SemanticBoundary()


def process_outcome_contract() -> ProcessOutcomeContract:
    return ProcessOutcomeContract()


def safety() -> ExecutionSafety:
    return ExecutionSafety()


def non_claims() -> tuple[str, ...]:
    return (
        "successor_runtime_not_executed",
        "c4_semantic_qualification_not_established",
        "p5_exact_runtime_requalification_not_established",
        "p6_exact_runtime_requalification_not_established",
        "variance_adequacy_not_established",
        "final_measured_abc_not_executed",
        "quality_non_inferiority_not_established",
        "execution_authorization_issuer_not_implemented",
        "execution_authorization_not_issued",
        "production_readiness_not_claimed",
    )


def static_artifacts(repo_root: Path) -> tuple[ArtifactIdentity, ...]:
    return tuple(identity(repo_root, path) for path in STATIC_PATHS)


def build_review(repo_root: Path) -> ImplementationReview:
    authorities = validate_authorities(repo_root)
    audit_frozen_p5_p6(repo_root)
    audit_successor_contract(repo_root)
    return ImplementationReview(
        implementation_base_main_commit=IMPLEMENTATION_BASE_MAIN_COMMIT,
        authorities=authorities,
        static_artifacts=static_artifacts(repo_root),
        runtime=runtime_contract(),
        semantic_boundary=semantic_boundary(),
        process_outcome_contract=process_outcome_contract(),
        p5_evaluator_ast_identical_to_v2=True,
        p6_evaluator_ast_identical_to_v2=True,
        authorization_scope=AUTHORIZATION_SCOPE,
        predecessor_authorization_scope_reusable=False,
        safety=safety(),
        next_gate=NEXT_GATE,
        non_claims=non_claims(),
    )


def render_runtime_template(
    repo_root: Path,
    implementation_review_sha256: str,
) -> bytes:
    template = read_file(repo_root, TEMPLATE_PATH).decode("utf-8")
    addendum_sha = identity(repo_root, ADDENDUM_PATH).sha256
    replacements = {
        "__NOTEBOOK_NAME__": NOTEBOOK_NAME,
        "__SOURCE_MAIN_COMMIT__": IMPLEMENTATION_BASE_MAIN_COMMIT,
        "__IMPLEMENTATION_REVIEW_SHA256__": implementation_review_sha256,
        "__DESIGN_RECORD_SHA256__": DESIGN_SHA256,
        "__MECHANISM_ADMISSION_CONTRACT_SHA256__": MECHANISM_CONTRACT_SHA256,
        "__IMPLEMENTATION_ADDENDUM_SHA256__": addendum_sha,
        "__MODEL_SNAPSHOT_SHA256__": MODEL_SNAPSHOT_SHA256,
        "__EVIDENCE_ZIP_NAME__": EVIDENCE_ZIP_NAME,
    }
    for token, value in replacements.items():
        if template.count(token) != 1:
            raise ImplementationError(
                "P5_P6_SUCCESSOR_TEMPLATE_PLACEHOLDER_DRIFT",
                f"runtime template placeholder count drifted: {token}",
                TEMPLATE_PATH.as_posix(),
            )
        template = template.replace(token, value)
    if re.search(r"__[A-Z0-9_]+__", template) is not None:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_TEMPLATE_PLACEHOLDER_DRIFT",
            "unresolved runtime-template placeholder remains",
            TEMPLATE_PATH.as_posix(),
        )
    compile(template, TEMPLATE_PATH.as_posix(), "exec")
    return template.encode("utf-8")


def wrapper_code(runtime_source: bytes) -> tuple[bytes, str, str]:
    runtime_sha = sha256_bytes(runtime_source)
    encoded = base64.b64encode(runtime_source).decode("ascii")
    chunks = tuple(encoded[index : index + 76] for index in range(0, len(encoded), 76))
    lines = [
        "import base64 as _ag_base64",
        "import hashlib as _ag_hashlib",
        "",
        "_AG_RUNTIME_B64 = (",
        *[f'    "{chunk}"' for chunk in chunks],
        ")",
        ('_AG_RUNTIME_SOURCE = _ag_base64.b64decode("".join(_AG_RUNTIME_B64)).decode("utf-8")'),
        f'_AG_EXPECTED_RUNTIME_SHA256 = "{runtime_sha}"',
        (
            "_AG_OBSERVED_RUNTIME_SHA256 = "
            '_ag_hashlib.sha256(_AG_RUNTIME_SOURCE.encode("utf-8")).hexdigest()'
        ),
        "if _AG_OBSERVED_RUNTIME_SHA256 != _AG_EXPECTED_RUNTIME_SHA256:",
        '    raise RuntimeError("runtime script identity mismatch")',
        "EXECUTED_RUNTIME_SCRIPT_SHA256 = _AG_OBSERVED_RUNTIME_SHA256",
        "exec(",
        ('    compile(_AG_RUNTIME_SOURCE, "<auragateway-p5-p6-mechanism-successor-v1>", "exec"),'),
        "    globals(),",
        "    globals(),",
        ")",
    ]
    wrapper = ("\n".join(lines) + "\n").encode("utf-8")
    maximum_line = max(len(line) for line in wrapper.decode("utf-8").splitlines())
    if maximum_line > 100:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_NOTEBOOK_LINE_LENGTH_DRIFT",
            "generated notebook wrapper exceeds 100 characters",
            NOTEBOOK_PATH.as_posix(),
        )
    compile(wrapper.decode("utf-8"), NOTEBOOK_PATH.as_posix(), "exec")
    return wrapper, runtime_sha, sha256_bytes(wrapper)


def notebook_bytes(runtime_source: bytes) -> tuple[bytes, str, str]:
    wrapper, runtime_sha, wrapper_sha = wrapper_code(runtime_source)
    lines = wrapper.decode("utf-8").splitlines()
    code_source = [
        line + "\n" if index < len(lines) - 1 else line for index, line in enumerate(lines)
    ]
    payload = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "p5p6mechanismsuccessorv1",
                "metadata": {},
                "outputs": [],
                "source": code_source,
            }
        ],
        "metadata": {
            "accelerator": "GPU",
            "internet": False,
            "kaggle": {
                "accelerator": "nvidiaTeslaT4",
                "dataSources": [],
                "dockerImageVersionId": None,
                "isGpuEnabled": True,
                "isInternetEnabled": False,
                "language": "python",
                "sourceType": "notebook",
            },
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    notebook = (json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
    return notebook, runtime_sha, wrapper_sha


def build_generated(
    repo_root: Path,
) -> tuple[ImplementationReview, ImplementationRecord, bytes]:
    review = build_review(repo_root)
    review_bytes = review.canonical_bytes()
    review_sha = sha256_bytes(review_bytes)
    runtime_source = render_runtime_template(repo_root, review_sha)
    notebook, runtime_sha, wrapper_sha = notebook_bytes(runtime_source)
    notebook_identity = NotebookIdentity(
        path=NOTEBOOK_PATH.as_posix(),
        sha256=sha256_bytes(notebook),
        size_bytes=len(notebook),
        runtime_script_sha256=runtime_sha,
        wrapper_code_sha256=wrapper_sha,
    )
    record = ImplementationRecord(
        implementation_base_main_commit=IMPLEMENTATION_BASE_MAIN_COMMIT,
        review=ArtifactIdentity(
            path=REVIEW_PATH.as_posix(),
            sha256=review_sha,
            size_bytes=len(review_bytes),
        ),
        notebook=notebook_identity,
        static_artifacts=static_artifacts(repo_root),
        runtime=runtime_contract(),
        semantic_boundary=semantic_boundary(),
        process_outcome_contract=process_outcome_contract(),
        authorization_scope=AUTHORIZATION_SCOPE,
        predecessor_authorization_scope_reusable=False,
        p5_requalified=False,
        p6_requalified=False,
        c4_semantic_qualified=False,
        safety=safety(),
        next_gate=NEXT_GATE,
    )
    return review, record, notebook


def write_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if temporary.exists():
        raise ImplementationError(
            "P5_P6_SUCCESSOR_TEMPORARY_PATH_EXISTS",
            "temporary producer path already exists",
            path.as_posix(),
        )
    temporary.write_bytes(payload)
    temporary.replace(path)


def generated_payloads(repo_root: Path) -> dict[Path, bytes]:
    review, record, notebook = build_generated(repo_root)
    return {
        REVIEW_PATH: review.canonical_bytes(),
        RECORD_PATH: record.canonical_bytes(),
        NOTEBOOK_PATH: notebook,
    }


def write_generated(repo_root: Path) -> dict[str, object]:
    outputs = generated_payloads(repo_root)
    for relative_path, payload in outputs.items():
        write_atomic(repo_root / relative_path, payload)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_IMPLEMENTATION_GENERATED",
        "generated_path_count": len(outputs),
        "identities": {path.as_posix(): sha256_bytes(payload) for path, payload in outputs.items()},
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def check_generated(repo_root: Path) -> dict[str, object]:
    outputs = generated_payloads(repo_root)
    identities: dict[str, str] = {}
    for relative_path, expected in outputs.items():
        observed = read_file(repo_root, relative_path)
        if observed != expected:
            raise ImplementationError(
                "P5_P6_SUCCESSOR_GENERATED_ARTIFACT_DRIFT",
                "generated successor artifact is non-canonical",
                relative_path.as_posix(),
            )
        identities[relative_path.as_posix()] = sha256_bytes(observed)
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_IMPLEMENTATION_VALID",
        "generated_path_count": len(outputs),
        "candidate_path_count": len(CANDIDATE_PATHS),
        "identities": identities,
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def runtime_namespace(repo_root: Path) -> dict[str, object]:
    review = build_review(repo_root)
    runtime_source = render_runtime_template(
        repo_root,
        sha256_bytes(review.canonical_bytes()),
    )
    module_name = "auragateway_p5_p6_mechanism_successor_static"
    module = types.ModuleType(module_name)
    module.__dict__["EXECUTED_RUNTIME_SCRIPT_SHA256"] = sha256_bytes(runtime_source)
    sys.modules[module_name] = module
    exec(
        compile(runtime_source, "<p5-p6-mechanism-successor-static>", "exec"),
        module.__dict__,
        module.__dict__,
    )
    return cast(dict[str, object], module.__dict__)


def validate(repo_root: Path) -> dict[str, object]:
    require_base_ancestor(repo_root)
    authorities = validate_authorities(repo_root)
    frozen = audit_frozen_p5_p6(repo_root)
    contract = audit_successor_contract(repo_root)
    generated = check_generated(repo_root)
    if len(CANDIDATE_PATHS) != 9:
        raise ImplementationError(
            "P5_P6_SUCCESSOR_CANDIDATE_BOUNDARY_DRIFT",
            "successor implementation candidate must contain exactly nine paths",
        )
    return {
        "status": "P5_P6_MECHANISM_ADMISSION_SUCCESSOR_IMPLEMENTATION_VALID",
        "implementation_base_main_commit": IMPLEMENTATION_BASE_MAIN_COMMIT,
        "authority_count": len(authorities),
        "candidate_path_count": len(CANDIDATE_PATHS),
        "frozen_evaluators": frozen,
        "successor_contract": contract,
        "generated": generated,
        "c4_semantic_qualified": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "runtime_execution_authorized": False,
        "model_requests_performed": 0,
        "gpu_execution_performed": False,
        "kaggle_execution_performed": False,
        "next_gate": NEXT_GATE,
    }


def parser() -> _ArgumentParser:
    result = _ArgumentParser()
    mode = result.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    result.add_argument("--repo-root", default=".")
    return result


def print_error(error: ImplementationError) -> None:
    print(canonical_json_bytes(error.envelope()).decode("utf-8"), file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    try:
        result = write_generated(repo_root) if args.write else validate(repo_root)
    except ImplementationError as error:
        print_error(error)
        return 2
    print(canonical_json_bytes(result).decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

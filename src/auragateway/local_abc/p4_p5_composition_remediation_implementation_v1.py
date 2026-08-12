"""Generate and validate P4/P5 Composition Remediation V1.

The accepted P5/P6 transaction-bound runtime is immutable input authority.
This producer emits a separate successor runtime under the frozen remediation
contract. It changes only the two cache-context instruction tails required by
the design and adds failure-safe pre-request token-identity evidence.

This module performs no Kaggle execution and issues no execution authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "57380a5b0a4771cd5a373daa81dee32b5f3f7c00"
DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_design_v1.json"
)
DESIGN_SHA256: Final = "ac737bccf6459951877b6695a6a6d368a81cba9318d6cee2656af48b6711c5ea"
PREDECESSOR_PATH: Final = Path("src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py")
PREDECESSOR_SHA256: Final = "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_remediation_implementation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_composition_remediation_implementation_v1.py"
)
SUCCESSOR_PATH: Final = Path("src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py")
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1.json"
)
REPORT_PATH: Final = Path(
    "docs/reports/AuraGateway_P4_P5_Composition_Remediation_Implementation_V1.md"
)
RUNBOOK_PATH: Final = Path(
    "docs/runbooks/local_abc_p4_p5_composition_remediation_implementation_v1.md"
)

V5_INSTRUCTION: Final = (
    "For structured probes, return only the exact JSON object supplied in the final user message."
)
V4_INSTRUCTION: Final = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
V5_SOURCE_LINE: Final = (
    '    "For structured probes, return only the exact JSON object supplied in '
    'the final user message."'
)
V4_SOURCE_LINES: Final = (
    '    "Return only the exact JSON object supplied in the final user message, "\n'
    '    "with no markdown or additional text."'
)
JOURNAL_NAME: Final = "pre_request_token_identity_journal_v1.json"
NEXT_GATE: Final = "MERGE_THEN_DESIGN_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1"
CHANGED_EXISTING_FUNCTIONS: Final = ("main", "run_structured_request")
ADDED_FUNCTIONS: Final = (
    "_read_pre_request_token_identity_journal",
    "initialize_pre_request_token_identity_journal",
    "persist_pre_request_token_identity",
)
CHANGED_EXISTING_GLOBALS: Final = (
    "OUTPUT_NAMES",
    "SYNTHETIC_CACHE_CONTEXT_A",
    "SYNTHETIC_CACHE_CONTEXT_B",
)
ADDED_GLOBALS: Final = ("PRE_REQUEST_TOKEN_IDENTITY_JOURNAL",)


class ImplementationError(RuntimeError):
    """Fail-closed static remediation implementation error."""

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
        raise ImplementationError("P4_P5_REMEDIATION_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImplementationReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p4-p5-composition-remediation-implementation-v1-review"]
    status: Literal["APPROVED_STATIC_REMEDIATION_IMPLEMENTATION"]
    base_main_commit: Literal["57380a5b0a4771cd5a373daa81dee32b5f3f7c00"]
    design_record_sha256: Literal[
        "ac737bccf6459951877b6695a6a6d368a81cba9318d6cee2656af48b6711c5ea"
    ]
    predecessor_runtime_sha256: Literal[
        "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
    ]
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    focused_test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runbook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    changed_existing_functions: tuple[str, ...]
    added_functions: tuple[str, ...]
    changed_existing_globals: tuple[str, ...]
    added_globals: tuple[str, ...]
    unchanged_existing_function_count: int = Field(ge=1)
    unchanged_existing_class_count: int = Field(ge=1)
    predecessor_runtime_preserved: Literal[True] = True
    v5_cache_context_tail_occurrences_before: Literal[2] = 2
    v5_cache_context_tail_occurrences_after: Literal[0] = 0
    v4_cache_context_tail_occurrences_after: Literal[2] = 2
    message_composition_preserved: Literal[True] = True
    generation_controls_preserved: Literal[True] = True
    p5_decision_semantics_preserved: Literal[True] = True
    p6_decision_semantics_preserved: Literal[True] = True
    pre_request_journal_added: Literal[True] = True
    journal_persisted_before_metric_snapshot: Literal[True] = True
    journal_persisted_before_budget_consumption: Literal[True] = True
    journal_persisted_before_chat_completion: Literal[True] = True
    request_payload_reused_after_hashing: Literal[True] = True
    raw_prompt_retained: Literal[False] = False
    raw_model_output_retained: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal["MERGE_THEN_DESIGN_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1"]

    @model_validator(mode="after")
    def validate_surface(self) -> Self:
        if self.changed_existing_functions != CHANGED_EXISTING_FUNCTIONS:
            raise ValueError("changed existing function inventory drifted")
        if self.added_functions != ADDED_FUNCTIONS:
            raise ValueError("added function inventory drifted")
        if self.changed_existing_globals != CHANGED_EXISTING_GLOBALS:
            raise ValueError("changed existing global inventory drifted")
        if self.added_globals != ADDED_GLOBALS:
            raise ValueError("added global inventory drifted")
        return self


class ImplementationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p4-p5-composition-remediation-implementation-v1"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    base_main_commit: Literal["57380a5b0a4771cd5a373daa81dee32b5f3f7c00"]
    design_record_sha256: Literal[
        "ac737bccf6459951877b6695a6a6d368a81cba9318d6cee2656af48b6711c5ea"
    ]
    predecessor_runtime_path: Literal[
        "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
    ]
    predecessor_runtime_sha256: Literal[
        "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
    ]
    successor_runtime_path: Literal[
        "src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py"
    ]
    successor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    pre_request_evidence_artifact: Literal["pre_request_token_identity_journal_v1.json"]
    remediation_implemented: Literal[True] = True
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    model_requests_performed: Literal[0] = 0
    model_loads_performed: Literal[0] = 0
    worker_starts_performed: Literal[0] = 0
    case_c_authorized: Literal[False] = False
    next_gate: Literal["MERGE_THEN_DESIGN_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1"]
    non_claims: tuple[str, ...] = Field(min_length=8)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ImplementationError(
            "P4_P5_REMEDIATION_ARTIFACT_MISSING",
            "required implementation artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _read_exact(root: Path, relative: Path, expected_sha256: str) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected_sha256:
        raise ImplementationError(
            "P4_P5_REMEDIATION_AUTHORITY_DRIFT",
            "required implementation authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _read_object(root: Path, relative: Path, expected_sha256: str) -> dict[str, object]:
    payload = _read_exact(root, relative, expected_sha256)
    try:
        observed: object = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ImplementationError(
            "P4_P5_REMEDIATION_AUTHORITY_INVALID",
            "required authority is not valid JSON",
            relative.as_posix(),
        ) from error
    if not isinstance(observed, dict):
        raise ImplementationError(
            "P4_P5_REMEDIATION_AUTHORITY_INVALID",
            "required authority must be one object",
            relative.as_posix(),
        )
    return cast(dict[str, object], observed)


def _validate_design(root: Path) -> None:
    design = _read_object(root, DESIGN_PATH, DESIGN_SHA256)
    intervention = design.get("intervention")
    invariants = design.get("composition_invariants")
    controls = design.get("generation_controls")
    journal = design.get("pre_request_evidence_control")
    acceptance = design.get("full_runtime_acceptance")
    safety = design.get("safety")
    if not all(
        isinstance(item, dict)
        for item in (intervention, invariants, controls, journal, acceptance, safety)
    ):
        raise ImplementationError(
            "P4_P5_REMEDIATION_DESIGN_DRIFT",
            "merged remediation design shape drifted",
            DESIGN_PATH.as_posix(),
        )
    assert isinstance(intervention, dict)
    assert isinstance(invariants, dict)
    assert isinstance(controls, dict)
    assert isinstance(journal, dict)
    assert isinstance(acceptance, dict)
    assert isinstance(safety, dict)
    if (
        design.get("design_status") != "DESIGN_FROZEN_NOT_IMPLEMENTED"
        or design.get("next_gate") != "IMPLEMENT_AND_MERGE_P4_P5_COMPOSITION_REMEDIATION_V1"
        or intervention.get("intervention_id")
        != "REPLACE_V5_CACHE_CONTEXT_INSTRUCTION_WITH_ACCEPTED_V4_INSTRUCTION"
        or intervention.get("replacement_scope") != "CACHE_CONTEXT_INSTRUCTION_TAIL_ONLY"
        or intervention.get("target_constants")
        != ["SYNTHETIC_CACHE_CONTEXT_A", "SYNTHETIC_CACHE_CONTEXT_B"]
        or intervention.get("expected_predecessor_occurrences") != 2
        or intervention.get("expected_successor_occurrences_of_before") != 0
        or intervention.get("expected_successor_occurrences_of_after_in_cache_contexts") != 2
        or invariants.get("message_roles") != ["system", "user", "assistant", "user"]
        or invariants.get("synthetic_assistant_ack_preserved") is not True
        or invariants.get("cache_context_repetition_count") != 24
        or invariants.get("prefix_variants_preserved") != ["A", "B"]
        or invariants.get("prefix_caching_preserved") is not True
        or invariants.get("p5_decision_semantics_preserved") is not True
        or invariants.get("p6_decision_semantics_preserved") is not True
        or controls.get("temperature") != 0
        or controls.get("top_p") != 1
        or controls.get("repetition_penalty") != 1.1
        or controls.get("seed") != 7
        or controls.get("max_tokens") != 32
        or controls.get("response_format_present") is not False
        or journal.get("artifact_name") != JOURNAL_NAME
        or journal.get("persist_after_tokenization") is not True
        or journal.get("persist_before_metric_snapshot") is not True
        or journal.get("persist_before_model_request_budget_consumption") is not True
        or journal.get("persist_before_chat_completion_request") is not True
        or journal.get("atomic_write_required") is not True
        or journal.get("payload_hash_only") is not True
        or acceptance.get("maximum_model_requests") != 6
        or acceptance.get("maximum_model_loads") != 3
        or acceptance.get("maximum_worker_starts") != 3
        or acceptance.get("p5_required_state") != "PASS"
        or acceptance.get("p6_required_state") != "PASS"
        or safety.get("runtime_execution_authorized") is not False
        or safety.get("new_execution_authorized") is not False
        or safety.get("remediation_implemented") is not False
    ):
        raise ImplementationError(
            "P4_P5_REMEDIATION_DESIGN_DRIFT",
            "merged remediation design no longer matches implementation contract",
            DESIGN_PATH.as_posix(),
        )


def _function_map(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    result: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            result[node.name] = node
    return result


def _class_map(tree: ast.Module) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}


def _global_assignment_map(tree: ast.Module) -> dict[str, ast.AST]:
    result: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                result[target.id] = node
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            result[node.target.id] = node
    return result


def _dump(node: ast.AST) -> str:
    return ast.dump(node, annotate_fields=True, include_attributes=False)


def _source_segment(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is None:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "unable to recover generated source segment",
        )
    return segment


def _insert_once(source: str, needle: str, replacement: str, label: str) -> str:
    if source.count(needle) != 1:
        raise ImplementationError(
            "P4_P5_REMEDIATION_PREDECESSOR_DRIFT",
            f"expected exactly one insertion anchor for {label}",
            PREDECESSOR_PATH.as_posix(),
        )
    return source.replace(needle, replacement, 1)


def _build_successor_text(predecessor: str) -> str:
    if predecessor.count(V5_SOURCE_LINE) != 2:
        raise ImplementationError(
            "P4_P5_REMEDIATION_V5_OCCURRENCE_DRIFT",
            "predecessor no longer has exactly two V5 cache-context instruction tails",
            PREDECESSOR_PATH.as_posix(),
        )
    successor = predecessor.replace(V5_SOURCE_LINE, V4_SOURCE_LINES)

    evidence_anchor = 'EVIDENCE_ZIP = WORK_ROOT / "ag-p5-p6-transaction-bound-evidence-v1.zip"\n'
    evidence_insert = evidence_anchor + (
        "PRE_REQUEST_TOKEN_IDENTITY_JOURNAL = OUTPUT_ROOT / "
        '"pre_request_token_identity_journal_v1.json"\n'
    )
    successor = _insert_once(
        successor,
        evidence_anchor,
        evidence_insert,
        "pre-request journal path",
    )

    output_anchor = '    "c4_output_contract_report_v1.json",\n'
    output_insert = output_anchor + '    "pre_request_token_identity_journal_v1.json",\n'
    successor = _insert_once(
        successor,
        output_anchor,
        output_insert,
        "journal output member",
    )

    token_anchor = """def validate_structured_response(
    content: str,
    expected_json: str,
) -> dict[str, object]:
"""
    journal_functions = """def _read_pre_request_token_identity_journal() -> dict[str, object]:
    if not PRE_REQUEST_TOKEN_IDENTITY_JOURNAL.is_file():
        raise RuntimeError("pre-request token-identity journal is unavailable")
    try:
        raw: object = json.loads(PRE_REQUEST_TOKEN_IDENTITY_JOURNAL.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError("pre-request token-identity journal is invalid") from error
    if not isinstance(raw, dict):
        raise RuntimeError("pre-request token-identity journal root is invalid")
    result: dict[str, object] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            raise RuntimeError("pre-request token-identity journal key is invalid")
        result[key] = value
    return result


def initialize_pre_request_token_identity_journal() -> None:
    if PRE_REQUEST_TOKEN_IDENTITY_JOURNAL.exists():
        raise RuntimeError("pre-request token-identity journal already exists")
    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            "schema_version": "1.0.0",
            "journal_id": (
                "auragateway-p4-p5-composition-remediation-pre-request-token-identity-v1"
            ),
            "entries": [],
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
        },
    )


def persist_pre_request_token_identity(
    request_ordinal: int,
    token_identity: TokenIdentityObservation,
    payload_sha256: str,
) -> None:
    journal = _read_pre_request_token_identity_journal()
    entries = journal.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError("pre-request token-identity journal entries are invalid")
    if request_ordinal != len(entries) + 1:
        raise RuntimeError("pre-request token-identity request ordinal drifted")
    if re.fullmatch(r"[0-9a-f]{64}", payload_sha256) is None:
        raise RuntimeError("pre-request payload identity is invalid")
    entry = {
        "request_ordinal": request_ordinal,
        "request_role": token_identity.request_role,
        "prefix_variant": token_identity.prefix_variant,
        "token_count": token_identity.token_count,
        "token_sha256": token_identity.token_sha256,
        "token_ids": list(token_identity.token_ids),
        "payload_sha256": payload_sha256,
        "persisted_before_model_request": True,
    }
    updated = {**journal, "entries": [*entries, entry]}
    write_json(PRE_REQUEST_TOKEN_IDENTITY_JOURNAL, updated)


"""
    successor = _insert_once(
        successor,
        token_anchor,
        journal_functions + token_anchor,
        "journal functions",
    )

    old_request = """def run_structured_request(
    worker: Worker,
    request_role: str,
    prefix_variant: str,
    counters: dict[str, int],
) -> dict[str, object]:
    token_identity = tokenize_request(
        worker,
        request_role=request_role,
        prefix_variant=prefix_variant,
    )
    before = worker.metric_snapshot()
    consume_actions(counters, "model_requests")
    request_id = (
        f"{request_role.lower()}-"
        f"{worker.worker_id}-g{worker.generation}-"
        f"{counters['model_requests']}"
    )
    response = post_json(
        f"http://127.0.0.1:{worker.port}/v1/chat/completions",
        request_payload(prefix_variant),
    )
"""
    new_request = """def run_structured_request(
    worker: Worker,
    request_role: str,
    prefix_variant: str,
    counters: dict[str, int],
) -> dict[str, object]:
    token_identity = tokenize_request(
        worker,
        request_role=request_role,
        prefix_variant=prefix_variant,
    )
    request_ordinal = counters["model_requests"] + 1
    payload = request_payload(prefix_variant)
    persist_pre_request_token_identity(
        request_ordinal,
        token_identity,
        sha256_text(canonical_json(payload)),
    )
    before = worker.metric_snapshot()
    consume_actions(counters, "model_requests")
    request_id = (
        f"{request_role.lower()}-"
        f"{worker.worker_id}-g{worker.generation}-"
        f"{counters['model_requests']}"
    )
    response = post_json(
        f"http://127.0.0.1:{worker.port}/v1/chat/completions",
        payload,
    )
"""
    successor = _insert_once(
        successor,
        old_request,
        new_request,
        "run_structured_request instrumentation",
    )

    main_anchor = """    OUTPUT_ROOT.mkdir(parents=True)
    LOG_ROOT.mkdir()
    SCRATCH_ROOT.mkdir()

    counters = {
"""
    main_insert = """    OUTPUT_ROOT.mkdir(parents=True)
    LOG_ROOT.mkdir()
    SCRATCH_ROOT.mkdir()
    initialize_pre_request_token_identity_journal()

    counters = {
"""
    successor = _insert_once(
        successor,
        main_anchor,
        main_insert,
        "journal initialization",
    )
    return successor


def _validate_static_surface(predecessor: str, successor: str) -> dict[str, int]:
    predecessor_tree = ast.parse(predecessor)
    successor_tree = ast.parse(successor)
    predecessor_functions = _function_map(predecessor_tree)
    successor_functions = _function_map(successor_tree)
    predecessor_classes = _class_map(predecessor_tree)
    successor_classes = _class_map(successor_tree)
    predecessor_globals = _global_assignment_map(predecessor_tree)
    successor_globals = _global_assignment_map(successor_tree)

    added_functions = tuple(sorted(set(successor_functions) - set(predecessor_functions)))
    if added_functions != tuple(sorted(ADDED_FUNCTIONS)):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "added function inventory drifted",
            SUCCESSOR_PATH.as_posix(),
        )
    removed_functions = set(predecessor_functions) - set(successor_functions)
    if removed_functions:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "predecessor function was removed",
            SUCCESSOR_PATH.as_posix(),
        )
    changed_functions = tuple(
        sorted(
            name
            for name in predecessor_functions
            if _dump(predecessor_functions[name]) != _dump(successor_functions[name])
        )
    )
    if changed_functions != tuple(sorted(CHANGED_EXISTING_FUNCTIONS)):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "changed existing function inventory drifted",
            SUCCESSOR_PATH.as_posix(),
        )

    if set(predecessor_classes) != set(successor_classes):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "class inventory drifted",
            SUCCESSOR_PATH.as_posix(),
        )
    changed_classes = tuple(
        name
        for name in predecessor_classes
        if _dump(predecessor_classes[name]) != _dump(successor_classes[name])
    )
    if changed_classes:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "existing class semantics drifted",
            SUCCESSOR_PATH.as_posix(),
        )

    added_globals = tuple(sorted(set(successor_globals) - set(predecessor_globals)))
    if added_globals != tuple(sorted(ADDED_GLOBALS)):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "added global inventory drifted",
            SUCCESSOR_PATH.as_posix(),
        )
    removed_globals = set(predecessor_globals) - set(successor_globals)
    if removed_globals:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "predecessor global was removed",
            SUCCESSOR_PATH.as_posix(),
        )
    changed_globals = tuple(
        sorted(
            name
            for name in predecessor_globals
            if _dump(predecessor_globals[name]) != _dump(successor_globals[name])
        )
    )
    if changed_globals != tuple(sorted(CHANGED_EXISTING_GLOBALS)):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "changed existing global inventory drifted",
            SUCCESSOR_PATH.as_posix(),
        )

    if successor.count(V5_INSTRUCTION) != 0:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "successor still contains the V5 cache-context instruction",
            SUCCESSOR_PATH.as_posix(),
        )
    for constant_name in ("SYNTHETIC_CACHE_CONTEXT_A", "SYNTHETIC_CACHE_CONTEXT_B"):
        node = successor_globals.get(constant_name)
        if node is None:
            raise ImplementationError(
                "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
                "successor cache-context constant is missing",
                SUCCESSOR_PATH.as_posix(),
            )
        literal_values = [
            item.value
            for item in ast.walk(node)
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        if V4_INSTRUCTION not in literal_values:
            raise ImplementationError(
                "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
                "successor cache-context V4 tail is incomplete",
                SUCCESSOR_PATH.as_posix(),
            )

    request_segment = _source_segment(
        successor,
        successor_functions["run_structured_request"],
    )
    ordered_markers = (
        "token_identity = tokenize_request(",
        'request_ordinal = counters["model_requests"] + 1',
        "payload = request_payload(prefix_variant)",
        "persist_pre_request_token_identity(",
        "before = worker.metric_snapshot()",
        'consume_actions(counters, "model_requests")',
        'f"http://127.0.0.1:{worker.port}/v1/chat/completions"',
        "payload,",
    )
    positions = tuple(request_segment.find(marker) for marker in ordered_markers)
    if any(position < 0 for position in positions) or positions != tuple(sorted(positions)):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "pre-request journal ordering contract drifted",
            SUCCESSOR_PATH.as_posix(),
        )
    if "request_payload(prefix_variant)," in request_segment:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "chat completion did not reuse the payload whose identity was journaled",
            SUCCESSOR_PATH.as_posix(),
        )

    main_segment = _source_segment(successor, successor_functions["main"])
    if "initialize_pre_request_token_identity_journal()" not in main_segment:
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "pre-request journal initialization is missing",
            SUCCESSOR_PATH.as_posix(),
        )
    output_node = successor_globals.get("OUTPUT_NAMES")
    if output_node is None or JOURNAL_NAME not in _source_segment(successor, output_node):
        raise ImplementationError(
            "P4_P5_REMEDIATION_STATIC_PROOF_FAILED",
            "pre-request journal is absent from the evidence bundle contract",
            SUCCESSOR_PATH.as_posix(),
        )
    return {
        "unchanged_existing_function_count": (
            len(predecessor_functions) - len(CHANGED_EXISTING_FUNCTIONS)
        ),
        "unchanged_existing_class_count": len(predecessor_classes),
    }


def _expected_successor(root: Path) -> tuple[bytes, dict[str, int]]:
    _validate_design(root)
    predecessor_bytes = _read_exact(root, PREDECESSOR_PATH, PREDECESSOR_SHA256)
    predecessor = predecessor_bytes.decode("utf-8")
    successor = _build_successor_text(predecessor)
    proof = _validate_static_surface(predecessor, successor)
    return successor.encode("utf-8"), proof


def _build_review(
    root: Path,
    successor_payload: bytes,
    proof: dict[str, int],
) -> ImplementationReview:
    return ImplementationReview(
        review_id=("auragateway-p4-p5-composition-remediation-implementation-v1-review"),
        status="APPROVED_STATIC_REMEDIATION_IMPLEMENTATION",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_sha256=PREDECESSOR_SHA256,
        implementation_source_sha256=_sha256(_read_required(root, SOURCE_PATH)),
        focused_test_sha256=_sha256(_read_required(root, TEST_PATH)),
        report_sha256=_sha256(_read_required(root, REPORT_PATH)),
        runbook_sha256=_sha256(_read_required(root, RUNBOOK_PATH)),
        successor_runtime_sha256=_sha256(successor_payload),
        changed_existing_functions=CHANGED_EXISTING_FUNCTIONS,
        added_functions=ADDED_FUNCTIONS,
        changed_existing_globals=CHANGED_EXISTING_GLOBALS,
        added_globals=ADDED_GLOBALS,
        unchanged_existing_function_count=proof["unchanged_existing_function_count"],
        unchanged_existing_class_count=proof["unchanged_existing_class_count"],
        predecessor_runtime_preserved=True,
        v5_cache_context_tail_occurrences_before=2,
        v5_cache_context_tail_occurrences_after=0,
        v4_cache_context_tail_occurrences_after=2,
        message_composition_preserved=True,
        generation_controls_preserved=True,
        p5_decision_semantics_preserved=True,
        p6_decision_semantics_preserved=True,
        pre_request_journal_added=True,
        journal_persisted_before_metric_snapshot=True,
        journal_persisted_before_budget_consumption=True,
        journal_persisted_before_chat_completion=True,
        request_payload_reused_after_hashing=True,
        raw_prompt_retained=False,
        raw_model_output_retained=False,
        runtime_execution_authorized=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def _build_record(
    successor_payload: bytes,
    review_payload: bytes,
) -> ImplementationRecord:
    return ImplementationRecord(
        record_id="auragateway-p4-p5-composition-remediation-implementation-v1",
        status="IMPLEMENTED_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_path=PREDECESSOR_PATH.as_posix(),
        predecessor_runtime_sha256=PREDECESSOR_SHA256,
        successor_runtime_path=SUCCESSOR_PATH.as_posix(),
        successor_runtime_sha256=_sha256(successor_payload),
        implementation_review_sha256=_sha256(review_payload),
        pre_request_evidence_artifact=JOURNAL_NAME,
        remediation_implemented=True,
        runtime_execution_authorized=False,
        new_execution_authorized=False,
        kaggle_execution_performed=False,
        gpu_execution_performed=False,
        model_requests_performed=0,
        model_loads_performed=0,
        worker_starts_performed=0,
        case_c_authorized=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "The remediation has not been executed on Kaggle.",
            "No runtime execution authority is issued by this implementation.",
            "No model has been loaded by this implementation tranche.",
            "No worker has been started by this implementation tranche.",
            "No model request has been performed by this implementation tranche.",
            "P5 remediation success is not established until governed execution.",
            "P6 remediation success is not established until governed execution.",
            "The V5 cache-context tail is not claimed to be the sole causal factor.",
            "Case C remains unauthorized.",
            "Production readiness is not established.",
        ),
    )


def generate(root: Path) -> ImplementationRecord:
    successor_payload, proof = _expected_successor(root)
    (root / SUCCESSOR_PATH).write_bytes(successor_payload)
    review = _build_review(root, successor_payload, proof)
    review_payload = _canonical_bytes(review.model_dump(mode="json"))
    (root / REVIEW_PATH).write_bytes(review_payload)
    record = _build_record(successor_payload, review_payload)
    (root / RECORD_PATH).write_bytes(_canonical_bytes(record.model_dump(mode="json")))
    return record


def validate_generated(root: Path) -> ImplementationRecord:
    successor_payload, proof = _expected_successor(root)
    observed_successor = _read_required(root, SUCCESSOR_PATH)
    if observed_successor != successor_payload:
        raise ImplementationError(
            "P4_P5_REMEDIATION_GENERATED_RUNTIME_DRIFT",
            "generated remediation runtime differs from deterministic successor",
            SUCCESSOR_PATH.as_posix(),
        )
    review = _build_review(root, successor_payload, proof)
    expected_review = _canonical_bytes(review.model_dump(mode="json"))
    if _read_required(root, REVIEW_PATH) != expected_review:
        raise ImplementationError(
            "P4_P5_REMEDIATION_REVIEW_DRIFT",
            "implementation review differs from deterministic review",
            REVIEW_PATH.as_posix(),
        )
    record = _build_record(successor_payload, expected_review)
    expected_record = _canonical_bytes(record.model_dump(mode="json"))
    if _read_required(root, RECORD_PATH) != expected_record:
        raise ImplementationError(
            "P4_P5_REMEDIATION_RECORD_DRIFT",
            "implementation record differs from deterministic record",
            RECORD_PATH.as_posix(),
        )
    return record


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument("action", choices=("generate", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        args = parser.parse_args(argv)
        root = args.repo_root.resolve()
        record = generate(root) if args.action == "generate" else validate_generated(root)
    except ImplementationError as error:
        print(json.dumps(error.envelope(), separators=(",", ":"), sort_keys=True))
        return 2
    print(json.dumps(record.model_dump(mode="json"), separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

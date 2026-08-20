"""Generate C4 paragraph-order behavioral differential runtime V1.

The merged paragraph-order design and governed C4 runtime are immutable
authorities. This producer emits a separate execution-inert successor runtime
for the frozen six-observation control/treatment diagnostic.

No model, GPU, Kaggle, worker, request, or live authorization execution occurs
inside this producer.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Final, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "5445caddf8f5331bbf0f9f5cbb06fd768230067f"

DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_c4_paragraph_order_behavioral_differential_design_v1.json"
)
DESIGN_SHA256: Final = "92bd8194cea68783116bc934b57ae0b1b3a675d0a0ad7dabfa05c680a4755ce9"

PREDECESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/canonical_synthetic_prefix_c4_behavioral_qualification_runtime_v1.py"
)
PREDECESSOR_RUNTIME_SHA256: Final = (
    "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82"
)

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/c4_paragraph_order_behavioral_differential_implementation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_c4_paragraph_order_behavioral_differential_implementation_v1.py"
)
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/c4_paragraph_order_behavioral_differential_runtime_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_c4_paragraph_order_behavioral_differential_implementation_v1.json"
)

CONTROL_CONDITION: Final = "CONTROL_ORIGINAL_C4"
TREATMENT_CONDITION: Final = "TREATMENT_REVERSED_MIDDLE_EIGHT"
REQUEST_ORDER: Final = (
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
    TREATMENT_CONDITION,
    CONTROL_CONDITION,
    CONTROL_CONDITION,
    TREATMENT_CONDITION,
)

CONTROL_TOKEN_SHA256: Final = "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
TREATMENT_TOKEN_SHA256: Final = "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
CONTROL_REQUEST_PAYLOAD_SHA256: Final = (
    "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
)
HISTORICAL_CONTROL_PARSED_OBJECT_SHA256: Final = (
    "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
)

PROMPT_TOKEN_COUNT: Final = 899
FINAL_USER_BOUNDARY: Final = 880
CONTROL_TREATMENT_COMMON_SUFFIX_COUNT: Final = 122
PARAGRAPH_COUNT: Final = 10
CONTROL_PARAGRAPH_ORDER: Final = tuple(range(1, 11))
TREATMENT_PARAGRAPH_ORDER: Final = (1, 9, 8, 7, 6, 5, 4, 3, 2, 10)

CHANGED_EXISTING_FUNCTIONS: Final = ("main",)
ADDED_FUNCTIONS: Final = (
    "decide_order_differential",
    "initialize_order_journal",
    "order_bundle_outputs",
    "order_condition_status",
    "order_context",
    "order_expected_payload_sha256",
    "order_expected_token_sha256",
    "order_public_observation",
    "order_request_messages",
    "order_request_payload",
    "order_token_identity",
    "order_token_sequence",
    "order_tokenize_payload",
    "persist_order_pre_request_identity",
    "run_order_fresh_worker_observation",
    "run_order_observation",
    "write_order_results",
)

NEXT_GATE: Final = (
    "MERGE_THEN_DESIGN_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
)

EXPECTED_RUFF_VERSION: Final = "ruff 0.15.21"
RUNTIME_FORMATTER_ARGS: Final = (
    "--isolated",
    "--config",
    'format.quote-style = "double"',
    "--config",
    'format.indent-style = "space"',
    "--config",
    'format.line-ending = "lf"',
    "format",
    "--target-version",
    "py311",
    "--line-length",
    "100",
    "--stdin-filename",
    RUNTIME_PATH.as_posix(),
    "-",
)


class ImplementationError(RuntimeError):
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
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImplementationReview(FrozenModel):
    schema_version: str = "1.0.0"
    review_id: str
    status: str
    base_main_commit: str
    design_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    focused_test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    treatment_request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_order: tuple[str, ...]
    changed_existing_functions: tuple[str, ...]
    added_functions: tuple[str, ...]
    prompt_token_count_per_condition: int
    final_user_boundary_per_condition: int
    observations_per_condition: int
    maximum_model_requests: int
    maximum_model_loads: int
    maximum_worker_starts: int
    maximum_worker_teardowns: int
    maximum_hidden_retries: int
    maximum_replacement_observations: int
    fresh_worker_process_per_observation: bool
    control_anchor_requires_historical_parsed_identity: bool
    treatment_exact_object_restoration_rule_preserved: bool
    treatment_same_phenotype_rule_preserved: bool
    treatment_changed_phenotype_rule_preserved: bool
    treatment_ambiguous_rule_preserved: bool
    static_token_multiset_premise_reexecuted: bool
    runtime_execution_authorized: bool
    new_execution_authorized: bool
    next_gate: str

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.status != "APPROVED_STATIC_PARAGRAPH_ORDER_DIFFERENTIAL_HARNESS":
            raise ValueError("implementation review status drifted")
        if self.request_order != REQUEST_ORDER:
            raise ValueError("request order drifted")
        if self.changed_existing_functions != CHANGED_EXISTING_FUNCTIONS:
            raise ValueError("changed existing function inventory drifted")
        if self.added_functions != ADDED_FUNCTIONS:
            raise ValueError("added function inventory drifted")
        if (
            self.prompt_token_count_per_condition,
            self.final_user_boundary_per_condition,
            self.observations_per_condition,
        ) != (899, 880, 3):
            raise ValueError("frozen experiment cardinality drifted")
        if (
            self.maximum_model_requests,
            self.maximum_model_loads,
            self.maximum_worker_starts,
            self.maximum_worker_teardowns,
        ) != (6, 6, 6, 6):
            raise ValueError("runtime action budget drifted")
        if self.maximum_hidden_retries != 0:
            raise ValueError("hidden retry budget drifted")
        if self.maximum_replacement_observations != 0:
            raise ValueError("replacement budget drifted")
        required = (
            self.fresh_worker_process_per_observation,
            self.control_anchor_requires_historical_parsed_identity,
            self.treatment_exact_object_restoration_rule_preserved,
            self.treatment_same_phenotype_rule_preserved,
            self.treatment_changed_phenotype_rule_preserved,
            self.treatment_ambiguous_rule_preserved,
        )
        if not all(required):
            raise ValueError("required behavioral control is disabled")
        if self.static_token_multiset_premise_reexecuted:
            raise ValueError("implementation producer may not promote static premise")
        if self.runtime_execution_authorized or self.new_execution_authorized:
            raise ValueError("static implementation crossed authority boundary")
        return self


class ImplementationRecord(FrozenModel):
    schema_version: str = "1.0.0"
    record_id: str
    status: str
    base_main_commit: str
    design_record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    predecessor_runtime_path: str
    predecessor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    successor_runtime_path: str
    successor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    implementation_review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    control_request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    treatment_request_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_requests_performed: int
    model_loads_performed: int
    worker_starts_performed: int
    kaggle_execution_performed: bool
    gpu_execution_performed: bool
    live_authorization_issued: bool
    runtime_execution_authorized: bool
    new_execution_authorized: bool
    p5_requalified: bool
    p6_requalified: bool
    final_abc_measured: bool
    production_readiness_established: bool
    next_gate: str
    non_claims: tuple[str, ...] = Field(min_length=10)

    @model_validator(mode="after")
    def exact(self) -> Self:
        if self.status != "IMPLEMENTED_NOT_EXECUTED":
            raise ValueError("implementation status drifted")
        if any(
            (
                self.model_requests_performed,
                self.model_loads_performed,
                self.worker_starts_performed,
            )
        ):
            raise ValueError("static implementation recorded runtime execution")
        prohibited = (
            self.kaggle_execution_performed,
            self.gpu_execution_performed,
            self.live_authorization_issued,
            self.runtime_execution_authorized,
            self.new_execution_authorized,
            self.p5_requalified,
            self.p6_requalified,
            self.final_abc_measured,
            self.production_readiness_established,
        )
        if any(prohibited):
            raise ValueError("static implementation overclaimed state")
        return self


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_ARTIFACT_MISSING",
            "required artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _read_exact(
    root: Path,
    relative: Path,
    expected_sha256: str,
) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected_sha256:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_AUTHORITY_DRIFT",
            "required authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _base_commit_is_ancestor_of_head(root: Path) -> bool:
    result = subprocess.run(
        [
            "git",
            "merge-base",
            "--is-ancestor",
            BASE_MAIN_COMMIT,
            "HEAD",
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise ImplementationError(
        "C4_PARAGRAPH_ORDER_IMPLEMENTATION_GIT_STATE_INVALID",
        "unable to verify implementation base ancestry",
    )


def _mapping(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            f"{label} is not an object",
            DESIGN_PATH.as_posix(),
        )
    return cast(dict[str, object], value)


def _array(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            f"{label} is not an array",
            DESIGN_PATH.as_posix(),
        )
    return cast(list[object], value)


def _validate_design(root: Path) -> dict[str, object]:
    if not _base_commit_is_ancestor_of_head(root):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_BASE_MAIN_DRIFT",
            "implementation base is not an ancestor of HEAD",
        )

    payload = _read_exact(
        root,
        DESIGN_PATH,
        DESIGN_SHA256,
    )
    try:
        parsed: object = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_INVALID",
            "frozen design is not valid JSON",
            DESIGN_PATH.as_posix(),
        ) from error

    design = _mapping(parsed, "design")

    expected_scalars: dict[str, object] = {
        "record_id": ("auragateway-c4-paragraph-order-behavioral-differential-design-v1"),
        "design_status": "DESIGN_FROZEN_NOT_EXECUTED",
        "next_gate": ("IMPLEMENT_AND_MERGE_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"),
    }
    for key, expected_scalar in expected_scalars.items():
        if design.get(key) != expected_scalar:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
                f"design.{key} drifted",
                key,
            )

    conditions = _array(design.get("conditions"), "conditions")
    if len(conditions) != 2:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            "condition cardinality drifted",
        )

    control = _mapping(conditions[0], "control")
    treatment = _mapping(conditions[1], "treatment")

    control_expected: dict[str, object] = {
        "condition_id": CONTROL_CONDITION,
        "role": "CONTEMPORANEOUS_FAILURE_ANCHOR",
        "prompt_token_count": PROMPT_TOKEN_COUNT,
        "prompt_token_sha256": CONTROL_TOKEN_SHA256,
        "paragraph_count": PARAGRAPH_COUNT,
        "paragraph_order": list(CONTROL_PARAGRAPH_ORDER),
        "final_user_boundary": FINAL_USER_BOUNDARY,
        "historical_exact_object_result": "0_OF_3",
        "historical_canonical_parsed_object_sha256": (HISTORICAL_CONTROL_PARSED_OBJECT_SHA256),
    }
    treatment_expected: dict[str, object] = {
        "condition_id": TREATMENT_CONDITION,
        "role": "ORDER_INTERVENTION",
        "prompt_token_count": PROMPT_TOKEN_COUNT,
        "prompt_token_sha256": TREATMENT_TOKEN_SHA256,
        "paragraph_count": PARAGRAPH_COUNT,
        "paragraph_order": list(TREATMENT_PARAGRAPH_ORDER),
        "final_user_boundary": FINAL_USER_BOUNDARY,
        "historical_exact_object_result": "NOT_EXECUTED",
        "historical_canonical_parsed_object_sha256": None,
    }

    for key, expected_control_value in control_expected.items():
        if control.get(key) != expected_control_value:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
                f"control.{key} drifted",
                key,
            )

    for key, expected_treatment_value in treatment_expected.items():
        if treatment.get(key) != expected_treatment_value:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
                f"treatment.{key} drifted",
                key,
            )

    isolation = _mapping(
        design.get("static_isolation_evidence"),
        "static isolation evidence",
    )
    expected_isolation: dict[str, object] = {
        "prompt_token_count_equal": True,
        "token_id_multiset_identical": True,
        "final_user_boundary_equal": True,
        "message_boundary_profile_equal": True,
        "common_suffix_token_count": CONTROL_TREATMENT_COMMON_SUFFIX_COUNT,
        "control_prompt_token_sha256": CONTROL_TOKEN_SHA256,
        "treatment_prompt_token_sha256": TREATMENT_TOKEN_SHA256,
        "control_paragraph_order": list(CONTROL_PARAGRAPH_ORDER),
        "treatment_paragraph_order": list(TREATMENT_PARAGRAPH_ORDER),
        "first_paragraph_preserved": True,
        "last_paragraph_preserved": True,
        "paragraph_content_multiset_preserved": True,
        "character_count_preserved": True,
        "producer_reexecutes_tokenizer": False,
    }
    for key, expected_isolation_value in expected_isolation.items():
        if isolation.get(key) != expected_isolation_value:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
                f"static_isolation_evidence.{key} drifted",
                key,
            )

    request_plan = _array(design.get("request_plan"), "request plan")
    observed_order = tuple(
        str(_mapping(item, "request item").get("condition_id")) for item in request_plan
    )
    observed_ordinals = tuple(
        _mapping(item, "request item").get("ordinal") for item in request_plan
    )
    if observed_order != REQUEST_ORDER:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            "request chronology drifted",
        )
    if observed_ordinals != tuple(range(1, 7)):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            "request ordinals drifted",
        )

    budget = _mapping(design.get("execution_budget"), "execution budget")
    expected_budget = {
        "maximum_kaggle_sessions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "maximum_model_requests": 6,
        "maximum_worker_teardowns": 6,
        "maximum_output_tokens_per_request": 32,
        "hidden_retries_permitted": 0,
        "replacement_observations_permitted": 0,
        "external_network_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
    }
    if budget != expected_budget:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            "execution budget drifted",
        )

    safety = _mapping(design.get("safety"), "safety")
    for key in (
        "runtime_execution_authorized",
        "new_execution_authorized",
        "execution_authorization_issued",
        "kaggle_execution_performed",
        "gpu_execution_performed",
        "model_loaded",
        "worker_started",
        "p5_p6_requalification_authorized",
        "measured_abc_execution_authorized",
    ):
        if safety.get(key) is not False:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
                f"safety.{key} drifted",
                key,
            )
    if safety.get("model_requests_performed") != 0:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_DESIGN_DRIFT",
            "design recorded model execution",
        )

    return design


def _assignment_node(
    source: str,
    name: str,
) -> ast.Assign | ast.AnnAssign:
    matches: list[ast.Assign | ast.AnnAssign] = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name for target in node.targets
        ):
            matches.append(node)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            matches.append(node)
    if len(matches) != 1:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_AMBIGUOUS",
            "assignment cardinality drifted",
            name,
        )
    return matches[0]


def _function_node(
    source: str,
    name: str,
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    matches = [
        node
        for node in ast.parse(source).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    if len(matches) != 1:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_AMBIGUOUS",
            "function cardinality drifted",
            name,
        )
    return matches[0]


def _segment(source: str, node: ast.AST) -> str:
    segment = ast.get_source_segment(source, node)
    if segment is None:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "unable to recover source segment",
        )
    return segment


def _replace_node(
    source: str,
    node: ast.AST,
    replacement: str,
) -> str:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if not isinstance(start, int) or not isinstance(end, int):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "source line boundary unavailable",
        )
    lines = source.splitlines(keepends=True)
    lines[start - 1 : end] = [replacement.rstrip() + "\n"]
    return "".join(lines)


def _replace_assignment(
    source: str,
    name: str,
    replacement: str,
) -> str:
    return _replace_node(
        source,
        _assignment_node(source, name),
        replacement,
    )


def _replace_function(
    source: str,
    name: str,
    replacement: str,
) -> str:
    return _replace_node(
        source,
        _function_node(source, name),
        replacement,
    )


def _function_segment(source: str, name: str) -> str:
    return _segment(source, _function_node(source, name))


def _derive_function(
    source: str,
    original_name: str,
    successor_name: str,
    replacements: tuple[tuple[str, str], ...] = (),
) -> str:
    derived = _function_segment(source, original_name)
    expected = f"def {original_name}("
    if expected not in derived:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "function declaration drifted",
            original_name,
        )
    derived = derived.replace(
        expected,
        f"def {successor_name}(",
        1,
    )
    for old, new in replacements:
        if old not in derived:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "expected predecessor source fragment is absent",
                old,
            )
        derived = derived.replace(old, new)
    return derived


def _literal_assignment(source: str, name: str) -> object:
    node = _assignment_node(source, name)
    value = node.value
    if value is None:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "literal assignment has no value",
            name,
        )
    return ast.literal_eval(value)


def _paragraph_contexts(
    predecessor_source: str,
) -> tuple[str, str]:
    original = _literal_assignment(
        predecessor_source,
        "C4_CANONICAL_CONTEXT",
    )
    system_prompt = _literal_assignment(
        predecessor_source,
        "SYSTEM_PROMPT",
    )

    if not isinstance(original, str) or not isinstance(system_prompt, str):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "canonical context authority is not textual",
        )

    if not original.endswith(system_prompt):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "canonical context instruction suffix drifted",
        )

    before_instruction = original[: -len(system_prompt)]
    body = before_instruction.rstrip(" \t\r\n")
    separator = before_instruction[len(body) :]

    if separator != " ":
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "context/instruction separator drifted",
        )

    paragraphs = body.split("\n\n")
    if len(paragraphs) != PARAGRAPH_COUNT:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "canonical paragraph count drifted",
        )

    reordered = [
        paragraphs[0],
        *reversed(paragraphs[1:9]),
        paragraphs[9],
    ]
    candidate = "\n\n".join(reordered) + separator + system_prompt

    if len(candidate) != len(original):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "paragraph-order intervention changed character count",
        )

    if sorted(reordered) != sorted(paragraphs):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "paragraph content multiset drifted",
        )

    return original, candidate


def _request_payload(
    predecessor_source: str,
    context: str,
) -> dict[str, object]:
    served_model = _literal_assignment(
        predecessor_source,
        "SERVED_MODEL_NAME",
    )
    system_prompt = _literal_assignment(
        predecessor_source,
        "SYSTEM_PROMPT",
    )
    acknowledgement = _literal_assignment(
        predecessor_source,
        "SYNTHETIC_ASSISTANT_ACK",
    )
    expected_object = _literal_assignment(
        predecessor_source,
        "EXPECTED_OBJECT",
    )

    if (
        not isinstance(served_model, str)
        or not isinstance(system_prompt, str)
        or not isinstance(acknowledgement, str)
        or not isinstance(expected_object, dict)
    ):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "request composition authority drifted",
        )

    expected_canonical = _canonical_json(expected_object)

    return {
        "model": served_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context},
            {"role": "assistant", "content": acknowledgement},
            {"role": "user", "content": expected_canonical},
        ],
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def _payload_sha256(payload: dict[str, object]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _runtime_constants_and_functions(
    treatment_payload_sha256: str,
) -> str:
    template = r"""
ORDER_DIAGNOSTIC_ID: Final = "C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"
ORDER_CONTROL_CONDITION: Final = "CONTROL_ORIGINAL_C4"
ORDER_TREATMENT_CONDITION: Final = "TREATMENT_REVERSED_MIDDLE_EIGHT"
ORDER_REQUEST_ORDER: Final = (
    ORDER_CONTROL_CONDITION,
    ORDER_TREATMENT_CONDITION,
    ORDER_TREATMENT_CONDITION,
    ORDER_CONTROL_CONDITION,
    ORDER_CONTROL_CONDITION,
    ORDER_TREATMENT_CONDITION,
)
ORDER_PROMPT_TOKEN_COUNT: Final = 899
ORDER_FINAL_USER_BOUNDARY: Final = 880
ORDER_CONTROL_TOKEN_SHA256: Final = (
    "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
)
ORDER_TREATMENT_TOKEN_SHA256: Final = (
    "14d6a6856ffb5c4caa4a4ed229fa0c94ac06b86fbef473be001dd6d8e3698cce"
)
ORDER_CONTROL_PAYLOAD_SHA256: Final = (
    "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
)
ORDER_TREATMENT_PAYLOAD_SHA256: Final = (
    "__TREATMENT_PAYLOAD_SHA256__"
)
ORDER_HISTORICAL_CONTROL_PARSED_OBJECT_SHA256: Final = (
    "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"
)
ORDER_TREATMENT_PARAGRAPH_ORDER: Final = (1, 9, 8, 7, 6, 5, 4, 3, 2, 10)
ORDER_OUTPUT_NAMES: Final = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "c4_paragraph_order_runtime_ready_v1.json",
    "pre_request_token_identity_journal_v1.json",
    "c4_paragraph_order_request_results_v1.json",
    "c4_paragraph_order_decision_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "failure_report_v1.json",
    "c4_paragraph_order_summary_v1.json",
    "human_report_v1.md",
    "bundle_manifest_v1.json",
)


def order_context(condition_id: str) -> str:
    if not C4_CANONICAL_CONTEXT.endswith(SYSTEM_PROMPT):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "canonical C4 instruction suffix drifted",
        )

    before_instruction = C4_CANONICAL_CONTEXT[: -len(SYSTEM_PROMPT)]
    body = before_instruction.rstrip(" \t\r\n")
    separator = before_instruction[len(body) :]

    if separator != " ":
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "canonical C4 instruction separator drifted",
        )

    paragraphs = body.split("\n\n")
    if len(paragraphs) != 10:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "canonical C4 paragraph count drifted",
        )

    if condition_id == ORDER_CONTROL_CONDITION:
        return C4_CANONICAL_CONTEXT

    if condition_id == ORDER_TREATMENT_CONDITION:
        reordered = [
            paragraphs[0],
            *reversed(paragraphs[1:9]),
            paragraphs[9],
        ]
        candidate = "\n\n".join(reordered) + separator + SYSTEM_PROMPT
        if len(candidate) != len(C4_CANONICAL_CONTEXT):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "paragraph-order intervention changed character count",
            )
        return candidate

    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "unsupported paragraph-order condition",
    )


def order_request_messages(
    condition_id: str,
    final_user_content: str,
) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": order_context(condition_id)},
        {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
        {"role": "user", "content": final_user_content},
    ]


def order_request_payload(
    condition_id: str,
) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": order_request_messages(
            condition_id,
            EXPECTED_OBJECT_CANONICAL,
        ),
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def order_tokenize_payload(
    condition_id: str,
    final_user_content: str,
) -> dict[str, object]:
    return {
        "model": SERVED_MODEL_NAME,
        "messages": order_request_messages(
            condition_id,
            final_user_content,
        ),
        "add_generation_prompt": True,
        "continue_final_message": False,
        "add_special_tokens": False,
        "return_token_strs": False,
    }


def order_token_sequence(
    worker: Worker,
    condition_id: str,
    final_user_content: str,
) -> tuple[int, ...]:
    response = post_json(
        f"http://127.0.0.1:{worker.port}/tokenize",
        order_tokenize_payload(
            condition_id,
            final_user_content,
        ),
    )
    raw_tokens = response.get("tokens")
    count = response.get("count")
    if (
        not isinstance(raw_tokens, list)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count != len(raw_tokens)
    ):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "paragraph-order tokenization response shape is invalid",
        )

    tokens: list[int] = []
    for raw_token in raw_tokens:
        if isinstance(raw_token, bool) or not isinstance(raw_token, int):
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "paragraph-order tokenization returned a non-integer token id",
            )
        if raw_token < 0:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "paragraph-order tokenization returned a negative token id",
            )
        tokens.append(raw_token)

    return tuple(tokens)


def order_expected_token_sha256(condition_id: str) -> str:
    if condition_id == ORDER_CONTROL_CONDITION:
        return ORDER_CONTROL_TOKEN_SHA256
    if condition_id == ORDER_TREATMENT_CONDITION:
        return ORDER_TREATMENT_TOKEN_SHA256
    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "unsupported paragraph-order token identity condition",
    )


def order_expected_payload_sha256(condition_id: str) -> str:
    if condition_id == ORDER_CONTROL_CONDITION:
        return ORDER_CONTROL_PAYLOAD_SHA256
    if condition_id == ORDER_TREATMENT_CONDITION:
        return ORDER_TREATMENT_PAYLOAD_SHA256
    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "unsupported paragraph-order payload identity condition",
    )


def order_token_identity(
    worker: Worker,
    condition_id: str,
) -> dict[str, object]:
    canonical_tokens = order_token_sequence(
        worker,
        condition_id,
        EXPECTED_OBJECT_CANONICAL,
    )
    sentinel_tokens = order_token_sequence(
        worker,
        condition_id,
        C4_FINAL_USER_BOUNDARY_SENTINEL,
    )
    reusable_tokens = c4_longest_common_prefix(
        canonical_tokens,
        sentinel_tokens,
    )

    canonical_sha256 = sha256_bytes(
        canonical_json(list(canonical_tokens)).encode("utf-8")
    )
    reusable_sha256 = sha256_bytes(
        canonical_json(list(reusable_tokens)).encode("utf-8")
    )

    if len(canonical_tokens) != ORDER_PROMPT_TOKEN_COUNT:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "paragraph-order prompt token count drifted",
        )
    if canonical_sha256 != order_expected_token_sha256(condition_id):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "paragraph-order prompt token identity drifted",
        )
    if len(reusable_tokens) != ORDER_FINAL_USER_BOUNDARY:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "paragraph-order final-user boundary drifted",
        )

    if (
        condition_id == ORDER_CONTROL_CONDITION
        and reusable_sha256 != C4_REUSABLE_PREFIX_TOKEN_SHA256
    ):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "control reusable-prefix identity drifted",
        )

    return {
        "token_count": len(canonical_tokens),
        "token_sha256": canonical_sha256,
        "reusable_prefix_token_count": len(reusable_tokens),
        "reusable_prefix_token_sha256": reusable_sha256,
        "sentinel_prompt_token_count": len(sentinel_tokens),
        "sentinel_prompt_token_sha256": sha256_bytes(
            canonical_json(list(sentinel_tokens)).encode("utf-8")
        ),
        "first_divergent_token_index": len(reusable_tokens),
    }


def initialize_order_journal() -> None:
    if PRE_REQUEST_TOKEN_IDENTITY_JOURNAL.exists():
        raise RuntimeError(
            "pre-request token-identity journal already exists"
        )
    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            "schema_version": "1.0.0",
            "journal_id": (
                "auragateway-c4-paragraph-order-behavioral-"
                "differential-pre-request-token-identity-v1"
            ),
            "diagnostic_id": ORDER_DIAGNOSTIC_ID,
            "entries": [],
            "raw_prompt_retained": False,
            "raw_model_output_retained": False,
        },
    )


def persist_order_pre_request_identity(
    request_ordinal: int,
    condition_id: str,
    token_identity: dict[str, object],
    payload_sha256: str,
) -> None:
    journal = _read_pre_request_token_identity_journal()
    entries = journal.get("entries")
    if not isinstance(entries, list):
        raise RuntimeError(
            "pre-request token-identity journal entries are invalid"
        )
    if request_ordinal != len(entries) + 1:
        raise RuntimeError(
            "pre-request token-identity request ordinal drifted"
        )
    if payload_sha256 != order_expected_payload_sha256(condition_id):
        raise RuntimeError(
            "paragraph-order request payload identity drifted"
        )

    write_json(
        PRE_REQUEST_TOKEN_IDENTITY_JOURNAL,
        {
            **journal,
            "entries": [
                *entries,
                {
                    "request_ordinal": request_ordinal,
                    "condition_id": condition_id,
                    "token_count": token_identity["token_count"],
                    "token_sha256": token_identity["token_sha256"],
                    "reusable_prefix_token_count": (
                        token_identity["reusable_prefix_token_count"]
                    ),
                    "reusable_prefix_token_sha256": (
                        token_identity["reusable_prefix_token_sha256"]
                    ),
                    "payload_sha256": payload_sha256,
                    "persisted_before_model_request": True,
                },
            ],
        },
    )


def write_order_results(
    results: list[dict[str, object]],
    status: str,
) -> None:
    write_json(
        OUTPUT_ROOT / "c4_paragraph_order_request_results_v1.json",
        {
            "schema_version": "1.0.0",
            "diagnostic_id": ORDER_DIAGNOSTIC_ID,
            "status": status,
            "scheduled_request_count": len(ORDER_REQUEST_ORDER),
            "observed_request_count": len(results),
            "request_order": list(ORDER_REQUEST_ORDER),
            "results": [
                order_public_observation(item)
                for item in results
            ],
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        },
    )


def order_condition_status(exact_count: int) -> str:
    if exact_count == 3:
        return "3_OF_3_EXACT_OBJECT_TRUE"
    if exact_count == 0:
        return "0_OF_3_EXACT_OBJECT_TRUE"
    if exact_count in {1, 2}:
        return "1_OR_2_OF_3_EXACT_OBJECT_TRUE"
    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "condition exact-object count is outside the frozen endpoint",
    )


def decide_order_differential(
    results: list[dict[str, object]],
    worker_reports: list[dict[str, object]],
    teardown_reports: list[dict[str, object]],
    counters: dict[str, int],
) -> dict[str, object]:
    if len(results) != 6:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "paragraph-order result count drifted",
        )
    if (
        tuple(str(row.get("condition_id")) for row in results)
        != ORDER_REQUEST_ORDER
    ):
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "paragraph-order chronology drifted",
        )
    if tuple(row.get("sequence_index") for row in results) != tuple(
        range(1, 7)
    ):
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "paragraph-order sequence indexes drifted",
        )
    if len(worker_reports) != 6 or len(teardown_reports) != 6:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "fresh-worker evidence cardinality drifted",
        )
    if any(
        item.get("status") != "PASSED"
        for item in teardown_reports
    ):
        raise DiagnosticFailure(
            "TEARDOWN_FAILURE",
            "one or more paragraph-order teardowns failed",
        )

    worker_identities = {
        str(row.get("worker_process_identity_sha256"))
        for row in results
        if isinstance(
            row.get("worker_process_identity_sha256"),
            str,
        )
    }
    if len(worker_identities) != 6:
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "fresh worker process identity was reused",
        )

    if any(
        row.get("zero_cache_baseline") is not True
        for row in results
    ):
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "one or more observations lacked zero cache baseline",
        )

    expected_counters = {
        "model_requests": 6,
        "model_loads": 6,
        "worker_starts": 6,
        "hidden_retries": 0,
        "network_requests": 0,
        "benchmark_trajectory_requests": 0,
        "external_spend": 0,
    }
    for name, expected in expected_counters.items():
        if counters.get(name) != expected:
            raise DiagnosticFailure(
                "REQUEST_RECONCILIATION_FAILURE",
                f"{name} expected {expected}, observed {counters.get(name)}",
            )

    rows_by_condition = {
        condition_id: [
            row
            for row in results
            if row.get("condition_id") == condition_id
        ]
        for condition_id in (
            ORDER_CONTROL_CONDITION,
            ORDER_TREATMENT_CONDITION,
        )
    }
    if any(
        len(rows) != 3
        for rows in rows_by_condition.values()
    ):
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "condition cardinality drifted",
        )

    expected_tokens = {
        ORDER_CONTROL_CONDITION: ORDER_CONTROL_TOKEN_SHA256,
        ORDER_TREATMENT_CONDITION: ORDER_TREATMENT_TOKEN_SHA256,
    }
    expected_payloads = {
        ORDER_CONTROL_CONDITION: ORDER_CONTROL_PAYLOAD_SHA256,
        ORDER_TREATMENT_CONDITION: ORDER_TREATMENT_PAYLOAD_SHA256,
    }

    for condition_id, rows in rows_by_condition.items():
        token_identities = {
            (
                row.get("token_count"),
                row.get("token_sha256"),
                row.get("reusable_prefix_token_count"),
            )
            for row in rows
        }
        if token_identities != {
            (
                ORDER_PROMPT_TOKEN_COUNT,
                expected_tokens[condition_id],
                ORDER_FINAL_USER_BOUNDARY,
            )
        }:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "condition token identity failed reconciliation",
            )

        if {
            row.get("payload_sha256")
            for row in rows
        } != {expected_payloads[condition_id]}:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "condition payload identity failed reconciliation",
            )

        if any(
            row.get("http_status") != 200
            or row.get("finish_reason") != "stop"
            or row.get("response_complete") is not True
            or row.get("worker_health_after_request") is not True
            or row.get("teardown_status") != "PASSED"
            for row in rows
        ):
            raise DiagnosticFailure(
                "OUTPUT_CONTRACT_FAILURE",
                "healthy observation contract drifted",
            )

    control_rows = rows_by_condition[ORDER_CONTROL_CONDITION]
    treatment_rows = rows_by_condition[ORDER_TREATMENT_CONDITION]

    control_exact = sum(
        row.get("exact_object") is True
        for row in control_rows
    )
    treatment_exact = sum(
        row.get("exact_object") is True
        for row in treatment_rows
    )

    control_valid_json = sum(
        row.get("valid_json") is True
        for row in control_rows
    )
    treatment_valid_json = sum(
        row.get("valid_json") is True
        for row in treatment_rows
    )

    control_parsed = {
        row.get("canonical_parsed_object_sha256")
        for row in control_rows
    }
    treatment_parsed = {
        row.get("canonical_parsed_object_sha256")
        for row in treatment_rows
    }

    control_anchor_reproduced = (
        control_exact == 0
        and control_valid_json == 3
        and control_parsed
        == {ORDER_HISTORICAL_CONTROL_PARSED_OBJECT_SHA256}
    )

    if not control_anchor_reproduced:
        state = (
            "CONTROL_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
        )
    elif treatment_exact == 3:
        state = "ORDER_INTERVENTION_RESTORES_BEHAVIOR"
    elif (
        treatment_exact == 0
        and treatment_valid_json == 3
        and treatment_parsed
        == {ORDER_HISTORICAL_CONTROL_PARSED_OBJECT_SHA256}
    ):
        state = (
            "ORDER_INTERVENTION_DOES_NOT_CHANGE_OBSERVED_PHENOTYPE"
        )
    elif (
        treatment_exact == 0
        and treatment_valid_json == 3
        and len(treatment_parsed) == 1
        and None not in treatment_parsed
        and treatment_parsed
        != {ORDER_HISTORICAL_CONTROL_PARSED_OBJECT_SHA256}
    ):
        state = "ORDER_INTERVENTION_CHANGES_FAILURE_PHENOTYPE"
    else:
        state = "ORDER_INTERVENTION_EFFECT_AMBIGUOUS"

    return {
        "schema_version": "1.0.0",
        "status": "DECIDED",
        "diagnostic_id": ORDER_DIAGNOSTIC_ID,
        "observed_terminal_state": state,
        "primary_endpoint": "exact_object",
        "condition_exact_object_counts": {
            ORDER_CONTROL_CONDITION: control_exact,
            ORDER_TREATMENT_CONDITION: treatment_exact,
        },
        "condition_valid_json_counts": {
            ORDER_CONTROL_CONDITION: control_valid_json,
            ORDER_TREATMENT_CONDITION: treatment_valid_json,
        },
        "condition_endpoint_statuses": {
            ORDER_CONTROL_CONDITION: order_condition_status(
                control_exact
            ),
            ORDER_TREATMENT_CONDITION: order_condition_status(
                treatment_exact
            ),
        },
        "control_anchor_reproduced": control_anchor_reproduced,
        "control_historical_parsed_identity_required": True,
        "fresh_worker_process_per_observation": True,
        "worker_identity_cardinality": len(worker_identities),
        "all_condition_token_identities_matched": True,
        "all_condition_payload_identities_matched": True,
        "static_token_multiset_premise_reexecuted": False,
        "paragraph_order_root_cause_established": False,
        "p5_requalified": False,
        "p6_requalified": False,
        "final_abc_measured": False,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }
"""
    return template.replace(
        "__TREATMENT_PAYLOAD_SHA256__",
        treatment_payload_sha256,
    ).strip()


def _derive_runtime_functions(source: str) -> str:
    observation = _derive_function(
        source,
        "run_c4_observation",
        "run_order_observation",
    )
    observation = observation.replace(
        "    worker: Worker,\n    sequence_index: int,",
        "    worker: Worker,\n    condition_id: str,\n    sequence_index: int,",
        1,
    )
    replacements = (
        (
            "token_identity = c4_token_identity(worker)",
            ("token_identity = order_token_identity(worker, condition_id)"),
        ),
        (
            "payload = c4_request_payload()",
            "payload = order_request_payload(condition_id)",
        ),
        (
            "if payload_sha256 != C4_REQUEST_PAYLOAD_SHA256:",
            ("if payload_sha256 != order_expected_payload_sha256(condition_id):"),
        ),
        (
            "persist_c4_pre_request_identity(\n        request_ordinal,\n        token_identity,",
            "persist_order_pre_request_identity(\n"
            "        request_ordinal,\n"
            "        condition_id,\n"
            "        token_identity,",
        ),
        (
            "prompt_tokens != C4_FULL_PROMPT_TOKEN_COUNT",
            "prompt_tokens != ORDER_PROMPT_TOKEN_COUNT",
        ),
        (
            '"observation_id": f"C4_OBSERVATION_{sequence_index}",',
            (
                '"observation_id": '
                'f"ORDER_{condition_id}_{sequence_index}",\n'
                '        "condition_id": condition_id,'
            ),
        ),
        ("C4 request", "paragraph-order request"),
        ("C4 response", "paragraph-order response"),
        ("C4 pre-request", "paragraph-order pre-request"),
    )
    for old, new in replacements:
        if old not in observation:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "C4 observation derivation anchor drifted",
                old,
            )
        observation = observation.replace(old, new)

    public = _derive_function(
        source,
        "c4_public_observation",
        "order_public_observation",
    )
    anchor = '        "observation_id",\n'
    if anchor not in public:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "public observation permit-list anchor drifted",
        )
    public = public.replace(
        anchor,
        anchor + '        "condition_id",\n',
        1,
    )

    fresh = _derive_function(
        source,
        "run_c4_fresh_worker_observation",
        "run_order_fresh_worker_observation",
    )
    fresh = fresh.replace(
        "    snapshot: Path,\n    sequence_index: int,",
        "    snapshot: Path,\n    condition_id: str,\n    sequence_index: int,",
        1,
    )
    fresh = fresh.replace(
        "observation = run_c4_observation(\n            worker,\n            sequence_index,",
        "observation = run_order_observation(\n"
        "            worker,\n"
        "            condition_id,\n"
        "            sequence_index,",
        1,
    )
    fresh = fresh.replace(
        'f"C4_OBSERVATION_{sequence_index}_TERMINAL"',
        'f"ORDER_{condition_id}_{sequence_index}_TERMINAL"',
    )
    fresh = fresh.replace("C4 observation", "paragraph-order observation")

    bundle = _derive_function(
        source,
        "c4_bundle_outputs",
        "order_bundle_outputs",
        (
            ("C4_OUTPUT_NAMES", "ORDER_OUTPUT_NAMES"),
            ("C4 evidence", "paragraph-order evidence"),
            ("C4_QUALIFICATION_ID", "ORDER_DIAGNOSTIC_ID"),
            ('"qualification_id":', '"diagnostic_id":'),
        ),
    )

    return "\n\n\n".join(
        (
            observation,
            public,
            fresh,
            bundle,
        )
    )


def _derive_main(source: str) -> str:
    main = _function_segment(source, "main")

    replacements = (
        ("initialize_c4_journal", "initialize_order_journal"),
        (
            '"c4_runtime_ready_v1.json"',
            '"c4_paragraph_order_runtime_ready_v1.json"',
        ),
        ("C4_QUALIFICATION_ID", "ORDER_DIAGNOSTIC_ID"),
        ('"qualification_id":', '"diagnostic_id":'),
        (
            "for sequence_index in range(1, C4_OBSERVATION_COUNT + 1):",
            ("for sequence_index, condition_id in enumerate(ORDER_REQUEST_ORDER, start=1):"),
        ),
        (
            "run_c4_fresh_worker_observation(\n"
            "                model_home,\n"
            "                snapshot,\n"
            "                sequence_index,",
            "run_order_fresh_worker_observation(\n"
            "                model_home,\n"
            "                snapshot,\n"
            "                condition_id,\n"
            "                sequence_index,",
        ),
        ("write_c4_results", "write_order_results"),
        ("decide_c4_qualification", "decide_order_differential"),
        (
            '"c4_decision_v1.json"',
            '"c4_paragraph_order_decision_v1.json"',
        ),
        (
            '"c4_summary_v1.json"',
            '"c4_paragraph_order_summary_v1.json"',
        ),
        ("c4_bundle_outputs", "order_bundle_outputs"),
        ('"scheduled_worker_starts": 3', '"scheduled_worker_starts": 6'),
        ('"scheduled_model_loads": 3', '"scheduled_model_loads": 6'),
        ('"scheduled_model_requests": 3', '"scheduled_model_requests": 6'),
        ('"model_loads": 3', '"model_loads": 6'),
        ('"worker_starts": 3', '"worker_starts": 6'),
        ('"model_requests": 3', '"model_requests": 6'),
        ('"scheduled_worker_count": 3', '"scheduled_worker_count": 6'),
        ("len(results) == 3", "len(results) == 6"),
        ('"scheduled_requests": 3', '"scheduled_requests": 6'),
        (
            'f"- Completed requests: {len(results)} / 3\\n"',
            'f"- Completed requests: {len(results)} / 6\\n"',
        ),
        (
            "f\"- Worker starts: {counters['worker_starts']} / 3\\n\"",
            "f\"- Worker starts: {counters['worker_starts']} / 6\\n\"",
        ),
        (
            "f\"- Model loads: {counters['model_loads']} / 3\\n\"",
            "f\"- Model loads: {counters['model_loads']} / 6\\n\"",
        ),
        (
            "PRESERVE_AND_RECONCILE_CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1",
            ("PRESERVE_AND_DISPOSITION_C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_V1"),
        ),
    )
    for old, new in replacements:
        if old not in main:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "main derivation anchor drifted",
                old,
            )
        main = main.replace(old, new)

    ready_identity = """                "full_prompt_token_count": (C4_FULL_PROMPT_TOKEN_COUNT),
                "full_prompt_token_sha256": (C4_FULL_PROMPT_TOKEN_SHA256),
                "reusable_prefix_token_count": (C4_REUSABLE_PREFIX_TOKEN_COUNT),
                "reusable_prefix_token_sha256": (C4_REUSABLE_PREFIX_TOKEN_SHA256),
                "request_payload_sha256": (C4_REQUEST_PAYLOAD_SHA256),"""
    ready_replacement = (
        '                "prompt_token_count_per_condition": '
        "ORDER_PROMPT_TOKEN_COUNT,\n"
        '                "control_prompt_token_sha256": '
        "ORDER_CONTROL_TOKEN_SHA256,\n"
        '                "treatment_prompt_token_sha256": '
        "ORDER_TREATMENT_TOKEN_SHA256,\n"
        '                "final_user_boundary_per_condition": '
        "ORDER_FINAL_USER_BOUNDARY,\n"
        '                "condition_request_payload_sha256": {\n'
        "                    ORDER_CONTROL_CONDITION: "
        "ORDER_CONTROL_PAYLOAD_SHA256,\n"
        "                    ORDER_TREATMENT_CONDITION: "
        "ORDER_TREATMENT_PAYLOAD_SHA256,\n"
        "                },"
    )
    if ready_identity not in main:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "runtime-ready identity block drifted",
        )
    main = main.replace(
        ready_identity,
        ready_replacement,
        1,
    )

    summary_identity = """        "full_prompt_token_count": C4_FULL_PROMPT_TOKEN_COUNT,
        "full_prompt_token_sha256": C4_FULL_PROMPT_TOKEN_SHA256,
        "reusable_prefix_token_count": (C4_REUSABLE_PREFIX_TOKEN_COUNT),
        "reusable_prefix_token_sha256": (C4_REUSABLE_PREFIX_TOKEN_SHA256),
        "canonical_request_payload_sha256": (C4_REQUEST_PAYLOAD_SHA256),"""
    summary_replacement = """        "prompt_token_count_per_condition": ORDER_PROMPT_TOKEN_COUNT,
        "control_prompt_token_sha256": ORDER_CONTROL_TOKEN_SHA256,
        "treatment_prompt_token_sha256": ORDER_TREATMENT_TOKEN_SHA256,
        "final_user_boundary_per_condition": ORDER_FINAL_USER_BOUNDARY,
        "condition_request_payload_sha256": {
            ORDER_CONTROL_CONDITION: ORDER_CONTROL_PAYLOAD_SHA256,
            ORDER_TREATMENT_CONDITION: ORDER_TREATMENT_PAYLOAD_SHA256,
        },"""
    if summary_identity not in main:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "summary identity block drifted",
        )
    main = main.replace(
        summary_identity,
        summary_replacement,
        1,
    )

    main = main.replace(
        '"c4_repository_state_advanced": False',
        '"paragraph_order_repository_state_advanced": False',
    )
    main = main.replace(
        '"# AuraGateway Canonical Synthetic Prefix C4 "\n'
        '        "Behavioral Qualification V1\\n\\n"',
        '"# AuraGateway C4 Paragraph-Order Behavioral "\n        "Differential V1\\n\\n"',
    )
    main = main.replace(
        '"- Qualification accepted by repository: false\\n"',
        '"- Differential accepted by repository: false\\n"',
    )
    main = main.replace(
        '"- P5/P6 were not requalified by this execution.\\n"',
        '"- P5/P6 are outside this diagnostic.\\n"',
    )

    return main


def _remove_main_guard(source: str) -> str:
    tree = ast.parse(source)
    matches: list[ast.If] = []
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        segment = ast.get_source_segment(source, node)
        if segment is None:
            continue
        if '__name__ == "__main__"' in segment:
            matches.append(node)
    if len(matches) != 1:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_SOURCE_AMBIGUOUS",
            "main guard cardinality drifted",
        )
    return _replace_node(source, matches[0], "")


def _build_runtime_source(
    predecessor_payload: bytes,
) -> tuple[str, str]:
    try:
        source = predecessor_payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_PREDECESSOR_INVALID",
            "predecessor runtime is not UTF-8",
        ) from error

    ast.parse(source)

    original_context, treatment_context = _paragraph_contexts(source)

    control_payload_sha256 = _payload_sha256(
        _request_payload(
            source,
            original_context,
        )
    )
    if control_payload_sha256 != CONTROL_REQUEST_PAYLOAD_SHA256:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_PAYLOAD_DRIFT",
            "control request payload identity drifted",
        )

    treatment_payload_sha256 = _payload_sha256(
        _request_payload(
            source,
            treatment_context,
        )
    )

    source = _remove_main_guard(source)

    source = _replace_assignment(
        source,
        "NOTEBOOK_NAME",
        'NOTEBOOK_NAME: Final = "ag-c4-paragraph-order-diff-v1"',
    )
    source = _replace_assignment(
        source,
        "SOURCE_MAIN_COMMIT",
        f'SOURCE_MAIN_COMMIT: Final = "{BASE_MAIN_COMMIT}"',
    )
    source = _replace_assignment(
        source,
        "OUTPUT_ROOT",
        ('OUTPUT_ROOT: Final = WORK_ROOT / "c4_paragraph_order_behavioral_differential_v1"'),
    )
    source = _replace_assignment(
        source,
        "SCRATCH_ROOT",
        (
            "SCRATCH_ROOT: Final = WORK_ROOT / "
            '"c4_paragraph_order_behavioral_differential_v1_scratch"'
        ),
    )
    source = _replace_assignment(
        source,
        "EVIDENCE_ZIP",
        ('EVIDENCE_ZIP: Final = WORK_ROOT / "ag-c4-paragraph-order-diff-evidence-v1.zip"'),
    )
    source = _replace_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
        """ACTION_BUDGET_LIMITS: Final = {
    "runtime_install_attempts": 1,
    "runtime_import_closure_probes": 1,
    "model_loads": 6,
    "worker_starts": 6,
    "model_requests": 6,
}""",
    )

    addition_anchor = _function_node(
        source,
        "c4_request_messages",
    )
    lines = source.splitlines(keepends=True)
    addition = (
        _runtime_constants_and_functions(treatment_payload_sha256)
        + "\n\n\n"
        + _derive_runtime_functions(source)
        + "\n\n\n"
    )
    lines[addition_anchor.lineno - 1 : addition_anchor.lineno - 1] = [addition]
    source = "".join(lines)

    source = _replace_function(
        source,
        "main",
        _derive_main(source),
    )

    source = source.rstrip() + ('\n\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n')

    ast.parse(source)

    required = set(ADDED_FUNCTIONS)
    observed = {node.name for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
    missing = required - observed
    if missing:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_RUNTIME_INCOMPLETE",
            f"generated runtime missing functions: {sorted(missing)}",
        )

    return source, treatment_payload_sha256


def _validate_authorities(
    root: Path,
) -> tuple[bytes, bytes]:
    _validate_design(root)

    design_payload = _read_exact(
        root,
        DESIGN_PATH,
        DESIGN_SHA256,
    )
    predecessor_payload = _read_exact(
        root,
        PREDECESSOR_RUNTIME_PATH,
        PREDECESSOR_RUNTIME_SHA256,
    )

    return design_payload, predecessor_payload


def _source_and_test_hashes(root: Path) -> tuple[str, str]:
    return (
        _sha256(_read_required(root, SOURCE_PATH)),
        _sha256(_read_required(root, TEST_PATH)),
    )


def _build_review(
    root: Path,
    runtime_sha256: str,
    treatment_payload_sha256: str,
) -> ImplementationReview:
    source_sha256, test_sha256 = _source_and_test_hashes(root)

    return ImplementationReview(
        review_id=(
            "auragateway-c4-paragraph-order-behavioral-differential-implementation-v1-review"
        ),
        status="APPROVED_STATIC_PARAGRAPH_ORDER_DIFFERENTIAL_HARNESS",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        implementation_source_sha256=source_sha256,
        focused_test_sha256=test_sha256,
        runtime_payload_sha256=runtime_sha256,
        control_request_payload_sha256=(CONTROL_REQUEST_PAYLOAD_SHA256),
        treatment_request_payload_sha256=(treatment_payload_sha256),
        request_order=REQUEST_ORDER,
        changed_existing_functions=CHANGED_EXISTING_FUNCTIONS,
        added_functions=ADDED_FUNCTIONS,
        prompt_token_count_per_condition=899,
        final_user_boundary_per_condition=880,
        observations_per_condition=3,
        maximum_model_requests=6,
        maximum_model_loads=6,
        maximum_worker_starts=6,
        maximum_worker_teardowns=6,
        maximum_hidden_retries=0,
        maximum_replacement_observations=0,
        fresh_worker_process_per_observation=True,
        control_anchor_requires_historical_parsed_identity=True,
        treatment_exact_object_restoration_rule_preserved=True,
        treatment_same_phenotype_rule_preserved=True,
        treatment_changed_phenotype_rule_preserved=True,
        treatment_ambiguous_rule_preserved=True,
        static_token_multiset_premise_reexecuted=False,
        runtime_execution_authorized=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )


def _build_record(
    runtime_sha256: str,
    review_sha256: str,
    treatment_payload_sha256: str,
) -> ImplementationRecord:
    return ImplementationRecord(
        record_id=("auragateway-c4-paragraph-order-behavioral-differential-implementation-v1"),
        status="IMPLEMENTED_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_path=(PREDECESSOR_RUNTIME_PATH.as_posix()),
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        successor_runtime_path=RUNTIME_PATH.as_posix(),
        successor_runtime_sha256=runtime_sha256,
        implementation_review_sha256=review_sha256,
        control_request_payload_sha256=(CONTROL_REQUEST_PAYLOAD_SHA256),
        treatment_request_payload_sha256=(treatment_payload_sha256),
        model_requests_performed=0,
        model_loads_performed=0,
        worker_starts_performed=0,
        kaggle_execution_performed=False,
        gpu_execution_performed=False,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        new_execution_authorized=False,
        p5_requalified=False,
        p6_requalified=False,
        final_abc_measured=False,
        production_readiness_established=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "No model request was performed.",
            "No model was loaded.",
            "No GPU execution was performed.",
            "No Kaggle execution was performed.",
            "No live execution authority was issued.",
            "Paragraph order is not established as root cause.",
            "The canonical C4 corpus is not globally invalidated.",
            "The static token-multiset premise was not reexecuted.",
            "P5 cache behavior is not requalified.",
            "P6 worker-state isolation is not requalified.",
            "Final A/B/C effects are not measured.",
            "Production readiness is not established.",
        ),
    )


def _canonicalize_runtime_source(
    root: Path,
    source: str,
) -> str:
    version_result = subprocess.run(
        [sys.executable, "-m", "ruff", "--version"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if version_result.returncode != 0:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_UNAVAILABLE",
            "unable to resolve the governed Ruff formatter",
        )

    observed_version = version_result.stdout.strip()
    if observed_version != EXPECTED_RUFF_VERSION:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_DRIFT",
            (
                "governed Ruff formatter identity drifted: "
                f"expected={EXPECTED_RUFF_VERSION} observed={observed_version}"
            ),
        )

    source_tree = ast.dump(
        ast.parse(source),
        include_attributes=False,
    )
    format_result = subprocess.run(
        [sys.executable, "-m", "ruff", *RUNTIME_FORMATTER_ARGS],
        cwd=root,
        input=source,
        check=False,
        capture_output=True,
        text=True,
    )
    if format_result.returncode != 0:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_FAILED",
            "governed Ruff formatter could not canonicalize the runtime",
        )

    formatted = format_result.stdout
    if not formatted:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_FAILED",
            "governed Ruff formatter returned an empty runtime",
        )

    try:
        formatted_tree = ast.dump(
            ast.parse(formatted),
            include_attributes=False,
        )
    except SyntaxError as error:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_FAILED",
            "canonical runtime is not valid Python",
        ) from error

    if formatted_tree != source_tree:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_SEMANTIC_DRIFT",
            "runtime canonicalization changed the Python AST",
        )

    if "\r\n" in formatted or not formatted.endswith("\n"):
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_FORMATTER_LINE_ENDING_DRIFT",
            "canonical runtime did not preserve governed LF line endings",
        )

    return formatted


def build_generated(
    root: Path,
) -> tuple[bytes, bytes, bytes]:
    _, predecessor_payload = _validate_authorities(root)

    runtime_source, treatment_payload_sha256 = _build_runtime_source(predecessor_payload)
    runtime_source = _canonicalize_runtime_source(
        root,
        runtime_source,
    )
    runtime_bytes = runtime_source.encode("utf-8")
    runtime_sha256 = _sha256(runtime_bytes)

    review = _build_review(
        root,
        runtime_sha256,
        treatment_payload_sha256,
    )
    review_bytes = _canonical_bytes(review)
    review_sha256 = _sha256(review_bytes)

    record = _build_record(
        runtime_sha256,
        review_sha256,
        treatment_payload_sha256,
    )
    record_bytes = _canonical_bytes(record)

    return runtime_bytes, review_bytes, record_bytes


def generate(root: Path) -> None:
    runtime_bytes, review_bytes, record_bytes = build_generated(root)

    outputs = (
        (RUNTIME_PATH, runtime_bytes),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    )
    for relative, payload in outputs:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


def validate_generated(root: Path) -> None:
    expected = build_generated(root)
    paths = (
        RUNTIME_PATH,
        REVIEW_PATH,
        RECORD_PATH,
    )

    for relative, expected_payload in zip(
        paths,
        expected,
        strict=True,
    ):
        observed = _read_required(root, relative)
        if observed != expected_payload:
            raise ImplementationError(
                "C4_PARAGRAPH_ORDER_IMPLEMENTATION_GENERATED_DRIFT",
                "generated implementation artifact drifted",
                relative.as_posix(),
            )


def load_generated_runtime(
    root: Path,
) -> ModuleType:
    path = root / RUNTIME_PATH
    spec = importlib.util.spec_from_file_location(
        "auragateway_c4_paragraph_order_runtime_v1",
        path,
    )
    if spec is None or spec.loader is None:
        raise ImplementationError(
            "C4_PARAGRAPH_ORDER_IMPLEMENTATION_RUNTIME_LOAD_FAILED",
            "generated runtime import specification is unavailable",
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _parser() -> _ArgumentParser:
    parser = _ArgumentParser()
    parser.add_argument(
        "--root",
        required=True,
        type=Path,
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=("generate", "validate"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()

    try:
        if args.mode == "generate":
            generate(root)
            print("C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_IMPLEMENTATION=GENERATED")
            print(f"RUNTIME={RUNTIME_PATH.as_posix()}")
            print(f"REVIEW={REVIEW_PATH.as_posix()}")
            print(f"RECORD={RECORD_PATH.as_posix()}")
            print("NEW_EXECUTION_AUTHORIZED=false")
            print("MODEL_REQUESTS_PERFORMED=0")
            print("GPU_EXECUTION_PERFORMED=false")
            print("KAGGLE_EXECUTION_PERFORMED=false")
            return 0

        validate_generated(root)
        print("C4_PARAGRAPH_ORDER_BEHAVIORAL_DIFFERENTIAL_IMPLEMENTATION=PASS")
        print("NEW_EXECUTION_AUTHORIZED=false")
        print("MODEL_REQUESTS_PERFORMED=0")
        print("GPU_EXECUTION_PERFORMED=false")
        print("KAGGLE_EXECUTION_PERFORMED=false")
        return 0

    except ImplementationError as error:
        print(
            json.dumps(
                error.envelope(),
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

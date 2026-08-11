"""Generate and validate the P4/P5 composition differential runtime V1.

The predecessor P5/P6 transaction-bound runtime is immutable input authority.
This producer emits a separate successor runtime that preserves the exact
runtime lifecycle through worker readiness and replaces only the experiment
boundary with the frozen six-request composition differential.

This module performs no Kaggle execution and issues no execution authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import textwrap
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "36defc782c08e211680489f4d60a9173de6e9052"

DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_differential_design_v1.json"
)
DESIGN_SHA256: Final = "5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1"

PREDECESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
)
PREDECESSOR_RUNTIME_SHA256: Final = (
    "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
)

P4_PRECEDENT_PATH: Final = Path(
    "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"
)
P4_PRECEDENT_SHA256: Final = "93bdcf4a2ab3f4b4a07b688b8d6f9dc295ba3edcbb0b9bd63da8967393811441"

SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/p4_p5_composition_differential_implementation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/test_p4_p5_composition_differential_implementation_v1.py"
)
RUNTIME_PATH: Final = Path("src/auragateway/local_abc/p4_p5_composition_differential_runtime_v1.py")
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_differential_implementation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_differential_implementation_v1.json"
)

NEXT_GATE: Final = "MERGE_THEN_DESIGN_P4_P5_COMPOSITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"

REQUEST_ORDER: Final = ("A", "B", "B", "A", "A", "B")
RETAINED_FIELDS: Final = (
    "case_id",
    "sequence_index",
    "http_status",
    "response_sha256",
    "response_length",
    "finish_reason",
    "completion_tokens",
    "valid_json",
    "exact_object",
    "json_error_line",
    "json_error_column",
    "json_error_position",
    "first_non_whitespace_class",
    "last_non_whitespace_class",
    "markdown_fence_detected",
)

CHANGED_EXISTING_FUNCTIONS: Final = (
    "main",
    "request_messages",
)
ADDED_FUNCTIONS: Final = (
    "decide_composition_differential",
    "differential_bundle_outputs",
    "differential_edge_class",
    "differential_failure_record",
    "run_differential_request",
    "write_differential_results",
)


class ImplementationError(RuntimeError):
    """Fail-closed static successor implementation error."""

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
            "P4_P5_DIFF_IMPLEMENTATION_ARGUMENT_INVALID",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ImplementationReview(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    review_id: Literal["auragateway-p4-p5-composition-differential-implementation-v1-review"]
    status: Literal["APPROVED_STATIC_SUCCESSOR_IMPLEMENTATION"]
    base_main_commit: Literal["36defc782c08e211680489f4d60a9173de6e9052"]
    design_record_sha256: Literal[
        "5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1"
    ]
    predecessor_runtime_sha256: Literal[
        "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
    ]
    historical_p4_precedent_sha256: Literal[
        "93bdcf4a2ab3f4b4a07b688b8d6f9dc295ba3edcbb0b9bd63da8967393811441"
    ]
    implementation_source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    focused_test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runtime_payload_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    request_order: tuple[str, ...]
    maximum_model_requests: Literal[6] = 6
    maximum_model_loads: Literal[1] = 1
    maximum_worker_starts: Literal[1] = 1
    maximum_hidden_retries: Literal[0] = 0
    maximum_external_network_requests: Literal[0] = 0
    changed_existing_functions: tuple[str, ...]
    added_functions: tuple[str, ...]
    unchanged_existing_function_count: int = Field(ge=1)
    predecessor_runtime_preserved: Literal[True] = True
    current_generation_controls_preserved: Literal[True] = True
    invalid_json_retained_as_observation: Literal[True] = True
    raw_prompt_retained: Literal[False] = False
    raw_output_retained: Literal[False] = False
    p5_p6_trajectory_reachable_from_successor_main: Literal[False] = False
    differential_notebook_generated: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "MERGE_THEN_DESIGN_P4_P5_COMPOSITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
    ]

    @model_validator(mode="after")
    def validate_review(self) -> ImplementationReview:
        if self.request_order != REQUEST_ORDER:
            raise ValueError("request order drifted")
        if self.changed_existing_functions != CHANGED_EXISTING_FUNCTIONS:
            raise ValueError("changed existing function inventory drifted")
        if self.added_functions != ADDED_FUNCTIONS:
            raise ValueError("added function inventory drifted")
        return self


class ImplementationRecord(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    record_id: Literal["auragateway-p4-p5-composition-differential-implementation-v1"]
    status: Literal["IMPLEMENTED_NOT_EXECUTED"]
    base_main_commit: Literal["36defc782c08e211680489f4d60a9173de6e9052"]
    design_record_sha256: Literal[
        "5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1"
    ]
    predecessor_runtime_path: Literal[
        "src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py"
    ]
    predecessor_runtime_sha256: Literal[
        "361244e8030eb50a50456f305f3eee8d74e406e11ec906f7a3494f8e66481cd3"
    ]
    successor_runtime_path: Literal[
        "src/auragateway/local_abc/p4_p5_composition_differential_runtime_v1.py"
    ]
    successor_runtime_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_requests_performed: Literal[0] = 0
    model_loads_performed: Literal[0] = 0
    worker_starts_performed: Literal[0] = 0
    kaggle_execution_performed: Literal[False] = False
    gpu_execution_performed: Literal[False] = False
    differential_notebook_generated: Literal[False] = False
    live_authorization_issued: Literal[False] = False
    runtime_execution_authorized: Literal[False] = False
    new_execution_authorized: Literal[False] = False
    runtime_fix_authorized: Literal[False] = False
    measured_abc_execution_authorized: Literal[False] = False
    next_gate: Literal[
        "MERGE_THEN_DESIGN_P4_P5_COMPOSITION_DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
    ]
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
            "P4_P5_DIFF_IMPLEMENTATION_ARTIFACT_MISSING",
            "required implementation artifact is missing or unsafe",
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
            "P4_P5_DIFF_IMPLEMENTATION_AUTHORITY_DRIFT",
            "required implementation authority identity drifted",
            relative.as_posix(),
        )

    return payload


def _read_object(
    root: Path,
    relative: Path,
    expected_sha256: str,
) -> dict[str, object]:
    payload = _read_exact(root, relative, expected_sha256)

    try:
        observed: object = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_AUTHORITY_INVALID",
            "required implementation authority is not valid JSON",
            relative.as_posix(),
        ) from error

    if not isinstance(observed, dict):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_AUTHORITY_INVALID",
            "required implementation authority must be one object",
            relative.as_posix(),
        )

    return cast(dict[str, object], observed)


def _validate_design(root: Path) -> None:
    design = _read_object(
        root,
        DESIGN_PATH,
        DESIGN_SHA256,
    )

    safety = design.get("safety")
    budget = design.get("execution_budget")
    diagnostics = design.get("diagnostics")
    authorities = design.get("accepted_authorities")
    cases = design.get("cases")
    request_plan = design.get("request_plan")

    if not isinstance(safety, dict):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design safety contract is unavailable",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(budget, dict):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design execution budget is unavailable",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(diagnostics, dict):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design diagnostic contract is unavailable",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(authorities, list):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design authority inventory is unavailable",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(cases, list) or len(cases) != 2:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design cases drifted",
            DESIGN_PATH.as_posix(),
        )

    if not isinstance(request_plan, list):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design request plan is unavailable",
            DESIGN_PATH.as_posix(),
        )

    if design.get("design_status") != "DESIGN_FROZEN_NOT_EXECUTED":
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design status drifted",
            DESIGN_PATH.as_posix(),
        )

    if safety.get("runtime_execution_authorized") is not False:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design unexpectedly authorizes runtime execution",
            DESIGN_PATH.as_posix(),
        )

    if safety.get("new_execution_authorized") is not False:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design unexpectedly authorizes new execution",
            DESIGN_PATH.as_posix(),
        )

    if safety.get("model_requests_performed") != 0:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design unexpectedly records model requests",
            DESIGN_PATH.as_posix(),
        )

    if budget.get("maximum_model_requests") != 6:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design model-request budget drifted",
            DESIGN_PATH.as_posix(),
        )

    if budget.get("maximum_model_loads") != 1:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design model-load budget drifted",
            DESIGN_PATH.as_posix(),
        )

    if budget.get("maximum_worker_starts") != 1:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design worker-start budget drifted",
            DESIGN_PATH.as_posix(),
        )

    observed_order = tuple(
        str(item.get("case_id")) for item in request_plan if isinstance(item, dict)
    )

    if observed_order != REQUEST_ORDER:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design request order drifted",
            DESIGN_PATH.as_posix(),
        )

    if tuple(diagnostics.get("retained_fields", ())) != RETAINED_FIELDS:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design retained-field contract drifted",
            DESIGN_PATH.as_posix(),
        )

    if diagnostics.get("raw_prompt_retained") is not False:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design raw-prompt boundary drifted",
            DESIGN_PATH.as_posix(),
        )

    if diagnostics.get("raw_output_retained") is not False:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design raw-output boundary drifted",
            DESIGN_PATH.as_posix(),
        )

    case_a = cases[0]
    case_b = cases[1]

    if not isinstance(case_a, dict) or not isinstance(case_b, dict):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "design case objects drifted",
            DESIGN_PATH.as_posix(),
        )

    if case_a.get("case_id") != "A":
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "Case A identity drifted",
            DESIGN_PATH.as_posix(),
        )

    if tuple(case_a.get("message_roles", ())) != ("system", "user"):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "Case A message shape drifted",
            DESIGN_PATH.as_posix(),
        )

    if case_b.get("case_id") != "B":
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "Case B identity drifted",
            DESIGN_PATH.as_posix(),
        )

    if tuple(case_b.get("message_roles", ())) != (
        "system",
        "user",
        "assistant",
        "user",
    ):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "Case B message shape drifted",
            DESIGN_PATH.as_posix(),
        )

    current_runtime_receipts = [
        item
        for item in authorities
        if isinstance(item, dict) and item.get("role") == "current_p5_runtime_composition"
    ]

    if len(current_runtime_receipts) != 1:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "current runtime authority cardinality drifted",
            DESIGN_PATH.as_posix(),
        )

    receipt = current_runtime_receipts[0]

    if receipt.get("sha256") != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_DESIGN_DRIFT",
            "current runtime authority SHA drifted",
            DESIGN_PATH.as_posix(),
        )


def _validate_p4_precedent(root: Path) -> None:
    source = _read_exact(
        root,
        P4_PRECEDENT_PATH,
        P4_PRECEDENT_SHA256,
    ).decode("utf-8")

    markers = (
        "def edge_class(",
        "response_sha256",
        "response_length",
        "json_error_line",
        "json_error_column",
        "json_error_position",
        "markdown_fence_detected",
        '"raw_output_retained": False',
    )

    for marker in markers:
        if marker not in source:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_P4_PRECEDENT_DRIFT",
                "historical P4 observation precedent drifted",
                P4_PRECEDENT_PATH.as_posix(),
            )


def _function_nodes(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    result: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in result:
                raise ImplementationError(
                    "P4_P5_DIFF_IMPLEMENTATION_SOURCE_AMBIGUOUS",
                    "duplicate top-level function name",
                    node.name,
                )
            result[node.name] = node

    return result


def _class_nodes(source: str) -> dict[str, ast.ClassDef]:
    tree = ast.parse(source)
    result: dict[str, ast.ClassDef] = {}

    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            if node.name in result:
                raise ImplementationError(
                    "P4_P5_DIFF_IMPLEMENTATION_SOURCE_AMBIGUOUS",
                    "duplicate top-level class name",
                    node.name,
                )
            result[node.name] = node

    return result


def _assignment_node(
    source: str,
    name: str,
) -> ast.Assign | ast.AnnAssign:
    tree = ast.parse(source)
    matches: list[ast.Assign | ast.AnnAssign] = []

    for node in tree.body:
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
            "P4_P5_DIFF_IMPLEMENTATION_SOURCE_AMBIGUOUS",
            "required top-level assignment cardinality drifted",
            name,
        )

    return matches[0]


def _segment(source: str, node: ast.AST) -> str:
    observed = ast.get_source_segment(source, node)

    if observed is None:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "unable to recover source segment",
        )

    return observed


def _replace_node(
    source: str,
    node: ast.AST,
    replacement: str,
) -> str:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)

    if not isinstance(start, int) or not isinstance(end, int):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "source node line boundary is unavailable",
        )

    lines = source.splitlines(keepends=True)
    normalized = replacement.rstrip() + "\n"
    lines[start - 1 : end] = [normalized]
    return "".join(lines)


def _replace_function(
    source: str,
    name: str,
    replacement: str,
) -> str:
    functions = _function_nodes(source)
    node = functions.get(name)

    if node is None:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_FUNCTION_MISSING",
            "required predecessor function is missing",
            name,
        )

    return _replace_node(
        source,
        node,
        textwrap.dedent(replacement).strip(),
    )


def _replace_assignment(
    source: str,
    name: str,
    replacement: str,
) -> str:
    node = _assignment_node(source, name)
    return _replace_node(source, node, replacement)


def _literal_int_dict_assignment(
    source: str,
    name: str,
) -> dict[str, int]:
    node = _assignment_node(source, name)

    value_node: ast.expr | None = None

    if isinstance(node, ast.Assign):
        value_node = node.value

    if isinstance(node, ast.AnnAssign):
        value_node = node.value

    if value_node is None:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_BUDGET_INVALID",
            "action-budget assignment has no value",
            name,
        )

    raw: object = ast.literal_eval(value_node)

    if not isinstance(raw, dict):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_BUDGET_INVALID",
            "action-budget assignment is not one dictionary",
            name,
        )

    result: dict[str, int] = {}

    for raw_key, raw_value in raw.items():
        if not isinstance(raw_key, str):
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_BUDGET_INVALID",
                "action-budget key is not a string",
                name,
            )

        if isinstance(raw_value, bool) or not isinstance(raw_value, int):
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_BUDGET_INVALID",
                "action-budget value is not an integer",
                name,
            )

        result[raw_key] = raw_value

    return result


def _render_int_dict_assignment(
    name: str,
    values: dict[str, int],
) -> str:
    lines = [f"{name}: Final = {{"]

    for key, value in values.items():
        lines.append(f'    "{key}": {value},')

    lines.append("}")
    return "\n".join(lines)


def _insert_before_function(
    source: str,
    function_name: str,
    block: str,
) -> str:
    functions = _function_nodes(source)
    node = functions.get(function_name)

    if node is None:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_FUNCTION_MISSING",
            "required insertion anchor is missing",
            function_name,
        )

    lines = source.splitlines(keepends=True)
    normalized = textwrap.dedent(block).strip() + "\n\n\n"
    lines[node.lineno - 1 : node.lineno - 1] = [normalized]
    return "".join(lines)


REQUEST_MESSAGES_FUNCTION: Final = r"""
def request_messages(prefix_variant: str) -> list[dict[str, str]]:
    if prefix_variant == "A":
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": EXPECTED_OBJECT_CANONICAL},
        ]

    if prefix_variant == "B":
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": SYNTHETIC_CACHE_CONTEXT_A},
            {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
            {"role": "user", "content": EXPECTED_OBJECT_CANONICAL},
        ]

    raise RuntimeError("unknown composition differential case")
"""


DIFFERENTIAL_HELPERS: Final = r"""

DIFFERENTIAL_IMPLEMENTATION_BASE_COMMIT: Final = "36defc782c08e211680489f4d60a9173de6e9052"
DIFFERENTIAL_DESIGN_RECORD_SHA256: Final = (
    "5bcea57f47573712c5776fcd7d210584c96ece5cf86d09902cf29453e27e39d1"
)
DIFFERENTIAL_REQUEST_ORDER: Final = ("A", "B", "B", "A", "A", "B")
DIFFERENTIAL_RETAINED_FIELDS: Final = (
    "case_id",
    "sequence_index",
    "http_status",
    "response_sha256",
    "response_length",
    "finish_reason",
    "completion_tokens",
    "valid_json",
    "exact_object",
    "json_error_line",
    "json_error_column",
    "json_error_position",
    "first_non_whitespace_class",
    "last_non_whitespace_class",
    "markdown_fence_detected",
)


def differential_edge_class(character: str | None) -> str:
    if character is None:
        return "NONE"

    if character in "{[":
        return "JSON_OPEN"

    if character in "]}":
        return "JSON_CLOSE"

    if character == "`":
        return "BACKTICK"

    if character.isspace():
        return "WHITESPACE"

    if character.isalpha():
        return "ALPHA"

    if character.isdigit():
        return "DIGIT"

    return "OTHER"


def run_differential_request(
    worker: Worker,
    case_id: str,
    sequence_index: int,
    counters: dict[str, int],
) -> dict[str, object]:
    if case_id not in {"A", "B"}:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "unsupported composition differential case",
        )

    consume_actions(counters, "model_requests")
    encoded = canonical_json(request_payload(case_id)).encode("utf-8")
    request = urllib.request.Request(
        bounded_loopback(f"http://127.0.0.1:{worker.port}/v1/chat/completions"),
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=HTTP_TIMEOUT_SECONDS,
        ) as response:
            status_code = response.status
            response_payload = response.read()
    except urllib.error.HTTPError as error:
        raise DiagnosticFailure(
            "P3_P6_REQUEST_FAILED",
            f"differential request HTTP failure: {error.code}",
        ) from error
    except (urllib.error.URLError, TimeoutError) as error:
        raise DiagnosticFailure(
            "P3_P6_REQUEST_FAILED",
            "differential request transport failed",
        ) from error

    if status_code != 200:
        raise DiagnosticFailure(
            "P3_P6_REQUEST_FAILED",
            "differential request returned an unexpected HTTP status",
        )

    try:
        envelope = json.loads(response_payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response envelope is not valid JSON",
        ) from error

    if not isinstance(envelope, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response envelope root is invalid",
        )

    usage = envelope.get("usage")
    choices = envelope.get("choices")

    if not isinstance(usage, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response usage is missing",
        )

    if not isinstance(choices, list) or len(choices) != 1:
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response choices are invalid",
        )

    choice = choices[0]

    if not isinstance(choice, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response choice is invalid",
        )

    message = choice.get("message")

    if not isinstance(message, dict):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response message is invalid",
        )

    content = message.get("content")

    if not isinstance(content, str):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential response content is not a string",
        )

    completion_tokens = usage.get("completion_tokens")

    if (
        isinstance(completion_tokens, bool)
        or not isinstance(completion_tokens, int)
        or not 1 <= completion_tokens <= 32
    ):
        raise DiagnosticFailure(
            "OUTPUT_CONTRACT_FAILURE",
            "differential completion-token budget drifted",
        )

    stripped = content.strip()
    first = stripped[0] if stripped else None
    last = stripped[-1] if stripped else None

    valid_json = False
    exact_object = False
    json_error_line: int | None = None
    json_error_column: int | None = None
    json_error_position: int | None = None

    try:
        parsed = json.loads(content)
        expected = json.loads(EXPECTED_OBJECT_CANONICAL)
        valid_json = True
        exact_object = parsed == expected
    except json.JSONDecodeError as error:
        json_error_line = error.lineno
        json_error_column = error.colno
        json_error_position = error.pos

    row: dict[str, object] = {
        "case_id": case_id,
        "sequence_index": sequence_index,
        "http_status": status_code,
        "response_sha256": sha256_text(content),
        "response_length": len(content),
        "finish_reason": choice.get("finish_reason"),
        "completion_tokens": completion_tokens,
        "valid_json": valid_json,
        "exact_object": exact_object,
        "json_error_line": json_error_line,
        "json_error_column": json_error_column,
        "json_error_position": json_error_position,
        "first_non_whitespace_class": differential_edge_class(first),
        "last_non_whitespace_class": differential_edge_class(last),
        "markdown_fence_detected": "```" in content,
    }

    if tuple(row) != DIFFERENTIAL_RETAINED_FIELDS:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "differential retained-field contract drifted",
        )

    return row


def write_differential_results(
    results: list[dict[str, object]],
    status: str,
) -> None:
    write_json(
        OUTPUT_ROOT / "p4_p5_composition_differential_request_results_v1.json",
        {
            "schema_version": "1.0.0",
            "status": status,
            "scheduled_request_count": len(DIFFERENTIAL_REQUEST_ORDER),
            "observed_request_count": len(results),
            "request_order": list(DIFFERENTIAL_REQUEST_ORDER),
            "results": results,
            "raw_prompt_retained": False,
            "raw_output_retained": False,
        },
    )


def decide_composition_differential(
    results: list[dict[str, object]],
) -> dict[str, object]:
    if len(results) != len(DIFFERENTIAL_REQUEST_ORDER):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "composition differential result count drifted",
        )

    observed_order = tuple(str(row.get("case_id")) for row in results)

    if observed_order != DIFFERENTIAL_REQUEST_ORDER:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "composition differential request order drifted",
        )

    expected_indexes = tuple(range(1, 7))
    observed_indexes_list: list[int] = []

    for row in results:
        sequence_index = row.get("sequence_index")

        if isinstance(sequence_index, int) and not isinstance(sequence_index, bool):
            observed_indexes_list.append(sequence_index)

    observed_indexes = tuple(observed_indexes_list)

    if observed_indexes != expected_indexes:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "composition differential sequence indexes drifted",
        )

    if any(row.get("http_status") != 200 for row in results):
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "composition differential contains a non-200 observation",
        )

    case_a = [row for row in results if row.get("case_id") == "A"]
    case_b = [row for row in results if row.get("case_id") == "B"]

    if len(case_a) != 3 or len(case_b) != 3:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "composition differential case cardinality drifted",
        )

    a_exact = sum(row.get("exact_object") is True for row in case_a)
    b_exact = sum(row.get("exact_object") is True for row in case_b)
    a_valid_json = sum(row.get("valid_json") is True for row in case_a)
    b_valid_json = sum(row.get("valid_json") is True for row in case_b)

    state = "NON_DETERMINISTIC_OR_AMBIGUOUS"

    if a_exact != 3:
        state = "SIMPLE_CONTROL_NOT_RELIABLE"

    if a_exact == 3 and b_exact == 0:
        state = "COMPOSITION_REGRESSION_SUPPORTED"

    if a_exact == 3 and b_exact == 3:
        state = "COMPOSITION_HYPOTHESIS_NOT_REPRODUCED"

    a_hashes = {
        str(row["response_sha256"]) for row in case_a if isinstance(row.get("response_sha256"), str)
    }
    b_hashes = {
        str(row["response_sha256"]) for row in case_b if isinstance(row.get("response_sha256"), str)
    }

    return {
        "schema_version": "1.0.0",
        "status": "DECIDED",
        "decision_state": state,
        "case_a_exact_object_count": a_exact,
        "case_b_exact_object_count": b_exact,
        "case_a_valid_json_count": a_valid_json,
        "case_b_valid_json_count": b_valid_json,
        "case_a_response_hash_cardinality": len(a_hashes),
        "case_b_response_hash_cardinality": len(b_hashes),
        "response_hash_cardinality_is_decision_input": False,
        "variable_under_test": "MESSAGE_COMPOSITION_ONLY",
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }


def differential_failure_record(
    error: BaseException,
    active_failure_code: str,
    failed_stage: str,
    completed_requests: int,
) -> dict[str, object]:
    if isinstance(error, DiagnosticAmbiguity):
        return {
            "schema_version": "1.0.0",
            "status": "DIAGNOSTIC_INVALID",
            "failed_stage": failed_stage,
            "completed_requests": completed_requests,
            "failure_class": error.failure_class,
            "detail_code": None,
            "error_type": type(error).__name__,
            "safe_message": error.safe_message,
        }

    if isinstance(error, DiagnosticFailure):
        return {
            "schema_version": "1.0.0",
            "status": "DIAGNOSTIC_INVALID",
            "failed_stage": failed_stage,
            "completed_requests": completed_requests,
            "failure_class": classify_failure_detail(error.error_code),
            "detail_code": error.error_code,
            "error_type": type(error).__name__,
            "safe_message": error.safe_message,
        }

    return {
        "schema_version": "1.0.0",
        "status": "DIAGNOSTIC_INVALID",
        "failed_stage": failed_stage,
        "completed_requests": completed_requests,
        "failure_class": classify_failure_detail(active_failure_code),
        "detail_code": active_failure_code,
        "error_type": type(error).__name__,
        "safe_message": (sanitize_excerpt(str(error))[:512] or type(error).__name__),
    }


def differential_bundle_outputs() -> dict[str, object]:
    required = {
        "runtime_source_identity_report_v1.json",
        "runtime_install_report_v1.json",
        "runtime_import_closure_report_v1.json",
        "runtime_environment_report_v1.json",
        "p4_p5_composition_differential_runtime_ready_v1.json",
        "p4_p5_composition_differential_request_results_v1.json",
        "p4_p5_composition_differential_decision_v1.json",
        "worker_teardown_report_v1.json",
        "scratch_cleanup_report_v1.json",
        "failure_report_v1.json",
        "p4_p5_composition_differential_summary_v1.json",
        "human_report_v1.md",
    }

    observed = {path.name for path in OUTPUT_ROOT.iterdir() if path.is_file()}

    missing = sorted(required - observed)

    if missing:
        raise DiagnosticFailure(
            "EVIDENCE_PROJECTION_FAILURE",
            "differential output set is incomplete: " + ",".join(missing),
        )

    files = [path for path in sorted(OUTPUT_ROOT.rglob("*")) if path.is_file()]

    if any(path.is_symlink() for path in files):
        raise DiagnosticFailure(
            "EVIDENCE_PROJECTION_FAILURE",
            "differential evidence contains a symbolic link",
        )

    members = [
        {
            "path": path.relative_to(OUTPUT_ROOT).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": file_sha256(path),
        }
        for path in files
        if path.name != "bundle_manifest_v1.json"
    ]

    write_json(
        OUTPUT_ROOT / "bundle_manifest_v1.json",
        {
            "schema_version": "1.0.0",
            "member_count": len(members),
            "members": members,
            "raw_prompt_included": False,
            "raw_model_output_included": False,
        },
    )

    archive_files = [path for path in sorted(OUTPUT_ROOT.rglob("*")) if path.is_file()]

    with zipfile.ZipFile(
        EVIDENCE_ZIP,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        for path in archive_files:
            archive.write(
                path,
                arcname=path.relative_to(OUTPUT_ROOT).as_posix(),
            )

    return {
        "evidence_zip_sha256": file_sha256(EVIDENCE_ZIP),
        "evidence_zip_size_bytes": EVIDENCE_ZIP.stat().st_size,
        "evidence_member_count": len(archive_files),
    }
"""


DIFFERENTIAL_MAIN: Final = r"""

def main() -> int:
    if OUTPUT_ROOT.exists() or SCRATCH_ROOT.exists() or EVIDENCE_ZIP.exists():
        raise RuntimeError("P4/P5 composition differential output or scratch path already exists")

    OUTPUT_ROOT.mkdir(parents=True)
    LOG_ROOT.mkdir()
    SCRATCH_ROOT.mkdir()

    counters = {
        "kaggle_sessions": 1,
        "runtime_install_attempts": 0,
        "runtime_import_closure_probes": 0,
        "model_loads": 0,
        "worker_starts": 0,
        "model_requests": 0,
        "benchmark_trajectory_requests": 0,
        "network_requests": 0,
        "hidden_retries": 0,
        "external_spend": 0,
    }

    worker: Worker | None = None
    teardown_reports: list[dict[str, object]] = []
    results: list[dict[str, object]] = []
    failure: dict[str, object] | None = None
    decision: dict[str, object] | None = None
    authorization: dict[str, object] | None = None

    active_failure_code = "P3_P6_RUNTIME_SOURCE_IDENTITY_MISMATCH"
    failed_stage = "SOURCE_IDENTITY"

    try:
        source_identity = write_runtime_source_identity_report()

        failed_stage = "PRIVACY_BOUNDARY"
        active_failure_code = "P3_P6_PRIVACY_BOUNDARY_VIOLATION"
        require_private_environment()

        failed_stage = "TRANSACTION_ADMISSION"
        active_failure_code = "AUTHORITY_FAILURE"
        authorization = require_transaction_bound_context()

        failed_stage = "WHEELHOUSE"
        active_failure_code = "P3_P6_WHEELHOUSE_INVALID"
        wheelhouse = discover_one_directory(RUNTIME_OUTPUT_DIRECTORY)
        validate_wheelhouse(wheelhouse)

        failed_stage = "MODEL_SNAPSHOT"
        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        source_snapshot = discover_model_snapshot()

        failed_stage = "RUNTIME_INSTALL"
        active_failure_code = "P3_P6_RUNTIME_INSTALL_FAILED"
        install_runtime(wheelhouse, counters)

        failed_stage = "RUNTIME_IDENTITY"
        active_failure_code = "P3_P6_PLATFORM_IDENTITY_MISMATCH"
        runtime_identity = validate_target_runtime()

        runtime_environment = process_tree_environment(
            0,
            SCRATCH_ROOT / "environment_report_model_home",
        )
        environment_report = runtime_environment_report(runtime_environment)

        if environment_report["prohibited_stub_path_present"] is not False:
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                "exact-runtime environment retained a CUDA stub path",
            )

        if environment_report["ld_preload_absent"] is not True:
            raise DiagnosticFailure(
                "MODEL_CONSTRUCTION_FAILURE",
                "exact-runtime environment retained LD_PRELOAD",
            )

        write_json(
            OUTPUT_ROOT / "runtime_environment_report_v1.json",
            environment_report,
        )

        failed_stage = "IMPORT_CLOSURE"
        active_failure_code = "P3_P6_RUNTIME_PROCESS_TREE_IMPORT_CLOSURE_FAILED"
        validate_process_tree_import_closure(counters)

        failed_stage = "MODEL_HOME"
        active_failure_code = "P3_P6_MODEL_IDENTITY_MISMATCH"
        model_home, snapshot = prepare_model_home(source_snapshot)

        failed_stage = "WORKER_STARTUP"
        active_failure_code = "MODEL_CONSTRUCTION_FAILURE"

        worker = Worker(
            "worker_1",
            0,
            8001,
            model_home,
            snapshot,
            generation=1,
        )
        worker.start(counters)
        worker.wait_ready()
        worker.validate_model()

        native_origins = validate_native_origin_closure(worker)

        write_json(
            OUTPUT_ROOT / "p4_p5_composition_differential_runtime_ready_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "PASSED",
                "source_identity": source_identity,
                "runtime_identity": runtime_identity,
                "worker": worker.report(),
                "native_origin_closure": native_origins,
                "model_repository": MODEL_REPOSITORY,
                "model_revision": MODEL_REVISION,
                "model_snapshot_sha256": MODEL_SNAPSHOT_SHA256,
            },
        )

        failed_stage = "DIFFERENTIAL_REQUESTS"
        active_failure_code = "P3_P6_REQUEST_FAILED"

        for sequence_index, case_id in enumerate(
            DIFFERENTIAL_REQUEST_ORDER,
            start=1,
        ):
            row = run_differential_request(
                worker,
                case_id,
                sequence_index,
                counters,
            )
            results.append(row)

            status = "PARTIAL"

            if len(results) == len(DIFFERENTIAL_REQUEST_ORDER):
                status = "COMPLETE"

            write_differential_results(results, status)

    except BaseException as error:
        failure = differential_failure_record(
            error,
            active_failure_code,
            failed_stage,
            len(results),
        )

    finally:
        if worker is not None:
            teardown_reports.append(
                safe_worker_teardown(
                    worker,
                    "DIFFERENTIAL_TERMINAL_FINALIZATION",
                )
            )

    teardown_failures = tuple(
        item for item in teardown_reports if item.get("status") not in {"PASSED", "NOT_STARTED"}
    )

    teardown_status = "NOT_RUN"

    if teardown_reports:
        teardown_status = "PASSED"

    if teardown_failures:
        teardown_status = "FAILED"

    write_json(
        OUTPUT_ROOT / "worker_teardown_report_v1.json",
        {
            "schema_version": "1.0.0",
            "status": teardown_status,
            "worker_teardowns": teardown_reports,
            "all_capture_threads_finalized": (
                not teardown_failures
                and all(
                    bool(
                        item.get(
                            "capture_threads_finalized",
                            True,
                        )
                    )
                    for item in teardown_reports
                )
            ),
            "all_ports_closed": (
                not teardown_failures
                and all(bool(item.get("port_closed_after", True)) for item in teardown_reports)
            ),
            "all_gpu_processes_absent": (
                not teardown_failures
                and all(
                    bool(
                        item.get(
                            "gpu_processes_absent_after",
                            True,
                        )
                    )
                    for item in teardown_reports
                )
            ),
        },
    )

    if teardown_failures and failure is None:
        failure = {
            "schema_version": "1.0.0",
            "status": "DIAGNOSTIC_INVALID",
            "failed_stage": "WORKER_TEARDOWN",
            "completed_requests": len(results),
            "failure_class": "TEARDOWN_FAILURE",
            "detail_code": "TEARDOWN_FAILURE",
            "error_type": "WorkerTeardownFailure",
            "safe_message": "worker teardown proof failed",
        }

    try:
        cleanup = cleanup_scratch()
    except BaseException as error:
        cleanup = {
            "status": "FAILED",
            "scratch_exists_after": SCRATCH_ROOT.exists(),
            "error_type": type(error).__name__,
            "safe_message": (sanitize_excerpt(str(error))[:512] or type(error).__name__),
        }

    write_json(
        OUTPUT_ROOT / "scratch_cleanup_report_v1.json",
        cleanup,
    )

    if cleanup.get("status") != "PASSED" and failure is None:
        failure = {
            "schema_version": "1.0.0",
            "status": "DIAGNOSTIC_INVALID",
            "failed_stage": "SCRATCH_CLEANUP",
            "completed_requests": len(results),
            "failure_class": "TEARDOWN_FAILURE",
            "detail_code": "P3_P6_SCRATCH_CLEANUP_FAILED",
            "error_type": str(cleanup.get("error_type")),
            "safe_message": str(cleanup.get("safe_message")),
        }

    if not (OUTPUT_ROOT / "p4_p5_composition_differential_request_results_v1.json").is_file():
        status = "NOT_RUN"

        if results:
            status = "PARTIAL"

        write_differential_results(results, status)

    if failure is None:
        expected_counters = {
            "kaggle_sessions": 1,
            "runtime_install_attempts": 1,
            "runtime_import_closure_probes": 1,
            "model_loads": 1,
            "worker_starts": 1,
            "model_requests": 6,
            "benchmark_trajectory_requests": 0,
            "network_requests": 0,
            "hidden_retries": 0,
            "external_spend": 0,
        }

        for name, expected in expected_counters.items():
            if counters[name] != expected:
                failure = {
                    "schema_version": "1.0.0",
                    "status": "DIAGNOSTIC_INVALID",
                    "failed_stage": "ACTION_RECONCILIATION",
                    "completed_requests": len(results),
                    "failure_class": "REQUEST_RECONCILIATION_FAILURE",
                    "detail_code": "P3_P6_ACTION_BUDGET_EXCEEDED",
                    "error_type": "ActionBudgetDrift",
                    "safe_message": (f"{name} expected {expected}, observed {counters[name]}"),
                }
                break

    if failure is None:
        try:
            decision = decide_composition_differential(results)
        except BaseException as error:
            failure = differential_failure_record(
                error,
                "HARNESS_SEMANTIC_FAILURE",
                "DIFFERENTIAL_DECISION",
                len(results),
            )

    if decision is not None and failure is None:
        write_json(
            OUTPUT_ROOT / "p4_p5_composition_differential_decision_v1.json",
            decision,
        )

    if decision is None or failure is not None:
        write_json(
            OUTPUT_ROOT / "p4_p5_composition_differential_decision_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NOT_EVALUATED",
                "decision_state": None,
                "blocked_by": (None if failure is None else failure.get("failure_class")),
                "raw_prompt_retained": False,
                "raw_output_retained": False,
            },
        )

    failure_class = None if failure is None else str(failure.get("failure_class"))

    ensure_runtime_source_identity_report(failure_class)
    ensure_install_report(failure_class)
    ensure_import_closure_report(failure_class)

    environment_path = OUTPUT_ROOT / "runtime_environment_report_v1.json"

    if not environment_path.is_file():
        write_json(
            environment_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
                "raw_environment_retained": False,
            },
        )

    ready_path = OUTPUT_ROOT / "p4_p5_composition_differential_runtime_ready_v1.json"

    if not ready_path.is_file():
        write_json(
            ready_path,
            {
                "schema_version": "1.0.0",
                "status": "NOT_RUN",
                "blocked_by": failure_class or "UPSTREAM_PRECONDITION",
            },
        )

    if failure is None:
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            {
                "schema_version": "1.0.0",
                "status": "NOT_APPLICABLE",
                "failure_class": None,
                "detail_code": None,
                "error_type": None,
                "safe_message": None,
                "completed_requests": len(results),
                "teardown_status": teardown_status,
            },
        )

    if failure is not None:
        failure["teardown_status"] = teardown_status
        write_json(
            OUTPUT_ROOT / "failure_report_v1.json",
            failure,
        )

    diagnostic_valid = decision is not None and failure is None

    decision_state: object = None

    if decision is not None and failure is None:
        decision_state = decision.get("decision_state")

    summary = {
        "schema_version": "1.0.0",
        "diagnostic_id": ("auragateway-p4-p5-composition-differential-v1"),
        "implementation_base_commit": (DIFFERENTIAL_IMPLEMENTATION_BASE_COMMIT),
        "design_record_sha256": DIFFERENTIAL_DESIGN_RECORD_SHA256,
        "authorization": authorization,
        "status": ("DIAGNOSTIC_COMPLETE" if diagnostic_valid else "DIAGNOSTIC_INVALID"),
        "decision_state": decision_state,
        "scheduled_request_count": len(DIFFERENTIAL_REQUEST_ORDER),
        "completed_request_count": len(results),
        "request_order": list(DIFFERENTIAL_REQUEST_ORDER),
        "counters": counters,
        "worker_teardown_status": teardown_status,
        "scratch_cleanup_status": cleanup.get("status"),
        "failure_class": failure_class,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
        "credentials_used": False,
        "customer_data_present": False,
        "external_network_requests": 0,
        "hidden_retries": 0,
        "pilot_execution_performed": False,
        "measured_abc_execution_performed": False,
        "next_gate": ("PRESERVE_AND_DISPOSITION_P4_P5_COMPOSITION_DIFFERENTIAL_V1"),
    }

    write_json(
        OUTPUT_ROOT / "p4_p5_composition_differential_summary_v1.json",
        summary,
    )

    human = (
        "# AuraGateway P4/P5 Composition Differential V1\n\n"
        f"- Status: {summary['status']}\n"
        f"- Decision: {summary['decision_state']}\n"
        f"- Completed requests: {len(results)} / 6\n"
        f"- Worker teardown: {teardown_status}\n"
        f"- Scratch cleanup: {cleanup.get('status')}\n"
        "- Raw prompts retained: false\n"
        "- Raw model outputs retained: false\n"
        "- Hidden retries: 0\n"
        "- No P5/P6 qualification trajectory was executed.\n"
        "- No measured A/B/C benchmark trajectory was executed.\n"
        "- Production readiness is not claimed.\n"
    )

    write_text(
        OUTPUT_ROOT / "human_report_v1.md",
        human,
    )

    try:
        bundle = differential_bundle_outputs()
    except BaseException as error:
        terminal_payload = {
            **summary,
            "status": "DIAGNOSTIC_INVALID",
            "decision_state": None,
            "bundle_status": "FAILED",
            "bundle_error_type": type(error).__name__,
        }
        print(canonical_json(terminal_payload))
        return 2

    terminal_payload = {
        **summary,
        **bundle,
    }

    print(canonical_json(terminal_payload))
    return 0 if diagnostic_valid else 2
"""


def _validate_predecessor_budget(source: str) -> dict[str, int]:
    budget = _literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    )

    required = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 3,
        "worker_starts": 3,
        "model_requests": 6,
    }

    if set(budget) != set(required):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_PREDECESSOR_BUDGET_DRIFT",
            "predecessor action budget keyset drifted",
            "ACTION_BUDGET_LIMITS",
        )

    for key, expected in required.items():
        if budget.get(key) != expected:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_PREDECESSOR_BUDGET_DRIFT",
                "predecessor action budget drifted",
                key,
            )

    return budget


def _function_segments(source: str) -> dict[str, str]:
    return {name: _segment(source, node) for name, node in _function_nodes(source).items()}


def _class_segments(source: str) -> dict[str, str]:
    return {name: _segment(source, node) for name, node in _class_nodes(source).items()}


def _validate_change_surface(
    predecessor: str,
    successor: str,
) -> int:
    predecessor_functions = _function_segments(predecessor)
    successor_functions = _function_segments(successor)

    expected_successor_names = set(predecessor_functions) | set(ADDED_FUNCTIONS)

    if set(successor_functions) != expected_successor_names:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
            "successor top-level function inventory drifted",
            RUNTIME_PATH.as_posix(),
        )

    changed: list[str] = []
    unchanged = 0

    for name, original in predecessor_functions.items():
        observed = successor_functions[name]

        if observed == original:
            unchanged += 1

        if observed != original:
            changed.append(name)

    if tuple(sorted(changed)) != tuple(sorted(CHANGED_EXISTING_FUNCTIONS)):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
            "unexpected predecessor function changed",
            ",".join(sorted(changed)),
        )

    predecessor_classes = _class_segments(predecessor)
    successor_classes = _class_segments(successor)

    if predecessor_classes != successor_classes:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_CLASS_SURFACE_DRIFT",
            "predecessor class implementation drifted",
            RUNTIME_PATH.as_posix(),
        )

    return unchanged


def _validate_successor_contract(source: str) -> None:
    functions = _function_nodes(source)
    main_node = functions["main"]
    messages_node = functions["request_messages"]

    main_source = _segment(source, main_node)
    messages_source = _segment(source, messages_node)

    forbidden_main_markers = (
        "decide_p5(",
        "decide_p6(",
        "route_isolation(",
        "run_structured_request(",
        "tokenize_request(",
        "worker_2",
        "POST_RESET_COLD",
        "CROSS_WORKER_COLD",
        "WORKER1_RETENTION",
    )

    for marker in forbidden_main_markers:
        if marker in main_source:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_P5_P6_REACHABILITY_DRIFT",
                "successor main retained a prohibited P5/P6 trajectory seam",
                marker,
            )

    required_main_markers = (
        "DIFFERENTIAL_REQUEST_ORDER",
        "run_differential_request(",
        "decide_composition_differential(",
        "safe_worker_teardown(",
        "cleanup_scratch()",
    )

    for marker in required_main_markers:
        if marker not in main_source:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_MAIN_CONTRACT_DRIFT",
                "successor main is missing a required differential seam",
                marker,
            )

    required_message_markers = (
        'if prefix_variant == "A":',
        '{"role": "system", "content": SYSTEM_PROMPT}',
        '{"role": "user", "content": EXPECTED_OBJECT_CANONICAL}',
        'if prefix_variant == "B":',
        '{"role": "user", "content": SYNTHETIC_CACHE_CONTEXT_A}',
        '{"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK}',
    )

    for marker in required_message_markers:
        if marker not in messages_source:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_MESSAGE_CONTRACT_DRIFT",
                "successor message composition drifted",
                marker,
            )

    budget = _literal_int_dict_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
    )

    expected_budget_values = {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 1,
        "worker_starts": 1,
        "model_requests": 6,
    }

    if set(budget) != set(expected_budget_values):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_SUCCESSOR_BUDGET_DRIFT",
            "successor action budget keyset drifted",
            "ACTION_BUDGET_LIMITS",
        )

    for key, expected in expected_budget_values.items():
        if budget.get(key) != expected:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_SUCCESSOR_BUDGET_DRIFT",
                "successor action budget drifted",
                key,
            )

    if "model response is not valid JSON" in _segment(
        source,
        functions["run_differential_request"],
    ):
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_OBSERVATION_CONTRACT_DRIFT",
            "successor differential runner raises the predecessor JSON error",
            RUNTIME_PATH.as_posix(),
        )


def build_runtime_payload(
    root: Path,
) -> tuple[bytes, int]:
    _validate_design(root)
    _validate_p4_precedent(root)

    predecessor_bytes = _read_exact(
        root,
        PREDECESSOR_RUNTIME_PATH,
        PREDECESSOR_RUNTIME_SHA256,
    )
    predecessor = predecessor_bytes.decode("utf-8")

    budget = _validate_predecessor_budget(predecessor)
    successor_budget = dict(budget)
    successor_budget["model_loads"] = 1
    successor_budget["worker_starts"] = 1

    source = predecessor

    source = _replace_assignment(
        source,
        "OUTPUT_ROOT",
        ('OUTPUT_ROOT: Final = WORK_ROOT / "p4_p5_composition_differential_v1"'),
    )

    source = _replace_assignment(
        source,
        "SCRATCH_ROOT",
        ('SCRATCH_ROOT: Final = WORK_ROOT / "p4_p5_composition_differential_v1_scratch"'),
    )

    source = _replace_assignment(
        source,
        "EVIDENCE_ZIP",
        ('EVIDENCE_ZIP: Final = WORK_ROOT / "ag-p4-p5-composition-differential-evidence-v1.zip"'),
    )

    source = _replace_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
        _render_int_dict_assignment(
            "ACTION_BUDGET_LIMITS",
            successor_budget,
        ),
    )

    source = _replace_function(
        source,
        "request_messages",
        REQUEST_MESSAGES_FUNCTION,
    )

    source = _insert_before_function(
        source,
        "main",
        DIFFERENTIAL_HELPERS,
    )

    source = _replace_function(
        source,
        "main",
        DIFFERENTIAL_MAIN,
    )

    compile(
        source,
        RUNTIME_PATH.as_posix(),
        "exec",
    )

    unchanged = _validate_change_surface(
        predecessor,
        source,
    )
    _validate_successor_contract(source)

    return source.encode("utf-8"), unchanged


def _candidate_sha(root: Path, relative: Path) -> str:
    return _sha256(_read_required(root, relative))


def _build_expected(
    root: Path,
) -> tuple[bytes, bytes, bytes]:
    runtime_payload, unchanged_count = build_runtime_payload(root)

    review = ImplementationReview(
        review_id=("auragateway-p4-p5-composition-differential-implementation-v1-review"),
        status="APPROVED_STATIC_SUCCESSOR_IMPLEMENTATION",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        historical_p4_precedent_sha256=P4_PRECEDENT_SHA256,
        implementation_source_sha256=_candidate_sha(
            root,
            SOURCE_PATH,
        ),
        focused_test_sha256=_candidate_sha(
            root,
            TEST_PATH,
        ),
        runtime_payload_sha256=_sha256(runtime_payload),
        request_order=REQUEST_ORDER,
        changed_existing_functions=CHANGED_EXISTING_FUNCTIONS,
        added_functions=ADDED_FUNCTIONS,
        unchanged_existing_function_count=unchanged_count,
        next_gate=NEXT_GATE,
    )

    review_bytes = _canonical_bytes(review.model_dump(mode="json"))

    record = ImplementationRecord(
        record_id=("auragateway-p4-p5-composition-differential-implementation-v1"),
        status="IMPLEMENTED_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_path=PREDECESSOR_RUNTIME_PATH.as_posix(),
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        successor_runtime_path=RUNTIME_PATH.as_posix(),
        successor_runtime_sha256=_sha256(runtime_payload),
        review_sha256=_sha256(review_bytes),
        next_gate=NEXT_GATE,
        non_claims=(
            "The composition hypothesis has not been proven.",
            "No Kaggle execution occurred in this implementation tranche.",
            "No model was loaded by this implementation producer.",
            "No model request was performed by this implementation producer.",
            "No live execution authorization was issued.",
            "The predecessor P5/P6 runtime was not modified.",
            "P5 failure is not established.",
            "P6 failure is not established.",
            "Generic Qwen JSON unreliability is not established.",
            "No runtime remediation is authorized.",
            "No measured A/B/C execution is authorized.",
        ),
    )

    return (
        runtime_payload,
        review_bytes,
        _canonical_bytes(record.model_dump(mode="json")),
    )


def generate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)

    for relative, payload in (
        (RUNTIME_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)

    if _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH)) != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "predecessor runtime changed during successor generation",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    return {
        "status": "P4_P5_COMPOSITION_DIFFERENTIAL_IMPLEMENTATION_GENERATED",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "predecessor_runtime_preserved": True,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "model_requests_performed": 0,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)

    expected = (
        (RUNTIME_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    )

    for relative, payload in expected:
        observed = _read_required(root, relative)

        if observed != payload:
            raise ImplementationError(
                "P4_P5_DIFF_IMPLEMENTATION_GENERATED_ARTIFACT_DRIFT",
                "generated successor implementation artifact drifted",
                relative.as_posix(),
            )

    if _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH)) != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "P4_P5_DIFF_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "predecessor runtime identity drifted",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )

    return {
        "status": "P4_P5_COMPOSITION_DIFFERENTIAL_IMPLEMENTATION_VALID",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "predecessor_runtime_preserved": True,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "model_requests_performed": 0,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=("generate", "validate"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        root = cast(Path, arguments.repo_root).resolve()

        result = generate(root) if arguments.command == "generate" else validate(root)

        print(
            json.dumps(
                result,
                sort_keys=True,
            )
        )
        return 0

    except (
        ImplementationError,
        ValueError,
        SyntaxError,
        json.JSONDecodeError,
    ) as error:
        if isinstance(error, ImplementationError):
            payload = error.envelope()

        if not isinstance(error, ImplementationError):
            payload = {
                "error_code": ("P4_P5_DIFF_IMPLEMENTATION_VALIDATION_ERROR"),
                "safe_message": str(error),
                "path": None,
            }

        print(
            json.dumps(
                payload,
                sort_keys=True,
            ),
            file=__import__("sys").stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

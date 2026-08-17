"""Generate the B-vs-D marker-diversified differential runtime V1.

The governed token-count-matched runtime is immutable input authority. This
producer emits a separate successor runtime for the frozen six-observation B-vs-D
diagnostic. The producer performs no Kaggle, GPU, model, worker, or request
execution and issues no execution authority.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
from collections.abc import Sequence
from pathlib import Path
from typing import Final, Never, cast

from pydantic import BaseModel, ConfigDict, Field, model_validator

BASE_MAIN_COMMIT: Final = "cfe36407fe7d7b1c71938d218886872e47a1be39"
DESIGN_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_design_v1.json"
)
DESIGN_SHA256: Final = "2e07651681d98d604f0e0f6b4e8964906f39b8bfa0e48b8f8fa8e9de431e7ef9"
PREDECESSOR_RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "p4_p5_token_count_matched_context_structure_differential_runtime_v1.py"
)
PREDECESSOR_RUNTIME_SHA256: Final = (
    "9327d3fef6b1ba2ea8e9d380338e69e6084388b0d365019af3505e8a6a880834"
)
SOURCE_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1.py"
)
TEST_PATH: Final = Path(
    "tests/unit/local_abc/"
    "test_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1.py"
)
RUNTIME_PATH: Final = Path(
    "src/auragateway/local_abc/"
    "b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_runtime_v1.py"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1_review.json"
)
RECORD_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_b_vs_d_cumulative_length_locked_marker_diversified_"
    "differential_implementation_v1.json"
)
NEXT_GATE: Final = (
    "MERGE_THEN_DESIGN_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_"
    "DIFFERENTIAL_EXECUTION_AUTHORIZATION_V1"
)
B_CONDITION: Final = "B_NEUTRAL_REPEATED_24X"
D_CONDITION: Final = "D_NEUTRAL_MARKER_DIVERSIFIED_24X_CUMULATIVE_LENGTH_LOCKED"
REQUEST_ORDER: Final = (
    B_CONDITION,
    D_CONDITION,
    D_CONDITION,
    B_CONDITION,
    B_CONDITION,
    D_CONDITION,
)
PROMPT_TOKEN_COUNT: Final = 899
B_TOKEN_SHA256: Final = "02f2675a0490d16e3a39de9619ae865a8f73024b26c6f9126bf4dea197d99f68"
B_PAYLOAD_SHA256: Final = "1c1ccaad07d7f83eca3c79ae015d231dbe8f3da7d6b055ec10da6070378c4efb"
D_TOKEN_SHA256: Final = "878ecc057fbc92764c7b8bddc3024e12720470b84a72d974ef677c16d1e37e21"
D_PAYLOAD_SHA256: Final = "0728e8632e4694cd670e472751154d38dcacc34071d74e1caad8ece6608c8010"
TOKEN_PROFILE: Final = tuple(range(83, 900, 34))
D_MARKERS: Final = (
    "birch",
    "grove",
    "juniper",
    "lagoon",
    "meadow",
    "prairie",
    "spruce",
    "umber",
    "willow",
    "acorn",
    "alder",
    "beech",
    "brook",
    "caper",
    "clover",
    "cove",
    "dune",
    "finch",
    "flint",
    "glade",
    "ivy",
    "larch",
    "lily",
    "orchid",
)
CHANGED_EXISTING_FUNCTIONS: Final = ("main",)
ADDED_FUNCTIONS: Final = (
    "decide_marker_diversified_differential",
    "initialize_marker_diversified_journal",
    "marker_diversified_bundle_outputs",
    "marker_diversified_condition_status",
    "marker_diversified_context",
    "marker_diversified_expected_payload_sha256",
    "marker_diversified_expected_token_sha256",
    "marker_diversified_failure_record",
    "marker_diversified_public_observation",
    "marker_diversified_request_messages",
    "marker_diversified_request_payload",
    "marker_diversified_token_identity",
    "marker_diversified_tokenize_payload",
    "persist_marker_diversified_pre_request_identity",
    "run_marker_diversified_fresh_worker_observation",
    "run_marker_diversified_observation",
    "write_marker_diversified_results",
)


class ImplementationError(RuntimeError):
    def __init__(self, error_code: str, safe_message: str, path: str | None = None) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {"error_code": self.error_code, "safe_message": self.safe_message, "path": self.path}


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ImplementationError("B_VS_D_IMPLEMENTATION_ARGUMENT_INVALID", message)


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
    request_order: tuple[str, ...]
    changed_existing_functions: tuple[str, ...]
    added_functions: tuple[str, ...]
    unchanged_existing_function_count: int = Field(ge=1)
    observations_per_condition: int
    prompt_token_count_per_condition: int
    maximum_model_requests: int
    maximum_model_loads: int
    maximum_worker_starts: int
    maximum_hidden_retries: int
    maximum_replacement_observations: int
    fresh_worker_process_per_observation: bool
    b_anchor_reproduction_rule_preserved: bool
    cumulative_prompt_token_profile_contract_preserved: bool
    text_boundary_token_boundary_assumption_used: bool
    invalid_json_retained_as_observation: bool
    predecessor_runtime_preserved: bool
    p5_p6_trajectory_reachable_from_successor_main: bool
    runtime_execution_authorized: bool
    new_execution_authorized: bool
    next_gate: str

    @model_validator(mode="after")
    def exact(self) -> ImplementationReview:
        if self.request_order != REQUEST_ORDER:
            raise ValueError("request order drifted")
        if self.changed_existing_functions != CHANGED_EXISTING_FUNCTIONS:
            raise ValueError("changed function inventory drifted")
        if self.added_functions != ADDED_FUNCTIONS:
            raise ValueError("added function inventory drifted")
        if (self.maximum_model_requests, self.maximum_model_loads, self.maximum_worker_starts) != (
            6,
            6,
            6,
        ):
            raise ValueError("action budget drifted")
        if self.maximum_hidden_retries != 0 or self.maximum_replacement_observations != 0:
            raise ValueError("retry or replacement budget drifted")
        if self.text_boundary_token_boundary_assumption_used:
            raise ValueError("retired token-boundary assumption returned")
        if self.runtime_execution_authorized or self.new_execution_authorized:
            raise ValueError("static implementation cannot authorize execution")
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
    review_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_requests_performed: int
    model_loads_performed: int
    worker_starts_performed: int
    kaggle_execution_performed: bool
    gpu_execution_performed: bool
    differential_notebook_generated: bool
    live_authorization_issued: bool
    runtime_execution_authorized: bool
    new_execution_authorized: bool
    runtime_fix_authorized: bool
    threshold_search_authorized: bool
    p5_p6_requalification_authorized: bool
    measured_abc_execution_authorized: bool
    next_gate: str
    non_claims: tuple[str, ...] = Field(min_length=12)

    @model_validator(mode="after")
    def exact(self) -> ImplementationRecord:
        if self.status != "IMPLEMENTED_NOT_EXECUTED":
            raise ValueError("implementation status drifted")
        if any(
            (
                self.model_requests_performed,
                self.model_loads_performed,
                self.worker_starts_performed,
            )
        ):
            raise ValueError("static producer recorded runtime execution")
        if any(
            (
                self.kaggle_execution_performed,
                self.gpu_execution_performed,
                self.differential_notebook_generated,
                self.live_authorization_issued,
                self.runtime_execution_authorized,
                self.new_execution_authorized,
                self.runtime_fix_authorized,
                self.threshold_search_authorized,
                self.p5_p6_requalification_authorized,
                self.measured_abc_execution_authorized,
            )
        ):
            raise ValueError("static implementation crossed authority boundary")
        return self


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return (
        json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode("utf-8")


def _read_required(root: Path, relative: Path) -> bytes:
    path = root / relative
    if not path.is_file() or path.is_symlink():
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_ARTIFACT_MISSING",
            "required artifact is missing or unsafe",
            relative.as_posix(),
        )
    return path.read_bytes()


def _read_exact(root: Path, relative: Path, expected: str) -> bytes:
    payload = _read_required(root, relative)
    if _sha256(payload) != expected:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_AUTHORITY_DRIFT",
            "required authority identity drifted",
            relative.as_posix(),
        )
    return payload


def _base_commit_is_ancestor_of_head(root: Path) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_MAIN_COMMIT, "HEAD"],
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
        "B_VS_D_IMPLEMENTATION_GIT_STATE_INVALID", "unable to verify base ancestry"
    )


def _mapping(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", f"{name} is not an object", DESIGN_PATH.as_posix()
        )
    return cast(dict[str, object], value)


def _array(value: object, name: str) -> list[object]:
    if not isinstance(value, list):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", f"{name} is not an array", DESIGN_PATH.as_posix()
        )
    return cast(list[object], value)


def _validate_design(root: Path) -> dict[str, tuple[str, ...]]:
    if not _base_commit_is_ancestor_of_head(root):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_BASE_MAIN_DRIFT",
            "implementation base is not an ancestor of HEAD",
        )
    payload = _read_exact(root, DESIGN_PATH, DESIGN_SHA256)
    try:
        raw: object = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_INVALID",
            "frozen design is not valid JSON",
            DESIGN_PATH.as_posix(),
        ) from error
    design = _mapping(raw, "design")
    if design.get("design_status") != "DESIGN_FROZEN_NOT_EXECUTED":
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "design status drifted", DESIGN_PATH.as_posix()
        )
    if design.get("base_main_commit") != "de5289686c23b00a9504b5301db12683144ad969":
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "design base identity drifted",
            DESIGN_PATH.as_posix(),
        )
    if (
        design.get("next_gate")
        != "IMPLEMENT_AND_MERGE_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"
    ):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "design next gate drifted", DESIGN_PATH.as_posix()
        )

    conditions = _array(design.get("conditions"), "conditions")
    if len(conditions) != 2:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "condition inventory drifted",
            DESIGN_PATH.as_posix(),
        )
    expected = {
        B_CONDITION: ("FAILURE_ANCHOR", "0_OF_3", B_TOKEN_SHA256, B_PAYLOAD_SHA256, 1),
        D_CONDITION: ("INTERVENTION", "NOT_EXECUTED", D_TOKEN_SHA256, D_PAYLOAD_SHA256, 24),
    }
    segments: dict[str, tuple[str, ...]] = {}
    observed_ids: list[str] = []
    for raw_condition in conditions:
        item = _mapping(raw_condition, "condition")
        condition_id = item.get("condition_id")
        if not isinstance(condition_id, str) or condition_id not in expected:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "condition id drifted", DESIGN_PATH.as_posix()
            )
        observed_ids.append(condition_id)
        role, history, token_sha, payload_sha, unique_count = expected[condition_id]
        checks = {
            "role": role,
            "historical_exact_object_result": history,
            "prompt_token_count": 899,
            "prompt_token_sha256": token_sha,
            "request_payload_sha256": payload_sha,
            "segment_count": 24,
            "unique_segment_count": unique_count,
        }
        for key, value in checks.items():
            if item.get(key) != value:
                raise ImplementationError(
                    "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
                    "condition contract drifted",
                    f"{condition_id}.{key}",
                )
        profile = tuple(_array(item.get("cumulative_prompt_token_count_profile"), "token profile"))
        increments = tuple(
            _array(item.get("cumulative_prompt_token_increments"), "token increments")
        )
        if profile != TOKEN_PROFILE or increments != (34,) * 24:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
                "cumulative token profile drifted",
                condition_id,
            )
        raw_segments = _array(item.get("segments"), "segments")
        if len(raw_segments) != 24 or not all(isinstance(value, str) for value in raw_segments):
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "segment inventory drifted", condition_id
            )
        observed_segments = tuple(cast(str, value) for value in raw_segments)
        if len(set(observed_segments)) != unique_count:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "segment uniqueness drifted", condition_id
            )
        markers = tuple(_array(item.get("marker_sequence"), "marker sequence"))
        if condition_id == B_CONDITION and markers != ("meadow",) * 24:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "B marker sequence drifted", condition_id
            )
        if condition_id == D_CONDITION and markers != D_MARKERS:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "D marker sequence drifted", condition_id
            )
        segments[condition_id] = observed_segments
    if tuple(observed_ids) != (B_CONDITION, D_CONDITION):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "condition order drifted", DESIGN_PATH.as_posix()
        )

    request_plan = _array(design.get("request_plan"), "request plan")
    observed_order: list[str] = []
    observed_ordinals: list[int] = []
    for raw_item in request_plan:
        item = _mapping(raw_item, "request-plan item")
        condition_id = item.get("condition_id")
        ordinal = item.get("ordinal")
        if (
            not isinstance(condition_id, str)
            or isinstance(ordinal, bool)
            or not isinstance(ordinal, int)
        ):
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
                "request-plan item drifted",
                DESIGN_PATH.as_posix(),
            )
        observed_order.append(condition_id)
        observed_ordinals.append(ordinal)
    if tuple(observed_order) != REQUEST_ORDER or tuple(observed_ordinals) != tuple(range(1, 7)):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "request chronology drifted",
            DESIGN_PATH.as_posix(),
        )

    budget = _mapping(design.get("execution_budget"), "execution budget")
    if budget != {
        "maximum_kaggle_sessions": 1,
        "maximum_runtime_install_attempts": 1,
        "maximum_runtime_import_closure_probes": 1,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "maximum_model_requests": 6,
        "maximum_output_tokens_per_request": 32,
        "hidden_retries_permitted": 0,
        "replacement_observations_permitted": 0,
        "external_network_requests_permitted": 0,
        "benchmark_trajectory_requests_permitted": 0,
        "external_spend": 0,
    }:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "execution budget drifted", DESIGN_PATH.as_posix()
        )
    starting = _mapping(design.get("starting_state"), "starting state")
    if starting != {
        "strategy": "FRESH_WORKER_PROCESS_PER_OBSERVATION",
        "prior_request_cache_carryover_permitted": False,
        "require_fresh_worker_identity": True,
        "require_zero_cached_prefix_baseline": True,
        "teardown_required_between_observations": True,
        "teardown_failure_invalidates_diagnostic": True,
    }:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "starting-state contract drifted",
            DESIGN_PATH.as_posix(),
        )
    primary = _mapping(design.get("primary_endpoint"), "primary endpoint")
    if primary != {
        "field": "exact_object",
        "per_condition_observations": 3,
        "condition_pass": "3_OF_3_EXACT_OBJECT_TRUE",
        "condition_fail": "0_OF_3_EXACT_OBJECT_TRUE",
        "condition_mixed": "1_OR_2_OF_3_EXACT_OBJECT_TRUE",
    }:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "primary endpoint drifted", DESIGN_PATH.as_posix()
        )
    comparator = _mapping(design.get("comparator_contract"), "comparator contract")
    if (
        comparator.get("cumulative_prompt_token_profile_equal") is not True
        or comparator.get("marker_only_textual_change") is not True
    ):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "comparator intervention drifted",
            DESIGN_PATH.as_posix(),
        )
    if comparator.get("text_segment_boundary_must_equal_token_boundary") is not False:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "retired token-boundary assumption returned",
            DESIGN_PATH.as_posix(),
        )
    rules = _array(design.get("decision_rules"), "decision rules")
    states = tuple(_mapping(item, "decision rule").get("state") for item in rules)
    if states != (
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK",
        "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL",
        "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM",
        "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE",
        "DIAGNOSTIC_INVALID",
    ):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "decision matrix drifted", DESIGN_PATH.as_posix()
        )
    safety = _mapping(design.get("safety"), "safety")
    for key in (
        "runtime_execution_authorized",
        "new_execution_authorized",
        "kaggle_execution_performed",
        "gpu_execution_performed",
        "model_loaded",
        "worker_started",
        "execution_authorization_issued",
        "threshold_search_authorized",
        "p5_p6_requalification_authorized",
        "measured_abc_execution_authorized",
    ):
        if safety.get(key) is not False:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT", "design safety boundary drifted", key
            )
    if safety.get("model_requests_performed") != 0:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_DESIGN_DRIFT",
            "design recorded model execution",
            DESIGN_PATH.as_posix(),
        )
    return segments


def _function_nodes(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    result: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in result:
                raise ImplementationError(
                    "B_VS_D_IMPLEMENTATION_SOURCE_AMBIGUOUS",
                    "duplicate top-level function",
                    node.name,
                )
            result[node.name] = node
    return result


def _class_nodes(source: str) -> dict[str, ast.ClassDef]:
    return {node.name: node for node in ast.parse(source).body if isinstance(node, ast.ClassDef)}


def _segment(source: str, node: ast.AST) -> str:
    observed = ast.get_source_segment(source, node)
    if observed is None:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED", "unable to recover source segment"
        )
    return observed


def _function_segment(source: str, name: str) -> str:
    node = _function_nodes(source).get(name)
    if node is None:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_FUNCTION_MISSING",
            "required predecessor function is missing",
            name,
        )
    return _segment(source, node)


def _assignment_node(source: str, name: str) -> ast.Assign | ast.AnnAssign:
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
            "B_VS_D_IMPLEMENTATION_SOURCE_AMBIGUOUS", "assignment cardinality drifted", name
        )
    return matches[0]


def _replace_node(source: str, node: ast.AST, replacement: str) -> str:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if not isinstance(start, int) or not isinstance(end, int):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED", "source boundary is unavailable"
        )
    lines = source.splitlines(keepends=True)
    lines[start - 1 : end] = [replacement.rstrip() + "\n"]
    return "".join(lines)


def _replace_assignment(source: str, name: str, replacement: str) -> str:
    return _replace_node(source, _assignment_node(source, name), replacement)


def _replace_function(source: str, name: str, replacement: str) -> str:
    node = _function_nodes(source).get(name)
    if node is None:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_FUNCTION_MISSING",
            "required predecessor function is missing",
            name,
        )
    return _replace_node(source, node, replacement)


def _insert_before_function(source: str, name: str, block: str) -> str:
    node = _function_nodes(source).get(name)
    if node is None:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_FUNCTION_MISSING", "required insertion anchor is missing", name
        )
    lines = source.splitlines(keepends=True)
    lines[node.lineno - 1 : node.lineno - 1] = [block.rstrip() + "\n\n\n"]
    return "".join(lines)


def _literal_int_dict_assignment(source: str, name: str) -> dict[str, int]:
    node = _assignment_node(source, name)
    value = node.value
    if value is None:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_BUDGET_INVALID", "budget assignment has no value", name
        )
    raw: object = ast.literal_eval(value)
    if not isinstance(raw, dict):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_BUDGET_INVALID", "budget is not a dictionary", name
        )
    result: dict[str, int] = {}
    for key, item in raw.items():
        if not isinstance(key, str) or isinstance(item, bool) or not isinstance(item, int):
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_BUDGET_INVALID", "budget entry is invalid", name
            )
        result[key] = item
    return result


def _render_int_dict_assignment(name: str, values: dict[str, int]) -> str:
    lines = [f"{name}: Final = {{"]
    lines.extend(f'    "{key}": {value},' for key, value in values.items())
    lines.append("}")
    return "\n".join(lines)


def _string_chunks(value: str, size: int = 72) -> tuple[str, ...]:
    if value == "":
        return ("",)
    return tuple(value[index : index + size] for index in range(0, len(value), size))


def _render_string_assignment(name: str, value: str) -> str:
    literal = json.dumps(value, ensure_ascii=True)
    one_line = f"{name}: Final = {literal}"
    if len(one_line) <= 100:
        return one_line
    lines = [f"{name}: Final = ("]
    lines.extend(f"    {json.dumps(chunk, ensure_ascii=True)}" for chunk in _string_chunks(value))
    lines.append(")")
    return "\n".join(lines)


def _render_string_tuple(name: str, values: tuple[str, ...]) -> str:
    lines = [f"{name}: Final = ("]
    for value in values:
        literal = json.dumps(value, ensure_ascii=True)
        if len(literal) <= 80:
            lines.append(f"    {literal},")
            continue
        lines.append("    (")
        lines.extend(
            f"        {json.dumps(chunk, ensure_ascii=True)}" for chunk in _string_chunks(value)
        )
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines)


def _derive_function(
    source: str, old: str, new: str, replacements: tuple[tuple[str, str], ...] = ()
) -> str:
    observed = _function_segment(source, old)
    header = f"def {old}("
    if header not in observed:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "expected function header is unavailable",
            old,
        )
    observed = observed.replace(header, f"def {new}(", 1)
    for before, after in replacements:
        if before not in observed:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "expected derived-function marker is unavailable",
                f"{old}:{before}",
            )
        observed = observed.replace(before, after)
    return observed


def _render_helpers(source: str, segments: dict[str, tuple[str, ...]]) -> str:
    b_segments = segments[B_CONDITION]
    d_segments = segments[D_CONDITION]
    constants = "\n".join(
        (
            _render_string_assignment("B_VS_D_IMPLEMENTATION_BASE_COMMIT", BASE_MAIN_COMMIT),
            _render_string_assignment("B_VS_D_DESIGN_RECORD_SHA256", DESIGN_SHA256),
            _render_string_assignment("B_VS_D_B_CONDITION", B_CONDITION),
            _render_string_assignment("B_VS_D_D_CONDITION", D_CONDITION),
            _render_string_tuple("B_VS_D_REQUEST_ORDER", REQUEST_ORDER),
            "B_VS_D_PROMPT_TOKEN_COUNT: Final = 899",
            _render_string_assignment("B_VS_D_B_TOKEN_SHA256", B_TOKEN_SHA256),
            _render_string_assignment("B_VS_D_B_PAYLOAD_SHA256", B_PAYLOAD_SHA256),
            _render_string_assignment("B_VS_D_D_TOKEN_SHA256", D_TOKEN_SHA256),
            _render_string_assignment("B_VS_D_D_PAYLOAD_SHA256", D_PAYLOAD_SHA256),
            _render_string_tuple("B_VS_D_B_SEGMENTS", b_segments),
            _render_string_tuple("B_VS_D_D_SEGMENTS", d_segments),
            """MARKER_DIVERSIFIED_OUTPUT_NAMES: Final = (
    "runtime_source_identity_report_v1.json",
    "runtime_install_report_v1.json",
    "runtime_environment_report_v1.json",
    "runtime_import_closure_report_v1.json",
    "b_vs_d_marker_diversified_runtime_ready_v1.json",
    "pre_request_token_identity_journal_v1.json",
    "b_vs_d_marker_diversified_request_results_v1.json",
    "b_vs_d_marker_diversified_decision_v1.json",
    "worker_teardown_report_v1.json",
    "scratch_cleanup_report_v1.json",
    "failure_report_v1.json",
    "b_vs_d_marker_diversified_summary_v1.json",
    "human_report_v1.md",
    "bundle_manifest_v1.json",
)""",
        )
    )
    context = """def marker_diversified_context(condition_id: str) -> str:
    if condition_id == B_VS_D_B_CONDITION:
        if len(B_VS_D_B_SEGMENTS) != 24 or len(set(B_VS_D_B_SEGMENTS)) != 1:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "B failure-anchor segment identity drifted",
            )
        return "".join(B_VS_D_B_SEGMENTS) + SYSTEM_PROMPT
    if condition_id == B_VS_D_D_CONDITION:
        if len(B_VS_D_D_SEGMENTS) != 24 or len(set(B_VS_D_D_SEGMENTS)) != 24:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "D marker-diversified segment inventory drifted",
            )
        return "".join(B_VS_D_D_SEGMENTS) + SYSTEM_PROMPT
    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "unsupported B-vs-D condition",
    )"""
    messages = _derive_function(
        source,
        "token_matched_request_messages",
        "marker_diversified_request_messages",
        (("token_matched_context", "marker_diversified_context"),),
    )
    request_payload = _derive_function(
        source,
        "token_matched_request_payload",
        "marker_diversified_request_payload",
        (("token_matched_request_messages", "marker_diversified_request_messages"),),
    )
    tokenize_payload = _derive_function(
        source,
        "token_matched_tokenize_payload",
        "marker_diversified_tokenize_payload",
        (("token_matched_request_messages", "marker_diversified_request_messages"),),
    )
    token_identity = _derive_function(
        source,
        "token_matched_token_identity",
        "marker_diversified_token_identity",
        (("token_matched_tokenize_payload", "marker_diversified_tokenize_payload"),),
    ).replace("token-matched", "B-vs-D")
    expected = """def marker_diversified_expected_token_sha256(condition_id: str) -> str:
    if condition_id == B_VS_D_B_CONDITION:
        return B_VS_D_B_TOKEN_SHA256
    if condition_id == B_VS_D_D_CONDITION:
        return B_VS_D_D_TOKEN_SHA256
    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "unsupported B-vs-D token identity condition",
    )


def marker_diversified_expected_payload_sha256(condition_id: str) -> str:
    if condition_id == B_VS_D_B_CONDITION:
        return B_VS_D_B_PAYLOAD_SHA256
    if condition_id == B_VS_D_D_CONDITION:
        return B_VS_D_D_PAYLOAD_SHA256
    raise DiagnosticFailure(
        "HARNESS_SEMANTIC_FAILURE",
        "unsupported B-vs-D payload identity condition",
    )"""
    journal = _derive_function(
        source,
        "initialize_token_matched_journal",
        "initialize_marker_diversified_journal",
    ).replace(
        "auragateway-p4-p5-token-count-matched-context-structure-",
        "auragateway-b-vs-d-cumulative-length-locked-marker-diversified-",
    )
    persist = _derive_function(
        source,
        "persist_token_matched_pre_request_identity",
        "persist_marker_diversified_pre_request_identity",
    )
    observation = _derive_function(
        source,
        "run_token_matched_observation",
        "run_marker_diversified_observation",
        (
            ("token_matched_token_identity", "marker_diversified_token_identity"),
            ("token_matched_request_payload", "marker_diversified_request_payload"),
            ("token_matched_expected_token_sha256", "marker_diversified_expected_token_sha256"),
            ("token_matched_expected_payload_sha256", "marker_diversified_expected_payload_sha256"),
            (
                "persist_token_matched_pre_request_identity",
                "persist_marker_diversified_pre_request_identity",
            ),
            ("TOKEN_MATCHED_PROMPT_TOKEN_COUNT", "B_VS_D_PROMPT_TOKEN_COUNT"),
        ),
    ).replace("token-matched", "B-vs-D")
    old_guard = """    if condition_id not in {
        "A_ORIGINAL_24X_ANCHOR",
        "B_NEUTRAL_REPEATED_24X",
        "C_NEUTRAL_DIVERSE_24_SEGMENT",
    }:"""
    new_guard = """    if condition_id not in {
        B_VS_D_B_CONDITION,
        B_VS_D_D_CONDITION,
    }:"""
    if old_guard not in observation:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "token-matched condition guard drifted",
            "run_token_matched_observation",
        )
    observation = observation.replace(old_guard, new_guard)
    public = _derive_function(
        source, "token_matched_public_observation", "marker_diversified_public_observation"
    )
    fresh_worker = _derive_function(
        source,
        "run_token_matched_fresh_worker_observation",
        "run_marker_diversified_fresh_worker_observation",
        (("run_token_matched_observation", "run_marker_diversified_observation"),),
    ).replace("TOKEN_MATCHED_OBSERVATION", "B_VS_D_OBSERVATION")
    write_results = _derive_function(
        source,
        "write_token_matched_results",
        "write_marker_diversified_results",
        (
            (
                "p4_p5_token_matched_request_results_v1.json",
                "b_vs_d_marker_diversified_request_results_v1.json",
            ),
            ("TOKEN_MATCHED_REQUEST_ORDER", "B_VS_D_REQUEST_ORDER"),
            ("token_matched_public_observation", "marker_diversified_public_observation"),
        ),
    )
    condition_status = _derive_function(
        source, "token_matched_condition_status", "marker_diversified_condition_status"
    )
    failure_record = _derive_function(
        source, "token_matched_failure_record", "marker_diversified_failure_record"
    )
    bundle = (
        _derive_function(
            source,
            "token_matched_bundle_outputs",
            "marker_diversified_bundle_outputs",
            (("TOKEN_MATCHED_OUTPUT_NAMES", "MARKER_DIVERSIFIED_OUTPUT_NAMES"),),
        )
        .replace("token-matched", "B-vs-D")
        .replace(
            "auragateway-p4-p5-token-count-matched-context-structure-differential-v1",
            "auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-v1",
        )
    )
    decision = """def decide_marker_diversified_differential(
    results: list[dict[str, object]],
    worker_reports: list[dict[str, object]],
    teardown_reports: list[dict[str, object]],
    counters: dict[str, int],
) -> dict[str, object]:
    if len(results) != 6:
        raise DiagnosticFailure("REQUEST_RECONCILIATION_FAILURE", "B-vs-D result count drifted")
    if tuple(str(row.get("condition_id")) for row in results) != B_VS_D_REQUEST_ORDER:
        raise DiagnosticFailure("REQUEST_RECONCILIATION_FAILURE", "B-vs-D chronology drifted")
    if tuple(row.get("sequence_index") for row in results) != tuple(range(1, 7)):
        raise DiagnosticFailure("REQUEST_RECONCILIATION_FAILURE", "B-vs-D sequence indexes drifted")
    if len(worker_reports) != 6 or len(teardown_reports) != 6:
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "fresh-worker evidence cardinality drifted",
        )
    if any(item.get("status") != "PASSED" for item in teardown_reports):
        raise DiagnosticFailure("TEARDOWN_FAILURE", "one or more observation teardowns failed")
    worker_identities = {
        str(row.get("worker_process_identity_sha256"))
        for row in results
        if isinstance(row.get("worker_process_identity_sha256"), str)
    }
    if len(worker_identities) != 6:
        raise DiagnosticFailure(
            "P5_STARTING_STATE_FAILURE",
            "fresh worker process identity was reused",
        )
    if any(row.get("zero_cache_baseline") is not True for row in results):
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
    condition_rows = {
        condition_id: [row for row in results if row.get("condition_id") == condition_id]
        for condition_id in (B_VS_D_B_CONDITION, B_VS_D_D_CONDITION)
    }
    if any(len(rows) != 3 for rows in condition_rows.values()):
        raise DiagnosticFailure(
            "REQUEST_RECONCILIATION_FAILURE",
            "B-vs-D condition cardinality drifted",
        )
    expected_identities = {
        B_VS_D_B_CONDITION: (B_VS_D_B_TOKEN_SHA256, B_VS_D_B_PAYLOAD_SHA256),
        B_VS_D_D_CONDITION: (B_VS_D_D_TOKEN_SHA256, B_VS_D_D_PAYLOAD_SHA256),
    }
    for condition_id, rows in condition_rows.items():
        expected_token, expected_payload = expected_identities[condition_id]
        observed_tokens = {(row.get("token_count"), row.get("token_sha256")) for row in rows}
        if observed_tokens != {(B_VS_D_PROMPT_TOKEN_COUNT, expected_token)}:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "B-vs-D condition token identity failed reconciliation",
            )
        if {row.get("payload_sha256") for row in rows} != {expected_payload}:
            raise DiagnosticFailure(
                "HARNESS_SEMANTIC_FAILURE",
                "B-vs-D condition payload identity failed reconciliation",
            )
    exact_counts = {
        condition_id: sum(row.get("exact_object") is True for row in rows)
        for condition_id, rows in condition_rows.items()
    }
    valid_json_counts = {
        condition_id: sum(row.get("valid_json") is True for row in rows)
        for condition_id, rows in condition_rows.items()
    }
    statuses = {
        condition_id: marker_diversified_condition_status(exact_count)
        for condition_id, exact_count in exact_counts.items()
    }
    b_exact = exact_counts[B_VS_D_B_CONDITION]
    d_exact = exact_counts[B_VS_D_D_CONDITION]
    if b_exact != 0:
        state = "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE"
    elif d_exact in {1, 2}:
        state = "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM"
    elif d_exact == 3:
        state = "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK"
    elif d_exact == 0:
        state = "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL"
    else:
        raise DiagnosticFailure(
            "HARNESS_SEMANTIC_FAILURE",
            "B-vs-D outcome is outside the frozen decision contract",
        )
    return {
        "schema_version": "1.0.0",
        "status": "DECIDED",
        "decision_state": state,
        "primary_endpoint": "exact_object",
        "condition_exact_object_counts": exact_counts,
        "condition_valid_json_counts": valid_json_counts,
        "condition_endpoint_statuses": statuses,
        "b_anchor_required_exact_object_count": 0,
        "b_anchor_reproduced": b_exact == 0,
        "mechanistic_inference_permitted": b_exact == 0 and d_exact in {0, 3},
        "fresh_worker_process_per_observation": True,
        "worker_identity_cardinality": len(worker_identities),
        "all_condition_token_identities_matched": True,
        "all_condition_payload_identities_matched": True,
        "complete_cumulative_prompt_token_profile_locked": True,
        "text_boundary_token_boundary_assumption_used": False,
        "marker_lexical_semantic_novelty_bounded_not_eliminated": True,
        "exact_ngram_block_and_periodicity_effects_not_individually_isolated": True,
        "cache_telemetry_is_diagnostic_only": True,
        "raw_prompt_retained": False,
        "raw_output_retained": False,
    }"""
    return "\n\n\n".join(
        (
            constants,
            context,
            messages,
            request_payload,
            tokenize_payload,
            token_identity,
            expected,
            journal,
            persist,
            observation,
            public,
            fresh_worker,
            write_results,
            condition_status,
            decision,
            failure_record,
            bundle,
        )
    )


def _derive_main(source: str) -> str:
    main = _function_segment(source, "main")
    replacements = (
        ("TOKEN_MATCHED_REQUEST_ORDER", "B_VS_D_REQUEST_ORDER"),
        ("initialize_token_matched_journal", "initialize_marker_diversified_journal"),
        (
            "run_token_matched_fresh_worker_observation",
            "run_marker_diversified_fresh_worker_observation",
        ),
        ("write_token_matched_results", "write_marker_diversified_results"),
        ("decide_token_matched_differential", "decide_marker_diversified_differential"),
        ("token_matched_failure_record", "marker_diversified_failure_record"),
        ("token_matched_bundle_outputs", "marker_diversified_bundle_outputs"),
        (
            "p4_p5_token_matched_runtime_ready_v1.json",
            "b_vs_d_marker_diversified_runtime_ready_v1.json",
        ),
        ("p4_p5_token_matched_decision_v1.json", "b_vs_d_marker_diversified_decision_v1.json"),
        ("p4_p5_token_matched_summary_v1.json", "b_vs_d_marker_diversified_summary_v1.json"),
        ("TOKEN_MATCHED_IMPLEMENTATION_BASE_COMMIT", "B_VS_D_IMPLEMENTATION_BASE_COMMIT"),
        ("TOKEN_MATCHED_DESIGN_RECORD_SHA256", "B_VS_D_DESIGN_RECORD_SHA256"),
        ("TOKEN_MATCHED_PROMPT_TOKEN_COUNT", "B_VS_D_PROMPT_TOKEN_COUNT"),
        ("token-matched differential", "B-vs-D differential"),
        ('"model_loads": 9', '"model_loads": 6'),
        ('"worker_starts": 9', '"worker_starts": 6'),
        ('"model_requests": 9', '"model_requests": 6'),
        ('"scheduled_worker_starts": 9', '"scheduled_worker_starts": 6'),
        ('"scheduled_model_loads": 9', '"scheduled_model_loads": 6'),
        ('"scheduled_model_requests": 9', '"scheduled_model_requests": 6'),
        ('"scheduled_worker_count": 9', '"scheduled_worker_count": 6'),
        ("len(results) == 9", "len(results) == 6"),
        ('"scheduled_requests": 9', '"scheduled_requests": 6'),
        (
            '"auragateway-p4-p5-token-count-matched-context-structure-differential-v1"',
            '"auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-v1"',
        ),
        (
            '"PRESERVE_AND_DISPOSITION_P4_P5_TOKEN_COUNT_MATCHED_CONTEXT_STRUCTURE_DIFFERENTIAL_V1"',
            '"PRESERVE_AND_DISPOSITION_B_VS_D_CUMULATIVE_LENGTH_LOCKED_MARKER_DIVERSIFIED_DIFFERENTIAL_V1"',
        ),
        (
            "# AuraGateway P4/P5 Token-Count-Matched Context-Structure Differential V1",
            "# AuraGateway B-vs-D Marker-Diversified Differential V1",
        ),
        (
            "- Conditions: A original anchor, B neutral repeated, C neutral diverse\\n",
            "- Conditions: B repeated failure anchor, D marker-diversified intervention\\n",
        ),
    )
    for before, after in replacements:
        if before not in main:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
                "expected main marker is unavailable",
                before,
            )
        main = main.replace(before, after)
    old_output_path_guard = (
        "        raise RuntimeError(\n"
        '            "B-vs-D differential output, scratch, or evidence path already exists"\n'
        "        )"
    )
    new_output_path_guard = (
        "        raise RuntimeError("
        '"B-vs-D differential output, scratch, or evidence path already exists")'
    )
    main = main.replace(old_output_path_guard, new_output_path_guard)
    old_map = """        "condition_token_sha256": {
            "A_ORIGINAL_24X_ANCHOR": TOKEN_MATCHED_A_TOKEN_SHA256,
            "B_NEUTRAL_REPEATED_24X": TOKEN_MATCHED_B_TOKEN_SHA256,
            "C_NEUTRAL_DIVERSE_24_SEGMENT": TOKEN_MATCHED_C_TOKEN_SHA256,
        },"""
    new_map = """        "condition_token_sha256": {
            B_VS_D_B_CONDITION: B_VS_D_B_TOKEN_SHA256,
            B_VS_D_D_CONDITION: B_VS_D_D_TOKEN_SHA256,
        },"""
    if old_map not in main:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_SOURCE_SEGMENT_FAILED",
            "summary token map drifted",
            "condition_token_sha256",
        )
    main = main.replace(old_map, new_map)
    main = main.replace("/ 9\\n", "/ 6\\n")
    return main


def _function_segments(source: str) -> dict[str, str]:
    return {name: _segment(source, node) for name, node in _function_nodes(source).items()}


def _class_segments(source: str) -> dict[str, str]:
    return {name: _segment(source, node) for name, node in _class_nodes(source).items()}


def _validate_change_surface(predecessor: str, successor: str) -> int:
    before = _function_segments(predecessor)
    after = _function_segments(successor)
    if set(after) != set(before) | set(ADDED_FUNCTIONS):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
            "successor function inventory drifted",
            RUNTIME_PATH.as_posix(),
        )
    changed: list[str] = []
    unchanged = 0
    for name, original in before.items():
        if after[name] == original:
            unchanged += 1
        else:
            changed.append(name)
    if tuple(sorted(changed)) != tuple(sorted(CHANGED_EXISTING_FUNCTIONS)):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_FUNCTION_SURFACE_DRIFT",
            "unexpected predecessor function changed",
            ",".join(sorted(changed)),
        )
    if _class_segments(predecessor) != _class_segments(successor):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_CLASS_SURFACE_DRIFT",
            "predecessor class implementation drifted",
            RUNTIME_PATH.as_posix(),
        )
    return unchanged


def _validate_successor_contract(source: str) -> None:
    functions = _function_nodes(source)
    main = _segment(source, functions["main"])
    for marker in (
        "TOKEN_MATCHED_REQUEST_ORDER",
        "run_token_matched_fresh_worker_observation(",
        "decide_token_matched_differential(",
        "REPETITION_REQUEST_ORDER",
        "run_fresh_worker_observation(",
        "decide_repetition_differential(",
        "decide_p5(",
        "decide_p6(",
        "route_isolation(",
        "run_structured_request(",
        "run_attributed_request(",
    ):
        if marker in main:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_P5_P6_REACHABILITY_DRIFT",
                "successor main retained a predecessor trajectory",
                marker,
            )
    for marker in (
        "B_VS_D_REQUEST_ORDER",
        "run_marker_diversified_fresh_worker_observation(",
        "decide_marker_diversified_differential(",
        '"model_loads": 6',
        '"worker_starts": 6',
        '"model_requests": 6',
    ):
        if marker not in main:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_MAIN_CONTRACT_DRIFT",
                "successor main is missing a required seam",
                marker,
            )
    runner = _segment(source, functions["run_marker_diversified_observation"])
    required = (
        "persist_marker_diversified_pre_request_identity(",
        "validate_zero_cache_baseline(worker)",
        'consume_actions(counters, "model_requests")',
        "B_VS_D_PROMPT_TOKEN_COUNT",
        "marker_diversified_expected_token_sha256(condition_id)",
        "marker_diversified_expected_payload_sha256(condition_id)",
        '"valid_json": valid_json',
        '"exact_object": exact_object',
        '"raw_prompt_retained": False',
        '"raw_output_retained": False',
    )
    for marker in required:
        if marker not in runner:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_OBSERVATION_CONTRACT_DRIFT",
                "observation contract drifted",
                marker,
            )
    if "validate_structured_response(" in runner:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_OBSERVATION_CONTRACT_DRIFT",
            "invalid JSON would abort instead of remaining an observation",
            "validate_structured_response",
        )
    if (
        not runner.index("persist_marker_diversified_pre_request_identity(")
        < runner.index("validate_zero_cache_baseline(worker)")
        < runner.index('consume_actions(counters, "model_requests")')
    ):
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_OBSERVATION_CONTRACT_DRIFT",
            "pre-request identity chronology drifted",
            "run_marker_diversified_observation",
        )
    decision = _segment(source, functions["decide_marker_diversified_differential"])
    for marker in (
        "MARKER_DIVERSIFICATION_RESTORES_BEHAVIOR_UNDER_CUMULATIVE_LENGTH_LOCK",
        "MARKER_DIVERSIFICATION_INSUFFICIENT_AT_D_REPETITION_LEVEL",
        "D_CONDITION_UNSTABLE_NO_MECHANISTIC_CLAIM",
        "B_ANCHOR_NONREPRODUCTION_INVALIDATES_INFERENCE",
        "complete_cumulative_prompt_token_profile_locked",
        "text_boundary_token_boundary_assumption_used",
        "marker_lexical_semantic_novelty_bounded_not_eliminated",
    ):
        if marker not in decision:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_DECISION_CONTRACT_DRIFT", "decision contract drifted", marker
            )
    if _literal_int_dict_assignment(source, "ACTION_BUDGET_LIMITS") != {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 6,
        "worker_starts": 6,
        "model_requests": 6,
    }:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_SUCCESSOR_BUDGET_DRIFT",
            "successor action budget drifted",
            "ACTION_BUDGET_LIMITS",
        )


def build_runtime_payload(root: Path) -> tuple[bytes, int]:
    segments = _validate_design(root)
    predecessor_bytes = _read_exact(root, PREDECESSOR_RUNTIME_PATH, PREDECESSOR_RUNTIME_SHA256)
    predecessor = predecessor_bytes.decode("utf-8")
    if _literal_int_dict_assignment(predecessor, "ACTION_BUDGET_LIMITS") != {
        "runtime_install_attempts": 1,
        "runtime_import_closure_probes": 1,
        "model_loads": 9,
        "worker_starts": 9,
        "model_requests": 9,
    }:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_PREDECESSOR_BUDGET_DRIFT",
            "predecessor action budget drifted",
            "ACTION_BUDGET_LIMITS",
        )
    source = predecessor
    source = _replace_assignment(
        source, "NOTEBOOK_NAME", 'NOTEBOOK_NAME: Final = "ag-b-vs-d-marker-diversified-diff-v1"'
    )
    source = _replace_assignment(
        source, "SOURCE_MAIN_COMMIT", f'SOURCE_MAIN_COMMIT: Final = "{BASE_MAIN_COMMIT}"'
    )
    source = _replace_assignment(
        source,
        "OUTPUT_ROOT",
        (
            "OUTPUT_ROOT: Final = (\n"
            '    WORK_ROOT / "b_vs_d_cumulative_length_locked_marker_diversified_differential_v1"\n'
            ")"
        ),
    )
    source = _replace_assignment(
        source,
        "SCRATCH_ROOT",
        (
            "SCRATCH_ROOT: Final = (\n"
            '    WORK_ROOT / "b_vs_d_cumulative_length_locked_marker_'
            'diversified_differential_v1_scratch"\n'
            ")"
        ),
    )
    source = _replace_assignment(
        source,
        "EVIDENCE_ZIP",
        (
            "EVIDENCE_ZIP: Final = (\n"
            '    WORK_ROOT / "ag-b-vs-d-cumulative-length-locked-marker-'
            'diversified-differential-evidence-v1.zip"\n'
            ")"
        ),
    )
    source = _replace_assignment(
        source,
        "ACTION_BUDGET_LIMITS",
        _render_int_dict_assignment(
            "ACTION_BUDGET_LIMITS",
            {
                "runtime_install_attempts": 1,
                "runtime_import_closure_probes": 1,
                "model_loads": 6,
                "worker_starts": 6,
                "model_requests": 6,
            },
        ),
    )
    source = _insert_before_function(source, "main", _render_helpers(source, segments))
    source = _replace_function(source, "main", _derive_main(predecessor))
    compile(source, RUNTIME_PATH.as_posix(), "exec")
    unchanged = _validate_change_surface(predecessor, source)
    _validate_successor_contract(source)
    return source.encode("utf-8"), unchanged


def _candidate_sha(root: Path, relative: Path) -> str:
    return _sha256(_read_required(root, relative))


def _build_expected(root: Path) -> tuple[bytes, bytes, bytes]:
    runtime_payload, unchanged = build_runtime_payload(root)
    review = ImplementationReview(
        review_id="auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-implementation-v1-review",
        status="APPROVED_STATIC_SUCCESSOR_IMPLEMENTATION",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        implementation_source_sha256=_candidate_sha(root, SOURCE_PATH),
        focused_test_sha256=_candidate_sha(root, TEST_PATH),
        runtime_payload_sha256=_sha256(runtime_payload),
        request_order=REQUEST_ORDER,
        changed_existing_functions=CHANGED_EXISTING_FUNCTIONS,
        added_functions=ADDED_FUNCTIONS,
        unchanged_existing_function_count=unchanged,
        observations_per_condition=3,
        prompt_token_count_per_condition=899,
        maximum_model_requests=6,
        maximum_model_loads=6,
        maximum_worker_starts=6,
        maximum_hidden_retries=0,
        maximum_replacement_observations=0,
        fresh_worker_process_per_observation=True,
        b_anchor_reproduction_rule_preserved=True,
        cumulative_prompt_token_profile_contract_preserved=True,
        text_boundary_token_boundary_assumption_used=False,
        invalid_json_retained_as_observation=True,
        predecessor_runtime_preserved=True,
        p5_p6_trajectory_reachable_from_successor_main=False,
        runtime_execution_authorized=False,
        new_execution_authorized=False,
        next_gate=NEXT_GATE,
    )
    review_bytes = _canonical_bytes(review)
    record = ImplementationRecord(
        record_id="auragateway-b-vs-d-cumulative-length-locked-marker-diversified-differential-implementation-v1",
        status="IMPLEMENTED_NOT_EXECUTED",
        base_main_commit=BASE_MAIN_COMMIT,
        design_record_sha256=DESIGN_SHA256,
        predecessor_runtime_path=PREDECESSOR_RUNTIME_PATH.as_posix(),
        predecessor_runtime_sha256=PREDECESSOR_RUNTIME_SHA256,
        successor_runtime_path=RUNTIME_PATH.as_posix(),
        successor_runtime_sha256=_sha256(runtime_payload),
        review_sha256=_sha256(review_bytes),
        model_requests_performed=0,
        model_loads_performed=0,
        worker_starts_performed=0,
        kaggle_execution_performed=False,
        gpu_execution_performed=False,
        differential_notebook_generated=False,
        live_authorization_issued=False,
        runtime_execution_authorized=False,
        new_execution_authorized=False,
        runtime_fix_authorized=False,
        threshold_search_authorized=False,
        p5_p6_requalification_authorized=False,
        measured_abc_execution_authorized=False,
        next_gate=NEXT_GATE,
        non_claims=(
            "The B-vs-D differential has not been executed.",
            "D endpoint behavior has not yet been observed.",
            "B anchor reproduction has not yet been observed in this tranche.",
            "Exact repetition is not established as the sole cause.",
            "Aligned 16-token block recurrence is not established as causal.",
            "Marker lexical novelty is not eliminated.",
            "Marker semantic novelty is not eliminated.",
            "An exact repetition threshold is not established.",
            "The exact root cause is not established.",
            "Prefix caching itself is not established as defective.",
            "No Kaggle execution occurred in this implementation tranche.",
            "No GPU execution occurred in this implementation tranche.",
            "No model was loaded by this implementation producer.",
            "No worker was started by this implementation producer.",
            "No model request was performed by this implementation producer.",
            "No live execution authorization was issued.",
            "The predecessor token-matched runtime was not modified.",
            "P5 was not requalified.",
            "P6 was not requalified.",
            "No threshold search is authorized.",
            "No measured North-Star A/B/C execution is authorized.",
            "Production readiness is not established.",
        ),
    )
    return runtime_payload, review_bytes, _canonical_bytes(record)


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
            "B_VS_D_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "predecessor runtime changed during generation",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )
    return {
        "status": "B_VS_D_IMPLEMENTATION_GENERATED",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "predecessor_runtime_preserved": True,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "model_requests_performed": 0,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    root = root.resolve()
    runtime_payload, review_bytes, record_bytes = _build_expected(root)
    for relative, payload in (
        (RUNTIME_PATH, runtime_payload),
        (REVIEW_PATH, review_bytes),
        (RECORD_PATH, record_bytes),
    ):
        if _read_required(root, relative) != payload:
            raise ImplementationError(
                "B_VS_D_IMPLEMENTATION_GENERATED_ARTIFACT_DRIFT",
                "generated implementation artifact drifted",
                relative.as_posix(),
            )
    if _sha256(_read_required(root, PREDECESSOR_RUNTIME_PATH)) != PREDECESSOR_RUNTIME_SHA256:
        raise ImplementationError(
            "B_VS_D_IMPLEMENTATION_PREDECESSOR_MUTATED",
            "predecessor runtime identity drifted",
            PREDECESSOR_RUNTIME_PATH.as_posix(),
        )
    return {
        "status": "B_VS_D_IMPLEMENTATION_VALID",
        "runtime_payload_sha256": _sha256(runtime_payload),
        "review_sha256": _sha256(review_bytes),
        "record_sha256": _sha256(record_bytes),
        "predecessor_runtime_preserved": True,
        "maximum_model_requests": 6,
        "maximum_model_loads": 6,
        "maximum_worker_starts": 6,
        "model_requests_performed": 0,
        "runtime_execution_authorized": False,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = _parser().parse_args(argv)
        root = cast(Path, arguments.repo_root).resolve()
        result = generate(root) if arguments.command == "generate" else validate(root)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (ImplementationError, ValueError, SyntaxError, json.JSONDecodeError) as error:
        payload = (
            error.envelope()
            if isinstance(error, ImplementationError)
            else {
                "error_code": "B_VS_D_IMPLEMENTATION_VALIDATION_ERROR",
                "safe_message": str(error),
                "path": None,
            }
        )
        print(json.dumps(payload, sort_keys=True), file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

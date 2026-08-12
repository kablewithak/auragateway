from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path("src/auragateway/local_abc/p4_p5_composition_remediation_implementation_v1.py")
DESIGN_PATH = Path("benchmarks/local_abc/auragateway_p4_p5_composition_remediation_design_v1.json")
PREDECESSOR_PATH = Path("src/auragateway/local_abc/p5_p6_transaction_bound_runtime_v1.py")
SUCCESSOR_PATH = Path("src/auragateway/local_abc/p4_p5_composition_remediated_runtime_v1.py")
REVIEW_PATH = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1_review.json"
)
RECORD_PATH = Path(
    "benchmarks/local_abc/auragateway_p4_p5_composition_remediation_implementation_v1.json"
)
REPORT_PATH = Path("docs/reports/AuraGateway_P4_P5_Composition_Remediation_Implementation_V1.md")
RUNBOOK_PATH = Path("docs/runbooks/local_abc_p4_p5_composition_remediation_implementation_v1.md")


def _load_module(repo_root: Path) -> Any:
    spec = importlib.util.spec_from_file_location(
        "p4_p5_composition_remediation_implementation_v1",
        repo_root / MODULE_PATH,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _copy_candidate_repo(source_root: Path, target_root: Path) -> None:
    for relative in (
        MODULE_PATH,
        DESIGN_PATH,
        PREDECESSOR_PATH,
        REPORT_PATH,
        RUNBOOK_PATH,
    ):
        destination = target_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_root / relative, destination)
    test_relative = Path(__file__).resolve().relative_to(source_root)
    test_destination = target_root / test_relative
    test_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(__file__), test_destination)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_generate_and_validate_are_deterministic(tmp_path: Path) -> None:
    root = Path.cwd().resolve()
    candidate = tmp_path / "repo"
    _copy_candidate_repo(root, candidate)
    module = _load_module(candidate)
    first = module.generate(candidate)
    runtime_first = (candidate / SUCCESSOR_PATH).read_bytes()
    review_first = (candidate / REVIEW_PATH).read_bytes()
    record_first = (candidate / RECORD_PATH).read_bytes()
    second = module.generate(candidate)
    assert second == first
    assert (candidate / SUCCESSOR_PATH).read_bytes() == runtime_first
    assert (candidate / REVIEW_PATH).read_bytes() == review_first
    assert (candidate / RECORD_PATH).read_bytes() == record_first
    assert module.validate_generated(candidate) == first


def test_predecessor_remains_byte_identical_after_generation(tmp_path: Path) -> None:
    root = Path.cwd().resolve()
    candidate = tmp_path / "repo"
    _copy_candidate_repo(root, candidate)
    before = _sha(candidate / PREDECESSOR_PATH)
    module = _load_module(candidate)
    module.generate(candidate)
    assert _sha(candidate / PREDECESSOR_PATH) == before
    assert before == module.PREDECESSOR_SHA256


def test_successor_implements_only_frozen_intervention_and_journal() -> None:
    root = Path.cwd().resolve()
    module = _load_module(root)
    predecessor = (root / PREDECESSOR_PATH).read_text(encoding="utf-8")
    successor = (root / SUCCESSOR_PATH).read_text(encoding="utf-8")
    proof = module._validate_static_surface(predecessor, successor)
    assert module.V5_INSTRUCTION not in successor
    successor_tree = module.ast.parse(successor)
    successor_globals = module._global_assignment_map(successor_tree)
    for name in ("SYNTHETIC_CACHE_CONTEXT_A", "SYNTHETIC_CACHE_CONTEXT_B"):
        segment = module._source_segment(successor, successor_globals[name])
        assert segment.count(module.V4_SOURCE_LINES) == 1
    assert "pre_request_token_identity_journal_v1.json" in successor
    assert proof["unchanged_existing_function_count"] > 0
    assert proof["unchanged_existing_class_count"] > 0


def test_journal_is_persisted_before_request_side_effects() -> None:
    root = Path.cwd().resolve()
    successor = (root / SUCCESSOR_PATH).read_text(encoding="utf-8")
    start = successor.index("def run_structured_request(")
    end = successor.index("\ndef gpu_inventory()", start)
    segment = successor[start:end]
    ordered = (
        "token_identity = tokenize_request(",
        'request_ordinal = counters["model_requests"] + 1',
        "payload = request_payload(prefix_variant)",
        "persist_pre_request_token_identity(",
        "before = worker.metric_snapshot()",
        'consume_actions(counters, "model_requests")',
        'f"http://127.0.0.1:{worker.port}/v1/chat/completions"',
        "payload,",
    )
    positions = tuple(segment.index(marker) for marker in ordered)
    assert positions == tuple(sorted(positions))
    assert "request_payload(prefix_variant)," not in segment


def test_request_message_shape_and_decision_semantics_are_preserved() -> None:
    root = Path.cwd().resolve()
    module = _load_module(root)
    predecessor = (root / PREDECESSOR_PATH).read_text(encoding="utf-8")
    successor = (root / SUCCESSOR_PATH).read_text(encoding="utf-8")
    before_tree = module.ast.parse(predecessor)
    after_tree = module.ast.parse(successor)
    before_functions = module._function_map(before_tree)
    after_functions = module._function_map(after_tree)
    for name in (
        "request_messages",
        "request_payload",
        "tokenize_payload",
        "decide_p5",
        "decide_p6",
    ):
        assert module._dump(before_functions[name]) == module._dump(after_functions[name])


def test_record_is_non_authorizing_and_points_to_full_runtime_gate() -> None:
    root = Path.cwd().resolve()
    record = json.loads((root / RECORD_PATH).read_text(encoding="utf-8"))
    assert record["status"] == "IMPLEMENTED_NOT_EXECUTED"
    assert record["remediation_implemented"] is True
    assert record["runtime_execution_authorized"] is False
    assert record["new_execution_authorized"] is False
    assert record["kaggle_execution_performed"] is False
    assert record["model_requests_performed"] == 0
    assert record["next_gate"] == (
        "MERGE_THEN_DESIGN_P4_P5_COMPOSITION_REMEDIATION_EXECUTION_AUTHORIZATION_V1"
    )


def test_predecessor_identity_drift_is_rejected(tmp_path: Path) -> None:
    root = Path.cwd().resolve()
    candidate = tmp_path / "repo"
    _copy_candidate_repo(root, candidate)
    predecessor = candidate / PREDECESSOR_PATH
    predecessor.write_text(
        predecessor.read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )
    module = _load_module(candidate)
    with pytest.raises(module.ImplementationError) as caught:
        module.generate(candidate)
    assert caught.value.error_code == "P4_P5_REMEDIATION_AUTHORITY_DRIFT"


def test_design_identity_drift_is_rejected(tmp_path: Path) -> None:
    root = Path.cwd().resolve()
    candidate = tmp_path / "repo"
    _copy_candidate_repo(root, candidate)
    design = candidate / DESIGN_PATH
    design.write_text(design.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    module = _load_module(candidate)
    with pytest.raises(module.ImplementationError) as caught:
        module.generate(candidate)
    assert caught.value.error_code == "P4_P5_REMEDIATION_AUTHORITY_DRIFT"

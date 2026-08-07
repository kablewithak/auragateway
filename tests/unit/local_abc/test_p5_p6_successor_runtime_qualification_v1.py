"""Tests for P5/P6 Successor Runtime Qualification V1 implementation assets."""

from __future__ import annotations

import json
import os
import shutil
import types
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from auragateway.local_abc import p5_p6_successor_runtime_qualification_v1 as subject


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"
    required = (
        subject.SUCCESSOR_REVIEW_AUTHORITY_PATH,
        subject.PREIMPLEMENTATION_REVIEW_PATH,
        subject.PREIMPLEMENTATION_POLICY_PATH,
        subject.P4_REQUEST_AUTHORITY_PATH,
        subject.V5_REQUEST_AUTHORITY_PATH,
        subject.P4_TEMPLATE_AUTHORITY_PATH,
        subject.V5_TEMPLATE_AUTHORITY_PATH,
        *subject.STATIC_PATHS,
    )
    for relative in required:
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    return repo_root


def _runtime_module(repo_root: Path) -> Any:
    source = subject._template_bytes(repo_root).decode("utf-8")
    module = types.ModuleType("auragateway_p5_p6_successor_runtime_v1")
    exec(
        compile(source, subject.TEMPLATE_PATH.as_posix(), "exec"),
        module.__dict__,
    )
    return module


def test_generate_validate_round_trip(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.record.status == "IMPLEMENTED_NOT_EXECUTED"
    assert generated.record.source_main_commit == subject.SOURCE_MAIN_COMMIT
    assert generated.record.safety.model_requests_performed == 0
    assert generated.record.safety.kaggle_execution_performed is False


def test_candidate_boundary_is_exact() -> None:
    assert len(subject.STATIC_PATHS) == 6
    assert len(subject.GENERATED_PATHS) == 4
    assert len(subject.CANDIDATE_PATHS) == 10
    assert set(subject.CANDIDATE_PATHS) == {
        *subject.STATIC_PATHS,
        *subject.GENERATED_PATHS,
    }


def test_authorities_are_exact_and_current_line_is_not_promoted(
    tmp_path: Path,
) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert len(request.accepted_authorities) == 7
    assert request.runtime_execution_authorized is False
    assert request.measured_abc_execution_authorized is False
    assert request.authorization_issuer_included is False
    assert request.next_gate == (
        "merge_then_design_separate_p5_p6_successor_execution_authorization_v1"
    )


def test_selected_p4_contract_is_frozen_case_a(tmp_path: Path) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request
    contract = request.selected_p4_contract

    assert contract.case_id == "A"
    assert contract.prompt_variant == "V4"
    assert contract.repetition_penalty == 1.1
    assert contract.output_mode == "UNCONSTRAINED"
    assert contract.exact_object_required is True
    assert contract.json_schema_required is False
    assert contract.reselection_permitted is False
    assert contract.p4_canary_reused_as_p5_cold_baseline is True


def test_case_a_payload_composes_v4_output_contract_with_v5_cache_context() -> None:
    payload = subject._case_a_payload()
    messages = payload["messages"]

    assert isinstance(messages, list)
    assert len(messages) == 4
    assert messages[0] == {"role": "system", "content": subject.V4_PROMPT}
    assert messages[1] == {
        "role": "user",
        "content": subject.V5_SYNTHETIC_CACHE_CONTEXT,
    }
    assert messages[2] == {
        "role": "assistant",
        "content": subject.SYNTHETIC_ASSISTANT_ACK,
    }
    assert messages[3] == {"role": "user", "content": '{"probe":"cold","value":1}'}
    assert payload["repetition_penalty"] == 1.1
    assert payload["max_tokens"] == 32
    assert "response_format" not in payload


def test_request_identity_freezes_shared_cache_prefix() -> None:
    identities = subject._request_identities()

    assert identities.p4_canary_logical_sha256 == identities.p5_cold_logical_sha256
    assert identities.p5_cold_reuses_p4_canary is True
    assert identities.all_runtime_payloads_identical is True
    assert len(identities.payload_sha256) == 64
    assert len(identities.shared_messages_sha256) == 64
    assert len(identities.eligible_prefix_messages_sha256) == 64
    assert identities.shared_messages_sha256 != identities.eligible_prefix_messages_sha256


def test_execution_budget_is_exact_five_request_ceiling(tmp_path: Path) -> None:
    request = subject.build_generated(_fixture_repo(tmp_path)).request

    assert tuple(item.stage for item in request.stage_budgets) == (
        "P3_CANARY",
        "P4_CANARY",
        "P5",
        "P6",
    )
    assert tuple(item.additional_model_requests for item in request.stage_budgets) == (
        0,
        1,
        2,
        2,
    )
    assert sum(item.additional_model_requests for item in request.stage_budgets) == 5
    assert request.execution_budget.maximum_model_loads == 3
    assert request.execution_budget.maximum_worker_starts == 3
    assert request.execution_budget.maximum_model_requests == 5
    assert request.execution_budget.hidden_retries_permitted == 0
    assert request.execution_budget.benchmark_trajectory_requests_permitted == 0
    assert request.execution_budget.network_requests_permitted == 0
    assert request.execution_budget.external_spend == 0


def test_runtime_environment_filters_stubs_and_removes_ld_preload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    target = tmp_path / "target"
    target_site = target / "site-packages"
    for relative in ("nvidia/cusparse/lib", "nvidia/nvjitlink/lib"):
        (target_site / relative).mkdir(parents=True)
    driver = tmp_path / "driver"
    driver.mkdir()

    monkeypatch.setattr(runtime, "TARGET_ROOT", target)
    monkeypatch.setattr(runtime, "TARGET_SITE", target_site)
    monkeypatch.setattr(runtime, "REAL_DRIVER_DIRECTORY", str(driver))
    monkeypatch.setenv(
        "LD_LIBRARY_PATH",
        os.pathsep.join(
            (
                "/usr/local/cuda/lib64/stubs",
                "/usr/local/cuda/compat",
                "/ambient/cuda",
            )
        ),
    )
    monkeypatch.setenv("LD_PRELOAD", "/ambient/libbad.so")

    environment = runtime.process_tree_environment(0, tmp_path / "model-home")
    paths = environment["LD_LIBRARY_PATH"].split(os.pathsep)

    assert "/usr/local/cuda/lib64/stubs" not in paths
    assert "/usr/local/cuda/compat" not in paths
    assert "/ambient/cuda" in paths
    assert "LD_PRELOAD" not in environment
    assert environment["PYTHONPATH"] == str(target_site)
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["LIBRARY_PATH"] == str(driver)
    assert environment["CUDA_VISIBLE_DEVICES"] == "0"
    assert environment["VLLM_ATTENTION_BACKEND"] == "TRITON_ATTN"


def test_metric_parser_fails_closed_on_multiple_relevant_series(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    payload = "\n".join(
        (
            'vllm:request_prompt_tokens_sum{model_name="a"} 10',
            'vllm:request_prompt_tokens_sum{model_name="b"} 20',
        )
    )

    with pytest.raises(RuntimeError, match="ambiguous relevant metric series"):
        runtime.parse_metrics(payload)


def test_native_origin_policy_allows_ambient_non_stub_but_requires_target_pair(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    target_root = tmp_path / "target"
    target_root.mkdir()
    monkeypatch.setattr(runtime, "TARGET_ROOT", target_root)

    target_cusparse = target_root / "nvidia/cusparse/lib/libcusparse.so.12"
    target_nvjitlink = target_root / "nvidia/nvjitlink/lib/libnvJitLink.so.12"
    ambient_cudart = "/usr/lib/x86_64-linux-gnu/libcudart.so.12"

    assert runtime.classify_native_origin(str(target_cusparse)) == "TARGET_RUNTIME"
    assert runtime.classify_native_origin(str(target_nvjitlink)) == "TARGET_RUNTIME"
    assert runtime.classify_native_origin(ambient_cudart) == "HOST_OR_AMBIENT_LIBRARY"

    worker = SimpleNamespace(
        process=SimpleNamespace(pid=100),
        worker_id="worker_1",
        instance_id="worker-1-test",
    )
    monkeypatch.setattr(runtime, "process_parent_map", lambda: {})
    monkeypatch.setattr(runtime, "descendants", lambda pid, parents: {pid})
    monkeypatch.setattr(
        runtime,
        "native_paths_for_process",
        lambda pid: {
            str(target_cusparse),
            str(target_nvjitlink),
            ambient_cudart,
        },
    )

    report = runtime.validate_native_origin_closure(worker)

    assert report["status"] == "PASSED"
    assert report["ambient_non_stub_origins_permitted"] is True
    assert report["required_target_origins"]["libcusparse"]["all_from_target"] is True
    assert report["required_target_origins"]["libnvjitlink"]["all_from_target"] is True


def test_p6_response_envelope_does_not_use_model_semantics_as_route_proof(
    tmp_path: Path,
) -> None:
    runtime = _runtime_module(_fixture_repo(tmp_path))
    envelope = runtime.validate_response_envelope(
        {
            "model": runtime.SERVED_MODEL_NAME,
            "usage": {"prompt_tokens": 700, "completion_tokens": 3},
            "choices": [
                {
                    "message": {"content": "unexpected-but-valid-envelope"},
                    "finish_reason": "stop",
                }
            ],
        }
    )

    assert envelope["response_envelope_valid"] is True
    assert envelope["model_identity_valid"] is True


def test_runtime_source_preserves_p5_and_p6_acceptance_boundaries(
    tmp_path: Path,
) -> None:
    source = subject._template_bytes(_fixture_repo(tmp_path)).decode("utf-8")

    assert 'float(cold_delta["cached_prefix_tokens"]) != 0' in source
    assert 'float(warm_delta["cached_prefix_tokens"]) <= 0' in source
    assert 'float(post_delta["cached_prefix_tokens"]) != 0' in source
    assert '"namespace_only_reset_used": False' in source
    assert "worker_1 route changed worker_2 metrics" in source
    assert "worker_2 route changed worker_1 metrics" in source
    assert '"model_semantics_used_as_route_proof": False' in source
    assert '"maximum_model_requests"' not in source
    assert "P5/P6 successor output or scratch path already exists" in source
    assert "-v5" not in source.lower()


def test_notebook_is_single_cell_unexecuted_and_hash_bound(tmp_path: Path) -> None:
    generated = subject.build_generated(_fixture_repo(tmp_path))
    notebook = json.loads(generated.notebook_bytes)
    cells = notebook["cells"]

    assert len(cells) == 1
    assert cells[0]["cell_type"] == "code"
    assert cells[0]["execution_count"] is None
    assert cells[0]["outputs"] == []
    assert cells[0]["id"] == "91ffcc0c52204f2590a8cbeec026a339"
    assert not cells[0]["source"][-1].endswith("\n")

    wrapper = "".join(cells[0]["source"])
    assert generated.runtime_script_sha256 in wrapper
    assert "runtime script identity mismatch" in wrapper
    assert (
        '_AG_RUNTIME_SOURCE = _ag_base64.b64decode("".join(_AG_RUNTIME_B64)).decode("utf-8")'
    ) in wrapper
    assert (
        "_AG_OBSERVED_RUNTIME_SHA256 = "
        '_ag_hashlib.sha256(_AG_RUNTIME_SOURCE.encode("utf-8")).hexdigest()'
    ) in wrapper
    assert max(len(line) for line in wrapper.splitlines()) <= 100


def test_generation_is_deterministic(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)

    first = subject.generate(repo_root)
    first_bytes = {path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS}
    second = subject.generate(repo_root)

    assert first == second
    assert {
        path: (repo_root / path).read_bytes() for path in subject.GENERATED_PATHS
    } == first_bytes


def test_generated_artifact_drift_fails_closed(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    subject.generate(repo_root)
    path = repo_root / subject.REQUEST_PATH
    path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        subject.SuccessorImplementationError,
        match="generated successor artifact differs from fresh rebuild",
    ):
        subject.validate(repo_root)


def test_authorization_artifact_presence_fails_closed(tmp_path: Path) -> None:
    repo_root = _fixture_repo(tmp_path)
    authorization = repo_root / subject.OPERATIONAL_AUTHORIZATION_PATH
    authorization.parent.mkdir(parents=True, exist_ok=True)
    authorization.write_text("{}\n", encoding="utf-8")

    with pytest.raises(
        subject.SuccessorImplementationError,
        match="operational authorization must remain absent",
    ):
        subject.build_generated(repo_root)

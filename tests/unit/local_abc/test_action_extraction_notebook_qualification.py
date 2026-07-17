"""Regression tests for the qualified action-extraction requalification notebook v2."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from pydantic import ValidationError

from auragateway.local_abc.action_extraction_notebook_qualification import (
    ActionExtractionNotebookQualificationPackageV2,
    ActionExtractionRequalificationNotebookBindingV2,
    canonical_notebook_binding_file_sha256,
    load_action_extraction_notebook_qualification_package_v2,
)

ROOT = Path(__file__).resolve().parents[3]
BENCHMARK_ROOT = ROOT / "benchmarks" / "local_abc"
NOTEBOOK_PATH = (
    ROOT / "notebooks/kaggle/"
    "auragateway_v2_reconcile_balance_action_extraction_requalification_v2.ipynb"
)
BINDING_PATH = (
    BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_notebook_binding_v2.json"
)

EXPECTED_NOTEBOOK_SHA256 = "e1e38afa6f269c9aa529bdafa1ce4ca8c4bba4a53d7b69e93bfaf0e3549a97e9"
EXPECTED_BINDING_SHA256 = "476d3be54fc34cafacba4bcdef07eaa1213a426df0496e4908bc8078b7edac88"
EXPECTED_ACTIVATION_MERGE_COMMIT = "639e21a63eb8a37d0221c2630b756203d1270f62"
EXPECTED_AUTHORIZATION_SHA256 = "a2a35e3fb566ed697089dd41c962c7d932490eaeda3ab12f1f3955c285225899"
EXPECTED_ACTIVATION_MANIFEST_SHA256 = (
    "42ce858a657afe0fd6d4eb7a5e0846fedf1b9c41ab883826acf08712a94b0526"
)

EXPECTED_CASE_IDS = (
    "historical-turn-one",
    "turn-two-history-distractors",
    "reordered-narrative",
    "zero-boundary",
    "repeated-operands",
    "metadata-number-distractors",
    "formatted-currency-values",
    "key-value-layout",
    "same-answer-different-operands",
    "maximum-opening-boundary",
    "credits-first-description",
    "turn-two-feedback-separation",
    "formatted-currency-multi-group",
    "formatted-currency-spaced-symbol",
    "key-value-credits-first-layout",
    "key-value-mixed-delimiters",
)


def load_package() -> ActionExtractionNotebookQualificationPackageV2:
    return load_action_extraction_notebook_qualification_package_v2(
        parent_manifest_path=(BENCHMARK_ROOT / "reconcile_balance_extraction_eval_cases_v1.json"),
        parent_plan_path=(BENCHMARK_ROOT / "reconcile_balance_extraction_eval_plan_v1.json"),
        remediation_manifest_path=(
            BENCHMARK_ROOT / "reconcile_balance_extraction_remediation_cases_v2.json"
        ),
        remediation_plan_path=(
            BENCHMARK_ROOT / "reconcile_balance_extraction_remediation_plan_v2.json"
        ),
        review_path=(BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_review_v2.json"),
        dry_run_path=(
            BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_dry_run_v2.json"
        ),
        review_manifest_path=(
            BENCHMARK_ROOT / "reconcile_balance_extraction_authorization_review_manifest_v2.json"
        ),
        authorization_path=(
            BENCHMARK_ROOT / "reconcile_balance_extraction_requalification_authorization_v2.json"
        ),
        activation_manifest_path=(
            BENCHMARK_ROOT
            / "reconcile_balance_extraction_authorization_activation_manifest_v2.json"
        ),
        notebook_path=NOTEBOOK_PATH,
        notebook_binding_path=BINDING_PATH,
    )


def load_notebook() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8")))


def code_sources() -> tuple[str, ...]:
    sources: list[str] = []
    for cell in cast(list[dict[str, Any]], load_notebook()["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = cell["source"]
        sources.append("".join(source) if isinstance(source, list) else cast(str, source))
    return tuple(sources)


def code_cell(header: str) -> str:
    matches = tuple(source for source in code_sources() if source.startswith(header))
    assert len(matches) == 1
    return matches[0]


def binding_payload() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(BINDING_PATH.read_text(encoding="utf-8")))


def test_qualification_package_loads() -> None:
    package = load_package()
    assert package.binding.notebook_sha256 == EXPECTED_NOTEBOOK_SHA256
    assert package.binding.fingerprint() == EXPECTED_BINDING_SHA256


def test_notebook_has_no_saved_execution_state_and_compiles() -> None:
    facts = load_package().notebook
    assert facts.notebook_has_saved_execution_state is False
    assert facts.notebook_cells_compile is True
    assert facts.notebook_code_cell_count == 12


def test_binding_is_canonical_single_line_json() -> None:
    text = BINDING_PATH.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert canonical_notebook_binding_file_sha256(BINDING_PATH) == (EXPECTED_BINDING_SHA256)


def test_binding_preserves_fresh_authorization_lineage() -> None:
    binding = load_package().binding
    assert binding.activation_merge_commit == EXPECTED_ACTIVATION_MERGE_COMMIT
    assert binding.authorization_sha256 == EXPECTED_AUTHORIZATION_SHA256
    assert binding.activation_manifest_sha256 == EXPECTED_ACTIVATION_MANIFEST_SHA256
    assert binding.authorization_consumed is False


def test_binding_uses_exact_pr88_blob_identities() -> None:
    bindings = load_package().binding.source_bindings
    assert tuple(item.git_blob_sha for item in bindings) == (
        "aa1afdf0acc52bd5bf2a3e0d7fb9c6b71f5fd342",
        "3f84ebc86450dc8e2e70c2d457593bf9b10136bf",
        "142133a745dcc69d64ecae81811c8d2cb377b909",
    )


def test_complete_sixteen_case_boundary_is_frozen() -> None:
    package = load_package()
    authorization = package.activation_package.authorization
    assert authorization.selected_case_ids == EXPECTED_CASE_IDS
    assert package.binding.case_count == 16
    assert package.binding.request_count == 16
    assert package.binding.request_attempts_per_case == 1
    assert package.binding.complete_suite_required is True


def test_notebook_loads_activation_and_v2_remediation() -> None:
    source = code_cell("# Cell 04 — Active Authorization and Fixed-Scope Preflight")
    assert "load_action_extraction_authorization_activation_package_v2" in source
    assert "build_reconcile_balance_extraction_response_format_v2" in source
    assert "render_reconcile_balance_extraction_prompt_v2" in source
    assert "authorization.authorization_consumed" in source


def test_notebook_builds_hash_only_sixteen_request_schedule() -> None:
    source = code_cell("# Cell 08 — Notebook Binding and Hash-Only Schedule Preflight")
    assert "build_remediated_extraction_prompt_identity" in source
    assert "normalized_prompt_sha256" in source
    assert "currency_integer_normalization_count" in source
    assert "if len(schedule_records) != 16" in source
    assert '"messages": [{"role": "user", "content": transient_prompt}]' in source


def test_notebook_runs_one_attempt_per_case_without_retry() -> None:
    source = code_cell("# Cell 10 — Sixteen-Request Requalification and Repository Scoring")
    assert "for sequence, case in enumerate(CASES, start=1)" in source
    assert "post_json_once(payload=request_body)" in source
    assert "if len(scores) != 16" in source
    assert "retry" not in source.lower()
    assert "repair" not in source.lower()


def test_notebook_retains_semantic_failures_and_aborts_infrastructure_failures() -> None:
    source = code_cell("# Cell 10 — Sixteen-Request Requalification and Repository Scoring")
    assert "scores.append(score)" in source
    assert "infrastructure_failure = safe_failure_detail(error)" in source
    assert "WorkerCleanupFailure" in source
    assert "ACTION_EXTRACTION_REQUALIFICATION_FAILED_DIAGNOSTIC" in source


def test_notebook_does_not_retain_or_print_raw_output() -> None:
    text = "\n".join(code_sources())
    assert "print(output_text)" not in text
    assert '"output_text": output_text' not in text
    assert "'output_text': output_text" not in text
    assert '"raw_output_retained": False' in text


def test_notebook_contains_no_cache_experiment_logic() -> None:
    text = "\n".join(code_sources())
    assert "--enable-prefix-caching" not in text
    assert "prompt_tokens_cached_total" not in text
    assert '"cache_measurement_in_scope": False' in text


def test_notebook_uses_isolated_runtime_and_binary_import_probe() -> None:
    runtime_setup = code_cell("# Cell 05 — Isolated Authorized vLLM Runtime Preparation")
    runtime_probe = code_cell("# Cell 06 — Isolated GPU, PyTorch, CUDA, and vLLM ABI Preflight")
    assert '"--without-pip"' in runtime_setup
    assert '"torch==2.11.0"' in runtime_setup
    assert "include-system-site-packages = false" in runtime_setup
    assert "import vllm" in runtime_probe
    assert "RUNTIME_PROBE_SENTINEL" in runtime_probe
    assert "binary_import_probe" in runtime_probe


def test_worker_uses_qualified_runtime_python() -> None:
    source = code_cell("# Cell 09 — Worker Lifecycle and One-Shot HTTP Transport")
    assert "str(RUNTIME_PYTHON)" in source
    assert '"vllm.entrypoints.openai.api_server"' in source
    assert 'sys.executable,\n        "-m",\n        "vllm"' not in source


def test_binding_blocks_scope_expansion() -> None:
    binding = load_package().binding
    assert binding.failed_case_only_execution_permitted is False
    assert binding.hidden_retry_count == 0
    assert binding.repair_attempt_count == 0
    assert binding.replacement_request_count == 0
    assert binding.cache_measurement_in_scope is False
    assert binding.full_measured_rerun_authorized is False


def test_binding_preserves_privacy_and_zero_spend() -> None:
    binding = load_package().binding
    assert binding.raw_prompt_retention_permitted is False
    assert binding.raw_output_retention_permitted is False
    assert binding.raw_action_retention_permitted is False
    assert binding.token_id_retention_permitted is False
    assert binding.external_spend == 0
    assert binding.customer_data_used is False


def test_mutated_notebook_hash_fails_closed() -> None:
    payload = binding_payload()
    payload["notebook_sha256"] = "0" * 64
    binding = ActionExtractionRequalificationNotebookBindingV2.model_validate(payload)
    package = load_package()
    with pytest.raises(ValidationError, match="exact notebook bytes"):
        ActionExtractionNotebookQualificationPackageV2(
            activation_package=package.activation_package,
            binding=binding,
            notebook=package.notebook,
        )


def test_consumed_authorization_fails_closed() -> None:
    package = load_package()
    authorization_payload = package.activation_package.authorization.model_dump(mode="json")
    authorization_payload["authorization_consumed"] = True
    with pytest.raises(ValidationError):
        type(package.activation_package.authorization).model_validate(authorization_payload)


def test_next_gate_is_execution_package_not_full_benchmark() -> None:
    binding = load_package().binding
    assert binding.notebook_qualified_for_bounded_execution is True
    assert binding.execution_command_available is False
    assert binding.next_gate == "bounded_action_extraction_v2_kaggle_execution_package"

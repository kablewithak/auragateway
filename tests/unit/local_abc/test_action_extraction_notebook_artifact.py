from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, cast

ROOT = Path(__file__).resolve().parents[3]
NOTEBOOK_PATH = (
    ROOT / "notebooks/kaggle/auragateway_v2_reconcile_balance_action_extraction_canary_v1.ipynb"
)
BINDING_PATH = (
    ROOT / "benchmarks/local_abc/reconcile_balance_extraction_canary_notebook_binding_v1.json"
)
EXPECTED_AUTHORIZATION_FINGERPRINT = (
    "9efe45c37b3223b6f01bd55e6471a1c487b5115ba6260b77bd3a6ff2219933a9"
)
EXPECTED_AUTHORIZATION_MERGE_COMMIT = "0619867a7acbee5e4c5b639963cf1046cbf36809"
EXPECTED_IMPORT_MODULES = (
    "auragateway",
    "auragateway.local_abc.action_extraction_authorization",
    "auragateway.local_abc.action_extraction_eval",
    "auragateway.local_abc.arithmetic_action",
)


def load_notebook() -> dict[str, Any]:
    payload = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def load_binding() -> dict[str, Any]:
    payload = json.loads(BINDING_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def code_cell_source(cell: dict[str, Any]) -> str:
    source = cell["source"]
    if isinstance(source, list):
        assert all(isinstance(line, str) for line in source)
        return "".join(source)
    assert isinstance(source, str)
    return source


def notebook_code_sources(
    notebook: dict[str, Any],
) -> tuple[str, ...]:
    return tuple(
        code_cell_source(cell) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )


def notebook_code_cell(
    notebook: dict[str, Any],
    header: str,
) -> str:
    matches = tuple(
        source for source in notebook_code_sources(notebook) if source.startswith(header)
    )
    assert len(matches) == 1
    return matches[0]


def test_notebook_exact_hash_matches_binding() -> None:
    binding = load_binding()

    assert hashlib.sha256(NOTEBOOK_PATH.read_bytes()).hexdigest() == binding["notebook_sha256"]


def test_notebook_code_source_hash_matches_binding() -> None:
    notebook = load_notebook()
    binding = load_binding()
    source_text = "\n\n# --- CELL BOUNDARY ---\n\n".join(notebook_code_sources(notebook))

    assert (
        hashlib.sha256(source_text.encode("utf-8")).hexdigest()
        == binding["notebook_code_source_sha256"]
    )
    assert len(notebook_code_sources(notebook)) == binding["notebook_code_cell_count"]


def test_notebook_has_no_saved_execution_state() -> None:
    notebook = load_notebook()

    for cell in notebook["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is None
            assert cell["outputs"] == []


def test_notebook_code_cells_compile() -> None:
    notebook = load_notebook()

    for index, source in enumerate(notebook_code_sources(notebook)):
        compile(
            source,
            f"notebook-cell-{index:02d}",
            "exec",
        )


def test_notebook_binding_preserves_authorized_boundary() -> None:
    binding = load_binding()

    assert binding["schema_version"] == "1.2.0"
    assert binding["authorization_fingerprint"] == (EXPECTED_AUTHORIZATION_FINGERPRINT)
    assert binding["authorization_merge_commit"] == (EXPECTED_AUTHORIZATION_MERGE_COMMIT)
    assert binding["case_count"] == 12
    assert binding["request_count"] == 12
    assert binding["request_attempts_per_case"] == 1
    assert binding["worker_id"] == "worker_1"
    assert binding["cache_measurement_in_scope"] is False
    assert binding["cache_claims_permitted"] is False
    assert binding["full_measured_rerun_authorized"] is False


def test_repository_import_gate_remains_required() -> None:
    binding = load_binding()

    assert binding["repository_import_qualification_required"] is True
    assert binding["repository_source_path_policy"] == ("exact_checkout_src_prepend_v1")
    assert binding["editable_install_required"] is False
    assert tuple(binding["required_import_modules"]) == (EXPECTED_IMPORT_MODULES)


def test_binding_requires_isolated_runtime() -> None:
    binding = load_binding()

    assert binding["runtime_environment_isolation_required"] is True
    assert binding["runtime_environment_policy"] == ("isolated_venv_exact_torch_cu129_v1")
    assert binding["runtime_system_site_packages_inherited"] is False
    assert binding["runtime_exact_torch_version"] == ("2.11.0+cu129")
    assert binding["runtime_cuda_version"] == "12.9"
    assert binding["runtime_exact_torchvision_version"] == ("0.26.0+cu129")
    assert binding["runtime_exact_torchaudio_version"] == ("2.11.0+cu129")
    assert binding["vllm_binary_import_probe_required"] is True
    assert binding["vllm_worker_python_policy"] == ("qualified_isolated_runtime_python_v1")


def test_binding_records_predecessor_runtime_failure() -> None:
    binding = load_binding()

    assert (
        binding["pre_execution_runtime_failure_classification"]
        == "PRE_EXECUTION_VLLM_ABI_RUNTIME_DRIFT"
    )
    assert binding["predecessor_runtime_base_torch_version"] == "2.10.0+cu128"
    assert binding["predecessor_runtime_base_cuda_version"] == "12.8"
    assert binding["predecessor_runtime_wheel_torch_requirement"] == "torch==2.11.0"
    assert binding["predecessor_runtime_failure_sent_model_requests"] is False
    assert binding["predecessor_runtime_failure_consumed_authorization"] is False


def test_runtime_preparation_uses_clean_venv() -> None:
    notebook = load_notebook()
    source = notebook_code_cell(
        notebook,
        "# Cell 05 — Isolated Authorized vLLM Runtime Preparation",
    )

    assert '"venv"' in source
    assert '"--index-url"' in source
    assert "PYTORCH_CU129_INDEX_URL" in source
    assert '"torch==2.11.0"' in source
    assert '"torchvision==0.26.0"' in source
    assert '"torchaudio==2.11.0"' in source
    assert '"pip",\n        "check"' in source
    assert "include-system-site-packages = false" in source
    assert '"--no-deps"' not in source
    assert '"--system-site-packages"' not in source


def test_runtime_gate_requires_binary_import_probe() -> None:
    notebook = load_notebook()
    source = notebook_code_cell(
        notebook,
        "# Cell 06 — Isolated GPU, PyTorch, CUDA, and vLLM ABI Preflight",
    )

    assert "import torch" in source
    assert "import vllm" in source
    assert "RUNTIME_PROBE_SENTINEL" in source
    assert "binary_import_probe" in source
    assert "torch_file.is_relative_to(runtime_root)" in source
    assert "vllm_file.is_relative_to(runtime_root)" in source
    assert '"status": "RUNTIME_PREFLIGHT_QUALIFIED"' in source


def test_current_kernel_does_not_import_vllm() -> None:
    notebook = load_notebook()
    source = notebook_code_cell(
        notebook,
        "# Cell 06 — Isolated GPU, PyTorch, CUDA, and vLLM ABI Preflight",
    )

    assert source.count("import vllm") == 1
    assert 'str(RUNTIME_PYTHON),\n        "-c"' in source
    assert "subprocess.run(" in source


def test_worker_uses_qualified_runtime_python() -> None:
    notebook = load_notebook()
    source = notebook_code_cell(
        notebook,
        "# Cell 09 — Worker Lifecycle and One-Shot HTTP Transport",
    )

    assert "if not RUNTIME_PYTHON.is_file()" in source
    assert "str(RUNTIME_PYTHON)" in source
    assert '"vllm.entrypoints.openai.api_server"' in source
    assert 'sys.executable,\n        "-m",\n        "vllm' not in source


def test_notebook_prohibits_retry_and_raw_retention() -> None:
    binding = load_binding()

    assert binding["hidden_retry_count"] == 0
    assert binding["repair_attempt_count"] == 0
    assert binding["replacement_request_count"] == 0
    assert binding["raw_prompt_retention_permitted"] is False
    assert binding["raw_output_retention_permitted"] is False
    assert binding["raw_action_retention_permitted"] is False
    assert binding["token_id_retention_permitted"] is False


def test_notebook_contains_no_cache_experiment_logic() -> None:
    notebook_text = NOTEBOOK_PATH.read_text(encoding="utf-8")

    assert "--enable-prefix-caching" not in notebook_text
    assert "/metrics" not in notebook_text
    assert "prompt_tokens_cached_total" not in notebook_text
    assert "cache_measurement_in_scope" in notebook_text


def test_notebook_does_not_print_transient_model_output() -> None:
    notebook_text = NOTEBOOK_PATH.read_text(encoding="utf-8")

    assert "print(output_text)" not in notebook_text
    assert '"output_text": output_text' not in notebook_text
    assert "'output_text': output_text" not in notebook_text


def test_binding_json_is_canonical_single_line() -> None:
    text = BINDING_PATH.read_text(encoding="utf-8")

    assert text.endswith("\n")
    assert text.count("\n") == 1
    assert json.dumps(
        json.loads(text),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ) == text.rstrip("\n")

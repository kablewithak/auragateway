from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = (
    ROOT / "src/auragateway/local_abc/measured_abc_variance_pilot_transaction_bound_runtime_v1.py"
)


def _source() -> str:
    return SOURCE.read_text(encoding="utf-8")


def test_runtime_payload_is_standalone_stdlib_only() -> None:
    tree = ast.parse(_source())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(item.name.split(".")[0] for item in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {
        "__future__",
        "hashlib",
        "json",
        "math",
        "os",
        "pathlib",
        "re",
        "time",
        "typing",
        "zipfile",
    }


def test_runtime_uses_per_trajectory_vllm_cache_salt() -> None:
    source = _source()
    assert '"cache_salt": cache_salt' in source
    assert 'cache_isolation_mechanism": "VLLM_CACHE_SALT"' in source
    assert "sha256_text(namespace)" in source


def test_runtime_blocks_pilot_until_timing_probe_passes() -> None:
    source = _source()
    preflight = source.index("_validate_preflight_pair")
    trajectory_loop = source.index("for expected_index, raw in enumerate(trajectories)")
    assert preflight < trajectory_loop
    assert "PILOT_TIMING_TELEMETRY_UNAVAILABLE" in source


def test_runtime_reuses_accepted_r2_install_and_worker_mechanisms() -> None:
    source = _source()
    assert 'R2["install_runtime"]' in source
    assert 'R2["validate_target_runtime"]' in source
    assert 'R2["prepare_model_home"]' in source
    assert 'R2["Worker"]' in source
    assert "stop_and_report" in source


def test_runtime_public_outputs_exclude_raw_content() -> None:
    source = _source()
    assert '"raw_prompt_retained": False' in source
    assert '"raw_output_retained": False' in source
    assert '"raw_retrieved_document_text_retained": False' in source
    assert '"external_network_requests": 0' in source


def test_runtime_requires_live_cache_salt_isolation_preflight() -> None:
    source = _source()
    assert "_cache_salt_isolation_preflight" in source
    assert "PILOT_CACHE_SALT_REUSE_NOT_OBSERVED" in source
    assert "PILOT_CACHE_SALT_ISOLATION_NOT_OBSERVED" in source
    assert '"cache_salt_isolation_qualified": True' in source

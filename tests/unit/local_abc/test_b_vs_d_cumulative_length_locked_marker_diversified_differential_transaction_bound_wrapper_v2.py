from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]

V1_TEMPLATE = REPO_ROOT / (
    "src/auragateway/local_abc/templates/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_"
    "transaction_bound_wrapper_v1.py.tmpl"
)

V2_TEMPLATE = REPO_ROOT / (
    "src/auragateway/local_abc/templates/"
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_"
    "transaction_bound_wrapper_v2.py.tmpl"
)

V1_TEMPLATE_SHA256 = "b30c890e359c0745d5e759758065d0a8a4d6619060a658c6a04f71ca76642432"

PRIMARY_FAILURE_PATH = Path(
    "b_vs_d_cumulative_length_locked_marker_diversified_differential_primary_failure_v1.json"
)


def _load_execute(
    template_path: Path,
    runtime_source: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Callable[[], None]:
    source = template_path.read_text(encoding="utf-8")
    namespace: dict[str, object] = {
        "__name__": "auragateway_wrapper_regression_test",
        "__file__": str(template_path),
    }

    exec(
        compile(source, str(template_path), "exec"),
        namespace,
        namespace,
    )

    namespace["admit"] = lambda: {"status": "TEST_ADMISSION"}
    namespace["_RUNTIME_PAYLOAD_B64"] = base64.b64encode(runtime_source.encode("utf-8")).decode(
        "ascii"
    )

    monkeypatch.chdir(tmp_path)

    execute = namespace.get("execute_bound_payload")
    if not callable(execute):
        raise AssertionError("wrapper execute_bound_payload is unavailable")

    return cast(Callable[[], None], execute)


def _read_primary_failure(tmp_path: Path) -> dict[str, object]:
    raw: object = json.loads((tmp_path / PRIMARY_FAILURE_PATH).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AssertionError("primary failure artifact must be one JSON object")
    return raw


def test_v1_historical_generator_identity_is_preserved() -> None:
    assert hashlib.sha256(V1_TEMPLATE.read_bytes()).hexdigest() == V1_TEMPLATE_SHA256


def test_v1_baseline_reproduces_zero_exit_false_positive(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute = _load_execute(
        V1_TEMPLATE,
        "raise SystemExit(0)\n",
        monkeypatch,
        tmp_path,
    )

    with pytest.raises(SystemExit) as captured:
        execute()

    assert captured.value.code == 0

    failure = _read_primary_failure(tmp_path)
    assert failure["status"] == "PRIMARY_FAILURE_CAPTURED"
    assert failure["exception_type"] == "SystemExit"
    assert failure["safe_message"] == "0"


def test_v2_zero_exit_is_normal_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute = _load_execute(
        V2_TEMPLATE,
        "raise SystemExit(0)\n",
        monkeypatch,
        tmp_path,
    )

    execute()

    assert not (tmp_path / PRIMARY_FAILURE_PATH).exists()


def test_v2_none_exit_is_normal_completion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute = _load_execute(
        V2_TEMPLATE,
        "raise SystemExit()\n",
        monkeypatch,
        tmp_path,
    )

    execute()

    assert not (tmp_path / PRIMARY_FAILURE_PATH).exists()


def test_v2_nonzero_system_exit_remains_primary_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute = _load_execute(
        V2_TEMPLATE,
        "raise SystemExit(3)\n",
        monkeypatch,
        tmp_path,
    )

    with pytest.raises(SystemExit) as captured:
        execute()

    assert captured.value.code == 3

    failure = _read_primary_failure(tmp_path)
    assert failure["status"] == "PRIMARY_FAILURE_CAPTURED"
    assert failure["exception_type"] == "SystemExit"
    assert failure["safe_message"] == "3"


def test_v2_runtime_error_remains_primary_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    execute = _load_execute(
        V2_TEMPLATE,
        "raise RuntimeError('synthetic-wrapper-failure')\n",
        monkeypatch,
        tmp_path,
    )

    with pytest.raises(RuntimeError, match="synthetic-wrapper-failure"):
        execute()

    failure = _read_primary_failure(tmp_path)
    assert failure["status"] == "PRIMARY_FAILURE_CAPTURED"
    assert failure["exception_type"] == "RuntimeError"
    assert failure["safe_message"] == "synthetic-wrapper-failure"

from __future__ import annotations

import os
import stat
import sys
import types
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest

from auragateway.local_abc import transaction_bound_execution_authorization_v1 as authorization
from auragateway.local_abc import transaction_bound_p5_p6_runtime_integration_v1 as subject

ROOT = Path(__file__).resolve().parents[3]
RUNTIME_PATH = ROOT / subject.RUNTIME_PAYLOAD_PATH


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="real repository authorities are unavailable in synthetic fixture",
)
def test_current_repository_runtime_integration_validates() -> None:
    result = subject.validate(ROOT)
    assert result["status"] == "TRANSACTION_BOUND_P5_P6_RUNTIME_INTEGRATION_VALID"
    assert result["authorization_specific_kaggle_inputs"] == 0
    assert result["symlink_regression_covered"] is True
    assert result["primary_failure_preserved_separately"] is True
    assert result["current_runtime_p5_p6_requalified"] is False
    assert result["live_authorization_issued"] is False
    assert result["gpu_execution_authorized"] is False


def test_runtime_payload_has_no_authorization_transport() -> None:
    source = RUNTIME_PATH.read_text(encoding="utf-8")
    forbidden = (
        "ag-p5-p6-auth-control-v1",
        "ag_p5_p6_auth_control_v1",
        "execution_authorization_v1.json",
        "AUTHORIZATION_CONTROL_",
        "resolve_authorization_control_output",
        "require_execution_authorization",
    )
    for token in forbidden:
        assert token not in source
    assert "require_transaction_bound_context()" in source


def test_six_request_contract_is_preserved() -> None:
    source = RUNTIME_PATH.read_text(encoding="utf-8")
    for role in subject.REQUEST_ROLES:
        assert role in source


def test_successful_bounded_process_semantics_are_zero_exit() -> None:
    source = RUNTIME_PATH.read_text(encoding="utf-8")
    assert 'process_outcome = "ZERO_EXIT"' in source
    assert 'if process_outcome == "ZERO_EXIT"' in source
    assert 'process_outcome = "PASSED"' not in source


class _FakeMember:
    def __init__(
        self,
        *,
        symlink: bool = False,
        directory: bool = False,
        size: int = 7,
    ) -> None:
        self._symlink = symlink
        self._directory = directory
        self._size = size

    def is_symlink(self) -> bool:
        return self._symlink

    def is_dir(self) -> bool:
        return self._directory

    def stat(self) -> SimpleNamespace:
        return SimpleNamespace(
            st_mode=stat.S_IFREG | 0o644,
            st_size=self._size,
        )


class _FakeRoot:
    def __init__(self, members: list[_FakeMember]) -> None:
        self._members = members

    def exists(self) -> bool:
        return True

    def is_dir(self) -> bool:
        return True

    def is_symlink(self) -> bool:
        return False

    def rglob(self, pattern: str) -> list[_FakeMember]:
        assert pattern == "*"
        return self._members


def _runtime_namespace() -> dict[str, object]:
    module_name = "auragateway_transaction_bound_runtime_test"
    module = types.ModuleType(module_name)
    module.__file__ = str(RUNTIME_PATH)
    sys.modules[module_name] = module

    source = RUNTIME_PATH.read_text(encoding="utf-8")
    exec(
        compile(source, str(RUNTIME_PATH), "exec"),
        module.__dict__,
        module.__dict__,
    )
    return module.__dict__


def test_directory_snapshot_counts_venv_symlink_without_rejecting() -> None:
    namespace = _runtime_namespace()
    directory_snapshot = namespace["directory_snapshot"]
    assert callable(directory_snapshot)
    snapshot = directory_snapshot(
        _FakeRoot(
            [
                _FakeMember(symlink=True),
                _FakeMember(size=11),
            ]
        )
    )
    assert snapshot == {
        "exists": True,
        "file_count": 1,
        "symlink_count": 1,
        "size_bytes": 11,
    }


def test_cleanup_snapshot_failure_is_secondary_and_scratch_is_removed(
    tmp_path: Path,
) -> None:
    namespace = _runtime_namespace()
    scratch = tmp_path / "scratch"
    output = tmp_path / "output"
    scratch.mkdir()
    output.mkdir()
    (scratch / "member.txt").write_text("x", encoding="utf-8")

    def fail_snapshot(path: Path) -> dict[str, object]:
        _ = path
        raise RuntimeError("synthetic snapshot failure")

    namespace["SCRATCH_ROOT"] = scratch
    namespace["OUTPUT_ROOT"] = output
    namespace["directory_snapshot"] = fail_snapshot

    cleanup_scratch = namespace["cleanup_scratch"]
    assert callable(cleanup_scratch)
    report = cleanup_scratch()

    assert report["status"] == "FAILED"
    assert report["snapshot_error_type"] == "RuntimeError"
    assert report["secondary_failure_only"] is True
    assert not scratch.exists()


class _FailingWorker:
    worker_id = "worker_test"
    instance_id = "worker_test-g1"

    def stop_and_report(self, reason: str) -> dict[str, object]:
        _ = reason
        raise RuntimeError("synthetic teardown failure")


def test_worker_teardown_failure_is_returned_not_raised() -> None:
    namespace = _runtime_namespace()
    safe_worker_teardown = namespace["safe_worker_teardown"]
    assert callable(safe_worker_teardown)
    report = safe_worker_teardown(_FailingWorker(), "TEST")
    assert report["status"] == "FAILED"
    assert report["secondary_failure_only"] is True
    assert report["teardown_error_type"] == "RuntimeError"


def test_transaction_context_requires_outer_wrapper_identity() -> None:
    namespace = _runtime_namespace()
    require_context = namespace["require_transaction_bound_context"]
    diagnostic_failure = cast(type[BaseException], namespace["DiagnosticFailure"])
    assert callable(require_context)

    with pytest.raises(diagnostic_failure):
        require_context()

    namespace["AURAGATEWAY_TRANSACTION_ID"] = "a" * 64
    context = require_context()
    assert context["transaction_id"] == "a" * 64
    assert context["authorization_transport"] == "EMBEDDED_WRAPPER_ADMISSION"
    assert context["authorization_specific_kaggle_inputs"] == 0


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="real merged integration record is unavailable in synthetic fixture",
)
def test_authorization_boundary_accepts_exact_generated_runtime_payload() -> None:
    payload = authorization._require_runtime_integration(
        ROOT,
        RUNTIME_PATH,
    )
    assert payload == RUNTIME_PATH.read_bytes()

from __future__ import annotations

import sys
import types
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_transaction_bound_authorization_v1 as subject,
)

ROOT = Path(__file__).resolve().parents[3]
R2_RUNTIME_PATH = (
    ROOT
    / "src"
    / "auragateway"
    / "local_abc"
    / "p5_p6_mechanism_admission_transaction_bound_runtime_v1.py"
)


def test_static_review_is_non_authorizing() -> None:
    review = subject.build_review(ROOT)
    assert review.status == "IMPLEMENTED_NOT_ISSUED"
    assert review.live_authorization_issued is False
    assert review.pilot_execution_authorized is False
    assert review.final_measured_abc_execution_authorized is False
    assert review.authorization_specific_kaggle_inputs == 0
    assert review.manual_confirmation_json_files == 0


def test_budget_separates_timing_preflight_from_pilot_attempts() -> None:
    budget = subject.ExecutionBudget()
    assert budget.maximum_timing_preflight_requests == 2
    assert budget.maximum_cache_salt_preflight_requests == 3
    assert budget.maximum_preflight_requests == 5
    assert budget.maximum_pilot_request_attempts == 432
    assert budget.maximum_total_model_requests == 437
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_external_spend == 0


def test_cache_isolation_contract_is_explicit() -> None:
    isolation = subject.CacheIsolationContract()
    assert isolation.mechanism == "VLLM_CACHE_SALT"
    assert isolation.per_trajectory_cache_salt_required is True
    assert isolation.same_trajectory_cache_reuse_permitted is True
    assert isolation.cross_trajectory_cache_reuse_permitted is False
    assert isolation.cache_salt_security_secret_claimed is False


def test_live_authorization_never_enables_final_measured_abc() -> None:
    now = datetime.now(UTC)
    authorization = subject.LiveAuthorization(
        authorization_id="variance-pilot-tx-test",
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        issuer_merge_commit="a" * 40,
        issuer_source_sha256="b" * 64,
        pilot_runtime_payload_sha256="c" * 64,
        pilot_material_sha256="d" * 64,
        runtime_launcher_readiness_sha256="e" * 64,
        current_p5_p6_acceptance_sha256="f" * 64,
    )
    assert authorization.pilot_execution_authorized is True
    assert authorization.final_measured_abc_execution_authorized is False
    assert authorization.single_use is True
    assert authorization.authorization_reusable is False
    assert authorization.unchanged_replay_authorized is False


def test_generated_outputs_validate() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == ("VARIANCE_PILOT_TRANSACTION_BOUND_AUTHORIZATION_V1_VALID")
    assert result["candidate_introduced_execution_authority"] is False


def _wrapper_namespace() -> dict[str, object]:
    source = (ROOT / subject.WRAPPER_TEMPLATE_PATH).read_text(encoding="utf-8")
    namespace: dict[str, object] = {"__name__": "variance_pilot_wrapper_test"}
    exec(
        compile(
            source,
            str(subject.WRAPPER_TEMPLATE_PATH),
            "exec",
        ),
        namespace,
        namespace,
    )
    return namespace


def test_wrapper_realizes_exact_r2_runtime_in_registered_module() -> None:
    namespace = _wrapper_namespace()
    loader = cast(
        Callable[[bytes], dict[str, object]],
        namespace["_load_r2_runtime"],
    )
    module_name = cast(str, namespace["_R2_RUNTIME_MODULE_NAME"])
    sys.modules.pop(module_name, None)
    try:
        r2_namespace = loader(R2_RUNTIME_PATH.read_bytes())
        assert module_name in sys.modules
        assert sys.modules[module_name].__dict__ is r2_namespace
        metric_type = r2_namespace["MetricSnapshotObservation"]
        assert getattr(metric_type, "__module__", None) == module_name
    finally:
        sys.modules.pop(module_name, None)


def test_wrapper_refuses_to_clobber_existing_r2_runtime_module() -> None:
    namespace = _wrapper_namespace()
    loader = cast(
        Callable[[bytes], dict[str, object]],
        namespace["_load_r2_runtime"],
    )
    module_name = cast(str, namespace["_R2_RUNTIME_MODULE_NAME"])
    marker = types.ModuleType("preexisting_r2_runtime")
    sys.modules[module_name] = marker
    try:
        with pytest.raises(
            RuntimeError,
            match="accepted R2 runtime module is already registered",
        ):
            loader(b"pass\n")
    finally:
        sys.modules.pop(module_name, None)


def test_wrapper_treats_runtime_system_exit_zero_as_success(
    capsys: pytest.CaptureFixture[str],
) -> None:
    namespace = _wrapper_namespace()
    runner = cast(
        Callable[[bytes, dict[str, object]], None],
        namespace["_execute_pilot_runtime"],
    )
    runner(b"raise SystemExit(0)\n", {"__name__": "__main__"})
    assert "AURAGATEWAY_VARIANCE_PILOT_RUNTIME_EXIT=0" in capsys.readouterr().out


def test_wrapper_propagates_nonzero_runtime_system_exit() -> None:
    namespace = _wrapper_namespace()
    runner = cast(
        Callable[[bytes, dict[str, object]], None],
        namespace["_execute_pilot_runtime"],
    )
    with pytest.raises(SystemExit) as observed:
        runner(b"raise SystemExit(3)\n", {"__name__": "__main__"})
    assert observed.value.code == 3

from __future__ import annotations

import hashlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_single_use_live_issuer_v1 as subject,
)
from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_authority_binding_v1 as binding,
)
from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_transaction_wrapper_rehearsal_v1 as rehearsal,
)

ROOT = Path(__file__).resolve().parents[3]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _live_authorization(now: datetime, material: bytes) -> subject.LiveAuthorization:
    return subject.LiveAuthorization(
        authorization_id="variance-pilot-v2-tx-test",
        issued_at=now,
        expires_at=now + timedelta(minutes=30),
        issuer_merge_commit="a" * 40,
        issuer_source_sha256="b" * 64,
        static_authority_binding_record_sha256="c" * 64,
        transaction_runtime_sha256=_sha256(
            (ROOT / rehearsal.TRANSACTION_RUNTIME_PATH).read_bytes()
        ),
        material_sha256=_sha256(material),
    )


def test_static_review_is_non_authorizing_and_v2_bound() -> None:
    review = subject.build_review(ROOT)
    assert review.status == "IMPLEMENTED_NOT_ISSUED"
    assert review.authority_binding_status == (
        "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_AUTHORITY_BINDING_VALID"
    )
    assert review.rendered_wrapper_sha256 == binding.EXPECTED_RENDERED_WRAPPER_SHA256
    assert review.bound_artifact_count == 19
    assert review.budget.maximum_pretreatment_requests == 24
    assert review.budget.maximum_pilot_request_attempts == 216
    assert review.budget.maximum_total_model_requests == 240
    assert review.budget.maximum_output_tokens_per_request == 256
    assert review.budget.maximum_hidden_retries == 0
    assert review.budget.maximum_replacement_cases == 0
    assert review.live_authorization_issued is False
    assert review.pilot_execution_authorized is False
    assert review.final_measured_abc_execution_authorized is False


def test_live_authorization_is_single_use_and_never_authorizes_final_abc() -> None:
    material = subject._canonical_bytes(rehearsal.build_transaction_material(ROOT))
    authorization = _live_authorization(datetime.now(UTC), material)
    assert authorization.pilot_execution_authorized is True
    assert authorization.final_measured_abc_execution_authorized is False
    assert authorization.single_use is True
    assert authorization.authorization_reusable is False
    assert authorization.unchanged_replay_authorized is False
    assert authorization.runtime_anti_replay_established is False
    assert authorization.authorization_specific_kaggle_inputs == 0
    assert authorization.authorization_producer_notebooks == 0
    assert authorization.manual_confirmation_json_files == 0


def test_live_wrapper_preserves_bound_graph_and_admits_exact_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    material = subject._canonical_bytes(rehearsal.build_transaction_material(ROOT))
    now = datetime.now(UTC)
    authorization = _live_authorization(now, material)
    authorization_bytes = subject._canonical_bytes(authorization)
    transaction_id = _sha256(authorization_bytes)
    wrapper = subject.render_live_wrapper(
        ROOT,
        authorization,
        transaction_id,
        authorization.issuer_merge_commit,
        authorization.issuer_source_sha256,
        authorization.static_authority_binding_record_sha256,
        material,
    )

    namespace: dict[str, Any] = {"__name__": "v2_live_wrapper_test"}
    exec(compile(wrapper, "<v2-live-wrapper-test>", "exec"), namespace, namespace)
    monkeypatch.setitem(namespace, "_gpu_count", lambda: 2)

    admission = namespace["admit"](now + timedelta(seconds=1))
    assert admission["status"] == (
        "VARIANCE_PILOT_SUCCESSOR_V2_TRANSACTION_BOUND_RUNTIME_ADMISSION_VALID"
    )
    assert admission["transaction_id"] == transaction_id
    assert admission["bound_artifact_count"] == 19
    assert admission["observed_gpu_count"] == 2

    assert admission["live_execution_enabled"] is True

    governed_module_names = (
        namespace["_AURAGATEWAY_PACKAGE"],
        namespace["_LOCAL_ABC_PACKAGE"],
        namespace["_OUTPUT_ADMISSION_MODULE"],
        namespace["_STANDALONE_MODULE"],
        namespace["_LIVE_SEMANTICS_MODULE"],
        namespace["_REQUEST_ADAPTER_MODULE"],
        namespace["_R2_RUNTIME_MODULE"],
        namespace["_TRANSACTION_RUNTIME_MODULE"],
    )
    for module_name in governed_module_names:
        assert isinstance(module_name, str)
        monkeypatch.delitem(sys.modules, module_name, raising=False)

    modules, created, realized_material = namespace["_realize_graph"]()
    try:
        assert len(modules) == 6
        assert realized_material["material_id"] == (
            "auragateway-variance-pilot-successor-v2-transaction-material-v1"
        )
        assert modules["transaction"].__dict__["main"] is not None
    finally:
        namespace["_cleanup"](created)


def test_live_wrapper_rejects_expired_authorization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    material = subject._canonical_bytes(rehearsal.build_transaction_material(ROOT))
    now = datetime.now(UTC)
    authorization = _live_authorization(now, material)
    transaction_id = _sha256(subject._canonical_bytes(authorization))
    wrapper = subject.render_live_wrapper(
        ROOT,
        authorization,
        transaction_id,
        authorization.issuer_merge_commit,
        authorization.issuer_source_sha256,
        authorization.static_authority_binding_record_sha256,
        material,
    )
    namespace: dict[str, Any] = {"__name__": "v2_live_wrapper_expiry_test"}
    exec(compile(wrapper, "<v2-live-wrapper-expiry-test>", "exec"), namespace, namespace)
    monkeypatch.setitem(namespace, "_gpu_count", lambda: 2)
    with pytest.raises(RuntimeError, match="outside its live window"):
        namespace["admit"](authorization.expires_at)


def test_live_issue_requires_main_before_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_git(repo_root: Path, *args: str, binary: bool = False) -> str | bytes:
        del repo_root, binary
        calls.append(args)
        if args == ("branch", "--show-current"):
            return "feature/test"
        raise AssertionError("issuer attempted a later Git action before rejecting non-main")

    monkeypatch.setattr(subject, "_git", fake_git)
    with pytest.raises(subject.IssuerError, match="only be issued from main"):
        subject._require_clean_synchronized_main(ROOT)
    assert calls == [("branch", "--show-current")]


def test_static_generated_outputs_validate() -> None:
    result = subject.validate_implementation(ROOT)
    assert result["status"] == ("VARIANCE_PILOT_SUCCESSOR_V2_SINGLE_USE_LIVE_ISSUER_VALID")
    assert result["candidate_introduced_live_authority"] is False
    assert result["live_authorization_issued"] is False
    assert result["model_requests_performed"] == 0
    assert result["gpu_execution_performed"] is False
    assert result["kaggle_execution_performed"] is False

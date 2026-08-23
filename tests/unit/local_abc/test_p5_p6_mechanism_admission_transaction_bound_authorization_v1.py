from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from auragateway.local_abc import (
    p5_p6_mechanism_admission_transaction_bound_authorization_v1 as subject,
)

PACKAGE_ROOT = Path(__file__).resolve().parents[3]


def _intent(
    *,
    prepared_at: datetime | None = None,
) -> subject.AuthorizationIntent:
    prepared = prepared_at or datetime(2026, 8, 23, 0, 0, tzinfo=UTC)
    return subject.AuthorizationIntent(
        intent_id="a" * 32,
        prepared_at=prepared,
        authorization_window_minutes=180,
        issuer_merge_commit="b" * 40,
        issuer_source_sha256="c" * 64,
        generator_contract_sha256="d" * 64,
        runtime_payload_sha256="e" * 64,
        runtime=subject.RuntimeModelContract(),
        budget=subject.ExecutionBudget(),
        mechanism=subject.MechanismContract(),
        required_platform=subject.RequiredPlatform(),
    )


def _authorization() -> subject.ExecutionAuthorization:
    intent = _intent()
    challenge = subject.authorization_challenge(intent)
    authorization, _ = subject.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=intent.prepared_at + timedelta(minutes=1),
    )
    return authorization


def test_candidate_boundary_is_eight_paths() -> None:
    assert len(subject.STATIC_PATHS) == 5
    assert len(subject.GENERATED_PATHS) == 3
    assert len(subject.CANDIDATE_PATHS) == 8
    assert subject.RUNTIME_PAYLOAD_PATH in subject.GENERATED_PATHS


def test_transaction_bound_operator_burden_is_zero() -> None:
    manifest = subject.ExecutionArtifactManifest(
        transaction_id="a" * 64,
        authorization_sha256="b" * 64,
        issuer_merge_commit="c" * 40,
        issuer_source_sha256="d" * 64,
        runtime_payload_sha256="e" * 64,
        generator_contract_sha256="f" * 64,
        executable_payload_sha256="1" * 64,
        notebook_container_sha256="2" * 64,
    )
    assert manifest.authorization_specific_kaggle_inputs == 0
    assert manifest.authorization_producer_notebooks == 0
    assert manifest.manual_confirmation_json_files == 0
    assert manifest.permitted_kaggle_input_roles == ("durable_runtime", "model_snapshot")


def test_execution_budget_is_frozen_at_six_three_three() -> None:
    budget = subject.ExecutionBudget()
    assert budget.maximum_model_requests == 6
    assert budget.maximum_worker_starts == 3
    assert budget.maximum_model_loads == 3
    assert budget.maximum_hidden_retries == 0
    assert budget.maximum_replacement_workers == 0
    assert budget.maximum_external_network_requests == 0


def test_mechanism_contract_preserves_semantic_separation() -> None:
    contract = subject.MechanismContract()
    assert contract.semantic_states == (
        "EXACT_MATCH",
        "VALID_JSON_MISMATCH",
        "NON_OBJECT_JSON",
        "INVALID_JSON",
    )
    assert contract.semantic_mismatch_blocks_mechanism is False
    assert contract.invalid_json_blocks_mechanism is False
    assert contract.finish_reason_stop_required is True
    assert contract.p5_uses_semantic_state is False
    assert contract.p6_uses_semantic_state is False
    assert contract.p5_acceptance_relaxed is False
    assert contract.p6_acceptance_relaxed is False


def test_authorization_challenge_binds_exact_intent() -> None:
    intent = _intent()
    challenge = subject.authorization_challenge(intent)
    expected = hashlib.sha256(subject._canonical_json_bytes(intent)).hexdigest()
    assert challenge == expected


def test_build_authorization_binds_transaction_identity() -> None:
    intent = _intent()
    challenge = subject.authorization_challenge(intent)
    authorization, encoded = subject.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=intent.prepared_at + timedelta(minutes=1),
    )
    body_bytes = subject._canonical_json_bytes(authorization.authorization)
    expected_transaction_id = hashlib.sha256(body_bytes).hexdigest()
    assert authorization.transaction_id == expected_transaction_id
    expected_encoded = subject._canonical_json_bytes(authorization)
    assert encoded == expected_encoded
    assert authorization.authorization.operator_confirmation_method == (
        "RETYPE_DYNAMIC_SHA256_CHALLENGE"
    )
    assert authorization.authorization.authorization_reusable is False


def test_build_authorization_rejects_wrong_challenge() -> None:
    intent = _intent()
    with pytest.raises(subject.AuthorizationIssuerError) as raised:
        subject.build_authorization(
            intent,
            challenge="0" * 64,
            confirmed_at=intent.prepared_at + timedelta(minutes=1),
        )
    assert raised.value.error_code == "P5_P6_TX_AUTH_CHALLENGE_DRIFT"


def test_build_authorization_rejects_stale_confirmation() -> None:
    intent = _intent()
    challenge = subject.authorization_challenge(intent)
    with pytest.raises(subject.AuthorizationIssuerError) as raised:
        subject.build_authorization(
            intent,
            challenge=challenge,
            confirmed_at=intent.prepared_at + timedelta(minutes=16),
        )
    assert raised.value.error_code == "P5_P6_TX_AUTH_CONFIRMATION_STALE"


def test_execution_authorization_rejects_wrong_transaction_id() -> None:
    authorization = _authorization()
    payload = authorization.model_dump(mode="json")
    payload["transaction_id"] = "0" * 64
    with pytest.raises(ValidationError):
        subject.ExecutionAuthorization.model_validate(payload)


def test_terminal_receipt_requires_outcome_for_consumed_execution() -> None:
    with pytest.raises(ValidationError):
        subject.TerminalReceipt(
            transaction_id="a" * 64,
            authorization_sha256="b" * 64,
            manifest_sha256="c" * 64,
            disposition=subject.TerminalDisposition.CONSUMED,
            execution_attempted=True,
            terminalized_at=datetime(2026, 8, 23, tzinfo=UTC),
        )


def test_unused_terminal_receipt_forbids_execution_outcome() -> None:
    with pytest.raises(ValidationError):
        subject.TerminalReceipt(
            transaction_id="a" * 64,
            authorization_sha256="b" * 64,
            manifest_sha256="c" * 64,
            disposition=subject.TerminalDisposition.CANCELLED_UNUSED,
            execution_attempted=False,
            execution_outcome=subject.ExecutionOutcome.FAILED,
            terminalized_at=datetime(2026, 8, 23, tzinfo=UTC),
        )


def test_wrapper_renders_embedded_transaction_bound_payload(tmp_path: Path) -> None:
    template_target = tmp_path / subject.TEMPLATE_PATH
    template_target.parent.mkdir(parents=True, exist_ok=True)
    packaged_template = PACKAGE_ROOT / subject.TEMPLATE_PATH
    template_target.write_bytes(packaged_template.read_bytes())

    runtime_target = tmp_path / subject.RUNTIME_PAYLOAD_PATH
    runtime_target.parent.mkdir(parents=True, exist_ok=True)
    runtime_target.write_text('print("runtime")\n', encoding="utf-8")

    intent = subject.AuthorizationIntent(
        intent_id="a" * 32,
        prepared_at=datetime(2026, 8, 23, tzinfo=UTC),
        authorization_window_minutes=180,
        issuer_merge_commit="b" * 40,
        issuer_source_sha256="c" * 64,
        generator_contract_sha256=hashlib.sha256(template_target.read_bytes()).hexdigest(),
        runtime_payload_sha256=hashlib.sha256(runtime_target.read_bytes()).hexdigest(),
        runtime=subject.RuntimeModelContract(),
        budget=subject.ExecutionBudget(),
        mechanism=subject.MechanismContract(),
        required_platform=subject.RequiredPlatform(),
    )
    challenge = subject.authorization_challenge(intent)
    authorization, authorization_bytes = subject.build_authorization(
        intent,
        challenge=challenge,
        confirmed_at=intent.prepared_at + timedelta(minutes=1),
    )
    wrapper, wrapper_sha = subject._render_wrapper(
        tmp_path,
        authorization,
        authorization_bytes,
    )
    text = wrapper.decode("utf-8")
    assert "__AUTHORIZATION_B64__" not in text
    assert "__RUNTIME_PAYLOAD_B64__" not in text
    assert authorization.transaction_id in text
    expected_wrapper_sha = hashlib.sha256(wrapper).hexdigest()
    assert wrapper_sha == expected_wrapper_sha
    compile(text, "<test-wrapper>", "exec")


def test_notebook_metadata_has_no_authorization_input_role() -> None:
    notebook = json.loads(subject._notebook_bytes(b'print("ok")\n'))
    metadata = notebook["metadata"]["auragateway"]
    assert metadata["authorization_specific_kaggle_inputs"] == 0
    assert metadata["authorization_producer_notebooks"] == 0
    assert metadata["manual_confirmation_json_files"] == 0


def _synthetic_behavior_template() -> str:
    return """from __future__ import annotations
import re
from enum import StrEnum
from typing import Final
NOTEBOOK_NAME: Final = "__NOTEBOOK_NAME__"
SOURCE_MAIN_COMMIT: Final = "__SOURCE_MAIN_COMMIT__"
IMPLEMENTATION_REVIEW_SHA256: Final = "__IMPLEMENTATION_REVIEW_SHA256__"
DESIGN_RECORD_SHA256: Final = "__DESIGN_RECORD_SHA256__"
MECHANISM_ADMISSION_CONTRACT_SHA256: Final = "__MECHANISM_ADMISSION_CONTRACT_SHA256__"
IMPLEMENTATION_ADDENDUM_SHA256: Final = "__IMPLEMENTATION_ADDENDUM_SHA256__"
MODEL_SNAPSHOT_SHA256: Final = "__MODEL_SNAPSHOT_SHA256__"
EVIDENCE_ZIP_NAME = "__EVIDENCE_ZIP_NAME__"
ACTION_BUDGET_LIMITS = {"model_requests": 6, "model_loads": 3, "worker_starts": 3}
class SemanticState(StrEnum):
    EXACT_MATCH = "EXACT_MATCH"
class DiagnosticFailure(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
AUTHORIZATION_FILENAME = "execution_authorization_v1.json"
AUTHORIZATION_CONTROL_NOTEBOOK_NAME = "ag-p5-p6-mechanism-auth-control-v1"
AUTHORIZATION_CONTROL_OUTPUT_DIRECTORY = "ag_p5_p6_mechanism_auth_control_v1"
AUTHORIZATION_TRANSPORT_CONTRACT = "GOVERNED_ROOT_EXACT_FLAT_V1"
def resolve_authorization_control_output() -> None:
    return None
def require_execution_authorization() -> dict[str, object]:
    return {"runtime_execution_authorized": True}

def consume_actions() -> None:
    return None
def get_text() -> str:
    class Response:
        def read(self) -> object:
            return b"ok"
    response = Response()
    if True:
        return response.read().decode("utf-8")
def validate_manifest(raw: dict[str, object]) -> None:
    if True:
        name = raw.get("path")
    assert name is None or isinstance(name, str)
def capture(source: object) -> None:
    while True:
        if True:
            if True:
                chunk = source.read(8192)
        break
    if True:
        if True:
            source.close()
def load_payload() -> dict[str, object]:
    payload = {}
    return payload


def _path_within_target() -> bool:
    return True
class Worker:
    def __init__(self) -> None:
        self.memory_before_start_mib = 0
    def start(self, identity: dict[str, object]) -> None:
        self.memory_before_start_mib = int(identity["memory_used_mib"])
def gpu_memory(identity: dict[str, object]) -> int:
    if identity:
        if True:
            return int(identity["memory_used_mib"])
    return 0
def observe_structured_response() -> object:
    finish_reason = "stop"
    if finish_reason != "stop":
        raise RuntimeError
    return SemanticState.EXACT_MATCH
def run_structured_request() -> dict[str, object]:
    return {"raw_output_logged": False}
def tokenize_request(
    worker: "Worker",
    request_role: str,
    prefix_variant: str,
) -> None:
    return None
def cacheable_common_prefix_bound(left: object, right: object) -> int:
    left.token_ids = ()
    right.token_ids = ()
    return sum(1 for _ in zip(left.token_ids, right.token_ids))
def decide_p5() -> bool:
    return SemanticState.EXACT_MATCH is SemanticState.EXACT_MATCH
def decide_p6() -> bool:
    return True
def main() -> int:
    try:
        active_failure_code = "AUTHORITY_FAILURE"
        authorization = require_execution_authorization()
        p5_observations = {"authorization": authorization}
        return 0
    except Exception:
        return 2
"""


def test_runtime_transform_removes_only_stale_authorization_boundary(tmp_path: Path) -> None:
    behavior = tmp_path / subject.BEHAVIOR_TEMPLATE_PATH
    behavior.parent.mkdir(parents=True, exist_ok=True)
    behavior.write_bytes(_synthetic_behavior_template().encode("utf-8"))
    payload = subject.build_runtime_payload(tmp_path)
    text = payload.decode("utf-8")
    assert "require_transaction_bound_context" in text
    assert "require_execution_authorization" not in text
    assert "AUTHORIZATION_CONTROL_NOTEBOOK_NAME" not in text
    assert "GOVERNED_ROOT_EXACT_FLAT_V1" not in text
    assert '"authorization_specific_kaggle_inputs": 0' in text
    assert subject.BASE_MAIN_COMMIT in text
    assert 'worker: "Worker"' not in text
    assert "worker: Worker" in text
    assert "zip(left.token_ids, right.token_ids)" not in text
    assert "zip(left.token_ids, right.token_ids, strict=False)" in text
    assert "# type: ignore[no-any-return]" in text
    assert "# type: ignore[assignment]" in text
    assert "# type: ignore[attr-defined]" in text
    assert "# type: ignore[call-overload]" in text
    assert "# type: ignore[no-any-return, call-overload]" in text
    assert "p5_observations: dict[str, object] = {" in text
    assert max(len(line) for line in text.splitlines()) <= 100


def test_repository_static_validation_when_authorities_are_present() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    if not (repo_root / subject.RECONCILIATION_RECORD_PATH).is_file():
        pytest.skip("full AuraGateway authority tree is not present")
    result = subject.validate_static(repo_root)
    assert result["candidate_path_count"] == 8
    assert result["authorization_specific_kaggle_inputs"] == 0
    assert result["authorization_producer_notebooks"] == 0
    assert result["mechanism_semantics_preserved"] is True
    assert result["live_authorization_issued"] is False

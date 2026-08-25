from __future__ import annotations

from pathlib import Path

import pytest

from auragateway.local_abc import (
    measured_abc_variance_pilot_v2_accepted_tokenizer_envelope_and_executable_rehearsal_v1,
)

subject = measured_abc_variance_pilot_v2_accepted_tokenizer_envelope_and_executable_rehearsal_v1

ROOT = Path(__file__).resolve().parents[3]


def _synthetic_observation() -> subject.AcceptedTokenizerEnvelopeObservationV1:
    request = subject.build_envelope_request(ROOT)
    rows = tuple(
        subject.AcceptedTokenizerObservationRow(
            sequence_index=slot.sequence_index,
            request_id=slot.request_id,
            known_segment_token_count=1000,
            prior_assistant_token_allowance=slot.prior_assistant_token_allowance,
            envelope_prompt_token_count=1000 + slot.prior_assistant_token_allowance,
        )
        for slot in request.slots
    )
    return subject.AcceptedTokenizerEnvelopeObservationV1(
        tokenizer=request.tokenizer,
        rows=rows,
    )


def test_envelope_request_binds_all_240_frozen_request_positions() -> None:
    request = subject.build_envelope_request(ROOT)
    assert len(request.slots) == 240
    assert tuple(item.sequence_index for item in request.slots) == tuple(range(240))
    assert len({item.request_id for item in request.slots}) == 240
    assert request.tokenizer.model_repository == "Qwen/Qwen2.5-0.5B-Instruct"
    assert request.tokenizer.transformers == "5.14.1"
    assert request.exact_future_assistant_outputs_claimed is False
    assert request.accepted_runtime_observation_required is True
    assert request.accepted_tokenizer_envelope_proof_complete is False
    assert request.model_requests_required is False
    assert request.gpu_required is False


def test_history_dependent_slots_reserve_the_frozen_prior_output_budget() -> None:
    request = subject.build_envelope_request(ROOT)
    pilot_slots = [slot for slot in request.slots if slot.phase == "pilot"]
    assert len(pilot_slots) == 216
    assert {slot.prior_assistant_message_count for slot in pilot_slots} == {0, 1, 2, 3}
    for slot in pilot_slots:
        assert (
            slot.prior_assistant_token_allowance
            == slot.prior_assistant_message_count * subject.MAX_OUTPUT_TOKENS
        )


def test_synthetic_complete_observation_validates_without_granting_authority() -> None:
    proof = subject.validate_accepted_tokenizer_observation(ROOT, _synthetic_observation())
    assert proof.accepted_tokenizer_envelope_proof_complete is True
    assert proof.observed_request_count == 240
    assert proof.maximum_observed_envelope_prompt_tokens == 1768
    assert proof.minimum_headroom_tokens == 2328
    assert proof.pilot_execution_authorized is False
    assert proof.new_execution_authorized is False


def test_over_budget_observation_is_rejected() -> None:
    observation = _synthetic_observation()
    rows = list(observation.rows)
    first = rows[0]
    rows[0] = subject.AcceptedTokenizerObservationRow(
        sequence_index=first.sequence_index,
        request_id=first.request_id,
        known_segment_token_count=3841,
        prior_assistant_token_allowance=0,
        envelope_prompt_token_count=3841,
    )
    drifted = observation.model_copy(update={"rows": tuple(rows)})
    with pytest.raises(subject.TokenizerEnvelopeRehearsalError) as observed:
        subject.validate_accepted_tokenizer_observation(ROOT, drifted)
    assert observed.value.error_code == "V2_ACCEPTED_TOKENIZER_ENVELOPE_EXCEEDED"


def test_whole_executable_rehearsal_exercises_loader_state_and_system_exit() -> None:
    result = subject.run_executable_rehearsal(ROOT)
    assert result.module_type_loader_used is True
    assert result.sys_modules_registration_used is True
    assert result.runtime_module_registered_during_execution is True
    assert result.runtime_injection_used is True
    assert result.fake_worker_request_count == 4
    assert result.token_budget_check_count == 4
    assert result.completed_turn_count == 4
    assert result.request_attempt_count == 4
    assert result.history_entry_count == 8
    assert result.system_exit_zero_handled is True
    assert result.module_registry_cleanup_complete is True
    assert result.model_requests_performed == 0
    assert result.gpu_execution_performed is False
    assert result.kaggle_execution_performed is False


def test_materialization_is_deterministic_non_authorizing_and_waits_for_observation() -> None:
    first = subject.build_materialization(ROOT)
    second = subject.build_materialization(ROOT)
    assert first == second
    assert first.executable_rehearsal_complete is True
    assert first.accepted_tokenizer_envelope_proof_complete is False
    assert first.live_runtime_executable_generated is False
    assert first.pilot_execution_authorized is False
    assert first.final_measured_abc_execution_authorized is False
    assert first.new_execution_authorized is False
    assert first.next_gate == subject.NEXT_GATE

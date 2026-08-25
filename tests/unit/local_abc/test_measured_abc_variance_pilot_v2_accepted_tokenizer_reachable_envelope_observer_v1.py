from __future__ import annotations

import importlib
from pathlib import Path

import pytest

driver = importlib.import_module(
    "auragateway.local_abc."
    "measured_abc_variance_pilot_v2_accepted_tokenizer_reachable_envelope_driver_v1"
)
observer = importlib.import_module(
    "auragateway.local_abc."
    "measured_abc_variance_pilot_v2_accepted_tokenizer_reachable_envelope_observer_v1"
)

_normalize_ids = driver._normalize_ids
EXPECTED_DEFERRED_COUNT = observer.EXPECTED_DEFERRED_COUNT
EXPECTED_OBSERVED_COUNT = observer.EXPECTED_OBSERVED_COUNT
MAX_PROMPT_TOKENS = observer.MAX_PROMPT_TOKENS
ReachableEnvelopeObservationV1 = observer.ReachableEnvelopeObservationV1
build_observation_request = observer.build_observation_request


def test_normalize_ids_accepts_flat_and_single_batch() -> None:
    assert _normalize_ids([1, 2, 3]) == [1, 2, 3]
    assert _normalize_ids([[1, 2, 3]]) == [1, 2, 3]


def test_normalize_ids_rejects_mapping_shape() -> None:
    with pytest.raises(TypeError):
        _normalize_ids({"input_ids": [1, 2]})


def test_observation_request_binds_only_history_independent_frontier() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    rows = build_observation_request(repo_root)

    assert len(rows) == EXPECTED_OBSERVED_COUNT
    assert len({row.sequence_index for row in rows}) == EXPECTED_OBSERVED_COUNT
    assert len({row.request_id for row in rows}) == EXPECTED_OBSERVED_COUNT
    assert all(len(row.messages) == 2 for row in rows)
    assert EXPECTED_OBSERVED_COUNT + EXPECTED_DEFERRED_COUNT == 240


def test_observation_contract_preserves_non_claims() -> None:
    fields = ReachableEnvelopeObservationV1.model_fields

    assert fields["history_dependent_prompt_counts_preobserved"].default is False
    assert fields["all_240_future_prompt_counts_claimed"].default is False
    assert fields["accepted_tokenizer_full_future_envelope_proof_complete"].default is False
    assert fields["static_prior_assistant_256_token_allowance_relied_on"].default is False
    assert fields["runtime_prospective_next_prompt_guard_required"].default is True
    assert fields["pilot_execution_authorized"].default is False
    assert fields["new_execution_authorized"].default is False
    assert MAX_PROMPT_TOKENS == 3840

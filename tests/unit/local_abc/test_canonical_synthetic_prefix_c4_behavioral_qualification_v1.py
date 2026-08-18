from __future__ import annotations

import copy
from pathlib import Path

import pytest

from auragateway.local_abc import (
    canonical_synthetic_prefix_c4_behavioral_qualification_v1,
)

qualification = canonical_synthetic_prefix_c4_behavioral_qualification_v1


def source_freeze_payload() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[3]
    payload = (repo_root / qualification.FREEZE_RECORD_PATH).read_bytes()
    return qualification.json_object(payload, "freeze record")


def test_frozen_corpus_authority_is_accepted() -> None:
    payload = source_freeze_payload()
    qualification.validate_freeze_record(payload)


def test_request_is_one_case_three_of_three_and_execution_inert() -> None:
    request = qualification.build_request()

    assert request.observation_contract.case_count == 1
    assert request.observation_contract.observation_count == 3
    assert request.observation_contract.exact_pass_count_required == 3
    assert request.observation_contract.fresh_worker_per_observation is True
    assert request.observation_contract.zero_cached_prefix_baseline_required is True
    assert request.observation_contract.hidden_retries_permitted == 0
    assert request.observation_contract.replacement_requests_permitted == 0

    assert request.runtime_execution_authorized is False
    assert request.authorization_issuer_included is False
    assert request.p5_execution_authorized is False
    assert request.p6_execution_authorized is False


def test_exact_request_identity_is_frozen() -> None:
    request = qualification.build_request()
    corpus = request.canonical_corpus

    assert corpus.version == "CANONICAL_SYNTHETIC_PREFIX_CORPUS_V1"
    assert corpus.sha256 == qualification.EXPECTED_CORPUS_SHA256
    assert corpus.rendered_prompt_token_count == 899
    assert corpus.rendered_prompt_token_sha256 == qualification.EXPECTED_PROMPT_TOKEN_SHA256
    assert corpus.message_roles == ("system", "user", "assistant", "user")
    assert corpus.final_object_canonical == '{"probe":"exact-runtime-p5-p6","value":1}'

    generation = request.generation_contract
    assert generation.temperature == 0
    assert generation.top_p == 1
    assert generation.repetition_penalty == 1.1
    assert generation.seed == 7
    assert generation.max_tokens == 32
    assert generation.stream is False
    assert generation.response_format is None
    assert generation.guided_decoding is None


def test_terminal_state_taxonomy_is_exact() -> None:
    request = qualification.build_request()
    states = tuple(item.state for item in request.terminal_states)
    assert states == ("QUALIFIED", "NOT_QUALIFIED", "INVALID_EXECUTION")


def test_prohibited_adaptations_block_known_shortcuts() -> None:
    request = qualification.build_request()
    joined = " ".join(request.prohibited_adaptations).lower()

    for fragment in (
        "schema",
        "parser",
        "hidden retries",
        "assistant acknowledgement",
        "canonical context",
        "message roles",
        "generation parameters",
        "model",
        "3/3",
    ):
        assert fragment in joined


def test_freeze_record_c4_state_drift_fails_closed() -> None:
    payload = copy.deepcopy(source_freeze_payload())
    qualification_state = qualification.mapping(
        payload.get("qualification_state"),
        "qualification state",
    )
    qualification_state["c4_behavioral_qualification"] = "QUALIFIED"

    with pytest.raises(
        qualification.QualificationDesignError,
        match="qualification state drifted",
    ):
        qualification.validate_freeze_record(payload)


def test_freeze_record_corpus_identity_drift_fails_closed() -> None:
    payload = copy.deepcopy(source_freeze_payload())
    corpus = qualification.mapping(payload.get("canonical_corpus"), "canonical corpus")
    corpus["sha256"] = "0" * 64

    with pytest.raises(
        qualification.QualificationDesignError,
        match="canonical corpus contract drifted",
    ):
        qualification.validate_freeze_record(payload)


def test_generated_request_bytes_are_canonical() -> None:
    request = qualification.build_request()
    payload = qualification.canonical_bytes(request.model_dump(mode="json"))

    assert payload.endswith(b"\n")
    parsed = qualification.json_object(payload, "request")
    assert parsed["qualification_id"] == (
        "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
    )
    assert parsed["runtime_execution_authorized"] is False

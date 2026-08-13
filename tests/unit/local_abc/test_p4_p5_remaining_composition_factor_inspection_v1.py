from __future__ import annotations

import ast
from pathlib import Path

import pytest

from auragateway.local_abc import p4_p5_remaining_composition_factor_inspection_v1 as subject


def _current_runtime_fixture() -> str:
    return """
SYSTEM_PROMPT = (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
SYNTHETIC_CACHE_CONTEXT_A = ("prefix " * 24) + (
    "Return only the exact JSON object supplied in the final user message, "
    "with no markdown or additional text."
)
SYNTHETIC_ASSISTANT_ACK = "Synthetic deterministic context acknowledged."

def request_messages(prefix_variant: str):
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": SYNTHETIC_CACHE_CONTEXT_A},
        {"role": "assistant", "content": SYNTHETIC_ASSISTANT_ACK},
        {"role": "user", "content": "{}"},
    ]

def request_payload(prefix_variant: str):
    return {
        "model": "m",
        "messages": request_messages(prefix_variant),
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }
"""


def test_static_string_supports_adjacent_addition_and_repetition() -> None:
    tree = ast.parse(_current_runtime_fixture())
    observed = subject._string_assignment(tree, "SYNTHETIC_CACHE_CONTEXT_A")
    assert observed.startswith("prefix prefix prefix ")
    assert observed.endswith(subject.V4_INSTRUCTION)
    assert subject._repetition_count(tree, "SYNTHETIC_CACHE_CONTEXT_A") == 24


def test_extracts_four_role_topology_and_generation_controls() -> None:
    tree = ast.parse(_current_runtime_fixture())
    assert subject._roles_from_static_lists(tree) == subject.EXPECTED_ROLES
    assert subject._generation_controls(tree) == {
        "temperature": 0,
        "top_p": 1,
        "repetition_penalty": 1.1,
        "seed": 7,
        "max_tokens": 32,
        "stream": False,
    }


def test_unknown_cache_tail_fails_closed() -> None:
    with pytest.raises(subject.InspectionError) as caught:
        subject._tail("unexpected")
    assert caught.value.error_code == "P4_P5_STATIC_INSPECTION_CACHE_CONTEXT_TAIL_UNKNOWN"


def test_record_model_rejects_non_contiguous_hypothesis_ranks() -> None:
    observation = subject.RuntimeCompositionObservation(
        role="CURRENT_REMEDIATED_RUNTIME",
        path="x.py",
        sha256="a" * 64,
        message_roles=subject.EXPECTED_ROLES,
        assistant_ack=subject.ASSISTANT_ACK,
        cache_context_repetition_count=24,
        system_instruction=subject.V4_INSTRUCTION,
        cache_context_tail=subject.V4_INSTRUCTION,
        temperature=0,
        top_p=1,
        repetition_penalty=1.1,
        seed=7,
        max_tokens=32,
        stream=False,
        accepted_behavioral_precedent=False,
    )
    historical = observation.model_copy(
        update={
            "role": "HISTORICAL_ACCEPTED_PREDECESSOR",
            "accepted_behavioral_precedent": True,
            "cache_context_tail": subject.V5_INSTRUCTION,
        }
    )
    hypotheses = (
        subject.HypothesisAssessment(
            rank=2,
            hypothesis_id="x",
            status=subject.HypothesisStatus.LIVE_UNRESOLVED,
            evidence_for=(),
            evidence_against=(),
            static_conclusion="unresolved",
        ),
    )
    with pytest.raises(ValueError, match="ranks are not contiguous"):
        subject.InspectionRecord(
            schema_version="1.0.0",
            record_id="auragateway-p4-p5-remaining-composition-factor-inspection-v1",
            stage_id=subject.STAGE_ID,
            status="STATIC_INSPECTION_COMPLETE_EXECUTION_NOT_AUTHORIZED",
            base_main_commit=subject.BASE_MAIN_COMMIT,
            current_first_material_divergence="C3_COMPOSED_REQUEST_OUTPUT_CONTRACT",
            current_composition_differential="COMPOSITION_REGRESSION_SUPPORTED",
            first_remediation_result="REMEDIATION_INTERVENTION_INSUFFICIENT",
            authorities=tuple(
                subject.AuthorityReceipt(
                    role=f"r{i}",
                    path=f"p{i}",
                    sha256="a" * 64,
                    scope=subject.AuthorityScope.CURRENT_ACCEPTED,
                )
                for i in range(10)
            ),
            current_runtime=observation,
            historical_predecessor=historical,
            hypotheses=hypotheses,
            preferred_discriminator=subject.RecommendedDiscriminator(
                test_id="CACHE_CONTEXT_REPETITION_24_VS_1_WITH_COMPOSITION_FROZEN",
                variable_under_test="CACHE_CONTEXT_REPETITION_COUNT",
                control_value=1,
                treatment_value=24,
                frozen_message_roles=subject.EXPECTED_ROLES,
                assistant_ack_preserved=True,
                accepted_v4_instruction_preserved=True,
                final_json_object_preserved=True,
                runtime_model_identity_preserved=True,
                generation_controls_preserved=True,
                hidden_retries_permitted=0,
                reason="isolate one variable",
                execution_required_to_resolve=True,
                execution_authorized_by_inspection=False,
            ),
            remaining_composition_subfactor_identified=False,
            root_cause_established=False,
            p5_reached=False,
            p6_reached=False,
            p5_failure_established=False,
            p6_failure_established=False,
            runtime_execution_authorized=False,
            gpu_execution_authorized=False,
            new_execution_authorized=False,
            guided_decoding_fix_authorized=False,
            source_sha256="b" * 64,
            non_claims=tuple(f"n{i}" for i in range(10)),
            next_gate=subject.NEXT_GATE,
        )


def test_write_bytes_atomic_rejects_existing_temp_path(tmp_path: Path) -> None:
    destination = tmp_path / "record.json"
    temporary = tmp_path / "record.json.tmp"
    temporary.write_text("occupied", encoding="utf-8")
    with pytest.raises(subject.InspectionError) as caught:
        subject._write_bytes_atomic(destination, b"{}\n")
    assert caught.value.error_code == "P4_P5_STATIC_INSPECTION_TEMP_PATH_EXISTS"

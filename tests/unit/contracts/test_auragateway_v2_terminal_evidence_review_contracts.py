from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.auragateway_v2_terminal_evidence_review import (
    AuraGatewayV2TerminalEvidenceReview,
    AuraGatewayV2TerminalEvidenceReviewManifest,
    TerminalEvidenceClaimDecision,
    TerminalEvidenceClaimKind,
    TerminalEvidenceNextPhase,
    TerminalEvidenceReviewStatus,
)

_REVIEW_ROOT = Path("data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_review_loads_with_terminal_negative_state() -> None:
    review = AuraGatewayV2TerminalEvidenceReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert (
        review.status
        is TerminalEvidenceReviewStatus.CLOSED_CORE_RUNTIME_WITH_NEGATIVE_PROVIDER_TELEMETRY
    )
    assert review.prd_version == "2.2.0"
    assert review.core_scope_closed is True
    assert review.achieved_state.measured_a_b_c_comparison_completed is False
    assert review.gate_4_resolution.gate_4_passed_for_measured_benchmark is False
    assert review.gate_4_resolution.negative_result_accepted is True


def test_review_contains_all_fourteen_claim_decisions() -> None:
    review = AuraGatewayV2TerminalEvidenceReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )
    decisions = {item.claim_kind: item.decision for item in review.claims}

    assert set(decisions) == set(TerminalEvidenceClaimKind)
    assert (
        decisions[TerminalEvidenceClaimKind.OBSERVED_PROVIDER_WIRE_OMISSION]
        is TerminalEvidenceClaimDecision.PERMITTED
    )
    assert (
        decisions[TerminalEvidenceClaimKind.MEASURED_A_B_C_COMPARISON]
        is TerminalEvidenceClaimDecision.BLOCKED
    )
    assert (
        decisions[TerminalEvidenceClaimKind.PRODUCTION_READINESS]
        is TerminalEvidenceClaimDecision.BLOCKED
    )


def test_review_rejects_missing_source_binding() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    bindings = deepcopy(payload["source_bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["source_bindings"] = bindings

    with pytest.raises(ValidationError):
        AuraGatewayV2TerminalEvidenceReview.model_validate(payload)


def test_review_rejects_duplicate_claim() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    claims = deepcopy(payload["claims"])
    assert isinstance(claims, list)
    claims[-1] = deepcopy(claims[0])
    payload["claims"] = claims

    with pytest.raises(ValidationError, match="all 14 claim decisions"):
        AuraGatewayV2TerminalEvidenceReview.model_validate(payload)


def test_review_rejects_a_b_c_claim_promotion() -> None:
    payload = _json_object(_REVIEW_ROOT / "review.json")
    claims = payload["claims"]
    assert isinstance(claims, list)
    for claim in claims:
        assert isinstance(claim, dict)
        if claim["claim_kind"] == "measured_a_b_c_comparison":
            claim["decision"] = "permitted"
            break

    with pytest.raises(
        ValidationError,
        match="terminal claim decision does not match evidence boundary",
    ):
        AuraGatewayV2TerminalEvidenceReview.model_validate(payload)


def test_review_preserves_unknown_not_zero() -> None:
    review = AuraGatewayV2TerminalEvidenceReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )
    decisions = {item.claim_kind: item.decision for item in review.claims}

    assert review.achieved_state.provider_cache_usage_measured is False
    assert (
        decisions[TerminalEvidenceClaimKind.CACHED_TOKENS_EQUAL_ZERO]
        is TerminalEvidenceClaimDecision.BLOCKED
    )


def test_review_separates_publication_from_core_runtime() -> None:
    review = AuraGatewayV2TerminalEvidenceReview.model_validate(
        _json_object(_REVIEW_ROOT / "review.json")
    )

    assert review.publication_boundary.hugging_face_publication_part_of_core_runtime is False
    assert review.publication_boundary.publication_layer_started is False
    assert review.publication_boundary.live_inference_permitted is False
    assert review.next_phase is TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN


def test_manifest_locks_governing_documents() -> None:
    manifest = AuraGatewayV2TerminalEvidenceReviewManifest.model_validate(
        _json_object(_REVIEW_ROOT / "manifest.json")
    )

    assert manifest.source_evidence_locked is True
    assert manifest.protected_evidence_read is False
    assert manifest.core_scope_closed is True
    assert manifest.next_phase is TerminalEvidenceNextPhase.HUGGING_FACE_PUBLICATION_LAYER_DESIGN

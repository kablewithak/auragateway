from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.hugging_face_publication import (
    ClaimDisposition,
    ClaimRecord,
    ProviderLineageRecord,
    ProviderLineageStatus,
    PublicationEvidenceClass,
    PublicationState,
)


def _lineage() -> ProviderLineageRecord:
    return ProviderLineageRecord(
        lineage_id="lineage",
        provider="provider",
        requested_model=None,
        evidence_class=PublicationEvidenceClass.CONTROLLED_PROVIDER,
        status=ProviderLineageStatus.CLOSED_TELEMETRY_UNAVAILABLE,
        attempts=1,
        provider_successes=1,
        cache_telemetry_observed=False,
        comparison_eligible=False,
        summary="terminal summary",
        permitted_claim="bounded claim",
        blocked_claims=("cache hit",),
        source_paths=("source.json",),
    )


def _claim() -> ClaimRecord:
    return ClaimRecord(
        claim_id="claim",
        disposition=ClaimDisposition.PERMITTED,
        statement="bounded statement",
        evidence_basis=("source.json",),
    )


def test_publication_state_accepts_static_sanitized_boundary() -> None:
    state = PublicationState(
        schema_version="1.0.0",
        publication_id="publication",
        project="AuraGateway v2",
        source_main_checkpoint="checkpoint",
        core_prd_version="2.3.0",
        hy3_mini_prd_version="1.1.0",
        evidence_maturity=("production-shaped",),
        provider_lineages=(_lineage(), _lineage().model_copy(update={"lineage_id": "two"})),
        claims=(_claim(),),
        comparison_eligible=False,
        live_inference_included=False,
        credential_required=False,
        customer_data_included=False,
        raw_provider_payload_included=False,
        publication_license="other",
    )

    assert state.publication_id == "publication"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("comparison_eligible", True),
        ("live_inference_included", True),
        ("credential_required", True),
        ("customer_data_included", True),
        ("raw_provider_payload_included", True),
    ],
)
def test_publication_state_rejects_boundary_violation(field: str, value: bool) -> None:
    payload = {
        "schema_version": "1.0.0",
        "publication_id": "publication",
        "project": "AuraGateway v2",
        "source_main_checkpoint": "checkpoint",
        "core_prd_version": "2.3.0",
        "hy3_mini_prd_version": "1.1.0",
        "evidence_maturity": ("production-shaped",),
        "provider_lineages": (
            _lineage().model_dump(mode="json"),
            _lineage().model_copy(update={"lineage_id": "two"}).model_dump(mode="json"),
        ),
        "claims": (_claim().model_dump(mode="json"),),
        "comparison_eligible": False,
        "live_inference_included": False,
        "credential_required": False,
        "customer_data_included": False,
        "raw_provider_payload_included": False,
        "publication_license": "other",
    }
    payload[field] = value

    with pytest.raises(ValidationError):
        PublicationState.model_validate(payload)

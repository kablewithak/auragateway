from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.retrieval_selection import (
    MetadataPolicy,
    RetrievalSelectionPolicy,
    SelectionBenefitWeights,
)


def test_default_selection_policy_is_development_only() -> None:
    policy = RetrievalSelectionPolicy()

    assert policy.top_k_values == (3, 5, 7)
    assert policy.eligible_metadata_policy is MetadataPolicy.AUTHORED
    assert policy.held_out_validation_required
    assert not policy.measured_execution_permitted


def test_benefit_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError):
        SelectionBenefitWeights(mean_recall_at_k=0.19)


def test_top_k_values_must_be_unique_and_sorted() -> None:
    with pytest.raises(ValidationError):
        RetrievalSelectionPolicy(top_k_values=(5, 3, 5), minimum_top_k=3)


def test_negative_control_policies_cannot_be_removed() -> None:
    with pytest.raises(ValidationError):
        RetrievalSelectionPolicy(metadata_policies=(MetadataPolicy.AUTHORED,))

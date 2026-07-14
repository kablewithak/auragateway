from __future__ import annotations

import pytest
from pydantic import ValidationError

from auragateway.contracts.openrouter import (
    OpenRouterCacheFieldObservation,
    OpenRouterCacheObservationState,
)


def test_cache_field_contract_preserves_explicit_zero() -> None:
    observation = OpenRouterCacheFieldObservation(
        field_name="cached_tokens",
        field_present=True,
        state=OpenRouterCacheObservationState.OBSERVED_ZERO,
        value=0,
    )
    assert observation.value == 0


def test_cache_field_contract_rejects_absent_as_zero() -> None:
    with pytest.raises(ValidationError, match="presence and value"):
        OpenRouterCacheFieldObservation(
            field_name="cached_tokens",
            field_present=False,
            state=OpenRouterCacheObservationState.FIELD_ABSENT,
            value=0,
        )


def test_cache_field_contract_rejects_nonpositive_positive_state() -> None:
    with pytest.raises(ValidationError, match="greater than zero"):
        OpenRouterCacheFieldObservation(
            field_name="cache_write_tokens",
            field_present=True,
            state=OpenRouterCacheObservationState.OBSERVED_POSITIVE,
            value=0,
        )

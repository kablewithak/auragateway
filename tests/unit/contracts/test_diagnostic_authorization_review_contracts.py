from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from auragateway.contracts.diagnostic_authorization_review import (
    DiagnosticAuthorizationReviewManifest,
    DiagnosticAuthorizationReviewPackage,
    DiagnosticDryRunReport,
)

_REVIEW_ROOT = Path("data/evals/benchmark/diagnostic-authorization-review-v1")


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def test_review_package_is_inactive_and_non_live() -> None:
    review = DiagnosticAuthorizationReviewPackage.model_validate(
        _json_object(_REVIEW_ROOT / "review_package.json")
    )

    assert review.status.value == "review_ready"
    assert review.activation_state.value == "inactive"
    assert review.maximum_provider_calls == 24
    assert review.minimum_planned_elapsed_seconds == 2220
    assert review.provider_calls_permitted is False
    assert review.execution_command_available is False
    assert review.active_authorization_id is None


def test_dry_run_report_validates_frozen_schedule() -> None:
    report = DiagnosticDryRunReport.model_validate(
        _json_object(_REVIEW_ROOT / "dry_run_report.json")
    )

    assert len(report.attempts) == 24
    assert report.attempts[0].planned_offset_seconds == 0
    assert report.attempts[-1].planned_offset_seconds == 2220
    assert report.unique_provider_request_count == 18
    assert report.repeated_provider_request_count == 6
    assert report.provider_calls_made is False


def test_review_manifest_binds_package_and_report() -> None:
    manifest = DiagnosticAuthorizationReviewManifest.model_validate(
        _json_object(_REVIEW_ROOT / "manifest.json")
    )

    assert manifest.activation_state == "inactive"
    assert manifest.active_authorization_present is False
    assert manifest.provider_calls_permitted is False


def test_review_package_cannot_enable_provider_calls() -> None:
    payload = _json_object(_REVIEW_ROOT / "review_package.json")
    payload["provider_calls_permitted"] = True

    with pytest.raises(ValidationError):
        DiagnosticAuthorizationReviewPackage.model_validate(payload)


def test_review_package_cannot_add_active_authorization_id() -> None:
    payload = _json_object(_REVIEW_ROOT / "review_package.json")
    payload["active_authorization_id"] = "unsafe-live-authorization"

    with pytest.raises(ValidationError):
        DiagnosticAuthorizationReviewPackage.model_validate(payload)


def test_review_package_requires_exact_five_bindings() -> None:
    payload = _json_object(_REVIEW_ROOT / "review_package.json")
    bindings = deepcopy(payload["bindings"])
    assert isinstance(bindings, list)
    bindings.pop()
    payload["bindings"] = bindings

    with pytest.raises(ValidationError):
        DiagnosticAuthorizationReviewPackage.model_validate(payload)


def test_dry_run_report_rejects_schedule_offset_drift() -> None:
    payload = _json_object(_REVIEW_ROOT / "dry_run_report.json")
    attempts = deepcopy(payload["attempts"])
    assert isinstance(attempts, list)
    assert isinstance(attempts[-1], dict)
    attempts[-1]["planned_offset_seconds"] = 2219
    payload["attempts"] = attempts

    with pytest.raises(ValidationError, match="frozen minimum elapsed time"):
        DiagnosticDryRunReport.model_validate(payload)


def test_dry_run_report_rejects_provider_request_count_drift() -> None:
    payload = _json_object(_REVIEW_ROOT / "dry_run_report.json")
    payload["unique_provider_request_count"] = 17

    with pytest.raises(ValidationError):
        DiagnosticDryRunReport.model_validate(payload)


def test_public_review_assets_contain_no_raw_prompt_or_output_fields() -> None:
    public_text = "\n".join(
        (
            (_REVIEW_ROOT / "review_package.json").read_text(encoding="utf-8"),
            (_REVIEW_ROOT / "dry_run_report.json").read_text(encoding="utf-8"),
            (_REVIEW_ROOT / "manifest.json").read_text(encoding="utf-8"),
        )
    )

    for forbidden in (
        '"system_prompt":',
        '"user_prompts_by_turn":',
        '"messages":',
        '"raw_request":',
        '"raw_output":',
        '"provider_error_message":',
        '"api_key":',
    ):
        assert forbidden not in public_text

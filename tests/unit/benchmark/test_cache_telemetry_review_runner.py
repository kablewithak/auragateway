from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark import cache_telemetry_review_runner
from auragateway.benchmark.cache_telemetry_review_runner import (
    CacheTelemetryReviewError,
    validate_cache_telemetry_review,
)

_REVIEW_ROOT = Path("data/evals/benchmark/cache-telemetry-review-v1")
_CLOSEOUT_PATH = Path("data/evals/benchmark/diagnostic-closeout-v1/closeout.json")
_CLOSEOUT_MANIFEST_PATH = Path("data/evals/benchmark/diagnostic-closeout-v1/manifest.json")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Cache_Telemetry_Sufficiency_Review.md")


def _copy_review_assets(repo_root: Path) -> None:
    for relative_path in (
        _REVIEW_ROOT / "review.json",
        _REVIEW_ROOT / "manifest.json",
        _REPORT_PATH,
    ):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def _write_closeout_assets(repo_root: Path) -> None:
    closeout = {
        "closeout_id": "batch-06-diagnostic-closeout-v1",
        "status": "closed_nonreproduced",
        "execution_outcome": {
            "provider_call_count": 24,
            "successful_call_count": 24,
            "provider_error_count": 0,
        },
        "cache_telemetry": {
            "cached_input_token_sample_count": 0,
            "total_cached_input_tokens": None,
            "cache_evidence_available": False,
            "unknown_interpreted_as_zero": False,
            "reason": "CACHE_EVIDENCE_UNAVAILABLE",
        },
        "authorization_consumed": True,
        "rerun_permitted": False,
        "resume_permitted": False,
        "execution_evidence_mutation_permitted": False,
        "benchmark_claims_permitted": False,
        "comparison_eligible": False,
        "next_gate": "cache_telemetry_sufficiency_review",
    }
    closeout_path = repo_root / _CLOSEOUT_PATH
    closeout_path.parent.mkdir(parents=True, exist_ok=True)
    closeout_path.write_text(
        json.dumps(closeout, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest = {"closeout_sha256": hashlib.sha256(closeout_path.read_bytes()).hexdigest()}
    manifest_path = repo_root / _CLOSEOUT_MANIFEST_PATH
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )


def _repo_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    _copy_review_assets(tmp_path)
    _write_closeout_assets(tmp_path)

    review = cast(
        dict[str, object],
        json.loads((tmp_path / _REVIEW_ROOT / "review.json").read_text(encoding="utf-8")),
    )
    bindings = review["source_bindings"]
    assert isinstance(bindings, list)
    expected_by_path = {
        cast(str, item["path"]): cast(str, item["git_blob_sha1"])
        for item in bindings
        if isinstance(item, dict)
    }

    def fake_git_blob_sha1(
        repo_root: Path,
        commit: str,
        path: str,
    ) -> str:
        assert repo_root == tmp_path
        assert commit == "247d611657bed874bcefdc58dbc7db1f3a014f7b"
        return expected_by_path[path]

    monkeypatch.setattr(
        cache_telemetry_review_runner,
        "_git_blob_sha1",
        fake_git_blob_sha1,
    )
    return tmp_path


def test_validator_accepts_frozen_review(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)

    summary = validate_cache_telemetry_review(repo_root)

    assert summary.command == "validate"
    assert summary.provider_call_count == 24
    assert summary.successful_call_count == 24
    assert summary.cached_input_token_sample_count == 0
    assert summary.cache_claim_sufficient is False
    assert summary.provider_call_authorized is False
    assert summary.credential_accessed is False


def test_validator_does_not_read_groq_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_cache_telemetry_review(repo_root)

    assert summary.credential_accessed is False
    assert summary.provider_call_authorized is False


def test_validator_rejects_review_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    review_path = repo_root / _REVIEW_ROOT / "review.json"
    payload = cast(
        dict[str, object],
        json.loads(review_path.read_text(encoding="utf-8")),
    )
    external_sources = payload["external_sources"]
    assert isinstance(external_sources, list)
    assert isinstance(external_sources[0], dict)
    assertions = external_sources[0]["assertions"]
    assert isinstance(assertions, list)
    assertions[0] = assertions[0] + " with reviewed semantics"
    review_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CacheTelemetryReviewError,
        match="no longer matches its manifest",
    ):
        validate_cache_telemetry_review(repo_root)


def test_validator_rejects_report_hash_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    report_path = repo_root / _REPORT_PATH
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CacheTelemetryReviewError,
        match="report no longer matches",
    ):
        validate_cache_telemetry_review(repo_root)


def test_validator_rejects_closeout_cache_evidence_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)
    closeout_path = repo_root / _CLOSEOUT_PATH
    payload = cast(
        dict[str, object],
        json.loads(closeout_path.read_text(encoding="utf-8")),
    )
    cache_telemetry = payload["cache_telemetry"]
    assert isinstance(cache_telemetry, dict)
    cache_telemetry["cached_input_token_sample_count"] = 1
    closeout_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    manifest_path = repo_root / _CLOSEOUT_MANIFEST_PATH
    manifest_path.write_text(
        json.dumps(
            {"closeout_sha256": hashlib.sha256(closeout_path.read_bytes()).hexdigest()},
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CacheTelemetryReviewError,
        match="cache telemetry closeout evidence",
    ):
        validate_cache_telemetry_review(repo_root)


def test_validator_rejects_source_binding_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _repo_fixture(tmp_path, monkeypatch)

    def mismatched_blob(
        repo_root: Path,
        commit: str,
        path: str,
    ) -> str:
        return "0" * 40

    monkeypatch.setattr(
        cache_telemetry_review_runner,
        "_git_blob_sha1",
        mismatched_blob,
    )

    with pytest.raises(
        CacheTelemetryReviewError,
        match="source no longer matches",
    ):
        validate_cache_telemetry_review(repo_root)

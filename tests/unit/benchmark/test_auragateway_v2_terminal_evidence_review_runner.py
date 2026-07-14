from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark.auragateway_v2_terminal_evidence_review_runner import (
    TerminalEvidenceReviewError,
    validate_terminal_evidence_review,
)

_REVIEW_ROOT = Path("data/evals/benchmark/auragateway-v2-terminal-evidence-review-v1")
_SUPERSESSION_ROOT = Path(
    "data/evals/benchmark/auragateway-v2-terminal-evidence-review-supersession-v1"
)
_SUPERSEDING_REVIEW_ROOT = Path("data/evals/benchmark/openrouter-hy3-terminal-evidence-review-v1")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json_object(path: Path) -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads(path.read_text(encoding="utf-8")),
    )


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _copy_repo_assets(repo_root: Path) -> None:
    review = _json_object(_REVIEW_ROOT / "review.json")
    bindings = review["source_bindings"]
    assert isinstance(bindings, list)

    paths = []
    for binding in bindings:
        assert isinstance(binding, dict)
        path = binding["path"]
        assert isinstance(path, str)
        paths.append(Path(path))

    manifest = _json_object(_REVIEW_ROOT / "manifest.json")
    for key in (
        "review_path",
        "report_path",
        "adr_path",
        "prd_path",
        "session_brief_path",
        "readme_path",
        "publication_prd_path",
    ):
        path = manifest[key]
        assert isinstance(path, str)
        paths.append(Path(path))

    paths.extend(
        (
            _REVIEW_ROOT / "manifest.json",
            _SUPERSESSION_ROOT / "supersession.json",
            _SUPERSEDING_REVIEW_ROOT / "manifest.json",
        )
    )

    for relative_path in set(paths):
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def _refresh_review_and_manifest(repo_root: Path) -> None:
    review_path = repo_root / _REVIEW_ROOT / "review.json"
    review = _json_object(review_path)
    bindings = review["source_bindings"]
    assert isinstance(bindings, list)
    for binding in bindings:
        assert isinstance(binding, dict)
        path = binding["path"]
        assert isinstance(path, str)
        binding["sha256"] = _sha256(repo_root / path)
    _write_json(review_path, review)

    manifest_path = repo_root / _REVIEW_ROOT / "manifest.json"
    manifest = _json_object(manifest_path)
    manifest["review_sha256"] = _sha256(review_path)
    _write_json(manifest_path, manifest)

    supersession_path = repo_root / _SUPERSESSION_ROOT / "supersession.json"
    supersession = _json_object(supersession_path)
    supersession["source_manifest_sha256"] = _sha256(manifest_path)
    _write_json(supersession_path, supersession)


def test_validator_accepts_terminal_review(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)

    summary = validate_terminal_evidence_review(tmp_path)

    assert summary.source_binding_count == 18
    assert summary.core_scope_closed is True
    assert summary.gate_4_passed_for_measured_benchmark is False
    assert summary.measured_a_b_c_comparison_completed is False
    assert summary.provider_cache_usage_measured is False
    assert summary.comparison_eligible is False
    assert summary.additional_provider_execution_permitted is False


def test_validator_reads_no_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_repo_assets(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")
    monkeypatch.setenv("OPENROUTER_API_KEY", "must-not-be-read")

    summary = validate_terminal_evidence_review(tmp_path)

    assert summary.core_scope_closed is True


def test_validator_rejects_source_binding_drift(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/report.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="bound terminal evidence asset no longer matches",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_governing_document_drift(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / "README.md"
    path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="superseded governing document no longer matches",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_immutable_document_drift(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / "docs/benchmark/AuraGateway_v2_Terminal_Evidence_Review.md"
    path.write_text(path.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="immutable governing document no longer matches",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_missing_supersession_overlay(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    (tmp_path / _SUPERSESSION_ROOT / "supersession.json").unlink()

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="required terminal review asset was not found",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_superseding_manifest_drift(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / _SUPERSEDING_REVIEW_ROOT / "manifest.json"
    path.write_text(path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="superseding terminal continuity manifest no longer matches",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_superseding_binding_drift(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / _SUPERSESSION_ROOT / "supersession.json"
    payload = _json_object(path)
    assets = payload["assets"]
    assert isinstance(assets, list)
    first = assets[0]
    assert isinstance(first, dict)
    first["superseding_sha256"] = "0" * 64
    _write_json(path, payload)

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="delegated document hash does not match the superseding manifest",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_invalid_supersession_mapping(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / _SUPERSESSION_ROOT / "supersession.json"
    payload = _json_object(path)
    assets = payload["assets"]
    assert isinstance(assets, list)
    first = assets[0]
    assert isinstance(first, dict)
    first["superseding_hash_field"] = "readme_sha256"
    _write_json(path, payload)

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="terminal review asset failed typed validation",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_historical_manifest_mutation(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    manifest_path = tmp_path / _REVIEW_ROOT / "manifest.json"
    manifest = _json_object(manifest_path)
    manifest["readme_sha256"] = "0" * 64
    _write_json(manifest_path, manifest)

    supersession_path = tmp_path / _SUPERSESSION_ROOT / "supersession.json"
    supersession = _json_object(supersession_path)
    supersession["source_manifest_sha256"] = _sha256(manifest_path)
    _write_json(supersession_path, supersession)

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="delegated historical document hash does not match",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_sdk_boundary_promotion(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / "data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1/review.json"
    payload = _json_object(path)
    payload["sdk_upgrade_required"] = True
    _write_json(path, payload)
    _refresh_review_and_manifest(tmp_path)

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="terminal review asset failed typed validation",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_execution_outcome_promotion(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = tmp_path / "data/evals/benchmark/groq-cache-telemetry-reauthorization-v1/report.json"
    payload = _json_object(path)
    payload["raw_numeric_sample_count"] = 1
    _write_json(path, payload)
    _refresh_review_and_manifest(tmp_path)

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="raw-wire execution conclusion no longer matches",
    ):
        validate_terminal_evidence_review(tmp_path)


def test_validator_rejects_gate_4_promotion(tmp_path: Path) -> None:
    _copy_repo_assets(tmp_path)
    path = (
        tmp_path
        / "data/evals/benchmark/groq-cache-telemetry-reauthorization-closeout-v1/closeout.json"
    )
    payload = _json_object(path)
    gate = payload["gate_4_resolution"]
    assert isinstance(gate, dict)
    gate["gate_4_passed"] = True
    _write_json(path, payload)
    _refresh_review_and_manifest(tmp_path)

    with pytest.raises(
        TerminalEvidenceReviewError,
        match="terminal review asset failed typed validation",
    ):
        validate_terminal_evidence_review(tmp_path)

from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.evals.remediation_runner import (
    RemediationError,
    main,
    verify_all,
    write_all,
)

REPO_ROOT = Path(".")


def _copy_inputs(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for relative in (
        "data/corpus",
        "data/chunking",
        "data/retrieval",
        "data/evals/retrieval/development-v1",
        "data/evals/retrieval/development-v2",
        "data/evals/retrieval/held-out-v1",
        "data/evals/retrieval/remediation-v1",
    ):
        source = Path(relative)
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    return repo_root


def test_persisted_remediation_evidence_verifies() -> None:
    summary = verify_all(REPO_ROOT)

    assert summary.remediated_candidate_count == 2
    assert summary.development_case_count == 24
    assert summary.resolved_case_count == 2
    assert summary.remaining_failure_count == 0
    assert summary.held_out_v2_required is True
    assert summary.retrieval_freeze_permitted is False


def test_write_then_verify_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)

    written = write_all(repo_root)
    verified = verify_all(repo_root)

    assert verified == written


def test_changed_metadata_registry_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    metadata_path = repo_root / "data/retrieval/remediation-v1/source_metadata.json"
    payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    payload["corpus_manifest_sha256"] = "0" * 64
    metadata_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        write_all(repo_root)
    except RemediationError as exc:
        assert exc.error_code == "REMEDIATION_CORPUS_MANIFEST_MISMATCH"
        return
    raise AssertionError("changed metadata registry was accepted")


def test_modified_scorecard_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    write_all(repo_root)
    scorecard_path = (
        repo_root / "data/evals/retrieval/remediation-v1/"
        "bm25-fixed-window-remediated-v2/scorecard.json"
    )
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    payload["aggregate"]["mean_recall_at_k"] = 0.0
    scorecard_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_all(repo_root)
    except RemediationError as exc:
        assert exc.error_code == "REMEDIATION_ARTIFACT_MISMATCH"
        return
    raise AssertionError("modified remediation scorecard was accepted")


def test_report_preserves_held_out_v1_hash() -> None:
    report = json.loads(
        Path("data/evals/retrieval/remediation-v1/report.json").read_text(encoding="utf-8")
    )

    assert report["held_out_v1_modified"] is False
    assert report["held_out_v2_required"] is True
    assert report["retrieval_freeze_permitted"] is False
    assert report["remaining_development_failure_ids"] == []


def test_cli_verify_prints_content_free_summary(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["gate_1_status"] == "blocked_pending_held_out_v2"
    assert payload["remaining_failure_count"] == 0
    assert "query_text" not in captured.out

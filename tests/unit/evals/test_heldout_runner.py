from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.contracts.retrieval_gate import GateOneDecisionStatus
from auragateway.evals.heldout_runner import (
    HeldOutValidationError,
    build_gate_one,
    main,
    verify_gate_one,
    write_gate_one,
)

REPO_ROOT = Path(".")


def _copy_inputs(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for relative in (
        "data/corpus",
        "data/chunking",
        "data/retrieval",
        "data/evals/retrieval/development-v1",
        "data/evals/retrieval/selection-v1",
        "data/evals/retrieval/held-out-v1",
    ):
        source = Path(relative)
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    return repo_root


def test_build_gate_one_exposes_real_held_out_block() -> None:
    build = build_gate_one(REPO_ROOT)

    assert len(build.candidates) == 2
    assert sum(candidate.variant.hard_gate_passed for candidate in build.candidates) == 0
    assert build.report.decision.status is GateOneDecisionStatus.BLOCKED
    assert build.freeze_manifest is None
    assert {
        failed_case
        for candidate in build.candidates
        for failed_case in candidate.variant.failed_case_ids
    } == {"ho-ret-002", "ho-ret-011"}


def test_persisted_gate_one_evidence_verifies() -> None:
    summary = verify_gate_one(REPO_ROOT)

    assert summary.held_out_case_count == 12
    assert summary.finalist_count == 2
    assert summary.passing_finalist_count == 0
    assert summary.gate_1_passed is False
    assert summary.retrieval_configuration_fingerprint is None


def test_write_then_verify_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)

    written = write_gate_one(repo_root)
    verified = verify_gate_one(repo_root)

    assert verified == written
    assert not (repo_root / "data/retrieval/frozen-v1/manifest.json").exists()


def test_changed_held_out_set_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    held_out_path = repo_root / "data/evals/retrieval/held-out-v1/accepted_cases.json"
    payload = json.loads(held_out_path.read_text(encoding="utf-8"))
    payload["cases"][0]["query_text"] += " changed"
    held_out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_gate_one(repo_root)
    except HeldOutValidationError as exc:
        assert exc.error_code == "HELD_OUT_SET_HASH_MISMATCH"
        return
    raise AssertionError("modified held-out set was accepted")


def test_modified_scorecard_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    write_gate_one(repo_root)
    scorecard_path = (
        repo_root / "data/evals/retrieval/held-out-v1/bm25-fixed-window-v1/scorecard.json"
    )
    payload = json.loads(scorecard_path.read_text(encoding="utf-8"))
    payload["aggregate"]["mean_recall_at_k"] = 0.0
    scorecard_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_gate_one(repo_root)
    except HeldOutValidationError as exc:
        assert exc.error_code == "HELD_OUT_SCORECARD_MISMATCH"
        return
    raise AssertionError("modified held-out scorecard was accepted")


def test_blocked_gate_rejects_unauthorized_freeze_manifest(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    write_gate_one(repo_root)
    freeze_path = repo_root / "data/retrieval/frozen-v1/manifest.json"
    freeze_path.parent.mkdir(parents=True, exist_ok=True)
    freeze_path.write_text("{}\n", encoding="utf-8")

    try:
        verify_gate_one(repo_root)
    except HeldOutValidationError as exc:
        assert exc.error_code == "HELD_OUT_UNAUTHORIZED_FREEZE_PRESENT"
        return
    raise AssertionError("blocked Gate 1 accepted an unauthorized freeze manifest")


def test_cli_verify_prints_content_free_summary(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["decision_status"] == "gate_1_blocked"
    assert payload["held_out_case_count"] == 12
    assert "query_text" not in captured.out

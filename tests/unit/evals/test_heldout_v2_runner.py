from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.contracts.retrieval_gate import GateOneDecisionStatus
from auragateway.evals.heldout_v2_runner import (
    HeldOutV2Error,
    build_gate_one_v2,
    main,
    verify_gate_one_v2,
    write_gate_one_v2,
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
        "data/evals/retrieval/selection-v1",
        "data/evals/retrieval/held-out-v1",
        "data/evals/retrieval/held-out-v2",
        "data/evals/retrieval/remediation-v1",
    ):
        source = Path(relative)
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
    return repo_root


def test_build_gate_one_v2_passes_and_reverses_development_ranking() -> None:
    build = build_gate_one_v2(REPO_ROOT)

    assert len(build.candidates) == 2
    assert all(candidate.variant.hard_gate_passed for candidate in build.candidates)
    assert build.report.decision.status is GateOneDecisionStatus.REVERSED
    assert build.report.decision.selected_retriever_config_id == (
        "dense-hashed-tfidf-section-aware-remediated-v2"
    )
    assert build.freeze_manifest is not None
    assert build.freeze_manifest.configuration_fingerprint == (
        "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"
    )


def test_persisted_gate_one_v2_evidence_verifies() -> None:
    summary = verify_gate_one_v2(REPO_ROOT)

    assert summary.held_out_case_count == 12
    assert summary.finalist_count == 2
    assert summary.passing_finalist_count == 2
    assert summary.gate_1_passed is True
    assert summary.retrieval_freeze_permitted is True


def test_write_then_verify_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)

    written = write_gate_one_v2(repo_root)
    verified = verify_gate_one_v2(repo_root)

    assert verified == written
    assert (repo_root / "data/retrieval/frozen-v1/manifest.json").is_file()


def test_changed_held_out_v2_set_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    path = repo_root / "data/evals/retrieval/held-out-v2/accepted_cases.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["cases"][0]["query_text"] += " changed"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_gate_one_v2(repo_root)
    except HeldOutV2Error as exc:
        assert exc.error_code == "HELD_OUT_V2_SET_HASH_MISMATCH"
        return
    raise AssertionError("modified held-out v2 set was accepted")


def test_held_out_v1_history_change_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    path = repo_root / "data/evals/retrieval/held-out-v1/decision.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "changed"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_gate_one_v2(repo_root)
    except HeldOutV2Error as exc:
        assert exc.error_code == "HELD_OUT_V1_DECISION_CHANGED"
        return
    raise AssertionError("changed held-out v1 history was accepted")


def test_modified_v2_scorecard_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    write_gate_one_v2(repo_root)
    path = (
        repo_root / "data/evals/retrieval/held-out-v2/"
        "dense-hashed-tfidf-section-aware-remediated-v2/scorecard.json"
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["aggregate"]["mean_recall_at_k"] = 0.0
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_gate_one_v2(repo_root)
    except HeldOutV2Error as exc:
        assert exc.error_code == "HELD_OUT_V2_SCORECARD_MISMATCH"
        return
    raise AssertionError("modified held-out v2 scorecard was accepted")


def test_modified_retrieval_freeze_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    write_gate_one_v2(repo_root)
    path = repo_root / "data/retrieval/frozen-v1/manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["selected_top_k"] = 7
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_gate_one_v2(repo_root)
    except HeldOutV2Error as exc:
        assert exc.error_code == "HELD_OUT_V2_RETRIEVAL_FREEZE_MISMATCH"
        return
    raise AssertionError("modified retrieval freeze was accepted")


def test_cli_verify_prints_content_free_summary(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["decision_status"] == "development_recommendation_reversed"
    assert payload["held_out_case_count"] == 12
    assert "query_text" not in captured.out

from __future__ import annotations

import json
import shutil
from pathlib import Path

from auragateway.evals.episode_runner import (
    EpisodeAssetError,
    build_assets,
    main,
    verify_assets,
    write_assets,
)

REPO_ROOT = Path(".")


def _copy_inputs(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    for relative in (
        "data/corpus/source_inventory.json",
        "data/retrieval/frozen-v1/manifest.json",
        "data/evals/episodes",
    ):
        source = Path(relative)
        target = repo_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return repo_root


def test_persisted_episode_assets_verify() -> None:
    summary = verify_assets(REPO_ROOT)

    assert summary.functional_episode_count == 18
    assert summary.runtime_episode_count == 6
    assert summary.rejected_proposal_count == 8
    assert summary.gate_2_passed is True
    assert summary.measured_execution_permitted is False


def test_build_assets_binds_retrieval_freeze() -> None:
    manifest, freeze, summary = build_assets(REPO_ROOT)

    assert manifest.retrieval_configuration_fingerprint == (
        "220ce9ac6e19789bedf1aedc2b6253db5ba03a09ebcc6efdac203eb80cd23490"
    )
    assert freeze.required_next_gate == "prefix_determinism"
    assert summary.validation_status == "valid"


def test_write_then_verify_in_isolated_repo(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)

    written = write_assets(repo_root)
    verified = verify_assets(repo_root)

    assert verified == written
    assert (repo_root / "data/evals/episodes/manifest.json").is_file()
    assert (repo_root / "data/evals/episodes/freeze_record.json").is_file()


def test_modified_episode_set_is_rejected_by_verification(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    path = repo_root / "data/evals/episodes/functional-v1/accepted_episodes.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["episodes"][0]["title"] += " changed"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        verify_assets(repo_root)
    except EpisodeAssetError as exc:
        assert exc.error_code == "EPISODE_MANIFEST_MISMATCH"
        return
    raise AssertionError("modified episode set was accepted")


def test_unknown_source_reference_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    path = repo_root / "data/evals/episodes/functional-v1/accepted_episodes.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["episodes"][0]["source_scope"]["required_source_ids"][0] = "NR-UNKNOWN-999"
    payload["episodes"][0]["expected_terminal_decision"]["required_citation_source_ids"][0] = (
        "NR-UNKNOWN-999"
    )
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_assets(repo_root)
    except EpisodeAssetError as exc:
        assert exc.error_code == "EPISODE_UNKNOWN_SOURCE_REFERENCE"
        return
    raise AssertionError("unknown source reference was accepted")


def test_noneligible_runtime_episode_is_rejected(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    path = repo_root / "data/evals/episodes/runtime-v1/selection.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["entries"][0]["episode_id"] = "ep-func-004"
    payload["entries"][0]["expected_terminal_decision"] = "answer"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_assets(repo_root)
    except EpisodeAssetError as exc:
        assert exc.error_code == "RUNTIME_EPISODE_NOT_ELIGIBLE"
        return
    raise AssertionError("noneligible runtime episode was accepted")


def test_review_protocol_cannot_expose_raw_content(tmp_path: Path) -> None:
    repo_root = _copy_inputs(tmp_path)
    path = repo_root / "data/evals/episodes/blinded_review_protocol.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["public_trace_contains_raw_content"] = True
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    try:
        build_assets(repo_root)
    except EpisodeAssetError as exc:
        assert exc.error_code == "EPISODE_ASSET_VALIDATION_FAILED"
        return
    raise AssertionError("raw public review content was accepted")


def test_cli_verify_prints_content_free_summary(capsys: object) -> None:
    exit_code = main(["verify", "--repo-root", "."])
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["functional_episode_count"] == 18
    assert payload["gate_2_passed"] is True
    assert "user_message" not in captured.out

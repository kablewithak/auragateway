from __future__ import annotations

import json
from pathlib import Path

from auragateway.publication.hugging_face import (
    DATASET_ROOT,
    PUBLICATION_MANIFEST_PATH,
    SANITIZATION_REPORT_PATH,
    SPACE_ROOT,
    validate_publication,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_committed_hugging_face_publication_is_canonical() -> None:
    manifest = validate_publication(_repo_root())

    assert manifest.live_inference_included is False
    assert manifest.credential_required is False
    assert manifest.remote_publication_authorized is False


def test_publication_assets_exclude_protected_material() -> None:
    repo_root = _repo_root()
    sanitization = json.loads((repo_root / SANITIZATION_REPORT_PATH).read_text(encoding="utf-8"))

    assert sanitization["passed"] is True
    assert sanitization["secret_pattern_match_count"] == 0
    assert sanitization["raw_payload_match_count"] == 0
    assert sanitization["forbidden_path_match_count"] == 0


def test_hugging_face_candidates_are_standalone() -> None:
    repo_root = _repo_root()
    dataset_files = {path.name for path in (repo_root / DATASET_ROOT).iterdir()}
    space_files = {path.name for path in (repo_root / SPACE_ROOT).iterdir()}

    assert {"README.md", "publication_state.json", "evidence_boundary.md"}.issubset(dataset_files)
    assert {"README.md", "index.html", "style.css", "app.js", "evidence.js"}.issubset(space_files)
    assert (repo_root / PUBLICATION_MANIFEST_PATH).is_file()


def test_space_is_static_and_has_no_network_or_storage_api() -> None:
    root = _repo_root()
    readme = (root / SPACE_ROOT / "README.md").read_text(encoding="utf-8")
    index = (root / SPACE_ROOT / "index.html").read_text(encoding="utf-8")
    app = (root / SPACE_ROOT / "app.js").read_text(encoding="utf-8")

    assert "sdk: static" in readme
    assert '<script src="evidence.js"></script>' in index
    assert '<script src="app.js"></script>' in index
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "localStorage", "sessionStorage"):
        assert forbidden not in app


def test_dataset_card_preserves_pending_license_boundary() -> None:
    readme = (_repo_root() / DATASET_ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("---\n")
    assert "license: other" in readme
    assert "Remote publication must remain blocked" in readme

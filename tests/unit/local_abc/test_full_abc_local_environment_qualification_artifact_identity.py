from __future__ import annotations

import hashlib
import json
from pathlib import Path

from auragateway.local_abc.full_abc_local_environment_qualification_artifact_identity import (
    directory_sha256,
)


def _canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def test_directory_sha256_uses_versioned_inventory_envelope(tmp_path: Path) -> None:
    root = tmp_path / "artifact"
    root.mkdir()
    (root / "alpha.txt").write_text("alpha", encoding="utf-8")
    (root / "nested").mkdir()
    (root / "nested/beta.txt").write_text("beta", encoding="utf-8")

    entries = [
        {
            "path": "alpha.txt",
            "sha256": hashlib.sha256(b"alpha").hexdigest(),
            "size_bytes": 5,
        },
        {
            "path": "nested/beta.txt",
            "sha256": hashlib.sha256(b"beta").hexdigest(),
            "size_bytes": 4,
        },
    ]
    wrapped = {
        "schema_version": "1.0.0",
        "files": entries,
    }
    wrapped_sha256 = hashlib.sha256(_canonical_json(wrapped).encode("utf-8")).hexdigest()
    bare_list_sha256 = hashlib.sha256(_canonical_json(entries).encode("utf-8")).hexdigest()

    assert wrapped_sha256 == ("de44bbe5c43edbdea52de0a8d24d78ac6da5d791a794bab66965edb8d09973bf")
    assert bare_list_sha256 == ("19d56bf75d68069373dbc801733ee432301472216c3ba1963bfa551020bd35dd")
    assert wrapped_sha256 != bare_list_sha256
    assert directory_sha256(root) == wrapped_sha256

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from auragateway.local_abc import full_abc_local_vllm_resolution_lock as lock

ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exact_resolution_lock_package_validates() -> None:
    summary = lock.validate_repository_package(ROOT)

    assert summary["status"] == "VLLM_CU129_EXACT_RESOLUTION_LOCK_PACKAGE_VALID"
    assert summary["resolution_lock_sha256"] == lock.EXPECTED_LOCK_SHA256
    assert summary["materializer_notebook_sha256"] == lock.EXPECTED_MATERIALIZER_SHA256
    assert summary["package_count"] == 176
    assert summary["host_count"] == 5
    assert summary["artifact_transfer_observed_during_reconnaissance"] is True
    assert summary["package_installation_performed"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["qualification_claimed"] is False
    assert summary["authorization_issued"] is False
    assert summary["next_gate"] == "materialize_exact_locked_cu129_wheelhouse"


def test_lock_binds_complete_unique_sorted_closure() -> None:
    payload = json.loads((ROOT / lock.LOCK_PATH).read_text(encoding="utf-8"))
    model = lock.ResolutionLockV1.model_validate(payload)

    assert model.package_count == 176
    assert len(model.records) == 176
    assert [record.normalized_name for record in model.records] == sorted(
        record.normalized_name for record in model.records
    )
    assert len(set(record.normalized_name for record in model.records)) == 176
    assert len(set(record.sha256 for record in model.records)) == 176


def test_lock_exact_host_inventory_matches_reconnaissance() -> None:
    payload = json.loads((ROOT / lock.LOCK_PATH).read_text(encoding="utf-8"))
    records = payload["records"]

    counts: dict[str, int] = {}
    for record in records:
        counts[record["hostname"]] = counts.get(record["hostname"], 0) + 1

    assert counts == lock.EXPECTED_HOST_COUNTS
    assert payload["wildcard_domains_permitted"] is False
    assert all(
        item["decision"] == "approved_only_for_exact_locked_artifacts"
        for item in payload["exact_host_policy"]
    )


def test_lock_binds_requested_runtime_versions() -> None:
    payload = json.loads((ROOT / lock.LOCK_PATH).read_text(encoding="utf-8"))
    versions = {record["normalized_name"]: record["version"] for record in payload["records"]}

    assert versions["vllm"] == "0.19.1"
    assert versions["torch"] == "2.10.0+cu129"
    assert versions["torchaudio"] == "2.10.0+cu129"
    assert versions["torchvision"] == "0.25.0+cu129"
    assert versions["transformers"] == "5.5.3"


def test_materializer_repairs_cu128_prefix_drift_and_binds_lock() -> None:
    payload = json.loads((ROOT / lock.MATERIALIZER_PATH).read_text(encoding="utf-8"))
    source = "".join(payload["cells"][1]["source"])

    assert _sha256(ROOT / lock.MATERIALIZER_PATH) == lock.EXPECTED_MATERIALIZER_SHA256
    assert f'RESOLUTION_LOCK_SHA256 = "{lock.EXPECTED_LOCK_SHA256}"' in source
    assert '"torch-2.10.0+cu129-"' in source
    assert '"torchaudio-2.10.0+cu129-"' in source
    assert '"torchvision-0.25.0+cu129-"' in source
    assert '"vllm-0.19.1-"' in source
    assert '"torch-2.10.0+cu128-"' not in source
    assert '"RESOLUTION_LOCK_MISMATCH"' in source


def test_reconnaissance_result_preserves_transfer_semantics() -> None:
    payload = json.loads((ROOT / lock.RESULT_PATH).read_text(encoding="utf-8"))
    review = payload["review_resolution"]

    assert payload["decision"] == "RECONNAISSANCE_ACCEPTED_AND_LOCKED"
    assert review["artifact_transfer_observed_during_pip_dry_run"] is True
    assert review["pip_download_subcommand_performed"] is False
    assert review["package_installation_performed"] is False
    assert review["persistent_wheelhouse_created"] is False

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from auragateway.local_abc import full_abc_local_vllm_runtime_compatibility as runtime

ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_repository_runtime_compatibility_package_validates() -> None:
    summary = runtime.validate_repository_package(ROOT)

    assert summary["status"] == "VLLM_RUNTIME_COMPATIBILITY_PACKAGE_VALID"
    assert summary["failure_code"] == "VLLM_TORCH_ABI_MISMATCH"
    assert summary["materializer_failure_code"] == "VLLM_CU128_RELEASE_ASSET_ABSENT"
    assert summary["selected_vllm"] == "0.19.1"
    assert summary["selected_torch"] == "2.10.0+cu129"
    assert summary["selected_cuda_variant"] == "cu129"
    assert summary["evidence_files_verified"] == 19
    assert summary["materializer_notebook_sha256"] == (
        runtime.EXPECTED_MATERIALIZER_NOTEBOOK_SHA256
    )
    assert summary["verifier_notebook_sha256"] == (runtime.EXPECTED_VERIFIER_NOTEBOOK_SHA256)
    assert summary["authorization_issued"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["qualification_claimed"] is False


def test_decision_record_binds_cu129_artifact_identities() -> None:
    payload = json.loads((ROOT / runtime.RECORD_PATH).read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.3.0"
    assert payload["decision"] == ("APPROVED_FOR_ISOLATED_CU129_WHEELHOUSE_MATERIALIZATION")
    assert payload["artifacts"] == {
        "materializer_kaggle_name": runtime.MATERIALIZER_NOTEBOOK_NAME,
        "materializer_notebook": runtime.MATERIALIZER_NOTEBOOK_PATH.as_posix(),
        "output_directory": runtime.OUTPUT_DIRECTORY_NAME,
        "verifier_evidence_directory": runtime.VERIFIER_EVIDENCE_DIRECTORY_NAME,
        "verifier_kaggle_name": runtime.VERIFIER_NOTEBOOK_NAME,
        "verifier_notebook": runtime.VERIFIER_NOTEBOOK_PATH.as_posix(),
    }


def test_decision_record_preserves_observed_and_selected_stacks() -> None:
    payload = json.loads((ROOT / runtime.RECORD_PATH).read_text(encoding="utf-8"))

    assert payload["failure"]["observed_vllm"] == "0.25.1+cu129"
    assert payload["failure"]["observed_torch"] == "2.10.0+cu128"
    assert payload["selected_runtime"]["vllm_release"] == "0.19.1"
    assert payload["selected_runtime"]["vllm"] == "0.19.1"
    assert payload["selected_runtime"]["cuda_variant"] == "cu129"
    assert payload["selected_runtime"]["vllm_binary_cuda"] == "12.9"
    assert payload["selected_runtime"]["torch"] == "2.10.0+cu129"
    assert payload["selected_runtime"]["transformers"] == "5.5.3"
    assert payload["selected_runtime"]["base_environment_torch_is_runtime_authority"] is False


def test_failed_cu128_materializer_identity_is_preserved() -> None:
    payload = json.loads((ROOT / runtime.RECORD_PATH).read_text(encoding="utf-8"))
    failure = payload["materializer_failure"]

    assert failure["classification"] == "MATERIALIZER_RELEASE_ASSET_CONTRACT_FAILURE"
    assert failure["code"] == "VLLM_CU128_RELEASE_ASSET_ABSENT"
    assert failure["historical_kaggle_title"] == ("auragateway-cu128-wheelhouse-asset-mismatch-v1")
    assert failure["execution_log_sha256"] == (runtime.EXPECTED_MATERIALIZER_FAILURE_LOG_SHA256)
    assert failure["output_generated"] is False
    assert failure["wheel_downloads_performed"] == 0
    assert failure["model_requests_performed"] == 0
    assert failure["qualification_claimed"] is False


def test_source_identity_preserves_prior_uploaded_evidence() -> None:
    identity = json.loads((ROOT / runtime.SOURCE_IDENTITY_PATH).read_text(encoding="utf-8"))

    assert identity["qualification_evidence_zip_sha256"] == (
        runtime.EXPECTED_QUALIFICATION_EVIDENCE_ZIP_SHA256
    )
    assert identity["qualification_log_sha256"] == (runtime.EXPECTED_QUALIFICATION_LOG_SHA256)
    assert identity["diagnostic_evidence_zip_sha256"] == (
        runtime.EXPECTED_DIAGNOSTIC_EVIDENCE_ZIP_SHA256
    )
    assert len(identity["diagnostic_evidence_members"]) == 14
    assert len(identity["qualification_evidence_members"]) == 3


def test_cu128_runtime_artifact_paths_are_retired() -> None:
    for path in runtime.LEGACY_NOTEBOOK_PATHS:
        assert not (ROOT / path).exists()

    assert not (ROOT / runtime.LEGACY_RUNBOOK_PATH).exists()
    assert (ROOT / runtime.MATERIALIZER_NOTEBOOK_PATH).is_file()
    assert (ROOT / runtime.VERIFIER_NOTEBOOK_PATH).is_file()
    assert (ROOT / runtime.SUPERSEDED_ADR_PATH).is_file()
    assert (ROOT / runtime.ADR_PATH).is_file()
    assert (ROOT / runtime.RUNBOOK_PATH).is_file()


def test_notebook_raw_identities_are_locked() -> None:
    assert _sha256(ROOT / runtime.MATERIALIZER_NOTEBOOK_PATH) == (
        runtime.EXPECTED_MATERIALIZER_NOTEBOOK_SHA256
    )
    assert _sha256(ROOT / runtime.VERIFIER_NOTEBOOK_PATH) == (
        runtime.EXPECTED_VERIFIER_NOTEBOOK_SHA256
    )


def test_materializer_notebook_binds_exact_official_release_asset() -> None:
    payload = json.loads((ROOT / runtime.MATERIALIZER_NOTEBOOK_PATH).read_text(encoding="utf-8"))
    source = "".join(payload["cells"][1]["source"])

    assert payload["metadata"]["auragateway"]["notebook_name"] == (
        runtime.MATERIALIZER_NOTEBOOK_NAME
    )
    assert payload["metadata"]["auragateway"]["internet_required"] is True
    assert payload["metadata"]["auragateway"]["model_requests_permitted"] == 0
    assert payload["cells"][1]["execution_count"] is None
    assert payload["cells"][1]["outputs"] == []
    assert f'NOTEBOOK_NAME = "{runtime.MATERIALIZER_NOTEBOOK_NAME}"' in source
    assert f'OUTPUT_DIRECTORY_NAME = "{runtime.OUTPUT_DIRECTORY_NAME}"' in source
    assert 'VLLM_DISTRIBUTION = "0.19.1"' in source
    assert 'VLLM_ASSET_NAME = "vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl"' in source
    assert runtime.EXPECTED_VLLM_ASSET_SHA256 in source
    assert '"torch==2.10.0+cu129"' in source
    assert '"transformers==5.5.3"' in source
    assert '"--require-hashes"' in source


def test_offline_verifier_uses_isolated_cu129_runtime_contract() -> None:
    payload = json.loads((ROOT / runtime.VERIFIER_NOTEBOOK_PATH).read_text(encoding="utf-8"))
    source = "".join(payload["cells"][1]["source"])

    assert payload["metadata"]["auragateway"]["notebook_name"] == (runtime.VERIFIER_NOTEBOOK_NAME)
    assert payload["metadata"]["auragateway"]["internet_required"] is False
    assert payload["metadata"]["auragateway"]["accelerator"] == "T4 x2"
    assert f'NOTEBOOK_NAME = "{runtime.VERIFIER_NOTEBOOK_NAME}"' in source
    assert (
        f'OUTPUT_ZIP = Path("/kaggle/working/{runtime.VERIFIER_EVIDENCE_DIRECTORY_NAME}.zip")'
    ) in source
    assert (
        f'EVIDENCE_ROOT = Path("/kaggle/working/{runtime.VERIFIER_EVIDENCE_DIRECTORY_NAME}")'
    ) in source
    assert f'"diagnostic_id": "{runtime.VERIFIER_NOTEBOOK_NAME}"' in source
    assert '"torch": "2.10.0+cu129"' in source
    assert '"cuda": "12.9"' in source
    assert '"vllm_distribution": "0.19.1"' in source
    assert '"--no-index"' in source
    assert "auragateway_vllm_runtime_cu129_v1" in source
    assert "vllm_native_extension" in source
    assert "model_requests_performed=0" in source
    assert "qualification_claimed=false" in source

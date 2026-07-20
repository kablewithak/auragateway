from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import cast

from auragateway.local_abc import (
    full_abc_local_vllm_resolution_reconnaissance as reconnaissance,
)

ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(
    name: str,
    version: str,
    url: str,
    digest: str,
) -> dict[str, object]:
    return {
        "metadata": {
            "name": name,
            "version": version,
        },
        "download_info": {
            "url": url,
            "archive_info": {
                "hashes": {
                    "sha256": digest,
                }
            },
        },
    }


def test_repository_reconnaissance_package_validates() -> None:
    summary = reconnaissance.validate_repository_package(ROOT)

    assert summary["status"] == "VLLM_RESOLUTION_RECONNAISSANCE_RESULT_VALID"
    assert summary["notebook_sha256"] == reconnaissance.EXPECTED_NOTEBOOK_SHA256
    assert summary["historical_failure_count"] == 3
    assert summary["nvidia_failure_log_sha256"] == (
        reconnaissance.EXPECTED_NVIDIA_FAILURE_LOG_SHA256
    )
    assert summary["resolved_distribution_count"] == 176
    assert summary["host_count"] == 5
    assert summary["policy_violation_count"] == 26
    assert summary["artifact_transfer_observed_during_pip_dry_run"] is True
    assert summary["materializer_paused"] is False
    assert summary["package_installation_performed"] is False
    assert summary["model_requests_performed"] == 0
    assert summary["qualification_claimed"] is False
    assert summary["authorization_issued"] is False
    assert summary["next_gate"] == "materialize_exact_locked_cu129_wheelhouse"


def test_plan_binds_all_three_failures_and_static_materializer_finding() -> None:
    payload = json.loads((ROOT / reconnaissance.PLAN_PATH).read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0.0"
    assert payload["decision"] == ("RUN_RESOLUTION_RECONNAISSANCE_BEFORE_MATERIALIZATION")
    assert [failure["attempt"] for failure in payload["historical_failures"]] == [1, 2, 3]
    assert payload["historical_failures"][2]["code"] == "NVIDIA_PACKAGE_HOST_NOT_ALLOWED"
    assert payload["historical_failures"][2]["execution_log_sha256"] == (
        reconnaissance.EXPECTED_NVIDIA_FAILURE_LOG_SHA256
    )
    assert payload["historical_failures"][2]["observed_host"] == "pypi.nvidia.com"
    assert payload["static_materializer_findings"][0]["code"] == (
        "MATERIALIZER_REQUIRED_PREFIX_VARIANT_DRIFT"
    )
    assert payload["reconnaissance_contract"]["collect_all_policy_violations"] is True
    assert payload["reconnaissance_contract"]["wheel_files_written"] == 0
    assert payload["reconnaissance_contract"]["package_installation_performed"] is False


def test_reconnaissance_notebook_raw_identity_is_locked() -> None:
    assert _sha256(ROOT / reconnaissance.NOTEBOOK_PATH) == (reconnaissance.EXPECTED_NOTEBOOK_SHA256)


def test_authority_mapping_is_package_family_specific() -> None:
    assert reconnaissance.expected_authority("vllm").value == "github_release"
    assert reconnaissance.expected_authority("torch").value == "pytorch"
    assert reconnaissance.expected_authority("torchaudio").value == "pytorch"
    assert reconnaissance.expected_authority("torchvision").value == "pytorch"
    assert reconnaissance.expected_authority("nvidia-cublas-cu12").value == "nvidia"
    assert reconnaissance.expected_authority("transformers").value == "pypi"


def test_candidate_nvidia_host_requires_review() -> None:
    authority, state = reconnaissance.observed_authority("pypi.nvidia.com")

    assert authority.value == "nvidia"
    assert state.value == "review_required"


def test_resolution_report_collects_all_policy_violations() -> None:
    digest_a = "a" * 64
    digest_b = "b" * 64
    digest_c = "c" * 64
    digest_d = "d" * 64
    report: dict[str, object] = {
        "install": [
            _record(
                "vllm",
                "0.19.1",
                (
                    "https://github.com/vllm-project/vllm/releases/download/"
                    "v0.19.1/vllm-0.19.1-cp38-abi3-manylinux_2_31_x86_64.whl"
                ),
                digest_a,
            ),
            _record(
                "torch",
                "2.10.0+cu129",
                "https://download-r2.pytorch.org/whl/cu129/torch.whl",
                digest_b,
            ),
            _record(
                "nvidia-cublas-cu12",
                "12.9.1.4",
                "https://pypi.nvidia.com/nvidia-cublas-cu12/cublas.whl",
                digest_c,
            ),
            _record(
                "mystery-package",
                "1.0.0",
                "https://unknown.example/mystery.whl",
                digest_d,
            ),
        ]
    }

    result = reconnaissance.evaluate_resolution_report(report)

    assert result["status"] == "RESOLUTION_RECONNAISSANCE_REVIEW_REQUIRED"
    resolved_artifacts = cast(list[dict[str, object]], result["resolved_artifacts"])
    host_inventory = cast(list[dict[str, object]], result["host_inventory"])
    violations = cast(list[dict[str, object]], result["violations"])

    assert len(resolved_artifacts) == 4
    assert [host["hostname"] for host in host_inventory] == [
        "download-r2.pytorch.org",
        "github.com",
        "pypi.nvidia.com",
        "unknown.example",
    ]
    violation_pairs = {
        (violation["distribution_name"], violation["hostname"])
        for violation in violations
        if violation["failure_code"] == "ARTIFACT_HOST_REVIEW_REQUIRED"
    }
    assert violation_pairs == {
        ("mystery-package", "unknown.example"),
        ("nvidia-cublas-cu12", "pypi.nvidia.com"),
    }


def test_resolution_report_preserves_unsafe_and_review_findings_together() -> None:
    report: dict[str, object] = {
        "install": [
            _record(
                "nvidia-cublas-cu12",
                "12.9.1.4",
                "http://user:password@pypi.nvidia.com/file.whl#fragment",
                "",
            ),
            {
                "metadata": {
                    "name": "another-package",
                    "version": "1.0.0",
                },
                "download_info": {
                    "url": "https://unknown.example/another.whl",
                    "archive_info": {},
                },
            },
        ]
    }

    result = reconnaissance.evaluate_resolution_report(report)
    violations = cast(list[dict[str, object]], result["violations"])
    failure_codes = {violation["failure_code"] for violation in violations}

    assert "ARTIFACT_URL_SCHEME_UNSAFE" in failure_codes
    assert "ARTIFACT_URL_CREDENTIALS_PRESENT" in failure_codes
    assert "ARTIFACT_URL_FRAGMENT_PRESENT" in failure_codes
    assert "ARTIFACT_SHA256_MISSING" in failure_codes
    assert "ARTIFACT_HOST_REVIEW_REQUIRED" in failure_codes


def test_resolution_report_accepts_fully_approved_exact_hosts() -> None:
    report: dict[str, object] = {
        "install": [
            _record(
                "vllm",
                "0.19.1",
                ("https://github.com/vllm-project/vllm/releases/download/v0.19.1/vllm.whl"),
                "a" * 64,
            ),
            _record(
                "torch",
                "2.10.0+cu129",
                "https://download-r2.pytorch.org/whl/cu129/torch.whl",
                "b" * 64,
            ),
            _record(
                "transformers",
                "5.5.3",
                "https://files.pythonhosted.org/packages/transformers.whl",
                "c" * 64,
            ),
        ]
    }

    result = reconnaissance.evaluate_resolution_report(report)

    assert result["status"] == "RESOLUTION_RECONNAISSANCE_POLICY_COMPLETE"
    assert result["violations"] == []

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import cast

import pytest

from auragateway.benchmark import groq_sdk_cache_schema_compatibility_runner
from auragateway.benchmark.groq_sdk_cache_schema_compatibility_runner import (
    GroqSdkCacheSchemaCompatibilityError,
    validate_groq_sdk_cache_schema_compatibility,
)
from auragateway.contracts.groq_sdk_cache_schema_compatibility import (
    GroqSdkCompatibilityClassification,
)

_REVIEW_ROOT = Path("data/evals/benchmark/groq-sdk-cache-schema-compatibility-v1")
_ADR_PATH = Path("docs/adr/groq-sdk-cache-schema-compatibility.md")
_REPORT_PATH = Path("docs/benchmark/AuraGateway_Groq_SDK_Cache_Schema_Compatibility_Review.md")


def _review_payload() -> dict[str, object]:
    return cast(
        dict[str, object],
        json.loads((_REVIEW_ROOT / "review.json").read_text(encoding="utf-8")),
    )


def _copy_assets(repo_root: Path) -> None:
    review = _review_payload()
    bindings = review["source_bindings"]
    assert isinstance(bindings, list)
    paths = [
        _REVIEW_ROOT / "review.json",
        _REVIEW_ROOT / "manifest.json",
        _ADR_PATH,
        _REPORT_PATH,
    ]
    paths.extend(Path(cast(str, item["path"])) for item in bindings if isinstance(item, dict))
    for relative_path in paths:
        destination = repo_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(relative_path, destination)


def test_validator_accepts_real_sdk_and_adapter_parity(tmp_path: Path) -> None:
    _copy_assets(tmp_path)

    summary = validate_groq_sdk_cache_schema_compatibility(tmp_path)

    assert summary.installed_sdk_version == "1.5.0"
    assert summary.primary_classification is (
        GroqSdkCompatibilityClassification.PROVIDER_OMISSION_SUPPORTED
    )
    assert summary.exact_provider_omission_cause_resolved is False
    assert summary.probe_case_count == 4
    assert summary.synthetic_adapter_probe_count == 4
    assert summary.sdk_upgrade_required is False
    assert summary.adapter_change_required is False
    assert summary.credential_accessed is False
    assert summary.provider_call_count == 0
    assert summary.provider_call_authorized is False
    assert summary.calibration_rerun_authorized is False
    assert summary.benchmark_execution_authorized is False


def test_validator_does_not_read_groq_credential(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setenv("GROQ_API_KEY", "must-not-be-read")

    summary = validate_groq_sdk_cache_schema_compatibility(tmp_path)

    assert summary.credential_accessed is False
    assert summary.provider_call_count == 0


def test_validator_rejects_source_binding_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    provider_path = tmp_path / "src/auragateway/providers/groq.py"
    provider_path.write_text(
        provider_path.read_text(encoding="utf-8") + "\n# drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        GroqSdkCacheSchemaCompatibilityError,
        match="source no longer matches",
    ):
        validate_groq_sdk_cache_schema_compatibility(tmp_path)


def test_validator_rejects_report_hash_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    report_path = tmp_path / _REPORT_PATH
    report_path.write_text(
        report_path.read_text(encoding="utf-8") + "drift\n",
        encoding="utf-8",
    )

    with pytest.raises(
        GroqSdkCacheSchemaCompatibilityError,
        match="report no longer matches",
    ):
        validate_groq_sdk_cache_schema_compatibility(tmp_path)


def test_validator_rejects_installed_sdk_version_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _copy_assets(tmp_path)
    monkeypatch.setattr(
        groq_sdk_cache_schema_compatibility_runner,
        "_installed_sdk_version",
        lambda: "1.6.0",
    )

    with pytest.raises(
        GroqSdkCacheSchemaCompatibilityError,
        match="differs from the reviewed version",
    ):
        validate_groq_sdk_cache_schema_compatibility(tmp_path)


def test_validator_rejects_dependency_requirement_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    pyproject_path = tmp_path / "pyproject.toml"
    pyproject_path.write_text(
        pyproject_path.read_text(encoding="utf-8").replace(
            '"groq>=1.5,<2"',
            '"groq>=1.4,<2"',
        ),
        encoding="utf-8",
    )

    with pytest.raises(GroqSdkCacheSchemaCompatibilityError):
        validate_groq_sdk_cache_schema_compatibility(tmp_path)

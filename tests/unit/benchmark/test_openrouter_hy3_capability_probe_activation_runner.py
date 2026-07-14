from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path

import pytest

from auragateway.benchmark.openrouter_hy3_capability_probe_activation_runner import (
    OpenRouterProbeActivationError,
    preflight_openrouter_probe,
    prepare_openrouter_probe_local,
    validate_openrouter_probe_activation,
    verify_openrouter_probe_local,
)

_ROOT = Path("data/evals/benchmark/openrouter-hy3-capability-probe-v1")
_LOCAL = Path(".local/benchmark/openrouter-hy3-capability-probe-v1")


class _PreflightClient:
    def __init__(
        self,
        *,
        models: tuple[str, ...] = ("tencent/hy3:free",),
        limit_remaining: int | None = 100,
    ) -> None:
        self.models = models
        self.limit_remaining = limit_remaining
        self.key_calls = 0
        self.model_calls = 0

    def get_key_status(self, *, timeout_seconds: float) -> Mapping[str, object]:
        assert timeout_seconds == 60
        self.key_calls += 1
        return {
            "data": {
                "label": "AuraGateway Probe",
                "limit": 100,
                "limit_remaining": self.limit_remaining,
                "usage": 0,
                "usage_daily": 0,
                "usage_weekly": 0,
                "usage_monthly": 0,
                "is_free_tier": True,
            }
        }

    def get_models(self, *, timeout_seconds: float) -> Mapping[str, object]:
        assert timeout_seconds == 60
        self.model_calls += 1
        return {"data": [{"id": model} for model in self.models]}


def _copy_assets(repo_root: Path) -> None:
    authorization = json.loads((_ROOT / "authorization.json").read_text(encoding="utf-8"))
    paths = {
        _ROOT / "authorization.json",
        _ROOT / "runtime_policy.json",
        _ROOT / "activation_report.json",
        _ROOT / "activation_manifest.json",
    }
    paths.update(Path(item["path"]) for item in authorization["bindings"])
    manifest_paths = {
        "contract_sha256": Path(
            "src/auragateway/contracts/openrouter_hy3_capability_probe_activation.py"
        ),
        "runner_sha256": Path(
            "src/auragateway/benchmark/openrouter_hy3_capability_probe_activation_runner.py"
        ),
        "adr_sha256": Path("docs/adr/openrouter-hy3-capability-probe-activation.md"),
        "report_sha256": Path(
            "docs/benchmark/AuraGateway_OpenRouter_Hy3_Capability_Probe_Activation.md"
        ),
    }
    paths.update(manifest_paths.values())
    for path in paths:
        destination = repo_root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, destination)


def test_validator_accepts_active_authorization_without_local_artifacts(
    tmp_path: Path,
) -> None:
    _copy_assets(tmp_path)
    summary = validate_openrouter_probe_activation(tmp_path)
    assert summary.authorization_status == "active"
    assert summary.protected_prompt_bundle_ready is False
    assert summary.live_preflight_passed is False
    assert summary.credential_accessed is False
    assert summary.network_request_count == 0


def test_prepare_local_creates_exact_protected_boundary(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    summary = prepare_openrouter_probe_local(tmp_path)
    assert summary.protected_prompt_bundle_ready is True
    assert summary.credential_accessed is False
    assert summary.network_request_count == 0
    bundle = tmp_path / _LOCAL / "prompt_bundle.json"
    receipt = tmp_path / _LOCAL / "preparation_receipt.json"
    assert bundle.stat().st_size == 55182
    assert receipt.is_file()
    for name in ("journal.jsonl", "raw_responses.jsonl", "parsed_responses.jsonl"):
        assert (tmp_path / _LOCAL / name).read_bytes() == b""


def test_prepare_local_is_idempotent_for_exact_assets(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    first = (tmp_path / _LOCAL / "prompt_bundle.json").read_bytes()
    prepare_openrouter_probe_local(tmp_path)
    assert (tmp_path / _LOCAL / "prompt_bundle.json").read_bytes() == first


def test_prepare_local_rejects_existing_bundle_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    path = tmp_path / _LOCAL / "prompt_bundle.json"
    path.write_bytes(path.read_bytes() + b"\n")
    with pytest.raises(OpenRouterProbeActivationError, match="different content"):
        prepare_openrouter_probe_local(tmp_path)


def test_preflight_requires_exact_phrase(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    with pytest.raises(OpenRouterProbeActivationError, match="confirmation phrase"):
        preflight_openrouter_probe(
            tmp_path,
            confirmation_phrase="wrong",
            client=_PreflightClient(),
        )


def test_preflight_retains_protected_metadata_receipt_without_inference(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    client = _PreflightClient()
    summary = preflight_openrouter_probe(
        tmp_path,
        confirmation_phrase="PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
        client=client,
    )
    assert summary.live_preflight_passed is True
    assert summary.credential_accessed is True
    assert summary.network_request_count == 2
    assert summary.inference_call_count == 0
    assert client.key_calls == 1
    assert client.model_calls == 1
    receipt = json.loads((tmp_path / _LOCAL / "preflight_receipt.json").read_text())
    assert receipt["requested_model_available"] is True
    assert receipt["inference_call_count"] == 0
    assert "AuraGateway Probe" not in json.dumps(receipt)


def test_preflight_rejects_missing_exact_model(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    with pytest.raises(OpenRouterProbeActivationError, match="absent"):
        preflight_openrouter_probe(
            tmp_path,
            confirmation_phrase="PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
            client=_PreflightClient(models=("tencent/hy3",)),
        )
    assert not (tmp_path / _LOCAL / "preflight_receipt.json").exists()


def test_preflight_cannot_repeat_after_success(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    preflight_openrouter_probe(
        tmp_path,
        confirmation_phrase="PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
        client=_PreflightClient(),
    )
    with pytest.raises(OpenRouterProbeActivationError, match="already exists"):
        preflight_openrouter_probe(
            tmp_path,
            confirmation_phrase="PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
            client=_PreflightClient(),
        )


def test_verify_local_accepts_prepared_and_preflighted_boundary(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    prepare_openrouter_probe_local(tmp_path)
    before = verify_openrouter_probe_local(tmp_path)
    assert before.live_preflight_passed is False
    preflight_openrouter_probe(
        tmp_path,
        confirmation_phrase="PREFLIGHT_OPENROUTER_HY3_CAPABILITY_PROBE_ONCE",
        client=_PreflightClient(),
    )
    after = verify_openrouter_probe_local(tmp_path)
    assert after.live_preflight_passed is True
    assert after.credential_accessed is False


def test_validator_rejects_bound_review_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = (
        tmp_path / "data/evals/benchmark/"
        "openrouter-hy3-capability-probe-authorization-review-v1/review.json"
    )
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(OpenRouterProbeActivationError, match="source input"):
        validate_openrouter_probe_activation(tmp_path)


def test_validator_rejects_manifest_bound_document_drift(tmp_path: Path) -> None:
    _copy_assets(tmp_path)
    path = tmp_path / "docs/adr/openrouter-hy3-capability-probe-activation.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(OpenRouterProbeActivationError, match="manifest"):
        validate_openrouter_probe_activation(tmp_path)

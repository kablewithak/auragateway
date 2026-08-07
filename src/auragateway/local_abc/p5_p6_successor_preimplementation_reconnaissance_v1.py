"""Validate P5/P6 successor preimplementation reconnaissance V1."""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Final, Literal, Never, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

SOURCE_MAIN_COMMIT: Final = "3939f17cf5263f54ebae022232bf6d7a6cd8ef8a"
POLICY_PATH: Final = Path(
    "data/evals/benchmark/environment-qualification-v1/"
    "p5_p6_successor_preimplementation_reconnaissance_v1_policy.json"
)
REVIEW_PATH: Final = Path(
    "benchmarks/local_abc/"
    "auragateway_p5_p6_successor_preimplementation_reconnaissance_v1_review.json"
)
NOTEBOOK_PATH: Final = Path(
    "notebooks/auragateway_p5_p6_successor_preimplementation_reconnaissance_v1.ipynb"
)

_POLICY_B64_ZLIB: Final[str] = (
    "eNqtVttu3DYQ/RVin/eiG3VxnoLULQK0sRG3AYKiEIbkaJexVlRIau1tkH/vUFrb63rtNG1fbGlF"
    "cnjOnDkzX2Yw+I2x2mt0s7Pfv9y/72utZmczN0iJzhlbW9xpvKl38Ww+W2tfi9aI2m2AFmEU8woL"
    "UFGW5QWWZSPLHJOk4SVXGKeZFLzKIKOdPfgN7RDYyc0W7LVbtUZCW4OQKxgsrMHjDezrntd9Xh9F"
    "Hzqvt1h/HqDVjZbgtenoModrLT8504XjB9sbhxThzWAtdp7Rq19cZuz+KBZCMOgUk+Bw8Zo5bFGG"
    "45azr/MnBPRZvUsoyucBnX8KvYGqibJCRaqIo1zkQuRNVpWq4TyJKuSi4JjzKH2ArsDDCnfQutU9"
    "Cyvsdtqabks3XjyCuNjFK7qCGXw/+FqazluQvlYa1h0h0/Lodk9JINwfkhEn24K3+nbE3dHJO1wc"
    "KGUbsAo73a3Z3fGniUhDRnb8eS4KlfJUYKTiuOIKoCqLggtJVGBUJQWUUuVFlVX/iYvxFndqOKaB"
    "P0/DB84u+eoyZ6QVgirxHumciUGtkf4HYrzpTWvW+xeE4HHbtySgE+ghzWORQsWbXElshFTAM8Sk"
    "wirLJGR5Ikke0QN6Zx9p/qgS7qK4b+Z+2e+XnhY/wns1ab0ZWjYp4JDxVgsLds+OGB5xmw4XN8Ze"
    "o2UHZl9WwPMkRBJlQiJIRBJLqIiFvIQokYlUEWaxaopQIDz/ThKeT/pJ/FOyD4jukjpnW6QSkG7O"
    "5AbldW905+nFEr/ItDPtKLI580gFYW5O28EuC9Z0p6MTBDQlT9KEZ6VIlChA5JyXMhVZmWGellUF"
    "gpMbxg8E3J1V72Bo/RF+OcRJtejTRZ/f1eriAfuiAd0OFhe7bBXM0mKjb2sJhI0KwaGnv72xvt5l"
    "izSL4iSK8/JpabxHIJFwNu1fjPuZxcFNFkkSahe9NUFObDyWVhrTPMsNpckYEivQCScaRaKqqCiK"
    "mCciK7Iyqegpz4silRFgAyk2PI6x+l/ZebhQDR20e6fdN0g5v6U6YxvtPKGTgaCcKSogux7NIxBz"
    "7yQKG+oe7gXLACrG3sNJucgi5ZDESQNkHchzKZq4FGkS5xmPgR7jKjhK/j2d80XHwFuUw9g7H65F"
    "bfQpBz8ZwtuhOjhIDySAAHzqljh1T/aacP8xn+Gtp8XhMi9PE7u23dZRHVd1XF/vDmrdUlbWaCl6"
    "oztFfShU8LEcnQdPwS1SLV9jxwRFVq+oo13jY91PCy36wXaOycMEMP3qN7STSqIF0nJ427Ib7TcM"
    "WEO63rAp4ptwztW4QXduZGf5NGtk75J6GhdNRVrOMSqgwIiSpwoIM4/MQBVFeWT1AfiK2pc0Fld/"
    "R04eRispflgYLeNqGY/vlAlNCtwf9oc6/ETcr8LLyfo7YvfgdRMlJ6g9AkpN01K+Vhv9iGVpqKrc"
    "KxZW0s5fpgMnE6B167XFIDl1qJM9uwkMj/GWk1Nox4xwaHeoTpCY8SaKEhodUYmE5gVEmVVFhFUk"
    "gFplCVWaZaKUT0k8YFtNsf4VeaTZtanD/WdnXx5qqqZ6Cato39004eoe7VZ7Qjo7i+azLYIjY1Gh"
    "7o6raUrFn2FVQ/MMzmcdVcUYoqbvoX7oKppaFYa+S1akKEnkKP941A2wDp9ejDt0RL9piXVygC1x"
    "p4Vug0isuXmM5ivBMWpsA+eXF1dvf714/7G+ePfzx/r8w9sfzt+9Oa9//O3q7cW7kAPTankQ2pHd"
    "LHoeHPj+9sQz3oOcpjaLZEQdaOdCOdEQt5jOCodavQN6ohxI4pS2aMJQk1U/wJEDyYuYqsOw+PhT"
    "hz40+TFVOuSkIfomV6SZUqsx/v1qCzd1gNse/NHRPg+6OzowLCGhbPunH4krRyWzhZp80Y3nzuJl"
    "tAxF7sxgZShn3QXKiV/6mFZp1cQFjb9JnjY0CQrAKEloOBA0IBaQS1ViU8Ls619Nh8FI"
)
_REVIEW_B64_ZLIB: Final[str] = (
    "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"
    "w2hOX1Or3MlsTGH8xS/AH7/+D0+/4EU="
)


class ReconnaissanceError(RuntimeError):
    def __init__(
        self,
        error_code: str,
        safe_message: str,
        path: str | None = None,
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ReconnaissanceError("P5_P6_RECON_ARGUMENT_INVALID", message)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Authority(_StrictModel):
    authority_id: str
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    path: str
    purpose: str


class ExternalAuthority(_StrictModel):
    authority_id: str
    finding: str
    git_blob_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    path: str
    ref: Literal["v0.19.1"]
    repository: Literal["vllm-project/vllm"]


class GoGate(_StrictModel):
    benchmark_trajectory_requests_permitted: Literal[0]
    measured_abc_execution_authorized: Literal[False]
    next_gate_on_pass: Literal["implement_and_merge_p5_p6_successor_runtime_qualification_v1"]
    runtime_execution_authorized: Literal[False]
    unresolved_compatibility_rows_permitted: Literal[0]


class PrivacyBoundary(_StrictModel):
    credentials_used: Literal[False]
    customer_data_used: Literal[False]
    network_required_for_local_validation: Literal[False]
    raw_model_outputs_retained: Literal[False]
    raw_prompts_retained: Literal[False]


class PolicyModel(_StrictModel):
    authorities: tuple[Authority, ...]
    external_authorities: tuple[ExternalAuthority, ...]
    go_gate: GoGate
    mode: Literal["REPOSITORY_ONLY_EVIDENCE_FUSION"]
    policy_id: Literal["auragateway-p5-p6-successor-preimplementation-reconnaissance-v1-policy"]
    privacy: PrivacyBoundary
    schema_version: Literal["1.0.0"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")


class CompatibilityRow(_StrictModel):
    classification: str
    resolution: str
    seam: str


class ReviewModel(_StrictModel):
    benchmark_trajectory_requests_permitted: Literal[0]
    compatibility_rows: tuple[CompatibilityRow, ...]
    composition_rules: dict[str, str]
    decision: Literal["GO_FOR_SUCCESSOR_IMPLEMENTATION_WITH_FROZEN_COMPOSITION_RULES"]
    established_findings: tuple[str, ...]
    implementation_invariants: tuple[str, ...]
    measured_abc_execution_authorized: Literal[False]
    next_gate: Literal["implement_and_merge_p5_p6_successor_runtime_qualification_v1"]
    non_claims: tuple[str, ...]
    review_id: Literal["auragateway-p5-p6-successor-preimplementation-reconnaissance-v1-review"]
    runtime_execution_authorized: Literal[False]
    schema_version: Literal["1.0.0"]
    source_main_commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    status: Literal["PREIMPLEMENTATION_RECONNAISSANCE_COMPLETE"]
    unresolved_compatibility_rows: tuple[object, ...]

    @model_validator(mode="after")
    def fail_closed(self) -> ReviewModel:
        if self.unresolved_compatibility_rows:
            raise ValueError("unresolved compatibility rows remain")
        if len(self.compatibility_rows) < 10:
            raise ValueError("compatibility matrix is incomplete")
        return self


def _inflate_mapping(payload: str) -> dict[str, object]:
    compressed = base64.b64decode(payload)
    decoded = zlib.decompress(compressed).decode("utf-8")
    value = json.loads(decoded)
    if not isinstance(value, dict):
        raise RuntimeError("embedded reconnaissance payload must be one object")
    return cast(dict[str, object], value)


EXPECTED_POLICY_MODEL: Final = PolicyModel.model_validate(_inflate_mapping(_POLICY_B64_ZLIB))
EXPECTED_REVIEW_MODEL: Final = ReviewModel.model_validate(_inflate_mapping(_REVIEW_B64_ZLIB))
EXPECTED_POLICY: Final = cast(
    dict[str, object],
    EXPECTED_POLICY_MODEL.model_dump(mode="json"),
)
EXPECTED_REVIEW: Final = cast(
    dict[str, object],
    EXPECTED_REVIEW_MODEL.model_dump(mode="json"),
)
AUTHORITY_BLOBS: Final = {
    authority.path: authority.git_blob_sha for authority in EXPECTED_POLICY_MODEL.authorities
}


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _git(
    repo_root: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )


def _git_blob_text(repo_root: Path, path: str) -> str:
    result = _git(repo_root, "show", f"{SOURCE_MAIN_COMMIT}:{path}")
    if result.returncode != 0:
        raise ReconnaissanceError(
            "P5_P6_RECON_AUTHORITY_READ_FAILED",
            "authority read failed",
            path,
        )
    return result.stdout


def _load_json(repo_root: Path, path: str) -> dict[str, object]:
    try:
        value = json.loads(_git_blob_text(repo_root, path))
    except json.JSONDecodeError as error:
        raise ReconnaissanceError(
            "P5_P6_RECON_AUTHORITY_JSON_INVALID",
            "authority JSON invalid",
            path,
        ) from error
    if not isinstance(value, dict):
        raise ReconnaissanceError(
            "P5_P6_RECON_AUTHORITY_SHAPE_INVALID",
            "authority root must be one object",
            path,
        )
    return cast(dict[str, object], value)


def _mapping(
    value: object,
    *,
    error_code: str,
    safe_message: str,
    path: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ReconnaissanceError(error_code, safe_message, path)
    return cast(dict[str, object], value)


def _number(
    value: object,
    *,
    error_code: str,
    safe_message: str,
    path: str,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ReconnaissanceError(error_code, safe_message, path)
    return float(value)


def _validate_repository_authorities(repo_root: Path) -> None:
    ancestor = _git(
        repo_root,
        "merge-base",
        "--is-ancestor",
        SOURCE_MAIN_COMMIT,
        "HEAD",
    )
    if ancestor.returncode != 0:
        raise ReconnaissanceError(
            "P5_P6_RECON_BASE_NOT_ANCESTOR",
            "source-main authority is not an ancestor of HEAD",
        )

    for path, expected in AUTHORITY_BLOBS.items():
        result = _git(
            repo_root,
            "rev-parse",
            f"{SOURCE_MAIN_COMMIT}:{path}",
        )
        if result.returncode != 0 or result.stdout.strip() != expected:
            raise ReconnaissanceError(
                "P5_P6_RECON_AUTHORITY_BLOB_DRIFT",
                "authority Git blob drifted",
                path,
            )


def _validate_successor_gate(repo_root: Path) -> None:
    path = "benchmarks/local_abc/auragateway_p5_p6_successor_runtime_qualification_v1_review.json"
    successor = _load_json(repo_root, path)
    if (
        successor.get("decision")
        != "IMPLEMENT_SUCCESSOR_P5_P6_QUALIFICATION_BEFORE_MEASURED_ABC_AUTHORIZATION"
        or successor.get("runtime_execution_authorized") is not False
        or successor.get("measured_abc_execution_authorized") is not False
    ):
        raise ReconnaissanceError(
            "P5_P6_RECON_SUCCESSOR_GATE_DRIFT",
            "successor gate drifted",
            path,
        )

    selected = _mapping(
        successor.get("selected_p4_contract"),
        error_code="P5_P6_RECON_SELECTED_CASE_DRIFT",
        safe_message="selected case-A contract is missing",
        path=path,
    )
    expected = {
        "case_id": "A",
        "prompt_variant": "V4",
        "repetition_penalty": 1.1,
        "output_mode": "UNCONSTRAINED",
        "reselection_permitted": False,
    }
    for key, value in expected.items():
        if selected.get(key) != value:
            raise ReconnaissanceError(
                "P5_P6_RECON_SELECTED_CASE_DRIFT",
                f"selected case-A contract drifted: {key}",
                path,
            )


def _validate_p4_hardening(repo_root: Path) -> None:
    path = (
        "data/evals/benchmark/environment-qualification-v1/"
        "p4_output_contract_diagnostic_v2_request.json"
    )
    p4 = _load_json(repo_root, path)
    hardening = _mapping(
        p4.get("runtime_hardening"),
        error_code="P5_P6_RECON_P4_HARDENING_INVALID",
        safe_message="P4 hardening contract is invalid",
        path=path,
    )
    expected: dict[str, object] = {
        "cuda_stub_paths_prohibited": True,
        "native_origin_closure_required": True,
        "real_driver_directory": "/usr/local/nvidia/lib64",
        "same_environment_for_import_and_worker": True,
        "shared_environment_helper_required": True,
        "target_nvidia_libraries_precede_ambient": True,
    }
    for key, value in expected.items():
        if hardening.get(key) != value:
            raise ReconnaissanceError(
                "P5_P6_RECON_P4_HARDENING_DRIFT",
                f"P4 hardening drifted: {key}",
                path,
            )


def _validate_v5_contract(repo_root: Path) -> None:
    path = (
        "data/evals/benchmark/environment-qualification-v1/p3_p6_runtime_diagnostic_v5_request.json"
    )
    v5 = _load_json(repo_root, path)
    budget = _mapping(
        v5.get("execution_budget"),
        error_code="P5_P6_RECON_V5_BUDGET_DRIFT",
        safe_message="V5 execution budget is invalid",
        path=path,
    )
    if (
        budget.get("maximum_model_requests") != 5
        or budget.get("benchmark_trajectory_requests_permitted") != 0
    ):
        raise ReconnaissanceError(
            "P5_P6_RECON_V5_BUDGET_DRIFT",
            "V5 execution budget drifted",
            path,
        )

    contract = _mapping(
        v5.get("evidence_contract"),
        error_code="P5_P6_RECON_V5_EVIDENCE_INVALID",
        safe_message="V5 evidence contract is invalid",
        path=path,
    )
    required = (
        "partial_p6_evidence_preservation_required",
        "per_worker_attempt_and_completion_counters_required",
        "typed_route_acknowledgement_required",
        "gpu_uuid_and_pci_bus_identity_required",
        "structured_teardown_report_required",
    )
    for key in required:
        if contract.get(key) is not True:
            raise ReconnaissanceError(
                "P5_P6_RECON_V5_EVIDENCE_DRIFT",
                f"V5 evidence contract drifted: {key}",
                path,
            )


def _validate_v4_p5_evidence(repo_root: Path) -> None:
    path = (
        "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v4/"
        "p5_prefix_cache_reset_report_v4-340120168.json"
    )
    p5 = _load_json(repo_root, path)
    if (
        p5.get("status") != "PASSED"
        or p5.get("decision") != "CACHE_SMOKE_AND_RESET_PASSED"
        or p5.get("same_worker_prefix_reuse_proven") is not True
        or p5.get("full_process_restart_reset_proven") is not True
        or p5.get("namespace_only_reset_used") is not False
    ):
        raise ReconnaissanceError(
            "P5_P6_RECON_V4_P5_DRIFT",
            "historical P5 proof drifted",
            path,
        )

    warm = _mapping(
        p5.get("warm_request"),
        error_code="P5_P6_RECON_V4_P5_SHAPE_INVALID",
        safe_message="historical warm request evidence is invalid",
        path=path,
    )
    reset = _mapping(
        p5.get("post_reset_request"),
        error_code="P5_P6_RECON_V4_P5_SHAPE_INVALID",
        safe_message="historical reset request evidence is invalid",
        path=path,
    )
    warm_metric = _mapping(
        warm.get("metric_delta"),
        error_code="P5_P6_RECON_V4_P5_SHAPE_INVALID",
        safe_message="historical warm metric evidence is invalid",
        path=path,
    )
    reset_metric = _mapping(
        reset.get("metric_delta"),
        error_code="P5_P6_RECON_V4_P5_SHAPE_INVALID",
        safe_message="historical reset metric evidence is invalid",
        path=path,
    )
    warm_cached = _number(
        warm_metric.get("cached_prefix_tokens"),
        error_code="P5_P6_RECON_V4_P5_METRIC_DRIFT",
        safe_message="historical warm cache metric is invalid",
        path=path,
    )
    reset_cached = _number(
        reset_metric.get("cached_prefix_tokens"),
        error_code="P5_P6_RECON_V4_P5_METRIC_DRIFT",
        safe_message="historical reset cache metric is invalid",
        path=path,
    )
    if warm_cached <= 0.0 or reset_cached != 0.0:
        raise ReconnaissanceError(
            "P5_P6_RECON_V4_P5_METRIC_DRIFT",
            "historical cache evidence drifted",
            path,
        )


def _validate_v4_p6_divergence(repo_root: Path) -> None:
    path = (
        "evidence_vault/local_abc/cu129-p3-p6-runtime-diagnostic-failure-v4/"
        "root_cause_analysis_v4-340120168.json"
    )
    root_cause = _load_json(repo_root, path)
    if (
        root_cause.get("first_observed_divergence")
        != "P6_WORKER_1_ROUTE_STRUCTURED_RESPONSE_OBJECT_MISMATCH"
    ):
        raise ReconnaissanceError(
            "P5_P6_RECON_V4_P6_DIVERGENCE_DRIFT",
            "historical P6 first divergence drifted",
            path,
        )


def _validate_template_differential(repo_root: Path) -> None:
    p4_path = "src/auragateway/local_abc/templates/p4_output_contract_diagnostic_v2.py.tmpl"
    v5_path = "src/auragateway/local_abc/templates/p3_p6_runtime_diagnostic_v5.py.tmpl"
    p4_template = _git_blob_text(repo_root, p4_path)
    v5_template = _git_blob_text(repo_root, v5_path)

    p4_required = (
        'environment.pop("LD_PRELOAD", None)',
        "PROHIBITED_LIBRARY_PATH_MARKERS",
        "target_nvjitlink_precedes_inherited",
    )
    for token in p4_required:
        if token not in p4_template:
            raise ReconnaissanceError(
                "P5_P6_RECON_P4_TEMPLATE_HARDENING_MISSING",
                "required P4 hardening token is missing",
                p4_path,
            )

    v5_has_ld_preload_removal = 'environment.pop("LD_PRELOAD", None)' in v5_template
    v5_has_unfiltered_inherited_ld = (
        'inherited_ld = os.environ.get("LD_LIBRARY_PATH", "")' in v5_template
    )
    if v5_has_ld_preload_removal or not v5_has_unfiltered_inherited_ld:
        raise ReconnaissanceError(
            "P5_P6_RECON_V5_DIFFERENTIAL_CHANGED",
            "V5 environment differential changed; reopen review",
            v5_path,
        )

    v5_required = (
        '"vllm:prompt_tokens_cached_total"',
        '"vllm:request_prefill_kv_computed_tokens_sum"',
        "def route_isolation(",
        "WORKER_1_METRICS_ATTRIBUTED",
        "WORKER_2_METRICS_ATTRIBUTED",
    )
    for token in v5_required:
        if token not in v5_template:
            raise ReconnaissanceError(
                "P5_P6_RECON_V5_P5_P6_CONTRACT_DRIFT",
                "required V5 P5/P6 contract token is missing",
                v5_path,
            )


def validate_authorities(repo_root: Path) -> None:
    _validate_repository_authorities(repo_root)
    _validate_successor_gate(repo_root)
    _validate_p4_hardening(repo_root)
    _validate_v5_contract(repo_root)
    _validate_v4_p5_evidence(repo_root)
    _validate_v4_p6_divergence(repo_root)
    _validate_template_differential(repo_root)


def _notebook_bytes() -> bytes:
    cell_source = """from pathlib import Path

from auragateway.local_abc import (
    p5_p6_successor_preimplementation_reconnaissance_v1 as recon,
)

repo_root = Path.cwd()
recon.validate_authorities(repo_root)
recon.validate_package(repo_root)
print("P5_P6_SUCCESSOR_PREIMPLEMENTATION_RECONNAISSANCE_PASSED=true")
print("runtime_execution_authorized=false")
print("measured_abc_execution_authorized=false")"""

    payload = {
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "id": "b3dc3aac18ef9738c933050d911e31c7",
                "metadata": {},
                "outputs": [],
                "source": cell_source.splitlines(keepends=True),
            }
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {
                "name": "python",
                "version": "3.11",
            },
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }

    notebook_json = json.dumps(
        payload,
        ensure_ascii=False,
        indent=1,
    )
    return (notebook_json + "\n").encode("utf-8")


def generate(repo_root: Path) -> None:
    validate_authorities(repo_root)
    (repo_root / REVIEW_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo_root / REVIEW_PATH).write_text(
        _canonical(EXPECTED_REVIEW) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    (repo_root / NOTEBOOK_PATH).parent.mkdir(parents=True, exist_ok=True)
    (repo_root / NOTEBOOK_PATH).write_bytes(_notebook_bytes())


def validate_package(repo_root: Path) -> None:
    validate_authorities(repo_root)
    try:
        policy_raw = json.loads((repo_root / POLICY_PATH).read_text(encoding="utf-8"))
        review_raw = json.loads((repo_root / REVIEW_PATH).read_text(encoding="utf-8"))
        PolicyModel.model_validate(policy_raw)
        ReviewModel.model_validate(review_raw)
    except (OSError, json.JSONDecodeError, ValidationError) as error:
        raise ReconnaissanceError(
            "P5_P6_RECON_PACKAGE_INVALID",
            "reconnaissance package is invalid",
        ) from error

    if policy_raw != EXPECTED_POLICY:
        raise ReconnaissanceError(
            "P5_P6_RECON_POLICY_DRIFT",
            "policy drifted",
            POLICY_PATH.as_posix(),
        )
    if review_raw != EXPECTED_REVIEW:
        raise ReconnaissanceError(
            "P5_P6_RECON_REVIEW_DRIFT",
            "review drifted",
            REVIEW_PATH.as_posix(),
        )
    if (repo_root / NOTEBOOK_PATH).read_bytes() != _notebook_bytes():
        raise ReconnaissanceError(
            "P5_P6_RECON_NOTEBOOK_DRIFT",
            "notebook drifted",
            NOTEBOOK_PATH.as_posix(),
        )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("validate-authorities", "generate", "validate-package"):
        item = subparsers.add_parser(name)
        item.add_argument("--repo-root", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    try:
        if args.command == "validate-authorities":
            validate_authorities(repo_root)
            payload: dict[str, object] = {
                "status": "P5_P6_SUCCESSOR_PREIMPLEMENTATION_AUTHORITIES_VALID",
                "source_main_commit": SOURCE_MAIN_COMMIT,
                "unresolved_compatibility_rows": 0,
                "runtime_execution_authorized": False,
                "measured_abc_execution_authorized": False,
            }
        elif args.command == "generate":
            generate(repo_root)
            payload = {
                "status": "GENERATED",
                "decision": EXPECTED_REVIEW_MODEL.decision,
                "compatibility_row_count": len(EXPECTED_REVIEW_MODEL.compatibility_rows),
                "runtime_execution_authorized": False,
                "measured_abc_execution_authorized": False,
            }
        else:
            validate_package(repo_root)
            payload = {
                "status": ("P5_P6_SUCCESSOR_PREIMPLEMENTATION_RECONNAISSANCE_V1_VALID"),
                "decision": EXPECTED_REVIEW_MODEL.decision,
                "unresolved_compatibility_rows": 0,
                "next_gate": EXPECTED_REVIEW_MODEL.next_gate,
                "runtime_execution_authorized": False,
                "measured_abc_execution_authorized": False,
            }
        print(_canonical(payload))
        return 0
    except ReconnaissanceError as error:
        print(_canonical(error.envelope()), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

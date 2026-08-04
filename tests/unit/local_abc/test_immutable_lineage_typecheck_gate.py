from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from auragateway.local_abc import immutable_lineage_typecheck_gate as subject

ROOT = Path(__file__).resolve().parents[3]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _synthetic_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    source_relative = Path(
        "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v3.py"
    )
    config_bytes = b'[tool.mypy]\nstrict = true\nfiles = ["src", "tests"]\n'
    source_bytes = b"VALUE = 1\n"
    config_path = repo_root / "pyproject.toml"
    source_path = repo_root / source_relative
    policy_path = repo_root / subject.POLICY_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_bytes(config_bytes)
    source_path.write_bytes(source_bytes)

    policy_payload = {
        "accepted_source_mutation_permitted": False,
        "allowlisted_diagnostics": [
            {
                "diagnostic_id": "synthetic-assignment-v1",
                "error_code": "assignment",
                "line": 769,
                "message": (
                    "Incompatible types in assignment "
                    '(expression has type "Any | None", variable has type "str")'
                ),
                "occurrences": 1,
                "path": source_relative.as_posix(),
                "reason": ("Synthetic immutable source used for bounded policy unit tests."),
                "severity": "error",
                "source_sha256": _sha256(source_bytes),
            }
        ],
        "maximum_total_diagnostic_count": 1,
        "missing_allowlisted_diagnostics_permitted": False,
        "mypy_arguments": [
            "--no-incremental",
            "--no-error-summary",
            "--show-error-codes",
            "--no-color-output",
            "--no-pretty",
            "--config-file",
            "pyproject.toml",
        ],
        "mypy_config_path": "pyproject.toml",
        "mypy_config_sha256": _sha256(config_bytes),
        "mypy_distribution_version": "1.20.2",
        "network_access_permitted": False,
        "policy_id": "auragateway-immutable-lineage-typecheck-v1",
        "schema_version": "1.0.0",
        "status": "ACTIVE",
        "timeout_seconds": 300,
        "unexpected_diagnostics_permitted": False,
    }
    policy_path.write_text(
        json.dumps(
            policy_payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return repo_root


def _policy(repo_root: Path) -> subject.ImmutableLineageTypecheckPolicy:
    policy, _receipt = subject._load_policy(repo_root)
    return policy


def _expected_diagnostic() -> subject.ObservedDiagnostic:
    return subject.ObservedDiagnostic(
        path=("src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v3.py"),
        line=769,
        severity="error",
        message=(
            'Incompatible types in assignment (expression has type "Any | None", '
            'variable has type "str")'
        ),
        error_code="assignment",
    )


def test_parser_normalizes_windows_paths() -> None:
    output = (
        "src\\auragateway\\local_abc\\"
        "p3_p6_runtime_diagnostic_failure_acceptance_v3.py:769: error: "
        'Incompatible types in assignment (expression has type "Any | None", '
        'variable has type "str")  [assignment]\n'
    )

    observed = subject._parse_diagnostics(ROOT, output)

    assert observed == (_expected_diagnostic(),)


def test_exact_diagnostic_is_accepted(tmp_path: Path) -> None:
    policy = _policy(_synthetic_repo(tmp_path))

    subject._evaluate_diagnostics(policy, (_expected_diagnostic(),))


def test_unexpected_diagnostic_fails_closed(tmp_path: Path) -> None:
    policy = _policy(_synthetic_repo(tmp_path))
    unexpected = _expected_diagnostic().model_copy(update={"error_code": "arg-type"})

    with pytest.raises(
        subject.ImmutableLineageTypecheckError,
        match="diagnostics differ",
    ):
        subject._evaluate_diagnostics(policy, (unexpected,))


def test_missing_diagnostic_fails_closed(tmp_path: Path) -> None:
    policy = _policy(_synthetic_repo(tmp_path))

    with pytest.raises(
        subject.ImmutableLineageTypecheckError,
        match="diagnostics differ",
    ):
        subject._evaluate_diagnostics(policy, ())


def test_source_identity_drift_fails_closed(tmp_path: Path) -> None:
    repo_root = _synthetic_repo(tmp_path)
    source_path = repo_root / (
        "src/auragateway/local_abc/p3_p6_runtime_diagnostic_failure_acceptance_v3.py"
    )
    source_path.write_bytes(source_path.read_bytes() + b"# drift\n")

    with pytest.raises(
        subject.ImmutableLineageTypecheckError,
        match="changed identity",
    ):
        subject.validate_policy(repo_root)


def test_config_identity_drift_fails_closed(tmp_path: Path) -> None:
    repo_root = _synthetic_repo(tmp_path)
    config_path = repo_root / "pyproject.toml"
    config_path.write_bytes(config_path.read_bytes() + b"# drift\n")

    with pytest.raises(
        subject.ImmutableLineageTypecheckError,
        match="changed identity",
    ):
        subject.validate_policy(repo_root)


def test_mypy_version_drift_fails_closed() -> None:
    with pytest.raises(
        subject.ImmutableLineageTypecheckError,
        match="differs from the reviewed policy",
    ):
        subject._validate_mypy_version("1.20.2", "1.20.3")


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="exact repository authorities are unavailable in synthetic fixture",
)
def test_repository_policy_binds_exact_config_and_source() -> None:
    report = subject.validate_policy(ROOT)

    assert report.status == "IMMUTABLE_LINEAGE_TYPECHECK_POLICY_VALID"
    assert report.mypy_distribution_version == "1.20.2"
    assert report.mypy_config.sha256 == (
        "5387ea09341bde18d73518e28a236f65865918dd406fcb13824c0c8156a57103"
    )
    assert report.immutable_sources[0].sha256 == (
        "3e6b8e301be25d442cfde251d517c6287bce248df8248af68d62bd99b0e2da0e"
    )


@pytest.mark.skipif(
    os.environ.get("AURAGATEWAY_SYNTHETIC_FIXTURE") == "1",
    reason="full repository and mypy distribution are unavailable in synthetic fixture",
)
def test_repository_gate_accepts_only_exact_immutable_baseline() -> None:
    report = subject.run_gate(ROOT)

    assert report.status == "PASSED_WITH_EXACT_IMMUTABLE_LINEAGE_EXCEPTION"
    assert report.mypy_exit_code == 1
    assert report.observed_diagnostic_count == 1
    assert report.unexpected_diagnostic_count == 0
    assert report.missing_diagnostic_count == 0
    assert report.candidate_introduced_diagnostic_count == 0
    assert report.accepted_authority_bytes_changed is False
    assert report.network_access_performed is False

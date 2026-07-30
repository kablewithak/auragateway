"""Tests for explicit driver-link execution acceptance V1."""

from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

import pytest

import auragateway.local_abc.explicit_driver_link_probe_execution_acceptance_v1 as subject


def _fixture_repo(tmp_path: Path) -> Path:
    source_root = Path(__file__).resolve().parents[3]
    repo_root = tmp_path / "repo"

    for relative in (
        subject.LOG_PATH,
        subject.EVIDENCE_ZIP_PATH,
    ):
        source = source_root / relative
        target = repo_root / relative
        target.parent.mkdir(
            parents=True,
            exist_ok=True,
        )
        shutil.copyfile(source, target)

    return repo_root


def test_generate_validate_round_trip(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)

    generated = subject.generate(repo_root)
    validated = subject.validate(repo_root)

    assert generated == validated
    assert generated.status == ("EXPLICIT_DRIVER_LINK_PROBE_EXECUTION_ACCEPTANCE_V1_VALID")


def test_saved_version_and_archive_are_bound(
    tmp_path: Path,
) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.saved_version.saved_version_id == 339127349
    assert record.saved_version.saved_version_url.endswith("scriptVersionId=339127349")
    assert record.saved_version.evidence_archive.sha256 == subject.EVIDENCE_ZIP_SHA256


def test_explicit_real_driver_contract_is_accepted(
    tmp_path: Path,
) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.link_contract.link_succeeded is True
    assert record.link_contract.selected_link_library == subject.REAL_DRIVER_RESOLVED_PATH
    assert record.link_contract.runtime_library_path == subject.RUNTIME_DRIVER_PATH
    assert record.link_contract.cu_init_zero is True


def test_stub_and_environment_mutation_are_rejected(
    tmp_path: Path,
) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.link_contract.cuda_toolkit_stub_rejected is True
    assert record.link_contract.global_environment_mutation_absent is True
    assert record.global_environment_mutation_required is False
    assert record.cuda_toolkit_stub_required is False


def test_safety_and_next_gate_are_exact(
    tmp_path: Path,
) -> None:
    record = subject.build_acceptance_record(_fixture_repo(tmp_path))

    assert record.safety.p2_performed is False
    assert record.safety.runtime_install_attempts == 0
    assert record.safety.kernel_compile_and_execution_attempts == 0
    assert record.safety.model_loads == 0
    assert record.safety.worker_starts == 0
    assert record.safety.model_requests == 0
    assert record.safety.network_requests == 0
    assert record.unchanged_probe_replay_authorized is False
    assert record.p0_p2_diagnostic_v2_implementation_authorized is True
    assert record.next_gate == ("design_and_implement_p0_p2_platform_diagnostic_v2")


def test_tampered_log_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.LOG_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.ExplicitDriverLinkAcceptanceError,
        match="identity drifted",
    ):
        subject.build_acceptance_record(repo_root)


def test_tampered_archive_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.EVIDENCE_ZIP_PATH
    path.write_bytes(path.read_bytes() + b"tampered")

    with pytest.raises(
        subject.ExplicitDriverLinkAcceptanceError,
        match="identity drifted",
    ):
        subject.build_acceptance_record(repo_root)


def test_manifest_semantic_drift_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    original_read = subject._read_bound_file

    def read_with_manifest_drift(
        fixture_root: Path,
        relative_path: Path,
        expected_sha256: str,
    ) -> bytes:
        payload = original_read(
            fixture_root,
            relative_path,
            expected_sha256,
        )
        if relative_path != subject.EVIDENCE_ZIP_PATH:
            return payload

        source = Path(tmp_path) / "source.zip"
        target = Path(tmp_path) / "drifted.zip"
        source.write_bytes(payload)

        with zipfile.ZipFile(source) as input_archive:
            members = {name: input_archive.read(name) for name in input_archive.namelist()}

        manifest = json.loads(members[subject.BUNDLE_MANIFEST_MEMBER])
        manifest["source_main_commit"] = "0" * 40
        members[subject.BUNDLE_MANIFEST_MEMBER] = json.dumps(
            manifest,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

        with zipfile.ZipFile(
            target,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as output_archive:
            for name, member_payload in members.items():
                output_archive.writestr(
                    name,
                    member_payload,
                )
        return target.read_bytes()

    monkeypatch.setattr(
        subject,
        "_read_bound_file",
        read_with_manifest_drift,
    )
    monkeypatch.setattr(
        subject,
        "EVIDENCE_ZIP_SHA256",
        subject._sha256_bytes(
            read_with_manifest_drift(
                repo_root,
                subject.EVIDENCE_ZIP_PATH,
                subject.EVIDENCE_ZIP_SHA256,
            )
        ),
    )

    with pytest.raises(
        subject.ExplicitDriverLinkAcceptanceError,
    ):
        subject.build_acceptance_record(repo_root)


def test_transient_authorization_is_rejected(
    tmp_path: Path,
) -> None:
    repo_root = _fixture_repo(tmp_path)
    path = repo_root / subject.AUTHORIZATION_PATH
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(
        subject.ExplicitDriverLinkAcceptanceError,
        match="authorization must remain absent",
    ):
        subject.build_acceptance_record(repo_root)

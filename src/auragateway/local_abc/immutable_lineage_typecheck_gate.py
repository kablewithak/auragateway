"""Validate mypy with one exact immutable-lineage diagnostic policy."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Final, Literal, Never, Self, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

POLICY_PATH: Final = Path("data/evals/typecheck/immutable-lineage-v1/policy.json")
_SHA256_PATTERN: Final = r"^[0-9a-f]{64}$"
_DIAGNOSTIC_PATTERN: Final = re.compile(
    r"^(?P<path>.+?):(?P<line>[0-9]+): "
    r"(?P<severity>error|note): (?P<message>.*?)"
    r"(?:  \[(?P<error_code>[^\]]+)\])?$"
)


class ImmutableLineageTypecheckError(RuntimeError):
    """Fail-closed typecheck policy or execution error."""

    def __init__(
        self,
        error_code: str,
        safe_message: str,
        *,
        path: str | None = None,
        details: tuple[str, ...] = (),
    ) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message
        self.path = path
        self.details = details

    def envelope(self) -> dict[str, object]:
        return {
            "error_code": self.error_code,
            "safe_message": self.safe_message,
            "path": self.path,
            "details": self.details,
        }


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_ARGUMENT_INVALID",
            "typecheck gate arguments are invalid",
            details=(message,),
        )


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_json(self) -> str:
        return json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )


class ArtifactReceipt(_StrictModel):
    path: str
    sha256: str = Field(pattern=_SHA256_PATTERN)
    size_bytes: int = Field(gt=0)


class AllowlistedDiagnostic(_StrictModel):
    diagnostic_id: str = Field(min_length=1)
    path: str
    source_sha256: str = Field(pattern=_SHA256_PATTERN)
    line: int = Field(gt=0)
    severity: Literal["error"]
    message: str = Field(min_length=1)
    error_code: str = Field(min_length=1)
    occurrences: Literal[1] = 1
    reason: str = Field(min_length=20)

    @model_validator(mode="after")
    def validate_path(self) -> Self:
        _validate_policy_relative_path(self.path)
        return self


class ImmutableLineageTypecheckPolicy(_StrictModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    policy_id: Literal["auragateway-immutable-lineage-typecheck-v1"]
    status: Literal["ACTIVE"]
    mypy_distribution_version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    mypy_config_path: Literal["pyproject.toml"]
    mypy_config_sha256: str = Field(pattern=_SHA256_PATTERN)
    mypy_arguments: tuple[str, ...]
    timeout_seconds: int = Field(ge=30, le=600)
    allowlisted_diagnostics: tuple[AllowlistedDiagnostic, ...]
    maximum_total_diagnostic_count: Literal[1] = 1
    unexpected_diagnostics_permitted: Literal[False] = False
    missing_allowlisted_diagnostics_permitted: Literal[False] = False
    accepted_source_mutation_permitted: Literal[False] = False
    network_access_permitted: Literal[False] = False

    @model_validator(mode="after")
    def validate_contract(self) -> Self:
        required_arguments = {
            "--no-incremental",
            "--no-error-summary",
            "--show-error-codes",
            "--no-color-output",
            "--no-pretty",
            "--config-file",
            "pyproject.toml",
        }
        observed_arguments = set(self.mypy_arguments)
        if not required_arguments.issubset(observed_arguments):
            raise ValueError("mypy argument contract is incomplete")
        if len(self.allowlisted_diagnostics) != 1:
            raise ValueError("exactly one immutable-lineage diagnostic is required")
        if sum(item.occurrences for item in self.allowlisted_diagnostics) != 1:
            raise ValueError("allowlisted diagnostic occurrence budget drifted")
        return self


class ObservedDiagnostic(_StrictModel):
    path: str
    line: int = Field(gt=0)
    severity: Literal["error", "note"]
    message: str
    error_code: str

    def signature(self) -> tuple[str, int, str, str, str]:
        return (
            self.path,
            self.line,
            self.severity,
            self.message,
            self.error_code,
        )


class PolicyValidationReport(_StrictModel):
    status: Literal["IMMUTABLE_LINEAGE_TYPECHECK_POLICY_VALID"]
    policy_id: str
    policy: ArtifactReceipt
    mypy_config: ArtifactReceipt
    immutable_sources: tuple[ArtifactReceipt, ...]
    mypy_distribution_version: str
    accepted_source_mutation_permitted: Literal[False] = False


class TypecheckGateReport(_StrictModel):
    status: Literal["PASSED_WITH_EXACT_IMMUTABLE_LINEAGE_EXCEPTION"]
    policy_id: str
    mypy_distribution_version: str
    mypy_exit_code: Literal[1]
    observed_diagnostic_count: Literal[1]
    allowlisted_diagnostic_count: Literal[1]
    unexpected_diagnostic_count: Literal[0]
    missing_diagnostic_count: Literal[0]
    candidate_introduced_diagnostic_count: Literal[0]
    accepted_authority_bytes_changed: Literal[False] = False
    network_access_performed: Literal[False] = False


def _validate_policy_relative_path(value: str) -> None:
    if "\\" in value:
        raise ValueError("policy paths must use forward slashes")
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise ValueError("policy path is unsafe")
    if path.as_posix() != value or value.startswith("./"):
        raise ValueError("policy path is not canonical")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _read_bytes(repo_root: Path, relative: Path) -> bytes:
    absolute = repo_root / relative
    if not absolute.is_file() or absolute.is_symlink():
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_FILE_MISSING",
            "a required typecheck policy file is missing or unsafe",
            path=relative.as_posix(),
        )
    return absolute.read_bytes()


def _receipt(repo_root: Path, relative: Path, expected_sha256: str) -> ArtifactReceipt:
    payload = _read_bytes(repo_root, relative)
    observed_sha256 = _sha256_bytes(payload)
    if observed_sha256 != expected_sha256:
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_IDENTITY_DRIFT",
            "a typecheck policy authority changed identity",
            path=relative.as_posix(),
            details=(
                f"expected_sha256={expected_sha256}",
                f"observed_sha256={observed_sha256}",
            ),
        )
    return ArtifactReceipt(
        path=relative.as_posix(),
        sha256=observed_sha256,
        size_bytes=len(payload),
    )


def _load_policy(repo_root: Path) -> tuple[ImmutableLineageTypecheckPolicy, ArtifactReceipt]:
    payload = _read_bytes(repo_root, POLICY_PATH)
    try:
        raw = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_POLICY_INVALID_JSON",
            "the immutable-lineage typecheck policy is not valid JSON",
            path=POLICY_PATH.as_posix(),
        ) from error
    if not isinstance(raw, dict):
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_POLICY_INVALID_ROOT",
            "the immutable-lineage typecheck policy must contain one object",
            path=POLICY_PATH.as_posix(),
        )
    try:
        policy = ImmutableLineageTypecheckPolicy.model_validate(cast(dict[str, object], raw))
    except ValidationError as error:
        details = tuple(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors(include_url=False, include_input=False)
        )
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_POLICY_VALIDATION_FAILED",
            "the immutable-lineage typecheck policy failed typed validation",
            path=POLICY_PATH.as_posix(),
            details=details,
        ) from error
    return (
        policy,
        ArtifactReceipt(
            path=POLICY_PATH.as_posix(),
            sha256=_sha256_bytes(payload),
            size_bytes=len(payload),
        ),
    )


def _installed_mypy_version() -> str:
    try:
        return importlib.metadata.version("mypy")
    except importlib.metadata.PackageNotFoundError as error:
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_MYPY_MISSING",
            "the mypy distribution is not installed",
        ) from error


def _validate_mypy_version(expected: str, observed: str) -> None:
    if observed != expected:
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_MYPY_VERSION_DRIFT",
            "the installed mypy version differs from the reviewed policy",
            details=(f"expected={expected}", f"observed={observed}"),
        )


def validate_policy(repo_root: Path) -> PolicyValidationReport:
    root = repo_root.resolve()
    policy, policy_receipt = _load_policy(root)
    config_receipt = _receipt(
        root,
        Path(policy.mypy_config_path),
        policy.mypy_config_sha256,
    )
    source_receipts = tuple(
        _receipt(root, Path(item.path), item.source_sha256)
        for item in policy.allowlisted_diagnostics
    )
    mypy_version = _installed_mypy_version()
    _validate_mypy_version(policy.mypy_distribution_version, mypy_version)
    return PolicyValidationReport(
        status="IMMUTABLE_LINEAGE_TYPECHECK_POLICY_VALID",
        policy_id=policy.policy_id,
        policy=policy_receipt,
        mypy_config=config_receipt,
        immutable_sources=source_receipts,
        mypy_distribution_version=mypy_version,
    )


def _normalize_observed_path(repo_root: Path, value: str) -> str:
    normalized = value.replace("\\", "/")
    windows_absolute = bool(re.match(r"^[A-Za-z]:/", normalized))
    if windows_absolute or normalized.startswith("/"):
        absolute = Path(value).resolve()
        try:
            normalized = absolute.relative_to(repo_root.resolve()).as_posix()
        except ValueError as error:
            raise ImmutableLineageTypecheckError(
                "IMMUTABLE_LINEAGE_TYPECHECK_DIAGNOSTIC_OUTSIDE_REPOSITORY",
                "mypy reported a diagnostic outside the repository",
                path=value,
            ) from error
    _validate_policy_relative_path(normalized)
    return normalized


def _parse_diagnostics(repo_root: Path, output: str) -> tuple[ObservedDiagnostic, ...]:
    diagnostics: list[ObservedDiagnostic] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = _DIAGNOSTIC_PATTERN.fullmatch(line)
        if match is None:
            raise ImmutableLineageTypecheckError(
                "IMMUTABLE_LINEAGE_TYPECHECK_OUTPUT_UNPARSABLE",
                "mypy emitted an unrecognized output line",
                details=(line,),
            )
        error_code = match.group("error_code") or ""
        diagnostics.append(
            ObservedDiagnostic(
                path=_normalize_observed_path(repo_root, match.group("path")),
                line=int(match.group("line")),
                severity=cast(Literal["error", "note"], match.group("severity")),
                message=match.group("message"),
                error_code=error_code,
            )
        )
    return tuple(diagnostics)


def _expected_signatures(
    policy: ImmutableLineageTypecheckPolicy,
) -> Counter[tuple[str, int, str, str, str]]:
    expected: Counter[tuple[str, int, str, str, str]] = Counter()
    for item in policy.allowlisted_diagnostics:
        signature = (
            item.path,
            item.line,
            item.severity,
            item.message,
            item.error_code,
        )
        expected[signature] += item.occurrences
    return expected


def _format_signature(signature: tuple[str, int, str, str, str]) -> str:
    path, line, severity, message, error_code = signature
    return f"{path}:{line}:{severity}:{message}:[{error_code}]"


def _evaluate_diagnostics(
    policy: ImmutableLineageTypecheckPolicy,
    observed: tuple[ObservedDiagnostic, ...],
) -> None:
    expected = _expected_signatures(policy)
    actual: Counter[tuple[str, int, str, str, str]] = Counter(item.signature() for item in observed)
    missing = expected - actual
    unexpected = actual - expected
    if len(observed) != policy.maximum_total_diagnostic_count or missing or unexpected:
        details: list[str] = [
            f"expected_total={policy.maximum_total_diagnostic_count}",
            f"observed_total={len(observed)}",
        ]
        details.extend(
            f"missing={count}x{_format_signature(signature)}"
            for signature, count in sorted(missing.items())
        )
        details.extend(
            f"unexpected={count}x{_format_signature(signature)}"
            for signature, count in sorted(unexpected.items())
        )
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_DIAGNOSTIC_DRIFT",
            "mypy diagnostics differ from the exact immutable-lineage policy",
            details=tuple(details),
        )


def run_gate(repo_root: Path) -> TypecheckGateReport:
    root = repo_root.resolve()
    policy, _policy_receipt = _load_policy(root)
    validate_policy(root)
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    with tempfile.TemporaryDirectory(prefix="auragateway-mypy-cache-") as cache_dir:
        command = [
            sys.executable,
            "-m",
            "mypy",
            *policy.mypy_arguments,
            "--cache-dir",
            cache_dir,
        ]
        try:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                command,
                cwd=root,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=environment,
                timeout=policy.timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise ImmutableLineageTypecheckError(
                "IMMUTABLE_LINEAGE_TYPECHECK_TIMEOUT",
                "mypy exceeded the governed typecheck timeout",
            ) from error
    if result.stderr.strip():
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_STDERR_UNEXPECTED",
            "mypy emitted unexpected stderr output",
            details=tuple(result.stderr.splitlines()),
        )
    if result.returncode != 1:
        raise ImmutableLineageTypecheckError(
            "IMMUTABLE_LINEAGE_TYPECHECK_EXIT_CODE_DRIFT",
            "mypy exit code differs from the exact immutable-lineage policy",
            details=("expected=1", f"observed={result.returncode}"),
        )
    observed = _parse_diagnostics(root, result.stdout)
    _evaluate_diagnostics(policy, observed)
    return TypecheckGateReport(
        status="PASSED_WITH_EXACT_IMMUTABLE_LINEAGE_EXCEPTION",
        policy_id=policy.policy_id,
        mypy_distribution_version=policy.mypy_distribution_version,
        mypy_exit_code=1,
        observed_diagnostic_count=1,
        allowlisted_diagnostic_count=1,
        unexpected_diagnostic_count=0,
        missing_diagnostic_count=0,
        candidate_introduced_diagnostic_count=0,
    )


def _parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="auragateway-immutable-lineage-typecheck")
    parser.add_argument(
        "command",
        choices=("validate-policy", "run"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        required=True,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        repo_root = cast(Path, arguments.repo_root)
        if arguments.command == "validate-policy":
            output: _StrictModel = validate_policy(repo_root)
        else:
            output = run_gate(repo_root)
        print(output.canonical_json())
        return 0
    except (
        ImmutableLineageTypecheckError,
        ValidationError,
        OSError,
        ValueError,
    ) as error:
        if isinstance(error, ImmutableLineageTypecheckError):
            payload = error.envelope()
        else:
            payload = {
                "error_code": "IMMUTABLE_LINEAGE_TYPECHECK_UNEXPECTED",
                "safe_message": str(error),
                "path": None,
                "details": (),
            }
        print(
            json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Disposition governed C4 NOT_QUALIFIED execution evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from typing import Final, Never

from pydantic import BaseModel, ConfigDict, Field, ValidationError

TRANSACTION_ID: Final = "70ef982013fd5ed97dcec8542fab075d3daa9a249ca80a11238e31926085c945"
SAVED_VERSION_ID: Final = 343536641
NEXT_GATE: Final = "ANALYZE_C4_NOT_QUALIFIED_OUTPUT_DIVERGENCE_BEFORE_NEW_EXECUTION_V1"
QUALIFICATION_ID: Final = "CANONICAL_SYNTHETIC_PREFIX_C4_BEHAVIORAL_QUALIFICATION_V1"
REQUEST_SHA: Final = "a888c17ed8e82360fdd46d0bb6833db9db2dc3fbbfb14d861f7063b271063788"
TOKEN_SHA: Final = "f009b149b0b8ccf08a423346e1736be81927095907b5221e070e59ffc6d87f4c"
PREFIX_SHA: Final = "f29af54ca46249fa63c7fd89da44ca375d64f183f8d463b3a43678318890dfb1"
RESPONSE_SHA: Final = "fb8cbfde0ffeff48c4773cee95c576f821b22f84b00dc1059410856502256aba"

VAULT: Final = Path("evidence_vault/local_abc/c4-canonical-prefix-qualification-not-qualified-v1")
CUSTODY_PATH: Final = VAULT / "custody_manifest_v1.json"
RECORD_PATH: Final = Path("benchmarks/local_abc") / (
    "auragateway_canonical_synthetic_prefix_c4_not_qualified_disposition_v1.json"
)
REVIEW_PATH: Final = Path("benchmarks/local_abc") / (
    "auragateway_canonical_synthetic_prefix_c4_not_qualified_disposition_v1_review.json"
)
SOURCE_PATH: Final = Path("src/auragateway/local_abc") / (
    "canonical_synthetic_prefix_c4_not_qualified_disposition_v1.py"
)
TEST_PATH: Final = Path("tests/unit/local_abc") / (
    "test_canonical_synthetic_prefix_c4_not_qualified_disposition_v1.py"
)
REPORT_PATH: Final = Path("docs/reports") / (
    "AuraGateway_Canonical_Synthetic_Prefix_C4_Not_Qualified_Disposition_V1.md"
)
RUNBOOK_PATH: Final = Path("docs/runbooks") / (
    "local_abc_canonical_synthetic_prefix_c4_not_qualified_disposition_v1.md"
)

CUSTODY: Final = (
    (
        "execution_authorization",
        VAULT / "lifecycle/execution_authorization_v1.json",
        "b4eca291432adb3a223f9c960f330ebc47f027ea004619fd4cbd3762b5a463ce",
    ),
    (
        "execution_artifact_manifest",
        VAULT / "lifecycle/execution_artifact_manifest_v1.json",
        "214fde88655e3c27fb335d3d26c38caf041d3b733344875a2c1a4552300ac9fc",
    ),
    (
        "platform_observation_receipt",
        VAULT / "lifecycle/platform_observation_receipt_v1.json",
        "d4ae89ccd88a02e7f7153baf0d487d6e1bba0f0296026b336764532c139b3a7e",
    ),
    (
        "authorization_terminal_receipt",
        VAULT / "lifecycle/authorization_terminal_receipt_v1.json",
        "e9898a7c7bb2b7622c7b01cc65b7e19fb6847c600e50b66ebbf0376495b01572",
    ),
    (
        "executed_notebook",
        VAULT / "kaggle/ag-c4-canonical-prefix-qual-v1-343536641.ipynb",
        "1c957bd787d878f8d87fca21da57998dc7fda022bf425d93e2b4631439f424a0",
    ),
    (
        "kaggle_terminal_log",
        VAULT / "kaggle/kaggle-terminal-343536641.log",
        "08d066c60a69241acebad5e86bc8d86105bee3f6b57e4871de8e16363187367d",
    ),
    (
        "outer_results_zip",
        VAULT / "kaggle/results-343536641.zip",
        "cad124c3901d6e62420db4872b0d83e310abad3e9b21fc3f796c97d4815e7a71",
    ),
    (
        "governed_evidence_zip",
        VAULT / "kaggle/evidence-v1-343536641.zip",
        "94ce021d8c208e5f4d4a39ac9f7c9e4fcb6db6fd25717b1eaa8d7772f6190ce4",
    ),
)
AUTHORITIES: Final = (
    (
        "runtime_payload",
        Path("src/auragateway/local_abc")
        / "canonical_synthetic_prefix_c4_behavioral_qualification_runtime_v1.py",
        "d2cc4f38823a0133345279ed0257bf726ebcf8190ef0985620e76815700d4e82",
    ),
    (
        "implementation_record",
        Path("benchmarks/local_abc")
        / (
            "auragateway_canonical_synthetic_prefix_c4_behavioral_"
            "qualification_implementation_v1.json"
        ),
        "7e5d102ed485279f0d8efd344529ec92b96e97a858b68652518a0472aeb9665a",
    ),
    (
        "implementation_review",
        Path("benchmarks/local_abc")
        / (
            "auragateway_canonical_synthetic_prefix_c4_behavioral_"
            "qualification_implementation_v1_review.json"
        ),
        "d5bbb90fbf171ad3c38e713b9aa71e2fd6dbc39254236933dcdf446e824d9452",
    ),
    (
        "authorization_design",
        Path("benchmarks/local_abc")
        / (
            "auragateway_canonical_synthetic_prefix_c4_single_use_"
            "execution_authorization_design_v1.json"
        ),
        "191f7886be32381a54c8efb81e34c9b6434cb1f7a612d8e61e0394b7a1271463",
    ),
    (
        "issuer_source",
        Path("src/auragateway/local_abc")
        / "canonical_synthetic_prefix_c4_single_use_execution_authorization_v1.py",
        "2c61881af7152ab1ed8bb95277b2920eac4045159ab53a7732d60524c341c458",
    ),
    (
        "generator_contract",
        Path("src/auragateway/local_abc/templates")
        / "canonical_synthetic_prefix_c4_transaction_bound_wrapper_v1.py.tmpl",
        "77130854715f25cbd2f30da1f7f24a943e064e8ece770588a13e5277f3249aff",
    ),
    (
        "qualification_request",
        Path("data/evals/benchmark/environment-qualification-v1")
        / "canonical_synthetic_prefix_c4_behavioral_qualification_v1_request.json",
        "0177ad9f81aac2f4f85ab7703cedb3f17a54cab4f47c414a31691a6e21e2a884",
    ),
    (
        "reusable_prefix_receipt",
        Path("benchmarks/local_abc/evidence/canonical_synthetic_prefix_corpus_design_v1")
        / "canonical_synthetic_prefix_reusable_prefix_identity_v1.json",
        "e6ae9dfac5653416ae02d5a8c649faa2b19a3a42529de2b1822a584335933835",
    ),
)
INNER_MEMBERS: Final = frozenset(
    {
        "runtime_source_identity_report_v1.json",
        "runtime_install_report_v1.json",
        "runtime_environment_report_v1.json",
        "runtime_import_closure_report_v1.json",
        "c4_runtime_ready_v1.json",
        "pre_request_token_identity_journal_v1.json",
        "c4_request_results_v1.json",
        "c4_decision_v1.json",
        "worker_teardown_report_v1.json",
        "scratch_cleanup_report_v1.json",
        "failure_report_v1.json",
        "c4_summary_v1.json",
        "human_report_v1.md",
        "bundle_manifest_v1.json",
    }
)


class DispositionError(RuntimeError):
    def __init__(self, code: str, message: str, path: str | None = None) -> None:
        super().__init__(message)
        self.code, self.message, self.path = code, message, path


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise DispositionError("C4_DISPOSITION_ARGUMENT_INVALID", message)


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Receipt(FrozenModel):
    role: str
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    size_bytes: int = Field(gt=0)


class CustodyManifest(FrozenModel):
    schema_version: str = "1.0.0"
    manifest_id: str = "auragateway-canonical-synthetic-prefix-c4-not-qualified-evidence-custody-v1"
    transaction_id: str = TRANSACTION_ID
    saved_version_id: int = SAVED_VERSION_ID
    terminal_disposition: str = "CONSUMED"
    observed_c4_state: str = "NOT_QUALIFIED"
    members: tuple[Receipt, ...]


class DispositionRecord(FrozenModel):
    schema_version: str = "1.0.0"
    record_id: str = "auragateway-canonical-synthetic-prefix-c4-not-qualified-disposition-v1"
    status: str = "DISPOSITIONED_VALID_GOVERNED_C4_NOT_QUALIFIED_EXECUTION"
    transaction_id: str = TRANSACTION_ID
    saved_version_id: int = SAVED_VERSION_ID
    execution_valid: bool = True
    observed_c4_state: str = "NOT_QUALIFIED"
    observation_count: int = 3
    exact_object_count: int = 0
    required_exact_object_count: int = 3
    valid_json_count: int = 3
    finish_reason_stop_count: int = 3
    http_200_count: int = 3
    zero_cache_baseline_count: int = 3
    worker_identity_cardinality: int = 3
    identical_nonqualifying_response_identity: bool = True
    canonical_parsed_object_sha256: str = RESPONSE_SHA
    full_prompt_token_count: int = 899
    reusable_prefix_token_count: int = 880
    hidden_retries: int = 0
    external_network_requests: int = 0
    external_spend: int = 0
    teardown_passed: bool = True
    scratch_cleanup_passed: bool = True
    failure_report_not_applicable: bool = True
    raw_prompt_retained: bool = False
    raw_output_retained: bool = False
    p5_requalified: bool = False
    p6_requalified: bool = False
    final_abc_measured: bool = False
    production_readiness_established: bool = False
    new_execution_authorized: bool = False
    authorization_reusable: bool = False
    custody_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_zip_sha256: str = CUSTODY[-1][2]
    outer_results_zip_sha256: str = CUSTODY[-2][2]
    authorities: tuple[Receipt, ...]
    non_claims: tuple[str, ...]
    next_gate: str = NEXT_GATE


class DispositionReview(FrozenModel):
    schema_version: str = "1.0.0"
    review_id: str = "auragateway-canonical-synthetic-prefix-c4-not-qualified-disposition-v1-review"
    status: str = "APPROVED_GOVERNED_C4_NOT_QUALIFIED_DISPOSITION"
    record_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    custody_manifest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    test_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runbook_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    execution_valid: bool = True
    c4_qualified_claimed: bool = False
    root_cause_claimed: bool = False
    new_execution_authorized: bool = False
    next_gate: str = NEXT_GATE


def sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical(value: object) -> bytes:
    payload = value.model_dump(mode="json") if isinstance(value, BaseModel) else value
    encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return (encoded + "\n").encode()


def read(root: Path, path: Path) -> bytes:
    target = root / path
    if not target.is_file():
        raise DispositionError(
            "C4_DISPOSITION_REQUIRED_ARTIFACT_MISSING",
            "required artifact missing",
            path.as_posix(),
        )
    return target.read_bytes()


def require(root: Path, path: Path, expected: str) -> bytes:
    payload = read(root, path)
    actual = sha(payload)
    if actual != expected:
        raise DispositionError(
            "C4_DISPOSITION_IDENTITY_MISMATCH",
            f"expected {expected}; observed {actual}",
            path.as_posix(),
        )
    return payload


def as_object(payload: bytes, label: str) -> dict[str, object]:
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise DispositionError(
            "C4_DISPOSITION_JSON_ROOT_INVALID",
            "JSON root must be object",
            label,
        )
    return value


def expect(value: dict[str, object], expected: dict[str, object], label: str) -> None:
    for key, wanted in expected.items():
        if value.get(key) != wanted:
            raise DispositionError("C4_DISPOSITION_SEMANTIC_DRIFT", f"{label}.{key} drifted")


def receipt(root: Path, spec: tuple[str, Path, str]) -> Receipt:
    role, path, expected = spec
    payload = require(root, path, expected)
    return Receipt(role=role, path=path.as_posix(), sha256=expected, size_bytes=len(payload))


def zip_object(archive: zipfile.ZipFile, name: str) -> dict[str, object]:
    try:
        return as_object(archive.read(name), name)
    except KeyError as error:
        raise DispositionError(
            "C4_DISPOSITION_EVIDENCE_MEMBER_MISSING",
            "evidence member missing",
            name,
        ) from error


def validate_requests(payload: dict[str, object]) -> None:
    expect(
        payload,
        {
            "status": "COMPLETE",
            "scheduled_request_count": 3,
            "observed_request_count": 3,
        },
        "requests",
    )
    results = payload.get("results")
    if not isinstance(results, list) or len(results) != 3:
        raise DispositionError(
            "C4_DISPOSITION_REQUEST_COUNT_INVALID",
            "expected three request results",
        )
    workers: set[str] = set()
    responses: set[str] = set()
    common = {
        "http_status": 200,
        "finish_reason": "stop",
        "response_complete": True,
        "valid_json": True,
        "json_root_type": "object",
        "duplicate_key_detected": False,
        "markdown_fence_detected": False,
        "leading_non_whitespace_content_detected": False,
        "trailing_non_whitespace_content_detected": False,
        "exact_object": False,
        "probe_exact": False,
        "value_exact": False,
        "request_error": None,
        "transport_error": None,
        "zero_cache_baseline": True,
        "teardown_status": "PASSED",
        "raw_output_retained": False,
        "raw_prompt_retained": False,
        "prompt_tokens": 899,
        "token_count": 899,
        "token_sha256": TOKEN_SHA,
        "reusable_prefix_token_count": 880,
        "reusable_prefix_token_sha256": PREFIX_SHA,
        "payload_sha256": REQUEST_SHA,
        "canonical_parsed_object_sha256": RESPONSE_SHA,
        "response_sha256": RESPONSE_SHA,
    }
    metric_expected: dict[str, object] = {
        "cached_prompt_tokens": 0.0,
        "external_kv_transfer": 0.0,
        "local_cache_hit": 0.0,
        "local_compute": 899.0,
        "newly_computed_prefill_tokens": 899.0,
        "prefix_cache_hits": 0.0,
        "prefix_cache_queries": 899.0,
    }
    for ordinal, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            raise DispositionError(
                "C4_DISPOSITION_REQUEST_RESULT_INVALID",
                "request result must be object",
            )
        expect(
            item,
            common | {"request_ordinal": ordinal, "sequence_index": ordinal},
            f"request[{ordinal}]",
        )
        metric = item.get("metric_delta")
        if not isinstance(metric, dict):
            raise DispositionError("C4_DISPOSITION_METRIC_INVALID", "metric delta missing")
        expect(metric, metric_expected, f"metric[{ordinal}]")
        worker, response = item.get("worker_instance_id"), item.get("response_sha256")
        if not isinstance(worker, str) or not isinstance(response, str):
            raise DispositionError(
                "C4_DISPOSITION_REQUEST_IDENTITY_INVALID",
                "request identity invalid",
            )
        workers.add(worker)
        responses.add(response)
    if len(workers) != 3 or responses != {RESPONSE_SHA}:
        raise DispositionError(
            "C4_DISPOSITION_REQUEST_IDENTITY_DRIFT",
            "worker or response identity drifted",
        )


def validate_bundle(root: Path) -> None:
    evidence_path = CUSTODY[-1][1]
    require(root, evidence_path, CUSTODY[-1][2])
    with zipfile.ZipFile(root / evidence_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or frozenset(names) != INNER_MEMBERS:
            raise DispositionError(
                "C4_DISPOSITION_EVIDENCE_MEMBER_SET_DRIFT",
                "evidence member set drifted",
            )
        manifest = zip_object(archive, "bundle_manifest_v1.json")
        members = manifest.get("members")
        if not isinstance(members, list) or len(members) != 13:
            raise DispositionError(
                "C4_DISPOSITION_BUNDLE_MANIFEST_INVALID",
                "bundle manifest cardinality drifted",
            )
        for item in members:
            if not isinstance(item, dict) or not isinstance(item.get("path"), str):
                raise DispositionError(
                    "C4_DISPOSITION_BUNDLE_MANIFEST_INVALID",
                    "bundle manifest member invalid",
                )
            member = archive.read(item["path"])
            if sha(member) != item.get("sha256") or len(member) != item.get("size_bytes"):
                raise DispositionError(
                    "C4_DISPOSITION_BUNDLE_MEMBER_DRIFT",
                    f"bundle member drifted: {item['path']}",
                )
        expect(
            zip_object(archive, "c4_decision_v1.json"),
            {
                "status": "DECIDED",
                "qualification_id": QUALIFICATION_ID,
                "complete_behavioral_run": True,
                "observation_count": 3,
                "exact_object_count": 0,
                "required_exact_object_count": 3,
                "observed_terminal_state": "NOT_QUALIFIED",
                "fresh_worker_process_per_observation": True,
                "worker_identity_cardinality": 3,
                "qualification_accepted_by_repository": False,
                "p5_requalified": False,
                "p6_requalified": False,
            },
            "decision",
        )
        validate_requests(zip_object(archive, "c4_request_results_v1.json"))
        expect(
            zip_object(archive, "c4_summary_v1.json"),
            {
                "status": "QUALIFICATION_EXECUTION_COMPLETE",
                "completed_requests": 3,
                "scheduled_requests": 3,
                "model_loads": 3,
                "worker_starts": 3,
                "model_requests": 3,
                "hidden_retries": 0,
                "external_network_requests": 0,
                "external_spend": 0,
                "observed_terminal_state": "NOT_QUALIFIED",
                "teardown_status": "PASSED",
                "scratch_cleanup_status": "PASSED",
                "qualification_accepted_by_repository": False,
                "p5_requalified": False,
                "p6_requalified": False,
                "final_abc_measured": False,
                "production_readiness_established": False,
            },
            "summary",
        )
        expect(
            zip_object(archive, "failure_report_v1.json"),
            {"status": "NOT_APPLICABLE", "failure_class": None},
            "failure",
        )
        expect(
            zip_object(archive, "worker_teardown_report_v1.json"),
            {
                "status": "PASSED",
                "observed_teardown_count": 3,
                "all_completed_observations_torn_down": True,
            },
            "teardown",
        )
        expect(
            zip_object(archive, "scratch_cleanup_report_v1.json"),
            {
                "status": "PASSED",
                "scratch_exists_after": False,
            },
            "cleanup",
        )


def validate_outer(root: Path) -> None:
    outer_path = CUSTODY[-2][1]
    require(root, outer_path, CUSTODY[-2][2])
    with zipfile.ZipFile(root / outer_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise DispositionError(
                "C4_DISPOSITION_DUPLICATE_OUTER_MEMBER",
                "outer ZIP contains duplicate names",
            )
        inner = "ag-c4-canonical-prefix-qual-evidence-v1.zip"
        if inner not in names or sha(archive.read(inner)) != CUSTODY[-1][2]:
            raise DispositionError(
                "C4_DISPOSITION_INNER_EVIDENCE_DRIFT",
                "outer ZIP does not bind evidence ZIP",
            )
        if "canonical_synthetic_prefix_c4_transaction_bound_admission_v1.json" not in names:
            raise DispositionError(
                "C4_DISPOSITION_ADMISSION_MISSING",
                "transaction admission receipt missing",
            )


def validate_lifecycle(root: Path) -> None:
    terminal = as_object(require(root, CUSTODY[3][1], CUSTODY[3][2]), "terminal")
    expect(
        terminal,
        {
            "transaction_id": TRANSACTION_ID,
            "disposition": "CONSUMED",
            "execution_attempted": True,
            "observed_c4_state": "NOT_QUALIFIED",
            "saved_version_id": SAVED_VERSION_ID,
            "evidence_zip_sha256": CUSTODY[-1][2],
            "terminal_log_sha256": CUSTODY[5][2],
        },
        "terminal",
    )
    platform = as_object(require(root, CUSTODY[2][1], CUSTODY[2][2]), "platform")
    expect(
        platform,
        {
            "transaction_id": TRANSACTION_ID,
            "accelerator": "T4_X2",
            "allocated_gpu_count": 2,
            "internet_enabled": False,
        },
        "platform",
    )


def build_all(root: Path) -> tuple[bytes, bytes, bytes]:
    root = root.resolve()
    custody = CustodyManifest(members=tuple(receipt(root, spec) for spec in CUSTODY))
    custody_bytes = canonical(custody)
    validate_lifecycle(root)
    validate_bundle(root)
    validate_outer(root)
    authorities = tuple(receipt(root, spec) for spec in AUTHORITIES)
    non_claims = (
        "C4 qualification is not established.",
        "The canonical synthetic-prefix design is not proven invalid.",
        "Structural diversity is not proven sufficient for C4 qualification.",
        "Exact repetition is not established as a sole or root cause.",
        "Context length alone is not established as causal.",
        "A model, vLLM, or prefix-cache defect is not established.",
        "The exact semantic content of the non-qualifying object was not retained.",
        "P5 and P6 are not requalified.",
        "Final measured A/B/C was not performed.",
        "Production readiness is not established.",
        "No new execution or unchanged replay is authorized.",
    )
    record = DispositionRecord(
        custody_manifest_sha256=sha(custody_bytes),
        authorities=authorities,
        non_claims=non_claims,
    )
    record_bytes = canonical(record)
    review = DispositionReview(
        record_sha256=sha(record_bytes),
        custody_manifest_sha256=sha(custody_bytes),
        source_sha256=sha(read(root, SOURCE_PATH)),
        test_sha256=sha(read(root, TEST_PATH)),
        report_sha256=sha(read(root, REPORT_PATH)),
        runbook_sha256=sha(read(root, RUNBOOK_PATH)),
    )
    return custody_bytes, record_bytes, canonical(review)


def generate(root: Path) -> dict[str, object]:
    custody, record, review = build_all(root)
    for path, payload in ((CUSTODY_PATH, custody), (RECORD_PATH, record), (REVIEW_PATH, review)):
        target = root.resolve() / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return {
        "status": "C4_NOT_QUALIFIED_DISPOSITION_GENERATED",
        "record_sha256": sha(record),
        "review_sha256": sha(review),
        "custody_manifest_sha256": sha(custody),
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def validate(root: Path) -> dict[str, object]:
    custody, record, review = build_all(root)
    for path, expected in ((CUSTODY_PATH, custody), (RECORD_PATH, record), (REVIEW_PATH, review)):
        if read(root.resolve(), path) != expected:
            raise DispositionError(
                "C4_DISPOSITION_GENERATED_ARTIFACT_DRIFT",
                "generated artifact drifted",
                path.as_posix(),
            )
    return {
        "status": "C4_NOT_QUALIFIED_DISPOSITION_VALID",
        "execution_valid": True,
        "observed_c4_state": "NOT_QUALIFIED",
        "exact_object_count": 0,
        "valid_json_count": 3,
        "finish_reason_stop_count": 3,
        "new_execution_authorized": False,
        "next_gate": NEXT_GATE,
    }


def main(argv: list[str] | None = None) -> int:
    parser = Parser()
    parser.add_argument("command", choices=("generate", "validate"))
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            result = generate(Path(args.repo_root))
        else:
            result = validate(Path(args.repo_root))
    except (
        DispositionError,
        ValidationError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        zipfile.BadZipFile,
    ) as error:
        if isinstance(error, DispositionError):
            failure = error
        else:
            failure = DispositionError(
                "C4_DISPOSITION_VALIDATION_FAILED",
                str(error),
            )
        failure_payload = {
            "error_code": failure.code,
            "safe_message": failure.message,
            "path": failure.path,
        }
        print(
            json.dumps(failure_payload, separators=(",", ":"), sort_keys=True),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

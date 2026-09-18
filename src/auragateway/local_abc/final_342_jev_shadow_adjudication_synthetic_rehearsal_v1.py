"""Synthetic Jev shadow-adjudication rehearsal for Final-342.

This module proves the live provider boundary on synthetic evidence only.
It must not read protected Final-342 review exports, persisted human reviews,
or authoritative adjudications.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal, Never

from pydantic import BaseModel, ConfigDict, Field, model_validator

from auragateway.contracts.blinded_quality import (
    BlindedQualityRubric,
    ReviewVerdict,
    RubricCriterion,
)
from auragateway.contracts.episodes import EpisodeFailureLabel
from auragateway.local_abc import (
    final_342_jev_shadow_adjudication_contract_v1 as jev_contract,
)

RUBRIC_PATH = Path("data/evals/quality/blinded-v1/rubric.json")
LOCAL_EVIDENCE_ROOT = Path(".local/auragateway/jev-shadow-adjudication-v1/synthetic-rehearsal-v1")

SYNTHETIC_REVIEW_ITEM_ID: Literal[
    "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
] = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SYNTHETIC_EPISODE_ID: Literal["ep-func-999"] = "ep-func-999"

PostJson = Callable[[str, dict[str, str], bytes], dict[str, Any]]


class SyntheticRehearsalError(RuntimeError):
    """Expected synthetic-rehearsal failure with a stable error code."""

    def __init__(self, error_code: str, safe_message: str) -> None:
        super().__init__(safe_message)
        self.error_code = error_code
        self.safe_message = safe_message


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> Never:
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_ARGUMENT_ERROR",
            message,
        )


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SyntheticReviewView(FrozenModel):
    """Reviewer result visible to the shadow adjudicator."""

    criterion_scores: dict[RubricCriterion, int]
    failure_labels: tuple[EpisodeFailureLabel, ...]
    verdict: ReviewVerdict

    @model_validator(mode="after")
    def validate_scores(self) -> SyntheticReviewView:
        if set(self.criterion_scores) != set(RubricCriterion):
            raise ValueError("synthetic review view must score every rubric criterion")
        if any(score < 1 or score > 4 for score in self.criterion_scores.values()):
            raise ValueError("synthetic review score must be in [1,4]")
        if len(self.failure_labels) != len(set(self.failure_labels)):
            raise ValueError("synthetic review failure labels must be unique")
        return self


class SyntheticAdjudicationPacket(FrozenModel):
    """Exact synthetic state shape sent through the Jev provider boundary."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    purpose: Literal["synthetic_shadow_adjudication_rehearsal"] = (
        "synthetic_shadow_adjudication_rehearsal"
    )
    review_item_id: Literal["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"] = (
        SYNTHETIC_REVIEW_ITEM_ID
    )
    episode_id: Literal["ep-func-999"] = SYNTHETIC_EPISODE_ID
    adjudication_instruction: str = Field(min_length=30, max_length=1000)
    visible_case_evidence: dict[str, Any]
    review_a: SyntheticReviewView
    review_b: SyntheticReviewView
    disagreement_reasons: tuple[
        Literal[
            "verdict_mismatch",
            "material_score_delta",
            "failure_label_mismatch",
        ],
        ...,
    ] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_disagreement_reasons(self) -> SyntheticAdjudicationPacket:
        if len(self.disagreement_reasons) != len(set(self.disagreement_reasons)):
            raise ValueError("synthetic disagreement reasons must be unique")
        return self


class SyntheticRehearsalReceipt(FrozenModel):
    schema_version: Literal["1.0.0"] = "1.0.0"
    status: Literal["FINAL_342_JEV_SYNTHETIC_REHEARSAL_PASS"] = (
        "FINAL_342_JEV_SYNTHETIC_REHEARSAL_PASS"
    )
    requested_model: Literal["jev-1.13.0"] = jev_contract.JEV_MODEL_PIN
    resolved_model: Literal["jev-1.13.0"]
    question_count: int
    criterion_question_count: int
    failure_question_count: int
    input_tokens: int
    output_tokens: int
    request_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    response_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    protected_final_342_data_sent: Literal[False] = False
    human_adjudication_seen_by_jev: Literal[False] = False
    authoritative_adjudication_created: Literal[False] = False
    effect_claims_permitted: Literal[False] = False


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _load_rubric(repo_root: Path) -> BlindedQualityRubric:
    path = repo_root / RUBRIC_PATH
    if not path.is_file() or path.is_symlink():
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_RUBRIC_MISSING",
            "frozen quality rubric is missing or unsafe",
        )
    return BlindedQualityRubric.model_validate_json(path.read_text(encoding="utf-8"))


def build_synthetic_packet() -> SyntheticAdjudicationPacket:
    """Build a disagreement shaped like the dominant observed Final-342 class."""

    review_a_scores = {criterion: 3 for criterion in RubricCriterion}
    review_b_scores = {criterion: 3 for criterion in RubricCriterion}

    return SyntheticAdjudicationPacket(
        adjudication_instruction=(
            "Independently determine the final rubric scores and failure-label "
            "likelihoods from visible evidence. The two initial reviews are "
            "advisory evidence only; neither review is authoritative."
        ),
        visible_case_evidence={
            "conversation": [
                {
                    "turn": 1,
                    "user": (
                        "Our fictional Acme API token stopped working after "
                        "30 days. Which lifetime should we rely on?"
                    ),
                }
            ],
            "retrieved_sources": [
                {
                    "source_id": "src-current",
                    "status": "current",
                    "text": "Current Acme API tokens expire after 30 days.",
                },
                {
                    "source_id": "src-legacy",
                    "status": "superseded",
                    "text": "Legacy Acme API tokens expire after 365 days.",
                },
            ],
            "candidate_output": {
                "decision": "answer",
                "response": "Acme API tokens expire after 365 days.",
                "citation_ids": ["src-legacy"],
            },
        },
        review_a=SyntheticReviewView(
            criterion_scores=review_a_scores,
            failure_labels=(EpisodeFailureLabel.STALE_SOURCE_SELECTED,),
            verdict=ReviewVerdict.FAIL,
        ),
        review_b=SyntheticReviewView(
            criterion_scores=review_b_scores,
            failure_labels=(EpisodeFailureLabel.UNSUPPORTED_CLAIM,),
            verdict=ReviewVerdict.FAIL,
        ),
        disagreement_reasons=("failure_label_mismatch",),
    )


def build_request(repo_root: Path) -> jev_contract.JevShadowRequest:
    rubric = _load_rubric(repo_root)
    packet = build_synthetic_packet()
    safe_state = jev_contract.ReviewerSafeJevState(payload=packet.model_dump(mode="json"))
    return jev_contract.build_request(safe_state, rubric)


def _stdlib_post_json(
    url: str,
    headers: dict[str, str],
    body: bytes,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url=url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = response.read()
    except urllib.error.HTTPError as error:
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_HTTP_ERROR",
            f"Jev synthetic request returned HTTP {error.code}",
        ) from error
    except urllib.error.URLError as error:
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_TRANSPORT_ERROR",
            "Jev synthetic request failed at the transport boundary",
        ) from error

    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_RESPONSE_JSON_INVALID",
            "Jev synthetic response was not valid UTF-8 JSON",
        ) from error

    if not isinstance(value, dict):
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_RESPONSE_SHAPE_INVALID",
            "Jev synthetic response JSON root must be an object",
        )

    return value


def _persist_local_evidence(
    repo_root: Path,
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    receipt: SyntheticRehearsalReceipt,
) -> tuple[Path, Path, Path]:
    root = repo_root / LOCAL_EVIDENCE_ROOT
    root.mkdir(parents=True, exist_ok=True)

    request_bytes = _canonical_bytes(request_payload)
    response_bytes = _canonical_bytes(response_payload)
    receipt_bytes = _canonical_bytes(receipt.model_dump(mode="json"))

    request_path = root / f"request-{_sha256_bytes(request_bytes)}.json"
    response_path = root / f"response-{_sha256_bytes(response_bytes)}.json"
    receipt_path = root / f"receipt-{_sha256_bytes(receipt_bytes)}.json"

    for path, payload in (
        (request_path, request_bytes),
        (response_path, response_bytes),
        (receipt_path, receipt_bytes),
    ):
        if path.exists():
            if path.is_symlink() or not path.is_file() or path.read_bytes() != payload:
                raise SyntheticRehearsalError(
                    "FINAL_342_JEV_SYNTHETIC_LOCAL_EVIDENCE_CONFLICT",
                    "existing local synthetic evidence differs from expected bytes",
                )
        else:
            path.write_bytes(payload)

    return request_path, response_path, receipt_path


def run_synthetic_rehearsal(
    repo_root: Path,
    *,
    post_json: PostJson = _stdlib_post_json,
) -> SyntheticRehearsalReceipt:
    root = repo_root.resolve()

    api_key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    if not api_key:
        raise SyntheticRehearsalError(
            "FINAL_342_JEV_SYNTHETIC_API_KEY_MISSING",
            "TYPESAFE_API_KEY is missing from the current environment",
        )

    request = build_request(root)
    request_payload = request.model_dump(mode="json")
    request_bytes = _canonical_bytes(request_payload)

    response_payload = post_json(
        jev_contract.JEV_ENDPOINT,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        request_bytes,
    )

    response = jev_contract.JevShadowResponse.model_validate(response_payload)
    jev_contract.validate_response_against_request(request, response)
    jev_contract.project_response(request, response)

    response_bytes = _canonical_bytes(response_payload)

    receipt = SyntheticRehearsalReceipt(
        resolved_model=response.model,
        question_count=len(request.questions),
        criterion_question_count=len(RubricCriterion),
        failure_question_count=len(EpisodeFailureLabel),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        request_sha256=_sha256_bytes(request_bytes),
        response_sha256=_sha256_bytes(response_bytes),
    )

    _persist_local_evidence(
        root,
        request_payload,
        response_payload,
        receipt,
    )

    return receipt


def _build_parser() -> argparse.ArgumentParser:
    parser = _ArgumentParser(prog="final_342_jev_shadow_adjudication_synthetic_rehearsal_v1")
    parser.add_argument(
        "command",
        choices=("inspect", "run"),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = args.repo_root.resolve()

    if args.command == "inspect":
        request = build_request(root)
        result = {
            "status": "FINAL_342_JEV_SYNTHETIC_REQUEST_READY",
            "model": request.model,
            "question_count": len(request.questions),
            "criterion_question_count": len(RubricCriterion),
            "failure_question_count": len(EpisodeFailureLabel),
            "protected_final_342_data_sent": False,
            "human_adjudication_seen_by_jev": False,
            "effect_claims_permitted": False,
        }
        print(json.dumps(result, sort_keys=True))
        return 0

    receipt = run_synthetic_rehearsal(root)
    print(receipt.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

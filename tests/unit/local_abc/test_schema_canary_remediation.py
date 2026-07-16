from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from auragateway.local_abc.schema_canary_remediation import (
    CANONICAL_RENDERED_TOKEN_POLICY,
    RenderedTokenNormalizationError,
    RenderedTokenNormalizationFailureCode,
    TurnTwoCacheConclusion,
    build_rendered_token_identity,
    common_prefix_token_count,
    load_schema_canary_remediation_package,
    normalize_rendered_token_ids,
    schema_canary_scope_sha256,
)

ROOT = Path(__file__).resolve().parents[3]
AUDIT_PATH = ROOT / "benchmarks/local_abc/schema_quality_cache_canary_v1_evidence_audit.json"
AUTHORIZATION_PATH = (
    ROOT / "benchmarks/local_abc/schema_constrained_quality_canary_rerun_authorization_v2.json"
)
EXPECTED_POLICY_FINGERPRINT = "9b16866de747d67f41e4289d6f5fc9e7398da0054ee052dcc9371c5585954830"
EXPECTED_SCOPE_FINGERPRINT = "d1563d346138f10c4701492a2c1ddc7bd02bb0c5c937221b36c916361e348c64"
EXPECTED_AUDIT_FINGERPRINT = "45712ac7ab42c17bc949dc374dd1e4114ab408657b54d36509c0d241a5f74019"
EXPECTED_AUTHORIZATION_FINGERPRINT = (
    "7e8f9529cdf43118a09f5c6c9512f8729447a506b3a61cd303c6e09a652dbd66"
)


class FakeArray:
    def __init__(self, value: object) -> None:
        self._value = value

    def tolist(self) -> object:
        return self._value


class FakeBatchEncoding(dict[str, object]):
    pass


class FakeTokenizer:
    def __init__(self, tokenized_output: object) -> None:
        self.tokenized_output = tokenized_output
        self.rendered = "<chat>synthetic incident severity request</chat>"
        self.render_call: tuple[Sequence[Mapping[str, str]], bool, bool] | None = None
        self.tokenize_call: tuple[str, bool] | None = None

    def apply_chat_template(
        self,
        conversation: Sequence[Mapping[str, str]],
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> object:
        self.render_call = (conversation, tokenize, add_generation_prompt)
        return self.rendered

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool,
    ) -> object:
        self.tokenize_call = (text, add_special_tokens)
        return self.tokenized_output


@pytest.mark.parametrize(
    ("tokenized_output", "expected"),
    [
        ([1, 2, 3], (1, 2, 3)),
        ((1, 2, 3), (1, 2, 3)),
        ([[1, 2, 3]], (1, 2, 3)),
        (FakeArray([1, 2, 3]), (1, 2, 3)),
        (FakeArray([[1, 2, 3]]), (1, 2, 3)),
        (FakeBatchEncoding(input_ids=[1, 2, 3]), (1, 2, 3)),
        (FakeBatchEncoding(input_ids=FakeArray([[1, 2, 3]])), (1, 2, 3)),
    ],
)
def test_normalize_rendered_token_ids_accepts_supported_shapes(
    tokenized_output: object,
    expected: tuple[int, ...],
) -> None:
    assert normalize_rendered_token_ids(tokenized_output) == expected


@pytest.mark.parametrize(
    ("tokenized_output", "expected_code"),
    [
        ({"attention_mask": [1, 1]}, RenderedTokenNormalizationFailureCode.INPUT_IDS_MISSING),
        ([], RenderedTokenNormalizationFailureCode.INPUT_IDS_EMPTY),
        ([[]], RenderedTokenNormalizationFailureCode.INPUT_IDS_EMPTY),
        ([[1, 2], [3, 4]], RenderedTokenNormalizationFailureCode.INPUT_IDS_AMBIGUOUS_BATCH),
        ([[[1, 2]]], RenderedTokenNormalizationFailureCode.INPUT_IDS_AMBIGUOUS_BATCH),
        ([1, "2"], RenderedTokenNormalizationFailureCode.INPUT_ID_INVALID),
        ([1, True], RenderedTokenNormalizationFailureCode.INPUT_ID_INVALID),
        ([1, -2], RenderedTokenNormalizationFailureCode.INPUT_ID_INVALID),
        (3, RenderedTokenNormalizationFailureCode.TOKENIZED_OUTPUT_UNSUPPORTED),
    ],
)
def test_normalize_rendered_token_ids_fails_closed(
    tokenized_output: object,
    expected_code: RenderedTokenNormalizationFailureCode,
) -> None:
    with pytest.raises(RenderedTokenNormalizationError) as exc_info:
        normalize_rendered_token_ids(tokenized_output)

    assert exc_info.value.code is expected_code


def test_build_identity_renders_then_tokenizes_exact_text() -> None:
    tokenizer = FakeTokenizer(FakeBatchEncoding(input_ids=[list(range(282))]))
    messages = [{"role": "user", "content": "synthetic incident severity request"}]

    identity = build_rendered_token_identity(
        tokenizer=tokenizer,
        messages=messages,
    )

    assert identity.token_count == 282
    assert len(identity.token_ids) == 282
    assert tokenizer.render_call == (messages, False, True)
    assert tokenizer.tokenize_call == (tokenizer.rendered, False)
    assert identity.policy_sha256 == CANONICAL_RENDERED_TOKEN_POLICY.fingerprint()


def test_identity_serialization_excludes_raw_token_ids_and_rendered_text() -> None:
    tokenizer = FakeTokenizer({"input_ids": [[10, 11, 12]]})

    identity = build_rendered_token_identity(
        tokenizer=tokenizer,
        messages=[{"role": "user", "content": "synthetic"}],
    )
    payload = identity.model_dump(mode="json")
    serialized = identity.canonical_json()

    assert "token_ids" not in payload
    assert tokenizer.rendered not in serialized
    assert identity.rendered_text_sha256 in serialized
    assert identity.token_ids_sha256 in serialized


def test_common_prefix_uses_normalized_token_ids() -> None:
    assert common_prefix_token_count((1, 2, 3, 4), (1, 2, 9, 4)) == 2
    assert common_prefix_token_count((1, 2), (1, 2, 3)) == 2
    assert common_prefix_token_count((1,), (2,)) == 0


def test_package_loads_and_cross_binds() -> None:
    package = load_schema_canary_remediation_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )

    assert CANONICAL_RENDERED_TOKEN_POLICY.fingerprint() == EXPECTED_POLICY_FINGERPRINT
    assert schema_canary_scope_sha256() == EXPECTED_SCOPE_FINGERPRINT
    assert package.audit.fingerprint() == EXPECTED_AUDIT_FINGERPRINT
    assert package.authorization.fingerprint() == EXPECTED_AUTHORIZATION_FINGERPRINT
    assert package.authorization.failed_canary_audit_sha256 == package.audit.fingerprint()
    assert (
        package.authorization.consumed_authorization_sha256
        == package.audit.consumed_authorization_sha256
    )


def test_failed_audit_preserves_exact_diagnostic_boundary() -> None:
    package = load_schema_canary_remediation_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )
    audit = package.audit

    assert audit.local_evidence_filename.endswith("evidence-v1 (1).zip")
    assert audit.notebook_planned_prompt_tokens == 2
    assert audit.api_prompt_tokens == 282
    assert audit.vllm_prompt_tokens == 282
    assert audit.turn_one_quality_passed is True
    assert audit.turn_one_schema_passed is True
    assert audit.model_boundary_defect is False
    assert audit.turn_two_reached is False
    assert audit.turn_two_cache is TurnTwoCacheConclusion.NOT_OBSERVED


def test_consumed_authorization_cannot_be_reused() -> None:
    package = load_schema_canary_remediation_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )

    assert package.audit.consumed_authorization_reusable is False
    assert package.authorization.historical_notebook_rerun_permitted is False


def test_rerun_scope_is_exactly_preserved() -> None:
    package = load_schema_canary_remediation_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )
    authorization = package.authorization

    assert authorization.preserved_scope_sha256 == schema_canary_scope_sha256()
    assert authorization.selected_case_ids == (
        "incident-severity",
        "payment-reconciliation",
        "data-sharing-policy",
    )
    assert authorization.condition_id == "C"
    assert authorization.intended_route == ("worker_1", "worker_1")
    assert authorization.trajectory_count == 3
    assert authorization.request_count == 6
    assert authorization.turns_per_trajectory == 2
    assert authorization.full_worker_restart_before_each_trajectory is True


def test_rerun_preserves_quality_cache_and_abort_gates() -> None:
    package = load_schema_canary_remediation_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )
    authorization = package.authorization

    assert authorization.require_turn_one_cold is True
    assert authorization.require_positive_turn_two_cached_tokens is True
    assert authorization.require_planned_api_metric_prompt_token_match is True
    assert authorization.max_trajectory_failures == 0
    assert authorization.hidden_retries_permitted is False
    assert authorization.replacement_trajectories_permitted is False
    assert authorization.full_measured_rerun_authorized is False


def test_merge_binding_and_gpu_order_remain_enforced() -> None:
    package = load_schema_canary_remediation_package(
        audit_path=AUDIT_PATH,
        authorization_path=AUTHORIZATION_PATH,
    )
    authorization = package.authorization

    assert authorization.requires_merged_commit_binding is True
    assert authorization.merge_commit_binding_state == ("required_at_corrected_notebook_generation")
    assert authorization.corrected_notebook_generation_permitted_after_merge is True
    assert authorization.gpu_enablement_permitted_before_corrected_notebook is False


def test_json_artifacts_are_canonical_single_line_payloads() -> None:
    for path in (AUDIT_PATH, AUTHORIZATION_PATH):
        text = path.read_text(encoding="utf-8")
        assert text.endswith("\n")
        assert text.count("\n") == 1
        assert json.dumps(
            json.loads(text),
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ) == text.rstrip("\n")

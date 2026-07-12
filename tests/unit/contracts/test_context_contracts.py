from __future__ import annotations

from pydantic import ValidationError

from auragateway.contracts.context import (
    ContextDataClassification,
    StaticAnchor,
    StaticAnchorKind,
    StaticAnchorRegistry,
    VolatileAppendItem,
    VolatileAppendLog,
    VolatileItemKind,
)

HASH = "a" * 64


def _anchor(order: int, kind: StaticAnchorKind) -> StaticAnchor:
    return StaticAnchor(
        anchor_id=f"anchor-{order}",
        order=order,
        kind=kind,
        artifact_path=f"data/context/anchor-{order}.json",
        artifact_sha256=HASH,
        data_classification=ContextDataClassification.SYNTHETIC_PUBLIC,
    )


def _complete_registry() -> StaticAnchorRegistry:
    kinds = tuple(StaticAnchorKind)
    return StaticAnchorRegistry(
        anchors=tuple(_anchor(index, kind) for index, kind in enumerate(kinds))
    )


def test_static_registry_requires_all_anchor_kinds() -> None:
    registry = _complete_registry()
    assert len(registry.anchors) == len(StaticAnchorKind)


def test_static_registry_rejects_non_contiguous_order() -> None:
    anchors = list(_complete_registry().anchors)
    anchors[-1] = anchors[-1].model_copy(update={"order": 7})
    try:
        StaticAnchorRegistry(anchors=tuple(anchors))
    except ValidationError as exc:
        assert "anchor order must be contiguous" in str(exc)
    else:
        raise AssertionError("non-contiguous anchor order was accepted")


def test_static_anchor_rejects_public_trace_content() -> None:
    try:
        _anchor(0, StaticAnchorKind.BENCHMARK_POLICY).model_copy(
            update={"content_in_public_trace": True}
        )
        StaticAnchor(
            anchor_id="unsafe-anchor",
            order=0,
            kind=StaticAnchorKind.BENCHMARK_POLICY,
            artifact_path="data/context/unsafe.json",
            artifact_sha256=HASH,
            data_classification=ContextDataClassification.SYNTHETIC_PUBLIC,
            content_in_public_trace=True,
        )
    except ValidationError as exc:
        assert "must not be placed in public traces" in str(exc)
    else:
        raise AssertionError("public trace content was accepted")


def _item(sequence: int, kind: VolatileItemKind = VolatileItemKind.USER_TURN) -> VolatileAppendItem:
    return VolatileAppendItem(
        item_id=f"item-{sequence}",
        sequence=sequence,
        kind=kind,
        content_sha256=HASH,
        content_bytes=10,
        data_classification=ContextDataClassification.SYNTHETIC_PROTECTED,
    )


def test_volatile_log_append_returns_new_log() -> None:
    original = VolatileAppendLog(run_id="run-001")
    updated = original.append(_item(0))
    assert original.items == ()
    assert len(updated.items) == 1


def test_volatile_log_rejects_item_after_terminal_decision() -> None:
    try:
        VolatileAppendLog(
            run_id="run-001",
            items=(
                _item(0, VolatileItemKind.TERMINAL_DECISION),
                _item(1, VolatileItemKind.RUNTIME_STATE),
            ),
        )
    except ValidationError as exc:
        assert "no volatile items may follow a terminal decision" in str(exc)
    else:
        raise AssertionError("post-terminal append was accepted")


def test_volatile_item_rejects_personal_data() -> None:
    try:
        VolatileAppendItem(
            item_id="item-pii",
            sequence=0,
            kind=VolatileItemKind.USER_TURN,
            content_sha256=HASH,
            content_bytes=10,
            data_classification=ContextDataClassification.SYNTHETIC_PROTECTED,
            contains_personal_data=True,
        )
    except ValidationError as exc:
        assert "personal data is prohibited" in str(exc)
    else:
        raise AssertionError("personal data was accepted")

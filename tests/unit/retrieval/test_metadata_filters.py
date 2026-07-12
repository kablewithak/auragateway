from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from auragateway.contracts.chunking import CorpusChunk
from auragateway.contracts.dense_retrieval import DenseRetrievalConfiguration
from auragateway.contracts.retrieval import RetrievalConfiguration, RetrievalFilter, RetrievalQuery
from auragateway.contracts.retrieval_metadata import (
    InterfaceKind,
    OAuthGrantKind,
    RepresentationKind,
    RetrievalMetadataFilter,
    SourceLanguage,
    SourceRetrievalMetadata,
    SourceRetrievalMetadataRegistry,
)
from auragateway.retrieval.bm25 import BM25Index
from auragateway.retrieval.dense import DenseIndex


def _load_chunks(path: Path) -> tuple[CorpusChunk, ...]:
    return tuple(
        CorpusChunk.model_validate_json(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def _metadata() -> Mapping[str, SourceRetrievalMetadata]:
    registry = SourceRetrievalMetadataRegistry.model_validate_json(
        Path("data/retrieval/remediation-v1/source_metadata.json").read_text(encoding="utf-8")
    )
    return registry.by_source_id()


def test_bm25_language_filter_excludes_parallel_sdk_source() -> None:
    chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    index = BM25Index(
        chunks,
        RetrievalConfiguration(
            config_id="bm25-fixed-window-remediated-test",
            chunking_config_id="fixed-window-v1",
        ),
        _metadata(),
    )
    query = RetrievalQuery(
        query_id="python-sdk-filter",
        query_text="configure the Python SDK timeout",
        filters=RetrievalFilter(
            api_areas=("sdk",),
            metadata=RetrievalMetadataFilter(
                languages=(SourceLanguage.PYTHON,),
                interface_kinds=(InterfaceKind.SDK,),
            ),
        ),
    )

    result = index.search(query)

    assert result.hits
    assert {hit.source_id for hit in result.hits} == {"NR-SDK-016"}
    assert result.hits[0].retrieval_metadata is not None
    assert result.hits[0].retrieval_metadata.language is SourceLanguage.PYTHON


def test_bm25_oauth_grant_filter_excludes_refresh_guidance() -> None:
    chunks = _load_chunks(Path("data/chunking/fixed-window-v1/chunks.jsonl"))
    index = BM25Index(
        chunks,
        RetrievalConfiguration(
            config_id="bm25-oauth-remediated-test",
            chunking_config_id="fixed-window-v1",
        ),
        _metadata(),
    )
    query = RetrievalQuery(
        query_id="client-credentials-filter",
        query_text="client credentials access token refresh token",
        filters=RetrievalFilter(
            api_areas=("oauth",),
            metadata=RetrievalMetadataFilter(
                interface_kinds=(InterfaceKind.RAW_HTTP,),
                oauth_grants=(OAuthGrantKind.CLIENT_CREDENTIALS,),
            ),
        ),
    )

    result = index.search(query)

    assert result.hits
    assert {hit.source_id for hit in result.hits} == {"NR-OAUTH-003"}


def test_dense_interface_filter_prevents_pagination_displacement() -> None:
    chunks = _load_chunks(Path("data/chunking/section-aware-v1/chunks.jsonl"))
    index = DenseIndex(
        chunks,
        DenseRetrievalConfiguration(
            config_id="dense-section-remediated-test",
            chunking_config_id="section-aware-v1",
        ),
        _metadata(),
    )
    query = RetrievalQuery(
        query_id="raw-http-pagination-filter",
        query_text="raw HTTP next cursor request",
        filters=RetrievalFilter(
            api_areas=("pagination",),
            metadata=RetrievalMetadataFilter(
                interface_kinds=(InterfaceKind.RAW_HTTP,),
                representations=(RepresentationKind.HUMAN_GUIDE,),
            ),
        ),
    )

    result = index.search(query)

    assert result.hits
    assert {hit.source_id for hit in result.hits} == {"NR-PAGE-005"}

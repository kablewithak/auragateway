"""Deterministic in-memory BM25 retrieval over typed corpus chunks."""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from auragateway.contracts.chunking import CorpusChunk
from auragateway.contracts.retrieval import (
    BM25TermContribution,
    RetrievalConfiguration,
    RetrievalEvidenceHit,
    RetrievalEvidenceResult,
    RetrievalFilter,
    RetrievalHit,
    RetrievalQuery,
    RetrievalResult,
    StalePolicy,
)
from auragateway.contracts.retrieval_metadata import SourceRetrievalMetadata

_TERM_PATTERN = re.compile(r"[a-z0-9]+")


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _model_sha256(model: BaseModel) -> str:
    return _sha256_bytes(_canonical_json_bytes(model.model_dump(mode="json")))


def tokenize(text: str) -> tuple[str, ...]:
    """Normalize text into deterministic Unicode alphanumeric terms."""

    normalized = unicodedata.normalize("NFKC", text).casefold()
    return tuple(_TERM_PATTERN.findall(normalized))


@dataclass(frozen=True, slots=True)
class IndexedChunk:
    """One typed chunk with deterministic sparse statistics."""

    chunk: CorpusChunk
    terms: tuple[str, ...]
    term_frequencies: dict[str, int]
    retrieval_metadata: SourceRetrievalMetadata | None


@dataclass(frozen=True, slots=True)
class ScoredChunk:
    """Internal ranking candidate before rank assignment."""

    score: float
    indexed_chunk: IndexedChunk
    matched_terms: tuple[str, ...]
    contributions: tuple[BM25TermContribution, ...]


class BM25Index:
    """Deterministic BM25 index using global corpus IDF and typed filters."""

    def __init__(
        self,
        chunks: tuple[CorpusChunk, ...],
        configuration: RetrievalConfiguration,
        source_metadata: Mapping[str, SourceRetrievalMetadata] | None = None,
    ) -> None:
        if not chunks:
            raise ValueError("BM25Index requires at least one chunk")
        if any(chunk.config_id != configuration.chunking_config_id for chunk in chunks):
            raise ValueError("all chunks must match the retrieval chunking_config_id")

        self.configuration = configuration
        self.configuration_sha256 = _model_sha256(configuration)
        self.source_metadata = dict(source_metadata or {})
        self.indexed_chunks = tuple(self._index_chunk(chunk) for chunk in chunks)
        self.chunk_count = len(self.indexed_chunks)
        self.document_frequency = self._document_frequency(self.indexed_chunks)
        self.total_index_tokens = sum(len(item.terms) for item in self.indexed_chunks)
        self.average_chunk_length = self.total_index_tokens / len(self.indexed_chunks)
        self.vocabulary_size = len(self.document_frequency)
        self.source_document_count = len({chunk.source_id for chunk in chunks})

    def _index_chunk(self, chunk: CorpusChunk) -> IndexedChunk:
        terms = tokenize(chunk.content)
        if not terms:
            raise ValueError(f"chunk {chunk.chunk_id} produced no retrieval terms")
        return IndexedChunk(
            chunk=chunk,
            terms=terms,
            term_frequencies=dict(Counter(terms)),
            retrieval_metadata=self.source_metadata.get(chunk.source_id),
        )

    @staticmethod
    def _document_frequency(chunks: tuple[IndexedChunk, ...]) -> dict[str, int]:
        frequencies: Counter[str] = Counter()
        for item in chunks:
            frequencies.update(set(item.terms))
        return dict(frequencies)

    def search(self, query: RetrievalQuery) -> RetrievalResult:
        """Return positive-score hits with stable tie-breaking."""

        query_terms = tokenize(query.query_text)
        query_term_frequencies = Counter(query_terms)
        top_k = query.top_k or self.configuration.default_top_k
        eligible = tuple(
            item
            for item in self.indexed_chunks
            if matches_filter(item.chunk, query.filters, item.retrieval_metadata)
        )
        scored = tuple(
            candidate
            for item in eligible
            if (candidate := self._score_chunk(item, query_term_frequencies)) is not None
        )
        ordered = sorted(
            scored,
            key=lambda item: (
                -item.score,
                item.indexed_chunk.chunk.source_id,
                item.indexed_chunk.chunk.chunk_index,
                item.indexed_chunk.chunk.chunk_id,
            ),
        )
        hits = tuple(self._to_hit(rank, item) for rank, item in enumerate(ordered[:top_k], start=1))
        return RetrievalResult(
            query_id=query.query_id,
            query_sha256=_sha256_bytes(query.query_text.encode("utf-8")),
            retriever_config_id=self.configuration.config_id,
            retriever_config_sha256=self.configuration_sha256,
            chunking_config_id=self.configuration.chunking_config_id,
            top_k=top_k,
            filters=query.filters,
            candidate_count=len(eligible),
            positive_score_count=len(ordered),
            hits=hits,
        )

    def _score_chunk(
        self,
        item: IndexedChunk,
        query_term_frequencies: Counter[str],
    ) -> ScoredChunk | None:
        contributions: list[BM25TermContribution] = []
        chunk_length = len(item.terms)
        total_score = 0.0
        for term in sorted(query_term_frequencies):
            chunk_term_frequency = item.term_frequencies.get(term, 0)
            if chunk_term_frequency == 0:
                continue
            document_frequency = self.document_frequency[term]
            idf = math.log(
                1.0
                + (len(self.indexed_chunks) - document_frequency + 0.5) / (document_frequency + 0.5)
            )
            length_normalizer = self.configuration.k1 * (
                1.0
                - self.configuration.b
                + self.configuration.b * chunk_length / self.average_chunk_length
            )
            term_score = (
                query_term_frequencies[term]
                * idf
                * (chunk_term_frequency * (self.configuration.k1 + 1.0))
                / (chunk_term_frequency + length_normalizer)
            )
            if term_score <= 0.0:
                continue
            total_score += term_score
            contributions.append(
                BM25TermContribution(
                    term=term,
                    query_term_frequency=query_term_frequencies[term],
                    document_frequency=document_frequency,
                    chunk_term_frequency=chunk_term_frequency,
                    idf=round(idf, self.configuration.score_precision),
                    score=round(term_score, self.configuration.score_precision),
                )
            )

        rounded_score = round(total_score, self.configuration.score_precision)
        if rounded_score <= self.configuration.minimum_score or not contributions:
            return None
        return ScoredChunk(
            score=rounded_score,
            indexed_chunk=item,
            matched_terms=tuple(contribution.term for contribution in contributions),
            contributions=tuple(contributions),
        )

    @staticmethod
    def _to_hit(rank: int, item: ScoredChunk) -> RetrievalHit:
        chunk = item.indexed_chunk.chunk
        return RetrievalHit(
            rank=rank,
            score=item.score,
            chunk_id=chunk.chunk_id,
            source_id=chunk.source_id,
            document_path=chunk.document_path,
            source_version=chunk.source_version,
            source_status=chunk.source_status,
            api_area=chunk.api_area,
            is_stale=chunk.is_stale,
            completeness=chunk.completeness,
            version_sensitive_procedure=chunk.version_sensitive_procedure,
            retrieval_metadata=item.indexed_chunk.retrieval_metadata,
            chunk_index=chunk.chunk_index,
            parent_headings=chunk.parent_headings,
            content=chunk.content,
            content_sha256=chunk.content_sha256,
            matched_terms=item.matched_terms,
            term_contributions=item.contributions,
        )


def matches_filter(
    chunk: CorpusChunk,
    filters: RetrievalFilter,
    metadata: SourceRetrievalMetadata | None = None,
) -> bool:
    if filters.api_areas and chunk.api_area not in filters.api_areas:
        return False
    if filters.source_statuses and chunk.source_status not in filters.source_statuses:
        return False
    if filters.completeness and chunk.completeness not in filters.completeness:
        return False
    if filters.source_ids and chunk.source_id not in filters.source_ids:
        return False
    if filters.stale_policy is StalePolicy.EXCLUDE and chunk.is_stale:
        return False
    if filters.stale_policy is StalePolicy.ONLY and not chunk.is_stale:
        return False
    if filters.version_sensitive_only and not chunk.version_sensitive_procedure:
        return False
    constraints = filters.metadata
    if constraints is None:
        return True
    if metadata is None:
        return False
    if constraints.languages and metadata.language not in constraints.languages:
        return False
    if constraints.interface_kinds and metadata.interface_kind not in constraints.interface_kinds:
        return False
    if constraints.oauth_grants and metadata.oauth_grant not in constraints.oauth_grants:
        return False
    return not (
        constraints.representations and metadata.representation not in constraints.representations
    )


def to_evidence_result(result: RetrievalResult) -> RetrievalEvidenceResult:
    """Remove retrieval content while retaining deterministic ranking evidence."""

    hits = tuple(
        RetrievalEvidenceHit(
            rank=hit.rank,
            score=hit.score,
            chunk_id=hit.chunk_id,
            source_id=hit.source_id,
            document_path=hit.document_path,
            source_version=hit.source_version,
            source_status=hit.source_status,
            api_area=hit.api_area,
            is_stale=hit.is_stale,
            retrieval_metadata=hit.retrieval_metadata,
            chunk_index=hit.chunk_index,
            parent_headings=hit.parent_headings,
            matched_terms=hit.matched_terms,
        )
        for hit in result.hits
    )
    return RetrievalEvidenceResult(
        schema_version=result.schema_version,
        query_id=result.query_id,
        query_sha256=result.query_sha256,
        retriever_config_id=result.retriever_config_id,
        retriever_config_sha256=result.retriever_config_sha256,
        chunking_config_id=result.chunking_config_id,
        top_k=result.top_k,
        filters=result.filters,
        candidate_count=result.candidate_count,
        positive_score_count=result.positive_score_count,
        hits=hits,
    )

"""Deterministic local dense retrieval using hashed TF-IDF vectors."""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass

from pydantic import BaseModel

from auragateway.contracts.chunking import CorpusChunk
from auragateway.contracts.dense_retrieval import (
    DenseRetrievalConfiguration,
    DenseRetrievalEvidenceHit,
    DenseRetrievalEvidenceResult,
    DenseRetrievalHit,
    DenseRetrievalResult,
    DenseSimilarityEvidence,
)
from auragateway.contracts.retrieval import RetrievalQuery
from auragateway.contracts.retrieval_metadata import SourceRetrievalMetadata
from auragateway.retrieval.bm25 import matches_filter, tokenize

Vector = tuple[float, ...]


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _model_sha256(model: BaseModel) -> str:
    return _sha256_bytes(_canonical_json_bytes(model.model_dump(mode="json")))


def _ngrams(tokens: tuple[str, ...], minimum: int, maximum: int) -> tuple[str, ...]:
    features: list[str] = []
    for size in range(minimum, maximum + 1):
        if len(tokens) < size:
            continue
        features.extend(
            "\x1f".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)
        )
    return tuple(features)


def _feature_bucket(feature: str, dimension: int) -> tuple[int, float]:
    digest = hashlib.sha256(feature.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:8], byteorder="big", signed=False) % dimension
    sign = 1.0 if digest[8] & 1 == 0 else -1.0
    return bucket, sign


def _l2_normalize(values: list[float]) -> Vector:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return tuple(values)
    return tuple(value / norm for value in values)


def _dot_product(left: Vector, right: Vector) -> float:
    return sum(
        left_value * right_value for left_value, right_value in zip(left, right, strict=True)
    )


def _nonzero_count(vector: Vector) -> int:
    return sum(value != 0.0 for value in vector)


@dataclass(frozen=True, slots=True)
class DenseIndexedChunk:
    """One corpus chunk and its normalized dense vector."""

    chunk: CorpusChunk
    vector: Vector
    nonzero_dimensions: int
    retrieval_metadata: SourceRetrievalMetadata | None


@dataclass(frozen=True, slots=True)
class DenseScoredChunk:
    """Internal dense ranking candidate before rank assignment."""

    score: float
    indexed_chunk: DenseIndexedChunk
    shared_nonzero_dimensions: int


class DenseIndex:
    """Deterministic hashed TF-IDF dense index with cosine similarity."""

    def __init__(
        self,
        chunks: tuple[CorpusChunk, ...],
        configuration: DenseRetrievalConfiguration,
        source_metadata: Mapping[str, SourceRetrievalMetadata] | None = None,
    ) -> None:
        if not chunks:
            raise ValueError("DenseIndex requires at least one chunk")
        if any(chunk.config_id != configuration.chunking_config_id for chunk in chunks):
            raise ValueError("all chunks must match the dense chunking_config_id")

        self.configuration = configuration
        self.configuration_sha256 = _model_sha256(configuration)
        self.source_metadata = dict(source_metadata or {})
        self.chunk_count = len(chunks)
        chunk_features = tuple(self._features(chunk.content) for chunk in chunks)
        self.document_frequency = self._document_frequency(chunk_features)
        self.vocabulary_size = len(self.document_frequency)
        self.indexed_chunks = tuple(
            self._index_chunk(chunk, features)
            for chunk, features in zip(chunks, chunk_features, strict=True)
        )
        self.source_document_count = len({chunk.source_id for chunk in chunks})
        self.average_nonzero_dimensions = (
            sum(item.nonzero_dimensions for item in self.indexed_chunks) / self.chunk_count
        )

    def _features(self, text: str) -> tuple[str, ...]:
        tokens = tokenize(text)
        return _ngrams(
            tokens,
            self.configuration.minimum_ngram,
            self.configuration.maximum_ngram,
        )

    @staticmethod
    def _document_frequency(feature_sets: tuple[tuple[str, ...], ...]) -> dict[str, int]:
        frequencies: Counter[str] = Counter()
        for features in feature_sets:
            frequencies.update(set(features))
        if not frequencies:
            raise ValueError("dense index contains no features")
        return dict(frequencies)

    def _idf(self, feature: str) -> float:
        document_frequency = self.document_frequency[feature]
        return math.log((self.chunk_count + 1.0) / (document_frequency + 1.0)) + 1.0

    def _vectorize_features(self, features: tuple[str, ...]) -> Vector:
        term_frequencies = Counter(
            feature for feature in features if feature in self.document_frequency
        )
        values = [0.0] * self.configuration.vector_dimension
        for feature in sorted(term_frequencies):
            frequency = term_frequencies[feature]
            term_weight = (
                1.0 + math.log(frequency)
                if self.configuration.sublinear_term_frequency
                else float(frequency)
            )
            weight = term_weight * self._idf(feature)
            bucket, sign = _feature_bucket(feature, self.configuration.vector_dimension)
            values[bucket] += sign * weight
        return _l2_normalize(values)

    def _index_chunk(
        self,
        chunk: CorpusChunk,
        features: tuple[str, ...],
    ) -> DenseIndexedChunk:
        vector = self._vectorize_features(features)
        nonzero_dimensions = _nonzero_count(vector)
        if nonzero_dimensions == 0:
            raise ValueError(f"chunk {chunk.chunk_id} produced an empty dense vector")
        return DenseIndexedChunk(
            chunk=chunk,
            vector=vector,
            nonzero_dimensions=nonzero_dimensions,
            retrieval_metadata=self.source_metadata.get(chunk.source_id),
        )

    def search(self, query: RetrievalQuery) -> DenseRetrievalResult:
        """Return positive cosine-similarity hits with stable tie-breaking."""

        query_vector = self._vectorize_features(self._features(query.query_text))
        query_nonzero_dimensions = _nonzero_count(query_vector)
        top_k = query.top_k or self.configuration.default_top_k
        eligible = tuple(
            item
            for item in self.indexed_chunks
            if matches_filter(item.chunk, query.filters, item.retrieval_metadata)
        )
        scored = tuple(
            candidate
            for item in eligible
            if (
                candidate := self._score_chunk(
                    item,
                    query_vector,
                    query_nonzero_dimensions,
                )
            )
            is not None
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
        hits = tuple(
            self._to_hit(rank, item, query_nonzero_dimensions)
            for rank, item in enumerate(ordered[:top_k], start=1)
        )
        return DenseRetrievalResult(
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
        item: DenseIndexedChunk,
        query_vector: Vector,
        query_nonzero_dimensions: int,
    ) -> DenseScoredChunk | None:
        if query_nonzero_dimensions == 0:
            return None
        similarity = _dot_product(query_vector, item.vector)
        rounded_score = round(similarity, self.configuration.score_precision)
        if rounded_score <= self.configuration.minimum_similarity:
            return None
        shared_dimensions = sum(
            query_value != 0.0 and chunk_value != 0.0
            for query_value, chunk_value in zip(query_vector, item.vector, strict=True)
        )
        if shared_dimensions == 0:
            return None
        return DenseScoredChunk(
            score=rounded_score,
            indexed_chunk=item,
            shared_nonzero_dimensions=shared_dimensions,
        )

    @staticmethod
    def _to_hit(
        rank: int,
        item: DenseScoredChunk,
        query_nonzero_dimensions: int,
    ) -> DenseRetrievalHit:
        chunk = item.indexed_chunk.chunk
        evidence = DenseSimilarityEvidence(
            query_nonzero_dimensions=query_nonzero_dimensions,
            chunk_nonzero_dimensions=item.indexed_chunk.nonzero_dimensions,
            shared_nonzero_dimensions=item.shared_nonzero_dimensions,
            cosine_similarity=item.score,
        )
        return DenseRetrievalHit(
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
            similarity_evidence=evidence,
        )


def to_dense_evidence_result(result: DenseRetrievalResult) -> DenseRetrievalEvidenceResult:
    """Remove retrieved content while retaining dense ranking evidence."""

    hits = tuple(
        DenseRetrievalEvidenceHit(
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
            similarity_evidence=hit.similarity_evidence,
        )
        for hit in result.hits
    )
    return DenseRetrievalEvidenceResult(
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

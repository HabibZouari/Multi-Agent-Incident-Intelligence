"""Hybrid retrieval: dense vector similarity + BM25 keyword search, fused with Reciprocal Rank Fusion."""

from functools import lru_cache
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from backend.core.config import settings
from backend.core.logger import logger
from backend.models.db import IS_POSTGRES, DocumentModel, SessionLocal
from backend.rag.embeddings import HashingEmbedder, tokenize

ALL_SERVICES = "All Services"
RRF_K = 60
MIN_DENSE_SIMILARITY = 0.10


class HybridRetriever:
    """Searches the document store with two complementary rankers and fuses their rankings.

    * dense  - cosine similarity over hashed embeddings (pgvector ``<=>`` on PostgreSQL, NumPy on SQLite)
    * sparse - BM25 over tokenised chunk text
    * fusion - Reciprocal Rank Fusion, which needs no score calibration between the two rankers
    """

    def __init__(self, embedder: HashingEmbedder | None = None, candidate_pool: int = 25):
        self.embedder = embedder or HashingEmbedder(settings.embedding_dim)
        self.candidate_pool = candidate_pool
        self._corpus: list[dict[str, Any]] | None = None
        self._bm25: BM25Okapi | None = None
        self._matrix: np.ndarray | None = None

    # ------------------------------------------------------------------ indexing
    def get_embedding(self, text: str) -> list[float]:
        return self.embedder.embed(text)

    def refresh(self) -> None:
        """Drop the in-memory index; it is rebuilt lazily on the next search."""
        self._corpus = self._bm25 = self._matrix = None

    def _ensure_index(self) -> list[dict[str, Any]]:
        if self._corpus is not None:
            return self._corpus
        with SessionLocal() as session:
            rows = session.query(DocumentModel).order_by(DocumentModel.document_id, DocumentModel.chunk_id).all()
            self._corpus = [
                {
                    "document_id": r.document_id,
                    "filename": r.filename,
                    "document_type": r.document_type,
                    "service_name": r.service_name,
                    "chunk_id": r.chunk_id,
                    "content": r.content,
                    "_embedding": None if IS_POSTGRES else r.embedding,
                }
                for r in rows
            ]
        tokenized = [tokenize(c["content"]) for c in self._corpus]
        self._bm25 = BM25Okapi(tokenized) if any(tokenized) else None
        if not IS_POSTGRES and self._corpus:
            zero = [0.0] * self.embedder.dim
            self._matrix = np.array([c["_embedding"] or zero for c in self._corpus], dtype=np.float32)
        logger.info("Retrieval index built with %d chunks", len(self._corpus))
        return self._corpus

    # ------------------------------------------------------------------ rankers
    @staticmethod
    def _allowed(chunk: dict[str, Any], service_filter: str | None) -> bool:
        if not service_filter:
            return True
        return chunk["service_name"] in (service_filter, ALL_SERVICES)

    def _sparse_ranking(self, query: str, mask: list[bool]) -> list[tuple[int, float]]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(tokenize(query))
        ranked = sorted(((i, float(s)) for i, s in enumerate(scores) if mask[i] and s > 0), key=lambda x: -x[1])
        return ranked[: self.candidate_pool]

    def _dense_ranking(self, query_vec: list[float], mask: list[bool]) -> list[tuple[int, float]]:
        corpus = self._corpus or []
        if IS_POSTGRES:
            index = {(c["document_id"], c["chunk_id"]): i for i, c in enumerate(corpus)}
            with SessionLocal() as session:
                distance = DocumentModel.embedding.cosine_distance(query_vec)
                rows = (
                    session.query(DocumentModel.document_id, DocumentModel.chunk_id, distance.label("d"))
                    .order_by(distance)
                    .limit(self.candidate_pool * 4)
                    .all()
                )
            ranked = [(index[(r.document_id, r.chunk_id)], 1.0 - float(r.d)) for r in rows]
        else:
            if self._matrix is None:
                return []
            sims = self._matrix @ np.array(query_vec, dtype=np.float32)
            ranked = [(i, float(s)) for i, s in enumerate(sims)]
        ranked = [(i, s) for i, s in ranked if mask[i] and s >= MIN_DENSE_SIMILARITY]
        ranked.sort(key=lambda x: -x[1])
        return ranked[: self.candidate_pool]

    # ------------------------------------------------------------------ public API
    def search(self, query: str, top_k: int = 5, service_filter: str | None = None) -> list[dict[str, Any]]:
        corpus = self._ensure_index()
        if not corpus or not query.strip():
            return []

        mask = [self._allowed(c, service_filter) for c in corpus]
        sparse = self._sparse_ranking(query, mask)
        dense = self._dense_ranking(self.get_embedding(query), mask)

        fused: dict[int, float] = {}
        for ranking in (sparse, dense):
            for rank, (idx, _) in enumerate(ranking, start=1):
                fused[idx] = fused.get(idx, 0.0) + 1.0 / (RRF_K + rank)
        sparse_scores, dense_scores = dict(sparse), dict(dense)

        max_possible = 2.0 / (RRF_K + 1)  # a chunk ranked first by both rankers
        results = []
        for idx, score in sorted(fused.items(), key=lambda x: -x[1])[:top_k]:
            chunk = corpus[idx]
            results.append(
                {
                    **{k: v for k, v in chunk.items() if not k.startswith("_")},
                    "score": round(score / max_possible, 4),
                    "bm25_score": round(sparse_scores.get(idx, 0.0), 4),
                    "vector_score": round(dense_scores.get(idx, 0.0), 4),
                    "source": f"{chunk['filename']} (Chunk {chunk['chunk_id']})",
                }
            )
        return results


@lru_cache
def get_retriever() -> HybridRetriever:
    """Process-wide retriever so the index is built once and shared by the API, agents and MCP server."""
    return HybridRetriever()


if __name__ == "__main__":
    for hit in get_retriever().search("authentication timeout error", top_k=3):
        print(f"[{hit['score']:.3f}] {hit['source']}: {hit['content'][:90]!r}")

from typing import Any

from backend.core.logger import logger
from backend.rag.retrieval import HybridRetriever, get_retriever


class KnowledgeAgent:
    """Retrieves runbook / documentation chunks with hybrid (vector + BM25) search."""

    def __init__(self, retriever: HybridRetriever | None = None):
        self.retriever = retriever or get_retriever()

    def search_docs(self, query: str, top_k: int = 3, service_filter: str | None = None) -> list[dict[str, Any]]:
        logger.info("KnowledgeAgent searching documentation for: %s", query)
        docs = self.retriever.search(query=query, top_k=top_k, service_filter=service_filter)
        logger.info("KnowledgeAgent retrieved %d document chunks", len(docs))
        return docs

from typing import List, Dict, Any, Optional
from backend.rag.retrieval import HybridRetriever
from backend.core.logger import logger

class KnowledgeAgent:
    def __init__(self):
        self.retriever = HybridRetriever()

    def search_docs(self, query: str, top_k: int = 3, service_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        logger.info(f"KnowledgeAgent searching documentation for: {query}")
        docs = self.retriever.search(query=query, top_k=top_k, service_filter=service_filter)
        logger.info(f"KnowledgeAgent retrieved {len(docs)} document chunks")
        return docs

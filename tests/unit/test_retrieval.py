import pytest
from backend.rag.retrieval import HybridRetriever

def test_hybrid_retriever():
    retriever = HybridRetriever()
    results = retriever.search("authentication error", top_k=2)
    assert isinstance(results, list)
    if len(results) > 0:
        assert "content" in results[0]
        assert "score" in results[0]
        assert results[0]["score"] >= 0.0

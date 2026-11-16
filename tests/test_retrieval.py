import pytest

from backend.rag.retrieval import get_retriever


@pytest.fixture
def retriever():
    return get_retriever()


def test_topical_query_returns_the_right_runbook_first(retriever):
    hits = retriever.search("kafka consumer lag", top_k=3)
    assert hits[0]["filename"] == "kafka-guide-02.md"
    assert hits[0]["source"].startswith("kafka-guide-02.md (Chunk")


def test_result_shape_and_score_range(retriever):
    for hit in retriever.search("authentication login errors", top_k=5):
        assert {"document_id", "filename", "content", "score", "bm25_score", "vector_score", "source"} <= hit.keys()
        assert 0.0 < hit["score"] <= 1.0


def test_both_rankers_contribute(retriever):
    hit = retriever.search("redis eviction maxmemory", top_k=1)[0]
    assert hit["bm25_score"] > 0 and hit["vector_score"] > 0


def test_top_k_is_respected(retriever):
    assert len(retriever.search("incident", top_k=2)) <= 2


def test_service_filter_keeps_matching_and_global_documents(retriever):
    hits = retriever.search("troubleshooting procedures", top_k=10, service_filter="Kafka Event Bus")
    assert hits
    assert {h["service_name"] for h in hits} <= {"Kafka Event Bus", "All Services"}


@pytest.mark.parametrize("query", ["", "   ", "zzzz qqqq xxxx"])
def test_irrelevant_or_empty_query_returns_nothing(retriever, query):
    assert retriever.search(query) == []

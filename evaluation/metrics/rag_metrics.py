"""
RAG Evaluation Metrics (Context Precision, Recall, Faithfulness)
"""

def compute_retrieval_hit_rate(retrieved_docs: list, ground_truth_docs: list) -> float:
    if not ground_truth_docs:
        return 0.0
    matches = sum(1 for doc in retrieved_docs if any(gt in doc.get("filename", "") for gt in ground_truth_docs))
    return 1.0 if matches > 0 else 0.0

def compute_context_precision(retrieved_docs: list, ground_truth_docs: list) -> float:
    if not retrieved_docs or not ground_truth_docs:
        return 0.0
    relevant = sum(1 for doc in retrieved_docs if any(gt in doc.get("filename", "") for gt in ground_truth_docs))
    return relevant / len(retrieved_docs)

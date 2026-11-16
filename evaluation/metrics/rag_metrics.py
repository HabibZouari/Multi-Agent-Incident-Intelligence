"""Retrieval metrics. A retrieved chunk is relevant when its filename is in the ground-truth set."""

from typing import Any


def _relevance(retrieved: list[dict[str, Any]], ground_truth: list[str]) -> list[bool]:
    truth = set(ground_truth)
    return [doc.get("filename") in truth for doc in retrieved]


def hit_rate(retrieved: list[dict[str, Any]], ground_truth: list[str]) -> float:
    """1.0 if at least one retrieved chunk comes from a ground-truth document."""
    return 1.0 if any(_relevance(retrieved, ground_truth)) else 0.0


def context_precision(retrieved: list[dict[str, Any]], ground_truth: list[str]) -> float:
    """Share of retrieved chunks that are relevant (precision@k)."""
    if not retrieved:
        return 0.0
    flags = _relevance(retrieved, ground_truth)
    return sum(flags) / len(flags)


def reciprocal_rank(retrieved: list[dict[str, Any]], ground_truth: list[str]) -> float:
    """1 / rank of the first relevant chunk, 0 if none was retrieved."""
    for rank, relevant in enumerate(_relevance(retrieved, ground_truth), start=1):
        if relevant:
            return 1.0 / rank
    return 0.0

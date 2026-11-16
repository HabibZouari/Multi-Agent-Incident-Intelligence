"""Deterministic, dependency-free text embeddings (feature hashing).

Tokens (unigrams + bigrams) are hashed into a fixed-size vector with a stable hash, weighted by
sub-linear term frequency and L2-normalised. Unlike Python's built-in ``hash`` the result is identical
across processes, so vectors stored at ingestion time are comparable with query vectors later.

This is a lexical-overlap embedding: it is fast, offline and reproducible, and is paired with BM25 in
``HybridRetriever``. A neural embedding model can be plugged in by implementing the same ``embed`` API.
"""

import hashlib
import math
import re
from collections import Counter

import numpy as np

STOPWORDS = frozenset(
    "a an and are as at be been by for from has have how i in is it its of on or our should that the "
    "their there this to was we were what when which who will with you your do does did can could us "
    "affecting about into over after before".split()
)

_WORD = re.compile(r"[a-z0-9]+")


def _normalise(token: str) -> str:
    """Very light plural stripping so 'deployments' matches 'deployment'."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumerics, drop stop-words, light-stem."""
    return [_normalise(t) for t in _WORD.findall(text.lower()) if t not in STOPWORDS]


def _bucket(feature: str, dim: int) -> tuple[int, float]:
    digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
    value = int.from_bytes(digest, "little")
    return value % dim, 1.0 if (value >> 63) & 1 else -1.0


class HashingEmbedder:
    def __init__(self, dim: int = 512):
        self.dim = dim

    def embed(self, text: str) -> list[float]:
        tokens = tokenize(text)
        features = Counter(tokens)
        features.update(f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False))

        vec = np.zeros(self.dim, dtype=np.float32)
        for feature, count in features.items():
            idx, sign = _bucket(feature, self.dim)
            vec[idx] += sign * (1.0 + math.log(count))

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec /= norm
        return vec.tolist()

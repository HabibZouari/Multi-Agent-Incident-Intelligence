import json
import os
import subprocess
import sys

import numpy as np

from backend.rag.embeddings import HashingEmbedder, tokenize

TEXT = "Kafka consumer lag spike on the orders topic"


def test_embedding_is_unit_norm_and_fixed_size():
    vec = HashingEmbedder(256).embed(TEXT)
    assert len(vec) == 256
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-5


def test_embedding_is_stable_across_processes():
    """Regression: the old implementation seeded RNG with hash(), which differs for every Python process."""
    code = (
        "import json;from backend.rag.embeddings import HashingEmbedder;"
        f"print(json.dumps(HashingEmbedder(64).embed({TEXT!r})))"
    )
    outputs = []
    for seed in ("1", "2"):
        env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": os.getcwd()}
        run = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True)
        outputs.append(json.loads(run.stdout))
    assert outputs[0] == outputs[1] == HashingEmbedder(64).embed(TEXT)


def test_related_text_is_closer_than_unrelated():
    embedder = HashingEmbedder(512)
    query = np.array(embedder.embed("kafka consumer lag"))
    related = np.array(embedder.embed("Kafka Consumer Lag Troubleshooting Guide"))
    unrelated = np.array(embedder.embed("SSL certificate renewal procedure"))
    assert query @ related > query @ unrelated


def test_tokenize_drops_stopwords_and_normalises_plurals():
    assert tokenize("The deployments of the services") == ["deployment", "service"]


def test_empty_text_gives_zero_vector():
    assert not any(HashingEmbedder(32).embed("the of and"))

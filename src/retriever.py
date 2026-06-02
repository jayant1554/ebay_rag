"""
retriever.py
Loads the FAISS vector index and retrieves top-k relevant chunks for a query.
"""

import os
import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

VECTORDB_PATH = os.path.join(os.path.dirname(__file__), "../vectordb")
CHUNKS_PATH   = os.path.join(os.path.dirname(__file__), "../chunks/chunks.json")
EMBED_MODEL   = "all-MiniLM-L6-v2"

_model = None
_index = None
_chunks = None


def _load_resources():
    global _model, _index, _chunks
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    if _index is None:
        _index = faiss.read_index(os.path.join(VECTORDB_PATH, "index.faiss"))
    if _chunks is None:
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            _chunks = json.load(f)


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Returns top_k most relevant chunks for the given query.
    Each item: {"id": int, "text": str, "score": float}
    """
    _load_resources()
    query_vec = _model.encode([query], normalize_embeddings=True).astype("float32")
    distances, indices = _index.search(query_vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        results.append({
            "id": int(idx),
            "text": _chunks[idx]["text"],
            "score": float(dist),
        })
    return results


def get_index_stats() -> dict:
    """Returns metadata about the loaded index."""
    _load_resources()
    return {
        "total_chunks": len(_chunks),
        "embedding_model": EMBED_MODEL,
        "index_type": "FAISS FlatIP (cosine similarity)",
    }

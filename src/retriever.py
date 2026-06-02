import os
import json
import logging
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from src.generator import Chunk  
import warnings
warnings.filterwarnings("ignore")

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
        index_path = os.path.join(VECTORDB_PATH, "index.faiss")
        if not os.path.exists(index_path):
            raise FileNotFoundError(f"FAISS index not found at {index_path}")
        _index = faiss.read_index(index_path)
    if _chunks is None:
        if not os.path.exists(CHUNKS_PATH):
            raise FileNotFoundError(f"Chunks file not found at {CHUNKS_PATH}")
        with open(CHUNKS_PATH, "r", encoding="utf-8") as f:
            _chunks = json.load(f)


def retrieve(query: str, top_k: int = 5, score_threshold: float = 0.0) -> list[Chunk]:
    if not query.strip():
        raise ValueError("query must not be empty")

    _load_resources()

    query_vec = _model.encode([query], normalize_embeddings=True).astype("float32")
    distances, indices = _index.search(query_vec, top_k)

    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        if dist < score_threshold:
            logger.debug("Skipping chunk %d with score %.4f (below threshold)", idx, dist)
            continue
        results.append(Chunk(
            text=_chunks[idx]["text"],
            source=_chunks[idx].get("source", ""), 
            score=float(dist),
        ))

    return results


def get_index_stats() -> dict:
    _load_resources()
    return {
        "total_chunks": len(_chunks),
        "index_vectors": _index.ntotal,
        "embedding_model": EMBED_MODEL,
        "index_type": "FAISS FlatIP (cosine similarity)",
    }
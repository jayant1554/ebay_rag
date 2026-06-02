from src.retriever import retrieve, get_index_stats
from src.generator import stream_answer
from typing import Generator


def rag_stream(
    query: str,
    provider: str = "deepseek",
    deepseek_api_key: str = "",
    ollama_model: str = "mistral",
    top_k: int = 5,
) -> tuple[list[dict], Generator[str, None, None]]:
    chunks = retrieve(query, top_k=top_k)
    token_gen = stream_answer(
        query=query,
        chunks=chunks,
        provider=provider,
        deepseek_api_key=deepseek_api_key,
        ollama_model=ollama_model,
    )
    return chunks, token_gen


def get_stats() -> dict:
    return get_index_stats()

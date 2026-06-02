from src.retriever import retrieve, get_index_stats
from src.generator import stream_answer, StreamConfig, Chunk
from typing import Generator, Any

SUPPORTED_PROVIDERS = {"deepseek", "ollama"}


def rag_stream(
    query: str,
    provider: str = "deepseek",
    deepseek_api_key: str | None = None,
    ollama_model: str = "mistral",
    top_k: int = 5,
) -> tuple[list[dict], Generator[str, None, None]]:

    if provider not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"provider must be one of {SUPPORTED_PROVIDERS}, got '{provider}'"
        )
    if provider == "deepseek" and not deepseek_api_key:
        raise ValueError("deepseek_api_key is required when provider='deepseek'")

    chunks: list[Chunk] = retrieve(query, top_k=top_k)
    config = StreamConfig(
        provider=provider,
        deepseek_api_key=deepseek_api_key or "",
        ollama_model=ollama_model,
    )
    sources = [
        {"id": i + 1, "text": c.text, "score": c.score}
        for i, c in enumerate(chunks)
    ]
    token_gen = stream_answer(query=query, chunks=chunks, config=config)
    return sources, token_gen

def get_stats() -> dict[str, Any]:
    return get_index_stats()
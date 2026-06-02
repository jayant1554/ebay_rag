"""
generator.py
Handles LLM generation with streaming support.
Supports: DeepSeek API, Ollama (local)
"""

import os
from openai import OpenAI
from typing import Generator

# ── Prompt Template ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant that answers questions strictly based on the provided context from the eBay User Agreement.

Rules:
- Answer ONLY using information present in the context below.
- If the answer is not in the context, say: "I couldn't find specific information about that in the eBay User Agreement."
- Be concise, accurate, and cite which part of the document supports your answer.
- Do not hallucinate or add external knowledge.
"""

def build_prompt(query: str, chunks: list[dict]) -> str:
    context = "\n\n---\n\n".join(
        [f"[Chunk {i+1}]:\n{c['text']}" for i, c in enumerate(chunks)]
    )
    return f"""Context from eBay User Agreement:
{context}

User Question: {query}

Answer based strictly on the context above:"""


# ── DeepSeek Streaming ────────────────────────────────────────────────────────

def stream_deepseek(query: str, chunks: list[dict], api_key: str) -> Generator[str, None, None]:
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": build_prompt(query, chunks)},
    ]
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        stream=True,
        temperature=0.1,
        max_tokens=1024,
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ── Ollama Streaming ──────────────────────────────────────────────────────────

def stream_ollama(query: str, chunks: list[dict], model: str = "mistral") -> Generator[str, None, None]:
    import requests, json

    prompt = build_prompt(query, chunks)
    payload = {
        "model": model,
        "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }
    with requests.post("http://localhost:11434/api/generate", json=payload, stream=True) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if line:
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break


# ── Unified stream interface ──────────────────────────────────────────────────

def stream_answer(
    query: str,
    chunks: list[dict],
    provider: str = "deepseek",       # "deepseek" | "ollama"
    deepseek_api_key: str = "",
    ollama_model: str = "mistral",
) -> Generator[str, None, None]:
    if provider == "deepseek":
        yield from stream_deepseek(query, chunks, deepseek_api_key)
    elif provider == "ollama":
        yield from stream_ollama(query, chunks, ollama_model)
    else:
        raise ValueError(f"Unknown provider: {provider}")

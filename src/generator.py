import json
import os
import time
from dataclasses import dataclass, field
from typing import Generator, Literal
import requests
from openai import APIStatusError, AuthenticationError, OpenAI

@dataclass
class Chunk:
    text: str
    source: str = ""
    score: float = 0.0

Provider = Literal["deepseek", "ollama"]

DEFAULT_SYSTEM_PROMPT = """"You are a helpful assistant called 'eBay UA Assistant', 
built by Jayant Bisht,  that answers questions strictly based on the provided context from the eBay User Agreement.

Rules:
-For greetings or small talk, respond briefly and friendly, then guide 
the user to ask about eBay policies.
- Answer ONLY using information present in the context below.
- If the answer is not in the context, say: "I couldn't find specific information about that in the eBay User Agreement.
- Be concise and accurate. Source passages are shown separately below the response.
- Do not hallucinate or add external knowledge.
"""
ABOUT = {
    "name": "eBay UA Assistant",
    "description": "Answers questions strictly based on the eBay User Agreement.",
    "model": "DeepSeek V4 Flash / Ollama",
    "built_by": "Jayant Bisht",
    "note": "Responses are limited to document context only — no external knowledge.",
}

def get_about() -> str:
    return (
        f"**{ABOUT['name']}**\n"
        f"{ABOUT['description']}\n"
        f"Powered by: {ABOUT['model']}\n"
        f"Built by: {ABOUT['built_by']}\n"
        f"Note: {ABOUT['note']}"
    )
# ── Prompt builder ───────────────────────────────────────────────────────────

def build_prompt(
    query: str,
    chunks: list[Chunk],
    max_chars: int = 12_000,
) -> str:
    """Build the user prompt, truncating chunks if they exceed max_chars."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if not chunks:
        raise ValueError("chunks must not be empty")

    parts: list[str] = []
    total = 0
    for i, chunk in enumerate(chunks):
        entry = f"[Chunk {i + 1}]:\n{chunk.text}"
        if total + len(entry) > max_chars:
            break
        parts.append(entry)
        total += len(entry)

    context = "\n\n---\n\n".join(parts)
    return (
        f"Context from eBay User Agreement:\n{context}\n\n"
        f"User Question: {query}\n\n"
        f"Answer based strictly on the context above:"
    )



def stream_deepseek(
    query: str,
    chunks: list[Chunk],
    api_key: str,
    model: str = "deepseek-v4-flash",
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    max_retries: int = 2,
) -> Generator[str, None, None]:
    if not api_key:
        raise ValueError("DeepSeek api_key is required")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": build_prompt(query, chunks)},
    ]

    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                temperature=0.2,
                max_tokens=1024,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
            return 

        except AuthenticationError as e:
            raise ValueError("Invalid DeepSeek API key") from e

        except APIStatusError as e:
            if attempt == max_retries:
                raise
            wait = 2 ** attempt
            time.sleep(wait)


def stream_ollama(
    query: str,
    chunks: list[Chunk],
    model: str = "mistral",
    base_url: str = "http://localhost:11434",
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    timeout: int = 120,
) -> Generator[str, None, None]:
    prompt = build_prompt(query, chunks)
    payload = {
        "model": model,
        "prompt": f"{system_prompt}\n\n{prompt}",
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 1024},
    }
    url = f"{base_url.rstrip('/')}/api/generate"

    try:
        with requests.post(url, json=payload, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break

    except requests.ConnectionError as e:
        raise ConnectionError(f"Could not reach Ollama at {base_url}. Is it running?") from e
    except requests.HTTPError as e:
        raise RuntimeError(f"Ollama returned HTTP {e.response.status_code}") from e



@dataclass
class StreamConfig:
    provider: Provider = "deepseek"
    deepseek_api_key: str = field(default_factory=lambda: os.getenv("DEEPSEEK_API_KEY", ""))
    deepseek_model: str = "deepseek-v4-flash"
    ollama_model: str = "mistral"
    ollama_base_url: str = "http://localhost:11434"
    system_prompt: str = DEFAULT_SYSTEM_PROMPT
    max_context_chars: int = 12_000


def stream_answer(
    query: str,
    chunks: list[Chunk],
    config: StreamConfig | None = None,
) -> Generator[str, None, None]:
    cfg = config or StreamConfig()

    if cfg.provider == "deepseek":
        yield from stream_deepseek(
            query, chunks,
            api_key=cfg.deepseek_api_key,
            model=cfg.deepseek_model,
            system_prompt=cfg.system_prompt,
        )
    elif cfg.provider == "ollama":
        yield from stream_ollama(
            query, chunks,
            model=cfg.ollama_model,
            base_url=cfg.ollama_base_url,
            system_prompt=cfg.system_prompt,
        )
    else:
        raise ValueError(f"Unknown provider: {cfg.provider!r}. Choose 'deepseek' or 'ollama'.")


import os
import re
import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
DATA_PATH    = "data/AI Training Document.pdf"
CHUNKS_DIR   = "chunks"
VECTORDB_DIR = "vectordb"
EMBED_MODEL  = "all-MiniLM-L6-v2"
CHUNK_SIZE   = 200        # target words per chunk
CHUNK_OVERLAP = 30        # overlap in words


# ── Text Extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(path: str) -> str:
    import pdfplumber
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text


def clean_text(text: str) -> str:
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    text = text.strip()
    return text


# ── Sentence-Aware Chunking ───────────────────────────────────────────────────

def split_into_sentences(text: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    sentences = split_into_sentences(text)
    chunks = []
    current_words = []
    current_count = 0

    for sentence in sentences:
        words = sentence.split()
        if current_count + len(words) > chunk_size and current_words:
            chunk_text = " ".join(current_words)
            chunks.append(chunk_text)
            # keep overlap
            overlap_words = current_words[-overlap:] if overlap else []
            current_words = overlap_words + words
            current_count = len(current_words)
        else:
            current_words.extend(words)
            current_count += len(words)

    if current_words:
        chunks.append(" ".join(current_words))

    return chunks


# ── Embedding + FAISS ─────────────────────────────────────────────────────────

def build_index(chunks: list[str]) -> None:
    print(f"Encoding {len(chunks)} chunks with {EMBED_MODEL}...")
    model = SentenceTransformer(EMBED_MODEL)
    embeddings = model.encode(chunks, show_progress_bar=True, normalize_embeddings=True)
    embeddings = np.array(embeddings, dtype="float32")

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)   # inner product = cosine sim (since normalized)
    index.add(embeddings)

    os.makedirs(VECTORDB_DIR, exist_ok=True)
    faiss.write_index(index, os.path.join(VECTORDB_DIR, "index.faiss"))
    print(f"FAISS index saved → {VECTORDB_DIR}/index.faiss")

    os.makedirs(CHUNKS_DIR, exist_ok=True)
    chunk_data = [{"id": i, "text": c} for i, c in enumerate(chunks)]
    with open(os.path.join(CHUNKS_DIR, "chunks.json"), "w", encoding="utf-8") as f:
        json.dump(chunk_data, f, indent=2, ensure_ascii=False)
    print(f"Chunks saved → {CHUNKS_DIR}/chunks.json")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== Preprocessing eBay User Agreement ===")
    print(f"Loading document: {DATA_PATH}")
    raw_text = extract_text_from_pdf(DATA_PATH)
    clean    = clean_text(raw_text)
    print(f"Total characters extracted: {len(clean):,}")

    chunks = chunk_text(clean)
    print(f"Total chunks created: {len(chunks)}")
    print(f"Avg chunk length: {sum(len(c.split()) for c in chunks) // len(chunks)} words")

    build_index(chunks)
    print("\n✅ Preprocessing complete! Run: streamlit run app.py")

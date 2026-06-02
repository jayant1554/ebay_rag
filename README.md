# 🛒 eBay User Agreement RAG Chatbot

An AI-powered chatbot that answers questions about the eBay User Agreement using a **Retrieval-Augmented Generation (RAG)** pipeline with real-time streaming responses.

> Built as part of the Amlgo Labs Junior AI Engineer Assignment.

---

## 🎥 Demo

> 📹 _[Insert GIF or YouTube link here after recording]_

---

## 🏗️ Architecture

```
User Query
    │
    ▼
[ Sentence Embedding ]  ←  all-MiniLM-L6-v2
    │
    ▼
[ FAISS Vector Search ]  ←  Top-K relevant chunks
    │
    ▼
[ Prompt Construction ]  ←  System prompt + context + query
    │
    ▼
[ LLM Generation ]  ←  DeepSeek API  or  Ollama (local)
    │
    ▼
[ Streaming Response ]  →  Streamlit UI (token-by-token)
```

**Components:**

| Module | File | Responsibility |
|---|---|---|
| Preprocessing | `preprocess.py` | PDF extraction, chunking, FAISS indexing |
| Retriever | `src/retriever.py` | Semantic search over vector DB |
| Generator | `src/generator.py` | LLM streaming (DeepSeek / Ollama) |
| Pipeline | `src/pipeline.py` | Combines retriever + generator |
| UI | `app.py` | Streamlit chatbot interface |

---

## ⚙️ Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/ebay-rag-chatbot.git
cd ebay-rag-chatbot
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Set up environment variables
```bash
cp .env.example .env
# Edit .env and add your DeepSeek API key
```

### 4. Add the document
Place `AI_Training_Document.pdf` (eBay User Agreement) inside the `/data` folder:
```
data/
└── AI_Training_Document.pdf
```

### 5. Run preprocessing (builds FAISS index)
```bash
python preprocess.py
```
This will:
- Extract and clean text from the PDF
- Split into sentence-aware chunks (~200 words each, 30-word overlap)
- Generate embeddings using `all-MiniLM-L6-v2`
- Save FAISS index to `/vectordb/index.faiss`
- Save chunks to `/chunks/chunks.json`

### 6. Launch the chatbot
```bash
streamlit run app.py
```

---

## 🤖 Model & Embedding Choices

### Embedding Model: `all-MiniLM-L6-v2`
- Lightweight (80MB), fast inference
- Strong semantic similarity performance on English text
- Ideal for legal/policy document retrieval

### LLM Options (switchable in sidebar)

| Provider | Model | Notes |
|---|---|---|
| **DeepSeek API** | `deepseek-chat` (V3) | Fast, accurate, free tier available |
| **Ollama (Local)** | `mistral`, `llama3`, `phi3`, `gemma2` | Fully offline, no API key needed |

### Vector Database: FAISS (`IndexFlatIP`)
- Inner product index (cosine similarity on normalized vectors)
- No server needed — stored as a local file
- Instant search across all chunks

---

## 💬 Sample Queries & Responses

### ✅ Success Cases

**Q: What happens if I don't pay for an item I won on eBay?**
> According to the agreement, failure to pay for items you've committed to buy is prohibited. eBay may limit, suspend, or terminate your account for non-payment, and the Unpaid Item policy will apply unless you have a valid reason such as the seller materially changing the item description after bidding.

**Q: Can eBay record my phone calls?**
> Yes. eBay may monitor or record telephone conversations without further notice for quality control, training purposes, or its own protection.

**Q: How do I dispute a charge from eBay?**
> Disputes must go through the Informal Dispute Resolution process first — you must submit a Notice of Dispute to DisputeNotice@eBay.com or by mail. If unresolved within 45 days, disputes proceed to binding arbitration through NAM.

### ❌ Failure / Limitation Cases

**Q: What is eBay's current seller fee percentage?**
> The chatbot responds that the agreement mentions fees exist and can change with 14 days' notice, but the exact percentage is not stated in the document — this is a known limitation since fee tables are on a separate page.

**Q: Who is the current CEO of eBay?**
> The model correctly states it cannot find this in the User Agreement, demonstrating grounding behavior.

---

## 🧠 Notes on Limitations & Hallucinations

- **Hallucination risk:** Low — the system prompt strictly instructs the model to answer only from context. If context is insufficient, it says so.
- **Chunking gaps:** Very long legal clauses (e.g., arbitration section) may be split mid-sentence. Overlap of 30 words mitigates this.
- **Numerical data:** Exact fee percentages, dates, and dollar amounts may not always be in retrieved chunks since they appear in tables/external links.
- **Ollama latency:** Local models on CPU can be slow (5–15s first token). DeepSeek API is significantly faster.
- **Multi-turn context:** Each query is independent; the chatbot does not maintain conversational memory across turns (by design, to stay grounded).

---

## 📁 Folder Structure

```
ebay-rag-chatbot/
├── data/                    # Source document
│   └── AI_Training_Document.pdf
├── chunks/                  # Processed text segments
│   └── chunks.json
├── vectordb/                # Saved FAISS index
│   └── index.faiss
├── notebooks/               # Preprocessing & evaluation
│   └── exploration.ipynb
├── src/                     # Core pipeline modules
│   ├── __init__.py
│   ├── retriever.py
│   ├── generator.py
│   └── pipeline.py
├── app.py                   # Streamlit chatbot
├── preprocess.py            # Run once to build index
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📄 License

This project was built as a technical assignment for Amlgo Labs.

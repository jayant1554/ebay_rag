"""
app.py  –  eBay User Agreement RAG Chatbot
Streamlit interface with real-time streaming, model switcher (DeepSeek / Ollama),
source chunk display, and sidebar stats.
"""

import os
import streamlit as st
from dotenv import load_dotenv
from src.pipeline import rag_stream, get_stats

load_dotenv()

# ── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="eBay Agreement Chatbot",
    page_icon="🛒",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    .main-title {
        font-size: 2rem; font-weight: 700;
        background: linear-gradient(135deg, #4f8ef7, #a78bfa);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .subtitle { color: #888; font-size: 0.9rem; margin-bottom: 1.5rem; }
    .source-box {
        background: #1e2130; border-left: 3px solid #4f8ef7;
        border-radius: 6px; padding: 0.8rem 1rem;
        margin-top: 0.5rem; font-size: 0.82rem; color: #aab;
    }
    .model-badge {
        display: inline-block; padding: 2px 10px;
        border-radius: 12px; font-size: 0.75rem; font-weight: 600;
        background: #1e3a5f; color: #4f8ef7; border: 1px solid #4f8ef7;
    }
    .chunk-count { color: #a78bfa; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Configuration")

    # Model switcher
    provider = st.radio(
        "🤖 Select Model Provider",
        options=["DeepSeek API", "Ollama (Local)"],
        index=0,
        help="Switch between cloud and local model",
    )

    if provider == "DeepSeek API":
        deepseek_key = st.text_input(
            "DeepSeek API Key",
            value=os.getenv("DEEPSEEK_API_KEY", ""),
            type="password",
            placeholder="sk-...",
        )
        ollama_model_name = ""
        model_display = "deepseek-chat"
    else:
        deepseek_key = ""
        ollama_model_name = st.selectbox(
            "Ollama Model",
            ["mistral", "llama3", "phi3", "gemma2"],
            index=0,
        )
        model_display = f"ollama/{ollama_model_name}"

    st.divider()

    # Index stats
    st.markdown("### 📊 Index Stats")
    try:
        stats = get_stats()
        st.markdown(f"**Chunks indexed:** <span class='chunk-count'>{stats['total_chunks']}</span>", unsafe_allow_html=True)
        st.markdown(f"**Embedding model:** `{stats['embedding_model']}`")
        st.markdown(f"**Index type:** `{stats['index_type']}`")
    except Exception:
        st.warning("⚠️ Index not found. Run `python preprocess.py` first.")

    st.divider()
    st.markdown(f"**Active model:** <span class='model-badge'>{model_display}</span>", unsafe_allow_html=True)

    top_k = st.slider("Top-K chunks to retrieve", min_value=3, max_value=10, value=5)

    st.divider()
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    show_sources = st.toggle("Show source chunks", value=True)

# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🛒 eBay User Agreement Chatbot</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ask anything about eBay\'s policies, fees, disputes, and more.</div>', unsafe_allow_html=True)

# Init chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and show_sources and msg.get("sources"):
            with st.expander("📄 Source Chunks Used"):
                for i, src in enumerate(msg["sources"]):
                    st.markdown(
                        f'<div class="source-box"><b>Chunk #{src["id"]} '
                        f'(score: {src["score"]:.3f})</b><br>{src["text"]}</div>',
                        unsafe_allow_html=True,
                    )

# Chat input
if prompt := st.chat_input("Ask about eBay policies, fees, disputes, returns..."):

    # Validate config
    if provider == "DeepSeek API" and not deepseek_key:
        st.error("Please enter your DeepSeek API key in the sidebar.")
        st.stop()

    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Stream assistant response
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        full_response = ""
        sources = []

        try:
            provider_key = "deepseek" if provider == "DeepSeek API" else "ollama"
            chunks, token_gen = rag_stream(
                query=prompt,
                provider=provider_key,
                deepseek_api_key=deepseek_key,
                ollama_model=ollama_model_name,
                top_k=top_k,
            )
            sources = chunks

            # Stream tokens
            for token in token_gen:
                full_response += token
                response_placeholder.markdown(full_response + "▌")

            response_placeholder.markdown(full_response)

            # Show sources
            if show_sources and sources:
                with st.expander("📄 Source Chunks Used"):
                    for i, src in enumerate(sources):
                        st.markdown(
                            f'<div class="source-box"><b>Chunk #{src["id"]} '
                            f'(score: {src["score"]:.3f})</b><br>{src["text"]}</div>',
                            unsafe_allow_html=True,
                        )

        except Exception as e:
            full_response = f"⚠️ Error: {str(e)}"
            response_placeholder.markdown(full_response)

    # Save to history
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "sources": sources,
    })

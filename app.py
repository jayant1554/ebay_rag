import os
import warnings
warnings.filterwarnings("ignore")
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

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
    div[data-testid="stButton"] > button {
        background: #1e2130 !important;
        border: 1px solid #2a2d3e !important;
        color: #a0a8c0 !important;
        border-radius: 8px !important;
        font-size: 0.82rem !important;
        width: 100%;
    }
    div[data-testid="stButton"] > button:hover {
        border-color: #4f8ef7 !important;
        color: #4f8ef7 !important;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚙️ Configuration")

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
        model_display = "deepseek-v4-flash"
    else:
        deepseek_key = ""
        ollama_model_name = st.selectbox(
            "Ollama Model",
            ["mistral", "llama3",  "qwen2.5:7b "],
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
        st.session_state.pop("pending_prompt", None)
        st.rerun()

    show_sources = st.toggle("Show source chunks", value=True)

    st.divider()
    st.markdown("""
    <div style="font-size:0.72em; color:#5a6080; text-align:center;">
        Built with FAISS · Streamlit<br>
        Document: eBay User Agreement
    </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="main-title">🛒 eBay User Agreement Chatbot</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Ask anything about eBay\'s policies, fees, disputes, and more.</div>', unsafe_allow_html=True)


if "messages" not in st.session_state:
    st.session_state.messages = []

if not st.session_state.messages:
    st.markdown("#### 💡 Try asking:")
    suggestions = [
        "What is the eBay Money Back Guarantee?",
        "How are disputes resolved on eBay?",
        "What fees do sellers pay on eBay?",
        "Can I opt out of the arbitration agreement?",
        "What happens if I sell prohibited items?",
        "How does international shipping work?",
    ]
    cols = st.columns(2)
    for i, suggestion in enumerate(suggestions):
        with cols[i % 2]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                st.session_state["pending_prompt"] = suggestion
                st.rerun()
    st.divider()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        REFUSAL_PHRASE = "I couldn't find specific information"
        if msg["role"] == "assistant" and show_sources and msg.get("sources") and REFUSAL_PHRASE not in msg["content"]:
            with st.expander("📄 Source Chunks Used"):
                for src in msg["sources"]:
                    st.markdown(
                        f'<div class="source-box"><b>Chunk #{src["id"]} '
                        f'(score: {src["score"]:.3f})</b><br>{src["text"]}</div>',
                        unsafe_allow_html=True,
                    )


prompt = st.session_state.pop("pending_prompt", None) or st.chat_input(
    "Ask about eBay policies, fees, disputes, returns..."
)

if prompt:
    if provider == "DeepSeek API" and not deepseek_key:
        st.error("Please enter your DeepSeek API key in the sidebar.")
        st.stop()


    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

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
            REFUSAL_PHRASE = "I couldn't find specific information"
            if show_sources and sources and REFUSAL_PHRASE not in full_response:
                with st.expander("📄 Source Chunks Used"):
                    for src in sources:
                        st.markdown(
                            f'<div class="source-box"><b>Chunk #{src["id"]} '
                            f'(score: {src["score"]:.3f})</b><br>{src["text"]}</div>',
                            unsafe_allow_html=True,
                        )

        except Exception as e:
            full_response = f"⚠️ Error: {str(e)}"
            response_placeholder.markdown(full_response)
    st.session_state.messages.append({
        "role": "assistant",
        "content": full_response,
        "sources": sources,
    })
    st.rerun()
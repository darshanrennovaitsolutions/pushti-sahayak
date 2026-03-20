"""
STEP 5 — STREAMLIT CHAT UI
============================
A beautiful chat interface for your Pushtimarg GPT.
No React needed — launches in 10 seconds!

Run:
    streamlit run 5_chat_ui.py

Then open:  http://localhost:8501
"""

import os
import sys
from pathlib import Path

# pip install streamlit
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title  ="Pushti Sahayak 🙏",
    page_icon   ="🪷",
    layout      ="centered",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
/* Saffron-gold Pushtimarg theme */
:root {
    --saffron : #FF8C00;
    --gold    : #FFD700;
    --maroon  : #800000;
    --cream   : #FFF8DC;
}

.main { background: linear-gradient(135deg, #FFF8DC 0%, #FFF3CD 100%); }

.stChatMessage[data-testid="stChatMessage"] {
    border-radius: 16px !important;
    margin-bottom: 8px;
}

.source-tag {
    display: inline-block;
    background: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 12px;
    padding: 2px 10px;
    font-size: 0.75rem;
    color: #856404;
    margin: 2px 3px;
}

.header-box {
    background: linear-gradient(135deg, #FF8C00, #FFD700);
    color: white;
    border-radius: 16px;
    padding: 20px 24px;
    text-align: center;
    margin-bottom: 20px;
    font-family: serif;
}
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────────────
st.markdown("""
<div class="header-box">
    <h2 style="margin:0; color:white; font-size:1.6rem">🪷 Pushti Sahayak</h2>
    <p style="margin:4px 0 0; opacity:0.9; font-size:0.95rem">
        पुष्टिमार्ग ज्ञान सहायक • Jai Shri Krishna 🙏
    </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar settings ─────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")

    ghar_options = [
        "All Ghars",
        "Giridharji (Nathdwara)",
        "Govindraiji (Kamvan)",
        "Balkrishnaji",
        "Gokulnathji",
        "Raghunathji",
        "Yadunathji",
        "Ghanshyamji (Kankroli)",
    ]

    selected_ghar = st.selectbox(
        "Filter by Ghar Pranalika",
        ghar_options,
        help="Filter answers to a specific Ghar's tradition",
    )

    language_pref = st.radio(
        "Preferred language",
        ["Auto-detect", "English", "Hindi (हिंदी)", "Gujarati (ગુજરાતી)"],
    )

    show_sources = st.toggle("Show source references", value=True)

    st.divider()

    if st.button("🔄 New Conversation", use_container_width=True):
        st.session_state.messages = []
        if "rag" in st.session_state:
            st.session_state.rag.reset_conversation()
        st.rerun()

    st.markdown("""
    **Sample questions:**
    - What is the meaning of Pushti?
    - Ashtayam seva ke 8 darshan kaunse hain?
    - Shri Vallabhacharya ji kaun the?
    - Shrinathji seva ni pranalika shu che?
    - What are the 84 Vaishnavas ki Varta?
    """)

    st.markdown("---")
    st.caption("Built with ❤️ for Pushtimarg Vaishnavs")


# ── Initialize RAG ───────────────────────────────────────────────────
@st.cache_resource
def load_rag():
    """Load RAG engine once, cache it across reruns."""
    try:
        from rag_engine import PushtimargRAG
        return PushtimargRAG(), None
    except Exception as e:
        return None, str(e)

rag, error = load_rag()

if error:
    st.error(f"⚠️ RAG engine error: {error}")
    st.info("Make sure you've run `python 1_ingest_data.py` and `python 2_create_embeddings.py` first!")
    st.stop()

# Store RAG in session state for conversation history
if "rag_instance" not in st.session_state:
    st.session_state.rag_instance = rag


# ── Chat history ──────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role"   : "assistant",
            "content": "Jai Shri Krishna! 🙏 I am Pushti Sahayak, your Pushtimarg knowledge assistant.\n\nYou can ask me about seva pranalika, philosophy, kirtans, festivals, 84/252 Varta, or any Pushtimarg topic. Feel free to ask in English, Hindi, or Gujarati!",
            "sources": [],
        }
    ]


# ── Render chat history ──────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🪷" if msg["role"] == "assistant" else "👤"):
        st.write(msg["content"])

        if show_sources and msg.get("sources"):
            st.markdown("📚 **Sources:**")
            tags = " ".join(
                f'<span class="source-tag">📖 {s["source"]} | {s["ghar"]} | {s["relevance"]:.0%}</span>'
                for s in msg["sources"]
            )
            st.markdown(tags, unsafe_allow_html=True)


# ── Chat input ───────────────────────────────────────────────────────
ghar_filter = None
if selected_ghar != "All Ghars":
    ghar_filter = selected_ghar.split(" ")[0]  # Extract "Giridharji" etc.

lang_hint = ""
if language_pref == "Hindi (हिंदी)":
    lang_hint = " (Please answer in Hindi)"
elif language_pref == "Gujarati (ગુજરાતી)":
    lang_hint = " (Please answer in Gujarati)"

if prompt := st.chat_input("Ask about Pushtimarg seva, philosophy, kirtan..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt, "sources": []})
    with st.chat_message("user", avatar="👤"):
        st.write(prompt)

    # Get RAG answer
    with st.chat_message("assistant", avatar="🪷"):
        with st.spinner("🙏 Searching Pushtimarg knowledge..."):
            try:
                result = st.session_state.rag_instance.ask(
                    question=prompt + lang_hint,
                    ghar_filter=ghar_filter,
                )
                answer  = result["answer"]
                sources = result["sources"]
            except Exception as e:
                answer  = f"Sorry, I encountered an error: {e}"
                sources = []

        st.write(answer)

        if show_sources and sources:
            st.markdown("📚 **Sources:**")
            tags = " ".join(
                f'<span class="source-tag">📖 {s["source"]} | {s["ghar"]} | {s["relevance"]:.0%}</span>'
                for s in sources
            )
            st.markdown(tags, unsafe_allow_html=True)

    st.session_state.messages.append({
        "role"   : "assistant",
        "content": answer,
        "sources": sources,
    })

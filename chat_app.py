"""
PUSHTI SAHAYAK — PUBLIC CHAT UI
=================================
The beautiful public-facing chat interface for Vaishnavs.
This is what your community members will use.

Run:
    streamlit run chat_app.py
"""

import sys
import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

st.set_page_config(
    page_title="Pushti Sahayak — Pushtimarg AI",
    page_icon="🪷",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

.stApp { background: #FFFDF7; }

/* Hero header */
.hero {
    background: linear-gradient(135deg, #7D0000 0%, #C0392B 50%, #E8660A 100%);
    border-radius: 20px;
    padding: 32px 28px;
    text-align: center;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero-lotus {
    position: absolute;
    font-size: 120px;
    opacity: 0.07;
    right: -20px;
    top: -30px;
    line-height: 1;
}
.hero h1 {
    font-family: 'Tiro Devanagari Hindi', serif;
    font-size: 1.8rem;
    color: white;
    margin: 0 0 4px;
    line-height: 1.3;
}
.hero p { color: rgba(255,255,255,0.82); margin: 0; font-size: 0.9rem; font-weight: 300; }

/* Chat messages */
[data-testid="stChatMessage"] {
    border-radius: 14px !important;
    border: 1px solid rgba(240,224,200,0.5);
    margin-bottom: 10px !important;
}

/* Source pills */
.source-pill {
    display: inline-block;
    background: #FFF3DC;
    border: 1px solid #F0E0C8;
    border-radius: 99px;
    padding: 3px 12px;
    font-size: 0.72rem;
    color: #7D4E07;
    margin: 2px 3px;
    font-weight: 500;
}

/* Ghar badge */
.ghar-badge {
    display: inline-block;
    background: #F0E0C8;
    border-radius: 6px;
    padding: 2px 8px;
    font-size: 0.72rem;
    color: #5C3317;
    font-weight: 500;
}

/* Suggestion chips */
.stButton > button {
    background: white !important;
    border: 1px solid #F0E0C8 !important;
    color: #5C3317 !important;
    border-radius: 99px !important;
    font-size: 0.82rem !important;
    padding: 4px 16px !important;
    font-weight: 400 !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    background: #FFF3DC !important;
    border-color: #E8660A !important;
    color: #7D0000 !important;
}

/* Chat input */
[data-testid="stChatInput"] textarea {
    border: 1.5px solid #F0E0C8 !important;
    border-radius: 14px !important;
    background: white !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #E8660A !important;
    box-shadow: 0 0 0 3px rgba(232,102,10,0.1) !important;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #FFF8ED !important;
}

/* Selectbox */
.stSelectbox [data-baseweb="select"] {
    border-radius: 10px !important;
}

/* Footer */
.footer {
    text-align: center;
    padding: 20px;
    font-size: 0.75rem;
    color: #B89870;
    margin-top: 16px;
}
</style>
""", unsafe_allow_html=True)


# ── Hero header ──────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-lotus">🪷</div>
    <h1>🪷 Pushti Sahayak</h1>
    <p>पुष्टिमार्ग ज्ञान सहायक • Pushtimarg Knowledge Assistant</p>
    <p style="margin-top:8px; font-size:0.78rem; opacity:0.65">
        Ask in English • हिंदी में पूछें • ગુજરાતીમાં પૂછો
    </p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🪷 Pushti Sahayak")
    st.markdown("Your Pushtimarg AI assistant")
    st.divider()

    ghar_options = {
        "All Ghars (Sarva)": None,
        "Giridharji — Nathdwara": "Giridharji",
        "Govindraiji — Kamvan": "Govindraiji",
        "Balkrishnaji": "Balkrishnaji",
        "Gokulnathji": "Gokulnathji",
        "Raghunathji": "Raghunathji",
        "Yadunathji": "Yadunathji",
        "Ghanshyamji — Kankroli": "Ghanshyamji",
    }
    selected_ghar_label = st.selectbox(
        "My Ghar Pranalika",
        list(ghar_options.keys()),
        help="Filter answers to your specific Ghar's tradition",
    )
    ghar_filter = ghar_options[selected_ghar_label]

    lang = st.radio(
        "Answer language",
        ["Auto (same as question)", "English", "Hindi", "Gujarati"],
    )

    show_sources = st.toggle("Show source references", True)
    st.divider()

    if st.button("🔄 New conversation", use_container_width=True):
        st.session_state.chat_history = []
        if "chat_rag" in st.session_state:
            st.session_state.chat_rag.reset_conversation()
        st.rerun()

    st.divider()
    st.markdown("""
    **About this tool:**
    Answers are sourced from authentic Pushtimarg granths, seva pranalika, Varta sahitya, and kirtan books.

    When in doubt, always consult your **Goswami Maharaj** or the original granth.
    """)
    st.markdown("""
    <div style="font-size:0.72rem; color:#B89870; text-align:center; margin-top:16px">
        Jai Shri Krishna 🙏
    </div>
    """, unsafe_allow_html=True)


# ── Load RAG ─────────────────────────────────────────────────────────
@st.cache_resource
def load_rag():
    try:
        from rag_engine import PushtimargRAG
        return PushtimargRAG(), None
    except Exception as e:
        return None, str(e)

rag, err = load_rag()

if err:
    st.error(f"⚠️ The AI database is not ready yet. Error: {err}")
    st.info("Ask your admin to run **Build AI** in the admin panel.")
    st.stop()

if "chat_rag" not in st.session_state:
    st.session_state.chat_rag = rag


# ── Suggestion chips ─────────────────────────────────────────────────
if "chat_history" not in st.session_state or not st.session_state.get("chat_history"):
    st.markdown(
        '<p style="text-align:center; color:#9C7E65; font-size:0.85rem; margin-bottom:10px">'
        'Try asking one of these:</p>',
        unsafe_allow_html=True
    )

    suggestions = [
        ("What is Pushtimarg?", "🌸"),
        ("Ashtayam seva ke 8 darshan", "🪔"),
        ("84 Vaishnavas ki Varta kya hai?", "📖"),
        ("Shrinathji ki seva kaun karta hai?", "🛕"),
        ("Pushti marg ma bhakti nu mahatva shu che?", "🙏"),
        ("Which granths did Vallabhacharyaji write?", "📜"),
    ]
    cols = st.columns(3)
    for i, (text, icon) in enumerate(suggestions):
        if cols[i % 3].button(f"{icon} {text}", key=f"sug_{i}"):
            st.session_state.pending = text


# ── Chat history ─────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Render history
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"], avatar="🪷" if msg["role"] == "assistant" else "👤"):
        st.write(msg["content"])
        if show_sources and msg.get("sources"):
            pills = " ".join(
                f'<span class="source-pill">📖 {s["source"][:28]} · {s["relevance"]:.0%}</span>'
                for s in msg["sources"]
            )
            st.markdown(f"<div style='margin-top:8px'>{pills}</div>", unsafe_allow_html=True)


# ── Welcome message ───────────────────────────────────────────────────
if not st.session_state.chat_history:
    with st.chat_message("assistant", avatar="🪷"):
        lang_suffix = {
            "Hindi": "\nमैं हिंदी में भी उत्तर दे सकता हूँ।",
            "Gujarati": "\nહું ગુજરાતીમાં પણ જવાબ આપી શકું છું.",
        }.get(lang, "")
        st.write(
            f"Jai Shri Krishna! 🙏\n\n"
            f"I am **Pushti Sahayak**, your Pushtimarg knowledge assistant. "
            f"Ask me anything about seva pranalika, philosophy, kirtan, festivals, "
            f"or Varta sahitya.{lang_suffix}"
        )


# ── Language suffix for prompts ───────────────────────────────────────
lang_note = {
    "Hindi"   : " (Please answer in Hindi / हिंदी में उत्तर दें)",
    "Gujarati": " (Please answer in Gujarati / ગુજરાતીમાં જવાબ આપો)",
    "English" : " (Please answer in English)",
}.get(lang, "")


# ── Chat input ────────────────────────────────────────────────────────
prompt = st.chat_input("Ask about seva, philosophy, kirtan, festivals...")

if not prompt and "pending" in st.session_state:
    prompt = st.session_state.pop("pending")

if prompt:
    # Show user message
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.write(prompt)

    # Get AI answer
    with st.chat_message("assistant", avatar="🪷"):
        with st.spinner("🙏 Searching Pushtimarg knowledge..."):
            try:
                result = st.session_state.chat_rag.ask(
                    question=prompt + lang_note,
                    ghar_filter=ghar_filter,
                )
                answer  = result["answer"]
                sources = result["sources"]
            except Exception as e:
                import os
                answer  = f"DEBUG: {str(e)} | KEY STARTS: {str(os.getenv('ANTHROPIC_API_KEY'))[:15]}"
                sources = []

        st.write(answer)

        if show_sources and sources:
            pills = " ".join(
                f'<span class="source-pill">📖 {s["source"][:28]} · {s["relevance"]:.0%}</span>'
                for s in sources
            )
            st.markdown(f"<div style='margin-top:8px'>{pills}</div>", unsafe_allow_html=True)

    st.session_state.chat_history.append({
        "role"   : "assistant",
        "content": answer,
        "sources": sources,
    })


# ── Footer ────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    🪷 Pushti Sahayak — Answers based on authentic Pushtimarg granths and seva pranalika<br>
    When in doubt, always consult your Goswami Maharaj • Jai Shri Krishna 🙏
</div>
""", unsafe_allow_html=True)

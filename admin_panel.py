"""
PUSHTI SAHAYAK — ADMIN PANEL
==============================
A complete admin dashboard with:
  - Library overview (how many books, size, status)
  - Search & download books from archive.org
  - Upload your own PDFs
  - Run ingestion + embedding pipeline with live logs
  - Chat interface to test the AI
  - Settings management

Run:
    streamlit run admin_panel.py
"""

import os
import sys
import time
import json
import shutil
import subprocess
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent))

# ── Page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Pushti Sahayak Admin",
    page_icon="🪷",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_DIR       = Path("./data")
EMBEDDINGS_DIR = Path("./embeddings")
DATA_DIR.mkdir(exist_ok=True)
EMBEDDINGS_DIR.mkdir(exist_ok=True)

# ── Custom CSS — Saffron/Gold temple aesthetic ───────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Hindi&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root {
    --saffron: #D4590A;
    --gold: #C8891A;
    --gold-light: #FFF3DC;
    --maroon: #8B1A1A;
    --cream: #FFFDF7;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

.stApp {
    background: linear-gradient(160deg, #FFFDF7 0%, #FFF8ED 100%);
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #3D0C0C 0%, #6B1515 100%) !important;
}
section[data-testid="stSidebar"] * {
    color: rgba(255,255,255,0.9) !important;
}
section[data-testid="stSidebar"] .stRadio label {
    color: rgba(255,255,255,0.85) !important;
}
section[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {
    color: rgba(255,255,255,0.7) !important;
    font-size: 0.8rem;
}

/* Metric cards */
[data-testid="metric-container"] {
    background: white;
    border: 1px solid #F0E0C8;
    border-radius: 12px;
    padding: 16px !important;
    box-shadow: 0 2px 8px rgba(139,26,26,0.06);
}
[data-testid="stMetricValue"] {
    color: #8B1A1A !important;
    font-weight: 600 !important;
    font-size: 2rem !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #C0392B, #E8660A);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.2s;
}
.stButton > button:hover {
    opacity: 0.9;
    transform: translateY(-1px);
}

/* Section headers */
.section-title {
    font-family: 'Tiro Devanagari Hindi', serif;
    font-size: 1.4rem;
    color: #8B1A1A;
    border-bottom: 2px solid #F0E0C8;
    padding-bottom: 8px;
    margin-bottom: 20px;
}

/* Book cards */
.book-card {
    background: white;
    border: 1px solid #F0E0C8;
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 10px;
    transition: box-shadow 0.2s;
}
.book-card:hover { box-shadow: 0 4px 16px rgba(139,26,26,0.1); }

/* Status badges */
.badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.72rem;
    font-weight: 600;
}
.badge-green  { background: #D8F3DC; color: #1B4332; }
.badge-orange { background: #FFF3DC; color: #7D4E07; }
.badge-red    { background: #FFE5E5; color: #9B2226; }
.badge-blue   { background: #E8F4FD; color: #1D3557; }

/* Chat messages */
.chat-user {
    background: #FFF3DC;
    border-radius: 12px 12px 4px 12px;
    padding: 12px 16px;
    margin: 8px 0;
    text-align: right;
}
.chat-bot {
    background: white;
    border: 1px solid #F0E0C8;
    border-radius: 12px 12px 12px 4px;
    padding: 12px 16px;
    margin: 8px 0;
}

/* Log output */
.log-box {
    background: #1E1208;
    color: #FFD166;
    font-family: monospace;
    font-size: 0.82rem;
    border-radius: 8px;
    padding: 16px;
    max-height: 300px;
    overflow-y: auto;
    line-height: 1.6;
}

/* Input fields */
.stTextInput > div > div > input {
    border-radius: 8px;
    border: 1px solid #F0E0C8;
}
.stTextInput > div > div > input:focus {
    border-color: #E8660A;
    box-shadow: 0 0 0 2px rgba(232,102,10,0.15);
}
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  SIDEBAR NAVIGATION
# ══════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 20px 0 16px'>
        <div style='font-size:2.5rem'>🪷</div>
        <div style='font-family:"Tiro Devanagari Hindi",serif; font-size:1.2rem; color:white'>
            Pushti Sahayak
        </div>
        <div style='font-size:0.78rem; opacity:0.6; margin-top:4px'>Admin Panel</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "📚  Library",
            "🔍  Add Books",
            "⚙️  Build AI",
            "💬  Test Chat",
            "🔧  Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # Quick stats in sidebar
    pdfs = list(DATA_DIR.glob("*.pdf"))
    txts = list(DATA_DIR.glob("*.txt"))
    chroma_exists = (EMBEDDINGS_DIR / "chroma_db").exists()

    st.markdown(f"""
    <div style='font-size:0.8rem; opacity:0.7; line-height:2'>
        📂 Books in library: <b style='color:white'>{len(pdfs)+len(txts)}</b><br>
        🧠 AI database: <b style='color:{"#52B788" if chroma_exists else "#FF8FA3"}'>{
        "Ready ✓" if chroma_exists else "Not built yet"}</b>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.72rem; opacity:0.5; text-align:center'>
        Jai Shri Krishna 🙏<br>Pushti Sahayak v1.0
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
#  PAGE: LIBRARY
# ══════════════════════════════════════════════════════
if "📚  Library" in page:
    st.markdown('<div class="section-title">📚 Your Pushtimarg Library</div>', unsafe_allow_html=True)

    from auto_download import get_library_stats
    stats = get_library_stats()

    # Metric row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📄 Total Books", stats["total_files"])
    c2.metric("📑 PDFs", stats["pdf_count"])
    c3.metric("📝 Text files", stats["txt_count"])
    c4.metric("💾 Total size", f"{stats['total_mb']} MB")

    st.markdown("<br>", unsafe_allow_html=True)

    if stats["files"]:
        st.markdown("### Books in your library")

        # Search filter
        search_filter = st.text_input("🔎 Filter books", placeholder="Type to filter...")

        for f in stats["files"]:
            if search_filter and search_filter.lower() not in f["name"].lower():
                continue

            col1, col2, col3, col4 = st.columns([5, 1.5, 1.5, 1.5])
            with col1:
                st.markdown(f"**{f['name']}**")
            with col2:
                st.caption(f"{f['size_kb']} KB")
            with col3:
                badge = "badge-blue" if f["type"] == "PDF" else "badge-orange"
                st.markdown(f'<span class="badge {badge}">{f["type"]}</span>', unsafe_allow_html=True)
            with col4:
                if st.button("🗑️ Delete", key=f"del_{f['name']}"):
                    (DATA_DIR / f["name"]).unlink()
                    st.success(f"Deleted {f['name']}")
                    st.rerun()

            st.markdown('<hr style="margin:4px 0; opacity:0.15"/>', unsafe_allow_html=True)
    else:
        st.info("📭 No books yet! Go to **Add Books** to get started.")

    # Upload your own PDF
    st.markdown("---")
    st.markdown("### Upload your own book")
    uploaded = st.file_uploader(
        "Drag & drop PDFs, TXT files from your computer",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
    )
    if uploaded:
        for f in uploaded:
            dest = DATA_DIR / f.name
            dest.write_bytes(f.read())
            st.success(f"✅ Uploaded: {f.name}")
        st.balloons()
        st.info("Now go to **Build AI** tab to update the database!")


# ══════════════════════════════════════════════════════
#  PAGE: ADD BOOKS
# ══════════════════════════════════════════════════════
elif "🔍  Add Books" in page:
    st.markdown('<div class="section-title">🔍 Search & Download Pushtimarg Books</div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🔎 Search archive.org", "⚡ Auto-download all"])

    # ── Tab 1: Manual search ──
    with tab1:
        st.markdown("Search for any Pushtimarg book on **archive.org** (free, 500+ books available)")

        col1, col2 = st.columns([4, 1])
        with col1:
            search_query = st.text_input(
                "Search query",
                placeholder="e.g. 84 vaishnavas varta  /  pushtimarg kirtan  /  subodhini vallabh",
                label_visibility="collapsed",
            )
        with col2:
            search_btn = st.button("🔍 Search", use_container_width=True)

        # Quick search suggestions
        st.markdown("**Quick searches:**")
        suggestions = [
            "84 vaishnavas varta",
            "pushtimarg kirtan gujarati",
            "shodash granth vallabh",
            "nathdwara seva",
            "252 vaishnavas varta",
            "pushtimarg philosophy hindi",
        ]
        cols = st.columns(3)
        for i, s in enumerate(suggestions):
            if cols[i % 3].button(s, key=f"sugg_{i}"):
                search_query = s
                search_btn = True

        if search_btn and search_query:
            from auto_download import search_and_preview, download_single
            with st.spinner(f"Searching archive.org for '{search_query}'..."):
                results = search_and_preview(search_query, max_results=8)

            if not results:
                st.warning("No results found. Try a different search term.")
            else:
                st.success(f"Found {len(results)} results")
                for r in results:
                    with st.container():
                        c1, c2 = st.columns([4, 1])
                        with c1:
                            st.markdown(f"**{r['title'][:80]}**")
                            st.caption(f"📥 {r['downloads']:,} downloads | 🔗 {r['archive_url']}")
                            if r["description"]:
                                st.caption(r["description"][:150] + "...")
                        with c2:
                            if r["already_downloaded"]:
                                st.markdown('<span class="badge badge-green">✓ Downloaded</span>', unsafe_allow_html=True)
                            elif r["has_pdf"]:
                                if st.button("⬇️ Download", key=f"dl_{r['identifier']}"):
                                    with st.spinner("Downloading..."):
                                        result = download_single(r["identifier"], r["title"], r["pdf_url"])
                                    if result["success"]:
                                        st.success(f"✅ Saved as {result['filename']}")
                                    else:
                                        st.error("Download failed. Try another book.")
                            else:
                                st.markdown('<span class="badge badge-red">No PDF</span>', unsafe_allow_html=True)
                        st.markdown('<hr style="opacity:0.15; margin:8px 0"/>', unsafe_allow_html=True)

    # ── Tab 2: Auto download ──
    with tab2:
        from auto_download import PUSHTIMARG_SEARCHES

        st.markdown(f"""
        Automatically searches for **{len(PUSHTIMARG_SEARCHES)} pre-configured** Pushtimarg topics
        and downloads the best PDFs for each. Best way to build your library fast!
        """)

        col1, col2 = st.columns(2)
        with col1:
            max_per_search = st.slider("Books per search topic", 1, 5, 2)
        with col2:
            st.metric("Estimated downloads", f"Up to {len(PUSHTIMARG_SEARCHES) * max_per_search} books")

        st.markdown("**Topics that will be searched:**")
        topics_html = " ".join(
            f'<span class="badge badge-blue" style="margin:2px">{s["query"][:30]}</span>'
            for s in PUSHTIMARG_SEARCHES
        )
        st.markdown(topics_html, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if st.button("⚡ Start Auto-Download", use_container_width=True):
            from auto_download import auto_download_all

            progress_bar = st.progress(0, text="Starting...")
            status_text  = st.empty()
            log_area     = st.empty()
            log_lines    = []

            def update_progress(event_type, fraction=0, message=""):
                progress_bar.progress(min(fraction, 1.0), text=message)
                log_lines.append(f"→ {message}")
                log_area.code("\n".join(log_lines[-15:]), language=None)

            with st.spinner("Downloading Pushtimarg books from archive.org..."):
                summary = auto_download_all(max_per_search=max_per_search)

            st.success(f"""
            ✅ Auto-download complete!
            • **Downloaded:** {summary['downloaded']} new books
            • **Already had:** {summary['skipped']}
            • **Failed:** {summary['failed']}
            """)
            if summary["downloaded"] > 0:
                st.info("👉 Now go to **Build AI** tab to update the database with new books!")


# ══════════════════════════════════════════════════════
#  PAGE: BUILD AI
# ══════════════════════════════════════════════════════
elif "⚙️  Build AI" in page:
    st.markdown('<div class="section-title">⚙️ Build / Update AI Database</div>', unsafe_allow_html=True)

    pdfs = list(DATA_DIR.glob("*.pdf")) + list(DATA_DIR.glob("*.txt"))
    chroma_exists = (EMBEDDINGS_DIR / "chroma_db").exists()
    chunks_exist  = (EMBEDDINGS_DIR / "chunks.json").exists()

    # Status overview
    st.markdown("### Current status")
    c1, c2, c3 = st.columns(3)
    c1.metric("Books in library", len(pdfs))
    c2.metric(
        "Chunks file",
        "✅ Ready" if chunks_exist else "❌ Not built",
        delta="Run Step 1" if not chunks_exist else None,
    )
    c3.metric(
        "AI database",
        "✅ Ready" if chroma_exists else "❌ Not built",
        delta="Run Step 2" if not chroma_exists else None,
    )

    if not pdfs:
        st.warning("⚠️ No books found in your library! Go to **Add Books** first.")
    else:
        st.markdown("---")
        st.markdown("### Run pipeline steps")

        # Step 1
        with st.expander("📖 Step 1 — Process Books (reads PDFs → creates chunks)", expanded=not chunks_exist):
            st.markdown("""
            Reads all your PDFs and splits them into small searchable pieces (chunks).
            Run this every time you add new books.
            """)
            if st.button("▶ Run Step 1: Process Books", use_container_width=True, key="run1"):
                with st.spinner("Processing your books... this takes 1-2 minutes"):
                    log_out = st.empty()
                    try:
                        result = subprocess.run(
                            [sys.executable, "1_ingest_data.py"],
                            capture_output=True, text=True, cwd=str(Path(__file__).parent)
                        )
                        output = result.stdout + result.stderr
                        log_out.code(output, language=None)
                        if result.returncode == 0:
                            st.success("✅ Step 1 complete! Books processed successfully.")
                        else:
                            st.error("❌ Step 1 failed. See output above.")
                    except Exception as e:
                        st.error(f"Error: {e}")

        # Step 2
        with st.expander("🧠 Step 2 — Build AI Database (creates embeddings)", expanded=chunks_exist and not chroma_exists):
            st.markdown("""
            Converts all chunks into AI vectors and stores them in ChromaDB.
            **One-time cost: ~₹5–₹50 on OpenAI API.**
            Run this after Step 1 finishes.
            """)
            if not chunks_exist:
                st.warning("Run Step 1 first!")
            else:
                if st.button("▶ Run Step 2: Build AI Database", use_container_width=True, key="run2"):
                    with st.spinner("Creating AI embeddings... this takes 5-15 minutes"):
                        log_out = st.empty()
                        try:
                            result = subprocess.run(
                                [sys.executable, "2_create_embeddings.py"],
                                capture_output=True, text=True, cwd=str(Path(__file__).parent)
                            )
                            output = result.stdout + result.stderr
                            log_out.code(output, language=None)
                            if result.returncode == 0:
                                st.success("✅ Step 2 complete! AI database is ready.")
                                st.balloons()
                            else:
                                st.error("❌ Step 2 failed. Check your OPENAI_API_KEY in .env file.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        # Run both
        st.markdown("---")
        st.markdown("### Or run both steps at once")
        if st.button("⚡ Run Full Pipeline (Step 1 + Step 2)", use_container_width=True):
            with st.spinner("Running full pipeline..."):
                for script in ["1_ingest_data.py", "2_create_embeddings.py"]:
                    st.markdown(f"Running `{script}`...")
                    result = subprocess.run(
                        [sys.executable, script],
                        capture_output=True, text=True, cwd=str(Path(__file__).parent)
                    )
                    st.code(result.stdout[-2000:], language=None)
                    if result.returncode != 0:
                        st.error(f"❌ {script} failed!")
                        break
                else:
                    st.success("✅ Full pipeline complete! Your AI is ready.")
                    st.balloons()


# ══════════════════════════════════════════════════════
#  PAGE: TEST CHAT
# ══════════════════════════════════════════════════════
elif "💬  Test Chat" in page:
    st.markdown('<div class="section-title">💬 Test Your Pushtimarg AI</div>', unsafe_allow_html=True)

    chroma_exists = (EMBEDDINGS_DIR / "chroma_db").exists()

    if not chroma_exists:
        st.warning("⚠️ AI database not built yet! Go to **Build AI** first.")
        st.stop()

    # Load RAG
    @st.cache_resource
    def load_rag():
        try:
            from rag_engine import PushtimargRAG
            return PushtimargRAG(), None
        except Exception as e:
            return None, str(e)

    rag, err = load_rag()
    if err:
        st.error(f"RAG Error: {err}")
        st.stop()

    # Sidebar options for chat
    col1, col2 = st.columns([3, 1])
    with col2:
        ghar = st.selectbox("Filter by Ghar", [
            "All Ghars", "Giridharji", "Govindraiji",
            "Balkrishnaji", "Gokulnathji", "Raghunathji",
            "Yadunathji", "Ghanshyamji"
        ])
        show_src = st.toggle("Show sources", True)
        if st.button("🔄 Reset chat"):
            st.session_state.admin_chat = []
            if rag:
                rag.reset_conversation()
            st.rerun()

    with col1:
        # Chat history
        if "admin_chat" not in st.session_state:
            st.session_state.admin_chat = []

        # Quick test questions
        st.markdown("**Quick test questions:**")
        quick = [
            "What is Pushtimarg?",
            "Ashtayam seva ke 8 darshan kaun se hain?",
            "Shrinathji ki seva pranalika kahan hai?",
            "84 Vaishnavas ki Varta kya hai?",
        ]
        qcols = st.columns(2)
        for i, q in enumerate(quick):
            if qcols[i % 2].button(q, key=f"q{i}"):
                st.session_state.pending_question = q

        st.markdown("---")

        # Display chat
        for msg in st.session_state.admin_chat:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">👤 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot">🪷 {msg["content"]}</div>', unsafe_allow_html=True)
                if show_src and msg.get("sources"):
                    src_tags = " ".join(
                        f'<span class="badge badge-blue" style="margin:2px">📖 {s["source"][:25]} ({s["relevance"]:.0%})</span>'
                        for s in msg["sources"]
                    )
                    st.markdown(f"<div style='margin-top:4px'>{src_tags}</div>", unsafe_allow_html=True)

        # Input
        question = st.chat_input("Ask about Pushtimarg seva, philosophy, kirtan...")
        if not question and "pending_question" in st.session_state:
            question = st.session_state.pop("pending_question")

        if question:
            st.session_state.admin_chat.append({"role": "user", "content": question})
            ghar_filter = None if ghar == "All Ghars" else ghar
            with st.spinner("Searching knowledge base..."):
                result = rag.ask(question, ghar_filter=ghar_filter)
            st.session_state.admin_chat.append({
                "role": "assistant",
                "content": result["answer"],
                "sources": result["sources"],
            })
            st.rerun()


# ══════════════════════════════════════════════════════
#  PAGE: SETTINGS
# ══════════════════════════════════════════════════════
elif "🔧  Settings" in page:
    st.markdown('<div class="section-title">🔧 Settings</div>', unsafe_allow_html=True)

    st.markdown("### API Keys")
    st.info("Your keys are stored in the `.env` file in your project folder. Edit them here or directly in VS Code.")

    env_path = Path(".env")
    current_env = {}
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                current_env[k.strip()] = v.strip()

    openai_key = st.text_input(
        "OpenAI API Key (for embeddings)",
        value=current_env.get("OPENAI_API_KEY", ""),
        type="password",
        help="Get from https://platform.openai.com/api-keys",
    )
    anthropic_key = st.text_input(
        "Anthropic API Key (for Claude answers)",
        value=current_env.get("ANTHROPIC_API_KEY", ""),
        type="password",
        help="Get from https://console.anthropic.com",
    )

    if st.button("💾 Save Keys"):
        env_content = f"OPENAI_API_KEY={openai_key}\nANTHROPIC_API_KEY={anthropic_key}\n"
        env_path.write_text(env_content)
        st.success("✅ Keys saved to .env file!")

    st.markdown("---")
    st.markdown("### AI Settings")

    col1, col2 = st.columns(2)
    with col1:
        top_k = st.slider("Number of sources to retrieve per answer", 3, 10, 5)
        chunk_size = st.slider("Chunk size (characters)", 300, 1000, 600)
    with col2:
        st.markdown(f"""
        **Current settings:**
        - Model: Claude claude-opus-4-5 (best quality)
        - Top K: {top_k} sources per answer
        - Chunk size: {chunk_size} characters
        - Overlap: 100 characters
        """)

    st.markdown("---")
    st.markdown("### Danger Zone")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗑️ Clear AI Database (keep books)", type="secondary"):
            chroma_path = EMBEDDINGS_DIR / "chroma_db"
            if chroma_path.exists():
                shutil.rmtree(chroma_path)
                st.warning("AI database cleared. Run Build AI to rebuild.")
    with col2:
        if st.button("🗑️ Clear All Books + Database", type="secondary"):
            st.error("This will delete ALL your books and database. Are you sure?")
            if st.button("⚠️ Yes, delete everything", type="primary"):
                for f in DATA_DIR.glob("*"):
                    f.unlink()
                if (EMBEDDINGS_DIR / "chroma_db").exists():
                    shutil.rmtree(EMBEDDINGS_DIR / "chroma_db")
                if (EMBEDDINGS_DIR / "chunks.json").exists():
                    (EMBEDDINGS_DIR / "chunks.json").unlink()
                st.success("All cleared.")

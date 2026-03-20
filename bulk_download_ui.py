"""
BULK DOWNLOAD PAGE — Add this into your admin_panel.py
========================================================
Replace the "Add Books" section in admin_panel.py with this,
OR run it standalone:
    streamlit run bulk_download_ui.py
"""

import threading
import time
from pathlib import Path
import streamlit as st

st.set_page_config(page_title="Bulk Downloader", page_icon="📥", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&display=swap');
* { font-family: 'DM Sans', sans-serif; }

.stApp { background: #FFFDF7; }

.hero-strip {
    background: linear-gradient(135deg, #7D0000, #C0392B, #E8660A);
    border-radius: 16px;
    padding: 28px 28px 24px;
    color: white;
    margin-bottom: 24px;
}
.hero-strip h2 { margin: 0 0 4px; font-size: 1.5rem; }
.hero-strip p  { margin: 0; opacity: 0.85; font-size: 0.9rem; }

.stat-card {
    background: white;
    border: 1px solid #F0E0C8;
    border-radius: 12px;
    padding: 16px 20px;
    text-align: center;
}
.stat-num  { font-size: 2rem; font-weight: 600; color: #8B1A1A; line-height: 1; }
.stat-label{ font-size: 0.78rem; color: #9C7E65; margin-top: 4px; }

.file-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    border-bottom: 1px solid #F5ECD8;
    font-size: 0.85rem;
}
.badge {
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 99px;
}
.badge-pdf  { background: #FFF3DC; color: #7D4E07; }
.badge-done { background: #D8F3DC; color: #1B4332; }
.badge-fail { background: #FFE5E5; color: #9B2226; }

div[data-testid="stProgress"] > div {
    background: linear-gradient(90deg, #C0392B, #E8660A) !important;
    border-radius: 99px !important;
}

.stButton > button {
    background: linear-gradient(135deg, #8B1A1A, #E8660A) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 500 !important;
    padding: 10px 24px !important;
    font-size: 1rem !important;
}
.stButton > button:hover { opacity: 0.9 !important; }

.stop-btn > button {
    background: #fff !important;
    color: #9B2226 !important;
    border: 1px solid #9B2226 !important;
}

.log-terminal {
    background: #1E1208;
    color: #95E1D3;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    border-radius: 10px;
    padding: 14px 16px;
    line-height: 1.8;
    max-height: 280px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-all;
}
</style>
""", unsafe_allow_html=True)

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

# ── Hero ─────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero-strip">
    <h2>📥 Bulk Download — Pushtimarg Collection</h2>
    <p>Download all books from archive.org/details/Pushtimarg in one click</p>
</div>
""", unsafe_allow_html=True)

# ── Current library stats ─────────────────────────────────────────────
pdfs     = list(DATA_DIR.glob("*.pdf"))
txts     = list(DATA_DIR.glob("*.txt"))
total_mb = sum(f.stat().st_size for f in pdfs + txts) / (1024 * 1024)

c1, c2, c3, c4 = st.columns(4)
for col, num, label in [
    (c1, len(pdfs),              "PDFs downloaded"),
    (c2, len(txts),              "Text files"),
    (c3, f"{total_mb:.0f} MB",   "Total size"),
    (c4, len(pdfs) + len(txts),  "Total books"),
]:
    col.markdown(f"""
    <div class="stat-card">
        <div class="stat-num">{num}</div>
        <div class="stat-label">{label}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Settings ──────────────────────────────────────────────────────────
with st.expander("⚙️ Download Settings", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        collection_url = st.text_input(
            "Archive.org Collection URL",
            value="https://archive.org/details/Pushtimarg/",
            help="Paste any archive.org collection URL here",
        )
        max_size = st.slider(
            "Max file size (MB) — skip files larger than this",
            min_value=10, max_value=500, value=150, step=10,
        )
        delay = st.slider(
            "Delay between downloads (seconds)",
            min_value=0.5, max_value=5.0, value=1.5, step=0.5,
            help="Higher = more polite to archive.org servers",
        )
    with col2:
        st.markdown("**File types to download:**")
        dl_pdf  = st.checkbox("📄 PDF  (recommended)", value=True)
        dl_txt  = st.checkbox("📝 TXT  text files",    value=True)
        dl_epub = st.checkbox("📱 EPUB e-books",       value=False)
        dl_djvu = st.checkbox("🗜️ DJVU scanned books (large)", value=False)

        st.markdown("<br>", unsafe_allow_html=True)
        resume = st.checkbox(
            "⏭️ Skip already-downloaded files (Resume mode)",
            value=True,
            help="Recommended — if download stops midway, restart and it will continue from where it left off",
        )

# Parse collection ID from URL
collection_id = collection_url.strip().rstrip("/").split("/")[-1]
st.caption(f"📦 Collection ID detected: **{collection_id}**")

st.markdown("---")

# ── Session state ─────────────────────────────────────────────────────
if "dl_running"  not in st.session_state: st.session_state.dl_running  = False
if "dl_progress" not in st.session_state: st.session_state.dl_progress = 0
if "dl_message"  not in st.session_state: st.session_state.dl_message  = ""
if "dl_log"      not in st.session_state: st.session_state.dl_log      = []
if "dl_done"     not in st.session_state: st.session_state.dl_done     = False
if "dl_stats"    not in st.session_state: st.session_state.dl_stats    = {}
if "stop_flag"   not in st.session_state: st.session_state.stop_flag   = threading.Event()

# ── Download controls ──────────────────────────────────────────────────
col_btn1, col_btn2 = st.columns([3, 1])

with col_btn1:
    if not st.session_state.dl_running:
        if st.button("🚀 Start Downloading All Books", use_container_width=True):
            from bulk_download import bulk_download

            # Reset state
            st.session_state.dl_running  = True
            st.session_state.dl_done     = False
            st.session_state.dl_progress = 0
            st.session_state.dl_log      = ["🪷 Starting Pushtimarg bulk download...", f"   Collection: {collection_id}"]
            st.session_state.stop_flag.clear()

            # Override config
            import bulk_download as bd
            bd.DATA_DIR         = DATA_DIR
            bd.COLLECTION_ID    = collection_id
            bd.MAX_FILE_SIZE_MB = max_size
            bd.DELAY_BETWEEN    = delay
            bd.RESUME           = resume
            bd.ALLOWED_EXTS     = set()
            if dl_pdf:  bd.ALLOWED_EXTS.add(".pdf")
            if dl_txt:  bd.ALLOWED_EXTS.add(".txt")
            if dl_epub: bd.ALLOWED_EXTS.add(".epub")
            if dl_djvu: bd.ALLOWED_EXTS.add(".djvu")

            def progress_cb(pct, msg):
                st.session_state.dl_progress = pct
                st.session_state.dl_message  = msg
                st.session_state.dl_log.append(f"→ {msg}")
                if len(st.session_state.dl_log) > 200:
                    st.session_state.dl_log = st.session_state.dl_log[-200:]

            def run_download():
                try:
                    stats = bulk_download(
                        collection_id=collection_id,
                        progress_cb=progress_cb,
                        stop_flag=st.session_state.stop_flag,
                    )
                    st.session_state.dl_stats = stats
                    st.session_state.dl_log.append(f"\n✅ Complete! {stats.get('files_downloaded',0)} files downloaded.")
                except Exception as e:
                    st.session_state.dl_log.append(f"\n❌ Error: {e}")
                finally:
                    st.session_state.dl_running = False
                    st.session_state.dl_done    = True

            # Run in background thread so UI stays responsive
            t = threading.Thread(target=run_download, daemon=True)
            t.start()
            st.rerun()
    else:
        st.info("⏳ Download is running in the background...")

with col_btn2:
    if st.session_state.dl_running:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        if st.button("⏹ Stop", use_container_width=True):
            st.session_state.stop_flag.set()
            st.session_state.dl_log.append("⏹️ Stop requested — finishing current file...")
        st.markdown("</div>", unsafe_allow_html=True)

# ── Live progress ──────────────────────────────────────────────────────
if st.session_state.dl_running or st.session_state.dl_done:
    st.markdown("### Progress")

    pct = st.session_state.dl_progress
    st.progress(pct / 100, text=st.session_state.dl_message or "Running...")
    st.caption(f"{pct}% complete")

    # Live log terminal
    if st.session_state.dl_log:
        log_text = "\n".join(st.session_state.dl_log[-60:])
        st.markdown(f'<div class="log-terminal">{log_text}</div>', unsafe_allow_html=True)

    # Auto-refresh while running
    if st.session_state.dl_running:
        time.sleep(2)
        st.rerun()

# ── Done summary ───────────────────────────────────────────────────────
if st.session_state.dl_done and st.session_state.dl_stats:
    stats = st.session_state.dl_stats
    st.success(f"""
    ✅ **Download Complete!**
    - **{stats.get('files_downloaded', 0)}** files downloaded
    - **{stats.get('files_skipped',    0)}** already existed (skipped)
    - **{stats.get('files_failed',     0)}** failed
    - **{stats.get('total_mb', 0):.1f} MB** downloaded
    """)
    st.info("👉 Now go to **Build AI** in the admin panel to update your knowledge base!")

    if st.button("🔄 Download Again / Resume"):
        st.session_state.dl_done  = False
        st.session_state.dl_stats = {}
        st.rerun()

# ── Recently downloaded files ──────────────────────────────────────────
st.markdown("---")
st.markdown("### Recently downloaded files")

recent_files = sorted(
    list(DATA_DIR.glob("*.pdf")) + list(DATA_DIR.glob("*.txt")),
    key=lambda f: f.stat().st_mtime,
    reverse=True,
)[:20]

if recent_files:
    for f in recent_files:
        size_kb = f.stat().st_size / 1024
        ext     = f.suffix.upper().lstrip(".")
        st.markdown(f"""
        <div class="file-row">
            <span class="badge badge-pdf">{ext}</span>
            <span style="flex:1; color:#3D1C00">{f.name[:65]}</span>
            <span style="color:#9C7E65; font-size:0.75rem">{size_kb:.0f} KB</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No books downloaded yet. Hit the button above to start!")

# ── How it works ──────────────────────────────────────────────────────
with st.expander("ℹ️ How does this work?"):
    st.markdown("""
    1. **Fetches the full list** of all items in the Pushtimarg collection using archive.org's search API
    2. **For each book**, checks what files are available (PDF, TXT, etc.)
    3. **Downloads** each file directly to your `data/` folder
    4. **Saves progress** after each book — so if it stops midway, restart and it picks up from where it left off
    5. **Respects archive.org** with a small pause between downloads so their servers aren't overloaded

    The entire Pushtimarg collection may take **30–90 minutes** to download fully depending on your internet speed.
    You can close this tab and reopen later — the download runs in the background.
    """)

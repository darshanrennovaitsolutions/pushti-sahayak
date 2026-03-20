"""
BULK DOWNLOADER — Entire Pushtimarg Collection
================================================
Downloads ALL books from:
    https://archive.org/details/Pushtimarg/

Uses the official internetarchive Python library.

HOW TO RUN:
    python bulk_download.py

OPTIONS (edit the CONFIG section below):
    - Download only PDFs (skip audio/video)
    - Set max file size limit
    - Resume interrupted downloads
    - Choose your data folder
"""

import os
import sys
import time
import json
import requests
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────────────────────
#  ⚙️  CONFIG — Edit these settings before running
# ─────────────────────────────────────────────────────────
COLLECTION_ID   = "Pushti"          # The archive.org collection name
DATA_DIR        = Path("./data")        # Where to save all PDFs
LOG_FILE        = Path("./logs/bulk_download_log.json")

# File type filters — True = download, False = skip
DOWNLOAD_PDF    = True    # PDF books          ← MOST IMPORTANT
DOWNLOAD_TXT    = True    # Plain text files
DOWNLOAD_EPUB   = False   # E-book format
DOWNLOAD_DJVU   = False   # Scanned book format (large files)
DOWNLOAD_MP3    = False   # Audio recordings
DOWNLOAD_MP4    = False   # Video files

# Size limit — skip files larger than this (in MB). 0 = no limit
MAX_FILE_SIZE_MB = 200    # Skip files over 200MB (very large scans)

# Politeness — wait between downloads (seconds)
DELAY_BETWEEN   = 1.5     # Be respectful to archive.org servers

# Resume mode — skip files already downloaded
RESUME          = True    # True = skip if file exists
# ─────────────────────────────────────────────────────────

DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTS = set()
if DOWNLOAD_PDF:  ALLOWED_EXTS.update([".pdf"])
if DOWNLOAD_TXT:  ALLOWED_EXTS.update([".txt"])
if DOWNLOAD_EPUB: ALLOWED_EXTS.update([".epub"])
if DOWNLOAD_DJVU: ALLOWED_EXTS.update([".djvu"])
if DOWNLOAD_MP3:  ALLOWED_EXTS.update([".mp3"])
if DOWNLOAD_MP4:  ALLOWED_EXTS.update([".mp4"])


# ── Colours for terminal output ──────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"


def log_print(msg, color=RESET):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] {msg}{RESET}")


def get_all_identifiers(collection_id: str) -> list[dict]:
    """
    Fetch ALL item identifiers in a collection using archive.org search API.
    Handles pagination automatically — gets every single item.
    """
    log_print(f"📡 Fetching item list from collection: {collection_id}", BLUE)
    
    all_items = []
    page = 1
    rows = 100  # Items per page (max 100)
    
    while True:
        url = "https://archive.org/advancedsearch.php"
        params = {
           "q" : f"Pushti AND mediatype:texts",
            "fl[]"   : ["identifier", "title", "mediatype", "downloads"],
            "output" : "json",
            "rows"   : rows,
            "page"   : page,
        }
        
        try:
            resp = requests.get(url, params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            
            docs        = data.get("response", {}).get("docs", [])
            total_found = data.get("response", {}).get("numFound", 0)
            
            if not docs:
                break
                
            all_items.extend(docs)
            log_print(f"   Page {page}: fetched {len(docs)} items (total so far: {len(all_items)}/{total_found})", BLUE)
            
            if len(all_items) >= total_found:
                break
                
            page += 1
            time.sleep(0.5)  # Small pause between pages
            
        except Exception as e:
            log_print(f"   ⚠️ Error on page {page}: {e}", YELLOW)
            break
    
    log_print(f"✅ Found {len(all_items)} items in '{collection_id}' collection", GREEN)
    return all_items


def get_pdf_files(identifier: str) -> list[dict]:
    """Get list of downloadable files for one item."""
    url = f"https://archive.org/metadata/{identifier}"
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        meta  = resp.json()
        files = meta.get("files", [])
        
        result = []
        for f in files:
            name = f.get("name", "")
            ext  = Path(name).suffix.lower()
            if ext not in ALLOWED_EXTS:
                continue
            size_bytes = int(f.get("size", 0))
            size_mb    = size_bytes / (1024 * 1024)
            if MAX_FILE_SIZE_MB > 0 and size_mb > MAX_FILE_SIZE_MB:
                continue
            result.append({
                "name"    : name,
                "size_mb" : round(size_mb, 2),
                "url"     : f"https://archive.org/download/{identifier}/{requests.utils.quote(name)}",
            })
        return result
    except Exception as e:
        return []


def download_file(url: str, dest: Path, size_mb: float) -> bool:
    """Download one file with a simple progress display."""
    if RESUME and dest.exists() and dest.stat().st_size > 1000:
        return True  # Already downloaded
    
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        
        total      = int(resp.headers.get("content-length", 0))
        downloaded = 0
        
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):  # 64KB chunks
                f.write(chunk)
                downloaded += len(chunk)
                # Simple progress indicator
                if total > 0:
                    pct = int(downloaded / total * 20)
                    bar = "█" * pct + "░" * (20 - pct)
                    mb  = downloaded / (1024 * 1024)
                    print(f"\r      [{bar}] {mb:.1f}/{size_mb:.1f} MB", end="", flush=True)
        
        print()  # New line after progress bar
        return True
        
    except Exception as e:
        print()  # New line
        if dest.exists():
            dest.unlink()  # Delete incomplete file
        return False


def sanitize_filename(title: str, identifier: str, original_name: str) -> str:
    """Create a clean, readable filename."""
    ext   = Path(original_name).suffix.lower()
    clean = "".join(c if c.isalnum() or c in " -_" else "_" for c in title)
    clean = clean.strip().replace(" ", "_")[:50]
    return f"{clean}__{identifier[:15]}{ext}"


def load_log() -> dict:
    if LOG_FILE.exists():
        try:
            return json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {
        "downloaded": [],
        "skipped"   : [],
        "failed"    : [],
        "stats"     : {"total_files": 0, "total_mb": 0},
        "started_at": str(datetime.now()),
    }


def save_log(log: dict):
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")


# ══════════════════════════════════════════════════════════
#  MAIN FUNCTION
# ══════════════════════════════════════════════════════════
def bulk_download(
    collection_id   : str   = COLLECTION_ID,
    progress_cb     = None,   # Optional callback(pct, message) for UI
    stop_flag       = None,   # Optional threading.Event to stop mid-run
):
    """
    Download all PDFs from an archive.org collection.
    Returns summary dict.
    """
    log = load_log()
    already_done = set(log["downloaded"] + log["failed"])
    
    print(f"\n{BOLD}{'='*55}")
    print(f"  🪷 Pushtimarg Bulk Downloader")
    print(f"  Collection: {collection_id}")
    print(f"  Saving to : {DATA_DIR.resolve()}")
    print(f"{'='*55}{RESET}\n")
    
    # ── Step 1: Get all items ─────────────────────────────
    items = get_all_identifiers(collection_id)
    total_items = len(items)
    
    if not items:
        log_print("❌ No items found! Check your collection ID.", RED)
        return {"error": "No items found"}
    
    stats = {
        "total_items"     : total_items,
        "items_processed" : 0,
        "files_downloaded": 0,
        "files_skipped"   : 0,
        "files_failed"    : 0,
        "total_mb"        : 0.0,
    }
    
    # ── Step 2: Download each item ────────────────────────
    for item_idx, item in enumerate(items):
        
        # Check stop signal (for UI)
        if stop_flag and stop_flag.is_set():
            log_print("⏹️  Download stopped by user.", YELLOW)
            break
        
        identifier = item.get("identifier", "")
        title      = item.get("title", identifier)[:60]
        
        # Progress callback for UI
        pct = int(item_idx / total_items * 100)
        msg = f"[{item_idx+1}/{total_items}] {title[:45]}..."
        if progress_cb:
            progress_cb(pct, msg)
        
        log_print(f"\n📖 [{item_idx+1}/{total_items}] {title}", BOLD)
        log_print(f"   ID: {identifier}", BLUE)
        
        # Get files for this item
        files = get_pdf_files(identifier)
        
        if not files:
            log_print(f"   ⚠️  No matching files (PDF/TXT) found", YELLOW)
            log["skipped"].append(identifier)
            stats["files_skipped"] += 1
            continue
        
        log_print(f"   📄 {len(files)} file(s) found", GREEN)
        
        # Download each file
        for file_info in files:
            file_key = f"{identifier}/{file_info['name']}"
            
            dest_name = sanitize_filename(title, identifier, file_info["name"])
            dest_path = DATA_DIR / dest_name
            
            if RESUME and dest_path.exists() and dest_path.stat().st_size > 1000:
                log_print(f"   ⏭️  Already exists: {dest_name}", YELLOW)
                stats["files_skipped"] += 1
                continue
            
            log_print(f"   ⬇️  Downloading: {file_info['name']} ({file_info['size_mb']} MB)", GREEN)
            
            success = download_file(file_info["url"], dest_path, file_info["size_mb"])
            
            if success:
                log_print(f"   ✅ Saved: {dest_name}", GREEN)
                log["downloaded"].append(file_key)
                stats["files_downloaded"] += 1
                stats["total_mb"] += file_info["size_mb"]
            else:
                log_print(f"   ❌ Failed: {file_info['name']}", RED)
                log["failed"].append(file_key)
                stats["files_failed"] += 1
        
        stats["items_processed"] += 1
        log["stats"]["total_files"] = stats["files_downloaded"]
        log["stats"]["total_mb"]    = round(stats["total_mb"], 1)
        save_log(log)  # Save progress after each item
        
        time.sleep(DELAY_BETWEEN)  # Be polite to archive.org
    
    # ── Summary ───────────────────────────────────────────
    print(f"\n{BOLD}{'='*55}")
    print(f"  🎉 Download Complete!")
    print(f"{'='*55}{RESET}")
    log_print(f"Items processed : {stats['items_processed']}/{total_items}", GREEN)
    log_print(f"Files downloaded: {stats['files_downloaded']}", GREEN)
    log_print(f"Files skipped   : {stats['files_skipped']}", YELLOW)
    log_print(f"Files failed    : {stats['files_failed']}", RED if stats['files_failed'] else GREEN)
    log_print(f"Total size      : {stats['total_mb']:.1f} MB  ({stats['total_mb']/1024:.2f} GB)", BLUE)
    log_print(f"Saved to        : {DATA_DIR.resolve()}", BLUE)
    
    if stats["files_downloaded"] > 0:
        print(f"\n{GREEN}{BOLD}✅ Run these next to add all books to your AI:{RESET}")
        print(f"   python 1_ingest_data.py")
        print(f"   python 2_create_embeddings.py\n")
    
    if progress_cb:
        progress_cb(100, f"Done! {stats['files_downloaded']} files downloaded.")
    
    return stats


# ── Run directly ──────────────────────────────────────────
if __name__ == "__main__":
    # Check for custom collection URL argument
    if len(sys.argv) > 1:
        col = sys.argv[1].strip("/").split("/")[-1]
        print(f"Using collection: {col}")
        bulk_download(collection_id=col)
    else:
        bulk_download()

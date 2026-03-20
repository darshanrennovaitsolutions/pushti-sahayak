"""
AUTO DOWNLOADER — Pushtimarg Books from Internet Archive
=========================================================
Searches archive.org and other free sources for Pushtimarg PDFs
and downloads them directly into your ./data/ folder.

Run directly:
    python auto_download.py

Or import and use the functions in your admin app.
"""

import os
import json
import time
import requests
from pathlib import Path
from urllib.parse import quote

DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)
LOG_FILE = Path("./logs/downloads.json")
LOG_FILE.parent.mkdir(exist_ok=True)

# ── Pre-configured Pushtimarg book search terms ──────────────────────
PUSHTIMARG_SEARCHES = [
    # Core granths
    {"query": "vallabhacharyaji shodash granth", "ghar": "all",         "topic": "Core Philosophy"},
    {"query": "subodhini bhagavat vallabh",      "ghar": "all",         "topic": "Bhagavat Tika"},
    {"query": "pushti marg philosophy hindi",    "ghar": "all",         "topic": "Philosophy"},
    # Varta sahitya
    {"query": "84 vaishnavas varta hindi",       "ghar": "Gokulnathji", "topic": "Varta Sahitya"},
    {"query": "252 vaishnavas ki varta",         "ghar": "Gokulnathji", "topic": "Varta Sahitya"},
    {"query": "chaurasi vaishnavan ki varta",    "ghar": "Gokulnathji", "topic": "Varta Sahitya"},
    # Seva
    {"query": "pushtimarg seva pranalika",       "ghar": "all",         "topic": "Seva Pranalika"},
    {"query": "nathdwara shrinathji seva",       "ghar": "Giridharji",  "topic": "Seva Pranalika"},
    {"query": "ashtayam seva kirtan",            "ghar": "all",         "topic": "Seva Pranalika"},
    # Kirtan
    {"query": "pushtimarg kirtan sangrah gujarati","ghar": "all",        "topic": "Kirtan"},
    {"query": "pushtimarg kirtan hindi braj",    "ghar": "all",         "topic": "Kirtan"},
    {"query": "kumbhandas pad pushtimarg",       "ghar": "all",         "topic": "Kirtan"},
    # Festivals
    {"query": "pushtimarg utsav pranalika",      "ghar": "all",         "topic": "Utsav"},
    {"query": "pushtimarg annakut festival",     "ghar": "all",         "topic": "Utsav"},
    # Gujarati
    {"query": "pushti marg gujarati granth",     "ghar": "all",         "topic": "Gujarati Texts"},
    {"query": "vallabhacharya gujarati",         "ghar": "all",         "topic": "Gujarati Texts"},
]


def search_archive_org(query: str, max_results: int = 5) -> list[dict]:
    """Search Internet Archive for Pushtimarg PDFs."""
    url = "https://archive.org/advancedsearch.php"
    params = {
        "q"       : f"{query} mediatype:texts",
        "fl[]"    : ["identifier", "title", "description", "downloads"],
        "output"  : "json",
        "rows"    : max_results,
        "page"    : 1,
        "sort[]"  : "downloads desc",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        docs = data.get("response", {}).get("docs", [])
        results = []
        for doc in docs:
            results.append({
                "identifier"  : doc.get("identifier", ""),
                "title"       : doc.get("title", "Unknown"),
                "description" : str(doc.get("description", ""))[:200],
                "downloads"   : doc.get("downloads", 0),
                "archive_url" : f"https://archive.org/details/{doc.get('identifier','')}",
            })
        return results
    except Exception as e:
        print(f"  ⚠️  Search error: {e}")
        return []


def get_pdf_url(identifier: str) -> str | None:
    """Get the direct PDF download URL for an archive.org item."""
    meta_url = f"https://archive.org/metadata/{identifier}"
    try:
        resp = requests.get(meta_url, timeout=15)
        resp.raise_for_status()
        meta = resp.json()
        files = meta.get("files", [])
        # Prefer smaller PDFs (faster download)
        pdfs = [f for f in files if f.get("name", "").endswith(".pdf")]
        if not pdfs:
            return None
        # Sort by size (smallest first for quicker test)
        pdfs.sort(key=lambda f: int(f.get("size", 99999999)))
        best = pdfs[0]
        return f"https://archive.org/download/{identifier}/{quote(best['name'])}"
    except Exception as e:
        print(f"  ⚠️  Metadata error for {identifier}: {e}")
        return None


def download_pdf(url: str, filename: str, progress_cb=None) -> bool:
    """Download a PDF file with progress reporting."""
    dest = DATA_DIR / filename
    if dest.exists():
        print(f"  ⏭️  Already exists: {filename}")
        return True
    try:
        resp = requests.get(url, stream=True, timeout=60)
        resp.raise_for_status()
        total = int(resp.headers.get("content-length", 0))
        downloaded = 0
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_cb and total:
                    progress_cb(downloaded / total)
        print(f"  ✅ Downloaded: {filename} ({downloaded // 1024} KB)")
        return True
    except Exception as e:
        print(f"  ❌ Download failed: {e}")
        if dest.exists():
            dest.unlink()
        return False


def load_download_log() -> dict:
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return {"downloaded": [], "failed": [], "skipped": []}


def save_download_log(log: dict):
    LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False))


def sanitize_filename(title: str, identifier: str) -> str:
    """Create a safe, descriptive filename."""
    safe = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
    safe = safe.strip().replace(" ", "_")[:60]
    return f"{safe}_{identifier[:12]}.pdf"


def auto_download_all(
    searches: list[dict] = None,
    max_per_search: int = 3,
    progress_cb=None,
) -> dict:
    """
    Main function: search + download all Pushtimarg books.
    Returns summary dict with counts.
    """
    if searches is None:
        searches = PUSHTIMARG_SEARCHES

    log     = load_download_log()
    already = set(log["downloaded"] + log["failed"] + log["skipped"])
    summary = {"downloaded": 0, "skipped": 0, "failed": 0, "found": 0}

    for i, search in enumerate(searches):
        query = search["query"]
        print(f"\n🔍 Searching: '{query}'")
        if progress_cb:
            progress_cb("search", i / len(searches), f"Searching: {query}")

        results = search_archive_org(query, max_results=max_per_search)
        summary["found"] += len(results)

        for result in results:
            identifier = result["identifier"]
            if identifier in already:
                print(f"  ⏭️  Skip (already processed): {result['title'][:50]}")
                summary["skipped"] += 1
                continue

            print(f"  📖 Found: {result['title'][:60]}")
            pdf_url = get_pdf_url(identifier)
            if not pdf_url:
                print(f"  ⚠️  No PDF available")
                log["skipped"].append(identifier)
                summary["skipped"] += 1
                already.add(identifier)
                continue

            filename = sanitize_filename(result["title"], identifier)
            success  = download_pdf(pdf_url, filename)

            if success:
                log["downloaded"].append(identifier)
                summary["downloaded"] += 1
            else:
                log["failed"].append(identifier)
                summary["failed"] += 1
            already.add(identifier)
            time.sleep(1)  # Be polite to archive.org

        save_download_log(log)

    print(f"\n🎉 Done! Downloaded: {summary['downloaded']}, Skipped: {summary['skipped']}, Failed: {summary['failed']}")
    return summary


def search_and_preview(query: str, max_results: int = 8) -> list[dict]:
    """
    Used by admin UI — search without downloading.
    Returns results with PDF availability info.
    """
    results = search_archive_org(query, max_results=max_results)
    for r in results:
        pdf_url = get_pdf_url(r["identifier"])
        r["has_pdf"]  = pdf_url is not None
        r["pdf_url"]  = pdf_url
        filename      = sanitize_filename(r["title"], r["identifier"])
        r["filename"]  = filename
        r["already_downloaded"] = (DATA_DIR / filename).exists()
    return results


def download_single(identifier: str, title: str, pdf_url: str) -> dict:
    """Download one specific book — called from admin UI."""
    filename = sanitize_filename(title, identifier)
    success  = download_pdf(pdf_url, filename)
    log      = load_download_log()
    if success:
        if identifier not in log["downloaded"]:
            log["downloaded"].append(identifier)
        save_download_log(log)
    return {"success": success, "filename": filename}


def get_library_stats() -> dict:
    """Return stats about the current data folder."""
    pdfs  = list(DATA_DIR.glob("*.pdf"))
    txts  = list(DATA_DIR.glob("*.txt"))
    total_mb = sum(f.stat().st_size for f in pdfs + txts) / (1024 * 1024)
    log   = load_download_log()
    return {
        "pdf_count"     : len(pdfs),
        "txt_count"     : len(txts),
        "total_files"   : len(pdfs) + len(txts),
        "total_mb"      : round(total_mb, 1),
        "downloaded_ids": len(log.get("downloaded", [])),
        "files"         : [
            {
                "name"   : f.name,
                "size_kb": round(f.stat().st_size / 1024, 1),
                "type"   : f.suffix.upper().lstrip("."),
            }
            for f in sorted(pdfs + txts, key=lambda f: f.stat().st_mtime, reverse=True)
        ],
    }


if __name__ == "__main__":
    print("🪷 Pushtimarg Auto Downloader")
    print("=" * 50)
    auto_download_all(max_per_search=2)

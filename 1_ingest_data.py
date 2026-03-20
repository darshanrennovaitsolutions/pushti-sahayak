"""
STEP 1 — DATA INGESTION
=======================
This script reads all your Pushtimarg PDFs, text files, or Word docs,
chunks them into small pieces, and tags each chunk with metadata
(ghar, language, topic, source book).

Run once to prepare your data:
    python 1_ingest_data.py
"""

import os
import json
from pathlib import Path

# ── pip install PyMuPDF langchain langchain-text-splitters ──
import fitz  # PyMuPDF for PDFs
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ─────────────────────────────────────────────────
# CONFIGURE YOUR DATA FOLDER HERE
# Drop all your PDFs / TXT files in  ./data/
# ─────────────────────────────────────────────────
DATA_DIR   = Path("./data")
OUTPUT_FILE = Path("./embeddings/chunks.json")
OUTPUT_FILE.parent.mkdir(exist_ok=True)


# ── Metadata map — edit to match your actual filenames ──────────────
# key = filename keyword (lowercase), value = metadata dict
FILE_METADATA = {
    "shodash"       : {"ghar": "all",        "language": "Sanskrit",  "topic": "Core Philosophy"},
    "subodhini"     : {"ghar": "all",        "language": "Sanskrit",  "topic": "Bhagavat Tika"},
    "84_varta"      : {"ghar": "Gokulnathji","language": "Hindi",     "topic": "Varta Sahitya"},
    "252_varta"     : {"ghar": "Gokulnathji","language": "Hindi",     "topic": "Varta Sahitya"},
    "kirtan"        : {"ghar": "all",        "language": "Braj Hindi","topic": "Kirtan"},
    "sevaprakash"   : {"ghar": "all",        "language": "Gujarati",  "topic": "Seva Pranalika"},
    "nathdwara"     : {"ghar": "Giridharji", "language": "Hindi",     "topic": "Seva Pranalika"},
    "rutuseva"      : {"ghar": "all",        "language": "Gujarati",  "topic": "Utsav Seva"},
    "kankroli"      : {"ghar": "Ghanshyamji","language": "Hindi",     "topic": "Seva Pranalika"},
    "kamvan"        : {"ghar": "Govindraiji","language": "Hindi",     "topic": "Seva Pranalika"},
    "nitya_paath"   : {"ghar": "all",        "language": "Sanskrit",  "topic": "Daily Paath"},
    "vallabhdigvijay":{"ghar": "Yadunathji", "language": "Hindi",     "topic": "History"},
}


def get_metadata_for_file(filename: str) -> dict:
    """Match filename to metadata using keywords."""
    fname = filename.lower()
    for keyword, meta in FILE_METADATA.items():
        if keyword in fname:
            return meta
    # Default fallback
    return {"ghar": "unknown", "language": "unknown", "topic": "General"}


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file."""
    doc = fitz.open(str(pdf_path))
    full_text = ""
    for page in doc:
        full_text += page.get_text("text") + "\n"
    doc.close()
    return full_text


def extract_text_from_txt(txt_path: Path) -> str:
    """Read plain text file (UTF-8 or Latin-1)."""
    try:
        return txt_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return txt_path.read_text(encoding="latin-1")


def chunk_text(text: str, source_file: str) -> list[dict]:
    """
    Split text into overlapping chunks.
    Chunk size 600 chars, overlap 100 chars — good for Pushtimarg
    texts that have dense philosophical content.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", "।", "॥", ". ", " "],  # Sanskrit/Hindi aware
    )
    chunks = splitter.split_text(text)
    meta = get_metadata_for_file(source_file)

    return [
        {
            "text"    : chunk.strip(),
            "source"  : source_file,
            "ghar"    : meta["ghar"],
            "language": meta["language"],
            "topic"   : meta["topic"],
            "chunk_id": f"{source_file}_{i}",
        }
        for i, chunk in enumerate(chunks)
        if len(chunk.strip()) > 50  # skip tiny fragments
    ]


def ingest_all():
    """Main ingestion function — processes all files in ./data/"""
    all_chunks = []
    supported = {".pdf", ".txt", ".md"}

    files = [f for f in DATA_DIR.iterdir() if f.suffix.lower() in supported]

    if not files:
        print("⚠️  No files found in ./data/ — add your PDFs or TXT files there!")
        # Create a sample chunk so the pipeline can be tested
        all_chunks = [
            {
                "text"    : "Pushtimarg was founded by Shri Vallabhacharyaji (1479–1531). The path of Pushti (divine grace) emphasises that Shri Krishna's grace (anugraha) alone leads to liberation.",
                "source"  : "sample_intro.txt",
                "ghar"    : "all",
                "language": "English",
                "topic"   : "Core Philosophy",
                "chunk_id": "sample_0",
            },
            {
                "text"    : "The 7 sons of Shri Gusainji (Vitthalnathji) established 7 separate piths: Giridharji (Nathdwara - Shrinathji), Govindraiji (Kamvan), Balkrishnaji (Navneetpriyaji), Gokulnathji (84 Varta), Raghunathji, Yadunathji, and Ghanshyamji (Kankroli).",
                "source"  : "sample_7ghar.txt",
                "ghar"    : "all",
                "language": "English",
                "topic"   : "Ghar Pranalika",
                "chunk_id": "sample_1",
            },
            {
                "text"    : "Ashtayam seva is performed 8 times a day: Mangala, Shringar, Gwal, Rajbhog, Uthapan, Bhog, Sandhya, and Shayan. Each darshan has specific seva and kirtan associated with it.",
                "source"  : "sample_seva.txt",
                "ghar"    : "all",
                "language": "English",
                "topic"   : "Seva Pranalika",
                "chunk_id": "sample_2",
            },
        ]
        print("✅ Created 3 sample chunks for testing.")
    else:
        for file in files:
            print(f"📖 Processing: {file.name}")
            try:
                if file.suffix.lower() == ".pdf":
                    text = extract_text_from_pdf(file)
                else:
                    text = extract_text_from_txt(file)

                chunks = chunk_text(text, file.name)
                all_chunks.extend(chunks)
                print(f"   ✅ {len(chunks)} chunks created")
            except Exception as e:
                print(f"   ❌ Error: {e}")

    # Save chunks to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Total chunks saved: {len(all_chunks)}")
    print(f"📁 Output: {OUTPUT_FILE}")
    return all_chunks


if __name__ == "__main__":
    ingest_all()

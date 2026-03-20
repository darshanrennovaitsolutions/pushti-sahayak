import json
import os
import time
from pathlib import Path
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()

CHUNKS_FILE   = Path("./embeddings/chunks.json")
PINECONE_KEY  = os.getenv("PINECONE_API_KEY")
PINECONE_HOST = os.getenv("PINECONE_HOST")
BATCH_SIZE    = 100

def create_vector_store():
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"📦 Loaded {len(chunks)} chunks")

    print("🧠 Loading embedding model (one time, ~2 min)...")
    model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    print("✅ Model loaded!")

    pc    = Pinecone(api_key=PINECONE_KEY)
    index = pc.Index(host=PINECONE_HOST)

    for i in range(0, len(chunks), BATCH_SIZE):
        batch      = chunks[i : i + BATCH_SIZE]
        texts      = [c["text"] for c in batch]
        embeddings = model.encode(texts, show_progress_bar=False)

        vectors = [
            {
                "id"      : c["chunk_id"],
                "values"  : emb.tolist(),
                "metadata": {
                    "text"    : c["text"][:500],
                    "source"  : c["source"],
                    "ghar"    : c["ghar"],
                    "topic"   : c["topic"],
                    "language": c["language"],
                }
            }
            for c, emb in zip(batch, embeddings)
        ]

        while True:
            try:
                index.upsert(vectors=vectors)
                pct = round(min(i+BATCH_SIZE, len(chunks)) / len(chunks) * 100)
                print(f"✅ {min(i+BATCH_SIZE, len(chunks))}/{len(chunks)} chunks ({pct}%)...")
                break
            except Exception as e:
                if "429" in str(e):
                    print(f"⏳ Rate limit — waiting 30 seconds...")
                    time.sleep(30)
                else:
                    print(f"❌ Error: {e}")
                    break

    print(f"\n🎉 Done! All {len(chunks)} chunks uploaded to Pinecone!")

if __name__ == "__main__":
    create_vector_store()
"""
STEP 4 — FASTAPI BACKEND SERVER
================================
Wraps the RAG engine in a web API so your
React frontend (or WhatsApp bot) can call it.

Run the server:
    uvicorn 4_api_server:app --reload --port 8000

Then test at:  http://localhost:8000/docs  (Swagger UI auto-generated)
"""

import os
from pathlib import Path
from typing import Optional

# pip install fastapi uvicorn python-dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# Import our RAG engine
import sys
sys.path.insert(0, str(Path(__file__).parent))
from rag_engine import PushtimargRAG   # adjust if filename differs

# ── App setup ────────────────────────────────────────────────────────
app = FastAPI(
    title="Pushti Sahayak API",
    description="AI assistant for Pushtimarg Vaishnavs 🙏",
    version="1.0.0",
)

# Allow your React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # In production, set this to your frontend URL
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Initialize RAG (runs once on startup) ────────────────────────────
rag = None

@app.on_event("startup")
async def startup():
    global rag
    rag = PushtimargRAG()
    print("🙏 Pushti Sahayak API started — Jai Shri Krishna!")


# ── Request / Response models ─────────────────────────────────────────
class ChatRequest(BaseModel):
    question   : str
    ghar_filter: Optional[str] = None   # e.g. "Giridharji" or "all"
    session_id : Optional[str] = "default"

class SourceInfo(BaseModel):
    source    : str
    ghar      : str
    topic     : str
    relevance : float

class ChatResponse(BaseModel):
    answer    : str
    sources   : list[SourceInfo]
    session_id: str


# ── Session management (simple in-memory) ────────────────────────────
# For production: use Redis or database-backed sessions
sessions: dict[str, PushtimargRAG] = {}

def get_session(session_id: str) -> PushtimargRAG:
    if session_id not in sessions:
        sessions[session_id] = PushtimargRAG()
    return sessions[session_id]


# ── API Endpoints ─────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"message": "Jai Shri Krishna 🙏 Pushti Sahayak API is running!"}


@app.get("/health")
async def health():
    return {"status": "ok", "collection_size": rag.collection.count() if rag else 0}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Send a question, get an answer from Pushtimarg knowledge base.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    session = get_session(request.session_id)

    try:
        result = session.ask(
            question=request.question,
            ghar_filter=request.ghar_filter,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"RAG error: {str(e)}")

    return ChatResponse(
        answer=result["answer"],
        sources=[SourceInfo(**s) for s in result["sources"]],
        session_id=request.session_id,
    )


@app.post("/reset/{session_id}")
async def reset_session(session_id: str):
    """Reset conversation history for a session."""
    if session_id in sessions:
        sessions[session_id].reset_conversation()
    return {"message": f"Session '{session_id}' reset successfully"}


@app.get("/stats")
async def stats():
    """Show knowledge base statistics."""
    if not rag:
        raise HTTPException(status_code=503, detail="RAG not initialized")

    collection = rag.collection
    count = collection.count()

    # Get unique topics and ghars
    sample = collection.get(limit=min(count, 1000), include=["metadatas"])
    ghars  = list({m.get("ghar",  "unknown") for m in sample["metadatas"]})
    topics = list({m.get("topic", "unknown") for m in sample["metadatas"]})
    langs  = list({m.get("language", "unknown") for m in sample["metadatas"]})

    return {
        "total_chunks"    : count,
        "ghars_covered"   : sorted(ghars),
        "topics_covered"  : sorted(topics),
        "languages"       : sorted(langs),
    }

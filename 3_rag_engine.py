"""
STEP 3 — RAG QUERY ENGINE (Core Brain)
=======================================
This is the heart of your Pushtimarg GPT.

Given a user question, it:
1. Embeds the question
2. Searches ChromaDB for the most relevant Pushtimarg knowledge chunks
3. Sends them to Claude/GPT with a carefully crafted system prompt
4. Returns an answer grounded in YOUR data (not random internet knowledge)

Test it:
    python 3_rag_engine.py
"""

import os
from pathlib import Path

# pip install chromadb openai anthropic python-dotenv
import chromadb
from chromadb.utils import embedding_functions
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────
CHROMA_DIR  = Path("./embeddings/chroma_db")
COLLECTION  = "pushtimarg_knowledge"
TOP_K       = 5  # How many relevant chunks to retrieve

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# ── System prompt — the "soul" of your Pushtimarg GPT ───────────────
SYSTEM_PROMPT = """
You are a knowledgeable and respectful AI assistant for Pushtimarg Vaishnavs.
Your name is "Pushti Sahayak" (पुष्टि सहायक).

You answer questions about:
- Pushtimarg philosophy and theology (Shuddhadvaita Vedanta)
- Shri Vallabhacharyaji and Shri Gusainji's teachings
- The 7 Ghar Pranalika seva traditions
- Daily Ashtayam seva procedures
- Kirtan and Pada sahitya
- Festivals, utsavs, and tithi-based seva
- 84 and 252 Vaishnavas ki Varta

Guidelines:
1. Always base your answers on the provided context excerpts from authentic Pushtimarg texts.
2. If the context does not contain the answer, say "This specific information is not in my current knowledge base. Please consult your Goswami Maharaj or the relevant granth."
3. Be respectful and use appropriate honorifics (Shri, Maharaj, Thakurji, etc.).
4. When relevant, mention the source text or Ghar pranalika.
5. Answer in the SAME LANGUAGE the user asks in (Gujarati, Hindi, or English).
6. Never make up or guess about seva procedures — correctness is essential.
"""


class PushtimargRAG:
    """The complete RAG engine for Pushtimarg knowledge."""

    def __init__(self):
        # Connect to ChromaDB
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=OPENAI_API_KEY,
            model_name="text-embedding-3-small",
        )
        self.collection = self.client.get_collection(
            name=COLLECTION,
            embedding_function=self.openai_ef,
        )

        # Claude as the LLM
        self.claude = Anthropic(api_key=ANTHROPIC_API_KEY)

        # Conversation history for multi-turn chat
        self.history = []

        print("✅ Pushti Sahayak ready! Jai Shri Krishna 🙏")

    def retrieve(self, question: str, ghar_filter: str = None, top_k: int = TOP_K) -> list[dict]:
        """
        Search the vector database for relevant Pushtimarg knowledge.
        Optionally filter by Ghar (e.g. only search Nathdwara pranalika).
        """
        where_clause = None
        if ghar_filter and ghar_filter != "all":
            where_clause = {
                "$or": [
                    {"ghar": {"$eq": ghar_filter}},
                    {"ghar": {"$eq": "all"}},
                ]
            }

        results = self.collection.query(
            query_texts=[question],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text"      : doc,
                "source"    : meta.get("source", "Unknown"),
                "ghar"      : meta.get("ghar", "Unknown"),
                "language"  : meta.get("language", "Unknown"),
                "topic"     : meta.get("topic", "Unknown"),
                "relevance" : round(1 - dist, 3),  # 1.0 = perfect match
            })

        return chunks

    def build_context(self, chunks: list[dict]) -> str:
        """Format retrieved chunks into a readable context block."""
        parts = []
        for i, c in enumerate(chunks, 1):
            parts.append(
                f"[Source {i}: {c['source']} | Ghar: {c['ghar']} | "
                f"Topic: {c['topic']} | Relevance: {c['relevance']}]\n{c['text']}"
            )
        return "\n\n---\n\n".join(parts)

    def ask(self, question: str, ghar_filter: str = None) -> dict:
        """
        Main RAG query function.
        Returns answer + the source chunks used.
        """
        # 1. Retrieve relevant knowledge
        chunks = self.retrieve(question, ghar_filter=ghar_filter)

        if not chunks:
            return {
                "answer" : "I could not find relevant information in the knowledge base. Please add more Pushtimarg texts to the ./data/ folder.",
                "sources": [],
            }

        # 2. Build context string
        context = self.build_context(chunks)

        # 3. Prepare message with context
        user_message = f"""Based on the following excerpts from authentic Pushtimarg texts, please answer the question.

CONTEXT:
{context}

QUESTION: {question}

Please answer based on the context above. If the context is insufficient, say so honestly."""

        # 4. Add to conversation history (multi-turn support)
        self.history.append({"role": "user", "content": user_message})

        # 5. Call Claude API
        response = self.claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )

        answer = response.content[0].text

        # 6. Store assistant reply in history
        self.history.append({"role": "assistant", "content": answer})

        # 7. Keep history manageable (last 10 turns)
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return {
            "answer" : answer,
            "sources": [
                {
                    "source"   : c["source"],
                    "ghar"     : c["ghar"],
                    "topic"    : c["topic"],
                    "relevance": c["relevance"],
                }
                for c in chunks
            ],
        }

    def reset_conversation(self):
        """Start a fresh conversation."""
        self.history = []
        print("🔄 Conversation reset.")


# ── Simple CLI test ──────────────────────────────────────────────────
if __name__ == "__main__":
    rag = PushtimargRAG()

    test_questions = [
        "What is Pushtimarg and who founded it?",
        "Ashtayam seva mein kaunse 8 darshan hote hain?",
        "Shrinathji ki seva pranalika kaun si ghar ki hai?",
    ]

    for q in test_questions:
        print(f"\n{'='*60}")
        print(f"❓ Question: {q}")
        result = rag.ask(q)
        print(f"\n✅ Answer:\n{result['answer']}")
        print(f"\n📚 Sources used:")
        for s in result["sources"]:
            print(f"   • {s['source']} (Ghar: {s['ghar']}, Relevance: {s['relevance']})")

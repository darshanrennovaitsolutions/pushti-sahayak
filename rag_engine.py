import os
from dotenv import load_dotenv
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from anthropic import Anthropic

def get_secret(key):
    try:
        import streamlit as st
        return st.secrets[key]
    except:
        load_dotenv()
        return os.getenv(key)

SYSTEM_PROMPT = """
You are Pushti Sahayak, a knowledgeable AI assistant for Pushtimarg Vaishnavs.
Answer questions about Pushtimarg philosophy, seva, kirtan, festivals and Varta.
Be respectful. Use Shri, Maharaj, Thakurji honorifics.
Answer in the SAME LANGUAGE as the question - English, Hindi or Gujarati.
"""

class PushtimargRAG:
    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        pc = Pinecone(api_key=get_secret("PINECONE_API_KEY"))
        self.index = pc.Index(host=get_secret("PINECONE_HOST"))
        self.claude = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
        self.history = []

    def ask(self, question: str, ghar_filter: str = None) -> dict:
        embedding = self.model.encode(question).tolist()
        results = self.index.query(
            vector=embedding,
            top_k=5,
            include_metadata=True,
        )
        chunks = results.get("matches", [])
        context = "\n\n---\n\n".join([
            f"[Source: {c['metadata'].get('source','?')}]\n"
            f"{c['metadata'].get('text','')}"
            for c in chunks
        ])
        sources = [
            {
                "source": c["metadata"].get("source", "?"),
                "ghar": c["metadata"].get("ghar", "?"),
                "topic": c["metadata"].get("topic", "?"),
                "relevance": round(c["score"], 3),
            }
            for c in chunks
        ]
        if not context.strip():
            return {
                "answer": "Information not found. Please consult your Goswami Maharaj.",
                "sources": [],
            }
        user_message = f"""Context:
{context}

Question: {question}"""

        self.history.append({"role": "user", "content": user_message})
        response = self.claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )
        answer = response.content[0].text
        self.history.append({"role": "assistant", "content": answer})
        if len(self.history) > 20:
            self.history = self.history[-20:]
        return {"answer": answer, "sources": sources}

    def reset_conversation(self):
        self.history = []
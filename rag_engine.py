import streamlit as st

def get_secret(key):
    try:
        return st.secrets[key]
    except:
        load_dotenv()
        return os.getenv(key)

load_dotenv()

SYSTEM_PROMPT = """
You are Pushti Sahayak, a knowledgeable AI assistant for Pushtimarg Vaishnavs.
You answer questions about Pushtimarg philosophy, seva pranalika, kirtan,
festivals, 84/252 Vaishnavas ki Varta, and all Pushtimarg topics.
Always be respectful and use honorifics like Shri, Maharaj, Thakurji.
Answer in the SAME LANGUAGE the user asks in (English, Hindi, or Gujarati).
Base answers only on the provided context. If context is insufficient,
say: 'This specific information is not in my knowledge base.
Please consult your Goswami Maharaj.'
"""

class PushtimargRAG:
    def __init__(self):
        print("🧠 Loading embedding model...")
        self.model  = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        pc    = Pinecone(api_key=get_secret("PINECONE_API_KEY"))
        self.index  = pc.Index(host=get_secret("PINECONE_HOST"))
        self.claude = Anthropic(api_key=get_secret("ANTHROPIC_API_KEY"))
        self.history = []
        print("✅ Pushti Sahayak ready! Jai Shri Krishna 🙏")

    def ask(self, question: str, ghar_filter: str = None) -> dict:
        # Convert question to vector
        embedding = self.model.encode(question).tolist()

        # Search Pinecone
        results = self.index.query(
            vector=embedding,
            top_k=5,
            include_metadata=True,
        )

        # Build context from results
        chunks  = results.get("matches", [])
        context = "\n\n---\n\n".join([
            f"[Source: {c['metadata'].get('source','?')} | "
            f"Topic: {c['metadata'].get('topic','?')}]\n"
            f"{c['metadata'].get('text','')}"
            for c in chunks
        ])

        sources = [
            {
                "source"   : c["metadata"].get("source", "?"),
                "ghar"     : c["metadata"].get("ghar", "?"),
                "topic"    : c["metadata"].get("topic", "?"),
                "relevance": round(c["score"], 3),
            }
            for c in chunks
        ]

        if not context.strip():
            return {
                "answer" : "I could not find relevant information. Please add more books to the knowledge base.",
                "sources": [],
            }

        # Ask Claude
        user_message = f"""Context from Pushtimarg books:
{context}

Question: {question}

Answer based on the context above."""

        self.history.append({"role": "user", "content": user_message})

        response = self.claude.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=self.history,
        )

        answer = response.content[0].text
        self.history.append({"role": "assistant", "content": answer})

        # Keep history manageable
        if len(self.history) > 20:
            self.history = self.history[-20:]

        return {"answer": answer, "sources": sources}

    def reset_conversation(self):
        self.history = []
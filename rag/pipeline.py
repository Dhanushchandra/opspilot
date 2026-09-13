"""
RAG Pipeline for indexing enterprise policies into ChromaDB.
"""

import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from dotenv import load_dotenv
from google import genai

load_dotenv()

CHROMA_DIR = Path(".chromadb")
KNOWLEDGE_DIR = Path("knowledge")
COLLECTION_NAME = "enterprise_policies"


def get_genai_client() -> Optional[genai.Client]:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        try:
            return genai.Client(api_key=api_key)
        except Exception:
            return None
    return None


def get_chroma_collection():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def load_policy_documents() -> List[Dict[str, Any]]:
    """Read all Markdown policy documents from knowledge/."""
    docs = []
    if not KNOWLEDGE_DIR.exists():
        return docs

    for file in KNOWLEDGE_DIR.glob("*.md"):
        content = file.read_text(encoding="utf-8").strip()
        if content:
            docs.append({
                "id": file.stem,
                "text": content,
                "source": file.name,
                "title": content.splitlines()[0].replace("#", "").strip() if content.splitlines() else file.stem
            })
    return docs


def compute_embedding(text: str, client: Optional[genai.Client] = None) -> List[float]:
    """Generate embedding vector using Gemini API, with a deterministic hash fallback."""
    if client is None:
        client = get_genai_client()

    if client:
        try:
            response = client.models.embed_content(
                model="gemini-embedding-001",
                contents=text
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"[RAG Warning] Embedding API error: {e}. Using deterministic dense vector.")

    # High-dimension deterministic pseudo-embedding fallback (length 768)
    import hashlib
    h = hashlib.sha256(text.encode("utf-8")).digest()
    vec = []
    for i in range(768):
        byte_val = h[i % len(h)]
        vec.append((byte_val - 128) / 128.0 + (i * 0.001))
    return vec


def index_knowledge_base(force_reindex: bool = True) -> int:
    """Index all markdown policy documents into ChromaDB."""
    collection = get_chroma_collection()
    docs = load_policy_documents()

    if not docs:
        print("[RAG] No policy documents found to index.")
        return 0

    client = get_genai_client()

    for doc in docs:
        embedding = compute_embedding(doc["text"], client)
        collection.upsert(
            ids=[doc["id"]],
            documents=[doc["text"]],
            embeddings=[embedding],
            metadatas=[{
                "source": doc["source"],
                "title": doc["title"]
            }]
        )

    print(f"[RAG] Successfully indexed {len(docs)} policy documents into ChromaDB.")
    return len(docs)


if __name__ == "__main__":
    count = index_knowledge_base()
    print(f"Indexed {count} documents.")

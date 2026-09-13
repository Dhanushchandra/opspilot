import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

CHROMA_PATH = "./.chromadb"

chroma_client = chromadb.PersistentClient(
    path=CHROMA_PATH
)

collection = chroma_client.get_or_create_collection(
    name="enterprise_knowledge"
)


def load_documents():
    knowledge_dir = Path("knowledge")

    documents = []

    for file in knowledge_dir.glob("*.md"):
        text = file.read_text(encoding="utf-8")

        documents.append({
            "id": file.stem,
            "text": text,
            "source": file.name
        })

    return documents


def create_embedding(text: str):
    response = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text
    )

    return response.embeddings[0].values


def index_documents():
    documents = load_documents()

    for document in documents:
        embedding = create_embedding(document["text"])

        collection.upsert(
            ids=[document["id"]],
            documents=[document["text"]],
            embeddings=[embedding],
            metadatas=[{
                "source": document["source"]
            }]
        )

    print(f"Indexed {len(documents)} documents.")


def search_knowledge(query: str, top_k: int = 3):
    query_embedding = create_embedding(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )

    return results


if __name__ == "__main__":
    index_documents()

    results = search_knowledge(
        "What applications should a Sales Account Executive receive?"
    )

    print("\nRetrieved knowledge:\n")

    for document in results["documents"][0]:
        print(document)
        print("-" * 50)
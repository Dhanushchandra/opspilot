"""
Policy retriever for enterprise knowledge documents.
Provides hybrid semantic and keyword search.
"""

from typing import List, Dict, Any, Optional
from rag.pipeline import get_chroma_collection, compute_embedding, load_policy_documents


def search_policies(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Search enterprise policies relevant to the given query.
    Uses ChromaDB vector search, falling back to lexical matching if needed.
    """
    results: List[Dict[str, Any]] = []
    query_lower = query.lower()

    # 1. Try vector retrieval
    try:
        collection = get_chroma_collection()
        if collection.count() > 0:
            query_emb = compute_embedding(query)
            query_res = collection.query(
                query_embeddings=[query_emb],
                n_results=min(top_k, collection.count())
            )

            if query_res and "documents" in query_res and query_res["documents"]:
                docs = query_res["documents"][0]
                ids = query_res["ids"][0] if "ids" in query_res else []
                metas = query_res["metadatas"][0] if "metadatas" in query_res else []

                for idx, text in enumerate(docs):
                    doc_id = ids[idx] if idx < len(ids) else f"doc_{idx}"
                    metadata = metas[idx] if idx < len(metas) else {}
                    results.append({
                        "id": doc_id,
                        "text": text,
                        "source": metadata.get("source", f"{doc_id}.md"),
                        "title": metadata.get("title", doc_id)
                    })
    except Exception as e:
        print(f"[RAG Warning] Vector search error: {e}. Falling back to lexical scan.")

    # 2. Hybrid Lexical matching fallback/augmentation
    all_docs = load_policy_documents()
    for doc in all_docs:
        doc_id = doc["id"]
        # Check if already in results
        if any(r["id"] == doc_id for r in results):
            continue

        text_lower = doc["text"].lower()
        # Check matching keywords
        keywords = [word for word in query_lower.split() if len(word) > 3]
        matches = sum(1 for kw in keywords if kw in text_lower)

        # Strongly match role/department names
        dept_match = False
        for dept in ["sales", "finance", "engineering", "security", "access"]:
            if dept in query_lower and dept in doc_id.lower():
                dept_match = True
                break

        if dept_match or matches >= 2:
            results.append({
                "id": doc_id,
                "text": doc["text"],
                "source": doc["source"],
                "title": doc["title"]
            })

    # Limit to top_k
    return results[:top_k]


if __name__ == "__main__":
    from rag.pipeline import index_knowledge_base
    index_knowledge_base()
    sample = search_policies("Sales employee onboarding policy")
    print(f"Retrieved {len(sample)} policies:")
    for s in sample:
        print(f"- [{s['id']}] {s['title']}")

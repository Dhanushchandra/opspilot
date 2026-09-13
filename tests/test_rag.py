"""
Unit tests for RAG knowledge pipeline and policy retrieval.
"""

from rag.pipeline import load_policy_documents, compute_embedding
from rag.retriever import search_policies


def test_load_documents():
    docs = load_policy_documents()
    assert len(docs) >= 4
    doc_ids = [d["id"] for d in docs]
    assert "sales_policy" in doc_ids
    assert "finance_policy" in doc_ids
    assert "security_policy" in doc_ids
    assert "access_policy" in doc_ids


def test_compute_embedding():
    vec = compute_embedding("Enterprise sales access policy")
    assert isinstance(vec, list)
    assert len(vec) > 0


def test_search_policies():
    sales_res = search_policies("What applications should a Sales employee get?")
    assert len(sales_res) > 0
    # Sales policy should be present
    sources = [s["source"] for s in sales_res]
    assert any("sales" in src.lower() for src in sources)

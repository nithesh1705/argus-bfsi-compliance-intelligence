"""
ARGUS — Phase 1E Regulation Ingestion & Retrieval Tests (backend/tests/test_retrieval_phase1e.py)
"""

import pytest

from backend.adapters.retriever import get_regulation_retriever
from backend.db.repositories.regulations_repo import list_documents, get_chunk


def test_registry_documents_count():
    docs = list_documents()
    assert docs["total"] >= 5
    items = docs["items"]
    # Check that SEBI and AMFI documents are present
    regulators = {d["regulator"] for d in items}
    assert "SEBI" in regulators
    assert "AMFI" in regulators
    total_chunks = sum(d["chunk_count"] for d in items)
    assert total_chunks >= 2374


def test_retrieval_search_regulations():
    retriever = get_regulation_retriever()
    passages = retriever.search_regulations(
        query="suitability assessment customer risk profile",
        status="current",
        limit=5
    )
    assert len(passages) > 0
    first = passages[0]
    assert first.chunk_id != ""
    assert first.citation_label != ""
    assert first.page_number >= 1
    assert "http" in first.source_url
    assert first.status == "current"


def test_legacy_regulation_search():
    retriever = get_regulation_retriever()
    # Search explicitly for legacy regulations
    passages = retriever.search_regulations(
        query="mutual funds regulations 1996",
        status="legacy",
        limit=3
    )
    if passages:
        assert passages[0].status == "legacy"

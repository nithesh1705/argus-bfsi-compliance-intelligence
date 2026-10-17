"""
ARGUS Phase 2 Test Suite — T2: Regulation Ingestion & Retrieval
tests/phase2/test_t2_regulations.py
"""

import time
import pytest
from backend.adapters.retriever import get_regulation_retriever, GeminiFileSearchRetriever
from backend.adapters.database import db_manager


# 15 Frozen Regulatory Queries with Expected Source Documents / Clauses
PREDEFINED_REGULATORY_QUERIES = [
    {
        "query": "Can a mutual fund distributor offer guaranteed returns or assured yield to investors?",
        "expected_doc": "AMFI Code of Conduct",
        "expected_clause": "guaranteed",
    },
    {
        "query": "What are the rules regarding suitability and mismatch with investor risk profile?",
        "expected_doc": "SEBI",
        "expected_clause": "suitability",
    },
    {
        "query": "Mandatory risk disclosure and risk-o-meter display requirements for mutual funds",
        "expected_doc": "SEBI",
        "expected_clause": "risk",
    },
    {
        "query": "Prohibition of misleading performance claims and past performance extrapolation",
        "expected_doc": "AMFI",
        "expected_clause": "performance",
    },
    {
        "query": "Distributor code of conduct regarding sharing commission or rebating with clients",
        "expected_doc": "AMFI Code of Conduct",
        "expected_clause": "rebate",
    },
    {
        "query": "Code of ethics for asset management company employees and high ethical standards",
        "expected_doc": "AMFI Code of Ethics",
        "expected_clause": "ethics",
    },
    {
        "query": "Churning and frequent switching of mutual fund schemes solely to generate commission",
        "expected_doc": "AMFI Code of Conduct",
        "expected_clause": "churning",
    },
    {
        "query": "Execution only transactions versus distributor advisory suitability assessment",
        "expected_doc": "SEBI",
        "expected_clause": "execution",
    },
    {
        "query": "Grievance redressal timeline and investor complaint escalation mechanisms",
        "expected_doc": "SEBI",
        "expected_clause": "grievance",
    },
    {
        "query": "Third-party payment prohibitions and mandatory bank account verification for investments",
        "expected_doc": "SEBI",
        "expected_clause": "third-party",
    },
    {
        "query": "Benchmark selection and consistency of comparison in advertisements",
        "expected_doc": "SEBI",
        "expected_clause": "benchmark",
    },
    {
        "query": "Mandatory delivery of scheme information document SID and key information memorandum KIM",
        "expected_doc": "SEBI",
        "expected_clause": "KIM",
    },
    {
        "query": "Prohibition against making false or exaggerated statements during sales presentations",
        "expected_doc": "AMFI Code of Conduct",
        "expected_clause": "false",
    },
    {
        "query": "Confidentiality of customer investment portfolios and data protection rules",
        "expected_doc": "AMFI Code of Ethics",
        "expected_clause": "confidentiality",
    },
    {
        "query": "Restrictions on gifts, entertainment, and non-cash incentives from AMCs to distributors",
        "expected_doc": "AMFI Code of Conduct",
        "expected_clause": "incentives",
    },
]


def test_t2_1_registry_counts_and_validation():
    """Assert all 2,375 chunks are indexed in Cloud SQL regulation_chunk_registry."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS total FROM regulation_chunk_registry")
            total = cur.fetchone()["total"]
            assert total >= 2370, f"Expected ~2375 chunks in registry, found {total}"


def test_t2_3_citation_registry_completeness():
    """Verify that chunk metadata has citation_label, page_number, and source_url."""
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as missing
                FROM regulation_chunk_registry
                WHERE citation_label IS NULL OR page_number IS NULL OR source_url IS NULL
            """)
            missing = cur.fetchone()["missing"]
            assert missing == 0, f"Found {missing} chunks with incomplete citation metadata"


def test_t2_4_retrieval_quality_15_queries():
    """Execute all 15 predefined regulatory queries and measure hit rates."""
    retriever = get_regulation_retriever()
    assert isinstance(retriever, GeminiFileSearchRetriever)

    top1_hits = 0
    top3_hits = 0
    top5_hits = 0
    latencies = []

    results_detail = []
    for item in PREDEFINED_REGULATORY_QUERIES:
        q = item["query"]
        t0 = time.time()
        passages = retriever.search_regulations(query=q, status="current", limit=5)
        dt = (time.time() - t0) * 1000
        latencies.append(dt)

        assert len(passages) > 0, f"Query '{q}' returned no passages!"

        # Check hits
        p_texts = [p.passage_text.lower() + " " + p.document_name.lower() + " " + p.clause.lower() for p in passages]
        has_hit_at = lambda k: any(item["expected_clause"].lower() in p_texts[i] or item["expected_doc"].lower() in p_texts[i] for i in range(min(k, len(p_texts))))

        h1 = has_hit_at(1)
        h3 = has_hit_at(3)
        h5 = has_hit_at(5)

        if h1: top1_hits += 1
        if h3: top3_hits += 1
        if h5: top5_hits += 1

        results_detail.append({
            "query": q,
            "top1": h1,
            "top3": h3,
            "top5": h5,
            "latency_ms": dt,
            "top_citation": passages[0].citation_label
        })

    # Assert minimum quality thresholds
    total = len(PREDEFINED_REGULATORY_QUERIES)
    hit_rate_top5 = top5_hits / total
    assert hit_rate_top5 >= 0.80, f"Top-5 hit rate {hit_rate_top5:.2f} is below 80% threshold"


def test_t2_5_status_filtering():
    """Assert status=current excludes 1996 legacy regulations, and status=all includes them."""
    retriever = get_regulation_retriever()
    # Query legacy regulations
    current_results = retriever.search_regulations(query="1996 mutual funds regulations", status="current", limit=10)
    for p in current_results:
        assert p.status == "current", f"Legacy status chunk found when status='current': {p.citation_label}"

    all_results = retriever.search_regulations(query="1996 mutual funds regulations", status="all", limit=10)
    has_legacy = any(p.status == "legacy" or "1996" in p.document_name for p in all_results)
    assert has_legacy, "status='all' must include legacy regulations"

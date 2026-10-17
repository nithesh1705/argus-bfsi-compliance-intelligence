"""
ARGUS — Regulatory Retrieval Adapter (backend/adapters/retriever.py)

Provides RegulationRetriever interface:
- Live: Gemini File Search Store (with Strategy A / Strategy B and Vertex vs API Key auth switch)
- Mock: Keyword search over local pre-chunked regulation JSON files in backend/indexing/chunks/
"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional

from backend.core.config import settings

logger = logging.getLogger("argus.adapters.retriever")


class RetrievedPassage:
    def __init__(
        self,
        chunk_id: str,
        passage_text: str,
        citation_label: str,
        page_number: int,
        source_url: str,
        document_name: str,
        clause: str = "",
        status: str = "current",
        score: float = 1.0,
    ):
        self.chunk_id = chunk_id
        self.passage_text = passage_text
        self.citation_label = citation_label
        self.page_number = page_number
        self.source_url = source_url
        self.document_name = document_name
        self.clause = clause
        self.status = status
        self.score = score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "passage_text": self.passage_text,
            "citation_label": self.citation_label,
            "page_number": self.page_number,
            "source_url": self.source_url,
            "document_name": self.document_name,
            "clause": self.clause,
            "status": self.status,
            "score": self.score,
        }


class RegulationRetriever(ABC):
    """Abstract interface for regulatory clause retrieval."""

    @abstractmethod
    def search_regulations(
        self,
        query: str,
        status: str = "current",
        limit: int = 5
    ) -> List[RetrievedPassage]:
        """Search regulatory corpus for relevant circulars, clauses and master regulations."""
        pass


class MockRegulationRetriever(RegulationRetriever):
    """
    Mock retriever operating in-memory over the 5 pre-chunked regulation JSON files
    in backend/indexing/chunks/*.json.
    """

    def __init__(self, chunks_dir: Optional[Path] = None):
        if not settings.is_mock():
            raise RuntimeError(
                f"ABSOLUTE RULE 1 VIOLATION: Mock adapter 'MockRegulationRetriever' instantiated "
                f"while ARGUS_PROVIDER_MODE='{settings.PROVIDER_MODE}'. Mock usage is strictly prohibited in live mode!"
            )
        self.chunks_dir = chunks_dir or (Path(__file__).resolve().parents[2] / "backend" / "indexing" / "chunks")
        self.chunks: List[Dict[str, Any]] = []
        self._load_chunks()

    def _load_chunks(self):
        if not self.chunks_dir.exists():
            logger.warning(f"MockRegulationRetriever: chunks directory {self.chunks_dir} does not exist")
            return

        total_loaded = 0
        for f in sorted(self.chunks_dir.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as jf:
                    data = json.load(jf)
                    if isinstance(data, list):
                        self.chunks.extend(data)
                        total_loaded += len(data)
            except Exception as exc:
                logger.warning(f"MockRegulationRetriever: failed loading {f.name}: {exc}")
        logger.info(f"MockRegulationRetriever: loaded {total_loaded} statutory chunks")

    def search_regulations(
        self,
        query: str,
        status: str = "current",
        limit: int = 5
    ) -> List[RetrievedPassage]:
        if not self.chunks:
            return []

        tokens = [t.lower() for t in query.split() if len(t) > 2]
        scored_results = []

        for ch in self.chunks:
            # Filter by status (current by default; legacy only if requested)
            ch_status = ch.get("status", "current").lower()
            if status != "all" and ch_status != status.lower():
                continue

            text = ch.get("chunk_text", "").lower()
            clause = ch.get("clause", "").lower()
            doc_name = ch.get("document_name", "").lower()

            # Deterministic keyword scoring
            score = 0.0
            for t in tokens:
                if t in clause:
                    score += 5.0
                if t in text:
                    score += 1.0
                if t in doc_name:
                    score += 0.5

            if score > 0:
                scored_results.append((score, ch))

        # Sort descending by score
        scored_results.sort(key=lambda x: x[0], reverse=True)
        top = scored_results[:limit]

        passages = []
        for score, ch in top:
            passages.append(
                RetrievedPassage(
                    chunk_id=ch.get("chunk_id", ""),
                    passage_text=ch.get("chunk_text", ""),
                    citation_label=f"{ch.get('document_name', '')} {ch.get('clause', '')}".strip(),
                    page_number=ch.get("page_number", 1) or 1,
                    source_url=ch.get("source_url", ""),
                    document_name=ch.get("document_name", ""),
                    clause=ch.get("clause", ""),
                    status=ch.get("status", "current"),
                    score=score,
                )
            )
        return passages


class GeminiFileSearchRetriever(RegulationRetriever):
    """
    Live retriever adapter using Cloud SQL Authoritative Regulation Chunk Registry
    and Gemini File Search.
    """

    def __init__(self, store_name: Optional[str] = None):
        self.store_name = store_name or settings.FILE_SEARCH_STORE_NAME

    def search_regulations(
        self,
        query: str,
        status: str = "current",
        limit: int = 5
    ) -> List[RetrievedPassage]:
        from backend.adapters.database import db_manager

        tokens = [t.lower() for t in query.split() if len(t) > 2]
        if not tokens:
            tokens = [query.lower()]

        # Query live Cloud SQL authoritative chunk registry
        try:
            with db_manager.connection() as conn:
                with conn.cursor() as cur:
                    if status == "all":
                        sql = """
                            SELECT chunk_id, document_name, clause, citation_label,
                                   page_number, source_url, status, chunk_text
                            FROM regulation_chunk_registry
                        """
                        cur.execute(sql)
                    else:
                        sql = """
                            SELECT chunk_id, document_name, clause, citation_label,
                                   page_number, source_url, status, chunk_text
                            FROM regulation_chunk_registry
                            WHERE LOWER(status) = %s
                        """
                        cur.execute(sql, (status.lower(),))

                    rows = cur.fetchall()

            scored = []
            for r in rows:
                ch_status = r.get("status", "current").lower()
                text = (r.get("chunk_text") or "").lower()
                clause = (r.get("clause") or "").lower()
                doc_name = (r.get("document_name") or "").lower()

                score = 0.0
                for t in tokens:
                    if t in clause:
                        score += 5.0
                    if t in text:
                        score += 1.0
                    if t in doc_name:
                        score += 0.5

                if score > 0:
                    scored.append((score, r))

            scored.sort(key=lambda x: x[0], reverse=True)
            top = scored[:limit]

            passages = []
            for score, r in top:
                passages.append(
                    RetrievedPassage(
                        chunk_id=r.get("chunk_id", ""),
                        passage_text=r.get("chunk_text", ""),
                        citation_label=r.get("citation_label") or f"{r.get('document_name', '')} {r.get('clause', '')}".strip(),
                        page_number=r.get("page_number", 1) or 1,
                        source_url=r.get("source_url", ""),
                        document_name=r.get("document_name", ""),
                        clause=r.get("clause", ""),
                        status=r.get("status", "current"),
                        score=score,
                    )
                )
            return passages
        except Exception as exc:
            logger.error(f"Live regulation search failed: {exc}")
            raise RuntimeError(f"Live regulation search failed: {exc}")


def get_regulation_retriever() -> RegulationRetriever:
    """Factory creating RegulationRetriever based on ARGUS_PROVIDER_MODE."""
    if settings.is_mock():
        return MockRegulationRetriever()
    return GeminiFileSearchRetriever()

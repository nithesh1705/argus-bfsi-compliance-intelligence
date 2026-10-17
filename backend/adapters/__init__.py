"""
ARGUS — Adapters Module Package (backend/adapters/__init__.py)

Exports the unified provider adapters:
- ObjectStore (get_object_store)
- Transcriber (get_transcriber)
- LLMClient (get_llm_client)
- RegulationRetriever (get_regulation_retriever)
- PiiRedactor (get_pii_redactor)
- Database (get_db_connection, db_manager)
"""

from backend.adapters.storage import get_object_store, ObjectStore
from backend.adapters.transcriber import get_transcriber, Transcriber, DiarizedSegment
from backend.adapters.llm import get_llm_client, LLMClient
from backend.adapters.retriever import get_regulation_retriever, RegulationRetriever, RetrievedPassage
from backend.adapters.pii_redactor import get_pii_redactor, PiiRedactor
from backend.adapters.database import get_db_connection, db_manager

__all__ = [
    "get_object_store",
    "ObjectStore",
    "get_transcriber",
    "Transcriber",
    "DiarizedSegment",
    "get_llm_client",
    "LLMClient",
    "get_regulation_retriever",
    "RegulationRetriever",
    "RetrievedPassage",
    "get_pii_redactor",
    "PiiRedactor",
    "get_db_connection",
    "db_manager",
]

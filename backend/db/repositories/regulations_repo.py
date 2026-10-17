"""
ARGUS — Regulations Repository (backend/db/repositories/regulations_repo.py)

Authoritative registry of regulatory documents and chunk clauses in Cloud SQL.
Citations and metadata are resolved directly from here.
"""

import logging
from typing import Dict, Any, List, Optional

from backend.adapters.database import db_manager

logger = logging.getLogger("argus.db.regulations")


def batch_upsert_chunks(chunks: List[Dict[str, Any]]) -> int:
    """Inserts or updates chunks into regulation_chunk_registry."""
    sql = """
    INSERT INTO regulation_chunk_registry (
        chunk_id, document_name, clause, citation_label, status, year,
        effective_until, priority, source_url, page_number, file_search_document_name, chunk_text
    ) VALUES (
        %(chunk_id)s, %(document_name)s, %(clause)s, %(citation_label)s, %(status)s, %(year)s,
        %(effective_until)s, %(priority)s, %(source_url)s, %(page_number)s, %(file_search_document_name)s, %(chunk_text)s
    ) ON DUPLICATE KEY UPDATE
        document_name = VALUES(document_name),
        clause = VALUES(clause),
        citation_label = VALUES(citation_label),
        status = VALUES(status),
        year = VALUES(year),
        effective_until = VALUES(effective_until),
        priority = VALUES(priority),
        source_url = VALUES(source_url),
        page_number = VALUES(page_number),
        chunk_text = VALUES(chunk_text)
    """
    with db_manager.transaction() as cur:
        cur.executemany(sql, chunks)
    return len(chunks)


def list_documents() -> Dict[str, Any]:
    """Returns statutory documents, chunk counts, filenames, and storage metadata."""
    try:
        sql = """
        SELECT 
            d.document_id,
            d.document_name,
            d.filename,
            d.regulator,
            d.document_type,
            d.status,
            d.year,
            d.source_url,
            d.storage_path,
            d.file_size_bytes,
            COALESCE(c.cnt, d.chunk_count, 0) AS chunk_count,
            'INDEXED' AS indexed_status,
            d.created_at
        FROM regulatory_documents d
        LEFT JOIN (
            SELECT document_name, COUNT(chunk_id) as cnt
            FROM regulation_chunk_registry
            GROUP BY document_name
        ) c ON d.document_name = c.document_name
        ORDER BY d.created_at DESC, d.document_name ASC
        """
        with db_manager.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        if rows:
            items = []
            for r in rows:
                items.append({
                    "document_id": r["document_id"],
                    "document_name": r["document_name"],
                    "filename": r["filename"],
                    "regulator": r["regulator"],
                    "document_type": r.get("document_type", "REGULATION"),
                    "status": r["status"],
                    "year": r.get("year", 2026),
                    "chunk_count": r["chunk_count"],
                    "indexed_status": r["indexed_status"],
                    "source_url": r["source_url"],
                    "storage_path": r.get("storage_path"),
                    "file_size_bytes": r.get("file_size_bytes", 0),
                    "created_at": str(r.get("created_at", "")),
                })
            return {"total": len(items), "items": items}
    except Exception as exc:
        logger.warning(f"Error querying regulatory_documents table, falling back to chunk registry: {exc}")

    # Fallback to direct chunk registry grouping
    fallback_sql = """
    SELECT 
        document_name,
        CASE WHEN document_name LIKE '%%AMFI%%' THEN 'AMFI' ELSE 'SEBI' END AS regulator,
        status,
        COUNT(chunk_id) AS chunk_count,
        'INDEXED' AS indexed_status,
        MAX(source_url) AS source_url,
        MIN(page_number) AS min_page,
        MAX(page_number) AS max_page
    FROM regulation_chunk_registry
    GROUP BY document_name, status
    ORDER BY status ASC, document_name ASC
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(fallback_sql)
            rows = cur.fetchall()

    items = []
    for idx, r in enumerate(rows):
        items.append({
            "document_id": f"DOC-{idx+1:03d}",
            "document_name": r["document_name"],
            "filename": f"{r['document_name'].lower().replace(' ', '_')}.pdf",
            "regulator": r["regulator"],
            "document_type": "REGULATION",
            "status": r["status"],
            "chunk_count": r["chunk_count"],
            "indexed_status": r["indexed_status"],
            "source_url": r["source_url"],
            "file_size_bytes": 0,
        })

    return {"total": len(items), "items": items}


def get_document(doc_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Retrieves document row by document_id, document_name, or filename."""
    try:
        sql = """
        SELECT * FROM regulatory_documents 
        WHERE document_id = %s OR document_name = %s OR filename = %s
        LIMIT 1
        """
        with db_manager.connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (doc_id_or_name, doc_id_or_name, doc_id_or_name))
                row = cur.fetchone()
                if row:
                    return row
    except Exception as exc:
        logger.warning(f"Failed to fetch from regulatory_documents: {exc}")

    # Fallback to chunk registry
    sql_chunk = """
    SELECT 
        document_name,
        CASE WHEN document_name LIKE '%%AMFI%%' THEN 'AMFI' ELSE 'SEBI' END AS regulator,
        status,
        COUNT(chunk_id) AS chunk_count,
        MAX(source_url) AS source_url,
        MAX(file_search_document_name) AS file_search_document_name
    FROM regulation_chunk_registry
    WHERE document_name = %s OR chunk_id LIKE %s
    GROUP BY document_name, status
    LIMIT 1
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_chunk, (doc_id_or_name, f"%{doc_id_or_name}%"))
            row = cur.fetchone()
            if row:
                return {
                    "document_id": doc_id_or_name,
                    "document_name": row["document_name"],
                    "filename": f"{row['document_name'].lower().replace(' ', '_')}.pdf",
                    "regulator": row["regulator"],
                    "status": row["status"],
                    "chunk_count": row["chunk_count"],
                    "source_url": row["source_url"],
                }
    return None


def create_regulatory_document(doc: Dict[str, Any]) -> str:
    """Inserts or updates a statutory document record in regulatory_documents."""
    sql = """
    INSERT INTO regulatory_documents (
        document_id, document_name, filename, regulator, document_type,
        status, year, source_url, storage_path, file_size_bytes, chunk_count
    ) VALUES (
        %(document_id)s, %(document_name)s, %(filename)s, %(regulator)s, %(document_type)s,
        %(status)s, %(year)s, %(source_url)s, %(storage_path)s, %(file_size_bytes)s, %(chunk_count)s
    ) ON DUPLICATE KEY UPDATE
        filename = VALUES(filename),
        regulator = VALUES(regulator),
        document_type = VALUES(document_type),
        status = VALUES(status),
        year = VALUES(year),
        source_url = VALUES(source_url),
        storage_path = VALUES(storage_path),
        file_size_bytes = VALUES(file_size_bytes),
        chunk_count = VALUES(chunk_count)
    """
    with db_manager.transaction() as cur:
        cur.execute(sql, doc)
    return doc["document_id"]


def delete_regulatory_document(doc_id_or_name: str) -> Optional[Dict[str, Any]]:
    """Deletes a document from regulatory_documents and removes all related chunks."""
    doc = get_document(doc_id_or_name)
    if not doc:
        return None

    doc_name = doc["document_name"]
    doc_id = doc.get("document_id", doc_id_or_name)

    with db_manager.transaction() as cur:
        # Delete chunks first
        cur.execute("DELETE FROM regulation_chunk_registry WHERE document_name = %s", (doc_name,))
        # Delete document record
        try:
            cur.execute("DELETE FROM regulatory_documents WHERE document_id = %s OR document_name = %s", (doc_id, doc_name))
        except Exception as exc:
            logger.warning(f"Could not delete from regulatory_documents: {exc}")

    return doc


def get_document_chunks(document_name: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves chunks for a document for inspection and preview."""
    sql = """
    SELECT chunk_id, clause, citation_label, status, year, page_number, chunk_text
    FROM regulation_chunk_registry
    WHERE document_name = %s
    ORDER BY page_number ASC, priority DESC
    LIMIT %s
    """
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (document_name, limit))
            return cur.fetchall()


def get_chunk(chunk_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves authoritative metadata for a specific chunk."""
    sql = "SELECT * FROM regulation_chunk_registry WHERE chunk_id = %s"
    with db_manager.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (chunk_id,))
            return cur.fetchone()


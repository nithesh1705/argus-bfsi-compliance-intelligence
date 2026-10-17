"""
ARGUS — Documents & Regulations API Route (backend/api/routes/documents.py)

Full lifecycle management for statutory regulatory corpus:
- Document Listing & Chunk Counts
- File In-Browser PDF/Text Preview
- Attachment Download
- Multipart File Upload & Automated Chunk Indexing
- Document Deletion & Corpus Pruning
"""

import io
import re
import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Response, Query, status

from backend.core.config import settings
from backend.db.repositories.regulations_repo import (
    list_documents,
    get_document,
    create_regulatory_document,
    delete_regulatory_document,
    batch_upsert_chunks,
    get_document_chunks,
)

logger = logging.getLogger("argus.api.documents")

router = APIRouter(prefix="/documents", tags=["Documents"])
regulations_router = APIRouter(prefix="/regulations", tags=["Regulations"])


def fetch_document_bytes(filename: str) -> Optional[bytes]:
    """
    Retrieves document content bytes from GCS bucket or local storage fallback.
    """
    # 1. GCS Fetch
    try:
        from google.cloud import storage
        client = storage.Client(project=settings.PROJECT_ID)
        bucket = client.bucket(settings.REGULATIONS_BUCKET)
        
        # Check regulations/ prefix
        blob = bucket.blob(f"regulations/{filename}")
        if blob.exists():
            return blob.download_as_bytes()
        
        # Check root of bucket
        blob_root = bucket.blob(filename)
        if blob_root.exists():
            return blob_root.download_as_bytes()
    except Exception as exc:
        logger.warning(f"GCS read failed for {filename}: {exc}")

    # 2. Local filesystem fallback
    local_candidates = [
        settings.BASE_DIR / "RegulatoryDocs" / filename,
        settings.BASE_DIR / "RegulatoryDocs" / "SEBI" / filename,
        settings.BASE_DIR / "RegulatoryDocs" / "AMFI" / filename,
        settings.STORAGE_LOCAL_ROOT / "regulations" / filename,
    ]
    for p in local_candidates:
        if p.exists() and p.is_file():
            try:
                return p.read_bytes()
            except Exception as e:
                logger.warning(f"Local read failed for {p}: {e}")

    return None


async def save_document_file(filename: str, content: bytes, content_type: str = "application/pdf") -> str:
    """Uploads document bytes to GCS bucket (and local backup)."""
    uri = f"gs://{settings.REGULATIONS_BUCKET}/regulations/{filename}"
    try:
        from google.cloud import storage
        client = storage.Client(project=settings.PROJECT_ID)
        bucket = client.bucket(settings.REGULATIONS_BUCKET)
        blob = bucket.blob(f"regulations/{filename}")
        blob.upload_from_string(content, content_type=content_type)
        logger.info(f"Successfully uploaded {filename} to {uri}")
    except Exception as exc:
        logger.warning(f"GCS upload failed for {filename}: {exc}")
        # Local backup
        local_path = settings.STORAGE_LOCAL_ROOT / "regulations" / filename
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(content)
        uri = f"file://{local_path}"

    return uri


def delete_document_file(filename: str):
    """Deletes document file from GCS storage."""
    try:
        from google.cloud import storage
        client = storage.Client(project=settings.PROJECT_ID)
        bucket = client.bucket(settings.REGULATIONS_BUCKET)
        blob = bucket.blob(f"regulations/{filename}")
        if blob.exists():
            blob.delete()
        blob_root = bucket.blob(filename)
        if blob_root.exists():
            blob_root.delete()
        logger.info(f"Deleted {filename} from storage")
    except Exception as exc:
        logger.warning(f"GCS delete failed for {filename}: {exc}")


def extract_and_chunk_document(
    content: bytes,
    filename: str,
    document_name: str,
    regulator: str,
    status_val: str,
    year_val: int,
    source_url: str = "",
) -> List[Dict[str, Any]]:
    """Extracts text from PDF/TXT document and constructs statutory indexed chunks."""
    chunks = []
    slug = re.sub(r"[^A-Za-z0-9]+", "_", document_name).strip("_").upper()[:30]

    # PDF text extraction
    if filename.lower().endswith(".pdf") or content[:4] == b"%PDF":
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content))
            for page_idx, page in enumerate(reader.pages):
                page_num = page_idx + 1
                text = page.extract_text() or ""
                clean_text = text.strip()
                if len(clean_text) < 15:
                    continue

                paragraphs = [p.strip() for p in clean_text.split("\n\n") if len(p.strip()) > 25]
                if not paragraphs:
                    paragraphs = [clean_text]

                for p_idx, para in enumerate(paragraphs):
                    chunk_id = f"{slug}_P{page_num}_{p_idx+1}"
                    clause = f"Clause P{page_num}.{p_idx+1}"
                    citation = f"{document_name} (Page {page_num})"
                    chunks.append({
                        "chunk_id": chunk_id,
                        "document_name": document_name,
                        "clause": clause,
                        "citation_label": citation,
                        "status": status_val,
                        "year": year_val,
                        "effective_until": None,
                        "priority": 10 if status_val == "current" else 1,
                        "source_url": source_url,
                        "page_number": page_num,
                        "file_search_document_name": filename,
                        "chunk_text": para,
                    })
        except Exception as exc:
            logger.warning(f"pypdf extraction failed for {filename}: {exc}")

    # Plaintext fallback extraction
    if not chunks:
        try:
            text = content.decode("utf-8", errors="replace").strip()
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 25]
            if not paragraphs and text:
                paragraphs = [text]

            for idx, p in enumerate(paragraphs):
                chunk_id = f"{slug}_SEC_{idx+1}"
                chunks.append({
                    "chunk_id": chunk_id,
                    "document_name": document_name,
                    "clause": f"Section {idx+1}",
                    "citation_label": f"{document_name} - Sec {idx+1}",
                    "status": status_val,
                    "year": year_val,
                    "effective_until": None,
                    "priority": 10,
                    "source_url": source_url,
                    "page_number": 1,
                    "file_search_document_name": filename,
                    "chunk_text": p,
                })
        except Exception as exc:
            logger.error(f"Text extraction failed: {exc}")

    # Fallback registry chunk
    if not chunks:
        chunks.append({
            "chunk_id": f"{slug}_INDEX",
            "document_name": document_name,
            "clause": "Full Document",
            "citation_label": document_name,
            "status": status_val,
            "year": year_val,
            "effective_until": None,
            "priority": 10,
            "source_url": source_url,
            "page_number": 1,
            "file_search_document_name": filename,
            "chunk_text": f"Regulatory Master Document: {document_name} ({filename}) registered in Cloud SQL corpus.",
        })

    return chunks


# ==============================================================================
# Shared Route Handlers
# ==============================================================================

async def handle_list_documents():
    """Returns statutory documents and chunk counts."""
    return list_documents()


async def handle_get_document(doc_id: str):
    """Retrieves metadata and sample chunks for a specific document."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")
    chunks = get_document_chunks(doc["document_name"], limit=50)
    return {"document": doc, "chunks": chunks, "chunk_count": len(chunks)}


async def handle_preview_document(doc_id: str):
    """Streams the document bytes inline for browser viewing (PDF/text)."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    filename = doc.get("filename") or f"{doc['document_name'].lower().replace(' ', '_')}.pdf"
    content = fetch_document_bytes(filename)

    if not content:
        # Fallback: if PDF file not in storage, synthesize text representation from chunks
        chunks = get_document_chunks(doc["document_name"], limit=100)
        if chunks:
            text_content = f"ARGUS REGULATORY CORPUS — {doc['document_name']}\n"
            text_content += f"Authority: {doc.get('regulator', 'SEBI')} | Status: {doc.get('status', 'current')} | Year: {doc.get('year', 2026)}\n"
            text_content += "=" * 80 + "\n\n"
            for c in chunks:
                text_content += f"[{c['citation_label']} | {c['clause']}]\n"
                text_content += f"{c['chunk_text']}\n\n"
            return Response(
                content=text_content.encode("utf-8"),
                media_type="text/plain; charset=utf-8",
                headers={"Content-Disposition": f'inline; filename="{doc["document_name"]}.txt"'},
            )
        raise HTTPException(status_code=404, detail=f"File binary for '{filename}' not found in storage bucket")

    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


async def handle_download_document(doc_id: str):
    """Downloads the document file attachment."""
    doc = get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    filename = doc.get("filename") or f"{doc['document_name'].lower().replace(' ', '_')}.pdf"
    content = fetch_document_bytes(filename)

    if not content:
        # Synthesize text fallback if binary not present
        chunks = get_document_chunks(doc["document_name"], limit=100)
        if chunks:
            text_content = f"ARGUS REGULATORY CORPUS — {doc['document_name']}\n\n"
            for c in chunks:
                text_content += f"[{c['citation_label']} | {c['clause']}]\n{c['chunk_text']}\n\n"
            return Response(
                content=text_content.encode("utf-8"),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f'attachment; filename="{doc["document_name"]}.txt"'},
            )
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found for download")

    media_type = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def handle_upload_document(
    file: UploadFile = File(...),
    document_name: Optional[str] = Form(None),
    regulator: Optional[str] = Form("SEBI"),
    document_type: Optional[str] = Form("REGULATION"),
    status_val: Optional[str] = Form("current"),
    year_val: Optional[int] = Form(2026),
    source_url: Optional[str] = Form(None),
):
    """Uploads a new regulatory document, writes to GCS, and indexes chunks into Cloud SQL."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file missing filename")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes)")

    clean_filename = re.sub(r"[^A-Za-z0-9_.-]+", "_", file.filename)
    doc_name = document_name.strip() if document_name and document_name.strip() else clean_filename.rsplit(".", 1)[0].replace("_", " ")

    # Generate persistent doc_id
    doc_id = f"DOC-{int(time.time() * 1000) % 1000000:06d}"

    # 1. Save file to storage
    storage_path = await save_document_file(clean_filename, content, content_type=file.content_type or "application/pdf")

    # 2. Extract and create chunks
    chunks = extract_and_chunk_document(
        content=content,
        filename=clean_filename,
        document_name=doc_name,
        regulator=regulator or "SEBI",
        status_val=status_val or "current",
        year_val=year_val or 2026,
        source_url=source_url or "",
    )

    # 3. Upsert chunks into registry
    upserted_count = batch_upsert_chunks(chunks)

    # 4. Insert into regulatory_documents
    doc_record = {
        "document_id": doc_id,
        "document_name": doc_name,
        "filename": clean_filename,
        "regulator": regulator or "SEBI",
        "document_type": document_type or "REGULATION",
        "status": status_val or "current",
        "year": year_val or 2026,
        "source_url": source_url or "",
        "storage_path": storage_path,
        "file_size_bytes": len(content),
        "chunk_count": len(chunks),
    }
    create_regulatory_document(doc_record)

    logger.info(f"Registered document '{doc_name}' ({doc_id}) with {upserted_count} chunks.")

    return {
        "success": True,
        "message": f"Document '{doc_name}' uploaded and indexed successfully.",
        "document": doc_record,
        "chunks_indexed": upserted_count,
    }


async def handle_delete_document(doc_id: str):
    """Deletes a document from the corpus and prunes all registered chunks."""
    deleted_doc = delete_regulatory_document(doc_id)
    if not deleted_doc:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    filename = deleted_doc.get("filename")
    if filename:
        delete_document_file(filename)

    return {
        "success": True,
        "message": f"Document '{deleted_doc['document_name']}' and its associated statutory chunks were permanently deleted.",
        "deleted_document_id": doc_id,
    }


# ==============================================================================
# Router Endpoints (/documents and /regulations)
# ==============================================================================

@router.get("", response_model=Dict[str, Any])
async def get_documents():
    return await handle_list_documents()

@regulations_router.get("", response_model=Dict[str, Any])
async def get_regulations():
    return await handle_list_documents()

@router.get("/authorities")
@regulations_router.get("/authorities")
def get_authorities(active_only: bool = Query(False, description="Filter for active authorities only")):
    from backend.db.repositories.admin_repo import list_authorities_admin
    return list_authorities_admin(active_only=active_only)

@router.get("/{doc_id}")
async def get_doc_by_id(doc_id: str):
    return await handle_get_document(doc_id)

@regulations_router.get("/{doc_id}")
async def get_reg_by_id(doc_id: str):
    return await handle_get_document(doc_id)

@router.get("/{doc_id}/preview")
async def preview_doc(doc_id: str):
    return await handle_preview_document(doc_id)

@regulations_router.get("/{doc_id}/preview")
async def preview_reg(doc_id: str):
    return await handle_preview_document(doc_id)

@router.get("/{doc_id}/download")
async def download_doc(doc_id: str):
    return await handle_download_document(doc_id)

@regulations_router.get("/{doc_id}/download")
async def download_reg(doc_id: str):
    return await handle_download_document(doc_id)

@router.post("/upload")
async def upload_doc(
    file: UploadFile = File(...),
    document_name: Optional[str] = Form(None),
    regulator: Optional[str] = Form("SEBI"),
    document_type: Optional[str] = Form("REGULATION"),
    status: Optional[str] = Form("current"),
    year: Optional[int] = Form(2026),
    source_url: Optional[str] = Form(None),
):
    return await handle_upload_document(file, document_name, regulator, document_type, status, year, source_url)

@regulations_router.post("/upload")
async def upload_reg(
    file: UploadFile = File(...),
    document_name: Optional[str] = Form(None),
    regulator: Optional[str] = Form("SEBI"),
    document_type: Optional[str] = Form("REGULATION"),
    status: Optional[str] = Form("current"),
    year: Optional[int] = Form(2026),
    source_url: Optional[str] = Form(None),
):
    return await handle_upload_document(file, document_name, regulator, document_type, status, year, source_url)

@router.delete("/{doc_id}")
async def delete_doc(doc_id: str):
    return await handle_delete_document(doc_id)

@regulations_router.delete("/{doc_id}")
async def delete_reg(doc_id: str):
    return await handle_delete_document(doc_id)

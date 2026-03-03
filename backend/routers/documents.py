import os
import re
from pathlib import Path

from fastapi import APIRouter, UploadFile, HTTPException

from schemas import DocumentInfo
from services import file_parser, rag

router = APIRouter(prefix="/api")

UPLOAD_DIR = Path("/app/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


def _sanitize_id(filename: str) -> str:
    stem = Path(filename).stem
    return re.sub(r"[^a-zA-Z0-9_-]", "_", stem)


@router.post("/upload", response_model=DocumentInfo)
async def upload_file(file: UploadFile):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type: {ext}")

    doc_id = _sanitize_id(file.filename or "upload")
    save_path = UPLOAD_DIR / f"{doc_id}{ext}"

    content = await file.read()
    save_path.write_bytes(content)

    text = file_parser.parse_file(str(save_path), ext)
    rag.add_document(doc_id, text)

    return DocumentInfo(id=doc_id, name=file.filename or doc_id)


@router.get("/documents", response_model=list[DocumentInfo])
async def list_documents():
    if not UPLOAD_DIR.exists():
        return []
    docs = []
    for f in sorted(UPLOAD_DIR.iterdir()):
        if f.is_file() and f.suffix.lower() in ALLOWED_EXTENSIONS:
            docs.append(DocumentInfo(id=f.stem, name=f.name))
    return docs


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    deleted = False
    for f in UPLOAD_DIR.iterdir():
        if f.stem == doc_id:
            f.unlink()
            deleted = True
            break

    rag.delete_document(doc_id)

    if not deleted:
        raise HTTPException(404, "Document not found")
    return {"status": "deleted"}

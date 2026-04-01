"""
rag_api.py — FastAPI application exposing /query and /upload endpoints.
"""

import sys
import shutil
from pathlib import Path

# ── Fix import paths ──────────────────────────────────────────────────────────
# __file__ is scripts/api/rag_api.py
# We need scripts/ on sys.path so that config, retriever_reranker_cache, etc.
# are importable. We also add scripts/api/ itself just in case.
_API_DIR     = Path(__file__).resolve().parent   # → scripts/api/
_SCRIPTS_DIR = _API_DIR.parent                   # → scripts/
for _p in (_SCRIPTS_DIR, _API_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import UPLOAD_DIR, CHUNK_SIZE
from retriever_reranker_cache import phase3_pipeline, add_file_to_rag, summarize_document

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="RAG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


class QueryResponse(BaseModel):
    answer:    str
    citations: list[str]
    chunks:    list[str]


class UploadResponse(BaseModel):
    filename:       str
    message:        str
    chunks_indexed: int


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_text(text: str) -> str:
    """Strip non-printable characters that leak in from binary PDFs."""
    return "".join(
        c for c in (text or "") if c.isprintable() or c in "\n\t "
    ).strip()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse)
async def query_endpoint(req: QueryRequest):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query must not be empty.")
    try:
        result = phase3_pipeline(req.query, limit=req.top_k)
        return QueryResponse(
            answer=result.get("llm_answer", ""),
            citations=result.get("citations", []),
            chunks=[_clean_text(c.get("text", "")) for c in result.get("chunks", [])],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/upload", response_model=UploadResponse)
async def upload_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    dest = UPLOAD_DIR / file.filename
    try:
        with dest.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    finally:
        await file.close()

    try:
        add_file_to_rag(dest)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Indexing failed: {exc}") from exc

    approx_chunks = max(1, dest.stat().st_size // (CHUNK_SIZE * 5))

    return UploadResponse(
        filename=file.filename,
        message="File uploaded and indexed successfully.",
        chunks_indexed=approx_chunks,
    )



@app.post("/summarize")
async def summarize_endpoint(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{suffix}'. Allowed: {ALLOWED_EXTENSIONS}",
        )

    dest = UPLOAD_DIR / file.filename
    try:
        with dest.open("wb") as buf:
            shutil.copyfileobj(file.file, buf)
    finally:
        await file.close()

    try:
        summary = summarize_document(dest)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Summarization failed: {exc}") from exc

    return {"filename": file.filename, "summary": summary}


@app.get("/health")
async def health():
    return {"status": "ok"}
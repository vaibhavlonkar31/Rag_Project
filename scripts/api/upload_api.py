"""
upload_api.py — Standalone upload-only FastAPI app.

For most use cases, prefer rag_api.py which includes both /query and /upload.
This file is kept for projects that run the upload service separately.
"""

import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from scripts.config import UPLOAD_DIR
from retriever_reranker_cache import add_file_to_rag

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}

app = FastAPI(title="RAG Upload Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
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

    return {
        "filename": file.filename,
        "message":  "File uploaded and indexed successfully.",
        "saved_to": str(dest),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
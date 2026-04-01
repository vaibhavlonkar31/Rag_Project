#!/usr/bin/env python3
"""
ingest_preprocess.py — Read, clean, chunk, and save documents to JSON.

Supported formats: PDF, DOCX, HTML, CSV, TXT
Output:  output/<stem>_chunks.json
"""

import re
import json
import time
import uuid
from pathlib import Path

from pdf2image import convert_from_path
from PyPDF2 import PdfReader
from bs4 import BeautifulSoup
import pandas as pd
import pytesseract

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None
    print("[WARN] python-docx not installed — DOCX files will be skipped.")

from config import DATA_DIR, OUTPUT_DIR, CHUNK_SIZE, CHUNK_OVERLAP


# ── Readers ───────────────────────────────────────────────────────────────────

def read_pdf(path: Path) -> str:
    text_parts = []
    try:
        reader = PdfReader(str(path))
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text_parts.append(extracted)

        if not any(text_parts):
            print(f"[INFO] No text layer found in {path.name} — falling back to OCR.")
            images = convert_from_path(str(path), dpi=200)
            for img in images:
                text_parts.append(pytesseract.image_to_string(img))

    except Exception as exc:
        print(f"[ERROR] Failed to read PDF {path.name}: {exc}")

    return "\n".join(text_parts)


def read_docx(path: Path) -> str:
    if DocxDocument is None:
        print(f"[SKIP] python-docx not installed — skipping {path.name}")
        return ""
    try:
        doc = DocxDocument(str(path))
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception as exc:
        print(f"[ERROR] DOCX read failed for {path.name}: {exc}")
        return ""


def read_html(path: Path) -> str:
    try:
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        return soup.get_text(separator="\n")
    except Exception as exc:
        print(f"[ERROR] HTML read failed for {path.name}: {exc}")
        return ""


def read_csv(path: Path) -> str:
    try:
        df = pd.read_csv(path)
        if "text" in df.columns:
            return "\n".join(df["text"].astype(str).tolist())
        return df.to_string(index=False)
    except Exception as exc:
        print(f"[ERROR] CSV read failed for {path.name}: {exc}")
        return ""


def read_file(path: Path) -> str:
    ext = path.suffix.lower()
    readers = {
        ".pdf":  read_pdf,
        ".docx": read_docx,
        ".doc":  read_docx,
        ".html": read_html,
        ".htm":  read_html,
        ".csv":  read_csv,
        ".txt":  lambda p: p.read_text(encoding="utf-8", errors="ignore"),
    }
    reader = readers.get(ext)
    if reader is None:
        print(f"[SKIP] Unsupported file type: {path.suffix}  ({path.name})")
        return ""
    return reader(path)


# ── Cleaning ──────────────────────────────────────────────────────────────────

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"Page\s*\d+\s*(of\s*\d+)?", "", text, flags=re.IGNORECASE)
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    if not words:
        return []
    chunks, start = [], 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


# ── Save ──────────────────────────────────────────────────────────────────────

def save_chunks(chunks: list[str], src_path: Path) -> Path:
    doc_id = str(uuid.uuid4())
    timestamp = int(time.time())

    records = [
        {
            "doc_id":      doc_id,
            "chunk_id":    idx,
            "title":       src_path.stem,
            "source_path": str(src_path),
            "position":    idx,
            "timestamp":   timestamp,
            "text":        chunk,
        }
        for idx, chunk in enumerate(chunks)
    ]

    out_file = OUTPUT_DIR / f"{src_path.stem}_chunks.json"
    out_file.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[SAVED] {out_file.name}  ({len(records)} chunks)")
    return out_file


# ── Per-file entry point (used by upload API) ─────────────────────────────────

def process_file(path: Path) -> Path | None:
    print(f"[PROCESS] {path.name}")
    raw = read_file(path)
    cleaned = clean_text(raw)
    if not cleaned:
        print(f"[WARN] No text extracted from {path.name}")
        return None
    chunks = chunk_text(cleaned)
    return save_chunks(chunks, path)


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    files = [f for f in DATA_DIR.glob("*") if f.is_file()]
    if not files:
        print(f"[INFO] No files found in {DATA_DIR}. Place your documents there.")
        return
    for file in files:
        process_file(file)


if __name__ == "__main__":
    main()
"""
config.py — Central configuration for the RAG pipeline.
All modules import from here so settings are consistent.
Supports both local .env and Streamlit Cloud secrets.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Streamlit secrets helper ───────────────────────────────────────────────────
def _secret(key: str, fallback: str = "") -> str:
    """Read from Streamlit secrets first, then env vars, then fallback."""
    try:
        import streamlit as st
        val = st.secrets.get(key)
        if val:
            return str(val)
    except Exception:
        pass
    return os.getenv(key, fallback)


# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent
DATA_DIR   = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR = BASE_DIR / "uploaded_files"

for _d in (DATA_DIR, OUTPUT_DIR, UPLOAD_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Qdrant ────────────────────────────────────────────────────────────────────
QDRANT_URL     = _secret("QDRANT_URL",     "http://localhost:6333")
QDRANT_API_KEY = _secret("QDRANT_API_KEY", "")
COLLECTION_NAME = "rag_chunks"

# ── Embedding model ───────────────────────────────────────────────────────────
EMBEDDER_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE    = 384          # must match the model above

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE    = 800           # chars per chunk (sentence-aware)
CHUNK_OVERLAP = 150           # overlap chars between chunks

# ── LLM (Groq) ────────────────────────────────────────────────────────────────
GROQ_API_KEY = _secret("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Add it to your .env file or to Streamlit Cloud Secrets."
    )

if not QDRANT_URL:
    raise EnvironmentError(
        "QDRANT_URL is not set. "
        "Add it to your .env file or to Streamlit Cloud Secrets."
    )
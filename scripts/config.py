"""
config.py — Central configuration for the RAG pipeline.
All modules import from here so settings are consistent.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR     = Path(__file__).resolve().parent
DATA_DIR     = BASE_DIR / "data"
OUTPUT_DIR   = BASE_DIR / "output"
UPLOAD_DIR   = BASE_DIR / "uploaded_files"

for _d in (DATA_DIR, OUTPUT_DIR, UPLOAD_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── Qdrant ────────────────────────────────────────────────────────────────────
QDRANT_HOST      = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT      = int(os.getenv("QDRANT_PORT", 6333))
QDRANT_URL       = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
COLLECTION_NAME  = "rag_chunks"

# ── Embedding model ───────────────────────────────────────────────────────────
EMBEDDER_MODEL = "all-MiniLM-L6-v2"
VECTOR_SIZE    = 384          # must match the model above

# ── Chunking ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 800              # chars per chunk (sentence-aware)
CHUNK_OVERLAP = 150           # overlap chars between chunks

# ── LLM (Groq) ────────────────────────────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.1-8b-instant"

if not GROQ_API_KEY:
    raise EnvironmentError(
        "GROQ_API_KEY is not set. "
        "Add it to your .env file or export it as an environment variable."
    )
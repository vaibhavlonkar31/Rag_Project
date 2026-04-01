#!/usr/bin/env python3
"""
reset_and_reindex.py — Wipe the Qdrant collection and re-index all uploaded files.

Usage:
    python reset_and_reindex.py
"""

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

from config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE, UPLOAD_DIR
from retriever_reranker_cache import add_file_to_rag

SUPPORTED = {".txt", ".pdf", ".docx"}


def main():
    print(f"[RESET] Connecting to Qdrant at {QDRANT_URL}...")
    qdrant = QdrantClient(url=QDRANT_URL)

    # ── Delete old collection ──────────────────────────────────────────────────
    existing = {c.name for c in qdrant.get_collections().collections}
    if COLLECTION_NAME in existing:
        qdrant.delete_collection(COLLECTION_NAME)
        print(f"[RESET] Deleted old collection '{COLLECTION_NAME}'.")
    else:
        print(f"[RESET] Collection '{COLLECTION_NAME}' did not exist — creating fresh.")

    # ── Create new collection ──────────────────────────────────────────────────
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"[RESET] Created '{COLLECTION_NAME}' (dim={VECTOR_SIZE}).")

    # ── Re-index uploaded files ────────────────────────────────────────────────
    if not UPLOAD_DIR.exists() or not any(UPLOAD_DIR.iterdir()):
        print(f"[RESET] No files found in {UPLOAD_DIR} — nothing to index.")
        return

    indexed = 0
    for file_path in UPLOAD_DIR.iterdir():
        if file_path.suffix.lower() in SUPPORTED:
            try:
                add_file_to_rag(file_path)
                indexed += 1
            except Exception as exc:
                print(f"[ERROR] Failed to index {file_path.name}: {exc}")
        else:
            print(f"[SKIP] {file_path.name} (unsupported type)")

    print(f"[DONE] Re-indexed {indexed} file(s). RAG system is ready.")


if __name__ == "__main__":
    main()
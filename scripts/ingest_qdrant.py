#!/usr/bin/env python3
"""
ingest_qdrant.py — Embed chunks from output/*.json and upsert into Qdrant.
"""

import json
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from sentence_transformers import SentenceTransformer

from config import (
    OUTPUT_DIR, QDRANT_URL, COLLECTION_NAME,
    EMBEDDER_MODEL, VECTOR_SIZE,
)


# ── Load chunks ───────────────────────────────────────────────────────────────

def load_chunks() -> list[dict]:
    json_files = list(OUTPUT_DIR.glob("*_chunks.json"))
    if not json_files:
        print(f"[ERROR] No chunk files found in {OUTPUT_DIR}.")
        return []

    all_chunks = []
    for jf in json_files:
        data = json.loads(jf.read_text(encoding="utf-8"))
        for item in data:
            all_chunks.append({
                "text": item["text"],
                "metadata": {
                    "doc_id":      item.get("doc_id", "unknown"),
                    "chunk_id":    item["chunk_id"],
                    "title":       item.get("title", "Untitled"),
                    "source_path": item.get("source_path", ""),
                    "position":    item.get("position", 0),
                    "timestamp":   item.get("timestamp", 0),
                },
            })

    print(f"[INFO] Loaded {len(all_chunks)} chunks from {len(json_files)} file(s).")
    return all_chunks


# ── Ensure collection exists ──────────────────────────────────────────────────

def ensure_collection(client: QdrantClient) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        print(f"[INFO] Creating collection '{COLLECTION_NAME}' (dim={VECTOR_SIZE})...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )
    else:
        print(f"[INFO] Collection '{COLLECTION_NAME}' already exists.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("[STEP 1] Loading chunks...")
    chunks = load_chunks()
    if not chunks:
        return

    print(f"[STEP 2] Loading embedding model: {EMBEDDER_MODEL}")
    embedder = SentenceTransformer(EMBEDDER_MODEL)

    print(f"[STEP 3] Connecting to Qdrant at {QDRANT_URL}...")
    qdrant = QdrantClient(url=QDRANT_URL)

    print("[STEP 4] Ensuring collection...")
    ensure_collection(qdrant)

    print("[STEP 5] Embedding chunks...")
    points = []
    for chunk in chunks:
        vector = embedder.encode(chunk["text"], convert_to_numpy=True).tolist()
        points.append(
            PointStruct(
                id=uuid.uuid4().hex,
                vector=vector,
                payload={**chunk["metadata"], "text": chunk["text"]},
            )
        )

    print(f"[STEP 6] Uploading {len(points)} points to Qdrant...")
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[DONE] Ingested {len(points)} chunks into '{COLLECTION_NAME}'.")


if __name__ == "__main__":
    main()
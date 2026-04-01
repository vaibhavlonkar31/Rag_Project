#!/usr/bin/env python3
"""
embeddings_qdrant.py — Embed all chunk JSON files and upsert into Qdrant.

This is a simpler alternative to ingest_qdrant.py — useful for quickly
re-embedding already-chunked files without re-processing raw documents.
"""

import json
import os
import uuid
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

from config import OUTPUT_DIR, QDRANT_URL, COLLECTION_NAME, EMBEDDER_MODEL, VECTOR_SIZE


def main():
    print(f"[EMBED] Loading model: {EMBEDDER_MODEL}")
    model = SentenceTransformer(EMBEDDER_MODEL)

    print(f"[EMBED] Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    # Ensure collection exists
    existing = {c.name for c in client.get_collections().collections}
    if COLLECTION_NAME not in existing:
        print(f"[EMBED] Creating collection '{COLLECTION_NAME}' (dim={VECTOR_SIZE})...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    chunk_files = list(OUTPUT_DIR.glob("*_chunks.json"))
    if not chunk_files:
        print(f"[EMBED] No chunk files found in {OUTPUT_DIR}.")
        return

    total = 0
    for chunk_file in chunk_files:
        print(f"[EMBED] Processing {chunk_file.name}...")
        data = json.loads(chunk_file.read_text(encoding="utf-8"))

        points = []
        for doc in data:
            text = doc.get("text", "").strip()
            if not text:
                continue

            vector = model.encode(text, normalize_embeddings=True).tolist()
            points.append(
                PointStruct(
                    id=uuid.uuid4().hex,
                    vector=vector,
                    payload={
                        "source":   chunk_file.name,
                        "chunk_id": doc.get("chunk_id", 0),
                        "text":     text,
                    },
                )
            )

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        total += len(points)
        print(f"[EMBED] {chunk_file.name} → {len(points)} points upserted.")

    print(f"[DONE] Total points upserted: {total}")


if __name__ == "__main__":
    main()
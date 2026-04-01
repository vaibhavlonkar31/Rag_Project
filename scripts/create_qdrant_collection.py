#!/usr/bin/env python3
"""
create_qdrant_collection.py — (Re)create the Qdrant collection with correct dimensions.

Run this once during initial setup, or after changing the embedding model.
"""

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

from config import QDRANT_URL, COLLECTION_NAME, VECTOR_SIZE


def main():
    client = QdrantClient(url=QDRANT_URL)
    existing = {c.name for c in client.get_collections().collections}

    if COLLECTION_NAME in existing:
        print(f"[INFO] Deleting existing collection '{COLLECTION_NAME}'...")
        client.delete_collection(COLLECTION_NAME)

    print(f"[INFO] Creating '{COLLECTION_NAME}' with dim={VECTOR_SIZE}...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    print(f"[DONE] Collection '{COLLECTION_NAME}' is ready.")


if __name__ == "__main__":
    main()
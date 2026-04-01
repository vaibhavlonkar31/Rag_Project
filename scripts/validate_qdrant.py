#!/usr/bin/env python3
"""
validate_qdrant.py — Search Qdrant with a test query and print top results.

Usage:
    python validate_qdrant.py "your search text here"
    python validate_qdrant.py          # uses a default query
"""

import sys
from pprint import pprint

from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

from config import QDRANT_URL, COLLECTION_NAME, EMBEDDER_MODEL

DEFAULT_QUERY = "What is this document about?"


def main():
    query = " ".join(sys.argv[1:]).strip() or DEFAULT_QUERY
    print(f"[VALIDATE] Query: {query!r}")

    print(f"[VALIDATE] Loading embedding model: {EMBEDDER_MODEL}")
    model = SentenceTransformer(EMBEDDER_MODEL)
    query_vector = model.encode(query, normalize_embeddings=True).tolist()

    print(f"[VALIDATE] Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL)

    response = client.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vector,
        limit=3,
    )
    results = response.points

    if not results:
        print("[VALIDATE] No results found. Is the collection populated?")
        return

    print(f"\n[VALIDATE] Top {len(results)} result(s):")
    for i, hit in enumerate(results, 1):
        print(f"\n  Result {i}:")
        print(f"  Score : {hit.score:.4f}")
        pprint(hit.payload, indent=4)


if __name__ == "__main__":
    main()
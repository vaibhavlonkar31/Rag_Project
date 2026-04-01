#!/usr/bin/env python3
"""
check_collections.py — List all Qdrant collections and their vector counts.
"""

from qdrant_client import QdrantClient
from config import QDRANT_URL


def main():
    client = QdrantClient(url=QDRANT_URL)
    collections = client.get_collections().collections

    if not collections:
        print("No collections found in Qdrant.")
        return

    print(f"Collections in Qdrant ({QDRANT_URL}):")
    for col in collections:
        try:
            info = client.get_collection(col.name)
            count = info.points_count
        except Exception:
            count = "?"
        print(f"  • {col.name}  ({count} points)")


if __name__ == "__main__":
    main()
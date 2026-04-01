#!/usr/bin/env python3
"""
test_phase3.py — Interactive CLI to test the full RAG pipeline end-to-end.

Usage:
    python test_phase3.py
"""

from retriever_reranker_cache import phase3_pipeline


def main():
    print("\n=== RAG Pipeline — Interactive Test ===\n")

    query = input("Enter your search query: ").strip()
    if not query:
        print("No query entered. Exiting.")
        return

    print("\n[TEST] Running pipeline...\n")
    output = phase3_pipeline(query, limit=5)

    chunks = output.get("chunks", [])
    answer = output.get("llm_answer", "")

    # ── Print retrieved chunks ─────────────────────────────────────────────────
    print("=" * 60)
    print("Reranked Chunks:")
    print("=" * 60)

    if not chunks:
        print("No chunks retrieved.")
    else:
        for i, c in enumerate(chunks, 1):
            print(f"\nChunk {i}:")
            print(f"  ID    : {c.get('id', '?')}")
            print(f"  Score : {c.get('score', 0.0):.4f}")
            snippet = c.get("text", "")[:400]
            print(f"  Text  : {snippet}{'...' if len(c.get('text','')) > 400 else ''}")

    # ── Print final answer ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("Final Answer:")
    print("=" * 60)
    print(answer or "(no answer generated)")
    print()


if __name__ == "__main__":
    main()
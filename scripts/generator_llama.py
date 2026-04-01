"""
generator_llama.py — Standalone answer generator using Groq / LLaMA 3.

Kept as a thin wrapper so other scripts can call generate_answer_with_llama()
directly. The core logic now lives in retriever_reranker_cache.py.
"""

from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def generate_answer_with_llama(query: str, reranked_chunks: list[dict]) -> str:
    """
    Generate a grounded answer from reranked document chunks.

    Args:
        query:           User's question.
        reranked_chunks: List of dicts with at least a 'text' key.

    Returns:
        The LLM-generated answer string.
    """
    doc_text = "\n\n".join(
        f"[{idx}] {chunk['text']}"
        for idx, chunk in enumerate(reranked_chunks)
    )

    prompt = (
        "You are an expert AI assistant.\n"
        "Answer ONLY using the document chunks below.\n"
        "If the answer is not present, say: \"I don't know based on the provided documents.\"\n\n"
        f"Document Chunks:\n{doc_text}\n\n"
        f"User Question:\n{query}\n\n"
        "Rules:\n"
        "1. Cite chunk numbers like [0], [1], etc.\n"
        "2. Do NOT use outside knowledge.\n"
        "3. If unsure, reply \"I don't know.\"\n\n"
        "Final Answer:"
    )

    response = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
    )
    return response.choices[0].message.content.strip()
"""
retriever_reranker_cache.py — High-accuracy RAG pipeline.

Accuracy improvements:
  1. Sentence-aware chunking       — chunks break on sentence boundaries, not mid-word
  2. Query expansion               — LLM rewrites the query into 3 variants before searching
  3. Wider retrieval pool          — fetch 15 candidates, rerank down to top 5
  4. Score-weighted reranking      — combines vector score + LLM relevance score
  5. Strict grounded prompt        — LLM must quote chunk IDs, cannot hallucinate
  6. Context stitching             — adjacent chunks are merged for more coherent context
  7. Fallback to general LLaMA     — when no docs or low confidence
"""

import json
import re
import uuid
from pathlib import Path

import chardet
import docx
from groq import Groq
from PyPDF2 import PdfReader
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

from config import (
    QDRANT_URL, COLLECTION_NAME,
    EMBEDDER_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    CHUNK_SIZE, CHUNK_OVERLAP,
)

# ── Tuning knobs ──────────────────────────────────────────────────────────────
MIN_RELEVANCE_SCORE  = 0.35   # below this → fallback to general LLaMA
RETRIEVAL_CANDIDATES = 15     # fetch this many from Qdrant, then rerank
FINAL_TOP_K          = 5      # keep this many after reranking

# ── Singletons ────────────────────────────────────────────────────────────────
_embedder: SentenceTransformer | None = None
_qdrant:   QdrantClient | None        = None
_groq:     Groq | None                = None


def get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(EMBEDDER_MODEL)
    return _embedder


def get_qdrant() -> QdrantClient:
    global _qdrant
    if _qdrant is None:
        _qdrant = QdrantClient(url=QDRANT_URL)
    return _qdrant


def get_groq() -> Groq:
    global _groq
    if _groq is None:
        _groq = Groq(api_key=GROQ_API_KEY)
    return _groq


# ── File readers ──────────────────────────────────────────────────────────────

def read_uploaded_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()
    if ext == ".txt":
        raw = file_path.read_bytes()
        encoding = chardet.detect(raw).get("encoding") or "utf-8"
        return raw.decode(encoding, errors="ignore")
    if ext == ".pdf":
        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if ext == ".docx":
        doc = docx.Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs)
    raise ValueError(f"Unsupported file type: {ext}")


# ── Sentence-aware chunking ───────────────────────────────────────────────────

def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using punctuation boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def split_text_into_chunks(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[dict]:
    """
    Sentence-aware chunking: accumulate sentences until chunk_size chars,
    then start a new chunk with `overlap` chars carried over.
    This avoids cutting mid-sentence which hurts retrieval quality.
    """
    sentences = _split_sentences(text)
    chunks    = []
    chunk_id  = 0
    current   = []
    current_len = 0

    for sentence in sentences:
        slen = len(sentence)
        if current_len + slen > chunk_size and current:
            chunk_text = " ".join(current)
            chunks.append({"id": str(chunk_id), "text": chunk_text})
            chunk_id += 1

            # Carry over last N chars worth of sentences for overlap
            overlap_sents = []
            overlap_len   = 0
            for s in reversed(current):
                if overlap_len + len(s) <= overlap:
                    overlap_sents.insert(0, s)
                    overlap_len += len(s)
                else:
                    break
            current     = overlap_sents
            current_len = overlap_len

        current.append(sentence)
        current_len += slen

    if current:
        chunks.append({"id": str(chunk_id), "text": " ".join(current)})

    return chunks


# ── Query expansion ───────────────────────────────────────────────────────────

def expand_query(query: str) -> list[str]:
    """
    Generate 3 alternative phrasings of the query using LLaMA.
    Searching with multiple variants catches more relevant chunks.
    """
    groq = get_groq()
    prompt = (
        "Rewrite the following search query into 3 different alternative phrasings "
        "that mean the same thing but use different words. "
        "Return ONLY a JSON array of 3 strings. No explanation.\n\n"
        f"Query: {query}\n\nAlternatives:"
    )
    try:
        resp = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=200,
        )
        raw = resp.choices[0].message.content.strip()
        alternatives = json.loads(raw)
        if isinstance(alternatives, list):
            return [query] + [str(a) for a in alternatives[:3]]
    except Exception:
        pass
    return [query]  # fallback: just use original


# ── Retrieval ─────────────────────────────────────────────────────────────────

def _collection_has_points() -> bool:
    try:
        info = get_qdrant().get_collection(COLLECTION_NAME)
        return (info.points_count or 0) > 0
    except Exception:
        return False


def retrieve(query: str, limit: int = RETRIEVAL_CANDIDATES) -> list[dict]:
    """
    Multi-query retrieval: expand the query into variants, search each,
    deduplicate results, and return top candidates ranked by best score.
    """
    embedder = get_embedder()
    qdrant   = get_qdrant()

    queries  = expand_query(query)
    seen_ids = {}

    for q in queries:
        q_vector = embedder.encode(q, normalize_embeddings=True).tolist()
        results  = qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=q_vector,
            limit=limit,
        )
        for r in results.points:
            rid = str(r.id)
            # Keep the highest score if the same chunk appears in multiple queries
            if rid not in seen_ids or r.score > seen_ids[rid]["score"]:
                seen_ids[rid] = {
                    "id":    rid,
                    "score": r.score,
                    "text":  r.payload.get("text", ""),
                    "source": r.payload.get("source_file", ""),
                }

    # Sort by score descending, return top candidates
    ranked = sorted(seen_ids.values(), key=lambda x: x["score"], reverse=True)
    return ranked[:limit]


# ── Context stitching ─────────────────────────────────────────────────────────

def stitch_chunks(chunks: list[dict]) -> list[dict]:
    """
    Merge chunks that are from the same source and numerically adjacent.
    This gives the LLM more coherent passages to reason over.
    """
    if not chunks:
        return chunks

    stitched  = []
    used      = set()

    for i, chunk in enumerate(chunks):
        if i in used:
            continue
        merged_text = chunk["text"]
        used.add(i)

        for j, other in enumerate(chunks):
            if j in used or j == i:
                continue
            # Simple heuristic: if texts share significant overlap, merge them
            if chunk.get("source") == other.get("source"):
                try:
                    ci = int(chunk["id"])
                    oj = int(other["id"])
                    if abs(ci - oj) == 1:
                        merged_text = merged_text + " " + other["text"]
                        used.add(j)
                except (ValueError, KeyError):
                    pass

        stitched.append({**chunk, "text": merged_text})

    return stitched


# ── LLM Reranking ─────────────────────────────────────────────────────────────

def rerank_with_llm(query: str, chunks: list[dict]) -> list[dict]:
    """
    Ask LLaMA to score each chunk 0-10 for relevance to the query.
    Combine with the vector score for a final weighted rank.
    """
    if not chunks:
        return []

    groq     = get_groq()
    numbered = "\n".join(
        f"[{i}] {c['text'][:400]}" for i, c in enumerate(chunks)
    )

    prompt = (
        f"You are a relevance judge. Score each chunk 0-10 for how well it answers "
        f"the query. 10 = directly answers, 0 = completely unrelated.\n\n"
        f"Query: {query}\n\n"
        f"Chunks:\n{numbered}\n\n"
        "Return ONLY a JSON object like: {\"scores\": [8, 3, 10, 1, 5]}\n"
        "The list must have exactly as many numbers as chunks. No explanation."
    )

    try:
        resp = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=200,
        )
        raw    = resp.choices[0].message.content.strip()
        parsed = json.loads(raw)
        scores = parsed.get("scores", [])
        if not isinstance(scores, list) or len(scores) != len(chunks):
            raise ValueError("Score count mismatch")
    except Exception:
        # Fallback: use vector scores only
        return sorted(chunks, key=lambda x: x["score"], reverse=True)[:FINAL_TOP_K]

    # Weighted combination: 60% LLM score + 40% vector score
    for i, chunk in enumerate(chunks):
        llm_score    = float(scores[i]) / 10.0          # normalize 0-1
        vector_score = float(chunk.get("score", 0))
        chunk["final_score"] = 0.6 * llm_score + 0.4 * vector_score

    reranked = sorted(chunks, key=lambda x: x["final_score"], reverse=True)
    return reranked[:FINAL_TOP_K]


# ── Answer generation — RAG mode ──────────────────────────────────────────────

def generate_answer_from_docs(query: str, chunks: list[dict]) -> str:
    """
    Strict grounded answer. LLM must cite chunk IDs and cannot use
    outside knowledge. Low temperature = more factual, less creative.
    """
    groq    = get_groq()
    context = "\n\n".join(
        f"[CHUNK {i} | source: {c.get('source','?')}]\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    prompt = (
        "You are a precise document Q&A assistant.\n"
        "Your job: answer the query using ONLY the document chunks below.\n\n"
        "STRICT RULES:\n"
        "1. Use ONLY information from the chunks. Do NOT add outside knowledge.\n"
        "2. Cite the chunk number like [CHUNK 0], [CHUNK 2] after each fact.\n"
        "3. If multiple chunks say the same thing, combine them.\n"
        "4. If the answer is NOT in any chunk, say exactly: "
        "'This information is not present in the uploaded documents.'\n"
        "5. Be specific and detailed — do not give vague summaries.\n"
        "6. If the query asks for a list, numbers, dates, or names — extract them exactly.\n"
        "7. Use bullet points or numbered lists when listing multiple items.\n\n"
        f"=== DOCUMENT CHUNKS ===\n{context}\n\n"
        f"=== QUERY ===\n{query}\n\n"
        "=== ANSWER ==="
    )

    response = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=800,
        temperature=0.1,   # very low = highly factual
    )
    return response.choices[0].message.content.strip()


# ── Answer generation — General fallback ──────────────────────────────────────

def generate_answer_general(query: str) -> str:
    """Fallback — direct LLaMA answer with no document context."""
    groq   = get_groq()
    prompt = (
        "You are a knowledgeable and helpful AI assistant and expert programmer.\n"
        "Answer the user's question clearly and concisely.\n"
        "Important rules:\n"
        "- If the question involves code, SQL, scripts, or commands, ALWAYS include "
        "working code examples using proper markdown code blocks "
        "(e.g. ```sql ... ```, ```python ... ```, etc.).\n"
        "- Explain the code briefly after showing it.\n"
        "- Use bullet points for non-code explanations.\n"
        "- Never give theory-only answers when code is applicable.\n\n"
        f"Question: {query}\n\nAnswer:"
    )
    response = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=900,
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()


# ── Full pipeline ─────────────────────────────────────────────────────────────

def phase3_pipeline(query: str, limit: int = RETRIEVAL_CANDIDATES) -> dict:

    # Case 1: No documents uploaded
    if not _collection_has_points():
        print("[RAG] No documents — general fallback.")
        answer = generate_answer_general(query)
        return {
            "chunks":     [],
            "llm_answer": f"⚠️ No documents uploaded yet. Answering from general knowledge:\n\n{answer}",
            "citations":  [],
            "mode":       "general",
        }

    # Case 2: Retrieve candidates
    print(f"[RAG] Multi-query retrieval (pool={limit})...")
    chunks = retrieve(query, limit=limit)

    # Case 3: Low confidence → fallback
    top_score = chunks[0]["score"] if chunks else 0.0
    if not chunks or top_score < MIN_RELEVANCE_SCORE:
        print(f"[RAG] Low confidence (top={top_score:.2f}) — general fallback.")
        answer = generate_answer_general(query)
        return {
            "chunks":     [],
            "llm_answer": f"ℹ️ Topic not found in your documents. Answering from general knowledge:\n\n{answer}",
            "citations":  [],
            "mode":       "general",
        }

    # Case 4: Stitch adjacent chunks for coherence
    print("[RAG] Stitching adjacent chunks...")
    stitched = stitch_chunks(chunks)

    # Case 5: LLM reranking
    print("[RAG] Reranking with LLM scores...")
    reranked = rerank_with_llm(query, stitched)

    # Case 6: Generate grounded answer
    print("[RAG] Generating grounded answer...")
    answer = generate_answer_from_docs(query, reranked)

    return {
        "chunks":     reranked,
        "llm_answer": answer,
        "citations":  [c["id"] for c in reranked],
        "mode":       "rag",
    }


# ── Upload helper ─────────────────────────────────────────────────────────────

def add_file_to_rag(file_path: Path | str) -> None:
    file_path = Path(file_path)
    print(f"[UPLOAD] Indexing '{file_path.name}'...")
    text   = read_uploaded_file(file_path)
    chunks = split_text_into_chunks(text)

    embedder = get_embedder()
    qdrant   = get_qdrant()

    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedder.encode(c["text"], normalize_embeddings=True).tolist(),
            payload={
                "text":        c["text"],
                "source_file": file_path.name,
                "chunk_id":    c["id"],
            },
        )
        for c in chunks
    ]
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"[UPLOAD] '{file_path.name}' indexed — {len(points)} chunks.")


# ── Document summarizer ───────────────────────────────────────────────────────

def summarize_document(file_path: Path | str) -> str:
    file_path = Path(file_path)
    print(f"[SUMMARIZE] Reading '{file_path.name}'...")
    text = read_uploaded_file(file_path)

    if not text.strip():
        return "Could not extract any text from this document."

    groq      = get_groq()
    MAX_CHARS = 3000
    segments  = [text[i:i+MAX_CHARS] for i in range(0, min(len(text), 15000), MAX_CHARS)]

    segment_summaries = []
    for i, segment in enumerate(segments):
        prompt = (
            "You are a helpful assistant that explains documents in simple, "
            "clear language that anyone can understand.\n"
            f"Summarize this section (part {i+1}/{len(segments)}) "
            "in 3-5 bullet points. Use plain English, no jargon:\n\n"
            f"{segment}"
        )
        resp = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.3,
        )
        segment_summaries.append(resp.choices[0].message.content.strip())

    if len(segment_summaries) == 1:
        return segment_summaries[0]

    combined     = "\n\n".join(segment_summaries)
    merge_prompt = (
        "Below are summaries of different parts of a document. "
        "Combine them into one clear, easy-to-read summary in simple language. "
        "Use bullet points. Cover main topics, key facts, and important takeaways:\n\n"
        f"{combined}\n\nFinal Summary:"
    )
    merge_resp = groq.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": merge_prompt}],
        max_tokens=600,
        temperature=0.3,
    )
    return merge_resp.choices[0].message.content.strip()
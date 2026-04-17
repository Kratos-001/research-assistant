import re
import hashlib
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

import os

# Persistent ChromaDB client and Embedding Model.
# We initialize these lazily to avoid uvicorn startup delays, but we forcefully 
# disable HF network calls to avoid the infamous httpx "closed client" thread crashes.
_chroma_client = None
_embedding_fn = None


def get_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path="./chroma_db")
    return _chroma_client


def get_embedding_fn() -> SentenceTransformerEmbeddingFunction:
    global _embedding_fn
    if _embedding_fn is None:
        # Bypasses httpx network calls completely; only uses the local cache
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TOKENIZERS_PARALLELISM"] = "false"
        _embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    return _embedding_fn


def _collection_name(file_name: str) -> str:
    """Derive a valid ChromaDB collection name from the filename.

    ChromaDB rules: 3-63 chars, alphanumeric/hyphens/underscores,
    starts and ends with alphanumeric.
    We use a sanitized name + 8-char hash suffix to avoid collisions.
    """
    stem = re.sub(r"[^a-zA-Z0-9]", "_", file_name)[:40].strip("_") or "doc"
    suffix = hashlib.md5(file_name.encode()).hexdigest()[:8]
    return f"{stem}_{suffix}"


# ── Separators for recursive chunking (coarsest → finest) ─────────────────
_SEPARATORS = ["\n\n\n", "\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Recursively split text using natural boundaries (paragraphs → sentences → words)."""
    return _recursive_split(text.strip(), chunk_size, overlap, _SEPARATORS)


def _word_count(s: str) -> int:
    return len(s.split())


def _recursive_split(text: str, chunk_size: int, overlap: int, separators: list[str]) -> list[str]:
    if _word_count(text) <= chunk_size:
        return [text] if text.strip() else []

    sep = separators[0]
    remaining_seps = separators[1:]

    if sep == "":
        words = text.split()
        chunks = []
        start = 0
        while start < len(words):
            end = start + chunk_size
            chunks.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start += chunk_size - overlap
        return chunks

    parts = re.split(re.escape(sep), text)
    if sep not in ("\n\n\n", "\n\n", "\n", " ", ""):
        parts = [p + sep for p in parts[:-1]] + [parts[-1]]

    chunks: list[str] = []
    current_words: list[str] = []

    for part in parts:
        part = part.strip()
        if not part:
            continue

        part_words = part.split()

        if len(part_words) > chunk_size:
            if current_words:
                chunks.append(" ".join(current_words))
                current_words = current_words[-overlap:] if overlap else []
            sub_chunks = _recursive_split(part, chunk_size, overlap, remaining_seps)
            if sub_chunks:
                chunks.extend(sub_chunks)
                current_words = sub_chunks[-1].split()[-overlap:] if overlap else []
            continue

        if len(current_words) + len(part_words) > chunk_size:
            if current_words:
                chunks.append(" ".join(current_words))
                current_words = current_words[-overlap:] if overlap else []

        current_words.extend(part_words)

    if current_words:
        chunks.append(" ".join(current_words))

    return [c for c in chunks if c.strip()]


# ── ChromaDB ingestion ─────────────────────────────────────────────────────

def store_document(file_name: str, document_text: str) -> tuple[str, int]:
    """Chunk the document, embed with sentence-transformers, and persist to ChromaDB.

    Stores per-chunk metadata:
      - file_name: original upload name
      - chunk_index: position in the document
      - total_chunks: total number of chunks for this document
      - char_start: approximate character offset of the chunk

    Returns (collection_name, total_chunks) so the caller can persist
    document-level metadata to the SQLite registry.
    Always recreates the collection so re-uploading the same file is idempotent.
    """
    client = get_client()
    ef = get_embedding_fn()
    name = _collection_name(file_name)

    # Drop existing collection for this file (idempotent re-upload)
    try:
        client.delete_collection(name)
    except Exception:
        pass

    collection = client.create_collection(
        name=name,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},  # cosine similarity
    )

    chunks = chunk_text(document_text)
    if not chunks:
        return name, 0

    # Build approximate char-offset map for metadata
    char_offsets = []
    pos = 0
    for chunk in chunks:
        idx = document_text.find(chunk[:50], pos)  # find start of chunk
        char_offsets.append(idx if idx != -1 else pos)
        pos = max(pos, idx + 1) if idx != -1 else pos

    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))],
        metadatas=[
            {
                "file_name": file_name,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "char_start": char_offsets[i],
            }
            for i in range(len(chunks))
        ],
    )

    return name, len(chunks)


# ── ChromaDB similarity search ─────────────────────────────────────────────

def similarity_search(collection_name: str, query: str, top_k: int = 5, max_distance: float = 0.75) -> list[dict]:
    """Cosine-similarity search against a stored ChromaDB collection.

    Returns a list of dicts with 'text' and 'metadata' keys, ranked by
    similarity (ChromaDB returns closest first when space=cosine).
    Filters out results with distance greater than max_distance.
    """
    client = get_client()
    ef = get_embedding_fn()

    collection = client.get_collection(name=collection_name, embedding_function=ef)
    # Fetch a larger candidate pool to ensure we have top_k AFTER distance filtering
    n = min(top_k * 2, collection.count())
    if n == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=n,
        include=["documents", "metadatas", "distances"],
    )

    valid_results = [
        {"text": doc, "metadata": meta, "distance": dist}
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
        if dist <= max_distance
    ]
    
    return valid_results[:top_k]


def reconstruct_text(collection_name: str, max_chars: int = 15000) -> str:
    """Reconstruct document text from stored chunks, ordered by chunk_index."""
    try:
        client = get_client()
        ef = get_embedding_fn()
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        if collection.count() == 0:
            return ""
        result = collection.get(include=["documents", "metadatas"])
        pairs = sorted(
            zip(result["documents"], result["metadatas"]),
            key=lambda x: x[1].get("chunk_index", 0),
        )
        full_text = " ".join(doc for doc, _ in pairs)
        return full_text[:max_chars]
    except Exception:
        return ""

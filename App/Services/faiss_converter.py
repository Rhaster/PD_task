"""  Faiss index builder from markdown files. contains chunking and embedding logic."""
from pathlib import Path
import re, json, uuid, logging
from typing import List, Dict
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from App.Services.utility import logging_function

_model = SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

_HEADING_RE = re.compile(r"^(#{1,6})\s+.+$", flags=re.MULTILINE)


def _split_by_headings(md: str) -> List[str]:
    """Split markdown ``md`` into sections using heading boundaries."""
    if not _HEADING_RE.search(md):
        return [md.strip()]
    parts = []
    last = 0
    for m in _HEADING_RE.finditer(md):
        start = m.start()
        if start > last:
            parts.append(md[last:start].strip())
        last = start
    parts.append(md[last:].strip())
    return [p for p in parts if p]

def _word_chunks(text: str, chunk_words: int, overlap_words: int) -> List[str]:
    """Return word-based chunks with a sliding window overlap."""
    words = text.split()
    if not words:
        return []
    chunks = []
    step = max(1, chunk_words - overlap_words)
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_words]).strip()
        if chunk:
            chunks.append(chunk)
        if i + chunk_words >= len(words):
            break
    return chunks

def chunk_markdown_local(md: str, chunk_words: int = 220, overlap_words: int = 50) -> List[Dict[str, str]]:
    """Convert a markdown string into a list of chunk records with UUIDs."""
    records = []
    sections = _split_by_headings(md)
    for sec in sections:
        norm = re.sub(r"\s+", " ", sec).strip()
        for chunk in _word_chunks(norm, chunk_words=chunk_words, overlap_words=overlap_words):
            records.append({"id": str(uuid.uuid4()), "text": chunk})
    return records


def embed_texts(texts: List[str], batch_size: int = 64) -> np.ndarray:
    """Encode ``texts`` into L2-normalized vectors for FAISS storage."""
    vecs = _model.encode(texts, normalize_embeddings=True, batch_size=batch_size)
    return np.array(vecs, dtype="float32")


def build_index(
    story_path: str,
    out_index_path: str = "data/index.faiss",
    out_meta_path: str = "data/index.faiss.meta.jsonl",
    chunk_words: int = 220,
    overlap_words: int = 50
) -> dict:
    """Build a FAISS index from a markdown file and return metadata.

    Raises FileNotFoundError or RuntimeError on invalid inputs.
    """
    path = Path(story_path)
    if not path.exists():
        raise FileNotFoundError(f"File {story_path} does not exist.")
    md = path.read_text(encoding="utf-8", errors="ignore").strip()
    if not md:
        raise RuntimeError(f"File {story_path} is empty.")

    records = chunk_markdown_local(md, chunk_words, overlap_words)
    if not records:
        raise RuntimeError("No records to index.")

    texts = [r["text"] for r in records]
    vecs = embed_texts(texts)
    dim = vecs.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(vecs)

    Path(out_index_path).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, out_index_path)

    Path(out_meta_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_meta_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    logging_function(f"FAISS index finished: {len(records)} chunks, dim={dim}", level="info")
    return {"chunks": len(records), "index_path": str(out_index_path), "meta_path": str(out_meta_path)}
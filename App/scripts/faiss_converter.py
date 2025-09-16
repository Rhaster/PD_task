# scripts/faiss_converter.py
# Script to build a FAISS index from a markdown story file using local embeddings.
# saves index and metadata to specified paths.
# Also includes a quick search function for testing the index.



from __future__ import annotations
from pathlib import Path
import re
import json
import argparse
from typing import List, Dict, Tuple

import numpy as np
import faiss

from sentence_transformers import SentenceTransformer
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")  # 384D
#


def embed_texts(texts: List[str]) -> List[List[float]]:
    vecs = _model.encode(texts, normalize_embeddings=True)
    return vecs.tolist()

_HEADING_RE = re.compile(r"^(#{1,6})\s+.+$", flags=re.MULTILINE)

def _split_by_headings(md: str) -> List[str]:
    if not _HEADING_RE.search(md):
        return [md]
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
    """
        Divide a text block into smaller chunks of words with overlap.

        Args:
            text (str): Input text to split.
            chunk_words (int): Number of words per chunk.
            overlap_words (int): Number of overlapping words between consecutive chunks.

        Returns:
            List[str]: List of word chunks as strings.
        
    """
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


def chunk_markdown_local(
    md: str,
    chunk_words: int = 220,
    overlap_words: int = 50,
) -> List[Dict[str, str]]:
    """
    Minimalny zamiennik md_chunker.chunk_markdown.
    Zwraca listę rekordów: {"id": "...", "text": "..."}.
    Najpierw dzieli po nagłówkach, potem tnie sekcje po słowach.
    """
    records = []
    sections = _split_by_headings(md)
    cid = 0
    for sec in sections:
        # usuwamy nadmiarowe pustki, scalmy nowe linie
        norm = re.sub(r"\s+", " ", sec).strip()
        for chunk in _word_chunks(norm, chunk_words=chunk_words, overlap_words=overlap_words):
            records.append({"id": f"chunk-{cid}", "text": chunk})
            cid += 1
    return records


# ----------------------------
# Budowa indeksu
# ----------------------------
def build_index(
    story_path: str,
    out_index_path: str = "data/index.faiss",
    out_meta_path: str = "data/index.faiss.meta.jsonl",
    chunk_words: int = 220,
    overlap_words: int = 50,
) -> dict:
    md = Path(story_path).read_text(encoding="utf-8")
    records = chunk_markdown_local(md, chunk_words=chunk_words, overlap_words=overlap_words)
    if not records:
        raise RuntimeError("Brak rekordów do indeksowania (sprawdź wejściowy plik).")

    texts = [r["text"] for r in records]
    vecs = embed_texts(texts)  # już znormalizowane (cosine-ready)
    dim = len(vecs[0])

    xb = np.array(vecs, dtype="float32")
    index = faiss.IndexFlatIP(dim)  # cosine przy znormalizowanych wektorach
    index.add(xb)

    Path(out_index_path).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, out_index_path)

    Path(out_meta_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_meta_path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    return {"chunks": len(records), "index_path": out_index_path, "meta_path": out_meta_path}


# ----------------------------
# Szybkie wyszukiwanie (smoke test)
# ----------------------------
def _load_meta(meta_path: str) -> Dict[int, Dict[str, str]]:
    meta = {}
    with open(meta_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            meta[i] = json.loads(line)
    return meta

def _embed_query(q: str) -> np.ndarray:
    v = _model.encode([q], normalize_embeddings=True)
    return np.asarray(v, dtype="float32")

def quick_search(query: str, index_path: str, meta_path: str, k: int = 3) -> List[Tuple[str, str]]:
    index = faiss.read_index(index_path)
    meta = _load_meta(meta_path)
    qv = _embed_query(query)
    D, I = index.search(qv, k)
    hits = []
    for idx in I[0]:
        if idx == -1:
            continue
        rec = meta.get(int(idx))
        if not rec:
            continue
        preview = rec["text"][:140].replace("\n", " ") + ("..." if len(rec["text"]) > 140 else "")
        hits.append((rec["id"], preview))
    return hits


# ----------------------------
# CLI
# ----------------------------
def cli():
    ap = argparse.ArgumentParser(description="Build FAISS index from story (local embeddings).")
    ap.add_argument("--story", default="data/fantasy.md", help="Ścieżka do pliku historii (.md/.txt)")
    ap.add_argument("--index", default="data/index.faiss", help="Ścieżka wyjściowa indeksu FAISS")
    ap.add_argument("--meta", default="data/index.faiss.meta.jsonl", help="Ścieżka wyjściowa metadanych JSONL")
    ap.add_argument("--chunk-words", type=int, default=220)
    ap.add_argument("--overlap-words", type=int, default=50)
    ap.add_argument("--k", type=int, default=3, help="k dla quick_search")
    ap.add_argument("--test-query", default="Kim są Ironhold Clans?", help="Pytanie do smoke-testu")
    args = ap.parse_args()

    info = build_index(
        story_path=args.story,
        out_index_path=args.index,
        out_meta_path=args.meta,
        chunk_words=args.chunk_words,
        overlap_words=args.overlap_words,
    )
    print("Zbudowano indeks:", info)

    # szybki test
    hits = quick_search(args.test_query, args.index, args.meta, k=args.k)
    print("Przykładowe trafienia:")
    for cid, preview in hits:
        print("-", cid, "→", preview)


if __name__ == "__main__":
    cli()
# Uruchom: python scripts/faiss_converter.py --story data/fantasy.md --index data/index.faiss --meta data/index.meta.jsonl --test-query "Kim są Ironhold Clans?"
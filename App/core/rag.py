
"""FAISS-backed retrieval over sentence embeddings.

The ``FaissRAG`` class loads a vector index and its metadata, performs search
over normalized embeddings, and returns identified chunk IDs with their text.
"""
from pathlib import Path
from typing import List, Tuple
import json, faiss, numpy as np
from App.Core.embeddings_local import embed_texts

CHUNK_PREFIX = "chunk_"
BASE_DIR = Path(__file__).resolve().parents[2]  
print("BASE_DIR", BASE_DIR)
DEFAULT_INDEX = BASE_DIR / "App" / "Data" / "index.faiss"

class FaissRAG:
    """Lightweight wrapper around a FAISS index and its metadata."""

    def __init__(self, index_path: str | Path = DEFAULT_INDEX):
        """Initialize with the path to the index (and inferred meta path)."""
        self.index_path = Path(index_path)
        self.meta_path = self.index_path.with_suffix(self.index_path.suffix + ".meta.jsonl")
        self.index = None
        self.texts: list[str] = []
        self.ids: list[str] = []

    def load(self):
        """Load FAISS index and metadata lines into memory."""
        if not self.index_path.exists() or not self.meta_path.exists():
            raise FileNotFoundError("Missing index/metadata files — run ingest first.")
        self.index = faiss.read_index(str(self.index_path))
        self.ids, self.texts = [], []
        with self.meta_path.open("r", encoding="utf-8") as f:
            for line in f:
                o = json.loads(line)
                self.ids.append(o["id"])
                self.texts.append(o["text"])
        if self.index.ntotal != len(self.ids):
            raise RuntimeError("Index and metadata size mismatch.")

    def search(self, query: str, k: int = 4) -> List[Tuple[str, str]]:
        """Return up to ``k`` best-matching chunks for the ``query`` string."""
        if self.index is None:
            self.load()
        q = np.array([embed_texts([query])[0]], dtype="float32")
        faiss.normalize_L2(q)
        D, I = self.index.search(q, k)
        out: List[Tuple[str, str]] = []
        for idx in I[0]:
            if idx == -1:
                continue
            out.append((self.ids[idx], self.texts[idx]))
        return out

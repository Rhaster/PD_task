"""Local embeddings using SentenceTransformers."""
from sentence_transformers import SentenceTransformer
_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")  # 384D
def embed_texts(texts: list[str]) -> list[list[float]]:
    vecs = _model.encode(texts, normalize_embeddings=True)
    return vecs.tolist()
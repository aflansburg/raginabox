from dataclasses import dataclass

import numpy as np


@dataclass
class Document:
    doc_id: str
    chunks: list[dict]
    embeddings: np.ndarray


class VectorStore:
    def __init__(self):
        self.documents: dict[str, Document] = {}

    def store(self, doc_id: str, chunks: list[dict], embeddings: np.ndarray) -> None:
        self.documents[doc_id] = Document(doc_id=doc_id, chunks=chunks, embeddings=embeddings)

    def search(self, doc_id: str, query_embedding: np.ndarray, top_k: int = 3) -> list[dict]:
        doc = self.documents[doc_id]
        query_norm = query_embedding / np.linalg.norm(query_embedding)
        doc_norms = doc.embeddings / np.linalg.norm(doc.embeddings, axis=1, keepdims=True)
        similarities = (doc_norms @ query_norm.T).flatten()
        top_indices = np.argsort(similarities)[::-1][:top_k]
        return [
            {
                "chunk_index": int(idx),
                "chunk_text": doc.chunks[idx]["text"],
                "score": float(similarities[idx]),
                "embedding_preview": doc.embeddings[idx][:10].tolist(),
            }
            for idx in top_indices
        ]

    def get(self, doc_id: str) -> Document | None:
        return self.documents.get(doc_id)

    def delete(self, doc_id: str) -> bool:
        return self.documents.pop(doc_id, None) is not None

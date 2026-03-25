import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os

class VectorService:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension = 384  # for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.id_to_event = {}  # Map FAISS index to event_id
        self.event_to_index = {}  # Map event_id to FAISS index

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        embedding = self.model.encode(text, convert_to_numpy=True)
        # Normalize for cosine similarity
        return embedding / np.linalg.norm(embedding)

    def add_vector(self, event_id: int, vector: np.ndarray, metadata: dict = None):
        """Add vector to FAISS index"""
        self.index.add(vector.reshape(1, -1))
        index_pos = self.index.ntotal - 1
        self.id_to_event[index_pos] = event_id
        self.event_to_index[event_id] = index_pos

    def search_similar(self, query_vector: np.ndarray, k: int = 5):
        """Search for similar vectors"""
        distances, indices = self.index.search(query_vector.reshape(1, -1), k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                event_id = self.id_to_event.get(idx)
                results.append((event_id, dist))
        return results

# Global instance
vector_service = VectorService()
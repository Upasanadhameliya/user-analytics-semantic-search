import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import os

from app.models import EventEmbedding

class VectorService:
    def __init__(self):
        self.model = None  # lazy load
        self.dimension = 384  # for all-MiniLM-L6-v2
        self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        self.id_to_event = {}  # Map FAISS index to event_id
        self.event_to_index = {}  # Map event_id to FAISS index

    def load_model(self):
        if self.model is None:
            print("Loading embedding model...")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')

    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for text"""
        self.load_model()  # 👈 ensure loaded
        embedding = self.model.encode(text, convert_to_numpy=True)
        # Normalize for cosine similarity
        return embedding / np.linalg.norm(embedding)

    def add_vector(self, event_id: int, vector: np.ndarray, metadata: dict = None):
        """Add vector to FAISS index and return the index position"""
        self.index.add(vector.reshape(1, -1))
        index_pos = self.index.ntotal - 1
        self.id_to_event[index_pos] = event_id
        self.event_to_index[event_id] = index_pos
        return index_pos

    def search_similar(self, query_vector: np.ndarray, k: int = 5):
        """Search for similar vectors"""
        distances, indices = self.index.search(query_vector.reshape(1, -1), k)
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx != -1:
                event_id = self.id_to_event.get(idx)
                results.append((event_id, dist))
        return results

    def rebuild_index(self, db):
        """Rebuild FAISS index from database embeddings"""

        # Reset index and mappings
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_to_event = {}
        self.event_to_index = {}

        # Fetch embeddings in consistent order
        embeddings = db.query(EventEmbedding).order_by(EventEmbedding.id).all()

        # Rebuild index
        for record in embeddings:
            vector = np.array(record.embedding, dtype=np.float32)

            # Normalize (important for cosine similarity with IndexFlatIP)
            norm = np.linalg.norm(vector)
            if norm == 0:
                continue  # skip bad vectors safely
            vector = vector / norm

            # Add to FAISS
            self.index.add(vector.reshape(1, -1))

            # Get actual FAISS index position
            idx = self.index.ntotal - 1

            # Rebuild mappings
            self.id_to_event[idx] = record.event_id
            self.event_to_index[record.event_id] = idx

        print(f"[FAISS] Rebuilt index with {self.index.ntotal} vectors")

# Global instance
vector_service = VectorService()
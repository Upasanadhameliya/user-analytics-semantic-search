from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from app.db.base import Base

class EventEmbedding(Base):
    __tablename__ = "event_embeddings"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    faiss_index = Column(Integer, nullable=False, index=True)
    embedding = Column(JSONB, nullable=False)

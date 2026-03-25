from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import User, Event, EventEmbedding
from datetime import datetime
from app.services.vector_service import vector_service

class EventService:
    def __init__(self):
        pass

    def get_or_create_user(self, db: Session, external_user_id: str) -> User:
        """Get user by external_id or create if not exists"""
        user = db.query(User).filter(User.external_user_id == external_user_id).first()
        if not user:
            user = User(external_user_id=external_user_id)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def create_event(self, db: Session, user_id: int, event_name: str, event_metadata: dict, timestamp: datetime = None) -> Event:
        """Create and save event to database"""
        event = Event(
            user_id=user_id,
            event_name=event_name,
            event_metadata=event_metadata,
            timestamp=timestamp or datetime.utcnow()
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def track_event(self, user_id: str, event: str, metadata: dict, timestamp: str = None):
        """Main tracking function"""
        with SessionLocal() as db:
            # Get or create user
            user = self.get_or_create_user(db, user_id)

            # Parse timestamp if provided
            event_timestamp = None
            if timestamp:
                try:
                    event_timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except:
                    pass  # Use default if invalid

            # Create event
            event_obj = self.create_event(db, user.id, event, metadata, event_timestamp)

            # Generate embedding
            text_to_embed = f"{event} {metadata}"
            embedding = vector_service.generate_embedding(text_to_embed)

            # Store in vector DB
            vector_service.add_vector(event_obj.id, embedding, metadata)
            faiss_index = vector_service.index.ntotal - 1

            # Persist vector mapping in SQL
            embedding_record = db.query(EventEmbedding).filter(EventEmbedding.event_id == event_obj.id).first()
            if not embedding_record:
                embedding_record = EventEmbedding(event_id=event_obj.id, faiss_index=faiss_index)
                db.add(embedding_record)
            else:
                embedding_record.faiss_index = faiss_index
            db.commit()

            return event_obj

# Global instance
event_service = EventService()
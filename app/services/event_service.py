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
                    pass

            # Create event
            event_obj = self.create_event(db, user.id, event, metadata, event_timestamp)

            # Generate embedding
            text_to_embed = f"{event} {metadata}"
            embedding = vector_service.generate_embedding(text_to_embed)

            # Store in FAISS
            faiss_index = vector_service.add_vector(event_obj.id, embedding)

            # Store embedding + mapping in DB
            embedding_record = EventEmbedding(
                event_id=event_obj.id,
                faiss_index=faiss_index,
                embedding=embedding.tolist()
            )

            db.add(embedding_record)
            db.commit()

            # Convert to dict BEFORE session closes
            return {
                "id": event_obj.id,
                "user_id": event_obj.user_id,
                "event_name": event_obj.event_name,
                "event_metadata": event_obj.event_metadata,
                "timestamp": event_obj.timestamp.isoformat() if event_obj.timestamp else None
            }

    def _build_query_with_filters(self, db: Session, event_filter: str = None, date_from: datetime = None, date_to: datetime = None):
        """Helper to build base query with filters applied"""
        query = db.query(Event)
        
        if event_filter:
            query = query.filter(Event.event_name == event_filter)
        
        if date_from:
            query = query.filter(Event.timestamp >= date_from)
        
        if date_to:
            query = query.filter(Event.timestamp <= date_to)
        
        return query

    def get_total_events_count(self, db: Session, event_filter: str = None, date_from: datetime = None, date_to: datetime = None) -> int:
        """Get total number of events with optional filters"""
        query = self._build_query_with_filters(db, event_filter, date_from, date_to)
        return query.count()

    def get_events_per_user(self, db: Session, event_filter: str = None, date_from: datetime = None, date_to: datetime = None) -> list:
        """Get event count per user with optional filters
        Returns: [{"user_id": int, "event_count": int}, ...]
        """
        from sqlalchemy import func
        
        query = self._build_query_with_filters(db, event_filter, date_from, date_to)
        results = query.with_entities(
            Event.user_id,
            func.count(Event.id).label('event_count')
        ).group_by(Event.user_id).all()
        
        return [{"user_id": row[0], "event_count": row[1]} for row in results]

    def get_most_active_users(self, db: Session, limit: int = 3, event_filter: str = None, date_from: datetime = None, date_to: datetime = None) -> list:
        """Get most active users (by event count) with optional filters
        Returns: [{"external_user_id": str, "event_count": int}, ...]
        """
        from sqlalchemy import func
        
        query = self._build_query_with_filters(db, event_filter, date_from, date_to)
        results = query.join(User, Event.user_id == User.id).with_entities(
            User.external_user_id,
            func.count(Event.id).label('event_count')
        ).group_by(User.external_user_id).order_by(
            func.count(Event.id).desc()
        ).limit(limit).all()
        
        return [{"external_user_id": row[0], "event_count": row[1]} for row in results]


# Global instance
event_service = EventService()
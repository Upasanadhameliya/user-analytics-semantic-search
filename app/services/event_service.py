from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models import User, Event, EventEmbedding
from datetime import datetime
from app.services.vector_service import vector_service
from threading import RLock
import numpy as np


class EventService:
    def __init__(self):
        self._user_profile_cache: dict[int, np.ndarray] = {}
        self._cache_lock = RLock()

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

            # Update cache for this user only
            self._upsert_user_profile_cache(db, user.id)

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

    def search_events(self, db: Session, query_text: str, k: int = 3):
        """Semantic search for events via vector embeddings"""
        from app.models import Event, User
        from sqlalchemy.orm import joinedload

        if not query_text or not query_text.strip():
            raise ValueError("query must be a non-empty string")

        query_vector = vector_service.generate_embedding(query_text)
        similar = vector_service.search_similar(query_vector, k)

        # similar is list[(event_id, score)]
        event_ids = [event_id for event_id, _ in similar]

        if not event_ids:
            return []

        # Fetch events in provided order (no joinedload because no relationship defined)
        events = db.query(Event).filter(Event.id.in_(event_ids)).all()
        event_by_id = {event.id: event for event in events}

        # Build output list with normalized score and event details.
        results = []
        for event_id, dist in similar:
            event_obj = event_by_id.get(event_id)
            if not event_obj:
                continue

            # FAISS index uses normalized vectors so inner product is cosine similarity in -1..1.
            similarity_score = float(dist)
            results.append({
                "event_id": event_obj.id,
                "user_id": event_obj.user_id,
                "event_name": event_obj.event_name,
                "event_metadata": event_obj.event_metadata,
                "timestamp": event_obj.timestamp.isoformat() if event_obj.timestamp else None,
                "similarity_score": similarity_score
            })

        return results

    def _get_or_build_profile_cache(self, db: Session) -> dict:
        """Return cache, building it from DB on first call."""
        with self._cache_lock:
            if not self._user_profile_cache:
                self._user_profile_cache = self._build_user_profile_vectors(db)
            return self._user_profile_cache

    def _recompute_single_user_profile(self, db: Session, user_id: int):
        """Recompute and return normalized profile vector for one user, or None."""
        rows = db.query(EventEmbedding.embedding).join(
            Event, Event.id == EventEmbedding.event_id
        ).filter(Event.user_id == user_id).all()

        vectors = []
        for (embedding,) in rows:
            if embedding is None:
                continue
            vector = np.array(embedding, dtype=np.float32)
            if vector.size > 0:
                vectors.append(vector)

        if not vectors:
            return None

        profile = np.mean(np.stack(vectors), axis=0)
        norm = np.linalg.norm(profile)
        if norm == 0:
            return None
        return profile / norm

    def _upsert_user_profile_cache(self, db: Session, user_id: int):
        """Recompute profile for one user and update cache in-place."""
        profile = self._recompute_single_user_profile(db, user_id)
        with self._cache_lock:
            if profile is not None:
                self._user_profile_cache[user_id] = profile
            else:
                self._user_profile_cache.pop(user_id, None)

    def _build_user_profile_vectors(self, db: Session) -> dict:
        """Build normalized profile vectors per user by averaging event embeddings."""
        rows = db.query(Event.user_id, EventEmbedding.embedding).join(
            EventEmbedding, EventEmbedding.event_id == Event.id
        ).all()

        vectors_by_user = {}
        for user_id, embedding in rows:
            if user_id is None or embedding is None:
                continue
            vector = np.array(embedding, dtype=np.float32)
            if vector.size == 0:
                continue
            vectors_by_user.setdefault(user_id, []).append(vector)

        profiles = {}
        for user_id, user_vectors in vectors_by_user.items():
            profile = np.mean(np.stack(user_vectors), axis=0)
            norm = np.linalg.norm(profile)
            if norm == 0:
                continue
            profiles[user_id] = profile / norm

        return profiles

    def find_similar_users(self, db: Session, user_id: int, k: int = 5) -> list:
        """Find users with similar behavior based on aggregated event embeddings."""
        user_exists = db.query(User.id).filter(User.id == user_id).first()
        if not user_exists:
            raise ValueError("user not found")

        if k < 1:
            raise ValueError("k must be at least 1")

        profiles = self._get_or_build_profile_cache(db)
        query_vector = profiles.get(user_id)
        if query_vector is None:
            return []

        similarities = []
        for candidate_user_id, candidate_vector in profiles.items():
            if candidate_user_id == user_id:
                continue
            score = float(np.dot(query_vector, candidate_vector))
            similarities.append((candidate_user_id, score))

        similarities.sort(key=lambda item: item[1], reverse=True)
        top_k = similarities[:k]

        candidate_ids = [candidate_user_id for candidate_user_id, _ in top_k]
        users = db.query(User.id, User.external_user_id).filter(User.id.in_(candidate_ids)).all()
        user_external_by_id = {uid: external_id for uid, external_id in users}

        results = []
        for candidate_user_id, score in top_k:
            results.append({
                "user_id": candidate_user_id,
                "external_user_id": user_external_by_id.get(candidate_user_id),
                "similarity_score": score
            })

        return results


# Global instance
event_service = EventService()
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.services.event_service import event_service

router = APIRouter()

class TrackRequest(BaseModel):
    userId: str
    event: str
    metadata: Optional[Dict[str, Any]] = {}
    timestamp: Optional[str] = None

@router.post("/track")
def track_event(request: TrackRequest):
    """
    Track user event
    - Store in database
    - Generate embedding
    - Store in vector database
    """
    try:
        event = event_service.track_event(
            user_id=request.userId,
            event=request.event,
            metadata=request.metadata,
            timestamp=request.timestamp
        )
        return {
            "success": True,
            "event_id": event.id,
            "message": "Event tracked successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to track event: {str(e)}")

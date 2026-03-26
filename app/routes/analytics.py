from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.db.session import SessionLocal
from app.services.event_service import event_service

router = APIRouter()


# ============================================================================
# Response Models
# ============================================================================

class EventPerUserStats(BaseModel):
    """Statistics for events per user"""
    user_id: int
    event_count: int


class ActiveUserStats(BaseModel):
    """Statistics for active users"""
    external_user_id: str
    event_count: int


class AnalyticsResponse(BaseModel):
    """Complete analytics response"""
    total_events: int
    events_per_user: List[EventPerUserStats]
    most_active_users: List[ActiveUserStats]


# ============================================================================
# Helper Functions
# ============================================================================

def parse_date_string(date_str: str) -> datetime:
    """Convert ISO date string (YYYY-MM-DD) to datetime
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        
    Returns:
        datetime object at 00:00:00
        
    Raises:
        ValueError: If date format is invalid
    """
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")


def parse_to_date_end_of_day(date_str: str) -> datetime:
    """Convert ISO date string (YYYY-MM-DD) to datetime at 23:59:59
    
    Args:
        date_str: Date string in format YYYY-MM-DD
        
    Returns:
        datetime object at 23:59:59
        
    Raises:
        ValueError: If date format is invalid
    """
    dt = parse_date_string(date_str)
    return dt.replace(hour=23, minute=59, second=59)


# ============================================================================
# Routes
# ============================================================================

@router.get("/analytics", response_model=AnalyticsResponse)
def get_analytics(
    event: Optional[str] = Query(None, description="Filter by event name"),
    from_date: Optional[str] = Query(None, alias="from", description="Start date (YYYY-MM-DD), inclusive"),
    to_date: Optional[str] = Query(None, alias="to", description="End date (YYYY-MM-DD), inclusive"),
    limit: Optional[int] = Query(3, description="Number of most active users to return")
):
    """
    Get comprehensive analytics about events
    
    Returns:
    - Total number of events
    - Events per user
    - Most active users (top N)
    
    Optional filters:
    - event: Filter by event name (exact match)
    - from: Start date (YYYY-MM-DD)
    - to: End date (YYYY-MM-DD)
    - limit: Number of most active users (default: 3)
    
    Examples:
    - GET /analytics
    - GET /analytics?event=click
    - GET /analytics?from=2026-01-01&to=2026-01-02
    - GET /analytics?event=click&from=2026-01-01&to=2026-01-02&limit=5
    """
    
    # Parse and validate parameters
    date_from = None
    date_to = None
    
    try:
        if from_date:
            date_from = parse_date_string(from_date)
        
        if to_date:
            date_to = parse_to_date_end_of_day(to_date)
        
        if limit < 1:
            raise ValueError("limit must be at least 1")
        
        if limit > 1000:
            raise ValueError("limit cannot exceed 1000")
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Query analytics
    try:
        with SessionLocal() as db:
            total_events = event_service.get_total_events_count(
                db, 
                event_filter=event,
                date_from=date_from,
                date_to=date_to
            )
            
            events_per_user = event_service.get_events_per_user(
                db,
                event_filter=event,
                date_from=date_from,
                date_to=date_to
            )
            
            most_active_users = event_service.get_most_active_users(
                db,
                limit=limit,
                event_filter=event,
                date_from=date_from,
                date_to=date_to
            )
        
        # Build response
        events_per_user_stats = [
            EventPerUserStats(user_id=item["user_id"], event_count=item["event_count"])
            for item in events_per_user
        ]
        
        most_active_users_stats = [
            ActiveUserStats(external_user_id=item["external_user_id"], event_count=item["event_count"])
            for item in most_active_users
        ]
        
        return AnalyticsResponse(
            total_events=total_events,
            events_per_user=events_per_user_stats,
            most_active_users=most_active_users_stats
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List
from app.db.session import SessionLocal
from app.services.event_service import event_service

router = APIRouter()


class EventSearchResult(BaseModel):
    event_id: int
    user_id: int
    event_name: str
    event_metadata: dict
    timestamp: str
    similarity_score: float


class SearchResponse(BaseModel):
    query: str
    results_count: int
    results: List[EventSearchResult]


@router.get("/search", response_model=SearchResponse)
def search(query: str = Query(..., min_length=1, max_length=500), limit: int = Query(3, ge=1, le=50)):
    """Semantic search for events using FAISS embeddings"""
    try:
        with SessionLocal() as db:
            results = event_service.search_events(db, query_text=query, k=limit)

            return SearchResponse(
                query=query,
                results_count=len(results),
                results=[EventSearchResult(**r) for r in results]
            )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search error: {str(e)}")

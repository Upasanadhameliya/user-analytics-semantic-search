from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List

from app.db.session import SessionLocal
from app.models import User
from app.services.event_service import event_service

router = APIRouter()


class SimilarUserResult(BaseModel):
	user_id: int
	external_user_id: str | None = None
	similarity_score: float


class SimilarUsersResponse(BaseModel):
	query_user_id: str
	results_count: int
	results: List[SimilarUserResult]


@router.get("/similar-users", response_model=SimilarUsersResponse)
def similar_users(
	userId: str = Query(..., min_length=1, description="External user ID to find similar users for"),
	limit: int = Query(5, ge=1, le=50, description="Maximum number of similar users to return")
):
	"""Find users with similar behavior using aggregated event embeddings."""
	try:
		with SessionLocal() as db:
			user = db.query(User).filter(User.external_user_id == userId).first()
			if not user:
				raise HTTPException(status_code=404, detail="User not found")

			results = event_service.find_similar_users(db, user_id=user.id, k=limit)

		return {
			"query_user_id": userId,
			"results_count": len(results),
			"results": results
		}
	except HTTPException:
		raise
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc))
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Failed to fetch similar users: {str(exc)}")

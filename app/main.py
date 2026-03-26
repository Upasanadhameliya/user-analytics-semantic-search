from fastapi import FastAPI
from app.db.session import SessionLocal
from app.services.vector_service import vector_service

app = FastAPI(
    title="User Analytics Semantic Search",
    description="Backend system for tracking user events, providing analytics, and enabling semantic search using embeddings.",
    version="1.0.0"
)

@app.on_event("startup")
def startup_event():
    """Rebuild FAISS index from database on app startup"""
    with SessionLocal() as db:
        vector_service.rebuild_index(db)

@app.get("/")
def read_root():
    return {"message": "Welcome to User Analytics Semantic Search API"}

# Include routers
from app.routes import track, analytics
app.include_router(track.router, tags=["tracking"])
app.include_router(analytics.router, tags=["analytics"])
from fastapi import FastAPI

app = FastAPI(
    title="User Analytics Semantic Search",
    description="Backend system for tracking user events, providing analytics, and enabling semantic search using embeddings.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to User Analytics Semantic Search API"}

# Include routers
from app.routes import track
app.include_router(track.router, tags=["tracking"])
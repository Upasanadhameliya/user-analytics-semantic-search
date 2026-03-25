from fastapi import FastAPI

app = FastAPI(
    title="User Analytics Semantic Search",
    description="Backend system for tracking user events, providing analytics, and enabling semantic search using embeddings.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "Welcome to User Analytics Semantic Search API"}

# TODO: Include routers when implemented
# from app.routes import track, analytics, search, users
# app.include_router(track.router, prefix="/track", tags=["tracking"])
# app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
# app.include_router(search.router, prefix="/search", tags=["search"])
# app.include_router(users.router, prefix="/users", tags=["users"])
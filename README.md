# user-analytics-semantic-search

A backend system for tracking user events, providing analytics, and enabling semantic search using embeddings.

---

## Installation

### Prerequisites

- Python 3.10+
- Docker and Docker Compose

---

### 1. Start the database

The database is a PostgreSQL instance defined in `docker-compose.yml`. Start it with:

```
docker compose up -d
```

This starts a PostgreSQL container on port `5432` with:
- User: `admin`
- Password: `password`
- Database: `analytics`

---

### 2. Create a virtual environment

```
python -m venv venv
```

Activate it:

On Windows:
```
venv\Scripts\activate
```

On macOS/Linux:
```
source venv/bin/activate
```

---

### 3. Install dependencies

```
pip install -r requirements.txt
```

---

### 4. Create database tables

Run Alembic migrations to create all required tables:

```
alembic upgrade head
```

---

### 5. Start the application

```
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive API docs are available at `http://localhost:8000/docs`.

---

## API Reference

### POST /track

Track a user event. Stores the event in the database and generates a semantic embedding.

**curl**

```
curl -X POST "http://localhost:8000/track" -H "Content-Type: application/json" -d "{\"userId\": \"user123\", \"event\": \"page_view\", \"metadata\": {\"page\": \"/home\"}}"
```

```
curl -X POST "http://localhost:8000/track" -H "Content-Type: application/json" -d "{\"userId\": \"user456\", \"event\": \"button_click\", \"metadata\": {\"button\": \"signup\"}}"
```

```
curl -X POST "http://localhost:8000/track" -H "Content-Type: application/json" -d "{\"userId\": \"user789\", \"event\": \"search\", \"metadata\": {\"query\": \"laptop\"}}"
```

```
curl -X POST "http://localhost:8000/track" -H "Content-Type: application/json" -d "{\"userId\": \"user123\", \"event\": \"purchase\", \"metadata\": {\"item\": \"laptop\", \"price\": 999}, \"timestamp\": \"2026-03-01T10:00:00Z\"}"
```

```
curl -X POST "http://localhost:8000/track" -H "Content-Type: application/json" -d "{\"userId\": \"user999\", \"event\": \"logout\", \"metadata\": {}}"
```

**Postman**

Method: `POST`
URL: `http://localhost:8000/track`
Headers: `Content-Type: application/json`

Body 1:
```json
{
	"userId": "user123",
	"event": "page_view",
	"metadata": { "page": "/home" }
}
```

Body 2:
```json
{
	"userId": "user456",
	"event": "button_click",
	"metadata": { "button": "signup" }
}
```

Body 3:
```json
{
	"userId": "user789",
	"event": "search",
	"metadata": { "query": "laptop" }
}
```

Body 4:
```json
{
	"userId": "user123",
	"event": "purchase",
	"metadata": { "item": "laptop", "price": 999 },
	"timestamp": "2026-03-01T10:00:00Z"
}
```

Body 5:
```json
{
	"userId": "user999",
	"event": "logout",
	"metadata": {}
}
```

---

### GET /analytics

Returns total event count, events per user, and most active users. Supports optional filters.

```
curl "http://localhost:8000/analytics"
```

```
curl "http://localhost:8000/analytics?event=page_view"
```

```
curl "http://localhost:8000/analytics?from=2026-03-01&to=2026-03-31"
```

```
curl "http://localhost:8000/analytics?event=purchase&from=2026-03-01&to=2026-03-31&limit=5"
```

```
curl "http://localhost:8000/analytics?limit=10"
```

---

### GET /search

Semantic search over tracked events using FAISS vector similarity.

```
curl "http://localhost:8000/search?query=user+clicked+signup+button"
```

```
curl "http://localhost:8000/search?query=product+purchase&limit=5"
```

```
curl "http://localhost:8000/search?query=page+view+home"
```

```
curl "http://localhost:8000/search?query=search+for+laptop&limit=10"
```

```
curl "http://localhost:8000/search?query=user+logged+out&limit=1"
```

---

### GET /similar-users

Find users with similar behavior based on aggregated event embeddings.

```
curl "http://localhost:8000/similar-users?userId=user123"
```

```
curl "http://localhost:8000/similar-users?userId=user456&limit=3"
```

```
curl "http://localhost:8000/similar-users?userId=user789&limit=2"
```

```
curl "http://localhost:8000/similar-users?userId=user999&limit=5"
```

```
curl "http://localhost:8000/similar-users?userId=nonexistent_user"
```

---

## Explanation of Design Decisions

### /track endpoint

When a user event comes in, `/track` does two things:

1. **Saves the event to PostgreSQL** — so we can query it later for analytics (counts, filters, etc.)
2. **Generates a vector embedding and stores it in FAISS** — so we can search events by meaning, not just exact keywords

The embedding model (`all-MiniLM-L6-v2`) converts the event text into a 384-dimension vector. FAISS uses these vectors to find semantically similar events fast. For example, "purchased a laptop" and "bought a computer" would score as similar even though the words are different.

We store in both places because SQL is great for structured queries, and FAISS is great for similarity search. Each does what it's best at.

### /analytics endpoint

`/analytics` is a pure SQL endpoint — no vectors involved.

It returns three things:
- **Total events** — how many events match your filters
- **Events per user** — breakdown of event counts by user
- **Most active users** — top N users ranked by event count

You can filter by event name, date range, or both. All filtering happens in PostgreSQL using standard SQL aggregation (`COUNT`, `GROUP BY`, `ORDER BY`).

No embeddings are needed here because analytics is about counting, not about meaning.

### /search endpoint

`/search` lets you find events by meaning instead of exact keywords.

When you send a query like "user bought something", the endpoint:

1. **Converts your query into a vector** — using the same embedding model (`all-MiniLM-L6-v2`) that `/track` used
2. **Searches FAISS for the closest matching event vectors** — using cosine similarity (dot product on normalized vectors)
3. **Returns the top matching events from PostgreSQL** — with their details and a similarity score

This means a search for "purchased a laptop" can match an event like "buy computer" because the vectors are close in meaning, even though the words don't overlap.

The `limit` parameter controls how many results come back. Each result includes the event name, metadata, user, timestamp, and how similar it was to your query (0 to 1, higher = more similar).

### /similar-users endpoint

`/similar-users` finds users who behave similarly based on what events they've performed.

Here's how it works:

1. **Builds a profile vector for each user** — by averaging all of that user's event embeddings into a single vector (mean + normalize)
2. **Compares the query user's profile against every other user's profile** — using cosine similarity (dot product on normalized vectors)
3. **Returns the top matching users** — ranked by similarity score

**In-memory caching to avoid repeated DB lookups:**

Instead of querying the database and recomputing all user profiles on every request, we maintain an **in-memory dictionary cache** (`dict[user_id → profile_vector]`).

- On the **first call** to `/similar-users`, the cache is empty, so we build all user profiles from the DB and store them in memory.
- On **subsequent calls**, profiles are read directly from the cache — no DB query needed for embeddings.
- When a new event is tracked via `POST /track`, only the **affected user's profile is recomputed** from the DB and updated in the cache. All other user profiles remain untouched.
- The cache is protected by a **thread lock** (`RLock`) so concurrent requests don't cause race conditions.

This means the expensive "fetch all embeddings and aggregate" operation happens only once at startup (or on first request). After that, the cache stays current because `/track` keeps it updated incrementally — one user at a time.


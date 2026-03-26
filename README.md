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


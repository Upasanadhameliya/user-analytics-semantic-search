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


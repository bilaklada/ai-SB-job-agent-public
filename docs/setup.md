# Setup And Configuration

## Prerequisites

- Python 3.11
- Docker and Docker Compose
- Node.js 20+ for direct frontend development
- PostgreSQL for non-SQLite local development

## Environment File

Create a local `.env` from the public template:

```bash
cp .env.example .env
```

Minimum values for most local work:

- `DATABASE_URL`
- `SECRET_KEY`
- `CORS_ORIGINS`

Additional values depend on which subsystem you are exercising:

- Adzuna ingestion: `ADZUNA_API_KEY`, `ADZUNA_APP_ID`
- JSearch ingestion: `JSEARCH_API_KEY`
- Gemini/OpenAI/Anthropic-backed flows: corresponding API keys
- browser/VNC workflow: `VNC_PASSWORD`

## Running With Docker Compose

Start backend and frontend:

```bash
docker-compose up --build
```

Useful endpoints:

- backend: `http://localhost:8000`
- backend docs: `http://localhost:8000/docs`
- frontend: `http://localhost:3000`

Optional agent container:

```bash
docker-compose --profile agent up --build agent
```

## Backend Development

If you prefer not to use Docker:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

The frontend proxies `/api/*` requests to the backend.

## Database

The application falls back to SQLite for quick local bootstrapping, but the schema and migrations are primarily shaped around PostgreSQL.

Alembic commands:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

## Tests

Backend tests:

```bash
pytest
```

Frontend lint/build:

```bash
cd frontend
npm run lint
npm run build
```

## Public-Safe Omissions

The original private project included operational setup details that are intentionally not reproduced here, including:

- real credentials
- real candidate/application data
- internal runbooks
- private deployment identifiers

Use the code and public docs as the canonical source for structure; treat any missing secret-dependent workflow as intentionally omitted.

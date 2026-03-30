# DataPilot

Production-oriented scaffold for a **multi-agent AI Data Analyst** system that works with **PostgreSQL** (including **GLPI**-style schemas). The repo provides FastAPI, SQLAlchemy (sync + async), read-only SQL enforcement, ChromaDB memory helpers, and stub agents ready for LangChain / LangGraph workflows.

## Project layout

- `agents/` — Data, query, critic, analytics, insight, visualization, and memory agents (stubs).
- `api/` — FastAPI application and HTTP routes.
- `db/` — Engine pooling and safe read-only query execution.
- `services/` — Query and alert services.
- `memory/` — Chroma persistent client and embedding helpers.
- `models/` — Pydantic schemas for the API.
- `config.py` — Environment-driven settings.

## Setup

1. Create a virtual environment and install dependencies:

```bash
cd ~/Desktop/project/DataPilot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set values:

```bash
cp .env.example .env
```

- `DATABASE_URL` — PostgreSQL URL, e.g. `postgresql://user:pass@host:5432/glpi`
- `OPENAI_API_KEY` — For future LLM calls
- `CHROMA_DB_PATH` — Directory for Chroma persistence (default `./chroma`)

## Run the server

From the **DataPilot** folder (so `config` and packages resolve):

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## Example API request

**Health check**

```bash
curl -s http://localhost:8000/health
```

**Read-only SQL** (mutating keywords are rejected)

```bash
curl -s -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT 1 AS one", "limit": 10}'
```

## Security note

Only **read-only** SQL is allowed. Statements containing `DELETE`, `DROP`, `UPDATE`, or `INSERT` are rejected before execution.
# DataPilot

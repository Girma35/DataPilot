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

**API + Next.js together**

```bash
./scripts/dev-all.sh
```

**GLPI in Docker** (optional; then finish setup at http://localhost:8080 and enable the REST API + app tokens)

```bash
docker compose -f docker-compose.glpi.yml up -d
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

## Web UI + Auth0 (optional)

From `web/`:

```bash
npm install
npm run dev
```

The UI loads `.env` from the **repository root** (see `web/next.config.ts`). Set `NEXT_PUBLIC_AUTH0_*` and `DATAPILOT_API_URL` there.

## Auth0 Token Vault (intermediary agent → Slack)

`POST /agent/slack` exchanges the caller’s **Auth0 access token** (audience = your **DataPilot Custom API**) for a **Slack access token** stored in **Token Vault**, then calls Slack `chat.postMessage`. This matches the **Authorized to Act** hackathon pattern: OAuth, consent, and refresh are handled by Auth0; your backend never stores Slack secrets.

**Dashboard checklist (summary):**

1. Create a **Custom API** (identifier = e.g. `https://datapilot-api`) — use the same value for `AUTH0_AUDIENCE` (API) and `NEXT_PUBLIC_AUTH0_AUDIENCE` (SPA).
2. Enable **Token Vault** and **access token exchange** for that API ([configure Token Vault](https://auth0.com/docs/secure/tokens/token-vault/configure-token-vault)).
3. Create a **Custom API client** linked to that API with the Token Vault grant; set `AUTH0_TOKEN_VAULT_CLIENT_ID` / `AUTH0_TOKEN_VAULT_CLIENT_SECRET`.
4. Add a **Slack** social connection with **Connected Accounts for Token Vault** enabled; set `AUTH0_VAULT_SLACK_CONNECTION` to the connection name (often `slack`).
5. Complete the **Connected Accounts** flow for your test user (My Account API + [MRRT](https://auth0.com/docs/secure/tokens/refresh-tokens/multi-resource-refresh-token) as in Auth0 docs) so Slack appears under the user’s connected accounts.
6. Optional: `NEXT_PUBLIC_AUTH0_ADDITIONAL_SCOPES` for My Account scopes (e.g. `create:me:connected_accounts read:me:connected_accounts`) when you implement the connect UI.

Env vars: see `.env.example`.

## Security note

Only **read-only** SQL is allowed. Statements containing `DELETE`, `DROP`, `UPDATE`, or `INSERT` are rejected before execution.

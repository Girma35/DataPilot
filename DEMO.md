# DataPilot — full demo walkthrough

Use this script so your recording covers **every integrated feature**. Approx. order: infra → Auth0 → UI workflow → API docs → GLPI → background agent.

## 0. Prerequisites (before you hit Record)

| Item | Purpose |
|------|---------|
| Python venv + `pip install -r requirements.txt` | FastAPI API |
| `cp .env.example .env` + fill values | All services |
| PostgreSQL + `DATABASE_URL` | Read-only SQL demo (`/query`) |
| `OPENAI_API_KEY` (or Groq via `LLM_*` in config) | AI text for GLPI webhook path |
| `SLACK_WEBHOOK_URL` / `DISCORD_WEBHOOK_URL` | Webhook alerts (`/alert`, GLPI forward) |
| Auth0: SPA app + **Custom API** (same identifier in `AUTH0_AUDIENCE` + `NEXT_PUBLIC_AUTH0_AUDIENCE`) | Login + JWT for API |
| Auth0: Token Vault + access token exchange + **Custom API client** (`AUTH0_TOKEN_VAULT_CLIENT_*`) | `/agent/slack` |
| Slack connection: Connected Accounts + Token Vault; **your user connected Slack** | Token Vault post |
| `npm install` in `web/` | Next.js UI |

**Two terminals**

1. Repo root: `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
2. `web/`: `npm run dev` → open `http://localhost:3000`

Optional: show `DATAPILOT_API_URL=http://127.0.0.1:8000` in `.env` so the UI hits your API.

---

## 1. API discovery (30 seconds)

- Browser: `http://localhost:8000/` → JSON lists `docs`, `health`, `query`, `agent_slack_token_vault`.
- Open **`http://localhost:8000/docs`** — mention protected routes need **Authorize** with a Bearer token (from Auth0 after login; copy from devtools only for demo, or use UI).

---

## 2. Health (no DB required)

**UI:** Sign in → Step **1. Backend health** → Run health check → expect `status: ok`.

**curl (optional):**

```bash
curl -s http://localhost:8000/health
```

---

## 3. Auth0 sign-in (human + agent identity)

**UI:** Sign out if needed → **Sign in with Auth0** → complete login → land on home with your name/email.

**Say on camera:** “The SPA never handles Slack tokens; it only holds an Auth0 session. The API validates JWTs for the DataPilot Custom API audience.”

---

## 4. Read-only SQL agent (`QueryAgent` + `POST /query`)

**UI:** Step **2. Read-only query** — start with `SELECT 1 AS ok`, then optionally a real table from your GLPI/Postgres schema.

**Narrate:** “Mutating SQL is blocked in the query service.”

**If DB missing:** Show the error JSON in the panel; explain `DATABASE_URL` is required for real rows.

---

## 5. Webhook alerts (`AlertService` + `POST /alert`)

**UI:** Step **3. Slack / Discord (webhooks)** — choose Slack, Discord, or Both → Send alert.

**Say:** “This path uses server-side webhooks, not the user’s Slack OAuth.”

**If webhooks unset:** Show `skipped` in the JSON — explain env vars.

---

## 6. Intermediary agent + Auth0 Token Vault (`POST /agent/slack`)

**UI:** Step **4. Token Vault → Slack** — paste a **Slack channel ID** (`C…`) from a workspace where you connected Slack via Auth0 → **Post via Token Vault**.

**Say:** “Auth0 exchanges my API access token for a Slack token stored in Token Vault; the backend posts as me—no bot webhook.”

**If exchange fails:** Show 502 `detail` briefly; mention Slack must be **connected** for this user in Auth0 and Vault client must be configured.

---

## 7. GLPI webhook + AI message (`POST /webhook/glpi`)

**Not in the Next UI** — use curl or Swagger:

```bash
curl -s -X POST http://localhost:8000/webhook/glpi \
  -H "Content-Type: application/json" \
  -d '{
    "event": "ticket.created",
    "id": 1234,
    "name": "Demo printer offline",
    "priority": 3,
    "status": "new",
    "category": "Hardware",
    "requester": "demo@example.com"
  }'
```

**Say:** “Ticket-shaped payloads are normalized; optional LLM summarizes for alerts; forwarding uses the same webhook alert service.”

**If no API key:** Fallback message still sends (check `ai_message_service` behavior).

---

## 8. Background Insight agent (`InsightAgent` + APScheduler)

**No direct button** — mention while API is running:

- On startup, a **placeholder job** runs every **15 minutes** and calls `AlertService.send_placeholder` (webhook path).

**Say:** “This stub stands in for scheduled analytics/insights.”

**Optional demo trick:** Temporarily change interval in `agents/insight_agent.py` for a quicker tick (remember to revert).

---

## 9. Stub agents (mention, don’t live-demo unless you built on them)

Under `agents/`: data, critic, analytics, visualization, memory, etc. are **scaffold stubs**—good for “roadmap” slide, not required to click in the video.

---

## 10. Checklist for the hackathon story (closing lines)

- **Identity:** Auth0 for users; JWT for API.
- **Delegated access:** Token Vault for Slack as the user.
- **Safe data path:** Read-only SQL enforcement.
- **Integrations:** GLPI-shaped webhooks + optional AI blurbs + Slack/Discord alerts.

---

## Quick troubleshooting

| Symptom | Check |
|---------|--------|
| Login → broken URL | `NEXT_PUBLIC_AUTH0_*`, callback URL in Auth0 app |
| `/query` 401 | Same `AUTH0_AUDIENCE` as token `aud`; user signed in |
| Token Vault 502 | Vault client env vars; Slack connected; Custom API audience on token |
| Webhooks skipped | `SLACK_WEBHOOK_URL` / `DISCORD_WEBHOOK_URL` in `.env` |

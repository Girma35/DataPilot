# DataPilot - Comprehensive Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [GLPI Integration](#glpi-integration)
6. [Configuration](#configuration)
7. [Running the Application](#running-the-application)
8. [API Endpoints](#api-endpoints)
9. [Agent System](#agent-system)
10. [Security](#security)
11. [Examples](#examples)
12. [Troubleshooting](#troubleshooting)

---

# DataPilot - Comprehensive Documentation

## Quick Start

```bash
# 1. Clone and setup
git clone <repository-url>
cd DataPilot
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure (create .env file)
DATABASE_URL=postgresql://user:pass@localhost:5432/glpi

# 3. Run
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Test
curl http://localhost:8000/health
```

---

## Project Overview

**DataPilot** is a production-oriented multi-agent AI Data Analyst system designed to work with PostgreSQL databases, specifically optimized for **GLPI** (Gestion Libre de Parc Informatique) - an IT Asset Management system.

### What is GLPI?
GLPI is a popular open-source IT Asset Management software that stores:
- **Tickets** - Help desk and support tickets
- **Assets** - Computers, printers, network equipment, software
- **Users** - Employee and customer information
- **Contracts** - Software and hardware licenses
- **Knowledge base** - FAQ and documentation

### What DataPilot Does
DataPilot provides an AI-powered interface to:
- Query GLPI data through natural language or SQL
- Analyze GLPI data for insights (ticket patterns, SLA compliance, asset distribution)
- Generate visualizations and reports
- Send alerts to Slack/Discord when specific conditions are met
- Maintain memory of past interactions using vector storage

---

## Architecture

```
DataPilot/
|-- agents/                 # AI Agent implementations
|   |-- query_agent.py      # Converts natural language to SQL (stub)
|   |-- data_agent.py       # Fetches and normalizes data from DB
|   |-- analytics_agent.py  # Statistical analysis and aggregations
|   |-- visualization_agent.py  # Chart generation (Plotly)
|   |-- memory_agent.py     # Vector-based memory (ChromaDB)
|   |-- insight_agent.py    # Scheduled insights with APScheduler
|   |-- critic_agent.py     # Output verification (stub)
|
|-- api/                   # FastAPI HTTP endpoints
|   |-- main.py            # Application entrypoint
|
|-- db/                    # Database connection layer
|   |-- connection.py      # SQLAlchemy engines, read-only enforcement
|
|-- services/              # Business logic services
|   |-- query_service.py   # Query execution wrapper
|   |-- alert_service.py   # Slack/Discord notifications
|
|-- memory/                # Vector store for memory
|   |-- vector_store.py    # ChromaDB client
|
|-- models/                # Pydantic schemas
|   |-- schemas.py         # Request/Response models
|
|-- config.py              # Environment configuration
|-- requirements.txt       # Python dependencies
```

---

## Prerequisites

### Software Requirements
- **Python 3.10+**
- **PostgreSQL** (with GLPI database)
- **Git** (for cloning)

### Python Packages
All dependencies are listed in `requirements.txt`:
```
fastapi              # Web framework
uvicorn              # ASGI server
psycopg2-binary      # PostgreSQL driver (sync)
asyncpg              # PostgreSQL driver (async)
sqlalchemy           # ORM
pandas               # Data manipulation
numpy                # Numerical computing
langchain            # LLM framework (stub)
langgraph            # Agent workflows (stub)
openai               # OpenAI integration
chromadb             # Vector database
matplotlib           # Plotting
plotly               # Interactive charts
apscheduler          # Job scheduling
reportlab            # PDF generation
python-dotenv        # Environment variables
requests             # HTTP client
```

---

## Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd DataPilot
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Database Configuration (REQUIRED)
DATABASE_URL=postgresql://username:password@host:port/glpi

# AI Integration (Optional - for future LLM features)
OPENAI_API_KEY=sk-your-openai-key

# Vector Database (Optional - defaults to ./chroma)
CHROMA_DB_PATH=./chroma

# Alert Notifications (Optional)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/XXX/YYY
```

#### DATABASE_URL Format
```
postgresql://username:password@host:port/database_name
```

Example for local GLPI:
```
DATABASE_URL=postgresql://glpi_user:glpi_pass@localhost:5432/glpi
```

---

## GLPI Integration

### What DataPilot Needs from GLPI

DataPilot is designed to work with GLPI's PostgreSQL database. Here's what it interacts with:

#### Core GLPI Tables

| Table | Description | Common Queries |
|-------|-------------|----------------|
| `glpi_tickets` | Help desk tickets | Count by status, priority, assignment |
| `glpi_users` | User accounts | Active users, last login |
| `glpi_computers` | Computer assets | Hardware inventory |
| `glpi_printers` | Printer assets | Printer status |
| `glpi_software` | Software licenses | License compliance |
| `glpi_entities` | Organizational entities | Multi-entity support |
| `glpi_groups` | User groups | Team organization |
| `glpi_profiles` | User profiles | Permission levels |
| `glpi_contracts` | Contracts | Expiration tracking |
| `glpi_locations` | Physical locations | Asset distribution |

#### GLPI Database Schema Details

To explore GLPI tables, you can use the `DataAgent.list_tables()` method:

```python
from agents.data_agent import DataAgent

agent = DataAgent()
tables = agent.list_tables()
print(tables)
```

To get schema information for a specific table:

```python
schema = agent.get_table_schema("glpi_tickets")
print(schema)
```

### Required GLPI Permissions

The database user needs **read-only** access to GLPI tables:

```sql
-- Grant read-only access (execute as database admin)
GRANT CONNECT ON DATABASE glpi TO datapilot;
GRANT USAGE ON SCHEMA public TO datapilot;

-- Grant SELECT on all GLPI tables
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datapilot;

-- Optional: For future write operations
-- (DataPilot only uses SELECT by default)
```

### Security: Read-Only Enforcement

DataPilot **blocks** any SQL containing:
- `DELETE`
- `DROP`
- `UPDATE`
- `INSERT`

This is enforced in `db/connection.py`:

```python
_FORBIDDEN_SQL = re.compile(
    r"\b(DELETE|DROP|UPDATE|INSERT)\b",
    re.IGNORECASE | re.DOTALL,
)
```

---

## Configuration

### Environment Variables

| Variable | Required | Description | Default |
|----------|----------|-------------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string | - |
| `OPENAI_API_KEY` | No | OpenAI API key for LLM features | Empty |
| `CHROMA_DB_PATH` | No | Path for Chroma vector storage | `./chroma` |
| `SLACK_WEBHOOK_URL` | No | Slack webhook for alerts | Empty |
| `DISCORD_WEBHOOK_URL` | No | Discord webhook for alerts | Empty |

### Configuration File (config.py)

The `config.py` module loads these variables:

```python
from config import DATABASE_URL, OPENAI_API_KEY, CHROMA_DB_PATH
```

---

## Running the Application

### Start the Server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Verify Server is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "DataPilot"
}
```

### API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## API Endpoints

### 0. Root Endpoint

**GET** `/`

Returns service information and available endpoints.

```bash
curl http://localhost:8000/
```

Response:
```json
{
  "service": "DataPilot",
  "docs": "/docs",
  "health": "/health",
  "query": "POST /query"
}
```

---

### 1. Health Check

**GET** `/health`

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "ok",
  "service": "DataPilot"
}
```

---

### 2. Execute SQL Query

**POST** `/query`

Execute read-only SQL queries against the GLPI database.

**Request Body:**
```json
{
  "sql": "SELECT * FROM glpi_tickets LIMIT 10",
  "limit": 10
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT * FROM glpi_tickets WHERE status = 1 LIMIT 5", "limit": 5}'
```

**Response:**
```json
{
  "ok": true,
  "rows": [...],
  "row_count": 5
}
```

**Error Response (Invalid SQL):**
```json
{
  "detail": "Only read-only queries are allowed; DELETE, DROP, UPDATE, and INSERT are not permitted."
}
```

---

### 3. Send Alert

**POST** `/alert`

Send notifications to Slack and/or Discord.

**Request Body:**
```json
{
  "message": "Ticket #1234 has been open for over 48 hours!",
  "channel": "slack"
}
```

**Parameters:**
- `message` (string, required): Alert message
- `channel` (string, required): One of `slack`, `discord`, or `both`

**Example:**
```bash
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"message": "SLA breach detected!", "channel": "both"}'
```

**Response:**
```json
{
  "ok": true,
  "results": {
    "slack": {"status": "success", "code": 200},
    "discord": {"status": "success", "code": 200}
  }
}
```

---

### 4. GLPI Webhook

**POST** `/webhook/glpi`

Receive ticket notifications from GLPI and optionally forward to Slack/Discord.

**Server Port:** The server runs on **port 8000** by default.

**Request Body:**
```json
{
  "event": "ticket.created",
  "id": 1234,
  "name": "Printer not working",
  "priority": 3,
  "status": "new",
  "category": "Hardware",
  "requester": "john@example.com"
}
```

**Supported Event Types:**
- `ticket.created` - New ticket created
- `ticket.updated` - Ticket updated
- `ticket.closed` - Ticket closed
- `ticket.resolved` - Ticket resolved
- `ticket.reply` - Reply added to ticket
- `ticket.note` - Note added to ticket
- `ticket.assigned` - Ticket assigned to user/group
- `ticket.priority_changed` - Priority changed
- `ticket.status_changed` - Status changed

**Example:**
```bash
curl -X POST http://localhost:8000/webhook/glpi \
  -H "Content-Type: application/json" \
  -d '{"event": "ticket.created", "id": 1234, "name": "Test ticket", "priority": 3, "status": "new"}'
```

**Response:**
```json
{
  "ok": true,
  "processed": true,
  "alert_sent": true,
  "message": "Webhook processed and alert forwarded"
}
```

**Configuring GLPI to send webhooks:**

In GLPI, set up a webhook notification pointing to:
```
http://your-server:8000/webhook/glpi
```

You can use GLPI's notification system or a plugin like "Webhook" to send POST requests to this endpoint when ticket events occur.

---

## Agent System

### QueryAgent

Converts natural language to validated SQL (stub for future LLM integration).

```python
from agents.query_agent import QueryAgent
from services.query_service import QueryService

agent = QueryAgent(QueryService())
results = agent.execute("SELECT COUNT(*) FROM glpi_tickets")
```

---

### DataAgent

Fetches and normalizes data from PostgreSQL into pandas DataFrames.

**Methods:**

| Method | Description |
|--------|-------------|
| `run(sql=..., table_name=..., limit=...)` | Fetch data as DataFrame |
| `get_table_schema(table_name)` | Get column info |
| `list_tables(schema='public')` | List all tables |
| `fetch_sample(table_name, sample_size=100)` | Random sample |

**Example:**
```python
from agents.data_agent import DataAgent

agent = DataAgent()

# Get all tickets
df = agent.run(sql="SELECT * FROM glpi_tickets WHERE status = 1")

# Get table schema
schema = agent.get_table_schema("glpi_tickets")

# List tables
tables = agent.list_tables()
```

---

### AnalyticsAgent

Performs statistical analysis on DataFrames.

**Methods:**

| Method | Description |
|--------|-------------|
| `run(df)` | Comprehensive analytics |
| `aggregate(df, group_by, agg_func, column)` | Group aggregations |
| `pivot_table(df, index, columns, values, aggfunc)` | Pivot tables |
| `time_series_analysis(df, date_col, value_col)` | Time series analysis |

**Example:**
```python
from agents.analytics_agent import AnalyticsAgent
from agents.data_agent import DataAgent

data_agent = DataAgent()
df = data_agent.run(sql="SELECT * FROM glpi_tickets")

analytics = AnalyticsAgent()
results = analytics.run(df)
```

**Output Structure:**
```python
{
    "summary": {
        "rows": 1000,
        "columns": 15,
        "column_names": [...],
        "dtypes": {...},
        "null_counts": {...}
    },
    "numeric_columns": {
        "id": {"mean": 500, "median": 500, "std": 289, ...},
        "priority": {"mean": 3.2, ...}
    },
    "categorical_columns": {
        "status": {"unique": 5, "top_values": [...]}
    },
    "correlations": {...},
    "outliers": {...}
}
```

---

### VisualizationAgent

Creates charts and dashboards using Plotly.

**Chart Types:**
- `auto` - Auto-detect best type
- `bar` - Bar charts
- `line` - Line charts
- `scatter` - Scatter plots
- `pie` - Pie charts
- `histogram` - Histograms
- `box` - Box plots

**Example:**
```python
from agents.visualization_agent import VisualizationAgent
from agents.data_agent import DataAgent

data_agent = DataAgent()
df = data_agent.run(sql="SELECT category, COUNT(*) as cnt FROM glpi_tickets GROUP BY category")

viz = VisualizationAgent()
chart = viz.run(df, chart_type="bar", x="category", y="cnt", title="Tickets by Category")

# Access output
print(chart["html"])      # HTML embed
print(chart["image_base64"])  # Base64 PNG
```

**Dashboard Creation:**
```python
config = {
    "charts": [
        {"type": "bar", "x": "category", "y": "count", "title": "By Category"},
        {"type": "line", "x": "date", "y": "count", "title": "Trend"}
    ]
}
dashboard = viz.create_dashboard(df, config)
```

**Generate Report:**
```python
report = viz.generate_summary_report(df, analytics_results)
print(report)  # Markdown formatted
```

---

### AlertService

Sends notifications to Slack and Discord.

**Example:**
```python
from services.alert_service import AlertService

alerts = AlertService(
    slack_webhook="https://hooks.slack.com/...",
    discord_webhook="https://discord.com/api/webhooks/..."
)

# Send to both
results = alerts.send("SLA breach alert!", channel="both")

# Send to specific
results = alerts.send("Warning message", channel="slack")
```

---

### InsightAgent

Scheduled insight generation using APScheduler. **This agent is functional**, not a stub.

**Features:**
- Runs periodic jobs (default: every 15 minutes)
- Sends alerts when scheduled jobs execute
- Automatically started when API server starts

**Usage:**
```python
from agents.insight_agent import InsightAgent

agent = InsightAgent()
agent.start_scheduler()

# Shutdown when done
agent.shutdown_scheduler(wait=True)
```

---

### MemoryAgent

Vector-based memory using ChromaDB (stub for RAG features).

```python
from agents.memory_agent import MemoryAgent

agent = MemoryAgent(collection_name="glpi_insights")
# Currently a placeholder - needs implementation
```

---

## Security

### Read-Only SQL Enforcement

All queries are validated before execution. The following operations are **blocked**:

- `DELETE` - Data deletion
- `DROP` - Table/schema deletion
- `UPDATE` - Data modification
- `INSERT` - Data insertion

### Input Validation

Table and column names are validated using regex:
```python
_VALID_IDENTIFIER = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)?$")
```

This prevents SQL injection attacks.

### Database Permissions

Always use a read-only database user for DataPilot:

```sql
-- Create dedicated read-only user
CREATE USER datapilot_ro WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE glpi TO datapilot_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO datapilot_ro;
```

---

## End-to-End Workflow Example

Here's how to use multiple agents together for a complete data analysis pipeline:

```python
from agents.data_agent import DataAgent
from agents.analytics_agent import AnalyticsAgent
from agents.visualization_agent import VisualizationAgent

# Step 1: Fetch data from GLPI
data_agent = DataAgent()
df = data_agent.run(sql="""
    SELECT 
        DATE(date_creation) as date,
        priority,
        status,
        COUNT(*) as ticket_count
    FROM glpi_tickets
    WHERE date_creation > CURRENT_DATE - INTERVAL '30 days'
    GROUP BY DATE(date_creation), priority, status
""")

# Step 2: Analyze the data
analytics = AnalyticsAgent()
results = analytics.run(df)
print(f"Total tickets: {results['summary']['rows']}")
print(f"Average priority: {results['numeric_columns'].get('priority', {}).get('mean', 0):.2f}")

# Step 3: Create visualization
viz = VisualizationAgent()
chart = viz.run(
    df, 
    chart_type="bar", 
    x="date", 
    y="ticket_count", 
    title="Tickets Last 30 Days"
)
print(chart["image_base64"])  # Use in HTML/React app

# Step 4: Generate report
report = viz.generate_summary_report(df, results)
print(report)
```

---

## Testing Your Setup

### Verify Database Connection

```python
from services.query_service import QueryService

service = QueryService()
result = service.run_read_query("SELECT 1 as test")
print(result)  # [{'test': 1}]
```

### List GLPI Tables

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT table_name FROM information_schema.tables WHERE table_schema = \'public\' LIMIT 20"}'
```

### Verify Alert Service

```bash
# Test with invalid channel (should fail)
curl -X POST http://localhost:8000/alert \
  -H "Content-Type: application/json" \
  -d '{"message": "test", "channel": "invalid"}'
```

---

## Examples

### Example 1: Count Tickets by Status

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT status, COUNT(*) as count FROM glpi_tickets GROUP BY status",
    "limit": 10
  }'
```

### Example 2: Find High Priority Open Tickets

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT id, name, priority, DATE(date_creation) as created FROM glpi_tickets WHERE priority >= 4 AND status = 1 ORDER BY priority DESC LIMIT 20"
  }'
```

### Example 3: Asset Distribution by Location

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT location_id, COUNT(*) as total FROM glpi_computers GROUP BY location_id ORDER BY total DESC"
  }'
```

### Example 4: User Activity Report

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "SELECT DATE(last_login) as date, COUNT(*) as logins FROM glpi_users WHERE last_login IS NOT NULL GROUP BY DATE(last_login) ORDER BY date DESC LIMIT 30"
  }'
```

---

## Troubleshooting

### Database Connection Failed

**Error:** `RuntimeError: DATABASE_URL is not set`

**Solution:** Ensure `.env` file exists and contains valid `DATABASE_URL`

---

### Permission Denied

**Error:** `permission denied for table glpi_tickets`

**Solution:** Grant SELECT permission to database user:
```sql
GRANT SELECT ON TABLE glpi_tickets TO datapilot_user;
```

---

### Query Blocked

**Error:** `Only read-only queries are allowed`

**Solution:** Remove DELETE, DROP, UPDATE, or INSERT from your query. DataPilot only supports SELECT statements.

---

### Slack/Discord Alerts Not Sending

**Check:**
1. Webhook URLs are correctly configured in `.env`
2. Webhooks are still active (check Slack/Discord workspace)
3. Network allows outbound HTTPS connections

---

### Import Errors

**Error:** `ModuleNotFoundError: No module named '...`

**Solution:** Ensure virtual environment is activated and dependencies are installed:
```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Future Enhancements

The following features are planned or stubbed for future implementation:

1. **Natural Language Querying** - Convert English to SQL using LLM
2. **Memory/RAG** - Context-aware responses using ChromaDB
3. **Critic Agent** - Validate and improve query results
4. **Scheduled Reports** - Automatic GLPI reports via email
5. **SLA Monitoring** - Real-time SLA breach detection
6. **Predictive Analytics** - Ticket volume forecasting

---

## License

This project is provided as-is for educational and production use.

---

## Support

For issues and questions:
1. Check the API documentation at `/docs`
2. Review the example queries above
3. Examine the agent source code in `/agents`
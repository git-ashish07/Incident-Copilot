# IncidentPilot

An AI-powered incident-response copilot that helps on-call engineers triage production issues fast — citing runbooks, recalling past postmortems, querying logs and metrics, and opening GitHub issues — while **never taking autonomous production actions**. All deploy and rollback steps require explicit human approval.

---

## What It Does

- **RAG over runbooks & postmortems** — retrieves relevant documented steps and cites the source, never improvises
- **Log & metrics querying** — calls a log/metrics tool to pull data for a given service and timeframe
- **Short-term memory** — rolls up prior turns in the session into a condensed prose summary so older context is never hard-dropped
- **Long-term memory** — at startup, scans unprocessed sessions in Postgres and extracts incident records and durable notes into ChromaDB; recalled by vector similarity on every query
- **GitHub issue creation** — opens a tracked issue with the triage summary via a tool call
- **Guardrails** — refuses to execute any deploy, rollback, or production-mutating action; drafts steps for a human to approve and run

---

## Documentation

| File | Description |
|------|-------------|
| [docs/requirements.md](docs/requirements.md) | Objective, user persona, sample queries, constraints, and guardrail requirements |
| [docs/tasks.md](docs/tasks.md) | 4-week build plan with definitions of done and evidence of completion |
| [docs/tools.md](docs/tools.md) | Tool specs: inputs, output shape, and error cases for all MCP tools |
| [docs/memory-schema.md](docs/memory-schema.md) | Memory design: short-term, incident-log, and notes store schemas |

---

## User Persona

**Alex Kim** — SRE on a rotating on-call schedule. Gets paged at 2am for a service degradation and needs to triage fast without digging through scattered runbooks, old postmortems, and log dashboards under pressure. Goal: cut mean-time-to-diagnosis, not mean-time-to-fix-without-a-human.

---

## Project Structure

```
incident-copilot/
├── chat_langgraph.py              # Gradio UI — LangGraph agent with streaming + side panels
├── main_langgraph.py              # CLI entry point — LangGraph agent (batch / logging)
├── main_mcp.py                    # CLI entry point — raw MCP tool-call loop (reference)
├── main.py                        # Legacy CLI entry point
├── pyproject.toml                 # Project config and dependencies
├── uv.lock                        # Locked dependency versions
├── .env-example                   # Example environment variables
├── src/
│   ├── data/
│   │   ├── data_overview.md             # Plain-language guide to all data assets
│   │   ├── sample_incident_queries.py   # Sample queries for dry runs
│   │   ├── incidents/
│   │   │   └── incidents.json           # Structured past-incident records
│   │   ├── metrics/                     # Synthetic per-day time-series metrics (CSV)
│   │   ├── logs/                        # Synthetic per-day raw logs (JSONL)
│   │   └── corpus/                      # RAG corpus — runbooks, postmortems, code docs
│   │       ├── runbooks/
│   │       ├── postmortems/
│   │       ├── code_docs/
│   │       └── sources.md
│   └── utils/
│       ├── llm_config.py                # LLM factory (Groq + OpenAI)
│       ├── models.py                    # Pydantic schemas + AgentState
│       ├── tools.py                     # MCP tool definitions (get_logs, get_metrics, …)
│       ├── nodes.py                     # LangGraph node factories
│       ├── memory.py                    # Short-term summarizer + long-term memory sweep
│       ├── pgdb.py                      # Postgres helpers for durable session storage
│       ├── prompts/
│       │   ├── system_prompts.py
│       │   └── prompt_template.py
│       └── rag/
│           ├── ingestion_funcs.py
│           └── retrieval_funcs.py
├── experiments/
│   └── code.ipynb
└── docs/
    ├── requirements.md
    ├── tasks.md
    ├── tools.md                   # MCP tool specs
    └── memory-schema.md           # Memory store design
```

---

## Getting Started

```bash
# Clone the repo
git clone <repo-url>
cd incident-copilot

# Create a virtual environment
uv venv

# Activate the virtual environment
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS / Linux

# Install dependencies
uv sync
```

> **Note:** This project uses [uv](https://docs.astral.sh/uv/) for dependency management. If you don't have it: `pip install uv` or see the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

To add a new library:
```bash
uv add <package-name>
```

---

## Tech Stack

| Area               | Technology                                      |
|--------------------|-------------------------------------------------|
| Language           | Python 3.11+                                    |
| LLM / Model        | OpenAI (primary), Groq (secondary)              |
| Agent Framework    | LangGraph (`StateGraph` + `InMemorySaver`)      |
| RAG / Vector Store | ChromaDB + BM25 + cross-encoder re-rank         |
| Tools / MCP        | FastMCP (`fastmcp`) — tools exposed as MCP server |
| Short-term Memory  | LangGraph in-memory checkpointer (rolling summary) |
| Long-term Memory   | ChromaDB (`incident_memory`, `agent_notes`) + PostgreSQL (session transcript log) |
| UI                 | Gradio                                          |
| Guardrails         | TBD                                             |
| Observability      | Per-run log files (`run_logs/`)                 |
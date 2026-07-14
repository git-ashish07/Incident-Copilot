# IncidentPilot

An AI-powered incident-response copilot that helps on-call engineers triage production issues fast — citing runbooks, recalling past postmortems, querying logs and metrics, and opening GitHub issues — while **never taking autonomous production actions**. All deploy and rollback steps require explicit human approval.

---

## What It Does

- **RAG over runbooks & postmortems** — retrieves relevant documented steps and cites the source, never improvises
- **Log & metrics querying** — calls a log/metrics tool to pull data for a given service and timeframe
- **Memory** — recalls similar past incidents and how they were resolved
- **GitHub issue creation** — opens a tracked issue with the triage summary via a tool call
- **Guardrails** — refuses to execute any deploy, rollback, or production-mutating action; drafts steps for a human to approve and run

---

## Documentation

| File | Description |
|------|-------------|
| [docs/requirements.md](docs/requirements.md) | Objective, user persona, sample queries, constraints, and guardrail requirements |
| [docs/tasks.md](docs/tasks.md) | 4-week build plan with definitions of done and evidence of completion |
| [docs/team.md](docs/team.md) | Team roster with roles, tech stacks, and requirements confirmation |
| [docs/team-assignments.md](docs/team-assignments.md) | Task ownership and comments per week |

---

## User Persona

**Alex Kim** — SRE on a rotating on-call schedule. Gets paged at 2am for a service degradation and needs to triage fast without digging through scattered runbooks, old postmortems, and log dashboards under pressure. Goal: cut mean-time-to-diagnosis, not mean-time-to-fix-without-a-human.

---

## Project Structure

```
incident-copilot/
├── main.py                        # Entry point
├── pyproject.toml                 # Project config and dependencies
├── uv.lock                        # Locked dependency versions
├── .env-example                   # Example environment variables
├── .gitignore
├── .python-version
├── src/
│   ├── data/
│   │   └── sample_incident_queries.py   # Sample queries for dry runs
│   ├── llm_funcs/
│   │   └── llm_config.py                # LLM instance configuration
│   ├── prompts/
│   │   ├── system_prompts.py            # System prompt definitions
│   │   └── prompt_template.py           # Prompt template builder
│   └── utils/                           # Shared utility helpers
├── experiments/
│   └── [member-name]/
│       └── code.ipynb                   # Experimentation notebook
└── docs/
    ├── requirements.md            # Full project requirements and sample queries
    ├── tasks.md                   # 4-week task plan (32 tasks)
    ├── team.md                    # Team roster, roles, and agreed tech stack
    └── team-assignments.md        # Per-task ownership and status by week
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

| Area             | Technology              |
|------------------|-------------------------|
| Language         | Python 3.11+            |
| LLM / Model      | Groq Cloud              |
| RAG / Vector Store | ChromaDB / FAISS / Qdrant |
| UI               | Gradio                  |
| Framework        | TBD                     |
| Memory           | TBD                     |
| MCP / Tools      | TBD                     |
| Guardrails       | TBD                     |
| Caching          | TBD                     |
| Observability    | TBD                     |
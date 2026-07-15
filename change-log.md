# Changelog

A running log of changes made to this repo — organized by date and author so anyone joining mid-project can quickly get up to speed.

---

## 2026-07-15 — Kartik

### Structure-sequencing decision + doc freshness pass, ahead of Tasks 6/7/9
- Reviewed an external AI-agent project template against IncidentPilot's actual requirements; adopted the layer-based `src/` organizing principle but rejected scaffolding empty `agent/`/`guardrails/`/`tools/`/`observability/` folders ahead of the weeks that need them — logged as `docs/decision-log.md` ADR-10.
- Decided the target structure will be reached incrementally: each folder gets created only when its first real file is written, sized to exactly what that task needs.
- Refreshed "last updated"/"as of" stamps on the living-status docs (`current-project-working-structure-design.md`, `enterprise-level-architecture-design.md`, `week1-task-status.md`) to reflect today's review. Historical dates in this changelog and in `decision-log.md`'s existing ADR entries were deliberately left untouched — they record when things actually happened, not when they were last read.
- No code changed. Next up: Task 6 (`src/retrieval/ingest.py`) and Task 7 (`src/retrieval/retriever.py`), per ADR-10's scoped plan.

---

## 2026-07-14 — Kartik

### Architecture review, Week 1 status audit, and system-prompt hardening
- **Architecture documentation** added under `docs/`:
  - `current-project-working-structure-design.md` — as-is vs. target-state HLD of the whole system, cross-checked against actual repo contents rather than the task plan alone
  - `enterprise-level-architecture-design.md` — leadership-facing delivery roadmap, one diagram per week, mapped to `requirements.md` and `tasks.md`
  - `week1-task-status.md` — task-by-task Week 1 status audited against real repo state (not just the `team-assignments.md` tracker, which was found to be stale for Tasks 4/5)
  - `decision-log.md` — new running ADR-style log for architecture/design decisions (see below)
- **System prompt hardened** (Task 3, scoped to not pull in later-week work):
  - `src/prompts/system_prompts.py` — added a citation contract (confirmed facts must cite the `[RETRIEVED CONTEXT]` block by source name), split grounding rules from escalation rules into their own sections, added three worked examples (confirmed/possible, refusal, escalation), reworded `CONSTRAINTS` so it no longer implies the prompt alone enforces the no-execution rule
  - `src/prompts/prompt_template.py` — added a `{retrieved_context}` slot and `NO_CONTEXT_PLACEHOLDER` constant, ready for Tasks 6-7 (retrieval) to populate
  - `main.py` — updated to pass the placeholder so the existing round trip keeps running; verified the template still renders correctly
  - Deliberately deferred: prompt-injection guard wording (no retrieved content exists yet to protect) and a prompt-version identifier (belongs to Task 24, observability)
- No changes to retrieval, tools, guardrails, or UI — Tasks 6, 7, and 9 are still outstanding, per `week1-task-status.md`.

---

## 2026-07-14 — Ashish Rathore

### Added synthetic dataset and RAG corpus (Task 4 & 5)
- **Synthetic incident data** added under `src/data/`:
  - `incidents/incidents.json` — structured synthetic incident log covering multiple services
  - `metrics/checkout-service_metrics.csv` and `metrics/payments-service_metrics.csv` — time-series metrics data
  - `data_overview.md` — summary of all data assets and how they relate to the sample queries
- **RAG corpus** added under `src/data/corpus/`:
  - `postmortems/` — three postmortem documents: `INC-1001` (payments connection pool exhaustion), `INC-1002` (checkout deploy latency regression), `INC-1003` (auth service cache stampede)
  - `runbooks/` — five runbooks covering connection pool exhaustion, deploy rollback procedure, high latency triage, hotfix and production change policy, and incident tracking via GitHub issues
  - `code_docs/` — architecture docs for the checkout service deploy pipeline and payments service
  - `sources.md` — index of all corpus sources with coverage mapping to the 6 sample queries in `requirements.md`
- Updated `README.md` to reflect data and corpus additions
- Updated `docs/team-assignments.md` with task 4/5 completion status
- Updated experiment notebook `experiments/ashish/code.ipynb` with latest runs

### Updated README (Task 3 wrap-up)
- Revised README structure for clarity — section headings, stack description, and quickstart steps updated

---

## 2026-07-14 — Ashish Rathore

### Completed Task 3 — System prompt + project structure refactor
- **`src/prompts/system_prompts.py`** — system prompt implementing the triage-copilot tone and the "no autonomous production actions" guardrail rule
- **`src/prompts/prompt_template.py`** — prompt template wiring user input into the system prompt
- **`src/llm_funcs/llm_config.py`** — LLM configuration (model, temperature, client setup)
- **`main.py`** — extended with full description → triage-summary round trip using the above modules
- **`src/data/sample_incident_queries.py`** — added 6 sample incident queries from `requirements.md` for manual testing
- **Restructured experiment notebooks**: moved `notebooks/ashish-code.ipynb` → `experiments/ashish/code.ipynb` to align with the agreed folder layout
- Updated `README.md` and `docs/team-assignments.md` to reflect completed tasks and new structure

---

## 2026-07-12 — Ashish Rathore

### Task 3 — System prompt experiment (initial notebook work)
- **`notebooks/ashish-code.ipynb`** — expanded with system prompt experiments: drafted triage-copilot persona, tested "no autonomous production actions" rule with 2 manual prompts
- **`pyproject.toml`** — added LLM dependencies (`openai`, `python-dotenv`, etc.)
- **`uv.lock`** — dependency lockfile generated
- **`.env-example`** — added example env file documenting required environment variables (API keys, model name)

---

## 2026-07-10 — Ashish Rathore

### Project setup — docs, folder structure, and README (Task 1 & 2)
- **`docs/requirements.md`** — project requirements document (Alex Kim persona, objectives, guardrail rules, sample queries, expected answers)
- **`docs/tasks.md`** — full 4-week, 32-task plan for the team
- **`docs/team.md`** — team roster, roles (prompt/RAG, tools/MCP, memory, guardrails/caching, observability/UI), and agreed tech stack
- **`docs/team-assignments.md`** — per-member task assignments and progress tracking
- **`main.py`** — scaffolded entry point for the application
- **`notebooks/ashish-code.ipynb`** — initial experiment notebook created
- **`pyproject.toml`** — project metadata and base dependencies
- **`.python-version`** — pinned Python version for the project
- Updated `README.md` with project overview, goals, folder structure, and setup instructions

---

## 2026-07-10 — Ashish Rathore

### Initial commit
- **`.gitignore`** — comprehensive Python gitignore (virtual envs, `.env`, `__pycache__`, IDE files, etc.)
- **`README.md`** — placeholder README created
